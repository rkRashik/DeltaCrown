"""
Celery Tasks for Leaderboards (Phase F Enhanced).

Scheduled tasks for:
- Tournament ranking snapshots (half-hour intervals)
- Season/all-time snapshots (daily)
- Cold storage compaction (weekly)

Phase F Enhancements:
- Half-hour tournament snapshots (30min intervals)
- Engine V2 integration for fast computation
- Snapshot metadata (duration_ms, entries_count, source="engine_v2")
- Rank delta tracking in snapshots
"""

from celery import shared_task
from django.utils import timezone
from django.conf import settings
import logging
import time

from apps.leaderboards.services import get_leaderboard_service
from apps.leaderboards.cache import get_leaderboard_cache
from apps.leaderboards.engine import RankingEngine, invalidate_ranking_cache
from apps.leaderboards.models import LeaderboardSnapshot, LeaderboardEntry
from apps.tournaments.models import Tournament
from apps.tournaments.realtime.broadcast import broadcast_rank_update


logger = logging.getLogger(__name__)


# ============================================================================
# Phase F: Tournament Snapshot Tasks (Half-Hour Intervals)
# ============================================================================

@shared_task
def snapshot_tournament_rankings(tournament_id: int) -> dict:
    """
    Snapshot tournament rankings using Engine V2 (Phase F).
    
    Scheduled: Every 30 minutes for active tournaments
    
    Args:
        tournament_id: Tournament ID to snapshot
        
    Returns:
        Dict with snapshot metadata:
        {
            'tournament_id': int,
            'entries_count': int,
            'duration_ms': int,
            'source': 'engine_v2',
            'snapshot_id': int,
        }
        
    Steps:
        1. Check if Engine V2 is enabled
        2. Compute rankings using RankingEngine
        3. Save to LeaderboardSnapshot (JSON field)
        4. Broadcast rank deltas via WebSocket
        5. Return metadata
        
    Example Celery Beat Entry:
        'snapshot_active_tournaments': {
            'task': 'apps.leaderboards.tasks.snapshot_active_tournaments',
            'schedule': crontab(minute='*/30'),  # Every 30 minutes
        }
    """
    start_time = time.time()
    
    # Check if Engine V2 is enabled
    engine_enabled = getattr(settings, "LEADERBOARDS_ENGINE_V2_ENABLED", False)
    if not engine_enabled:
        logger.info(f"Engine V2 disabled, skipping tournament {tournament_id} snapshot")
        return {
            'tournament_id': tournament_id,
            'status': 'skipped',
            'reason': 'engine_v2_disabled',
        }
    
    # Verify tournament exists and is active
    try:
        tournament = Tournament.objects.get(id=tournament_id)
        if tournament.status not in ['registration_open', 'ongoing', 'in_progress']:
            logger.info(f"Tournament {tournament_id} not active (status={tournament.status}), skipping snapshot")
            return {
                'tournament_id': tournament_id,
                'status': 'skipped',
                'reason': f'tournament_status_{tournament.status}',
            }
    except Tournament.DoesNotExist:
        logger.error(f"Tournament {tournament_id} not found")
        return {
            'tournament_id': tournament_id,
            'status': 'error',
            'reason': 'tournament_not_found',
        }
    
    # Compute rankings using Engine V2
    engine = RankingEngine(cache_ttl=1800)  # 30-minute cache for snapshots
    response = engine.compute_tournament_rankings(tournament_id, use_cache=False)
    
    if not response.rankings:
        logger.warning(f"No rankings computed for tournament {tournament_id}")
        return {
            'tournament_id': tournament_id,
            'status': 'empty',
            'reason': 'no_rankings',
        }
    
    # Save snapshot to database
    snapshot_data = {
        "rankings": [r.to_dict() for r in response.rankings],
        "metadata": response.metadata,
    }
    
    snapshot, created = LeaderboardSnapshot.objects.update_or_create(
        leaderboard_type="tournament",
        tournament_id=tournament_id,
        snapshot_date=timezone.now().date(),
        defaults={
            "data": snapshot_data,
        }
    )
    
    # Broadcast rank deltas to spectators
    if response.deltas:
        deltas_json = [d.to_dict() for d in response.deltas]
        broadcast_rank_update(tournament_id, deltas_json)
        logger.info(f"Broadcast {len(response.deltas)} rank deltas for tournament {tournament_id}")
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        f"Snapshot complete: tournament={tournament_id}, "
        f"entries={len(response.rankings)}, duration={duration_ms}ms, "
        f"created={'new' if created else 'updated'}"
    )
    
    return {
        'tournament_id': tournament_id,
        'status': 'success',
        'entries_count': len(response.rankings),
        'delta_count': len(response.deltas),
        'duration_ms': duration_ms,
        'source': 'engine_v2',
        'snapshot_id': snapshot.id,
        'created': created,
    }


