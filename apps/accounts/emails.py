from django.core.mail import send_mail
from django.template.loader import render_to_string

def send_otp_email(user, code):
    subject = "Your DeltaCrown verification code"
    body = render_to_string("accounts/otp_email.txt", {"code": code, "user": user})
    send_mail(subject, body, None, [user.email], fail_silently=False)
