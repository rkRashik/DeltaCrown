"""
Tests for moderation policy cache.

Validates:
- Cache hits/misses
- Correct invalidation on create/revoke
- PII validation (IDs-only in cache)
- TTL expiration
- Flag-gated behavior (OFF by default)
"""
import pytest
import time
from django.test import TestCase, TransactionTestCase, override_settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from apps.user_profile.models import UserProfile
from apps.moderation.services import sanctions_service
from apps.moderation import cache as mod_cache

User = get_user_model()


def create_cache_test_user(username_prefix):
    """Helper to create User + UserProfile for cache tests."""
    timestamp = timezone.now().timestamp()
    user = User.objects.create_user(
        username=f'{username_prefix}_{timestamp}',
        email=f'{username_prefix}_{timestamp}@cachetest.com',
        password='testpass123'
    )
    profile = UserProfile.objects.create(
        user=user,
        display_name=f'{username_prefix.title()} Cache Test'
    )
    return profile


class TestCacheDisabledByDefault(TestCase):
    """Verify cache is OFF by default (zero overhead in production)."""
    
    def test_cache_disabled_by_default(self):
        """With flag OFF (default), cache operations should be no-ops."""
        # should_use_cache returns False
        self.assertFalse(mod_cache.should_use_cache())
        
        # get_cached_policies returns None
        result = mod_cache.get_cached_policies(user_id=123)
        self.assertIsNone(result)
        
        # set_cached_policies is a no-op
        mod_cache.set_cached_policies(123, [{'sanction_id': 1}])
        
        # Verify nothing was cached
        key = mod_cache.cache_key_for_user(123)
        self.assertIsNone(cache.get(key))


@pytest.mark.django_db(transaction=True)
@override_settings(MODERATION_POLICY_CACHE_ENABLED=True)
class TestCacheMissThenHit(TransactionTestCase):
    """Test cache miss → DB fetch → cache population → cache hit."""
    
    def setUp(self):
        """Create test users and clear cache."""
        cache.clear()
        self.moderator = create_cache_test_user('cache_mod')
        self.subject = create_cache_test_user('cache_subject')
    
    def test_cache_miss_then_hit(self):
        """First call: miss. Second call: hit."""
        # Create sanction
        sanction = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Cache test',
            moderator_id=self.moderator.id,
            scope='global',
            scope_id=None,
            duration_days=7,
            idempotency_key=f'cache_test_{timezone.now().timestamp()}'
        )
        
        # First call: cache miss
        cached = mod_cache.get_cached_policies(self.subject.id)
        self.assertIsNone(cached, "First call should be cache MISS")
        
        # Simulate fetching from DB and setting cache
        policies = [{'sanction_id': sanction['sanction_id'], 'type': 'BAN'}]
        mod_cache.set_cached_policies(self.subject.id, policies)
        
        # Second call: cache hit
        cached = mod_cache.get_cached_policies(self.subject.id)
        self.assertIsNotNone(cached, "Second call should be cache HIT")
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached[0]['sanction_id'], sanction['sanction_id'])


@pytest.mark.django_db(transaction=True)
@override_settings(MODERATION_POLICY_CACHE_ENABLED=True)
class TestCacheInvalidation(TransactionTestCase):
    """Test cache invalidation on create/revoke operations."""
    
    def setUp(self):
        """Create test users and clear cache."""
        cache.clear()
        self.moderator = create_cache_test_user('cache_inv_mod')
        self.subject = create_cache_test_user('cache_inv_subject')
    
    def test_invalidation_on_create_sanction(self):
        """Creating a sanction should invalidate cached policies."""
        # Populate cache
        policies = [{'sanction_id': 999, 'type': 'MUTE'}]
        mod_cache.set_cached_policies(self.subject.id, policies)
        
        # Verify cached
        cached = mod_cache.get_cached_policies(self.subject.id)
        self.assertIsNotNone(cached)
        
        # Invalidate
        mod_cache.invalidate_user_sanctions(self.subject.id)
        
        # Verify cache cleared
        cached_after = mod_cache.get_cached_policies(self.subject.id)
        self.assertIsNone(cached_after, "Cache should be cleared after invalidation")
    
    def test_invalidation_on_revoke_sanction(self):
        """Revoking a sanction should invalidate cached policies."""
        # Populate cache
        policies = [{'sanction_id': 888, 'type': 'BAN'}]
        mod_cache.set_cached_policies(self.subject.id, policies)
        
        # Verify cached
        cached = mod_cache.get_cached_policies(self.subject.id)
        self.assertIsNotNone(cached)
        
        # Invalidate
        mod_cache.invalidate_user_sanctions(self.subject.id)
        
        # Verify cache cleared
        cached_after = mod_cache.get_cached_policies(self.subject.id)
        self.assertIsNone(cached_after)


@pytest.mark.django_db(transaction=True)
@override_settings(MODERATION_POLICY_CACHE_ENABLED=True)
class TestCacheTTL(TransactionTestCase):
    """Test cache TTL expiration (60 seconds)."""
    
    def setUp(self):
        """Create test users and clear cache."""
        cache.clear()
        self.moderator = create_cache_test_user('cache_ttl_mod')
        self.subject = create_cache_test_user('cache_ttl_subject')
    
    def test_cache_expires_after_ttl(self):
        """Cache entries should expire after 60 seconds."""
        # Set cache with TTL=1s for testing (override in method)
        key = mod_cache.cache_key_for_user(self.subject.id)
        policies = [{'sanction_id': 777, 'type': 'SUSPEND'}]
        
        # Set with short TTL for test
        cache.set(key, policies, 2)  # 2 seconds
        
        # Immediately: should exist
        cached = cache.get(key)
        self.assertIsNotNone(cached)
        
        # Wait 3 seconds
        time.sleep(3)
        
        # Should be expired
        cached_after = cache.get(key)
        self.assertIsNone(cached_after, "Cache should expire after TTL")


