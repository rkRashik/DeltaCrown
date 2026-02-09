"""
Data Validation Report Service for Phase 5 migration (P5-T4).

Provides repeatable validation/report tooling to measure migration readiness
and data correctness between legacy (apps.teams) and vNext (apps.organizations).

Key Metrics:
- Coverage %: How much legacy data is represented in vNext + mapped
- Mapping completeness: TeamMigrationMap coverage and uniqueness
- Consistency checks: Spot-verify fields across legacy â†” vNext
- Dual-write health: Detect missing legacy shadow rows after vNext writes

Usage:
    from apps.organizations.services.validation_report_service import generate_migration_validation_report
    
    report = generate_migration_validation_report(sample_size=50, game_id=1)
    print(f"Coverage: {report['coverage']['mapping_percentage']:.1f}%")
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from django.conf import settings
from django.db import models
from django.db.models import Q, Count, Exists, OuterRef
from django.utils import timezone

from apps.organizations.models import (
    Team as VNextTeam,
    TeamMembership as VNextMembership,
    TeamMigrationMap,
    TeamRanking as VNextRanking,
)
from apps.organizations.models import (
    Team as LegacyTeam,
    TeamMembership as LegacyMembership,
    TeamRankingBreakdown as LegacyRanking,
)

logger = logging.getLogger(__name__)


def generate_migration_validation_report(
    *,
    sample_size: int = 50,
    game_id: Optional[int] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive validation report for team migration.
    
    Args:
        sample_size: Number of teams to sample for consistency checks
        game_id: Filter by game_id (optional)
        region: Filter by region (optional)
    
    Returns:
        JSON-serializable dict with:
        - meta: timestamps, environment flags, sample_size
        - coverage: totals and percentages
        - mapping_health: duplicates, missing links, orphan mappings
        - consistency: summary of mismatches + samples
        - dual_write_health: only if TEAM_VNEXT_DUAL_WRITE_ENABLED=True
        - recommendations: human-readable next actions
    """
    start_time = timezone.now()
    
    # Collect all metrics
    meta = _collect_meta(sample_size, game_id, region)
    coverage = _calculate_coverage(game_id, region)
    mapping_health = _check_mapping_health()
    consistency = _check_consistency(sample_size, game_id, region)
    dual_write_health = _check_dual_write_health() if meta['dual_write_enabled'] else None
    recommendations = _generate_recommendations(coverage, mapping_health, consistency, dual_write_health)
    
    elapsed = (timezone.now() - start_time).total_seconds()
    
    return {
        'meta': {**meta, 'execution_time_seconds': round(elapsed, 2)},
        'coverage': coverage,
        'mapping_health': mapping_health,
        'consistency': consistency,
        'dual_write_health': dual_write_health,
        'recommendations': recommendations,
    }


def _collect_meta(sample_size: int, game_id: Optional[int], region: Optional[str]) -> Dict[str, Any]:
    """Collect metadata about report execution."""
    return {
        'generated_at': timezone.now().isoformat(),
        'sample_size': sample_size,
        'filters': {
            'game_id': game_id,
            'region': region,
        },
        'dual_write_enabled': getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False),
        'dual_write_strict_mode': getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE', False),
        'legacy_write_blocked': getattr(settings, 'TEAM_LEGACY_WRITE_BLOCKED', False),
    }


def _calculate_coverage(game_id: Optional[int], region: Optional[str]) -> Dict[str, Any]:
    """
    Calculate coverage metrics.
    
    Returns:
        - legacy_team_count: Total active legacy teams
        - vnext_team_count: Total vNext teams
        - mapped_team_count: Teams with mapping entries
        - unmapped_legacy_count: Legacy teams without vNext mapping
        - mapping_percentage: % of legacy teams mapped to vNext
    """
    # Build filters
    legacy_filters = Q(is_active=True)
    vnext_filters = Q(status='ACTIVE')
    
    if game_id:
        # Legacy uses game slug, vNext uses game_id
        game_slug_map = {1: 'valorant', 2: 'csgo', 3: 'dota2', 4: 'pubg'}
        game_slug = game_slug_map.get(game_id)
        if game_slug:
            legacy_filters &= Q(game=game_slug)
        vnext_filters &= Q(game_id=game_id)
    
    if region:
        legacy_filters &= Q(region=region)
        vnext_filters &= Q(region=region)
    
    # Count legacy teams
    legacy_team_count = LegacyTeam.objects.filter(legacy_filters).count()
    
    # Count vNext teams
    vnext_team_count = VNextTeam.objects.filter(vnext_filters).count()
    
    # Count mapped teams
    mapped_team_count = TeamMigrationMap.objects.count()
    
    # Count legacy teams with mapping
    legacy_teams_with_mapping = TeamMigrationMap.objects.filter(
        legacy_team_id__in=LegacyTeam.objects.filter(legacy_filters).values('id')
    ).count()
    
    # Unmapped legacy teams
    unmapped_legacy_count = legacy_team_count - legacy_teams_with_mapping
    
    # Calculate percentage
    mapping_percentage = (legacy_teams_with_mapping / legacy_team_count * 100) if legacy_team_count > 0 else 0
    
    return {
        'legacy_team_count': legacy_team_count,
        'vnext_team_count': vnext_team_count,
        'mapped_team_count': mapped_team_count,
        'legacy_teams_with_mapping': legacy_teams_with_mapping,
        'unmapped_legacy_count': unmapped_legacy_count,
        'mapping_percentage': round(mapping_percentage, 2),
    }


