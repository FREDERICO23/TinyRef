from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import ReferralCode, ReferralClick, Referral
from .forms import ReferralCodeForm
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json


def signup(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome {user.username}! Your account has been created.')
            return redirect('dashboard')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})

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
    
    # Calculate average revenue per conversion
    avg_revenue_per_conversion = 0
    if code.total_conversions > 0:
        avg_revenue_per_conversion = round(float(code.total_revenue) / code.total_conversions, 2)
    
    context = {
        'code': code,
        'recent_clicks': recent_clicks,
        'recent_referrals': recent_referrals,
        'avg_revenue_per_conversion': avg_revenue_per_conversion,
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

# Track clicks
def track_click(request):
    """Track referral clicks and redirect to destination"""
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
    
    # Add the ref parameter to the destination URL
    if ref_code and redirect_url != '/':
        separator = '&' if '?' in redirect_url else '?'
        redirect_url = f"{redirect_url}{separator}ref={ref_code}"
    
    return redirect(redirect_url)

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@csrf_exempt
@require_POST
def track_signup_api(request):
    """API endpoint for tracking signups from external sites"""
    try:
        data = json.loads(request.body)
        ref_code = data.get('ref')
        email = data.get('email')
        
        if ref_code and email:
            code = ReferralCode.objects.get(code=ref_code, is_active=True)
            Referral.objects.create(
                referral_code=code,
                email=email,
                status='signed_up'
            )
            return JsonResponse({'status': 'success'})
    except Exception as e:
        pass
    
    return JsonResponse({'status': 'error'})