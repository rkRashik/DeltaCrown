# Tournament System Improvements Plan

**Date:** November 17, 2025  
**Status:** Planning & Implementation  
**Priority:** High

---

## Executive Summary

This document outlines critical improvements needed for the DeltaCrown tournament system based on user feedback and planning documents. Issues range from immediate fixes (payment methods, terms & conditions) to comprehensive features (staff management, notification system, organizer console expansion).

---

## 1. COMPLETED FIXES ✅

### 1.1 Team URL Pattern (404 Error)
**Issue:** Teams accessed via `/teams/10/` but URLs expect slug format `/teams/dhaka-dragons/`  
**Root Cause:** Teams created without slugs in seed data  
**Solution:** Generated slugs for all existing teams using `slugify(team.name)`  
**Status:** ✅ FIXED - All 5 teams now have proper slugs

---

## 2. IMMEDIATE FIXES NEEDED (High Priority)

### 2.1 Payment Methods Configuration
**Issue:** Payment methods field is a simple ArrayField. No way to configure account numbers, instructions per method.

**Current Implementation:**
```python
# Tournament Model
payment_methods = ArrayField(
    models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES),
    blank=True,
    default=list,
    help_text='Accepted payment methods'
)
```

**Required Implementation:**
```python
# New TournamentPaymentMethod Model
class TournamentPaymentMethod(models.Model):
    """Configurable payment method for tournament entry fees"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='payment_configurations')
    method = models.CharField(max_length=50, choices=Tournament.PAYMENT_METHOD_CHOICES)
    is_enabled = models.BooleanField(default=True)
    
    # bKash Configuration
    bkash_merchant_number = models.CharField(max_length=20, blank=True)
    bkash_account_type = models.CharField(max_length=20, choices=[('personal', 'Personal'), ('merchant', 'Merchant')], default='personal')
    bkash_instructions = models.TextField(blank=True, help_text='Instructions for bKash payment')
    
    # Nagad Configuration
    nagad_account_number = models.CharField(max_length=20, blank=True)
    nagad_instructions = models.TextField(blank=True)
    
    # Rocket Configuration
    rocket_account_number = models.CharField(max_length=20, blank=True)
    rocket_instructions = models.TextField(blank=True)
    
    # Bank Transfer Configuration
    bank_name = models.CharField(max_length=100, blank=True)
    bank_account_number = models.CharField(max_length=50, blank=True)
    bank_account_name = models.CharField(max_length=100, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)
    bank_routing_number = models.CharField(max_length=50, blank=True)
    bank_instructions = models.TextField(blank=True)
    
    # Display order
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'method']
        unique_together = [('tournament', 'method')]
```

**Admin Interface:**
- Inline editor in TournamentAdmin
- Collapsible sections for each payment method
- Show/hide fields based on selected method
- Preview payment instructions before publishing

---

### 2.2 Tournament End Field Removal
**Issue:** `tournament_end` field is automatically set but tournaments don't have fixed end dates - they end when matches are completed.

**Solution:**
1. Remove `tournament_end` from Tournament model (keep `tournament_start`)
2. Add computed property `estimated_end_date` based on format and participant count
3. Track actual completion via `completed_at` timestamp (already exists)

```python
@property
def estimated_end_date(self):
    """Estimate tournament end based on format and participants"""
    if not self.tournament_start:
        return None
    
    # Single Elimination: log2(n) rounds, ~2 hours per round
    if self.format == self.SINGLE_ELIM:
        import math
        rounds = math.ceil(math.log2(self.max_participants))
        hours = rounds * 2
        return self.tournament_start + timedelta(hours=hours)
    
    # Add logic for other formats
    ...
```

---

### 2.3 Rules: Text + PDF Upload
**Issue:** Rules are text-only. Need option to upload PDF for detailed rules.

**Solution:**
```python
# Add to Tournament Model
rules_text = models.TextField(blank=True, help_text='Tournament rules in text format')
rules_pdf = models.FileField(upload_to='tournaments/rules/', blank=True, null=True, help_text='Rules document (PDF)')

# Validation: At least one must be provided
def clean(self):
    if not self.rules_text and not self.rules_pdf:
        raise ValidationError('Either rules text or rules PDF must be provided.')
```

