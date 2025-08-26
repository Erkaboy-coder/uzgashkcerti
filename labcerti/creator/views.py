from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from labcerti.models import Certificate, UserProfile, Reject
from django.core.paginator import Paginator
from django.db.models import Q
from labcerti.forms import CertificateForm
from django.contrib import messages
from django.http import Http404
import locale
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractYear
from django.utils.safestring import mark_safe
import json
from django.db import transaction
from datetime import timedelta

@login_required
def dashboard(request, status=None):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    if user_profile.role != 'creator':
        return redirect('login')

    # Asosiy queryset
    queryset = Certificate.objects.filter(created_by=user_profile).order_by('-created_at')

    # Status URL orqali filterlash
    if status in ['draft', 'pending', 'approved', 'rejected']:
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
    if status_get in ['draft', 'pending', 'approved', 'rejected']:
        queryset = queryset.filter(status=status_get)
    if from_date:
        queryset = queryset.filter(created_at__date__gte=from_date)
    if to_date:
        queryset = queryset.filter(created_at__date__lte=to_date)

    # Statistikalar
    draft_count = Certificate.objects.filter(created_by=user_profile, status='draft').count()
    pending_count = Certificate.objects.filter(created_by=user_profile, status='pending').count()
    approved_count = Certificate.objects.filter(created_by=user_profile, status='approved').count()
    rejected_count = Certificate.objects.filter(created_by=user_profile, status='rejected').count()
    total_count = Certificate.objects.filter(created_by=user_profile).count()

    # Paginator
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'certificates': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'current_status': status if status else (status_get if status_get else ''),
        'drafts_count': draft_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_certificates_count': total_count,
        'request': request,  # search form uchun
    }
    return render(request, 'labcerti/creator/dashboard.html', context)




@login_required
def certificate_detail(request, pk):
    """Sertifikat tafsilotlarini ko'rsatish"""
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Sertifikatni olish
    cert = get_object_or_404(Certificate, pk=pk)

    # Faqat egasi ko'rishi mumkin bo'lishi
    if cert.created_by.user != request.user:
        return render(request, '403.html', status=403)
    rejections = cert.rejections.all()
    context = {
        'cert': cert,
        'rejections':rejections
    }

    return render(request, 'labcerti/creator/detail.html', context)


@login_required
def create_certificate(request, pk=None):
    """
    Yangi sertifikat yaratish yoki mavjud (rad etilgan) sertifikatni
    qayta yuborish va saqlash uchun.
    """
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Mavjud sertifikatni yuklash
    if pk:
        certificate = get_object_or_404(Certificate, pk=pk, created_by__user=request.user)
    else:
        certificate = None

    if request.method == 'POST':
        form = CertificateForm(request.POST, request.FILES, instance=certificate)
        if form.is_valid():
            with transaction.atomic():
                cert = form.save(commit=False)
                cert.created_by = user_profile

                # "Yuborish" yoki "Qayta yuborish" tugmasi bosilganda
                if 'submit_pending' in request.POST:
                    cert.status = 'pending'

                    # Agar bu rad etilgan sertifikat bo'lsa, sanalarni yangilash va xabarni o'zgartirish
                    if certificate and certificate.status == 'rejected':
                        cert.comparison_date = timezone.now().date()
                        cert.valid_until_date = cert.comparison_date + timedelta(days=365)
                        message = 'Sertifikat muvaffaqiyatli qayta yuborildi!'
                    else:
                        message = 'Sertifikat muvaffaqiyatli yuborildi!'

                    cert.save()
                    messages.success(request, message)
                    return redirect('creator:dashboard')

                # "Saqlash" tugmasi bosilganda
                else:
                    cert.status = 'draft'
                    cert.save()
                    messages.success(request, 'Sertifikat muvaffaqiyatli saqlandi!')

                    # Draft saqlangandan keyin tahrirlash sahifasiga yo'naltirish
                    return redirect('creator:edit', pk=cert.pk)

        else:
            messages.error(request, 'Iltimos, xatoliklarni to‘g‘rilang!')
    else:
        form = CertificateForm(instance=certificate)

    context = {
        'form': form,
        'certificate': certificate,
    }

    return render(request, 'labcerti/creator/create.html', context)


@login_required
def create_certificate(request):
    """Yangi sertifikat yaratish va dastlab draft sifatida saqlash."""
    user_profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'POST':
        form = CertificateForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                cert = form.save(commit=False)
                cert.created_by = user_profile

                # Agar POST so‘rovidan yuborish bo‘lsa, status pending
                if 'submit_pending' in request.POST:
                    cert.status = 'pending'
                    cert.save()
                    messages.success(request, 'Sertifikat muvaffaqiyatli yuborildi!')
                    return redirect('creator:dashboard')
                else:
                    cert.status = 'draft'  # Dastlab saqlash
                    cert.save()
                    messages.success(request, 'Sertifikat muvaffaqiyatli saqlandi!')

                    # Draft saqlangandan keyin edit sahifasiga yo‘naltirish
                    return redirect('creator:edit', pk=cert.pk)

        else:
            messages.error(request, 'Iltimos, xatoliklarni to‘g‘rilang!')
    else:
        form = CertificateForm()

    return render(request, 'labcerti/creator/create.html', {'form': form})

@login_required
def resend_rejected_certificate(request, pk):
    """
    Rad etilgan sertifikatni qayta yuborish view'i.
    GET so‘rov orqali ishlaydi.
    """
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Faqat rad etilgan sertifikatni olish
    certificate = get_object_or_404(Certificate, pk=pk, created_by=user_profile, status='rejected')

    # Qayta yuborish jarayoni
    with transaction.atomic():
        certificate.status = 'pending'
        certificate.comparison_date = timezone.now().date()
        certificate.valid_until_date = certificate.comparison_date + timedelta(days=365)
        certificate.save()

    messages.success(request, 'Sertifikat muvaffaqiyatli qayta yuborildi!')
    return redirect('creator:dashboard')




@login_required
def edit_certificate(request, pk):
    """Mavjud sertifikatni tahrirlash, draft yoki pending sifatida saqlash."""
    certificate = get_object_or_404(Certificate, pk=pk)
    user_profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'POST':
        form = CertificateForm(request.POST, request.FILES, instance=certificate)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.created_by = user_profile  # Agar kerak bo'lsa, yaratganini saqlash
            if 'save_draft' in request.POST:
                cert.status = 'draft'
                messages.success(request, 'Sertifikat muvafaqqiyatli saqlandi!')
            elif 'submit_pending' in request.POST:
                cert.status = 'pending'
                messages.success(request, 'Sertifikat yuborildi!')
            cert.save()
            return redirect('creator:dashboard')
    else:
        form = CertificateForm(instance=certificate)

    return render(request, 'labcerti/creator/edit.html', {'form': form, 'certificate': certificate})



@login_required
def delete_certificate(request, pk):
    # Sertifikatni olish yoki 404 qaytarish
    certificate = get_object_or_404(Certificate, pk=pk)

    # Faqat egasi o'chira olishi
    if certificate.created_by.user != request.user:
        messages.error(request, "Sizda bu sertifikatni o'chirish huquqi yo'q!")
        return redirect('creator:dashboard')

    # O'chirish
    certificate.delete()
    messages.success(request, f"Sertifikat {certificate.certificate_number} muvaffaqiyatli o'chirildi!")
    return redirect('creator:dashboard')
