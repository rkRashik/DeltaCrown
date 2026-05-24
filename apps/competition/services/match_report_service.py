"""
Match Report Service

Phase 3A-C: Business logic for submitting and managing match reports.
Services layer owns all business rules, views remain thin.
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from typing import Optional

from apps.competition.models import MatchReport, MatchVerification, GameRankingConfig
from apps.organizations.models import Team
from apps.organizations.services.team_authority import can_manage_team_profile


class MatchReportService:
    """Service for handling match report submission and validation"""
    
    @staticmethod
    def submit_match_report(
        submitted_by,
        team1: Team,
        team2: Team,
        game_id: str,
        result: str,
        played_at,
        match_type: str = 'RANKED',
        evidence_url: Optional[str] = None,
        evidence_file = None,
    ) -> MatchReport:
        """
        Submit a new match report with validation
        
        Args:
            submitted_by: User submitting the report; must have team admin
                authority on team1 via team_authority.can_manage_team_profile.
            team1: Reporting team
            team2: Opponent team
            game_id: Game identifier (must exist in GameRankingConfig)
            result: Match result (WIN, LOSS, DRAW)
            played_at: When the match was played
            match_type: Type of match (RANKED, CASUAL, SCRIM)
            evidence_url: Optional external evidence URL
            evidence_file: Optional uploaded evidence file
            
        Returns:
            Created MatchReport instance
            
        Raises:
            PermissionDenied: If user not authorized
            ValidationError: If data invalid
        """
        if not can_manage_team_profile(submitted_by, team1):
            raise PermissionDenied(
                "Only team owners, managers, org administrators, or the team creator "
                "can submit match reports on behalf of a team."
            )
        
        # Validate teams are different
        if team1.id == team2.id:
            raise ValidationError("Cannot report a match against your own team")
        
        # Validate game exists
        if not GameRankingConfig.objects.filter(game_id=game_id).exists():
            raise ValidationError(f"Game '{game_id}' not supported for ranking")
        
        # Validate played_at not in future
        if played_at > timezone.now():
            raise ValidationError("Match date cannot be in the future")
        
        # Validate result
        if result not in ['WIN', 'LOSS', 'DRAW']:
            raise ValidationError("Result must be WIN, LOSS, or DRAW")
        
        # Validate match_type
        if match_type not in ['RANKED', 'CASUAL', 'SCRIM']:
            raise ValidationError("Match type must be RANKED, CASUAL, or SCRIM")
        
        # Create report and verification atomically
        with transaction.atomic():
            match_report = MatchReport.objects.create(
                team1=team1,
                team2=team2,
                game_id=game_id,
                match_type=match_type,
                result=result,
                evidence_url=evidence_url or '',
                evidence_notes=f"Submitted by {submitted_by.username}",
                submitted_by=submitted_by,
                played_at=played_at,
            )
            
            # Determine initial confidence based on evidence
            confidence = 'MEDIUM' if evidence_url else 'LOW'
            
            MatchVerification.objects.create(
                match_report=match_report,
                status='PENDING',
                confidence_level=confidence,
                admin_notes=f"Awaiting confirmation from {team2.name}"
            )
        
        return match_report
