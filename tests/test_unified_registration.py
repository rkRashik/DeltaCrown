# tests/test_unified_registration.py
"""
Test cases for the new unified tournament registration system.
"""
import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.apps import apps

from apps.tournaments.models import Tournament
from apps.user_profile.models import UserProfile

User = get_user_model()

Registration = apps.get_model("tournaments", "Registration")
Team = apps.get_model("organizations", "Team")
TeamMembership = apps.get_model("organizations", "TeamMembership")
TournamentRegistrationPolicy = apps.get_model("tournaments", "TournamentRegistrationPolicy")


class UnifiedRegistrationTestCase(TestCase):
    """Test the new unified registration flow."""
    
    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(
            username="testplayer",
            email="test@example.com",
            password="testpass123"
        )
        
        # Create user profile
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.user,
            defaults={"display_name": "Test Player"}
        )
        
        # Create test tournaments
        self.solo_tournament = Tournament.objects.create(
            name="Test Solo Tournament",
            slug="test-solo",
            game="efootball",
            entry_fee_bdt=100,
            slot_size=16
        )
        
        self.team_tournament = Tournament.objects.create(
            name="Test Team Tournament", 
            slug="test-team",
            game="valorant",
            entry_fee_bdt=500,
            slot_size=8
        )
        
        # Create registration policies
        TournamentRegistrationPolicy.objects.create(
            tournament=self.solo_tournament,
            mode="solo",
            team_size_min=1,
            team_size_max=1
        )
        
        TournamentRegistrationPolicy.objects.create(
            tournament=self.team_tournament,
            mode="team",
            team_size_min=5,
            team_size_max=5
        )
        
        self.client = Client()
    
    def test_authentication_required(self):
        """Test that unauthenticated users are redirected to login."""
        url = reverse("tournaments:unified_register", kwargs={"slug": "test-solo"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)
    
    def test_solo_tournament_registration_form(self):
        """Test that solo tournament shows correct form."""
        self.client.login(username="testplayer", password="testpass123")
        url = reverse("tournaments:unified_register", kwargs={"slug": "test-solo"})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Individual Tournament Registration")
        self.assertContains(response, "Complete the form below to register as an individual player")
        self.assertNotContains(response, "Team Tournament Registration")
    
    def test_team_tournament_registration_form_no_team(self):
        """Test team tournament form when user has no team."""
        self.client.login(username="testplayer", password="testpass123")
        url = reverse("tournaments:unified_register", kwargs={"slug": "test-team"})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team Tournament Registration")
        self.assertContains(response, "You don't have a team yet")
        self.assertContains(response, "Team Name")
        self.assertContains(response, "Save as permanent team")
    
    def test_team_tournament_with_existing_team(self):
        """Test team tournament when user is captain of existing team."""
        # Create a team with user as captain
        team = Team.objects.create(
            name="Test Team",
            tag="TST",
            captain=self.profile,
            game="valorant"
        )
        
        TeamMembership.objects.create(
            team=team,
            profile=self.profile,
            role="CAPTAIN",
            status="ACTIVE"
        )
        
        self.client.login(username="testplayer", password="testpass123")
        url = reverse("tournaments:unified_register", kwargs={"slug": "test-team"})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Team Tournament Registration")
        self.assertContains(response, 'Register your team "Test Team"')
        self.assertNotContains(response, "You don't have a team yet")
    
    def test_solo_registration_submission(self):
        """Test successful solo registration submission."""
        self.client.login(username="testplayer", password="testpass123")
        url = reverse("tournaments:unified_register", kwargs={"slug": "test-solo"})
        
        data = {
            "display_name": "Test Player",
            "phone": "01712345678",
            "email": "test@example.com",
            "payment_method": "bkash",
            "payment_reference": "ABC123456789",
            "payer_account_number": "01712345678",
            "agree_rules": "on"
        }
        
        response = self.client.post(url, data)
        
        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)
        
        # Check registration was created
        registration = Registration.objects.filter(
            tournament=self.solo_tournament,
            user=self.profile
        ).first()
        
        self.assertIsNotNone(registration)
        self.assertEqual(registration.payment_method, "bkash")
        self.assertEqual(registration.payment_reference, "ABC123456789")
    
    def test_team_creation_during_registration(self):
        """Test creating a new team during tournament registration."""
        self.client.login(username="testplayer", password="testpass123")
        url = reverse("tournaments:unified_register", kwargs={"slug": "test-team"})
        
        data = {
            "display_name": "Test Player",
            "phone": "01712345678", 
            "email": "test@example.com",
            "team_name": "New Test Team",
            "save_as_team": "1",
            "payment_method": "nagad",
            "payment_reference": "DEF987654321",
            "payer_account_number": "01712345678",
            "agree_rules": "on"
        }
        
        response = self.client.post(url, data)
        
        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)
        
        # Check team was created
        team = Team.objects.filter(name="New Test Team").first()
        self.assertIsNotNone(team)
        self.assertEqual(team.captain, self.profile)
        
        # Check membership was created
        membership = TeamMembership.objects.filter(
            team=team,
            profile=self.profile,
            role="CAPTAIN"
        ).first()
        self.assertIsNotNone(membership)
        
        # Check registration was created
        registration = Registration.objects.filter(
            tournament=self.team_tournament,
            team=team
        ).first()
        self.assertIsNotNone(registration)
    
    def test_already_registered_status(self):
        """Test showing already registered status."""
        # Create existing registration
        Registration.objects.create(
            tournament=self.solo_tournament,
            user=self.profile,
            status="PENDING"
        )
        
        self.client.login(username="testplayer", password="testpass123")
        url = reverse("tournaments:unified_register", kwargs={"slug": "test-solo"})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Already Registered!")
        self.assertContains(response, "Back to Tournament")
    
    def test_payment_validation(self):
        """Test payment field validation for paid tournaments."""
        self.client.login(username="testplayer", password="testpass123")
        url = reverse("tournaments:unified_register", kwargs={"slug": "test-solo"})
        
        # Submit without payment info
        data = {
            "display_name": "Test Player",
            "phone": "01712345678",
            "email": "test@example.com",
            "agree_rules": "on"
        }
        
        response = self.client.post(url, data)
        
        # Should show error message
        messages = list(response.context["messages"])
        self.assertTrue(any("Payment method and transaction reference are required" in str(m) for m in messages))
    
    def test_free_tournament_no_payment_required(self):
        """Test registration for free tournaments doesn't require payment."""
        # Create free tournament
        free_tournament = Tournament.objects.create(
            name="Free Tournament",
            slug="free-test", 
            game="efootball",
            entry_fee_bdt=0,
            slot_size=32
        )
        
        TournamentRegistrationPolicy.objects.create(
            tournament=free_tournament,
            mode="solo"
        )
        
        self.client.login(username="testplayer", password="testpass123")
        url = reverse("tournaments:unified_register", kwargs={"slug": "free-test"})
        
        data = {
            "display_name": "Test Player",
            "phone": "01712345678",
            "email": "test@example.com",
            "agree_rules": "on"
        }
        
        response = self.client.post(url, data)
        
        # Should redirect successfully without payment info
        self.assertEqual(response.status_code, 302)
        
        # Check registration was created
        registration = Registration.objects.filter(
            tournament=free_tournament,
            user=self.profile
        ).first()
        self.assertIsNotNone(registration)


if __name__ == "__main__":
    pytest.main([__file__])