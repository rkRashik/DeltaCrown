"""
Regression Test: Prevent 'owner' Field References

This test ensures that the 'owner' field error is never reintroduced.
The Team model uses 'created_by', not 'owner'.

ISSUE: FieldError: Invalid field name(s) given in select_related: 'owner'
FIXED: 2026-02-03 - All references changed from 'owner' to 'created_by'
"""

import pytest
import re
from pathlib import Path


def get_organization_service_files():
    """Get all Python files in apps/organizations/services/"""
    base_path = Path(__file__).parent.parent / "apps" / "organizations" / "services"
    return list(base_path.rglob("*.py"))


def get_organization_test_files():
    """Get all Python test files in apps/organizations/tests/"""
    base_path = Path(__file__).parent.parent / "apps" / "organizations" / "tests"
    return list(base_path.rglob("test_*.py"))


def check_file_for_owner_references(file_path):
    """
    Check if file contains dangerous 'owner' field references.
    
    Allowed:
        - MembershipRole.OWNER (enum value)
        - role == MembershipRole.OWNER (comparison)
        - "owner" in comments
        - owner in string literals (not field access)
    
    Forbidden:
        - select_related('owner')
        - prefetch_related('owner')
        - team.owner (field access)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove comments (lines starting with #)
    lines = content.split('\n')
    code_lines = [line for line in lines if not line.strip().startswith('#')]
    code_content = '\n'.join(code_lines)
    
    # Remove docstrings
    code_content = re.sub(r'""".*?"""', '', code_content, flags=re.DOTALL)
    code_content = re.sub(r"'''.*?'''", '', code_content, flags=re.DOTALL)
    
    # Check for forbidden patterns
    forbidden_patterns = [
        r"select_related\(['\"]owner['\"]\)",  # select_related('owner')
        r"prefetch_related\(['\"]owner['\"]\)",  # prefetch_related('owner')
        r"\.owner\b(?!\s*=)",  # .owner (field access, not assignment)
    ]
    
    violations = []
    for pattern in forbidden_patterns:
        matches = re.finditer(pattern, code_content)
        for match in matches:
            # Skip if this is MembershipRole.OWNER
            if 'MembershipRole.OWNER' in match.group():
                continue
            
            # Find line number
            line_num = code_content[:match.start()].count('\n') + 1
            violations.append({
                'pattern': pattern,
                'line': line_num,
                'match': match.group()
            })
    
    return violations


@pytest.mark.regression
def test_no_owner_field_in_services():
    """
    Regression test: Ensure 'owner' field is not referenced in service layer.
    
    The Team model uses 'created_by', not 'owner'.
    This test prevents the FieldError from being reintroduced.
    """
    service_files = get_organization_service_files()
    assert len(service_files) > 0, "No service files found to check"
    
    all_violations = {}
    for file_path in service_files:
        violations = check_file_for_owner_references(file_path)
        if violations:
            all_violations[str(file_path)] = violations
    
    if all_violations:
        error_msg = "❌ REGRESSION: 'owner' field references found!\n\n"
        for file_path, violations in all_violations.items():
            error_msg += f"File: {file_path}\n"
            for v in violations:
                error_msg += f"  Line {v['line']}: {v['match']}\n"
        
        error_msg += "\n⚠️  Team model uses 'created_by', not 'owner'.\n"
        error_msg += "Replace with: select_related('created_by') or .created_by\n"
        
        pytest.fail(error_msg)


@pytest.mark.regression
def test_no_owner_field_in_tests():
    """
    Regression test: Ensure test fixtures use 'created_by', not 'owner'.
    
    Tests should use team.created_by, not team.owner.
    """
    test_files = get_organization_test_files()
    assert len(test_files) > 0, "No test files found to check"
    
    all_violations = {}
    for file_path in test_files:
        # For tests, also check for TeamFactory(owner=...) usage
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for TeamFactory(owner=...)
        factory_pattern = r"TeamFactory\.create\([^)]*owner\s*="
        matches = list(re.finditer(factory_pattern, content))
        if matches:
            violations = []
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                violations.append({
                    'pattern': 'TeamFactory(owner=...)',
                    'line': line_num,
                    'match': 'TeamFactory(..., owner=...)'
                })
            all_violations[str(file_path)] = violations
    
    if all_violations:
        error_msg = "❌ REGRESSION: 'owner' parameter in TeamFactory found!\n\n"
        for file_path, violations in all_violations.items():
            error_msg += f"File: {file_path}\n"
            for v in violations:
                error_msg += f"  Line {v['line']}: {v['match']}\n"
        
        error_msg += "\n⚠️  Use: TeamFactory.create(created_by=user)\n"
        error_msg += "Not: TeamFactory.create(owner=user)\n"
        
        pytest.fail(error_msg)


@pytest.mark.regression
def test_team_model_has_created_by_not_owner():
    """
    Regression test: Verify Team model has 'created_by' field, not 'owner'.
    """
    from apps.organizations.models import Team
    
    # Check field exists
    assert hasattr(Team, 'created_by'), "Team model must have 'created_by' field"
    
    # Check 'owner' does not exist as a field
    field_names = [f.name for f in Team._meta.get_fields()]
    assert 'owner' not in field_names, "Team model should NOT have 'owner' field (use 'created_by')"
    assert 'created_by' in field_names, "Team model must have 'created_by' field"


if __name__ == '__main__':
    # Run this test standalone to check current codebase
    print("🔍 Checking for 'owner' field references...\n")
    
    test_no_owner_field_in_services()
    print("✅ Service layer: PASS\n")
    
    test_no_owner_field_in_tests()
    print("✅ Test files: PASS\n")
    
    test_team_model_has_created_by_not_owner()
    print("✅ Model field: PASS\n")
    
    print("🎉 All regression checks passed!")
