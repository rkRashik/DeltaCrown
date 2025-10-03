"""
Tournament Finance Helper Functions

This module provides helper functions for working with tournament financial data.
These helpers provide a consistent interface for accessing financial information
whether it comes from the new TournamentFinance model or old Tournament fields.

This supports a gradual migration:
1. First, we create TournamentFinance model and migrate data
2. Then, we use these helpers in views (backward compatible)
3. Finally, we can remove old Tournament financial fields

Key Features:
- Backward compatibility with old Tournament fields
- Consistent financial data access across the codebase
- Payment validation and requirement checking
- Prize distribution management
- Revenue calculations
- Query optimization utilities

Author: GitHub Copilot
Date: October 3, 2025
"""

from decimal import Decimal
from typing import Optional, Dict, Any
from django.db.models import QuerySet


# ============================================================================
# FINANCIAL DATA ACCESS HELPERS
# ============================================================================

def get_finance_field(tournament, field_name: str, default=None):
    """
    Get a financial field value with 3-tier fallback:
    1. Try TournamentFinance model (preferred)
    2. Fall back to Tournament field (legacy)
    3. Return default value
    
    Args:
        tournament: Tournament instance
        field_name: Name of the field ('entry_fee_bdt', 'prize_pool_bdt', etc.)
        default: Default value if field not found
    
    Returns:
        Field value or default
    
    Example:
        entry_fee = get_finance_field(tournament, 'entry_fee_bdt', Decimal('0'))
    """
    # Try TournamentFinance model first
    try:
        if hasattr(tournament, 'finance'):
            finance = tournament.finance
            if hasattr(finance, field_name):
                value = getattr(finance, field_name)
                if value is not None:
                    return value
    except Exception:
        pass
    
    # Fall back to Tournament field
    if hasattr(tournament, field_name):
        value = getattr(tournament, field_name)
        if value is not None:
            return value
    
    # Return default
    return default


def get_entry_fee(tournament) -> Decimal:
    """
    Get tournament entry fee.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Entry fee as Decimal (0 if free)
    """
    return get_finance_field(tournament, 'entry_fee_bdt', Decimal('0'))


def get_prize_pool(tournament) -> Decimal:
    """
    Get tournament prize pool.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Prize pool as Decimal (0 if no prizes)
    """
    return get_finance_field(tournament, 'prize_pool_bdt', Decimal('0'))


def is_free_tournament(tournament) -> bool:
    """
    Check if tournament is completely free (no entry fee).
    
    Args:
        tournament: Tournament instance
    
    Returns:
        True if tournament has no entry fee
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.is_free
    except Exception:
        pass
    
    return get_entry_fee(tournament) == 0


def has_entry_fee(tournament) -> bool:
    """
    Check if tournament requires an entry fee.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        True if tournament has entry fee > 0
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.has_entry_fee
    except Exception:
        pass
    
    return get_entry_fee(tournament) > 0


def has_prize_pool(tournament) -> bool:
    """
    Check if tournament has a prize pool.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        True if tournament has prizes
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.has_prize_pool
    except Exception:
        pass
    
    return get_prize_pool(tournament) > 0


# ============================================================================
# PAYMENT & VALIDATION HELPERS
# ============================================================================

def is_payment_required(tournament) -> bool:
    """
    Check if payment is required for this tournament.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        True if payment is required before participation
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.payment_required
    except Exception:
        pass
    
    # Default: payment required if there's an entry fee
    return has_entry_fee(tournament)


def get_payment_deadline_hours(tournament) -> int:
    """
    Get payment deadline in hours.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Hours until payment deadline (default: 72)
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.payment_deadline_hours
    except Exception:
        pass
    
    return 72  # Default 3 days


def can_afford_tournament(tournament, user_balance: Decimal) -> bool:
    """
    Check if user can afford tournament entry fee.
    
    Args:
        tournament: Tournament instance
        user_balance: User's current balance
    
    Returns:
        True if user has sufficient balance
    """
    entry_fee = get_entry_fee(tournament)
    
    # Include platform fee if applicable
    try:
        if hasattr(tournament, 'finance'):
            total_cost = tournament.finance.total_with_platform_fee
            return user_balance >= total_cost
    except Exception:
        pass
    
    return user_balance >= entry_fee


def get_total_cost(tournament) -> Decimal:
    """
    Get total cost including platform fees.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Total cost (entry fee + platform fee)
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.total_with_platform_fee
    except Exception:
        pass
    
    return get_entry_fee(tournament)


# ============================================================================
# PRIZE DISTRIBUTION HELPERS
# ============================================================================

def get_prize_for_position(tournament, position: int) -> Optional[Decimal]:
    """
    Get prize amount for a specific position.
    
    Args:
        tournament: Tournament instance
        position: Position number (1 = first place)
    
    Returns:
        Prize amount or None if no prize for that position
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.get_prize_for_position(position)
    except Exception:
        pass
    
    return None


def get_prize_distribution(tournament) -> Dict[str, Decimal]:
    """
    Get complete prize distribution.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Dictionary mapping positions to prize amounts
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.prize_distribution or {}
    except Exception:
        pass
    
    return {}


def has_prize_distribution(tournament) -> bool:
    """
    Check if tournament has a defined prize distribution.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        True if prize distribution is configured
    """
    distribution = get_prize_distribution(tournament)
    return bool(distribution)


