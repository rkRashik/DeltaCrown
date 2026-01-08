"""
Simplified Email Verification API
- Primary email: Already verified, just copy it (no OTP needed)
- Custom email: Send OTP and verify
"""
import random
import string
from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import json


def generate_otp(length=6):
    """Generate a random 6-digit OTP code"""
    return ''.join(random.choices(string.digits, k=length))


@login_required
@require_http_methods(["POST"])
def send_verification_otp(request):
    """
    Send OTP code to custom email for verification.
    If use_primary is True, just mark as verified (already verified during signup).
    Rate limited to 3 attempts per hour for custom emails.
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        use_primary = data.get('use_primary', False)
        
        if not email:
            return JsonResponse({'success': False, 'error': 'Email address is required'}, status=400)
        
        
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'success': False, 'error': 'Invalid email address'}, status=400)
        
        # If using primary email, no OTP needed - already verified during account creation
        if use_primary:
            if email != request.user.email.lower():
                return JsonResponse({'success': False, 'error': 'Email must match your account email'}, status=400)
            
            # Just update profile directly - no verification needed
            profile = request.user.profile
            profile.secondary_email = request.user.email
            profile.secondary_email_verified = True
            profile.save(update_fields=['secondary_email', 'secondary_email_verified'])
            
            return JsonResponse({
                'success': True,
                'message': 'Primary email set successfully',
                'already_verified': True,
                'email': email
            })
        
        # For custom email, send OTP
        # Check rate limiting (max 3 attempts per hour)
        attempt_key = f"email_otp_attempts_{request.user.id}"
        attempts = cache.get(attempt_key, 0)
        
        if attempts >= 3:
            return JsonResponse({
                'success': False,
                'error': 'Too many verification attempts. Please try again in 1 hour.'
            }, status=429)
        
        # Generate OTP
        otp = generate_otp()
        
        # Store OTP in cache (expires in 10 minutes)
        cache_key = f"email_otp_{request.user.id}_{email}"
        cache.set(cache_key, otp, timeout=600)  # 10 minutes
        
        # Increment attempt counter (expires in 1 hour)
        cache.set(attempt_key, attempts + 1, timeout=3600)
        
        # Send email
        subject = 'Verify Your Public Email - DeltaCrown'
        message = f"""Hi {request.user.username},

Your verification code is: {otp}

This code will expire in 10 minutes.

If you didn't request this verification, please ignore this email.

Best regards,
DeltaCrown Team
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email sending error: {e}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to send verification email. Please try again later.'
            }, status=500)
        
        return JsonResponse({
            'success': True,
            'message': f'Verification code sent to {email}',
            'expires_in': 600  # seconds
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Verification error: {e}")
        return JsonResponse({'success': False, 'error': 'An error occurred'}, status=500)


@login_required
@require_http_methods(["POST"])
def verify_otp_code(request):
    """
    Verify OTP code for custom email only.
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip().lower()
        otp = data.get('code', '').strip()
        
        if not email or not otp:
            return JsonResponse({'success': False, 'error': 'Email and code are required'}, status=400)
        
        # Validate email
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'success': False, 'error': 'Invalid email address'}, status=400)
        
        # Get OTP from cache
        cache_key = f"email_otp_{request.user.id}_{email}"
        stored_otp = cache.get(cache_key)
        
        if not stored_otp:
            return JsonResponse({
                'success': False,
                'error': 'Verification code expired or not found. Please request a new code.'
            }, status=400)
        
        # Verify OTP
        if otp != stored_otp:
            return JsonResponse({'success': False, 'error': 'Invalid verification code'}, status=400)
        
        # Update user profile
        profile = request.user.profile
        profile.secondary_email = email
        profile.secondary_email_verified = True
        profile.save(update_fields=['secondary_email', 'secondary_email_verified'])
        
        # Clear OTP from cache
        cache.delete(cache_key)
        
        # Clear attempt counter on success
        attempt_key = f"email_otp_attempts_{request.user.id}"
        cache.delete(attempt_key)
        
        return JsonResponse({
            'success': True,
            'message': 'Email verified successfully!',
            'email': email,
            'verified': True
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Verification error: {e}")
        return JsonResponse({'success': False, 'error': 'An error occurred'}, status=500)

        cache.delete(attempt_key)
        
        return JsonResponse({
            'success': True,
            'message': 'Email verified successfully!',
            'email': email,
            'verified': True
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        print(f"Verification error: {e}")
        return JsonResponse({'success': False, 'error': 'An error occurred'}, status=500)
