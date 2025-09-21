#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
sys.path.append(os.path.dirname(__file__))
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.tournaments.models import Tournament, Registration
from apps.user_profile.models import UserProfile

User = get_user_model()

def test_registration():
    # Clean up any existing test data
    User.objects.filter(username='debugtester').delete()
    Tournament.objects.filter(slug='debug-solo').delete()
    
    # Create test user
    user = User.objects.create_user(
        username='debugtester', 
        email='debug@example.com',
        password='testpass123'
    )
    
    # Create user profile
    profile, created = UserProfile.objects.get_or_create(
        user=user,
        defaults={'display_name': 'Debug Tester'}
    )
    
    # Create test tournament
    tournament = Tournament.objects.create(
        name='Debug Solo Tournament',
        slug='debug-solo',
        status='OPEN',
        entry_fee_bdt=100,
        start_at=None
    )
    
    # Test registration
    client = Client()
    client.login(username='debugtester', password='testpass123')
    url = reverse('tournaments:unified_register', kwargs={'slug': 'debug-solo'})
    
    # First, test GET request
    print("Testing GET request...")
    response = client.get(url)
    print(f"GET Status: {response.status_code}")
    
    if response.status_code == 200 and hasattr(response, 'context'):
        context = response.context
        if context:
            print(f"Template: {getattr(response, 'template_name', 'Unknown')}")
            print(f"Tournament rules: {context.get('tournament_rules', {})}")
            print(f"Registration type: {context.get('registration_type', 'Unknown')}")
    
    # Test POST request
    print("\nTesting POST request...")
    data = {
        'display_name': 'Debug Tester',
        'phone': '01712345678',
        'email': 'debug@example.com',
        'payment_method': 'bkash',
        'payment_reference': 'DEBUG123456789',
        'payer_account_number': '01712345678',
        'agree_rules': 'on'
    }
    
    response = client.post(url, data)
    print(f"POST Status: {response.status_code}")
    
    if response.status_code == 200:
        # Registration failed, check for error messages
        content = response.content.decode('utf-8')
        
        # Look for validation error messages
        if 'error' in content.lower() or 'required' in content.lower():
            lines = content.split('\n')
            for line in lines:
                if ('error' in line.lower() or 'required' in line.lower()) and line.strip():
                    print(f"Error message found: {line.strip()}")
        
        # Check Django messages
        if hasattr(response, 'context') and response.context:
            messages = response.context.get('messages', [])
            for msg in messages:
                print(f"Django message: {msg}")
    
    elif response.status_code == 302:
        print("Registration successful - redirected")
        
        # Check if registration was created
        reg_count = Registration.objects.filter(
            tournament=tournament,
            user=profile
        ).count()
        print(f"Registrations created: {reg_count}")
    
    else:
        print(f"Unexpected status code: {response.status_code}")

if __name__ == '__main__':
    test_registration()