@shared_task
def snapshot_active_tournaments() -> dict:
    """
    Snapshot rankings for all active tournaments (Phase F).
    
    Scheduled: Every 30 minutes
    
    Returns:
        Dict with summary:
        {
            'processed': int,
            'success': int,
            'skipped': int,
            'errors': int,
            'total_duration_ms': int,
        }
        
    Steps:
        1. Query all active tournaments (registration_open, ongoing, in_progress)
        2. Call snapshot_tournament_rankings() for each
        3. Return aggregated results
    """
    start_time = time.time()
    
    # Query active tournaments
    # Module 9.1: Optimized query for active tournaments
    # Planning ref: PART_5.2 Section 4.4 (Query Optimization)
    active_tournaments = Tournament.objects.filter(
        status__in=['registration_open', 'ongoing', 'in_progress']
    ).select_related('game', 'organizer').values_list('id', flat=True)
    
    if not active_tournaments:
        logger.info("No active tournaments to snapshot")
        return {
            'processed': 0,
            'success': 0,
            'skipped': 0,
            'errors': 0,
            'total_duration_ms': 0,
        }
    
    logger.info(f"Snapshotting {len(active_tournaments)} active tournaments")
    
    results = {
        'processed': 0,
        'success': 0,
        'skipped': 0,
        'errors': 0,
    }
    
    for tournament_id in active_tournaments:
        result = snapshot_tournament_rankings(tournament_id)
        results['processed'] += 1
        
        if result['status'] == 'success':
            results['success'] += 1
        elif result['status'] == 'skipped':
            results['skipped'] += 1
        else:
            results['errors'] += 1
    
    duration_ms = int((time.time() - start_time) * 1000)
    results['total_duration_ms'] = duration_ms
    
    logger.info(
        f"Snapshot batch complete: {results['success']}/{results['processed']} successful, "
        f"{results['skipped']} skipped, {results['errors']} errors, {duration_ms}ms"
    )
    
    return results


# ============================================================================
# Phase F: Season/All-Time Snapshot Tasks (Daily)
# ============================================================================

