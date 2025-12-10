"""
Django management command to list dead-letter events.

Usage:
    python manage.py list_dead_letter_events
    python manage.py list_dead_letter_events --event-name=MatchCompletedEvent
    python manage.py list_dead_letter_events --from-date=2025-12-01 --to-date=2025-12-10
    python manage.py list_dead_letter_events --limit=50

Phase 8, Epic 8.1
"""

from datetime import datetime

from django.core.management.base import BaseCommand

from apps.common.events.dead_letter_service import DeadLetterService


class Command(BaseCommand):
    help = "List events in the Dead Letter Queue (failed after max retries)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--event-name",
            type=str,
            help="Filter by event type (e.g., MatchCompletedEvent)",
        )
        parser.add_argument(
            "--from-date",
            type=str,
            help="Filter events from this date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--to-date",
            type=str,
            help="Filter events to this date (YYYY-MM-DD)",
        )
        parser.add_argument(
            "--min-retry-count",
            type=int,
            help="Filter events with retry_count >= this value",
        )
        parser.add_argument(
            "--correlation-id",
            type=str,
            help="Filter by correlation ID",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of results (default 100)",
        )

    def handle(self, *args, **options):
        service = DeadLetterService()

        # Parse date arguments
        from_date = None
        to_date = None
        if options["from_date"]:
            from_date = datetime.strptime(options["from_date"], "%Y-%m-%d")
        if options["to_date"]:
            to_date = datetime.strptime(options["to_date"], "%Y-%m-%d")

        # Query dead-letter events
        events = service.list_dead_letter_events(
            event_name=options["event_name"],
            from_date=from_date,
            to_date=to_date,
            min_retry_count=options["min_retry_count"],
            correlation_id=options["correlation_id"],
            limit=options["limit"],
        )

        # Display results
        count = events.count()
        self.stdout.write(
            self.style.SUCCESS(f"\nFound {count} dead-letter event(s):\n")
        )

        if count == 0:
            self.stdout.write("  (none)\n")
            return

        for event in events:
            self.stdout.write(f"\n  ID: {event.id}")
            self.stdout.write(f"  Name: {event.name}")
            self.stdout.write(f"  Occurred: {event.occurred_at}")
            self.stdout.write(f"  Retry Count: {event.retry_count}")
            self.stdout.write(f"  Last Error: {event.last_error[:200] if event.last_error else 'N/A'}")
            self.stdout.write(f"  Last Error At: {event.last_error_at or 'N/A'}")
            if event.correlation_id:
                self.stdout.write(f"  Correlation ID: {event.correlation_id}")
            self.stdout.write("")

        self.stdout.write(
            self.style.WARNING(
                f"\nTo replay an event: python manage.py replay_event --id=<ID>"
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f"To acknowledge an event: Use Django admin or DeadLetterService"
            )
        )
