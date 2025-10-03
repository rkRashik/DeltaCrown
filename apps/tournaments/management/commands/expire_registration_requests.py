# apps/tournaments/management/commands/expire_registration_requests.py
"""
Management command to expire old registration requests
Run this as a cron job: 0 * * * * (every hour)
"""
from django.core.management.base import BaseCommand
from django.apps import apps
from django.utils import timezone


class Command(BaseCommand):
    help = 'Mark expired registration requests as EXPIRED'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be expired without actually changing data',
        )

    def handle(self, *args, **options):
        try:
            from apps.tournaments.services.approval_service import ApprovalService
        except ImportError:
            self.stdout.write(
                self.style.ERROR('Could not import ApprovalService')
            )
            return

        dry_run = options.get('dry_run', False)
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )

        try:
            RegistrationRequest = apps.get_model("tournaments", "RegistrationRequest")
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Could not load RegistrationRequest model: {e}')
            )
            return

        now = timezone.now()
        
        # Find expired requests
        expired_requests = RegistrationRequest.objects.filter(
            status="PENDING",
            expires_at__lt=now
        ).select_related('requester', 'tournament', 'captain')

        count = expired_requests.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No expired requests found')
            )
            return

        self.stdout.write(
            self.style.WARNING(f'Found {count} expired request(s)')
        )

        # Process each request
        expired_count = 0
        for request in expired_requests:
            requester_name = getattr(request.requester, 'display_name', 'Unknown')
            tournament_name = getattr(request.tournament, 'name', 'Unknown')
            
            self.stdout.write(
                f'  - {requester_name} → {tournament_name} '
                f'(expired {(now - request.expires_at).days} days ago)'
            )
            
            if not dry_run:
                try:
                    if request.mark_expired():
                        expired_count += 1
                        
                        # Send notification
                        try:
                            from apps.notifications.services import NotificationService
                            NotificationService.send(
                                recipient=request.requester,
                                event="APPROVAL_REQUEST_EXPIRED",
                                title="Request Expired",
                                message=f"Your registration request for {tournament_name} has expired.",
                                action_url=f"/tournaments/{request.tournament.slug}/",
                                priority="LOW"
                            )
                        except Exception as e:
                            self.stdout.write(
                                self.style.WARNING(f'    Failed to send notification: {e}')
                            )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'    Failed to expire: {e}')
                    )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'Would have expired {count} request(s)')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully expired {expired_count} request(s)')
            )

