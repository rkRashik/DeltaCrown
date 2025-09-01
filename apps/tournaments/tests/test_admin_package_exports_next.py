# apps/tournaments/tests/test_admin_package_exports_next.py
def test_admin_package_exports_next():
    from apps.tournaments.admin import (
        TournamentAdmin, RegistrationAdmin, MatchAdmin,
        action_generate_bracket, action_lock_bracket,
        action_verify_payment, action_reject_payment,
        action_auto_schedule, action_clear_schedule,
        export_tournaments_csv, export_disputes_csv, export_matches_csv,
    )
    assert TournamentAdmin and RegistrationAdmin and MatchAdmin
    for fn in (action_generate_bracket, action_lock_bracket,
               action_verify_payment, action_reject_payment,
               action_auto_schedule, action_clear_schedule,
               export_tournaments_csv, export_disputes_csv, export_matches_csv):
        assert callable(fn)
