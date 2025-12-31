# P0 Implementation Checklist
**Date:** December 31, 2025  
**Owner:** Tech Lead  
**Type:** Implementation Checklist (NO CODE)  
**Purpose:** Granular task breakdown for P0 launch blockers

---

## A. PROFILE PAGE RENDERING + PERMISSION GATING

### A.1 Archive Current Templates
- **Definition of Done:** `archive_2025_12_31/` directory exists with `public_v4.html`, `profile.html` copied inside
- **Files Touched:**
  - `templates/user_profile/profile/archive_2025_12_31/` (new directory)
  - `templates/user_profile/profile/public_v4.html` (copied, not deleted)
  - `templates/user_profile/profile/profile.html` (copied, not deleted)

### A.2 Create Aurora Zenith Template Structure
- **Definition of Done:** `public_v5_aurora.html` renders with mock data, no 500 errors
- **Files Touched:**
  - `templates/user_profile/profile/public_v5_aurora.html` (copied from drafts)
  - `templates/user_profile/profile/partials_aurora/` (new directory)

### A.3 Create Hero Partials
- **Definition of Done:** Hero section renders avatar, bio, followers, action buttons with real context
- **Files Touched:**
  - `templates/user_profile/profile/partials_aurora/_hero_background.html`
  - `templates/user_profile/profile/partials_aurora/_hero_avatar.html`
  - `templates/user_profile/profile/partials_aurora/_hero_identity.html`
  - `templates/user_profile/profile/partials_aurora/_hero_stats_hud.html`
  - `templates/user_profile/profile/partials_aurora/_hero_action_dock.html`

### A.4 Create Tab Navigation + Placeholders
- **Definition of Done:** All tabs clickable, tab content switches via JS, non-existent features show "Coming Soon" cards
- **Files Touched:**
  - `templates/user_profile/profile/partials_aurora/_tab_navigation.html`
  - `templates/user_profile/profile/partials_aurora/_tab_overview.html` (with placeholders)
  - `templates/user_profile/profile/partials_aurora/_tab_wallet.html` (owner-only)
  - `templates/user_profile/profile/partials_aurora/_tab_career.html`
  - `templates/user_profile/profile/partials_aurora/_tab_posts.html` (placeholder only)

### A.5 Wallet Owner-Only Gating
- **Definition of Done:** Non-owners see "Wallet is Private" message, wallet tab hidden in nav, owner sees full balance/transactions
- **Files Touched:**
  - `apps/user_profile/views/fe_v2.py` (profile_view_v5 context logic)
  - `templates/user_profile/profile/partials_aurora/_tab_wallet.html` (conditional rendering)
  - `templates/user_profile/profile/partials_aurora/_tab_navigation.html` (conditional tab visibility)

### A.6 Update Profile View Context
- **Definition of Done:** Context passes `is_owner`, `view_mode`, `wallet_visible`, `follower_stats`, `active_teams` to template
- **Files Touched:**
  - `apps/user_profile/views/fe_v2.py` (profile_view_v5 function)

### A.7 Update URL Routing
- **Definition of Done:** `/@username/` route points to new view, old routes still functional (rollback safety)
- **Files Touched:**
  - `apps/user_profile/urls.py` (update path to profile_view_v5)

### A.8 Test Profile Load Time
- **Definition of Done:** Profile page loads in <1.5s (avg), no template errors in logs
- **Files Touched:**
  - Manual testing, browser DevTools performance tab

---

## B. EMBED URL SAFETY (STREAM + HIGHLIGHTS)

### B.1 Create URL Validator Service
- **Definition of Done:** `validate_highlight_url()`, `validate_stream_url()`, `validate_affiliate_url()` functions exist, return `{valid: bool, platform: str, video_id: str}` or error
- **Files Touched:**
  - `apps/user_profile/services/url_validator.py` (new file)

### B.2 Add URL Whitelists
- **Definition of Done:** Whitelists for YouTube, Twitch, Medal.tv (highlights), Twitch/YouTube/Facebook (streams), Amazon/Logitech/Razer (affiliate) hardcoded in validator
- **Files Touched:**
  - `apps/user_profile/services/url_validator.py` (domain constants)

