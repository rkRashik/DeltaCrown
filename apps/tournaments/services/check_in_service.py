# Backward-compat redirect: use checkin_service.py (canonical)
from apps.tournaments.services.checkin_service import CheckinService as CheckInService  # noqa: F401

__all__ = ['CheckInService']
