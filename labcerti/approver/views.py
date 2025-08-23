from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from labcerti.models import Certificate, UserProfile
from django.contrib import messages
from django.db.models import Q
from django.contrib import messages
from django.utils import timezone
from django.template.loader import render_to_string
from weasyprint import HTML
from django.conf import settings
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import traceback
from django.db import transaction
import os
from django.core.paginator import Paginator


@login_required
def approver_list(request, status_filter=None, **kwargs):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    search_query = request.GET.get('search', '')

    # Avval GET parametrlardan olamiz, agar bo'lmasa URL kwargs-dan olamiz
    status_filter = request.GET.get('status') or status_filter

    # Base queryset
    all_certificates = Certificate.objects.all()

    # Sidebar hisoblash
    new_certificates_count = all_certificates.filter(status='pending').count()
    approved_certificates_count = all_certificates.filter(status='approved', approved_by=user_profile).count()
    rejected_certificates_count = all_certificates.filter(status='rejected', approved_by=user_profile).count()
    total_certificates_count = new_certificates_count + approved_certificates_count + rejected_certificates_count

    # Filter qilish
    certificates = all_certificates
    if status_filter == 'new':
        certificates = certificates.filter(status='pending')
    elif status_filter == 'approved':
        certificates = certificates.filter(status='approved', approved_by=user_profile)
    elif status_filter == 'rejected':
        certificates = certificates.filter(status='rejected', approved_by=user_profile)

    if search_query:
        certificates = certificates.filter(certificate_number__icontains=search_query)

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        certificates = certificates.filter(created_at__date__gte=date_from)
    if date_to:
        certificates = certificates.filter(created_at__date__lte=date_to)

    certificates = certificates.order_by('-created_at')

    # Paginator
    paginator = Paginator(certificates, 10)
    page_number = request.GET.get('page')
    certificates_page = paginator.get_page(page_number)

    context = {
        'certificates': certificates_page,
        'status_filter': status_filter,
        'search_query': search_query,
        'date_from': date_from,
        'date_to': date_to,
        'total_certificates_count': total_certificates_count,
        'sent_certificates_count': new_certificates_count,
        'approved_certificates_count': approved_certificates_count,
        'rejected_certificates_count': rejected_certificates_count,
    }
    return render(request, 'approver/dashboard.html', context)





@login_required
def approve_certificate(request, pk):
    if request.method == "POST":
        certificate = get_object_or_404(Certificate, pk=pk)
        user_profile = get_object_or_404(UserProfile, user=request.user)

        try:
            with transaction.atomic():
                # Statusni yangilash
                if certificate.status == 'pending':
                    certificate.status = 'approved'
                certificate.approved_by = user_profile
                certificate.approved_at = timezone.now()

                # Eski fayllarni o‘chirish
                # Fayl streamini yopish va faylni o'chirishga urinish
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

                # Yangi QR va PDF yaratish
                certificate.generate_qr_code()
                certificate.generate_pdf_file()

                # Modelni saqlash
                certificate.save()

            messages.success(
                request,
                f"Sertifikat #{certificate.certificate_number} muvaffaqiyatli yangilandi."
            )

        except Exception as e:
            print("XATO TUTILDI:", e)
            print(traceback.format_exc())
            messages.error(
                request,
                f"Sertifikatni tasdiqlashda xatolik yuz berdi: {e}"
            )

        return redirect('approver:all')





@login_required
def reject_certificate(request, pk):
    if request.method == "POST":
        certificate = get_object_or_404(Certificate, pk=pk)

        # Sertifikatni faqat pending (yangi) holatda bo'lsa va 
        # foydalanuvchi huquqi bo'lsa rad etishni tekshiramiz.
        # Qoidaga ko'ra, "approved_by" maydoni bo'sh bo'lishi kerak.
        # UserProfile modelini tekshirish shart emas, chunki har bir approver rad etishi mumkin.
        
        if certificate.status == 'pending':
            certificate.status = 'rejected'
            certificate.approved_by = request.user.userprofile
            certificate.save()
            messages.success(request, f"Sertifikat #{certificate.certificate_number} rad etildi.")
        else:
            messages.error(request, f"Ushbu sertifikatni rad etish mumkin emas, chunki uning holati 'Yangi' emas.")
        
        return redirect('approver:all')


@login_required
def approver_detail(request, pk):
    # Foydalanuvchi profilini olish
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Sertifikatni topish
    certificate = get_object_or_404(Certificate, pk=pk)

    # Approver tomonidan tasdiqlangan va rad etilgan sertifikatlarni hisoblash
    # Barcha tasdiqlash uchun yuborilgan sertifikatlar
    all_pending_certificates = Certificate.objects.filter(status='pending')
    
    # Joriy approver tomonidan tasdiqlanganlar
    approved_by_me = Certificate.objects.filter(approved_by=user_profile, status='approved')
    
    # Joriy approver tomonidan rad etilganlar
    rejected_by_me = Certificate.objects.filter(approved_by=user_profile, status='rejected')

    total_certificates_for_approver = all_pending_certificates.count() + approved_by_me.count() + rejected_by_me.count()

    context = {
        'certificate': certificate,
        'total_certificates_count': total_certificates_for_approver,
        'sent_certificates_count': all_pending_certificates.count(),
        'approved_certificates_count': approved_by_me.count(),
        'rejected_certificates_count': rejected_by_me.count(),
    }
    return render(request, 'approver/detail.html', context)