**Admin:**
- Show both fields
- Add preview button for PDF
- Warning if both are empty

---

### 2.4 Terms & Conditions
**Issue:** No terms and conditions field. Every tournament should have T&C.

**Solution:**
```python
# Add to Tournament Model
terms_and_conditions = models.TextField(blank=True, help_text='Terms and conditions all participants must agree to')
terms_pdf = models.FileField(upload_to='tournaments/terms/', blank=True, null=True, help_text='Terms & Conditions document (PDF)')
require_terms_acceptance = models.BooleanField(default=True, help_text='Participants must explicitly accept terms')

# On Registration form
acceptance_timestamp = models.DateTimeField(null=True, blank=True)
accepted_by_ip = models.GenericIPAddressField(null=True, blank=True)
```

---

### 2.5 Official Tournament Auto-Organizer
**Issue:** When `is_official=True`, should automatically set organizer to DeltaCrown, hide organizer field.

**Solution:**
```python
# In Tournament Model
def save(self, *args, **kwargs):
    if self.is_official and not self.organizer_id:
        # Get or create official DeltaCrown account
        official_user, _ = User.objects.get_or_create(
            username='deltacrown_official',
            defaults={
                'email': 'official@deltacrown.gg',
                'first_name': 'DeltaCrown',
                'last_name': 'Official',
                'is_staff': True
            }
        )
        self.organizer = official_user
    super().save(*args, **kwargs)
```

**Admin:**
```python
# In TournamentAdmin
def get_fields(self, request, obj=None):
    fields = super().get_fields(request, obj)
    if obj and obj.is_official:
        # Hide organizer field for official tournaments
        fields = [f for f in fields if f != 'organizer']
    return fields

def get_readonly_fields(self, request, obj=None):
    readonly = list(super().get_readonly_fields(request, obj))
    if obj and obj.is_official:
        readonly.append('organizer')
    return readonly
```

---

## 3. MAJOR FEATURES NEEDED (Medium-High Priority)

### 3.1 Tournament Staff Management System

**Requirements:**
- Assign multiple staff members to tournament
- Each staff has specific role with permissions
- Roles: Participant Reviewer, Support Staff, Bracket Manager, Scorecard Manager, Social Media Manager, Dispute Resolver
- Staff can only access their assigned areas
- Audit trail of staff actions

**Implementation:**