### B.3 HTTPS Enforcement
- **Definition of Done:** `http://` URLs rejected, only `https://` accepted
- **Files Touched:**
  - `apps/user_profile/services/url_validator.py` (protocol check)

### B.4 Video ID Character Whitelist
- **Definition of Done:** Only `[a-zA-Z0-9_-]` allowed in extracted video IDs, reject SQL keywords/path separators
- **Files Touched:**
  - `apps/user_profile/services/url_validator.py` (regex validation)

### B.5 Add CSP Headers
- **Definition of Done:** `Content-Security-Policy` header includes `frame-src https://youtube.com https://clips.twitch.tv https://medal.tv`, `script-src 'self'`, `frame-ancestors 'none'`
- **Files Touched:**
  - `config/settings/security.py` (CSP_FRAME_SRC, CSP_SCRIPT_SRC settings)
  - `config/middleware.py` (CSP middleware if not using django-csp)

### B.6 Add Iframe Sandbox Attributes
- **Definition of Done:** All `<iframe>` tags have `sandbox="allow-scripts allow-same-origin"`, `loading="lazy"`, `referrerpolicy="no-referrer"`
- **Files Touched:**
  - `templates/user_profile/profile/partials_aurora/_highlight_video_embed.html` (new partial)
  - `templates/user_profile/profile/partials_aurora/_sidebar_live_status.html` (stream embed)

### B.7 Twitch Parent Parameter
- **Definition of Done:** All Twitch embed URLs include `&parent=deltacrown.com` (hardcoded domain, not user-provided)
- **Files Touched:**
  - `apps/user_profile/services/url_validator.py` (Twitch URL builder)
  - `templates/user_profile/profile/partials_aurora/_highlight_video_embed.html`

### B.8 Test XSS Prevention
- **Definition of Done:** Inject `<script>alert('XSS')</script>` in clip title/description, verify escaped, no alert fires
- **Files Touched:**
  - Manual testing, automated test in `apps/user_profile/tests/test_url_validation.py`

---

## C. BOUNTY P0 (CREATE/ACCEPT/EXPIRY/REFUND MINIMAL)

### C.1 Create Bounty Models
- **Definition of Done:** 4 models (`Bounty`, `BountyAcceptance`, `BountyProof`, `BountyDispute`) exist with all fields, migrations applied without errors
- **Files Touched:**
  - `apps/user_profile/models/bounty.py` (new file)
  - `apps/user_profile/models/__init__.py` (import new models)
  - `apps/user_profile/migrations/0001_bounty_models.py` (generated)

### C.2 Add Bounty Indexes
- **Definition of Done:** Composite indexes on `(status, expires_at)`, `(creator_id, status)` exist, query planner uses them
- **Files Touched:**
  - `apps/user_profile/models/bounty.py` (Meta class indexes)
  - `apps/user_profile/migrations/0001_bounty_models.py` (includes indexes)

### C.3 Extend DeltaCrownTransaction Reasons
- **Definition of Done:** `BOUNTY_ESCROW`, `BOUNTY_WIN`, `BOUNTY_REFUND`, `BOUNTY_FEE` added to `DeltaCrownTransaction.Reason` choices
- **Files Touched:**
  - `apps/economy/models.py` (DeltaCrownTransaction.Reason enum)
  - `apps/economy/migrations/000X_bounty_transaction_reasons.py` (generated)

### C.4 Add Wallet Check Constraint
- **Definition of Done:** Database constraint `CHECK (cached_balance - pending_balance >= 0)` exists on `DeltaCrownWallet`, prevents negative available balance
- **Files Touched:**
  - `apps/economy/models.py` (DeltaCrownWallet Meta constraints)
  - `apps/economy/migrations/000X_wallet_check_constraint.py` (generated)

### C.5 Create Economy Escrow Services
- **Definition of Done:** 4 functions (`lock_bounty_stake`, `release_bounty_escrow`, `refund_bounty_stake`, `collect_platform_fee`) exist with `@transaction.atomic`, `select_for_update()`, idempotency keys
- **Files Touched:**
  - `apps/economy/services.py` (extend existing file)

