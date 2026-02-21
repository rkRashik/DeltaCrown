# Smart Registration System — Complete Rebuild Plan

**Date:** February 21, 2026  
**Status:** Active  
**Scope:** Full audit → rebuild of tournament registration (frontend + backend + admin)

---

## 1. AUDIT FINDINGS — CRITICAL ISSUES

### 1.1 Broken / Dead Code
| Issue | Location | Severity |
|-------|----------|----------|
| `GameRosterConfig.validate_roster_size()` is dead code — zero callers | `roster_config.py:144` | HIGH |
| `TeamService.validate_roster()` raises `NotImplementedError` | `team_service.py:253` | HIGH |
| `TournamentFormConfiguration` exists but is NOT wired into `SmartRegistrationView` | `form_configuration.py` / `smart_registration.py` | CRITICAL |
| Dual registration systems coexist (`Registration` vs `FormResponse`) | `registration.py` / `form_template.py` | MEDIUM |
| Three overlapping form config layers (boolean toggles, JSON schema, RegistrationQuestion) | Multiple models | HIGH |
| Hardcoded `min_team_size = 5` in legacy adapter | `team_adapter.py:393` | HIGH |
| "Too many starting players" error unreachable — no max roster validation during registration | Eligibility → Registration flow | HIGH |

### 1.2 Registration Form Gaps (User-Reported)
| Gap | Current State | Required |
|-----|---------------|----------|
| Match Coordinator role not explained | Just "Phone/Discord" label | Role selector (IGL/Captain/Other) + tooltip explaining responsibilities |
| Contact fields hardcoded | Always phone + discord | Dynamic based on organizer config (discord, messenger, email, WhatsApp, custom) |
| Preferred communication not shown | Hidden field | Visible dropdown when organizer enables it |
| Team Info section too basic | Name + tag only | Logo upload, banner upload, region, bio, social links |
| Roster not editable | Read-only list from team app | Editable lineup selector (drag positions, swap starters/subs) |
| Member details not viewable | Just name + role badge | Click to expand: game ID, rank, role, real name, photo |
| Missing member info not fillable | No option | Inline edit for missing fields (saved back to team roster) |
| Member photos not uploadable | No option | Per-member image upload for LAN/official tournaments |
| Payment options limited | bKash/Nagad/Rocket + DeltaCoin | Dynamic from organizer config (bank, crypto, DeltaCoin, custom methods) |
| Review section too basic | Just contact + payment + roster | Full manifest with all sections, expandable details, edit links |

### 1.3 Admin / Organizer Gaps
| Gap | Current State | Required |
|-----|---------------|----------|
| Form config not wired to registration view | `TournamentFormConfiguration` ignored | View must read config and drive field visibility |
| No per-tournament registration form editor | Only admin boolean toggles | Rich form builder in admin (communication channels, custom fields, roster requirements) |
| Communication channel config missing | No model fields | New model/JSONField for organizer-defined communication channels |
| Member info requirements missing | No config | Organizer can require: real name, photo, age, ID for each member |
| Payment method config limited | `payment_methods` ArrayField | Full payment config with instructions, numbers, DeltaCoin toggle, custom methods |

---

## 2. REAL-WORLD ESPORTS PLATFORM ANALYSIS

### Toornament.com
- Multi-step wizard: Team Info → Lineup → Custom Fields → Review
- Lineup fully editable during registration (drag/drop, role assignment)
- Custom fields per tournament (organizer-defined)
- Each player can have individual custom fields
- Payment handled separately (not in registration wizard)

### Battlefy
- Clean card-based registration
- Team roster with role assignment (Captain, Player, Sub, Coach)
- Free agent registration / team finder built-in
- Custom questions per tournament
- Discord integration for team communication
- Each player's profile linked with stats

### FACEIT
- One-click registration when profile complete
- Roster management with skill ratings visible
- Substitute system with clear rules
- Anti-cheat readiness verification
- Match coordinator auto-assigned (highest rank captain)

