from django import forms
from django.core.exceptions import ValidationError
import re

from .models import Certificate, Organization, UserProfile
from django.contrib.auth.models import User


class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = [
            'standards_used',
            'comparison_document',
            'owner_inn',
            'owner_name',
            'manufacturer',
            'origin_country',
            'measurement_range',
            'error_limit',
            'device_name',
            'device_serial_numbers',
            'comparison_methodology_doc',
            'protocol_file',
        ]
        widgets = {
            'protocol_file': forms.ClearableFileInput(attrs={'accept': 'application/pdf'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        placeholders = {
            'standards_used': 'Etalonlar (namunaviy o‘lchash vositalari) nomi va belgilanishi',
            'comparison_document': 'Qiyoslash bo‘yicha hujjat nomi va belgilanishi',
            'owner_inn': '123456789',
            'owner_name': 'Tashkilot nomi',
            'manufacturer': 'Tayyorlovchi(ishlab chiqaruvchi) nomi',
            'origin_country': 'Davlat',
            'measurement_range': '0-100',
            'error_limit': '±0.01',
            'device_name': 'O‘lchash vositasining nomi',
            'device_serial_numbers': 'Zavod raqami',
            'comparison_methodology_doc': 'Normativ hujjat nomi',
        }

        # Barcha fieldlarga umumiy class va placeholder qo‘shamiz
        for field_name, field in self.fields.items():
            if field_name != 'protocol_file':
                field.widget.attrs.update({
                    'class': 'form-control',
                    'placeholder': placeholders.get(field_name, '')
                })
            else:
                field.widget.attrs.update({
                    'class': 'form-control',
                })

        # owner_inn uchun maxsus validatsiya atributlari
        self.fields['owner_inn'].widget.attrs.update({
            'type': 'number',
            'pattern': r'^\d{9}$',   # faqat 9 ta raqam
            'title': 'INN faqat 9 ta raqamdan iborat bo‘lishi kerak',
            'maxlength': '9',
            'inputmode': 'numeric'   # mobil klaviaturada raqam chiqadi
        })

    def clean_owner_inn(self):
        inn = self.cleaned_data.get('owner_inn')
        if not inn:
            raise ValidationError("INN kiritilishi shart.")

        # inn endi int, string emas → str() qilib tekshiramiz
        inn_str = str(inn)
        if len(inn_str) != 9 or not inn_str.isdigit():
            raise ValidationError("INN faqat 9 ta raqamdan iborat bo‘lishi kerak.")

        return inn


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        # Foydalanuvchi faqat o'z kontakt raqamini o'zgartira oladi
        fields = ['contact']
