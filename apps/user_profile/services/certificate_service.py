"""
Certificate Generation Service
Auto-generates tournament certificates for winners and top placements.

Features:
- Auto-generate certificates on tournament completion
- Upload to S3/media storage
- Email delivery to winners
- PDF generation with custom templates
- Verification code generation

Usage:
    from apps.user_profile.services.certificate_service import generate_tournament_certificate
    certificate = generate_tournament_certificate(user, tournament, placement=1)
"""

import logging
import secrets
from datetime import datetime
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from apps.user_profile.models import Certificate

logger = logging.getLogger(__name__)


def generate_verification_code():
    """Generate a unique verification code for certificates"""
    return secrets.token_urlsafe(16)


def create_certificate_image(user, tournament, placement, prize_amount=None):
    """
    Create a certificate image using PIL.
    
    Args:
        user: User instance
        tournament: Tournament instance
        placement: Integer placement (1, 2, 3, etc.)
        prize_amount: Optional prize amount
        
    Returns:
        BytesIO object containing the certificate image
    """
    # Certificate dimensions
    width, height = 1920, 1080
    
    # Create image with gradient background
    img = Image.new('RGB', (width, height), color='#0b1220')
    draw = ImageDraw.Draw(img)
    
    # Add gradient effect (simplified - production would use actual gradient)
    for y in range(height):
        alpha = int(255 * (1 - y / height))
        color = (11 + alpha // 10, 18 + alpha // 10, 32 + alpha // 10)
        draw.line([(0, y), (width, y)], fill=color)
    
    # Try to load custom fonts, fallback to default
    try:
        title_font = ImageFont.truetype("arial.ttf", 80)
        name_font = ImageFont.truetype("arial.ttf", 100)
        details_font = ImageFont.truetype("arial.ttf", 40)
        small_font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        # Fallback to default font
        title_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        details_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Certificate content
    placement_text = {
        1: "FIRST PLACE",
        2: "SECOND PLACE",
        3: "THIRD PLACE",
    }.get(placement, f"{placement}TH PLACE")
    
    # Draw certificate elements
    y_offset = 150
    
    # Title
    title = "CERTIFICATE OF ACHIEVEMENT"
    bbox = draw.textbbox((0, 0), title, font=title_font)
    title_width = bbox[2] - bbox[0]
    draw.text(((width - title_width) / 2, y_offset), title, fill='#FFD700', font=title_font)
    y_offset += 120
    
    # Placement
    bbox = draw.textbbox((0, 0), placement_text, font=details_font)
    placement_width = bbox[2] - bbox[0]
    draw.text(((width - placement_width) / 2, y_offset), placement_text, fill='#6366F1', font=details_font)
    y_offset += 100
    
    # User name
    user_name = user.profile.display_name or user.username
    bbox = draw.textbbox((0, 0), user_name, font=name_font)
    name_width = bbox[2] - bbox[0]
    draw.text(((width - name_width) / 2, y_offset), user_name, fill='#FFFFFF', font=name_font)
    y_offset += 150
    
    # Tournament name
    tournament_text = f"has achieved {placement_text.lower()} in"
    bbox = draw.textbbox((0, 0), tournament_text, font=details_font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, y_offset), tournament_text, fill='#94A3B8', font=details_font)
    y_offset += 60
    
    bbox = draw.textbbox((0, 0), tournament.name, font=details_font)
    tournament_width = bbox[2] - bbox[0]
    draw.text(((width - tournament_width) / 2, y_offset), tournament.name, fill='#FFFFFF', font=details_font)
    y_offset += 120
    
    # Prize amount (if applicable)
    if prize_amount and prize_amount > 0:
        prize_text = f"Prize: {prize_amount:,} DeltaCoins"
        bbox = draw.textbbox((0, 0), prize_text, font=details_font)
        prize_width = bbox[2] - bbox[0]
        draw.text(((width - prize_width) / 2, y_offset), prize_text, fill='#10B981', font=details_font)
        y_offset += 80
    
    # Date
    date_text = f"Issued: {datetime.now().strftime('%B %d, %Y')}"
    bbox = draw.textbbox((0, 0), date_text, font=small_font)
    date_width = bbox[2] - bbox[0]
    draw.text(((width - date_width) / 2, y_offset), date_text, fill='#64748B', font=small_font)
    
    # DeltaCrown branding
    brand_text = "DeltaCrown Esports Platform"
    bbox = draw.textbbox((0, 0), brand_text, font=small_font)
    brand_width = bbox[2] - bbox[0]
    draw.text(((width - brand_width) / 2, height - 80), brand_text, fill='#475569', font=small_font)
    
    # Save to BytesIO
    output = BytesIO()
    img.save(output, format='PNG', quality=95)
    output.seek(0)
    
    return output


