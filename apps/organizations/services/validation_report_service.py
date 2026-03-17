"""
Data Validation Report Service (post-migration).

Provides validation/report tooling for organizations.Team data health.
Legacy teams app has been fully removed (TASK-015). This service now
validates only vNext (organizations) data and TeamMigrationMap integrity.

Usage:
    from apps.organizations.services.validation_report_service import generate_migration_validation_report

    report = generate_migration_validation_report()
    print(f"Team count: {report['coverage']['team_count']}")
"""

import logging
from typing import Dict, Any, List, Optional
from django.db.models import Count, Exists, OuterRef
from django.utils import timezone

from apps.organizations.models import (
    Team,
    TeamMembership,
    TeamMigrationMap,
)

logger = logging.getLogger(__name__)


def generate_migration_validation_report(
    *,
    sample_size: int = 50,
    game_id: Optional[int] = None,
    region: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate validation report for team data health.

    Returns JSON-serializable dict with coverage, mapping health,
    and recommendations.
    """
    start_time = timezone.now()

    coverage = _calculate_coverage(game_id, region)
    mapping_health = _check_mapping_health()
    recommendations = _generate_recommendations(coverage, mapping_health)

    elapsed = (timezone.now() - start_time).total_seconds()

    return {
        'meta': {
            'generated_at': timezone.now().isoformat(),
            'sample_size': sample_size,
            'filters': {'game_id': game_id, 'region': region},
            'execution_time_seconds': round(elapsed, 2),
        },
        'coverage': coverage,
        'mapping_health': mapping_health,
        'recommendations': recommendations,
    }


def _calculate_coverage(game_id: Optional[int], region: Optional[str]) -> Dict[str, Any]:
    """Calculate team coverage metrics."""
    from django.db.models import Q

    filters = Q(status='ACTIVE')
    if game_id:
        filters &= Q(game_id=game_id)
    if region:
        filters &= Q(region=region)

    team_count = Team.objects.filter(filters).count()
    mapped_count = TeamMigrationMap.objects.count()

    return {
        'team_count': team_count,
        'mapped_count': mapped_count,
    }


def _check_mapping_health() -> Dict[str, Any]:
    """Check TeamMigrationMap health."""
    duplicate_vnext = (
        TeamMigrationMap.objects
        .values('vnext_team_id')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )
    duplicate_vnext_ids = [item['vnext_team_id'] for item in duplicate_vnext]

    orphan_mappings = list(
        TeamMigrationMap.objects.filter(
            ~Exists(Team.objects.filter(id=OuterRef('vnext_team_id')))
        ).values_list('id', 'legacy_team_id', 'vnext_team_id')[:10]
    )

    total_mappings = TeamMigrationMap.objects.count()

    return {
        'total_mappings': total_mappings,
        'duplicate_vnext_ids': duplicate_vnext_ids,
        'duplicate_vnext_count': len(duplicate_vnext_ids),
        'orphan_count': len(orphan_mappings),
        'orphan_mappings': [
            {'mapping_id': m[0], 'legacy_team_id': m[1], 'vnext_team_id': m[2]}
            for m in orphan_mappings
        ],
    }


def _generate_recommendations(
    coverage: Dict[str, Any],
    mapping_health: Dict[str, Any],
) -> List[str]:
    """Generate human-readable recommendations."""
    recommendations = []

    if mapping_health['duplicate_vnext_count'] > 0:
        recommendations.append(
            f"CRITICAL: {mapping_health['duplicate_vnext_count']} duplicate vnext_team_id entries "
            f"in TeamMigrationMap. Clean up duplicates."
        )

    if mapping_health['orphan_count'] > 0:
        recommendations.append(
            f"WARNING: {mapping_health['orphan_count']} orphan mappings point to missing teams. "
            f"Investigate and clean up."
        )

    if not recommendations:
        recommendations.append("All validation checks passed. Team data is healthy.")

    return recommendations


# Singleton-like access
validation_report_service = type('ValidationReportService', (), {
    'generate_migration_validation_report': staticmethod(generate_migration_validation_report),
})()
