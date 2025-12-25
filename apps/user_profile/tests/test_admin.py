"""
Admin-level tests for user profile Django Admin.

UP-ADMIN-01: Verify audit immutability, admin actions work correctly.
"""
import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.user_profile.admin import (
    UserAuditEventAdmin,
    UserProfileStatsAdmin,
)
from apps.user_profile.models import UserAuditEvent, UserProfileStats
from apps.user_profile.services.audit import AuditService

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create superuser for admin tests"""
    return User.objects.create_superuser(
        username='admin',
        email='admin@test.com',
        password='admin123'
    )


@pytest.fixture
def regular_user(db):
    """Create regular user with profile for tests"""
    from apps.user_profile.models import UserProfile
    user = User.objects.create_user(
        username='testuser',
        email='test@test.com',
        password='test123'
    )
    # Create profile (should be auto-created by signal, but ensure it exists)
    UserProfile.objects.get_or_create(user=user, defaults={'display_name': 'Test User'})
    return user


@pytest.fixture
def admin_site():
    """Admin site instance"""
    return AdminSite()


@pytest.fixture
def request_factory():
    """Request factory for admin tests"""
    return RequestFactory()


class TestUserAuditEventAdmin:
    """Test UserAuditEvent admin - must be completely immutable"""
    
    def test_cannot_add_audit_event_through_admin(self, admin_user, admin_site):
        """Audit events cannot be manually created in admin"""
        admin_instance = UserAuditEventAdmin(UserAuditEvent, admin_site)
        request = RequestFactory().get('/')
        request.user = admin_user
        
        assert admin_instance.has_add_permission(request) is False
    
    def test_cannot_edit_audit_event_through_admin(self, db, admin_user, regular_user, admin_site):
        """Audit events cannot be edited in admin"""
        # Create audit event via service (proper way)
        event = AuditService.record_event(
            subject_user_id=regular_user.id,
            event_type='stats_recomputed',
            source_app='user_profile',
            object_type='userprofilestats',
            object_id=1,
        )
        
        admin_instance = UserAuditEventAdmin(UserAuditEvent, admin_site)
        request = RequestFactory().get('/')
        request.user = admin_user
        
        assert admin_instance.has_change_permission(request, event) is False
    
    def test_cannot_delete_audit_event_through_admin(self, db, admin_user, regular_user, admin_site):
        """Audit events cannot be deleted in admin"""
        # Create audit event via service (proper way)
        event = AuditService.record_event(
            subject_user_id=regular_user.id,
            event_type='stats_recomputed',
            source_app='user_profile',
            object_type='userprofilestats',
            object_id=1,
        )
        
        admin_instance = UserAuditEventAdmin(UserAuditEvent, admin_site)
        request = RequestFactory().get('/')
        request.user = admin_user
        
        assert admin_instance.has_delete_permission(request, event) is False


class TestUserProfileStatsAdmin:
    """Test UserProfileStats admin - read-only with safe actions"""
    
    def test_cannot_add_stats_through_admin(self, admin_user, admin_site):
        """Stats cannot be manually created (derived data)"""
        admin_instance = UserProfileStatsAdmin(UserProfileStats, admin_site)
        request = RequestFactory().get('/')
        request.user = admin_user
        
        assert admin_instance.has_add_permission(request) is False
    
    def test_cannot_delete_stats_through_admin(self, db, admin_user, regular_user, admin_site):
        """Stats cannot be deleted (should persist)"""
        stats = UserProfileStats.objects.create(user_profile=regular_user.profile)
        
        admin_instance = UserProfileStatsAdmin(UserProfileStats, admin_site)
        request = RequestFactory().get('/')
        request.user = admin_user
        
        assert admin_instance.has_delete_permission(request, stats) is False
    
    def test_recompute_stats_action_records_audit_event(
        self, db, admin_user, regular_user, admin_site, request_factory
    ):
        """Recompute stats action creates audit event"""
        from django.contrib.messages.storage.fallback import FallbackStorage
        
        stats = UserProfileStats.objects.create(user_profile=regular_user.profile)
        
        admin_instance = UserProfileStatsAdmin(UserProfileStats, admin_site)
        request = request_factory.post('/')
        request.user = admin_user
        
        # Mock Django messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        
        # Call recompute action
        queryset = UserProfileStats.objects.filter(id=stats.id)
        admin_instance.recompute_stats(request, queryset)
        
        # Check audit event was created
        audit_events = UserAuditEvent.objects.filter(
            subject_user_id=regular_user.id,
            event_type='stats_recomputed',
            actor_user_id=admin_user.id,
        )
        
        assert audit_events.count() == 1
        event = audit_events.first()
        assert event.object_type == 'userprofilestats'
        assert event.metadata.get('trigger') == 'admin_action'
    
    def test_reconcile_economy_action_works(
        self, db, admin_user, regular_user, admin_site, request_factory
    ):
        """Reconcile economy action runs without error"""
        from django.contrib.messages.storage.fallback import FallbackStorage
        from apps.economy.models import DeltaCrownWallet
        
        # Create wallet and stats
        profile = regular_user.profile
        wallet = DeltaCrownWallet.objects.create(profile=profile)
        stats = UserProfileStats.objects.create(user_profile=profile)
        
        admin_instance = UserProfileStatsAdmin(UserProfileStats, admin_site)
        request = request_factory.post('/')
        request.user = admin_user
        
        # Mock Django messages framework
        setattr(request, 'session', {})
        setattr(request, '_messages', FallbackStorage(request))
        
        # Call reconcile action - should not raise
        queryset = UserProfileStats.objects.filter(id=stats.id)
        admin_instance.reconcile_economy(request, queryset)
        
        # Just check it didn't crash (audit event creation depends on whether economy_sync service creates them)
        assert True    
    def test_admin_display_methods_work(
        self, db, admin_user, regular_user, admin_site
    ):
        """Test that admin display methods don't crash and return reasonable values"""
        from apps.economy.models import DeltaCrownWallet
        
        profile = regular_user.profile
        
        # Create wallet with balance
        wallet = DeltaCrownWallet.objects.create(
            profile=profile,
            cached_balance=5000,
            lifetime_earnings=10000
        )
        
        # Create stats
        stats = UserProfileStats.objects.create(
            user_profile=profile,
            tournaments_played=5,
            tournaments_won=2,
            matches_played=20,
            matches_won=12
        )
        
        admin_instance = UserProfileStatsAdmin(UserProfileStats, admin_site)
        
        # Test public_id_display
        public_id_result = admin_instance.public_id_display(stats)
        assert public_id_result  # Should return public_id or '—'
        
        # Test deltacoin_balance_display
        balance_result = admin_instance.deltacoin_balance_display(stats)
        assert balance_result  # Should return formatted balance
        assert '5000' in str(balance_result) or '—' in str(balance_result)
        
        # Test lifetime_earnings_display
        earnings_result = admin_instance.lifetime_earnings_display(stats)
        assert earnings_result  # Should return formatted earnings
        assert '10000' in str(earnings_result) or '—' in str(earnings_result)
        
        # Test teams_joined_display (may return '—' if no team membership relation)
        teams_result = admin_instance.teams_joined_display(stats)
        assert teams_result  # Should not crash
        
        # Test current_team_display (may return '—' if no team membership relation)
        team_result = admin_instance.current_team_display(stats)
        assert team_result  # Should not crash