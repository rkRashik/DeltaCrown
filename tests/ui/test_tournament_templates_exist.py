from django.template.loader import get_template

def test_tournament_templates_exist():
    for name in [
        "tournaments/list.html",
        "tournaments/detail.html",
        "tournaments/register.html",
        "tournaments/bracket.html",
        "tournaments/report_form.html",
        "tournaments/dispute_form.html",
        "tournaments/register_success.html",
        "tournaments/register_closed.html",
        "tournaments/register_error.html",
        "tournaments/partials/_card.html",
        "tournaments/partials/_status_pill.html",
        "tournaments/partials/_meta.html",
        "tournaments/partials/_match_card.html",
    ]:
        get_template(name)
