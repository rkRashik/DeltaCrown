"""
Debug command to investigate why hub shows no teams.

Usage:
    python manage.py debug_hub_visibility
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from apps.organizations.models import Team
from apps.organizations.choices import TeamStatus


class Command(BaseCommand):
    help = "Debug hub team visibility - show what teams exist and why they might not appear"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("\n=== HUB VISIBILITY DEBUG REPORT ===\n"))
        
        # Total teams
        total = Team.objects.count()
        self.stdout.write(f"Total Teams in DB: {total}")
        
        if total == 0:
            self.stdout.write(self.style.ERROR("\n❌ NO TEAMS IN DATABASE - This is why hub shows nothing!\n"))
            self.stdout.write("Action: Create teams via API or admin, then re-run this command.\n")
            return
        
        # By status
        self.stdout.write("\n--- Teams by Status ---")
        status_counts = Team.objects.values('status').annotate(count=Count('id')).order_by('-count')
        for entry in status_counts:
            status_name = entry['status'] or 'NULL'
            self.stdout.write(f"  {status_name}: {entry['count']}")
        
        # By visibility
        self.stdout.write("\n--- Teams by Visibility ---")
        visibility_counts = Team.objects.values('visibility').annotate(count=Count('id')).order_by('-count')
        for entry in visibility_counts:
            visibility_name = entry['visibility'] or 'NULL'
            self.stdout.write(f"  {visibility_name}: {entry['count']}")
        
        # Null checks
        self.stdout.write("\n--- Null Field Checks ---")
        null_created_by = Team.objects.filter(created_by__isnull=True).count()
        null_game_id = Team.objects.filter(game_id__isnull=True).count()
        self.stdout.write(f"  created_by is NULL: {null_created_by}")
        self.stdout.write(f"  game_id is NULL: {null_game_id}")
        
        # Hub eligible count
        self.stdout.write("\n--- Hub Eligibility ---")
        eligible = Team.objects.filter(
            status=TeamStatus.ACTIVE,
            visibility='PUBLIC'
        ).count()
        
        if eligible == 0:
            self.stdout.write(self.style.ERROR(f"  ❌ ELIGIBLE (PUBLIC + ACTIVE): {eligible}"))
            self.stdout.write("\n  This is the problem! No PUBLIC ACTIVE teams exist.")
            self.stdout.write("  Check if teams are being created as PRIVATE or non-ACTIVE by default.\n")
        else:
            self.stdout.write(self.style.SUCCESS(f"  ✅ ELIGIBLE (PUBLIC + ACTIVE): {eligible}"))
        
        # Recent teams
        self.stdout.write("\n--- 10 Most Recent Teams ---")
        recent = Team.objects.select_related('organization', 'created_by').order_by('-created_at')[:10]
        
        if not recent:
            self.stdout.write("  (none)")
        else:
            self.stdout.write(f"\n  {'Slug':<20} {'Name':<25} {'Status':<12} {'Vis':<10} {'Created':<20} {'Org':<15} {'Game':<15}")
            self.stdout.write("  " + "-" * 140)
            
            for team in recent:
                slug = team.slug[:19] if team.slug else 'NULL'
                name = team.name[:24] if team.name else 'NULL'
                status = team.status[:11] if team.status else 'NULL'
                vis = team.visibility[:9] if team.visibility else 'NULL'
                created = team.created_at.strftime('%Y-%m-%d %H:%M') if team.created_at else 'NULL'
                org = team.organization.name[:14] if team.organization else 'Independent'
                game = str(team.game_id) if team.game_id else 'NULL'
                
                # Color-code by eligibility
                if team.status == TeamStatus.ACTIVE and team.visibility == 'PUBLIC':
                    line = self.style.SUCCESS(f"  {slug:<20} {name:<25} {status:<12} {vis:<10} {created:<20} {org:<15} {game:<15}")
                else:
                    line = self.style.WARNING(f"  {slug:<20} {name:<25} {status:<12} {vis:<10} {created:<20} {org:<15} {game:<15}")
                
                self.stdout.write(line)
        
        # Summary
        self.stdout.write("\n--- Summary ---")
        if eligible > 0:
            self.stdout.write(self.style.SUCCESS(f"✅ {eligible} teams should be visible on hub"))
            self.stdout.write("   If hub still shows nothing, check:")
            self.stdout.write("   1. Cache issues (empty results cached too long)")
            self.stdout.write("   2. Template context mismatch (view returns 'teams' but template expects 'featured_teams')")
            self.stdout.write("   3. Hub view queryset filters (ranking dependency, verified_only, etc)")
        else:
            self.stdout.write(self.style.ERROR(f"❌ {eligible} teams eligible - hub correctly shows nothing"))
            self.stdout.write("   Fix team creation defaults (status=ACTIVE, visibility=PUBLIC)")
        
        self.stdout.write("\n=== END REPORT ===\n")
