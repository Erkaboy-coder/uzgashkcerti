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

from django.core.paginator import Paginator

# @login_required
# def index(request):
#     user_profile = get_object_or_404(UserProfile, user=request.user)

#     total_certificates_count = 0
#     draft_certificates_count = 0
#     pending_certificates_count = 0
#     approved_certificates_count = 0
#     rejected_certificates_count = 0
#     monthly_data = {'labels': [], 'data': []}

#     if user_profile.role == 'creator':
#         queryset = Certificate.objects.filter(created_by=user_profile)
#         draft_certificates_count = queryset.filter(status='draft').count()
#         pending_certificates_count = queryset.filter(status='pending').count()
#         approved_certificates_count = queryset.filter(status='approved').count()
#         rejected_certificates_count = queryset.filter(status='rejected').count()
#         total_certificates_count = queryset.count()
#         template = 'labcerti/creator/dashboard.html'

#     elif user_profile.role == 'approver':
#         draft_certificates_count = Certificate.objects.filter(status='draft').count()
#         pending_certificates_count = Certificate.objects.filter(status='pending', approved_by__isnull=True).count()
#         approved_certificates_count = Certificate.objects.filter(approved_by=user_profile, status='approved').count()
#         rejected_certificates_count = Certificate.objects.filter(approved_by=user_profile, status='rejected').count()
#         total_certificates_count = draft_certificates_count + pending_certificates_count + approved_certificates_count + rejected_certificates_count

#         queryset = Certificate.objects.filter(
#             Q(status='draft') | Q(status='pending', approved_by__isnull=True) | Q(approved_by=user_profile)
#         )
#         template = 'labcerti/approver/dashboard.html'

#     # Grafik uchun ma'lumot
#     monthly_data_queryset = queryset.annotate(
#         month=ExtractMonth('created_at'),
#         year=ExtractYear('created_at')
#     ).values('year', 'month').annotate(
#         count=Count('id')
#     ).order_by('year', 'month')

#     labels = []
#     data = []
#     for entry in monthly_data_queryset:
#         labels.append(f"{entry['year']}-{entry['month']:02d}")
#         data.append(entry['count'])

#     monthly_data = {
#         'labels': labels,
#         'data': data
#     }

#     # Paginator
#     paginator = Paginator(queryset, 10)  # har bir sahifada 10 ta sertifikat
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     context = {
#         'total_certificates_count': total_certificates_count,
#         'drafts_count': draft_certificates_count,
#         'pending_count': pending_certificates_count,
#         'approved_count': approved_certificates_count,
#         'rejected_count': rejected_certificates_count,
#         'monthly_data': mark_safe(json.dumps(monthly_data)),
#         'certificates': page_obj,  # paginator bilan sahifalangan ro'yxat
#     }

#     return render(request, template, context)





from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

def login_page(request):
    # Agar foydalanuvchi allaqachon tizimga kirgan bo'lsa
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            if profile.status != 'active':
                messages.error(request, "Sizning profilingiz nofaol. Administratorga murojaat qiling.")
                logout(request)
                return redirect('login')

            # Rolga qarab yo'naltirish
            if profile.role == 'creator':
                return redirect('creator:dashboard')
            elif profile.role == 'approver':
                return redirect('approver:dashboard')
            elif profile.role.strip() == 'administrator':
                return redirect('administrator:dashboard')
            else:
                return redirect('index')

        except UserProfile.DoesNotExist:
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
                    error = "Foydalanuvchi profilingiz faol emas. Administratorga murojaat qiling."
                else:
                    login(request, user)
                    if remember:
                        request.session.set_expiry(86400)  # 1 kun
                    else:
                        request.session.set_expiry(0)

                    # Rolga qarab yo'naltirish
                    if profile.role == 'creator':
                        return redirect('creator:dashboard')
                    elif profile.role == 'approver':
                        return redirect('approver:dashboard')
                    elif profile.role.strip() == 'administrator':
                        return redirect('administrator:workers_list')
                    else:
                        return redirect('index')

            except UserProfile.DoesNotExist:
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
            return redirect('labcerti:profile')
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
            return redirect('labcerti:profile')
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
    return render(request, 'labcerti/profile.html', context)


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

def custom_404_view(request, exception):
    return render(request, 'labcerti/404.html', status=404)

def test(request, pk):
    cert = get_object_or_404(Certificate, pk=pk)
    return render(request, 'labcerti/certificates/certificate_template.html', {"cert": cert})

def qr_link_detail(request, certificate_number):
    cert = get_object_or_404(Certificate, certificate_number=certificate_number)
    return render(request, 'labcerti/certificates/qr_detail.html', {"cert": cert})

def user_logout(request):
    logout(request)
    return redirect('login')