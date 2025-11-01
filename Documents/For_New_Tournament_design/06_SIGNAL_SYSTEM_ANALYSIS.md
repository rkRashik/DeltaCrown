# Signal System Analysis - "Signal Hell"

**Document:** 06 - Signal System Analysis  
**Date:** November 2, 2025  
**Purpose:** Complete analysis of Django signals used in tournament system and their problems

---

## 📋 Overview

The DeltaCrown tournament system heavily relies on Django signals to implement business logic. This document catalogs all signals, their triggers, side effects, and the problems they create.

**Location:** `apps/tournaments/signals.py` (primary), plus signals in related apps

---

## 🔄 All Tournament-Related Signals

### Signal Handler Map

| Signal | Model | Trigger | Handler Function | Side Effects |
|--------|-------|---------|------------------|---------------|
| post_save | Tournament | After creation | `_ensure_tournament_settings` | Creates TournamentSettings |
| post_save | Tournament | After creation | `_ensure_game_config_for_tournament` | Creates game config (Valorant/eFootball) |
| post_save | Registration | After creation | `_ensure_payment_verification` | Creates PaymentVerification |
| post_save | Registration | After creation | `_set_team_game_from_registration` | Modifies Team.game field |
| post_save | Registration | After creation | `handle_tournament_registration_notification` | Sends notification |
| pre_save | Registration | Before save | `_validate_registration_mode` | Validates team requirement |
| pre_save | ValorantConfig | Before save | `_validate_config_matches_game` | Validates game match |
| pre_save | EfootballConfig | Before save | `_validate_config_matches_game` | Validates game match |
| post_save | PaymentVerification | After save | `_maybe_award_coins_on_verification` | Awards DeltaCoins |
| post_save | Match | After save | `handle_match_result_notification` | Sends match notifications |
| post_save | Tournament | After save | `handle_bracket_ready_notification` | Sends bracket ready notification |

**Total Signal Handlers:** 11+ in tournaments app alone

---

## 📝 Detailed Signal Analysis

### 1. Tournament Settings Auto-Creation

**Signal:** `post_save` on `Tournament`  
**Handler:** `_ensure_tournament_settings`  
**Dispatch UID:** `tournaments.ensure_settings`

#### Code:
```python
def _ensure_tournament_settings(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        Settings = apps.get_model("tournaments", "TournamentSettings")
        _safe(Settings.objects.get_or_create, tournament=instance)
    except LookupError:
        return
```

#### Behavior:
- **Trigger:** Every time a new Tournament is created
- **Action:** Creates a TournamentSettings record
- **Rationale:** Avoid null checks in templates/views

#### Problems:
1. **Hidden Dependency:** TournamentSettings existence not obvious from Tournament creation code
2. **Silent Failures:** Uses `_safe()` wrapper that swallows exceptions
3. **Testing:** Must check for TournamentSettings in tournament tests
4. **Database Bloat:** Creates records even if never used

#### Alternatives:
```python
# Explicit creation in service
class TournamentService:
    def create_tournament(self, data):
        tournament = Tournament.objects.create(**data)
        TournamentSettings.objects.create(tournament=tournament)
        return tournament
```

---

### 2. Game Config Auto-Creation

**Signal:** `post_save` on `Tournament`  
**Handler:** `_ensure_game_config_for_tournament`  
**Dispatch UID:** `tournaments.ensure_game_config`

#### Code:
```python
def _ensure_game_config_for_tournament(sender, instance, created, **kwargs):
    if not created:
        return
    game = getattr(instance, "game", None)
    if not game:
        return
    if game == "valorant":
        try:
            VC = apps.get_model("game_valorant", "ValorantConfig")
            _safe(VC.objects.get_or_create, tournament=instance)
        except LookupError:
            pass
    elif game == "efootball":
        try:
            EC = apps.get_model("game_efootball", "EfootballConfig")
            _safe(EC.objects.get_or_create, tournament=instance)
        except LookupError:
            pass
```

#### Behavior:
- **Trigger:** Every time a new Tournament is created
- **Action:** Creates game-specific config based on `Tournament.game` field
- **Rationale:** Convenience - Config always exists

