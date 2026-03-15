# Frontend Game Passport Audit

Date: 2026-03-14
Scope: Current frontend implementation only (no new features proposed, no backend model review).
Primary files reviewed:
- templates/user_profile/profile/settings/partials/_game_passports.html
- static/user_profile/js/oauth_linked_accounts.js
- templates/user_profile/profile/settings_control_deck.html
- static/js/settings_controller.js
- static/user_profile/js/settings_v3.js
- static/user_profile/profile.js

---

## 1) DOM and Visual Architecture (Current State)

### 1.1 Entry point and composition
- The Game Passports tab content is injected through a server-side include in settings_control_deck.html:2177.
- The tab container is tab-passports in _game_passports.html:21.
- The section is composed in this order:
  - Header + info button + Link New Game CTA (_game_passports.html:24-43)
  - OAuth Linked Accounts cards + manual-only placeholders (_game_passports.html:45-149)
  - Existing passports grid (_game_passports.html:151)
  - Inline builder (selector + dynamic schema form) (_game_passports.html:152-281)
  - Right-side info drawer + mobile overlay (_game_passports.html:284-417)

### 1.2 Styling strategy
- Styling uses a hybrid of utility classes in markup and a large scoped inline style block in the partial (_game_passports.html:421 onward).
- Status/UX classes are defined locally in the partial, including:
  - status-badge variants (_game_passports.html:557-591)
  - game selector cards (_game_passports.html:593 onward)
  - OTP digit field animation and validation classes (_game_passports.html:963 onward)
- Visual direction is consistent with the control deck: neon/cyan esports palette, strong gradients, card borders, heavy iconography.

### 1.3 Notable UI composition details
- OAuth cards are presentationally separate from the dynamic passport grid and are keyed by data-oauth-game attributes (_game_passports.html:61, 77, 93, 109).
- Manual-entry-only games are represented as static advisory cards (eFootball, PUBG Mobile), not interactive controls (_game_passports.html:124-149).
- The builder uses a two-step flow (game selector -> generated fields) rather than a modal.

### 1.4 Frontend architecture finding
- High: the inline style block contains Tailwind @apply directives (_game_passports.html:792 onward, 941 onward). In an inline browser style tag, @apply is not processed by PostCSS/Tailwind and is ignored at runtime.
- Impact: intended validation state styles may not actually render, causing inconsistent visual feedback for touched/valid/invalid fields.

---

## 2) JavaScript and State Flow Architecture

### 2.1 Initialization path
- Primary tab init path in this screen is switchTab('passports') in settings_control_deck.html:3118-3126.
- The code gates first run using window.gamePassports._initialized.
- The Game Passport module itself is attached globally as window.gamePassports in _game_passports.html:3096.
- There is a second lazy-init hook in static/js/settings_controller.js:295-297 for section game-passports. If both controllers are active on the same page, both rely on the same _initialized gate.

### 2.2 Internal module state
- _game_passports.html defines a closure-scoped state object with:
  - games
  - passports
  - currentGame
  - editingPassport
  - touched
  - cache-related members
  (_game_passports.html:998-1005)

### 2.3 Data loading and rendering
- init() performs parallel fetches:
  - /profile/api/games/ (schema list, cache-aware)
  - /profile/api/game-passports/
  (_game_passports.html:1328-1383)
- Render responsibilities:
  - renderPassportsGrid() draws the linked passports (_game_passports.html:1500 onward)
  - renderGamesGrid() draws available game cards for linking (_game_passports.html:1652 onward)
- The module emits a cross-component custom event whenever passport data is rendered:
  - game-passports:data-updated in _game_passports.html:1507 and 1641.

### 2.4 OAuth linked cards integration
- static/user_profile/js/oauth_linked_accounts.js subscribes to game-passports:data-updated (line 183), then maps passports to OAuth cards by normalized slug.
- It also performs fallback fetch from /profile/api/game-passports/ at startup (line 140).
- CTA behavior:
  - connect: redirects via window.location.href to card-specific OAuth route (line 162)
  - disconnect: delegates to window.gamePassports.initiateOTPDelete(passportId) (line 171)

### 2.5 Frontend architecture findings
- Medium: dual initialization pathways (settings_control_deck inline controller and static/js/settings_controller.js) increase coupling and debugging complexity even with _initialized guards.
- Medium: oauth_linked_accounts has its own initial fetch plus event-driven updates; this can momentarily paint stale/empty states before main module dispatch completes.
- Low: high volume of console logging remains in production paths (_game_passports.html multiple console.log calls across init/validation/OTP setup).

---

## 3) Manual Entry UX and Builder Flow

### 3.1 Manual-only game experience
- eFootball and PUBG Mobile are shown as manual-only informational cards with no direct action wiring (_game_passports.html:124-149).
- User must discover and use the global Link New Game CTA to continue.

