from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import UserProfile, PrivacySettings, VerificationRecord

User = get_user_model()
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **_):
    defaults = {"display_name": instance.username or instance.email}
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults=defaults)
    else:
        UserProfile.objects.get_or_create(user=instance, defaults=defaults)


@receiver(post_save, sender=UserProfile)
def ensure_privacy_and_verification(sender, instance, created, **_):
    """
    Auto-create PrivacySettings and VerificationRecord for each UserProfile.
    This ensures every profile has privacy controls and KYC tracking.
    """
    # Create PrivacySettings with default values (all permissions enabled)
    if not hasattr(instance, 'privacy_settings'):
        PrivacySettings.objects.get_or_create(
            user_profile=instance,
            defaults={
                # Profile Visibility (default: all public except sensitive data)
                'show_real_name': False,  # Hidden by default for privacy
                'show_phone': False,      # Hidden by default for privacy
                'show_email': False,      # Hidden by default for privacy
                'show_age': True,
                'show_gender': True,
                'show_country': True,
                'show_address': False,    # Hidden by default for privacy
                # Gaming & Activity
                'show_game_ids': True,
                'show_match_history': True,
                'show_teams': True,
                'show_achievements': True,
                # Economy & Inventory
                'show_inventory_value': False,  # Hidden by default
                'show_level_xp': True,
                # Social
                'show_social_links': True,
                # Interaction Permissions
                'allow_team_invites': True,
                'allow_friend_requests': True,
                'allow_direct_messages': True,
            }
        )
    
    # Create VerificationRecord for KYC tracking
    if not hasattr(instance, 'verification_record'):
        VerificationRecord.objects.get_or_create(
            user_profile=instance,
            defaults={'status': 'unverified'}
        )


# ===== XP AND BADGE AWARD SIGNALS =====

@receiver(post_save, sender=VerificationRecord)
def award_kyc_badge(sender, instance, created, **kwargs):
    """Award 'Verified Player' badge when KYC is approved"""
    # Only award on status change to verified, not on creation
    if not created and instance.status == 'verified':
        # Check if status actually changed to verified
        old_instance = VerificationRecord.objects.filter(pk=instance.pk).first()
        if old_instance and old_instance.status != 'verified':
            user = instance.user_profile.user
            
            # Award XP for KYC completion
            from apps.user_profile.services import award_xp, award_badge
            award_xp(user, 100, reason='KYC verification completed')
            
            # Award Verified Player badge
            award_badge(user, 'verified-player', context={'kyc_verified_at': instance.reviewed_at.isoformat()})
            
            logger.info(f"Awarded KYC badge to {user.username}")


def award_team_captain_badge(user):
    """Award 'Team Captain' badge when user creates a team"""
    from apps.user_profile.services import award_xp, award_badge
    
    # Award XP for team creation
    award_xp(user, 75, reason='Created a team')
    
    # Award Team Captain badge
    award_badge(user, 'team-captain', context={'timestamp': timezone.now().isoformat()})
    
    logger.info(f"Awarded Team Captain badge to {user.username}")


def award_first_withdrawal_badge(user):
    """Award 'First Withdrawal' badge on first successful withdrawal"""
    from apps.economy.models import WithdrawalRequest
    from apps.user_profile.services import award_xp, award_badge
    
    # Check if this is the first completed withdrawal
    completed_count = WithdrawalRequest.objects.filter(
        wallet__user_profile__user=user,
        status='completed'
    ).count()
    
    if completed_count == 1:  # First withdrawal
        # Award XP
        award_xp(user, 150, reason='Completed first withdrawal')
        
        # Award First Withdrawal badge
        award_badge(user, 'first-withdrawal', context={'timestamp': timezone.now().isoformat()})
        
        logger.info(f"Awarded First Withdrawal badge to {user.username}")


