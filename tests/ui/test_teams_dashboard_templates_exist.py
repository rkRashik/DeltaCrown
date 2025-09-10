from django.template.loader import get_template

def test_templates_compile():
    paths = [
        "teams/list.html", "teams/detail.html", "teams/manage.html",
        "teams/partials/_card.html", "teams/partials/_member.html",
        "dashboard/index.html", "dashboard/matches.html",
    ]
    for p in paths:
        get_template(p)
