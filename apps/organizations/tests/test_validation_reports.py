"""
Tests for Data Validation Report Service (P5-T4).

Test Coverage:
1. Coverage % computed correctly with seeded fixtures
2. Mapping duplicates detected
3. Orphan mapping detected
4. Consistency mismatch example (membership count mismatch)
5. Dual-write health only appears when flag enabled
"""

import pytest
from datetime import timedelta
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.organizations.models import (
    Team as VNextTeam,
    TeamMembership as VNextMembership,
    TeamMigrationMap,
    TeamRanking as VNextRanking,
)
from apps.teams.models import (
    Team as LegacyTeam,
    TeamMembership as LegacyMembership,
    TeamRankingBreakdown as LegacyRanking,
)
from apps.user_profile.models import UserProfile
from apps.organizations.services.validation_report_service import generate_migration_validation_report

User = get_user_model()


@pytest.mark.django_db
class TestValidationReportCoverage:
    """Test 1: Coverage % computed correctly with seeded fixtures"""
    
    def test_coverage_calculation_100_percent(self):
        """When all legacy teams are mapped, coverage should be 100%"""
        user = User.objects.create_user(username='owner', password='test')
        
        # Create 5 legacy teams
        legacy_teams = []
        for i in range(5):
            legacy = LegacyTeam.objects.create(
                name=f'Legacy Team {i}',
                slug=f'legacy-team-{i}',
                game='valorant',
                is_active=True
            )
            legacy_teams.append(legacy)
        
        # Create 5 vNext teams and map all
        for i, legacy in enumerate(legacy_teams):
            vnext = VNextTeam.objects.create(
                name=f'Legacy Team {i}',
                slug=f'legacy-team-{i}',
                owner=user,
                status='ACTIVE',
                game_id=1
            )
            TeamMigrationMap.objects.create(
                legacy_team=legacy,
                vnext_team=vnext,
                legacy_slug=legacy.slug
            )
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify coverage
        assert report['coverage']['legacy_team_count'] == 5
        assert report['coverage']['vnext_team_count'] == 5
        assert report['coverage']['mapped_team_count'] == 5
        assert report['coverage']['unmapped_legacy_count'] == 0
        assert report['coverage']['mapping_percentage'] == 100.0
    
    def test_coverage_calculation_partial(self):
        """When only some legacy teams are mapped, coverage should be partial"""
        user = User.objects.create_user(username='owner', password='test')
        
        # Create 10 legacy teams
        legacy_teams = []
        for i in range(10):
            legacy = LegacyTeam.objects.create(
                name=f'Legacy Team {i}',
                slug=f'legacy-team-{i}',
                game='valorant',
                is_active=True
            )
            legacy_teams.append(legacy)
        
        # Map only 6 of them
        for i in range(6):
            legacy = legacy_teams[i]
            vnext = VNextTeam.objects.create(
                name=f'Legacy Team {i}',
                slug=f'legacy-team-{i}',
                owner=user,
                status='ACTIVE',
                game_id=1
            )
            TeamMigrationMap.objects.create(
                legacy_team=legacy,
                vnext_team=vnext,
                legacy_slug=legacy.slug
            )
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify coverage
        assert report['coverage']['legacy_team_count'] == 10
        assert report['coverage']['vnext_team_count'] == 6
        assert report['coverage']['legacy_teams_with_mapping'] == 6
        assert report['coverage']['unmapped_legacy_count'] == 4
        assert report['coverage']['mapping_percentage'] == 60.0


