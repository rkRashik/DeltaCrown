"""
Django management command to replay a single event by ID.

Usage:
    python manage.py replay_event --id=123
    python manage.py replay_event --id=123 --no-reset-status

Phase 8, Epic 8.1
"""

from django.core.management.base import BaseCommand, CommandError

from apps.common.events.replay_service import EventReplayService


class Command(BaseCommand):
    help = "Replay a single event from EventLog by ID"

    def add_arguments(self, parser):
        parser.add_argument(
            "--id",
            type=int,
            required=True,
            help="EventLog ID to replay",
        )
        parser.add_argument(
            "--no-reset-status",
            action="store_true",
            help="Don't reset event status before replay (default: reset DEAD_LETTER/FAILED to PENDING)",
        )

    def handle(self, *args, **options):
        service = EventReplayService()
        event_log_id = options["id"]
        reset_status = not options["no_reset_status"]

        self.stdout.write(f"\nReplaying event {event_log_id}...")
        self.stdout.write(f"Reset status: {reset_status}\n")

        success = service.replay_event(
            event_log_id=event_log_id,
            reset_status=reset_status,
        )

        if success:
            self.stdout.write(
                self.style.SUCCESS(f"\n✓ Successfully replayed event {event_log_id}\n")
            )
            self.stdout.write(
                "  Event has been republished via EventBus with is_replay=True metadata.\n"
            )
            self.stdout.write(
                "  Check EventLog for new processing status.\n"
            )
        else:
            raise CommandError(
                f"Failed to replay event {event_log_id}. Event may not exist or replay failed. Check logs for details."
            )
