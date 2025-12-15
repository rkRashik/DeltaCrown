from __future__ import annotations
from django import forms
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import FAQ, Testimonial


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
    """Modern FAQ page with categorized questions"""
    
    # Group FAQs by category
    faqs_by_category = {}
    
    for cat_code, cat_name in FAQ.CATEGORY_CHOICES:
        faqs = FAQ.objects.filter(
            category=cat_code,
            is_active=True
        ).order_by('order', '-created_at')
        
        if faqs.exists():
            faqs_by_category[cat_name] = faqs
    
    context = {
        'faqs_by_category': faqs_by_category,
        'total_faqs': FAQ.objects.filter(is_active=True).count(),
        'featured_faqs': FAQ.objects.filter(is_active=True, is_featured=True).order_by('order')[:5],
    }
    
    return render(request, 'support/faq.html', context)


def rules_view(request):
    """Rules and Fair Play page"""
    return render(request, 'support/rules.html')


def get_homepage_testimonials():
    """Get testimonials for homepage display"""
    return Testimonial.objects.filter(
        show_on_homepage=True
    ).order_by('order', '-created_at')[:3]

