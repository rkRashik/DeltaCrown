"""Test script: verify registration template renders with all form_config toggles enabled."""
import os, sys, django, datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from django.template.loader import get_template
from django.test import RequestFactory
from types import SimpleNamespace


def main():
    # Template compilation
    print('=== Template Compilation ===')
    templates = [
        'tournaments/registration/smart_register.html',
        'tournaments/registration/includes/_step_coordinator.html',
        'tournaments/registration/includes/_step_comms.html',
        'tournaments/registration/includes/_step_team_info.html',
        'tournaments/registration/includes/_step_roster.html',
        'tournaments/registration/includes/_step_questions.html',
        'tournaments/registration/includes/_step_payment.html',
        'tournaments/registration/includes/_step_review.html',
    ]
    for t in templates:
        try:
            get_template(t)
            print(f'  {t.split("/")[-1]}: OK')
        except Exception as e:
            print(f'  {t.split("/")[-1]}: FAIL - {e}')
            return

    # Full render test
    print('\n=== Full Render Test (all toggles ON) ===')

    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.first()
    if not user:
        print('  No users in DB — skipping render test')
        return

    factory = RequestFactory()
    request = factory.get('/test/')
    request.user = user

    team = SimpleNamespace(
        slug='test-team', name='Test Team', tag='TST', logo=None, banner=None,
        bio='Test bio', region='South Asia', is_verified=True,
        created_at=datetime.datetime.now()
    )

    tournament_game = SimpleNamespace(name='Valorant')
    tournament = SimpleNamespace(
        name='Test Tournament', slug='test-slug', game=tournament_game,
        has_entry_fee=True, entry_fee_amount=100, entry_fee_currency='BDT',
        get_format_display=lambda: '5v5', participation_type='team',
        refund_policy='no_refund', get_refund_policy_display=lambda: 'No Refund',
        refund_policy_text='',
    )

    form_config = {
        'form_type': 'default_team',
        'enable_coordinator_role': True,
        'coordinator_roles': [{'value': 'captain', 'label': 'Captain', 'description': 'Leads'}],
        'coordinator_help': 'Select role',
        'channels': [{'key': 'discord', 'label': 'Discord ID', 'placeholder': 'User#0000', 'required': True}],
        'enable_preferred_communication': True,
        'enable_team_logo_upload': True,
        'enable_team_banner_upload': True,
        'enable_team_bio': True,
        'require_member_real_name': True,
        'require_member_photo': False,
        'require_member_email': True,
        'require_member_age': False,
        'require_member_national_id': False,
        'member_custom_fields': [],
        'allow_roster_editing': True,
        'show_member_ranks': True,
        'show_member_game_ids': True,
        'enable_age_field': True,
        'enable_country_field': True,
        'enable_platform_field': True,
        'enable_rank_field': True,
        'enable_phone_field': True,
        'enable_discord_field': True,
        'enable_preferred_contact_field': True,
        'enable_team_logo_field': True,
        'enable_team_region_field': True,
        'enable_captain_display_name_field': True,
        'enable_captain_whatsapp_field': True,
        'enable_captain_phone_field': True,
        'enable_captain_discord_field': True,
        'enable_roster_display_names': True,
        'enable_roster_emails': True,
        'enable_payment_mobile_number_field': True,
        'enable_payment_screenshot_field': True,
        'enable_payment_notes_field': True,
    }

    context = {
        'tournament': tournament, 'game_spec': None,
        'game_color': '#06b6d4', 'game_color_rgb': '6, 182, 212',
        'registration_type': 'team', 'readiness': 75,
        'filled_count': 6, 'missing_count': 2, 'total_fields': 8,
        'circumference': 251, 'dash_offset': 62,
        'identity_complete': True, 'game_complete': True,
        'team': team, 'roster_members': [], 'user_teams': [],
        'deltacoin_can_afford': True, 'deltacoin_balance': 500,
        'game_id_label': 'Riot ID', 'game_id_placeholder': 'Name#TAG',
        'sections_complete': 3, 'sections_total': 5,
        'sections_needing_input': ['comms', 'roster'],
        'custom_questions': [], 'refund_policy': 'no_refund',
        'refund_policy_display': 'No Refund', 'refund_policy_text': '',
        'is_guest_team': False, 'allows_guest_teams': False,
        'guest_slots_remaining': 0, 'max_guest_teams': 0,
        'is_waitlist': False, 'waitlist_count': 0,
        'allow_display_name_override': False,
        'form_config': form_config,
        'roster_config': {
            'min_team_size': 5, 'max_team_size': 5,
            'min_substitutes': 0, 'max_substitutes': 2,
            'min_roster_size': 5, 'max_roster_size': 10,
            'allow_coaches': True, 'max_coaches': 1,
            'allow_analysts': False, 'max_analysts': 0,
            'team_size_display': '5v5',
        },
        'roster_roles': [],
        'payment_methods': ['bkash', 'nagad', 'rocket'],
        'request': request, 'messages': [],
        'fields': {
            'full_name': {'value': user.get_full_name() or 'Test User'},
            'display_name': {'value': user.username},
            'email': {'value': user.email},
            'phone': {'value': '01700001234'},
            'discord': {'value': 'test#1234'},
            'country': {'value': 'BD'},
            'game_id': {'value': 'Test#1234', 'locked': True, 'source': 'passport'},
            'platform_server': {'value': 'AP'},
            'rank': {'value': 'Diamond'},
            'preferred_contact': {'value': 'discord'},
        },
    }

    try:
        template = get_template('tournaments/registration/smart_register.html')
        html = template.render(context, request)
        print(f'  Render: OK ({len(html)} bytes)')

        # Check review elements
        review_ids = [
            'review-age', 'review-country', 'review-platform',
            'review-captain-display', 'review-captain-whatsapp',
            'review-captain-phone', 'review-captain-discord',
            'review-team-region', 'review-team-bio',
            'review-payment-mobile', 'review-payment-notes',
            'review-preferred-contact',
        ]
        print('\n=== Review Element Check ===')
        for rid in review_ids:
            found = f'id="{rid}"' in html
            print(f'  #{rid}: {"FOUND" if found else "MISSING"}')

        # Check no template comments leaked
        import re
        comments = re.findall(r'\{#.*?#\}', html)
        print(f'\n  Template comments in output: {len(comments)}')

        # Check no Django errors
        errors = ['NoReverseMatch', 'TemplateSyntaxError', 'VariableDoesNotExist']
        for err in errors:
            if err in html:
                print(f'  ERROR: {err} found in output!')

    except Exception as e:
        print(f'  RENDER ERROR: {e}')
        import traceback
        traceback.print_exc()

    print('\n=== DONE ===')


if __name__ == '__main__':
    main()
