"""
Management command to clean up ghost teams created by failed creation attempts.

A "ghost team" is defined as:
- Team exists in database
- Missing required membership OR event ledger entry
- Created recently (last 7 days by default)
- Status is ACTIVE (not intentionally disbanded)

This happens when team creation crashes after Team.objects.create() but before
membership/event creation completes.

Usage:
    python manage.py cleanup_ghost_teams --dry-run  # Preview what would be deleted
    python manage.py cleanup_ghost_teams            # Actually delete ghost teams
    python manage.py cleanup_ghost_teams --days=14  # Check last 14 days
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Clean up ghost teams (teams without proper memberships/events)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Check teams created in the last N days (default: 7)',
        )

    def handle(self, *args, **options):
        from apps.organizations.models import Team, TeamMembership, TeamMembershipEvent
        from apps.organizations.choices import MembershipRole
        
        dry_run = options['dry_run']
        days = options['days']
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(
            self.style.WARNING(
                f"\n{'=' * 70}\n"
                f"Ghost Team Cleanup Utility\n"
                f"{'=' * 70}\n"
            )
        )
        
        self.stdout.write(
            f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will delete)'}\n"
            f"Checking teams created since: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        
        # Find independent teams without proper owner/manager membership
        ghost_teams = []
        
        teams = Team.objects.filter(
            created_at__gte=cutoff_date,
            organization__isnull=True,  # Independent teams only
            status='ACTIVE'
        ).order_by('created_at')
        
        self.stdout.write(f"\nScanning {teams.count()} independent teams...\n")
        
        for team in teams:
            # Check for ACTIVE owner/manager membership
            has_owner = TeamMembership.objects.filter(
                team=team,
                role__in=[MembershipRole.OWNER, MembershipRole.MANAGER],
                status='ACTIVE'
            ).exists()
            
            # Check for JOINED event in ledger
            has_join_event = TeamMembershipEvent.objects.filter(
                team=team,
                event_type='JOINED'
            ).exists()
            
            # A team is a ghost if it lacks BOTH owner membership AND join event
            if not has_owner or not has_join_event:
                ghost_teams.append({
                    'team': team,
                    'has_owner': has_owner,
                    'has_join_event': has_join_event,
                    'membership_count': TeamMembership.objects.filter(team=team).count(),
                    'event_count': TeamMembershipEvent.objects.filter(team=team).count(),
                })
        
        if not ghost_teams:
            self.stdout.write(self.style.SUCCESS("\n✅ No ghost teams found!\n"))
            return
        
        # Display findings
        self.stdout.write(
            self.style.WARNING(
                f"\n⚠️  Found {len(ghost_teams)} ghost team(s):\n"
                f"{'-' * 70}\n"
            )
        )
        
        for idx, item in enumerate(ghost_teams, 1):
            team = item['team']
            self.stdout.write(
                f"\n{idx}. Team: {team.name} (ID: {team.id}, Slug: {team.slug})\n"
                f"   Created: {team.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"   Created By: {team.created_by.username} (ID: {team.created_by.id})\n"
                f"   Game: {team.game.name} (ID: {team.game_id})\n"
                f"   Has Active Owner: {'✅' if item['has_owner'] else '❌'}\n"
                f"   Has Join Event: {'✅' if item['has_join_event'] else '❌'}\n"
                f"   Membership Count: {item['membership_count']}\n"
                f"   Event Count: {item['event_count']}\n"
            )
        
        # Confirm deletion
        if not dry_run:
            self.stdout.write(
                self.style.ERROR(
                    f"\n{'=' * 70}\n"
                    f"⚠️  WARNING: About to DELETE {len(ghost_teams)} team(s)\n"
                    f"{'=' * 70}\n"
                )
            )
            
            confirm = input("Type 'DELETE' to confirm deletion (or anything else to cancel): ")
            
            if confirm != 'DELETE':
                self.stdout.write(self.style.SUCCESS("\n✋ Deletion cancelled.\n"))
                return
            
            # Delete ghost teams
            self.stdout.write("\n🗑️  Deleting ghost teams...\n")
            
            deleted_count = 0
            for item in ghost_teams:
                team = item['team']
                try:
                    with transaction.atomic():
                        # Delete related objects first
                        TeamMembership.objects.filter(team=team).delete()
                        TeamMembershipEvent.objects.filter(team=team).delete()
                        
                        # Delete the team
                        team_id = team.id
                        team_name = team.name
                        team.delete()
                        
                        deleted_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"   ✅ Deleted: {team_name} (ID: {team_id})"
                            )
                        )
                        
                        logger.info(
                            f"Ghost team deleted: {team_name} (ID: {team_id})",
                            extra={
                                'event_type': 'ghost_team_deleted',
                                'team_id': team_id,
                                'team_name': team_name,
                                'reason': 'cleanup_command',
                            }
                        )
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f"   ❌ Failed to delete {team.name} (ID: {team.id}): {e}"
                        )
                    )
                    logger.exception(
                        f"Failed to delete ghost team {team.id}",
                        extra={
                            'event_type': 'ghost_team_deletion_failed',
                            'team_id': team.id,
                            'error': str(e),
                        }
                    )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{'=' * 70}\n"
                    f"✅ Successfully deleted {deleted_count} ghost team(s)\n"
                    f"{'=' * 70}\n"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"\n{'=' * 70}\n"
                    f"DRY RUN complete. Run without --dry-run to delete these teams.\n"
                    f"{'=' * 70}\n"
                )
            )
