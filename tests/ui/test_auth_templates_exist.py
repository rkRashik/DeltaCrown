from django.template.loader import get_template

def test_auth_templates_compile():
    paths = [
        "account/login.html",
        "account/signup.html",
        "account/password_reset.html",
        "account/password_reset_done.html",
        "account/password_reset_from_key.html",
        "account/verification_sent.html",
        "account/confirm_email.html",
        "socialaccount/signup.html",
        "profile/index.html",
        "components/_form_fields.html",
    ]
    for p in paths:
        get_template(p)
