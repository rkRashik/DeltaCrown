"""
Legacy Dependency Guard Tests for vNext Organizations App.

These tests ensure that the vNext organizations app does NOT import
or depend on legacy teams app code. This prevents accidental coupling
during the migration period.

HARD RULES ENFORCED:
1. NO imports from apps.teams.* (except explicit migration utilities)
2. NO template references to templates/teams/*
3. NO static file references to static/teams/*

Exceptions:
- apps/organizations/adapters/* (dual-write layer, allowed by design)
- apps/organizations/tests/test_dual_write_service.py (tests dual-write)
- apps/organizations/tests/test_validation_reports.py (tests validation)
- apps/organizations/tests/test_legacy_write_enforcement.py (tests enforcement)
"""

import os
import re
import pytest
from pathlib import Path


@pytest.mark.django_db
class TestLegacyDependencyGuard:
    """
    Tests to prevent accidental legacy teams app coupling.
    
    These tests scan code for banned patterns and fail if found.
    Run these tests regularly to catch regressions.
    """
    
    def get_organizations_app_root(self):
        """Get the absolute path to apps/organizations/"""
        current_file = Path(__file__).resolve()
        # Go up from tests/ to apps/organizations/
        return current_file.parent.parent
    
    def get_python_files(self, exclude_dirs=None):
        """
        Get all Python files in apps/organizations/ (excluding specified dirs).
        
        Args:
            exclude_dirs: List of directory names to exclude (e.g., ['adapters', 'tests'])
        
        Returns:
            List of Path objects for .py files
        """
        if exclude_dirs is None:
            exclude_dirs = []
        
        root = self.get_organizations_app_root()
        python_files = []
        
        for py_file in root.rglob('*.py'):
            # Check if file is in an excluded directory
            if any(excluded_dir in py_file.parts for excluded_dir in exclude_dirs):
                continue
            python_files.append(py_file)
        
        return python_files
    
    def test_no_legacy_backend_imports_in_services(self):
        """
        Services MUST NOT import from legacy teams app.
        
        Allowed exceptions:
        - adapters/ (dual-write layer, by design)
        - tests/ (test fixtures may need legacy imports)
        """
        root = self.get_organizations_app_root()
        services_dir = root / 'services'
        
        if not services_dir.exists():
            pytest.skip("Services directory not found")
        
        # Patterns that indicate legacy imports
        banned_patterns = [
            r'from apps\.teams',
            r'import apps\.teams',
            r'from teams\.models',
            r'from teams\.services',
        ]
        
        violations = []
        
        for py_file in services_dir.rglob('*.py'):
            # Skip __init__.py and test files
            if py_file.name in ['__init__.py'] or 'test' in py_file.name:
                continue
            
            content = py_file.read_text(encoding='utf-8')
            
            for pattern in banned_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    violations.append({
                        'file': str(py_file.relative_to(root)),
                        'pattern': pattern,
                        'matches': matches
                    })
        
        assert not violations, (
            f"Found {len(violations)} legacy import violations in services/:\n" +
            "\n".join([
                f"  - {v['file']}: {v['pattern']} (found {len(v['matches'])} times)"
                for v in violations
            ])
        )
    
    def test_no_legacy_backend_imports_in_models(self):
        """
        Models MUST NOT import from legacy teams app.
        
        vNext models should be completely independent.
        """
        root = self.get_organizations_app_root()
        models_dir = root / 'models'
        
        if not models_dir.exists():
            pytest.skip("Models directory not found")
        
        banned_patterns = [
            r'from apps\.teams',
            r'import apps\.teams',
            r'from teams\.models',
        ]
        
        violations = []
        
        for py_file in models_dir.rglob('*.py'):
            if py_file.name == '__init__.py':
                continue
            
            content = py_file.read_text(encoding='utf-8')
            
            for pattern in banned_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    violations.append({
                        'file': str(py_file.relative_to(root)),
                        'pattern': pattern,
                    })
        
        assert not violations, (
            f"Found {len(violations)} legacy import violations in models/:\n" +
            "\n".join([f"  - {v['file']}: {v['pattern']}" for v in violations])
        )
    
    def test_no_legacy_backend_imports_in_views(self):
        """
        Views MUST NOT import from legacy teams app.
        
        All UI views should use vNext services and models only.
        """
        root = self.get_organizations_app_root()
        
        # Check both views.py (if exists) and views/ package
        view_files = []
        
        views_file = root / 'views.py'
        if views_file.exists():
            view_files.append(views_file)
        
        views_dir = root / 'views'
        if views_dir.exists():
            view_files.extend(views_dir.rglob('*.py'))
        
        if not view_files:
            pytest.skip("No view files found")
        
        banned_patterns = [
            r'from apps\.teams',
            r'import apps\.teams',
            r'from teams\.models',
            r'from teams\.services',
        ]
        
        violations = []
        
        for py_file in view_files:
            if py_file.name == '__init__.py':
                continue
            
            content = py_file.read_text(encoding='utf-8')
            
            for pattern in banned_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    violations.append({
                        'file': str(py_file.relative_to(root)),
                        'pattern': pattern,
                    })
        
        assert not violations, (
            f"Found {len(violations)} legacy import violations in views:\n" +
            "\n".join([f"  - {v['file']}: {v['pattern']}" for v in violations])
        )
    
    def test_no_legacy_backend_imports_in_api(self):
        """
        API endpoints MUST NOT import from legacy teams app.
        
        All API logic should use vNext services only.
        """
        root = self.get_organizations_app_root()
        api_dir = root / 'api'
        
        if not api_dir.exists():
            pytest.skip("API directory not found")
        
        banned_patterns = [
            r'from apps\.teams',
            r'import apps\.teams',
            r'from teams\.models',
            r'from teams\.services',
        ]
        
        violations = []
        
        for py_file in api_dir.rglob('*.py'):
            if py_file.name == '__init__.py' or 'test' in py_file.name:
                continue
            
            content = py_file.read_text(encoding='utf-8')
            
            for pattern in banned_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    violations.append({
                        'file': str(py_file.relative_to(root)),
                        'pattern': pattern,
                    })
        
        assert not violations, (
            f"Found {len(violations)} legacy import violations in api/:\n" +
            "\n".join([f"  - {v['file']}: {v['pattern']}" for v in violations])
        )
    
    def test_templates_use_organizations_path(self):
        """
        Verify that vNext templates are in templates/organizations/.
        
        This test checks that key templates exist in the correct location.
        """
        project_root = self.get_organizations_app_root().parent.parent
        templates_dir = project_root / 'templates' / 'organizations'
        
        # Key templates that MUST exist
        required_templates = [
            'hub/team_hub.html',
            'team/team_create.html',
            'team/team_detail.html',
            'team/team_invites.html',
            'org/organization_detail.html',
        ]
        
        missing_templates = []
        
        for template_path in required_templates:
            full_path = templates_dir / template_path
            if not full_path.exists():
                missing_templates.append(template_path)
        
        assert not missing_templates, (
            f"Missing {len(missing_templates)} required templates in templates/organizations/:\n" +
            "\n".join([f"  - {t}" for t in missing_templates])
        )
    
    def test_static_files_use_organizations_path(self):
        """
        Verify that vNext static files are in static/organizations/.
        
        This test checks that key static files exist in the correct location.
        """
        project_root = self.get_organizations_app_root().parent.parent
        static_dir = project_root / 'static' / 'organizations'
        
        # Key directories that MUST exist
        required_dirs = [
            'hub',
            'team',
            'org',
        ]
        
        missing_dirs = []
        
        for dir_name in required_dirs:
            full_path = static_dir / dir_name
            if not full_path.exists():
                missing_dirs.append(dir_name)
        
        assert not missing_dirs, (
            f"Missing {len(missing_dirs)} required directories in static/organizations/:\n" +
            "\n".join([f"  - {d}/" for d in missing_dirs])
        )
    
    def test_views_render_correct_templates(self):
        """
        Verify that views reference templates/organizations/* paths.
        
        This test scans view files for render() calls and checks template paths.
        """
        root = self.get_organizations_app_root()
        
        # Get all view files
        view_files = []
        views_file = root / 'views.py'
        if views_file.exists():
            view_files.append(views_file)
        
        views_dir = root / 'views'
        if views_dir.exists():
            view_files.extend(views_dir.rglob('*.py'))
        
        if not view_files:
            pytest.skip("No view files found")
        
        # Pattern to find render() calls with legacy templates/teams/
        legacy_template_pattern = r"render\([^,]+,\s*['\"]teams/"
        
        violations = []
        
        for py_file in view_files:
            content = py_file.read_text(encoding='utf-8')
            
            matches = re.findall(legacy_template_pattern, content)
            if matches:
                violations.append({
                    'file': str(py_file.relative_to(root)),
                    'matches': matches
                })
        
        assert not violations, (
            f"Found {len(violations)} views rendering legacy templates/teams/* templates:\n" +
            "\n".join([
                f"  - {v['file']}: {len(v['matches'])} legacy render() calls"
                for v in violations
            ])
        )


