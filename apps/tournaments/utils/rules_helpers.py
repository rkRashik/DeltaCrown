"""
TournamentRules Helper Functions
Helper utilities for accessing and managing tournament rules and requirements.

Part of Phase 1 - Core Tournament Models
These helpers provide backward compatibility and centralized logic.
"""

from typing import Optional, Dict, List
from django.db.models import QuerySet
from apps.tournaments.models.tournament import Tournament


# ============================================================================
# CATEGORY 1: RULE SECTION ACCESS HELPERS
# Direct field access with fallback support
# ============================================================================

def get_general_rules(tournament: Tournament) -> Optional[str]:
    """
    Get tournament general rules.
    
    Tries:
    1. rules.general_rules (new)
    2. None (no old field fallback)
    
    Returns:
        Rules text or None
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.general_rules
    return None


def get_eligibility_requirements(tournament: Tournament) -> Optional[str]:
    """
    Get tournament eligibility requirements.
    
    Returns:
        Requirements text or None
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.eligibility_requirements
    return None


def get_match_rules(tournament: Tournament) -> Optional[str]:
    """
    Get tournament match rules.
    
    Returns:
        Match rules text or None
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.match_rules
    return None


def get_scoring_system(tournament: Tournament) -> Optional[str]:
    """
    Get tournament scoring system.
    
    Returns:
        Scoring system text or None
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.scoring_system
    return None


def get_penalty_rules(tournament: Tournament) -> Optional[str]:
    """
    Get tournament penalty rules.
    
    Returns:
        Penalty rules text or None
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.penalty_rules
    return None


def get_prize_distribution_rules(tournament: Tournament) -> Optional[str]:
    """
    Get tournament prize distribution rules.
    
    Returns:
        Prize distribution rules text or None
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.prize_distribution_rules
    return None


def get_additional_notes(tournament: Tournament) -> Optional[str]:
    """
    Get tournament additional notes.
    
    Returns:
        Additional notes text or None
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.additional_notes
    return None


def get_checkin_instructions(tournament: Tournament) -> Optional[str]:
    """
    Get tournament check-in instructions.
    
    Returns:
        Check-in instructions text or None
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.checkin_instructions
    return None


# ============================================================================
# CATEGORY 2: REQUIREMENT CHECK HELPERS
# Check what's required for participation
# ============================================================================

def requires_discord(tournament: Tournament) -> bool:
    """Check if tournament requires Discord account"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.require_discord
    return False


def requires_game_id(tournament: Tournament) -> bool:
    """Check if tournament requires game account ID"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.require_game_id
    return True  # Default to True for safety


def requires_team_logo(tournament: Tournament) -> bool:
    """Check if tournament requires team logo"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.require_team_logo
    return False


def get_requirements(tournament: Tournament) -> Dict[str, bool]:
    """
    Get all requirement flags.
    
    Returns:
        Dict with requirement flags
    """
    return {
        'require_discord': requires_discord(tournament),
        'require_game_id': requires_game_id(tournament),
        'require_team_logo': requires_team_logo(tournament),
    }


# ============================================================================
# CATEGORY 3: RESTRICTION CHECK HELPERS
# Check age, region, and rank restrictions
# ============================================================================

def get_min_age(tournament: Tournament) -> Optional[int]:
    """Get minimum age requirement"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.min_age
    return None


def get_max_age(tournament: Tournament) -> Optional[int]:
    """Get maximum age requirement"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.max_age
    return None


def get_age_range_text(tournament: Tournament) -> Optional[str]:
    """
    Get formatted age range text.
    
    Returns:
        Formatted string like "18-25 years" or "18+ years"
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.age_range_text
    return None


def get_region_restriction(tournament: Tournament) -> Optional[str]:
    """Get region restriction text"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.region_restriction
    return None


def get_rank_restriction(tournament: Tournament) -> Optional[str]:
    """Get rank restriction text"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.rank_restriction
    return None


def has_age_restrictions(tournament: Tournament) -> bool:
    """Check if tournament has any age restrictions"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_age_restrictions
    return False


def has_region_restriction(tournament: Tournament) -> bool:
    """Check if tournament has region restrictions"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_region_restriction
    return False


