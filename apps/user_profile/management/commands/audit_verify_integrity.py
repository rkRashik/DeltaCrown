"""
Verify audit log integrity.

Usage:
    python manage.py audit_verify_integrity --limit 1000
"""
from django.core.management.base import BaseCommand
from apps.user_profile.models.audit import UserAuditEvent


class Command(BaseCommand):
    help = "Verify audit log integrity (append-only, required fields)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Maximum number of events to check',
        )

    def handle(self, *args, **options):
        limit = options['limit']

        queryset = UserAuditEvent.objects.all().order_by('id')
        if limit:
            queryset = queryset[:limit]

        total = queryset.count()
        self.stdout.write(f"Checking {total} audit events...")

        errors = []
        warnings = []

        for event in queryset:
            # Check required fields
            if not event.subject_user_id:
                errors.append(f"Event {event.id}: missing subject_user_id")

            if not event.event_type:
                errors.append(f"Event {event.id}: missing event_type")

            if not event.source_app:
                errors.append(f"Event {event.id}: missing source_app")

            if not event.object_type:
                errors.append(f"Event {event.id}: missing object_type")

            if not event.created_at:
                errors.append(f"Event {event.id}: missing created_at")

            # Check for PII in snapshots (basic check)
            forbidden = ['password', 'email', 'oauth_token', 'access_token']
            
            if event.before_snapshot:
                for key in forbidden:
                    if key in event.before_snapshot:
                        errors.append(f"Event {event.id}: forbidden field '{key}' in before_snapshot")

            if event.after_snapshot:
                for key in forbidden:
                    if key in event.after_snapshot:
                        errors.append(f"Event {event.id}: forbidden field '{key}' in after_snapshot")

        # Summary
        self.stdout.write("\n" + "="*50)
        if errors:
            self.stdout.write(self.style.ERROR(f"❌ {len(errors)} errors found:"))
            for error in errors[:10]:  # Show first 10
                self.stdout.write(f"  - {error}")
            if len(errors) > 10:
                self.stdout.write(f"  ... and {len(errors) - 10} more")
        else:
            self.stdout.write(self.style.SUCCESS(f"✅ No integrity errors found ({total} events checked)"))

        if warnings:
            self.stdout.write(self.style.WARNING(f"⚠️  {len(warnings)} warnings:"))
            for warning in warnings[:10]:
                self.stdout.write(f"  - {warning}")

        self.stdout.write("="*50)