```python
# New Model: TournamentStaffRole
class TournamentStaffRole(models.Model):
    """Define staff roles and permissions"""
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    
    # Permissions
    can_review_participants = models.BooleanField(default=False)
    can_verify_payments = models.BooleanField(default=False)
    can_manage_brackets = models.BooleanField(default=False)
    can_manage_matches = models.BooleanField(default=False)
    can_enter_scores = models.BooleanField(default=False)
    can_handle_disputes = models.BooleanField(default=False)
    can_send_notifications = models.BooleanField(default=False)
    can_manage_social_media = models.BooleanField(default=False)
    can_access_support = models.BooleanField(default=False)
    can_modify_tournament = models.BooleanField(default=False)
    
    # Access levels
    can_view_pii = models.BooleanField(default=False, help_text='Can view personally identifiable information')
    can_view_payment_proofs = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Tournament Staff Role'
        verbose_name_plural = 'Tournament Staff Roles'

# New Model: TournamentStaff
class TournamentStaff(models.Model):
    """Assign staff to tournaments with specific roles"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='staff_assignments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournament_staff_roles')
    role = models.ForeignKey(TournamentStaffRole, on_delete=models.PROTECT)
    
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='staff_assignments_made')
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text='Internal notes about this staff assignment')
    
    class Meta:
        unique_together = [('tournament', 'user', 'role')]
        ordering = ['role__name', 'user__username']

# Default Roles to Create
DEFAULT_STAFF_ROLES = [
    {
        'name': 'Participant Reviewer',
        'slug': 'participant-reviewer',
        'description': 'Reviews and verifies participant registrations',
        'permissions': {
            'can_review_participants': True,
            'can_view_pii': True,
        }
    },
    {
        'name': 'Payment Verifier',
        'slug': 'payment-verifier',
        'description': 'Verifies payment proofs and entry fees',
        'permissions': {
            'can_verify_payments': True,
            'can_view_payment_proofs': True,
            'can_view_pii': True,
        }
    },
    {
        'name': 'Bracket Manager',
        'slug': 'bracket-manager',
        'description': 'Manages tournament brackets and match scheduling',
        'permissions': {
            'can_manage_brackets': True,
            'can_manage_matches': True,
        }
    },
    {
        'name': 'Scorekeeper',
        'slug': 'scorekeeper',
        'description': 'Enters and verifies match scores',
        'permissions': {
            'can_enter_scores': True,
            'can_manage_matches': True,
        }
    },
    {
        'name': 'Dispute Resolver',
        'slug': 'dispute-resolver',
        'description': 'Handles match disputes and protests',
        'permissions': {
            'can_handle_disputes': True,
            'can_view_pii': True,
        }
    },
    {
        'name': 'Support Staff',
        'slug': 'support-staff',
        'description': 'Provides participant support and answers questions',
        'permissions': {
            'can_access_support': True,
            'can_view_pii': True,
        }
    },
    {
        'name': 'Social Media Manager',
        'slug': 'social-media',
        'description': 'Manages tournament social media and announcements',
        'permissions': {
            'can_send_notifications': True,
            'can_manage_social_media': True,
        }
    },
    {
        'name': 'Tournament Admin',
        'slug': 'tournament-admin',
        'description': 'Full access to all tournament management features',
        'permissions': {
            'can_review_participants': True,
            'can_verify_payments': True,
            'can_manage_brackets': True,
            'can_manage_matches': True,
            'can_enter_scores': True,
            'can_handle_disputes': True,
            'can_send_notifications': True,
            'can_manage_social_media': True,
            'can_access_support': True,
            'can_modify_tournament': True,
            'can_view_pii': True,
            'can_view_payment_proofs': True,
        }
    },
]
```

**Admin Interface:**
- Inline StaffAssignment editor in TournamentAdmin
- Filterable by role
- Bulk assign staff
- Permission preview

**Organizer Console Integration:**
- Staff management tab
- Assign/remove staff
- View staff activity logs
- Permission matrix view

---

### 3.2 Participant Information Display

**Requirements:**
- Show detailed registration information to organizers and staff
- Team rosters with player names, game IDs, contact info
- Registration timestamps, payment status
- Custom field responses
- Export to CSV/Excel

**Implementation:**

**Organizer Console - Participants Tab:**
```
[Search: ___________] [Filter: All | Confirmed | Pending | Rejected]

Participants (15/16 registered)

┌─────────────────────────────────────────────────────────────────────┐
│ #1 - Dhaka Dragons (Team)                                 CONFIRMED │
│ Captain: alex_gaming (alex.rahman@gmail.com)                        │
│ Roster:                                                              │
│   • alex_gaming - Duelist - Riot ID: DhakaDragon#0001               │
│   • shadow_striker - Controller - Riot ID: ShadowStrike#BD1         │
│   • nova_star - Sentinel - Riot ID: NovaStar#7777                   │
│   • phoenix_rising - Initiator - Riot ID: PhoenixBD#2025            │
│   • cyber_wolf - Flex - Riot ID: CyberWolf#MLBB                     │
│ Registered: Nov 12, 2025 10:30 AM                                   │
│ Payment: ✓ Verified (bKash - TXN12345)                              │
│ [View Details] [Message Team] [Download Info]                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ #2 - Bengal Tigers (Team)                                 CONFIRMED │
│ ...                                                                  │
└─────────────────────────────────────────────────────────────────────┘

[Export All] [Export Confirmed Only] [Email All]
```