def has_rank_restriction(tournament: Tournament) -> bool:
    """Check if tournament has rank restrictions"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_rank_restriction
    return False


def has_any_restrictions(tournament: Tournament) -> bool:
    """Check if tournament has any restrictions"""
    return (
        has_age_restrictions(tournament) or
        has_region_restriction(tournament) or
        has_rank_restriction(tournament)
    )


def get_restrictions(tournament: Tournament) -> Dict[str, any]:
    """
    Get all restrictions in a dictionary.
    
    Returns:
        Dict with all restriction data
    """
    return {
        'age_range': get_age_range_text(tournament),
        'min_age': get_min_age(tournament),
        'max_age': get_max_age(tournament),
        'region': get_region_restriction(tournament),
        'rank': get_rank_restriction(tournament),
    }


# ============================================================================
# CATEGORY 4: BOOLEAN CHECK HELPERS
# Check if rule sections exist
# ============================================================================

def has_general_rules(tournament: Tournament) -> bool:
    """Check if tournament has general rules"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_general_rules
    return False


def has_eligibility_requirements(tournament: Tournament) -> bool:
    """Check if tournament has eligibility requirements"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_eligibility_requirements
    return False


def has_match_rules(tournament: Tournament) -> bool:
    """Check if tournament has match rules"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_match_rules
    return False


def has_scoring_system(tournament: Tournament) -> bool:
    """Check if tournament has scoring system"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_scoring_system
    return False


def has_penalty_rules(tournament: Tournament) -> bool:
    """Check if tournament has penalty rules"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_penalty_rules
    return False


def has_prize_distribution_rules(tournament: Tournament) -> bool:
    """Check if tournament has prize distribution rules"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_prize_distribution_rules
    return False


def has_additional_notes(tournament: Tournament) -> bool:
    """Check if tournament has additional notes"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_additional_notes
    return False


def has_checkin_instructions(tournament: Tournament) -> bool:
    """Check if tournament has check-in instructions"""
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_checkin_instructions
    return False


def has_complete_rules(tournament: Tournament) -> bool:
    """
    Check if tournament has all essential rule sections.
    
    Essential sections: general_rules, eligibility_requirements, match_rules
    
    Returns:
        True if all essential sections exist
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.has_complete_rules
    return False


# ============================================================================
# CATEGORY 5: AGGREGATE HELPERS
# Get multiple related items at once
# ============================================================================

def get_rule_sections(tournament: Tournament) -> Dict[str, Optional[str]]:
    """
    Get all rule sections in a dictionary.
    
    Returns:
        Dict with all rule section content
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.get_rule_sections()
    
    return {
        'general_rules': None,
        'eligibility_requirements': None,
        'match_rules': None,
        'scoring_system': None,
        'penalty_rules': None,
        'prize_distribution_rules': None,
        'additional_notes': None,
        'checkin_instructions': None,
    }


def get_populated_sections(tournament: Tournament) -> List[str]:
    """
    Get list of section names that have content.
    
    Returns:
        List of section field names that have content
    """
    if hasattr(tournament, 'rules') and tournament.rules:
        return tournament.rules.get_populated_sections()
    return []


def get_populated_sections_count(tournament: Tournament) -> int:
    """
    Count how many rule sections have content.
    
    Returns:
        Number of sections with content (0-8)
    """
    return len(get_populated_sections(tournament))


def get_rules_summary(tournament: Tournament) -> Dict[str, any]:
    """
    Get summary of all rules data.
    
    Returns:
        Dict with boolean flags for each section and counts
    """
    return {
        'has_general_rules': has_general_rules(tournament),
        'has_eligibility_requirements': has_eligibility_requirements(tournament),
        'has_match_rules': has_match_rules(tournament),
        'has_scoring_system': has_scoring_system(tournament),
        'has_penalty_rules': has_penalty_rules(tournament),
        'has_prize_distribution_rules': has_prize_distribution_rules(tournament),
        'has_additional_notes': has_additional_notes(tournament),
        'has_checkin_instructions': has_checkin_instructions(tournament),
        'has_complete_rules': has_complete_rules(tournament),
        'populated_sections_count': get_populated_sections_count(tournament),
        'has_any_restrictions': has_any_restrictions(tournament),
    }


