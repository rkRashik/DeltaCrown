"""
Test suite for apps.organizations.

This module contains comprehensive tests for the Team & Organization vNext system.

Test Coverage Requirements:
- Models: 80%+ line coverage
- Service layer (Phase 2): 85%+ line coverage
- Views (Phase 3): 75%+ line coverage

Test Organization:
- test_organization.py: Organization and OrganizationMembership model tests
- test_team.py: Team model tests
- test_membership.py: TeamMembership model tests
- test_ranking.py: TeamRanking and OrganizationRanking model tests
- test_migration.py: TeamMigrationMap model tests
- test_activity.py: TeamActivityLog model tests
- factories.py: Factory Boy fixtures for all models

Running Tests:
    # All organization tests
    pytest apps/organizations/tests/

    # Specific test file
    pytest apps/organizations/tests/test_team.py

    # With coverage report
    pytest apps/organizations/tests/ --cov=apps.organizations --cov-report=term-missing

Performance Target:
- Full test suite must run in <30 seconds
- Individual test files should run in <5 seconds
"""
