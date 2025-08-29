from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import F
from io import BytesIO
import qrcode
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.template.loader import render_to_string
import qrcode
from django.core.files.base import ContentFile
from io import BytesIO
from django.conf import settings
import os
from django.core.validators import FileExtensionValidator
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.templatetags.static import static
from weasyprint import HTML, CSS
from xhtml2pdf import pisa
from django.http import HttpRequest

from django.contrib.staticfiles import finders


def validate_file_size(value):
    # Fayl hajmi 5MB dan oshmasligini tekshiradi
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError('Fayl hajmi 5 MB dan oshmasligi kerak.')


class ActiveUserProfileManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


def link_callback(uri, rel):
    """HTML-dagi URL'larni fayl tizimi yo'liga o'tkazadi."""
    # Statik fayllar uchun
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        return path

    # QR kod uchun (sizning maxsus papkangiz)
    elif uri.startswith('/data/labcerti/'):
        path = os.path.join(settings.DATA_LABCERTI_ROOT, uri.replace('/data/labcerti/', ""))
        return path

    return uri


class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('creator', 'Creator'),
        ('approver', 'Approver'),
        ('administrator', 'Administrator'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_center_user = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='creator')
    contact = models.CharField(
        max_length=50, blank=True, null=True,
        validators=[RegexValidator(r'^\+?\d{9,15}$', "Telefon raqami to'g'ri formatda emas.")]
    )

    STATUS_CHOICES = [
        ('active', 'Faol'),
        ('inactive', 'Faol emas'),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='active', verbose_name="Faollik holati"
    )

    # 🔹 soft delete
    is_deleted = models.BooleanField(default=False)

    # managers
    objects = models.Manager()  # default
    active_objects = ActiveUserProfileManager()  # faqat is_deleted=False

    def delete(self, *args, **kwargs):
        """Soft delete – bazadan o‘chirib yubormaydi"""
        self.is_deleted = True
        self.save()

    def __str__(self):
        return f"{self.user.username} - {self.role}"