### C.6 Create Bounty Service Layer
- **Definition of Done:** 8 methods exist (`create_bounty`, `accept_bounty`, `submit_bounty_result`, `complete_bounty`, `raise_bounty_dispute`, `resolve_bounty_dispute`, `expire_bounty`, `cancel_bounty`), all wrapped in transactions
- **Files Touched:**
  - `apps/user_profile/services/bounty_service.py` (new file)

### C.7 Add Reputation Check (Create Bounty)
- **Definition of Done:** `create_bounty()` rejects if `user.reputation < 50`, returns error message
- **Files Touched:**
  - `apps/user_profile/services/bounty_service.py` (reputation validation)

### C.8 Add Self-Acceptance Prevention
- **Definition of Done:** `accept_bounty()` rejects if `acceptor == creator`, returns error message
- **Files Touched:**
  - `apps/user_profile/services/bounty_service.py` (acceptor validation)

### C.9 Add Block List Check
- **Definition of Done:** `accept_bounty()` rejects if `creator.blocked_users.filter(id=acceptor.id).exists()`, returns error
- **Files Touched:**
  - `apps/user_profile/services/bounty_service.py` (block list query)

### C.10 Create Bounty Expiry Celery Task
- **Definition of Done:** `expire_bounties_task()` runs every 15 minutes, queries expired bounties with `select_for_update()`, calls `expire_bounty()` for each
- **Files Touched:**
  - `apps/user_profile/tasks.py` (new file)
  - `config/celery.py` (register periodic task, beat schedule)

### C.11 Create Bounty Views
- **Definition of Done:** 6 views exist (`BountyCreateView`, `BountyAcceptView`, `BountySubmitResultView`, `BountyDisputeView`, `BountyListView`, `BountyDetailView`), all require login, use service layer
- **Files Touched:**
  - `apps/user_profile/views/bounty_views.py` (new file)

### C.12 Add Rate Limiting
- **Definition of Done:** Bounty creation limited to 10/day, 1-hour cooldown enforced, returns 429 if exceeded
- **Files Touched:**
  - `apps/user_profile/views/bounty_views.py` (rate limit decorator or service check)
  - `requirements.txt` (add django-ratelimit if not present)

### C.13 Create Bounty Templates
- **Definition of Done:** 3 partials render (`_bounty_card.html`, `_tab_bounties.html`, `_tab_overview.html` with bounty section), show stake, countdown, status
- **Files Touched:**
  - `templates/user_profile/profile/partials_aurora/_bounty_card.html` (new file)
  - `templates/user_profile/profile/partials_aurora/_tab_bounties.html` (new file)
  - `templates/user_profile/profile/partials_aurora/_tab_overview.html` (add bounty section)

### C.14 Add Bounty URLs
- **Definition of Done:** 6 routes exist (`/bounty/create/`, `/bounty/<id>/accept/`, `/bounty/<id>/submit/`, `/bounty/<id>/dispute/`, `/bounty/`, `/bounty/<id>/`), all resolve without 404
- **Files Touched:**
  - `apps/user_profile/urls.py` (bounty URL patterns)

### C.15 Create Bounty Admin
- **Definition of Done:** `BountyAdmin`, `BountyDisputeAdmin` registered, list views show status/stake/creator/acceptor, actions (force_complete, force_refund) work
- **Files Touched:**
  - `apps/user_profile/admin.py` (BountyAdmin, BountyDisputeAdmin classes)

### C.16 Test Bounty Escrow Atomicity
- **Definition of Done:** Test creates bounty, verifies `pending_balance` increased, `cached_balance` unchanged, idempotency key prevents double debit
- **Files Touched:**
  - `apps/user_profile/tests/test_bounty_escrow.py` (new file)

### C.17 Test Bounty Expiry Race Condition
- **Definition of Done:** Test simulates concurrent expiry task + user acceptance, verifies only one succeeds, no double refund
- **Files Touched:**
  - `apps/user_profile/tests/test_bounty_expiry.py` (new file)

