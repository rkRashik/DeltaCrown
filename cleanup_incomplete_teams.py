"""
Cleanup script for incomplete/failed team creation records.

Run with: python cleanup_incomplete_teams.py

This script will:
1. Find all ACTIVE teams that have no owner membership
2. Find all teams created in last 24 hours with only INVITED memberships
3. Delete or mark as DISBANDED these incomplete records
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

from apps.organizations.models import Team, TeamMembership

User = get_user_model()


def cleanup_incomplete_teams(dry_run=True):
    """
    Find and clean up incomplete team records.
    
    Args:
        dry_run: If True, only show what would be deleted
    """
    print("=" * 80)
    print("TEAM CLEANUP SCRIPT")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will delete)'}")
    print()
    
    # Find teams with no ACTIVE owner membership
    teams_no_owner = Team.objects.filter(
        status='ACTIVE',
        organization__isnull=True  # Independent teams only
    ).exclude(
        vnext_memberships__status='ACTIVE',
        vnext_memberships__role='OWNER'
    ).distinct()
    
    print(f"Found {teams_no_owner.count()} ACTIVE teams with no ACTIVE owner:")
    for team in teams_no_owner:
        memberships = team.vnext_memberships.all()
        game_name = 'No game'
        if team.game_id:
            try:
                from apps.games.models import Game
                game = Game.objects.get(id=team.game_id)
                game_name = game.name
            except:
                game_name = f'Game ID {team.game_id}'
        
        print(f"  - Team #{team.id}: {team.name} ({game_name})")
        print(f"    Created: {team.created_at}")
        print(f"    Memberships: {memberships.count()}")
        for m in memberships:
            print(f"      - {m.user.username}: {m.role} ({m.status})")
        
        if not dry_run:
            # Option 1: Delete completely
            team.delete()
            print(f"    ✅ DELETED")
            
            # Option 2: Mark as disbanded (preserve for audit)
            # team.status = 'DISBANDED'
            # team.save()
            # print(f"    ✅ MARKED AS DISBANDED")
    
    print()
    
    # Find teams created recently with only INVITED memberships
    recent_cutoff = timezone.now() - timedelta(hours=24)
    teams_only_invited = Team.objects.filter(
        status='ACTIVE',
        organization__isnull=True,  # Independent teams only
        created_at__gte=recent_cutoff
    ).exclude(
        vnext_memberships__status='ACTIVE'
    ).distinct()
    
    print(f"Found {teams_only_invited.count()} recent ACTIVE teams with only INVITED memberships:")
    for team in teams_only_invited:
        memberships = team.vnext_memberships.all()
        game_name = 'No game'
        if team.game_id:
            try:
                from apps.games.models import Game
                game = Game.objects.get(id=team.game_id)
                game_name = game.name
            except:
                game_name = f'Game ID {team.game_id}'
        
        print(f"  - Team #{team.id}: {team.name} ({game_name})")
        print(f"    Created: {team.created_at}")
        print(f"    Memberships: {memberships.count()}")
        
        if not dry_run:
            team.delete()
            print(f"    ✅ DELETED")
    
    print()
    print("=" * 80)
    if dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print("Run with --live flag to actually delete: python cleanup_incomplete_teams.py --live")
    else:
        print("CLEANUP COMPLETE")
    print("=" * 80)


def cleanup_user_teams(username=None, user_id=None, dry_run=True):
    """
    Clean up all teams for a specific user.
    
    Args:
        username: Username to clean up
        user_id: User ID to clean up
        dry_run: If True, only show what would be deleted
    """
    if not username and not user_id:
        print("ERROR: Must provide either username or user_id")
        return
    
    try:
        if user_id:
            user = User.objects.get(id=user_id)
        else:
            user = User.objects.get(username=username)
    except User.DoesNotExist:
        print(f"ERROR: User not found: {username or user_id}")
        return
    
    print("=" * 80)
    print(f"CLEANUP TEAMS FOR USER: {user.username} (ID: {user.id})")
    print("=" * 80)
    print(f"Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will delete)'}")
    print()
    
    # Find all teams where user is owner
    user_teams = Team.objects.filter(
        status='ACTIVE',
        organization__isnull=True,
        vnext_memberships__user=user,
        vnext_memberships__status='ACTIVE',
        vnext_memberships__role='OWNER'
    ).distinct()
    
    print(f"Found {user_teams.count()} ACTIVE independent teams owned by {user.username}:")
    for team in user_teams:
        game_name = 'No game'
        if team.game_id:
            try:
                from apps.games.models import Game
                game = Game.objects.get(id=team.game_id)
                game_name = game.name
            except:
                game_name = f'Game ID {team.game_id}'
        
        print(f"  - Team #{team.id}: {team.name}")
        print(f"    Game: {game_name}")
        print(f"    Created: {team.created_at}")
        
        if not dry_run:
            team.delete()
            print(f"    ✅ DELETED")
    
    print()
    print("=" * 80)
    if dry_run:
        print("DRY RUN COMPLETE - No changes made")
        print("Run with --live flag to actually delete")
    else:
        print("CLEANUP COMPLETE")
    print("=" * 80)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up incomplete team records')
    parser.add_argument('--live', action='store_true', help='Actually delete records (default is dry-run)')
    parser.add_argument('--user', type=str, help='Clean up teams for specific username')
    parser.add_argument('--user-id', type=int, help='Clean up teams for specific user ID')
    
    args = parser.parse_args()
    
    dry_run = not args.live
    
    if args.user or args.user_id:
        cleanup_user_teams(username=args.user, user_id=args.user_id, dry_run=dry_run)
    else:
        cleanup_incomplete_teams(dry_run=dry_run)
