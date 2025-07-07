from django import forms
from .models import ReferralCode

class ReferralCodeForm(forms.ModelForm):
    class Meta:
        model = ReferralCode
        fields = ['name', 'code', 'domain']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Instagram Campaign'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Leave empty for auto-generation'
            }),
            'domain': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://yoursite.com/signup'
            })
        }
        help_texts = {
            'name': 'Give your referral campaign a descriptive name',
            'code': 'Custom code or leave empty for auto-generation',
            'domain': 'The URL where you want to send referred users'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['code'].required = False