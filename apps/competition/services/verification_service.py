"""
Verification Service

Phase 3A-C: Business logic for match verification workflow.
Handles confirmation, disputes, and admin verification.
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError

from apps.competition.models import MatchReport, MatchVerification
from apps.organizations.models import TeamMembership
from apps.organizations.choices import MembershipStatus


class VerificationService:
    """Service for handling match verification workflows"""
    
    @staticmethod
    def confirm_match(user, match_report_id: int) -> MatchVerification:
        """
        Confirm a match report (opponent confirms result)
        
        Args:
            user: User confirming (must be team2 member)
            match_report_id: ID of the match report to confirm
            
        Returns:
            Updated MatchVerification instance
            
        Raises:
            PermissionDenied: If user not authorized
            ValidationError: If verification not in confirmable state
        """
        try:
            match_report = MatchReport.objects.select_related('verification').get(id=match_report_id)
        except MatchReport.DoesNotExist:
            raise ValidationError("Match report not found")
        
        # Validate user is team2 member (opponent team)
        if not TeamMembership.objects.filter(
            team=match_report.team2,
            user=user,
            status=MembershipStatus.ACTIVE
        ).exists():
            raise PermissionDenied("Only members of the opponent team can confirm matches")
        
        verification = match_report.verification
        
        # Validate current status
        if verification.status != 'PENDING':
            raise ValidationError(f"Cannot confirm match with status '{verification.status}'")
        
        # Update verification
        with transaction.atomic():
            verification.status = 'CONFIRMED'
            verification.confidence_level = 'HIGH'
            verification.verified_at = timezone.now()
            verification.verified_by = user
            verification.admin_notes = f"Confirmed by {user.username} from {match_report.team2.name}"
            verification.save()
        
        return verification
    
    @staticmethod
    def dispute_match(user, match_report_id: int, reason: str) -> MatchVerification:
        """
        Dispute a match report (opponent disputes result)
        
        Args:
            user: User disputing (must be team2 member)
            match_report_id: ID of the match report to dispute
            reason: Reason for the dispute
            
        Returns:
            Updated MatchVerification instance
            
        Raises:
            PermissionDenied: If user not authorized
            ValidationError: If verification not in disputable state or reason missing
        """
        if not reason or len(reason.strip()) < 10:
            raise ValidationError("Dispute reason must be at least 10 characters")
        
        try:
            match_report = MatchReport.objects.select_related('verification').get(id=match_report_id)
        except MatchReport.DoesNotExist:
            raise ValidationError("Match report not found")
        
        # Validate user is team2 member (opponent team)
        if not TeamMembership.objects.filter(
            team=match_report.team2,
            user=user,
            status=MembershipStatus.ACTIVE
        ).exists():
            raise PermissionDenied("Only members of the opponent team can dispute matches")
        
        verification = match_report.verification
        
        # Validate current status
        if verification.status != 'PENDING':
            raise ValidationError(f"Cannot dispute match with status '{verification.status}'")
        
        # Update verification
        with transaction.atomic():
            verification.status = 'DISPUTED'
            verification.confidence_level = 'NONE'
            verification.verified_at = timezone.now()
            verification.verified_by = user
            verification.dispute_reason = reason
            verification.admin_notes = f"DISPUTED by {user.username}: {reason}"
            verification.save()
        
        return verification
    
    @staticmethod
    def admin_verify_match(user, match_report_id: int) -> MatchVerification:
        """
        Admin manually verifies a match (for disputed or unconfirmed matches)
        
        Args:
            user: Admin user verifying (must be staff)
            match_report_id: ID of the match report to verify
            
        Returns:
            Updated MatchVerification instance
            
        Raises:
            PermissionDenied: If user not staff
            ValidationError: If match report not found
        """
        if not user.is_staff:
            raise PermissionDenied("Only staff members can admin verify matches")
        
        try:
            match_report = MatchReport.objects.select_related('verification').get(id=match_report_id)
        except MatchReport.DoesNotExist:
            raise ValidationError("Match report not found")
        
        verification = match_report.verification
        
        # Update verification
        with transaction.atomic():
            verification.status = 'ADMIN_VERIFIED'
            verification.confidence_level = 'HIGH'
            verification.verified_at = timezone.now()
            verification.verified_by = user
            verification.admin_notes = f"Admin verified by {user.username}"
            verification.save()
        
        return verification
    
    @staticmethod
    def reject_match(user, match_report_id: int, reason: str = None) -> MatchVerification:
        """
        Admin rejects a match report (invalid/fraudulent)
        
        Args:
            user: Admin user rejecting (must be staff)
            match_report_id: ID of the match report to reject
            reason: Optional reason for rejection
            
        Returns:
            Updated MatchVerification instance
            
        Raises:
            PermissionDenied: If user not staff
            ValidationError: If match report not found
        """
        if not user.is_staff:
            raise PermissionDenied("Only staff members can reject matches")
        
        try:
            match_report = MatchReport.objects.select_related('verification').get(id=match_report_id)
        except MatchReport.DoesNotExist:
            raise ValidationError("Match report not found")
        
        verification = match_report.verification
        
        # Update verification
        with transaction.atomic():
            verification.status = 'REJECTED'
            verification.confidence_level = 'NONE'
            verification.verified_at = timezone.now()
            verification.verified_by = user
            notes = f"REJECTED by {user.username}"
            if reason:
                notes += f": {reason}"
            verification.admin_notes = notes
            verification.save()
        
        return verification
