# FE-T-001: Tournament List Page
# FE-T-002: Tournament Detail Page
# FE-T-003: Registration CTA States

"""
Tournament Frontend Views (Main) - REDIRECT MODULE.

Phase 3 Restructure: This file now re-exports from split modules.
- discovery.py  -> TournamentListView
- detail.py     -> TournamentDetailView, participant_checkin

All original code has been preserved in the new files.
Import from here for backward compatibility.
"""

from apps.tournaments.views.discovery import TournamentListView  # noqa: F401
from apps.tournaments.views.detail import TournamentDetailView, participant_checkin  # noqa: F401