### Common Patterns Across All Platforms
1. **Step 1: Coordinator/Team Identity** — Who is registering, what team, coordinator role
2. **Step 2: Communication Setup** — Organizer-defined channels with clear labels
3. **Step 3: Roster Builder** — Interactive lineup with role assignment, editable positions
4. **Step 4: Per-Member Details** — Game IDs, ranks, photos (if required by organizer)
5. **Step 5: Custom Fields** — Organizer questions, additional info
6. **Step 6: Payment** — Multiple options based on organizer config
7. **Step 7: Review & Confirm** — Full manifest, edit capability, terms acceptance

---

## 3. REBUILD ARCHITECTURE

### 3.1 Step Structure (New 7-Step Wizard)

```
Step 1: COORDINATOR & IDENTITY
  - Solo: Player profile card + game identity
  - Team: Team card + Match Coordinator role selector
  - Coordinator role: IGL / Captain / Manager / Other (with description tooltip)
  - Coordinator info tooltip explaining responsibilities

Step 2: COMMUNICATION CHANNELS (Dynamic)
  - Fields driven by TournamentFormConfiguration + organizer-defined channels
  - Each field: label, placeholder, required/optional, icon
  - Built-in channels: Phone/WhatsApp, Discord, Email
  - Organizer-added channels: Messenger, Telegram, Line, WeChat, custom
  - Preferred communication dropdown (when organizer enables)

Step 3: TEAM INFO (Team tournaments only — Enhanced)
  - Team name, tag (pre-filled, editable if allowed)
  - Logo upload (drag-drop with preview)
  - Banner upload (optional, with preview)
  - Team region/server
  - Short bio / motto (optional)
  - Guest team: full form for new team creation

Step 4: ROSTER ENGINE (Team tournaments — Full Rebuild)
  - Interactive roster builder
  - Game-specific limits from GameRosterConfig (starters, subs, coach)
  - Drag to reorder / assign positions
  - Click member → expandable detail panel:
    * Game ID, rank, display name
    * Role assignment (Starter / Substitute / Coach / Analyst)
    * Real name (if organizer requires)
    * Photo upload (if organizer requires)
    * Any missing fields highlighted with inline editor
  - "Add Member" for guest teams (dynamic rows)
  - Changes saved to RegistrationDraft AND optionally to team roster
  - Position labels from GameRosterConfig (e.g., "Duelist", "Support")

Step 5: ADDITIONAL DETAILS (Custom Questions — Enhanced)
  - Organizer-defined questions from RegistrationQuestion
  - Per-team AND per-player questions
  - Conditional display (show_if logic)
  - File uploads, multi-select, date pickers
  - Clear section labels and help text

Step 6: PAYMENT GATEWAY (Dynamic)
  - Payment methods from tournament.payment_methods
  - DeltaCoin option (if enabled and affordable)
  - Multiple mobile methods with per-method instructions
  - Bank transfer option (if configured)
  - Custom payment methods (organizer-defined)
  - Payment proof upload (image/PDF)
  - Note field (if enabled)
  - Fee waiver indicator (if applicable)

Step 7: REVIEW & LOCK (Comprehensive)
  - Full manifest with all sections
  - Each section expandable/collapsible
  - "Edit" links that jump back to relevant step
  - Roster manifest with all member details
  - Payment summary
  - Terms & conditions checkbox
  - Refund policy display
  - Waitlist notice (if applicable)
  - Submission confirmation
```

### 3.2 Backend Changes

#### A. Wire `TournamentFormConfiguration` into View
- Read form config at start of `_build_context()`
- Drive field visibility/requiredness from config
- Pass config to template as `form_config` dict

#### B. Add Communication Channel Configuration
- New JSONField on `TournamentFormConfiguration`: `communication_channels`
- Schema: `[{key, label, placeholder, icon, required, type}]`
- Default channels: phone, discord
- Organizer can add/remove/reorder channels in admin

