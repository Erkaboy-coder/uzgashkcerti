from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from labcerti.models import Certificate, UserProfile
from django.contrib import messages
from django.db.models import Q
from django.contrib import messages
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import traceback
from django.db import transaction
import os
from django.core.paginator import Paginator
from datetime import timedelta
from django.utils import timezone

@login_required
def dashboard(request, status=None):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'approver':
        return redirect('login')

    # Asosiy queryset — qoralamalarni chiqarib tashlaymiz
    queryset = Certificate.objects.exclude(status='draft').order_by('-created_at')

    # Status bo‘yicha filter (URL orqali)
    if status in ['pending', 'approved', 'rejected']:
        queryset = queryset.filter(status=status)

    # GET orqali qidiruv
    certificate_number = request.GET.get('certificate_number')
    owner_inn = request.GET.get('owner_inn')
    device_name = request.GET.get('device_name')
    device_serial = request.GET.get('device_serial')
    status_get = request.GET.get('status')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    if certificate_number:
        queryset = queryset.filter(certificate_number__icontains=certificate_number)
    if owner_inn:
        queryset = queryset.filter(owner_inn__icontains=owner_inn)
    if device_name:
        queryset = queryset.filter(device_name__icontains=device_name)
    if device_serial:
        queryset = queryset.filter(device_serial_numbers__icontains=device_serial)
    if status_get in ['pending', 'approved', 'rejected']:
        queryset = queryset.filter(status=status_get)
    if from_date:
        queryset = queryset.filter(created_at__date__gte=from_date)
    if to_date:
        queryset = queryset.filter(created_at__date__lte=to_date)

    # Statistikalar (draftsizlik bilan)
    pending_count = Certificate.objects.filter(status='pending').count()
    approved_count = Certificate.objects.filter(status='approved').count()
    rejected_count = Certificate.objects.filter(status='rejected').count()
    total_count = pending_count + approved_count + rejected_count  # draftsiz jami

    # Paginator
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'certificates': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'current_status': status if status else (status_get if status_get else ''),
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_certificates_count': total_count,
        'request': request,  # search form uchun
    }
    return render(request, 'labcerti/approver/dashboard.html', context)


@login_required
def approve_certificate(request, pk):
    if request.method == "POST":
        certificate = get_object_or_404(Certificate, pk=pk)
        user_profile = get_object_or_404(UserProfile, user=request.user)

        try:
            with transaction.atomic():
                if certificate.status == 'pending':
                    certificate.status = 'approved'

                    # Tasdiqlashda comparison_date va valid_until_date set qilish
                    if not certificate.comparison_date:
                        certificate.comparison_date = timezone.now().date()
                    certificate.valid_until_date = certificate.comparison_date + timedelta(days=365)

                certificate.approved_by = user_profile
                certificate.approved_at = timezone.now()

                # Fayllar o'chirish va yaratish
                if certificate.certificate_file:
                    try:
                        certificate.certificate_file.close()
                        os.remove(certificate.certificate_file.path)
                    except Exception as e:
                        print("PDF faylini o'chirishda xato:", e)

                if certificate.qr_code_image:
                    try:
                        certificate.qr_code_image.close()
                        os.remove(certificate.qr_code_image.path)
                    except Exception as e:
                        print("QR kod faylini o'chirishda xato:", e)

                certificate.generate_qr_code()
                certificate.generate_pdf_file()

                certificate.save()

            messages.success(
                request,
                f"Sertifikat #{certificate.certificate_number} muvaffaqiyatli tasdiqlandi."
            )

        except Exception as e:
            print("XATO TUTILDI:", e)
            print(traceback.format_exc())
            messages.error(
                request,
                f"Sertifikatni tasdiqlashda xatolik yuz berdi: {e}"
            )

    return redirect('approver:dashboard')



@login_required
def reject_certificate(request, pk):
    certificate = get_object_or_404(Certificate, pk=pk)

    if request.method == "POST":
        if certificate.status == 'pending':
            certificate.status = 'rejected'
            certificate.rejected_by = request.user.userprofile  # ❗️bu yerda approved_by emas
            certificate.rejected_at = timezone.now()
            certificate.save()
            messages.success(request, f"Sertifikat #{certificate.certificate_number} rad etildi.")
        else:
            messages.error(request, "Faqat 'pending' holatdagi sertifikatni rad etish mumkin.")

        return redirect('approver:dashboard')

    # Agar GET bo'lsa → dashboardga qaytaramiz yoki 405 qaytaramiz
    return redirect('approver:dashboard')


@login_required
def approver_detail(request, pk):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Faqat approver roliga ruxsat
    if user_profile.role != 'approver':
        return redirect('login')

    certificate = get_object_or_404(Certificate, pk=pk)

    return render(request, 'labcerti/approver/detail.html', {'cert': certificate})