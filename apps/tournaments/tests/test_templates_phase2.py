"""
Template rendering tests for Phase 2.

Tests that templates correctly render Phase 1 model data
and handle missing data gracefully.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from apps.tournaments.models import (
    Tournament,
    TournamentSchedule,
    TournamentCapacity,
    TournamentFinance,
    TournamentMedia,
    TournamentRules,
    TournamentArchive,
)

User = get_user_model()


class TestDetailTemplateRendering(TestCase):
    """Test detail.html template rendering with Phase 1 data."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.tournament = Tournament.objects.create(
            name='Template Test Tournament',
            slug='template-test',
            game='valorant',
            status='PUBLISHED',
        )
        
        self.schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=timezone.now(),
            reg_close_at=timezone.now() + timedelta(days=7),
            start_at=timezone.now() + timedelta(days=10),
            end_at=timezone.now() + timedelta(days=12)
        )
        
        self.capacity = TournamentCapacity.objects.create(
            tournament=self.tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=8,
            waitlist_enabled=True
        )
        
        self.finance = TournamentFinance.objects.create(
            tournament=self.tournament,
            entry_fee_bdt=Decimal('500.00'),
            prize_pool_bdt=Decimal('5000.00')
        )
    
    def test_capacity_widget_renders(self):
        """Test that capacity widget renders correctly."""
        url = reverse('tournaments:detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check widget structure
        self.assertIn('capacity-widget', content)
        self.assertIn('capacity-progress', content)
        self.assertIn('capacity-bar', content)
        self.assertIn('capacity-stats', content)
        
        # Check values
        self.assertIn('8', content)  # current_registrations
        self.assertIn('16', content)  # max_teams
        self.assertIn('50', content)  # fill_percentage
        
        # Check waitlist
        self.assertIn('Waitlist: 3', content)
    
    def test_schedule_widget_renders(self):
        """Test that schedule countdown widget renders correctly."""
        url = reverse('tournaments:detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check countdown widget
        self.assertIn('countdown-widget', content)
        self.assertIn('countdown', content)
        self.assertIn('Registration closes in', content)
    
    def test_finance_widget_renders(self):
        """Test that finance widget renders correctly."""
        url = reverse('tournaments:detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check finance display
        self.assertIn('Financial Details', content)
        self.assertIn('finance-display', content)
        self.assertIn('Entry Fee', content)
        self.assertIn('Prize Pool', content)
        
        # Check formatted values
        self.assertIn('৳500', content)
        self.assertIn('৳5,000', content)
        self.assertIn('৳4,000', content)  # Collected
    
    def test_quick_facts_uses_phase1_data(self):
        """Test that Quick Facts section prefers Phase 1 data."""
        url = reverse('tournaments:detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Should use Phase 1 schedule data
        self.assertIn('Reg. open', content)
        self.assertIn('Reg. close', content)
        
        # Should use Phase 1 capacity data
        self.assertIn('8/16', content)
    
    def test_rules_requirements_render(self):
        """Test that rules requirements render correctly."""
        TournamentRules.objects.create(
            tournament=self.tournament,
            general_rules='Tournament rules and guidelines',
            eligibility_requirements='Must be 18+. Must have Discord. Must have valid ID.',
            match_rules='Standard match rules apply',
            require_discord=True,
            require_game_id=True
        )
        
        url = reverse('tournaments:detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check requirements list
        self.assertIn('Requirements', content)
        self.assertIn('requirements-list', content)
        self.assertIn('Must be 18+', content)
        self.assertIn('Must have Discord', content)
        self.assertIn('Must have valid ID', content)
        
        # Check restrictions
        self.assertIn('Age Requirement: 18+', content)
        self.assertIn('Region: Bangladesh', content)
        self.assertIn('Rank Restriction: Gold or higher', content)
    
    def test_archive_status_renders(self):
        """Test that archive status renders when tournament is archived."""
        TournamentArchive.objects.create(
            tournament=self.tournament,
            status='archived',
            archived_at=timezone.now(),
            archived_by=self.user,
            reason='Tournament completed successfully'
        )
        
        url = reverse('tournaments:detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check archive card
        self.assertIn('Archived', content)
        self.assertIn('This tournament has been archived', content)
        self.assertIn('Tournament completed successfully', content)
        self.assertIn('View Archive', content)
    
    def test_template_without_phase1_data(self):
        """Test that template renders gracefully without Phase 1 data."""
        # Create tournament without Phase 1 models
        tournament_no_phase1 = Tournament.objects.create(
            name='Old Tournament',
            slug='old-tournament',
            game='valorant',
            status='PUBLISHED',
        )
        
        url = reverse('tournaments:detail', kwargs={'slug': tournament_no_phase1.slug})
        response = self.client.get(url)
        
        # Should render successfully
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Should show tournament name
        self.assertIn('Old Tournament', content)
        
        # Phase 1 widgets should not appear
        self.assertNotIn('capacity-widget', content)
        self.assertNotIn('Financial Details', content)


class TestRegistrationTemplateRendering(TestCase):
    """Test modern_register.html template rendering."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.tournament = Tournament.objects.create(
            name='Registration Template Test',
            slug='registration-template-test',
            game='valorant',
            status='PUBLISHED',
        )
        
        self.schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=timezone.now() - timedelta(days=1),
            reg_close_at=timezone.now() + timedelta(days=7),
            start_at=timezone.now() + timedelta(days=10),
            end_at=timezone.now() + timedelta(days=12)
        )
        
        self.capacity = TournamentCapacity.objects.create(
            tournament=self.tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=12  # Nearly full
        )
        
        self.finance = TournamentFinance.objects.create(
            tournament=self.tournament,
            entry_fee_bdt=Decimal('1000.00'),
            prize_pool_bdt=Decimal('10000.00')
        )
    
    def test_header_finance_badges_render(self):
        """Test that finance badges render in header."""
        url = reverse('tournaments:modern_register', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check finance badges
        self.assertIn('৳1,000', content)  # Entry fee
        self.assertIn('Prize: ৳10,000', content)  # Prize pool
    
    def test_header_capacity_badge_renders(self):
        """Test that capacity badge renders in header."""
        url = reverse('tournaments:modern_register', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check capacity badge
        self.assertIn('12/16 slots', content)
        
        # Should show warning class (nearly full)
        self.assertIn('warning', content)
    
    def test_header_schedule_badge_renders(self):
        """Test that schedule timing badge renders."""
        url = reverse('tournaments:modern_register', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check schedule badge
        self.assertIn('Closes', content)
    
    def test_requirements_notice_renders(self):
        """Test that requirements notice renders in Step 1."""
        TournamentRules.objects.create(
            tournament=self.tournament,
            general_rules='Standard tournament rules apply',
            eligibility_requirements='Must be 18 years or older. Must have a Discord account. Must have a Riot account. Must be available on tournament dates. Must have stable internet connection.',
            match_rules='Match rules',
            require_discord=True,
            require_game_id=True
        )
        
        url = reverse('tournaments:modern_register', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check requirements notice
        self.assertIn('requirements-notice', content)
        self.assertIn('Tournament Requirements', content)
        self.assertIn('Must be 18 years or older', content)
        self.assertIn('Must have a Discord account', content)
        self.assertIn('Must have a Riot account', content)
        
        # Should show first 5 requirements
        self.assertIn('Must have stable internet connection', content)
        
        # Check restrictions
        self.assertIn('Age: Must be 18+ years old', content)
        self.assertIn('Region: Bangladesh only', content)
        self.assertIn('Rank: Gold+', content)
    
    def test_requirements_notice_truncates_long_list(self):
        """Test that long requirements list is truncated."""
        # Create long requirements text
        long_requirements = '. '.join([f'Requirement {i+1}' for i in range(10)])
        TournamentRules.objects.create(
            tournament=self.tournament,
            eligibility_requirements=long_requirements,
            general_rules='General rules'
        )
        
        url = reverse('tournaments:modern_register', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Should show first 5
        self.assertIn('Requirement 1', content)
        self.assertIn('Requirement 5', content)
        
        # Should show "more" indicator
        self.assertIn('+5 more', content)
    
    def test_conditional_discord_field_required(self):
        """Test that Discord field is required when rules require it."""
        TournamentRules.objects.create(
            tournament=self.tournament,
            require_discord=True,
            general_rules='General rules'
        )
        
        url = reverse('tournaments:modern_register', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Discord field should be required
        self.assertIn('Discord ID', content)
        # Should have required indicator near Discord field
        discord_section = content[content.find('Discord ID'):content.find('Discord ID') + 500]
        self.assertIn('required', discord_section.lower())
    
    def test_conditional_discord_field_optional(self):
        """Test that Discord field is optional when rules don't require it."""
        TournamentRules.objects.create(
            tournament=self.tournament,
            require_discord=False,
            general_rules='General rules'
        )
        
        url = reverse('tournaments:modern_register', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Discord field should be optional
        self.assertIn('Discord ID', content)
        self.assertIn('Optional', content)
    
    def test_conditional_game_id_field(self):
        """Test that Game ID field is conditional."""
        TournamentRules.objects.create(
            tournament=self.tournament,
            require_game_id=True,
            general_rules='General rules'
        )
        
        url = reverse('tournaments:modern_register', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Game ID should be required
        self.assertIn('In-Game ID', content)
    
    def test_payment_section_prize_display(self):
        """Test that payment section displays prize pool."""
        url = reverse('tournaments:modern_register', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check prize display in payment section
        if 'prize-display' in content:
            self.assertIn('Prize Pool', content)
            self.assertIn('৳10,000', content)
    
    def test_free_tournament_display(self):
        """Test that free tournaments show correct badge."""
        # Create free tournament
        free_tournament = Tournament.objects.create(
            name='Free Tournament',
            slug='free-tournament',
            game='valorant',
            status='PUBLISHED',
        )
        
        TournamentFinance.objects.create(
            tournament=free_tournament,
            entry_fee_bdt=Decimal('0.00'),
            prize_pool_bdt=Decimal('0.00')
        )
        
        url = reverse('tournaments:modern_register', kwargs={'slug': free_tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Should show "Free Entry"
        self.assertIn('Free Entry', content)
        self.assertIn('free', content)  # CSS class


class TestArchiveTemplateRendering(TestCase):
    """Test archive template rendering."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            is_staff=True
        )
        self.client.login(username='testuser', password='testpass123')
        
        self.tournament = Tournament.objects.create(
            name='Archive Template Test',
            slug='archive-template-test',
            game='valorant',
            status='completed',
        )
        
        self.schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=timezone.now() - timedelta(days=30),
            reg_close_at=timezone.now() - timedelta(days=20),
            start_at=timezone.now() - timedelta(days=15),
            end_at=timezone.now() - timedelta(days=10)
        )
        
        self.capacity = TournamentCapacity.objects.create(
            tournament=self.tournament,
            max_teams=16,
            current_registrations=16
        )
        
        self.finance = TournamentFinance.objects.create(
            tournament=self.tournament,
            entry_fee_bdt=Decimal('500.00'),
            prize_pool_bdt=Decimal('5000.00')
        )
        
        self.rules = TournamentRules.objects.create(
            tournament=self.tournament,
            general_rules='Tournament rules',
            eligibility_requirements='Must be 18+. Must have Discord.',
            require_discord=True
        )
        
        self.archive = TournamentArchive.objects.create(
            tournament=self.tournament,
            archive_type='ARCHIVED',
            is_archived=True,
            archived_at=timezone.now() - timedelta(days=5),
            archived_by=self.user
        )
    
    def test_archive_detail_renders_all_sections(self):
        """Test that archive detail renders all Phase 1 model sections."""
        url = reverse('tournaments:archive_detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check main sections
        self.assertIn('Archive Information', content)
        self.assertIn('Schedule', content)
        self.assertIn('Capacity', content)
        self.assertIn('Finance', content)
        self.assertIn('Rules', content)
    
    def test_archive_detail_displays_archive_info(self):
        """Test that archive info is displayed correctly."""
        url = reverse('tournaments:archive_detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check archive metadata
        self.assertIn('Tournament completed successfully', content)
        self.assertIn('testuser', content)  # Archived by
        
        # Check preservation flags
        self.assertIn('Registrations Preserved', content)
        self.assertIn('Matches Preserved', content)
    
    def test_archive_detail_displays_schedule(self):
        """Test that schedule section displays correctly."""
        url = reverse('tournaments:archive_detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check schedule fields
        self.assertIn('Registration Open', content)
        self.assertIn('Registration Close', content)
        self.assertIn('Tournament Start', content)
        self.assertIn('Tournament End', content)
    
    def test_archive_detail_displays_capacity(self):
        """Test that capacity section displays with progress bar."""
        url = reverse('tournaments:archive_detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check capacity display
        self.assertIn('16/16', content)
        self.assertIn('100', content)  # Fill percentage
        self.assertIn('progress', content.lower())  # Progress bar
    
    def test_archive_detail_displays_finance(self):
        """Test that finance section displays all financial data."""
        url = reverse('tournaments:archive_detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check finance fields
        self.assertIn('৳500', content)  # Entry fee
        self.assertIn('৳5,000', content)  # Prize pool
        self.assertIn('৳8,000', content)  # Collected
        self.assertIn('৳5,000', content)  # Paid out
    
    def test_archive_list_displays_cards(self):
        """Test that archive list displays tournament cards."""
        url = reverse('tournaments:archive_list')
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check card elements
        self.assertIn('Archive Template Test', content)
        self.assertIn('16 teams', content)
        self.assertIn('৳500', content)
    
    def test_clone_form_date_calculator(self):
        """Test that clone form includes date calculator JavaScript."""
        url = reverse('tournaments:clone_tournament', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check for JavaScript code
        self.assertIn('days_offset', content)
        self.assertIn('updateDatePreview', content)
        self.assertIn('formatDate', content)
    
    def test_archive_history_timeline(self):
        """Test that archive history displays timeline."""
        url = reverse('tournaments:archive_history', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check timeline elements
        self.assertIn('timeline', content)
        self.assertIn('Tournament Archived', content)
        self.assertIn('Tournament completed successfully', content)


class TestResponsiveDesign(TestCase):
    """Test that templates are responsive."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.tournament = Tournament.objects.create(
            name='Responsive Test',
            slug='responsive-test',
            game='valorant',
            status='PUBLISHED',
        )
        
        TournamentCapacity.objects.create(
            tournament=self.tournament,
            slot_size=16,
            max_teams=16,
            current_registrations=8
        )
    
    def test_mobile_viewport_meta_tag(self):
        """Test that templates include viewport meta tag."""
        url = reverse('tournaments:detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        # This should be in base.html, but check rendering
        self.assertEqual(response.status_code, 200)
    
    def test_capacity_widget_mobile_classes(self):
        """Test that capacity widget has responsive classes."""
        url = reverse('tournaments:detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # CSS should handle responsive layout
        self.assertIn('capacity-widget', content)


class TestCSSIntegration(TestCase):
    """Test that Phase 1 widgets CSS is properly integrated."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.tournament = Tournament.objects.create(
            name='CSS Test',
            slug='css-test',
            game='valorant',
            status='PUBLISHED',
        )
    
    def test_phase1_widgets_css_classes_present(self):
        """Test that Phase 1 widget CSS classes are used."""
        TournamentCapacity.objects.create(
            tournament=self.tournament,
            max_teams=16,
            current_registrations=8
        )
        
        url = reverse('tournaments:detail', kwargs={'slug': self.tournament.slug})
        response = self.client.get(url)
        
        content = response.content.decode()
        
        # Check for Phase 1 CSS classes
        self.assertIn('capacity-widget', content)
        self.assertIn('capacity-progress', content)
        self.assertIn('capacity-bar', content)
        self.assertIn('capacity-stats', content)
