from django import forms
from .models import Certificate, Organization ,UserProfile
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm

from django import forms
from .models import Certificate

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
            'manufacturer': 'Tayyorlovchi nomi',
            'origin_country': 'Davlat',
            'measurement_range': '0-100',
            'error_limit': '±0.01',
            'device_name': 'O‘lchash vositasining nomi',
            'device_serial_numbers': 'Zavod raqami',
            'comparison_methodology_doc': 'Normativ hujjat nomi',
        }

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

        


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        # Foydalanuvchi faqat o'z kontakt raqamini o'zgartira oladi
        fields = ['contact']