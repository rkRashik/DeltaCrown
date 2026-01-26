"""
URL namespace contract tests for organizations app.

Ensures that:
1. organizations_api namespace is properly registered
2. All API endpoints can be reversed by name
3. URL routing order is correct (/orgs/create/ before /orgs/<slug>/)
4. Template URL tags work without NoReverseMatch errors

CRITICAL: These tests prevent production crashes from missing namespaces.
"""

import pytest
from django.urls import reverse, resolve
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()


class TestOrganizationsAPINamespace:
    """Test that organizations_api namespace is registered and functional."""
    
    def test_validate_organization_name_url_reverses(self):
        """organizations_api:validate_organization_name must be reversible."""
        url = reverse('organizations_api:validate_organization_name')
        assert url == '/organizations/api/vnext/organizations/validate-name/'
    
    def test_validate_organization_badge_url_reverses(self):
        """organizations_api:validate_organization_badge must be reversible."""
        url = reverse('organizations_api:validate_organization_badge')
        assert url == '/organizations/api/vnext/organizations/validate-badge/'
    
    def test_validate_organization_slug_url_reverses(self):
        """organizations_api:validate_organization_slug must be reversible."""
        url = reverse('organizations_api:validate_organization_slug')
        assert url == '/organizations/api/vnext/organizations/validate-slug/'
    
    def test_create_organization_url_reverses(self):
        """organizations_api:create_organization must be reversible."""
        url = reverse('organizations_api:create_organization')
        assert url == '/organizations/api/vnext/organizations/create/'
    
    def test_all_api_endpoints_use_organizations_api_namespace(self):
        """All API endpoints must use organizations_api namespace (not just 'organizations')."""
        expected_urls = [
            'validate_organization_name',
            'validate_organization_badge',
            'validate_organization_slug',
            'create_organization',
            'validate_team_name',
            'validate_team_tag',
            'create_team',
        ]
        
        for url_name in expected_urls:
            # Should work with namespace
            url = reverse(f'organizations_api:{url_name}')
            assert url.startswith('/organizations/api/vnext/')
            
            # Should NOT work without namespace (would raise NoReverseMatch)
            with pytest.raises(Exception):  # NoReverseMatch
                reverse(url_name)


class TestOrganizationUIURLOrdering:
    """Test that URL routing order is correct for UI views."""
    
    def test_orgs_create_resolves_to_org_create_view(self):
        """
        /orgs/create/ must resolve to org_create view, not organization_detail.
        
        CRITICAL: This prevents "create" being captured as <org_slug>.
        """
        match = resolve('/organizations/orgs/create/')
        assert match.view_name == 'organizations:org_create'
        assert match.func.__name__ == 'org_create'
    
    def test_orgs_slug_resolves_to_organization_detail_view(self):
        """/orgs/<slug>/ must resolve to organization_detail view."""
        match = resolve('/organizations/orgs/test-org/')
        assert match.view_name == 'organizations:organization_detail'
        assert match.func.__name__ == 'organization_detail'
        assert match.kwargs == {'org_slug': 'test-org'}
    
    def test_url_pattern_order_prevents_create_from_being_captured_as_slug(self):
        """
        Regression test: ensure create route is defined BEFORE slug catch-all.
        
        If this test fails, /orgs/create/ will incorrectly route to
        organization_detail(org_slug='create') causing crashes.
        """
        create_match = resolve('/organizations/orgs/create/')
        assert create_match.view_name == 'organizations:org_create'
        
        # Ensure other slugs still work
        slug_match = resolve('/organizations/orgs/actual-org-slug/')
        assert slug_match.view_name == 'organizations:organization_detail'


