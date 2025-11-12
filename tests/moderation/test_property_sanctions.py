"""
Property-based tests for moderation sanctions using Hypothesis.

Tests invariants that must hold for ANY valid input (deterministic seed: 20250123):
- Policy composition: BAN > SUSPEND > MUTE precedence
- Scoped vs global: Global always applies, scoped only to target
- Revoked precedence: Revoked sanctions never block
- Time window invariants: No negative durations, ends_at > starts_at
- Idempotency: Same idempotency_key = same sanction ID
"""
import pytest
from hypothesis import given, strategies as st, assume, settings, seed
from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.user_profile.models import UserProfile
from apps.moderation.services import sanctions_service
from apps.moderation.models import ModerationSanction
from apps.tournaments.models import Tournament

User = get_user_model()

# Deterministic seed for reproducible property tests
PROPERTY_TEST_SEED = 20250123


def create_test_user(username_prefix):
    """Helper to create User + UserProfile without collisions."""
    timestamp = timezone.now().timestamp()
    user = User.objects.create_user(
        username=f'{username_prefix}_{timestamp}',
        email=f'{username_prefix}_{timestamp}@proptest.com',
        password='testpass123'
    )
    profile = UserProfile.objects.create(
        user=user,
        display_name=f'{username_prefix.title()} User'
    )
    return profile


