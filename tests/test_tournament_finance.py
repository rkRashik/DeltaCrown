"""
Comprehensive tests for TournamentFinance model and finance helpers.

Tests cover:
- Model creation and validation
- Computed properties
- Helper functions with 3-tier fallback
- Financial calculations
- Data integrity
- Edge cases
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.tournaments.models.core import TournamentFinance
from apps.tournaments.utils.finance_helpers import (
    get_finance_field, get_entry_fee, get_prize_pool,
    is_free_tournament, has_entry_fee, has_prize_pool,
    is_payment_required, get_payment_deadline_hours,
    can_afford_tournament, get_total_cost, get_prize_for_position,
    get_prize_distribution, has_prize_distribution,
    calculate_potential_revenue, calculate_platform_revenue,
    get_prize_to_entry_ratio, format_entry_fee, format_prize_pool,
    get_currency, optimize_queryset_for_finance, get_finance_context,
)


@pytest.fixture
def base_tournament(db):
    """Create a basic tournament for testing."""
    return Tournament.objects.create(
        name="Test Tournament",
        slug="test-tournament",
        game="valorant",
        status="PUBLISHED",
        start_at=timezone.now() + timezone.timedelta(days=7),
        entry_fee_bdt=Decimal('500'),
        prize_pool_bdt=Decimal('5000'),
    )


@pytest.fixture
def free_tournament(db):
    """Create a free tournament (no entry fee)."""
    return Tournament.objects.create(
        name="Free Tournament",
        slug="free-tournament",
        game="efootball",
        status="PUBLISHED",
        start_at=timezone.now() + timezone.timedelta(days=7),
        entry_fee_bdt=Decimal('0'),
        prize_pool_bdt=Decimal('0'),
    )


@pytest.fixture
def paid_finance(base_tournament):
    """Create TournamentFinance for paid tournament."""
    return TournamentFinance.objects.create(
        tournament=base_tournament,
        entry_fee_bdt=Decimal('500'),
        prize_pool_bdt=Decimal('5000'),
        currency='BDT',
        payment_required=True,
        payment_deadline_hours=72,
        prize_distribution={'1': 3000, '2': 1500, '3': 500},
        platform_fee_percent=Decimal('10'),
    )


@pytest.fixture
def free_finance(free_tournament):
    """Create TournamentFinance for free tournament."""
    return TournamentFinance.objects.create(
        tournament=free_tournament,
        entry_fee_bdt=Decimal('0'),
        prize_pool_bdt=Decimal('0'),
        currency='BDT',
        payment_required=False,
    )


# ============================================================================
# MODEL TESTS
# ============================================================================

@pytest.mark.django_db
class TestTournamentFinanceModel:
    """Test TournamentFinance model creation and validation."""
    
    def test_create_basic_finance(self, base_tournament):
        """Test creating basic finance record."""
        finance = TournamentFinance.objects.create(
            tournament=base_tournament,
            entry_fee_bdt=Decimal('200'),
            prize_pool_bdt=Decimal('2000'),
        )
        
        assert finance.entry_fee_bdt == Decimal('200')
        assert finance.prize_pool_bdt == Decimal('2000')
        assert finance.currency == 'BDT'  # Default
        assert finance.payment_required is False  # Default
        
    def test_free_tournament_finance(self, free_tournament):
        """Test finance record for free tournament."""
        finance = TournamentFinance.objects.create(
            tournament=free_tournament,
            entry_fee_bdt=Decimal('0'),
            prize_pool_bdt=Decimal('0'),
        )
        
        assert finance.is_free is True
        assert finance.has_entry_fee is False
        assert finance.has_prize_pool is False
        
    def test_paid_tournament_finance(self, paid_finance):
        """Test finance record for paid tournament."""
        assert paid_finance.is_free is False
        assert paid_finance.has_entry_fee is True
        assert paid_finance.has_prize_pool is True
        assert paid_finance.payment_required is True
        
    def test_prize_distribution(self, paid_finance):
        """Test prize distribution functionality."""
        assert paid_finance.prize_distribution == {'1': 3000, '2': 1500, '3': 500}
        assert paid_finance.get_prize_for_position(1) == Decimal('3000')
        assert paid_finance.get_prize_for_position(2) == Decimal('1500')
        assert paid_finance.get_prize_for_position(3) == Decimal('500')
        assert paid_finance.get_prize_for_position(4) == Decimal('0')  # No prize
        
    def test_platform_fee_calculation(self, paid_finance):
        """Test platform fee calculation."""
        # Entry fee: ৳500, Platform fee: 10%
        total_cost = paid_finance.total_with_platform_fee
        expected_fee = Decimal('500') * Decimal('1.10')  # ৳550
        assert total_cost == expected_fee
        
    def test_revenue_calculations(self, paid_finance):
        """Test revenue calculation methods."""
        # 10 participants, ৳500 entry fee
        total_revenue = paid_finance.calculate_total_revenue(10)
        assert total_revenue == Decimal('5000')
        
        # Platform revenue: 10% of ৳5000 = ৳500
        platform_revenue = paid_finance.calculate_platform_revenue(10)
        assert platform_revenue == Decimal('500')
        
    def test_prize_to_entry_ratio(self, paid_finance):
        """Test prize to entry fee ratio calculation."""
        ratio = paid_finance.prize_to_entry_ratio
        # Prize pool: ৳5000, Entry fee: ৳500
        # Ratio: 5000 / 500 = 10.0
        assert ratio == Decimal('10.0')
        
    def test_formatted_displays(self, paid_finance):
        """Test formatted display strings."""
        assert paid_finance.formatted_entry_fee == "৳500.00"
        assert paid_finance.formatted_prize_pool == "৳5,000.00"


# ============================================================================
# HELPER FUNCTION TESTS - DATA ACCESS
# ============================================================================

@pytest.mark.django_db
class TestFinanceHelperDataAccess:
    """Test finance helper functions for data access."""
    
    def test_get_entry_fee_from_finance_model(self, base_tournament, paid_finance):
        """Test getting entry fee from finance model."""
        fee = get_entry_fee(base_tournament)
        assert fee == Decimal('500')
        
    def test_get_entry_fee_fallback(self, base_tournament):
        """Test entry fee fallback to old field."""
        # Delete finance record to test fallback
        TournamentFinance.objects.filter(tournament=base_tournament).delete()
        
        fee = get_entry_fee(base_tournament)
        assert fee == Decimal('500')  # Falls back to tournament.entry_fee_bdt
        
    def test_get_prize_pool_from_finance_model(self, base_tournament, paid_finance):
        """Test getting prize pool from finance model."""
        prize = get_prize_pool(base_tournament)
        assert prize == Decimal('5000')
        
    def test_get_prize_pool_fallback(self, base_tournament):
        """Test prize pool fallback to old field."""
        TournamentFinance.objects.filter(tournament=base_tournament).delete()
        
        prize = get_prize_pool(base_tournament)
        assert prize == Decimal('5000')  # Falls back to tournament.prize_pool_bdt
        
    def test_get_finance_field_with_default(self, base_tournament):
        """Test get_finance_field with default value."""
        TournamentFinance.objects.filter(tournament=base_tournament).delete()
        
        value = get_finance_field(base_tournament, 'nonexistent_field', 'default')
        assert value == 'default'


# ============================================================================
# HELPER FUNCTION TESTS - BOOLEAN CHECKS
# ============================================================================

@pytest.mark.django_db
class TestFinanceHelperBooleanChecks:
    """Test finance helper boolean check functions."""
    
    def test_is_free_tournament_true(self, free_tournament, free_finance):
        """Test free tournament detection."""
        assert is_free_tournament(free_tournament) is True
        
    def test_is_free_tournament_false(self, base_tournament, paid_finance):
        """Test paid tournament detection."""
        assert is_free_tournament(base_tournament) is False
        
    def test_has_entry_fee_true(self, base_tournament, paid_finance):
        """Test entry fee detection."""
        assert has_entry_fee(base_tournament) is True
        
    def test_has_entry_fee_false(self, free_tournament, free_finance):
        """Test no entry fee detection."""
        assert has_entry_fee(free_tournament) is False
        
    def test_has_prize_pool_true(self, base_tournament, paid_finance):
        """Test prize pool detection."""
        assert has_prize_pool(base_tournament) is True
        
    def test_has_prize_pool_false(self, free_tournament, free_finance):
        """Test no prize pool detection."""
        assert has_prize_pool(free_tournament) is False
        
    def test_is_payment_required(self, base_tournament, paid_finance):
        """Test payment required check."""
        assert is_payment_required(base_tournament) is True
        
    def test_payment_not_required(self, free_tournament, free_finance):
        """Test payment not required."""
        assert is_payment_required(free_tournament) is False


# ============================================================================
# HELPER FUNCTION TESTS - PAYMENT & AFFORDABILITY
# ============================================================================

@pytest.mark.django_db
class TestFinanceHelperPayment:
    """Test finance helper payment and affordability functions."""
    
    def test_get_payment_deadline_hours(self, base_tournament, paid_finance):
        """Test getting payment deadline."""
        hours = get_payment_deadline_hours(base_tournament)
        assert hours == 72
        
    def test_can_afford_tournament_sufficient_balance(self, base_tournament, paid_finance):
        """Test affordability with sufficient balance."""
        user_balance = Decimal('1000')
        assert can_afford_tournament(base_tournament, user_balance) is True
        
    def test_can_afford_tournament_insufficient_balance(self, base_tournament, paid_finance):
        """Test affordability with insufficient balance."""
        user_balance = Decimal('100')
        assert can_afford_tournament(base_tournament, user_balance) is False
        
    def test_can_afford_free_tournament(self, free_tournament, free_finance):
        """Test free tournament is always affordable."""
        user_balance = Decimal('0')
        assert can_afford_tournament(free_tournament, user_balance) is True
        
    def test_get_total_cost(self, base_tournament, paid_finance):
        """Test total cost calculation including fees."""
        total = get_total_cost(base_tournament)
        # Entry: ৳500 + 10% platform fee = ৳550
        assert total == Decimal('550')
        
    def test_get_total_cost_free(self, free_tournament, free_finance):
        """Test total cost for free tournament."""
        total = get_total_cost(free_tournament)
        assert total == Decimal('0')


# ============================================================================
# HELPER FUNCTION TESTS - PRIZE DISTRIBUTION
# ============================================================================

@pytest.mark.django_db
class TestFinanceHelperPrizeDistribution:
    """Test finance helper prize distribution functions."""
    
    def test_get_prize_for_position(self, base_tournament, paid_finance):
        """Test getting prize for specific position."""
        first_prize = get_prize_for_position(base_tournament, 1)
        assert first_prize == Decimal('3000')
        
        second_prize = get_prize_for_position(base_tournament, 2)
        assert second_prize == Decimal('1500')
        
    def test_get_prize_for_nonexistent_position(self, base_tournament, paid_finance):
        """Test getting prize for position without prize."""
        prize = get_prize_for_position(base_tournament, 10)
        assert prize == Decimal('0')
        
    def test_get_prize_distribution(self, base_tournament, paid_finance):
        """Test getting complete prize distribution."""
        distribution = get_prize_distribution(base_tournament)
        assert distribution == {'1': 3000, '2': 1500, '3': 500}
        
    def test_has_prize_distribution_true(self, base_tournament, paid_finance):
        """Test prize distribution exists."""
        assert has_prize_distribution(base_tournament) is True
        
    def test_has_prize_distribution_false(self, free_tournament, free_finance):
        """Test no prize distribution."""
        assert has_prize_distribution(free_tournament) is False


# ============================================================================
# HELPER FUNCTION TESTS - REVENUE CALCULATIONS
# ============================================================================

@pytest.mark.django_db
class TestFinanceHelperRevenue:
    """Test finance helper revenue calculation functions."""
    
    def test_calculate_potential_revenue(self, base_tournament, paid_finance):
        """Test potential revenue calculation."""
        revenue = calculate_potential_revenue(base_tournament, 20)
        # 20 participants × ৳500 = ৳10,000
        assert revenue == Decimal('10000')
        
    def test_calculate_platform_revenue(self, base_tournament, paid_finance):
        """Test platform revenue calculation."""
        platform_rev = calculate_platform_revenue(base_tournament, 20)
        # 20 × ৳500 = ৳10,000, 10% = ৳1,000
        assert platform_rev == Decimal('1000')
        
    def test_get_prize_to_entry_ratio(self, base_tournament, paid_finance):
        """Test prize to entry ratio calculation."""
        ratio = get_prize_to_entry_ratio(base_tournament)
        assert ratio == Decimal('10.0')
        
    def test_prize_to_entry_ratio_free(self, free_tournament, free_finance):
        """Test ratio for free tournament."""
        ratio = get_prize_to_entry_ratio(free_tournament)
        # For free tournaments, ratio is either None or 0 (both acceptable)
        assert ratio is None or ratio == Decimal('0')


# ============================================================================
# HELPER FUNCTION TESTS - FORMATTING
# ============================================================================

@pytest.mark.django_db
class TestFinanceHelperFormatting:
    """Test finance helper formatting functions."""
    
    def test_format_entry_fee_paid(self, base_tournament, paid_finance):
        """Test formatting entry fee for paid tournament."""
        formatted = format_entry_fee(base_tournament)
        assert formatted == "৳500.00"
        
    def test_format_entry_fee_free(self, free_tournament, free_finance):
        """Test formatting entry fee for free tournament."""
        formatted = format_entry_fee(free_tournament)
        assert formatted == "Free"
        
    def test_format_prize_pool_with_prizes(self, base_tournament, paid_finance):
        """Test formatting prize pool with prizes."""
        formatted = format_prize_pool(base_tournament)
        assert formatted == "৳5,000.00"
        
    def test_format_prize_pool_no_prizes(self, free_tournament, free_finance):
        """Test formatting prize pool without prizes."""
        formatted = format_prize_pool(free_tournament)
        assert formatted == "No prizes"
        
    def test_get_currency(self, base_tournament, paid_finance):
        """Test getting currency code."""
        currency = get_currency(base_tournament)
        assert currency == 'BDT'


# ============================================================================
# HELPER FUNCTION TESTS - QUERY OPTIMIZATION
# ============================================================================

@pytest.mark.django_db
class TestFinanceHelperQueryOptimization:
    """Test finance helper query optimization functions."""
    
    def test_optimize_queryset_for_finance(self, base_tournament, paid_finance):
        """Test queryset optimization."""
        queryset = Tournament.objects.all()
        optimized = optimize_queryset_for_finance(queryset)
        
        # Check that select_related was applied
        assert 'finance' in str(optimized.query)
        
    def test_get_finance_context(self, base_tournament, paid_finance):
        """Test getting complete finance context."""
        context = get_finance_context(base_tournament)
        
        assert context['entry_fee'] == Decimal('500')
        assert context['prize_pool'] == Decimal('5000')
        assert context['is_free'] is False
        assert context['has_entry_fee'] is True
        assert context['has_prize_pool'] is True
        assert context['payment_required'] is True
        assert context['entry_fee_formatted'] == "৳500.00"
        assert context['prize_pool_formatted'] == "৳5,000.00"
        assert context['currency'] == 'BDT'
        
    def test_get_finance_context_free(self, free_tournament, free_finance):
        """Test finance context for free tournament."""
        context = get_finance_context(free_tournament)
        
        assert context['entry_fee'] == Decimal('0')
        assert context['prize_pool'] == Decimal('0')
        assert context['is_free'] is True
        assert context['has_entry_fee'] is False
        assert context['has_prize_pool'] is False
        assert context['entry_fee_formatted'] == "Free"
        assert context['prize_pool_formatted'] == "No prizes"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

@pytest.mark.django_db
class TestFinanceIntegration:
    """Test finance functionality in realistic scenarios."""
    
    def test_complete_paid_tournament_flow(self, base_tournament, paid_finance):
        """Test complete flow for paid tournament."""
        # Check pricing
        assert not is_free_tournament(base_tournament)
        assert has_entry_fee(base_tournament)
        assert has_prize_pool(base_tournament)
        
        # Check affordability
        rich_user_balance = Decimal('1000')
        poor_user_balance = Decimal('100')
        assert can_afford_tournament(base_tournament, rich_user_balance) is True
        assert can_afford_tournament(base_tournament, poor_user_balance) is False
        
        # Check revenue potential
        revenue = calculate_potential_revenue(base_tournament, 16)
        assert revenue == Decimal('8000')  # 16 × ৳500
        
        # Check prize distribution
        assert get_prize_for_position(base_tournament, 1) == Decimal('3000')
        
    def test_complete_free_tournament_flow(self, free_tournament, free_finance):
        """Test complete flow for free tournament."""
        # Check pricing
        assert is_free_tournament(free_tournament)
        assert not has_entry_fee(free_tournament)
        assert not has_prize_pool(free_tournament)
        
        # Free tournaments are always affordable
        assert can_afford_tournament(free_tournament, Decimal('0')) is True
        
        # No revenue for free tournaments
        revenue = calculate_potential_revenue(free_tournament, 16)
        assert revenue == Decimal('0')
        
    def test_fallback_system_works(self, base_tournament):
        """Test 3-tier fallback system."""
        # Tier 1: With finance model
        finance = TournamentFinance.objects.create(
            tournament=base_tournament,
            entry_fee_bdt=Decimal('300'),
        )
        # Need to refresh to get the finance relationship
        base_tournament.refresh_from_db()
        assert get_entry_fee(base_tournament) == Decimal('300')
        
        # Tier 2: Without finance model (fallback to old field)
        finance.delete()
        # Refresh to clear the cached relationship
        base_tournament.refresh_from_db()
        assert get_entry_fee(base_tournament) == Decimal('500')  # From tournament.entry_fee_bdt
        
        # Tier 3: No data anywhere (default)
        base_tournament.entry_fee_bdt = None
        base_tournament.save()
        base_tournament.refresh_from_db()
        assert get_entry_fee(base_tournament) == Decimal('0')  # Default


# ============================================================================
# EDGE CASES
# ============================================================================

@pytest.mark.django_db
class TestFinanceEdgeCases:
    """Test edge cases and error handling."""
    
    def test_negative_balance_check(self, base_tournament, paid_finance):
        """Test affordability with negative balance."""
        negative_balance = Decimal('-100')
        assert can_afford_tournament(base_tournament, negative_balance) is False
        
    def test_exact_balance_match(self, base_tournament, paid_finance):
        """Test affordability with exact balance match."""
        exact_balance = Decimal('550')  # Exact total cost
        assert can_afford_tournament(base_tournament, exact_balance) is True
        
    def test_very_large_prize_pool(self, base_tournament):
        """Test handling very large prize pool."""
        finance = TournamentFinance.objects.create(
            tournament=base_tournament,
            entry_fee_bdt=Decimal('1000'),
            prize_pool_bdt=Decimal('1000000'),  # ৳1 million
        )
        
        formatted = format_prize_pool(base_tournament)
        assert "1,000,000" in formatted
        
    def test_zero_platform_fee(self, base_tournament):
        """Test tournament with zero platform fee."""
        finance = TournamentFinance.objects.create(
            tournament=base_tournament,
            entry_fee_bdt=Decimal('500'),
            platform_fee_percent=Decimal('0'),
        )
        
        total = get_total_cost(base_tournament)
        assert total == Decimal('500')  # No additional fee
        
    def test_multi_currency_support(self, base_tournament):
        """Test different currency codes."""
        finance = TournamentFinance.objects.create(
            tournament=base_tournament,
            entry_fee_bdt=Decimal('500'),
            currency='USD',
        )
        
        assert get_currency(base_tournament) == 'USD'
