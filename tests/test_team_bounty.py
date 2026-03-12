"""
Team Bounty Tests — Challenge type validation, team membership,
game-based restrictions, and DeltaCoin escrow for team vs team bounties.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.test import TestCase
from unittest.mock import patch, MagicMock

from apps.user_profile.models import Bounty, BountyStatus, BountyType

User = get_user_model()


class BountyModelTeamFieldsTest(TestCase):
    """Test Bounty model team fields and validation."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="player_a", email="a@test.com", password="pass123"
        )
        self.user_b = User.objects.create_user(
            username="player_b", email="b@test.com", password="pass123"
        )

    def test_bounty_type_choices(self):
        """BountyType enum has solo and team values."""
        assert BountyType.SOLO == "solo"
        assert BountyType.TEAM == "team"

    def test_default_challenge_type_is_solo(self):
        """New bounties default to solo challenge type."""
        bounty = Bounty(
            creator=self.user_a,
            title="Default Type",
            stake_amount=500,
            status=BountyStatus.OPEN,
        )
        assert bounty.challenge_type == BountyType.SOLO

    def test_str_shows_1v1_for_solo(self):
        """__str__ includes [1v1] for solo bounties."""
        bounty = Bounty(
            creator=self.user_a,
            title="Solo Duel",
            challenge_type=BountyType.SOLO,
        )
        assert "[1v1]" in str(bounty)

    def test_str_shows_team_for_team_bounty(self):
        """__str__ includes [Team] for team bounties."""
        bounty = Bounty(
            creator=self.user_a,
            title="Team Match",
            challenge_type=BountyType.TEAM,
        )
        assert "[Team]" in str(bounty)

    def test_clean_team_bounty_requires_creator_team(self):
        """Team bounties without creator_team fail validation."""
        bounty = Bounty(
            creator=self.user_a,
            title="No Team",
            challenge_type=BountyType.TEAM,
            stake_amount=500,
            status=BountyStatus.OPEN,
        )
        with self.assertRaises(ValidationError) as ctx:
            bounty.clean()
        assert "creator_team" in str(ctx.exception).lower()


class BountyServiceTeamCreateTest(TestCase):
    """Test create_bounty() with team challenge parameters."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="team_creator", email="tc@test.com", password="pass123"
        )
        self.user_b = User.objects.create_user(
            username="team_opponent", email="to@test.com", password="pass123"
        )

        # Create profiles + wallets
        from apps.user_profile.models import UserProfile
        from apps.economy.models import DeltaCrownWallet

        self.profile_a = UserProfile.objects.get(user=self.user_a)
        self.profile_b = UserProfile.objects.get(user=self.user_b)

        self.wallet_a, _ = DeltaCrownWallet.objects.get_or_create(
            profile=self.profile_a
        )
        self.wallet_a.cached_balance = 5000
        self.wallet_a.save()

        self.wallet_b, _ = DeltaCrownWallet.objects.get_or_create(
            profile=self.profile_b
        )
        self.wallet_b.cached_balance = 5000
        self.wallet_b.save()

        # Create game with roster config
        from apps.games.models import Game, GameRosterConfig

        self.game = Game.objects.create(
            name="Valorant",
            display_name="VALORANT",
            slug="valorant-tb",
            short_code="VTB",
            is_active=True,
        )
        self.roster_config = GameRosterConfig.objects.create(
            game=self.game,
            max_team_size=5,
            min_team_size=5,
        )

        # Solo-only game
        self.solo_game = Game.objects.create(
            name="Chess",
            display_name="Chess",
            slug="chess-tb",
            short_code="CTB",
            is_active=True,
        )
        GameRosterConfig.objects.create(
            game=self.solo_game,
            max_team_size=1,
            min_team_size=1,
        )

        # Create teams
        from apps.organizations.models.team import Team
        from apps.organizations.models.membership import TeamMembership

        self.team_a = Team.objects.create(
            name="Alpha Squad",
            slug="alpha-squad-tb",
            game_id=self.game.id,
            region="NA",
            created_by=self.user_a,
        )
        self.team_b = Team.objects.create(
            name="Bravo Squad",
            slug="bravo-squad-tb",
            game_id=self.game.id,
            region="EU",
            created_by=self.user_b,
        )

        # Memberships
        TeamMembership.objects.create(
            team=self.team_a,
            user=self.user_a,
            role="OWNER",
            status="ACTIVE",
            game_id=self.game.id,
        )
        TeamMembership.objects.create(
            team=self.team_b,
            user=self.user_b,
            role="OWNER",
            status="ACTIVE",
            game_id=self.game.id,
        )

    def test_create_team_bounty_success(self):
        """Team bounty creation with valid team and game succeeds."""
        from apps.user_profile.services import bounty_service

        bounty = bounty_service.create_bounty(
            creator=self.user_a,
            title="5v5 Showdown",
            game=self.game,
            stake_amount=500,
            challenge_type=BountyType.TEAM,
            creator_team=self.team_a,
        )
        assert bounty.challenge_type == BountyType.TEAM
        assert bounty.creator_team == self.team_a
        assert bounty.status == BountyStatus.OPEN

    def test_create_team_bounty_without_team_fails(self):
        """Team bounty creation without creator_team raises ValidationError."""
        from apps.user_profile.services import bounty_service

        with self.assertRaises(ValidationError):
            bounty_service.create_bounty(
                creator=self.user_a,
                title="No Team",
                game=self.game,
                stake_amount=500,
                challenge_type=BountyType.TEAM,
                creator_team=None,
            )

    def test_create_team_bounty_solo_game_fails(self):
        """Team bounty on a solo-only game raises ValidationError."""
        from apps.user_profile.services import bounty_service

        with self.assertRaises(ValidationError):
            bounty_service.create_bounty(
                creator=self.user_a,
                title="Solo Game Team Attempt",
                game=self.solo_game,
                stake_amount=500,
                challenge_type=BountyType.TEAM,
                creator_team=self.team_a,
            )

    def test_create_team_bounty_self_challenge_fails(self):
        """Cannot challenge your own team."""
        from apps.user_profile.services import bounty_service

        with self.assertRaises(ValidationError):
            bounty_service.create_bounty(
                creator=self.user_a,
                title="Self Challenge",
                game=self.game,
                stake_amount=500,
                challenge_type=BountyType.TEAM,
                creator_team=self.team_a,
                target_team=self.team_a,
            )

    def test_create_team_bounty_non_member_fails(self):
        """Non-member cannot create team bounty for a team they don't belong to."""
        from apps.user_profile.services import bounty_service

        with self.assertRaises(PermissionDenied):
            bounty_service.create_bounty(
                creator=self.user_a,
                title="Wrong Team",
                game=self.game,
                stake_amount=500,
                challenge_type=BountyType.TEAM,
                creator_team=self.team_b,
            )

    def test_create_solo_bounty_still_works(self):
        """Solo bounties still work normally with team fields as None."""
        from apps.user_profile.services import bounty_service

        bounty = bounty_service.create_bounty(
            creator=self.user_a,
            title="1v1 Aim Duel",
            game=self.game,
            stake_amount=300,
            challenge_type=BountyType.SOLO,
        )
        assert bounty.challenge_type == BountyType.SOLO
        assert bounty.creator_team is None
        assert bounty.acceptor_team is None


