"""
Management command to generate team statistics and reports.
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Q

from apps.teams.models import Team, TeamMembership, TeamInvite
from apps.teams.management import TeamAnalytics


class Command(BaseCommand):
    help = "Generate team statistics and reports"

    def add_arguments(self, parser):
        parser.add_argument(
            '--team-slug',
            type=str,
            help='Generate report for specific team'
        )
        parser.add_argument(
            '--format',
            choices=['table', 'json', 'csv'],
            default='table',
            help='Output format'
        )

    def handle(self, *args, **options):
        team_slug = options.get('team_slug')
        format_type = options['format']
        
        if team_slug:
            try:
                team = Team.objects.get(slug=team_slug)
                self.generate_team_report(team, format_type)
            except Team.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"Team with slug '{team_slug}' not found")
                )
        else:
            self.generate_overall_report(format_type)

    def generate_team_report(self, team, format_type):
        """Generate report for a specific team."""
        analytics = TeamAnalytics(team)
        
        member_stats = analytics.get_member_statistics()
        invite_stats = analytics.get_invitation_statistics()
        
        if format_type == 'table':
            self.stdout.write(f"\n=== Team Report: {team.name} ===")
            self.stdout.write(f"Tag: {team.tag}")
            self.stdout.write(f"Game: {team.get_game_display() if team.game else 'Not set'}")
            self.stdout.write(f"Created: {team.created_at}")
            self.stdout.write(f"Captain: {team.captain.display_name}")
            
            self.stdout.write("\n--- Member Statistics ---")
            self.stdout.write(f"Total Members: {member_stats['total_members']}")
            self.stdout.write(f"Active Members (30 days): {member_stats['active_members']}")
            
            if member_stats['newest_member']:
                self.stdout.write(
                    f"Newest Member: {member_stats['newest_member'].user.display_name} "
                    f"(joined {member_stats['newest_member'].joined_at})"
                )
            
            self.stdout.write("\n--- Invitation Statistics ---")
            self.stdout.write(f"Total Sent: {invite_stats['total_sent']}")
            self.stdout.write(f"Pending: {invite_stats['pending']}")
            self.stdout.write(f"Accepted: {invite_stats['accepted']}")
            self.stdout.write(f"Declined: {invite_stats['declined']}")
            self.stdout.write(f"Acceptance Rate: {invite_stats['acceptance_rate']:.1f}%")
            
        elif format_type == 'json':
            import json
            report_data = {
                'team': {
                    'name': team.name,
                    'tag': team.tag,
                    'game': team.game,
                    'created_at': team.created_at.isoformat(),
                    'captain': team.captain.display_name,
                },
                'members': member_stats,
                'invitations': invite_stats,
            }
            self.stdout.write(json.dumps(report_data, indent=2, default=str))

    def generate_overall_report(self, format_type):
        """Generate overall statistics report."""
        total_teams = Team.objects.count()
        active_teams = Team.objects.filter(
            memberships__status="ACTIVE"
        ).distinct().count()
        
        recruiting_teams = Team.objects.filter(is_recruiting=True).count()
        open_teams = Team.objects.filter(is_open=True).count()
        
        total_memberships = TeamMembership.objects.filter(status="ACTIVE").count()
        total_invites = TeamInvite.objects.count()
        pending_invites = TeamInvite.objects.filter(status="PENDING").count()
        
        if format_type == 'table':
            self.stdout.write("\n=== DeltaCrown Team Statistics ===")
            self.stdout.write(f"Total Teams: {total_teams}")
            self.stdout.write(f"Active Teams: {active_teams}")
            self.stdout.write(f"Recruiting Teams: {recruiting_teams}")
            self.stdout.write(f"Open Teams: {open_teams}")
            self.stdout.write(f"Total Active Memberships: {total_memberships}")
            self.stdout.write(f"Total Invitations: {total_invites}")
            self.stdout.write(f"Pending Invitations: {pending_invites}")
            
            # Team distribution by game
            self.stdout.write("\n--- Teams by Game ---")
            games = Team.objects.values('game').annotate(
                count=Count('id')
            ).order_by('-count')
            
            for game_data in games:
                game = game_data['game'] or 'Not specified'
                count = game_data['count']
                self.stdout.write(f"{game}: {count}")
                
        elif format_type == 'json':
            import json
            report_data = {
                'overview': {
                    'total_teams': total_teams,
                    'active_teams': active_teams,
                    'recruiting_teams': recruiting_teams,
                    'open_teams': open_teams,
                    'total_memberships': total_memberships,
                    'total_invites': total_invites,
                    'pending_invites': pending_invites,
                }
            }
            self.stdout.write(json.dumps(report_data, indent=2))