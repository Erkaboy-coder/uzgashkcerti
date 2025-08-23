from django import forms
from .models import Certificate, Organization ,UserProfile
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm

class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = [
            'document_type',
            'comparison_date',
            # 'valid_until_date' maydoni bu yerdan olib tashlandi.
            'service_provider_name',
            'owner',
            'device_name',
            'device_serial_numbers',
            'manufacturer',
            'origin_country',
            'measurement_range',
            'error_limit',
            'comparison_methodology_doc',
            'standards_used',
            'metrologist_name',
            'protocol_file',
        ]
        widgets = {
            'comparison_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})

        self.fields['owner'].queryset = Organization.objects.all().order_by('name')
        
        self.fields['document_type'].widget.attrs['readonly'] = 'readonly'


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        # Foydalanuvchi faqat o'z kontakt raqamini o'zgartira oladi
        fields = ['contact']