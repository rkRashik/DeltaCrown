# DeltaCrown — Tournament Management & Operations Master Plan v3.0

> **Version:** 3.0 (Supersedes v2.0)
> **Date:** February 19, 2026
> **Author:** Project Architect
> **Status:** Planning — Pending Final Review
> **Scope:** Registration System + Tournament Operations Center
> **Inputs:** 59 prior planning docs, platform research (Toornament, Battlefy, Start.gg, Challonge, FACEIT), codebase audit (33 views, 29 models, 40 services, 21 ops services), senior engineering review

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What Changed from v2.0](#2-what-changed-from-v20)
3. [Codebase Inventory — What Already Exists](#3-codebase-inventory--what-already-exists)
4. [Architecture Decisions](#4-architecture-decisions)
5. [Registration UX — Progressive Disclosure (Mobile-First)](#5-registration-ux--progressive-disclosure-mobile-first)
6. [Registration Flow — Solo Player](#6-registration-flow--solo-player)
7. [Registration Flow — Team](#7-registration-flow--team)
8. [Registration Flow — Guest Team (Abuse-Mitigated)](#8-registration-flow--guest-team-abuse-mitigated)
9. [Smart Auto-Fill System](#9-smart-auto-fill-system)
10. [Custom Questions & Dynamic Fields](#10-custom-questions--dynamic-fields)
11. [Payment System (With Migration Safety)](#11-payment-system-with-migration-safety)
12. [Organizer-Level Overrides & Refund Policy](#12-organizer-level-overrides--refund-policy)
13. [Registration Status Machine](#13-registration-status-machine)
14. [The Tournament Operations Center](#14-the-tournament-operations-center)
15. [TOC Module 1: Command Center (Home)](#15-toc-module-1-command-center-home)
16. [TOC Module 2: Participants & Registration Hub](#16-toc-module-2-participants--registration-hub)
17. [TOC Module 3: Bracket Generation & Seeding Engine](#17-toc-module-3-bracket-generation--seeding-engine)
18. [TOC Module 4: Match Operations & Live Control](#18-toc-module-4-match-operations--live-control)
19. [TOC Module 5: Scheduling & Check-In Control](#19-toc-module-5-scheduling--check-in-control)
20. [TOC Module 6: Dispute Resolution Center](#20-toc-module-6-dispute-resolution-center)
21. [TOC Module 7: Participant Data Control](#21-toc-module-7-participant-data-control)
22. [Notifications](#22-notifications)
23. [Anti-Fraud & Security](#23-anti-fraud--security)
24. [Implementation Phases](#24-implementation-phases)

---

## 1. Executive Summary

DeltaCrown aims to be the definitive competitive gaming platform for the Bangladesh esports ecosystem and beyond. This plan defines two interconnected systems:

**System A — Smart Registration:** A single-view, auto-fill, mobile-first registration path for solo, team, and guest-team participation with manual payment verification (bKash/Nagad/Rocket).

**System B — Tournament Operations Center (TOC):** A comprehensive organizer backend rivaling FACEIT, Toornament, and Battlefy — covering registration management, bracket generation, seeding, live match operations, scheduling, dispute resolution, and full participant data control.

### Design Principles

1. **One Registration Path** — `SmartRegistrationView` for everything. No parallel systems.
2. **Progressive Disclosure** — Clean by default, details on demand. Mobile-first.
3. **Manual-First, Automation-Ready** — Build human verification UI; wire API hooks later.
4. **Configuration Over Code** — Organizers configure via TOC UI, not developer deployments.
5. **Organizer-Centric** — The TOC proactively tells organizers what needs attention.
6. **Anti-Friction for Players** — Auto-fill everything. Never ask what we already know.
7. **Abuse-Aware** — Soft friction for abusable features (guest teams, waitlists).
8. **Data Safety** — Financial model migrations use atomic, reversible strategies.

---

## 2. What Changed from v2.0

| Area | v2.0 | v3.0 |
|------|------|------|
| **Registration UX** | All sections visible at once | Progressive Disclosure — clean default, issues collapsed behind "Fix issues" expander |
| **Mobile** | "Single page" mentioned | Sticky section headers, jump-to-section mini-nav, auto-scroll to first error |
| **Guest Teams** | Unlimited, smart conversion in same phase | Soft-capped per tournament (`max_guest_teams`), conversion deferred to Phase 4 |
| **Payment Migration** | "Merge PaymentVerification into Payment" | Explicit 4-step atomic migration with rollback plan and data-loss protection |
| **Organizer Overrides** | Not addressed | Display name override toggle, refund policy toggles, refund visibility on registration form |
| **Organizer Dashboard** | Registration + payment verification only | Full **Tournament Operations Center** with 7 modules |
| **Bracket Management** | Referenced but not designed | Full spec: SE/DE/RR/Swiss, drag-drop seeding, live draws, DQ/drop |
| **Match Operations** | Not in plan | Match Medic mode, force-start, manual score, penalty system, live dispute resolution |
| **Scheduling** | Basic check-in | Round-by-round scheduling, breaks, rescheduling, conflict detection |
| **Participant Control** | Approve/reject only | Manual add, name changes, free agent pool, roster swaps, DQ with cascading bracket effects |
| **Scope** | Registration system plan | Full tournament management & operations suite |

---

## 3. Codebase Inventory — What Already Exists

### Models (29 files in `apps/tournaments/models/`)

| Category | Models | Status |
|----------|--------|--------|
| **Tournament** | `Tournament` (877 lines), `CustomField`, `TournamentVersion` | ✅ Working |
| **Registration** | `Registration` (626 lines), Phase 5 models: `RegistrationQuestion`, `RegistrationDraft`, `RegistrationAnswer`, `RegistrationRule` | ✅ Working (Phase 5 models unused) |
| **Payment** | `Payment` (in registration.py) + `PaymentVerification` (separate) | ⚠️ Dual model problem |
| **Bracket** | `Bracket`, `BracketNode` (462 lines), `BracketEditLog` | ✅ Working |
| **Stage** | `TournamentStage` (243 lines) | ✅ Working |
| **Group** | `Group`, `GroupStanding`, `GroupStage` (523 lines) | ✅ Working |
| **Match** | `Match` (570 lines), `MatchOperationLog`, `MatchModeratorNote` | ✅ Working |
| **Result** | `TournamentResult` (293 lines), `MatchResultSubmission` (233 lines) | ✅ Working |
| **Dispute** | `Dispute` (legacy), `DisputeRecord` (Phase 6, 255 lines) | ✅ Working |
| **Staff** | `TournamentStaff`, `StaffAssignment` | ✅ Working |

### Services (40 + 21 files)

| Category | Service | Lines | Status |
|----------|---------|-------|--------|
| **Registration** | `registration_service.py` | 1,999 | ✅ Working |
| **Auto-fill** | `registration_autofill.py` | 503 | ✅ Working |
| **Eligibility** | `registration_eligibility.py` | 270 | ✅ Working |
| **Bracket** | `bracket_service.py` | 1,498 | ✅ Working |
| **Bracket (Universal)** | `bracket_engine_service.py` | 267 | ✅ Working |
| **Bracket Generators** | SE (223), DE (359), RR (149), Swiss (377) | — | ✅ SE/DE/RR, ⚠️ Swiss R2+ TODO |
| **Bracket Editor** | `bracket_editor_service.py` | 427 | ✅ Working |
| **Match** | `match_service.py` | 1,318 | ✅ Working |
| **Match Ops (MOCC)** | `match_ops_service.py` | 632 | ✅ Working |
| **Group Stage** | `group_stage_service.py` | 1,167 | ✅ Working |
| **Stage Transition** | `stage_transition_service.py` | 466 | ✅ Working |
| **Winner** | `winner_service.py` | 926 | ✅ Working |
| **Scheduling** | `manual_scheduling_service.py` | 405 | ✅ Working |
| **Check-in** | `checkin_service.py` | 453 | ✅ Working |
| **Dispute** | `dispute_service.py` | 651 | ✅ Working |
| **Result Submission** | `result_submission_service.py` | 500 | ✅ Working |
| **Staffing** | `staffing_service.py` | 563 | ✅ Working |
| **Lifecycle** | `lifecycle_service.py` | 334 | ✅ Working |
| **Tournament Ops** | `tournament_ops_service.py` | 2,829 | ✅ Working |

### Views (33 files, ~7,165 lines)

| Category | View File | Lines | Status |
|----------|-----------|-------|--------|
| **Organizer Hub** | `organizer.py` | 654 | ✅ Working (tab-based management) |
| **Organizer Matches** | `organizer_matches.py` | 150 | ✅ Working |
| **Organizer Participants** | `organizer_participants.py` | 165 | ✅ Working |
| **Organizer Payments** | `organizer_payments.py` | 148 | ✅ Working |
| **Organizer Results** | `organizer_results.py` | 248 | ✅ Working |
| **Smart Registration** | `smart_registration.py` | 446 | ✅ Working |
| **Group Stage** | `group_stage.py` | 316 | ✅ Working |
| **Live/Bracket** | `live.py` | 375 | ✅ Working |
| **Match Room** | `match_room.py` | 244 | ✅ Working |
| **Dispute** | `dispute_resolution.py` + `disputes_management.py` | 317 | ✅ Working |
| **Check-in** | `checkin.py` | 409 | ✅ Working |

### Templates

Existing template directories: `templates/tournaments/organizer/`, `templates/tournaments/manage/`, `templates/tournaments/registration/`, `templates/tournaments/public/`, `templates/tournaments/match_room/`, `templates/tournaments/groups/`, `templates/tournaments/emails/`.

### URL Patterns

30+ organizer URLs already exist under `organizer/<slug>/` covering: match operations, participant management, payment verification, dispute resolution, group configuration, health metrics, and CSV exports.

### The Key Insight

**The backend is largely built.** Models, services, and many views exist for brackets, matches, disputes, scheduling, and check-in. What's missing is:

1. **A unified, polished frontend** — The TOC UI that ties all modules into one cohesive experience
2. **Smart Registration UX upgrades** — Progressive disclosure, guest team hardening, custom question wiring
3. **Glue code** — Connecting existing services to the TOC views and templates
4. **Swiss rounds 2+** — The only significant service gap

---

## 4. Architecture Decisions

### Decision 1: Single View, Multiple Registration Modes

```
SmartRegistrationView (upgraded)
├── Mode: SOLO
├── Mode: TEAM
└── Mode: GUEST_TEAM (capped, always needs_review)
```

### Decision 2: Tournament Operations Center as Tab-Based Hub

```
/tournaments/<slug>/manage/              → TOC Command Center (Home)
/tournaments/<slug>/manage/participants/ → Participants & Registration Hub
/tournaments/<slug>/manage/brackets/     → Bracket Generation & Seeding
/tournaments/<slug>/manage/matches/      → Match Operations & Live Control
/tournaments/<slug>/manage/schedule/     → Scheduling & Check-In
/tournaments/<slug>/manage/disputes/     → Dispute Resolution Center
/tournaments/<slug>/manage/settings/     → Tournament Settings & Configuration
```

The existing `OrganizerHubView` already supports tab routing. We upgrade it from a basic management page into the full TOC by expanding the tab system and building the matching templates.

### Decision 3: Progressive Disclosure for Registration

```
DEFAULT STATE (Clean):
  ┌────────────────────────────┐
  │ Everything looks good ✅    │
  │ Your profile is 100% ready │
  └────────────────────────────┘

IF ISSUES EXIST:
  ┌────────────────────────────┐
  │ 2 items need attention ⚠️  │
  │ [Fix issues ▾]             │
  │   ├─ Missing phone number  │
  │   └─ Discord not linked    │
  └────────────────────────────┘
```

### Decision 4: Guest Team Soft-Friction Cap

```python
# Tournament model addition
max_guest_teams = models.PositiveIntegerField(
    default=0,  # 0 = guest teams disabled
    help_text="Maximum guest teams allowed (0 = disabled)"
)
```

This replaces the boolean `allow_guest_teams`. Value of 0 means disabled, any positive integer caps the count. Guest-to-Real-Team conversion deferred to Phase 4.

### Decision 5: Atomic Payment Model Migration

See Section 11 for the full 4-step safe migration plan.

---

## 5. Registration UX — Progressive Disclosure (Mobile-First)

### The Problem

Displaying readiness bars, locked-field icons, auto-fill warnings, custom questions, and payment info simultaneously overwhelms new mobile users. Research from Toornament and Battlefy shows simpler forms convert better.

### The Fix: Three-Layer Progressive Disclosure

**Layer 1 — The Summary Bar (Always Visible)**

```
┌────────────────────────────────────────────────┐
│ ✅ Your profile is ready         [Submit ▶]   │
└────────────────────────────────────────────────┘

  OR (if issues):

┌────────────────────────────────────────────────┐
│ ⚠️ 2 items need attention       [Fix issues ▾]│
└────────────────────────────────────────────────┘
```

**Layer 2 — Collapsible Sections (Expandable)**

Each section is collapsed by default if fully auto-filled and valid. Only sections that need attention are auto-expanded:

```
▼ Player Info ✅ (auto-filled)      ← collapsed, green check
▼ Game Info ✅ (auto-filled)        ← collapsed, green check
▶ Custom Questions (2 required)     ← expanded, needs input
▼ Payment ✅ (DeltaCoin selected)   ← collapsed if selected
```

**Layer 3 — Detail Popups (On Demand)**

Locked fields show an info tooltip on tap: "This comes from your verified profile. Update it in Settings."

### Mobile-Specific Enhancements

| Feature | Implementation |
|---------|---------------|
| **Sticky section headers** | CSS `position: sticky; top: 0;` on section headers |
| **Jump-to-section mini-nav** | Floating bottom bar with section dots (like carousel indicators) |
| **Auto-scroll to first error** | On submit failure, `scrollIntoView({ behavior: 'smooth' })` first error |
| **Touch-friendly controls** | Min 48px tap targets, select dropdowns instead of radio for >3 options |
| **Offline-aware auto-save** | `localStorage` draft if network lost, sync when reconnected |

### Desktop vs Mobile Rendering

| Element | Desktop | Mobile |
|---------|---------|--------|
| Form layout | Two-column (info left, preview right) | Single-column stacked |
| Section headers | Sticky at scroll position | Sticky + mini-nav dots |
| Payment instructions | Side panel | Full-width accordion |
| Readiness indicator | Top bar with percentage | Simple ✅/⚠️ icon |
| Custom questions | Inline in form | Separate collapsible section |

---

## 6. Registration Flow — Solo Player

### End-to-End Walkthrough

1. Player visits `/tournaments/<slug>/register/`
2. `SmartRegistrationView` runs eligibility pre-check (async)
3. Auto-fill fires: pulls from `UserProfile`, `GamePassport`, prior registrations
4. **Progressive Disclosure UI** renders:
   - All valid sections collapsed with ✅
   - Any sections needing input auto-expanded with ⚠️
   - Summary bar shows overall readiness
5. Player reviews collapsed sections (can expand any to verify)
6. If custom questions exist, that section is expanded — player fills answers
7. Payment section (if paid tournament):
   - Refund policy displayed with required acceptance checkbox
   - Payment method selection (bKash/Nagad/Rocket/DeltaCoin)
   - Upload proof area active after acceptance
8. Player hits Submit
9. Registration created:
   - Free + auto-approve → `confirmed`
   - Paid → `submitted` → payment instructions displayed → status becomes `pending` after proof upload
   - Manual-approve → `submitted` → organizer reviews

### Auto-Fill Field Sources

| Field | Source | Locked? |
|-------|--------|---------|
| Full Name | `UserProfile.full_name` | Yes (verified) |
| Email | `User.email` | Yes |
| Game ID / IGN | `GamePassport.game_id` | Yes (verified by game) |
| Rank | `GamePassport.rank` | Yes |
| Phone | `UserProfile.phone_number` | Yes |
| Discord | `UserProfile.discord_tag` | Yes |
| Display Name | New field (if override enabled) | Editable |

---

## 7. Registration Flow — Team

### End-to-End Walkthrough

1. Team captain/manager/owner visits `/tournaments/<slug>/register/`
2. `SmartRegistrationView` detects team tournament, shows team selection
3. If user has exactly 1 eligible team → auto-selected
4. If multiple teams → dropdown with eligibility badges per team
5. Roster displayed: each member's game ID status shown (✅ verified, ⚠️ missing)
6. Auto-fill pulls from team's collective `GamePassport` data
7. Progressive Disclosure: collapsed if all members have valid Game IDs
8. Captain can optionally select starting lineup (for games with roster size > team size)
9. **Lineup snapshot** stored in `Registration.lineup_snapshot` (JSON array of member IDs + game IDs)
10. Payment + submit same as solo flow

### Permission Check

```python
# Who can register a team:
ALLOWED_ROLES = ['owner', 'manager', 'captain']
# Already enforced in SmartRegistrationView._resolve_team()
```

### Roster Validation

- Minimum roster size check against `Tournament.team_size_min`
- Maximum roster size check against `Tournament.team_size_max`
- All members must have `GamePassport` for tournament's game
- Members cannot be registered with another team in same tournament

---

## 8. Registration Flow — Guest Team (Abuse-Mitigated)

### Changes from v2.0

| Aspect | v2.0 | v3.0 |
|--------|------|------|
| Toggle | Boolean `allow_guest_teams` | Integer `max_guest_teams` (0=disabled, N=cap) |
| Verification | "Needs review" | "Needs review" + soft friction (captain must write justification) |
| Conversion | Same phase as guest reg | Deferred to Phase 4 |
| Rate limit | None | Max 1 guest team registration per user per tournament |

### Flow

1. Player selects "Register as Guest Team" (only shown if `max_guest_teams > 0` and not at cap)
2. **Soft friction UI** shown:

```
┌───────────────────────────────────────────────────┐
│ Guest Team Registration                            │
│                                                     │
│ ℹ️ Guest teams require manual verification by the   │
│ organizer. This may take up to 24 hours.            │
│                                                     │
│ Guest team slots: 2/5 remaining                     │
│                                                     │
│ Team Name:     [________________________]           │
│ Team Tag:      [______]                             │
│ Captain Name:  [________________________]           │
│ Captain Email: [________________________]           │
│                                                     │
│ Member 1 IGN:  [________________________]           │
│ Member 2 IGN:  [________________________]           │
│ Member 3 IGN:  [________________________]           │
│ Member 4 IGN:  [________________________]           │
│ Member 5 IGN:  [________________________]           │
│                                                     │
│ Why is your team not on DeltaCrown? (required)      │
│ [We are new to the platform and haven't ___________]│
│ [created accounts yet.                    ]         │
│                                                     │
│ This helps the organizer verify your team faster.   │
└───────────────────────────────────────────────────┘
```

3. On submit:
   - Registration created with `is_guest_team=True`, `status='needs_review'`
   - Guest team data stored in `Registration.data` JSONB
   - Counter incremented against `max_guest_teams` cap
   - Organizer notified via Command Center alert

### Organizer-Side Guest Team Controls

```python
# Tournament model addition
max_guest_teams = models.PositiveIntegerField(
    default=0,
    help_text="Maximum guest teams allowed (0 = disabled)"
)

# Runtime validation in SmartRegistrationView
current_guest_count = Registration.objects.filter(
    tournament=tournament,
    is_guest_team=True,
    status__in=['submitted', 'pending', 'needs_review', 'confirmed']
).count()
if current_guest_count >= tournament.max_guest_teams:
    raise ValidationError("Guest team limit reached for this tournament.")

# Per-user rate limit
user_guest_count = Registration.objects.filter(
    tournament=tournament,
    is_guest_team=True,
    registered_by=user
).count()
if user_guest_count >= 1:
    raise ValidationError("You can only register one guest team per tournament.")
```

### Guest-to-Real-Team Conversion (Phase 4 — NOT in MVP)

The invite-link conversion path is architecturally valid but adds significant complexity. Deferred until Phase 4 (Automation) so we can:

1. Auto-match game IDs when teammates create accounts
2. Auto-link via verified Game Passport data
3. Trigger conversion without organizer intervention
4. Handle partial conversions (3 of 5 members joined)

---

## 9. Smart Auto-Fill System

### Architecture

```
SmartRegistrationView.get_context_data()
  └── RegistrationAutofillService.get_autofill_data(user, tournament)
        ├── UserProfile fields (name, email, phone, discord)
        ├── GamePassport fields (game_id, rank, server)
        ├── Previous registration data (same game tournaments)
        └── Team data (if team mode)
```

### Auto-Fill Behavior

| Scenario | Behavior |
|----------|----------|
| Field has verified data | Locked (read-only), green ✅, collapsed in progressive disclosure |
| Field has unverified data | Pre-filled but editable, yellow ⚠️ |
| Field has no data | Empty, section auto-expanded, field highlighted |
| Field from previous registration | Pre-filled, tooltip "From your last registration" |

### Progressive Disclosure Integration

Auto-filled sections are **collapsed by default** when all fields are valid. Users see:

```
▼ Player Info ✅ (auto-filled from profile)
   Name: John Doe (locked)
   Email: john@example.com (locked)
   Phone: +8801XXXXXXXXX (locked)
```

They can click to expand and review, but don't need to interact if everything is correct. This dramatically reduces form completion time on mobile.

---

## 10. Custom Questions & Dynamic Fields

### Models (Already Exist — Unused)

```python
# apps/tournaments/models/smart_registration.py (454 lines)
class RegistrationQuestion(models.Model):
    tournament = models.ForeignKey(Tournament)
    label = models.CharField(max_length=200)
    field_type = models.CharField(choices=FIELD_TYPES)  # text, number, select, checkbox, file
    required = models.BooleanField(default=False)
    options = models.JSONField(default=list)  # For select/radio
    order = models.PositiveIntegerField(default=0)
    help_text = models.CharField(max_length=500, blank=True)

class RegistrationAnswer(models.Model):
    registration = models.ForeignKey(Registration)
    question = models.ForeignKey(RegistrationQuestion)
    value = models.TextField()

class RegistrationDraft(models.Model):
    user = models.ForeignKey(User)
    tournament = models.ForeignKey(Tournament)
    data = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)
```

### Wiring Plan (Phase 1)

1. `SmartRegistrationView.get_context_data()` — query `RegistrationQuestion.objects.filter(tournament=tournament).order_by('order')`
2. Template renders questions in a dedicated "Custom Questions" collapsible section
3. On submit, `RegistrationAnswer` objects created for each question
4. Validation: required questions checked server-side
5. Organizer creates questions via TOC Settings panel

### Draft Auto-Save (Phase 2)

- Frontend: debounced `fetch()` call on field change → saves to `RegistrationDraft`
- Backend: AJAX endpoint `POST /tournaments/<slug>/register/draft/` → upsert `RegistrationDraft`
- On page load: if draft exists, pre-fill form from draft (overrides auto-fill for edited fields)
- On successful registration: delete draft

---

## 11. Payment System (With Migration Safety)

### Current State

Two models track overlapping data for the same financial event:

- `Payment` (in `apps/tournaments/models/registration.py`) — stores amount, method, transaction ID, proof image, status
- `PaymentVerification` (separate model) — stores verified_by, verified_at, rejection_reason, notes

### Architecture Decision: Consolidate to Single Payment Model

**Why:** Dual models create confusion, dual queries, and risk of desync.

**Risk:** Financial data migration can cause data loss or integrity violations.

### Safe Migration Strategy: 4-Step Atomic Migration

#### Step 1: Add New Fields (Non-Destructive)

```python
# Migration: 0XXX_add_verification_fields_to_payment.py
class Migration(migrations.Migration):
    operations = [
        migrations.AddField('Payment', 'verified_by', models.ForeignKey(
            'accounts.User', null=True, blank=True, on_delete=models.SET_NULL,
            related_name='verified_payments'
        )),
        migrations.AddField('Payment', 'verified_at', models.DateTimeField(null=True, blank=True)),
        migrations.AddField('Payment', 'rejection_reason', models.TextField(blank=True, default='')),
        migrations.AddField('Payment', 'verification_notes', models.TextField(blank=True, default='')),
        migrations.AddField('Payment', 'expires_at', models.DateTimeField(null=True, blank=True)),
    ]
```

**Rollback:** Simply remove the fields. No data affected.

#### Step 2: Data Migration (Copy, Don't Move)

```python
# Migration: 0XXX_copy_verification_data.py
def forward(apps, schema_editor):
    PaymentVerification = apps.get_model('tournaments', 'PaymentVerification')
    Payment = apps.get_model('tournaments', 'Payment')

    for pv in PaymentVerification.objects.select_related('payment').all():
        if pv.payment_id:
            Payment.objects.filter(id=pv.payment_id).update(
                verified_by_id=pv.verified_by_id,
                verified_at=pv.verified_at,
                rejection_reason=pv.rejection_reason or '',
                verification_notes=pv.notes or '',
            )

def reverse(apps, schema_editor):
    # Reverse: clear the copied fields (safe — original PaymentVerification still exists)
    Payment = apps.get_model('tournaments', 'Payment')
    Payment.objects.all().update(
        verified_by=None, verified_at=None,
        rejection_reason='', verification_notes=''
    )
```

**Rollback:** Run reverse migration. Original `PaymentVerification` records untouched.

#### Step 3: Code Migration (Dual-Write Period)

Update all service code to:
- **Write** verification data to BOTH `Payment` fields AND `PaymentVerification` simultaneously
- **Read** from `Payment` fields first, fallback to `PaymentVerification`
- Run in production for 1-2 weeks to verify zero discrepancies
- Monitor with a management command that compares both sources

```python
# Verification command for dual-write period
def verify_payment_data_consistency():
    mismatches = []
    for pv in PaymentVerification.objects.select_related('payment').all():
        p = pv.payment
        if p.verified_by_id != pv.verified_by_id or p.verified_at != pv.verified_at:
            mismatches.append(pv.id)
    return mismatches
```

**Rollback:** Revert to reading from `PaymentVerification` only.

#### Step 4: Drop Old Model (After Confidence Period)

```python
# Migration: 0XXX_remove_payment_verification.py
# ONLY after 2+ weeks with zero dual-write discrepancies
class Migration(migrations.Migration):
    operations = [
        migrations.DeleteModel('PaymentVerification'),
    ]
```

**Rollback:** Re-create model from backup schema + restore data from DB backup.

### Payment Flows

#### Manual Payment (bKash/Nagad/Rocket)

```
Player                     System               Organizer
  │                          │                       │
  ├── Select bKash ──────────►│                       │
  │                          │                       │
  │◄── Show bKash number ────│                       │
  │    "Send ৳500 to         │                       │
  │     01XXXXXXXXX"         │                       │
  │                          │                       │
  ├── Upload proof image ────►│                       │
  │                          ├── Create Payment ─────►│
  │                          │   status=submitted     │
  │                          │                       │
  │◄── "Proof uploaded,      │◄── Verify/Reject ─────│
  │     awaiting review"     │                       │
  │                          │                       │
  │◄── Email: Verified! ─────│   status=verified     │
  │    Registration confirmed │                       │
```

#### DeltaCoin (Instant — Phase 4)

```
Player                     System
  │                          │
  ├── Select DeltaCoin ──────►│
  │                          ├── Check balance
  │                          ├── Deduct amount
  │                          ├── Payment status=verified
  │◄── Instantly confirmed ──│
```

---

## 12. Organizer-Level Overrides & Refund Policy

### Display Name Override

**Problem:** At LAN events, players' real names don't match their esports handles. Locked "Full Name" field frustrates organizers who want to use gamer tags.

**Solution:** Tournament-level toggle:

```python
# Tournament model addition
allow_display_name_override = models.BooleanField(
    default=False,
    help_text="Allow participants to use a custom display name instead of their profile name"
)
```

When enabled:
- Registration form adds an editable "Display Name" field below the locked "Full Name"
- Display name used in brackets, match rooms, and public displays
- Real name stored in registration data for organizer reference
- Default: OFF (standard tournaments use verified profile names)

When rendered in the registration form:

```
▶ Player Info ✅
   Full Name:    John Doe (locked — from profile)
   Display Name: [NightShade___________] ← editable
   ℹ️ This name will appear in brackets and match rooms.
```

### Refund Policy Configuration

**Problem:** Players upload bKash payment proofs without understanding refund rules. Disputes arise when tournaments are cancelled or players withdraw.

**Solution:** Tournament-level refund policy with mandatory user-facing visibility:

```python
# Tournament model additions
refund_policy = models.CharField(
    max_length=30,
    choices=[
        ('no_refund', 'Non-refundable'),
        ('refund_until_checkin', 'Refundable until check-in'),
        ('refund_until_bracket', 'Refundable until bracket generation'),
        ('full_refund', 'Fully refundable anytime'),
        ('custom', 'Custom policy'),
    ],
    default='no_refund'
)
refund_policy_text = models.TextField(
    blank=True,
    help_text="Custom refund policy text (Markdown). Shown to users before payment."
)
```

### User-Facing Refund Display (Mandatory Before Payment)

On the payment section of the registration form, BEFORE the upload area:

```
┌──────────────────────────────────────────────────┐
│ ⚠️ Refund Policy                                  │
│                                                    │
│ This tournament's payments are NON-REFUNDABLE.     │
│ Once you upload your payment proof, the entry fee  │
│ will not be returned if you withdraw.              │
│                                                    │
│ □ I understand and accept the refund policy         │
└──────────────────────────────────────────────────┘
```

The checkbox is **required** before the "Upload Proof" button becomes active. This explicit consent protects both organizers and the platform from payment disputes.

### Organizer-Configurable Overrides Summary

| Toggle | Field | Default | Where Configured |
|--------|-------|---------|-----------------|
| Display name override | `allow_display_name_override` | OFF | TOC Settings |
| Refund policy | `refund_policy` | `no_refund` | TOC Settings |
| Custom refund text | `refund_policy_text` | Empty | TOC Settings |
| Guest team cap | `max_guest_teams` | 0 (disabled) | TOC Settings |
| Auto-approve registrations | `auto_approve` (existing) | OFF | TOC Settings |
| Require payment | `entry_fee > 0` (existing) | — | Tournament Create |

---

## 13. Registration Status Machine

### Status Values (11 states — existing)

```
              ┌──────────┐
              │  DRAFT   │ (auto-saved, not submitted)
              └────┬─────┘
                   │ submit
              ┌────▼─────┐
         ┌────│SUBMITTED │────┐
         │    └────┬─────┘    │
    auto_approve   │          │ needs_review
         │    ┌────▼─────┐    │
         │    │ PENDING  │    │
         │    └────┬─────┘    │
         │         │          │
    ┌────▼─────┐   │    ┌─────▼──────┐
    │CONFIRMED │   │    │NEEDS_REVIEW│
    └────┬─────┘   │    └─────┬──────┘
         │         │          │ approve/reject
         │    ┌────▼─────┐    │
         │    │ APPROVED │◄───┘
         │    └────┬─────┘
         │         │ payment verified
    ┌────▼─────────▼─────┐
    │    CONFIRMED       │
    └────┬───────────────┘
         │
    ┌────▼─────┐  ┌──────────┐  ┌──────────┐
    │CHECKED_IN│  │DISQUALIF.│  │WITHDRAWN │
    └──────────┘  └──────────┘  └──────────┘
                  ┌──────────┐  ┌──────────┐
                  │WAITLISTED│  │ REJECTED │
                  └──────────┘  └──────────┘
                  ┌──────────┐
                  │ EXPIRED  │
                  └──────────┘
```

### XOR Constraint

Each registration is EITHER player-based or team-based, enforced by the existing XOR constraint:

```python
# Existing on Registration model
class Meta:
    constraints = [
        models.CheckConstraint(
            check=Q(player__isnull=False, team__isnull=True) |
                  Q(player__isnull=True, team__isnull=False),
            name='registration_xor_player_team'
        ),
    ]
```

Guest teams use `team__isnull=True` + `is_guest_team=True` + `data` JSONB for guest roster.

---

## 14. The Tournament Operations Center

### Vision

The TOC transforms the basic organizer dashboard into a **professional tournament management suite**. It is the single interface organizers use to run every aspect of their tournament — from the moment participants register to the moment winners are crowned.

### Competitive Comparison

| Feature | DeltaCrown TOC | FACEIT | Toornament | Battlefy |
|---------|---------------|--------|------------|---------|
| Registration management | ✅ Smart + guest | ✅ | ✅ | ✅ |
| Payment verification (manual) | ✅ bKash/Nagad | ❌ (Stripe only) | ❌ (Stripe only) | ❌ |
| Bracket generation | ✅ SE/DE/RR/Swiss | ✅ | ✅ | ✅ |
| Drag-drop seeding | ✅ Planned | ❌ | ✅ | ✅ |
| Live match ops | ✅ Match Medic | ✅ | ✅ | ⚠️ Basic |
| Dispute resolution | ✅ Built-in | ✅ | ⚠️ Basic | ⚠️ Basic |
| Manual scheduling | ✅ Conflict detection | ⚠️ Basic | ✅ | ⚠️ Basic |
| Proactive alerts | ✅ Command Center | ❌ | ❌ | ❌ |
| Guest team support | ✅ Unique | ❌ | ❌ | ❌ |
| Mobile money payments | ✅ BD-specific | ❌ | ❌ | ❌ |

### Technical Architecture

```
/tournaments/<slug>/manage/              → TOC Command Center
    ├── participants/                    → Module 2: Participant Hub
    ├── brackets/                        → Module 3: Bracket Engine
    ├── matches/                         → Module 4: Match Operations
    ├── schedule/                        → Module 5: Scheduling
    ├── disputes/                        → Module 6: Dispute Center
    ├── settings/                        → Module 7: Settings
    └── API endpoints for HTMX/AJAX

OrganizerHubView (existing, 654 lines)
    → Extended with tab routing for all 7 modules
    → Each module served as HTMX partial or full page
    → Shared base template: templates/tournaments/manage/_base.html (exists)
```

### URL Structure

Leverages existing `manage/` URLs and adds new ones:

```python
# Existing (keep)
path('manage/', OrganizerHubView.as_view(), name='organizer_hub'),
path('manage/participants/', ..., name='manage_participants'),
path('manage/payments/', ..., name='manage_payments'),
path('manage/brackets/', ..., name='manage_brackets'),
path('manage/disputes/', ..., name='manage_disputes'),
path('manage/settings/', ..., name='manage_settings'),

# New (add)
path('manage/matches/', ..., name='manage_matches'),
path('manage/schedule/', ..., name='manage_schedule'),
path('manage/matches/<int:match_id>/score/', ..., name='manage_match_score'),
path('manage/matches/<int:match_id>/force-start/', ..., name='manage_match_force_start'),
path('manage/brackets/generate/', ..., name='manage_bracket_generate'),
path('manage/brackets/seed/', ..., name='manage_bracket_seed'),
path('manage/schedule/checkin/', ..., name='manage_checkin_control'),
```

---

## 15. TOC Module 1: Command Center (Home)

### Purpose

The first thing an organizer sees. System-generated alerts and nudges so they never miss a required action. No digging through tabs — the Command Center tells you what needs attention RIGHT NOW.

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ 🏆 Valorant Champions Series 2026          [▶ Go Live]     │
│ Status: Registration Open │ 24/32 slots │ 3 days remaining  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ⚡ ACTION REQUIRED                                          │
│ ┌──────────────────────────────────────────────────────────┐│
│ │ ⚠️ 3 payments awaiting verification        [Review →]   ││
│ │ ⚠️ 2 guest teams need manual review        [Review →]   ││
│ │ ⚠️ 1 duplicate player detected             [Resolve →]  ││
│ │ ⚠️ 1 dispute filed on Match #7             [Review →]   ││
│ └──────────────────────────────────────────────────────────┘│
│                                                             │
│ 📊 QUICK STATS                                             │
│ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐               │
│ │ 24     │ │ 3      │ │ 18     │ │ 2      │               │
│ │Regist. │ │Pending │ │Confirm.│ │Waitlist│               │
│ └────────┘ └────────┘ └────────┘ └────────┘               │
│                                                             │
│ 📅 UPCOMING                                                │
│ ├─ Registration closes in 3 days                           │
│ ├─ Check-in opens Feb 25, 2:00 PM                          │
│ └─ Tournament starts Feb 25, 3:00 PM                       │
│                                                             │
│ 📋 TOURNAMENT LIFECYCLE                                    │
│ Registration ━━━━━●━━━━━ Brackets ─────── Live ─────── End │
│              [open]      [not generated]                    │
└─────────────────────────────────────────────────────────────┘
```

### Alert Generation Logic

Alerts are computed from existing services on each page load (no polling needed at MVP):

```python
def get_command_center_alerts(tournament):
    """Generate prioritized alerts for the Command Center."""
    alerts = []

    # P1: Pending payments
    pending_payments = Payment.objects.filter(
        registration__tournament=tournament,
        status='submitted'
    ).count()
    if pending_payments:
        alerts.append({
            'type': 'warning', 'priority': 1,
            'message': f'{pending_payments} payment(s) awaiting verification',
            'action_url': reverse('manage_payments', args=[tournament.slug]),
            'action_label': 'Review',
        })

    # P1: Guest teams needing review
    guest_reviews = Registration.objects.filter(
        tournament=tournament, is_guest_team=True, status='needs_review'
    ).count()
    if guest_reviews:
        alerts.append({
            'type': 'warning', 'priority': 1,
            'message': f'{guest_reviews} guest team(s) need manual review',
            'action_url': reverse('manage_participants', args=[tournament.slug]) + '?filter=guest',
            'action_label': 'Review',
        })

    # P2: Open disputes
    open_disputes = DisputeRecord.objects.filter(
        tournament=tournament, status__in=['open', 'under_review']
    ).count()
    if open_disputes:
        alerts.append({
            'type': 'warning', 'priority': 2,
            'message': f'{open_disputes} dispute(s) require attention',
            'action_url': reverse('manage_disputes', args=[tournament.slug]),
            'action_label': 'Review',
        })

    # P3: Check-in approaching (within 2 hours)
    # P3: Registration deadline approaching (within 24 hours)
    # P4: Bracket not yet generated (registration closed)

    return sorted(alerts, key=lambda a: a['priority'])
```

### Existing Code to Leverage

- `apps/tournaments/views/organizer.py` → `OrganizerHubView` (654 lines, already serves as home)
- `templates/tournaments/manage/overview.html` — existing template (upgrade it to Command Center)
- `apps/tournaments/views/health_metrics.py` (281 lines) — existing health/stats view

---

## 16. TOC Module 2: Participants & Registration Hub

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Participants (24 confirmed / 32 max)        [Export CSV ↓]  │
│                                                             │
│ [All] [Pending (5)] [Confirmed (18)] [Waitlist (2)]         │
│ [Payment Queue (3)] [Guest Teams (2)] [DQ'd (0)]            │
│                                                             │
│ Search: [________________] Filter: [Status ▼] [Type ▼]     │
│                                                             │
│ [☐ Select All] [Bulk: Approve ▼]                           │
│                                                             │
│ ┌───┬────────────────┬──────────┬─────────┬──────────┬────┐│
│ │ ☐ │ Name/Team      │ Status   │ Payment │ Date     │ ⋮  ││
│ ├───┼────────────────┼──────────┼─────────┼──────────┼────┤│
│ │ ☐ │ 🏆 Phoenix RSG │ ✅ Conf. │ ✅ Paid │ Feb 15   │ ▸  ││
│ │ ☐ │ 👤 NightShade  │ ⏳ Pend. │ 📤 Sent │ Feb 16   │ ▸  ││
│ │ ☐ │ 👥 Guest: Apex │ 🔍 Rev.  │ ❌ None │ Feb 17   │ ▸  ││
│ └───┴────────────────┴──────────┴─────────┴──────────┴────┘│
│                                                             │
│ Actions per row (⋮ menu):                                   │
│   • View Details                                            │
│   • Approve / Reject                                        │
│   • Toggle Check-In                                         │
│   • Send Message                                            │
│   • Change Status                                           │
│   • Transfer Registration                                   │
│   • Disqualify                                              │
│                                                             │
│ [← Previous] Page 1 of 3 [Next →]                          │
└─────────────────────────────────────────────────────────────┘
```

### Payment Verification Queue

Dedicated sub-tab showing only `payment.status = 'submitted'`:

```
┌─────────────────────────────────────────────────────────────┐
│ Payment Verification Queue (3 pending)                       │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ #VCS-2026-042 │ NightShade │ bKash │ ৳500              │ │
│ │ TxID: ABC123XYZ │ Submitted: Feb 16, 4:20 PM           │ │
│ │                                                         │ │
│ │ ┌──────────────────┐  [✅ Verify] [❌ Reject]          │ │
│ │ │ 📎 Proof Image   │  Reason: [________________]       │ │
│ │ │ (Click to zoom)  │                                    │ │
│ │ └──────────────────┘                                    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ #VCS-2026-044 │ BlazeMaster │ Nagad │ ৳500             │ │
│ │ TxID: DEF456UVW │ Submitted: Feb 17, 11:00 AM          │ │
│ │ ... (same layout)                                       │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Existing Code to Leverage

- `apps/tournaments/views/organizer_participants.py` (165 lines)
- `apps/tournaments/views/organizer_payments.py` (148 lines)
- `templates/tournaments/manage/participants.html` — existing stub
- `templates/tournaments/manage/payments.html` — existing stub

---

## 17. TOC Module 3: Bracket Generation & Seeding Engine

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Bracket & Seeding                                            │
│                                                             │
│ Format: [Single Elimination ▼]  Participants: 24 confirmed  │
│ Seeding: [Registration Order ▼]                             │
│                                                             │
│ ☐ Include 3rd place match                                   │
│ ☐ Enable Grand Finals reset (Double Elimination only)       │
│                                                             │
│ [Generate Bracket]  [Reset]                                 │
│                                                             │
│ ─── SEEDING PREVIEW ──────────────────────────────────────  │
│                                                             │
│ Drag to reorder seeds before publishing:                    │
│ ┌────┬────────────────┬────────┬───────┐                   │
│ │ #  │ Team           │ Rank   │ ≡     │                   │
│ ├────┼────────────────┼────────┼───────┤                   │
│ │ 1  │ Phoenix RSG    │ Dia. 2 │ ☰     │ ← draggable      │
│ │ 2  │ Shadow Wolves  │ Dia. 1 │ ☰     │                   │
│ │ 3  │ Rising Stars   │ Plat 3 │ ☰     │                   │
│ │ 4  │ BYE            │ —      │       │                   │
│ └────┴────────────────┴────────┴───────┘                   │
│                                                             │
│ [Publish Bracket]  (locks seeding — no further changes)     │
│                                                             │
│ ─── BRACKET VISUALIZATION ────────────────────────────────  │
│                                                             │
│ (Interactive bracket tree rendered after generation)         │
│ Supports: SE tree, DE winners+losers, RR table, Swiss table │
└─────────────────────────────────────────────────────────────┘
```

### Supported Formats

| Format | Generator File | Status | Config Options |
|--------|---------------|--------|---------------|
| Single Elimination | `bracket_generators/single_elimination.py` (223 lines) | ✅ Working | 3rd place match toggle |
| Double Elimination | `bracket_generators/double_elimination.py` (359 lines) | ✅ Working | Grand Finals reset toggle |
| Round Robin | `bracket_generators/round_robin.py` (149 lines) | ✅ Working | Points config: win/draw/loss/bye |
| Swiss | `bracket_generators/swiss.py` (377 lines) | ⚠️ R1 only | Number of rounds, tiebreaker rules |
| Group → Playoff | `stage_transition_service.py` (466 lines) | ✅ Working | Groups count, advancement count |

### Seeding Methods

| Method | Service | Status |
|--------|---------|--------|
| Registration order | `bracket_service.apply_seeding()` | ✅ Working |
| Random | `bracket_service.apply_seeding()` | ✅ Working |
| Ranked (by GamePassport rank) | `bracket_service.apply_seeding()` + ranking | ✅ Working |
| Manual (drag-and-drop) | `bracket_service.apply_seeding()` | ✅ Service, UI TODO |

### Drag-and-Drop Seeding

- **Backend:** `bracket_editor_service.py` (427 lines) supports swap, move, remove operations
- **Frontend:** HTML5 Drag and Drop API or Sortable.js (lightweight, no jQuery)
- **API:** HTMX `POST` to reorder endpoint → returns updated seed list as HTML partial

Workflow:
1. Organizer generates bracket
2. Bracket displayed in "Draft" state with draggable seed list
3. Organizer drags teams to desired seed positions
4. Each drag fires HTMX request to `bracket_editor_service.swap_participants()`
5. "Publish Bracket" locks seeding — no further drag-drop changes

### DQ / Drop from Bracket

```python
# Already exists in bracket_editor_service.py:
def remove_participant(self, bracket, participant_id) -> dict:
    """Remove participant from bracket, cascade BYEs to future rounds."""
```

When an organizer DQs a participant from the bracket:
1. Registration status → `disqualified`
2. Bracket node → set as BYE, opponent auto-advances
3. Future matches involving this participant → auto-forfeit
4. Audit log entry created via `BracketEditLog`
5. Winner determination recalculated if needed

### Existing Code to Leverage

- `apps/tournaments/services/bracket_service.py` (1,498 lines)
- `apps/tournament_ops/services/bracket_engine_service.py` (267 lines)
- `apps/tournament_ops/services/bracket_generators/` — all 4 generators
- `apps/tournaments/services/bracket_editor_service.py` (427 lines)
- `apps/tournaments/views/live.py` — `TournamentBracketView` (public bracket)
- `templates/tournaments/manage/brackets.html` — existing stub
- `templates/tournaments/public/live/bracket.html` — public bracket

---

## 18. TOC Module 4: Match Operations & Live Control

### The "Match Medic" Concept

During live tournaments, things go wrong: players disconnect, scores are disputed, matches stall. The Match Operations module gives organizers **emergency tools** to keep the tournament running. We call these tools "Match Medics."

### Match Center Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Match Operations                       Tournament: LIVE 🔴   │
│                                                             │
│ [Active (3)] [Upcoming (8)] [Completed (12)] [All]          │
│                                                             │
│ ─── ACTIVE MATCHES ───────────────────────────────────────  │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Match #13 │ Round 3 │ 🔴 LIVE                          │ │
│ │ Phoenix RSG  2  vs  1  Shadow Wolves                   │ │
│ │ Started: 3:45 PM │ Duration: 42 min                    │ │
│ │                                                         │ │
│ │ [📝 Edit Score] [⏸ Pause] [⏩ Force Complete]          │ │
│ │ [🔄 Reset Score] [⚠️ Add Note] [🚫 Forfeit]           │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Match #14 │ Round 3 │ ⏳ CHECK_IN                       │ │
│ │ Rising Stars  —  vs  —  Team Valor                     │ │
│ │ Check-in closes: 3:50 PM (8 min remaining)             │ │
│ │                                                         │ │
│ │ Check-in: ✅ Rising Stars │ ❌ Team Valor              │ │
│ │ [Force Check-In] [▶ Force Start] [🚫 No-Show Forfeit] │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Score Override Panel

```
┌─────────────────────────────────────────────────────────────┐
│ ─── SCORE OVERRIDE (Match #13) ────────────────────────── │
│                                                             │
│ Phoenix RSG: [_2_]  Shadow Wolves: [_1_]                   │
│ Winner: [Phoenix RSG ▼]                                     │
│                                                             │
│ Reason (required):                                          │
│ [Score correction — player reported wrong score            ]│
│                                                             │
│ ⚠️ This will be logged in the audit trail.                  │
│                                                             │
│ [Confirm Override]  [Cancel]                                │
└─────────────────────────────────────────────────────────────┘
```

### Match Medic Actions

| Action | Service Method | Status |
|--------|---------------|--------|
| Edit Score | `match_ops_service.override_result()` | ✅ Working |
| Pause Match | `match_ops_service.pause()` | ✅ Working |
| Resume Match | `match_ops_service.resume()` | ✅ Working |
| Force Complete | `match_ops_service.force_complete()` | ✅ Working |
| Force Start | `match_service.start_match()` (skip check-in) | ✅ Working |
| Reset Score | `match_ops_service.reset()` | ✅ Working |
| Add Moderator Note | `MatchModeratorNote.objects.create()` | ✅ Working |
| Forfeit (one side) | `match_service.forfeit_match()` | ✅ Working |
| Cancel Match | `match_service.cancel_match()` | ✅ Working |
| Reschedule | `match_service.reschedule_match()` | ✅ Working |

### Advanced Competitive Features

| Feature | Implementation | Status |
|---------|---------------|--------|
| **3rd Place Match** | `bracket.third_place_match = True` | ✅ Generator supports it |
| **Grand Finals Reset (DE)** | `bracket.grand_finals_reset = True` | ✅ Generator supports it |
| **Live Draw** | Random seeding with WS broadcast | Phase 4 (WebSocket) |
| **Map Veto** | `Match.lobby_info` JSONB | Future enhancement |
| **Penalty Points** | `match_ops_service` + `MatchOperationLog` | ✅ Audit trail exists |

### Existing Code to Leverage

- `apps/tournament_ops/services/match_ops_service.py` (632 lines) — all MOCC operations
- `apps/tournaments/services/match_service.py` (1,318 lines) — full match lifecycle
- `apps/tournaments/views/organizer_matches.py` (150 lines) — existing match views
- `apps/tournament_ops/services/result_submission_service.py` (500 lines)
- `apps/tournaments/models/match_ops.py` — `MatchOperationLog`, `MatchModeratorNote`
- Match URL patterns already exist: `submit-score/<id>/`, `reschedule-match/<id>/`, `forfeit-match/<id>/`, `override-score/<id>/`, `cancel-match/<id>/`

---

## 19. TOC Module 5: Scheduling & Check-In Control

### Scheduling Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Schedule & Check-In                                          │
│                                                             │
│ [Schedule] [Check-In Control]                               │
│                                                             │
│ ─── ROUND-BY-ROUND SCHEDULE ─────────────────────────────  │
│                                                             │
│ Round 1 — Feb 25, 3:00 PM                                   │
│ ┌──────────────┬──────────┬───────────┬──────────┐         │
│ │ Match        │ Time     │ Status    │ Actions  │         │
│ ├──────────────┼──────────┼───────────┼──────────┤         │
│ │ #1 PHX v SHW │ 3:00 PM  │ Scheduled │ [Edit]   │         │
│ │ #2 RSG v VAL │ 3:00 PM  │ Scheduled │ [Edit]   │         │
│ │ #3 APX v UND │ 3:30 PM  │ Scheduled │ [Edit]   │         │
│ │ #4 SKY v BLZ │ 3:30 PM  │ Scheduled │ [Edit]   │         │
│ └──────────────┴──────────┴───────────┴──────────┘         │
│ [+ Add Break] [Auto-Schedule Round] [Shift All +30min]      │
│                                                             │
│ Round 2 — Feb 25, 4:00 PM                                   │
│ (auto-generated after R1 completes)                         │
│                                                             │
│ ─── SCHEDULING CONTROLS ──────────────────────────────────  │
│ Default match duration: [30 ▼] minutes                      │
│ Break between rounds:   [15 ▼] minutes                      │
│ Parallel matches:       [2  ▼] (how many at once)           │
│ [Auto-Schedule All Rounds]                                  │
└─────────────────────────────────────────────────────────────┘
```

### Check-In Control

```
┌─────────────────────────────────────────────────────────────┐
│ Check-In Control                                             │
│                                                             │
│ Window: Opens Feb 25 2:30 PM │ Closes Feb 25 3:00 PM        │
│ Status: ⏳ Opens in 2 hours                                  │
│                                                             │
│ ✅ Checked in: 18/24                                        │
│ ⏳ Not checked in: 4/24                                     │
│ ❌ No-show: 2/24                                            │
│                                                             │
│ ┌──────────────────┬──────────┬──────────────────┐         │
│ │ Team/Player      │ Status   │ Actions          │         │
│ ├──────────────────┼──────────┼──────────────────┤         │
│ │ Phoenix RSG      │ ✅ In    │                  │         │
│ │ Shadow Wolves    │ ⏳ Wait  │ [Force Check-In] │         │
│ │ Team Valor       │ ❌ NoShow│ [Force] [Drop]   │         │
│ └──────────────────┴──────────┴──────────────────┘         │
│                                                             │
│ [Open Check-In Early] [Extend +15min] [Close & Drop All]    │
│                                                             │
│ On drop: ☐ Auto-promote from waitlist                       │
│          ☐ Auto-adjust bracket (fill BYEs)                  │
└─────────────────────────────────────────────────────────────┘
```

### Scheduling Service Integration

```python
# Already exists: manual_scheduling_service.py (405 lines)
class ManualSchedulingService:
    def assign_match_time(self, match, scheduled_time, stream=None)
    def bulk_shift_schedule(self, tournament, round_number, delta_minutes)
    def generate_round_slots(self, tournament, round_number, start_time, duration, parallel)
    def detect_scheduling_conflicts(self, tournament) -> list
    def auto_schedule_round(self, tournament, round_number, config)
```

### Check-In Service Integration

```python
# Already exists: checkin_service.py (453 lines)
class CheckinService:
    def check_in(self, registration)
    def undo_check_in(self, registration)
    def organizer_toggle_checkin(self, registration, organizer)
    def bulk_check_in(self, registrations)
    def get_checkin_status(self, tournament) -> dict
    def validate_checkin_eligibility(self, registration) -> bool
    def open_checkin_window(self, tournament)
    def close_checkin_window(self, tournament)
    def extend_checkin_window(self, tournament, minutes)
```

### Existing Code to Leverage

- `apps/tournament_ops/services/manual_scheduling_service.py` (405 lines)
- `apps/tournaments/services/checkin_service.py` (453 lines)
- `apps/tournaments/views/checkin.py` (409 lines)
- URL: `toggle-checkin/<id>/` already exists

---

## 20. TOC Module 6: Dispute Resolution Center

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Dispute Resolution                                           │
│                                                             │
│ [Open (2)] [Under Review (1)] [Resolved (5)] [All]          │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ Dispute #D-007 │ Match #13 │ 🔴 OPEN                   │ │
│ │ Filed by: Phoenix RSG │ Against: Shadow Wolves          │ │
│ │ Category: Score Mismatch                                │ │
│ │ Filed: Feb 25, 4:15 PM │ Priority: HIGH                │ │
│ │                                                         │ │
│ │ Submitter Statement:                                    │ │
│ │ "We won 2-1 but opponent reported 2-0 in their favor"  │ │
│ │                                                         │ │
│ │ Evidence:                                               │ │
│ │ 📎 screenshot_round3.png [View]                         │ │
│ │ 📎 match_replay.mp4 [View]                              │ │
│ │                                                         │ │
│ │ Opponent Response: (not yet submitted)                  │ │
│ │                                                         │ │
│ │ ─── Organizer Actions ─────────────────────────────     │ │
│ │ [Accept (submitter wins)]  [Reject (keep result)]       │ │
│ │ [Request More Info from Submitter]                      │ │
│ │ [Request Response from Opponent]                        │ │
│ │ [Escalate to Platform Admin]                            │ │
│ │                                                         │ │
│ │ Resolution notes:                                       │ │
│ │ [____________________________________________________] │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Dispute Lifecycle

```
OPEN → UNDER_REVIEW → RESOLVED (accepted/rejected)
  │                      │
  └→ ESCALATED ─────────→│
```

If "Accept" → match score overridden, bracket updated, parties notified.
If "Reject" → original result stands, submitter notified with explanation.

### Existing Code to Leverage

- `apps/tournament_ops/services/dispute_service.py` (651 lines) — full dispute lifecycle
- `apps/tournaments/models/dispute.py` (255 lines) — `DisputeRecord` model (Phase 6)
- `apps/tournaments/views/dispute_resolution.py` (245 lines)
- `apps/tournaments/views/disputes_management.py` (72 lines)
- `templates/tournaments/manage/disputes.html` — existing stub
- URL patterns: `disputes/manage/`, `resolve-dispute/<id>/`

---

## 21. TOC Module 7: Participant Data Control

### Capabilities

| Action | How | Service |
|--------|-----|---------|
| **Manually add participant** | Organizer enters player/team info, skip registration flow | New: `registration_service.create_manual_registration()` |
| **Change display name** | Edit registration's display name (if override enabled) | `Registration.data` JSON update |
| **Swap team name/tag** | Update team display in bracket nodes + roster | `bracket_editor_service.swap_participants()` |
| **Manage free agents** | Pool of solo players in team tournaments | New: Free agent pool query |
| **Roster swap/substitute** | Replace a team member with a substitute | Update `lineup_snapshot`, audit log |
| **Transfer registration** | Move registration from one user/team to another | New: `registration_service.transfer_registration()` |
| **DQ with cascade** | Disqualify → auto-forfeit all future matches → opponent advances | `bracket_editor_service.remove_participant()` |
| **Override seed** | Change participant's seed position post-generation | `bracket_editor_service.swap_participants()` |

### Free Agent Pool

For team tournaments where solo players want to join but lack a team:

```
┌─────────────────────────────────────────────────────────────┐
│ Free Agents (3 available)                                    │
│                                                             │
│ ┌──────────────┬──────────┬──────────┬───────────────────┐ │
│ │ Player       │ Rank     │ Role     │ Actions           │ │
│ ├──────────────┼──────────┼──────────┼───────────────────┤ │
│ │ SkyDiver     │ Diamond 2│ Duelist  │ [Assign to Team ▼]│ │
│ │ BlazeMaster  │ Plat 3   │ Sentinel │ [Assign to Team ▼]│ │
│ │ NightHawk    │ Dia. 1   │ Controller│ [Assign to Team ▼]│ │
│ └──────────────┴──────────┴──────────┴───────────────────┘ │
│                                                             │
│ (Solo registrations in team tournaments = free agents)      │
└─────────────────────────────────────────────────────────────┘
```

### Manual Registration Addition

Organizer can bypass the SmartRegistrationView to manually add a participant:

```
┌─────────────────────────────────────────────────────────────┐
│ Add Participant Manually                                     │
│                                                             │
│ Type: ● Player  ○ Team  ○ Guest Team                       │
│                                                             │
│ Search user: [________________] [Search]                    │
│   Results: NightShade (Diamond 2, Valorant)  [+ Add]       │
│                                                             │
│ OR enter manually:                                          │
│ Player Name: [________________________]                     │
│ Game ID:     [________________________]                     │
│ Payment:     ● Waived  ○ Mark as Paid  ○ Require Payment   │
│                                                             │
│ [Add to Tournament]                                         │
└─────────────────────────────────────────────────────────────┘
```

### Existing Code to Leverage

- `apps/tournaments/services/bracket_editor_service.py` (427 lines) — swap, move, remove, validate, repair
- `apps/tournaments/views/organizer_participants.py` (165 lines) — DQ, export
- `apps/tournaments/services/registration_service.py` (1,999 lines) — already has bulk ops

---

## 22. Notifications

### Event Triggers

| Event | Participant Notification | Organizer Notification |
|-------|------------------------|----------------------|
| Registration submitted | ✅ Email confirmation | ✅ Dashboard counter |
| Registration approved | ✅ Email + in-app | |
| Registration rejected | ✅ Email with reason | |
| Payment submitted | ✅ "Proof uploaded" | ✅ Alert: verify queue |
| Payment verified | ✅ Email + registration confirmed | |
| Payment rejected | ✅ Email with instructions | |
| Waitlist promoted | ✅ Email + in-app | ✅ Dashboard log |
| Check-in open | ✅ Email + push (if available) | |
| Match scheduled | ✅ Email + in-app | |
| Match result pending | | ✅ Alert: confirm result |
| Dispute filed | ✅ Both parties notified | ✅ Alert: dispute queue |
| Dispute resolved | ✅ Both parties notified | |
| Tournament cancelled | ✅ Email to all participants | |

### Email Templates (Already Exist)

```
templates/tournaments/emails/
├── payment_pending.html
├── payment_verified.html
├── registration_approved.html
├── registration_confirmed.html
├── registration_rejected.html
├── waitlist_promotion.html
└── custom_notification.html
```

---

## 23. Anti-Fraud & Security

### Existing Protections

- Rate-limited registration (built into view)
- Game ID collision detection (same game ID in multiple registrations)
- Payment proof de-duplication (same image hash detection)
- Transaction ID uniqueness check per tournament
- CSRF on all forms
- `OrganizerRequiredMixin` on all management views

### Guest Team Additional Protections (v3.0)

- `max_guest_teams` integer cap per tournament (not boolean)
- Captain must provide justification text explaining why team isn't on platform
- Rate limit: max 1 guest team registration per user per tournament
- All guest teams permanently require `needs_review` status (never auto-approved)
- Organizer sees "⚠️ Guest Team" badge prominently in participant lists and alerts
- Guest team registrations logged with IP + user-agent for fraud analysis

### Payment Fraud Mitigations

- Same proof image to multiple tournaments → flagged
- Same transaction ID within a tournament → blocked
- Payment amount mismatch (proof shows ৳300 but entry fee is ৳500) → organizer warning
- Expired payment window → auto-reject with notification

---

## 24. Implementation Phases

### Phase 1: MVP — Registration + Core TOC (3-4 weeks)

**Goal:** Players can register (solo + team) with payment. Organizers can verify payments and manage participants through the TOC.

| # | Task | Key Files |
|---|------|-----------|
| 1.1 | Progressive Disclosure UX for registration | `smart_register.html`, `smart_registration.py` |
| 1.2 | Wire RegistrationQuestion/Answer into SmartView | `smart_registration.py`, models |
| 1.3 | Lineup snapshot on team registration | `Registration.lineup_snapshot` |
| 1.4 | Registration number generation | `Registration.registration_number` |
| 1.5 | TOC Command Center (alerts + stats) | `organizer.py`, `manage/overview.html` |
| 1.6 | TOC Participants Hub (table, filters, detail) | `organizer_participants.py`, `manage/participants.html` |
| 1.7 | TOC Payment Verification Queue | `organizer_payments.py`, `manage/payments.html` |
| 1.8 | Refund policy display + acceptance checkbox | Tournament model, `smart_register.html` |
| 1.9 | TOC navigation — all 7 tabs in `_base.html` | `manage/_base.html` |

### Phase 2: Advanced Registration + Check-In (2-3 weeks)

**Goal:** Guest teams, duplicate detection, waitlists, check-in, drafts.

| # | Task | Key Files |
|---|------|-----------|
| 2.1 | Guest team registration mode | `smart_registration.py`, new template section |
| 2.2 | `max_guest_teams` cap + soft friction | Tournament model, SmartView |
| 2.3 | Duplicate player detection | Cross-registration game ID check |
| 2.4 | Waitlist logic + promotion UI | `registration_service.py`, TOC Participants |
| 2.5 | Check-in control panel in TOC | `checkin_service.py`, new `manage/schedule.html` |
| 2.6 | Display name override toggle | Tournament model, registration form |
| 2.7 | Draft auto-save (RegistrationDraft) | `RegistrationDraft`, AJAX endpoint |

### Phase 3: Tournament Ops & Brackets (3-4 weeks)

**Goal:** Full Tournament Operations Center with brackets, match ops, scheduling, disputes.

| # | Task | Key Files |
|---|------|-----------|
| 3.1 | TOC Bracket Generation UI | `bracket_service.py`, `manage/brackets.html` |
| 3.2 | Drag-and-drop seeding interface | `bracket_editor_service.py`, Sortable.js |
| 3.3 | TOC Match Operations (Match Medic) | `match_ops_service.py`, new `manage/matches.html` |
| 3.4 | TOC Scheduling panel | `manual_scheduling_service.py`, `manage/schedule.html` |
| 3.5 | TOC Dispute Resolution Center | `dispute_service.py`, `manage/disputes.html` |
| 3.6 | Participant Data Control panel | Existing services + new endpoints |
| 3.7 | Swiss rounds 2+ completion | `swiss.py` generator |
| 3.8 | 3rd place + Grand Finals reset UI | Bracket model config |

### Phase 4: Automation & Polish (2-3 weeks)

**Goal:** DeltaCoin payments, auto-expiry, guest conversion, notification events, live draw.

| # | Task | Key Files |
|---|------|-----------|
| 4.1 | DeltaCoin payment integration | `payment_service.py`, Economy app |
| 4.2 | Payment deadline auto-expiry (Celery) | New Celery task |
| 4.3 | Payment model consolidation (4-step migration) | See Section 11 |
| 4.4 | Guest-to-Real Team conversion | New conversion service |
| 4.5 | RegistrationRule auto-evaluation | Wire `RegistrationRule.evaluate()` |
| 4.6 | Notification event handlers | Event system + email templates |
| 4.7 | Live draw (WebSocket broadcast) | `bracket_service` + WS channel |

---

> **Next Step:** Review this document and approve. Then see `05_IMPLEMENTATION_TRACKER.md` for the granular execution checklist with exact file paths and acceptance criteria.
