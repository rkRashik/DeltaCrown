# apps/user_profile/services/xp_service.py
"""
XP and Badge Awarding Service

Handles:
- XP calculation and awarding
- Level progression
- Badge criteria checking
- Badge awarding with progress tracking
"""
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class XPService:
    """Central service for XP and badge management"""
    
    # XP thresholds for each level (exponential growth)
    # Level 1: 0 XP
    # Level 2: 100 XP
    # Level 3: 250 XP (+150)
    # Level 4: 500 XP (+250)
    # Level 5: 850 XP (+350)
    # Level 10: 4,500 XP
    # Level 25: 30,000 XP
    # Level 50: 125,000 XP
    # Level 100: 500,000 XP
    
    @staticmethod
    def xp_for_level(level):
        """Calculate total XP required for a given level"""
        if level <= 1:
            return 0
        # Exponential formula: XP = 50 * (level^2) - 50
        return int(50 * (level ** 2) - 50)
    
    @staticmethod
    def level_for_xp(xp):
        """Calculate level from total XP"""
        level = 1
        while XPService.xp_for_level(level + 1) <= xp:
            level += 1
        return level
    
    @staticmethod
    def xp_to_next_level(current_xp, current_level):
        """Calculate XP needed for next level"""
        next_level_xp = XPService.xp_for_level(current_level + 1)
        return max(0, next_level_xp - current_xp)
    
    @staticmethod
    @transaction.atomic
    def award_xp(user, amount, reason='', context=None):
        """
        Award XP to a user and check for level-ups
        
        Args:
            user: User instance or user ID
            amount: XP amount to award (positive integer)
            reason: String description of why XP was awarded
            context: Optional dict with additional metadata
        
        Returns:
            dict with keys: xp_awarded, new_total, old_level, new_level, leveled_up
        """
        if isinstance(user, int):
            user = User.objects.get(pk=user)
        
        profile = user.profile
        old_xp = profile.xp
        old_level = profile.level
        
        # Award XP
        profile.xp += amount
        new_xp = profile.xp
        
        # Check for level-up
        new_level = XPService.level_for_xp(new_xp)
        leveled_up = new_level > old_level
        
        if leveled_up:
            profile.level = new_level
            logger.info(
                f"User {user.username} leveled up: {old_level} → {new_level} "
                f"(+{amount} XP from {reason})"
            )
            
            # Check for level milestone badges
            XPService._check_level_badges(user, new_level)
        
        profile.save(update_fields=['xp', 'level', 'updated_at'])
        
        logger.info(
            f"Awarded {amount} XP to {user.username} for {reason} "
            f"(Total: {new_xp} XP, Level {new_level})"
        )
        
        return {
            'xp_awarded': amount,
            'new_total': new_xp,
            'old_level': old_level,
            'new_level': new_level,
            'leveled_up': leveled_up
        }
    
    @staticmethod
    def _check_level_badges(user, level):
        """Check and award level milestone badges"""
        from apps.user_profile.models import Badge
        
        level_badges = {
            10: 'level-10',
            25: 'level-25',
            50: 'level-50',
            100: 'level-100'
        }
        
        if level in level_badges:
            try:
                badge = Badge.objects.get(slug=level_badges[level], is_active=True)
                XPService.award_badge(
                    user,
                    badge,
                    context={'level_reached': level}
                )
            except Badge.DoesNotExist:
                logger.warning(f"Level {level} badge not found")
    
    @staticmethod
    @transaction.atomic
    def award_badge(user, badge, context=None):
        """
        Award a badge to a user
        
        Args:
            user: User instance or user ID
            badge: Badge instance or badge slug
            context: Optional dict with metadata about earning context
        
        Returns:
            UserBadge instance or None if already earned
        """
        from apps.user_profile.models import Badge, UserBadge
        
        if isinstance(user, int):
            user = User.objects.get(pk=user)
        
        if isinstance(badge, str):
            try:
                badge = Badge.objects.get(slug=badge, is_active=True)
            except Badge.DoesNotExist:
                logger.error(f"Badge '{badge}' not found or inactive")
                return None
        
        # Check if user already has this badge
        existing = UserBadge.objects.filter(user=user, badge=badge).first()
        if existing:
            logger.info(f"User {user.username} already has badge {badge.name}")
            return existing
        
        # Create UserBadge
        user_badge = UserBadge.objects.create(
            user=user,
            badge=badge,
            context=context or {},
            progress={'current': 100, 'required': 100}  # Mark as complete
        )
        
        # Award badge XP reward
        if badge.xp_reward > 0:
            XPService.award_xp(
                user,
                badge.xp_reward,
                reason=f"Earned badge: {badge.name}",
                context={'badge_id': badge.id}
            )
        
        logger.info(
            f"User {user.username} earned badge {badge.icon} {badge.name} "
            f"(+{badge.xp_reward} XP)"
        )
        
        return user_badge
    
    @staticmethod
    def update_badge_progress(user, badge_slug, current, required):
        """
        Update progress on an incremental badge
        
        Args:
            user: User instance
            badge_slug: Badge slug
            current: Current progress value
            required: Required value for completion
        
        Returns:
            UserBadge instance (earned if completed)
        """
        from apps.user_profile.models import Badge, UserBadge
        
        try:
            badge = Badge.objects.get(slug=badge_slug, is_active=True)
        except Badge.DoesNotExist:
            logger.error(f"Badge '{badge_slug}' not found")
            return None
        
        # Check if already earned
        user_badge = UserBadge.objects.filter(user=user, badge=badge).first()
        
        if current >= required:
            # Badge complete - award if not already earned
            if not user_badge:
                return XPService.award_badge(user, badge)
            return user_badge
        else:
            # Update progress if badge exists
            if user_badge:
                user_badge.progress = {
                    'current': current,
                    'required': required,
                    'updated_at': timezone.now().isoformat()
                }
                user_badge.save(update_fields=['progress'])
            
            return user_badge
    
    @staticmethod
    def check_badge_criteria(user, badge):
        """
        Check if user meets criteria for a badge
        
        Args:
            user: User instance
            badge: Badge instance
        
        Returns:
            tuple (eligible: bool, progress: dict)
        """
        from apps.user_profile.models import UserBadge
        
        # Already earned?
        if UserBadge.objects.filter(user=user, badge=badge).exists():
            return (False, {'reason': 'already_earned'})
        
        criteria = badge.criteria
        criteria_type = criteria.get('type')
        
        # Simple criteria checks
        if criteria_type == 'kyc_verified':
            eligible = user.userprofile.kyc_status == 'verified'
            return (eligible, {'type': 'kyc_verified'})
        
        if criteria_type == 'team_created':
            # Check if user is captain of any team
            from apps.teams.models import Team
            eligible = Team.objects.filter(captain=user).exists()
            return (eligible, {'type': 'team_created'})
        
        if criteria_type == 'stream_active':
            eligible = user.userprofile.stream_status
            return (eligible, {'type': 'stream_active'})
        
        if criteria_type == 'level':
            threshold = criteria.get('threshold', 0)
            current = user.userprofile.level
            eligible = current >= threshold
            return (eligible, {'current': current, 'required': threshold})
        
        # Threshold-based criteria (need to query related data)
        threshold = criteria.get('threshold', 0)
        
        if criteria_type == 'tournament_participation':
            from apps.tournaments.models import Registration
            count = Registration.objects.filter(
                team__captain=user,
                status='confirmed'
            ).count()
            return (count >= threshold, {'current': count, 'required': threshold})
        
        if criteria_type == 'match_wins':
            # Would need to query match results
            # Placeholder for now
            return (False, {'current': 0, 'required': threshold})
        
        if criteria_type == 'tournament_wins':
            # Would need to query tournament winners
            # Placeholder for now
            return (False, {'current': 0, 'required': threshold})
        
        if criteria_type == 'withdrawals':
            from apps.economy.models import WithdrawalRequest
            count = WithdrawalRequest.objects.filter(
                wallet__user_profile__user=user,
                status='completed'
            ).count()
            return (count >= threshold, {'current': count, 'required': threshold})
        
        if criteria_type == 'lifetime_earnings':
            current = user.userprofile.lifetime_earnings or 0
            return (current >= threshold, {'current': current, 'required': threshold})
        
        # Manual award badges
        if criteria_type == 'manual_award':
            return (False, {'type': 'manual_award'})
        
        # Unknown criteria
        return (False, {'reason': 'unknown_criteria', 'type': criteria_type})
    
    @staticmethod
    def check_all_badges(user):
        """
        Check all active badges and award eligible ones
        
        Args:
            user: User instance
        
        Returns:
            list of newly earned UserBadge instances
        """
        from apps.user_profile.models import Badge
        
        newly_earned = []
        badges = Badge.objects.filter(is_active=True, is_hidden=False)
        
        for badge in badges:
            eligible, progress = XPService.check_badge_criteria(user, badge)
            if eligible:
                user_badge = XPService.award_badge(user, badge)
                if user_badge:
                    newly_earned.append(user_badge)
        
        return newly_earned


# Convenience functions
def award_xp(user, amount, reason='', context=None):
    """Award XP to a user"""
    return XPService.award_xp(user, amount, reason, context)


def award_badge(user, badge, context=None):
    """Award a badge to a user"""
    return XPService.award_badge(user, badge, context)


def check_level_up(user):
    """Check and update user level based on current XP"""
    profile = user.profile
    correct_level = XPService.level_for_xp(profile.xp)
    
    if correct_level != profile.level:
        old_level = profile.level
        profile.level = correct_level
        profile.save(update_fields=['level', 'updated_at'])
        
        logger.info(f"Corrected level for {user.username}: {old_level} → {correct_level}")
        
        # Check level badges
        XPService._check_level_badges(user, correct_level)
        
        return True
    return False
