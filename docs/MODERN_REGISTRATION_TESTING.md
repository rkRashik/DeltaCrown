# 🧪 Modern Registration System - Testing Guide

## 📋 Testing Overview

This guide covers all testing scenarios for the modern tournament registration system, from unit tests to end-to-end user flows.

---

## 🎯 Test Categories

### 1. Unit Tests (Service Layer)
### 2. Integration Tests (API Endpoints)
### 3. E2E Tests (User Flows)
### 4. Manual Testing (UI/UX)
### 5. Performance Tests
### 6. Security Tests

---

## 1️⃣ Unit Tests (Service Layer)

### Test File: `apps/tournaments/tests/test_registration_service.py`

```python
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.tournaments.models import Tournament, Registration
from apps.tournaments.services.registration_service import RegistrationService
from apps.user_profile.models import UserProfile
from apps.teams.models import Team, TeamMembership

User = get_user_model()


class RegistrationServiceTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
        self.profile = UserProfile.objects.create(
            user=self.user,
            display_name='Test User',
            phone='01712345678'
        )
        
        # Create test tournament
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game='valorant',
            status='PUBLISHED',
            slot_size=32,
            entry_fee_bdt=100
        )
    
    def test_get_registration_context_register_state(self):
        """Test registration context for eligible user"""
        from datetime import timedelta
        from django.utils import timezone
        
        # Set registration window
        self.tournament.reg_open_at = timezone.now() - timedelta(days=1)
        self.tournament.reg_close_at = timezone.now() + timedelta(days=7)
        self.tournament.save()
        
        context = RegistrationService.get_registration_context(
            self.tournament, self.user
        )
        
        self.assertTrue(context.can_register)
        self.assertEqual(context.button_state, 'register')
        self.assertEqual(context.button_text, 'Register Now')
    
    def test_get_registration_context_already_registered(self):
        """Test context when user already registered"""
        Registration.objects.create(
            tournament=self.tournament,
            user=self.profile,
            status='CONFIRMED'
        )
        
        context = RegistrationService.get_registration_context(
            self.tournament, self.user
        )
        
        self.assertFalse(context.can_register)
        self.assertEqual(context.button_state, 'registered')
        self.assertTrue(context.already_registered)
    
    def test_get_registration_context_tournament_full(self):
        """Test context when tournament slots full"""
        from datetime import timedelta
        from django.utils import timezone
        
        self.tournament.reg_open_at = timezone.now() - timedelta(days=1)
        self.tournament.reg_close_at = timezone.now() + timedelta(days=7)
        self.tournament.slot_size = 1
        self.tournament.save()
        
        # Create registration to fill slot
        other_user = User.objects.create_user(username='other')
        other_profile = UserProfile.objects.create(
            user=other_user,
            display_name='Other User'
        )
        Registration.objects.create(
            tournament=self.tournament,
            user=other_profile,
            status='CONFIRMED'
        )
        
        context = RegistrationService.get_registration_context(
            self.tournament, self.user
        )
        
        self.assertFalse(context.can_register)
        self.assertEqual(context.button_state, 'full')
        self.assertFalse(context.slots_available)
    
    def test_auto_fill_profile_data(self):
        """Test profile data extraction"""
        self.profile.discord_id = 'TestUser#1234'
        self.profile.riot_id = 'TestPlayer#TAG'
        self.profile.save()
        
        data = RegistrationService.auto_fill_profile_data(self.user)
        
        self.assertEqual(data['display_name'], 'Test User')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['phone'], '01712345678')
        self.assertEqual(data['discord_id'], 'TestUser#1234')
        self.assertEqual(data['riot_id'], 'TestPlayer#TAG')
    
    def test_validate_registration_data_valid(self):
        """Test validation with valid data"""
        data = {
            'display_name': 'Test User',
            'email': 'test@example.com',
            'phone': '01712345678',
            'in_game_id': 'TestPlayer#TAG',
            'payment_method': 'bkash',
            'payment_reference': 'TXN123456',
            'agree_rules': True
        }
        
        is_valid, errors = RegistrationService.validate_registration_data(
            self.tournament, self.user, data
        )
        
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
    
    def test_validate_registration_data_invalid_phone(self):
        """Test validation with invalid phone"""
        data = {
            'display_name': 'Test User',
            'phone': '123',  # Invalid
            'payment_method': 'bkash',
            'payment_reference': 'TXN123456'
        }
        
        is_valid, errors = RegistrationService.validate_registration_data(
            self.tournament, self.user, data
        )
        
        self.assertFalse(is_valid)
        self.assertIn('phone', errors)
    
    def test_validate_registration_data_missing_payment(self):
        """Test validation with missing payment info for paid tournament"""
        data = {
            'display_name': 'Test User',
            'phone': '01712345678',
            # Missing payment_method and payment_reference
        }
        
        is_valid, errors = RegistrationService.validate_registration_data(
            self.tournament, self.user, data
        )
        
        self.assertFalse(is_valid)
        self.assertIn('payment_method', errors)
        self.assertIn('payment_reference', errors)
    
    def test_create_registration_success(self):
        """Test successful registration creation"""
        from datetime import timedelta
        from django.utils import timezone
        
        self.tournament.reg_open_at = timezone.now() - timedelta(days=1)
        self.tournament.reg_close_at = timezone.now() + timedelta(days=7)
        self.tournament.save()
        
        data = {
            'display_name': 'Test User',
            'email': 'test@example.com',
            'phone': '01712345678',
            'payment_method': 'bkash',
            'payer_account_number': '01712345678',
            'payment_reference': 'TXN123456'
        }
        
        registration = RegistrationService.create_registration(
            self.tournament, self.user, data
        )
        
        self.assertIsNotNone(registration)
        self.assertEqual(registration.tournament, self.tournament)
        self.assertEqual(registration.user, self.profile)
        self.assertEqual(registration.status, 'PENDING')
    
    def test_create_registration_duplicate_prevented(self):
        """Test that duplicate registration raises error"""
        from django.core.exceptions import ValidationError
        
        # Create first registration
        Registration.objects.create(
            tournament=self.tournament,
            user=self.profile,
            status='CONFIRMED'
        )
        
        data = {
            'display_name': 'Test User',
            'phone': '01712345678'
        }
        
        with self.assertRaises(ValidationError):
            RegistrationService.create_registration(
                self.tournament, self.user, data
            )


class ApprovalServiceTests(TestCase):
    def setUp(self):
        # Create captain
        self.captain_user = User.objects.create_user(
            username='captain',
            email='captain@example.com'
        )
        self.captain_profile = UserProfile.objects.create(
            user=self.captain_user,
            display_name='Captain'
        )
        
        # Create member
        self.member_user = User.objects.create_user(
            username='member',
            email='member@example.com'
        )
        self.member_profile = UserProfile.objects.create(
            user=self.member_user,
            display_name='Member'
        )
        
        # Create team
        self.team = Team.objects.create(
            name='Test Team',
            tag='TEST',
            game='valorant',
            captain=self.captain_profile
        )
        
        # Create memberships
        TeamMembership.objects.create(
            team=self.team,
            profile=self.captain_profile,
            role='CAPTAIN',
            status='ACTIVE'
        )
        TeamMembership.objects.create(
            team=self.team,
            profile=self.member_profile,
            role='PLAYER',
            status='ACTIVE'
        )
        
        # Create tournament
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game='valorant',
            status='PUBLISHED'
        )
    
    def test_create_request_success(self):
        """Test creating approval request"""
        from apps.tournaments.services.approval_service import ApprovalService
        
        request = ApprovalService.create_request(
            requester=self.member_profile,
            tournament=self.tournament,
            team=self.team,
            message='Please register us!'
        )
        
        self.assertIsNotNone(request)
        self.assertEqual(request.requester, self.member_profile)
        self.assertEqual(request.captain, self.captain_profile)
        self.assertEqual(request.status, 'PENDING')
    
    def test_create_request_captain_cannot_request(self):
        """Test that captain cannot request from themselves"""
        from django.core.exceptions import ValidationError
        from apps.tournaments.services.approval_service import ApprovalService
        
        with self.assertRaises(ValidationError):
            ApprovalService.create_request(
                requester=self.captain_profile,
                tournament=self.tournament,
                team=self.team,
                message='Test'
            )
    
    def test_approve_request_success(self):
        """Test approving a request"""
        from apps.tournaments.services.approval_service import ApprovalService
        from apps.tournaments.models import RegistrationRequest
        
        # Create request
        request = RegistrationRequest.objects.create(
            requester=self.member_profile,
            tournament=self.tournament,
            team=self.team,
            captain=self.captain_profile,
            status='PENDING',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # Approve
        registration = ApprovalService.approve_request(
            request=request,
            captain=self.captain_profile,
            response_message='Approved!',
            auto_register=True
        )
        
        request.refresh_from_db()
        self.assertEqual(request.status, 'APPROVED')
        self.assertIsNotNone(registration)
    
    def test_reject_request_success(self):
        """Test rejecting a request"""
        from apps.tournaments.services.approval_service import ApprovalService
        from apps.tournaments.models import RegistrationRequest
        
        # Create request
        request = RegistrationRequest.objects.create(
            requester=self.member_profile,
            tournament=self.tournament,
            team=self.team,
            captain=self.captain_profile,
            status='PENDING',
            expires_at=timezone.now() + timedelta(days=7)
        )
        
        # Reject
        ApprovalService.reject_request(
            request=request,
            captain=self.captain_profile,
            response_message='Not now'
        )
        
        request.refresh_from_db()
        self.assertEqual(request.status, 'REJECTED')


# Run tests
# python manage.py test apps.tournaments.tests.test_registration_service
```

