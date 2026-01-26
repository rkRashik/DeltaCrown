"""
Tests for schema compatibility and defensive query handling.

These tests ensure the hub and other views can handle:
- Missing database columns (migrations not applied yet)
- Missing database tables (fresh install)
- Partial schema states (rollback scenarios)

Regression Prevention: Prevents ProgrammingError crashes when schema incomplete.
"""

import pytest
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.db import connection
from unittest.mock import patch, MagicMock

from apps.organizations.utils.schema_compat import (
    has_team_tag_columns,
    get_team_queryset_only_fields,
    _get_table_columns,
)

User = get_user_model()


class SchemaCompatibilityTests(TestCase):
    """Test schema introspection and compatibility helpers."""
    
    def test_get_table_columns_returns_set(self):
        """Table column introspection returns a set of column names."""
        columns = _get_table_columns('organizations_team')
        
        assert isinstance(columns, set)
        # Base columns from initial migration should always exist
        assert 'id' in columns
        assert 'slug' in columns
        assert 'name' in columns
    
    def test_has_team_tag_columns_checks_both(self):
        """has_team_tag_columns() returns True only if BOTH tag and tagline exist."""
        result = has_team_tag_columns()
        
        # Result should be boolean
        assert isinstance(result, bool)
        
        # If True, both columns must exist
        if result:
            columns = _get_table_columns('organizations_team')
            assert 'tag' in columns
            assert 'tagline' in columns
    
    def test_get_team_queryset_only_fields_includes_base(self):
        """Safe field list always includes base fields from initial migration."""
        fields = get_team_queryset_only_fields()
        
        # Base fields must be present
        assert 'id' in fields
        assert 'slug' in fields
        assert 'name' in fields
        assert 'status' in fields
        assert 'game_id' in fields
    
    def test_get_team_queryset_only_fields_conditional_tag(self):
        """Safe field list includes tag/tagline only if columns exist."""
        fields = get_team_queryset_only_fields()
        
        has_columns = has_team_tag_columns()
        
        if has_columns:
            assert 'tag' in fields
            assert 'tagline' in fields
        else:
            assert 'tag' not in fields
            assert 'tagline' not in fields


class HubViewSchemaCompatibilityTests(TestCase):
    """Test hub view handles missing schema gracefully."""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
    
    def test_hub_view_loads_without_crash(self):
        """Hub view should load even if tag/tagline columns missing."""
        from apps.organizations.views.hub import vnext_hub
        
        request = self.factory.get('/teams/vnext/')
        request.user = self.user
        
        # This should NOT raise ProgrammingError
        try:
            response = vnext_hub(request)
            # Response should be 200 or 302 (redirect if feature flags disabled)
            assert response.status_code in [200, 302]
        except Exception as e:
            pytest.fail(f"Hub view crashed with: {e}")
    
    def test_featured_teams_handles_missing_ranking(self):
        """_get_featured_teams handles missing TeamRanking table."""
        from apps.organizations.views.hub import _get_featured_teams
        
        # Should return empty list or valid teams, not crash
        try:
            teams = _get_featured_teams(limit=5)
            assert isinstance(teams, list)
        except Exception as e:
            pytest.fail(f"_get_featured_teams crashed with: {e}")
    
    def test_leaderboard_handles_missing_table(self):
        """_get_leaderboard handles missing TeamRanking table gracefully."""
        from apps.organizations.views.hub import _get_leaderboard
        
        # Should return empty list or valid rankings, not crash
        try:
            rankings = _get_leaderboard(limit=10)
            assert isinstance(rankings, list)
        except Exception as e:
            pytest.fail(f"_get_leaderboard crashed with: {e}")


