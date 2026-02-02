"""MatchVerification model - verification workflow for match reports."""
from django.conf import settings
from django.db import models


class MatchVerification(models.Model):
    """
    Match verification workflow (Phase 3A-B).
    
    Tracks verification status and confidence for each MatchReport.
    Used to weight matches in ranking calculations.
    
    Verification Flow:
    1. PENDING → New report, awaiting opponent confirmation or timeout
    2. CONFIRMED → Opponent confirmed (100% weight)
    3. DISPUTED → Opponent rejected (requires admin review)
    4. ADMIN_VERIFIED → Manually verified by staff (100% weight)
    5. REJECTED → Invalid or fraudulent report (0% weight)
    """
    
    STATUS_CHOICES = [
        ('PENDING', 'Pending Verification'),
        ('CONFIRMED', 'Confirmed by Opponent'),
        ('DISPUTED', 'Disputed by Opponent'),
        ('ADMIN_VERIFIED', 'Admin Verified'),
        ('REJECTED', 'Rejected'),
    ]
    
    CONFIDENCE_CHOICES = [
        ('HIGH', 'High Confidence'),       # 100% weight
        ('MEDIUM', 'Medium Confidence'),   # 70% weight
        ('LOW', 'Low Confidence'),         # 30% weight
        ('NONE', 'No Confidence'),         # 0% weight
    ]
    
    # One-to-one with MatchReport
    match_report = models.OneToOneField(
        'competition.MatchReport',
        on_delete=models.CASCADE,
        related_name='verification',
        primary_key=True
    )
    
    # Verification status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        db_index=True
    )
    
    confidence_level = models.CharField(
        max_length=10,
        choices=CONFIDENCE_CHOICES,
        default='LOW',
        help_text="Confidence level affects ranking weight"
    )
    
    # Verification timeline
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When status changed to CONFIRMED/ADMIN_VERIFIED"
    )
    
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_matches',
        help_text="User who verified (opponent or admin)"
    )
    
    # Dispute handling
    dispute_reason = models.TextField(
        blank=True,
        help_text="Reason for dispute (if status=DISPUTED)"
    )
    
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal notes for admin review"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'competition_match_verification'
        verbose_name = 'Match Verification'
        verbose_name_plural = 'Match Verifications'
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['confidence_level']),
        ]
    
    def __str__(self):
        return f"Verification for {self.match_report} - {self.status}"
    
    def get_ranking_weight(self):
        """
        Get ranking weight multiplier based on confidence level.
        
        Returns:
            float: Weight multiplier (0.0 to 1.0)
        """
        weight_map = {
            'HIGH': 1.0,
            'MEDIUM': 0.7,
            'LOW': 0.3,
            'NONE': 0.0,
        }
        return weight_map.get(self.confidence_level, 0.0)
