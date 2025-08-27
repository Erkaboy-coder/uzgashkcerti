from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from labcerti.models import Certificate, UserProfile
from django.db.models import Q
from labcerti.decorators import admin_required
from labcerti.forms import WorkerCreateForm


@admin_required
@login_required
def dashboard(request, status=None):
    user_profile = get_object_or_404(UserProfile.active_objects, user=request.user)
    if user_profile.role != 'administrator':
        return redirect('login')

    queryset = Certificate.objects.exclude(status='draft').order_by('-created_at')

    if status in ['pending', 'approved', 'rejected']:
        queryset = queryset.filter(status=status)

    # GET parametrlari
    certificate_number = request.GET.get('certificate_number')
    owner_inn = request.GET.get('owner_inn')
    device_name = request.GET.get('device_name')
    device_serial = request.GET.get('device_serial')
    status_get = request.GET.get('status')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    employee_id = request.GET.get('employee')

    # Filtering
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

    # 🔑 Agar xodim tanlangan bo‘lsa
    if employee_id:
        queryset = queryset.filter(
            Q(created_by__id=employee_id) | Q(approved_by__id=employee_id)
        )

    # Statistikalar
    pending_count = Certificate.objects.filter(status='pending').count()
    approved_count = Certificate.objects.filter(status='approved').count()
    rejected_count = Certificate.objects.filter(status='rejected').count()
    total_count = pending_count + approved_count + rejected_count

    # Paginator
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Admin uchun barcha xodimlar ro‘yxati (faqat is_deleted=False)
    employees = UserProfile.active_objects.filter(
        Q(role='creator') | Q(role='approver')
    ).select_related('user')

    context = {
        'certificates': page_obj,
        'page_obj': page_obj,
        'paginator': paginator,
        'current_status': status if status else (status_get if status_get else ''),
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'total_certificates_count': total_count,
        'employees': employees,
        'request': request,
    }
    return render(request, 'labcerti/administrator/dashboard.html', context)


@admin_required
@login_required
def workers_list(request):
    """Workerlar ro‘yxati (faqat administrator ko‘radi)"""
    profile = get_object_or_404(UserProfile.active_objects, user=request.user)
    if profile.role != 'administrator':
        messages.error(request, "Sizda bu sahifaga kirish huquqi yo‘q!")
        return redirect("administrator:dashboard")

    # GET parametrlardan olish
    status = request.GET.get("status")        # active / inactive / None
    show_deleted = request.GET.get("deleted") == "1"

    # Workerlarni olish
    base_qs = UserProfile.objects.filter(role__in=['creator', 'approver']).select_related("user")

    if show_deleted:
        workers = base_qs.filter(is_deleted=True)
    else:
        workers = base_qs.filter(is_deleted=False)

    # Status bo‘yicha filter
    if status in ["active", "inactive"]:
        workers = workers.filter(status=status)

    # Statistikalar
    total_count = base_qs.filter(is_deleted=False).count()
    active_count = base_qs.filter(is_deleted=False, status="active").count()
    inactive_count = base_qs.filter(is_deleted=False, status="inactive").count()
    deleted_count = base_qs.filter(is_deleted=True).count()

    context = {
        "workers": workers,
        "total_count": total_count,
        "active_count": active_count,
        "inactive_count": inactive_count,
        "deleted_count": deleted_count,
        "current_status": status or "all",  # frontda qaysi tugma tanlanganini ko‘rsatish uchun
        "show_deleted": show_deleted,
    }
    return render(request, "labcerti/administrator/workers.html", context)




@admin_required
@login_required
def worker_toggle_status(request, pk):
    """Xodimni faollik statusini almashtirish"""
    profile = get_object_or_404(UserProfile.active_objects, pk=pk)
    if profile.status == "active":
        profile.status = "inactive"
    else:
        profile.status = "active"
    profile.save()
    return redirect("administrator:workers_list")


@admin_required
@login_required
def worker_detail(request, pk):
    worker = get_object_or_404(UserProfile.active_objects, pk=pk)
    return render(request, "labcerti/administrator/worker_detail.html", {"worker": worker})


@admin_required
@login_required
def worker_delete(request, pk):
    worker = get_object_or_404(UserProfile.active_objects, pk=pk)
    worker.delete()   # bu yerda soft delete ishlaydi
    return redirect("administrator:workers_list")


@admin_required
@login_required
def worker_create(request):
    if request.method == "POST":
        form = WorkerCreateForm(request.POST)
        if form.is_valid():
            user, profile, password = form.save()
            messages.success(
                request,
                f"✅ Yangi xodim yaratildi! Login: {user.username}, Parol: {password}. "
                f"Foydalanuvchi tizimga kirib parolni almashtirishi kerak."
            )
            return JsonResponse({"success": True})
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    return JsonResponse({"success": False, "errors": "Noto‘g‘ri so‘rov"})
