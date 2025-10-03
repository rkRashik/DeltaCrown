# apps/tournaments/models/core/tournament_schedule.py
"""
TournamentSchedule Model - Pilot Phase
Separates all schedule/timing concerns from the main Tournament model.

This is Phase 1 (Pilot) of the tournament system refactoring.
Goal: Validate the approach before proceeding with other models.
"""
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class TournamentSchedule(models.Model):
    """
    Manages all schedule and timing aspects of a tournament.
    
    Replaces these fields from Tournament model:
    - reg_open_at (registration window start)
    - reg_close_at (registration window end)
    - start_at (tournament start time)
    - end_at (tournament end time)
    
    Additionally adds:
    - check_in_open_mins (minutes before start for check-in)
    - check_in_close_mins (minutes before start to close check-in)
    
    Design decisions:
    - OneToOneField maintains simple lookups (tournament.schedule)
    - All datetime fields use timezone-aware DateTimeField
    - Validation ensures logical date ordering
    - Related name 'schedule' for intuitive access
    """
    
    # Link to main tournament (one schedule per tournament)
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='schedule',
        help_text="Tournament this schedule belongs to"
    )
    
    # ===== Registration Window =====
    reg_open_at = models.DateTimeField(
        verbose_name="Registration Opens At",
        help_text="When participants can start registering",
        null=True,
        blank=True
    )
    
    reg_close_at = models.DateTimeField(
        verbose_name="Registration Closes At",
        help_text="When registration deadline ends",
        null=True,
        blank=True
    )
    
    # ===== Tournament Window =====
    start_at = models.DateTimeField(
        verbose_name="Tournament Starts At",
        help_text="When matches begin",
        null=True,
        blank=True
    )
    
    end_at = models.DateTimeField(
        verbose_name="Tournament Ends At",
        help_text="Expected tournament completion time",
        null=True,
        blank=True
    )
    
    # ===== Check-in Window =====
    check_in_open_mins = models.PositiveIntegerField(
        verbose_name="Check-in Opens (minutes before start)",
        help_text="How many minutes before tournament start should check-in open",
        default=60,
        null=True,
        blank=True
    )
    
    check_in_close_mins = models.PositiveIntegerField(
        verbose_name="Check-in Closes (minutes before start)",
        help_text="How many minutes before tournament start should check-in close",
        default=10,
        null=True,
        blank=True
    )
    
    # ===== Metadata =====
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournaments_schedule'
        verbose_name = 'Tournament Schedule'
        verbose_name_plural = 'Tournament Schedules'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reg_open_at', 'reg_close_at'], name='idx_reg_window'),
            models.Index(fields=['start_at', 'end_at'], name='idx_tournament_window'),
        ]
    
    def __str__(self):
        if self.start_at:
            return f"Schedule for {self.tournament.name} (starts {self.start_at.strftime('%Y-%m-%d %H:%M')})"
        return f"Schedule for {self.tournament.name}"
    
    def clean(self):
        """
        Comprehensive validation of all schedule dates.
        Ensures logical ordering and prevents invalid configurations.
        """
        errors = {}
        
        # Validate registration window
        if self.reg_open_at and self.reg_close_at:
            if self.reg_open_at >= self.reg_close_at:
                errors['reg_close_at'] = 'Registration close time must be after open time.'
        
        # Validate tournament window
        if self.start_at and self.end_at:
            if self.start_at >= self.end_at:
                errors['end_at'] = 'Tournament end time must be after start time.'
        
        # Validate registration closes before tournament starts
        if self.reg_close_at and self.start_at:
            if self.reg_close_at > self.start_at:
                errors['reg_close_at'] = 'Registration must close before tournament starts.'
        
        # Validate check-in window makes sense
        if self.check_in_open_mins and self.check_in_close_mins:
            if self.check_in_open_mins <= self.check_in_close_mins:
                errors['check_in_close_mins'] = (
                    'Check-in must close closer to start time than it opens. '
                    f'Open: {self.check_in_open_mins}min, Close: {self.check_in_close_mins}min'
                )
        
        if errors:
            raise ValidationError(errors)
    
    def save(self, *args, **kwargs):
        """Run validation before saving."""
        self.full_clean()
        super().save(*args, **kwargs)
    
    # ===== Computed Properties =====
    
    @property
    def is_registration_open(self) -> bool:
        """Check if registration is currently accepting participants."""
        if not self.reg_open_at or not self.reg_close_at:
            return False
        now = timezone.now()
        return self.reg_open_at <= now <= self.reg_close_at
    
    @property
    def is_tournament_live(self) -> bool:
        """Check if tournament is currently running."""
        if not self.start_at or not self.end_at:
            return False
        now = timezone.now()
        return self.start_at <= now <= self.end_at
    
    @property
    def is_check_in_open(self) -> bool:
        """Check if check-in window is currently open."""
        if not self.start_at or not self.check_in_open_mins or not self.check_in_close_mins:
            return False
        
        now = timezone.now()
        check_in_open = self.start_at - timezone.timedelta(minutes=self.check_in_open_mins)
        check_in_close = self.start_at - timezone.timedelta(minutes=self.check_in_close_mins)
        
        return check_in_open <= now <= check_in_close
    
    @property
    def registration_status(self) -> str:
        """Human-readable registration status."""
        if not self.reg_open_at or not self.reg_close_at:
            return "Not scheduled"
        
        now = timezone.now()
        if now < self.reg_open_at:
            return f"Opens {self.reg_open_at.strftime('%b %d, %Y at %H:%M')}"
        elif now > self.reg_close_at:
            return "Closed"
        else:
            return "Open"
    
    @property
    def tournament_status(self) -> str:
        """Human-readable tournament status."""
        if not self.start_at:
            return "Not scheduled"
        
        now = timezone.now()
        if now < self.start_at:
            return f"Starts {self.start_at.strftime('%b %d, %Y at %H:%M')}"
        elif self.end_at and now > self.end_at:
            return "Completed"
        else:
            return "Live"
    
    @property
    def check_in_window_text(self) -> str:
        """Human-readable check-in window."""
        if not self.check_in_open_mins or not self.check_in_close_mins:
            return "Not configured"
        return f"Opens {self.check_in_open_mins}min • Closes {self.check_in_close_mins}min before start"
    
    @property
    def time_until_registration(self) -> timezone.timedelta | None:
        """Time remaining until registration opens (if not yet open)."""
        if not self.reg_open_at:
            return None
        now = timezone.now()
        if now >= self.reg_open_at:
            return None
        return self.reg_open_at - now
    
    @property
    def time_until_tournament(self) -> timezone.timedelta | None:
        """Time remaining until tournament starts (if not yet started)."""
        if not self.start_at:
            return None
        now = timezone.now()
        if now >= self.start_at:
            return None
        return self.start_at - now
    
    # ===== Helper Methods =====
    
    def get_registration_window_display(self) -> str:
        """Format registration window for display."""
        if not self.reg_open_at or not self.reg_close_at:
            return "Not scheduled"
        
        open_str = self.reg_open_at.strftime('%b %d, %Y %H:%M')
        close_str = self.reg_close_at.strftime('%b %d, %Y %H:%M')
        return f"{open_str} to {close_str}"
    
    def get_tournament_window_display(self) -> str:
        """Format tournament window for display."""
        if not self.start_at:
            return "Not scheduled"
        
        start_str = self.start_at.strftime('%b %d, %Y %H:%M')
        if self.end_at:
            end_str = self.end_at.strftime('%b %d, %Y %H:%M')
            return f"{start_str} to {end_str}"
        return f"Starts {start_str}"
    
    def clone_for_tournament(self, target_tournament):
        """
        Create a copy of this schedule for another tournament.
        Useful for creating similar tournaments quickly.
        
        Args:
            target_tournament: Tournament instance to clone schedule to
            
        Returns:
            New TournamentSchedule instance
        """
        return TournamentSchedule.objects.create(
            tournament=target_tournament,
            reg_open_at=self.reg_open_at,
            reg_close_at=self.reg_close_at,
            start_at=self.start_at,
            end_at=self.end_at,
            check_in_open_mins=self.check_in_open_mins,
            check_in_close_mins=self.check_in_close_mins,
        )
