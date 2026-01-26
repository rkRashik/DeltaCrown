"""
URL Name Contract Tests for Organizations App.

These tests enforce stable URL naming conventions to prevent NoReverseMatch errors.
All templates must reference only canonical URL names defined in urls.py.

Canonical URL Names:
- organizations:vnext_hub - Hub landing page
- organizations:team_create - Team creation wizard
- organizations:team_detail - Team detail page (kwarg: team_slug)
- organizations:team_invites - Team invitations dashboard
- organizations:organization_detail - Organization profile (kwarg: org_slug)
- organizations:org_create - Organization creation wizard
- organizations:org_hub - Organization hub dashboard (kwarg: org_slug)

Run: pytest apps/organizations/tests/test_url_name_contract.py -v
"""

import re
import pytest
from pathlib import Path
from django.urls import reverse, resolve, NoReverseMatch
from django.test import TestCase, SimpleTestCase, Client


class URLNamingContractTests(SimpleTestCase):
    """
    Tests that verify all canonical URL names can be reversed.
    Uses SimpleTestCase to avoid database requirements.
    """
    
    def test_vnext_hub_url_reverses(self):
        """Hub URL must reverse with canonical name 'vnext_hub'."""
        url = reverse('organizations:vnext_hub')
        self.assertEqual(url, '/teams/vnext/')
        
        # Verify it resolves back correctly
        resolved = resolve('/teams/vnext/')
        self.assertEqual(resolved.view_name, 'organizations:vnext_hub')
    
    def test_team_create_url_reverses(self):
        """Team creation URL must reverse with canonical name 'team_create'."""
        url = reverse('organizations:team_create')
        self.assertEqual(url, '/teams/create/')
        
        resolved = resolve('/teams/create/')
        self.assertEqual(resolved.view_name, 'organizations:team_create')
    
    def test_team_invites_url_reverses(self):
        """Team invites URL must reverse with canonical name 'team_invites'."""
        url = reverse('organizations:team_invites')
        self.assertEqual(url, '/teams/invites/')
        
        resolved = resolve('/teams/invites/')
        self.assertEqual(resolved.view_name, 'organizations:team_invites')
    
    def test_team_detail_url_reverses(self):
        """Team detail URL must reverse with canonical name 'team_detail' using team_slug kwarg."""
        url = reverse('organizations:team_detail', kwargs={'team_slug': 'test-team'})
        self.assertEqual(url, '/teams/test-team/')
        
        resolved = resolve('/teams/test-team/')
        self.assertEqual(resolved.view_name, 'organizations:team_detail')
        self.assertEqual(resolved.kwargs['team_slug'], 'test-team')
    
    def test_organization_detail_url_reverses(self):
        """Organization detail URL must reverse with canonical name 'organization_detail' using org_slug kwarg."""
        url = reverse('organizations:organization_detail', kwargs={'org_slug': 'test-org'})
        self.assertEqual(url, '/orgs/test-org/')
        
        resolved = resolve('/orgs/test-org/')
        self.assertEqual(resolved.view_name, 'organizations:organization_detail')
        self.assertEqual(resolved.kwargs['org_slug'], 'test-org')
    
    def test_org_create_url_reverses(self):
        """Organization creation URL must reverse with canonical name 'org_create'."""
        url = reverse('organizations:org_create')
        self.assertEqual(url, '/orgs/create/')
        
        resolved = resolve('/orgs/create/')
        self.assertEqual(resolved.view_name, 'organizations:org_create')
    
    def test_org_hub_url_reverses(self):
        """Organization hub URL must reverse with canonical name 'org_hub' using org_slug kwarg."""
        url = reverse('organizations:org_hub', kwargs={'org_slug': 'test-org'})
        self.assertEqual(url, '/orgs/test-org/hub/')
        
        resolved = resolve('/orgs/test-org/hub/')
        self.assertEqual(resolved.view_name, 'organizations:org_hub')
        self.assertEqual(resolved.kwargs['org_slug'], 'test-org')
    
    def test_no_duplicate_url_names(self):
        """Ensure no URL name collisions within organizations namespace."""
        from django.urls import get_resolver
        
        resolver = get_resolver()
        namespace = 'organizations'
        
        # Get all URL patterns in organizations namespace
        org_patterns = resolver.reverse_dict.get(namespace, {})
        
        # Should have exactly 7 named patterns (updated from 5)
        named_patterns = [name for name in org_patterns.keys() if isinstance(name, str)]
        
        expected_names = {
            'vnext_hub',
            'team_create',
            'team_invites',
            'team_detail',
            'organization_detail',
            'org_create',
            'org_hub',
        }
        from django.urls import get_resolver
        
        resolver = get_resolver()
        namespace = 'organizations'
        
        # Get all URL patterns in organizations namespace
        org_patterns = resolver.reverse_dict.get(namespace, {})
        
        # Should have exactly 5 named patterns
        named_patterns = [name for name in org_patterns.keys() if isinstance(name, str)]
        
        expected_names = {
            'vnext_hub',
            'team_create',
            'team_invites',
            'team_detail',
            'organization_detail',
        }
        
        actual_names = set(named_patterns)
        
        # Check all expected names exist
        missing = expected_names - actual_names
        self.assertEqual(missing, set(), f"Missing URL names: {missing}")
        
        # Check no unexpected names
        extra = actual_names - expected_names
        self.assertEqual(extra, set(), f"Unexpected URL names: {extra}")