# ============================================================================
# REVENUE & STATISTICS HELPERS
# ============================================================================

def calculate_potential_revenue(tournament, expected_participants: int) -> Decimal:
    """
    Calculate potential revenue from tournament.
    
    Args:
        tournament: Tournament instance
        expected_participants: Number of expected participants
    
    Returns:
        Potential revenue (entry fees * participants)
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.calculate_total_revenue(expected_participants)
    except Exception:
        pass
    
    entry_fee = get_entry_fee(tournament)
    return entry_fee * expected_participants


def calculate_platform_revenue(tournament, participant_count: int) -> Decimal:
    """
    Calculate platform fee revenue.
    
    Args:
        tournament: Tournament instance
        participant_count: Number of participants
    
    Returns:
        Platform fee revenue
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.calculate_platform_revenue(participant_count)
    except Exception:
        pass
    
    return Decimal('0')


def get_prize_to_entry_ratio(tournament) -> Optional[Decimal]:
    """
    Get ratio of prize pool to entry fee (ROI indicator).
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Ratio as Decimal or None if no entry fee
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.prize_to_entry_ratio
    except Exception:
        pass
    
    entry_fee = get_entry_fee(tournament)
    prize_pool = get_prize_pool(tournament)
    
    if entry_fee > 0:
        return prize_pool / entry_fee
    
    return None


# ============================================================================
# FORMATTING HELPERS
# ============================================================================

def format_entry_fee(tournament) -> str:
    """
    Get formatted entry fee string.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Formatted string like "৳500.00" or "Free"
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.formatted_entry_fee
    except Exception:
        pass
    
    entry_fee = get_entry_fee(tournament)
    if entry_fee == 0:
        return "Free"
    return f"৳{entry_fee:,.2f}"


def format_prize_pool(tournament) -> str:
    """
    Get formatted prize pool string.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Formatted string like "৳5,000.00" or "No prizes"
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.formatted_prize_pool
    except Exception:
        pass
    
    prize_pool = get_prize_pool(tournament)
    if prize_pool == 0:
        return "No prizes"
    return f"৳{prize_pool:,.2f}"


def get_currency(tournament) -> str:
    """
    Get tournament currency code.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Currency code (e.g., 'BDT', 'USD')
    """
    try:
        if hasattr(tournament, 'finance'):
            return tournament.finance.currency
    except Exception:
        pass
    
    return 'BDT'  # Default


# ============================================================================
# QUERY OPTIMIZATION HELPERS
# ============================================================================

def optimize_queryset_for_finance(queryset: QuerySet) -> QuerySet:
    """
    Optimize queryset to efficiently load finance data.
    
    Adds select_related('finance') to prevent N+1 queries
    when accessing financial data.
    
    Args:
        queryset: Tournament QuerySet
    
    Returns:
        Optimized QuerySet
    
    Example:
        tournaments = Tournament.objects.filter(status='PUBLISHED')
        tournaments = optimize_queryset_for_finance(tournaments)
    """
    return queryset.select_related('finance')


def get_finance_context(tournament) -> Dict[str, Any]:
    """
    Get complete finance context for templates.
    
    Returns all financial information in a template-friendly format.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        Dictionary with all financial data
    
    Example:
        context = get_finance_context(tournament)
        # Returns: {
        #     'entry_fee': Decimal('500'),
        #     'entry_fee_formatted': '৳500.00',
        #     'prize_pool': Decimal('5000'),
        #     'prize_pool_formatted': '৳5,000.00',
        #     'is_free': False,
        #     'has_prizes': True,
        #     'payment_required': True,
        #     ...
        # }
    """
    return {
        'entry_fee': get_entry_fee(tournament),
        'entry_fee_formatted': format_entry_fee(tournament),
        'prize_pool': get_prize_pool(tournament),
        'prize_pool_formatted': format_prize_pool(tournament),
        'total_cost': get_total_cost(tournament),
        'is_free': is_free_tournament(tournament),
        'has_entry_fee': has_entry_fee(tournament),
        'has_prize_pool': has_prize_pool(tournament),
        'payment_required': is_payment_required(tournament),
        'payment_deadline_hours': get_payment_deadline_hours(tournament),
        'currency': get_currency(tournament),
        'prize_distribution': get_prize_distribution(tournament),
        'has_prize_distribution': has_prize_distribution(tournament),
        'prize_to_entry_ratio': get_prize_to_entry_ratio(tournament),
    }


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_user_can_register(tournament, user_balance: Decimal) -> tuple[bool, Optional[str]]:
    """
    Validate if user can register for tournament financially.
    
    Args:
        tournament: Tournament instance
        user_balance: User's current balance
    
    Returns:
        Tuple of (can_register: bool, error_message: Optional[str])
    
    Example:
        can_register, error = validate_user_can_register(tournament, user.balance)
        if not can_register:
            messages.error(request, error)
    """
    # Check if payment is required
    if not is_payment_required(tournament):
        return True, None
    
    # Check if tournament is free
    if is_free_tournament(tournament):
        return True, None
    
    # Check if user can afford it
    if not can_afford_tournament(tournament, user_balance):
        total_cost = get_total_cost(tournament)
        return False, f"Insufficient balance. Entry fee: {format_entry_fee(tournament)}. Your balance: ৳{user_balance:,.2f}"
    
    return True, None