### 3.2 Dynamic schema-driven form generation
- On game selection, fields are generated from state.currentGame.passport_schema and categorized into:
  - Core Identity
  - Competitive Info
  - Optional
  (_game_passports.html:1715 onward)
- createFieldElement() applies required/regex/min-max constraints and per-field help/error elements (_game_passports.html:1791 onward).
- Duplicate checking for identity is added via check-identity endpoint with debounced blur checks for immutable required fields (_game_passports.html:1124 onward, 1853 onward).

### 3.3 Validation model
- Save button enablement is schema-aware and requires:
  - all required fields valid
  - no duplicate errors
  - Fair Play checkbox checked (new passport only)
  (_game_passports.html:2899 onward)
- Terms checkbox is hidden during edit mode (_game_passports.html:1779 onward).

### 3.4 Manual UX findings
- Medium: manual-only cards do not include direct preselect actions (for example, pre-opening the builder with a target game), creating an unnecessary cognitive step.
- Medium: identity duplicate checks only run for immutable required fields; non-immutable identity-like fields rely on submit-time validation only.
- Low: there are two educational surfaces (info drawer and inline Learn About accordion). They are useful but create content duplication and maintenance overhead.

---

## 4) OTP, Lock, Verified, and Cooldown UI Behavior

### 4.1 Main passport card state presentation
- Cards render status badges as:
  - locked when is_locked
  - verified when verification_status == VERIFIED
  - flagged when verification_status == FLAGGED
  - pending otherwise
  (_game_passports.html:1520-1528)
- Cooldown status is intentionally hidden from main cards and shown in edit actions (comment in _game_passports.html:1533).

### 4.2 Edit and delete gating
- editPassport() computes lock state as passport.is_locked OR passport.cooldown.is_active and conditionally shows:
  - cooldown warning panel
  - lock warning panel
  - verified warning panel
  - or OTP deletion request button
  (_game_passports.html:2279-2350)

### 4.3 OTP flow
- initiateOTPDelete(passportId):
  - blocks verified and locked/cooldown states before OTP request
  - requests code from /profile/api/game-passports/request-delete-otp/
  - renders a 6-digit OTP UI in the edit actions area
  (_game_passports.html:2568 onward)
- confirmOTPDelete(passportId):
  - submits code to /profile/api/game-passports/confirm-delete/
  - removes passport from state/DOM and refreshes games list
  (_game_passports.html:2746 onward)
- resendOTP(passportId):
  - enforces client-side 60-second resend cooldown
  - restarts 10-minute OTP expiry countdown
  (_game_passports.html:2812 onward)

### 4.4 OAuth card lock-state parity
- OAuth cards mark an account as locked when any of these are true:
  - is_locked
  - cooldown active
  - verification_status is VERIFIED
  (oauth_linked_accounts.js:58-76)
- Disconnect button is disabled for those locked states and text reflects lock reason (oauth_linked_accounts.js:98-117).

### 4.5 Lock/cooldown findings
- High: lock semantics are not fully aligned between main passport cards and OAuth cards.
  - Main card lock badge uses is_locked only (_game_passports.html:1521)
  - OAuth card lock logic includes cooldown and verified (oauth_linked_accounts.js:58-76)
  - Result: user may see a passport as generally connected in one surface while seeing locked/cooldown in another.
- Medium: policy copy is inconsistent.
  - Fair Play references 30-day lock in UI copy (_game_passports.html:380, 2310)
  - delete success fallback mentions re-add after 90 days (_game_passports.html:2777)
  - If backend policy is truly dynamic this should be consistently source-driven in all user-facing copy.
- Low: OTP timers are tracked per passport in memory and cleared on cancel/success, but not centrally cleaned on tab switch/unload.

---

## Current Risk Summary (Frontend Only)

1. High: Inline @apply usage in runtime style tag likely prevents intended validation styles from applying.
2. High: Status/lock semantics differ between main passport cards and OAuth linked cards.
3. Medium: Two potential settings controllers can initialize the same module path, increasing coupling.
4. Medium: Manual-only cards are informational but not action-connected, making manual onboarding less direct.
5. Medium: Lock/cooldown policy messaging appears inconsistent (30-day vs 90-day references).

---

## Appendix: Control Ownership Map

- Primary passport state owner: _game_passports.html (window.gamePassports)
- OAuth linked cards state adapter: static/user_profile/js/oauth_linked_accounts.js
- Tab activation trigger: settings_control_deck.html switchTab()
- Secondary generic settings tab controller present in codebase: static/js/settings_controller.js
- Legacy profile modal-style passport controller still exists elsewhere: static/user_profile/profile.js (different modal IDs and API paths)