@shared_task
def snapshot_season_rankings(season_id: str, game_code: str) -> dict:
    """
    Snapshot season rankings using Engine V2 (Phase F).
    
    Scheduled: Daily at 00:00 UTC
    
    Args:
        season_id: Season identifier (e.g., "2025_S1")
        game_code: Game code (e.g., "valorant", "cs2")
        
    Returns:
        Dict with snapshot metadata
        
    Steps:
        1. Compute season rankings using Engine V2
        2. Save to LeaderboardSnapshot
        3. Return metadata
    """
    start_time = time.time()
    
    engine_enabled = getattr(settings, "LEADERBOARDS_ENGINE_V2_ENABLED", False)
    if not engine_enabled:
        logger.info(f"Engine V2 disabled, skipping season {season_id}/{game_code} snapshot")
        return {
            'season_id': season_id,
            'game_code': game_code,
            'status': 'skipped',
            'reason': 'engine_v2_disabled',
        }
    
    # Compute season rankings
    engine = RankingEngine(cache_ttl=3600)
    response = engine.compute_season_rankings(season_id, game_code, use_cache=False)
    
    if not response.rankings:
        logger.warning(f"No season rankings for {season_id}/{game_code}")
        return {
            'season_id': season_id,
            'game_code': game_code,
            'status': 'empty',
            'reason': 'no_rankings',
        }
    
    # Save snapshot
    snapshot_data = {
        "rankings": [r.to_dict() for r in response.rankings],
        "metadata": response.metadata,
    }
    
    snapshot, created = LeaderboardSnapshot.objects.update_or_create(
        leaderboard_type="season",
        season=season_id,
        game=game_code,
        snapshot_date=timezone.now().date(),
        defaults={
            "data": snapshot_data,
        }
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        f"Season snapshot: {season_id}/{game_code}, "
        f"entries={len(response.rankings)}, duration={duration_ms}ms"
    )
    
    return {
        'season_id': season_id,
        'game_code': game_code,
        'status': 'success',
        'entries_count': len(response.rankings),
        'duration_ms': duration_ms,
        'source': 'engine_v2',
        'snapshot_id': snapshot.id,
        'created': created,
    }


@shared_task
def snapshot_all_time(game_code: str = None) -> dict:
    """
    Snapshot all-time rankings (Phase F).
    
    Scheduled: Daily at 00:00 UTC
    
    Args:
        game_code: Optional game filter (None = cross-game)
        
    Returns:
        Dict with snapshot metadata
        
    Note:
        All-time rankings are computed from existing snapshots,
        not live matches (too expensive).
    """
    start_time = time.time()
    
    engine_enabled = getattr(settings, "LEADERBOARDS_ENGINE_V2_ENABLED", False)
    if not engine_enabled:
        logger.info(f"Engine V2 disabled, skipping all-time snapshot")
        return {
            'game_code': game_code,
            'status': 'skipped',
            'reason': 'engine_v2_disabled',
        }
    
    # Fetch all-time rankings from existing snapshots
    engine = RankingEngine()
    response = engine.compute_all_time_rankings(game_code=game_code)
    
    if not response.rankings:
        logger.warning(f"No all-time rankings for game={game_code}")
        return {
            'game_code': game_code,
            'status': 'empty',
            'reason': 'no_rankings',
        }
    
    # Save snapshot
    snapshot_data = {
        "rankings": [r.to_dict() for r in response.rankings],
        "metadata": response.metadata,
    }
    
    snapshot, created = LeaderboardSnapshot.objects.update_or_create(
        leaderboard_type="all_time",
        game=game_code,
        snapshot_date=timezone.now().date(),
        defaults={
            "data": snapshot_data,
        }
    )
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        f"All-time snapshot: game={game_code}, "
        f"entries={len(response.rankings)}, duration={duration_ms}ms"
    )
    
    return {
        'game_code': game_code,
        'status': 'success',
        'entries_count': len(response.rankings),
        'duration_ms': duration_ms,
        'source': 'snapshot',
        'snapshot_id': snapshot.id,
        'created': created,
    }


# ============================================================================
# Phase F: Cold Storage Compaction (Weekly)
# ============================================================================

