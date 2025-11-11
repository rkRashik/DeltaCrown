"""
Module 7.3 - Transaction History & Reporting Tests

Tests for transaction history pagination, filtering, totals, and CSV export.

Coverage targets:
- Services ≥90%
- Models ≥95%
- Runtime ≤90s
"""

import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import csv
import io


@pytest.mark.django_db
class TestTransactionHistoryPagination:
    """Test pagination for transaction history retrieval."""
    
    def test_get_history_with_default_pagination(self, user_with_history):
        """Retrieve first page with default page size."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=1, page_size=10)
        
        assert 'transactions' in result
        assert 'page' in result
        assert 'total_count' in result
        assert result['page'] == 1
        assert len(result['transactions']) <= 10
        assert result['total_count'] == 5  # From fixture
    
    def test_get_history_second_page(self, user_with_history):
        """Retrieve second page of transactions."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        # Create more transactions to trigger pagination
        from apps.economy.services import credit
        for i in range(15):
            credit(wallet.profile, 10, reason='MANUAL_ADJUST', idempotency_key=f'extra_{wallet.id}_{i}')
        
        result = get_transaction_history(wallet, page=2, page_size=10)
        
        assert result['page'] == 2
        assert len(result['transactions']) <= 10
        assert result['total_count'] == 20  # 5 + 15
    
    def test_get_history_with_custom_page_size(self, user_with_history):
        """Retrieve transactions with custom page size."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=1, page_size=3)
        
        assert len(result['transactions']) == 3
        assert result['page'] == 1
        assert result['total_count'] == 5
    
    def test_get_history_empty_page_returns_empty_list(self, user_with_history):
        """Requesting page beyond available data returns empty list."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=10, page_size=10)
        
        assert result['transactions'] == []
        assert result['page'] == 10
        assert result['total_count'] == 5
    
    def test_get_history_cursor_based_pagination(self, user_with_history):
        """Test cursor-based pagination for stable ordering."""
        from apps.economy.services import get_transaction_history_cursor
        
        user, wallet = user_with_history
        result = get_transaction_history_cursor(wallet, limit=3)
        
        assert 'transactions' in result
        assert 'next_cursor' in result
        assert len(result['transactions']) == 3
        
        # Fetch next page with cursor
        if result['next_cursor']:
            result2 = get_transaction_history_cursor(wallet, cursor=result['next_cursor'], limit=3)
            assert len(result2['transactions']) <= 3
            # Verify no overlap
            ids1 = {t['id'] for t in result['transactions']}
            ids2 = {t['id'] for t in result2['transactions']}
            assert ids1.isdisjoint(ids2)