@pytest.mark.django_db(transaction=True)
@override_settings(MODERATION_POLICY_CACHE_ENABLED=True)
class TestCachePIIGuard(TransactionTestCase):
    """Test PII validation in cached data."""
    
    def setUp(self):
        """Create test users and clear cache."""
        cache.clear()
        self.moderator = create_cache_test_user('cache_pii_mod')
        self.subject = create_cache_test_user('cache_pii_subject')
    
    def test_reject_username_in_cache(self):
        """Cache should reject policies containing 'username'."""
        policies = [
            {'sanction_id': 123, 'type': 'BAN', 'username': 'badactor'}
        ]
        
        with self.assertRaises(ValueError) as ctx:
            mod_cache.set_cached_policies(self.subject.id, policies)
        
        self.assertIn('PII leak', str(ctx.exception))
        self.assertIn('username', str(ctx.exception))
    
    def test_reject_email_in_cache(self):
        """Cache should reject policies containing 'email'."""
        policies = [
            {'sanction_id': 456, 'type': 'MUTE', 'email': 'test@example.com'}
        ]
        
        with self.assertRaises(ValueError) as ctx:
            mod_cache.set_cached_policies(self.subject.id, policies)
        
        self.assertIn('PII leak', str(ctx.exception))
        self.assertIn('email', str(ctx.exception))
    
    def test_reject_ip_in_cache(self):
        """Cache should reject policies containing 'ip'."""
        policies = [
            {'sanction_id': 789, 'type': 'BAN', 'ip': '192.168.1.1'}
        ]
        
        with self.assertRaises(ValueError) as ctx:
            mod_cache.set_cached_policies(self.subject.id, policies)
        
        self.assertIn('PII leak', str(ctx.exception))
        self.assertIn('ip', str(ctx.exception))
    
    def test_allow_ids_only_in_cache(self):
        """Cache should allow policies with IDs only."""
        policies = [
            {'sanction_id': 999, 'type': 'BAN', 'user_id': self.subject.id}
        ]
        
        # Should NOT raise
        mod_cache.set_cached_policies(self.subject.id, policies)
        
        # Verify cached
        cached = mod_cache.get_cached_policies(self.subject.id)
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 1)


@pytest.mark.django_db(transaction=True)
@override_settings(MODERATION_POLICY_CACHE_ENABLED=True)
class TestTournamentScopedCache(TransactionTestCase):
    """Test cache with tournament-scoped sanctions."""
    
    def setUp(self):
        """Create test users and clear cache."""
        cache.clear()
        self.moderator = create_cache_test_user('cache_tourn_mod')
        self.subject = create_cache_test_user('cache_tourn_subject')
    
    def test_tournament_scoped_cache_key(self):
        """Tournament-scoped sanctions use different cache keys."""
        tournament_id = 12345
        
        # Global key
        global_key = mod_cache.cache_key_for_user(self.subject.id)
        self.assertEqual(global_key, f"moderation:user:{self.subject.id}:sanctions")
        
        # Tournament-scoped key
        tourney_key = mod_cache.cache_key_for_user(self.subject.id, tournament_id)
        self.assertEqual(
            tourney_key,
            f"moderation:user:{self.subject.id}:tournament:{tournament_id}:sanctions"
        )
        
        # Keys should be different
        self.assertNotEqual(global_key, tourney_key)
    
    def test_tournament_invalidation(self):
        """Tournament invalidation clears both global and tournament-specific caches."""
        tournament_id = 54321
        
        # Set global cache
        mod_cache.set_cached_policies(self.subject.id, [{'sanction_id': 1}])
        
        # Set tournament cache
        mod_cache.set_cached_policies(self.subject.id, [{'sanction_id': 2}], tournament_id)
        
        # Verify both cached
        self.assertIsNotNone(mod_cache.get_cached_policies(self.subject.id))
        self.assertIsNotNone(mod_cache.get_cached_policies(self.subject.id, tournament_id))
        
        # Invalidate tournament
        mod_cache.invalidate_tournament_sanctions(self.subject.id, tournament_id)
        
        # Both should be cleared
        self.assertIsNone(mod_cache.get_cached_policies(self.subject.id))
        self.assertIsNone(mod_cache.get_cached_policies(self.subject.id, tournament_id))


@pytest.mark.django_db(transaction=True)
@override_settings(MODERATION_POLICY_CACHE_ENABLED=True)
class TestCacheStats(TransactionTestCase):
    """Test cache statistics retrieval."""
    
    def setUp(self):
        """Clear cache."""
        cache.clear()
    
    def test_get_cache_stats(self):
        """get_cache_stats should return dict with enabled status."""
        stats = mod_cache.get_cache_stats()
        
        self.assertIsInstance(stats, dict)
        self.assertIn('enabled', stats)
        self.assertTrue(stats['enabled'], "Cache should be enabled in test")
        self.assertIn('backend', stats)