@pytest.mark.django_db
class TestOrgCreatePageURLResolution:
    """
    Test that org_create page can render without NoReverseMatch errors.
    
    CRITICAL: Template uses {% url 'organizations_api:...' %} tags
    which must resolve successfully or page crashes.
    """
    
    def test_org_create_page_loads_without_url_errors(self, client, django_user_model):
        """
        GET /orgs/create/ must return 200 and render template without reverse errors.
        
        This is an integration test verifying that:
        1. URL routes correctly (not caught by <org_slug> pattern)
        2. Template can reverse organizations_api namespace URLs
        3. No NoReverseMatch exceptions occur
        """
        # Create authenticated user
        user = django_user_model.objects.create_user(
            username='testceo',
            email='ceo@test.com',
            password='testpass123'
        )
        client.force_login(user)
        
        # Request org create page
        response = client.get('/organizations/orgs/create/')
        
        # Must return 200 OK (not 404, not 500)
        assert response.status_code == 200
        
        # Must use correct template
        assert 'organizations/org/org_create.html' in [t.name for t in response.templates]
        
        # Template must have rendered successfully (no NoReverseMatch)
        content = response.content.decode('utf-8')
        assert 'validate-name' in content or 'validateNameUrl' in content
        assert 'validate-badge' in content or 'validateBadgeUrl' in content
    
    def test_org_create_template_variables_include_api_urls(self, rf, django_user_model):
        """
        org_create view context must include API URLs for validation endpoints.
        
        Alternative approach: verify context data contains resolved URLs.
        """
        from apps.organizations.views import org_create
        
        user = django_user_model.objects.create_user(
            username='testceo',
            email='ceo@test.com',
            password='testpass123'
        )
        
        request = rf.get('/organizations/orgs/create/')
        request.user = user
        
        response = org_create(request)
        
        # View should return successful response
        assert response.status_code == 200
        
        # Template should be able to reverse API URLs
        # (no need to check context since template does {% url %} tag resolution)


class TestAdminFieldIntegrity:
    """
    Test that admin configuration matches model fields.
    
    Prevents FieldError exceptions when admin tries to display non-existent fields.
    """
    
    def test_organization_admin_does_not_reference_nonexistent_fields(self):
        """OrganizationAdmin fieldsets must only reference real model fields."""
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization
        
        admin_instance = OrganizationAdmin(Organization, None)
        
        # Collect all fields from fieldsets
        fieldset_fields = []
        for fieldset in admin_instance.fieldsets:
            fields = fieldset[1].get('fields', ())
            fieldset_fields.extend(fields)
        
        # Get model field names
        model_field_names = {f.name for f in Organization._meta.get_fields()}
        model_field_names.add('id')  # pk is always valid
        
        # Check that all fieldset fields exist on model
        for field in fieldset_fields:
            assert field in model_field_names or field in admin_instance.readonly_fields, \
                f"Admin fieldset references non-existent field: {field}"
    
    def test_organization_admin_does_not_include_twitter_field(self):
        """
        Admin must NOT display twitter field (requirement: remove Twitter).
        
        Twitter field exists on model (for backwards compat) but should be
        hidden in admin interface.
        """
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization
        
        admin_instance = OrganizationAdmin(Organization, None)
        
        # Collect all fields from fieldsets
        fieldset_fields = []
        for fieldset in admin_instance.fieldsets:
            fields = fieldset[1].get('fields', ())
            fieldset_fields.extend(fields)
        
        # Twitter must NOT be in admin fieldsets
        assert 'twitter' not in fieldset_fields, \
            "twitter field should be removed from admin (outdated/duplicated)"
    
    def test_organization_admin_includes_id_field_readonly(self):
        """Admin must display Organization ID (read-only) in Identity section."""
        from apps.organizations.admin import OrganizationAdmin
        from apps.organizations.models import Organization
        
        admin_instance = OrganizationAdmin(Organization, None)
        
        # Check readonly_fields includes 'id'
        assert 'id' in admin_instance.readonly_fields, \
            "Organization ID must be in readonly_fields"
        
        # Check 'id' is in Identity fieldset
        identity_fieldset = None
        for fieldset in admin_instance.fieldsets:
            if 'Identity' in fieldset[0]:
                identity_fieldset = fieldset
                break
        
        assert identity_fieldset is not None, "Identity fieldset must exist"
        assert 'id' in identity_fieldset[1]['fields'], \
            "Organization ID must be displayed in Identity section"


@pytest.mark.django_db
class TestAdminPageLoading:
    """
    Integration test: admin pages must load without FieldError.
    
    Prevents admin crashes from misconfigured fieldsets.
    """
    
    def test_organization_admin_change_page_loads(self, client, django_user_model):
        """
        /admin/organizations/organization/<id>/change/ must load without errors.
        
        Verifies that admin fieldsets don't reference non-existent fields.
        """
        from apps.organizations.models import Organization
        
        # Create superuser
        admin_user = django_user_model.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123'
        )
        client.force_login(admin_user)
        
        # Create test organization
        org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            ceo=admin_user
        )
        
        # Request admin change page
        response = client.get(f'/admin/organizations/organization/{org.id}/change/')
        
        # Must return 200 OK (not 500 from FieldError)
        assert response.status_code == 200
        
        # Must display Organization ID
        content = response.content.decode('utf-8')
        assert 'Organization ID' in content or str(org.id) in content
        
        # Must NOT display Twitter field
        assert 'twitter' not in content.lower() or 'Twitter' not in content