@pytest.mark.django_db
class TestValidationReportMappingHealth:
    """Test 2 & 3: Mapping duplicates and orphans detected"""
    
    def test_duplicate_legacy_ids_detected(self):
        """Duplicate legacy_team_id should be detected"""
        user = User.objects.create_user(username='owner', password='test')
        
        legacy = LegacyTeam.objects.create(
            name='Test Team',
            slug='test-team',
            game='valorant',
            is_active=True
        )
        
        vnext1 = VNextTeam.objects.create(name='Test 1', slug='test-1', owner=user, status='ACTIVE')
        vnext2 = VNextTeam.objects.create(name='Test 2', slug='test-2', owner=user, status='ACTIVE')
        
        # Create duplicate mappings with same legacy_team_id
        TeamMigrationMap.objects.create(legacy_team=legacy, vnext_team=vnext1, legacy_slug='test-team')
        TeamMigrationMap.objects.create(legacy_team=legacy, vnext_team=vnext2, legacy_slug='test-team')
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify duplicate detected
        mapping_health = report['mapping_health']
        assert mapping_health['duplicate_legacy_count'] == 1
        assert legacy.id in mapping_health['duplicate_legacy_ids']
    
    def test_duplicate_vnext_ids_detected(self):
        """Duplicate vnext_team_id should be detected"""
        user = User.objects.create_user(username='owner', password='test')
        
        legacy1 = LegacyTeam.objects.create(name='Legacy 1', slug='legacy-1', game='valorant', is_active=True)
        legacy2 = LegacyTeam.objects.create(name='Legacy 2', slug='legacy-2', game='valorant', is_active=True)
        
        vnext = VNextTeam.objects.create(name='Test', slug='test', owner=user, status='ACTIVE')
        
        # Create duplicate mappings with same vnext_team_id
        TeamMigrationMap.objects.create(legacy_team=legacy1, vnext_team=vnext, legacy_slug='legacy-1')
        TeamMigrationMap.objects.create(legacy_team=legacy2, vnext_team=vnext, legacy_slug='legacy-2')
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify duplicate detected
        mapping_health = report['mapping_health']
        assert mapping_health['duplicate_vnext_count'] == 1
        assert vnext.id in mapping_health['duplicate_vnext_ids']
    
    def test_orphan_mapping_detected(self):
        """Mappings pointing to deleted teams should be detected as orphans"""
        user = User.objects.create_user(username='owner', password='test')
        
        legacy = LegacyTeam.objects.create(name='Legacy', slug='legacy', game='valorant', is_active=True)
        vnext = VNextTeam.objects.create(name='vNext', slug='vnext', owner=user, status='ACTIVE')
        
        # Create mapping
        mapping = TeamMigrationMap.objects.create(
            legacy_team=legacy,
            vnext_team=vnext,
            legacy_slug='legacy'
        )
        
        # Delete legacy team (creates orphan)
        legacy_id = legacy.id
        legacy.delete()
        
        # Update mapping to point to non-existent legacy team
        TeamMigrationMap.objects.filter(id=mapping.id).update(legacy_team_id=legacy_id)
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify orphan detected
        mapping_health = report['mapping_health']
        assert mapping_health['orphan_count'] >= 1
        
        # Find our orphan in the list
        orphan_types = [o['type'] for o in mapping_health['orphan_mappings']]
        assert 'missing_legacy_team' in orphan_types


@pytest.mark.django_db
class TestValidationReportConsistency:
    """Test 4: Consistency mismatch example (membership count mismatch)"""
    
    def test_membership_count_mismatch_detected(self):
        """Membership count differences should be detected"""
        user = User.objects.create_user(username='owner', password='test')
        profile = UserProfile.objects.create(user=user, username='owner')
        
        # Create legacy team with 3 members
        legacy = LegacyTeam.objects.create(name='Test', slug='test', game='valorant', is_active=True)
        for i in range(3):
            member_user = User.objects.create_user(username=f'member{i}', password='test')
            member_profile = UserProfile.objects.create(user=member_user, username=f'member{i}')
            LegacyMembership.objects.create(
                team=legacy,
                profile=member_profile,
                role='PLAYER',
                status='ACTIVE'
            )
        
        # Create vNext team with only 1 member (mismatch)
        vnext = VNextTeam.objects.create(name='Test', slug='test', owner=user, status='ACTIVE', game_id=1)
        VNextMembership.objects.create(team=vnext, user=user, role='OWNER', status='ACTIVE')
        
        # Create mapping
        TeamMigrationMap.objects.create(legacy_team=legacy, vnext_team=vnext, legacy_slug='test')
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify mismatch detected
        consistency = report['consistency']
        assert consistency['membership_count_mismatch_count'] >= 1
        
        # Check samples
        mismatches = consistency['samples']['membership_count_mismatches']
        assert len(mismatches) > 0
        mismatch = mismatches[0]
        assert mismatch['legacy_count'] == 3
        assert mismatch['vnext_count'] == 1
        assert mismatch['difference'] == 2
    
    def test_name_mismatch_detected(self):
        """Name differences should be detected"""
        user = User.objects.create_user(username='owner', password='test')
        
        legacy = LegacyTeam.objects.create(name='Old Name', slug='test', game='valorant', is_active=True)
        vnext = VNextTeam.objects.create(name='New Name', slug='test', owner=user, status='ACTIVE', game_id=1)
        
        TeamMigrationMap.objects.create(legacy_team=legacy, vnext_team=vnext, legacy_slug='test')
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify mismatch detected
        consistency = report['consistency']
        assert consistency['name_mismatch_count'] >= 1
        
        mismatches = consistency['samples']['name_mismatches']
        assert len(mismatches) > 0
        assert mismatches[0]['legacy_name'] == 'Old Name'
        assert mismatches[0]['vnext_name'] == 'New Name'
    
    def test_ranking_mismatch_detected(self):
        """Ranking presence differences should be detected"""
        user = User.objects.create_user(username='owner', password='test')
        
        legacy = LegacyTeam.objects.create(name='Test', slug='test', game='valorant', is_active=True)
        vnext = VNextTeam.objects.create(name='Test', slug='test', owner=user, status='ACTIVE', game_id=1)
        
        # Create legacy ranking but not vNext ranking (mismatch)
        LegacyRanking.objects.create(team=legacy, final_total=1000, calculated_total=1000)
        
        TeamMigrationMap.objects.create(legacy_team=legacy, vnext_team=vnext, legacy_slug='test')
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify mismatch detected
        consistency = report['consistency']
        assert consistency['ranking_mismatch_count'] >= 1
        
        mismatches = consistency['samples']['ranking_mismatches']
        assert len(mismatches) > 0
        assert mismatches[0]['legacy_has_ranking'] is True
        assert mismatches[0]['vnext_has_ranking'] is False