def award_tournament_badges(user, tournament, placement=None):
    """
    Award badges for tournament participation and wins
    
    Args:
        user: User instance
        tournament: Tournament instance
        placement: Final placement (1 = champion, 2-3 = podium, etc.)
    """
    from apps.user_profile.services import award_xp, award_badge, XPService
    
    # Award participation XP
    award_xp(user, 20, reason=f'Participated in {tournament.name}')
    
    # Award Tournament Debut badge (first participation)
    from apps.tournaments.models import Registration
    participation_count = Registration.objects.filter(
        team__captain=user,
        status='confirmed'
    ).count()
    
    if participation_count == 1:
        award_badge(user, 'tournament-debut', context={
            'tournament_id': tournament.id,
            'tournament_name': tournament.name
        })
    
    # Award placement-based rewards
    if placement == 1:  # Champion
        # Award champion XP
        award_xp(user, 500, reason=f'Won {tournament.name}')
        
        # Award Champion badge (first tournament win)
        award_badge(user, 'champion', context={
            'tournament_id': tournament.id,
            'tournament_name': tournament.name,
            'game': tournament.game.slug if hasattr(tournament, 'game') else None
        })
        
        # Check for game-specific badges (10+ wins)
        if hasattr(tournament, 'game'):
            game_slug = tournament.game.slug
            # Count tournament wins for this game
            # (This is a placeholder - actual implementation would query match results)
            
            # Award game-specific master badges
            if game_slug == 'pubg-mobile':
                award_badge(user, 'pubgm-master')
            elif game_slug == 'free-fire':
                award_badge(user, 'freefire-legend')
            elif game_slug == 'valorant':
                award_badge(user, 'valorant-champion')


def award_match_win_xp(user, match, xp_amount=50):
    """Award XP for winning a match"""
    from apps.user_profile.services import award_xp, award_badge
    
    award_xp(user, xp_amount, reason=f'Won match #{match.id}')
    
    # Award First Victory badge (first match win)
    from apps.user_profile.models import UserBadge
    if not UserBadge.objects.filter(user=user, badge__slug='first-victory').exists():
        award_badge(user, 'first-victory', context={
            'match_id': match.id,
            'timestamp': timezone.now().isoformat()
        })


def check_lifetime_earnings_badges(user):
    """Check and award badges based on lifetime earnings milestones"""
    from apps.user_profile.services import award_badge
    
    profile = user.profile
    lifetime_earnings = profile.lifetime_earnings or 0
    
    # Big Earner badge (10,000+ DeltaCoins)
    if lifetime_earnings >= 10000:
        award_badge(user, 'big-earner', context={
            'lifetime_earnings': lifetime_earnings,
            'timestamp': timezone.now().isoformat()
        })


def award_content_creator_badge(user):
    """Award 'Content Creator' badge when user starts streaming"""
    from apps.user_profile.services import award_xp, award_badge
    
    # Award XP for streaming
    award_xp(user, 30, reason='Started streaming')
    
    # Award Content Creator badge
    award_badge(user, 'content-creator', context={'timestamp': timezone.now().isoformat()})
    
    logger.info(f"Awarded Content Creator badge to {user.username}")


# ============================================================================
# ACHIEVEMENT SYSTEM SIGNALS
# Automatically check and award achievements when relevant actions occur
# ============================================================================

@receiver(post_save, sender='user_profile.Follow')
def check_achievements_on_follow(sender, instance, created, **kwargs):
    """Check social achievements when someone gets a new follower"""
    if created:
        from apps.user_profile.services.achievement_service import check_social_achievements
        # Check for the user who was followed (gained a follower)
        check_social_achievements(instance.following)


@receiver(post_save, sender='user_profile.GameProfile')
def check_achievements_on_game_profile(sender, instance, created, **kwargs):
    """Check profile achievements when game profiles are added"""
    if created:
        from apps.user_profile.services.achievement_service import check_profile_achievements
        check_profile_achievements(instance.user)


@receiver(post_save, sender='user_profile.SocialLink')
def check_achievements_on_social_link(sender, instance, created, **kwargs):
    """Check profile achievements when social links are added"""
    if created:
        from apps.user_profile.services.achievement_service import check_profile_achievements
        check_profile_achievements(instance.user)


@receiver(post_save, sender='teams.TeamMembership')
def check_achievements_on_team_join(sender, instance, created, **kwargs):
    """Check social achievements when joining a team"""
    if created and instance.status == 'active':
        from apps.user_profile.services.achievement_service import check_social_achievements
        check_social_achievements(instance.user)


@receiver(post_save, sender=UserProfile)
def check_achievements_on_kyc_verification(sender, instance, created, **kwargs):
    """Check profile achievements when KYC is verified"""
    if not created and instance.kyc_verified:
        from apps.user_profile.services.achievement_service import check_profile_achievements
        check_profile_achievements(instance.user)