**Backend:**
```python
# In Organizer Console View
def participants_list(request, tournament_slug):
    tournament = get_object_or_404(Tournament, slug=tournament_slug)
    
    # Check permission
    if not (tournament.organizer == request.user or 
            tournament.staff_assignments.filter(
                user=request.user, 
                role__can_review_participants=True
            ).exists()):
        raise PermissionDenied
    
    registrations = tournament.registrations.select_related(
        'user', 'team'
    ).prefetch_related(
        'team__memberships__profile__user'
    ).annotate(
        payment_status=Case(
            When(payments__status='verified', then=Value('verified')),
            When(payments__status='submitted', then=Value('pending')),
            default=Value('none'),
            output_field=CharField()
        )
    ).order_by('slot_number', 'registered_at')
    
    return render(request, 'tournaments/organizer/participants.html', {
        'tournament': tournament,
        'registrations': registrations,
    })
```

---

### 3.3 Notification Management System

**Requirements:**
- Configure which notifications to send (registration confirmed, payment verified, match scheduled, etc.)
- Preview notifications before sending
- Send test notifications
- Schedule notifications
- Track delivery status
- Template customization

**Implementation:**

```python
# New Model: TournamentNotificationTemplate
class TournamentNotificationTemplate(models.Model):
    """Customizable notification templates for tournaments"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name='notification_templates')
    event_type = models.CharField(max_length=50, choices=[
        ('registration_confirmed', 'Registration Confirmed'),
        ('payment_verified', 'Payment Verified'),
        ('match_scheduled', 'Match Scheduled'),
        ('match_starting_soon', 'Match Starting Soon (30 min)'),
        ('match_live', 'Match is Live'),
        ('match_completed', 'Match Completed'),
        ('bracket_updated', 'Bracket Updated'),
        ('dispute_resolved', 'Dispute Resolved'),
        ('tournament_starting_soon', 'Tournament Starting Soon'),
        ('tournament_completed', 'Tournament Completed'),
    ])
    
    is_enabled = models.BooleanField(default=True)
    send_email = models.BooleanField(default=True)
    send_in_app = models.BooleanField(default=True)
    send_discord = models.BooleanField(default=False)
    
    # Email Template
    email_subject = models.CharField(max_length=200)
    email_body_html = models.TextField()
    email_body_text = models.TextField()
    
    # In-App Notification
    notification_title = models.CharField(max_length=100)
    notification_message = models.TextField()
    
    # Timing
    send_delay_minutes = models.IntegerField(default=0, help_text='Send X minutes after event (0 = immediate)')
    
    class Meta:
        unique_together = [('tournament', 'event_type')]

# New Model: NotificationLog
class NotificationLog(models.Model):
    """Track notification delivery"""
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50)
    
    sent_at = models.DateTimeField(auto_now_add=True)
    delivery_method = models.CharField(max_length=20, choices=[
        ('email', 'Email'),
        ('in_app', 'In-App'),
        ('discord', 'Discord'),
    ])
    
    status = models.CharField(max_length=20, choices=[
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ])
    
    error_message = models.TextField(blank=True)
```

**Organizer Console - Notifications Tab:**
```
Configure Tournament Notifications

┌─────────────────────────────────────────────────────────────────────┐
│ Registration Confirmed                                      ✓ ENABLED│
│ Send via: [✓] Email [✓] In-App [ ] Discord                          │
│ Subject: Your registration for {{tournament.name}} is confirmed!    │
│ [Edit Template] [Preview] [Send Test]                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Payment Verified                                            ✓ ENABLED│
│ Send via: [✓] Email [✓] In-App [ ] Discord                          │
│ Subject: Payment confirmed - You're all set for {{tournament.name}}!│
│ [Edit Template] [Preview] [Send Test]                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│ Match Scheduled                                             ✓ ENABLED│
│ Send via: [✓] Email [✓] In-App [ ] Discord                          │
│ Delay: 0 minutes (send immediately)                                 │
│ Subject: Your match is scheduled for {{match.scheduled_time}}       │
│ [Edit Template] [Preview] [Send Test]                               │
└─────────────────────────────────────────────────────────────────────┘

[+ Add Custom Notification] [Save All]

Notification History (Last 7 days)
─────────────────────────────────────────────────────────────────────
Nov 16, 2:30 PM - Registration Confirmed → 15 recipients (15 delivered)
Nov 16, 3:15 PM - Payment Verified → 12 recipients (12 delivered)
Nov 17, 10:00 AM - Match Scheduled → 4 recipients (4 delivered)

[View Full History] [Export Logs]
```