#### Problems:
1. **Hardcoded Game Logic:** Must modify this function to add new games
2. **Tight Coupling:** Tournament app knows about game_valorant and game_efootball
3. **Cross-App Dependencies:** Imports models from other apps at runtime
4. **Silent Failures:** `LookupError` caught but not logged
5. **Wasteful:** Creates config even if organizer doesn't need it
6. **No Rollback:** If ValorantConfig creation fails, Tournament still exists

#### Why This is "Signal Hell":
```
Developer creates a Tournament:
    tournament = Tournament.objects.create(name="Test", game="valorant")

Behind the scenes (invisible):
    1. Tournament saved to database
    2. post_save signal fires
    3. TournamentSettings auto-created
    4. ValorantConfig auto-created
    
Developer wonders: "Where did ValorantConfig come from?!"
```

#### Alternatives:
```python
# Factory pattern
class TournamentFactory:
    def create(self, game, **data):
        tournament = Tournament.objects.create(game=game, **data)
        
        # Explicit and traceable
        if game == "valorant":
            ValorantConfig.objects.create(tournament=tournament)
        elif game == "efootball":
            EfootballConfig.objects.create(tournament=tournament)
        
        return tournament
```

---

### 3. Payment Verification Auto-Creation

**Signal:** `post_save` on `Registration`  
**Handler:** `_ensure_payment_verification`  
**Dispatch UID:** `tournaments.ensure_payment_verification`

#### Code:
```python
def _ensure_payment_verification(sender, instance, created, **kwargs):
    if not created:
        return
    try:
        PV = apps.get_model("tournaments", "PaymentVerification")
        _safe(PV.objects.get_or_create, registration=instance)
    except LookupError:
        return
```

#### Behavior:
- **Trigger:** After Registration is created
- **Action:** Creates PaymentVerification record
- **Rationale:** Payment workflow always starts with verification record

#### Problems:
1. **Assumption:** Every registration requires payment (what about free tournaments?)
2. **Workflow Coupling:** Payment verification model must exist
3. **Testing:** Must account for PaymentVerification in registration tests

---

### 4. Team Game Field Auto-Update

**Signal:** `post_save` on `Registration`  
**Handler:** `_set_team_game_from_registration`  
**Dispatch UID:** `tournaments.set_team_game_from_registration`

#### Code:
```python
def _set_team_game_from_registration(sender, instance, created, **kwargs):
    if not created:
        return
    team = getattr(instance, "team", None)
    tour = getattr(instance, "tournament", None)
    current = (getattr(team, "game", "") or "") if team else ""
    if team and tour and current == "":
        team.game = getattr(tour, "game", "") or ""
        _safe(team.save, update_fields=["game"])
```

#### Behavior:
- **Trigger:** After team registration is created
- **Action:** Sets Team.game to match Tournament.game (if Team.game is empty)
- **Rationale:** Teams should know what game they play

#### Problems:
1. **Side Effect on Different Model:** Registration save modifies Team
2. **Race Conditions:** If Team.save() triggers its own signals, cascade effect
3. **Business Logic Location:** Why is this in signals.py, not in Team or Tournament logic?
4. **Implicit Behavior:** Developer saving Registration doesn't expect Team modification
5. **Testing Complexity:** Must check Team state after Registration save

#### Example Confusion:
```python
# Developer creates registration
registration = Registration.objects.create(
    tournament=valorant_tournament,
    team=my_team
)

# my_team.game was "", now it's "valorant" - BUT HOW?!
# Must trace through signals to understand
```

---

### 5. Registration Mode Validation

**Signal:** `pre_save` on `Registration`  
**Handler:** `_validate_registration_mode`  
**Dispatch UID:** `tournaments.validate_registration_mode`

#### Code:
```python
def _validate_registration_mode(sender, instance, **kwargs):
    tour = getattr(instance, "tournament", None)
    if not tour:
        return
    game = getattr(tour, "game", None)
    if game == "valorant" and not getattr(instance, "team_id", None):
        raise ValidationError({"team": "Team registration is required for Valorant tournaments."})
```

#### Behavior:
- **Trigger:** Before Registration is saved
- **Action:** Validates that Valorant tournaments require team registration
- **Rationale:** Enforce game-specific rules

#### Problems:
1. **Game Logic in Signals:** Valorant requirements hardcoded
2. **Extensibility:** Adding new game rules requires modifying this function
3. **Validation Location:** Should be in Registration.clean() or form validation
4. **Error Handling:** ValidationError raised from signal (unexpected)
5. **Testing:** Must test signal handlers separately

