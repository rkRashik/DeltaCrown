"""
Certificate model for tournament achievement proofs.

Source Documents:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md (Module 5.3)
- Documents/Planning/PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md (Sprint 6)
- Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md (ADR-001 Service Layer)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Service patterns)

This module defines:
- Certificate: PDF/image certificate generation with QR code verification
- Supports multi-language (Bengali + English)
- SHA-256 hash for tamper detection
- Revocation support for audit trail
"""

import uuid
from django.db import models
from django.conf import settings
from apps.common.models import TimestampedModel


class Certificate(TimestampedModel):
    """
    Tournament achievement certificates (PDF + image).
    
    Features:
    - PDF and PNG certificate generation (ReportLab + Pillow)
    - QR code verification with unique UUID
    - SHA-256 hash for tamper detection
    - Download tracking (count + first download timestamp)
    - Revocation support for disputed results
    - Multi-language templates (English + Bengali)
    
    Source: PHASE_5_IMPLEMENTATION_PLAN.md#module-53
    """
    
    # Certificate type choices
    WINNER = 'winner'
    RUNNER_UP = 'runner_up'
    THIRD_PLACE = 'third_place'
    PARTICIPANT = 'participant'
    
    CERTIFICATE_TYPE_CHOICES = [
        (WINNER, 'Winner Certificate'),
        (RUNNER_UP, 'Runner-up Certificate'),
        (THIRD_PLACE, 'Third Place Certificate'),
        (PARTICIPANT, 'Participation Certificate'),
    ]
    
    # Core relationships
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.CASCADE,
        related_name='certificates',
        help_text="Tournament this certificate was awarded for"
    )
    
    participant = models.ForeignKey(
        'Registration',
        on_delete=models.CASCADE,
        related_name='certificates',
        help_text="Participant who received this certificate (via Registration)"
    )
    
    # Certificate details
    certificate_type = models.CharField(
        max_length=20,
        choices=CERTIFICATE_TYPE_CHOICES,
        help_text="Type of certificate (winner, runner-up, etc.)"
    )
    
    placement = models.CharField(
        max_length=20,
        blank=True,
        default='',
        help_text="Placement string (e.g., '1st', '2nd', '3rd') for display"
    )
    
    # File storage (PDF + image)
    file_pdf = models.FileField(
        upload_to='certificates/pdf/%Y/%m/',
        null=True,
        blank=True,
        help_text="Generated PDF certificate file"
    )
    
    file_image = models.ImageField(
        upload_to='certificates/images/%Y/%m/',
        null=True,
        blank=True,
        help_text="Generated PNG/JPEG certificate image"
    )
    
    # Verification and tamper detection
    verification_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Unique verification code (UUID4) for public verification"
    )
    
    certificate_hash = models.CharField(
        max_length=64,
        help_text="SHA-256 hash of PDF file for tamper detection (64 hex characters)"
    )
    
    # Usage tracking
    generated_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When certificate was generated"
    )
    
    downloaded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="First download timestamp"
    )
    
    download_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times certificate has been downloaded"
    )
    
    # Revocation support (for disputed results or regeneration)
    revoked_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When certificate was revoked (if applicable)"
    )
    
    revoked_reason = models.TextField(
        blank=True,
        default='',
        help_text="Reason for revocation (e.g., 'Result disputed and changed', 'Regenerated with corrections')"
    )
    
    # S3 Migration tracking (Module 6.5)
    migrated_to_s3_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When certificate files were migrated to S3 (backfill tracking)"
    )
    
    class Meta:
        db_table = 'tournament_engine_certificate_certificate'
        verbose_name = 'Certificate'
        verbose_name_plural = 'Certificates'
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['tournament', 'certificate_type']),
            models.Index(fields=['participant']),
            models.Index(fields=['verification_code']),  # Explicitly index for fast lookups
            models.Index(fields=['revoked_at']),  # For filtering active certificates
        ]
        constraints = [
            # Prevent duplicate certificates for same participant + type (unless revoked)
            models.UniqueConstraint(
                fields=['tournament', 'participant', 'certificate_type'],
                name='unique_cert_per_type_per_participant',
                condition=models.Q(revoked_at__isnull=True),
            ),
        ]
    
    def __str__(self) -> str:
        participant_name = self.get_participant_display_name()
        revoked_suffix = " (REVOKED)" if self.is_revoked else ""
        return f"{self.get_certificate_type_display()} - {participant_name} - {self.tournament.name}{revoked_suffix}"
    
    def get_participant_display_name(self) -> str:
        """
        Get participant display name for certificate.
        
        Uses:
        1. User's full name (first_name + last_name) if available
        2. Fallback to username if no full name
        3. Team ID if team-based tournament
        
        Returns:
            Display name string
        """
        if self.participant.user:
            full_name = self.participant.user.get_full_name()
            if full_name.strip():
                return full_name
            return self.participant.user.username
        elif self.participant.team_id:
            return f"Team {self.participant.team_id}"
        return "Participant"
    
    @property
    def is_revoked(self) -> bool:
        """Check if certificate has been revoked"""
        return self.revoked_at is not None
    
    @property
    def has_been_downloaded(self) -> bool:
        """Check if certificate has been downloaded at least once"""
        return self.downloaded_at is not None
    
    @property
    def verification_url(self) -> str:
        """Get public verification URL for this certificate"""
        # Note: This assumes SITE_URL is configured in settings
        # In production, this should use the actual domain
        from django.conf import settings
        site_url = getattr(settings, 'SITE_URL', 'https://deltacrown.com')
        return f"{site_url}/api/tournaments/certificates/verify/{self.verification_code}/"
    
    def increment_download_count(self, set_downloaded_at: bool = False) -> None:
        """
        Increment download counter and optionally set first download timestamp.
        
        Args:
            set_downloaded_at: If True and downloaded_at is None, set to now
        """
        from django.utils import timezone
        
        self.download_count += 1
        
        if set_downloaded_at and self.downloaded_at is None:
            self.downloaded_at = timezone.now()
        
        self.save(update_fields=['download_count', 'downloaded_at', 'updated_at'])
    
    def revoke(self, reason: str = '') -> None:
        """
        Revoke this certificate (for disputed results or regeneration).
        
        Args:
            reason: Reason for revocation
        """
        from django.utils import timezone
        
        self.revoked_at = timezone.now()
        self.revoked_reason = reason
        self.save(update_fields=['revoked_at', 'revoked_reason', 'updated_at'])
