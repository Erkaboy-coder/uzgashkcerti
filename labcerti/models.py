from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import F
from io import BytesIO
import qrcode
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.template.loader import render_to_string
from weasyprint import HTML
import qrcode
from django.core.files.base import ContentFile
from io import BytesIO
from django.conf import settings
import os
from django.core.validators import FileExtensionValidator
from datetime import timedelta
from django.utils import timezone

def validate_file_size(value):
    # Fayl hajmi 5MB dan oshmasligini tekshiradi
    limit = 5 * 1024 * 1024
    if value.size > limit:
        raise ValidationError('Fayl hajmi 5 MB dan oshmasligi kerak.')
    
class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('creator', 'Creator'),
        ('approver', 'Approver'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_center_user = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='creator')
    contact = models.CharField(max_length=50, blank=True, null=True,
    validators=[
        RegexValidator(r'^\+?\d{9,15}$', "Telefon raqami to'g'ri formatda emas.")
    ])
    STATUS_CHOICES = [
        ('active', 'Faol'),
        ('inactive', 'Faol emas'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Faollik holati")


    def __str__(self):
        return f"{self.user.username} - {self.role}"

class Organization(models.Model):
    name = models.CharField(max_length=255, unique=True)
    inn = models.CharField(max_length=15, unique=True)
    registrar = models.CharField(max_length=255, verbose_name="Ro'yxatdan o'tkazuvchi organ", blank=True, null=True)
    registration_date = models.DateField(verbose_name="Davlat ro'yxatidan o'tkazilgan sana",  blank=True, null=True)
    registration_number = models.CharField(max_length=255, verbose_name="Davlat ro'yxatidan o'tkazilgan raqami", blank=True, null=True)
    legal_form = models.CharField(max_length=255, verbose_name="Tashkiliy-huquqiy shakli", blank=True, null=True)
    ifut_code = models.CharField(max_length=255, verbose_name="IFUT kodi", blank=True, null=True)
    dbibt_code = models.CharField(max_length=255, verbose_name="DBIBT kodi", blank=True, null=True)
    small_business = models.BooleanField(verbose_name="Kichik tadbirkorlik sub'ektlariga mansubligi", default=False)
    status = models.CharField(max_length=255, verbose_name="Faollik holati", blank=True, null=True)
    charter_fund = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="lank=TrueUstav fondi", blank=True, null=True)
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
    certificate_number = models.CharField(max_length=255, unique=True, verbose_name="Guvohnoma raqami")
    comparison_date = models.DateField(verbose_name="Qiyoslash sanasi", blank=True, null=True)
    valid_until_date = models.DateField(verbose_name="Amal qilish muddati", blank=True, null=True)
    standards_used = models.TextField(verbose_name="Etalonlar va vositalar")
    comparison_document = models.CharField(blank=True, null=True, verbose_name="qiyoslash bo'yicha xujjatning belgilanishi va nomlanishi")
    service_provider_name = models.CharField(max_length=255, verbose_name="O'lchash vositalarini qiyoslagan metrologiya xizmatining nomi")
    metrologist_name = models.CharField(max_length=255, verbose_name="Qiyoslovchi")
    owner = models.ForeignKey("Organization", on_delete=models.CASCADE, verbose_name="Egasi", blank=True, null=True)
    owner_inn = models.CharField(max_length=255, verbose_name="O'lchash vositalarining egasi - yuridik shaxs INNsi")
    owner_name = models.CharField(max_length=255, verbose_name="O'lchash vositalarining egasi - yuridik shaxs nomi")

    manufacturer = models.CharField(max_length=255, verbose_name="O'lchash vositalarini tayyorlovchi")
    origin_country = models.CharField(max_length=255, verbose_name="O'lchash vositalarining tayyorlovchi - import qiluvchi mamlakat")
    measurement_range = models.CharField(max_length=255, verbose_name="o'lchash vositalari parametrlarining nomi, o'lchashlar")
    error_limit = models.CharField(max_length=255, verbose_name="Xatolik chegaralari, aniqlik klassi")
    device_name = models.CharField(max_length=255, verbose_name="O'lchash vositasining nomi")
    device_serial_numbers = models.CharField(max_length=255, verbose_name="Zavod raqami")
    comparison_methodology_doc = models.CharField(max_length=255, verbose_name="O'lchash vositalariga qo'yiladigan talablarni reglamentlovchi normativ xujjat belgilanishi va nomi")

    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending', verbose_name="Holati")
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

    certificate_file = models.FileField(upload_to='data/labcerti/certificates/', verbose_name="Sertifikat fayli", blank=True, null=True)
    qr_code_image = models.ImageField(upload_to='data/labcerti/qr_codes/', verbose_name="QR kod", blank=True, null=True)

    created_by = models.ForeignKey("UserProfile",on_delete=models.SET_NULL,null=True,related_name="created_certificates",verbose_name="Yaratdi")
    approved_by = models.ForeignKey("UserProfile",on_delete=models.SET_NULL,null=True,blank=True,related_name="approved_certificates",verbose_name="Tasdiqladi")
    rejected_by = models.ForeignKey("UserProfile",on_delete=models.SET_NULL,null=True,blank=True,related_name="rejected_certificates",verbose_name="Rad etdi")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")
    approved_at = models.DateTimeField(blank=True, null=True, verbose_name="Tasdiqlangan sana")
    rejected_at = models.DateTimeField(blank=True, null=True, verbose_name="Rad etilgan sana")

    def save(self, *args, **kwargs):
        # Sertifikat raqamini avtomatik generatsiya qilish
        if not self.certificate_number:
            try:
                last_certificate = Certificate.objects.all().order_by(F('id').desc()).first()
                if last_certificate and last_certificate.certificate_number and last_certificate.certificate_number.isdigit():
                    last_number = int(last_certificate.certificate_number)
                    new_number = last_number + 1
                else:
                    new_number = 100000
            except (ValueError, TypeError):
                new_number = 100000
            self.certificate_number = str(new_number)

        # Amal qilish muddatini hisoblash
        if self.comparison_date and not self.valid_until_date:
            self.valid_until_date = self.comparison_date + timedelta(days=365)

        super().save(*args, **kwargs)

    def generate_qr_code(self):
        # Agar PDF fayl mavjud bo'lsa, QR o'sha faylga link beradi
        if self.certificate_file:
            pdf_url = settings.BASE_URL + self.certificate_file.url  # to'liq URL
        else:
            # Agar PDF hali yo'q bo'lsa, verify sahifaga yo'naltiradi
            pdf_url = f"{settings.BASE_URL}/data/labcerti/certificates/{self.id}/verify/"

        qr = qrcode.make(pdf_url)
        buffer = BytesIO()
        qr.save(buffer, format="PNG")
        filename = f"qr_{self.certificate_number}.png"
        self.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)

    def generate_pdf_file(self):
        # Agar eski PDF mavjud bo'lsa, uni o'chirish
        if self.certificate_file and os.path.exists(self.certificate_file.path):
            os.remove(self.certificate_file.path)

        context = {
            'cert': self,
            'logo_url': f"{settings.BASE_URL}{settings.STATIC_URL}assets/logo/image.png",
        }
        html_string = render_to_string('labcerti/certificates/certificate_template.html', context)
        pdf = HTML(string=html_string, base_url=settings.BASE_URL).write_pdf()

        buffer = BytesIO(pdf)
        buffer.seek(0)
        filename = f"certificate_{self.certificate_number}.pdf"

        file_obj = InMemoryUploadedFile(
            file=buffer,
            field_name='certificate_file',
            name=filename,
            content_type='application/pdf',
            size=len(pdf),
            charset=None
        )

        self.certificate_file.save(filename, file_obj, save=False)

    def __str__(self):
        return f"{self.certificate_number} ({self.get_status_display()})"