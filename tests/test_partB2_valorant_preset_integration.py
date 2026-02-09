import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import RequestFactory

User = get_user_model()
UserProfile = apps.get_model('user_profile', 'UserProfile')
Tournament = apps.get_model('tournaments', 'Tournament')
ValorantTeamPreset = apps.get_model('organizations', 'ValorantTeamPreset')
ValorantPlayerPreset = apps.get_model('organizations', 'ValorantPlayerPreset')

from apps.game_valorant.forms import ValorantTeamForm

def make_user(username='u1'):
    u = User.objects.create_user(username=username, email=f"{username}@example.com", password='x')
    prof, _ = UserProfile.objects.get_or_create(user=u)
    return u, prof

@pytest.mark.django_db
def test_valorant_prefill_from_preset_when_no_active_team():
    u, prof = make_user('prefill1')
    ValorantTeamPreset.objects.create(profile=prof, name='Saved', team_name='Alpha', team_tag='ALP', region='SEA')
    t = Tournament.objects.create(name='Val Cup', slug='val-cup', game='valorant')
    rf = RequestFactory()
    req = rf.get('/')
    req.user = u
    form = ValorantTeamForm(None, None, tournament=t, request=req, entry_fee_bdt=0)
    assert form.fields['team_name'].initial == 'Alpha'
    assert form.fields['team_tag'].initial == 'ALP'
    assert form.fields['region'].initial == 'SEA'

@pytest.mark.django_db
def test_valorant_save_preset_on_post():
    u, prof = make_user('save1')
    t = Tournament.objects.create(name='Val Cup 2', slug='val-cup-2', game='valorant')
    rf = RequestFactory()
    req = rf.post('/')
    req.user = u
    data = {
        'team': '',
        'team_name': 'Bravo',
        'team_tag': 'BRV',
        'region': 'SEA',
        'agree_captain_consent': True,
        'agree_rules': True,
        'agree_no_cheat': True,
        'agree_enforcement': True,
        'payment_method': '',
        'payer_account_number': '',
        'payment_reference': '',
        'amount_bdt': '',
        'save_as_preset': True,
        # players: 5 starters minimum
        'p0-full_name': 'A', 'p0-riot_id': 'a', 'p0-riot_tagline': 'AP', 'p0-discord': 'a#1', 'p0-role': 'starter',
        'p1-full_name': 'B', 'p1-riot_id': 'b', 'p1-riot_tagline': 'AP', 'p1-discord': 'b#1', 'p1-role': 'starter',
        'p2-full_name': 'C', 'p2-riot_id': 'c', 'p2-riot_tagline': 'AP', 'p2-discord': 'c#1', 'p2-role': 'starter',
        'p3-full_name': 'D', 'p3-riot_id': 'd', 'p3-riot_tagline': 'AP', 'p3-discord': 'd#1', 'p3-role': 'starter',
        'p4-full_name': 'E', 'p4-riot_id': 'e', 'p4-riot_tagline': 'AP', 'p4-discord': 'e#1', 'p4-role': 'starter',
    }
    form = ValorantTeamForm(data, None, tournament=t, request=req, entry_fee_bdt=0)
    assert form.is_valid(), form.errors
    reg = form.save()
    vp = ValorantTeamPreset.objects.filter(profile=prof).order_by('-created_at').first()
    assert vp and vp.team_name == 'Bravo' and vp.team_tag == 'BRV' and vp.region == 'SEA'
    # players copied to preset
    assert ValorantPlayerPreset.objects.filter(preset=vp).count() >= 5
