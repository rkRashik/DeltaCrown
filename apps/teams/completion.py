"""
Team Completion Progress System
Calculates team profile completion percentage and provides actionable prompts
"""
from typing import Dict, List, Tuple
from .models import Team, TeamMembership


class TeamCompletionCalculator:
    """
    Calculate team profile completion based on various criteria.
    
    Completion Categories:
    - Basic Info (20%): Name, Tag, Game, Region, Description
    - Branding (20%): Logo and Banner
    - Roster (30%): Has active members with game IDs
    - Social Links (15%): At least 2 social links
    - Captain Game ID (15%): Captain has game ID set
    """
    
    # Weight distribution
    WEIGHTS = {
        'basic_info': 20,
        'branding': 20,
        'roster': 30,
        'social': 15,
        'captain_game_id': 15,
    }
    
    def __init__(self, team: Team, captain_profile=None):
        self.team = team
        self.captain_profile = captain_profile or team.captain
        
    def calculate_completion(self) -> Dict:
        """
        Calculate overall completion percentage and breakdown.
        
        Returns:
            {
                'percentage': int,  # 0-100
                'breakdown': {...},  # Category scores
                'missing': [...],  # List of missing items
                'suggestions': [...],  # Action suggestions
            }
        """
        scores = {}
        missing = []
        suggestions = []
        
        # 1. Basic Info (20%)
        basic_score, basic_missing = self._check_basic_info()
        scores['basic_info'] = basic_score
        missing.extend(basic_missing)
        if basic_missing:
            suggestions.append({
                'title': 'Complete Basic Information',
                'description': f'Add {", ".join(basic_missing)} to improve team profile',
                'action': 'Edit team settings',
                'url': f'/teams/{self.team.slug}/settings/',
                'priority': 'high',
                'icon': 'info-circle'
            })
        
        # 2. Branding (20%)
        branding_score, branding_missing = self._check_branding()
        scores['branding'] = branding_score
        missing.extend(branding_missing)
        if branding_missing:
            suggestions.append({
                'title': 'Add Team Branding',
                'description': f'Upload {" and ".join(branding_missing)} for better visibility',
                'action': 'Upload branding',
                'url': f'/teams/{self.team.slug}/settings/',
                'priority': 'medium',
                'icon': 'image'
            })
        
        # 3. Roster (30%)
        roster_score, roster_missing = self._check_roster()
        scores['roster'] = roster_score
        missing.extend(roster_missing)
        if roster_missing:
            suggestions.append({
                'title': 'Build Your Roster',
                'description': roster_missing[0],  # First item is the message
                'action': 'Invite members',
                'url': f'/teams/{self.team.slug}/dashboard/#roster',
                'priority': 'high',
                'icon': 'users'
            })
        
        # 4. Social Links (15%)
        social_score, social_missing = self._check_social()
        scores['social'] = social_score
        missing.extend(social_missing)
        if social_missing:
            suggestions.append({
                'title': 'Connect Social Media',
                'description': 'Add social links to grow your community',
                'action': 'Add social links',
                'url': f'/teams/{self.team.slug}/settings/',
                'priority': 'low',
                'icon': 'share-alt'
            })
        
        # 5. Captain Game ID (15%)
        captain_score, captain_missing = self._check_captain_game_id()
        scores['captain_game_id'] = captain_score
        missing.extend(captain_missing)
        if captain_missing:
            suggestions.append({
                'title': 'Set Your Game ID',
                'description': f'Add your {self.team.game.upper()} game ID to lead your team',
                'action': 'Add game ID',
                'url': '/profile/edit/#game-ids',
                'priority': 'high',
                'icon': 'gamepad'
            })
        
        # Calculate weighted total
        total_percentage = sum(
            (score / 100) * self.WEIGHTS[category]
            for category, score in scores.items()
        )
        
        return {
            'percentage': int(total_percentage),
            'breakdown': scores,
            'missing': missing,
            'suggestions': suggestions,
            'is_complete': total_percentage >= 100,
            'next_milestone': self._get_next_milestone(total_percentage),
        }
    
    def _check_basic_info(self) -> Tuple[int, List[str]]:
        """
        Check basic info completion.
        Required: Name (auto), Tag (auto), Game (auto), Region, Description
        """
        score = 60  # Name, Tag, Game are always present
        missing = []
        
        # Region (20%)
        if self.team.region and self.team.region.strip():
            score += 20
        else:
            missing.append('region')
        
        # Description (20%)
        if self.team.description and len(self.team.description.strip()) >= 20:
            score += 20
        else:
            missing.append('detailed description')
        
        return score, missing
    
    def _check_branding(self) -> Tuple[int, List[str]]:
        """Check branding assets: logo and banner."""
        score = 0
        missing = []
        
        # Logo (50%)
        if self.team.logo:
            score += 50
        else:
            missing.append('team logo')
        
        # Banner (50%)
        if self.team.banner_image:
            score += 50
        else:
            missing.append('team banner')
        
        return score, missing
    
    def _check_roster(self) -> Tuple[int, List[str]]:
        """
        Check roster completion.
        - Has at least 1 member besides captain (40%)
        - Meets minimum roster size for game (60%)
        """
        score = 0
        missing = []
        
        # Get active members
        members_count = TeamMembership.objects.filter(
            team=self.team,
            status='ACTIVE'
        ).count()
        
        # At least 2 members total (captain + 1)
        if members_count >= 2:
            score += 40
        else:
            missing.append(f'Need at least 1 more member')
        
        # Check game-specific minimum
        from .game_config import get_game_config
        game_config = get_game_config(self.team.game)
        
        if game_config and members_count >= game_config.min_starters:
            score += 60
        else:
            min_needed = game_config.min_starters if game_config else 5
            missing.append(f'Need {min_needed - members_count} more members for {self.team.game.upper()}')
        
        return score, missing
    
    def _check_social(self) -> Tuple[int, List[str]]:
        """Check social media links. Need at least 2 for full score."""
        social_fields = [
            'twitter', 'instagram', 'discord', 
            'youtube', 'twitch', 'linktree'
        ]
        
        links_count = sum(
            1 for field in social_fields
            if getattr(self.team, field, None) and getattr(self.team, field).strip()
        )
        
        if links_count >= 2:
            score = 100
            missing = []
        elif links_count == 1:
            score = 50
            missing = [f'Add {2 - links_count} more social link']
        else:
            score = 0
            missing = ['Add at least 2 social links']
        
        return score, missing
    
    def _check_captain_game_id(self) -> Tuple[int, List[str]]:
        """Check if captain has game ID set for team's game."""
        if not self.captain_profile:
            return 0, ['Captain profile not found']
        
        from apps.user_profile.services.game_passport_service import GamePassportService
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            user = User.objects.get(id=self.captain_profile.user_id)
            passport = GamePassportService.get_passport(user, self.team.game)
            game_id = passport.in_game_name if passport else None
        except Exception:
            game_id = None
        
        if game_id:
            if game_id:
                return 100, []
        
        return 0, [f'{self.team.game.upper()} game ID']
    
    def _get_next_milestone(self, current_percentage: float) -> Dict:
        """Get next completion milestone."""
        milestones = [
            {'threshold': 40, 'title': 'Getting Started', 'icon': 'flag'},
            {'threshold': 60, 'title': 'Well Established', 'icon': 'check'},
            {'threshold': 80, 'title': 'Almost There', 'icon': 'star'},
            {'threshold': 100, 'title': 'Fully Complete', 'icon': 'trophy'},
        ]
        
        for milestone in milestones:
            if current_percentage < milestone['threshold']:
                return {
                    'percentage': milestone['threshold'],
                    'title': milestone['title'],
                    'icon': milestone['icon'],
                    'remaining': milestone['threshold'] - current_percentage,
                }
        
        return {
            'percentage': 100,
            'title': 'Fully Complete',
            'icon': 'trophy',
            'remaining': 0,
        }


def get_team_completion(team: Team, captain_profile=None) -> Dict:
    """
    Convenience function to get team completion data.
    
    Usage:
        completion = get_team_completion(team, captain_profile)
        print(f"Team is {completion['percentage']}% complete")
    """
    calculator = TeamCompletionCalculator(team, captain_profile)
    return calculator.calculate_completion()