---

## 2️⃣ Integration Tests (API Endpoints)

### Test File: `apps/tournaments/tests/test_registration_api.py`

```python
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
import json

User = get_user_model()


class RegistrationAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Create tournament
        from apps.tournaments.models import Tournament
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
            game='valorant',
            status='PUBLISHED'
        )
    
    def test_registration_context_api(self):
        """Test GET /api/tournaments/<slug>/register/context/"""
        url = reverse('tournaments:registration_context_api', 
                     kwargs={'slug': self.tournament.slug})
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('context', data)
        self.assertIn('button_state', data['context'])
    
    def test_validate_registration_api(self):
        """Test POST /api/tournaments/<slug>/register/validate/"""
        url = reverse('tournaments:validate_registration_api',
                     kwargs={'slug': self.tournament.slug})
        
        data = {
            'display_name': 'Test User',
            'phone': '01712345678',
            'email': 'test@example.com'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn('success', result)
    
    def test_submit_registration_api(self):
        """Test POST /api/tournaments/<slug>/register/submit/"""
        from datetime import timedelta
        from django.utils import timezone
        from apps.user_profile.models import UserProfile
        
        # Create profile
        profile = UserProfile.objects.create(
            user=self.user,
            display_name='Test User'
        )
        
        # Set registration window
        self.tournament.reg_open_at = timezone.now() - timedelta(days=1)
        self.tournament.reg_close_at = timezone.now() + timedelta(days=7)
        self.tournament.save()
        
        url = reverse('tournaments:submit_registration_api',
                     kwargs={'slug': self.tournament.slug})
        
        data = {
            'display_name': 'Test User',
            'phone': '01712345678',
            'email': 'test@example.com',
            'payment_method': 'bkash',
            'payment_reference': 'TXN123456',
            'payer_account_number': '01712345678'
        }
        
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertTrue(result['success'])
        self.assertIn('registration_id', result)


# Run tests
# python manage.py test apps.tournaments.tests.test_registration_api
```

