# Phase 9A-27: OTP-Based Delete Confirmation APIs

from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from apps.user_profile.models import GameProfile
from apps.user_profile.models.delete_otp import GamePassportDeleteOTP
from apps.user_profile.models.cooldown import GamePassportCooldown
from apps.common.api_responses import success_response, error_response


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@api_view(['POST'])
def request_delete_otp(request):
    """
    Request OTP code for passport deletion.
    Sends 6-digit code to user's email.
    
    POST /profile/api/game-passports/request-delete-otp/
    Body: {passport_id: int}
    """
    passport_id = request.data.get('passport_id')
    
    if not passport_id:
        return error_response('MISSING_PASSPORT_ID', 'passport_id is required', status=400)
    
    try:
        passport = GameProfile.objects.get(id=passport_id, user=request.user)
    except GameProfile.DoesNotExist:
        return error_response('PASSPORT_NOT_FOUND', 'Passport not found', status=404)
    
    # Check if passport is VERIFIED (cannot be deleted)
    if passport.verification_status == 'VERIFIED':
        return error_response(
            'VERIFIED_PASSPORT',
            'Verified passports cannot be deleted. Contact support if you need assistance.',
            status=403
        )
    
    # Check if within 30-day lock window
    if passport.is_identity_locked():
        lock_days = (passport.locked_until - timezone.now()).days
        return error_response(
            'IDENTITY_LOCKED',
            f'This passport is locked for {lock_days} more days. Identity fields cannot be changed until then.',
            status=403,
            metadata={'days_remaining': lock_days}
        )
    
    # Phase 9A-28: Check for team membership
    from apps.organizations.models import TeamMembership
    team_membership = TeamMembership.objects.filter(
        user=request.user,
        team__game_id=passport.game_id,
        status='ACTIVE'
    ).first()
    
    if team_membership:
        return error_response(
            'TEAM_MEMBERSHIP_BLOCK',
            f'You must leave your team "{team_membership.team.name}" before deleting this passport.',
            status=403,
            metadata={
                'team_name': team_membership.team.name,
                'team_id': team_membership.team.id
            }
        )
    
    # Phase 9A-28: Check for tournament participation
    from apps.tournaments.models import Registration
    active_registration = Registration.objects.filter(
        user=request.user,
        tournament__game__slug=passport.game.slug,
        status__in=['pending', 'confirmed', 'payment_submitted', 'submitted', 'auto_approved', 'needs_review'],
        tournament__tournament_end__gte=timezone.now()
    ).first()
    
    if active_registration:
        return error_response(
            'TOURNAMENT_LOCK_BLOCK',
            f'You are registered for "{active_registration.tournament.name}". Withdraw from the tournament before deleting this passport.',
            status=403,
            metadata={
                'tournament_name': active_registration.tournament.name,
                'tournament_id': active_registration.tournament.id
            }
        )
    
    # Check resend cooldown (60 seconds)
    recent_otp = GamePassportDeleteOTP.objects.filter(
        user=request.user,
        passport=passport,
        created_at__gte=timezone.now() - timezone.timedelta(seconds=60)
    ).first()
    
    if recent_otp:
        seconds_remaining = 60 - (timezone.now() - recent_otp.created_at).seconds
        return error_response(
            'RESEND_COOLDOWN',
            f'Please wait {seconds_remaining} seconds before requesting a new code',
            status=429,
            metadata={'seconds_remaining': seconds_remaining}
        )
    
    # Create OTP
    ip_address = get_client_ip(request)
    otp = GamePassportDeleteOTP.create_for_passport(request.user, passport, ip_address)
    
    # Send email
    subject = 'DeltaCrown - Confirm Passport Deletion'
    message = f"""
Hello {request.user.username},

You requested to delete your {passport.game} game passport.

Your confirmation code is: {otp.code}

This code will expire in 10 minutes.

If you did not request this, please ignore this email and secure your account.

- DeltaCrown Team
    """
    
    # Attempt email sending with proper error handling
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [request.user.email],
            fail_silently=False,
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send OTP email to {request.user.email}: {str(e)}")
        
        # Return structured error (HTTP 503 - Service Unavailable)
        return error_response(
            'EMAIL_NOT_CONFIGURED',
            'Email service is not configured. Contact support@deltacrown.gg for assistance.',
            status=503,
            metadata={
                'support_email': 'support@deltacrown.gg',
                'otp_code': otp.code if settings.DEBUG else None  # Dev fallback
            }
        )
    
    # Mask email for privacy (show first 2 chars + @domain)
    email_parts = request.user.email.split('@')
    masked_email = f"{email_parts[0][:2]}***@{email_parts[1]}" if len(email_parts) == 2 else "***"
    
    return success_response({
        'message': 'Confirmation code sent to your email',
        'email_masked': masked_email,
        'expires_in_minutes': 10,
        'otp_id': otp.id
    })


@api_view(['POST'])
def confirm_delete(request):
    """
    Confirm passport deletion with OTP code.
    
    POST /profile/api/game-passports/confirm-delete/
    Body: {passport_id: int, otp_code: str}
    """
    passport_id = request.data.get('passport_id')
    otp_code = request.data.get('otp_code')
    
    if not passport_id or not otp_code:
        return error_response(
            'MISSING_PARAMETERS',
            'passport_id and otp_code are required',
            status=400
        )
    
    try:
        passport = GameProfile.objects.get(id=passport_id, user=request.user)
    except GameProfile.DoesNotExist:
        return error_response('PASSPORT_NOT_FOUND', 'Passport not found', status=404)
    
    # Verify OTP
    valid, result = GamePassportDeleteOTP.verify_code(request.user, passport, otp_code)
    
    if not valid:
        return error_response('INVALID_OTP', result, status=400)
    
    otp = result
    
    # Re-check deletion policies
    if passport.verification_status == 'VERIFIED':
        return error_response(
            'VERIFIED_PASSPORT',
            'Verified passports cannot be deleted',
            status=403
        )
    
    if passport.is_identity_locked():
        return error_response(
            'IDENTITY_LOCKED',
            'Passport is locked',
            status=403
        )
    
    # Mark OTP as used
    otp.mark_used()
    
    # Create 90-day cooldown
    GamePassportCooldown.create_post_delete_cooldown(
        user=request.user,
        game=passport.game,
        days=90
    )
    
    # Delete passport
    game_name = passport.game.display_name
    passport.delete()
    
    return success_response({
        'message': f'{game_name} passport deleted successfully',
        'cooldown_days': 90,
        'cooldown_message': f'You can re-add {game_name} after 90 days. Contact support@deltacrown.gg if you need assistance.',
        'success': True
    })
