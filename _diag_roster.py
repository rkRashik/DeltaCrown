import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()
import logging
logging.disable(logging.CRITICAL)

from apps.user_profile.models import GameProfile
from apps.tournaments.models import Registration, Tournament
from apps.teams.models import Team, TeamMember

t = Tournament.objects.get(slug='valorant-scrims-44')
print('game:', t.game, ' | type:', t.participation_type)
regs = list(Registration.objects.filter(tournament=t).select_related('user')[:3])
for r in regs:
    rd = r.registration_data or {}
    snap = r.lineup_snapshot or []
    print(f'\nReg {r.id} | username={r.user.username if r.user else None} | team_id={r.team_id}')
    print(f'  reg_data keys: {list(rd.keys())}')
    print(f'  lineup_snapshot entries: {len(snap)}')
    if snap:
        print(f'  snap[0]: {snap[0]}')
    if r.team_id:
        team = Team.objects.filter(id=r.team_id).first()
        print(f'  Team: {team.name if team else "NOTFOUND"} | tag: {getattr(team, "tag", None) if team else None}')
        members = list(TeamMember.objects.filter(team__id=r.team_id).select_related('user')[:6])
        for m in members:
            # Check game profiles
            gps = list(GameProfile.objects.filter(user=m.user)[:3])
            gp_info = [(gp.game, gp.ign) for gp in gps]
            print(f'    Member: {m.user.username} | role: {m.role} | game_profiles: {gp_info}')

print('\n--- GameProfile structure ---')
gp_sample = GameProfile.objects.first()
if gp_sample:
    print('Fields:', [f.name for f in GameProfile._meta.fields])
    print('Sample:', gp_sample.user, gp_sample.game, gp_sample.ign, gp_sample.game_display_name)
