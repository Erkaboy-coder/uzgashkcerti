from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import Certificate, UserProfile
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import PasswordChangeForm

from django.db.models import Count
from django.db.models.functions import ExtractMonth, ExtractYear
import json
from django.utils.safestring import mark_safe
from django.db.models import Q
from .forms import UserForm, UserProfileForm

# views.py
@login_required
def index(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)

    total_certificates_count = 0
    pending_certificates_count = 0
    approved_certificates_count = 0 # Yangi o'zgaruvchi
    rejected_certificates_count = 0
    monthly_data = {'labels': [], 'data': []}
    
    if user_profile.role == 'creator':
        queryset = Certificate.objects.filter(created_by=user_profile)
        pending_certificates_count = queryset.filter(status='pending').count()
        approved_certificates_count = queryset.filter(status='approved').count() # Qo'shilgan qator
        rejected_certificates_count = queryset.filter(status='rejected').count()
        total_certificates_count = queryset.count()
    
    elif user_profile.role == 'approver':
        # Yangi (pending) sertifikatlarni approved_by maydoni bo'sh bo'lganlar sifatida hisoblaymiz.
        pending_certificates_count = Certificate.objects.filter(status='pending', approved_by__isnull=True).count()
        
        # O'zi tasdiqlagan yoki rad etgan sertifikatlar
        approved_certificates_count = Certificate.objects.filter(approved_by=user_profile, status='approved').count()
        rejected_certificates_count = Certificate.objects.filter(approved_by=user_profile, status='rejected').count()

        # Umumiy sertifikatlar soni barchasining yig'indisi
        total_certificates_count = pending_certificates_count + approved_certificates_count + rejected_certificates_count

        # Grafik uchun ma'lumotlar. Barcha `pending` va o'zi tasdiqlagan/rad etgan sertifikatlarni olamiz.
        queryset = Certificate.objects.filter(
            Q(status='pending', approved_by__isnull=True) | Q(approved_by=user_profile)
        )

    # Oylar kesimida statistikani olish
    monthly_data_queryset = queryset.annotate(
        month=ExtractMonth('created_at'),
        year=ExtractYear('created_at')
    ).values('year', 'month').annotate(
        count=Count('id')
    ).order_by('year', 'month')

    labels = []
    data = []
    for entry in monthly_data_queryset:
        labels.append(f"{entry['year']}-{entry['month']:02d}")
        data.append(entry['count'])

    monthly_data = {
        'labels': labels,
        'data': data
    }
    
    context = {
        'total_certificates_count': total_certificates_count,
        'sent_certificates_count': pending_certificates_count,
        'approved_certificates_count': approved_certificates_count, # Tasdiqlanganlar soni qo'shildi
        'rejected_certificates_count': rejected_certificates_count,
        'monthly_data': mark_safe(json.dumps(monthly_data))
    }

    return render(request, 'labcerti/index.html', context)



def login_page(request):
    # Agar foydalanuvchi allaqachon tizimga kirgan bo'lsa
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.status == 'active':
                # Foydalanuvchi profili faol bo'lsa, 'index' sahifasiga yo'naltiramiz
                return redirect('index')
            else:
                # Agar profili faol bo'lmasa, tizimdan chiqaramiz
                messages.error(request, "Sizning profilingiz nofaol. Administratorga murojaat qiling.")
                logout(request)
                return redirect('login') # Yoki boshqa sahifaga
        except UserProfile.DoesNotExist:
            # Agar foydalanuvchi uchun UserProfile mavjud bo'lmasa
            messages.error(request, "Sizning profilingiz topilmadi. Administratorga murojaat qiling.")
            logout(request)
            return redirect('login')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember = request.POST.get('remember')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                profile = UserProfile.objects.get(user=user)
                if profile.status != 'active':
                    # Profil nofaol bo'lsa
                    error = "Foydalanuvchi profilingiz faol emas. Administratorga murojaat qiling."
                else:
                    # Tizimga kirish
                    login(request, user)
                    if remember:
                        request.session.set_expiry(86400)  # 1 kun
                    else:
                        request.session.set_expiry(0)
                    return redirect('index')
            except UserProfile.DoesNotExist:
                # Agar kirishga urinayotgan foydalanuvchi uchun UserProfile modeli bo'lmasa
                error = "Sizning profilingiz topilmadi. Administratorga murojaat qiling."
        else:
            error = "Login yoki parol noto‘g‘ri."

    return render(request, 'labcerti/auth/login.html', {'error': error})


@login_required
def user_profile(request):
    user = request.user
    user_profile_instance = get_object_or_404(UserProfile, user=user)

    # Ma'lumotlarni yangilash formasi
    if request.method == 'POST' and 'profile_form_submit' in request.POST:
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=user_profile_instance)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Sizning maʼlumotlaringiz muvaffaqiyatli yangilandi.')
            return redirect('your_app_name:profile')
        else:
            messages.error(request,
                           'Maʼlumotlarni saqlashda xato yuz berdi. Iltimos, maʼlumotlarni toʻgʻri kiritganingizni tekshiring.')

    # Parolni o'zgartirish formasi
    elif request.method == 'POST' and 'password_form_submit' in request.POST:
        password_form = PasswordChangeForm(user=user, data=request.POST)
        if password_form.is_valid():
            password_form.save()
            update_session_auth_hash(request, password_form.user)
            messages.success(request, 'Sizning parolingiz muvaffaqiyatli o‘zgartirildi.')
            return redirect('your_app_name:profile')
        else:
            messages.error(request,
                           'Parolni oʻzgartirishda xato yuz berdi. Iltimos, eski parolni va yangi parolni toʻgʻri kiritganingizni tekshiring.')

    # GET so'rovi uchun formalar
    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=user_profile_instance)
        password_form = PasswordChangeForm(user=user)

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'password_form': password_form,
        'user_profile_instance': user_profile_instance,  # Model instance'ini ham context'ga qo'shamiz
    }
    return render(request, 'profile.html', context)


def public_certificate_search(request):
    search_query = request.GET.get('q', '')
    certificates = [] # Natijalarni saqlash uchun bo'sh ro'yxat

    if search_query:
        # Faqat tasdiqlangan sertifikatlarni qidiramiz
        certificates = Certificate.objects.filter(
            Q(certificate_number__icontains=search_query) & Q(status='approved')
        ).order_by('-created_at')

    context = {
        'certificates': certificates,
        'search_query': search_query,
    }
    return render(request, 'labcerti/search.html', context)


def certificate_detail(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    return render(request, 'search/certificate_detail.html', {"certificate": cert})

def custcustom_404_viewom_404(request, exception):
    return render(request, 'labcerti/404.html', status=404)


def user_logout(request):
    logout(request)
    return redirect('login')