def test_admin_package_exports():
    from apps.tournaments.admin import (
        TournamentAdmin,
        RegistrationAdmin,
        action_generate_bracket,
        action_lock_bracket,
        action_verify_payment,
        action_reject_payment,
        export_tournaments_csv,
        export_disputes_csv,
        export_matches_csv,
    )
    # Sanity: just ensure they’re importable/callable
    assert TournamentAdmin
    assert RegistrationAdmin
    assert callable(action_generate_bracket)
    assert callable(action_lock_bracket)
    assert callable(action_verify_payment)
    assert callable(action_reject_payment)
    assert callable(export_tournaments_csv)
    assert callable(export_disputes_csv)
    assert callable(export_matches_csv)
