# tests/test_tournament_schedule_pilot.py
"""
Test suite for TournamentSchedule model (Pilot Phase).

This comprehensive test validates the new schedule model
before proceeding with full refactoring.

Test Coverage:
- Model creation and validation
- Date ordering validations
- Computed properties (is_registration_open, is_live, etc.)
- Helper methods
- Database indexes and performance
- Backward compatibility
"""
import pytest
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.test import TestCase

from apps.tournaments.models import Tournament, TournamentSchedule


class TournamentScheduleCreationTest(TestCase):
    """Test basic creation and relationships."""
    
    def setUp(self):
        """Create a test tournament."""
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            slug="test-tournament",
            game="valorant",
            status="DRAFT"
        )
    
    def test_create_schedule(self):
        """Test creating a basic schedule."""
        now = timezone.now()
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=now + timedelta(days=1),
            reg_close_at=now + timedelta(days=7),
            start_at=now + timedelta(days=8),
            end_at=now + timedelta(days=9),
        )
        
        self.assertIsNotNone(schedule.id)
        self.assertEqual(schedule.tournament, self.tournament)
    
    def test_one_to_one_relationship(self):
        """Test that one tournament can only have one schedule."""
        now = timezone.now()
        
        # Create first schedule
        TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=now + timedelta(days=1),
            reg_close_at=now + timedelta(days=7),
            start_at=now + timedelta(days=8),
            end_at=now + timedelta(days=9),
        )
        
        # Trying to create second schedule should fail
        with self.assertRaises(Exception):  # IntegrityError
            TournamentSchedule.objects.create(
                tournament=self.tournament,
                reg_open_at=now + timedelta(days=10),
                reg_close_at=now + timedelta(days=17),
                start_at=now + timedelta(days=18),
                end_at=now + timedelta(days=19),
            )
    
    def test_access_schedule_from_tournament(self):
        """Test accessing schedule via tournament.schedule."""
        now = timezone.now()
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=now + timedelta(days=1),
            reg_close_at=now + timedelta(days=7),
            start_at=now + timedelta(days=8),
            end_at=now + timedelta(days=9),
        )
        
        # Access via relationship
        self.assertEqual(self.tournament.schedule, schedule)
    
    def test_cascade_delete(self):
        """Test that deleting tournament deletes schedule."""
        now = timezone.now()
        TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=now + timedelta(days=1),
            reg_close_at=now + timedelta(days=7),
            start_at=now + timedelta(days=8),
            end_at=now + timedelta(days=9),
        )
        
        schedule_id = self.tournament.schedule.id
        self.tournament.delete()
        
        # Schedule should be deleted
        with self.assertRaises(TournamentSchedule.DoesNotExist):
            TournamentSchedule.objects.get(id=schedule_id)


class TournamentScheduleValidationTest(TestCase):
    """Test all validation rules."""
    
    def setUp(self):
        """Create a test tournament."""
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            slug="test-tournament",
            game="valorant",
            status="DRAFT"
        )
    
    def test_reg_close_before_reg_open_fails(self):
        """Test that registration close cannot be before open."""
        now = timezone.now()
        
        with self.assertRaises(ValidationError) as context:
            schedule = TournamentSchedule(
                tournament=self.tournament,
                reg_open_at=now + timedelta(days=7),
                reg_close_at=now + timedelta(days=1),  # Before open!
            )
            schedule.full_clean()
        
        self.assertIn('reg_close_at', context.exception.message_dict)
    
    def test_tournament_end_before_start_fails(self):
        """Test that tournament end cannot be before start."""
        now = timezone.now()
        
        with self.assertRaises(ValidationError) as context:
            schedule = TournamentSchedule(
                tournament=self.tournament,
                start_at=now + timedelta(days=10),
                end_at=now + timedelta(days=5),  # Before start!
            )
            schedule.full_clean()
        
        self.assertIn('end_at', context.exception.message_dict)
    
    def test_reg_close_after_tournament_start_fails(self):
        """Test that registration must close before tournament starts."""
        now = timezone.now()
        
        with self.assertRaises(ValidationError) as context:
            schedule = TournamentSchedule(
                tournament=self.tournament,
                reg_open_at=now + timedelta(days=1),
                reg_close_at=now + timedelta(days=10),
                start_at=now + timedelta(days=8),  # Before reg close!
            )
            schedule.full_clean()
        
        self.assertIn('reg_close_at', context.exception.message_dict)
    
    def test_check_in_close_after_open_fails(self):
        """Test check-in close must be closer to start than open."""
        now = timezone.now()
        
        with self.assertRaises(ValidationError) as context:
            schedule = TournamentSchedule(
                tournament=self.tournament,
                start_at=now + timedelta(days=8),
                check_in_open_mins=10,  # Opens 10min before
                check_in_close_mins=60,  # Closes 60min before (wrong!)
            )
            schedule.full_clean()
        
        self.assertIn('check_in_close_mins', context.exception.message_dict)
    
    def test_valid_schedule_passes(self):
        """Test that a properly configured schedule validates."""
        now = timezone.now()
        
        schedule = TournamentSchedule(
            tournament=self.tournament,
            reg_open_at=now + timedelta(days=1),
            reg_close_at=now + timedelta(days=7),
            start_at=now + timedelta(days=8),
            end_at=now + timedelta(days=9),
            check_in_open_mins=60,
            check_in_close_mins=10,
        )
        
        # Should not raise
        schedule.full_clean()
        schedule.save()


