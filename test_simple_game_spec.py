"""Simple test to verify game_spec is in tournament detail context"""
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from apps.tournaments.views.main import TournamentDetailView
from apps.tournaments.models import Tournament

# Get test tournament
tournament = Tournament.objects.filter(status__in=['published', 'registration_open', 'live']).select_related('game').first()

if tournament:
    print(f"Testing with: {tournament.name} ({tournament.game.slug})")
    
    # Create view
    factory = RequestFactory()
    request = factory.get(f'/tournaments/{tournament.slug}/')
    request.user = AnonymousUser()
    
    view = TournamentDetailView()
    view.request = request
    view.object = tournament
    
    # Get context
    context = view.get_context_data()
    
    if 'game_spec' in context:
        game_spec = context['game_spec']
        print(f"SUCCESS: game_spec in context")
        print(f"  Name: {game_spec.name}")
        print(f"  Display: {game_spec.display_name}")
        print(f"  Slug: {game_spec.slug}")
        print(f"  Icon: {game_spec.icon}")
        print(f"  Colors: {len(game_spec.colors)} keys")
        print(f"  Team size: {game_spec.min_team_size}-{game_spec.max_team_size}")
    else:
        print("FAILED: game_spec NOT in context")
else:
    print("No tournament found for testing")
