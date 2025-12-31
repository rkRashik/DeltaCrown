# apps/user_profile/tests/test_trophy_showcase.py
"""
Test suite for Trophy Showcase Config (P0 Feature).

Tests:
- TrophyShowcaseConfig model (border/frame/badges)
- Border unlock logic (from badge rarities)
- Frame unlock logic (from tournament achievements)
- Equip/unequip/reorder badge operations
- Validation (max 5 badges, ownership checks)
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from apps.user_profile.models import (
    TrophyShowcaseConfig,
    Badge,
    UserBadge,
)
from apps.user_profile.services.trophy_showcase_service import (
    get_unlocked_borders,
    get_unlocked_frames,
    get_pinnable_badges,
    equip_border,
    equip_frame,
    get_or_create_showcase,
    get_showcase_data,
    validate_showcase_config,
)

User = get_user_model()


# ============================================================================
# MODEL TESTS
# ============================================================================

@pytest.mark.django_db
class TestTrophyShowcaseConfigModel:
    """Test TrophyShowcaseConfig model operations."""
    
    def test_create_showcase_defaults(self):
        """Default showcase should have 'none' border/frame and no badges."""
        user = User.objects.create_user(username='player1', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        assert showcase.border == 'none'
        assert showcase.frame == 'none'
        assert showcase.pinned_badge_ids == []
        assert showcase.created_at
        assert showcase.updated_at
    
    def test_one_showcase_per_user(self):
        """OneToOneField should enforce one showcase per user."""
        user = User.objects.create_user(username='player2', password='test123')
        showcase1 = TrophyShowcaseConfig.objects.create(user=user)
        
        # Second should fail (OneToOne constraint)
        with pytest.raises(Exception):  # IntegrityError
            TrophyShowcaseConfig.objects.create(user=user)
    
    def test_equip_border(self):
        """User can equip a border style."""
        user = User.objects.create_user(username='player3', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        showcase.border = 'gold'
        showcase.save()
        showcase.refresh_from_db()
        
        assert showcase.border == 'gold'
    
    def test_equip_frame(self):
        """User can equip a frame style."""
        user = User.objects.create_user(username='player4', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        showcase.frame = 'champion'
        showcase.save()
        showcase.refresh_from_db()
        
        assert showcase.frame == 'champion'
    
    def test_pin_badge(self):
        """User can pin badges using pin_badge() helper."""
        user = User.objects.create_user(username='player5', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        # Create badge and earn it
        badge = Badge.objects.create(
            name='First Win',
            slug='first_win',
            icon='🏆',
            rarity='common',
            category='achievement',
        )
        user_badge = UserBadge.objects.create(user=user, badge=badge)
        
        # Pin badge
        showcase.pin_badge(user_badge.pk)
        showcase.refresh_from_db()
        
        assert user_badge.pk in showcase.pinned_badge_ids
        assert len(showcase.pinned_badge_ids) == 1
    
    def test_unpin_badge(self):
        """User can unpin badges using unpin_badge() helper."""
        user = User.objects.create_user(username='player6', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        # Create badge and earn it
        badge = Badge.objects.create(
            name='Ten Wins',
            slug='ten_wins',
            icon='🏆',
            rarity='rare',
            category='achievement',
        )
        user_badge = UserBadge.objects.create(user=user, badge=badge)
        
        # Pin then unpin
        showcase.pin_badge(user_badge.pk)
        showcase.unpin_badge(user_badge.pk)
        showcase.refresh_from_db()
        
        assert user_badge.pk not in showcase.pinned_badge_ids
        assert len(showcase.pinned_badge_ids) == 0
    
    def test_max_5_badges(self):
        """User cannot pin more than 5 badges (validation)."""
        user = User.objects.create_user(username='player7', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        # Create 6 badges
        badges = []
        for i in range(6):
            badge = Badge.objects.create(
                name=f'Badge {i}',
                slug=f'badge_{i}',
                icon='🏆',
                rarity='common',
                category='achievement',
            )
            user_badge = UserBadge.objects.create(user=user, badge=badge)
            badges.append(user_badge)
        
        # Pin 5 badges (should succeed)
        for ub in badges[:5]:
            showcase.pin_badge(ub.pk)
        
        # Try to pin 6th badge (should fail)
        with pytest.raises(ValidationError) as exc_info:
            showcase.pin_badge(badges[5].pk)
        
        assert 'max 5 badges' in str(exc_info.value).lower()
    
    def test_reorder_pinned_badges(self):
        """User can reorder pinned badges."""
        user = User.objects.create_user(username='player8', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        # Create 3 badges
        badges = []
        for i in range(3):
            badge = Badge.objects.create(
                name=f'Badge {i}',
                slug=f'badge_{i}',
                icon='🏆',
                rarity='common',
                category='achievement',
            )
            user_badge = UserBadge.objects.create(user=user, badge=badge)
            badges.append(user_badge)
            showcase.pin_badge(user_badge.pk)
        
        # Reorder (reverse order)
        new_order = [badges[2].pk, badges[1].pk, badges[0].pk]
        showcase.reorder_pinned_badges(new_order)
        showcase.refresh_from_db()
        
        assert showcase.pinned_badge_ids == new_order
    
    def test_get_pinned_badges_returns_userbadges(self):
        """get_pinned_badges() should return UserBadge instances."""
        user = User.objects.create_user(username='player9', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        # Create badge and earn it
        badge = Badge.objects.create(
            name='Champion',
            slug='champion',
            icon='🏆',
            rarity='legendary',
            category='tournament',
        )
        user_badge = UserBadge.objects.create(user=user, badge=badge)
        showcase.pin_badge(user_badge.pk)
        
        # Get pinned badges
        pinned = showcase.get_pinned_badges()
        
        assert len(pinned) == 1
        assert pinned[0] == user_badge
        assert pinned[0].badge.name == 'Champion'


# ============================================================================
# SERVICE TESTS - UNLOCK LOGIC
# ============================================================================

@pytest.mark.django_db
class TestBorderUnlockLogic:
    """Test border unlock logic from badge rarities."""
    
    def test_no_badges_only_none(self):
        """User with no badges can only use 'none' border."""
        user = User.objects.create_user(username='player10', password='test123')
        unlocked = get_unlocked_borders(user)
        
        assert unlocked == ['none']
    
    def test_common_badge_unlocks_bronze(self):
        """Earning a Common badge unlocks Bronze border."""
        user = User.objects.create_user(username='player11', password='test123')
        
        # Create Common badge
        badge = Badge.objects.create(
            name='First Blood',
            slug='first_blood',
            icon='🩸',
            rarity='common',
            category='achievement',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        unlocked = get_unlocked_borders(user)
        
        assert 'bronze' in unlocked
        assert 'silver' not in unlocked
    
    def test_rare_badge_unlocks_silver(self):
        """Earning a Rare badge unlocks Silver border."""
        user = User.objects.create_user(username='player12', password='test123')
        
        # Create Rare badge
        badge = Badge.objects.create(
            name='Sharpshooter',
            slug='sharpshooter',
            icon='🎯',
            rarity='rare',
            category='achievement',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        unlocked = get_unlocked_borders(user)
        
        assert 'silver' in unlocked
        assert 'bronze' in unlocked  # Should also have Bronze
    
    def test_epic_badge_unlocks_gold(self):
        """Earning an Epic badge unlocks Gold border."""
        user = User.objects.create_user(username='player13', password='test123')
        
        # Create Epic badge
        badge = Badge.objects.create(
            name='Ace Master',
            slug='ace_master',
            icon='🔥',
            rarity='epic',
            category='achievement',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        unlocked = get_unlocked_borders(user)
        
        assert 'gold' in unlocked
        assert 'silver' in unlocked
        assert 'bronze' in unlocked
    
    def test_legendary_badge_unlocks_platinum(self):
        """Earning a Legendary badge unlocks Platinum border."""
        user = User.objects.create_user(username='player14', password='test123')
        
        # Create Legendary badge
        badge = Badge.objects.create(
            name='Untouchable',
            slug='untouchable',
            icon='✨',
            rarity='legendary',
            category='achievement',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        unlocked = get_unlocked_borders(user)
        
        assert 'platinum' in unlocked
        assert 'gold' in unlocked
    
    def test_10_legendary_badges_unlocks_diamond(self):
        """Earning 10+ Legendary badges unlocks Diamond border."""
        user = User.objects.create_user(username='player15', password='test123')
        
        # Create 10 Legendary badges
        for i in range(10):
            badge = Badge.objects.create(
                name=f'Legendary {i}',
                slug=f'legendary_{i}',
                icon='💎',
                rarity='legendary',
                category='achievement',
            )
            UserBadge.objects.create(user=user, badge=badge)
        
        unlocked = get_unlocked_borders(user)
        
        assert 'diamond' in unlocked
        assert 'platinum' in unlocked
    
    def test_tournament_champion_unlocks_master(self):
        """Winning a tournament unlocks Master border."""
        user = User.objects.create_user(username='player16', password='test123')
        
        # Create tournament champion badge
        badge = Badge.objects.create(
            name='Tournament Champion',
            slug='tournament_champion',
            icon='👑',
            rarity='legendary',
            category='tournament',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        unlocked = get_unlocked_borders(user)
        
        assert 'master' in unlocked
        assert 'platinum' in unlocked


@pytest.mark.django_db
class TestFrameUnlockLogic:
    """Test frame unlock logic from tournament achievements."""
    
    def test_no_tournament_badges_only_none(self):
        """User with no tournament badges can only use 'none' frame."""
        user = User.objects.create_user(username='player17', password='test123')
        unlocked = get_unlocked_frames(user)
        
        assert unlocked == ['none']
    
    def test_tournament_participant_unlocks_competitor(self):
        """Participating in a tournament unlocks Competitor frame."""
        user = User.objects.create_user(username='player18', password='test123')
        
        # Create participant badge
        badge = Badge.objects.create(
            name='Tournament Participant',
            slug='tournament_participant',
            icon='🎮',
            rarity='common',
            category='tournament',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        unlocked = get_unlocked_frames(user)
        
        assert 'competitor' in unlocked
        assert 'finalist' not in unlocked
    
    def test_tournament_finalist_unlocks_finalist(self):
        """Reaching tournament finals unlocks Finalist frame."""
        user = User.objects.create_user(username='player19', password='test123')
        
        # Create finalist badge
        badge = Badge.objects.create(
            name='Tournament Finalist',
            slug='tournament_finalist',
            icon='🥈',
            rarity='rare',
            category='tournament',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        unlocked = get_unlocked_frames(user)
        
        assert 'finalist' in unlocked
        assert 'competitor' in unlocked
    
    def test_tournament_champion_unlocks_champion(self):
        """Winning a tournament unlocks Champion frame."""
        user = User.objects.create_user(username='player20', password='test123')
        
        # Create champion badge
        badge = Badge.objects.create(
            name='Tournament Champion',
            slug='tournament_champion',
            icon='🏆',
            rarity='epic',
            category='tournament',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        unlocked = get_unlocked_frames(user)
        
        assert 'champion' in unlocked
        assert 'finalist' in unlocked
        assert 'competitor' in unlocked
    
    def test_3_tournament_wins_unlocks_grand_champion(self):
        """Winning 3+ tournaments unlocks Grand Champion frame."""
        user = User.objects.create_user(username='player21', password='test123')
        
        # Create champion badge
        badge = Badge.objects.create(
            name='Tournament Champion',
            slug='tournament_champion',
            icon='🏆',
            rarity='epic',
            category='tournament',
        )
        
        # Award badge 3 times (user can earn same badge multiple times with different contexts)
        for i in range(3):
            UserBadge.objects.create(
                user=user,
                badge=badge,
                context={'tournament_id': i}  # Different tournament
            )
        
        unlocked = get_unlocked_frames(user)
        
        assert 'grand_champion' in unlocked
        assert 'champion' in unlocked
    
    def test_10_tournament_wins_unlocks_legend(self):
        """Winning 10+ tournaments unlocks Legend frame."""
        user = User.objects.create_user(username='player22', password='test123')
        
        # Create champion badge
        badge = Badge.objects.create(
            name='Tournament Champion',
            slug='tournament_champion',
            icon='🏆',
            rarity='epic',
            category='tournament',
        )
        
        # Award badge 10 times
        for i in range(10):
            UserBadge.objects.create(
                user=user,
                badge=badge,
                context={'tournament_id': i}
            )
        
        unlocked = get_unlocked_frames(user)
        
        assert 'legend' in unlocked
        assert 'grand_champion' in unlocked


# ============================================================================
# SERVICE TESTS - EQUIP OPERATIONS
# ============================================================================

@pytest.mark.django_db
class TestEquipOperations:
    """Test equip_border() and equip_frame() service functions."""
    
    def test_equip_unlocked_border(self):
        """User can equip an unlocked border."""
        user = User.objects.create_user(username='player23', password='test123')
        
        # Create Common badge (unlocks Bronze)
        badge = Badge.objects.create(
            name='First Win',
            slug='first_win',
            icon='🏆',
            rarity='common',
            category='achievement',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        # Equip Bronze border
        showcase = equip_border(user, 'bronze')
        
        assert showcase.border == 'bronze'
    
    def test_cannot_equip_locked_border(self):
        """User cannot equip a locked border."""
        user = User.objects.create_user(username='player24', password='test123')
        # No badges earned
        
        # Try to equip Gold border (locked)
        with pytest.raises(ValueError) as exc_info:
            equip_border(user, 'gold')
        
        assert 'not unlocked' in str(exc_info.value).lower()
    
    def test_equip_unlocked_frame(self):
        """User can equip an unlocked frame."""
        user = User.objects.create_user(username='player25', password='test123')
        
        # Create tournament champion badge (unlocks Champion frame)
        badge = Badge.objects.create(
            name='Tournament Champion',
            slug='tournament_champion',
            icon='🏆',
            rarity='epic',
            category='tournament',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        # Equip Champion frame
        showcase = equip_frame(user, 'champion')
        
        assert showcase.frame == 'champion'
    
    def test_cannot_equip_locked_frame(self):
        """User cannot equip a locked frame."""
        user = User.objects.create_user(username='player26', password='test123')
        # No tournament badges earned
        
        # Try to equip Legend frame (locked)
        with pytest.raises(ValueError) as exc_info:
            equip_frame(user, 'legend')
        
        assert 'not unlocked' in str(exc_info.value).lower()


# ============================================================================
# SERVICE TESTS - VALIDATION
# ============================================================================

@pytest.mark.django_db
class TestShowcaseValidation:
    """Test validate_showcase_config() validation logic."""
    
    def test_valid_showcase_no_errors(self):
        """Showcase with unlocked cosmetics passes validation."""
        user = User.objects.create_user(username='player27', password='test123')
        
        # Create Common badge (unlocks Bronze)
        badge = Badge.objects.create(
            name='First Win',
            slug='first_win',
            icon='🏆',
            rarity='common',
            category='achievement',
        )
        UserBadge.objects.create(user=user, badge=badge)
        
        # Equip Bronze border
        showcase = equip_border(user, 'bronze')
        
        errors = validate_showcase_config(user, showcase)
        
        assert len(errors) == 0
    
    def test_locked_border_fails_validation(self):
        """Showcase with locked border fails validation."""
        user = User.objects.create_user(username='player28', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        # Manually set locked border (bypass equip_border validation)
        showcase.border = 'master'
        showcase.save()
        
        errors = validate_showcase_config(user, showcase)
        
        assert len(errors) > 0
        assert 'border' in errors[0].lower()
    
    def test_locked_frame_fails_validation(self):
        """Showcase with locked frame fails validation."""
        user = User.objects.create_user(username='player29', password='test123')
        showcase = TrophyShowcaseConfig.objects.create(user=user)
        
        # Manually set locked frame (bypass equip_frame validation)
        showcase.frame = 'legend'
        showcase.save()
        
        errors = validate_showcase_config(user, showcase)
        
        assert len(errors) > 0
        assert 'frame' in errors[0].lower()


# ============================================================================
# SERVICE TESTS - GET SHOWCASE DATA
# ============================================================================

@pytest.mark.django_db
class TestGetShowcaseData:
    """Test get_showcase_data() aggregator function."""
    
    def test_showcase_data_includes_equipped_and_unlocked(self):
        """get_showcase_data() returns equipped + unlocked cosmetics."""
        user = User.objects.create_user(username='player30', password='test123')
        
        # Create badges to unlock cosmetics
        badge1 = Badge.objects.create(
            name='Common Badge',
            slug='common_badge',
            icon='🏆',
            rarity='common',
            category='achievement',
        )
        badge2 = Badge.objects.create(
            name='Rare Badge',
            slug='rare_badge',
            icon='💎',
            rarity='rare',
            category='achievement',
        )
        UserBadge.objects.create(user=user, badge=badge1)
        UserBadge.objects.create(user=user, badge=badge2)
        
        # Equip Bronze border
        equip_border(user, 'bronze')
        
        # Get showcase data
        data = get_showcase_data(user)
        
        assert 'equipped' in data
        assert data['equipped']['border'] == 'bronze'
        assert data['equipped']['frame'] == 'none'
        
        assert 'unlocked' in data
        assert 'bronze' in data['unlocked']['borders']
        assert 'silver' in data['unlocked']['borders']  # Rare badge unlocks Silver
        
        assert 'pinned_badges' in data