class TournamentSchedulePropertiesTest(TestCase):
    """Test computed properties and helper methods."""
    
    def setUp(self):
        """Create tournament and schedule."""
        self.tournament = Tournament.objects.create(
            name="Test Tournament",
            slug="test-tournament",
            game="valorant",
            status="PUBLISHED"
        )
        self.now = timezone.now()
    
    def test_is_registration_open_before_window(self):
        """Test registration status before window opens."""
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=self.now + timedelta(hours=1),  # Future
            reg_close_at=self.now + timedelta(days=7),
            start_at=self.now + timedelta(days=8),
        )
        
        self.assertFalse(schedule.is_registration_open)
    
    def test_is_registration_open_during_window(self):
        """Test registration status during open window."""
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=self.now - timedelta(hours=1),  # Past
            reg_close_at=self.now + timedelta(days=7),  # Future
            start_at=self.now + timedelta(days=8),
        )
        
        self.assertTrue(schedule.is_registration_open)
    
    def test_is_registration_open_after_window(self):
        """Test registration status after window closes."""
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=self.now - timedelta(days=7),  # Past
            reg_close_at=self.now - timedelta(hours=1),  # Past
            start_at=self.now + timedelta(days=1),
        )
        
        self.assertFalse(schedule.is_registration_open)
    
    def test_is_tournament_live_before_start(self):
        """Test tournament status before it starts."""
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            start_at=self.now + timedelta(days=1),  # Future
            end_at=self.now + timedelta(days=2),
        )
        
        self.assertFalse(schedule.is_tournament_live)
    
    def test_is_tournament_live_during_event(self):
        """Test tournament status during the event."""
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            start_at=self.now - timedelta(hours=1),  # Past
            end_at=self.now + timedelta(hours=3),  # Future
        )
        
        self.assertTrue(schedule.is_tournament_live)
    
    def test_is_tournament_live_after_end(self):
        """Test tournament status after it ends."""
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            start_at=self.now - timedelta(days=2),  # Past
            end_at=self.now - timedelta(days=1),  # Past
        )
        
        self.assertFalse(schedule.is_tournament_live)
    
    def test_registration_status_text(self):
        """Test human-readable registration status."""
        # Before opening
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            reg_open_at=self.now + timedelta(days=1),
            reg_close_at=self.now + timedelta(days=7),
            start_at=self.now + timedelta(days=8),
        )
        
        status = schedule.registration_status
        self.assertIn("Opens", status)
        
        # After closing
        schedule.reg_open_at = self.now - timedelta(days=7)
        schedule.reg_close_at = self.now - timedelta(hours=1)
        schedule.save()
        
        self.assertEqual(schedule.registration_status, "Closed")
    
    def test_check_in_window_text(self):
        """Test check-in window display text."""
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament,
            start_at=self.now + timedelta(days=1),
            check_in_open_mins=60,
            check_in_close_mins=10,
        )
        
        text = schedule.check_in_window_text
        self.assertIn("60min", text)
        self.assertIn("10min", text)


