from __future__ import annotations
from django import forms
from django.db import models
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from .models import FAQ, Testimonial, ContactMessage


class ContactForm(forms.ModelForm):
    """Contact form with validation"""
    honeypot = forms.CharField(
        required=False,
        widget=forms.HiddenInput,
        label="Leave this field empty"
    )
    
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Your full name',
                'class': 'w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-dc-cyan focus:border-transparent transition-all'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'your.email@example.com',
                'class': 'w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-dc-cyan focus:border-transparent transition-all'
            }),
            'subject': forms.TextInput(attrs={
                'placeholder': 'What can we help you with?',
                'class': 'w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-dc-cyan focus:border-transparent transition-all'
            }),
            'message': forms.Textarea(attrs={
                'placeholder': 'Please provide as much detail as possible...',
                'rows': 6,
                'class': 'w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-dc-cyan focus:border-transparent transition-all resize-none'
            }),
        }
    
    def clean_honeypot(self):
        """Check honeypot field to prevent spam"""
        honeypot = self.cleaned_data.get('honeypot')
        if honeypot:
            raise forms.ValidationError("Invalid submission detected.")
        return honeypot


def contact_view(request):
    """Contact support page with form submission"""
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            # Check honeypot
            if form.cleaned_data.get('honeypot'):
                messages.success(request, "Thank you! We'll be in touch soon.")
                return redirect('support:contact')
            
            # Save the message
            contact_message = form.save(commit=False)
            
            # Add user if logged in
            if request.user.is_authenticated:
                contact_message.user = request.user
            
            # Capture metadata
            contact_message.ip_address = get_client_ip(request)
            contact_message.user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
            
            contact_message.save()
            
            messages.success(
                request, 
                "Thank you for contacting us! We've received your message and will respond within 24-48 hours."
            )
            return redirect('support:contact')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        # Pre-fill form for authenticated users
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'name': request.user.get_full_name() or request.user.username,
                'email': request.user.email,
            }
        form = ContactForm(initial=initial_data)
    
    context = {
        'form': form,
    }
    return render(request, "support/contact.html", context)


def faq_view(request):
    """FAQ page with search and categories"""
    
    # Get search query
    search_query = request.GET.get('q', '').strip()
    
    # Group FAQs by category
    faqs_by_category = {}
    
    for cat_code, cat_name in FAQ.CATEGORY_CHOICES:
        faqs = FAQ.objects.filter(
            category=cat_code,
            is_active=True
        ).order_by('order', '-created_at')
        
        # Apply search filter if provided
        if search_query:
            faqs = faqs.filter(
                models.Q(question__icontains=search_query) |
                models.Q(answer__icontains=search_query)
            )
        
        if faqs.exists():
            faqs_by_category[cat_name] = faqs
    
    context = {
        'faqs_by_category': faqs_by_category,
        'total_faqs': FAQ.objects.filter(is_active=True).count(),
        'featured_faqs': FAQ.objects.filter(is_active=True, is_featured=True).order_by('order')[:5],
        'search_query': search_query,
    }
    
    return render(request, 'support/faq.html', context)


def moderation_view(request):
    """Moderation & Fair Play page"""
    context = {
        'page_title': 'Moderation & Fair Play',
    }
    return render(request, 'support/moderation.html', context)


def rules_view(request):
    """Rules and Fair Play page"""
    return render(request, 'support/rules.html')


def get_homepage_testimonials():
    """Get testimonials for homepage display"""
    return Testimonial.objects.filter(
        show_on_homepage=True
    ).order_by('order', '-created_at')[:3]


def get_client_ip(request):
    """Get client IP address from request"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

