from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.user_profile.models import UserProfile
from apps.economy.models import DeltaCrownWallet

User = get_user_model()


class PublicProfileViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='rkrashik', email='rkrashik@example.com', password='pass123')
        # Ensure profile exists (some signals may auto-create it)
        profile, created = UserProfile.objects.get_or_create(user=self.user)
        if created or profile.display_name != 'Rashik':
            profile.display_name = 'Rashik'
            profile.save(update_fields=['display_name'])
        # Create wallet
        wallet, _ = DeltaCrownWallet.objects.get_or_create(profile=profile)
        wallet.cached_balance = 100
        wallet.save()

    def test_public_profile_anonymous(self):
        # Anonymous should be able to view public profile
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # is_own_profile should be False for anonymous
        self.assertIn('is_own_profile', response.context)
        self.assertFalse(response.context['is_own_profile'])
        # wallet should not be visible to anonymous
        self.assertIn('wallet', response.context)
        self.assertIsNone(response.context['wallet'])

    def test_public_profile_owner(self):
        # Login as the owner
        login_ok = self.client.login(username=self.user.username, password='pass123')
        self.assertTrue(login_ok)
        url = reverse('user_profile:public_profile', kwargs={'username': self.user.username})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_own_profile'])
        # wallet should be present and have the balance
        self.assertIn('wallet', response.context)
        wallet = response.context['wallet']
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.cached_balance, 100)

    def test_named_routes_and_reverses(self):
        # Verify that the economy and browse routes do reverse correctly
        from django.urls import reverse
        deposit = reverse('economy:deposit')
        withdraw = reverse('economy:withdraw')
        transactions = reverse('economy:transaction_history')
        self.assertTrue(deposit)
        self.assertTrue(withdraw)
        self.assertTrue(transactions)
        # Browse routes
        t_browse = reverse('tournaments:browse')
        team_browse = reverse('teams:browse')
        self.assertTrue(t_browse)
        self.assertTrue(team_browse)