# ============================================================================
# CATEGORY 6: TEMPLATE CONTEXT HELPERS
# Generate complete context for templates
# ============================================================================

def get_rules_context(tournament: Tournament) -> Dict[str, any]:
    """
    Get complete rules context for templates.
    
    Returns:
        Dict with all rules data, sections, requirements, and restrictions
    """
    return {
        # Rule sections
        'general_rules': get_general_rules(tournament),
        'eligibility_requirements': get_eligibility_requirements(tournament),
        'match_rules': get_match_rules(tournament),
        'scoring_system': get_scoring_system(tournament),
        'penalty_rules': get_penalty_rules(tournament),
        'prize_distribution_rules': get_prize_distribution_rules(tournament),
        'additional_notes': get_additional_notes(tournament),
        'checkin_instructions': get_checkin_instructions(tournament),
        
        # Requirements
        'require_discord': requires_discord(tournament),
        'require_game_id': requires_game_id(tournament),
        'require_team_logo': requires_team_logo(tournament),
        'requirements': get_requirements(tournament),
        
        # Restrictions
        'min_age': get_min_age(tournament),
        'max_age': get_max_age(tournament),
        'age_range': get_age_range_text(tournament),
        'region_restriction': get_region_restriction(tournament),
        'rank_restriction': get_rank_restriction(tournament),
        'restrictions': get_restrictions(tournament),
        
        # Boolean flags
        'has_general_rules': has_general_rules(tournament),
        'has_eligibility_requirements': has_eligibility_requirements(tournament),
        'has_match_rules': has_match_rules(tournament),
        'has_scoring_system': has_scoring_system(tournament),
        'has_penalty_rules': has_penalty_rules(tournament),
        'has_prize_distribution_rules': has_prize_distribution_rules(tournament),
        'has_additional_notes': has_additional_notes(tournament),
        'has_checkin_instructions': has_checkin_instructions(tournament),
        'has_complete_rules': has_complete_rules(tournament),
        'has_age_restrictions': has_age_restrictions(tournament),
        'has_region_restriction': has_region_restriction(tournament),
        'has_rank_restriction': has_rank_restriction(tournament),
        'has_any_restrictions': has_any_restrictions(tournament),
        
        # Counts and lists
        'populated_sections': get_populated_sections(tournament),
        'populated_sections_count': get_populated_sections_count(tournament),
    }


# ============================================================================
# CATEGORY 7: QUERY OPTIMIZATION HELPERS
# Optimize database queries for rules
# ============================================================================

def optimize_queryset_for_rules(queryset: QuerySet) -> QuerySet:
    """
    Optimize queryset to efficiently load rules relationships.
    
    Adds select_related for rules to reduce queries.
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Optimized queryset with rules prefetched
    """
    return queryset.select_related('rules')


def get_tournaments_with_rules(queryset: QuerySet) -> QuerySet:
    """
    Filter tournaments that have rules records.
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Filtered queryset
    """
    return queryset.filter(rules__isnull=False)


def get_tournaments_with_complete_rules(queryset: QuerySet) -> QuerySet:
    """
    Filter tournaments that have complete rules (all essential sections).
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Filtered queryset
    """
    return queryset.filter(
        rules__general_rules__isnull=False,
        rules__eligibility_requirements__isnull=False,
        rules__match_rules__isnull=False
    ).exclude(
        rules__general_rules='',
    ).exclude(
        rules__eligibility_requirements='',
    ).exclude(
        rules__match_rules=''
    )


def get_tournaments_with_restrictions(queryset: QuerySet) -> QuerySet:
    """
    Filter tournaments that have any restrictions (age, region, or rank).
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Filtered queryset
    """
    from django.db.models import Q
    
    return queryset.filter(
        Q(rules__min_age__isnull=False) |
        Q(rules__max_age__isnull=False) |
        Q(rules__region_restriction__isnull=False) |
        Q(rules__rank_restriction__isnull=False)
    )


def get_tournaments_requiring_discord(queryset: QuerySet) -> QuerySet:
    """
    Filter tournaments that require Discord.
    
    Args:
        queryset: Base tournament queryset
        
    Returns:
        Filtered queryset
    """
    return queryset.filter(rules__require_discord=True)
