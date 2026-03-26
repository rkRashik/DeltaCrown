from django.template.loader import get_template

def test_tournament_templates_exist():
    for name in [
        "tournaments/list.html",
        "tournaments/base.html",
        "tournaments/detailPages/_base_detail.html",
        "tournaments/detailPages/detail_registration.html",
        "tournaments/detailPages/detail_live.html",
        "tournaments/detailPages/detail_completed.html",
        "tournaments/detailPages/detail_cancelled.html",
        "tournaments/hub/hub.html",
        "tournaments/toc/base.html",
        "tournaments/registration/smart_register.html",
        "tournaments/registration_ineligible.html",
        "tournaments/spectator/hub.html",
    ]:
        get_template(name)
