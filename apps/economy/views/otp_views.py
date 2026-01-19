# apps/economy/views/otp_views.py
"""
UP PHASE 7.7: OTP verification for PIN setup/change.

Security-first implementation with email verification before PIN changes.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.db import transaction as db_transaction
from django.db.utils import ProgrammingError, OperationalError
from datetime import timedelta
import logging
import time
import random
import string

from apps.economy.models import DeltaCrownWallet, WalletPINOTP
from apps.user_profile.models import UserProfile

logger = logging.getLogger(__name__)


def generate_otp_code():
    """Generate a random 6-digit OTP code"""
    return ''.join(random.choices(string.digits, k=6))


@login_required
@require_POST
def otp_request(request):
    """
    Request OTP for PIN setup/change.
    
    POST /api/wallet/pin/otp/request/
    
    Payload:
        - purpose: 'pin_setup' or 'pin_change'
        - current_pin: (required if purpose='pin_change')
    
    Returns:
        JSON with OTP ID and expiry time
    """
    start_time = time.time()
    
    try:
        # UP-PHASE7.8: Graceful handling of missing table
        try:
            # Test if WalletPINOTP table exists by attempting a simple query
            WalletPINOTP.objects.exists()
        except (ProgrammingError, OperationalError) as db_err:
            logger.error(
                f"[ECON][OTP] missing_table | Database table 'economy_walletpinotp' does not exist. "
                f"Run migrations: python manage.py migrate economy | Error: {db_err}"
            )
            return JsonResponse({
                'success': False,
                'error': 'OTP system is not initialized. Please contact support or run migrations.'
            }, status=503)
        
        # Get user's profile
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User profile not found'
            }, status=404)
        
        # Get or create wallet
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        
        # Validate purpose
        purpose = request.POST.get('purpose', '').strip()
        if purpose not in ['pin_setup', 'pin_change']:
            return JsonResponse({
                'success': False,
                'error': 'Invalid purpose. Must be "pin_setup" or "pin_change"'
            }, status=400)
        
        # If changing PIN, verify current PIN first
        if purpose == 'pin_change':
            if not wallet.pin_enabled:
                return JsonResponse({
                    'success': False,
                    'error': 'No PIN set. Use "pin_setup" instead.'
                }, status=400)
            
            current_pin = request.POST.get('current_pin', '').strip()
            if not current_pin:
                return JsonResponse({
                    'success': False,
                    'error': 'Current PIN required for PIN change'
                }, status=400)
            
            # Check if PIN is locked
            if wallet.pin_locked_until and timezone.now() < wallet.pin_locked_until:
                remaining = int((wallet.pin_locked_until - timezone.now()).total_seconds() / 60)
                return JsonResponse({
                    'success': False,
                    'error': f'PIN locked. Try again in {remaining} minutes.'
                }, status=403)
            
            # Verify current PIN
            if not check_password(current_pin, wallet.pin_hash):
                wallet.pin_failed_attempts += 1
                
                if wallet.pin_failed_attempts >= 5:
                    wallet.pin_locked_until = timezone.now() + timedelta(minutes=15)
                    wallet.save()
                    return JsonResponse({
                        'success': False,
                        'error': 'Too many failed attempts. PIN locked for 15 minutes.'
                    }, status=403)
                else:
                    wallet.save()
                    remaining_attempts = 5 - wallet.pin_failed_attempts
                    return JsonResponse({
                        'success': False,
                        'error': f'Incorrect current PIN. {remaining_attempts} attempts remaining.'
                    }, status=403)
            
            # Current PIN verified - reset failed attempts
            wallet.pin_failed_attempts = 0
            wallet.save()
        
        # Check for recent unused OTP (rate limiting: 1 OTP per minute)
        recent_otp = WalletPINOTP.objects.filter(
            wallet=wallet,
            created_at__gte=timezone.now() - timedelta(minutes=1),
            is_used=False
        ).first()
        
        if recent_otp:
            return JsonResponse({
                'success': False,
                'error': 'OTP already sent. Please wait 1 minute before requesting again.',
                'retry_after': 60
            }, status=429)
        
        # Generate OTP
        otp_code = generate_otp_code()
        otp_hash = make_password(otp_code)
        expires_at = timezone.now() + timedelta(minutes=10)
        
        # Create OTP record
        otp = WalletPINOTP.objects.create(
            wallet=wallet,
            code_hash=otp_hash,
            purpose=purpose,
            expires_at=expires_at
        )
        
        # Send OTP email
        user_email = request.user.email
        if not user_email:
            otp.delete()
            return JsonResponse({
                'success': False,
                'error': 'No email address on file. Please add an email to your account.'
            }, status=400)
        
        try:
            # Email subject and message
            subject = f'DeltaCrown Wallet PIN Verification - {otp_code}'
            message = f"""
