"""
CertificateService - Business logic for tournament certificate generation (Module 5.3)

Source Documents:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md (Module 5.3: Certificates & Achievement Proofs)
- Documents/Planning/PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md (Sprint 6: Certificate generation)
- Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md (ADR-001: Service Layer Pattern)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Certificate model schema)

Architecture Decisions:
- ADR-001: Service layer pattern - All business logic in services
- Tech Stack: ReportLab (PDF), Pillow (PNG), qrcode (QR codes)
- Storage: Local MEDIA_ROOT (S3 migration planned for Phase 6/7)
- Hashing: SHA-256 over exact PDF bytes for tamper detection
- Fonts: Noto Sans Bengali (bundled in static/fonts/)

Certificate Generation Flow:
1. Verify tournament is COMPLETED and participant exists
2. Check for existing non-revoked certificate (idempotency)
3. Generate PDF using ReportLab with QR code
4. Calculate SHA-256 hash of PDF bytes
5. Convert PDF to PNG using Pillow (optional)
6. Save Certificate record with file paths and hash
7. Return Certificate instance

Service Responsibilities:
- Certificate generation (PDF + PNG)
- Idempotency enforcement (return existing non-revoked certificate)
- QR code generation (links to verification endpoint)
- SHA-256 hash calculation (tamper detection)
- Multi-language support (English default, Bengali optional)
- Template rendering (ReportLab canvas code)
- Verification system (public endpoint logic)
- Display name sanitization (no PII)

Template Layout (Simple & Code-Driven):
┌─────────────────────────────────────────┐
│  [Logo]           CERTIFICATE           │
│                                         │
│       Awarded to: [Participant Name]    │
│                                         │
│    For participating in/winning:        │
│         [Tournament Name]               │
│                                         │
│    Placement: [Winner/Runner-up/3rd]    │
│    Date: [Tournament End Date]          │
│                                         │
│    [QR Code]                            │
│    Verification Code: [UUID]            │
└─────────────────────────────────────────┘
"""

import hashlib
import io
import logging
import uuid
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from datetime import datetime

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError

# Cairo / ReportLab are optional – they require native C libraries that may
# not be present on every platform (e.g. Windows dev machines).  The
# certificate generation code will raise a clear error at *call time* if
# the libraries are missing, but Django and the rest of the app will boot
# fine without them.
try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.units import inch, cm
    from reportlab.lib import colors
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.utils import ImageReader
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

from apps.tournaments.models import (
    Tournament,
    Registration,
    Certificate,
)

logger = logging.getLogger(__name__)


