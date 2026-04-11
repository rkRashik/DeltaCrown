"""
Unit tests for payment verification IDOR fix (SEC-001).

Verifies that ``IsStaffOrTournamentOrganizer`` permission class correctly
gates the ``verify``, ``reject``, and ``refund`` actions.

Pure mock-based — no database or API server required.
"""

from unittest.mock import patch, MagicMock, PropertyMock

import pytest


_PAYMENTS_MODULE = "apps.tournaments.api.payments"


def _staff_request(user_id=1, is_superuser=False):
    r = MagicMock()
    r.user.id = user_id
    r.user.pk = user_id
    r.user.is_staff = True
    r.user.is_superuser = is_superuser
    return r


class TestIsStaffOrTournamentOrganizer:
    """SEC-001: object-level permission gate on payment moderation."""

    def test_organizer_has_permission(self):
        from apps.tournaments.api.payments import IsStaffOrTournamentOrganizer

        perm = IsStaffOrTournamentOrganizer()
        request = _staff_request(user_id=5)

        pv = MagicMock()
        pv.registration.tournament.organizer_id = 5
        pv.registration.tournament.co_organizers.filter.return_value.exists.return_value = False

        assert perm.has_object_permission(request, None, pv) is True

    def test_co_organizer_has_permission(self):
        from apps.tournaments.api.payments import IsStaffOrTournamentOrganizer

        perm = IsStaffOrTournamentOrganizer()
        request = _staff_request(user_id=7)

        pv = MagicMock()
        pv.registration.tournament.organizer_id = 99  # not the organizer
        pv.registration.tournament.co_organizers.filter.return_value.exists.return_value = True

        assert perm.has_object_permission(request, None, pv) is True

    def test_superuser_has_permission(self):
        from apps.tournaments.api.payments import IsStaffOrTournamentOrganizer

        perm = IsStaffOrTournamentOrganizer()
        request = _staff_request(user_id=1, is_superuser=True)

        pv = MagicMock()
        pv.registration.tournament.organizer_id = 99
        pv.registration.tournament.co_organizers.filter.return_value.exists.return_value = False

        assert perm.has_object_permission(request, None, pv) is True

    def test_unrelated_staff_denied(self):
        from apps.tournaments.api.payments import IsStaffOrTournamentOrganizer

        perm = IsStaffOrTournamentOrganizer()
        request = _staff_request(user_id=42)

        pv = MagicMock()
        pv.registration.tournament.organizer_id = 99
        pv.registration.tournament.co_organizers.filter.return_value.exists.return_value = False

        assert perm.has_object_permission(request, None, pv) is False

    def test_anonymous_user_denied_at_class_level(self):
        from apps.tournaments.api.payments import IsStaffOrTournamentOrganizer

        perm = IsStaffOrTournamentOrganizer()
        request = MagicMock()
        request.user.is_staff = False
        request.user.is_superuser = False

        # has_permission should deny non-staff
        assert perm.has_permission(request, None) is False
