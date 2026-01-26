"""
De-legacy Guards: Prevent Runtime Dependency on Legacy Teams App.

These tests enforce ZERO runtime dependency on the legacy apps/teams module.
They fail fast if any non-adapter code attempts to import or use legacy teams.

Test Philosophy:
- Adapter layer (apps/organizations/adapters/) is ALLOWED to import legacy
- Dual-write tooling (services/dual_write_service.py) is ALLOWED
- Everything else MUST NOT import from apps.teams

Run: pytest apps/organizations/tests/test_delegacy_guards.py -v
"""

import os
import re
import pytest
from pathlib import Path
from django.urls import reverse, resolve
from django.test import TestCase


class LegacyImportGuardTests(TestCase):
    """
    Tests to prevent accidental legacy teams imports in vNext code.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.orgs_root = Path(__file__).parent.parent
        cls.allowed_legacy_files = {
            'adapters/team_adapter.py',
            'adapters/tournament_helpers.py',
            'adapters/flags.py',
            'adapters/metrics.py',
            'services/dual_write_service.py',
            'services/validation_report_service.py',
            'tests/test_dual_write_service.py',
            'tests/test_legacy_write_enforcement.py',
            'tests/test_validation_reports.py',
            'tests/test_no_legacy_dependencies.py',
            'tests/test_delegacy_guards.py',  # this file
        }
    
    def test_no_legacy_imports_in_views(self):
        """Views must not import from apps.teams."""
        views_dir = self.orgs_root / 'views'
        violations = []
        
        for py_file in views_dir.rglob('*.py'):
            if py_file.name == '__init__.py':
                continue
                
            content = py_file.read_text(encoding='utf-8')
            
            # Check for legacy imports
            patterns = [
                r'from apps\.teams',
                r'import apps\.teams',
                r'from teams\.models',
                r'from teams\.services',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': str(py_file.relative_to(self.orgs_root)),
                        'line': line_num,
                        'pattern': pattern,
                        'issue': f'Legacy import found: {match.group()}',
                    })
        
        assert not violations, (
            f"Found {len(violations)} legacy import(s) in views:\n" +
            '\n'.join([f"  {v['file']}:{v['line']} - {v['issue']}" for v in violations])
        )
    
    def test_no_legacy_imports_in_services(self):
        """Services (except dual-write) must not import from apps.teams."""
        services_dir = self.orgs_root / 'services'
        violations = []
        
        for py_file in services_dir.rglob('*.py'):
            if py_file.name == '__init__.py':
                continue
            
            # Check if this file is allowed
            rel_path = str(py_file.relative_to(self.orgs_root)).replace('\\', '/')
            if rel_path in self.allowed_legacy_files:
                continue
                
            content = py_file.read_text(encoding='utf-8')
            
            # Check for legacy imports
            patterns = [
                r'from apps\.teams',
                r'import apps\.teams',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': rel_path,
                        'line': line_num,
                        'issue': f'Legacy import found: {match.group()}',
                    })
        
        assert not violations, (
            f"Found {len(violations)} legacy import(s) in services:\n" +
            '\n'.join([f"  {v['file']}:{v['line']} - {v['issue']}" for v in violations])
        )
    
    def test_no_legacy_imports_in_api(self):
        """API endpoints must not import from apps.teams."""
        api_dir = self.orgs_root / 'api'
        violations = []
        
        for py_file in api_dir.rglob('*.py'):
            if py_file.name == '__init__.py':
                continue
                
            content = py_file.read_text(encoding='utf-8')
            
            # Check for legacy imports
            patterns = [
                r'from apps\.teams',
                r'import apps\.teams',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': str(py_file.relative_to(self.orgs_root)),
                        'line': line_num,
                        'issue': f'Legacy import found: {match.group()}',
                    })
        
        assert not violations, (
            f"Found {len(violations)} legacy import(s) in API:\n" +
            '\n'.join([f"  {v['file']}:{v['line']} - {v['issue']}" for v in violations])
        )


class TemplateGuardTests(TestCase):
    """
    Tests to prevent legacy template references.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.templates_root = Path(__file__).parent.parent.parent.parent / 'templates' / 'organizations'
    
    def test_no_legacy_template_extends(self):
        """Templates must not extend from templates/teams/."""
        violations = []
        
        if not self.templates_root.exists():
            pytest.skip(f"Templates directory not found: {self.templates_root}")
        
        for html_file in self.templates_root.rglob('*.html'):
            content = html_file.read_text(encoding='utf-8')
            
            # Check for legacy template references
            patterns = [
                r'{%\s*extends\s+["\']teams/',
                r'{%\s*include\s+["\']teams/',
                r'templates/teams/',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': str(html_file.relative_to(self.templates_root)),
                        'line': line_num,
                        'issue': f'Legacy template reference: {match.group()}',
                    })
        
        assert not violations, (
            f"Found {len(violations)} legacy template reference(s):\n" +
            '\n'.join([f"  {v['file']}:{v['line']} - {v['issue']}" for v in violations])
        )
    
    def test_no_legacy_static_references(self):
        """Templates must not reference static/teams/."""
        violations = []
        
        if not self.templates_root.exists():
            pytest.skip(f"Templates directory not found: {self.templates_root}")
        
        for html_file in self.templates_root.rglob('*.html'):
            content = html_file.read_text(encoding='utf-8')
            
            # Check for legacy static references
            patterns = [
                r'static/teams/',
                r'{%\s*static\s+["\']teams/',
            ]
            
            for pattern in patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    line_num = content[:match.start()].count('\n') + 1
                    violations.append({
                        'file': str(html_file.relative_to(self.templates_root)),
                        'line': line_num,
                        'issue': f'Legacy static reference: {match.group()}',
                    })
        
        assert not violations, (
            f"Found {len(violations)} legacy static reference(s):\n" +
            '\n'.join([f"  {v['file']}:{v['line']} - {v['issue']}" for v in violations])
        )


