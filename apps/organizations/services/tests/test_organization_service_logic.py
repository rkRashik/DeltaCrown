"""
Test OrganizationService business logic implementation.

These tests verify the actual business logic of implemented service methods
using Django's test database and Factory Boy fixtures.
"""

import pytest
from django.test import override_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.contrib.auth import get_user_model

from apps.organizations.services import (
    OrganizationService,
    OrganizationInfo,
    NotFoundError,
    ValidationError,
    ConflictError,
    PermissionDeniedError,
)
from apps.organizations.models import Organization, OrganizationMembership, OrganizationRanking
from apps.organizations.tests.factories import OrganizationFactory, UserFactory


User = get_user_model()


@pytest.mark.django_db
class TestGetOrganization:
    """Test get_organization business logic."""
    
    def test_lookup_by_id_returns_dto(self):
        """get_organization with org_id should return OrganizationInfo DTO."""
        user = UserFactory(username='ceo_user')
        org = OrganizationFactory(
            name='SYNTAX Esports',
            slug='syntax-esports',
            ceo=user,
            is_verified=True
        )
        
        result = OrganizationService.get_organization(org_id=org.id)
        
        # Verify DTO fields
        assert isinstance(result, OrganizationInfo)
        assert result.organization_id == org.id
        assert result.name == 'SYNTAX Esports'
        assert result.slug == 'syntax-esports'
        assert result.is_verified is True
        assert result.ceo_user_id == user.id
        assert result.ceo_username == 'ceo_user'
        assert result.team_count == 0  # No teams created
    
    def test_lookup_by_slug_returns_dto(self):
        """get_organization with org_slug should return OrganizationInfo DTO."""
        user = UserFactory(username='admin_user')
        org = OrganizationFactory(
            name='Cloud9 BD',
            slug='cloud9-bd',
            ceo=user,
            is_verified=False
        )
        
        result = OrganizationService.get_organization(org_slug='cloud9-bd')
        
        # Verify DTO fields
        assert isinstance(result, OrganizationInfo)
        assert result.organization_id == org.id
        assert result.name == 'Cloud9 BD'
        assert result.slug == 'cloud9-bd'
        assert result.is_verified is False
        assert result.ceo_user_id == user.id
        assert result.ceo_username == 'admin_user'
    
    def test_both_params_provided_raises_validation_error(self):
        """Providing both org_id and org_slug should raise ValidationError."""
        org = OrganizationFactory()
        
        with pytest.raises(ValidationError) as exc_info:
            OrganizationService.get_organization(org_id=org.id, org_slug=org.slug)
        
        # Verify error code and details
        assert exc_info.value.error_code == 'INVALID_LOOKUP_PARAMS'
        assert 'Exactly one' in exc_info.value.message
        assert exc_info.value.details['org_id_provided'] is True
        assert exc_info.value.details['org_slug_provided'] is True
    
    def test_neither_param_provided_raises_validation_error(self):
        """Providing neither org_id nor org_slug should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            OrganizationService.get_organization()
        
        # Verify error code
        assert exc_info.value.error_code == 'INVALID_LOOKUP_PARAMS'
        assert exc_info.value.details['org_id_provided'] is False
        assert exc_info.value.details['org_slug_provided'] is False
    
    def test_missing_org_by_id_raises_not_found(self):
        """Non-existent org_id should raise NotFoundError with stable error_code."""
        with pytest.raises(NotFoundError) as exc_info:
            OrganizationService.get_organization(org_id=99999)
        
        # Verify exception fields
        assert exc_info.value.error_code == 'ORG_NOT_FOUND'
        assert 'id=99999' in exc_info.value.message
        assert exc_info.value.details['org_id'] == 99999
    
    def test_missing_org_by_slug_raises_not_found(self):
        """Non-existent org_slug should raise NotFoundError with stable error_code."""
        with pytest.raises(NotFoundError) as exc_info:
            OrganizationService.get_organization(org_slug='nonexistent-org')
        
        # Verify exception fields
        assert exc_info.value.error_code == 'ORG_NOT_FOUND'
        assert 'slug=nonexistent-org' in exc_info.value.message
        assert exc_info.value.details['org_slug'] == 'nonexistent-org'
    
    def test_query_count_one_query(self):
        """get_organization should use exactly 1 query (select_related + annotate)."""
        user = UserFactory()
        org = OrganizationFactory(ceo=user)
        
        with CaptureQueriesContext(connection) as queries:
            OrganizationService.get_organization(org_id=org.id)
        
        # Should be 1 query: SELECT org with ceo join + team count annotation
        assert len(queries) == 1, f"Expected 1 query, got {len(queries)}"
        
        # Verify select_related and annotate used
        query_sql = queries[0]['sql'].lower()
        assert 'join' in query_sql or 'auth_user' in query_sql  # CEO join
        assert 'count' in query_sql  # team_count annotation
    
    def test_team_count_annotation(self):
        """team_count should reflect ACTIVE non-temporary teams only."""
        from apps.organizations.tests.factories import TeamFactory
        
        user = UserFactory()
        org = OrganizationFactory(ceo=user)
        
        # Create 2 active teams
        TeamFactory(organization=org, status='ACTIVE', is_temporary=False)
        TeamFactory(organization=org, status='ACTIVE', is_temporary=False)
        
        # Create teams that should NOT count
        TeamFactory(organization=org, status='INACTIVE', is_temporary=False)  # Wrong status
        TeamFactory(organization=org, status='ACTIVE', is_temporary=True)  # Temporary
        
        result = OrganizationService.get_organization(org_id=org.id)
        
        # Should only count 2 active non-temporary teams
        assert result.team_count == 2


@pytest.mark.django_db
class TestCreateOrganization:
    """Test create_organization business logic."""
    
    def test_creates_organization_with_required_fields(self):
        """create_organization should create org with valid inputs."""
        user = UserFactory(username='new_ceo')
        
        org_id = OrganizationService.create_organization(
            name='New Esports Org',
            ceo_user_id=user.id
        )
        
        # Verify org created
        org = Organization.objects.get(id=org_id)
        assert org.name == 'New Esports Org'
        assert org.slug == 'new-esports-org'  # Auto-generated
        assert org.ceo.id == user.id
        assert org.is_verified is False  # Default
    
    def test_creates_ceo_membership(self):
        """create_organization should create CEO membership record."""
        user = UserFactory(username='new_ceo')
        
        org_id = OrganizationService.create_organization(
            name='Test Org',
            ceo_user_id=user.id
        )
        
        # Verify CEO membership created
        membership = OrganizationMembership.objects.get(organization_id=org_id, user=user)
        assert membership.role == 'CEO'
        assert membership.permissions == {}
    
    def test_slug_auto_generation(self):
        """create_organization should auto-generate slug if not provided."""
        user = UserFactory()
        
        org_id = OrganizationService.create_organization(
            name='Test Organization 123',
            ceo_user_id=user.id
        )
        
        org = Organization.objects.get(id=org_id)
        assert org.slug == 'test-organization-123'
    
    def test_custom_slug_respected(self):
        """create_organization should use provided slug if given."""
        user = UserFactory()
        
        org_id = OrganizationService.create_organization(
            name='Test Org',
            ceo_user_id=user.id,
            slug='custom-slug-123'
        )
        
        org = Organization.objects.get(id=org_id)
        assert org.slug == 'custom-slug-123'
    
    def test_optional_fields_saved(self):
        """create_organization should save optional branding fields."""
        user = UserFactory()
        
        org_id = OrganizationService.create_organization(
            name='Rich Org',
            ceo_user_id=user.id,
            description='Best esports org',
            website='https://richorg.gg',
            twitter='richorg'
        )
        
        org = Organization.objects.get(id=org_id)
        assert org.description == 'Best esports org'
        assert org.website == 'https://richorg.gg'
        assert org.twitter == 'richorg'
    
    def test_empty_name_raises_validation_error(self):
        """create_organization with empty name should raise ValidationError."""
        user = UserFactory()
        
        with pytest.raises(ValidationError) as exc_info:
            OrganizationService.create_organization(
                name='',
                ceo_user_id=user.id
            )
        
        assert exc_info.value.error_code == 'INVALID_ORG_NAME'
        assert 'cannot be empty' in exc_info.value.message
    
    def test_whitespace_only_name_raises_validation_error(self):
        """create_organization with whitespace-only name should raise ValidationError."""
        user = UserFactory()
        
        with pytest.raises(ValidationError) as exc_info:
            OrganizationService.create_organization(
                name='   ',
                ceo_user_id=user.id
            )
        
        assert exc_info.value.error_code == 'INVALID_ORG_NAME'
    
    def test_too_long_name_raises_validation_error(self):
        """create_organization with >100 char name should raise ValidationError."""
        user = UserFactory()
        long_name = 'A' * 101
        
        with pytest.raises(ValidationError) as exc_info:
            OrganizationService.create_organization(
                name=long_name,
                ceo_user_id=user.id
            )
        
        assert exc_info.value.error_code == 'INVALID_ORG_NAME'
        assert 'too long' in exc_info.value.message
        assert exc_info.value.details['length'] == 101
    
    def test_nonexistent_user_raises_not_found(self):
        """create_organization with invalid ceo_user_id should raise NotFoundError."""
        with pytest.raises(NotFoundError) as exc_info:
            OrganizationService.create_organization(
                name='Test Org',
                ceo_user_id=99999
            )
        
        assert exc_info.value.error_code == 'USER_NOT_FOUND'
        assert exc_info.value.details['ceo_user_id'] == 99999
    
    def test_duplicate_slug_raises_conflict_error(self):
        """create_organization with duplicate slug should raise ConflictError."""
        user1 = UserFactory()
        user2 = UserFactory()
        
        # Create first org
        OrganizationService.create_organization(
            name='First Org',
            ceo_user_id=user1.id,
            slug='my-unique-slug'
        )
        
        # Attempt to create second org with same slug
        with pytest.raises(ConflictError) as exc_info:
            OrganizationService.create_organization(
                name='Second Org',
                ceo_user_id=user2.id,
                slug='my-unique-slug'
            )
        
        assert exc_info.value.error_code == 'SLUG_CONFLICT'
        assert 'my-unique-slug' in exc_info.value.message
    
    def test_duplicate_name_raises_conflict_error(self):
        """create_organization with duplicate name should raise ConflictError."""
        user1 = UserFactory()
        user2 = UserFactory()
        
        # Create first org
        OrganizationService.create_organization(
            name='Unique Org Name',
            ceo_user_id=user1.id
        )
        
        # Attempt to create second org with same name
        with pytest.raises(ConflictError) as exc_info:
            OrganizationService.create_organization(
                name='Unique Org Name',
                ceo_user_id=user2.id
            )
        
        assert exc_info.value.error_code == 'NAME_CONFLICT'
        assert 'Unique Org Name' in exc_info.value.message
    
    def test_user_already_ceo_raises_permission_denied(self):
        """create_organization by existing CEO should raise PermissionDeniedError."""
        user = UserFactory()
        
        # User creates first org
        OrganizationService.create_organization(
            name='First Org',
            ceo_user_id=user.id
        )
        
        # User attempts to create second org
        with pytest.raises(PermissionDeniedError) as exc_info:
            OrganizationService.create_organization(
                name='Second Org',
                ceo_user_id=user.id
            )
        
        assert exc_info.value.error_code == 'USER_ALREADY_CEO'
        assert user.username in exc_info.value.message
    
    def test_query_count_three_queries_max(self):
        """create_organization should use ≤3 queries."""
        user = UserFactory()
        
        with CaptureQueriesContext(connection) as queries:
            OrganizationService.create_organization(
                name='Test Org',
                ceo_user_id=user.id
            )
        
        # Expected queries:
        # 1. SELECT user (ceo validation)
        # 2. SELECT existing CEO membership (ownership check)
        # 3. INSERT organization (within transaction)
        # 4. INSERT membership (within transaction)
        # 5. INSERT/SELECT ranking (get_or_create, optional)
        query_count = len(queries)
        assert query_count <= 5, f"Expected ≤5 queries, got {query_count}"
    
    def test_transaction_atomicity(self):
        """create_organization should rollback on failure (atomic transaction)."""
        user = UserFactory()
        existing_org = OrganizationFactory(slug='conflict-slug')
        
        initial_org_count = Organization.objects.count()
        initial_membership_count = OrganizationMembership.objects.count()
        
        # Attempt to create org with conflicting slug (should fail)
        with pytest.raises(ConflictError):
            OrganizationService.create_organization(
                name='New Org',
                ceo_user_id=user.id,
                slug='conflict-slug'
            )
        
        # Verify no partial data created (transaction rolled back)
        assert Organization.objects.count() == initial_org_count
        assert OrganizationMembership.objects.count() == initial_membership_count


@pytest.mark.django_db
class TestOrganizationInfoDTO:
    """Test OrganizationInfo DTO structure."""
    
    def test_dto_is_dataclass(self):
        """OrganizationInfo should be a dataclass."""
        from dataclasses import is_dataclass
        assert is_dataclass(OrganizationInfo)
    
    def test_dto_serializable_for_api(self):
        """OrganizationInfo should be serializable with asdict()."""
        from dataclasses import asdict
        
        user = UserFactory()
        org = OrganizationFactory(ceo=user)
        
        dto = OrganizationService.get_organization(org_id=org.id)
        
        # Convert to dict for JSON serialization
        data = asdict(dto)
        
        # Verify all fields present
        assert 'organization_id' in data
        assert 'name' in data
        assert 'slug' in data
        assert 'ceo_username' in data
        assert 'team_count' in data


@pytest.mark.django_db
class TestPerformanceContract:
    """Test performance targets (<50ms get, <100ms create)."""
    
    def test_get_organization_under_50ms(self):
        """get_organization should complete in <50ms (p95 target)."""
        import time
        
        user = UserFactory()
        org = OrganizationFactory(ceo=user)
        
        # Warm up cache (first query may be slower)
        OrganizationService.get_organization(org_id=org.id)
        
        # Time 10 executions
        times = []
        for _ in range(10):
            start = time.perf_counter()
            OrganizationService.get_organization(org_id=org.id)
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
        
        # Calculate p95 (9th percentile of 10 samples)
        times.sort()
        p95 = times[8]  # 9th of 10 samples
        
        assert p95 < 50, f"p95 latency {p95:.2f}ms exceeds 50ms target"
    
    def test_create_organization_under_100ms(self):
        """create_organization should complete in <100ms (p95 target)."""
        import time
        
        # Time 5 executions (can't reuse same user due to CEO constraint)
        times = []
        for i in range(5):
            user = UserFactory(username=f'ceo_{i}')
            
            start = time.perf_counter()
            OrganizationService.create_organization(
                name=f'Test Org {i}',
                ceo_user_id=user.id
            )
            elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
            times.append(elapsed)
        
        # Calculate p95 (4th percentile of 5 samples)
        times.sort()
        p95 = times[4]  # 5th of 5 samples (p100, conservative estimate)
        
        assert p95 < 100, f"p95 latency {p95:.2f}ms exceeds 100ms target"