#### Why This is Wrong:
```python
# Expected: Validation in model/form
class RegistrationForm(forms.ModelForm):
    def clean(self):
        # Obvious validation logic here
        pass

# Actual: Validation hidden in signal file
# Developer must search entire codebase to find validation logic
```

---

### 6. Game Config Validation

**Signal:** `pre_save` on `ValorantConfig` and `EfootballConfig`  
**Handler:** `_validate_config_matches_game`  
**Dispatch UID:** `tournaments.val_cfg_exclusive` / `tournaments.efb_cfg_exclusive`

#### Code:
```python
def _validate_config_matches_game(sender, instance, **kwargs):
    tour = getattr(instance, "tournament", None)
    if not tour:
        return
    game = getattr(tour, "game", None)
    if sender.__name__ == "ValorantConfig" and game != "valorant":
        raise ValidationError({"tournament": "ValorantConfig is only allowed on valorant tournaments."})
    if sender.__name__ == "EfootballConfig" and game != "efootball":
        raise ValidationError({"tournament": "EfootballConfig is only allowed on efootball tournaments."})
```

#### Behavior:
- **Trigger:** Before game config is saved
- **Action:** Validates that config matches tournament game
- **Rationale:** Prevent mismatched configurations

#### Problems:
1. **Should be in Model.clean():** This belongs in ValorantConfig.clean()
2. **String Comparison:** Uses `sender.__name__` (fragile)
3. **Duplication:** Similar logic for each game config
4. **Cross-Model Validation:** Config depends on Tournament state

---

### 7. Coin Award on Payment Verification

**Signal:** `post_save` on `PaymentVerification`  
**Handler:** `_maybe_award_coins_on_verification`  
**Dispatch UID:** `tournaments.maybe_award_coins`

#### Code:
```python
def _maybe_award_coins_on_verification(sender, instance, created, **kwargs):
    try:
        status = getattr(instance, "status", None)
        if status not in ("VERIFIED", "APPROVED", "CONFIRMED"):
            return
        svc = import_module("apps.economy.services.participation")
        if hasattr(svc, "award_participation_for_registration"):
            reg = getattr(instance, "registration", None)
            if reg is not None:
                _safe(svc.award_participation_for_registration, reg)
    except Exception:
        pass
```

#### Behavior:
- **Trigger:** After PaymentVerification is saved
- **Action:** Awards DeltaCoins if status is verified
- **Rationale:** Reward users for tournament participation

#### Problems:
1. **Cross-App Business Logic:** Tournament app calling economy app
2. **Runtime Import:** `import_module()` at runtime (slow, fragile)
3. **Silent Failures:** Broad `except Exception` hides errors
4. **Transaction Issues:** Coins awarded outside original transaction
5. **Testing Nightmare:** Must mock economy service
6. **No Idempotency:** Called on every save, not just status change

#### Critical Problem:
```python
# What if coin award fails but payment verification succeeds?
payment_verification.status = "VERIFIED"
payment_verification.save()  # Signal fires

# If coin award fails:
# - PaymentVerification still saved (status = VERIFIED)
# - User thinks they got coins
# - No coins actually awarded
# - Silent failure (logged nowhere)
```

---

### 8. Tournament Registration Notification

**Signal:** `post_save` on `Registration`  
**Handler:** `handle_tournament_registration_notification`  
**Dispatch UID:** None (receiver decorator)

#### Code:
```python
@receiver(post_save, sender='tournaments.Registration')
def handle_tournament_registration_notification(sender, instance, created, **kwargs):
    from apps.notifications.services import NotificationService
    
    if created and instance.status in ['APPROVED', 'CONFIRMED']:
        try:
            NotificationService.notify_tournament_registration(instance.tournament, instance.team)
            logger.info(f"Tournament registration notification triggered for team {instance.team.id}")
        except Exception as e:
            logger.error(f"Failed to send tournament registration notification: {e}")
```

#### Behavior:
- **Trigger:** After Registration created with approved status
- **Action:** Sends notification via NotificationService
- **Rationale:** Notify team of successful registration

#### Problems:
1. **Cross-App Dependency:** Imports notification service
2. **Status Assumption:** Checks for APPROVED/CONFIRMED (what about other statuses?)
3. **Notification Timing:** Fired immediately (blocking operation)
4. **Error Handling:** Logs error but doesn't retry
5. **No Batch Processing:** One notification per registration (not efficient)

