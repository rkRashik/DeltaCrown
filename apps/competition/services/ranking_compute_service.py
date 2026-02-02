"""
Ranking Compute Service

Phase 3A-D: Business logic for calculating team rankings.
Computes scores from verified matches and tournament participation.
"""

from typing import Dict, Optional, Tuple
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q

from apps.competition.models import (
    MatchReport,
    MatchVerification,
    GameRankingConfig,
)
from apps.competition.integrations.tournament_adapter import TournamentAdapter


class RankingComputeService:
    """Service for computing team rankings from verified matches and tournaments"""
    
    # Verification status that counts toward ranking
    VERIFIED_STATUSES = ['CONFIRMED', 'ADMIN_VERIFIED']
    
    # Confidence weight multipliers (from MatchVerification.CONFIDENCE_CHOICES)
    CONFIDENCE_WEIGHTS = {
        'HIGH': 1.0,      # 100% weight
        'MEDIUM': 0.7,    # 70% weight
        'LOW': 0.3,       # 30% weight
        'NONE': 0.0,      # 0% weight (rejected/disputed)
    }
    
    @staticmethod
    def compute_team_game_score(team, game_id: str) -> Tuple[int, Dict]:
        """
        Compute ranking score for a team in a specific game.
        
        Args:
            team: Team instance
            game_id: Game identifier (e.g., 'LOL')
            
        Returns:
            Tuple of (total_score: int, breakdown: dict)
            
        Breakdown dict contains:
            - verified_match_score: Points from verified matches
            - tournament_score: Points from tournament wins
            - decay_penalty: Points lost to inactivity
            - total_verified_matches: Count of verified matches
        """
        # Get game config
        try:
            config = GameRankingConfig.objects.get(game_id=game_id)
        except GameRankingConfig.DoesNotExist:
            return 0, {
                'error': f'No config found for game {game_id}',
                'verified_match_score': 0,
                'tournament_score': 0,
                'decay_penalty': 0,
                'total_verified_matches': 0,
            }
        
        # Extract weights from config
        weights = config.scoring_weights or {}
        verified_match_win_weight = weights.get('verified_match_win', 10)
        tournament_win_weight = weights.get('tournament_win', 500)
        
        # Calculate verified match score
        match_score, match_count = RankingComputeService._calculate_verified_match_score(
            team, game_id, verified_match_win_weight
        )
        
        # Calculate tournament score (fails gracefully if tournaments unavailable)
        tournament_score = TournamentAdapter.get_team_tournament_score(
            team, game_id, tournament_win_weight
        )
        
        # Calculate decay penalty
        decay_penalty = RankingComputeService._calculate_decay_penalty(
            team, game_id, config.decay_policy or {}
        )
        
        # Total score
        total_score = max(0, match_score + tournament_score - decay_penalty)
        
        breakdown = {
            'verified_match_score': match_score,
            'tournament_score': tournament_score,
            'decay_penalty': decay_penalty,
            'total_verified_matches': match_count,
        }
        
        return total_score, breakdown
    
    @staticmethod
    def compute_team_global_score(team) -> Tuple[int, Dict]:
        """
        Compute global ranking score across all games for a team.
        
        Args:
            team: Team instance
            
        Returns:
            Tuple of (global_score: int, breakdown: dict)
            
        Breakdown dict contains:
            - per_game: Dict[game_id, score]
            - games_played: Count of games with verified matches
            - total_verified_matches: Total across all games
        """
        # Get all active game configs
        configs = GameRankingConfig.objects.filter(is_active=True)
        
        per_game_scores = {}
        total_verified_matches = 0
        
        for config in configs:
            score, game_breakdown = RankingComputeService.compute_team_game_score(
                team, config.game_id
            )
            
            # Only include games where team has activity
            if score > 0 or game_breakdown.get('total_verified_matches', 0) > 0:
                per_game_scores[config.game_id] = score
                total_verified_matches += game_breakdown.get('total_verified_matches', 0)
        
        global_score = sum(per_game_scores.values())
        games_played = len(per_game_scores)
        
        breakdown = {
            'per_game': per_game_scores,
            'games_played': games_played,
            'total_verified_matches': total_verified_matches,
        }
        
        return global_score, breakdown
    
    @staticmethod
    def compute_confidence_level(verified_match_count: int) -> str:
        """
        Determine confidence level based on verified match count.
        
        Args:
            verified_match_count: Number of verified matches
            
        Returns:
            Confidence level: 'PROVISIONAL', 'ESTABLISHED', or 'STABLE'
        """
        if verified_match_count >= 20:
            return 'STABLE'
        elif verified_match_count >= 10:
            return 'ESTABLISHED'
        else:
            return 'PROVISIONAL'
    
    @staticmethod
    def compute_tier(score: int, tier_thresholds: Dict) -> str:
        """
        Determine tier based on score and thresholds.
        
        Args:
            score: Total ranking score
            tier_thresholds: Dict from GameRankingConfig
            
        Returns:
            Tier name: 'DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE', or 'UNRANKED'
        """
        # Default thresholds if config is empty
        default_thresholds = {
            'DIAMOND': 2000,
            'PLATINUM': 1200,
            'GOLD': 600,
            'SILVER': 250,
            'BRONZE': 100,
        }
        
        thresholds = tier_thresholds or default_thresholds
        
        # Check tiers in descending order
        for tier in ['DIAMOND', 'PLATINUM', 'GOLD', 'SILVER', 'BRONZE']:
            if score >= thresholds.get(tier, float('inf')):
                return tier
        
        return 'UNRANKED'
    
    # --- Private helper methods ---
    
    @staticmethod
    def _calculate_verified_match_score(
        team,
        game_id: str,
        win_weight: int
    ) -> Tuple[int, int]:
        """
        Calculate score from verified matches for a team in a game.
        
        Args:
            team: Team instance
            game_id: Game identifier
            win_weight: Points per verified win
            
        Returns:
            Tuple of (score: int, match_count: int)
        """
        # Query verified matches where team participated
        verified_matches = MatchReport.objects.filter(
            Q(team1=team) | Q(team2=team),
            game_id=game_id,
            verification__status__in=RankingComputeService.VERIFIED_STATUSES
        ).select_related('verification')
        
        total_score = 0
        match_count = verified_matches.count()
        
        for match in verified_matches:
            # Determine if team won
            if match.team1 == team:
                # Team1's perspective
                won = match.result == 'WIN'
            else:
                # Team2's perspective (invert result)
                won = match.result == 'LOSS'
            
            # Apply confidence weight
            confidence = match.verification.confidence_level
            weight_multiplier = RankingComputeService.CONFIDENCE_WEIGHTS.get(confidence, 0.0)
            
            if won:
                total_score += int(win_weight * weight_multiplier)
        
        return total_score, match_count
    
    @staticmethod
    def _calculate_decay_penalty(team, game_id: str, decay_policy: Dict) -> int:
        """
        Calculate decay penalty for inactive teams.
        
        Args:
            team: Team instance
            game_id: Game identifier
            decay_policy: Decay config from GameRankingConfig
            
        Returns:
            Decay penalty points (0 if decay disabled or team active)
        """
        if not decay_policy.get('enabled', False):
            return 0
        
        # Get most recent match for this team/game
        last_match = MatchReport.objects.filter(
            Q(team1=team) | Q(team2=team),
            game_id=game_id
        ).order_by('-played_at').first()
        
        if not last_match:
            return 0  # No matches, no decay
        
        # Calculate days since last match
        days_inactive = (timezone.now() - last_match.played_at).days
        threshold = decay_policy.get('inactivity_threshold_days', 30)
        
        if days_inactive < threshold:
            return 0  # Still active
        
        # Apply decay
        decay_rate = decay_policy.get('decay_rate_per_day', 0.01)  # 1% per day default
        days_over_threshold = days_inactive - threshold
        
        # Calculate decay penalty (could be % of current score or flat rate)
        # For simplicity, using flat rate here
        penalty = int(days_over_threshold * decay_rate * 100)  # Scale up for visibility
        
        return penalty
