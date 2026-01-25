"""
Management command to generate migration validation reports (P5-T4).

Usage:
    python manage.py vnext_validation_report
    python manage.py vnext_validation_report --format=json --output=report.json
    python manage.py vnext_validation_report --sample-size=100 --game-id=1
    python manage.py vnext_validation_report --fail-on-errors
"""

import json
import sys
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.organizations.services.validation_report_service import generate_migration_validation_report


class Command(BaseCommand):
    help = 'Generate migration validation report for Team & Organization vNext'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--format',
            type=str,
            choices=['text', 'json'],
            default='text',
            help='Output format (text or json)',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (optional, prints to stdout if not provided)',
        )
        parser.add_argument(
            '--sample-size',
            type=int,
            default=50,
            help='Number of teams to sample for consistency checks (default: 50)',
        )
        parser.add_argument(
            '--game-id',
            type=int,
            help='Filter by game_id (optional)',
        )
        parser.add_argument(
            '--region',
            type=str,
            help='Filter by region (optional)',
        )
        parser.add_argument(
            '--fail-on-errors',
            action='store_true',
            help='Exit with code 1 if errors detected',
        )
    
    def handle(self, *args, **options):
        format_type = options['format']
        output_file = options['output']
        sample_size = options['sample_size']
        game_id = options['game_id']
        region = options['region']
        fail_on_errors = options['fail_on_errors']
        
        self.stdout.write(self.style.SUCCESS('Generating migration validation report...'))
        
        # Generate report
        report = generate_migration_validation_report(
            sample_size=sample_size,
            game_id=game_id,
            region=region
        )
        
        # Format output
        if format_type == 'json':
            output = self._format_json(report)
        else:
            output = self._format_text(report)
        
        # Write output
        if output_file:
            with open(output_file, 'w') as f:
                f.write(output)
            self.stdout.write(self.style.SUCCESS(f'Report written to: {output_file}'))
        else:
            self.stdout.write(output)
        
        # Check for errors and fail if requested
        if fail_on_errors:
            has_errors = self._check_for_errors(report)
            if has_errors:
                self.stdout.write(self.style.ERROR('\n❌ Validation errors detected. Exiting with code 1.'))
                sys.exit(1)
        
        self.stdout.write(self.style.SUCCESS('\n✅ Report generation complete.'))
    
    def _format_json(self, report):
        """Format report as JSON."""
        return json.dumps(report, indent=2)
    
    def _format_text(self, report):
        """Format report as human-readable text."""
        lines = []
        
        # Header
        lines.append('=' * 80)
        lines.append('MIGRATION VALIDATION REPORT')
        lines.append('=' * 80)
        lines.append('')
        
        # Meta
        meta = report['meta']
        lines.append(f"Generated: {meta['generated_at']}")
        lines.append(f"Execution Time: {meta['execution_time_seconds']}s")
        lines.append(f"Sample Size: {meta['sample_size']}")
        lines.append('')
        
        # Filters
        if meta['filters']['game_id'] or meta['filters']['region']:
            lines.append('Filters:')
            if meta['filters']['game_id']:
                lines.append(f"  Game ID: {meta['filters']['game_id']}")
            if meta['filters']['region']:
                lines.append(f"  Region: {meta['filters']['region']}")
            lines.append('')
        
        # Environment
        lines.append('Environment Flags:')
        lines.append(f"  Dual-Write Enabled: {meta['dual_write_enabled']}")
        lines.append(f"  Dual-Write Strict Mode: {meta['dual_write_strict_mode']}")
        lines.append(f"  Legacy Write Blocked: {meta['legacy_write_blocked']}")
        lines.append('')
        
        # Coverage
        lines.append('-' * 80)
        lines.append('COVERAGE METRICS')
        lines.append('-' * 80)
        coverage = report['coverage']
        lines.append(f"Legacy Teams (Active):     {coverage['legacy_team_count']:,}")
        lines.append(f"vNext Teams:               {coverage['vnext_team_count']:,}")
        lines.append(f"Mapped Teams:              {coverage['mapped_team_count']:,}")
        lines.append(f"Legacy Teams with Mapping: {coverage['legacy_teams_with_mapping']:,}")
        lines.append(f"Unmapped Legacy Teams:     {coverage['unmapped_legacy_count']:,}")
        lines.append(f"Mapping Coverage:          {coverage['mapping_percentage']:.2f}%")
        lines.append('')
        
        # Mapping Health
        lines.append('-' * 80)
        lines.append('MAPPING HEALTH')
        lines.append('-' * 80)
        mapping = report['mapping_health']
        lines.append(f"Total Mappings:            {mapping['total_mappings']:,}")
        lines.append(f"Duplicate Legacy IDs:      {mapping['duplicate_legacy_count']}")
        lines.append(f"Duplicate vNext IDs:       {mapping['duplicate_vnext_count']}")
        lines.append(f"Orphan Mappings:           {mapping['orphan_count']}")
        
        if mapping['duplicate_legacy_ids']:
            lines.append(f"  Duplicate Legacy IDs: {mapping['duplicate_legacy_ids'][:5]}")
        if mapping['duplicate_vnext_ids']:
            lines.append(f"  Duplicate vNext IDs: {mapping['duplicate_vnext_ids'][:5]}")
        if mapping['orphan_mappings']:
            lines.append('  Orphan Samples:')
            for orphan in mapping['orphan_mappings'][:3]:
                lines.append(f"    - Mapping ID {orphan['mapping_id']}: {orphan['type']}")
        lines.append('')
        
        # Consistency
        lines.append('-' * 80)
        lines.append('CONSISTENCY CHECKS')
        lines.append('-' * 80)
        consistency = report['consistency']
        lines.append(f"Sampled Teams:             {consistency['sampled_teams']}")
        lines.append(f"Name Mismatches:           {consistency['name_mismatch_count']}")
        lines.append(f"Slug Mismatches:           {consistency['slug_mismatch_count']}")
        lines.append(f"Membership Count Mismatches: {consistency['membership_count_mismatch_count']}")
        lines.append(f"Ranking Mismatches:        {consistency['ranking_mismatch_count']}")
        
        # Show samples if any
        samples = consistency['samples']
        if samples['name_mismatches']:
            lines.append('\n  Name Mismatch Samples:')
            for item in samples['name_mismatches'][:3]:
                lines.append(f"    - Legacy: '{item['legacy_name']}' vs vNext: '{item['vnext_name']}'")
        
        if samples['membership_count_mismatches']:
            lines.append('\n  Membership Count Mismatch Samples:')
            for item in samples['membership_count_mismatches'][:3]:
                lines.append(f"    - Team {item['vnext_team_id']}: Legacy={item['legacy_count']}, vNext={item['vnext_count']}")
        
        lines.append('')
        
        # Dual-Write Health
        if report['dual_write_health']:
            lines.append('-' * 80)
            lines.append('DUAL-WRITE HEALTH')
            lines.append('-' * 80)
            dwh = report['dual_write_health']
            lines.append(f"Recent vNext Teams (24h):  {dwh['recent_vnext_teams']}")
            lines.append(f"Missing Legacy Shadow:     {dwh['missing_legacy_count']}")
            lines.append(f"Severity:                  {dwh['severity']}")
            
            if dwh['missing_mappings']:
                lines.append('\n  Missing Mappings Samples:')
                for item in dwh['missing_mappings'][:5]:
                    lines.append(f"    - vNext Team {item['vnext_team_id']}: '{item['vnext_team_name']}' (created {item['created_at']})")
            lines.append('')
        
        # Recommendations
        lines.append('-' * 80)
        lines.append('RECOMMENDATIONS')
        lines.append('-' * 80)
        for rec in report['recommendations']:
            lines.append(f"  {rec}")
        lines.append('')
        
        lines.append('=' * 80)
        
        return '\n'.join(lines)
    
    def _check_for_errors(self, report):
        """Check if report contains any errors."""
        has_errors = False
        
        # Coverage errors
        if report['coverage']['mapping_percentage'] < 100:
            has_errors = True
        
        # Mapping health errors
        mapping = report['mapping_health']
        if mapping['duplicate_legacy_count'] > 0 or mapping['duplicate_vnext_count'] > 0:
            has_errors = True
        
        # Dual-write errors (only in strict mode)
        if report['dual_write_health']:
            dwh = report['dual_write_health']
            if dwh['severity'] == 'ERROR' and dwh['missing_legacy_count'] > 0:
                has_errors = True
        
        return has_errors