Hello {request.user.username},

Your OTP for wallet PIN {'setup' if purpose == 'pin_setup' else 'change'} is:

{otp_code}

This code will expire in 10 minutes.

If you did not request this, please ignore this email and secure your account.

- DeltaCrown Esports Team
"""
            
            # Send email (in development, log OTP to console)
            if settings.DEBUG:
                logger.info(f"[ECON][OTP] OTP for {request.user.username}: {otp_code} (expires in 10 min)")
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user_email],
                fail_silently=False
            )
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[ECON][OTP] otp_request user={request.user.username} purpose={purpose} otp_id={otp.id} ms={elapsed_ms}")
            
            return JsonResponse({
                'success': True,
                'otp_id': otp.id,
                'expires_at': expires_at.isoformat(),
                'message': f'OTP sent to {user_email}. Please check your email.'
            })
            
        except Exception as email_error:
            # Email failed - delete OTP and return error
            otp.delete()
            logger.error(f"[ECON][OTP] Email send failed: {email_error}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': 'Failed to send OTP email. Please try again later.'
            }, status=500)
        
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[ECON][OTP] otp_request error user={request.user.username} error={str(e)} ms={elapsed_ms}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to process OTP request'
        }, status=500)


@login_required
@require_POST
def otp_verify_and_set_pin(request):
    """
    Verify OTP and set/change PIN atomically.
    
    POST /api/wallet/pin/otp/verify/
    
    Payload:
        - otp_code: 6-digit OTP
        - pin: 6-digit new PIN
        - confirm_pin: PIN confirmation
    
    Returns:
        JSON with success status
    """
    start_time = time.time()
    
    try:
        # Get user's profile
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'User profile not found'
            }, status=404)
        
        # Get wallet
        try:
            wallet = DeltaCrownWallet.objects.get(profile=profile)
        except DeltaCrownWallet.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Wallet not found'
            }, status=404)
        
        # Validate OTP code
        otp_code = request.POST.get('otp_code', '').strip()
        if not otp_code or len(otp_code) != 6 or not otp_code.isdigit():
            return JsonResponse({
                'success': False,
                'error': 'Invalid OTP code. Must be 6 digits.'
            }, status=400)
        
        # Validate PIN
        pin = request.POST.get('pin', '').strip()
        confirm_pin = request.POST.get('confirm_pin', '').strip()
        
        if not pin or not confirm_pin:
            return JsonResponse({
                'success': False,
                'error': 'PIN and confirmation are required'
            }, status=400)
        
        if len(pin) != 6 or not pin.isdigit():
            return JsonResponse({
                'success': False,
                'error': 'PIN must be exactly 6 digits'
            }, status=400)
        
        if pin != confirm_pin:
            return JsonResponse({
                'success': False,
                'error': 'PIN and confirmation do not match'
            }, status=400)
        
        # Get most recent valid OTP
        otp = WalletPINOTP.objects.filter(
            wallet=wallet,
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp:
            return JsonResponse({
                'success': False,
                'error': 'No pending OTP found. Please request a new OTP.'
            }, status=404)
        
        # Check if OTP is still valid
        if not otp.is_valid():
            if otp.is_used:
                error_msg = 'OTP already used. Please request a new OTP.'
            elif otp.expires_at <= timezone.now():
                error_msg = 'OTP expired. Please request a new OTP.'
            elif otp.attempt_count >= otp.max_attempts:
                error_msg = 'Too many failed attempts. Please request a new OTP.'
            else:
                error_msg = 'OTP is no longer valid. Please request a new OTP.'
            
            return JsonResponse({
                'success': False,
                'error': error_msg
            }, status=400)
        
        # Verify OTP code
        if not otp.verify_code(otp_code):
            remaining_attempts = otp.max_attempts - otp.attempt_count
            
            if remaining_attempts <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'Too many failed attempts. Please request a new OTP.'
                }, status=403)
            else:
                return JsonResponse({
                    'success': False,
                    'error': f'Incorrect OTP. {remaining_attempts} attempts remaining.'
                }, status=403)
        
        # OTP verified! Set PIN atomically
        with db_transaction.atomic():
            wallet.pin_hash = make_password(pin)
            wallet.pin_enabled = True
            wallet.pin_failed_attempts = 0
            wallet.pin_locked_until = None
            wallet.save()
            
            # Mark OTP as used
            otp.mark_used()
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[ECON][PIN] pin_set_via_otp user={request.user.username} purpose={otp.purpose} success=True ms={elapsed_ms}")
        
        return JsonResponse({
            'success': True,
            'message': 'PIN set successfully'
        })
        
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[ECON][PIN] otp_verify error user={request.user.username} error={str(e)} ms={elapsed_ms}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to verify OTP and set PIN'
        }, status=500)