---

## 3️⃣ E2E Tests (User Flows)

### Using Selenium

```python
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class RegistrationE2ETests(StaticLiveServerTestCase):
    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.implicitly_wait(10)
    
    def tearDown(self):
        self.driver.quit()
    
    def test_solo_registration_flow(self):
        """Test complete solo registration flow"""
        # 1. Navigate to tournament page
        self.driver.get(f'{self.live_server_url}/tournaments/t/test-tournament/')
        
        # 2. Click register button
        register_btn = WebDriverWait(self.driver, 10).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'btn-register'))
        )
        register_btn.click()
        
        # 3. Fill form
        display_name = self.driver.find_element(By.ID, 'display_name')
        display_name.send_keys('Test User')
        
        phone = self.driver.find_element(By.ID, 'phone')
        phone.send_keys('01712345678')
        
        # 4. Next step
        next_btn = self.driver.find_element(By.CLASS_NAME, 'btn-next')
        next_btn.click()
        
        # 5. Agree to rules
        agree_checkbox = self.driver.find_element(By.ID, 'agree_rules')
        agree_checkbox.click()
        
        # 6. Submit
        submit_btn = self.driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
        submit_btn.click()
        
        # 7. Check success
        WebDriverWait(self.driver, 10).until(
            EC.url_contains('/registration-receipt')
        )
        
        success_msg = self.driver.find_element(By.CLASS_NAME, 'alert-success')
        self.assertIn('Registration submitted', success_msg.text)


# Run tests
# python manage.py test apps.tournaments.tests.test_registration_e2e
```

