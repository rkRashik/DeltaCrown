# Generated data migration to fix teams exceeding game-specific roster limits
from django.db import migrations
from django.db.models import Count, Q


def get_max_roster_for_game(game):
    """Get maximum roster size for a game"""
    ROSTER_LIMITS = {
        'valorant': 9,      # 5 starters + 3 subs + 1 coach
        'cs2': 8,           # 5 starters + 2 subs + 1 coach
        'dota2': 8,         # 5 starters + 2 subs + 1 coach
        'mlbb': 9,          # 5 starters + 2 subs + 1 coach + 1 analyst
        'codm': 7,          # 5 starters + 1 sub + 1 coach
        'pubgm': 7,         # 4 starters + 2 subs + 1 coach
        'freefire': 7,      # 4 starters + 2 subs + 1 coach
        'efootball': 4,     # 2 starters + 1 sub + 1 coach
        'fc26': 4,          # 2 starters + 1 sub + 1 coach
    }
    return ROSTER_LIMITS.get(game, 8)  # Default to legacy limit


def cleanup_oversized_rosters(apps, schema_editor):
    """
    Remove excess members from teams that exceed their game-specific roster limits.
    
    Priority for removal (keep these):
    1. OWNER (always keep)
    2. Captain (team.captain FK or is_captain=True)
    3. MANAGER roles
    4. COACH roles
    5. PLAYER with earliest join date
    6. SUBSTITUTE with earliest join date
    
    Priority for removal (remove these first):
    1. SUBSTITUTE with latest join date
    2. PLAYER with latest join date (not captain)
    3. Duplicates of roles that should be singular
    """
    Team = apps.get_model('teams', 'Team')
    TeamMembership = apps.get_model('teams', 'TeamMembership')
    
    fixed_teams = []
    removed_count = 0
    
    # Get all teams with active members
    teams = Team.objects.annotate(
        active_count=Count('memberships', filter=Q(memberships__status='ACTIVE'))
    ).filter(active_count__gt=0)
    
    for team in teams:
        max_roster = get_max_roster_for_game(team.game)
        active_members = TeamMembership.objects.filter(
            team=team,
            status='ACTIVE'
        ).select_related('profile').order_by('joined_at')
        
        current_count = active_members.count()
        
        if current_count <= max_roster:
            continue  # Team is within limits
        
        excess_count = current_count - max_roster
        
        # Build priority list (members to KEEP)
        keep_members = set()
        
        # 1. Always keep OWNER
        owner = active_members.filter(role='OWNER').first()
        if owner:
            keep_members.add(owner.id)
        
        # 2. Keep captain (FK field or is_captain flag)
        if team.captain_id:
            captain = active_members.filter(id=team.captain_id).first()
            if captain:
                keep_members.add(captain.id)
        else:
            # Fallback to is_captain flag
            captain = active_members.filter(is_captain=True).first()
            if captain:
                keep_members.add(captain.id)
        
        # 3. Keep all MANAGER roles (usually max 2-3)
        for manager in active_members.filter(role='MANAGER'):
            keep_members.add(manager.id)
        
        # 4. Keep COACH roles (usually max 1)
        for coach in active_members.filter(role='COACH'):
            keep_members.add(coach.id)
        
        # 5. Keep oldest PLAYER members (fill remaining slots)
        remaining_slots = max_roster - len(keep_members)
        if remaining_slots > 0:
            for player in active_members.filter(role='PLAYER').exclude(id__in=keep_members):
                if len(keep_members) >= max_roster:
                    break
                keep_members.add(player.id)
        
        # 6. Keep oldest SUBSTITUTE members (fill remaining slots)
        remaining_slots = max_roster - len(keep_members)
        if remaining_slots > 0:
            for sub in active_members.filter(role='SUBSTITUTE').exclude(id__in=keep_members):
                if len(keep_members) >= max_roster:
                    break
                keep_members.add(sub.id)
        
        # Identify members to remove
        members_to_remove = active_members.exclude(id__in=keep_members)
        
        if members_to_remove.exists():
            removed_usernames = [
                f"{m.profile.display_name if m.profile else 'Unknown'} ({m.role})"
                for m in members_to_remove
            ]
            
            # Remove excess members by setting status to REMOVED
            members_to_remove.update(status='REMOVED')
            
            removed_count += members_to_remove.count()
            fixed_teams.append({
                'team_id': team.id,
                'team_name': team.name,
                'game': team.game,
                'max_roster': max_roster,
                'had': current_count,
                'removed': members_to_remove.count(),
                'removed_members': removed_usernames
            })
    
    # Print summary
    if fixed_teams:
        print(f"\n{'='*80}")
        print(f"ROSTER CLEANUP SUMMARY")
        print(f"{'='*80}")
        print(f"Teams fixed: {len(fixed_teams)}")
        print(f"Total members removed: {removed_count}")
        print(f"\nDetails:")
        for info in fixed_teams:
            print(f"\n  Team: {info['team_name']} (ID: {info['team_id']})")
            print(f"  Game: {info['game']} (Max roster: {info['max_roster']})")
            print(f"  Had {info['had']} members, removed {info['removed']}:")
            for username in info['removed_members']:
                print(f"    - {username}")
        print(f"\n{'='*80}\n")
    else:
        print("\nNo teams exceeded their game-specific roster limits. No cleanup needed.\n")


def reverse_cleanup(apps, schema_editor):
    """
    Reversal is not possible because we don't know which members were removed.
    This is a data cleanup migration that should not be reversed.
    """
    print("\nWARNING: This migration cannot be reversed. Removed members are permanently archived.")
    print("If you need to restore members, use database backups.\n")


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0006_add_tournament_lock_fields'),
    ]

    operations = [
        migrations.RunPython(cleanup_oversized_rosters, reverse_cleanup),
    ]
