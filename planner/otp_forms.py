from django import forms
from django.core.validators import RegexValidator

class OTPVerificationForm(forms.Form):
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        validators=[RegexValidator(r'^\d{6}$', 'Enter a valid 6-digit OTP code.')],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 6-digit OTP',
            'maxlength': '6',
            'pattern': '\d{6}',
            'title': 'Please enter 6 digits',
            'style': 'text-align: center; font-size: 18px; letter-spacing: 5px;'
        })
    )
    
    def clean_otp_code(self):
        otp_code = self.cleaned_data['otp_code']
        if not otp_code.isdigit() or len(otp_code) != 6:
            raise forms.ValidationError("OTP must be exactly 6 digits.")
        return otp_code