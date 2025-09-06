import pytest
from django.apps import apps
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()
UserProfile = apps.get_model('user_profile', 'UserProfile')
Tournament = apps.get_model('tournaments', 'Tournament')
EfootballTeamPreset = apps.get_model('teams', 'EfootballTeamPreset')

from apps.game_efootball.forms import EfootballDuoForm

def make_user(username='u_ef1'):
    u = User.objects.create_user(username=username, password='x')
    prof, _ = UserProfile.objects.get_or_create(user=u)
    return u, prof

@pytest.mark.django_db
def test_efootball_prefill_from_preset_when_no_active_team():
    u, prof = make_user('prefill_ef')
    EfootballTeamPreset.objects.create(
        profile=prof, name='EF Preset', team_name='Duo Alpha',
        captain_name='Rahim', captain_ign='EF_Rahim',
        mate_name='Karim', mate_ign='EF_Karim'
    )
    t = Tournament.objects.create(name='EF Cup', slug='ef-cup', game='efootball')
    rf = RequestFactory()
    req = rf.get('/')
    req.user = u
    form = EfootballDuoForm(None, None, tournament=t, request=req, entry_fee_bdt=0)
    assert form.fields['team_name'].initial == 'Duo Alpha'
    assert form.fields['captain_full_name'].initial == 'Rahim'
    assert form.fields['captain_ign'].initial == 'EF_Rahim'
    assert form.fields['mate_full_name'].initial == 'Karim'
    assert form.fields['mate_ign'].initial == 'EF_Karim'

@pytest.mark.django_db
def test_efootball_save_preset_on_post():
    u, prof = make_user('save_ef')
    t = Tournament.objects.create(name='EF Cup 2', slug='ef-cup-2', game='efootball')
    rf = RequestFactory()
    req = rf.post('/')
    req.user = u
    data = {
        'use_team_id': '',
        'team_name': 'Bravo Duo',
        'captain_full_name': 'Rahim Uddin',
        'captain_ign': 'EF_Rahim',
        'captain_email': '',
        'captain_phone': '',
        'mate_full_name': 'Karim Ali',
        'mate_ign': 'EF_Karim',
        'mate_email': '',
        'mate_phone': '',
        'agree_consent': True,
        'agree_rules': True,
        'agree_no_tools': True,
        'agree_no_multi_team': True,
        'payment_method': '',
        'payer_account_number': '',
        'payment_reference': '',
        'amount_bdt': '',
        'save_as_preset': True,
    }
    form = EfootballDuoForm(data, None, tournament=t, request=req, entry_fee_bdt=0)
    assert form.is_valid(), form.errors
    reg = form.save()
    ep = EfootballTeamPreset.objects.filter(profile=prof).order_by('-created_at').first()
    assert ep and ep.team_name == 'Bravo Duo' and ep.captain_ign == 'EF_Rahim' and ep.mate_ign == 'EF_Karim'
