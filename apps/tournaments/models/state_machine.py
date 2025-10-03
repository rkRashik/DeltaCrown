# apps/tournaments/models/state_machine.py
"""
Centralized tournament state machine and business logic.
Eliminates scattered validation and state checks across views/services.
"""
from __future__ import annotations
from datetime import timedelta
from enum import Enum
from typing import TYPE_CHECKING, Optional, Tuple
from django.utils import timezone

if TYPE_CHECKING:
    from .tournament import Tournament


class RegistrationState(str, Enum):
    """All possible registration states - single source of truth."""
    NOT_OPEN = "not_open"
    OPEN = "open"
    CLOSED = "closed"
    FULL = "full"
    STARTED = "started"
    COMPLETED = "completed"


class TournamentPhase(str, Enum):
    """Tournament lifecycle phases."""
    DRAFT = "draft"
    REGISTRATION = "registration"
    LIVE = "live"
    COMPLETED = "completed"


class TournamentStateMachine:
    """
    Centralized state computation for tournaments.
    All views/services should use this instead of scattered checks.
    """
    
    def __init__(self, tournament: Tournament):
        self.tournament = tournament
        self._now = timezone.now()
        self._settings = getattr(tournament, 'settings', None)
    
    @property
    def current_phase(self) -> TournamentPhase:
        """Compute current tournament phase."""
        if self.tournament.status == 'DRAFT':
            return TournamentPhase.DRAFT
        elif self.tournament.status == 'COMPLETED':
            return TournamentPhase.COMPLETED
        elif self.tournament.status == 'RUNNING':
            return TournamentPhase.LIVE
        elif self.is_started:
            return TournamentPhase.LIVE
        else:
            return TournamentPhase.REGISTRATION
    
    @property
    def phase(self) -> TournamentPhase:
        """Alias for current_phase for convenience."""
        return self.current_phase
    
    @property
    def is_published(self) -> bool:
        """Is tournament visible to public?"""
        return self.tournament.status in ['PUBLISHED', 'RUNNING', 'COMPLETED']
    
    @property
    def is_started(self) -> bool:
        """Has tournament start time passed?"""
        start_time = self.start_datetime
        return start_time is not None and self._now >= start_time
    
    @property
    def is_completed(self) -> bool:
        """Is tournament finished?"""
        return self.tournament.status == 'COMPLETED'
    
    @property
    def start_datetime(self) -> Optional[timezone.datetime]:
        """Get start datetime from tournament or settings."""
        # Prefer tournament-level, fallback to settings
        if self.tournament.start_at:
            return self.tournament.start_at
        if self._settings and hasattr(self._settings, 'start_at'):
            return self._settings.start_at
        return None
    
    @property
    def registration_window(self) -> Tuple[Optional[timezone.datetime], Optional[timezone.datetime]]:
        """Get registration open/close datetimes."""
        # Prefer settings, fallback to tournament
        if self._settings:
            reg_open = getattr(self._settings, 'reg_open_at', None) or self.tournament.reg_open_at
            reg_close = getattr(self._settings, 'reg_close_at', None) or self.tournament.reg_close_at
        else:
            reg_open = self.tournament.reg_open_at
            reg_close = self.tournament.reg_close_at
        
        return (reg_open, reg_close)
    
    @property
    def registration_state(self) -> RegistrationState:
        """
        Compute current registration state.
        This is the single source of truth for button states.
        """
        # Not published = not open
        if not self.is_published:
            return RegistrationState.NOT_OPEN
        
        # Completed = closed
        if self.is_completed:
            return RegistrationState.COMPLETED
        
        # Check registration window
        reg_open, reg_close = self.registration_window
        
        # No explicit window set
        if not reg_open or not reg_close:
            # Fallback logic: if published and not started, allow registration
            if self.tournament.status == 'PUBLISHED' and not self.is_started:
                # Check slots
                if self.is_full:
                    return RegistrationState.FULL
                return RegistrationState.OPEN
            # If started without window, registration is closed
            if self.is_started:
                return RegistrationState.STARTED
            return RegistrationState.NOT_OPEN
        
        # Check if we're in the window
        if self._now < reg_open:
            return RegistrationState.NOT_OPEN
        elif self._now > reg_close:
            return RegistrationState.CLOSED
        else:
            # In window - check slots
            if self.is_full:
                return RegistrationState.FULL
            return RegistrationState.OPEN
    
    @property
    def is_full(self) -> bool:
        """Check if tournament has reached capacity."""
        slot_size = self.tournament.slot_size
        if not slot_size or slot_size <= 0:
            return False  # No limit
        
        # Count confirmed registrations
        try:
            from .registration import Registration
            confirmed_count = Registration.objects.filter(
                tournament=self.tournament,
                status='CONFIRMED'
            ).count()
            return confirmed_count >= slot_size
        except Exception:
            return False
    
    @property
    def slots_info(self) -> dict:
        """Get slot capacity information."""
        slot_size = self.tournament.slot_size or 0
        try:
            from .registration import Registration
            confirmed = Registration.objects.filter(
                tournament=self.tournament,
                status='CONFIRMED'
            ).count()
        except Exception:
            confirmed = 0
        
        return {
            'total': slot_size if slot_size > 0 else None,
            'taken': confirmed,
            'available': (slot_size - confirmed) if slot_size > 0 else None,
            'is_full': self.is_full,
            'has_limit': slot_size > 0,
        }
    
    @property
    def is_team_based(self) -> bool:
        """Determine if tournament requires teams."""
        if not self._settings:
            return False
        
        min_size = getattr(self._settings, 'min_team_size', None)
        max_size = getattr(self._settings, 'max_team_size', None)
        
        return (min_size and min_size > 1) or (max_size and max_size > 1)
    
    def time_until_start(self) -> Optional[timedelta]:
        """Get time remaining until tournament starts."""
        start_time = self.start_datetime
        if not start_time or self.is_started:
            return None
        return start_time - self._now
    
    def time_until_registration_closes(self) -> Optional[timedelta]:
        """Get time remaining in registration window."""
        _, reg_close = self.registration_window
        if not reg_close or self._now > reg_close:
            return None
        return reg_close - self._now
    
    def can_register(self, user=None) -> Tuple[bool, str]:
        """
        Check if registration is allowed.
        Returns (can_register, reason).
        """
        # Check authentication
        if not user or not user.is_authenticated:
            return (False, "You must be logged in to register")
        
        # Check registration state
        state = self.registration_state
        
        if state == RegistrationState.NOT_OPEN:
            reg_open, _ = self.registration_window
            if reg_open:
                return (False, f"Registration opens {reg_open.strftime('%b %d, %Y at %H:%M')}")
            return (False, "Registration is not yet open")
        
        elif state == RegistrationState.CLOSED:
            return (False, "Registration has closed")
        
        elif state == RegistrationState.FULL:
            return (False, "Tournament is full")
        
        elif state == RegistrationState.STARTED:
            return (False, "Tournament has already started")
        
        elif state == RegistrationState.COMPLETED:
            return (False, "Tournament has ended")
        
        elif state == RegistrationState.OPEN:
            return (True, "Registration is open")
        
        return (False, "Registration is not available")
    
    def to_dict(self) -> dict:
        """Export state as dictionary for API/templates."""
        reg_state = self.registration_state
        can_reg, reason = self.can_register()
        
        return {
            'phase': self.current_phase.value,
            'is_published': self.is_published,
            'is_started': self.is_started,
            'is_completed': self.is_completed,
            'registration_state': reg_state.value,
            'can_register': can_reg,
            'reason': reason,
            'is_team_based': self.is_team_based,
            'slots': self.slots_info,
            'time_until_start': str(self.time_until_start()) if self.time_until_start() else None,
            'time_until_reg_closes': str(self.time_until_registration_closes()) if self.time_until_registration_closes() else None,
        }
