# apps/economy/views/pin_views.py
"""
Wallet PIN management endpoints (UP PHASE 7.2).

Owner-only PIN setup, verification, and security features.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta
import logging
import time

from apps.economy.models import DeltaCrownWallet
from apps.user_profile.models import UserProfile

logger = logging.getLogger(__name__)


@login_required
@require_POST
def pin_setup(request):
    """
    Setup or change wallet PIN.
    
    POST /economy/api/wallet/pin/setup/
    
    Payload:
        - pin (required): 6-digit PIN
        - confirm_pin (required): PIN confirmation
        - current_pin (optional): Required if changing existing PIN
    
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
        
        # Get or create wallet
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        
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
        
        # If PIN already exists, verify current PIN first
        if wallet.pin_enabled:
            current_pin = request.POST.get('current_pin', '').strip()
            if not current_pin:
                return JsonResponse({
                    'success': False,
                    'error': 'Current PIN required to change PIN'
                }, status=400)
            
            if not check_password(current_pin, wallet.pin_hash):
                return JsonResponse({
                    'success': False,
                    'error': 'Current PIN is incorrect'
                }, status=403)
        
        # Set new PIN
        wallet.pin_hash = make_password(pin)
        wallet.pin_enabled = True
        wallet.pin_failed_attempts = 0
        wallet.pin_locked_until = None
        wallet.save()
        
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.info(f"[ECON] pin_setup user={request.user.username} success=True ms={elapsed_ms}")
        
        return JsonResponse({
            'success': True,
            'message': 'PIN setup successfully'
        })
        
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[ECON] pin_setup user={request.user.username} error={str(e)} ms={elapsed_ms}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to setup PIN'
        }, status=500)


@login_required
@require_POST
def pin_verify(request):
    """
    Verify wallet PIN.
    
    POST /economy/api/wallet/pin/verify/
    
    Payload:
        - pin (required): 6-digit PIN
    
    Returns:
        JSON with verification result
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
                'error': 'Wallet not found. Please set up your PIN first.'
            }, status=404)
        
        # Check if PIN is enabled
        if not wallet.pin_enabled:
            return JsonResponse({
                'success': False,
                'error': 'PIN not set up. Please set up your PIN first.'
            }, status=400)
        
        # Check if PIN is locked
        if wallet.pin_locked_until:
            if timezone.now() < wallet.pin_locked_until:
                remaining = int((wallet.pin_locked_until - timezone.now()).total_seconds() / 60)
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.warning(f"[ECON] pin_verify user={request.user.username} ok=False locked=True remaining_min={remaining} ms={elapsed_ms}")
                return JsonResponse({
                    'success': False,
                    'error': f'PIN locked. Try again in {remaining} minutes.'
                }, status=403)
            else:
                # Lockout expired, reset
                wallet.pin_locked_until = None
                wallet.pin_failed_attempts = 0
                wallet.save()
        
        # Validate PIN
        pin = request.POST.get('pin', '').strip()
        
        if not pin:
            return JsonResponse({
                'success': False,
                'error': 'PIN is required'
            }, status=400)
        
        # Verify PIN
        if check_password(pin, wallet.pin_hash):
            # Success - reset failed attempts
            wallet.pin_failed_attempts = 0
            wallet.save()
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            logger.info(f"[ECON] pin_verify user={request.user.username} ok=True failed_attempts=0 ms={elapsed_ms}")
            
            return JsonResponse({
                'success': True,
                'message': 'PIN verified successfully'
            })
        else:
            # Failed - increment attempts
            wallet.pin_failed_attempts += 1
            
            # Lock after 5 failed attempts
            if wallet.pin_failed_attempts >= 5:
                wallet.pin_locked_until = timezone.now() + timedelta(minutes=15)
                wallet.save()
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.warning(f"[ECON] pin_verify user={request.user.username} ok=False failed_attempts={wallet.pin_failed_attempts} locked=True ms={elapsed_ms}")
                
                return JsonResponse({
                    'success': False,
                    'error': 'Too many failed attempts. PIN locked for 15 minutes.'
                }, status=403)
            else:
                wallet.save()
                remaining_attempts = 5 - wallet.pin_failed_attempts
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                logger.warning(f"[ECON] pin_verify user={request.user.username} ok=False failed_attempts={wallet.pin_failed_attempts} ms={elapsed_ms}")
                
                return JsonResponse({
                    'success': False,
                    'error': f'Incorrect PIN. {remaining_attempts} attempts remaining before lockout.'
                }, status=403)
        
    except Exception as e:
        elapsed_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[ECON] pin_verify user={request.user.username} error={str(e)} ms={elapsed_ms}", exc_info=True)
        return JsonResponse({
            'success': False,
            'error': 'Failed to verify PIN'
        }, status=500)