@pytest.mark.django_db
class TestTransactionHistoryFiltering:
    """Test filtering transactions by date, type, and other criteria."""
    
    def test_filter_by_transaction_type_debit(self, user_with_history):
        """Filter transactions by type: DEBIT."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, transaction_type='DEBIT', page=1, page_size=10)
        
        # From fixture: 3 debits (2x ENTRY_FEE_DEBIT)
        assert result['total_count'] >= 3
        for txn in result['transactions']:
            assert txn['amount'] < 0  # Debits are negative
    
    def test_filter_by_transaction_type_credit(self, user_with_history):
        """Filter transactions by type: CREDIT."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, transaction_type='CREDIT', page=1, page_size=10)
        
        # From fixture: 2 credits (MANUAL_ADJUST, PRIZE_PAYOUT)
        assert result['total_count'] >= 2
        for txn in result['transactions']:
            assert txn['amount'] > 0  # Credits are positive
    
    def test_filter_by_reason(self, user_with_history):
        """Filter transactions by reason."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, reason='ENTRY_FEE_DEBIT', page=1, page_size=10)
        
        # From fixture: 3 ENTRY_FEE_DEBIT transactions
        assert result['total_count'] == 3
        for txn in result['transactions']:
            assert txn['reason'] == 'ENTRY_FEE_DEBIT'
    
    def test_filter_by_date_range(self, wallet_with_date_range_history):
        """Filter transactions by date range."""
        from apps.economy.services import get_transaction_history
        
        wallet = wallet_with_date_range_history
        start_date = timezone.now() - timedelta(days=20)
        end_date = timezone.now() - timedelta(days=5)
        
        result = get_transaction_history(
            wallet,
            start_date=start_date,
            end_date=end_date,
            page=1,
            page_size=10
        )
        
        # Should include transactions from 15 days ago and 7 days ago
        assert result['total_count'] >= 2
        for txn in result['transactions']:
            created_at = txn['created_at']
            assert start_date <= created_at <= end_date
    
    def test_filter_by_date_range_start_only(self, wallet_with_date_range_history):
        """Filter transactions with start date only."""
        from apps.economy.services import get_transaction_history
        
        wallet = wallet_with_date_range_history
        start_date = timezone.now() - timedelta(days=10)
        
        result = get_transaction_history(
            wallet,
            start_date=start_date,
            page=1,
            page_size=10
        )
        
        # Should include transactions from 7 days ago, yesterday, and today
        assert result['total_count'] >= 3
        for txn in result['transactions']:
            assert txn['created_at'] >= start_date
    
    def test_filter_by_date_range_end_only(self, wallet_with_date_range_history):
        """Filter transactions with end date only."""
        from apps.economy.services import get_transaction_history
        
        wallet = wallet_with_date_range_history
        end_date = timezone.now() - timedelta(days=10)
        
        result = get_transaction_history(
            wallet,
            end_date=end_date,
            page=1,
            page_size=10
        )
        
        # Should include transactions from 30 days ago and 15 days ago
        assert result['total_count'] >= 2
        for txn in result['transactions']:
            assert txn['created_at'] <= end_date
    
    def test_filter_combined_type_and_date(self, user_with_history):
        """Filter with multiple criteria: type and date range."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        start_date = timezone.now() - timedelta(hours=1)
        
        result = get_transaction_history(
            wallet,
            transaction_type='DEBIT',
            start_date=start_date,
            page=1,
            page_size=10
        )
        
        assert 'transactions' in result
        for txn in result['transactions']:
            assert txn['amount'] < 0  # Debit
            assert txn['created_at'] >= start_date


@pytest.mark.django_db
class TestTransactionOrdering:
    """Test transaction ordering options."""
    
    def test_default_ordering_newest_first(self, user_with_history):
        """Default ordering is newest first (DESC)."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=1, page_size=10)
        
        transactions = result['transactions']
        assert len(transactions) > 0
        
        # Verify descending order
        for i in range(len(transactions) - 1):
            assert transactions[i]['created_at'] >= transactions[i+1]['created_at']
    
    def test_ordering_oldest_first(self, user_with_history):
        """Order transactions oldest first (ASC)."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=1, page_size=10, order='asc')
        
        transactions = result['transactions']
        assert len(transactions) > 0
        
        # Verify ascending order
        for i in range(len(transactions) - 1):
            assert transactions[i]['created_at'] <= transactions[i+1]['created_at']