def _check_mapping_health() -> Dict[str, Any]:
    """
    Check TeamMigrationMap health.
    
    Returns:
        - duplicate_legacy_ids: List of legacy_team_id with multiple mappings
        - duplicate_vnext_ids: List of vnext_team_id with multiple mappings
        - orphan_mappings: Mappings pointing to missing teams
        - total_mappings: Total mapping count
    """
    # Check for duplicate legacy_team_id
    duplicate_legacy = (
        TeamMigrationMap.objects
        .values('legacy_team_id')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    duplicate_legacy_ids = [item['legacy_team_id'] for item in duplicate_legacy]
    
    # Check for duplicate vnext_team_id
    duplicate_vnext = (
        TeamMigrationMap.objects
        .values('vnext_team_id')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    duplicate_vnext_ids = [item['vnext_team_id'] for item in duplicate_vnext]
    
    # Check for orphan mappings (mapping points to missing team)
    orphan_mappings = []
    
    # Mappings with missing legacy team
    mappings_missing_legacy = TeamMigrationMap.objects.filter(
        ~Exists(LegacyTeam.objects.filter(id=OuterRef('legacy_team_id')))
    ).values_list('id', 'legacy_team_id', 'vnext_team_id')
    
    for mapping_id, legacy_id, vnext_id in mappings_missing_legacy:
        orphan_mappings.append({
            'mapping_id': mapping_id,
            'type': 'missing_legacy_team',
            'legacy_team_id': legacy_id,
            'vnext_team_id': vnext_id,
        })
    
    # Mappings with missing vNext team
    mappings_missing_vnext = TeamMigrationMap.objects.filter(
        ~Exists(VNextTeam.objects.filter(id=OuterRef('vnext_team_id')))
    ).values_list('id', 'legacy_team_id', 'vnext_team_id')
    
    for mapping_id, legacy_id, vnext_id in mappings_missing_vnext:
        orphan_mappings.append({
            'mapping_id': mapping_id,
            'type': 'missing_vnext_team',
            'legacy_team_id': legacy_id,
            'vnext_team_id': vnext_id,
        })
    
    total_mappings = TeamMigrationMap.objects.count()
    
    return {
        'total_mappings': total_mappings,
        'duplicate_legacy_ids': duplicate_legacy_ids,
        'duplicate_legacy_count': len(duplicate_legacy_ids),
        'duplicate_vnext_ids': duplicate_vnext_ids,
        'duplicate_vnext_count': len(duplicate_vnext_ids),
        'orphan_mappings': orphan_mappings,
        'orphan_count': len(orphan_mappings),
    }


def _check_consistency(
    sample_size: int,
    game_id: Optional[int],
    region: Optional[str]
) -> Dict[str, Any]:
    """
    Check data consistency between legacy and vNext for sampled mapped teams.
    
    Returns:
        - sampled_teams: Number of teams sampled
        - name_mismatches: Teams with different names
        - slug_mismatches: Teams with different slugs
        - membership_count_mismatches: Teams with different member counts
        - ranking_mismatches: Teams with inconsistent ranking presence
        - samples: List of mismatch examples
    """
    # Build filter for mapped teams
    mappings_query = TeamMigrationMap.objects.all()
    
    # Apply filters based on legacy/vNext team IDs if needed
    if game_id or region:
        legacy_ids = None
        vnext_ids = None
        
        if game_id:
            game_slug_map = {1: 'valorant', 2: 'csgo', 3: 'dota2', 4: 'pubg'}
            game_slug = game_slug_map.get(game_id)
            if game_slug:
                legacy_ids = set(LegacyTeam.objects.filter(game=game_slug, is_active=True).values_list('id', flat=True))
            vnext_ids = set(VNextTeam.objects.filter(game_id=game_id, status='ACTIVE').values_list('id', flat=True))
        
        if region:
            legacy_region_ids = set(LegacyTeam.objects.filter(region=region, is_active=True).values_list('id', flat=True))
            vnext_region_ids = set(VNextTeam.objects.filter(region=region, status='ACTIVE').values_list('id', flat=True))
            
            legacy_ids = legacy_region_ids if legacy_ids is None else legacy_ids & legacy_region_ids
            vnext_ids = vnext_region_ids if vnext_ids is None else vnext_ids & vnext_region_ids
        
        if legacy_ids is not None:
            mappings_query = mappings_query.filter(legacy_team_id__in=legacy_ids)
        if vnext_ids is not None:
            mappings_query = mappings_query.filter(vnext_team_id__in=vnext_ids)
    
    # Sample mappings
    sampled_mappings = list(mappings_query[:sample_size])
    
    name_mismatches = []
    slug_mismatches = []
    membership_count_mismatches = []
    ranking_mismatches = []
    
    for mapping in sampled_mappings:
        # Fetch teams manually since we use IntegerField IDs
        try:
            legacy = LegacyTeam.objects.get(id=mapping.legacy_team_id)
        except LegacyTeam.DoesNotExist:
            continue
        
        try:
            vnext = VNextTeam.objects.get(id=mapping.vnext_team_id)
        except VNextTeam.DoesNotExist:
            continue
        
        # Check name
        if legacy.name != vnext.name:
            name_mismatches.append({
                'mapping_id': mapping.id,
                'legacy_team_id': legacy.id,
                'vnext_team_id': vnext.id,
                'legacy_name': legacy.name,
                'vnext_name': vnext.name,
            })
        
        # Check slug
        if legacy.slug != vnext.slug:
            slug_mismatches.append({
                'mapping_id': mapping.id,
                'legacy_team_id': legacy.id,
                'vnext_team_id': vnext.id,
                'legacy_slug': legacy.slug,
                'vnext_slug': vnext.slug,
            })
        
        # Check membership counts (active only)
        legacy_member_count = LegacyMembership.objects.filter(
            team_id=legacy.id,
            status='ACTIVE'
        ).count()
        
        vnext_member_count = VNextMembership.objects.filter(
            team_id=vnext.id,
            status='ACTIVE'
        ).count()
        
        if legacy_member_count != vnext_member_count:
            membership_count_mismatches.append({
                'mapping_id': mapping.id,
                'legacy_team_id': legacy.id,
                'vnext_team_id': vnext.id,
                'legacy_count': legacy_member_count,
                'vnext_count': vnext_member_count,
                'difference': abs(legacy_member_count - vnext_member_count),
            })
        
        # Check ranking presence
        legacy_has_ranking = LegacyRanking.objects.filter(team_id=legacy.id).exists()
        vnext_has_ranking = VNextRanking.objects.filter(team_id=vnext.id).exists()
        
        if legacy_has_ranking != vnext_has_ranking:
            ranking_mismatches.append({
                'mapping_id': mapping.id,
                'legacy_team_id': legacy.id,
                'vnext_team_id': vnext.id,
                'legacy_has_ranking': legacy_has_ranking,
                'vnext_has_ranking': vnext_has_ranking,
            })
    
    # Limit samples to first 5 of each type
    samples = {
        'name_mismatches': name_mismatches[:5],
        'slug_mismatches': slug_mismatches[:5],
        'membership_count_mismatches': membership_count_mismatches[:5],
        'ranking_mismatches': ranking_mismatches[:5],
    }
    
    return {
        'sampled_teams': len(list(sampled_mappings)),
        'name_mismatch_count': len(name_mismatches),
        'slug_mismatch_count': len(slug_mismatches),
        'membership_count_mismatch_count': len(membership_count_mismatches),
        'ranking_mismatch_count': len(ranking_mismatches),
        'samples': samples,
    }


def _check_dual_write_health() -> Dict[str, Any]:
    """
    Check dual-write health (only when TEAM_VNEXT_DUAL_WRITE_ENABLED=True).
    
    For vNext teams created recently, verify corresponding legacy team exists + mapped.
    
    Returns:
        - recent_vnext_teams: Count of vNext teams created in last 24h
        - missing_legacy_count: vNext teams without legacy shadow row
        - missing_mappings: List of vNext teams without mapping
    """
    # Check recent vNext teams (last 24 hours)
    recent_cutoff = timezone.now() - timedelta(hours=24)
    recent_vnext_teams = VNextTeam.objects.filter(created_at__gte=recent_cutoff)
    recent_count = recent_vnext_teams.count()
    
    # Check which have mappings
    vnext_ids_with_mapping = set(
        TeamMigrationMap.objects.filter(
            vnext_team_id__in=recent_vnext_teams.values_list('id', flat=True)
        ).values_list('vnext_team_id', flat=True)
    )
    
    # Find missing mappings
    missing_mappings = []
    for team in recent_vnext_teams:
        if team.id not in vnext_ids_with_mapping:
            missing_mappings.append({
                'vnext_team_id': team.id,
                'vnext_team_name': team.name,
                'vnext_team_slug': team.slug,
                'created_at': team.created_at.isoformat(),
            })
    
    missing_legacy_count = len(missing_mappings)
    
    # Severity: ERROR if strict mode, WARNING otherwise
    strict_mode = getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE', False)
    severity = 'ERROR' if strict_mode else 'WARNING'
    
    return {
        'recent_vnext_teams': recent_count,
        'missing_legacy_count': missing_legacy_count,
        'missing_mappings': missing_mappings[:10],  # Limit to 10 samples
        'severity': severity,
    }


def _generate_recommendations(
    coverage: Dict[str, Any],
    mapping_health: Dict[str, Any],
    consistency: Dict[str, Any],
    dual_write_health: Optional[Dict[str, Any]]
) -> List[str]:
    """
    Generate human-readable recommendations based on report results.
    
    Returns:
        List of recommendation strings
    """
    recommendations = []
    
    # Coverage recommendations
    if coverage['mapping_percentage'] < 100:
        unmapped = coverage['unmapped_legacy_count']
        recommendations.append(
            f"ðŸ”´ CRITICAL: {unmapped} legacy teams unmapped ({100 - coverage['mapping_percentage']:.1f}% missing). "
            f"Run migration scripts to achieve 100% coverage before Phase 6."
        )
    elif coverage['mapping_percentage'] == 100:
        recommendations.append("âœ… Coverage: 100% of legacy teams are mapped to vNext.")
    
    # Mapping health recommendations
    if mapping_health['duplicate_legacy_count'] > 0:
        recommendations.append(
            f"ðŸ”´ CRITICAL: {mapping_health['duplicate_legacy_count']} duplicate legacy_team_id entries in TeamMigrationMap. "
            f"Clean up duplicates immediately."
        )
    
    if mapping_health['duplicate_vnext_count'] > 0:
        recommendations.append(
            f"ðŸ”´ CRITICAL: {mapping_health['duplicate_vnext_count']} duplicate vnext_team_id entries in TeamMigrationMap. "
            f"Clean up duplicates immediately."
        )
    
    if mapping_health['orphan_count'] > 0:
        recommendations.append(
            f"âš ï¸ WARNING: {mapping_health['orphan_count']} orphan mappings point to missing teams. "
            f"Investigate and clean up orphan records."
        )
    
    # Consistency recommendations
    if consistency['name_mismatch_count'] > 0:
        recommendations.append(
            f"âš ï¸ WARNING: {consistency['name_mismatch_count']} teams have name mismatches. "
            f"Review and sync team names."
        )
    
    if consistency['membership_count_mismatch_count'] > 0:
        recommendations.append(
            f"âš ï¸ WARNING: {consistency['membership_count_mismatch_count']} teams have membership count mismatches. "
            f"Re-run membership migration or check dual-write sync."
        )
    
    if consistency['ranking_mismatch_count'] > 0:
        recommendations.append(
            f"â„¹ï¸ INFO: {consistency['ranking_mismatch_count']} teams have ranking presence mismatches. "
            f"Verify ranking migration completed successfully."
        )
    
    # Dual-write health recommendations
    if dual_write_health and dual_write_health['missing_legacy_count'] > 0:
        severity_icon = "ðŸ”´ CRITICAL" if dual_write_health['severity'] == 'ERROR' else "âš ï¸ WARNING"
        recommendations.append(
            f"{severity_icon}: {dual_write_health['missing_legacy_count']} recent vNext teams missing legacy shadow rows. "
            f"Dual-write sync may be failing. Check logs and re-run sync."
        )
    
    # Overall readiness
    if not recommendations:
        recommendations.append("âœ… All validation checks passed. Migration data is healthy and ready for Phase 6.")
    
    return recommendations


# Singleton-like access
validation_report_service = type('ValidationReportService', (), {
    'generate_migration_validation_report': staticmethod(generate_migration_validation_report),
})()
