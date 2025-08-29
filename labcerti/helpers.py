import qrcode
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.files.base import ContentFile
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from django.conf import settings
import os
import platform

def link_callback(uri, rel):
    """xhtml2pdf uchun statik va media fayllar yo‘lini to‘g‘ri olish"""
    if uri.startswith(settings.STATIC_URL):
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
        return path
    elif uri.startswith('/data/labcerti/'):
        path = os.path.join(settings.DATA_LABCERTI_ROOT, uri.replace('/data/labcerti/', ""))
        return path
    return uri

def generate_qr_code(certificate):
    """QR kod yaratadi va BytesIO obyektini qaytaradi"""
    qr_url = f"{settings.BASE_URL}/qr_link_detail/{certificate.certificate_number}/"
    qr_img = qrcode.make(qr_url)
    buffer = BytesIO()
    qr_img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

def generate_pdf(certificate, template_name='labcerti/certificates/certificate_template.html'):
    """HTML shablondan PDF yaratadi va InMemoryUploadedFile qaytaradi"""
    font_path = os.path.join(settings.BASE_DIR, 'static/fonts/roboto/static/Roboto-Regular.ttf')

    context = {
        "cert": certificate,
        "qr_url": certificate.qr_code_image.url if certificate.qr_code_image else None,
        "bg_url": settings.STATIC_URL + 'assets/img/bg5.png',
        "font_url": font_path,
    }
    html_string = render_to_string(template_name, context)
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(src=html_string, dest=pdf_buffer, encoding='utf-8', link_callback=link_callback)
    if pisa_status.err:
        raise Exception("PDF yaratishda xatolik yuz berdi!")

    pdf_buffer.seek(0)
    filename = f"certificate_{certificate.certificate_number}.pdf"
    file_obj = InMemoryUploadedFile(
        pdf_buffer,
        field_name='certificate_file',
        name=filename,
        content_type='application/pdf',
        size=pdf_buffer.getbuffer().nbytes,
        charset=None
    )
    return file_obj
