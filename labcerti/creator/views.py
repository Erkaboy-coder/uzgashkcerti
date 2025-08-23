from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from labcerti.models import Certificate, UserProfile
from django.core.paginator import Paginator
from django.db.models import Q
from labcerti.forms import CertificateForm
from django.contrib import messages
from django.http import Http404
import locale

@login_required
def dashboard(request, status_filter=None, **kwargs):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # GET query params
    search_query = request.GET.get('search', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    # Agar URL orqali status_filter kelgan bo'lsa - uni ishlatamiz
    # Aks holda GET paramdan olamiz
    if not status_filter:
        status_filter = request.GET.get('status', '')

    # Base queryset
    certificates = Certificate.objects.filter(created_by=user_profile)

    # Holat bo‘yicha filter
    if status_filter in ['pending', 'approved', 'rejected']:
        certificates = certificates.filter(status=status_filter)

    # Search
    if search_query:
        certificates = certificates.filter(
            Q(certificate_number__icontains=search_query) |
            Q(owner__name__icontains=search_query) |
            Q(device_name__icontains=search_query)
        )

    # Sana bo‘yicha filter
    if date_from:
        certificates = certificates.filter(created_at__date__gte=date_from)
    if date_to:
        certificates = certificates.filter(created_at__date__lte=date_to)

    certificates = certificates.order_by('-created_at')

    # Statistika
    total_certificates_count = Certificate.objects.filter(created_by=user_profile).count()
    sent_certificates_count = Certificate.objects.filter(created_by=user_profile, status='pending').count()
    approved_certificates_count = Certificate.objects.filter(created_by=user_profile, status='approved').count()
    rejected_certificates_count = Certificate.objects.filter(created_by=user_profile, status='rejected').count()

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
        'sent_certificates_count': sent_certificates_count,
        'approved_certificates_count': approved_certificates_count,
        'rejected_certificates_count': rejected_certificates_count,
    }
    return render(request, 'creator/dashboard.html', context)


@login_required
def certificate_detail(request, pk):
    # Foydalanuvchi profili
    user_profile = get_object_or_404(UserProfile, user=request.user)

    # Sertifikatni topish
    cert = get_object_or_404(Certificate, pk=pk)

    # Sertifikatlar sonini hisoblash
    # Faqat kirgan creator yaratgan sertifikatlarni hisoblaymiz
    all_certificates_of_creator = Certificate.objects.filter(created_by=user_profile)

    total_certificates_count = all_certificates_of_creator.count()
    pending_certificates_count = all_certificates_of_creator.filter(status='pending').count()
    approved_certificates_count = all_certificates_of_creator.filter(status='approved').count()
    rejected_certificates_count = all_certificates_of_creator.filter(status='rejected').count()

    context = {
        'cert': cert,
        'total_certificates_count': total_certificates_count,
        'sent_certificates_count': pending_certificates_count,
        'approved_certificates_count': approved_certificates_count,
        'rejected_certificates_count': rejected_certificates_count,
    }
    return render(request, 'creator/detail.html', context)

@login_required
def create_certificate(request):
    """Yangi sertifikat yaratish va 'pending' sifatida saqlash."""
    user_profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == 'POST':
        print('asdasd')
        form = CertificateForm(request.POST, request.FILES)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.created_by = user_profile
            cert.status = 'pending'
            cert.save()
            messages.success(request, 'Sertifikat muvaffaqiyatli yaratildi!')
            return redirect('creator:all')
    else:
        form = CertificateForm()

    return render(request, 'creator/create.html', {'form': form})



@login_required
def edit_certificate(request, pk):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    certificate = get_object_or_404(Certificate, pk=pk)

    # Faqat creator o'zining sertifikatini tahrirlashi mumkin
    if certificate.created_by.user != request.user:
        messages.error(request, "Sizda bu sertifikatni tahrirlash uchun huquq yo'q.")
        return redirect('creator:all')

    # Faqat pending yoki rejected holatdagi sertifikatlarni tahrirlash mumkin
    if certificate.status not in ['pending', 'rejected']:
        messages.error(request, "Tasdiqlangan sertifikatni tahrirlash mumkin emas.")
        return redirect('creator:all')

    if request.method == 'POST':
        form = CertificateForm(request.POST, instance=certificate)
        if form.is_valid():
            edited_cert = form.save(commit=False)

            if edited_cert.status == 'rejected':
                edited_cert.status = 'pending'
                edited_cert.approved_by = None
                edited_cert.approved_at = None

            edited_cert.save()
            messages.success(request, "Sertifikat muvaffaqiyatli yangilandi va qayta yuborildi.")
            return redirect('creator:all')
    else:
        form = CertificateForm(instance=certificate)

    # Creatorga tegishli sertifikatlar sonini hisoblash
    all_certificates_of_creator = Certificate.objects.filter(created_by=user_profile)

    total_certificates_count = all_certificates_of_creator.count()
    pending_certificates_count = all_certificates_of_creator.filter(status='pending').count()
    approved_certificates_count = all_certificates_of_creator.filter(status='approved').count()
    rejected_certificates_count = all_certificates_of_creator.filter(status='rejected').count()

    context = {
        'form': form,
        'certificate': certificate,
        'total_certificates_count': total_certificates_count,
        'sent_certificates_count': pending_certificates_count,
        'approved_certificates_count': approved_certificates_count,
        'rejected_certificates_count': rejected_certificates_count,
    }
    return render(request, 'creator/edit.html', context)


@login_required
def delete_certificate(request, pk):
    try:
        certificate = get_object_or_404(Certificate, pk=pk)
    except Http404:
        # Agar sertifikat topilmasa, 404 xatosi qaytarish
        return render(request, '404.html', status=404)

    # Sertifikatni faqat uning egasi o'chira olishini ta'minlash
    if certificate.created_by.user != request.user:
        # Agar egasi bo'lmasa, ruxsat etilmagan xabarni ko'rsatish
        return render(request, '403.html', status=403)

    if request.method == 'POST':
        certificate.delete()
        return redirect('creator:all')

    return render(request, 'creator/confirm_delete.html', {'cert': certificate})

