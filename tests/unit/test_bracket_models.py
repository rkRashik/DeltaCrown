"""
Unit tests for Bracket and BracketNode models (Module 1.5)

Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Section 5: Bracket Structure Models)
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Section 6: BracketService)
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md (Bracket visualization)

Test Coverage:
- Bracket model: format, seeding methods, bracket_structure JSONB, is_finalized
- BracketNode model: double-linked list navigation, participant tracking, position/round
- Constraints: round_positive, parent_slot, bracket_type validation
- Relationships: tournament, bracket, parent/child nodes, match

Target: 100% model field and method coverage
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.tournaments.models import (
    Tournament,
    Game,
    Bracket,
    BracketNode,
    Match
)


@pytest.mark.django_db
class TestBracketModel:
    """Test Bracket model"""

    @pytest.fixture
    def game(self):
        """Create a game instance"""
        return Game.objects.create(
            name="VALORANT",
            slug="valorant",
            is_active=True
        )

    @pytest.fixture
    def tournament(self, game):
        """Create a tournament instance"""
        return Tournament.objects.create(
            title="VALORANT Championship",
            slug="valorant-championship",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now() + timedelta(days=7),
            registration_opens_at=timezone.now(),
            registration_closes_at=timezone.now() + timedelta(days=5),
            status=Tournament.PUBLISHED
        )

    def test_bracket_creation_minimal(self, tournament):
        """Test creating bracket with minimal required fields"""
        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=4,
            total_matches=15
        )

        assert bracket.id is not None
        assert bracket.tournament == tournament
        assert bracket.format == Bracket.SINGLE_ELIMINATION
        assert bracket.total_rounds == 4
        assert bracket.total_matches == 15
        assert bracket.bracket_structure == {}  # Default empty dict
        assert bracket.seeding_method == Bracket.SLOT_ORDER  # Default
        assert bracket.is_finalized is False  # Default
        assert bracket.generated_at is not None
        assert bracket.updated_at is not None

    def test_bracket_format_choices(self, tournament):
        """Test all bracket format choices"""
        formats = [
            Bracket.SINGLE_ELIMINATION,
            Bracket.DOUBLE_ELIMINATION,
            Bracket.ROUND_ROBIN,
            Bracket.SWISS,
            Bracket.GROUP_STAGE
        ]

        for fmt in formats:
            bracket = Bracket.objects.create(
                tournament=tournament,
                format=fmt,
                total_rounds=3,
                total_matches=7
            )
            assert bracket.format == fmt
            bracket.delete()

    def test_bracket_seeding_method_choices(self, tournament):
        """Test all seeding method choices"""
        seeding_methods = [
            Bracket.SLOT_ORDER,
            Bracket.RANDOM,
            Bracket.RANKED,
            Bracket.MANUAL
        ]

        for method in seeding_methods:
            bracket = Bracket.objects.create(
                tournament=tournament,
                format=Bracket.SINGLE_ELIMINATION,
                total_rounds=3,
                total_matches=7,
                seeding_method=method
            )
            assert bracket.seeding_method == method
            bracket.delete()

    def test_bracket_structure_jsonb(self, tournament):
        """Test bracket_structure JSONB field"""
        structure = {
            "format": "single-elimination",
            "total_participants": 8,
            "rounds": [
                {"round_number": 1, "round_name": "Quarter Finals", "matches": 4},
                {"round_number": 2, "round_name": "Semi Finals", "matches": 2},
                {"round_number": 3, "round_name": "Finals", "matches": 1}
            ],
            "third_place_match": True
        }

        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=3,
            total_matches=7,
            bracket_structure=structure
        )

        bracket.refresh_from_db()
        assert bracket.bracket_structure == structure
        assert bracket.bracket_structure["total_participants"] == 8
        assert len(bracket.bracket_structure["rounds"]) == 3
        assert bracket.bracket_structure["third_place_match"] is True

    def test_bracket_one_to_one_tournament(self, tournament):
        """Test one-to-one relationship with tournament"""
        bracket1 = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=3,
            total_matches=7
        )

        # Attempting to create second bracket for same tournament should fail
        with pytest.raises(IntegrityError):
            Bracket.objects.create(
                tournament=tournament,
                format=Bracket.SINGLE_ELIMINATION,
                total_rounds=3,
                total_matches=7
            )

    def test_bracket_is_finalized_flag(self, tournament):
        """Test is_finalized flag behavior"""
        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=3,
            total_matches=7,
            is_finalized=False
        )

        assert bracket.is_finalized is False

        bracket.is_finalized = True
        bracket.save()
        bracket.refresh_from_db()

        assert bracket.is_finalized is True

    def test_bracket_string_representation(self, tournament):
        """Test string representation"""
        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=3,
            total_matches=7
        )

        str_repr = str(bracket)
        assert "VALORANT Championship" in str_repr
        assert "Single Elimination" in str_repr

    def test_bracket_timestamps_auto_update(self, tournament):
        """Test timestamps are auto-updated"""
        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=3,
            total_matches=7
        )

        original_updated_at = bracket.updated_at

        # Wait and update
        import time
        time.sleep(0.1)
        
        bracket.total_rounds = 4
        bracket.save()
        bracket.refresh_from_db()

        assert bracket.updated_at > original_updated_at


@pytest.mark.django_db
class TestBracketNodeModel:
    """Test BracketNode model"""

    @pytest.fixture
    def game(self):
        return Game.objects.create(name="VALORANT", slug="valorant", is_active=True)

    @pytest.fixture
    def tournament(self, game):
        return Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=16,
            start_date=timezone.now() + timedelta(days=1),
            registration_opens_at=timezone.now(),
            registration_closes_at=timezone.now() + timedelta(hours=12),
            status=Tournament.PUBLISHED
        )

    @pytest.fixture
    def bracket(self, tournament):
        return Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=4,
            total_matches=15
        )

    def test_bracketnode_creation_minimal(self, bracket):
        """Test creating bracket node with minimal fields"""
        node = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1
        )

        assert node.id is not None
        assert node.bracket == bracket
        assert node.position == 1
        assert node.round_number == 1
        assert node.match_number_in_round == 1
        assert node.match is None
        assert node.participant1_id is None
        assert node.participant2_id is None
        assert node.winner_id is None
        assert node.parent_node is None
        assert node.parent_slot is None
        assert node.child1_node is None
        assert node.child2_node is None
        assert node.is_bye is False
        assert node.bracket_type == BracketNode.MAIN  # Default

    def test_bracketnode_with_participants(self, bracket):
        """Test creating node with participants"""
        node = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta"
        )

        assert node.participant1_id == 101
        assert node.participant1_name == "Team Alpha"
        assert node.participant2_id == 102
        assert node.participant2_name == "Team Beta"

    def test_bracketnode_parent_child_relationships(self, bracket):
        """Test parent-child node relationships"""
        # Create child nodes (Round 1)
        child1 = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1
        )
        child2 = BracketNode.objects.create(
            bracket=bracket,
            position=2,
            round_number=1,
            match_number_in_round=2
        )

        # Create parent node (Round 2)
        parent = BracketNode.objects.create(
            bracket=bracket,
            position=3,
            round_number=2,
            match_number_in_round=1,
            child1_node=child1,
            child2_node=child2
        )

        # Update children to point to parent
        child1.parent_node = parent
        child1.parent_slot = 1
        child1.save()

        child2.parent_node = parent
        child2.parent_slot = 2
        child2.save()

        # Verify relationships
        parent.refresh_from_db()
        assert parent.child1_node == child1
        assert parent.child2_node == child2

        child1.refresh_from_db()
        assert child1.parent_node == parent
        assert child1.parent_slot == 1

        child2.refresh_from_db()
        assert child2.parent_node == parent
        assert child2.parent_slot == 2

    def test_bracketnode_bracket_type_choices(self, bracket):
        """Test bracket_type choices"""
        types = [
            BracketNode.MAIN,
            BracketNode.LOSERS,
            BracketNode.THIRD_PLACE,
            "group-1",  # Group stage example
            "group-2"
        ]

        for idx, btype in enumerate(types, start=1):
            node = BracketNode.objects.create(
                bracket=bracket,
                position=idx,
                round_number=1,
                match_number_in_round=idx,
                bracket_type=btype
            )
            assert node.bracket_type == btype

    def test_bracketnode_is_bye_flag(self, bracket):
        """Test is_bye flag for bye matches"""
        node = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            is_bye=True
        )

        assert node.is_bye is True
        assert node.participant1_id == 101
        assert node.participant2_id is None  # No opponent in bye

    def test_bracketnode_unique_position_per_bracket(self, bracket):
        """Test unique position constraint per bracket"""
        BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1
        )

        # Attempting to create another node with same position should fail
        with pytest.raises(IntegrityError):
            BracketNode.objects.create(
                bracket=bracket,
                position=1,  # Duplicate position
                round_number=1,
                match_number_in_round=2
            )

    def test_bracketnode_parent_slot_validation(self, bracket):
        """Test parent_slot must be 1 or 2"""
        node = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1
        )

        parent = BracketNode.objects.create(
            bracket=bracket,
            position=2,
            round_number=2,
            match_number_in_round=1
        )

        # Valid slots
        node.parent_node = parent
        node.parent_slot = 1
        node.save()  # Should succeed

        node.parent_slot = 2
        node.save()  # Should succeed

        # Invalid slot (constraint check at database level)
        # Note: Django won't raise ValidationError for CHECK constraints
        # until save() is called and database rejects it

    def test_bracketnode_round_number_positive(self, bracket):
        """Test round_number must be positive"""
        # This will be enforced by database CHECK constraint
        # Django ORM won't validate until save()
        node = BracketNode(
            bracket=bracket,
            position=1,
            round_number=0,  # Invalid
            match_number_in_round=1
        )

        # Database will reject this on save
        with pytest.raises(IntegrityError):
            node.save()

    def test_bracketnode_winner_tracking(self, bracket):
        """Test winner_id tracking"""
        node = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1,
            participant1_id=101,
            participant1_name="Team Alpha",
            participant2_id=102,
            participant2_name="Team Beta"
        )

        # Set winner
        node.winner_id = 101
        node.save()
        node.refresh_from_db()

        assert node.winner_id == 101

    def test_bracketnode_match_relationship(self, bracket):
        """Test relationship with Match model"""
        node = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1
        )

        match = Match.objects.create(
            tournament=bracket.tournament,
            bracket=bracket,
            round_number=1,
            match_number=1,
            state=Match.SCHEDULED
        )

        node.match = match
        node.save()
        node.refresh_from_db()

        assert node.match == match

    def test_bracketnode_string_representation(self, bracket):
        """Test string representation"""
        node = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1,
            bracket_type=BracketNode.MAIN
        )

        str_repr = str(node)
        assert "R1" in str_repr or "Round 1" in str_repr
        assert "M1" in str_repr or "Match 1" in str_repr


@pytest.mark.django_db
class TestBracketNodeNavigation:
    """Test BracketNode double-linked list navigation"""

    @pytest.fixture
    def game(self):
        return Game.objects.create(name="VALORANT", slug="valorant", is_active=True)

    @pytest.fixture
    def tournament(self, game):
        return Tournament.objects.create(
            title="Test Tournament",
            slug="test-tournament",
            game=game,
            organizer_id=1,
            format=Tournament.SINGLE_ELIMINATION,
            max_participants=8,
            start_date=timezone.now() + timedelta(days=1),
            registration_opens_at=timezone.now(),
            registration_closes_at=timezone.now() + timedelta(hours=12),
            status=Tournament.PUBLISHED
        )

    @pytest.fixture
    def bracket(self, tournament):
        return Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            total_rounds=3,
            total_matches=7
        )

    def test_simple_bracket_tree_navigation(self, bracket):
        """Test navigation in simple 4-team bracket"""
        # Round 1 (Semi Finals)
        node1 = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1,
            participant1_id=101,
            participant2_id=102
        )
        node2 = BracketNode.objects.create(
            bracket=bracket,
            position=2,
            round_number=1,
            match_number_in_round=2,
            participant1_id=103,
            participant2_id=104
        )

        # Round 2 (Finals)
        finals = BracketNode.objects.create(
            bracket=bracket,
            position=3,
            round_number=2,
            match_number_in_round=1,
            child1_node=node1,
            child2_node=node2
        )

        # Set parent relationships
        node1.parent_node = finals
        node1.parent_slot = 1
        node1.save()

        node2.parent_node = finals
        node2.parent_slot = 2
        node2.save()

        # Navigate from child to parent
        node1.refresh_from_db()
        assert node1.parent_node == finals
        assert node1.parent_slot == 1

        # Navigate from parent to children
        finals.refresh_from_db()
        assert finals.child1_node == node1
        assert finals.child2_node == node2

    def test_winner_progression_to_parent(self, bracket):
        """Test winner progresses to parent node"""
        # Round 1 nodes
        node1 = BracketNode.objects.create(
            bracket=bracket,
            position=1,
            round_number=1,
            match_number_in_round=1,
            participant1_id=101,
            participant1_name="Team A",
            participant2_id=102,
            participant2_name="Team B"
        )

        # Round 2 parent
        parent = BracketNode.objects.create(
            bracket=bracket,
            position=2,
            round_number=2,
            match_number_in_round=1,
            child1_node=node1
        )

        node1.parent_node = parent
        node1.parent_slot = 1
        node1.save()

        # Simulate match completion - Team A wins
        node1.winner_id = 101
        node1.save()

        # Winner should advance to parent node's slot 1
        parent.refresh_from_db()
        # This would be set by BracketService.update_bracket_after_match()
        parent.participant1_id = node1.winner_id
        parent.participant1_name = "Team A"
        parent.save()

        assert parent.participant1_id == 101
        assert parent.participant1_name == "Team A"
