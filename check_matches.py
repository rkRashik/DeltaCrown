from apps.tournaments.models import Tournament
from apps.tournaments.models.match import Match

# Find tournament
t = Tournament.objects.filter(name__icontains='Winter Cup').first()
print(f'Tournament: {t.name if t else "Not found"}')

if t:
    matches = Match.objects.filter(tournament=t, is_deleted=False)
    print(f'Total Matches: {matches.count()}')
    
    if matches.exists():
        print('\nMatch Details:')
        for i, m in enumerate(matches[:3], 1):
            print(f'\n{i}. {m.participant1_name} vs {m.participant2_name}')
            print(f'   State: {m.state}')
            print(f'   Round: {m.round_number}, Match: {m.match_number}')
            print(f'   lobby_info: {m.lobby_info}')
            print(f'   Stream URL: {m.stream_url or "None"}')
    else:
        print('\nNo matches found!')
        print('Run the seed script: Get-Content seed_realistic_matches.py | python manage.py shell')
