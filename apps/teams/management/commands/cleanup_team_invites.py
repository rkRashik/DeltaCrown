"""
Management command to clean up expired team invitations.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.teams.models import TeamInvite
from apps.teams.management import TeamManagementService


class Command(BaseCommand):
    help = "Clean up expired team invitations"

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days after which invitations expire (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        expired_invites = TeamInvite.objects.filter(
            status="PENDING",
            created_at__lt=cutoff_date
        )
        
        count = expired_invites.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would expire {count} invitations older than {days} days"
                )
            )
            
            for invite in expired_invites[:10]:  # Show first 10 as examples
                self.stdout.write(
                    f"  - {invite.team.name}: {invite.invited_user.display_name} "
                    f"(created {invite.created_at})"
                )
            
            if count > 10:
                self.stdout.write(f"  ... and {count - 10} more")
                
        else:
            expired_count = TeamManagementService.cleanup_expired_invites()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully expired {expired_count} old invitations"
                )
            )