### C.18 Test Bounty Permissions
- **Definition of Done:** Test verifies reputation check, self-acceptance rejection, block list enforcement
- **Files Touched:**
  - `apps/user_profile/tests/test_bounty_permissions.py` (new file)

---

## D. ENDORSEMENTS P0 (MATCH-BOUND AWARDS MINIMAL)

### D.1 Create Endorsement Models
- **Definition of Done:** 2 models (`SkillEndorsement`, `EndorsementOpportunity`) exist, migrations applied, unique constraint `(match_id, endorser)` enforced
- **Files Touched:**
  - `apps/user_profile/models/endorsement.py` (new file)
  - `apps/user_profile/models/__init__.py` (import new models)
  - `apps/user_profile/migrations/000X_endorsement_models.py` (generated)

### D.2 Add Endorsement Indexes
- **Definition of Done:** Composite index on `(match_id, endorser)`, index on `receiver_id` exist
- **Files Touched:**
  - `apps/user_profile/models/endorsement.py` (Meta class indexes)

### D.3 Create Endorsement Service
- **Definition of Done:** 4 methods exist (`create_endorsement_opportunity`, `endorse_teammate`, `aggregate_endorsements`, `unlock_cosmetic`), teammate validation works
- **Files Touched:**
  - `apps/user_profile/services/endorsement_service.py` (new file)

### D.4 Connect Match Completion Signal
- **Definition of Done:** `Match.post_save` signal triggers `create_endorsement_opportunity()` when `status=COMPLETED`, opportunities created for all participants
- **Files Touched:**
  - `apps/tournament_ops/signals.py` (post_save signal handler)
  - `apps/user_profile/apps.py` (import signals in ready())

### D.5 Create Endorsement View
- **Definition of Done:** `EndorseTeammateView` exists, validates match participation, prevents duplicate endorsements, returns success/error JSON
- **Files Touched:**
  - `apps/user_profile/views/endorsement_views.py` (new file)

### D.6 Create Endorsement Templates
- **Definition of Done:** 2 partials render (`_endorsement_skill_meter.html`, `_tab_endorsements.html`), show skill bars, counts, top skill
- **Files Touched:**
  - `templates/user_profile/profile/partials_aurora/_endorsement_skill_meter.html` (new file)
  - `templates/user_profile/profile/partials_aurora/_tab_endorsements.html` (new file)
  - `templates/user_profile/profile/partials_aurora/_tab_overview.html` (add endorsement summary)

### D.7 Add Endorsement URLs
- **Definition of Done:** Route `/endorse/` exists, POST with match_id/receiver_id/skill works
- **Files Touched:**
  - `apps/user_profile/urls.py` (endorsement URL pattern)

### D.8 Test Endorsement Uniqueness
- **Definition of Done:** Test attempts duplicate endorsement (same match + endorser), verifies unique constraint prevents it
- **Files Touched:**
  - `apps/user_profile/tests/test_endorsement_service.py` (new file)

### D.9 Test Teammate Validation
- **Definition of Done:** Test verifies endorser/receiver must be on same team in match, cross-team endorsement rejected
- **Files Touched:**
  - `apps/user_profile/tests/test_endorsement_service.py` (teammate validation test)

---

## E. SHOWCASE P0 (EQUIPPED BADGE/FRAME MINIMAL)

### E.1 Create Showcase Models
- **Definition of Done:** 3 models (`ProfileFrame`, `ProfileBanner`, `UnlockedCosmetic`) exist, migrations applied
- **Files Touched:**
  - `apps/user_profile/models/showcase.py` (new file or extend existing)
  - `apps/user_profile/models/__init__.py` (import new models)
  - `apps/user_profile/migrations/000X_showcase_models.py` (generated)

### E.2 Extend Badge Model
- **Definition of Done:** `Badge` has `unlocks_frame_id`, `unlocks_banner_id` ForeignKeys, nullable
- **Files Touched:**
  - `apps/user_profile/models/badge.py` (add FKs if Badge model exists)
  - `apps/user_profile/migrations/000X_badge_unlock_fks.py` (generated)