---

## 4️⃣ Manual Testing Checklist

### Solo Tournament Registration

- [ ] **Registration Opens**
  - [ ] Button shows "Register Now" when within reg window
  - [ ] Button disabled before reg_open_at
  - [ ] Button disabled after reg_close_at

- [ ] **Form Display**
  - [ ] Profile data auto-fills correctly
  - [ ] Email field is locked
  - [ ] Phone field is editable
  - [ ] In-game ID field shows
  - [ ] Discord field is optional

- [ ] **Validation**
  - [ ] Required fields show error if empty
  - [ ] Phone validates BD mobile format
  - [ ] Email validates format
  - [ ] Payment fields required for paid tournaments

- [ ] **Multi-Step Navigation**
  - [ ] Can go to next step
  - [ ] Can go back to previous step
  - [ ] Progress bar updates correctly
  - [ ] Review shows correct data

- [ ] **Submission**
  - [ ] Form submits successfully
  - [ ] Notification sent
  - [ ] Redirects to receipt page
  - [ ] Registration saved in database

### Team Tournament (Captain)

- [ ] **Team Detection**
  - [ ] System detects user's team
  - [ ] Captain status verified
  - [ ] Button shows "Register Team"

- [ ] **Team Step**
  - [ ] Team logo displays
  - [ ] All members listed
  - [ ] Roles shown correctly (Captain, Player, Sub)
  - [ ] Verification badges display

- [ ] **Registration**
  - [ ] Captain can submit
  - [ ] Team linked to registration
  - [ ] All team members notified

### Team Tournament (Non-Captain)

- [ ] **Approval Request**
  - [ ] Button shows "Request Captain Approval"
  - [ ] Modal opens on click
  - [ ] Can enter message
  - [ ] Request submits successfully
  - [ ] Captain receives notification

- [ ] **After Request**
  - [ ] Button changes to "Request Pending"
  - [ ] Cannot create duplicate request
  - [ ] Can view request status

### Captain Approval Flow

- [ ] **Captain Dashboard**
  - [ ] Pending requests show
  - [ ] Can approve request
  - [ ] Can reject request
  - [ ] Can add response message

- [ ] **Auto-Registration**
  - [ ] Team registers on approval
  - [ ] Requester notified
  - [ ] Dashboard updates

### Edge Cases

- [ ] **Duplicate Registration**
  - [ ] Shows "Registered ✓" if already registered
  - [ ] Cannot register twice

