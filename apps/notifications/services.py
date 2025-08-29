import os
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from .models import Notification

def _from_email():
    return os.getenv("DeltaCrownEmail", "deltacrownhq@gmail.com")

def send_email(to_email: str, subject: str, template_base: str, ctx: dict):
    text = render_to_string(f"emails/{template_base}.txt", ctx)
    html = render_to_string(f"emails/{template_base}.html", ctx)
    email = EmailMultiAlternatives(subject, text, _from_email(), [to_email])
    email.attach_alternative(html, "text/html")
    email.send(fail_silently=True)

def notify(recipient_profile, ntype, title, *, body="", url="", tournament=None, match=None,
           email_subject=None, email_template=None, email_ctx=None):
    n = Notification.objects.create(
        recipient=recipient_profile, type=ntype, title=title, body=body, url=url,
        tournament=tournament, match=match
    )
    user = recipient_profile.user
    if getattr(user, "email", "") and email_subject and email_template:
        send_email(user.email, email_subject, email_template, email_ctx or {})
    return n