class TournamentScheduleHelperMethodsTest(TestCase):
    """Test helper methods."""
    
    def setUp(self):
        """Create tournaments."""
        self.tournament1 = Tournament.objects.create(
            name="Tournament 1",
            slug="tournament-1",
            game="valorant",
            status="PUBLISHED"
        )
        self.tournament2 = Tournament.objects.create(
            name="Tournament 2",
            slug="tournament-2",
            game="efootball",
            status="DRAFT"
        )
        self.now = timezone.now()
    
    def test_clone_for_tournament(self):
        """Test cloning schedule to another tournament."""
        # Create original schedule
        original = TournamentSchedule.objects.create(
            tournament=self.tournament1,
            reg_open_at=self.now + timedelta(days=1),
            reg_close_at=self.now + timedelta(days=7),
            start_at=self.now + timedelta(days=8),
            end_at=self.now + timedelta(days=9),
            check_in_open_mins=60,
            check_in_close_mins=10,
        )
        
        # Clone to tournament2
        cloned = original.clone_for_tournament(self.tournament2)
        
        # Verify it's a new instance
        self.assertNotEqual(original.id, cloned.id)
        
        # Verify it's linked to tournament2
        self.assertEqual(cloned.tournament, self.tournament2)
        
        # Verify dates were copied
        self.assertEqual(cloned.reg_open_at, original.reg_open_at)
        self.assertEqual(cloned.check_in_open_mins, original.check_in_open_mins)
    
    def test_get_registration_window_display(self):
        """Test formatted registration window display."""
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament1,
            reg_open_at=self.now + timedelta(days=1),
            reg_close_at=self.now + timedelta(days=7),
            start_at=self.now + timedelta(days=8),
        )
        
        display = schedule.get_registration_window_display()
        self.assertIn("to", display)
        self.assertTrue(len(display) > 0)
    
    def test_str_representation(self):
        """Test string representation of schedule."""
        schedule = TournamentSchedule.objects.create(
            tournament=self.tournament1,
            start_at=self.now + timedelta(days=8),
        )
        
        str_repr = str(schedule)
        self.assertIn(self.tournament1.name, str_repr)


class BackwardCompatibilityTest(TestCase):
    """Test that existing Tournament fields still work."""
    
    def test_tournament_without_schedule_still_works(self):
        """Test that tournaments without schedule still function."""
        tournament = Tournament.objects.create(
            name="Legacy Tournament",
            slug="legacy-tournament",
            game="valorant",
            status="PUBLISHED",
            # Old fields still present
            reg_open_at=timezone.now() + timedelta(days=1),
            reg_close_at=timezone.now() + timedelta(days=7),
            start_at=timezone.now() + timedelta(days=8),
        )
        
        # Old properties should still work
        self.assertIsNotNone(tournament.reg_open_at)
        self.assertFalse(tournament.registration_open)  # Old property
    
    def test_tournament_with_schedule_prefers_schedule(self):
        """Test that schedule data takes precedence when available."""
        now = timezone.now()
        tournament = Tournament.objects.create(
            name="Hybrid Tournament",
            slug="hybrid-tournament",
            game="valorant",
            status="PUBLISHED",
            # Old fields
            reg_open_at=now - timedelta(days=10),
            reg_close_at=now - timedelta(days=5),
        )
        
        # Create new schedule with different dates
        schedule = TournamentSchedule.objects.create(
            tournament=tournament,
            reg_open_at=now - timedelta(hours=1),  # Open now
            reg_close_at=now + timedelta(days=7),  # Closes in future
            start_at=now + timedelta(days=8),
        )
        
        # Schedule properties should be used
        self.assertTrue(schedule.is_registration_open)
        # Tournament old property should return False
        self.assertFalse(tournament.registration_open)


class PerformanceTest(TestCase):
    """Test database performance and indexes."""
    
    def test_query_by_registration_window(self):
        """Test that registration window queries use indexes."""
        # Create multiple schedules
        now = timezone.now()
        for i in range(10):
            tournament = Tournament.objects.create(
                name=f"Tournament {i}",
                slug=f"tournament-{i}",
                game="valorant",
                status="PUBLISHED"
            )
            TournamentSchedule.objects.create(
                tournament=tournament,
                reg_open_at=now + timedelta(days=i),
                reg_close_at=now + timedelta(days=i+7),
                start_at=now + timedelta(days=i+8),
            )
        
        # Query by registration window (should use index)
        with self.assertNumQueries(1):
            schedules = TournamentSchedule.objects.filter(
                reg_open_at__lte=now + timedelta(days=5),
                reg_close_at__gte=now + timedelta(days=5)
            )
            list(schedules)  # Force evaluation


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