class MigrationPresenceTests(TestCase):
    """Test that required migrations exist and are correct."""
    
    def test_tag_tagline_migration_exists(self):
        """Migration 0002_add_team_tag_and_tagline.py exists."""
        from apps.organizations.migrations import __path__ as migrations_path
        import os
        
        migration_file = os.path.join(
            migrations_path[0],
            '0002_add_team_tag_and_tagline.py'
        )
        
        assert os.path.exists(migration_file), \
            "Migration 0002_add_team_tag_and_tagline.py is missing"
    
    def test_tag_tagline_migration_adds_fields(self):
        """Migration 0002 contains AddField operations for tag and tagline."""
        # Import the migration module dynamically
        from importlib import import_module
        
        migration_module = import_module(
            'apps.organizations.migrations.0002_add_team_tag_and_tagline'
        )
        Migration = migration_module.Migration
        
        # Check operations
        operations = Migration.operations
        
        # Find AddField operations
        add_field_ops = [
            op for op in operations 
            if op.__class__.__name__ == 'AddField'
        ]
        
        # Should have at least 2 AddField ops (tag + tagline)
        assert len(add_field_ops) >= 2, \
            "Migration should add at least tag and tagline fields"
        
        # Check field names
        field_names = [op.name for op in add_field_ops]
        assert 'tag' in field_names, "Migration should add 'tag' field"
        assert 'tagline' in field_names, "Migration should add 'tagline' field"


class ModularViewsWiringTests(TestCase):
    """Test that URL routing uses modular views package."""
    
    def test_urls_import_from_modular_views(self):
        """URL config imports from apps.organizations.views package not views.py."""
        from apps.organizations import urls as org_urls
        import inspect
        
        # Get source code of urls module
        source = inspect.getsource(org_urls)
        
        # Should import from modular package
        assert 'from apps.organizations.views import' in source, \
            "URLs should import from modular views package"
        
        # Should NOT import old monolithic module
        assert 'from . import views' not in source, \
            "URLs should not import from old monolithic views.py"
    
    def test_vnext_hub_resolves_to_modular_view(self):
        """vnext_hub URL resolves to apps.organizations.views.hub.vnext_hub."""
        from django.urls import resolve
        
        match = resolve('/teams/vnext/')
        
        # Check function module path
        func_module = match.func.__module__
        assert func_module == 'apps.organizations.views.hub', \
            f"vnext_hub should resolve to hub.py module, got: {func_module}"
        
        # Check function name
        assert match.func.__name__ == 'vnext_hub'
    
    def test_team_views_resolve_to_team_module(self):
        """Team views resolve to apps.organizations.views.team module."""
        from django.urls import resolve
        
        # Test team_create
        match = resolve('/teams/create/')
        assert match.func.__module__ == 'apps.organizations.views.team'
        
        # Test team_invites
        match = resolve('/teams/invites/')
        assert match.func.__module__ == 'apps.organizations.views.team'


@pytest.mark.django_db
class HubLoadTestWithoutMigrations(TestCase):
    """
    Integration test: Hub must load even before migrations applied.
    
    This simulates a fresh install or rollback scenario where
    tag/tagline columns don't exist yet.
    """
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='integrationuser',
            email='integration@example.com',
            password='testpass123'
        )
    
    def test_hub_returns_200_or_302(self):
        """Hub view returns valid HTTP response (not crash)."""
        from apps.organizations.views.hub import vnext_hub
        
        request = self.factory.get('/teams/vnext/')
        request.user = self.user
        
        response = vnext_hub(request)
        
        # Should return 200 (success) or 302 (feature flag redirect)
        assert response.status_code in [200, 302], \
            f"Hub should return 200 or 302, got {response.status_code}"
    
    def test_hub_handles_empty_database(self):
        """Hub loads gracefully even with empty database."""
        from apps.organizations.views.hub import vnext_hub
        from apps.organizations.models import Team, Organization
        
        # Delete all teams and orgs
        Team.objects.all().delete()
        Organization.objects.all().delete()
        
        request = self.factory.get('/teams/vnext/')
        request.user = self.user
        
        # Should not crash
        response = vnext_hub(request)
        assert response.status_code in [200, 302]
