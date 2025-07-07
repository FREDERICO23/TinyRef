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