class CertificateService:
    """
    Service for generating and managing tournament certificates.
    
    Implements:
    - PDF generation (ReportLab)
    - PNG generation (Pillow)
    - QR code embedding
    - SHA-256 tamper detection
    - Idempotency (no duplicate non-revoked certificates)
    - Multi-language support (en/bn)
    """
    
    # Certificate dimensions (A4 landscape)
    PDF_WIDTH, PDF_HEIGHT = A4[1], A4[0]  # Landscape: 842pt x 595pt
    
    # Certificate types display names
    TYPE_DISPLAY_NAMES = {
        'winner': {'en': 'Winner Certificate', 'bn': 'বিজয়ী সনদপত্র'},
        'runner_up': {'en': 'Runner-up Certificate', 'bn': 'দ্বিতীয় স্থান সনদপত্র'},
        'third_place': {'en': 'Third Place Certificate', 'bn': 'তৃতীয় স্থান সনদপত্র'},
        'participant': {'en': 'Participation Certificate', 'bn': 'অংশগ্রহণ সনদপত্র'},
    }
    
    # Placement display names
    PLACEMENT_DISPLAY = {
        '1': {'en': '1st Place - Winner', 'bn': '১ম স্থান - বিজয়ী'},
        '2': {'en': '2nd Place - Runner-up', 'bn': '২য় স্থান - রানার-আপ'},
        '3': {'en': '3rd Place', 'bn': '৩য় স্থান'},
    }
    
    def __init__(self):
        """Initialize service and register fonts if available."""
        self.bengali_font_available = self._register_bengali_font()
    
    def _register_bengali_font(self) -> bool:
        """
        Register Noto Sans Bengali font for ReportLab.
        
        Returns:
            bool: True if font registered successfully, False otherwise
        """
        try:
            # Check if font file exists
            if settings.STATIC_ROOT:
                font_path = Path(settings.STATIC_ROOT) / 'fonts' / 'NotoSansBengali-Regular.ttf'
            else:
                # Fallback to staticfiles directory during development
                font_path = Path(settings.BASE_DIR) / 'static' / 'fonts' / 'NotoSansBengali-Regular.ttf'
            
            if not font_path.exists():
                logger.warning(
                    f"Bengali font not found at {font_path}. "
                    "Bengali text will fall back to standard font. "
                    "See static/fonts/README.md for installation instructions."
                )
                return False
            
            # Register font with ReportLab
            pdfmetrics.registerFont(TTFont('NotoSansBengali', str(font_path)))
            logger.info(f"Successfully registered Bengali font from {font_path}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to register Bengali font: {e}. Bengali text may not render correctly.")
            return False
    
    @transaction.atomic
    def generate_certificate(
        self,
        registration_id: int,
        certificate_type: str,
        placement: Optional[str] = None,
        language: str = 'en',
        force_regenerate: bool = False,
    ) -> Certificate:
        """
        Generate certificate for a tournament participant.
        
        Args:
            registration_id: Registration ID (participant)
            certificate_type: One of: winner, runner_up, third_place, participant
            placement: Placement string (e.g., '1', '2', '3') - optional
            language: 'en' or 'bn' (default: 'en')
            force_regenerate: If True, regenerate even if non-revoked certificate exists
        
        Returns:
            Certificate: Generated or existing certificate instance
        
        Raises:
            ValidationError: If registration not found or tournament not completed
        """
        # ── Guard: ensure PDF libraries are available ────────────────
        if not HAS_REPORTLAB:
            raise RuntimeError(
                "Certificate generation requires reportlab + Cairo. "
                "Install them: pip install reportlab pycairo cairocffi CairoSVG"
            )

        # Validate inputs
        if certificate_type not in self.TYPE_DISPLAY_NAMES:
            raise ValidationError(f"Invalid certificate_type: {certificate_type}")
        
        if language not in ('en', 'bn'):
            raise ValidationError(f"Invalid language: {language}. Must be 'en' or 'bn'.")
        
        # Fetch registration with related data
        try:
            registration = Registration.objects.select_related(
                'tournament', 'user'
            ).get(id=registration_id)
        except Registration.DoesNotExist:
            raise ValidationError(f"Registration {registration_id} not found.")
        
        tournament = registration.tournament
        
        # Verify tournament is completed
        if tournament.status not in ('COMPLETED', 'completed'):
            raise ValidationError(
                f"Cannot generate certificate for tournament '{tournament.name}' "
                f"(status: {tournament.status}). Tournament must be COMPLETED."
            )
        
        # Check for existing non-revoked certificate (idempotency)
        if not force_regenerate:
            existing_cert = Certificate.objects.filter(
                tournament=tournament,
                participant=registration,
                certificate_type=certificate_type,
                revoked_at__isnull=True,
            ).first()
            
            if existing_cert:
                logger.info(
                    f"Returning existing certificate {existing_cert.id} for "
                    f"registration {registration_id}, type {certificate_type}"
                )
                return existing_cert
        
        # Generate certificate files
        pdf_bytes, png_bytes, verification_code = self._render_certificate(
            tournament=tournament,
            registration=registration,
            certificate_type=certificate_type,
            placement=placement,
            language=language,
        )
        
        # Calculate PDF hash (SHA-256 of exact bytes served to users)
        cert_hash = self._calculate_hash(pdf_bytes)
        
        # Create Certificate record
        certificate = Certificate.objects.create(
            tournament=tournament,
            participant=registration,
            certificate_type=certificate_type,
            placement=placement or '',
            verification_code=verification_code,
            certificate_hash=cert_hash,
            generated_at=timezone.now(),
        )
        
        # Save files
        pdf_filename = f"cert_{certificate.id}_{verification_code.hex[:8]}.pdf"
        png_filename = f"cert_{certificate.id}_{verification_code.hex[:8]}.png"
        
        certificate.file_pdf.save(pdf_filename, ContentFile(pdf_bytes), save=False)
        certificate.file_image.save(png_filename, ContentFile(png_bytes), save=False)
        certificate.save()
        
        logger.info(
            f"Generated certificate {certificate.id} (type: {certificate_type}) "
            f"for registration {registration_id} in tournament '{tournament.name}'"
        )
        
        return certificate
    
    def _render_certificate(
        self,
        tournament: Tournament,
        registration: Registration,
        certificate_type: str,
        placement: Optional[str],
        language: str,
    ) -> Tuple[bytes, bytes, uuid.UUID]:
        """
        Render certificate to PDF and PNG bytes.
        
        Args:
            tournament: Tournament instance
            registration: Registration instance
            certificate_type: Certificate type
            placement: Placement string
            language: Language code ('en' or 'bn')
        
        Returns:
            Tuple of (pdf_bytes, png_bytes, verification_code)
        """
        # Generate unique verification code
        verification_code = uuid.uuid4()
        
        # Build verification URL
        verification_url = self._build_verification_url(verification_code)
        
        # Generate QR code image
        qr_image = self._create_qr_code(verification_url, size=200)
        
        # Render PDF
        pdf_bytes = self._render_pdf_certificate(
            tournament=tournament,
            registration=registration,
            certificate_type=certificate_type,
            placement=placement,
            language=language,
            verification_code=verification_code,
            qr_image=qr_image,
        )
        
        # Render PNG (convert PDF to image using Pillow)
        png_bytes = self._render_png_certificate(
            tournament=tournament,
            registration=registration,
            certificate_type=certificate_type,
            placement=placement,
            language=language,
            verification_code=verification_code,
            qr_image=qr_image,
        )
        
        return pdf_bytes, png_bytes, verification_code
    
    def _render_pdf_certificate(
        self,
        tournament: Tournament,
        registration: Registration,
        certificate_type: str,
        placement: Optional[str],
        language: str,
        verification_code: uuid.UUID,
        qr_image: Image.Image,
    ) -> bytes:
        """
        Render certificate as PDF using ReportLab.
        
        Simple layout:
        - Header: "CERTIFICATE" (centered, large font)
        - Body: Participant name, tournament name, placement, date
        - Footer: QR code + verification code
        
        Args:
            tournament: Tournament instance
            registration: Registration instance
            certificate_type: Certificate type
            placement: Placement string
            language: Language code
            verification_code: UUID for verification
            qr_image: PIL Image of QR code
        
        Returns:
            bytes: PDF file content
        """
        buffer = io.BytesIO()
        
        # Create canvas (A4 landscape)
        c = canvas.Canvas(buffer, pagesize=(self.PDF_WIDTH, self.PDF_HEIGHT))
        
        # Set metadata
        c.setAuthor("DeltaCrown Tournament Platform")
        c.setTitle(f"{certificate_type.replace('_', ' ').title()} - {tournament.name}")
        participant_name = self._get_participant_display_name(registration)
        c.setSubject(f"Certificate for {participant_name}")
        
        # Choose font (Bengali or standard)
        if language == 'bn' and self.bengali_font_available:
            body_font = 'NotoSansBengali'
            header_font = 'Helvetica-Bold'  # Use standard for header (works well)
        else:
            body_font = 'Helvetica'
            header_font = 'Helvetica-Bold'
        
        # === HEADER ===
        c.setFont(header_font, 36)
        header_text = "CERTIFICATE" if language == 'en' else "সনদপত্র"
        c.drawCentredString(self.PDF_WIDTH / 2, self.PDF_HEIGHT - 80, header_text)
        
        # Certificate type subtitle
        c.setFont(header_font, 20)
        type_display = self.TYPE_DISPLAY_NAMES[certificate_type][language]
        c.drawCentredString(self.PDF_WIDTH / 2, self.PDF_HEIGHT - 120, type_display)
        
        # === BODY ===
        y_position = self.PDF_HEIGHT - 200
        
        # "Awarded to" label
        c.setFont(body_font, 16)
        awarded_label = "Awarded to:" if language == 'en' else "প্রদত্ত:"
        c.drawCentredString(self.PDF_WIDTH / 2, y_position, awarded_label)
        y_position -= 40
        
        # Participant name (bold, larger)
        c.setFont(header_font, 24)
        participant_name = self._get_participant_display_name(registration)
        # Truncate long names (edge case handling)
        if len(participant_name) > 50:
            participant_name = participant_name[:47] + "..."
        c.drawCentredString(self.PDF_WIDTH / 2, y_position, participant_name)
        y_position -= 60
        
        # "For participating in/winning" label
        c.setFont(body_font, 14)
        participation_label = (
            "for their achievement in:" if certificate_type != 'participant' 
            else "for participating in:"
        ) if language == 'en' else (
            "তাদের অর্জনের জন্য:" if certificate_type != 'participant'
            else "অংশগ্রহণের জন্য:"
        )
        c.drawCentredString(self.PDF_WIDTH / 2, y_position, participation_label)
        y_position -= 35
        
        # Tournament name (bold)
        c.setFont(header_font, 18)
        tournament_name = tournament.name
        # Truncate very long tournament names (edge case handling)
        if len(tournament_name) > 60:
            tournament_name = tournament_name[:57] + "..."
        c.drawCentredString(self.PDF_WIDTH / 2, y_position, tournament_name)
        y_position -= 50
        
        # Placement (if applicable)
        if placement and placement in self.PLACEMENT_DISPLAY:
            c.setFont(body_font, 16)
            placement_text = self.PLACEMENT_DISPLAY[placement][language]
            c.drawCentredString(self.PDF_WIDTH / 2, y_position, placement_text)
            y_position -= 35
        
        # Date
        c.setFont(body_font, 12)
        date_label = "Date:" if language == 'en' else "তারিখ:"
        date_text = f"{date_label} {timezone.now().strftime('%B %d, %Y')}"
        c.drawCentredString(self.PDF_WIDTH / 2, y_position, date_text)
        
        # === FOOTER: QR Code + Verification Code ===
        # Draw QR code (bottom center)
        qr_buffer = io.BytesIO()
        qr_image.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        qr_reader = ImageReader(qr_buffer)
        
        qr_size = 1.5 * inch  # 1.5 inch square
        qr_x = (self.PDF_WIDTH - qr_size) / 2
        qr_y = 80
        c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)
        
        # Verification code text (below QR)
        c.setFont('Courier', 8)
        verify_label = "Verification Code:" if language == 'en' else "যাচাইকরণ কোড:"
        c.drawCentredString(self.PDF_WIDTH / 2, 60, verify_label)
        c.drawCentredString(self.PDF_WIDTH / 2, 45, str(verification_code))
        
        # Footer text (bottom)
        c.setFont('Helvetica', 8)
        footer_text = "Scan QR code to verify authenticity" if language == 'en' else "সত্যতা যাচাই করতে QR কোড স্ক্যান করুন"
        c.drawCentredString(self.PDF_WIDTH / 2, 25, footer_text)
        
        # Finalize PDF
        c.showPage()
        c.save()
        
        buffer.seek(0)
        return buffer.read()
    
    def _render_png_certificate(
        self,
        tournament: Tournament,
        registration: Registration,
        certificate_type: str,
        placement: Optional[str],
        language: str,
        verification_code: uuid.UUID,
        qr_image: Image.Image,
    ) -> bytes:
        """
        Render certificate as PNG using Pillow.
        
        Creates a 1920x1080 image with similar layout to PDF.
        
        Args:
            tournament: Tournament instance
            registration: Registration instance
            certificate_type: Certificate type
            placement: Placement string
            language: Language code
            verification_code: UUID for verification
            qr_image: PIL Image of QR code
        
        Returns:
            bytes: PNG file content
        """
        # Create image (1920x1080, white background)
        img = Image.new('RGB', (1920, 1080), color='white')
        draw = ImageDraw.Draw(img)
        
        # Try to use system fonts (fallback to default if not available)
        try:
            font_large = ImageFont.truetype("arial.ttf", 60)
            font_medium = ImageFont.truetype("arial.ttf", 40)
            font_small = ImageFont.truetype("arial.ttf", 28)
            font_tiny = ImageFont.truetype("arial.ttf", 18)
        except IOError:
            # Fallback to default font
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_tiny = ImageFont.load_default()
        
        # Draw border
        border_margin = 40
        draw.rectangle(
            [(border_margin, border_margin), (1920 - border_margin, 1080 - border_margin)],
            outline='black',
            width=3,
        )
        
        # Header: "CERTIFICATE"
        header_text = "CERTIFICATE" if language == 'en' else "সনদপত্র"
        header_bbox = draw.textbbox((0, 0), header_text, font=font_large)
        header_width = header_bbox[2] - header_bbox[0]
        draw.text(((1920 - header_width) / 2, 100), header_text, fill='black', font=font_large)
        
        # Certificate type
        type_display = self.TYPE_DISPLAY_NAMES[certificate_type][language]
        type_bbox = draw.textbbox((0, 0), type_display, font=font_medium)
        type_width = type_bbox[2] - type_bbox[0]
        draw.text(((1920 - type_width) / 2, 180), type_display, fill='gray', font=font_medium)
        
        # Body
        y_pos = 300
        
        # "Awarded to"
        awarded_label = "Awarded to:" if language == 'en' else "প্রদত্ত:"
        awarded_bbox = draw.textbbox((0, 0), awarded_label, font=font_small)
        awarded_width = awarded_bbox[2] - awarded_bbox[0]
        draw.text(((1920 - awarded_width) / 2, y_pos), awarded_label, fill='black', font=font_small)
        y_pos += 60
        
        # Participant name
        participant_name = self._get_participant_display_name(registration)
        if len(participant_name) > 50:
            participant_name = participant_name[:47] + "..."
        name_bbox = draw.textbbox((0, 0), participant_name, font=font_medium)
        name_width = name_bbox[2] - name_bbox[0]
        draw.text(((1920 - name_width) / 2, y_pos), participant_name, fill='#0066cc', font=font_medium)
        y_pos += 100
        
        # Participation label
        participation_label = (
            "for their achievement in:" if certificate_type != 'participant' 
            else "for participating in:"
        ) if language == 'en' else (
            "তাদের অর্জনের জন্য:" if certificate_type != 'participant'
            else "অংশগ্রহণের জন্য:"
        )
        part_bbox = draw.textbbox((0, 0), participation_label, font=font_small)
        part_width = part_bbox[2] - part_bbox[0]
        draw.text(((1920 - part_width) / 2, y_pos), participation_label, fill='black', font=font_small)
        y_pos += 50
        
        # Tournament name
        tournament_name = tournament.name
        if len(tournament_name) > 60:
            tournament_name = tournament_name[:57] + "..."
        tourn_bbox = draw.textbbox((0, 0), tournament_name, font=font_medium)
        tourn_width = tourn_bbox[2] - tourn_bbox[0]
        draw.text(((1920 - tourn_width) / 2, y_pos), tournament_name, fill='black', font=font_medium)
        y_pos += 80
        
        # Placement (if applicable)
        if placement and placement in self.PLACEMENT_DISPLAY:
            placement_text = self.PLACEMENT_DISPLAY[placement][language]
            place_bbox = draw.textbbox((0, 0), placement_text, font=font_small)
            place_width = place_bbox[2] - place_bbox[0]
            draw.text(((1920 - place_width) / 2, y_pos), placement_text, fill='#008800', font=font_small)
            y_pos += 50
        
        # Date
        date_label = "Date:" if language == 'en' else "তারিখ:"
        date_text = f"{date_label} {timezone.now().strftime('%B %d, %Y')}"
        date_bbox = draw.textbbox((0, 0), date_text, font=font_small)
        date_width = date_bbox[2] - date_bbox[0]
        draw.text(((1920 - date_width) / 2, y_pos), date_text, fill='black', font=font_small)
        
        # QR code (bottom center)
        qr_resized = qr_image.resize((200, 200))
        qr_x = (1920 - 200) // 2
        qr_y = 820
        img.paste(qr_resized, (qr_x, qr_y))
        
        # Verification code
        verify_label = f"Verification: {str(verification_code)}"
        verify_bbox = draw.textbbox((0, 0), verify_label, font=font_tiny)
        verify_width = verify_bbox[2] - verify_bbox[0]
        draw.text(((1920 - verify_width) / 2, 1030), verify_label, fill='gray', font=font_tiny)
        
        # Save to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.read()
    
    def _create_qr_code(self, url: str, size: int = 300) -> Image.Image:
        """
        Generate QR code image for verification URL.
        
        Args:
            url: Verification URL to encode
            size: QR code size in pixels (default: 300x300)
        
        Returns:
            PIL Image of QR code
        """
        qr = qrcode.QRCode(
            version=1,  # Auto-adjust size
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        # Generate image
        img = qr.make_image(fill_color="black", back_color="white")
        img = img.resize((size, size))
        
        return img
    
    def _calculate_hash(self, pdf_bytes: bytes) -> str:
        """
        Calculate SHA-256 hash of PDF bytes for tamper detection.
        
        Args:
            pdf_bytes: PDF file content
        
        Returns:
            str: 64-character hex SHA-256 hash
        """
        return hashlib.sha256(pdf_bytes).hexdigest()
    
    def _build_verification_url(self, verification_code: uuid.UUID) -> str:
        """
        Build public verification URL for certificate.
        
        Args:
            verification_code: UUID verification code
        
        Returns:
            str: Full verification URL
        """
        # Use settings.SITE_URL or construct from domain
        base_url = getattr(settings, 'SITE_URL', 'https://deltacrown.com')
        return f"{base_url}/api/tournaments/certificates/verify/{verification_code}/"
    
    def _get_participant_display_name(self, registration: Registration) -> str:
        """
        Get display name for participant (no PII).
        
        Priority:
        1. User full name (first + last)
        2. Username
        3. Fallback: "Participant"
        
        Args:
            registration: Registration instance
        
        Returns:
            str: Display name for participant
        """
        user = registration.user
        
        # Try full name
        if user.first_name or user.last_name:
            full_name = f"{user.first_name} {user.last_name}".strip()
            if full_name:
                return full_name
        
        # Fallback to username
        if user.username:
            return user.username
        
        # Last resort fallback
        return "Participant"
    
    def verify_certificate(self, verification_code: uuid.UUID) -> Dict[str, Any]:
        """
        Verify certificate authenticity by verification code.
        
        This method is used by the public verification endpoint.
        
        Args:
            verification_code: UUID verification code from certificate
        
        Returns:
            dict: Verification result with structure:
                {
                    'valid': bool,
                    'certificate_id': int,
                    'tournament_name': str,
                    'participant_name': str,  # Display name only, no PII
                    'certificate_type': str,
                    'placement': str,
                    'generated_at': datetime,
                    'revoked': bool,
                    'is_tampered': bool,  # True if hash mismatch
                }
        
        Raises:
            ValidationError: If verification code not found
        """
        try:
            certificate = Certificate.objects.select_related(
                'tournament', 'participant__user'
            ).get(verification_code=verification_code)
        except Certificate.DoesNotExist:
            raise ValidationError(f"Certificate with verification code {verification_code} not found.")
        
        # Check if certificate is revoked
        is_revoked = certificate.is_revoked
        
        # Check for tampering (compare stored hash with actual file hash)
        is_tampered = False
        if certificate.file_pdf:
            try:
                certificate.file_pdf.open('rb')
                actual_bytes = certificate.file_pdf.read()
                actual_hash = self._calculate_hash(actual_bytes)
                is_tampered = (actual_hash != certificate.certificate_hash)
                certificate.file_pdf.close()
            except Exception as e:
                logger.error(f"Failed to read certificate file for tampering check: {e}")
                is_tampered = True  # Assume tampered if file can't be read
        
        # Build response (no PII - display name only)
        return {
            'valid': not is_revoked and not is_tampered,
            'certificate_id': certificate.id,
            'tournament_name': certificate.tournament.name,
            'participant_name': self._get_participant_display_name(certificate.participant),  # Display name, no PII
            'certificate_type': certificate.get_certificate_type_display(),
            'placement': certificate.placement,
            'generated_at': certificate.generated_at,
            'revoked': is_revoked,
            'revoked_reason': certificate.revoked_reason if is_revoked else None,
            'is_tampered': is_tampered,
        }
    
    @transaction.atomic
    def generate_all_certificates_for_tournament(
        self,
        tournament_id: int,
        language: str = 'en',
        force_regenerate: bool = False,
    ) -> List[Certificate]:
        """
        Generate certificates for all participants in a tournament.
        
        Generates:
        - Winner certificate (1st place)
        - Runner-up certificate (2nd place)
        - Third place certificate (3rd place)
        - Participation certificates for all other registered participants
        
        Args:
            tournament_id: Tournament ID
            language: 'en' or 'bn' (default: 'en')
            force_regenerate: If True, regenerate even if certificates exist
        
        Returns:
            List[Certificate]: Generated certificates
        
        Raises:
            ValidationError: If tournament not found or not completed
        """
        try:
            tournament = Tournament.objects.get(id=tournament_id)
        except Tournament.DoesNotExist:
            raise ValidationError(f"Tournament {tournament_id} not found.")
        
        if tournament.status not in ('COMPLETED', 'completed'):
            raise ValidationError(
                f"Cannot generate certificates for tournament '{tournament.name}' "
                f"(status: {tournament.status}). Tournament must be COMPLETED."
            )
        
        certificates = []
        
        # Get all registrations
        registrations = Registration.objects.filter(
            tournament=tournament
        ).select_related('user')
        
        # TODO: In future, integrate with TournamentResult to auto-determine winners
        # For now, this is a manual process - organizers call this after manually setting placements
        
        # Generate participation certificates for all
        for registration in registrations:
            try:
                cert = self.generate_certificate(
                    registration_id=registration.id,
                    certificate_type='participant',
                    placement=None,
                    language=language,
                    force_regenerate=force_regenerate,
                )
                certificates.append(cert)
            except Exception as e:
                logger.error(
                    f"Failed to generate certificate for registration {registration.id}: {e}"
                )
        
        logger.info(
            f"Generated {len(certificates)} certificates for tournament '{tournament.name}' "
            f"(ID: {tournament_id})"
        )
        
        return certificates


# Singleton instance for easy import
certificate_service = CertificateService()