---

### 9. Match Result Notification

**Signal:** `post_save` on `Match`  
**Handler:** `handle_match_result_notification`  
**Dispatch UID:** None

#### Code:
```python
@receiver(post_save, sender='tournaments.Match')
def handle_match_result_notification(sender, instance, created, **kwargs):
    from apps.notifications.services import NotificationService
    
    if not created:
        if instance.winner_id and instance.status in ['completed', 'finished']:
            try:
                NotificationService.notify_match_result(instance)
                logger.info(f"Match result notification triggered for match {instance.id}")
            except Exception as e:
                logger.error(f"Failed to send match result notification: {e}")
```

#### Behavior:
- **Trigger:** After Match is updated (not created)
- **Action:** Sends notification if match has winner
- **Rationale:** Notify teams of match results

#### Problems:
1. **Called on Every Update:** Even if winner didn't change
2. **No State Change Detection:** Cannot tell if winner just set or was already set
3. **Duplicate Notifications:** If match saved multiple times after completion
4. **Logic Location:** Match notification logic in signals.py, not in Match model

---

## 🔗 Signal Dependency Chains

### Chain 1: Tournament Creation
```
User creates Tournament
    ↓
Tournament.save()
    ↓
[post_save signal 1] _ensure_tournament_settings()
    → TournamentSettings.objects.create()
    
[post_save signal 2] _ensure_game_config_for_tournament()
    → ValorantConfig.objects.create() [if game == "valorant"]
        ↓
    [pre_save signal] _validate_config_matches_game()
        → Validates tournament.game == "valorant"
```

**Total Objects Created:** 3 (Tournament, TournamentSettings, ValorantConfig)  
**Total Signal Handlers Fired:** 3  
**Developer Visible:** Only Tournament creation

---

### Chain 2: Team Registration
```
User submits registration form
    ↓
[pre_save signal] _validate_registration_mode()
    → Validates team requirement for game
    
Registration.save()
    ↓
[post_save signal 1] _ensure_payment_verification()
    → PaymentVerification.objects.create()
    
[post_save signal 2] _set_team_game_from_registration()
    → team.game = tournament.game
    → team.save(update_fields=["game"])
        ↓
    [Team signals fire...]
    
[post_save signal 3] handle_tournament_registration_notification()
    → NotificationService.notify_tournament_registration()
    → Notification.objects.create()
        ↓
    [Notification signals fire...]
```

**Total Objects Modified:** 4+ (Registration, PaymentVerification, Team, Notification)  
**Total Signal Handlers Fired:** 6+  
**Developer Visible:** Only Registration creation

---

### Chain 3: Payment Verification
```
Admin verifies payment
    ↓
payment_verification.status = "VERIFIED"
payment_verification.save()
    ↓
[post_save signal] _maybe_award_coins_on_verification()
    → apps.economy.services.award_participation_for_registration()
    → CoinTransaction.objects.create()
        ↓
    [Economy signals fire...]
    → Notification about coins (economy app)
```

**Total Objects Created:** 2+ (PaymentVerification update, CoinTransaction)  
**Total Signal Handlers Fired:** 4+  
**Cross-App Calls:** 2 (economy, notifications)

---

## 🐛 Real-World Problems Caused by Signals

### Problem 1: Ghost Registrations
**Scenario:** User submits registration, payment verification fails, but Registration exists.

**What Happened:**
1. Registration.save() succeeded
2. Signal created PaymentVerification successfully
3. Signal tried to send notification → Failed (email service down)
4. Exception caught and ignored
5. User sees "Registration pending" but no notification sent
6. Admin doesn't know registration exists

**Root Cause:** Signals not wrapped in transaction, silent failure handling

---

### Problem 2: Duplicate Coin Awards
**Scenario:** Admin saves PaymentVerification multiple times, coins awarded multiple times.

**What Happened:**
1. Admin verifies payment (status = "VERIFIED")
2. Coin awarded via signal
3. Admin edits payment verification to add note
4. Saves again (status still "VERIFIED")
5. Signal fires again (checks status, not change)
6. Coins awarded again

**Root Cause:** Signal checks status, not status change, no idempotency

---

### Problem 3: Cascade Failures
**Scenario:** Tournament creation fails mysteriously.

