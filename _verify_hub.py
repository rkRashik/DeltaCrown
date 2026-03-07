"""Quick Hub verification — checks the view compiles & API responds."""
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament

User = get_user_model()
t = Tournament.objects.get(slug='deltacrown-valorant-spring-2026')
print(f"Tournament: {t.name} (ID={t.id})")

# Check the view module imports correctly
from apps.tournaments.views.hub import (
    TournamentHubView, HubMatchesAPIView, HubParticipantsAPIView,
)
print("Hub views imported OK")

# Check the sidebar template exists and renders
from django.template.loader import get_template
tpl = get_template('tournaments/hub/_sidebar.html')
print(f"Sidebar template loaded OK")
tpl2 = get_template('tournaments/hub/hub.html')
print(f"Hub template loaded OK")

# Check via test client
client = Client()
# Need a logged-in staff user
staff = User.objects.filter(is_staff=True).first()
if staff:
    client.force_login(staff)
    resp = client.get(f'/tournaments/{t.slug}/hub/')
    print(f"Hub page (staff): {resp.status_code}")
    if resp.status_code == 200:
        content = resp.content.decode()
        has_organizer_block = 'Staff / Organizer' in content or 'Viewing As' in content
        print(f"  Organizer identity block: {'FOUND' if has_organizer_block else 'MISSING'}")
    elif resp.status_code == 302:
        print(f"  Redirected to: {resp.url}")
else:
    print("No staff user found")

# Check registered user
from apps.tournaments.models import Registration
reg = Registration.objects.filter(tournament=t, status='confirmed').first()
if reg and reg.user:
    client.force_login(reg.user)
    resp = client.get(f'/tournaments/{t.slug}/hub/')
    print(f"Hub page (participant): {resp.status_code}")

    # Test matches API
    resp2 = client.get(f'/tournaments/{t.slug}/hub/api/matches/')
    print(f"Matches API (participant): {resp2.status_code}")
    if resp2.status_code == 200:
        import json
        data = json.loads(resp2.content)
        print(f"  active={len(data.get('active_matches',[]))}, history={len(data.get('match_history',[]))}")

    # Test participants API
    resp3 = client.get(f'/tournaments/{t.slug}/hub/api/participants/')
    print(f"Participants API (participant): {resp3.status_code}")
    if resp3.status_code == 200:
        import json
        data = json.loads(resp3.content)
        print(f"  participants={data.get('total',0)}")
else:
    print("No registered participant found")

# Staff test for APIs
if staff:
    client.force_login(staff)
    resp4 = client.get(f'/tournaments/{t.slug}/hub/api/matches/')
    print(f"Matches API (staff): {resp4.status_code}")
    if resp4.status_code == 200:
        import json
        data = json.loads(resp4.content)
        print(f"  active={len(data.get('active_matches',[]))}, history={len(data.get('match_history',[]))}, total={data.get('total',0)}")

    resp5 = client.get(f'/tournaments/{t.slug}/hub/api/participants/')
    print(f"Participants API (staff): {resp5.status_code}")
    if resp5.status_code == 200:
        import json
        data = json.loads(resp5.content)
        print(f"  participants={data.get('total',0)}")

print("\nDone.")