class BountyServiceTeamAcceptTest(TestCase):
    """Test accept_bounty() with team challenge validation."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="accept_creator", email="ac@test.com", password="pass123"
        )
        self.user_b = User.objects.create_user(
            username="accept_opponent", email="ao@test.com", password="pass123"
        )

        from apps.user_profile.models import UserProfile
        from apps.economy.models import DeltaCrownWallet

        self.profile_a = UserProfile.objects.get(user=self.user_a)
        self.profile_b = UserProfile.objects.get(user=self.user_b)

        self.wallet_a, _ = DeltaCrownWallet.objects.get_or_create(
            profile=self.profile_a
        )
        self.wallet_a.cached_balance = 5000
        self.wallet_a.save()

        self.wallet_b, _ = DeltaCrownWallet.objects.get_or_create(
            profile=self.profile_b
        )
        self.wallet_b.cached_balance = 5000
        self.wallet_b.save()

        from apps.games.models import Game, GameRosterConfig

        self.game = Game.objects.create(
            name="CS2",
            display_name="Counter-Strike 2",
            slug="cs2-ab",
            short_code="CAB",
            is_active=True,
        )
        GameRosterConfig.objects.create(
            game=self.game,
            max_team_size=5,
        )

        from apps.organizations.models.team import Team
        from apps.organizations.models.membership import TeamMembership

        self.team_a = Team.objects.create(
            name="Team Accept A",
            slug="team-accept-a",
            game_id=self.game.id,
            region="NA",
            created_by=self.user_a,
        )
        self.team_b = Team.objects.create(
            name="Team Accept B",
            slug="team-accept-b",
            game_id=self.game.id,
            region="EU",
            created_by=self.user_b,
        )

        TeamMembership.objects.create(
            team=self.team_a,
            user=self.user_a,
            role="OWNER",
            status="ACTIVE",
            game_id=self.game.id,
        )
        TeamMembership.objects.create(
            team=self.team_b,
            user=self.user_b,
            role="OWNER",
            status="ACTIVE",
            game_id=self.game.id,
        )

        # Create team bounty
        from apps.user_profile.services import bounty_service

        self.team_bounty = bounty_service.create_bounty(
            creator=self.user_a,
            title="Team Showdown",
            game=self.game,
            stake_amount=500,
            challenge_type=BountyType.TEAM,
            creator_team=self.team_a,
        )

    def test_accept_team_bounty_success(self):
        """Team bounty accepted with valid opponent team."""
        from apps.user_profile.services import bounty_service

        result = bounty_service.accept_bounty(
            bounty=self.team_bounty,
            acceptor=self.user_b,
            acceptor_team=self.team_b,
        )
        self.team_bounty.refresh_from_db()
        assert self.team_bounty.status == BountyStatus.ACCEPTED
        assert self.team_bounty.acceptor == self.user_b
        assert self.team_bounty.acceptor_team == self.team_b

    def test_accept_team_bounty_without_team_fails(self):
        """Cannot accept team bounty without specifying a team."""
        from apps.user_profile.services import bounty_service

        with self.assertRaises(ValidationError):
            bounty_service.accept_bounty(
                bounty=self.team_bounty,
                acceptor=self.user_b,
                acceptor_team=None,
            )

    def test_accept_own_team_bounty_fails(self):
        """Cannot accept your own team's bounty."""
        from apps.user_profile.services import bounty_service

        with self.assertRaises(ValidationError):
            bounty_service.accept_bounty(
                bounty=self.team_bounty,
                acceptor=self.user_a,
                acceptor_team=self.team_a,
            )