@pytest.mark.parametrize('banned_import', [
    'from apps.teams',
    'from teams.models',
    'from teams.services',
    'import apps.teams',
])
def test_no_specific_legacy_import_in_core_code(banned_import):
    """
    Parametrized test to check for specific banned imports.
    
    This test is more targeted and will show exactly which import is problematic.
    """
    root = Path(__file__).resolve().parent.parent
    
    # Exclude adapters and specific test files
    exclude_patterns = [
        'adapters/',
        'test_dual_write',
        'test_validation_reports',
        'test_legacy_write_enforcement',
        'test_no_legacy_dependencies.py',  # THIS FILE (contains test strings)
    ]
    
    python_files = []
    for py_file in root.rglob('*.py'):
        # Check exclusions
        if any(pattern in str(py_file) for pattern in exclude_patterns):
            continue
        python_files.append(py_file)
    
    violations = []
    
    for py_file in python_files:
        content = py_file.read_text(encoding='utf-8')
        
        # Check for the specific banned import (skip comments)
        if banned_import in content:
            # Get line number
            lines = content.split('\n')
            for i, line in enumerate(lines, 1):
                # Skip comment-only lines
                stripped = line.strip()
                if stripped.startswith('#'):
                    continue
                
                if banned_import in line:
                    violations.append({
                        'file': str(py_file.relative_to(root)),
                        'line': i,
                        'content': line.strip()
                    })
    
    assert not violations, (
        f"Found {len(violations)} instances of banned import '{banned_import}':\n" +
        "\n".join([
            f"  - {v['file']}:{v['line']} → {v['content']}"
            for v in violations
        ])
    )
