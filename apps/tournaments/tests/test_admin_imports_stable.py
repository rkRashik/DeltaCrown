def test_admin_package_exports_actions():
    from apps.tournaments.admin import (
        export_tournaments_csv,
        export_disputes_csv,
        export_matches_csv,
    )
    assert callable(export_tournaments_csv)
    assert callable(export_disputes_csv)
    assert callable(export_matches_csv)