class URLRoutingGuardTests(TestCase):
    """
    Tests to ensure vNext URLs are correctly configured.
    """
    
    def test_vnext_hub_url_resolves(self):
        """Hub URL /teams/vnext/ must resolve to organizations.vnext_hub."""
        url = reverse('organizations:vnext_hub')
        assert url == '/teams/vnext/', f"Expected /teams/vnext/, got {url}"
        
        resolved = resolve('/teams/vnext/')
        assert resolved.view_name == 'organizations:vnext_hub'
        assert 'organizations.views' in str(resolved.func.__module__)
    
    def test_team_create_url_resolves(self):
        """Team creation URL /teams/create/ must resolve to organizations.team_create."""
        url = reverse('organizations:team_create')
        assert url == '/teams/create/', f"Expected /teams/create/, got {url}"
        
        resolved = resolve('/teams/create/')
        assert resolved.view_name == 'organizations:team_create'
        assert 'organizations.views' in str(resolved.func.__module__)
    
    def test_team_invites_url_resolves(self):
        """Invites URL /teams/invites/ must resolve to organizations.team_invites."""
        url = reverse('organizations:team_invites')
        assert url == '/teams/invites/', f"Expected /teams/invites/, got {url}"
        
        resolved = resolve('/teams/invites/')
        assert resolved.view_name == 'organizations:team_invites'
        assert 'organizations.views' in str(resolved.func.__module__)
    
    def test_team_detail_url_resolves(self):
        """Team detail URL /teams/<slug>/ must resolve to organizations.team_detail."""
        url = reverse('organizations:team_detail', kwargs={'team_slug': 'test-team'})
        assert url == '/teams/test-team/', f"Expected /teams/test-team/, got {url}"
        
        resolved = resolve('/teams/test-team/')
        assert resolved.view_name == 'organizations:team_detail'
        assert 'organizations.views' in str(resolved.func.__module__)
    
    def test_org_detail_url_resolves(self):
        """Organization detail URL /orgs/<slug>/ must resolve to organizations.organization_detail."""
        url = reverse('organizations:organization_detail', kwargs={'org_slug': 'test-org'})
        assert url == '/orgs/test-org/', f"Expected /orgs/test-org/, got {url}"
        
        resolved = resolve('/orgs/test-org/')
        assert resolved.view_name == 'organizations:organization_detail'
        assert 'organizations.views' in str(resolved.func.__module__)


class StaticFilesGuardTests(TestCase):
    """
    Tests to ensure static files are properly organized.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.static_root = Path(__file__).parent.parent.parent.parent / 'static' / 'organizations'
    
    def test_static_files_organized(self):
        """Static JS files must exist in proper subfolders."""
        if not self.static_root.exists():
            pytest.skip(f"Static directory not found: {self.static_root}")
        
        expected_files = {
            'hub/vnext_hub.js': 'Hub JavaScript',
            'team/team_create.js': 'Team creation JavaScript',
            'team/team_detail.js': 'Team detail JavaScript',
            'team/team_invites.js': 'Team invites JavaScript',
            'org/organization_detail.js': 'Organization detail JavaScript',
        }
        
        missing = []
        for file_path, description in expected_files.items():
            full_path = self.static_root / file_path
            if not full_path.exists():
                missing.append(f"{file_path} ({description})")
        
        assert not missing, (
            f"Missing {len(missing)} expected static file(s):\n" +
            '\n'.join([f"  - {f}" for f in missing])
        )


class InvitesVNextGuardTests(TestCase):
    """
    Tests to ensure invites functionality uses vNext models only.
    """
    
    def test_invites_api_endpoint_exists(self):
        """Invites API endpoint must exist and be properly routed."""
        url = reverse('organizations_api:list_invites')
        assert '/api/vnext/teams/invites/' in url
    
    def test_accept_membership_endpoint_exists(self):
        """Accept membership invite endpoint must exist."""
        url = reverse('organizations_api:accept_membership', kwargs={'membership_id': 1})
        assert '/api/vnext/teams/invites/membership/1/accept/' in url
    
    def test_decline_membership_endpoint_exists(self):
        """Decline membership invite endpoint must exist."""
        url = reverse('organizations_api:decline_membership', kwargs={'membership_id': 1})
        assert '/api/vnext/teams/invites/membership/1/decline/' in url
    
    def test_accept_email_endpoint_exists(self):
        """Accept email invite endpoint must exist."""
        import uuid
        token = uuid.uuid4()
        url = reverse('organizations_api:accept_email', kwargs={'token': token})
        assert f'/api/vnext/teams/invites/email/{token}/accept/' in url
    
    def test_decline_email_endpoint_exists(self):
        """Decline email invite endpoint must exist."""
        import uuid
        token = uuid.uuid4()
        url = reverse('organizations_api:decline_email', kwargs={'token': token})
        assert f'/api/vnext/teams/invites/email/{token}/decline/' in url
