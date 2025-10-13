"""
Fix Tournament Types for Test Tournaments
Sets tournament_type based on game characteristics
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.tournaments.models import Tournament

print("=" * 70)
print("FIXING TOURNAMENT TYPES")
print("=" * 70)

# Define which games are typically solo vs team
SOLO_GAMES = ['efootball', 'fc26']  # Sports games - typically 1v1
TEAM_GAMES = ['valorant', 'cs2', 'dota2', 'mlbb', 'pubg', 'freefire']  # Squad games

tournaments = Tournament.objects.filter(name__icontains='test', status='PUBLISHED')

fixed_count = 0
for tournament in tournaments:
    print(f"\n{'='*70}")
    print(f"Tournament: {tournament.name}")
    print(f"Game: {tournament.game} ({tournament.get_game_display()})")
    print(f"Current tournament_type: {tournament.tournament_type}")
    
    # Determine correct type
    if tournament.game in SOLO_GAMES:
        new_type = 'SOLO'
    elif tournament.game in TEAM_GAMES:
        new_type = 'TEAM'
    else:
        new_type = 'TEAM'  # Default to TEAM
    
    # Update if different
    if tournament.tournament_type != new_type:
        old_type = tournament.tournament_type
        tournament.tournament_type = new_type
        tournament.save(update_fields=['tournament_type'])
        print(f"✅ UPDATED: {old_type} → {new_type}")
        fixed_count += 1
    else:
        print(f"✓ Already correct: {new_type}")
    
    # Also create/update settings for team tournaments
    if new_type == 'TEAM':
        from apps.tournaments.models import TournamentSettings
        
        settings, created = TournamentSettings.objects.get_or_create(
            tournament=tournament
        )
        
        # Set team sizes based on game
        if tournament.game == 'valorant':
            settings.min_team_size = 5
            settings.max_team_size = 7
        elif tournament.game == 'cs2':
            settings.min_team_size = 5
            settings.max_team_size = 7
        elif tournament.game == 'dota2':
            settings.min_team_size = 5
            settings.max_team_size = 7
        elif tournament.game == 'mlbb':
            settings.min_team_size = 5
            settings.max_team_size = 7
        elif tournament.game == 'pubg':
            settings.min_team_size = 4
            settings.max_team_size = 4
        elif tournament.game == 'freefire':
            settings.min_team_size = 4
            settings.max_team_size = 4
        
        settings.save()
        
        if created:
            print(f"   📋 Created settings with team_size: {settings.min_team_size}-{settings.max_team_size}")
        else:
            print(f"   📋 Updated settings with team_size: {settings.min_team_size}-{settings.max_team_size}")

print(f"\n{'='*70}")
print(f"✅ COMPLETE - Fixed {fixed_count} tournaments")
print("=" * 70)
