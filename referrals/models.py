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
        """Generate the complete referral URL that goes through our tracking system"""
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        return f"{base_url}/track?ref={self.code}&redirect={self.domain}"
    
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