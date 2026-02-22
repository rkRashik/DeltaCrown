import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'deltacrown.settings'
django.setup()

from django.utils import timezone
from apps.tournaments.models import Tournament
from apps.tournaments.views.hub import _get_next_phase_event

t = Tournament()
t.tournament_start = timezone.now() + timezone.timedelta(hours=2)
t.tournament_end = timezone.now() + timezone.timedelta(hours=5)
t.registration_start = timezone.now() - timezone.timedelta(days=1)
t.registration_end = timezone.now() + timezone.timedelta(hours=1)

statuses = ['draft', 'published', 'registration_open', 'registration_closed', 'live', 'completed']
for s in statuses:
    t.status = s
    r = _get_next_phase_event(t, None, timezone.now())
    print(f"[OK] {s:25s} -> type={r.get('type','?'):8s} label={r.get('label','?')}")

print("\nALL STATUS PATHS OK")