@pytest.mark.django_db
class TestValidationReportDualWriteHealth:
    """Test 5: Dual-write health only appears when flag enabled"""
    
    @override_settings(TEAM_VNEXT_DUAL_WRITE_ENABLED=False)
    def test_dual_write_health_absent_when_disabled(self):
        """Dual-write health section should not appear when flag is False"""
        report = generate_migration_validation_report(sample_size=10)
        
        assert report['dual_write_health'] is None
        assert report['meta']['dual_write_enabled'] is False
    
    @override_settings(TEAM_VNEXT_DUAL_WRITE_ENABLED=True)
    def test_dual_write_health_present_when_enabled(self):
        """Dual-write health section should appear when flag is True"""
        report = generate_migration_validation_report(sample_size=10)
        
        assert report['dual_write_health'] is not None
        assert report['meta']['dual_write_enabled'] is True
        assert 'recent_vnext_teams' in report['dual_write_health']
        assert 'missing_legacy_count' in report['dual_write_health']
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=False
    )
    def test_dual_write_health_detects_missing_legacy(self):
        """Missing legacy shadow rows should be detected"""
        user = User.objects.create_user(username='owner', password='test')
        
        # Create recent vNext team without legacy shadow
        recent_time = timezone.now() - timedelta(hours=1)
        vnext = VNextTeam.objects.create(
            name='Recent Team',
            slug='recent-team',
            owner=user,
            status='ACTIVE',
            created_at=recent_time
        )
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify missing legacy detected
        dwh = report['dual_write_health']
        assert dwh['recent_vnext_teams'] >= 1
        assert dwh['missing_legacy_count'] >= 1
        assert dwh['severity'] == 'WARNING'  # Not strict mode
        
        # Check missing mappings
        missing = dwh['missing_mappings']
        assert len(missing) > 0
        assert any(m['vnext_team_id'] == vnext.id for m in missing)
    
    @override_settings(
        TEAM_VNEXT_DUAL_WRITE_ENABLED=True,
        TEAM_VNEXT_DUAL_WRITE_STRICT_MODE=True
    )
    def test_dual_write_health_severity_in_strict_mode(self):
        """Severity should be ERROR in strict mode"""
        user = User.objects.create_user(username='owner', password='test')
        
        # Create recent vNext team without legacy shadow
        recent_time = timezone.now() - timedelta(minutes=30)
        VNextTeam.objects.create(
            name='Recent Team',
            slug='recent-team',
            owner=user,
            status='ACTIVE',
            created_at=recent_time
        )
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Verify severity is ERROR
        dwh = report['dual_write_health']
        assert dwh['severity'] == 'ERROR'