### E.3 Extend UserProfile Model
- **Definition of Done:** `UserProfile` has `equipped_frame_id`, `equipped_banner_id` ForeignKeys, nullable
- **Files Touched:**
  - `apps/user_profile/models/user_profile.py` (add FKs)
  - `apps/user_profile/migrations/000X_userprofile_equipped_fks.py` (generated)

### E.4 Create Showcase Service
- **Definition of Done:** 2 methods exist (`unlock_cosmetic`, `equip_cosmetic`), unlock requires badge ownership, equip requires UnlockedCosmetic record
- **Files Touched:**
  - `apps/user_profile/services/showcase_service.py` (new file)

### E.5 Create Showcase Templates
- **Definition of Done:** 2 partials render (`_cosmetic_item.html`, `_tab_inventory.html`), show rarity colors (Common gray, Rare blue, Epic purple, Legendary gold)
- **Files Touched:**
  - `templates/user_profile/profile/partials_aurora/_cosmetic_item.html` (new file)
  - `templates/user_profile/profile/partials_aurora/_tab_inventory.html` (new file)

### E.6 Update Hero Avatar Partial
- **Definition of Done:** `_hero_avatar.html` displays equipped frame (overlay or border), falls back to default if none equipped
- **Files Touched:**
  - `templates/user_profile/profile/partials_aurora/_hero_avatar.html` (add frame rendering)

### E.7 Test Unlock Validation
- **Definition of Done:** Test verifies user cannot unlock cosmetic without owning prerequisite badge
- **Files Touched:**
  - `apps/user_profile/tests/test_showcase_service.py` (new file)

### E.8 Test Equip Validation
- **Definition of Done:** Test verifies user cannot equip cosmetic without UnlockedCosmetic record
- **Files Touched:**
  - `apps/user_profile/tests/test_showcase_service.py` (equip validation test)

---

## F. LOADOUT P0 (BASIC MODELS + DISPLAY)

### F.1 Create Loadout Models
- **Definition of Done:** 4 models (`HardwareProduct`, `UserHardware`, `GameConfig`, `GameSettingsSchema`) exist, migrations applied
- **Files Touched:**
  - `apps/user_profile/models/loadout.py` (new file)
  - `apps/user_profile/models/__init__.py` (import new models)
  - `apps/user_profile/migrations/000X_loadout_models.py` (generated)

### F.2 Add Loadout Indexes
- **Definition of Done:** Composite indexes on `(user_id, category)` for UserHardware, `(user_id, game_id)` for GameConfig exist
- **Files Touched:**
  - `apps/user_profile/models/loadout.py` (Meta class indexes)

### F.3 Create Loadout Service
- **Definition of Done:** 2 methods exist (`set_user_hardware`, `set_game_config`), DPI validation works, schema validation works
- **Files Touched:**
  - `apps/user_profile/services/loadout_service.py` (new file)

### F.4 Create Loadout Templates
- **Definition of Done:** 2 partials render (`_hardware_item.html`, `_sidebar_gear_setup.html`), show product name, specs, affiliate link
- **Files Touched:**
  - `templates/user_profile/profile/partials_aurora/_hardware_item.html` (new file)
  - `templates/user_profile/profile/partials_aurora/_sidebar_gear_setup.html` (new file)

### F.5 Seed Hardware Catalog (Minimal)
- **Definition of Done:** 20 products added (5 mice, 5 keyboards, 5 headsets, 5 monitors) via fixture or admin
- **Files Touched:**
  - `apps/user_profile/fixtures/hardware_catalog_minimal.json` (new file)

### F.6 Test Hardware Validation
- **Definition of Done:** Test verifies DPI value must be within product specs range, invalid DPI rejected
- **Files Touched:**
  - `apps/user_profile/tests/test_loadout_service.py` (new file)

---

## G. ADMIN P0 (REGISTER CORE MODELS, FILTERS)

### G.1 Register Bounty Admin
- **Definition of Done:** `BountyAdmin` visible in admin, list displays status/stake/creator/acceptor, filterable by status/game
- **Files Touched:**
  - `apps/user_profile/admin.py` (BountyAdmin class)

