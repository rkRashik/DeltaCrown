"""
Enhanced Tournament Registration Service
Handles registration workflow with proper email notifications
"""

from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from datetime import timedelta

def send_registration_confirmation_email(registration):
    """Send registration confirmation email with payment instructions"""
    try:
        # Get user email
        user_email = None
        user_name = "Player"
        
        if hasattr(registration, 'user') and registration.user:
            profile = registration.user
            if hasattr(profile, 'user') and profile.user:
                user_email = profile.user.email
                user_name = profile.display_name or profile.user.username
        elif hasattr(registration, 'team') and registration.team:
            team = registration.team
            if hasattr(team, 'captain') and team.captain:
                captain_profile = team.captain
                if hasattr(captain_profile, 'user') and captain_profile.user:
                    user_email = captain_profile.user.email
                    user_name = captain_profile.display_name or captain_profile.user.username
        
        if not user_email:
            print(f"⚠️  No email found for registration {registration.id}")
            return False
        
        tournament = registration.tournament
        
        # Create email content
        subject = f"[DeltaCrown] Registration Confirmation - {tournament.name}"
        
        # Plain text message
        message = f"""
Hello {user_name},

Thank you for registering for {tournament.name}!

Tournament Details:
- Game: {tournament.get_game_display()}
- Start Date: {tournament.start_at.strftime('%B %d, %Y at %I:%M %p') if tournament.start_at else 'TBD'}
- Entry Fee: ৳{tournament.entry_fee_bdt or 0}
- Prize Pool: ৳{tournament.prize_pool_bdt or 0}

Your registration is currently PENDING payment verification.

Payment Instructions:
1. Send ৳{tournament.entry_fee_bdt or 0} using bKash/Nagad/Rocket
2. Use reference: DC-{tournament.id}-{registration.id}
3. Submit your transaction ID through the tournament portal

We'll confirm your registration once payment is verified.

Good luck and see you in the tournament!

Best regards,
DeltaCrown Team

Visit: http://127.0.0.1:8000{tournament.get_absolute_url()}
        """
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False
        )
        
        print(f"✅ Registration confirmation email sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send registration email: {str(e)}")
        return False

def send_payment_confirmation_email(registration):
    """Send payment confirmation email when payment is verified"""
    try:
        # Get user email (same logic as registration confirmation)
        user_email = None
        user_name = "Player"
        
        if hasattr(registration, 'user') and registration.user:
            profile = registration.user
            if hasattr(profile, 'user') and profile.user:
                user_email = profile.user.email
                user_name = profile.display_name or profile.user.username
        elif hasattr(registration, 'team') and registration.team:
            team = registration.team
            if hasattr(team, 'captain') and team.captain:
                captain_profile = team.captain
                if hasattr(captain_profile, 'user') and captain_profile.user:
                    user_email = captain_profile.user.email
                    user_name = captain_profile.display_name or captain_profile.user.username
        
        if not user_email:
            return False
        
        tournament = registration.tournament
        
        subject = f"[DeltaCrown] Payment Confirmed - {tournament.name}"
        
        message = f"""
Hello {user_name},

Congratulations! Your payment has been verified and your tournament registration is now CONFIRMED.

Tournament: {tournament.name}
Game: {tournament.get_game_display()}
Start: {tournament.start_at.strftime('%B %d, %Y at %I:%M %p') if tournament.start_at else 'TBD'}

What's Next:
✅ You're officially registered!
🕒 Check-in opens 30 minutes before tournament start
📊 Tournament brackets will be published 24 hours before start
🎮 Prepare your game setup and ensure stable internet

Important: Make sure to check-in on tournament day to secure your spot!

Best of luck in the tournament!

DeltaCrown Team

Tournament Details: http://127.0.0.1:8000{tournament.get_absolute_url()}
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False
        )
        
        print(f"✅ Payment confirmation email sent to {user_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send payment confirmation email: {str(e)}")
        return False

@transaction.atomic
def create_registration_with_email(tournament, user_profile=None, team=None, payment_method=None, payment_reference=None):
    """
    Create registration and send confirmation email
    """
    from apps.tournaments.models import Registration
    
    try:
        # Create registration
        reg_data = {
            'tournament': tournament,
            'status': 'PENDING'
        }
        
        if user_profile:
            reg_data['user'] = user_profile
        elif team:
            reg_data['team'] = team
        else:
            raise ValueError("Either user_profile or team must be provided")
        
        registration = Registration.objects.create(**reg_data)
        
        # Create payment verification if payment details provided
        if payment_method or payment_reference:
            from apps.tournaments.models import PaymentVerification
            PaymentVerification.objects.create(
                registration=registration,
                method=payment_method,
                transaction_id=payment_reference,
                status='PENDING'
            )
        
        # Send confirmation email
        send_registration_confirmation_email(registration)
        
        return registration
        
    except Exception as e:
        print(f"❌ Registration creation failed: {str(e)}")
        raise

def confirm_payment_and_notify(registration):
    """
    Confirm payment and send notification email
    """
    try:
        # Update registration status
        registration.status = 'CONFIRMED'
        registration.save()
        
        # Update payment verification if exists
        if hasattr(registration, 'payment_verification') and registration.payment_verification:
            pv = registration.payment_verification
            pv.status = 'VERIFIED'
            pv.verified_at = timezone.now()
            pv.save()
        
        # Send confirmation email
        send_payment_confirmation_email(registration)
        
        print(f"✅ Payment confirmed for registration {registration.id}")
        return True
        
    except Exception as e:
        print(f"❌ Payment confirmation failed: {str(e)}")
        return False