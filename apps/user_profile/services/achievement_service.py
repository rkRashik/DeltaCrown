"""
Achievement Service - Automatic achievement awarding logic
This service checks user stats and awards achievements based on triggers.

Usage:
    from apps.user_profile.services.achievement_service import check_all_achievements
    check_all_achievements(user)
"""

from django.db.models import Count, Sum, Q
from apps.user_profile.models_main import Achievement, Follow, GameProfile, SocialLink
from apps.user_profile.utils import get_user_profile_safe
from apps.teams.models import TeamMembership
from datetime import datetime, timedelta


def award_achievement(user, name, description, emoji, rarity, context=None):
    """
    Award an achievement to a user if they don't already have it.
    
    Args:
        user: User instance
        name: Achievement name
        description: Achievement description  
        emoji: Emoji icon
        rarity: 'common', 'rare', 'epic', or 'legendary'
        context: Optional context dict
        
    Returns:
        Achievement instance if created, None if already exists
    """
    if context is None:
        context = {}
    
    # Check if user already has this achievement
    if Achievement.objects.filter(user=user, name=name).exists():
        return None
    
    # Create the achievement
    achievement = Achievement.objects.create(
        user=user,
        name=name,
        description=description,
        emoji=emoji,
        rarity=rarity,
        context=context
    )
    
    return achievement


