from apps.tournaments.models import Tournament
from apps.tournaments.models.match import Match

# Find tournament with matches
t = Tournament.objects.filter(name__icontains='Winter Cup').first()
if t:
    print(f'Tournament: {t.name}')
    print(f'Slug: {t.slug}')
    print(f'Game: {t.game.slug}')
    print(f'Matches: {Match.objects.filter(tournament=t).count()}')
    print(f'\nURL: http://localhost:8000/tournaments/{t.slug}/')
else:
    print('No tournament found with Winter Cup in name')
    print('\nAll tournaments:')
    for t in Tournament.objects.filter(is_deleted=False)[:5]:
        mc = Match.objects.filter(tournament=t).count()
        print(f'  - {t.name} ({t.game.slug}) - {mc} matches')
