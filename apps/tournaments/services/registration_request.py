# apps/tournaments/services/registration_request.py
"""
Service for handling registration requests from non-captain team members.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.utils import timezone


def create_registration_request(requester, tournament, team, captain, message=""):
    """
    Create a registration request from a team member to their captain.
    
    Args:
        requester: UserProfile of the requesting member
        tournament: Tournament to register for
        team: Team to register
        captain: UserProfile of the team captain
        message: Optional message from requester to captain
    
    Returns:
        RegistrationRequest instance
    """
    from apps.tournaments.models import RegistrationRequest
    
    # Check if there's already a pending request
    existing = RegistrationRequest.objects.filter(
        tournament=tournament,
        team=team,
        requester=requester,
        status=RegistrationRequest.Status.PENDING
    ).first()
    
    if existing:
        return existing
    
    # Create new request
    request = RegistrationRequest.objects.create(
        requester=requester,
        tournament=tournament,
        team=team,
        captain=captain,
        message=message
    )
    
    # Send notification email to captain
    send_captain_notification_email(request)
    
    return request


def send_captain_notification_email(registration_request):
    """
    Send email to captain notifying them of a registration request.
    """
    try:
        captain = registration_request.captain
        requester = registration_request.requester
        tournament = registration_request.tournament
        team = registration_request.team
        
        captain_user = getattr(captain, 'user', None)
        if not captain_user or not getattr(captain_user, 'email', None):
            print(f"⚠️  Captain {captain} has no email")
            return False
        
        captain_email = captain_user.email
        captain_name = getattr(captain, 'display_name', None) or getattr(captain_user, 'username', 'Captain')
        
        requester_user = getattr(requester, 'user', None)
        requester_name = getattr(requester, 'display_name', None) or (
            getattr(requester_user, 'username', 'Team member') if requester_user else 'Team member'
        )
        
        subject = f"[DeltaCrown] Registration Request for {tournament.name}"
        
        # Build approval URL (you can create a dedicated view for this)
        try:
            approve_url = f"http://127.0.0.1:8000/dashboard/registration-requests/{registration_request.id}/approve/"
        except Exception:
            approve_url = "http://127.0.0.1:8000/dashboard/"
        
        message = f"""
Hello {captain_name},

{requester_name} from your team "{team.name}" has requested that you register the team for the tournament:

🎮 Tournament: {tournament.name}
🏆 Game: {tournament.get_game_display() if hasattr(tournament, 'get_game_display') else tournament.game}
📅 Registration Closes: {tournament.reg_close_at.strftime('%B %d, %Y at %I:%M %p') if tournament.reg_close_at else 'TBD'}

{f'Message from {requester_name}:' if registration_request.message else ''}
{registration_request.message if registration_request.message else ''}

As team captain, you can:
✅ Register the team for this tournament
❌ Decline the request

Visit your dashboard to manage this request:
{approve_url}

Or register directly:
http://127.0.0.1:8000{tournament.register_url if hasattr(tournament, 'register_url') else f'/tournaments/register/{tournament.slug}/'}

Best regards,
DeltaCrown Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[captain_email],
            fail_silently=False
        )
        
        print(f"✅ Registration request notification sent to {captain_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send captain notification: {str(e)}")
        return False


def send_requester_response_email(registration_request):
    """
    Send email to requester notifying them of captain's response.
    """
    try:
        requester = registration_request.requester
        captain = registration_request.captain
        tournament = registration_request.tournament
        
        requester_user = getattr(requester, 'user', None)
        if not requester_user or not getattr(requester_user, 'email', None):
            return False
        
        requester_email = requester_user.email
        requester_name = getattr(requester, 'display_name', None) or getattr(requester_user, 'username', 'Player')
        
        captain_name = getattr(captain, 'display_name', None) or 'Your captain'
        
        if registration_request.status == registration_request.Status.APPROVED:
            subject = f"[DeltaCrown] Registration Request Approved - {tournament.name}"
            status_text = "✅ APPROVED"
            action_text = f"{captain_name} has registered the team for this tournament!"
        else:
            subject = f"[DeltaCrown] Registration Request Declined - {tournament.name}"
            status_text = "❌ DECLINED"
            action_text = f"{captain_name} has declined the registration request."
        
        message = f"""
Hello {requester_name},

Your registration request for {tournament.name} has been {status_text}.

🎮 Tournament: {tournament.name}
🏆 Status: {status_text}

{action_text}

{f'Response from {captain_name}:' if registration_request.response_message else ''}
{registration_request.response_message if registration_request.response_message else ''}

View tournament details:
http://127.0.0.1:8000{tournament.get_absolute_url() if hasattr(tournament, 'get_absolute_url') else f'/tournaments/{tournament.slug}/'}

Best regards,
DeltaCrown Team
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[requester_email],
            fail_silently=False
        )
        
        print(f"✅ Response notification sent to {requester_email}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send response notification: {str(e)}")
        return False