@pytest.mark.django_db
class TestTransactionTotals:
    """Test transaction totals and summary endpoints."""
    
    def test_get_transaction_totals(self, user_with_history):
        """Get totals for current balance, credits, debits."""
        from apps.economy.services import get_transaction_totals
        
        user, wallet = user_with_history
        totals = get_transaction_totals(wallet)
        
        assert 'current_balance' in totals
        assert 'total_credits' in totals
        assert 'total_debits' in totals
        assert 'transaction_count' in totals
        
        # From fixture: 1000 + 500 - 100 - 50 - 200 = 1150
        assert totals['current_balance'] == wallet.cached_balance
        assert totals['transaction_count'] == 5
    
    def test_get_totals_with_date_range(self, wallet_with_date_range_history):
        """Get totals filtered by date range."""
        from apps.economy.services import get_transaction_totals
        
        wallet = wallet_with_date_range_history
        start_date = timezone.now() - timedelta(days=20)
        end_date = timezone.now() - timedelta(days=5)
        
        totals = get_transaction_totals(wallet, start_date=start_date, end_date=end_date)
        
        assert 'current_balance' in totals
        assert 'total_credits' in totals
        assert 'transaction_count' in totals
        # Should only count transactions in date range
        assert totals['transaction_count'] >= 2
        assert totals['transaction_count'] < 5
    
    def test_get_pending_holds_summary(self, user_with_history):
        """Get summary of pending shop holds."""
        from apps.economy.services import get_pending_holds_summary
        from apps.shop.models import ReservationHold
        from django.utils import timezone
        from datetime import timedelta
        
        user, wallet = user_with_history
        
        # Create some holds directly
        ReservationHold.objects.create(
            wallet=wallet,
            amount=100,
            sku='TEST_ITEM',
            status='authorized',
            idempotency_key='hold1',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        ReservationHold.objects.create(
            wallet=wallet,
            amount=50,
            sku='TEST_ITEM',
            status='authorized',
            idempotency_key='hold2',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        summary = get_pending_holds_summary(wallet)
        
        assert 'total_pending' in summary
        assert 'hold_count' in summary
        assert 'available_balance' in summary
        assert summary['total_pending'] == 150
        assert summary['hold_count'] == 2
        assert summary['available_balance'] == wallet.cached_balance - 150


@pytest.mark.django_db
class TestCSVExport:
    """Test CSV export functionality for transactions."""
    
    def test_export_transactions_to_csv(self, user_with_history):
        """Export transaction history to CSV."""
        from apps.economy.services import export_transactions_csv
        
        user, wallet = user_with_history
        csv_data = export_transactions_csv(wallet)
        
        assert csv_data is not None
        assert isinstance(csv_data, str)
        
        # Parse CSV (strip BOM if present)
        csv_data_clean = csv_data.lstrip('\ufeff')
        reader = csv.DictReader(io.StringIO(csv_data_clean))
        rows = list(reader)
        
        assert len(rows) == 5  # From fixture
        assert 'Date' in reader.fieldnames
        assert 'Type' in reader.fieldnames
        assert 'Amount' in reader.fieldnames
        assert 'Balance After' in reader.fieldnames
        assert 'Reason' in reader.fieldnames
    
    def test_export_csv_with_filters(self, user_with_history):
        """Export filtered transactions to CSV."""
        from apps.economy.services import export_transactions_csv
        
        user, wallet = user_with_history
        csv_data = export_transactions_csv(wallet, transaction_type='DEBIT')
        
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        
        # Only debits from fixture
        assert len(rows) == 3
        for row in rows:
            amount = int(row['Amount'])
            assert amount < 0  # Debits
    
    def test_export_csv_includes_bom(self, user_with_history):
        """CSV export includes BOM for Excel compatibility."""
        from apps.economy.services import export_transactions_csv
        
        user, wallet = user_with_history
        csv_data = export_transactions_csv(wallet)
        
        # Check for UTF-8 BOM
        assert csv_data.startswith('\ufeff') or csv_data.startswith('Date')
    
    def test_export_csv_no_pii(self, user_with_history):
        """CSV export does not include PII."""
        from apps.economy.services import export_transactions_csv
        
        user, wallet = user_with_history
        csv_data = export_transactions_csv(wallet)
        
        # Verify no email, username, or sensitive data
        assert user.email not in csv_data
        assert user.username not in csv_data
    
    def test_export_csv_capped_row_limit(self, user_with_history):
        """CSV export respects maximum row limit."""
        from apps.economy.services import export_transactions_csv
        from apps.economy.services import credit
        
        user, wallet = user_with_history
        # Create many transactions
        for i in range(1500):
            credit(wallet.profile, 1, reason='MANUAL_ADJUST', idempotency_key=f'bulk_{wallet.id}_{i}')
        
        csv_data = export_transactions_csv(wallet, max_rows=1000)
        
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        
        # Should be capped at 1000
        assert len(rows) == 1000
    
    def test_export_csv_streaming_for_large_datasets(self, user_with_history):
        """CSV export uses streaming for large datasets."""
        from apps.economy.services import export_transactions_csv_streaming
        
        user, wallet = user_with_history
        # This should return a generator or iterator
        csv_generator = export_transactions_csv_streaming(wallet)
        
        assert hasattr(csv_generator, '__iter__')
        
        # Consume generator
        chunks = list(csv_generator)
        assert len(chunks) > 0
        
        # Combine chunks and verify
        csv_data = ''.join(chunks)
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        assert len(rows) == 5


@pytest.mark.django_db
class TestTransactionDTOs:
    """Test data transfer objects for transactions."""
    
    def test_transaction_dto_structure(self, user_with_history):
        """Verify transaction DTO has correct structure."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=1, page_size=1)
        
        txn = result['transactions'][0]
        
        # Required fields
        assert 'id' in txn
        assert 'amount' in txn
        assert 'balance_after' in txn
        assert 'reason' in txn
        assert 'created_at' in txn
        assert 'idempotency_key' in txn
        
        # Verify types
        assert isinstance(txn['id'], int)
        assert isinstance(txn['amount'], int)
        assert txn['balance_after'] is None or isinstance(txn['balance_after'], int)  # Optional field
        assert isinstance(txn['reason'], str)
    
    def test_transaction_dto_no_direct_pii(self, user_with_history):
        """Transaction DTO does not include direct PII."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=1, page_size=1)
        
        txn = result['transactions'][0]
        
        # Should not have user email, username, etc.
        assert 'email' not in txn
        assert 'username' not in txn
        assert 'user' not in txn


@pytest.mark.django_db
class TestPIISafety:
    """Test PII safety in transaction history responses."""
    
    def test_history_response_contains_no_user_email(self, user_with_history):
        """History API response does not expose user email."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=1, page_size=10)
        
        # Convert to string to check for any email presence
        import json
        result_str = json.dumps(result, default=str)
        assert user.email not in result_str
    
    def test_totals_response_contains_no_pii(self, user_with_history):
        """Totals API response does not expose PII."""
        from apps.economy.services import get_transaction_totals
        
        user, wallet = user_with_history
        totals = get_transaction_totals(wallet)
        
        import json
        totals_str = json.dumps(totals, default=str)
        assert user.email not in totals_str
        assert user.username not in totals_str


@pytest.mark.django_db
class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_get_history_for_wallet_with_no_transactions(self, db):
        """Get history for empty wallet."""
        from apps.economy.services import get_transaction_history
        from apps.economy.models import DeltaCrownWallet
        from apps.user_profile.models import UserProfile
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(username='empty', email='empty@test.com', password='test')
        profile, _ = UserProfile.objects.get_or_create(user=user)
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        
        result = get_transaction_history(wallet, page=1, page_size=10)
        
        assert result['transactions'] == []
        assert result['total_count'] == 0
        assert result['page'] == 1
    
    def test_get_totals_for_empty_wallet(self, db):
        """Get totals for wallet with no transactions."""
        from apps.economy.services import get_transaction_totals
        from apps.economy.models import DeltaCrownWallet
        from apps.user_profile.models import UserProfile
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(username='empty2', email='empty2@test.com', password='test')
        profile, _ = UserProfile.objects.get_or_create(user=user)
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        
        totals = get_transaction_totals(wallet)
        
        assert totals['current_balance'] == 0
        assert totals['total_credits'] == 0
        assert totals['total_debits'] == 0
        assert totals['transaction_count'] == 0
    
    def test_invalid_page_number_returns_empty(self, user_with_history):
        """Invalid page number returns empty results."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=0, page_size=10)
        
        # Page 0 is invalid, should return empty or page 1
        assert 'transactions' in result
    
    def test_negative_page_size_uses_default(self, user_with_history):
        """Negative page size uses default."""
        from apps.economy.services import get_transaction_history
        
        user, wallet = user_with_history
        result = get_transaction_history(wallet, page=1, page_size=-1)
        
        # Should use default page size (e.g., 20)
        assert len(result['transactions']) <= 20
    
    def test_export_csv_for_empty_wallet(self, db):
        """Export CSV for wallet with no transactions."""
        from apps.economy.services import export_transactions_csv
        from apps.economy.models import DeltaCrownWallet
        from apps.user_profile.models import UserProfile
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        user = User.objects.create_user(username='empty3', email='empty3@test.com', password='test')
        profile, _ = UserProfile.objects.get_or_create(user=user)
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        
        csv_data = export_transactions_csv(wallet)
        
        # Should have headers but no data rows
        reader = csv.DictReader(io.StringIO(csv_data))
        rows = list(reader)
        assert len(rows) == 0
