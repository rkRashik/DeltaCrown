"""Pure presentation regression checks; no Django setup or database access."""

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from apps.siteui.homepage_presentation import get_homepage_presentation, tournament_presentation


class HomepagePresentationTests(TestCase):
    def hero(self, mode='guest'):
        return dict(mode=mode, subcopy='Your match needs a result.',
                    primary_cta_url='/account/signup/', primary_cta_label='Create your account',
                    secondary_cta_url='/tournaments/?status=registration_open',
                    secondary_cta_label='Explore tournaments')

    def test_empty_catalog_does_not_invent_eleven_games_or_open_registration(self):
        ui = get_homepage_presentation({}, self.hero())
        self.assertEqual(ui['games_count'], 0)
        self.assertNotIn('11', ui['summary'])
        self.assertFalse(ui['has_open_registration'])
        self.assertEqual(ui['secondary_url'], '/tournaments/')
        self.assertNotEqual(ui['primary_url'], ui['secondary_url'])

    def test_live_events_do_not_imply_open_registration(self):
        ui = get_homepage_presentation({'games_count': 14, 'tournaments_live': 2}, self.hero())
        self.assertIn('registration currently closed', ui['status'])
        self.assertIn('14 games', ui['summary'])

    def test_open_registration_and_personalized_action_share_responsive_copy(self):
        ui = get_homepage_presentation({'games_count': 1, 'registration_open': 1}, self.hero('pending_action'))
        self.assertEqual(ui['status'], '1 tournament accepting entries')
        self.assertEqual(ui['summary'], 'Your match needs a result.')
        self.assertEqual(ui['games_label'], '1 supported game')

    def test_live_upcoming_closed_and_full_events_do_not_offer_registration(self):
        now = datetime(2026, 10, 18, tzinfo=timezone.utc)
        for status, deadline, full in [
            ('live', None, False), ('published', None, False),
            ('registration_open', now - timedelta(seconds=1), False),
            ('registration_open', now + timedelta(days=1), True),
        ]:
            with self.subTest(status=status, deadline=deadline, full=full):
                ui = tournament_presentation(status, deadline, now, full)
                self.assertFalse(ui['can_register'])
                self.assertEqual(ui['cta_label'], 'View tournament')

    def test_deadline_is_exclusive_and_missing_deadline_uses_event_status(self):
        now = datetime(2026, 10, 18, tzinfo=timezone.utc)
        self.assertFalse(tournament_presentation('registration_open', now, now)['can_register'])
        self.assertTrue(tournament_presentation('registration_open', None, now)['can_register'])
