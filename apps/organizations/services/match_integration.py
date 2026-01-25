"""
Match Result Integration Service - Connects match completion to vNext RankingService.

This module provides the bridge between the match/tournament system and the vNext
ranking system. It processes match results and updates team rankings via
RankingService.apply_match_result().

COMPATIBILITY: vNext-only when feature flags enabled. Legacy system unaffected.
PERFORMANCE: Target <100ms (p95) for match result processing.

Integration Points:
- Called after match completion (manual trigger or signal-based)
- Feature flag gated (TEAM_VNEXT_ADAPTER_ENABLED)
- Supports mixed matches (vNext vs legacy teams)
- Logs metrics for monitoring

Phase 4 - Task P4-T1
"""

import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction

from apps.organizations.models import Team as VNextTeam
from apps.organizations.services.ranking_service import RankingService, MatchResultDelta
from apps.organizations.services.exceptions import NotFoundError, ValidationError

logger = logging.getLogger(__name__)


# ============================================================================
# DATA TRANSFER OBJECTS
# ============================================================================

@dataclass
class MatchIntegrationResult:
    """Result of match integration processing."""
    success: bool
    vnext_processed: bool  # True if any vNext teams were updated
    legacy_processed: bool  # True if legacy teams were processed
    winner_tier_changed: bool
    loser_tier_changed: bool
    error_message: Optional[str] = None
    processing_time_ms: Optional[float] = None


# ============================================================================
# MATCHRESULTINTEGRATOR - PUBLIC API
# ============================================================================