class TemplatURLReferencesTests(SimpleTestCase):
    """
    Tests that verify templates only reference canonical URL names.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.templates_root = Path(__file__).parent.parent.parent.parent / 'templates' / 'organizations'
        
        # Canonical URL names that are allowed
        cls.allowed_url_names = {
            'vnext_hub',
            'team_create',
            'team_invites',
            'org_create',
            'org_hub',
        }
        
        # Forbidden URL names (common mistakes)
        cls.forbidden_url_names = {
            'hub',  # Should be vnext_hub or org_hub
            'create',  # Should be team_create or org_create
            'invites',  # Should be team_invites
            'detail',  # Should be team_detail or organization_detail
            'organization_create',  # Should be org_create (canonical short form)
            'invites',  # Should be team_invites
            'detail',  # Should be team_detail or organization_detail
        }
    
    def test_no_forbidden_url_names_in_templates(self):
        """Templates must not reference forbidden URL names."""
        if not self.templates_root.exists():
            pytest.skip(f"Templates directory not found: {self.templates_root}")
        
        violations = []
        
        for html_file in self.templates_root.rglob('*.html'):
            content = html_file.read_text(encoding='utf-8')
            
            # Check for forbidden names
            for forbidden_name in self.forbidden_url_names:
                pattern = rf"{{% url 'organizations:{forbidden_name}'"
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': str(html_file.relative_to(self.templates_root)),
                        'line': line_num,
                        'forbidden_name': forbidden_name,
                        'issue': f"Uses forbidden URL name 'organizations:{forbidden_name}'",
                    })
        
        self.assertEqual(violations, [], 
            f"Found {len(violations)} forbidden URL reference(s) in templates:\n" +
            '\n'.join([f"  {v['file']}:{v['line']} - {v['issue']}" for v in violations])
        )
    
    def test_all_template_url_references_are_valid(self):
        """All {% url 'organizations:...' %} references must use canonical names."""
        if not self.templates_root.exists():
            pytest.skip(f"Templates directory not found: {self.templates_root}")
        
        violations = []
        
        for html_file in self.templates_root.rglob('*.html'):
            content = html_file.read_text(encoding='utf-8')
            
            # Find all organizations URL references
            pattern = r"{{% url 'organizations:([a-zA-Z_]+)'"
            matches = re.finditer(pattern, content)
            
            for match in matches:
                url_name = match.group(1)
                
                if url_name not in self.allowed_url_names:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': str(html_file.relative_to(self.templates_root)),
                        'line': line_num,
                        'url_name': url_name,
                        'issue': f"References unknown URL name 'organizations:{url_name}'",
                        'suggestion': f"Must be one of: {', '.join(sorted(self.allowed_url_names))}",
                    })
        
        self.assertEqual(violations, [],
            f"Found {len(violations)} invalid URL reference(s) in templates:\n" +
            '\n'.join([f"  {v['file']}:{v['line']} - {v['issue']} ({v['suggestion']})" for v in violations])
        )
    
    def test_team_detail_uses_correct_kwarg(self):
        """Team detail URL references must use 'team_slug' kwarg, not 'slug'."""
        if not self.templates_root.exists():
            pytest.skip(f"Templates directory not found: {self.templates_root}")
        
        violations = []
        
        for html_file in self.templates_root.rglob('*.html'):
            content = html_file.read_text(encoding='utf-8')
            
            # Find team_detail URL references with wrong kwarg
            # Pattern: {% url 'organizations:team_detail' slug=...
            wrong_pattern = r"{{% url 'organizations:team_detail' slug="
            matches = re.finditer(wrong_pattern, content)
            
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                violations.append({
                    'file': str(html_file.relative_to(self.templates_root)),
                    'line': line_num,
                    'issue': "Uses 'slug=' instead of 'team_slug=' for team_detail URL",
                })
        
        self.assertEqual(violations, [],
            f"Found {len(violations)} incorrect kwarg usage(s) in templates:\n" +
            '\n'.join([f"  {v['file']}:{v['line']} - {v['issue']}" for v in violations])
        )
    
    def test_org_detail_uses_correct_kwarg(self):
        """Organization detail URL references must use 'org_slug' kwarg."""
        if not self.templates_root.exists():
            pytest.skip(f"Templates directory not found: {self.templates_root}")
        
        violations = []
        
        for html_file in self.templates_root.rglob('*.html'):
            content = html_file.read_text(encoding='utf-8')
            
            # Find organization_detail URL references with wrong kwarg
            wrong_pattern = r"{{% url 'organizations:organization_detail' slug="
            matches = re.finditer(wrong_pattern, content)
            
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                violations.append({
                    'file': str(html_file.relative_to(self.templates_root)),
                    'line': line_num,
                    'issue': "Uses 'slug=' instead of 'org_slug=' for organization_detail URL",
                })
        
        self.assertEqual(violations, [],
            f"Found {len(violations)} incorrect kwarg usage(s) in templates:\n" +
            '\n'.join([f"  {v['file']}:{v['line']} - {v['issue']}" for v in violations])
        )


class URLSmokeTests(TestCase):
    """
    Smoke tests to verify URLs load without 500 errors.
    May return redirects (302) due to auth/feature flags, but must not crash.
    """
    
    def setUp(self):
        self.client = Client()
    
    def test_vnext_hub_loads_without_500(self):
        """Hub page must not return 500 error (200 or 302 acceptable)."""
        response = self.client.get('/teams/vnext/')
        self.assertIn(response.status_code, [200, 302], 
            f"Hub returned {response.status_code}, expected 200 or 302")
    
    def test_team_create_loads_without_500(self):
        """Team creation page must not return 500 error (200 or 302 acceptable)."""
        response = self.client.get('/teams/create/')
        self.assertIn(response.status_code, [200, 302],
            f"Team create returned {response.status_code}, expected 200 or 302")
    
    def test_team_invites_loads_without_500(self):
        """Team invites page must not return 500 error (200 or 302 acceptable)."""
        response = self.client.get('/teams/invites/')
        self.assertIn(response.status_code, [200, 302],
            f"Team invites returned {response.status_code}, expected 200 or 302")
    
    def test_team_detail_with_invalid_slug_returns_404_not_500(self):
        """Team detail with non-existent slug should return 404, not 500."""
        response = self.client.get('/teams/nonexistent-team-slug-12345/')
        self.assertIn(response.status_code, [302, 404],
            f"Team detail returned {response.status_code}, expected 404 or 302 (redirect)")
    
    def test_org_detail_with_invalid_slug_returns_404_not_500(self):
        """Organization detail with non-existent slug should return 404, not 500."""
        response = self.client.get('/orgs/nonexistent-org-slug-12345/')
        self.assertIn(response.status_code, [302, 404],
            f"Org detail returned {response.status_code}, expected 404 or 302 (redirect)")


class URLKwargsValidationTests(SimpleTestCase):
    """
    Tests to ensure URL patterns expect the correct kwargs.
    """
    
    def test_team_detail_expects_team_slug_kwarg(self):
        """Team detail URL pattern must expect 'team_slug' kwarg."""
        # This should work
        url = reverse('organizations:team_detail', kwargs={'team_slug': 'test'})
        self.assertEqual(url, '/teams/test/')
        
        # This should fail
        with self.assertRaises(NoReverseMatch):
            reverse('organizations:team_detail', kwargs={'slug': 'test'})
    
    def test_organization_detail_expects_org_slug_kwarg(self):
        """Organization detail URL pattern must expect 'org_slug' kwarg."""
        # This should work
        url = reverse('organizations:organization_detail', kwargs={'org_slug': 'test'})
        self.assertEqual(url, '/orgs/test/')
        
        # This should fail
        with self.assertRaises(NoReverseMatch):
            reverse('organizations:organization_detail', kwargs={'slug': 'test'})
