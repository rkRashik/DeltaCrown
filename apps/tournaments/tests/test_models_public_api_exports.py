# apps/tournaments/tests/test_models_public_api_exports.py
def test_tournaments_models_public_api_exports():
    from apps.tournaments import models as m
    required = {
        "STATUS_CHOICES","PAYMENT_METHODS",
        "tournament_banner_path","rules_pdf_path","rules_upload_path",
        "BracketVisibility","Tournament","Registration","Bracket","Match",
        "TournamentSettings","MatchEvent","MatchComment","MatchDispute",
    }
    exported = set(getattr(m, "__all__", []))
    assert required.issubset(exported)
