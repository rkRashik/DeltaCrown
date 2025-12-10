"""
Django management command to replay multiple events matching filters.

Usage:
    python manage.py replay_events --event-name=MatchCompletedEvent
    python manage.py replay_events --from-date=2025-12-01 --to-date=2025-12-10
    python manage.py replay_events --status=DEAD_LETTER --limit=50
    python manage.py replay_events --dry-run --event-name=MatchCompletedEvent

Phase 8, Epic 8.1
"""

from datetime import datetime

from django.core.management.base import BaseCommand

from apps.common.events.replay_service import EventReplayService


class Command(BaseCommand):
    help = "Replay multiple events from EventLog matching filters"

    def add_arguments(self, parser):
        parser.add_argument(
            "--event-name",
            type=str,
            help="Filter by event type (e.g., MatchCompletedEvent)",
        )
        parser.add_argument(
            "--from-date",
            type=str,
            help="Replay events from this date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--to-date",
            type=str,
            help="Replay events to this date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--correlation-id",
            type=str,
            help="Filter by correlation ID",
        )
        parser.add_argument(
            "--status",
            type=str,
            help="Filter by status (PENDING, PROCESSING, PROCESSED, FAILED, DEAD_LETTER)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of events to replay (default 100)",
        )
        parser.add_argument(
            "--no-reset-status",
            action="store_true",
            help="Don't reset event status before replay (default: reset DEAD_LETTER/FAILED to PENDING)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview events that would be replayed without executing",
        )

    def handle(self, *args, **options):
        service = EventReplayService()

        # Parse date arguments
        from_date = None
        to_date = None
        if options["from_date"]:
            from_date = datetime.strptime(options["from_date"], "%Y-%m-%d")
        if options["to_date"]:
            to_date = datetime.strptime(options["to_date"], "%Y-%m-%d")

        reset_status = not options["no_reset_status"]

        # Dry-run mode: just preview
        if options["dry_run"]:
            events = service.replay_events_dry_run(
                event_name=options["event_name"],
                from_date=from_date,
                to_date=to_date,
                correlation_id=options["correlation_id"],
                status=options["status"],
                limit=options["limit"],
            )

            count = events.count()
            self.stdout.write(
                self.style.WARNING(f"\n[DRY RUN] Would replay {count} event(s):\n")
            )

            if count == 0:
                self.stdout.write("  (none)\n")
                return

            for event in events[:20]:  # Show first 20
                self.stdout.write(
                    f"  - {event.id}: {event.name} at {event.occurred_at} (status: {event.status})"
                )

            if count > 20:
                self.stdout.write(f"\n  ... and {count - 20} more events\n")

            self.stdout.write(
                self.style.SUCCESS(
                    f"\nTo replay these events, run the command without --dry-run\n"
                )
            )
            return

        # Actually replay events
        self.stdout.write(f"\nReplaying events...")
        self.stdout.write(f"  Event Name: {options['event_name'] or 'all'}")
        self.stdout.write(f"  From Date: {options['from_date'] or 'any'}")
        self.stdout.write(f"  To Date: {options['to_date'] or 'any'}")
        self.stdout.write(f"  Status: {options['status'] or 'any'}")
        self.stdout.write(f"  Limit: {options['limit']}")
        self.stdout.write(f"  Reset status: {reset_status}\n")

        replayed_count = service.replay_events(
            event_name=options["event_name"],
            from_date=from_date,
            to_date=to_date,
            correlation_id=options["correlation_id"],
            status=options["status"],
            reset_status=reset_status,
            limit=options["limit"],
        )

        self.stdout.write(
            self.style.SUCCESS(f"\n✓ Successfully replayed {replayed_count} event(s)\n")
        )
        self.stdout.write(
            "  Events have been republished via EventBus with is_replay=True metadata.\n"
        )
        self.stdout.write(
            "  Check EventLog for updated processing status.\n"
        )
