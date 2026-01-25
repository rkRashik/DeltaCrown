"""
Ranking Celery Tasks for vNext Teams and Organizations.

These tasks handle bulk ranking operations that run on schedules:
- Nightly team ranking recalculation
- Inactivity decay processing
- Organization aggregate ranking updates

Performance Requirements:
- Chunked processing (200-500 records per batch)
- Efficient queryset usage (select_related, prefetch_related)
- Transaction management (atomic only where needed)
- Structured logging with metrics

Phase 4 - Task P4-T2
"""

import logging
from datetime import timedelta
from typing import Optional, Dict, Any
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from celery import shared_task

from apps.organizations.models import Team, TeamRanking, Organization, OrganizationRanking
from apps.organizations.services.ranking_service import RankingService

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

# Chunk size for batch processing
RANKING_CHUNK_SIZE = 500

# Inactivity thresholds
INACTIVITY_CUTOFF_DAYS = 7  # Teams inactive for 7+ days subject to decay
INACTIVITY_DECAY_RATE = 0.05  # 5% CP loss per week

# CP floors
MINIMUM_CP = 0  # CP cannot go below 0


# ============================================================================
# TEAM RANKING RECALCULATION
# ============================================================================

@shared_task(
    name='apps.organizations.tasks.recalculate_team_rankings',
    bind=True,
    max_retries=3,
    default_retry_delay=300  # 5 minutes
)
def recalculate_team_rankings(
    self,
    game_id: Optional[int] = None,
    region: Optional[str] = None,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Recalculate team rankings (tier, sanity checks).
    
    This task runs nightly to:
    1. Recalculate tier based on current CP
    2. Sanity-check CP floors (ensure CP >= 0)
    3. Update derived fields if needed
    
    Args:
        game_id: Optional filter by game ID
        region: Optional filter by region
        limit: Optional limit number of teams to process (for testing)
    
    Returns:
        Dict with processing metrics:
        - teams_processed: Total teams processed
        - teams_updated: Teams with changes
        - tier_changes: Count of tier changes
        - errors: Count of errors
        - duration_seconds: Total processing time
    
    Idempotency:
        Safe to run multiple times. Only updates teams where changes detected.
    
    Performance:
        - Processes in chunks of 500 teams
        - Uses select_related for single-query team fetching
        - Target: <1ms per team (500 teams = ~500ms per chunk)
    """
    start_time = timezone.now()
    teams_processed = 0
    teams_updated = 0
    tier_changes = 0
    errors = 0
    
    logger.info(
        f"Starting team ranking recalculation (game_id={game_id}, region={region}, limit={limit})"
    )
    
    try:
        # Build queryset
        queryset = TeamRanking.objects.select_related('team').filter(
            team__status='ACTIVE'
        )
        
        if game_id is not None:
            queryset = queryset.filter(team__game_id=game_id)
        
        if region:
            queryset = queryset.filter(team__region__iexact=region)
        
        if limit:
            queryset = queryset[:limit]
        
        # Process in chunks
        rankings_to_update = []
        
        for ranking in queryset.iterator(chunk_size=RANKING_CHUNK_SIZE):
            teams_processed += 1
            
            try:
                # Sanity check: CP floor
                if ranking.current_cp < MINIMUM_CP:
                    logger.warning(
                        f"Team {ranking.team.id} has negative CP ({ranking.current_cp}), resetting to 0"
                    )
                    ranking.current_cp = MINIMUM_CP
                    teams_updated += 1
                
                # Recalculate tier
                old_tier = ranking.tier
                new_tier = RankingService.calculate_tier(ranking.current_cp)
                
                if old_tier != new_tier:
                    ranking.tier = new_tier
                    tier_changes += 1
                    teams_updated += 1
                    
                    logger.debug(
                        f"Team {ranking.team.name} tier changed: {old_tier} -> {new_tier} (CP: {ranking.current_cp})"
                    )
                
                # Batch updates for efficiency
                if teams_updated > 0 and teams_processed % 100 == 0:
                    rankings_to_update.append(ranking)
                elif old_tier != new_tier or ranking.current_cp < 0:
                    rankings_to_update.append(ranking)
                
                # Bulk update every 100 records
                if len(rankings_to_update) >= 100:
                    TeamRanking.objects.bulk_update(
                        rankings_to_update,
                        ['current_cp', 'tier'],
                        batch_size=100
                    )
                    rankings_to_update = []
                
            except Exception as e:
                errors += 1
                logger.error(
                    f"Error processing team ranking {ranking.team.id}: {e}",
                    exc_info=True
                )
                # Continue processing other teams
                continue
        
        # Final bulk update
        if rankings_to_update:
            TeamRanking.objects.bulk_update(
                rankings_to_update,
                ['current_cp', 'tier'],
                batch_size=100
            )
        
        duration = (timezone.now() - start_time).total_seconds()
        
        result = {
            'teams_processed': teams_processed,
            'teams_updated': teams_updated,
            'tier_changes': tier_changes,
            'errors': errors,
            'duration_seconds': round(duration, 2)
        }
        
        logger.info(
            f"Team ranking recalculation complete: {result}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Fatal error in team ranking recalculation: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e)


# ============================================================================
# INACTIVITY DECAY
# ============================================================================

@shared_task(
    name='apps.organizations.tasks.apply_inactivity_decay',
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def apply_inactivity_decay(
    self,
    cutoff_days: int = INACTIVITY_CUTOFF_DAYS,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Apply inactivity decay to teams with no recent matches.
    
    Teams that haven't played matches in `cutoff_days` lose CP gradually:
    - 5% CP loss per week of inactivity
    - Applied incrementally (not compounded)
    - Stops at CP floor (0)
    
    Args:
        cutoff_days: Days of inactivity before decay applies (default: 7)
        limit: Optional limit for testing
    
    Returns:
        Dict with processing metrics:
        - teams_processed: Total teams checked
        - teams_decayed: Teams with decay applied
        - total_cp_lost: Sum of CP lost
        - errors: Count of errors
        - duration_seconds: Total processing time
    
    Idempotency:
        Uses last_decay_applied timestamp to prevent double-decay.
        Safe to run multiple times per day.
    
    Performance:
        - Chunks of 500 teams
        - Single query with date filtering
        - Target: <2ms per team (includes CP calculation + tier recalc)
    """
    start_time = timezone.now()
    teams_processed = 0
    teams_decayed = 0
    total_cp_lost = 0
    errors = 0
    
    cutoff_date = timezone.now() - timedelta(days=cutoff_days)
    
    logger.info(
        f"Starting inactivity decay (cutoff: {cutoff_date}, cutoff_days={cutoff_days})"
    )
    
    try:
        # Build queryset: active teams, last activity before cutoff
        queryset = TeamRanking.objects.select_related('team').filter(
            team__status='ACTIVE',
            last_activity_date__lt=cutoff_date
        ).filter(
            # Only decay if not decayed today
            last_decay_applied__isnull=True
        ) | TeamRanking.objects.select_related('team').filter(
            team__status='ACTIVE',
            last_activity_date__lt=cutoff_date,
            last_decay_applied__lt=timezone.now().date()
        )
        
        if limit:
            queryset = queryset[:limit]
        
        rankings_to_update = []
        
        for ranking in queryset.iterator(chunk_size=RANKING_CHUNK_SIZE):
            teams_processed += 1
            
            try:
                # Skip if already at minimum CP
                if ranking.current_cp <= MINIMUM_CP:
                    continue
                
                # Calculate decay
                decay_amount = int(ranking.current_cp * INACTIVITY_DECAY_RATE)
                
                if decay_amount <= 0:
                    continue  # No meaningful decay
                
                # Apply decay with floor
                old_cp = ranking.current_cp
                new_cp = max(MINIMUM_CP, ranking.current_cp - decay_amount)
                cp_lost = old_cp - new_cp
                
                if cp_lost > 0:
                    ranking.current_cp = new_cp
                    ranking.last_decay_applied = timezone.now()
                    
                    # Recalculate tier
                    old_tier = ranking.tier
                    ranking.tier = RankingService.calculate_tier(new_cp)
                    
                    teams_decayed += 1
                    total_cp_lost += cp_lost
                    
                    logger.debug(
                        f"Team {ranking.team.name} decay: {old_cp} -> {new_cp} (-{cp_lost} CP, tier: {old_tier} -> {ranking.tier})"
                    )
                    
                    rankings_to_update.append(ranking)
                    
                    # Bulk update every 100 records
                    if len(rankings_to_update) >= 100:
                        TeamRanking.objects.bulk_update(
                            rankings_to_update,
                            ['current_cp', 'tier', 'last_decay_applied'],
                            batch_size=100
                        )
                        rankings_to_update = []
                
            except Exception as e:
                errors += 1
                logger.error(
                    f"Error applying decay to team {ranking.team.id}: {e}",
                    exc_info=True
                )
                continue
        
        # Final bulk update
        if rankings_to_update:
            TeamRanking.objects.bulk_update(
                rankings_to_update,
                ['current_cp', 'tier', 'last_decay_applied'],
                batch_size=100
            )
        
        duration = (timezone.now() - start_time).total_seconds()
        
        result = {
            'teams_processed': teams_processed,
            'teams_decayed': teams_decayed,
            'total_cp_lost': total_cp_lost,
            'errors': errors,
            'duration_seconds': round(duration, 2)
        }
        
        logger.info(
            f"Inactivity decay complete: {result}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Fatal error in inactivity decay: {e}", exc_info=True)
        raise self.retry(exc=e)


# ============================================================================
# ORGANIZATION RANKING RECALCULATION
# ============================================================================

@shared_task(
    name='apps.organizations.tasks.recalculate_organization_rankings',
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def recalculate_organization_rankings(
    self,
    limit: Optional[int] = None
) -> Dict[str, Any]:
    """
    Recalculate organization rankings (empire_score).
    
    Empire Score Calculation:
    - Sum of top 3 teams' CP within the organization
    - Weighted: 1st team (1.0x), 2nd team (0.75x), 3rd team (0.5x)
    - Encourages organizations to build multiple strong teams
    
    Args:
        limit: Optional limit for testing
    
    Returns:
        Dict with processing metrics:
        - orgs_processed: Total organizations processed
        - orgs_updated: Organizations with changes
        - errors: Count of errors
        - duration_seconds: Total processing time
    
    Idempotency:
        Safe to run multiple times. Recalculates from current team CP values.
    
    Performance:
        - Prefetch team rankings per organization
        - Chunks of 200 organizations
        - Target: <10ms per organization (includes top-3 sorting)
    """
    start_time = timezone.now()
    orgs_processed = 0
    orgs_updated = 0
    errors = 0
    
    logger.info(
        f"Starting organization ranking recalculation (limit={limit})"
    )
    
    try:
        # Build queryset with prefetch
        queryset = Organization.objects.prefetch_related(
            'teams__ranking'
        ).all()
        
        if limit:
            queryset = queryset[:limit]
        
        orgs_to_update = []
        
        for org in queryset.iterator(chunk_size=200):
            orgs_processed += 1
            
            try:
                # Get top 3 teams by CP
                teams_with_cp = []
                for team in org.teams.filter(status='ACTIVE'):
                    try:
                        ranking = team.ranking
                        teams_with_cp.append((team, ranking.current_cp))
                    except TeamRanking.DoesNotExist:
                        # Team has no ranking yet
                        continue
                
                # Sort by CP descending, take top 3
                teams_with_cp.sort(key=lambda x: x[1], reverse=True)
                top_3 = teams_with_cp[:3]
                
                # Calculate empire score with weighting [1.0, 0.75, 0.5]
                weights = [1.0, 0.75, 0.5]
                empire_score = 0
                for i, (team, cp) in enumerate(top_3):
                    empire_score += int(cp * weights[i])
                
                # Get or create organization ranking
                org_ranking, created = OrganizationRanking.objects.get_or_create(
                    organization=org,
                    defaults={'empire_score': empire_score}
                )
                
                # Update if changed
                if org_ranking.empire_score != empire_score or created:
                    old_score = org_ranking.empire_score if not created else 0
                    org_ranking.empire_score = empire_score
                    org_ranking.last_calculated = timezone.now()
                    
                    orgs_updated += 1
                    
                    logger.debug(
                        f"Org {org.name} empire score: {old_score} -> {empire_score} (top 3 teams: {len(top_3)})"
                    )
                    
                    orgs_to_update.append(org_ranking)
                    
                    # Bulk update every 50 records
                    if len(orgs_to_update) >= 50:
                        OrganizationRanking.objects.bulk_update(
                            orgs_to_update,
                            ['empire_score', 'last_calculated'],
                            batch_size=50
                        )
                        orgs_to_update = []
                
            except Exception as e:
                errors += 1
                logger.error(
                    f"Error processing organization {org.id}: {e}",
                    exc_info=True
                )
                continue
        
        # Final bulk update
        if orgs_to_update:
            OrganizationRanking.objects.bulk_update(
                orgs_to_update,
                ['empire_score', 'last_calculated'],
                batch_size=50
            )
        
        duration = (timezone.now() - start_time).total_seconds()
        
        result = {
            'orgs_processed': orgs_processed,
            'orgs_updated': orgs_updated,
            'errors': errors,
            'duration_seconds': round(duration, 2)
        }
        
        logger.info(
            f"Organization ranking recalculation complete: {result}"
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Fatal error in organization ranking recalculation: {e}", exc_info=True)
        raise self.retry(exc=e)
