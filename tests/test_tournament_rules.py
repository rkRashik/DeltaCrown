"""
TournamentRules Model Tests
Comprehensive test suite for TournamentRules model and rules helper functions.

Test Coverage:
- Model creation and validation
- Age restriction validation
- Rule section property methods
- Requirement flags
- Restriction checks
- Helper functions (rule access, requirements, restrictions)
- Query optimization
- Integration scenarios
- Edge cases
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.tournaments.models import Tournament, TournamentRules
from apps.tournaments.utils import rules_helpers


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def base_tournament(db):
    """Create a basic tournament for testing"""
    return Tournament.objects.create(
        name="Test Tournament",
        slug="test-tournament",
        game="valorant",
        status="DRAFT"
    )


@pytest.fixture
def basic_rules(db):
    """Create tournament with basic rules"""
    tournament = Tournament.objects.create(
        name="Tournament with Basic Rules",
        slug="tournament-basic-rules",
        game="valorant",
        status="DRAFT"
    )
    return TournamentRules.objects.create(
        tournament=tournament,
        general_rules="<p>Be respectful to all players</p>",
        eligibility_requirements="<p>Open to all</p>",
        match_rules="<p>Best of 3</p>"
    )


@pytest.fixture
def complete_rules(db):
    """Create tournament with complete rules"""
    tournament = Tournament.objects.create(
        name="Tournament with Complete Rules",
        slug="tournament-complete-rules",
        game="valorant",
        status="DRAFT"
    )
    return TournamentRules.objects.create(
        tournament=tournament,
        general_rules="<p>General tournament rules</p>",
        eligibility_requirements="<p>Must be 18+</p>",
        match_rules="<p>Best of 5 finals</p>",
        scoring_system="<p>Points based on kills</p>",
        penalty_rules="<p>Cheating = disqualification</p>",
        prize_distribution_rules="<p>Top 3 get prizes</p>",
        additional_notes="<p>Good luck!</p>",
        checkin_instructions="<p>Check in 30 mins before</p>",
        require_discord=True,
        require_game_id=True,
        require_team_logo=True,
        min_age=18,
        max_age=35,
        region_restriction="Bangladesh only",
        rank_restriction="Gold and above"
    )


@pytest.fixture
def age_restricted_rules(db):
    """Create tournament with age restrictions only"""
    tournament = Tournament.objects.create(
        name="Age Restricted Tournament",
        slug="age-restricted",
        game="valorant",
        status="DRAFT"
    )
    return TournamentRules.objects.create(
        tournament=tournament,
        min_age=16,
        max_age=25
    )


# ============================================================================
# TEST CLASS 1: MODEL CREATION AND VALIDATION
# ============================================================================

@pytest.mark.django_db
class TestTournamentRulesModel:
    """Test TournamentRules model creation and validation"""
    
    def test_create_empty_rules(self, base_tournament):
        """Test creating rules record with no content"""
        rules = TournamentRules.objects.create(tournament=base_tournament)
        
        assert rules.tournament == base_tournament
        assert not rules.has_general_rules
        assert not rules.has_complete_rules
        assert rules.populated_sections_count == 0
    
    def test_create_rules_with_content(self, basic_rules):
        """Test creating rules with content"""
        assert basic_rules.has_general_rules
        assert basic_rules.has_eligibility_requirements
        assert basic_rules.has_match_rules
        assert basic_rules.has_complete_rules
    
    def test_one_to_one_relationship(self, base_tournament):
        """Test that tournament can only have one rules record"""
        TournamentRules.objects.create(tournament=base_tournament)
        
        # Try to create second rules record for same tournament
        with pytest.raises(IntegrityError):
            TournamentRules.objects.create(tournament=base_tournament)
    
    def test_rules_str_representation(self, basic_rules):
        """Test string representation"""
        assert "Rules for Tournament with Basic Rules" in str(basic_rules)
    
    def test_rules_ordering(self, basic_rules):
        """Test that rules are ordered by updated_at desc"""
        # Create another tournament and rules
        t2 = Tournament.objects.create(
            name="Tournament 2",
            slug="tournament-2",
            game="valorant",
            status="DRAFT"
        )
        rules2 = TournamentRules.objects.create(
            tournament=t2,
            general_rules="<p>Rules 2</p>"
        )
        
        # Most recent should be first
        all_rules = TournamentRules.objects.all()
        assert all_rules[0] == rules2
        assert all_rules[1] == basic_rules


# ============================================================================
# TEST CLASS 2: AGE VALIDATION
# ============================================================================

@pytest.mark.django_db
class TestAgeValidation:
    """Test age restriction validation"""
    
    def test_valid_age_range(self, base_tournament):
        """Test creating rules with valid age range"""
        rules = TournamentRules(
            tournament=base_tournament,
            min_age=18,
            max_age=35
        )
        rules.clean()  # Should not raise
        rules.save()
        
        assert rules.min_age == 18
        assert rules.max_age == 35
    
    def test_negative_min_age_rejected(self, base_tournament):
        """Test that negative min_age is rejected"""
        rules = TournamentRules(
            tournament=base_tournament,
            min_age=-1
        )
        
        with pytest.raises(ValidationError) as exc_info:
            rules.clean()
        
        assert 'min_age' in exc_info.value.error_dict
    
    def test_negative_max_age_rejected(self, base_tournament):
        """Test that negative max_age is rejected"""
        rules = TournamentRules(
            tournament=base_tournament,
            max_age=-5
        )
        
        with pytest.raises(ValidationError) as exc_info:
            rules.clean()
        
        assert 'max_age' in exc_info.value.error_dict
    
    def test_min_age_greater_than_max_age_rejected(self, base_tournament):
        """Test that min_age > max_age is rejected"""
        rules = TournamentRules(
            tournament=base_tournament,
            min_age=40,
            max_age=30
        )
        
        with pytest.raises(ValidationError) as exc_info:
            rules.clean()
        
        assert 'max_age' in exc_info.value.error_dict
    
    def test_unreasonably_high_min_age_rejected(self, base_tournament):
        """Test that unreasonably high min_age is rejected"""
        rules = TournamentRules(
            tournament=base_tournament,
            min_age=150
        )
        
        with pytest.raises(ValidationError) as exc_info:
            rules.clean()
        
        assert 'min_age' in exc_info.value.error_dict
    
    def test_unreasonably_high_max_age_rejected(self, base_tournament):
        """Test that unreasonably high max_age is rejected"""
        rules = TournamentRules(
            tournament=base_tournament,
            max_age=200
        )
        
        with pytest.raises(ValidationError) as exc_info:
            rules.clean()
        
        assert 'max_age' in exc_info.value.error_dict
    
    def test_equal_min_max_age_allowed(self, base_tournament):
        """Test that min_age == max_age is allowed"""
        rules = TournamentRules(
            tournament=base_tournament,
            min_age=25,
            max_age=25
        )
        rules.clean()  # Should not raise
        rules.save()
        
        assert rules.min_age == 25
        assert rules.max_age == 25


# ============================================================================
# TEST CLASS 3: PROPERTY METHODS
# ============================================================================

@pytest.mark.django_db
class TestRulesPropertyMethods:
    """Test property methods on TournamentRules model"""
    
    def test_has_rule_section_properties(self, complete_rules):
        """Test has_* properties for rule sections"""
        assert complete_rules.has_general_rules
        assert complete_rules.has_eligibility_requirements
        assert complete_rules.has_match_rules
        assert complete_rules.has_scoring_system
        assert complete_rules.has_penalty_rules
        assert complete_rules.has_prize_distribution_rules
        assert complete_rules.has_additional_notes
        assert complete_rules.has_checkin_instructions
    
    def test_has_age_restrictions_property(self, age_restricted_rules):
        """Test has_age_restrictions property"""
        assert age_restricted_rules.has_age_restrictions
    
    def test_has_region_restriction_property(self, complete_rules):
        """Test has_region_restriction property"""
        assert complete_rules.has_region_restriction
    
    def test_has_rank_restriction_property(self, complete_rules):
        """Test has_rank_restriction property"""
        assert complete_rules.has_rank_restriction
    
    def test_has_any_restrictions_property(self, complete_rules):
        """Test has_any_restrictions property"""
        assert complete_rules.has_any_restrictions
    
    def test_has_complete_rules_property(self, basic_rules):
        """Test has_complete_rules property"""
        assert basic_rules.has_complete_rules
    
    def test_age_range_text_both_ages(self, age_restricted_rules):
        """Test age_range_text with both min and max"""
        assert age_restricted_rules.age_range_text == "16-25 years"
    
    def test_age_range_text_min_only(self, base_tournament):
        """Test age_range_text with only min_age"""
        rules = TournamentRules.objects.create(
            tournament=base_tournament,
            min_age=18
        )
        assert rules.age_range_text == "18+ years"
    
    def test_age_range_text_max_only(self, base_tournament):
        """Test age_range_text with only max_age"""
        rules = TournamentRules.objects.create(
            tournament=base_tournament,
            max_age=16
        )
        assert rules.age_range_text == "Under 16 years"
    
    def test_age_range_text_none(self, base_tournament):
        """Test age_range_text with no age restrictions"""
        rules = TournamentRules.objects.create(tournament=base_tournament)
        assert rules.age_range_text is None
    
    def test_get_rule_sections(self, complete_rules):
        """Test get_rule_sections method"""
        sections = complete_rules.get_rule_sections()
        
        assert 'general_rules' in sections
        assert 'eligibility_requirements' in sections
        assert 'match_rules' in sections
        assert sections['general_rules'] is not None
    
    def test_get_requirements(self, complete_rules):
        """Test get_requirements method"""
        requirements = complete_rules.get_requirements()
        
        assert requirements['require_discord'] is True
        assert requirements['require_game_id'] is True
        assert requirements['require_team_logo'] is True
    
    def test_get_restrictions(self, complete_rules):
        """Test get_restrictions method"""
        restrictions = complete_rules.get_restrictions()
        
        assert restrictions['min_age'] == 18
        assert restrictions['max_age'] == 35
        assert restrictions['age_range'] == "18-35 years"
        assert restrictions['region'] == "Bangladesh only"
        assert restrictions['rank'] == "Gold and above"
    
    def test_get_populated_sections(self, complete_rules):
        """Test get_populated_sections method"""
        sections = complete_rules.get_populated_sections()
        
        assert 'general_rules' in sections
        assert 'eligibility_requirements' in sections
        assert len(sections) == 8  # All 8 sections have content
    
    def test_populated_sections_count(self, complete_rules):
        """Test populated_sections_count property"""
        assert complete_rules.populated_sections_count == 8


# ============================================================================
# TEST CLASS 4: HELPER RULE SECTION ACCESS
# ============================================================================

@pytest.mark.django_db
class TestRuleSectionAccessHelpers:
    """Test rule section access helper functions"""
    
    def test_get_general_rules(self, basic_rules):
        """Test get_general_rules helper"""
        rules_text = rules_helpers.get_general_rules(basic_rules.tournament)
        assert rules_text is not None
        assert "Be respectful" in rules_text
    
    def test_get_general_rules_none(self, base_tournament):
        """Test get_general_rules returns None when no rules"""
        rules_text = rules_helpers.get_general_rules(base_tournament)
        assert rules_text is None
    
    def test_get_eligibility_requirements(self, basic_rules):
        """Test get_eligibility_requirements helper"""
        req_text = rules_helpers.get_eligibility_requirements(basic_rules.tournament)
        assert req_text is not None
    
    def test_get_match_rules(self, basic_rules):
        """Test get_match_rules helper"""
        match_rules = rules_helpers.get_match_rules(basic_rules.tournament)
        assert match_rules is not None
        assert "Best of 3" in match_rules
    
    def test_get_scoring_system(self, complete_rules):
        """Test get_scoring_system helper"""
        scoring = rules_helpers.get_scoring_system(complete_rules.tournament)
        assert scoring is not None
    
    def test_get_penalty_rules(self, complete_rules):
        """Test get_penalty_rules helper"""
        penalties = rules_helpers.get_penalty_rules(complete_rules.tournament)
        assert penalties is not None
    
    def test_get_prize_distribution_rules(self, complete_rules):
        """Test get_prize_distribution_rules helper"""
        prize_rules = rules_helpers.get_prize_distribution_rules(complete_rules.tournament)
        assert prize_rules is not None
    
    def test_get_additional_notes(self, complete_rules):
        """Test get_additional_notes helper"""
        notes = rules_helpers.get_additional_notes(complete_rules.tournament)
        assert notes is not None
    
    def test_get_checkin_instructions(self, complete_rules):
        """Test get_checkin_instructions helper"""
        instructions = rules_helpers.get_checkin_instructions(complete_rules.tournament)
        assert instructions is not None


# ============================================================================
# TEST CLASS 5: HELPER REQUIREMENT CHECKS
# ============================================================================

@pytest.mark.django_db
class TestRequirementCheckHelpers:
    """Test requirement check helper functions"""
    
    def test_requires_discord(self, complete_rules):
        """Test requires_discord helper"""
        assert rules_helpers.requires_discord(complete_rules.tournament) is True
    
    def test_requires_discord_false(self, basic_rules):
        """Test requires_discord returns False by default"""
        assert rules_helpers.requires_discord(basic_rules.tournament) is False
    
    def test_requires_game_id(self, complete_rules):
        """Test requires_game_id helper"""
        assert rules_helpers.requires_game_id(complete_rules.tournament) is True
    
    def test_requires_game_id_default_true(self, base_tournament):
        """Test requires_game_id defaults to True"""
        assert rules_helpers.requires_game_id(base_tournament) is True
    
    def test_requires_team_logo(self, complete_rules):
        """Test requires_team_logo helper"""
        assert rules_helpers.requires_team_logo(complete_rules.tournament) is True
    
    def test_get_requirements(self, complete_rules):
        """Test get_requirements helper"""
        requirements = rules_helpers.get_requirements(complete_rules.tournament)
        
        assert requirements['require_discord'] is True
        assert requirements['require_game_id'] is True
        assert requirements['require_team_logo'] is True


# ============================================================================
# TEST CLASS 6: HELPER RESTRICTION CHECKS
# ============================================================================

@pytest.mark.django_db
class TestRestrictionCheckHelpers:
    """Test restriction check helper functions"""
    
    def test_get_min_age(self, age_restricted_rules):
        """Test get_min_age helper"""
        assert rules_helpers.get_min_age(age_restricted_rules.tournament) == 16
    
    def test_get_max_age(self, age_restricted_rules):
        """Test get_max_age helper"""
        assert rules_helpers.get_max_age(age_restricted_rules.tournament) == 25
    
    def test_get_age_range_text(self, age_restricted_rules):
        """Test get_age_range_text helper"""
        assert rules_helpers.get_age_range_text(age_restricted_rules.tournament) == "16-25 years"
    
    def test_get_region_restriction(self, complete_rules):
        """Test get_region_restriction helper"""
        assert rules_helpers.get_region_restriction(complete_rules.tournament) == "Bangladesh only"
    
    def test_get_rank_restriction(self, complete_rules):
        """Test get_rank_restriction helper"""
        assert rules_helpers.get_rank_restriction(complete_rules.tournament) == "Gold and above"
    
    def test_has_age_restrictions(self, age_restricted_rules):
        """Test has_age_restrictions helper"""
        assert rules_helpers.has_age_restrictions(age_restricted_rules.tournament) is True
    
    def test_has_region_restriction(self, complete_rules):
        """Test has_region_restriction helper"""
        assert rules_helpers.has_region_restriction(complete_rules.tournament) is True
    
    def test_has_rank_restriction(self, complete_rules):
        """Test has_rank_restriction helper"""
        assert rules_helpers.has_rank_restriction(complete_rules.tournament) is True
    
    def test_has_any_restrictions(self, complete_rules):
        """Test has_any_restrictions helper"""
        assert rules_helpers.has_any_restrictions(complete_rules.tournament) is True
    
    def test_has_any_restrictions_false(self, basic_rules):
        """Test has_any_restrictions returns False"""
        assert rules_helpers.has_any_restrictions(basic_rules.tournament) is False
    
    def test_get_restrictions(self, complete_rules):
        """Test get_restrictions helper"""
        restrictions = rules_helpers.get_restrictions(complete_rules.tournament)
        
        assert restrictions['min_age'] == 18
        assert restrictions['max_age'] == 35
        assert restrictions['age_range'] == "18-35 years"
        assert restrictions['region'] == "Bangladesh only"
        assert restrictions['rank'] == "Gold and above"


# ============================================================================
# TEST CLASS 7: HELPER BOOLEAN CHECKS
# ============================================================================

@pytest.mark.django_db
class TestBooleanCheckHelpers:
    """Test boolean check helper functions"""
    
    def test_has_general_rules(self, basic_rules):
        """Test has_general_rules helper"""
        assert rules_helpers.has_general_rules(basic_rules.tournament) is True
    
    def test_has_eligibility_requirements(self, basic_rules):
        """Test has_eligibility_requirements helper"""
        assert rules_helpers.has_eligibility_requirements(basic_rules.tournament) is True
    
    def test_has_match_rules(self, basic_rules):
        """Test has_match_rules helper"""
        assert rules_helpers.has_match_rules(basic_rules.tournament) is True
    
    def test_has_scoring_system(self, complete_rules):
        """Test has_scoring_system helper"""
        assert rules_helpers.has_scoring_system(complete_rules.tournament) is True
    
    def test_has_penalty_rules(self, complete_rules):
        """Test has_penalty_rules helper"""
        assert rules_helpers.has_penalty_rules(complete_rules.tournament) is True
    
    def test_has_prize_distribution_rules(self, complete_rules):
        """Test has_prize_distribution_rules helper"""
        assert rules_helpers.has_prize_distribution_rules(complete_rules.tournament) is True
    
    def test_has_additional_notes(self, complete_rules):
        """Test has_additional_notes helper"""
        assert rules_helpers.has_additional_notes(complete_rules.tournament) is True
    
    def test_has_checkin_instructions(self, complete_rules):
        """Test has_checkin_instructions helper"""
        assert rules_helpers.has_checkin_instructions(complete_rules.tournament) is True
    
    def test_has_complete_rules(self, basic_rules):
        """Test has_complete_rules helper"""
        assert rules_helpers.has_complete_rules(basic_rules.tournament) is True
    
    def test_has_complete_rules_false(self, base_tournament):
        """Test has_complete_rules returns False when incomplete"""
        # Create rules with only general_rules (missing eligibility and match rules)
        TournamentRules.objects.create(
            tournament=base_tournament,
            general_rules="<p>Some rules</p>"
        )
        assert rules_helpers.has_complete_rules(base_tournament) is False


# ============================================================================
# TEST CLASS 8: HELPER AGGREGATE FUNCTIONS
# ============================================================================

@pytest.mark.django_db
class TestAggregateHelpers:
    """Test aggregate helper functions"""
    
    def test_get_rule_sections(self, complete_rules):
        """Test get_rule_sections helper"""
        sections = rules_helpers.get_rule_sections(complete_rules.tournament)
        
        assert 'general_rules' in sections
        assert 'eligibility_requirements' in sections
        assert 'match_rules' in sections
        assert sections['general_rules'] is not None
        assert len(sections) == 8
    
    def test_get_populated_sections(self, complete_rules):
        """Test get_populated_sections helper"""
        sections = rules_helpers.get_populated_sections(complete_rules.tournament)
        
        assert 'general_rules' in sections
        assert len(sections) == 8
    
    def test_get_populated_sections_count(self, complete_rules):
        """Test get_populated_sections_count helper"""
        count = rules_helpers.get_populated_sections_count(complete_rules.tournament)
        assert count == 8
    
    def test_get_rules_summary(self, complete_rules):
        """Test get_rules_summary helper"""
        summary = rules_helpers.get_rules_summary(complete_rules.tournament)
        
        assert summary['has_general_rules'] is True
        assert summary['has_complete_rules'] is True
        assert summary['populated_sections_count'] == 8
        assert summary['has_any_restrictions'] is True


# ============================================================================
# TEST CLASS 9: HELPER TEMPLATE CONTEXT
# ============================================================================

@pytest.mark.django_db
class TestTemplateContextHelpers:
    """Test template context helper"""
    
    def test_get_rules_context(self, complete_rules):
        """Test get_rules_context helper returns complete context"""
        context = rules_helpers.get_rules_context(complete_rules.tournament)
        
        # Check rule sections
        assert 'general_rules' in context
        assert 'eligibility_requirements' in context
        assert 'match_rules' in context
        
        # Check requirements
        assert 'require_discord' in context
        assert 'require_game_id' in context
        assert 'requirements' in context
        
        # Check restrictions
        assert 'min_age' in context
        assert 'max_age' in context
        assert 'age_range' in context
        assert 'restrictions' in context
        
        # Check boolean flags
        assert 'has_general_rules' in context
        assert 'has_complete_rules' in context
        assert 'has_any_restrictions' in context
        
        # Check counts and lists
        assert 'populated_sections' in context
        assert 'populated_sections_count' in context
        
        # Verify values
        assert context['has_general_rules'] is True
        assert context['require_discord'] is True
        assert context['min_age'] == 18
        assert context['populated_sections_count'] == 8


# ============================================================================
# TEST CLASS 10: QUERY OPTIMIZATION
# ============================================================================

@pytest.mark.django_db
class TestQueryOptimization:
    """Test query optimization helpers"""
    
    def test_optimize_queryset_for_rules(self, basic_rules):
        """Test optimize_queryset_for_rules reduces queries"""
        queryset = Tournament.objects.all()
        optimized = rules_helpers.optimize_queryset_for_rules(queryset)
        
        # Should have select_related
        assert 'rules' in str(optimized.query).lower()
    
    def test_get_tournaments_with_rules(self, basic_rules, base_tournament):
        """Test get_tournaments_with_rules filter"""
        queryset = Tournament.objects.all()
        with_rules = rules_helpers.get_tournaments_with_rules(queryset)
        
        assert basic_rules.tournament in with_rules
        assert base_tournament not in with_rules
    
    def test_get_tournaments_with_complete_rules(self, basic_rules, complete_rules):
        """Test get_tournaments_with_complete_rules filter"""
        # Create tournament with incomplete rules
        t_incomplete = Tournament.objects.create(
            name="Incomplete",
            slug="incomplete",
            game="valorant",
            status="DRAFT"
        )
        TournamentRules.objects.create(
            tournament=t_incomplete,
            general_rules="<p>Only general rules</p>"
        )
        
        queryset = Tournament.objects.all()
        complete = rules_helpers.get_tournaments_with_complete_rules(queryset)
        
        # Both basic_rules and complete_rules have all 3 essential sections
        assert basic_rules.tournament in complete
        assert complete_rules.tournament in complete
        
        # incomplete only has general_rules
        assert t_incomplete not in complete
    
    def test_get_tournaments_with_restrictions(self, complete_rules, basic_rules):
        """Test get_tournaments_with_restrictions filter"""
        queryset = Tournament.objects.all()
        with_restrictions = rules_helpers.get_tournaments_with_restrictions(queryset)
        
        # complete_rules has restrictions
        assert complete_rules.tournament in with_restrictions
        
        # basic_rules has no restrictions
        assert basic_rules.tournament not in with_restrictions
    
    def test_get_tournaments_requiring_discord(self, complete_rules, basic_rules):
        """Test get_tournaments_requiring_discord filter"""
        queryset = Tournament.objects.all()
        discord_required = rules_helpers.get_tournaments_requiring_discord(queryset)
        
        # complete_rules requires Discord
        assert complete_rules.tournament in discord_required
        
        # basic_rules doesn't require Discord
        assert basic_rules.tournament not in discord_required


# ============================================================================
# TEST CLASS 11: INTEGRATION SCENARIOS
# ============================================================================

@pytest.mark.django_db
class TestRulesIntegration:
    """Test complete integration scenarios"""
    
    def test_complete_tournament_rules_workflow(self, base_tournament):
        """Test complete workflow: create tournament, add rules, access via helpers"""
        # Create rules
        rules = TournamentRules.objects.create(
            tournament=base_tournament,
            general_rules="<p>General rules</p>",
            eligibility_requirements="<p>18+ only</p>",
            match_rules="<p>Best of 3</p>",
            require_discord=True,
            min_age=18
        )
        
        # Access via helpers
        assert rules_helpers.has_general_rules(base_tournament)
        assert rules_helpers.has_complete_rules(base_tournament)
        assert rules_helpers.requires_discord(base_tournament)
        assert rules_helpers.get_min_age(base_tournament) == 18
        
        # Get complete context
        context = rules_helpers.get_rules_context(base_tournament)
        assert context['general_rules'] is not None
        assert context['require_discord'] is True
        assert context['min_age'] == 18
    
    def test_tournament_without_rules_relationship(self, base_tournament):
        """Test helpers work when tournament has no rules record"""
        # No rules record created
        assert not rules_helpers.has_general_rules(base_tournament)
        assert not rules_helpers.has_complete_rules(base_tournament)
        assert rules_helpers.get_general_rules(base_tournament) is None
        
        context = rules_helpers.get_rules_context(base_tournament)
        assert context['general_rules'] is None
        assert context['has_general_rules'] is False


# ============================================================================
# TEST CLASS 12: EDGE CASES
# ============================================================================

@pytest.mark.django_db
class TestRulesEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_rules_with_no_tournament_fails(self):
        """Test that rules without tournament fails"""
        with pytest.raises(IntegrityError):
            TournamentRules.objects.create()
    
    def test_age_range_edge_cases(self, base_tournament):
        """Test age range edge cases"""
        # Zero age
        rules = TournamentRules.objects.create(
            tournament=base_tournament,
            min_age=0,
            max_age=100
        )
        assert rules.min_age == 0
        assert rules.age_range_text == "0-100 years"
    
    def test_empty_rule_sections(self, base_tournament):
        """Test rules with all empty sections"""
        rules = TournamentRules.objects.create(tournament=base_tournament)
        
        sections = rules.get_rule_sections()
        assert all(value is None for value in sections.values())
        
        assert rules.populated_sections_count == 0
        assert not rules.has_complete_rules
    
    def test_requirements_all_false(self, base_tournament):
        """Test requirements when all are False"""
        rules = TournamentRules.objects.create(
            tournament=base_tournament,
            require_discord=False,
            require_game_id=False,
            require_team_logo=False
        )
        
        requirements = rules.get_requirements()
        assert requirements['require_discord'] is False
        assert requirements['require_game_id'] is False
        assert requirements['require_team_logo'] is False
    
    def test_restrictions_all_none(self, base_tournament):
        """Test restrictions when all are None"""
        rules = TournamentRules.objects.create(tournament=base_tournament)
        
        assert not rules.has_age_restrictions
        assert not rules.has_region_restriction
        assert not rules.has_rank_restriction
        assert not rules.has_any_restrictions
        
        restrictions = rules.get_restrictions()
        assert restrictions['min_age'] is None
        assert restrictions['age_range'] is None