### G.2 Register BountyDispute Admin
- **Definition of Done:** `BountyDisputeAdmin` visible, list displays bounty/raised_by/moderator/status, actions (resolve) work
- **Files Touched:**
  - `apps/user_profile/admin.py` (BountyDisputeAdmin class)

### G.3 Register Endorsement Admin (Read-Only)
- **Definition of Done:** `SkillEndorsementAdmin` visible, list displays match/endorser/receiver/skill, no add/edit/delete permissions (audit only)
- **Files Touched:**
  - `apps/user_profile/admin.py` (SkillEndorsementAdmin class)

### G.4 Register Showcase Admin
- **Definition of Done:** `ProfileFrameAdmin`, `ProfileBannerAdmin`, `UnlockedCosmeticAdmin` visible, can add/edit frames/banners
- **Files Touched:**
  - `apps/user_profile/admin.py` (Showcase admin classes)

### G.5 Register Loadout Admin
- **Definition of Done:** `HardwareProductAdmin`, `GameSettingsSchemaAdmin` visible, can add/edit products/schemas
- **Files Touched:**
  - `apps/user_profile/admin.py` (Loadout admin classes)

### G.6 Add Admin Filters
- **Definition of Done:** Bounty admin filterable by status, game, stake range; Endorsement admin filterable by match, skill
- **Files Touched:**
  - `apps/user_profile/admin.py` (list_filter attributes)

---

## TESTING CHECKLIST (P0 Coverage)

### Critical Tests
- [ ] `test_bounty_escrow.py` - idempotency, pending_balance lock/release, double refund prevention
- [ ] `test_bounty_service.py` - create, accept, complete, expire, cancel flows
- [ ] `test_bounty_permissions.py` - reputation ≥50, self-acceptance rejected, block list honored
- [ ] `test_bounty_expiry.py` - Celery task locks rows, concurrent expiry handled
- [ ] `test_url_validation.py` - whitelist enforcement, HTTPS only, XSS escaped
- [ ] `test_wallet_permissions.py` - owner-only context, non-owner sees "Private"
- [ ] `test_endorsement_service.py` - uniqueness, teammate validation, match completion signal
- [ ] `test_showcase_service.py` - unlock requires badge, equip requires UnlockedCosmetic
- [ ] `test_loadout_service.py` - DPI validation, schema validation

### Integration Tests
- [ ] Profile page loads without errors for owner/public/friend view modes
- [ ] Wallet tab hidden for non-owners
- [ ] Bounty creation → escrow lock → acceptance → completion → prize release flow
- [ ] Match completion → endorsement opportunities created
- [ ] Badge earned → cosmetic unlocked → equipped on profile

---

## DEPLOYMENT CHECKLIST

### Pre-Deployment
- [ ] All migrations applied to staging (8 migrations total)
- [ ] Celery beat task registered (`expire_bounties_task` runs every 15 min)
- [ ] CSP headers configured in `settings/security.py`
- [ ] Rate limiting middleware/decorator configured
- [ ] Archive directory created, old templates copied
- [ ] URL routing updated to `profile_view_v5`

### Smoke Tests (Staging)
- [ ] Profile page loads in <1.5s
- [ ] Wallet tab visible only to owner
- [ ] Create bounty → stake locked in `pending_balance`
- [ ] Accept bounty → status changes to ACCEPTED
- [ ] Expire bounty (manually trigger task) → refund issued
- [ ] Complete match → endorsement opportunities created
- [ ] Iframe embeds render (YouTube, Twitch)
- [ ] CSP violations: 0 errors in browser console

### Rollback Plan
- [ ] Feature flag: `ENABLE_BOUNTY_SYSTEM=False` in settings (disables bounty views)
- [ ] URL routing: Revert to `public_v4.html` (1-line change in `urls.py`)
- [ ] Monitor error logs: Template errors <5%, page load <3s, bounce rate stable

---

**END OF P0 CHECKLIST**

**Status:** ✅ Ready for Implementation  
**Total Items:** 78 checklist items across 7 modules  
**Next Step:** Begin A.1 (Archive Current Templates)
