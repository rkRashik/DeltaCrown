"""
Export audit events for compliance/analysis.

Usage:
    python manage.py audit_export --user-id 42
    python manage.py audit_export --since 2025-12-01 --limit 1000
    python manage.py audit_export --event-type public_id_assigned --output audit.jsonl
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
import json
import sys

from apps.user_profile.models.audit import UserAuditEvent


class Command(BaseCommand):
    help = "Export audit events as JSONL"

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='Filter by subject user ID',
        )
        parser.add_argument(
            '--event-type',
            type=str,
            help='Filter by event type',
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Filter events since date (YYYY-MM-DD)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum number of events to export',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Output file path (default: stdout)',
        )

    def handle(self, *args, **options):
        user_id = options['user_id']
        event_type = options['event_type']
        since = options['since']
        limit = options['limit']
        output_path = options['output']

        # Build query
        queryset = UserAuditEvent.objects.select_related('actor_user', 'subject_user').all()

        if user_id:
            queryset = queryset.filter(subject_user_id=user_id)

        if event_type:
            queryset = queryset.filter(event_type=event_type)

        if since:
            try:
                since_date = datetime.strptime(since, '%Y-%m-%d')
                queryset = queryset.filter(created_at__gte=since_date)
            except ValueError:
                self.stdout.write(self.style.ERROR(f"Invalid date format: {since}. Use YYYY-MM-DD"))
                return

        queryset = queryset.order_by('-created_at')[:limit]

        # Open output
        if output_path:
            output = open(output_path, 'w')
        else:
            output = sys.stdout

        # Export as JSONL
        count = 0
        for event in queryset:
            record = {
                'id': event.id,
                'subject_user': event.subject_user.username,
                'actor_user': event.actor_user.username if event.actor_user else 'SYSTEM',
                'event_type': event.event_type,
                'source_app': event.source_app,
                'object_type': event.object_type,
                'object_id': event.object_id,
                'before_snapshot': event.before_snapshot,
                'after_snapshot': event.after_snapshot,
                'metadata': event.metadata,
                'created_at': event.created_at.isoformat(),
            }
            output.write(json.dumps(record) + '\n')
            count += 1

        if output_path:
            output.close()
            self.stdout.write(self.style.SUCCESS(f"✅ Exported {count} audit events to {output_path}"))
        else:
            self.stderr.write(f"✅ Exported {count} audit events\n")
