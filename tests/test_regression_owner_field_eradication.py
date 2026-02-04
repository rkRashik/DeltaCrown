"""
Regression test: Verify NO usage of deprecated 'owner' field in critical modules.

This test ensures Phase 14 + 14.1 + 15 cleanup is permanent.
Any code referencing team.owner (except legacy modules) should FAIL this test.
"""

import pytest
import os
import re
from pathlib import Path


class TestOwnerFieldEradication:
    """Ensure 'owner' field usage is eliminated from vNext critical modules."""
    
    CRITICAL_MODULES = [
        'apps/organizations/services',
        'apps/organizations/views',
        'apps/organizations/api',
        'apps/competition/services',
        'apps/competition/views',
        'apps/competition/leaderboards.py',
        'apps/notifications/services.py',
        'apps/tournaments/views/registration.py',
    ]
    
    # Patterns that indicate deprecated owner field usage
    FORBIDDEN_PATTERNS = [
        r'team\.owner\b',  # team.owner access
        r"select_related\(['\"]owner['\"]\)",  # select_related('owner')
        r'\.owner_id\b',  # .owner_id access
        r'team_data\[.owner.\]',  # team_data['owner']
    ]
    
    # Allowed patterns (legitimate uses)
    ALLOWED_CONTEXTS = [
        r'MembershipRole\.OWNER',  # Enum value
        r'role.*=.*[\'"]OWNER[\'"]',  # Role assignment
        r'#.*owner',  # Comments
        r'""".*owner.*"""',  # Docstrings
        r"'''.*owner.*'''",  # Docstrings
        r'created_by.*owner',  # Comment about creator being owner
        r'owner_link',  # Admin field name
        r'profile_owner',  # Variable name (not team.owner)
        r'def.*owner',  # Function names
        r'class.*Owner',  # Class names
    ]
    
    @pytest.fixture
    def project_root(self):
        """Get absolute path to project root."""
        return Path(__file__).parent.parent
    
    def is_allowed_context(self, line: str) -> bool:
        """Check if line contains allowed usage of 'owner'."""
        for pattern in self.ALLOWED_CONTEXTS:
            if re.search(pattern, line, re.IGNORECASE):
                return True
        return False
    
    def test_no_team_owner_in_organizations_services(self, project_root):
        """Test: organizations/services has no team.owner references."""
        violations = []
        services_dir = project_root / 'apps' / 'organizations' / 'services'
        
        if not services_dir.exists():
            pytest.skip(f"Directory not found: {services_dir}")
        
        for py_file in services_dir.rglob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if self.is_allowed_context(line):
                        continue
                    
                    for pattern in self.FORBIDDEN_PATTERNS:
                        if re.search(pattern, line):
                            violations.append({
                                'file': str(py_file.relative_to(project_root)),
                                'line': line_num,
                                'content': line.strip(),
                                'pattern': pattern
                            })
        
        if violations:
            msg = "\n".join([
                f"{v['file']}:{v['line']} - {v['content']}"
                for v in violations
            ])
            pytest.fail(f"Found {len(violations)} owner field violations:\n{msg}")
    
    def test_no_team_owner_in_competition_services(self, project_root):
        """Test: competition/services has no team.owner references."""
        violations = []
        services_dir = project_root / 'apps' / 'competition' / 'services'
        
        if not services_dir.exists():
            pytest.skip(f"Directory not found: {services_dir}")
        
        for py_file in services_dir.rglob('*.py'):
            with open(py_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if self.is_allowed_context(line):
                        continue
                    
                    for pattern in self.FORBIDDEN_PATTERNS:
                        if re.search(pattern, line):
                            violations.append({
                                'file': str(py_file.relative_to(project_root)),
                                'line': line_num,
                                'content': line.strip()
                            })
        
        if violations:
            msg = "\n".join([
                f"{v['file']}:{v['line']} - {v['content']}"
                for v in violations
            ])
            pytest.fail(f"Found {len(violations)} owner field violations:\n{msg}")
    
    def test_no_team_owner_in_notifications_services(self, project_root):
        """Test: notifications/services.py has no team.owner references (Phase 14 fix)."""
        file_path = project_root / 'apps' / 'notifications' / 'services.py'
        
        if not file_path.exists():
            pytest.skip(f"File not found: {file_path}")
        
        violations = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if self.is_allowed_context(line):
                    continue
                
                # Check for team.owner pattern
                if re.search(r'team\.owner\b', line):
                    violations.append({
                        'line': line_num,
                        'content': line.strip()
                    })
        
        if violations:
            msg = "\n".join([
                f"Line {v['line']}: {v['content']}"
                for v in violations
            ])
            pytest.fail(
                f"notifications/services.py still has team.owner references "
                f"(should use team.created_by):\n{msg}"
            )
    
    def test_no_team_owner_in_tournament_registration(self, project_root):
        """Test: tournaments/views/registration.py has no team.owner (Phase 14 fix)."""
        file_path = project_root / 'apps' / 'tournaments' / 'views' / 'registration.py'
        
        if not file_path.exists():
            pytest.skip(f"File not found: {file_path}")
        
        violations = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if self.is_allowed_context(line):
                    continue
                
                # Check for team.owner pattern (should be team.created_by)
                if re.search(r'team\.owner\b', line) and 'created_by' not in line:
                    violations.append({
                        'line': line_num,
                        'content': line.strip()
                    })
        
        if violations:
            msg = "\n".join([
                f"Line {v['line']}: {v['content']}"
                for v in violations
            ])
            pytest.fail(
                f"tournaments/views/registration.py still has team.owner references "
                f"(should use team.created_by):\n{msg}"
            )
    
    def test_no_select_related_owner_in_hub(self, project_root):
        """Test: hub views don't use select_related('owner') (Phase 13 fix)."""
        hub_file = project_root / 'apps' / 'organizations' / 'views' / 'hub.py'
        
        if not hub_file.exists():
            pytest.skip(f"File not found: {hub_file}")
        
        with open(hub_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for select_related('owner') pattern
        pattern = r"select_related\(['\"]owner['\"]\)"
        if re.search(pattern, content):
            pytest.fail(
                "hub.py contains select_related('owner') - "
                "should use select_related('created_by') or remove if not needed"
            )
    
    def test_vnext_team_model_has_no_owner_field(self, project_root):
        """Test: vNext Team model does not have 'owner' field."""
        team_model = project_root / 'apps' / 'organizations' / 'models' / 'team.py'
        
        if not team_model.exists():
            pytest.skip(f"File not found: {team_model}")
        
        with open(team_model, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for owner field definition (ForeignKey, OneToOneField, etc.)
        pattern = r'^\s*owner\s*=\s*(models\.|ForeignKey|OneToOneField)'
        
        for line_num, line in enumerate(content.split('\n'), 1):
            if re.match(pattern, line):
                pytest.fail(
                    f"vNext Team model still has 'owner' field at line {line_num}.\n"
                    f"Should use 'created_by' field instead."
                )
    
    def test_api_endpoints_use_created_by(self, project_root):
        """Test: Team creation API uses created_by, not owner (Phase 11 fix)."""
        api_views = project_root / 'apps' / 'organizations' / 'api' / 'views.py'
        
        if not api_views.exists():
            pytest.skip(f"File not found: {api_views}")
        
        with open(api_views, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for team_data['owner'] pattern (should be team_data['created_by'])
        pattern = r"team_data\[['\"]owner['\"]\]"
        if re.search(pattern, content):
            pytest.fail(
                "API views contain team_data['owner'] assignment - "
                "should use team_data['created_by'] (Phase 11 fix regression)"
            )
