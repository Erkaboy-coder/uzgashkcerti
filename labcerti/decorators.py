from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated and hasattr(request.user, "userprofile"):
            if request.user.userprofile.role == "administrator":
                return view_func(request, *args, **kwargs)
        messages.error(request, "Sizda ushbu amalni bajarish uchun ruxsat yo‘q!")
        return redirect("home")  # kerakli sahifaga yo‘naltirish
    return wrapper