@shared_task
def compact_old_snapshots(days_threshold: int = 90) -> dict:
    """
    Compact old leaderboard snapshots into aggregated storage (Phase F).
    
    Scheduled: Weekly (Sundays at 03:00 UTC)
    
    Args:
        days_threshold: Archive snapshots older than N days (default: 90)
        
    Returns:
        Dict with compaction metadata:
        {
            'archived_count': int,
            'deleted_count': int,
            'duration_ms': int,
        }
        
    Steps:
        1. Query snapshots older than threshold
        2. For each tournament/season:
            - Keep only top 100 entries
            - Compress JSON (remove full metadata)
            - Update snapshot with compacted data
        3. Delete very old snapshots (> 1 year)
        4. Return summary
        
    Example:
        # Before compaction: 10,000 entries, 2 MB JSON
        # After compaction: 100 entries, 50 KB JSON
    """
    start_time = time.time()
    
    cutoff_date = timezone.now().date() - timezone.timedelta(days=days_threshold)
    one_year_ago = timezone.now().date() - timezone.timedelta(days=365)
    
    # Query old snapshots
    old_snapshots = LeaderboardSnapshot.objects.filter(
        snapshot_date__lt=cutoff_date,
        snapshot_date__gte=one_year_ago
    )
    
    logger.info(f"Compacting {old_snapshots.count()} snapshots older than {days_threshold} days")
    
    archived_count = 0
    
    for snapshot in old_snapshots:
        rankings = snapshot.data.get("rankings", [])
        
        if len(rankings) > 100:
            # Keep only top 100
            compacted_rankings = rankings[:100]
            
            # Remove verbose metadata
            snapshot.data = {
                "rankings": compacted_rankings,
                "metadata": {
                    "compacted": True,
                    "original_count": len(rankings),
                    "compacted_date": timezone.now().isoformat(),
                },
            }
            snapshot.save()
            archived_count += 1
    
    # Delete very old snapshots (> 1 year)
    deleted_count, _ = LeaderboardSnapshot.objects.filter(
        snapshot_date__lt=one_year_ago
    ).delete()
    
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.info(
        f"Compaction complete: {archived_count} compacted, "
        f"{deleted_count} deleted, {duration_ms}ms"
    )
    
    return {
        'archived_count': archived_count,
        'deleted_count': deleted_count,
        'duration_ms': duration_ms,
    }


# ============================================================================
# Legacy Tasks (Pre-Phase F)
# ============================================================================

@shared_task
def compute_seasonal_leaderboard(season: str):
    """
    Compute seasonal leaderboard for all players (LEGACY).
    
    Scheduled: Hourly
    
    Note: Phase F uses snapshot_season_rankings() instead.
    """
    service = get_leaderboard_service()
    cache = get_leaderboard_cache()
    
    # TODO: Implement seasonal leaderboard computation
    # (Not yet implemented in service layer)
    
    # Invalidate cache after computation
    cache.invalidate("seasonal", season=season)


@shared_task
def compute_all_time_leaderboard():
    """
    Compute all-time global leaderboard (LEGACY).
    
    Scheduled: Daily at 00:00 UTC
    
    Note: Phase F uses snapshot_all_time() instead.
    """
    service = get_leaderboard_service()
    cache = get_leaderboard_cache()
    
    # TODO: Implement all-time leaderboard computation
    
    # Invalidate cache
    cache.invalidate("all_time")


@shared_task
def compute_game_specific_leaderboard(game: str, season: str):
    """
    Compute game-specific seasonal leaderboard (LEGACY).
    
    Scheduled: Hourly
    
    Note: Phase F uses snapshot_season_rankings() instead.
    """
    service = get_leaderboard_service()
    cache = get_leaderboard_cache()
    
    # TODO: Implement game-specific leaderboard computation
    
    # Invalidate cache
    cache.invalidate("game_specific", game=game, season=season)


@shared_task
def compute_team_leaderboard():
    """
    Compute team leaderboard (cross-tournament) (LEGACY).
    
    Scheduled: Hourly
    """
    service = get_leaderboard_service()
    cache = get_leaderboard_cache()
    
    # TODO: Implement team leaderboard computation
    
    # Invalidate cache
    cache.invalidate("team")


@shared_task
def snapshot_leaderboards():
    """
    Create daily snapshots of all leaderboards (LEGACY).
    
    Scheduled: Daily at 00:00 UTC
    
    Note: Phase F uses snapshot_active_tournaments() + snapshot_season_rankings() instead.
    """
    service = get_leaderboard_service()
    service.snapshot_leaderboards()


@shared_task
def mark_inactive_players():
    """
    Mark players as inactive if no activity in last 30 days.
    
    Scheduled: Daily at 02:00 UTC
    
    Sets is_active=False for players with no recent tournament participation.
    """
    service = get_leaderboard_service()
    service.mark_inactive_players(days_threshold=30)


