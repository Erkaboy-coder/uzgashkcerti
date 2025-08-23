from django.contrib import admin
from .models import UserProfile, Organization, Certificate


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "role", "status")   # contact kerakmas, faqat asosiylari
    list_filter = ("role", "status")
    search_fields = ("user__username",)
    


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "inn", "status", "director_name")  # asosiylari
    list_filter = ("status", "small_business")
    search_fields = ("name", "inn", "director_name")


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = (
        "id", "certificate_number", "owner",
        "comparison_date", "valid_until_date", "status"
    )
    list_filter = ("status", "comparison_date", "valid_until_date")
    search_fields = ("certificate_number", "owner__name", "device_name")
    ordering = ("-created_at",)
    list_display_links = ("id","certificate_number")
