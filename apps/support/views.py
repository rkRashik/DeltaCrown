from __future__ import annotations
from django import forms
from django.shortcuts import render, redirect
from django.contrib import messages


class ContactForm(forms.Form):
    name = forms.CharField(max_length=120)
    email = forms.EmailField()
    subject = forms.CharField(max_length=160)
    message = forms.CharField(widget=forms.Textarea)
    website = forms.CharField(required=False)  # honeypot


def contact_view(request):
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get("website"):
                return render(request, "support/contact_success.html")
            return render(request, "support/contact_success.html")
        else:
            return render(request, "support/contact_error.html", {"form": form})
    else:
        form = ContactForm()
    return render(request, "support/contact.html", {"form": form})


def faq_view(request):
    faqs = [
        ("General", [
            ("What games do you support?", "Valorant and eFootball Mobile, with more coming."),
            ("How do I register?", "Go to a tournament page and click Register."),
        ]),
        ("Payments", [
            ("Which methods?", "bKash and Nagad; bank transfer for special events."),
            ("When are payouts issued?", "Within 48 hours after verification."),
        ]),
        ("Matches", [
            ("How do I report?", "Use Report on your dashboard or the match page."),
            ("How do disputes work?", "Open a dispute with evidence; referees review."),
        ]),
    ]
    return render(request, "support/faq.html", {"faqs": faqs})