# ============================================================================
# Celery Beat Schedule Configuration (Phase F)
# ============================================================================

# Add to settings.py:
"""
CELERY_BEAT_SCHEDULE = {
    # Phase F: Half-hour tournament snapshots
    'snapshot_active_tournaments': {
        'task': 'apps.leaderboards.tasks.snapshot_active_tournaments',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes
    },
    
    # Phase F: Daily season snapshots (one per game)
    'snapshot_season_valorant': {
        'task': 'apps.leaderboards.tasks.snapshot_season_rankings',
        'schedule': crontab(hour=0, minute=0),  # Daily at 00:00 UTC
        'args': ['2025_S1', 'valorant'],
    },
    'snapshot_season_cs2': {
        'task': 'apps.leaderboards.tasks.snapshot_season_rankings',
        'schedule': crontab(hour=0, minute=5),  # Daily at 00:05 UTC
        'args': ['2025_S1', 'cs2'],
    },
    'snapshot_season_efootball': {
        'task': 'apps.leaderboards.tasks.snapshot_season_rankings',
        'schedule': crontab(hour=0, minute=10),  # Daily at 00:10 UTC
        'args': ['2025_S1', 'efootball'],
    },
    
    # Phase F: Daily all-time snapshots
    'snapshot_all_time_global': {
        'task': 'apps.leaderboards.tasks.snapshot_all_time',
        'schedule': crontab(hour=0, minute=30),  # Daily at 00:30 UTC
        'args': [None],  # Cross-game
    },
    'snapshot_all_time_valorant': {
        'task': 'apps.leaderboards.tasks.snapshot_all_time',
        'schedule': crontab(hour=0, minute=35),  # Daily at 00:35 UTC
        'args': ['valorant'],
    },
    
    # Phase F: Weekly cold storage compaction
    'compact_old_snapshots': {
        'task': 'apps.leaderboards.tasks.compact_old_snapshots',
        'schedule': crontab(hour=3, minute=0, day_of_week=0),  # Sundays at 03:00 UTC
        'args': [90],  # 90 days threshold
    },
    
    # Legacy tasks (preserved for backward compatibility)
    'mark_inactive_players': {
        'task': 'apps.leaderboards.tasks.mark_inactive_players',
        'schedule': crontab(hour=2, minute=0),  # Daily at 02:00 UTC
    },
    
    # ========================================================================
    # Phase 8, Epic 8.5: Advanced Analytics Background Jobs
    # ========================================================================
    
    'nightly_user_analytics_refresh': {
        'task': 'apps.leaderboards.tasks.nightly_user_analytics_refresh',
        'schedule': crontab(hour=1, minute=0),  # Daily at 01:00 UTC
    },
    'nightly_team_analytics_refresh': {
        'task': 'apps.leaderboards.tasks.nightly_team_analytics_refresh',
        'schedule': crontab(hour=1, minute=30),  # Daily at 01:30 UTC
    },
    'hourly_leaderboard_refresh': {
        'task': 'apps.leaderboards.tasks.hourly_leaderboard_refresh',
        'schedule': crontab(minute=0),  # Every hour at :00
    },
    'seasonal_rollover': {
        'task': 'apps.leaderboards.tasks.seasonal_rollover',
        'schedule': crontab(hour=0, minute=0, day_of_month=1),  # First of month at 00:00 UTC
    },
}
"""


# ============================================================================
# Phase 8, Epic 8.5: Analytics Background Jobs
# ============================================================================