---

### 3.4 Organizer Console Expansion

**Current State:** Basic console with limited features  
**Required Features:**

1. **Dashboard Tab** (✓ Partially exists)
   - Add: Quick actions, pending tasks, recent activity

2. **Participants Tab** (New)
   - List all registrations
   - Participant details with contact info
   - Payment verification interface
   - Export participant data

3. **Bracket Management Tab** (Needs expansion)
   - Visual bracket editor
   - Drag-and-drop seeding
   - Auto-generate brackets
   - Manual match adjustments

4. **Match Management Tab** (New)
   - Match list with filters (upcoming, live, completed)
   - Quick score entry
   - Reschedule matches
   - Mark no-shows/forfeits

5. **Disputes Tab** (New)
   - List all disputes
   - Dispute details with evidence
   - Resolution interface
   - Communication with parties

6. **Notifications Tab** (New - described above)

7. **Staff Management Tab** (New - described above)

8. **Analytics Tab** (New)
   - Registration timeline
   - Payment collection rate
   - Match completion rate
   - Participant engagement metrics

9. **Settings Tab** (Expand)
   - Tournament configuration
   - Payment methods setup
   - Rules & terms management
   - Feature toggles

---

## 4. IMPLEMENTATION TIMELINE

### Phase 1 (Week 1) - Critical Fixes
- ✅ Team URL slugs (COMPLETED)
- Payment methods configuration model + admin
- Terms & conditions fields
- Official tournament auto-organizer
- Rules PDF upload

### Phase 2 (Week 2) - Staff Management
- TournamentStaffRole model
- TournamentStaff model
- Default roles creation
- Admin interface for staff assignment
- Permission checking system

### Phase 3 (Week 3) - Participant Information
- Participants list view in organizer console
- Detailed participant information display
- Export functionality
- Contact/messaging interface

### Phase 4 (Week 4) - Notification System
- Notification template models
- Template editor interface
- Preview & test send functionality
- Delivery tracking
- Notification history

### Phase 5 (Week 5-6) - Organizer Console Expansion
- Match management tab
- Disputes tab
- Analytics tab
- Enhanced bracket management
- Settings consolidation

---

## 5. TESTING REQUIREMENTS

- Unit tests for all new models
- Integration tests for staff permissions
- E2E tests for organizer console workflows
- Load testing for notification system
- Security testing for PII access

---

## 6. DOCUMENTATION REQUIREMENTS

- Staff role permission matrix
- Organizer console user guide
- Notification template variables reference
- API documentation for staff endpoints
- Migration guides for existing tournaments

---

## STATUS TRACKING

| Feature | Status | Priority | ETA |
|---------|--------|----------|-----|
| Team URL Slugs | ✅ COMPLETE | High | Nov 17 |
| Payment Methods Config | 📋 PLANNED | High | Nov 19 |
| Terms & Conditions | 📋 PLANNED | High | Nov 19 |
| Official Tournament Auto-Organizer | 📋 PLANNED | Medium | Nov 20 |
| Staff Management System | 📋 PLANNED | High | Nov 24 |
| Participant Information Display | 📋 PLANNED | High | Nov 27 |
| Notification Management | 📋 PLANNED | High | Dec 1 |
| Organizer Console Expansion | 📋 PLANNED | Medium | Dec 8 |

---

**Next Steps:**
1. Review and approve this plan
2. Begin Phase 1 implementation
3. Create detailed tickets for each feature
4. Set up testing environment
5. Begin documentation drafts