**What Happened:**
1. Developer creates Tournament (game="valorant")
2. Tournament saved successfully
3. Signal tries to create ValorantConfig
4. ValorantConfig validation fails (bug in validation)
5. Exception swallowed by `_safe()` wrapper
6. Developer thinks tournament created successfully
7. Later, views break because valorant_config is missing

**Root Cause:** Silent exception handling in signals

---

### Problem 4: Testing Complexity
**Scenario:** Simple unit test becomes integration test.

**What Happened:**
```python
def test_tournament_creation():
    # Developer thinks: "I'll test tournament creation"
    tournament = Tournament.objects.create(name="Test", game="valorant")
    
    # But actually testing:
    # - Tournament creation
    # - TournamentSettings creation (signal)
    # - ValorantConfig creation (signal)
    # - All validation in signals
    
    # Must now mock or create:
    # - game_valorant app
    # - ValorantConfig model
    # - Signal handlers
    
    # Simple unit test became integration test!
```

**Root Cause:** Signals create implicit dependencies

---

## 📊 Signal Statistics

### By Type:
- **post_save signals:** 8 handlers
- **pre_save signals:** 3 handlers
- **post_delete signals:** 0 handlers
- **m2m_changed signals:** 0 handlers

### By Purpose:
- **Auto-creation (related models):** 3 handlers
- **Validation:** 2 handlers
- **Cross-app actions:** 4 handlers
- **Notification:** 4 handlers

### By Risk Level:
- 🔴 **High Risk (cross-app, silent failures):** 5 handlers
- 🟡 **Medium Risk (implicit dependencies):** 4 handlers
- 🟢 **Low Risk (simple operations):** 2 handlers

---

## 🎯 Why "Signal Hell"?

### Definition
**Signal Hell:** A state where business logic is so deeply embedded in signal handlers that:
1. Developer cannot understand code flow without tracing signals
2. Debugging requires following signal chains across files
3. Testing requires complex mock setups
4. Changes have unpredictable side effects
5. Silent failures are common
6. Code is fragile and hard to maintain

### Characteristics Present in DeltaCrown:

✅ **Hidden Business Logic** - Coin awards, game config creation not obvious  
✅ **Cross-App Dependencies** - Signals call into economy, notification apps  
✅ **Silent Failures** - Broad exception handling hides errors  
✅ **Cascade Effects** - One save triggers 5+ other operations  
✅ **Testing Complexity** - Unit tests become integration tests  
✅ **Debugging Difficulty** - Must trace signal chains to find bugs  
✅ **Implicit Behavior** - Developer expectations don't match reality  
✅ **Race Conditions** - Signal order not guaranteed  
✅ **Transaction Boundaries** - Signals escape original transaction  

---

## ✅ Alternative: Service Layer Pattern

### Current (Signals):
```python
# Hidden, implicit
tournament = Tournament.objects.create(name="Test", game="valorant")
# Magic happens via signals...
```

### Proposed (Service Layer):
```python
# Explicit, traceable
class TournamentCreationService:
    def create_tournament(self, data):
        with transaction.atomic():
            tournament = Tournament.objects.create(**data)
            TournamentSettings.objects.create(tournament=tournament)
            
            if data['game'] == 'valorant':
                ValorantConfig.objects.create(tournament=tournament)
            
            return tournament

# Usage
service = TournamentCreationService()
tournament = service.create_tournament({
    'name': 'Test',
    'game': 'valorant'
})
# Explicit, clear, testable
```

### Benefits:
- **Explicit:** All operations visible in code
- **Traceable:** Easy to follow logic flow
- **Testable:** Can mock dependencies
- **Transactional:** Wrapped in atomic block
- **Debuggable:** Set breakpoints in service methods
- **Maintainable:** Change logic in one place

---

## 📝 Conclusion

The signal-heavy architecture in DeltaCrown's tournament system creates more problems than it solves:

1. **Hidden Complexity:** Business logic scattered across signal files
2. **Poor Developer Experience:** Unpredictable behavior, hard to debug
3. **Fragile Code:** Changes have unexpected side effects
4. **Testing Difficulty:** Cannot test in isolation
5. **Maintenance Burden:** Fear of breaking things prevents changes

**Recommendation:** Eliminate signals entirely, replace with explicit service layer.

**Next Document:** `14_CONFIGURATION_CHAOS.md` - Configuration model redundancy analysis