def generate_tournament_certificate(user, tournament, placement, prize_amount=None, send_email=True):
    """
    Generate and save a tournament certificate for a user.
    
    Args:
        user: User instance
        tournament: Tournament instance
        placement: Integer placement (1, 2, 3, etc.)
        prize_amount: Optional prize amount in DeltaCoins
        send_email: Whether to send email notification
        
    Returns:
        Certificate instance
    """
    # Check if certificate already exists
    existing = Certificate.objects.filter(
        user=user,
        tournament_id=tournament.id,
        metadata__placement=placement
    ).first()
    
    if existing:
        logger.info(f"Certificate already exists for user {user.id} in tournament {tournament.id}")
        return existing
    
    # Generate certificate image
    try:
        image_data = create_certificate_image(user, tournament, placement, prize_amount)
    except Exception as e:
        logger.error(f"Failed to create certificate image: {e}")
        # Fallback: Create without image (manual upload required)
        image_data = None
    
    # Create certificate record
    placement_text = {
        1: "1st Place",
        2: "2nd Place",
        3: "3rd Place",
    }.get(placement, f"{placement}th Place")
    
    certificate = Certificate(
        user=user,
        title=f"{placement_text} - {tournament.name}",
        tournament_name=tournament.name,
        tournament_id=tournament.id,
        issued_at=datetime.now(),
        verification_code=generate_verification_code(),
        is_verified=True,
        metadata={
            'placement': placement,
            'prize_amount': prize_amount,
            'game': getattr(tournament, 'game', None),
            'tournament_slug': getattr(tournament, 'slug', None),
        }
    )
    
    # Save image if generated
    if image_data:
        filename = f"cert_{user.id}_{tournament.id}_{placement}.png"
        certificate.image.save(filename, ContentFile(image_data.read()), save=False)
    
    certificate.save()
    
    logger.info(
        f"Generated certificate: user={user.username}, tournament={tournament.name}, "
        f"placement={placement}, cert_id={certificate.id}"
    )
    
    # Send email notification
    if send_email and image_data:
        try:
            send_certificate_email(user, certificate, tournament, placement)
        except Exception as e:
            logger.error(f"Failed to send certificate email: {e}")
    
    # Award certificate achievement
    try:
        from apps.user_profile.services.achievement_service import check_special_achievements
        check_special_achievements(user)
    except Exception as e:
        logger.debug(f"Achievement check failed: {e}")
    
    return certificate


def send_certificate_email(user, certificate, tournament, placement):
    """
    Send email with certificate to user.
    
    Args:
        user: User instance
        certificate: Certificate instance
        tournament: Tournament instance
        placement: Integer placement
    """
    if not user.email:
        logger.warning(f"User {user.id} has no email, skipping certificate email")
        return
    
    placement_text = {
        1: "1st Place",
        2: "2nd Place",
        3: "3rd Place",
    }.get(placement, f"{placement}th Place")
    
    subject = f"🏆 Your {placement_text} Certificate - {tournament.name}"
    
    # Render email template
    context = {
        'user': user,
        'certificate': certificate,
        'tournament': tournament,
        'placement': placement,
        'placement_text': placement_text,
    }
    
    html_message = render_to_string('emails/certificate_issued.html', context)
    plain_message = f"""
Congratulations {user.profile.display_name or user.username}!

You've earned {placement_text} in {tournament.name}!

Your tournament certificate is ready. View it in your profile:
{settings.SITE_URL}/me/certificates/

Verification Code: {certificate.verification_code}

Keep competing and climbing the ranks!

- DeltaCrown Team
    """
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=html_message,
        fail_silently=False,
    )
    
    logger.info(f"Certificate email sent to {user.email} for tournament {tournament.name}")


def auto_generate_certificates_for_tournament(tournament):
    """
    Auto-generate certificates for all top placements in a completed tournament.
    
    Args:
        tournament: Completed Tournament instance
        
    Returns:
        List of generated Certificate instances
    """
    certificates = []
    
    # Get tournament results/rankings
    # This assumes tournament has a method to get final rankings
    # Adjust based on actual tournament model structure
    try:
        # Option 1: If tournament has participation/ranking model
        from apps.tournaments.models import Participation
        
        top_placements = Participation.objects.filter(
            tournament=tournament
        ).exclude(
            placement__isnull=True
        ).filter(
            placement__lte=3  # Top 3 get certificates
        ).order_by('placement')
        
        for participation in top_placements:
            # Get user (might be team-based, adjust accordingly)
            user = participation.user if hasattr(participation, 'user') else None
            if not user:
                continue
            
            # Get prize amount (if applicable)
            prize_amount = participation.prize_amount if hasattr(participation, 'prize_amount') else None
            
            # Generate certificate
            cert = generate_tournament_certificate(
                user=user,
                tournament=tournament,
                placement=participation.placement,
                prize_amount=prize_amount,
                send_email=True
            )
            certificates.append(cert)
        
    except ImportError:
        logger.warning("Participation model not found, skipping auto-certificate generation")
    except Exception as e:
        logger.error(f"Failed to auto-generate certificates: {e}")
    
    logger.info(
        f"Auto-generated {len(certificates)} certificates for tournament {tournament.name}"
    )
    
    return certificates