def check_tournament_achievements(user):
    """Check and award tournament-related achievements"""
    achievements_awarded = []
    
    # Get tournament participation stats
    # Note: This assumes tournament app has Participation or Result models
    # Adjust based on actual tournament model structure
    try:
        from apps.tournaments.models import Participation
        
        participations = Participation.objects.filter(
            user=user,
            tournament__status='completed'
        )
        total_tournaments = participations.count()
        wins = participations.filter(placement=1).count()
        top_3 = participations.filter(placement__lte=3).count()
        
        # First Blood
        if wins >= 1:
            ach = award_achievement(
                user, 'First Blood',
                'Won your first tournament',
                '🥇', 'common',
                {'wins': wins}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Triple Crown
        if wins >= 3:
            ach = award_achievement(
                user, 'Triple Crown',
                'Won 3 tournaments',
                '👑', 'rare',
                {'wins': wins}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Champion
        if wins >= 10:
            ach = award_achievement(
                user, 'Champion',
                'Won 10 tournaments',
                '🏆', 'epic',
                {'wins': wins}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Legend
        if wins >= 25:
            ach = award_achievement(
                user, 'Legend',
                'Won 25 tournaments',
                '⭐', 'legendary',
                {'wins': wins}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Rookie
        if total_tournaments >= 1:
            ach = award_achievement(
                user, 'Rookie',
                'Participated in your first tournament',
                '🎮', 'common',
                {'tournaments': total_tournaments}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Veteran
        if total_tournaments >= 10:
            ach = award_achievement(
                user, 'Veteran',
                'Participated in 10 tournaments',
                '🎯', 'rare',
                {'tournaments': total_tournaments}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Grinder
        if total_tournaments >= 50:
            ach = award_achievement(
                user, 'Grinder',
                'Participated in 50 tournaments',
                '⚡', 'epic',
                {'tournaments': total_tournaments}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Competitor
        if total_tournaments >= 100:
            ach = award_achievement(
                user, 'Competitor',
                'Participated in 100 tournaments',
                '🔥', 'legendary',
                {'tournaments': total_tournaments}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Runner Up
        second_place = participations.filter(placement=2).exists()
        if second_place:
            ach = award_achievement(
                user, 'Runner Up',
                'Placed 2nd in a tournament',
                '🥈', 'common',
                {'placement': 2}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Bronze Medalist
        third_place = participations.filter(placement=3).exists()
        if third_place:
            ach = award_achievement(
                user, 'Bronze Medalist',
                'Placed 3rd in a tournament',
                '🥉', 'common',
                {'placement': 3}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Consistent
        if top_3 >= 5:
            ach = award_achievement(
                user, 'Consistent',
                'Placed in top 3 five times',
                '📈', 'rare',
                {'top_3_count': top_3}
            )
            if ach:
                achievements_awarded.append(ach)
        
    except ImportError:
        # Tournament models not available yet
        pass
    
    return achievements_awarded


def check_social_achievements(user):
    """Check and award social-related achievements"""
    achievements_awarded = []
    
    # Follower count
    follower_count = Follow.objects.filter(following=user).count()
    
    # Influencer
    if follower_count >= 100:
        ach = award_achievement(
            user, 'Influencer',
            'Gained 100 followers',
            '🌟', 'rare',
            {'followers': follower_count}
        )
        if ach:
            achievements_awarded.append(ach)
    
    # Celebrity
    if follower_count >= 500:
        ach = award_achievement(
            user, 'Celebrity',
            'Gained 500 followers',
            '✨', 'epic',
            {'followers': follower_count}
        )
        if ach:
            achievements_awarded.append(ach)
    
    # Icon
    if follower_count >= 1000:
        ach = award_achievement(
            user, 'Icon',
            'Gained 1,000 followers',
            '🎖️', 'legendary',
            {'followers': follower_count}
        )
        if ach:
            achievements_awarded.append(ach)
    
    # Team Player
    user_profile = get_user_profile_safe(user)
    team_count = TeamMembership.objects.filter(
        profile=user_profile,
        status='active'
    ).count()
    
    if team_count >= 1:
        ach = award_achievement(
            user, 'Team Player',
            'Joined your first team',
            '🤝', 'common',
            {'teams': team_count}
        )
        if ach:
            achievements_awarded.append(ach)
    
    return achievements_awarded


def check_profile_achievements(user):
    """Check and award profile completion achievements"""
    achievements_awarded = []
    
    # KYC Verified
    try:
        if user.profile.kyc_verified:
            ach = award_achievement(
                user, 'Verified',
                'Completed KYC verification',
                '✅', 'rare',
                {'verified': True}
            )
            if ach:
                achievements_awarded.append(ach)
    except AttributeError:
        pass
    
    # Multi-Game Master
    game_profile_count = GameProfile.objects.filter(user=user).count()
    if game_profile_count >= 3:
        ach = award_achievement(
            user, 'Multi-Game Master',
            'Added game profiles for 3+ games',
            '🎲', 'rare',
            {'games': game_profile_count}
        )
        if ach:
            achievements_awarded.append(ach)
    
    # Social Butterfly
    social_link_count = SocialLink.objects.filter(user=user).count()
    if social_link_count >= 3:
        ach = award_achievement(
            user, 'Social Butterfly',
            'Connected 3+ social media accounts',
            '🦋', 'common',
            {'links': social_link_count}
        )
        if ach:
            achievements_awarded.append(ach)
    
    return achievements_awarded


def check_economic_achievements(user):
    """Check and award economic/wallet achievements"""
    achievements_awarded = []
    
    try:
        from apps.economy.models import Wallet, Transaction
        
        wallet = Wallet.objects.filter(user=user).first()
        if not wallet:
            return achievements_awarded
        
        # First Earnings
        total_earnings = Transaction.objects.filter(
            wallet=wallet,
            transaction_type='credit'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        if total_earnings >= 1:
            ach = award_achievement(
                user, 'First Earnings',
                'Earned your first DeltaCoin',
                '💵', 'common',
                {'earnings': total_earnings}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Whale
        if wallet.balance >= 10000:
            ach = award_achievement(
                user, 'Whale',
                'Accumulated 10,000 DeltaCoins',
                '🐋', 'epic',
                {'balance': wallet.balance}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Mogul
        if total_earnings >= 50000:
            ach = award_achievement(
                user, 'Mogul',
                'Total lifetime earnings exceeded 50,000 DC',
                '💎', 'legendary',
                {'earnings': total_earnings}
            )
            if ach:
                achievements_awarded.append(ach)
        
        # Big Spender
        total_spent = Transaction.objects.filter(
            wallet=wallet,
            transaction_type='debit'
        ).aggregate(Sum('amount'))['amount__sum'] or 0
        
        if total_spent >= 1000:
            ach = award_achievement(
                user, 'Big Spender',
                'Spent 1,000 DeltaCoins',
                '💸', 'rare',
                {'spent': total_spent}
            )
            if ach:
                achievements_awarded.append(ach)
        
    except ImportError:
        # Economy models not available
        pass
    
    return achievements_awarded


def check_special_achievements(user):
    """Check and award special achievements"""
    achievements_awarded = []
    
    # Early Adopter (joined before Dec 1, 2025)
    early_adopter_cutoff = datetime(2025, 12, 1, tzinfo=user.date_joined.tzinfo)
    if user.date_joined <= early_adopter_cutoff:
        ach = award_achievement(
            user, 'Early Adopter',
            'Joined DeltaCrown in the first month',
            '🚀', 'legendary',
            {'joined': user.date_joined.isoformat()}
        )
        if ach:
            achievements_awarded.append(ach)
    
    # Certified
    try:
        from apps.user_profile.models import Certificate
        cert_count = Certificate.objects.filter(user=user).count()
        if cert_count >= 1:
            ach = award_achievement(
                user, 'Certified',
                'Earned your first tournament certificate',
                '📜', 'rare',
                {'certificates': cert_count}
            )
            if ach:
                achievements_awarded.append(ach)
    except ImportError:
        pass
    
    return achievements_awarded


def check_all_achievements(user):
    """
    Check and award all possible achievements for a user.
    This is the main entry point for achievement checking.
    
    Args:
        user: User instance
        
    Returns:
        list of Achievement instances that were newly awarded
    """
    all_awarded = []
    
    # Check each category
    all_awarded.extend(check_tournament_achievements(user))
    all_awarded.extend(check_social_achievements(user))
    all_awarded.extend(check_profile_achievements(user))
    all_awarded.extend(check_economic_achievements(user))
    all_awarded.extend(check_special_achievements(user))
    
    return all_awarded


def get_achievement_progress(user):
    """
    Get user's progress toward unearned achievements.
    
    Returns:
        dict mapping achievement names to progress percentage
    """
    progress = {}
    
    # Follower-based achievements
    follower_count = Follow.objects.filter(following=user).count()
    if follower_count < 100:
        progress['Influencer'] = (follower_count / 100) * 100
    if follower_count < 500:
        progress['Celebrity'] = (follower_count / 500) * 100
    if follower_count < 1000:
        progress['Icon'] = (follower_count / 1000) * 100
    
    # Game profile achievements
    game_count = GameProfile.objects.filter(user=user).count()
    if game_count < 3:
        progress['Multi-Game Master'] = (game_count / 3) * 100
    
    # Social links
    social_count = SocialLink.objects.filter(user=user).count()
    if social_count < 3:
        progress['Social Butterfly'] = (social_count / 3) * 100
    
    # Tournament achievements (if available)
    try:
        from apps.tournaments.models import Participation
        participations = Participation.objects.filter(
            user=user,
            tournament__status='completed'
        )
        total = participations.count()
        wins = participations.filter(placement=1).count()
        
        if wins < 3:
            progress['Triple Crown'] = (wins / 3) * 100
        if wins < 10:
            progress['Champion'] = (wins / 10) * 100
        if wins < 25:
            progress['Legend'] = (wins / 25) * 100
        
        if total < 10:
            progress['Veteran'] = (total / 10) * 100
        if total < 50:
            progress['Grinder'] = (total / 50) * 100
        if total < 100:
            progress['Competitor'] = (total / 100) * 100
    except ImportError:
        pass
    
    return progress