class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    inn = models.CharField(max_length=15, unique=True)
    registrar = models.CharField(max_length=255, verbose_name="Ro'yxatdan o'tkazuvchi organ", blank=True, null=True)
    registration_date = models.DateField(verbose_name="Davlat ro'yxatidan o'tkazilgan sana", blank=True, null=True)
    registration_number = models.CharField(max_length=255, verbose_name="Davlat ro'yxatidan o'tkazilgan raqami",
                                           blank=True, null=True)
    legal_form = models.CharField(max_length=255, verbose_name="Tashkiliy-huquqiy shakli", blank=True, null=True)
    ifut_code = models.CharField(max_length=255, verbose_name="IFUT kodi", blank=True, null=True)
    dbibt_code = models.CharField(max_length=255, verbose_name="DBIBT kodi", blank=True, null=True)
    small_business = models.BooleanField(verbose_name="Kichik tadbirkorlik sub'ektlariga mansubligi", default=False)
    status = models.CharField(max_length=255, verbose_name="Faollik holati", blank=True, null=True)
    charter_fund = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="lank=TrueUstav fondi", blank=True,
                                       null=True)
    email = models.EmailField(max_length=255, blank=True, null=True, verbose_name="Elektron pochta manzili")
    phone = models.CharField(max_length=255, blank=True, null=True, verbose_name="Aloqa telefoni")
    mho_code = models.CharField(max_length=255, verbose_name="MHOBT kodi", blank=True, null=True)
    address = models.TextField(verbose_name="Ko'cha, uy, xonadon", blank=True, null=True)
    director_name = models.CharField(max_length=255, verbose_name="Rahbarning F.I.SH.", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Certificate(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    document_type = models.CharField(max_length=255, default='GUVOHNOMASI', verbose_name="Hujjat turi")
    certificate_number = models.PositiveIntegerField(unique=True, verbose_name="Guvohnoma raqami")
    comparison_date = models.DateField(verbose_name="Qiyoslash sanasi", blank=True, null=True)
    valid_until_date = models.DateField(verbose_name="Amal qilish muddati", blank=True, null=True)
    standards_used = models.TextField(verbose_name="Etalonlar va vositalar")
    comparison_document = models.CharField(blank=True, null=True,
                                           verbose_name="qiyoslash bo'yicha xujjatning belgilanishi va nomlanishi")
    service_provider_name = models.CharField(max_length=255,
                                             verbose_name="O'lchash vositalarini qiyoslagan metrologiya xizmatining nomi",
                                             default="Geodezik metrologiya xizmat markazi")
    metrologist = models.ForeignKey("UserProfile", on_delete=models.SET_NULL, null=True,
                                    related_name="metrologist_certificates", verbose_name="Qiyoslovchi")

    owner = models.ForeignKey("Organization", on_delete=models.CASCADE, verbose_name="Egasi", blank=True, null=True)
    owner_inn = models.PositiveIntegerField(unique=True,
                                            verbose_name="O'lchash vositalarining egasi - yuridik shaxs INNsi")
    owner_name = models.CharField(max_length=255, verbose_name="O'lchash vositalarining egasi - yuridik shaxs nomi")

    manufacturer = models.CharField(max_length=255,
                                    verbose_name="O'lchash vositalarini tayyorlovchi (ishlab chiqaruvchi)")
    origin_country = models.CharField(max_length=255,
                                      verbose_name="O'lchash vositalarining tayyorlovchi (ishlab chiqaruvchi) - import qiluvchi mamlakat")
    measurement_range = models.CharField(max_length=255,
                                         verbose_name="o'lchash vositalari parametrlarining nomi, o'lchashlar")
    error_limit = models.CharField(max_length=255, verbose_name="Xatolik chegaralari, aniqlik klassi")
    device_name = models.CharField(max_length=255, verbose_name="O'lchash vositasining nomi")
    device_serial_numbers = models.CharField(max_length=255, verbose_name="Zavod raqami")
    comparison_methodology_doc = models.CharField(max_length=255,
                                                  verbose_name="O'lchash vositalariga qo'yiladigan talablarni reglamentlovchi normativ xujjat belgilanishi va nomi")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Holati")
    protocol_file = models.FileField(
        upload_to='data/labcerti/protocols/',
        verbose_name="Protokol fayli",
        validators=[
            validate_file_size,  # agar sizda fayl hajmi cheklov validator bor bo'lsa
            FileExtensionValidator(allowed_extensions=['pdf'])  # faqat PDF
        ],
        blank=True,
        null=True
    )

    certificate_file = models.FileField(upload_to='data/labcerti/certificates/', verbose_name="Sertifikat fayli",
                                        blank=True, null=True)
    qr_code_image = models.ImageField(upload_to='data/labcerti/qr_codes/', verbose_name="QR kod", blank=True, null=True)

    created_by = models.ForeignKey("UserProfile", on_delete=models.SET_NULL, null=True,
                                   related_name="created_certificates", verbose_name="Yaratdi")
    approved_by = models.ForeignKey("UserProfile", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="approved_certificates", verbose_name="Tasdiqladi")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")
    approved_at = models.DateTimeField(blank=True, null=True, verbose_name="Tasdiqlangan sana")

    def save(self, *args, **kwargs):
        # Raqam berish
        if not self.certificate_number:
            with transaction.atomic():
                last_certificate = (
                    Certificate.objects
                    .select_for_update(skip_locked=True)
                    .order_by('-certificate_number')
                    .first()
                )
                if last_certificate:
                    self.certificate_number = last_certificate.certificate_number + 1
                else:
                    self.certificate_number = 100001

        # Agar comparison_date bo‘lmasa → hozirgi sana
        if not self.comparison_date:
            self.comparison_date = timezone.now().date()

        # valid_until_date = comparison_date + 1 yil
        self.valid_until_date = self.comparison_date + timedelta(days=365)

        # metrologist = created_by foydalanuvchi
        if self.created_by and not self.metrologist:
            self.metrologist = self.created_by

        super().save(*args, **kwargs)


class Reject(models.Model):
    certificate = models.ForeignKey(
        'Certificate',  # Sizning Certificate modeli nomi
        on_delete=models.CASCADE,
        related_name='rejections'
    )
    rejected_by = models.ForeignKey("UserProfile", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="rejected_certificates", verbose_name="Rad etdi")
    reason = models.TextField("Rad etish sababi")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rad etilgan sertifikat"
        verbose_name_plural = "Rad etilgan sertifikatlar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.certificate} - {self.rejected_by} tomonidan rad etildi"


class Document(models.Model):
    title = models.CharField("Sarlavha", max_length=255)
    file = models.FileField("Fayl", upload_to='data/labcerti/documents/', )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_documents'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hujjat"
        verbose_name_plural = "Hujjatlar"
        ordering = ['-created_at']

    def __str__(self):
        return self.title