@pytest.mark.django_db
class TestValidationReportFilters:
    """Test report filtering by game_id and region"""
    
    def test_game_id_filter(self):
        """Report should filter by game_id"""
        user = User.objects.create_user(username='owner', password='test')
        
        # Create teams for different games
        legacy1 = LegacyTeam.objects.create(name='Valorant', slug='val', game='valorant', is_active=True)
        legacy2 = LegacyTeam.objects.create(name='CSGO', slug='csgo', game='csgo', is_active=True)
        
        vnext1 = VNextTeam.objects.create(name='Valorant', slug='val', owner=user, status='ACTIVE', game_id=1)
        vnext2 = VNextTeam.objects.create(name='CSGO', slug='csgo', owner=user, status='ACTIVE', game_id=2)
        
        TeamMigrationMap.objects.create(legacy_team=legacy1, vnext_team=vnext1, legacy_slug='val')
        TeamMigrationMap.objects.create(legacy_team=legacy2, vnext_team=vnext2, legacy_slug='csgo')
        
        # Generate report with game_id filter
        report = generate_migration_validation_report(sample_size=10, game_id=1)
        
        # Should only include Valorant teams
        assert report['coverage']['legacy_team_count'] == 1
        assert report['coverage']['vnext_team_count'] == 1
        assert report['meta']['filters']['game_id'] == 1
    
    def test_region_filter(self):
        """Report should filter by region"""
        user = User.objects.create_user(username='owner', password='test')
        
        # Create teams for different regions
        legacy1 = LegacyTeam.objects.create(name='NA', slug='na', game='valorant', region='NA', is_active=True)
        legacy2 = LegacyTeam.objects.create(name='EU', slug='eu', game='valorant', region='EU', is_active=True)
        
        vnext1 = VNextTeam.objects.create(name='NA', slug='na', owner=user, status='ACTIVE', region='NA')
        vnext2 = VNextTeam.objects.create(name='EU', slug='eu', owner=user, status='ACTIVE', region='EU')
        
        TeamMigrationMap.objects.create(legacy_team=legacy1, vnext_team=vnext1, legacy_slug='na')
        TeamMigrationMap.objects.create(legacy_team=legacy2, vnext_team=vnext2, legacy_slug='eu')
        
        # Generate report with region filter
        report = generate_migration_validation_report(sample_size=10, region='NA')
        
        # Should only include NA teams
        assert report['coverage']['legacy_team_count'] == 1
        assert report['coverage']['vnext_team_count'] == 1
        assert report['meta']['filters']['region'] == 'NA'


@pytest.mark.django_db
class TestValidationReportRecommendations:
    """Test recommendation generation"""
    
    def test_recommendations_for_incomplete_coverage(self):
        """Recommendations should flag incomplete coverage"""
        user = User.objects.create_user(username='owner', password='test')
        
        # Create 5 legacy teams but only map 3
        for i in range(5):
            legacy = LegacyTeam.objects.create(
                name=f'Team {i}',
                slug=f'team-{i}',
                game='valorant',
                is_active=True
            )
            if i < 3:
                vnext = VNextTeam.objects.create(
                    name=f'Team {i}',
                    slug=f'team-{i}',
                    owner=user,
                    status='ACTIVE'
                )
                TeamMigrationMap.objects.create(legacy_team=legacy, vnext_team=vnext, legacy_slug=legacy.slug)
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Check recommendations
        recommendations = report['recommendations']
        assert len(recommendations) > 0
        
        # Should have critical recommendation about incomplete coverage
        critical_recs = [r for r in recommendations if '🔴 CRITICAL' in r and 'unmapped' in r.lower()]
        assert len(critical_recs) > 0
    
    def test_recommendations_for_perfect_migration(self):
        """Recommendations should be positive when everything is good"""
        user = User.objects.create_user(username='owner', password='test')
        
        # Create perfect migration: 5 legacy teams, all mapped, all consistent
        for i in range(5):
            legacy = LegacyTeam.objects.create(
                name=f'Team {i}',
                slug=f'team-{i}',
                game='valorant',
                is_active=True
            )
            vnext = VNextTeam.objects.create(
                name=f'Team {i}',
                slug=f'team-{i}',
                owner=user,
                status='ACTIVE',
                game_id=1
            )
            TeamMigrationMap.objects.create(legacy_team=legacy, vnext_team=vnext, legacy_slug=legacy.slug)
        
        # Generate report
        report = generate_migration_validation_report(sample_size=10)
        
        # Check recommendations
        recommendations = report['recommendations']
        
        # Should have success message
        success_recs = [r for r in recommendations if '✅' in r]
        assert len(success_recs) > 0