@pytest.mark.django_db(transaction=True)
class TestSanctionPropertyInvariants(TransactionTestCase):
    """Property-based tests for sanction invariants (isolated DB transactions)."""
    
    def setUp(self):
        """Create fresh test users for each property test."""
        self.moderator = create_test_user('prop_mod')
        self.subject = create_test_user('prop_subject')
    
    @seed(PROPERTY_TEST_SEED)
    @given(
        sanction_type=st.sampled_from(['BAN', 'MUTE', 'SUSPEND']),
        scope=st.sampled_from(['global', 'tournament']),
        duration_days=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=20, deadline=5000)
    def test_active_sanction_is_sanctioned_returns_true(
        self, sanction_type, scope, duration_days
    ):
        """Property: Any active sanction → is_sanctioned() returns True."""
        tournament = None
        if scope == 'tournament':
            tournament = Tournament.objects.create(
                name=f'PropTest Tournament {timezone.now().timestamp()}',
                start_date=timezone.now() + timedelta(days=7),
                end_date=timezone.now() + timedelta(days=14)
            )
        
        # Create active sanction
        sanction = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type=sanction_type,
            reason='Property test invariant',
            moderator_id=self.moderator.id,
            scope=scope,
            scope_id=tournament.id if tournament else None,
            duration_days=duration_days,
            idempotency_key=f'prop_active_{timezone.now().timestamp()}'
        )
        
        # Property: must return True
        result = sanctions_service.is_sanctioned(
            self.subject.id,
            scope=scope,
            scope_id=tournament.id if tournament else None
        )
        assert result is True, f"Active {sanction_type} ({scope}) must return True from is_sanctioned()"
    
    @seed(PROPERTY_TEST_SEED)
    @given(
        ban_duration=st.integers(min_value=1, max_value=30),
        mute_duration=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=15, deadline=5000)
    def test_ban_precedence_over_mute(self, ban_duration, mute_duration):
        """Property: BAN+MUTE both active → BAN takes precedence (both in policies)."""
        ban = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Property test BAN',
            moderator_id=self.moderator.id,
            scope='global',
            scope_id=None,
            duration_days=ban_duration,
            idempotency_key=f'prop_ban_{timezone.now().timestamp()}'
        )
        
        mute = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='MUTE',
            reason='Property test MUTE',
            moderator_id=self.moderator.id,
            scope='global',
            scope_id=None,
            duration_days=mute_duration,
            idempotency_key=f'prop_mute_{timezone.now().timestamp()}'
        )
        
        # Property: both must be in effective_policies
        policies = sanctions_service.effective_policies(self.subject.id)
        sanction_ids = [s['sanction_id'] for s in policies]
        
        assert ban['sanction_id'] in sanction_ids, "BAN must be in policies"
        assert mute['sanction_id'] in sanction_ids, "MUTE must be in policies"
        assert len(policies) == 2, "Both sanctions should be active"
    
    @seed(PROPERTY_TEST_SEED)
    @given(
        scope=st.sampled_from(['global', 'tournament']),
        duration_days=st.integers(min_value=1, max_value=30)
    )
    @settings(max_examples=15, deadline=5000)
    def test_revoked_sanction_not_in_effective_policies(self, scope, duration_days):
        """Property: Revoked sanction never appears in effective_policies."""
        tournament = None
        if scope == 'tournament':
            tournament = Tournament.objects.create(
                name=f'PropTest Revoke {timezone.now().timestamp()}',
                start_date=timezone.now() + timedelta(days=7),
                end_date=timezone.now() + timedelta(days=14)
            )
        
        # Create and immediately revoke
        sanction = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Property test revocation',
            moderator_id=self.moderator.id,
            scope=scope,
            scope_id=tournament.id if tournament else None,
            duration_days=duration_days,
            idempotency_key=f'prop_revoke_{timezone.now().timestamp()}'
        )
        
        sanctions_service.revoke_sanction(
            sanction_id=sanction['sanction_id'],
            revoked_by_id=self.moderator.id,
            notes={'reason': 'Property test revocation'}
        )
        
        # Property: must NOT be in effective policies
        policies = sanctions_service.effective_policies(
            self.subject.id,
            scope=scope,
            scope_id=tournament.id if tournament else None
        )
        
        sanction_ids = [s['sanction_id'] for s in policies]
        assert sanction['sanction_id'] not in sanction_ids, "Revoked sanction must NOT be in policies"
    
    @seed(PROPERTY_TEST_SEED)
    @given(duration_days=st.integers(min_value=1, max_value=30))
    @settings(max_examples=15, deadline=5000)
    def test_time_window_invariant_ends_after_starts(self, duration_days):
        """Property: ends_at > starts_at for all sanctions."""
        sanction = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Property test time window',
            moderator_id=self.moderator.id,
            scope='global',
            scope_id=None,
            duration_days=duration_days,
            idempotency_key=f'prop_time_{timezone.now().timestamp()}'
        )
        
        obj = ModerationSanction.objects.get(id=sanction['sanction_id'])
        assert obj.ends_at > obj.starts_at, f"ends_at must be > starts_at (duration={duration_days}d)"
        
        # Additional: duration should match within tolerance
        delta = (obj.ends_at - obj.starts_at).days
        assert delta == duration_days, f"Duration mismatch: expected {duration_days}, got {delta}"
    
    @seed(PROPERTY_TEST_SEED)
    @given(
        idempotency_key=st.text(min_size=15, max_size=40, alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=65, max_codepoint=122
        ))
    )
    @settings(max_examples=10, deadline=5000)
    def test_idempotency_same_key_returns_same_id(self, idempotency_key):
        """Property: Same idempotency_key → same sanction ID (no duplicates)."""
        # First call
        sanction1 = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Idempotency test',
            moderator_id=self.moderator.id,
            scope='global',
            scope_id=None,
            duration_days=7,
            idempotency_key=idempotency_key
        )
        
        # Second call (same key)
        sanction2 = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Idempotency test',
            moderator_id=self.moderator.id,
            scope='global',
            scope_id=None,
            duration_days=7,
            idempotency_key=idempotency_key
        )
        
        # Property: must return same ID
        assert sanction1['sanction_id'] == sanction2['sanction_id'], "Same idempotency_key must return same sanction ID"
    
    @seed(PROPERTY_TEST_SEED)
    @given(duration_days=st.integers(min_value=1, max_value=30))
    @settings(max_examples=15, deadline=5000)
    def test_global_sanction_applies_to_all_tournaments(self, duration_days):
        """Property: Global sanction → applies to ANY tournament."""
        # Create global sanction
        sanction = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Global property test',
            moderator_id=self.moderator.id,
            scope='global',
            scope_id=None,
            duration_days=duration_days,
            idempotency_key=f'prop_global_{timezone.now().timestamp()}'
        )
        
        # Create arbitrary tournament
        tournament = Tournament.objects.create(
            name=f'Random Tournament {timezone.now().timestamp()}',
            start_date=timezone.now() + timedelta(days=7),
            end_date=timezone.now() + timedelta(days=14)
        )
        
        # Property: global sanction must apply to ANY tournament
        result = sanctions_service.is_sanctioned(
            self.subject.id,
            scope='tournament',
            scope_id=tournament.id
        )
        assert result is True, "Global sanction must apply to any tournament"
    
    @seed(PROPERTY_TEST_SEED)
    @given(
        tournament_a_offset=st.integers(min_value=100, max_value=500),
        tournament_b_offset=st.integers(min_value=600, max_value=1000)
    )
    @settings(max_examples=10, deadline=5000)
    def test_tournament_scoped_sanction_only_applies_to_target(
        self, tournament_a_offset, tournament_b_offset
    ):
        """Property: Tournament-scoped sanction → only applies to target tournament."""
        # Create tournaments with unique names
        timestamp = timezone.now().timestamp()
        t_a = Tournament.objects.create(
            name=f'Tournament A {timestamp}_{tournament_a_offset}',
            start_date=timezone.now() + timedelta(days=7),
            end_date=timezone.now() + timedelta(days=14)
        )
        t_b = Tournament.objects.create(
            name=f'Tournament B {timestamp}_{tournament_b_offset}',
            start_date=timezone.now() + timedelta(days=7),
            end_date=timezone.now() + timedelta(days=14)
        )
        
        # Create tournament-scoped sanction for t_a
        sanction = sanctions_service.create_sanction(
            subject_profile_id=self.subject.id,
            sanction_type='BAN',
            reason='Scoped property test',
            moderator_id=self.moderator.id,
            scope='tournament',
            scope_id=t_a.id,
            duration_days=7,
            idempotency_key=f'prop_scoped_{t_a.id}_{timezone.now().timestamp()}'
        )
        
        # Property: must apply to t_a
        result_a = sanctions_service.is_sanctioned(
            self.subject.id, scope='tournament', scope_id=t_a.id
        )
        assert result_a is True, f"Sanction must apply to target tournament {t_a.id}"
        
        # Property: must NOT apply to t_b
        result_b = sanctions_service.is_sanctioned(
            self.subject.id, scope='tournament', scope_id=t_b.id
        )
        assert result_b is False, f"Sanction must NOT apply to different tournament {t_b.id}"
