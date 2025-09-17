from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


def send_otp_email(user, code, *, expires_in_minutes: int = 10):
    subject = "Verify your DeltaCrown account"
    body = render_to_string(
        "account/otp_email.txt",
        {
            "code": code,
            "user": user,
            "expires_in": expires_in_minutes,
        },
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or getattr(settings, "EMAIL_HOST_USER", None)
    send_mail(subject, body, from_email, [user.email], fail_silently=False)