#### C. Add Member Info Requirements
- New JSONField on `TournamentFormConfiguration`: `member_info_requirements`
- Schema: `[{field, label, required, description}]`
- Fields: real_name, photo, age, national_id, email, custom

#### D. Fix Roster Validation
- Wire `GameRosterConfig.validate_roster_size()` into eligibility flow
- Allow registration with editable roster (don't block if max exceeded — let user adjust)
- Show roster limits in UI

#### E. Enhance Roster Processing in View POST
- Accept edited roster data (position changes, role assignments)
- Validate against GameRosterConfig limits
- Save lineup_snapshot with full details
- Optionally update team membership records

#### F. Add Payment Configuration
- Read `tournament.payment_methods` for available methods
- Support DeltaCoin, mobile, bank, custom
- Per-method instructions from organizer config

### 3.3 Admin Changes

#### A. Enhanced TournamentFormConfiguration Inline
- Communication channels JSON editor with add/remove UI
- Member info requirements checkboxes
- Roster display options (show ranks, show photos, etc.)
- Payment method configuration

#### B. Per-Tournament Registration Form Preview
- Admin action: "Preview Registration Form" → opens form in new tab

---

## 4. IMPLEMENTATION ORDER

### Phase 1: Backend Foundation (This Session)
1. ✅ Audit complete
2. Wire `TournamentFormConfiguration` into `SmartRegistrationView`
3. Add communication channels config to model + view
4. Add member info requirements to model + view
5. Fix roster validation (wire GameRosterConfig)
6. Enhance payment config reading

### Phase 2: Template Rebuild (This Session)
1. New 7-step wizard structure
2. Step 1: Coordinator & Identity (with role selector + tooltips)
3. Step 2: Communication Channels (dynamic fields)
4. Step 3: Team Info (logo/banner upload)
5. Step 4: Roster Engine (interactive, editable)
6. Step 5: Custom Questions (enhanced)
7. Step 6: Payment Gateway (dynamic methods)
8. Step 7: Review & Lock (comprehensive manifest)

### Phase 3: JavaScript Engine (This Session)
1. Full wizard engine with 7 steps
2. Per-step validation with live feedback
3. Roster drag-drop and member detail panels
4. Payment method switching
5. Auto-save draft
6. Review data live sync
7. Form submission with loading overlay

### Phase 4: Admin Enhancement (This Session)
1. Enhanced TournamentFormConfiguration inline
2. Communication channel config
3. Migration for new fields

---

## 5. FILES TO MODIFY

| File | Changes |
|------|---------|
| `apps/tournaments/models/form_configuration.py` | Add communication_channels, member_info_requirements, roster_display_config, coordinator_role_config JSONFields |
| `apps/tournaments/views/smart_registration.py` | Wire form config, enhance context, process roster edits, handle new fields |
| `apps/tournaments/admin.py` | Enhanced inline with new fieldsets |
| `templates/tournaments/registration/smart_register.html` | New 7-step wizard structure |
| `templates/tournaments/registration/includes/_step_coordinator.html` | NEW — coordinator role + identity |
| `templates/tournaments/registration/includes/_step_comms.html` | NEW — communication channels |
| `templates/tournaments/registration/includes/_step_team_info.html` | NEW — enhanced team info |
| `templates/tournaments/registration/includes/_step_roster.html` | REBUILD — interactive roster |
| `templates/tournaments/registration/includes/_step_questions.html` | Minor enhancements |
| `templates/tournaments/registration/includes/_step_payment.html` | REBUILD — dynamic payment methods |
| `templates/tournaments/registration/includes/_step_review.html` | REBUILD — comprehensive manifest |
| `static/js/smart_registration.js` | NEW — full wizard engine |
| `static/css/smart_registration.css` | NEW — all styles extracted |
| Migration file | New fields on TournamentFormConfiguration |
