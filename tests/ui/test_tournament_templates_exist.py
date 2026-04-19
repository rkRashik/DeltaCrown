from django.template.loader import get_template

def test_tournament_templates_exist():
    for name in [
        "tournaments/list.html",
        "tournaments/base.html",
        "tournaments/detailPages/detail.html",
        "tournaments/detailPages/widgets/_widget_styles.html",
        "tournaments/detailPages/widgets/_overview_widget_stack.html",
        "tournaments/detailPages/widgets/_bottom_board_widget.html",
        "tournaments/detailPages/widgets/_widget_methods.js.html",
        "tournaments/hub/hub.html",
        "tournaments/toc/base.html",
        "tournaments/registration/smart_register.html",
        "tournaments/registration/includes/_step_select_team.html",
        "tournaments/registration/includes/_step_guest_team.html",
        "tournaments/registration/includes/_step_profile.html",
        "tournaments/registration/includes/_step_roster.html",
        "tournaments/registration/includes/_step_coordinator.html",
        "tournaments/registration/includes/_step_extras.html",
        "tournaments/registration/includes/_step_payment.html",
        "tournaments/registration/includes/_step_review.html",
        "tournaments/registration/includes/_wizard_engine.js",
        "tournaments/registration/includes/_roster_card.html",
        "tournaments/registration_ineligible.html",
        "tournaments/spectator/hub.html",
    ]:
        get_template(name)