@shared_task
def nightly_user_analytics_refresh() -> dict:
    """
    Refresh user analytics snapshots for all users (nightly job).
    
    Scheduled: Daily at 01:00 UTC
    
    Computes:
    - MMR/ELO snapshots
    - Win rates (overall + rolling 7d/30d)
    - KDA ratios
    - Match volume metrics
    - Streak detection
    - Tier assignment
    - Percentile ranking
    
    Returns:
        Dict with job metadata:
        {
            'users_refreshed': int,
            'duration_ms': int,
            'errors': int,
        }
    """
    from apps.common.events.event_bus import EventBus
    
    start_time = time.time()
    event_bus = EventBus()
    
    # Emit job started event
    event_bus.publish(
        event_type="analytics.job_started",
        payload={"job_type": "user_analytics_refresh", "timestamp": timezone.now().isoformat()}
    )
    
    try:
        # Get all games (would use game adapter in real implementation)
        games = ["valorant", "csgo", "lol"]  # Hardcoded for now
        
        users_refreshed = 0
        errors = 0
        
        # Refresh analytics for each game
        for game_slug in games:
            try:
                # Get all users with stats for this game
                from apps.leaderboards.models import UserStats
                user_stats_queryset = UserStats.objects.filter(game_slug=game_slug)
                
                logger.info(f"Refreshing user analytics for {user_stats_queryset.count()} users in {game_slug}")
                
                # Batch process users
                for user_stats in user_stats_queryset:
                    try:
                        # Initialize analytics service
                        from apps.tournament_ops.services.analytics_engine_service import AnalyticsEngineService
                        from apps.tournament_ops.adapters import (
                            AnalyticsAdapter,
                            UserStatsAdapter,
                            TeamStatsAdapter,
                            TeamRankingAdapter,
                            DjangoMatchHistoryAdapter,
                        )
                        
                        analytics_service = AnalyticsEngineService(
                            analytics_adapter=AnalyticsAdapter(),
                            user_stats_adapter=UserStatsAdapter(),
                            team_stats_adapter=TeamStatsAdapter(),
                            team_ranking_adapter=TeamRankingAdapter(),
                            match_history_adapter=DjangoMatchHistoryAdapter(),
                        )
                        
                        # Compute and save analytics
                        analytics_service.compute_user_analytics(user_stats.user_id, game_slug)
                        users_refreshed += 1
                        
                    except Exception as e:
                        logger.error(f"Error refreshing analytics for user {user_stats.user_id} in {game_slug}: {e}")
                        errors += 1
                        
            except Exception as e:
                logger.error(f"Error processing game {game_slug}: {e}")
                errors += 1
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Emit job completed event
        event_bus.publish(
            event_type="analytics.job_completed",
            payload={
                "job_type": "user_analytics_refresh",
                "users_refreshed": users_refreshed,
                "duration_ms": duration_ms,
                "errors": errors,
            }
        )
        
        logger.info(f"User analytics refresh completed: {users_refreshed} users, {errors} errors, {duration_ms}ms")
        
        return {
            'users_refreshed': users_refreshed,
            'duration_ms': duration_ms,
            'errors': errors,
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Emit job failed event
        event_bus.publish(
            event_type="analytics.job_failed",
            payload={
                "job_type": "user_analytics_refresh",
                "error": str(e),
                "duration_ms": duration_ms,
            }
        )
        
        logger.error(f"User analytics refresh failed: {e}")
        raise


@shared_task
def nightly_team_analytics_refresh() -> dict:
    """
    Refresh team analytics snapshots for all teams (nightly job).
    
    Scheduled: Daily at 01:30 UTC
    
    Computes:
    - Team ELO snapshots + volatility
    - Average member skill
    - Win rates (overall + rolling 7d/30d)
    - Synergy score
    - Activity score
    - Tier assignment
    - Percentile ranking
    
    Returns:
        Dict with job metadata:
        {
            'teams_refreshed': int,
            'duration_ms': int,
            'errors': int,
        }
    """
    from apps.common.events.event_bus import EventBus
    
    start_time = time.time()
    event_bus = EventBus()
    
    # Emit job started event
    event_bus.publish(
        event_type="analytics.job_started",
        payload={"job_type": "team_analytics_refresh", "timestamp": timezone.now().isoformat()}
    )
    
    try:
        # Get all games
        games = ["valorant", "csgo", "lol"]
        
        teams_refreshed = 0
        errors = 0
        
        # Refresh analytics for each game
        for game_slug in games:
            try:
                # Get all teams with stats for this game
                from apps.leaderboards.models import TeamStats
                team_stats_queryset = TeamStats.objects.filter(game_slug=game_slug)
                
                logger.info(f"Refreshing team analytics for {team_stats_queryset.count()} teams in {game_slug}")
                
                # Batch process teams
                for team_stats in team_stats_queryset:
                    try:
                        # Initialize analytics service
                        from apps.tournament_ops.services.analytics_engine_service import AnalyticsEngineService
                        from apps.tournament_ops.adapters import (
                            AnalyticsAdapter,
                            UserStatsAdapter,
                            TeamStatsAdapter,
                            TeamRankingAdapter,
                            DjangoMatchHistoryAdapter,
                        )
                        
                        analytics_service = AnalyticsEngineService(
                            analytics_adapter=AnalyticsAdapter(),
                            user_stats_adapter=UserStatsAdapter(),
                            team_stats_adapter=TeamStatsAdapter(),
                            team_ranking_adapter=TeamRankingAdapter(),
                            match_history_adapter=DjangoMatchHistoryAdapter(),
                        )
                        
                        # Compute and save analytics
                        analytics_service.compute_team_analytics(team_stats.team_id, game_slug)
                        teams_refreshed += 1
                        
                    except Exception as e:
                        logger.error(f"Error refreshing analytics for team {team_stats.team_id} in {game_slug}: {e}")
                        errors += 1
                        
            except Exception as e:
                logger.error(f"Error processing game {game_slug}: {e}")
                errors += 1
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Emit job completed event
        event_bus.publish(
            event_type="analytics.job_completed",
            payload={
                "job_type": "team_analytics_refresh",
                "teams_refreshed": teams_refreshed,
                "duration_ms": duration_ms,
                "errors": errors,
            }
        )
        
        logger.info(f"Team analytics refresh completed: {teams_refreshed} teams, {errors} errors, {duration_ms}ms")
        
        return {
            'teams_refreshed': teams_refreshed,
            'duration_ms': duration_ms,
            'errors': errors,
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Emit job failed event
        event_bus.publish(
            event_type="analytics.job_failed",
            payload={
                "job_type": "team_analytics_refresh",
                "error": str(e),
                "duration_ms": duration_ms,
            }
        )
        
        logger.error(f"Team analytics refresh failed: {e}")
        raise


@shared_task
def hourly_leaderboard_refresh() -> dict:
    """
    Refresh all leaderboards (hourly job).
    
    Scheduled: Every hour at :00
    
    Refreshes:
    - Game-specific user leaderboards (per game)
    - Team leaderboards (per game)
    - Global user leaderboard (cross-game)
    - MMR/ELO leaderboards
    - Tier leaderboards
    
    Returns:
        Dict with job metadata:
        {
            'leaderboards_refreshed': dict,  # Mapping leaderboard type to entry count
            'duration_ms': int,
            'errors': int,
        }
    """
    from apps.common.events.event_bus import EventBus
    
    start_time = time.time()
    event_bus = EventBus()
    
    # Emit job started event
    event_bus.publish(
        event_type="analytics.job_started",
        payload={"job_type": "leaderboard_refresh", "timestamp": timezone.now().isoformat()}
    )
    
    try:
        # Initialize analytics service
        from apps.tournament_ops.services.analytics_engine_service import AnalyticsEngineService
        from apps.tournament_ops.adapters import (
            AnalyticsAdapter,
            UserStatsAdapter,
            TeamStatsAdapter,
            TeamRankingAdapter,
            DjangoMatchHistoryAdapter,
        )
        
        analytics_service = AnalyticsEngineService(
            analytics_adapter=AnalyticsAdapter(),
            user_stats_adapter=UserStatsAdapter(),
            team_stats_adapter=TeamStatsAdapter(),
            team_ranking_adapter=TeamRankingAdapter(),
            match_history_adapter=DjangoMatchHistoryAdapter(),
        )
        
        # Refresh all leaderboards
        results = analytics_service.refresh_all_leaderboards()
        
        duration_ms = int((time.time() - start_time) * 1000)
        total_entries = sum(results.values())
        
        # Emit job completed event
        event_bus.publish(
            event_type="analytics.job_completed",
            payload={
                "job_type": "leaderboard_refresh",
                "leaderboards_refreshed": results,
                "total_entries": total_entries,
                "duration_ms": duration_ms,
            }
        )
        
        logger.info(f"Leaderboard refresh completed: {len(results)} leaderboards, {total_entries} total entries, {duration_ms}ms")
        
        return {
            'leaderboards_refreshed': results,
            'duration_ms': duration_ms,
            'errors': 0,
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Emit job failed event
        event_bus.publish(
            event_type="analytics.job_failed",
            payload={
                "job_type": "leaderboard_refresh",
                "error": str(e),
                "duration_ms": duration_ms,
            }
        )
        
        logger.error(f"Leaderboard refresh failed: {e}")
        raise


@shared_task
def seasonal_rollover() -> dict:
    """
    Perform seasonal rollover (monthly job).
    
    Scheduled: First of month at 00:00 UTC
    
    Performs:
    - Deactivate expired seasons
    - Activate new seasons
    - Archive previous season leaderboards
    - Reset seasonal rankings (if configured)
    
    Returns:
        Dict with job metadata:
        {
            'seasons_deactivated': int,
            'seasons_activated': int,
            'duration_ms': int,
        }
    """
    from apps.common.events.event_bus import EventBus
    from apps.leaderboards.models import Season
    
    start_time = time.time()
    event_bus = EventBus()
    
    # Emit job started event
    event_bus.publish(
        event_type="analytics.job_started",
        payload={"job_type": "seasonal_rollover", "timestamp": timezone.now().isoformat()}
    )
    
    try:
        now = timezone.now()
        seasons_deactivated = 0
        seasons_activated = 0
        
        # Deactivate expired seasons
        expired_seasons = Season.objects.filter(is_active=True, end_date__lt=now)
        for season in expired_seasons:
            season.is_active = False
            season.save(update_fields=['is_active'])
            seasons_deactivated += 1
            logger.info(f"Deactivated expired season: {season.season_id}")
            
            # Emit season changed event
            event_bus.publish(
                event_type="season.changed",
                payload={
                    "season_id": season.season_id,
                    "action": "deactivated",
                    "timestamp": now.isoformat(),
                }
            )
        
        # Activate new seasons
        new_seasons = Season.objects.filter(is_active=False, start_date__lte=now, end_date__gt=now)
        for season in new_seasons:
            season.is_active = True
            season.save(update_fields=['is_active'])
            seasons_activated += 1
            logger.info(f"Activated new season: {season.season_id}")
            
            # Emit season changed event
            event_bus.publish(
                event_type="season.changed",
                payload={
                    "season_id": season.season_id,
                    "action": "activated",
                    "timestamp": now.isoformat(),
                }
            )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Emit job completed event
        event_bus.publish(
            event_type="analytics.job_completed",
            payload={
                "job_type": "seasonal_rollover",
                "seasons_deactivated": seasons_deactivated,
                "seasons_activated": seasons_activated,
                "duration_ms": duration_ms,
            }
        )
        
        logger.info(f"Seasonal rollover completed: {seasons_deactivated} deactivated, {seasons_activated} activated, {duration_ms}ms")
        
        return {
            'seasons_deactivated': seasons_deactivated,
            'seasons_activated': seasons_activated,
            'duration_ms': duration_ms,
        }
        
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Emit job failed event
        event_bus.publish(
            event_type="analytics.job_failed",
            payload={
                "job_type": "seasonal_rollover",
                "error": str(e),
                "duration_ms": duration_ms,
            }
        )
        
        logger.error(f"Seasonal rollover failed: {e}")
        raise
