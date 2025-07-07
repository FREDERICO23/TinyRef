# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import secrets

class ReferralCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='referral_codes')
    name = models.CharField(max_length=100, help_text="Campaign or code name")
    code = models.CharField(max_length=20, unique=True, db_index=True)
    domain = models.URLField(help_text="Your landing page URL (e.g., https://yoursite.com/signup)")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Performance counters
    total_clicks = models.PositiveIntegerField(default=0)
    total_signups = models.PositiveIntegerField(default=0)
    total_conversions = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)
    
    def generate_unique_code(self):
        while True:
            code = secrets.token_urlsafe(8)
            if not ReferralCode.objects.filter(code=code).exists():
                return code
    
    @property
    def full_referral_url(self):
        """Generate the complete referral URL"""
        domain = self.domain.rstrip('/')
        separator = '&' if '?' in domain else '?'
        return f"{domain}{separator}ref={self.code}"
    
    @property
    def conversion_rate(self):
        if self.total_signups == 0:
            return 0
        return round((self.total_conversions / self.total_signups) * 100, 2)
    
    def __str__(self):
        return f"{self.name} ({self.code})"

class ReferralClick(models.Model):
    referral_code = models.ForeignKey(ReferralCode, on_delete=models.CASCADE, related_name='clicks')
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    referer = models.URLField(null=True, blank=True)
    clicked_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Increment click counter
        self.referral_code.total_clicks += 1
        self.referral_code.save(update_fields=['total_clicks'])

class Referral(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('signed_up', 'Signed Up'),
        ('converted', 'Converted'),
        ('churned', 'Churned'),
    ]
    
    referral_code = models.ForeignKey(ReferralCode, on_delete=models.CASCADE, related_name='referrals')
    email = models.EmailField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            if self.status == 'signed_up':
                self.referral_code.total_signups += 1
                self.referral_code.save(update_fields=['total_signups'])
            elif self.status == 'converted':
                self.referral_code.total_conversions += 1
                self.referral_code.total_revenue += self.revenue
                self.referral_code.save(update_fields=['total_conversions', 'total_revenue'])

# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import ReferralCode, ReferralClick, Referral
from .forms import ReferralCodeForm

@login_required
def dashboard(request):
    """Main dashboard with overview stats"""
    user_codes = ReferralCode.objects.filter(user=request.user, is_active=True)
    
    # Calculate totals
    total_codes = user_codes.count()
    total_clicks = sum(code.total_clicks for code in user_codes)
    total_signups = sum(code.total_signups for code in user_codes)
    total_conversions = sum(code.total_conversions for code in user_codes)
    total_revenue = sum(code.total_revenue for code in user_codes)
    
    # Recent activity
    recent_codes = user_codes[:5]
    
    context = {
        'total_codes': total_codes,
        'total_clicks': total_clicks,
        'total_signups': total_signups,
        'total_conversions': total_conversions,
        'total_revenue': total_revenue,
        'conversion_rate': round((total_conversions / total_signups * 100) if total_signups > 0 else 0, 2),
        'recent_codes': recent_codes,
    }
    
    return render(request, 'referrals/dashboard.html', context)

@login_required
def create_code(request):
    """Create a new referral code"""
    if request.method == 'POST':
        form = ReferralCodeForm(request.POST)
        if form.is_valid():
            code = form.save(commit=False)
            code.user = request.user
            code.save()
            messages.success(request, f'Referral code "{code.name}" created successfully!')
            return render(request, 'referrals/create_code.html', {
                'form': ReferralCodeForm(),  # Fresh form
                'created_code': code
            })
    else:
        form = ReferralCodeForm()
    
    return render(request, 'referrals/create_code.html', {'form': form})

@login_required
def generated_codes(request):
    """List all generated codes"""
    codes = ReferralCode.objects.filter(user=request.user, is_active=True)
    
    # Pagination
    paginator = Paginator(codes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'codes': page_obj,
    }
    
    return render(request, 'referrals/generated_codes.html', context)

@login_required
def code_analytics(request, code_id):
    """View analytics for a specific code"""
    code = get_object_or_404(ReferralCode, id=code_id, user=request.user)
    
    # Get recent clicks and referrals
    recent_clicks = code.clicks.order_by('-clicked_at')[:50]
    recent_referrals = code.referrals.order_by('-created_at')[:50]
    
    context = {
        'code': code,
        'recent_clicks': recent_clicks,
        'recent_referrals': recent_referrals,
    }
    
    return render(request, 'referrals/analytics.html', context)

@login_required
def delete_code(request, code_id):
    """Delete/deactivate a referral code"""
    code = get_object_or_404(ReferralCode, id=code_id, user=request.user)
    
    if request.method == 'POST':
        code.is_active = False
        code.save()
        messages.success(request, f'Referral code "{code.name}" has been deactivated.')
        return redirect('generated_codes')
    
    return render(request, 'referrals/confirm_delete.html', {'code': code})

# Track clicks (this can be called from external sites)
def track_click(request):
    """Track referral clicks from external sites"""
    ref_code = request.GET.get('ref')
    redirect_url = request.GET.get('redirect', '/')
    
    if ref_code:
        try:
            code = ReferralCode.objects.get(code=ref_code, is_active=True)
            ReferralClick.objects.create(
                referral_code=code,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                referer=request.META.get('HTTP_REFERER')
            )
        except ReferralCode.DoesNotExist:
            pass
    
    return redirect(redirect_url)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# forms.py
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

# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('create/', views.create_code, name='create_code'),
    path('codes/', views.generated_codes, name='generated_codes'),
    path('analytics/<int:code_id>/', views.code_analytics, name='code_analytics'),
    path('delete/<int:code_id>/', views.delete_code, name='delete_code'),
    path('track/', views.track_click, name='track_click'),
]

# admin.py
from django.contrib import admin
from .models import ReferralCode, ReferralClick, Referral

@admin.register(ReferralCode)
class ReferralCodeAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'user', 'domain', 'total_clicks', 'total_signups', 'total_conversions', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'code', 'user__username']
    readonly_fields = ['total_clicks', 'total_signups', 'total_conversions', 'total_revenue']

@admin.register(ReferralClick)
class ReferralClickAdmin(admin.ModelAdmin):
    list_display = ['referral_code', 'ip_address', 'clicked_at']
    list_filter = ['clicked_at']
    search_fields = ['referral_code__code', 'ip_address']

@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = ['email', 'referral_code', 'status', 'revenue', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['email', 'referral_code__code']