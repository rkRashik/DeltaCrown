"""
Data Migration: Copy Tournament capacity data to TournamentCapacity

Migrates existing slot_size and derives team size constraints
from game type to populate TournamentCapacity records.

This is a non-destructive migration - original Tournament fields
are preserved for backward compatibility.

Author: DeltaCrown Development Team
Date: October 3, 2025
"""

from django.db import migrations


def migrate_capacity_data(apps, schema_editor):
    """
    Copy capacity data from Tournament to TournamentCapacity.
    
    For each tournament with slot_size:
    1. Create TournamentCapacity record
    2. Set max_teams = slot_size
    3. Derive team sizes based on game type
    4. Set sensible defaults for other fields
    """
    Tournament = apps.get_model('tournaments', 'Tournament')
    TournamentCapacity = apps.get_model('tournaments', 'TournamentCapacity')
    
    print("\n" + "=" * 70)
    print("🔄 Migrating capacity data from Tournament to TournamentCapacity")
    print("=" * 70)
    
    tournaments = Tournament.objects.filter(slot_size__isnull=False)
    total_count = tournaments.count()
    
    print(f"\n📊 Found {total_count} tournaments to process...")
    print()
    
    created_count = 0
    skipped_count = 0
    errors = []
    
    for tournament in tournaments:
        try:
            # Check if capacity already exists
            if TournamentCapacity.objects.filter(tournament=tournament).exists():
                print(f"⏭️  Skipping '{tournament.name}' (capacity already exists)")
                skipped_count += 1
                continue
            
            # Determine team sizes based on game
            if tournament.game == 'valorant':
                min_team_size = 5  # Standard 5v5
                max_team_size = 7  # Allow 2 substitutes
                game_display = "Valorant (5v5)"
            elif tournament.game == 'efootball':
                min_team_size = 1  # 1v1 matches
                max_team_size = 1
                game_display = "eFootball (1v1)"
            else:
                # Default for other games
                min_team_size = 1
                max_team_size = 10
                game_display = f"{tournament.game} (flexible)"
            
            # Create TournamentCapacity
            capacity = TournamentCapacity.objects.create(
                tournament=tournament,
                slot_size=tournament.slot_size,
                max_teams=tournament.slot_size,  # Initially same as slot_size
                min_team_size=min_team_size,
                max_team_size=max_team_size,
                registration_mode='open',  # Default to open registration
                waitlist_enabled=True,     # Enable waitlist by default
                current_registrations=0    # Will be synced later if needed
            )
            
            print(f"✅ Created capacity for '{tournament.name}'")
            print(f"   Game: {game_display}")
            print(f"   Slots: {capacity.slot_size}, Teams: {capacity.max_teams}")
            print(f"   Team Size: {min_team_size}-{max_team_size} players")
            
            created_count += 1
            
        except Exception as e:
            error_msg = f"Failed to migrate '{tournament.name}': {str(e)}"
            errors.append(error_msg)
            print(f"❌ {error_msg}")
    
    # Print summary
    print()
    print("=" * 70)
    print("📈 Migration Summary")
    print("=" * 70)
    print(f"Total tournaments: {total_count}")
    print(f"Capacities created: {created_count}")
    print(f"Capacities skipped: {skipped_count}")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print("\n⚠️  Errors encountered:")
        for error in errors:
            print(f"   • {error}")
    
    if created_count > 0:
        print(f"\n✅ Successfully created {created_count} TournamentCapacity records!")
    elif skipped_count == total_count:
        print("\nℹ️  No new capacities created (all tournaments already migrated or have no capacity data)")
    
    print("=" * 70)
    print()


def reverse_capacity_migration(apps, schema_editor):
    """
    Reverse migration - delete TournamentCapacity records.
    
    Note: This only deletes TournamentCapacity records.
    Original Tournament.slot_size data is preserved.
    """
    TournamentCapacity = apps.get_model('tournaments', 'TournamentCapacity')
    
    count = TournamentCapacity.objects.count()
    
    if count > 0:
        print(f"\n🔄 Reversing migration: Deleting {count} TournamentCapacity records...")
        TournamentCapacity.objects.all().delete()
        print(f"✅ Deleted {count} TournamentCapacity records")
        print("ℹ️  Original Tournament.slot_size data preserved")
    else:
        print("\nℹ️  No TournamentCapacity records to delete")


class Migration(migrations.Migration):
    """
    Migration to copy capacity data from Tournament to TournamentCapacity.
    
    This migration is:
    - Non-destructive: Original Tournament fields preserved
    - Idempotent: Safe to run multiple times
    - Reversible: Can be rolled back cleanly
    """
    
    dependencies = [
        ('tournaments', '0033_add_tournament_capacity'),
    ]
    
    operations = [
        migrations.RunPython(
            migrate_capacity_data,
            reverse_capacity_migration
        ),
    ]