class MatchResultIntegrator:
    """
    Service for integrating match results with vNext ranking system.
    
    This class provides the integration layer between match completion
    events and vNext team rankings. It handles feature flag checks,
    team type detection (vNext vs legacy), and delegates to RankingService.
    
    Thread Safety: All methods are thread-safe.
    """
    
    # ========================================================================
    # FEATURE FLAG CHECKS
    # ========================================================================
    
    @staticmethod
    def is_vnext_enabled() -> bool:
        """
        Check if vNext adapter is enabled.
        
        Returns:
            bool: True if vNext ranking integration should be active
        """
        return (
            getattr(settings, 'TEAM_VNEXT_ADAPTER_ENABLED', False) and
            not getattr(settings, 'TEAM_VNEXT_FORCE_LEGACY', False)
        )
    
    # ========================================================================
    # TEAM TYPE DETECTION
    # ========================================================================
    
    @staticmethod
    def is_vnext_team(team_id: int) -> bool:
        """
        Check if team ID belongs to vNext system.
        
        Args:
            team_id: Team primary key
        
        Returns:
            bool: True if team is vNext, False if legacy or not found
        """
        try:
            VNextTeam.objects.get(id=team_id)
            return True
        except VNextTeam.DoesNotExist:
            return False
    
    @staticmethod
    def get_team_types(winner_team_id: int, loser_team_id: int) -> Tuple[bool, bool]:
        """
        Determine team types for both participants.
        
        Args:
            winner_team_id: Winning team ID
            loser_team_id: Losing team ID
        
        Returns:
            Tuple of (winner_is_vnext, loser_is_vnext)
        """
        winner_is_vnext = MatchResultIntegrator.is_vnext_team(winner_team_id)
        loser_is_vnext = MatchResultIntegrator.is_vnext_team(loser_team_id)
        return winner_is_vnext, loser_is_vnext
    
    # ========================================================================
    # MATCH RESULT PROCESSING
    # ========================================================================
    
    @staticmethod
    def process_match_result(
        winner_team_id: int,
        loser_team_id: int,
        *,
        match_id: Optional[int] = None,
        is_tournament_match: bool = False
    ) -> MatchIntegrationResult:
        """
        Process match result and update rankings for vNext teams.
        
        This is the main entry point for match result integration. It:
        1. Checks if vNext is enabled
        2. Determines team types (vNext vs legacy)
        3. Calls RankingService.apply_match_result() for vNext teams
        4. Logs metrics and errors
        
        Args:
            winner_team_id: Winning team ID
            loser_team_id: Losing team ID
            match_id: Match record ID for audit trail (optional)
            is_tournament_match: Tournament matches may have bonus multipliers
        
        Returns:
            MatchIntegrationResult with processing details
        
        Raises:
            None - All errors are caught and logged, returns error in result
        
        Performance:
            - Target: <100ms (p95)
            - Queries: ≤5 (2 for team type checks, 3 for ranking updates)
        
        Usage:
            # After match completion in tournament system:
            result = MatchResultIntegrator.process_match_result(
                winner_team_id=42,
                loser_team_id=99,
                match_id=12345,
                is_tournament_match=True
            )
            if result.success and result.winner_tier_changed:
                send_notification("Congratulations! You ranked up!")
        """
        import time
        start_time = time.time()
        
        try:
            # Check feature flags
            if not MatchResultIntegrator.is_vnext_enabled():
                logger.debug(
                    f"vNext adapter disabled, skipping ranking update for match {match_id}"
                )
                return MatchIntegrationResult(
                    success=True,
                    vnext_processed=False,
                    legacy_processed=False,
                    winner_tier_changed=False,
                    loser_tier_changed=False,
                    error_message="vNext adapter disabled"
                )
            
            # Determine team types
            winner_is_vnext, loser_is_vnext = MatchResultIntegrator.get_team_types(
                winner_team_id, loser_team_id
            )
            
            # Skip if neither team is vNext
            if not winner_is_vnext and not loser_is_vnext:
                logger.debug(
                    f"Match {match_id}: Both teams are legacy, skipping vNext ranking update"
                )
                return MatchIntegrationResult(
                    success=True,
                    vnext_processed=False,
                    legacy_processed=True,
                    winner_tier_changed=False,
                    loser_tier_changed=False
                )
            
            # Both teams must be vNext for ranking update
            # (Mixed matches don't update rankings in Phase 4)
            if not (winner_is_vnext and loser_is_vnext):
                logger.info(
                    f"Match {match_id}: Mixed vNext/legacy match detected. "
                    f"Winner vNext: {winner_is_vnext}, Loser vNext: {loser_is_vnext}. "
                    f"Skipping ranking update (not supported in Phase 4)."
                )
                return MatchIntegrationResult(
                    success=True,
                    vnext_processed=False,
                    legacy_processed=False,
                    winner_tier_changed=False,
                    loser_tier_changed=False,
                    error_message="Mixed vNext/legacy matches not supported for ranking updates"
                )
            
            # Both teams are vNext - update rankings
            logger.info(
                f"Processing vNext match result: Match {match_id}, "
                f"Winner: {winner_team_id}, Loser: {loser_team_id}, "
                f"Tournament: {is_tournament_match}"
            )
            
            delta = RankingService.apply_match_result(
                winner_team_id=winner_team_id,
                loser_team_id=loser_team_id,
                match_id=match_id,
                is_tournament_match=is_tournament_match
            )
            
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            
            logger.info(
                f"Match {match_id} rankings updated successfully. "
                f"Winner CP: +{delta.winner_cp_gain} (Tier: {delta.winner_new_tier}, "
                f"Changed: {delta.winner_tier_changed}), "
                f"Loser CP: -{delta.loser_cp_loss} (Tier: {delta.loser_new_tier}, "
                f"Changed: {delta.loser_tier_changed}). "
                f"Processing time: {processing_time:.2f}ms"
            )
            
            return MatchIntegrationResult(
                success=True,
                vnext_processed=True,
                legacy_processed=False,
                winner_tier_changed=delta.winner_tier_changed,
                loser_tier_changed=delta.loser_tier_changed,
                processing_time_ms=processing_time
            )
        
        except NotFoundError as e:
            error_msg = f"Team not found: {str(e)}"
            logger.error(
                f"Match {match_id} ranking update failed: {error_msg}",
                extra={"winner_team_id": winner_team_id, "loser_team_id": loser_team_id}
            )
            return MatchIntegrationResult(
                success=False,
                vnext_processed=False,
                legacy_processed=False,
                winner_tier_changed=False,
                loser_tier_changed=False,
                error_message=error_msg
            )
        
        except ValidationError as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(
                f"Match {match_id} ranking update failed: {error_msg}",
                extra={"winner_team_id": winner_team_id, "loser_team_id": loser_team_id}
            )
            return MatchIntegrationResult(
                success=False,
                vnext_processed=False,
                legacy_processed=False,
                winner_tier_changed=False,
                loser_tier_changed=False,
                error_message=error_msg
            )
        
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.exception(
                f"Match {match_id} ranking update failed with unexpected error",
                extra={"winner_team_id": winner_team_id, "loser_team_id": loser_team_id}
            )
            return MatchIntegrationResult(
                success=False,
                vnext_processed=False,
                legacy_processed=False,
                winner_tier_changed=False,
                loser_tier_changed=False,
                error_message=error_msg
            )
    
    # ========================================================================
    # DJANGO SIGNAL HANDLER (Phase 4+)
    # ========================================================================
    
    @staticmethod
    def handle_match_result_signal(sender, **kwargs):
        """
        Django signal handler for match_result_finalized signal.
        
        This handler is called automatically when a match completes.
        Connect in AppConfig.ready():
        
            from django.dispatch import receiver
            from apps.match.signals import match_result_finalized
            
            @receiver(match_result_finalized)
            def handle_match_completion(sender, **kwargs):
                MatchResultIntegrator.handle_match_result_signal(sender, **kwargs)
        
        Args:
            sender: Signal sender
            **kwargs: Signal data (must include winner_team_id, loser_team_id)
        """
        winner_team_id = kwargs.get('winner_team_id')
        loser_team_id = kwargs.get('loser_team_id')
        match_id = kwargs.get('match_id')
        is_tournament_match = kwargs.get('is_tournament_match', False)
        
        if not winner_team_id or not loser_team_id:
            logger.error(
                f"match_result_finalized signal missing required data: {kwargs}"
            )
            return
        
        MatchResultIntegrator.process_match_result(
            winner_team_id=winner_team_id,
            loser_team_id=loser_team_id,
            match_id=match_id,
            is_tournament_match=is_tournament_match
        )
