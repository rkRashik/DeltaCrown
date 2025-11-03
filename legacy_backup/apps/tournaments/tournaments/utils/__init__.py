"""Utility helpers for the tournaments app."""

# Schedule helpers
from .schedule_helpers import (
    is_registration_open,
    is_tournament_live,
    get_registration_status_text,
    get_tournament_status_text,
    optimize_queryset_for_schedule,
    get_schedule_context,
)

# Capacity helpers
from .capacity_helpers import (
    get_capacity_field,
    is_tournament_full,
    get_available_slots,
    can_accept_registrations,
    get_capacity_status_text,
    validate_team_size,
    optimize_queryset_for_capacity,
    get_capacity_context,
    increment_tournament_registrations,
    decrement_tournament_registrations,
    refresh_tournament_capacity,
    get_registration_mode,
)

# Finance helpers
from .finance_helpers import (
    get_finance_field,
    get_entry_fee,
    get_prize_pool,
    is_free_tournament,
    has_entry_fee,
    has_prize_pool,
    is_payment_required,
    get_payment_deadline_hours,
    can_afford_tournament,
    get_total_cost,
    get_prize_for_position,
    get_prize_distribution,
    has_prize_distribution,
    calculate_potential_revenue,
    calculate_platform_revenue,
    get_prize_to_entry_ratio,
    format_entry_fee,
    format_prize_pool,
    get_currency,
    optimize_queryset_for_finance,
    get_finance_context,
)

__all__ = [
    # Schedule helpers
    'is_registration_open',
    'is_tournament_live',
    'get_registration_status_text',
    'get_tournament_status_text',
    'optimize_queryset_for_schedule',
    'get_schedule_context',
    # Capacity helpers
    'get_capacity_field',
    'is_tournament_full',
    'get_available_slots',
    'can_accept_registrations',
    'get_capacity_status_text',
    'validate_team_size',
    'optimize_queryset_for_capacity',
    'get_capacity_context',
    'increment_tournament_registrations',
    'decrement_tournament_registrations',
    'refresh_tournament_capacity',
    'get_registration_mode',
    # Finance helpers
    'get_finance_field',
    'get_entry_fee',
    'get_prize_pool',
    'is_free_tournament',
    'has_entry_fee',
    'has_prize_pool',
    'is_payment_required',
    'get_payment_deadline_hours',
    'can_afford_tournament',
    'get_total_cost',
    'get_prize_for_position',
    'get_prize_distribution',
    'has_prize_distribution',
    'calculate_potential_revenue',
    'calculate_platform_revenue',
    'get_prize_to_entry_ratio',
    'format_entry_fee',
    'format_prize_pool',
    'get_currency',
    'optimize_queryset_for_finance',
    'get_finance_context',
]

