"""
Snapshot Service

Phase 3A-D: Business logic for creating and updating ranking snapshots.
Updates TeamGameRankingSnapshot and TeamGlobalRankingSnapshot records.
"""

from typing import Optional
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Max

from apps.competition.models import (
    MatchReport,
    TeamGameRankingSnapshot,
    TeamGlobalRankingSnapshot,
    GameRankingConfig,
)
from apps.competition.services.ranking_compute_service import RankingComputeService


class SnapshotService:
    """Service for updating ranking snapshots"""
    
    @staticmethod
    def update_team_game_snapshot(team, game_id: str) -> TeamGameRankingSnapshot:
        """
        Create or update ranking snapshot for a team in a specific game.
        
        Args:
            team: Team instance
            game_id: Game identifier (e.g., 'LOL')
            
        Returns:
            Updated TeamGameRankingSnapshot instance
            
        Raises:
            ValueError: If game_id invalid
        """
        # Validate game exists
        try:
            config = GameRankingConfig.objects.get(game_id=game_id)
        except GameRankingConfig.DoesNotExist:
            raise ValueError(f"Invalid game_id: {game_id}")
        
        # Compute scores
        score, breakdown = RankingComputeService.compute_team_game_score(team, game_id)
        verified_match_count = breakdown.get('total_verified_matches', 0)
        
        # Determine tier
        tier = RankingComputeService.compute_tier(score, config.tier_thresholds)
        
        # Determine confidence level
        confidence_level = RankingComputeService.compute_confidence_level(verified_match_count)
        
        # Get last match date
        last_match = MatchReport.objects.filter(
            Q(team1=team) | Q(team2=team),
            game_id=game_id
        ).order_by('-played_at').first()
        
        last_match_at = last_match.played_at if last_match else None
        
        # Calculate rank (position among all teams for this game)
        # This is expensive, so we'll defer precise rank calculation
        # For now, use None and calculate in batch later
        rank = None
        percentile = 0.0
        
        # Create or update snapshot
        with transaction.atomic():
            snapshot, created = TeamGameRankingSnapshot.objects.update_or_create(
                team=team,
                game_id=game_id,
                defaults={
                    'score': score,
                    'tier': tier,
                    'rank': rank,
                    'percentile': percentile,
                    'verified_match_count': verified_match_count,
                    'confidence_level': confidence_level,
                    'breakdown': breakdown,
                    'last_match_at': last_match_at,
                    'snapshot_date': timezone.now(),
                }
            )
        
        return snapshot
    
    @staticmethod
    def update_team_global_snapshot(team) -> TeamGlobalRankingSnapshot:
        """
        Create or update global ranking snapshot for a team (across all games).
        
        Args:
            team: Team instance
            
        Returns:
            Updated TeamGlobalRankingSnapshot instance
        """
        # Compute global score
        global_score, breakdown = RankingComputeService.compute_team_global_score(team)
        
        per_game_scores = breakdown.get('per_game', {})
        games_played = breakdown.get('games_played', 0)
        
        # Determine global tier (use same tier thresholds as games)
        # For simplicity, using first config's thresholds
        first_config = GameRankingConfig.objects.filter(is_active=True).first()
        tier_thresholds = first_config.tier_thresholds if first_config else {}
        global_tier = RankingComputeService.compute_tier(global_score, tier_thresholds)
        
        # Calculate global rank (defer to batch calculation)
        global_rank = None
        
        # Create or update snapshot
        with transaction.atomic():
            snapshot, created = TeamGlobalRankingSnapshot.objects.update_or_create(
                team=team,
                defaults={
                    'global_score': global_score,
                    'global_tier': global_tier,
                    'global_rank': global_rank,
                    'games_played': games_played,
                    'game_contributions': per_game_scores,
                    'snapshot_date': timezone.now(),
                }
            )
        
        return snapshot
    
    @staticmethod
    def update_all_snapshots(game_id: Optional[str] = None):
        """
        Batch update snapshots for all teams.
        
        This is intended for periodic recalculation (e.g., daily cron job)
        or initial bootstrap (compute_initial_rankings command).
        
        Args:
            game_id: Optional game filter. If provided, only update this game.
                    If None, update all games and global snapshots.
        """
        from apps.organizations.models import Team
        
        # Get all active teams (teams with at least one member)
        teams = Team.objects.filter(
            status='ACTIVE'
        ).distinct()
        
        if game_id:
            # Update single game snapshots only
            for team in teams:
                try:
                    SnapshotService.update_team_game_snapshot(team, game_id)
                except Exception as e:
                    # Log error but continue (don't fail entire batch)
                    print(f"Error updating {team.slug}/{game_id}: {e}")
        else:
            # Update all games + global for each team
            configs = GameRankingConfig.objects.filter(is_active=True)
            
            for team in teams:
                # Update per-game snapshots
                for config in configs:
                    try:
                        SnapshotService.update_team_game_snapshot(team, config.game_id)
                    except Exception as e:
                        print(f"Error updating {team.slug}/{config.game_id}: {e}")
                
                # Update global snapshot
                try:
                    SnapshotService.update_team_global_snapshot(team)
                except Exception as e:
                    print(f"Error updating global for {team.slug}: {e}")
        
        # After all snapshots updated, recalculate ranks
        SnapshotService._recalculate_ranks(game_id)
    
    @staticmethod
    def _recalculate_ranks(game_id: Optional[str] = None):
        """
        Recalculate rank positions after batch snapshot updates.
        
        Ranks are calculated by ordering snapshots by score (descending)
        and assigning positions.
        
        Args:
            game_id: Optional game filter. If None, recalculate all games + global.
        """
        if game_id:
            # Recalculate ranks for single game
            snapshots = TeamGameRankingSnapshot.objects.filter(
                game_id=game_id
            ).order_by('-score', 'team__slug')
            
            for idx, snapshot in enumerate(snapshots, start=1):
                snapshot.rank = idx
                # Calculate percentile (100 = top, 0 = bottom)
                total_count = snapshots.count()
                snapshot.percentile = ((total_count - idx + 1) / total_count) * 100 if total_count > 0 else 0
                snapshot.save(update_fields=['rank', 'percentile'])
        else:
            # Recalculate ranks for all games
            configs = GameRankingConfig.objects.filter(is_active=True)
            for config in configs:
                SnapshotService._recalculate_ranks(config.game_id)
            
            # Recalculate global ranks
            global_snapshots = TeamGlobalRankingSnapshot.objects.all().order_by(
                '-global_score', 'team__slug'
            )
            
            total_count = global_snapshots.count()
            for idx, snapshot in enumerate(global_snapshots, start=1):
                snapshot.global_rank = idx
                snapshot.save(update_fields=['global_rank'])
