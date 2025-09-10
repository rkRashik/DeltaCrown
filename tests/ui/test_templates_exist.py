from django.template.loader import get_template

def test_core_templates_exist():
    for name in [
        "base.html",
        "home.html",
        "partials/nav.html",
        "partials/footer.html",
        "partials/toasts.html",
        "partials/seo_meta.html",
        "sections/hero.html",
        "sections/pillars.html",
        "sections/timeline.html",
        "sections/stats.html",
        "sections/spotlight.html",
        "sections/split_cta.html",
        "pages/about.html",
        "pages/community.html",
    ]:
        get_template(name)