- [ ] **Tournament Full**
  - [ ] Button shows "Tournament Full"
  - [ ] Cannot register when slots exhausted

- [ ] **Tournament Started**
  - [ ] Button shows "Tournament Started"
  - [ ] Cannot register after start

- [ ] **No Team**
  - [ ] Shows "Create/Join Team First"
  - [ ] Links to team creation

### Mobile Testing

- [ ] **Responsive Design**
  - [ ] Form displays correctly on mobile
  - [ ] Buttons are tap-friendly
  - [ ] Progress bar visible
  - [ ] No horizontal scroll

- [ ] **Touch Interactions**
  - [ ] Modal opens on tap
  - [ ] Form fields work correctly
  - [ ] Validation feedback visible

### Browser Compatibility

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile browsers

---

## 5️⃣ Performance Tests

```python
import time
from django.test import TestCase


class RegistrationPerformanceTests(TestCase):
    def test_context_api_response_time(self):
        """Context API should respond in <100ms"""
        start = time.time()
        
        # Make request
        response = self.client.get('/tournaments/api/test/register/context/')
        
        end = time.time()
        response_time = (end - start) * 1000  # ms
        
        self.assertLess(response_time, 100)
    
    def test_auto_fill_performance(self):
        """Auto-fill should complete in <50ms"""
        from apps.tournaments.services.registration_service import RegistrationService
        
        start = time.time()
        
        data = RegistrationService.auto_fill_profile_data(self.user)
        
        end = time.time()
        execution_time = (end - start) * 1000
        
        self.assertLess(execution_time, 50)
```

---

## 6️⃣ Security Tests

```python
class RegistrationSecurityTests(TestCase):
    def test_csrf_protection(self):
        """Registration requires CSRF token"""
        response = self.client.post(
            '/tournaments/api/test/register/submit/',
            {},
            enforce_csrf_checks=True
        )
        self.assertEqual(response.status_code, 403)
    
    def test_captain_authorization(self):
        """Non-captain cannot register team"""
        # Create non-captain user
        member = User.objects.create_user('member', 'pass')
        self.client.login(username='member', password='pass')
        
        # Try to register team
        context = RegistrationService.get_registration_context(
            tournament, member
        )
        
        self.assertEqual(context.button_state, 'request_approval')
        self.assertFalse(context.is_captain)
    
    def test_sql_injection_prevention(self):
        """System prevents SQL injection"""
        malicious_input = "'; DROP TABLE registrations; --"
        
        data = {
            'display_name': malicious_input,
            'phone': '01712345678'
        }
        
        # Should not crash or execute SQL
        is_valid, errors = RegistrationService.validate_registration_data(
            tournament, user, data
        )
        
        # Data should be escaped
        self.assertIn(malicious_input, errors.get('display_name', ''))
```

---

## 🎯 Test Coverage Goals

- **Unit Tests**: 90%+ coverage
- **Integration Tests**: 80%+ coverage
- **E2E Tests**: Critical paths only
- **Manual Tests**: 100% of checklist
- **Performance**: All < 100ms
- **Security**: All vulnerabilities addressed

---

## 📊 Running Tests

```bash
# All tests
python manage.py test apps.tournaments.tests

# Specific test file
python manage.py test apps.tournaments.tests.test_registration_service

# With coverage
coverage run --source='apps/tournaments' manage.py test
coverage report
coverage html

# Performance tests
python manage.py test apps.tournaments.tests.test_performance --settings=settings_test

# E2E tests (requires selenium)
python manage.py test apps.tournaments.tests.test_e2e
```

---

## ✅ Definition of Done

A feature is considered complete when:

- [✅] All unit tests pass
- [✅] All integration tests pass
- [✅] Manual testing checklist complete
- [✅] Code review approved
- [✅] Documentation updated
- [✅] No critical bugs
- [✅] Performance benchmarks met
- [✅] Security review passed

---

**Last Updated**: October 2, 2025  
**Test Coverage**: Target 85%+
