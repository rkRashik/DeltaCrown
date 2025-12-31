# Implementation Execution Plan
**Date:** December 31, 2025  
**Owner:** Tech Lead  
**Type:** Implementation Order (NO CODE)  
**Purpose:** Define exact execution sequence for profile expansion features

---

## P0 - CRITICAL (Launch Blockers)

**Effort:** ~29 days (6 weeks, 1 engineer)  
**Goal:** Launch Bounty System MVP with escrow security + basic profile rendering

### 1. Archive Current Templates
- **Changes:** Create `templates/user_profile/profile/archive_2025_12_31/` directory, move `public_v4.html`, `profile.html`
- **App:** `user_profile`
- **Why:** Rollback safety, preserve existing code

### 2. Bounty Models (4 models)
- **Changes:** Create `apps/user_profile/models/bounty.py` with `Bounty`, `BountyAcceptance`, `BountyProof`, `BountyDispute`
- **App:** `user_profile`
- **Migration:** Add fields: `status` (9 states), `stake_amount`, `expires_at`, `creator`, `acceptor`, `game_id`, `proof_requirement`
- **Indexes:** Composite on `(status, expires_at)`, `(creator_id, status)`

### 3. Economy Escrow Services
- **Changes:** Extend `apps/economy/services.py` with `lock_bounty_stake()`, `release_bounty_escrow()`, `refund_bounty_stake()`, `collect_platform_fee()`
- **App:** `economy`
- **Safety:** `@transaction.atomic`, `select_for_update()` on wallet, idempotency keys: `f"bounty:{action}:{bounty_id}:{wallet_id}"`
- **Transaction Reasons:** Add `BOUNTY_ESCROW`, `BOUNTY_WIN`, `BOUNTY_REFUND`, `BOUNTY_FEE` to `DeltaCrownTransaction.Reason`

### 4. Bounty Service Layer
- **Changes:** Create `apps/user_profile/services/bounty_service.py` with 8 methods:
  - `create_bounty()` - validate reputation ≥50, lock stake in `pending_balance`
  - `accept_bounty()` - check not self, not blocked, max 3 concurrent
  - `submit_bounty_result()` - attach proof, update status
  - `complete_bounty()` - release escrow, award prize, collect 5% fee
  - `raise_bounty_dispute()` - 24-hour window post-completion
  - `resolve_bounty_dispute()` - moderator decision
  - `expire_bounty()` - refund creator stake
  - `cancel_bounty()` - only if OPEN status
- **App:** `user_profile`
- **Dependencies:** Economy escrow services, Bounty models

### 5. Bounty Expiry Celery Task
- **Changes:** Create `apps/user_profile/tasks.py` with `expire_bounties_task()` (runs every 15 min)
- **App:** `user_profile`
- **Logic:** Query `Bounty.filter(status='ACCEPTED', expires_at__lt=now()).select_for_update()`, call `expire_bounty()` for each
- **Risk:** Race conditions (handle via row locking + idempotency)

### 6. Bounty Views (6 views)
- **Changes:** Create `apps/user_profile/views/bounty_views.py`:
  - `BountyCreateView` (POST: stake, game, proof_requirement)
  - `BountyAcceptView` (POST: bounty_id)
  - `BountySubmitResultView` (POST: result, proof_url)
  - `BountyDisputeView` (POST: bounty_id, reason)
  - `BountyListView` (GET: open bounties feed)
  - `BountyDetailView` (GET: bounty detail with proofs)
- **App:** `user_profile`
- **Permissions:** Login required, reputation checks, ownership validation

### 7. Bounty Templates (3 partials)
- **Changes:** Create `templates/user_profile/profile/partials_aurora/`:
  - `_bounty_card.html` (title, stake, requirements, countdown)
  - `_tab_bounties.html` (created/accepted/completed lists)
  - `_tab_overview.html` (show active bounty card)
- **App:** `user_profile`
- **Context:** `active_bounty`, `user_bounties`, `bounty_stats`

### 8. URL Validation Service
- **Changes:** Create `apps/user_profile/services/url_validator.py` with `validate_highlight_url()`, `validate_stream_url()`, `validate_affiliate_url()`
- **App:** `user_profile`
- **Whitelists:** 
  - Highlights: `youtube.com`, `youtu.be`, `twitch.tv`, `clips.twitch.tv`, `medal.tv`
  - Streams: `player.twitch.tv`, `www.youtube.com`, `www.facebook.com`
  - Affiliate: `amazon.com`, `logitech.com`, `razer.com`
- **Enforcement:** HTTPS only, character whitelist `[a-zA-Z0-9_-]` for video IDs

### 9. CSP Headers + Iframe Sandbox
- **Changes:** Update `settings/middleware.py` or `settings/security.py`:
  - Add CSP: `frame-src https://youtube.com https://clips.twitch.tv https://medal.tv`
  - Add CSP: `script-src 'self'` (no unsafe-inline)
  - Add CSP: `frame-ancestors 'none'` (prevent clickjacking)
- **Changes:** Update all `<iframe>` tags in templates:
  - Add `sandbox="allow-scripts allow-same-origin"` (no allow-top-navigation)
  - Add `loading="lazy"` (performance)
  - Add `referrerpolicy="no-referrer"` (privacy)
  - Twitch: Add `&parent=deltacrown.com` parameter (hardcoded domain)
- **App:** `user_profile` templates, base template

### 10. Wallet Owner-Only Gating
- **Changes:** Update `apps/user_profile/views/fe_v2.py`:
  - In `profile_view_v5()`, only populate `wallet`, `wallet_transactions` if `is_owner=True`
  - Set `wallet_visible=False` for non-owners
- **Changes:** Update `templates/user_profile/profile/partials_aurora/_tab_wallet.html`:
  - Wrap content in `{% if is_owner %}...{% else %}Private wallet{% endif %}`
- **App:** `user_profile`
- **Security:** Never expose balance, transactions to non-owners

### 11. Rate Limiting
- **Changes:** Add rate limit decorators to views:
  - Bounty creation: `@ratelimit(key='user', rate='10/d')` (10 per day)
  - Bounty acceptance: `@ratelimit(key='user', rate='20/h')` (20 per hour)
  - Highlight upload: `@ratelimit(key='user', rate='5/h')` (5 per hour)
- **Changes:** Add cooldown check in `create_bounty()`:
  - Query `user.bounties_created.latest('created_at').created_at` + 1 hour > now → reject
- **App:** `user_profile`
- **Library:** Django Ratelimit or Redis-based

### 12. Bounty Admin Interface
- **Changes:** Create `apps/user_profile/admin.py`:
  - `BountyAdmin` - list view (status, stake, creator, acceptor), actions (force_complete, force_refund)
  - `BountyDisputeAdmin` - moderation queue (view proofs, resolve disputes)
- **App:** `user_profile`
- **Permissions:** Superuser only

### 13. Database Constraints + Indexes
- **Changes:** Migration to add:
  - Check constraint: `CHECK (cached_balance - pending_balance >= 0)` on `DeltaCrownWallet`
  - Unique constraint: `UNIQUE (match_id, endorser)` on `SkillEndorsement` (for P1, add now)
  - Composite index: `(status, expires_at)` on `Bounty`
  - Composite index: `(creator_id, status)` on `Bounty`
  - Index: `idempotency_key` on `DeltaCrownTransaction` (verify exists)
- **App:** `economy`, `user_profile`

### 14. Bounty Tests (4 test files)
- **Changes:** Create `apps/user_profile/tests/`:
  - `test_bounty_service.py` - create, accept, complete, expire, cancel flows
  - `test_bounty_escrow.py` - idempotency, race conditions, double refund prevention
  - `test_bounty_permissions.py` - reputation checks, self-acceptance, block list
  - `test_bounty_expiry.py` - Celery task execution, concurrent expiry handling
- **App:** `user_profile`
- **Coverage:** >80% for bounty_service.py, escrow operations

### 15. New Profile Template (Aurora Zenith)
- **Changes:** Copy `templates/My drafts/user_profile_temp_draft/user_profile.html` to `templates/user_profile/profile/public_v5_aurora.html`
- **Changes:** Convert mock data to Django variables (`{{ profile.user.username }}`, `{{ wallet.cached_balance }}`, etc.)
- **Changes:** Create `partials_aurora/` with 5 hero partials + tab navigation
- **Changes:** Update `apps/user_profile/views/fe_v2.py` to render `public_v5_aurora.html`
- **Changes:** Update URL routing to point to new view
- **App:** `user_profile`
- **Placeholders:** Show "Coming soon" for non-existent features (Highlights, Endorsements, Loadout)

---

## P1 - HIGH PRIORITY (MVP Features)

**Effort:** ~52 days (10 weeks, 1 engineer)  
**Goal:** Add Endorsements, Showcase, Loadout, Highlights systems

### 1. Endorsement Models + Service
- **Changes:** Create `apps/user_profile/models/endorsement.py` with `SkillEndorsement`, `EndorsementOpportunity`
- **Changes:** Create `apps/user_profile/services/endorsement_service.py` with:
  - `create_endorsement_opportunity()` - triggered by Match COMPLETED signal
  - `endorse_teammate()` - validate teammate, unique per match
  - `aggregate_endorsements()` - count by skill (Aim, Shotcalling, Clutch, etc.)
- **Changes:** Connect signal: `Match.post_save` → create opportunities for participants
- **App:** `user_profile`, `tournament_ops` (signal)
- **Migration:** Add `SkillEndorsement` (match_id, endorser, receiver, skill_name, created_at), `EndorsementOpportunity` (match_id, participant_id, expires_at)

### 2. Endorsement Views + Templates
- **Changes:** Create `apps/user_profile/views/endorsement_views.py` with `EndorseTeammateView` (POST: match_id, receiver_id, skill)
- **Changes:** Create partials: `_endorsement_skill_meter.html`, `_tab_endorsements.html`
- **Changes:** Update `_tab_overview.html` to show top 3 endorsed skills
- **App:** `user_profile`
- **Context:** `endorsement_summary`, `recent_endorsement_matches`

### 3. Showcase Models + Service
- **Changes:** Create `apps/user_profile/models/showcase.py` with `ProfileFrame`, `ProfileBanner`, `UnlockedCosmetic`
- **Changes:** Extend `Badge` model: Add `unlocks_frame_id`, `unlocks_banner_id` FKs
- **Changes:** Extend `UserProfile` model: Add `equipped_frame_id`, `equipped_banner_id` FKs
- **Changes:** Create `apps/user_profile/services/showcase_service.py` with `unlock_cosmetic()`, `equip_cosmetic()`
- **App:** `user_profile`
- **Migration:** 3 new models + 4 new FKs

### 4. Showcase Views + Templates
- **Changes:** Create `apps/user_profile/views/showcase_views.py` with `ShowcaseSettingsView` (GET/POST: equip frames/banners)
- **Changes:** Create partials: `_cosmetic_item.html`, `_tab_inventory.html`
- **Changes:** Update `_hero_avatar.html` to display equipped frame (holographic ring overlay)
- **App:** `user_profile`
- **Context:** `unlocked_cosmetics`, `equipped_frame`, `equipped_banner`

### 5. Loadout Models + Service
- **Changes:** Create `apps/user_profile/models/loadout.py` with `HardwareProduct`, `UserHardware`, `GameConfig`, `GameSettingsSchema`
- **Changes:** Create `apps/user_profile/services/loadout_service.py` with:
  - `set_user_hardware()` - validate DPI in product specs
  - `set_game_config()` - validate against GameSettingsSchema
- **App:** `user_profile`
- **Migration:** 4 new models, hardware categories (MOUSE, KEYBOARD, HEADSET, MONITOR, MOUSEPAD)

### 6. Loadout Views + Templates
- **Changes:** Create `apps/user_profile/views/loadout_views.py` with `LoadoutSettingsView` (GET/POST: hardware + game configs)
- **Changes:** Create partials: `_hardware_item.html`, `_tab_loadout.html`, `_sidebar_gear_setup.html`
- **App:** `user_profile`
- **Context:** `user_hardware`, `game_configs`, `hardware_catalog` (cached 24h)

### 7. Highlight Models + Service
- **Changes:** Create `apps/user_profile/models/highlight.py` with `HighlightClip`
- **Changes:** Extend `UserProfile` model: Add `pinned_clip_id` FK
- **Changes:** Create `apps/user_profile/services/highlight_service.py` with:
  - `add_highlight_clip()` - validate URL, extract video_id
  - `reorder_clips()` - bulk update positions atomically
  - `pin_clip()` - set UserProfile.pinned_clip_id
- **App:** `user_profile`
- **Migration:** 1 model + 1 FK, add index on `(user_id, position)`

### 8. Highlight Views + Templates
- **Changes:** Create `apps/user_profile/views/highlight_views.py` with `HighlightAddView`, `HighlightReorderView`, `HighlightPinView`, `HighlightDeleteView`
- **Changes:** Create partials: `_highlight_video_embed.html`, `_tab_highlights.html`
- **Changes:** Update `_tab_overview.html` to show pinned clip
- **App:** `user_profile`
- **Context:** `pinned_clip`, `highlight_clips`, `can_add_more_clips`

### 9. Live Status + Stream Embed Service
- **Changes:** Create `apps/user_profile/services/live_status_service.py` with:
  - `get_live_match()` - query `Match.filter(state='LIVE', participant=user)`
  - `get_embed_url()` - construct Twitch/YouTube iframe URL with parent param
- **Changes:** Add `is_public` boolean field to `Match` model (hide scrims)
- **Changes:** Add cache invalidation signal: `Match.post_save` → invalidate `live_match:{user_id}` cache
- **App:** `user_profile`, `tournament_ops` (Match model extension)
- **Caching:** 1-minute TTL for live match status

### 10. Performance Optimization
- **Changes:** Add caching to profile view:
  - `cache.set(f'endorsement_stats:{user_id}', stats, 3600)` - 1 hour
  - `cache.set(f'live_match:{user_id}', match_id, 60)` - 1 minute
  - `cache.set('hardware_catalog', products, 86400)` - 24 hours
- **Changes:** Add `select_related()` / `prefetch_related()` to profile queries:
  - `UserProfile.select_related('pinned_clip', 'equipped_frame', 'equipped_banner')`
  - `Bounty.select_related('acceptor', 'game').prefetch_related('proofs')`
- **Changes:** Add database indexes (from P0 constraint migration + new models)
- **App:** `user_profile`, caching middleware

---

## P2 - MEDIUM PRIORITY (Post-MVP Enhancements)

**Effort:** ~50 days (10 weeks, 1 engineer)  
**Goal:** Admin tools, collusion detection, catalog seeding, advanced features

### 1. Endorsement Collusion Detection
- **Changes:** Create `apps/user_profile/services/collusion_detector.py` with `detect_mutual_endorsement_farming()`
- **Logic:** Aggregation query: pairs with >80% mutual endorsements flagged
- **App:** `user_profile`
- **Admin:** Add "Suspicious pairs" report to admin

### 2. Bounty Dispute Admin Workflow
- **Changes:** Extend `BountyDisputeAdmin` with proof viewer, resolution form, moderator notes
- **Changes:** Add `BountyDispute.moderator_notes` TextField
- **App:** `user_profile`
- **Migration:** Add moderator_notes field

### 3. Hardware Catalog Seeding
- **Changes:** Create fixture: `apps/user_profile/fixtures/hardware_catalog.json` with 200+ products (research required)
- **Categories:** Mouse (50), Keyboard (50), Headset (40), Monitor (40), Mousepad (20)
- **App:** `user_profile`
- **Effort:** 5 days (data entry + validation)

### 4. Game Settings Schemas
- **Changes:** Create fixture: `apps/user_profile/fixtures/game_settings_schemas.json` for 11 games
- **Games:** Valorant, CS2, PUBG, MLBB, Free Fire, Call of Duty, Apex, Fortnite, Overwatch, Rainbow Six, League of Legends
- **Schema Examples:** Valorant (sensitivity, DPI, crosshair), CS2 (viewmodel, rates)
- **App:** `user_profile`
- **Effort:** 8 days (per-game research)

### 5. Loadout Search
- **Changes:** Create `apps/user_profile/views/loadout_search.py` with `LoadoutSearchView` (query: hardware, game, pro player)
- **Changes:** Add Postgres full-text search on `HardwareProduct.name`, `UserHardware.user__username`
- **App:** `user_profile`
- **Migration:** Add GIN index on search fields

### 6. Bounty Feed Filters
- **Changes:** Extend `BountyListView` with filters: game, stake range, proof type
- **Changes:** Add pagination (50 per page)
- **App:** `user_profile`
- **Template:** Update `_tab_bounties.html` with filter dropdowns

### 7. TikTok Embed Support (Optional)
- **Changes:** Add TikTok to URL whitelist: `tiktok.com`, `vm.tiktok.com`
- **Changes:** Update `highlight_service.py` to extract TikTok video IDs
- **Changes:** Add CSP: `frame-src https://www.tiktok.com`
- **App:** `user_profile`
- **Effort:** 2 days (API research)

### 8. Animated Profile Frames (Cosmetics)
- **Changes:** Add `ProfileFrame.is_animated` boolean, `animation_url` field (WebM/GIF)
- **Changes:** Update `_hero_avatar.html` to render `<video>` or `<img>` based on frame type
- **App:** `user_profile`
- **Assets:** 10 animated frames (design team)

### 9. Team Bounties (Team vs Team)
- **Changes:** Extend `Bounty` model: Add `team_challenge` boolean, `challenger_team_id`, `opponent_team_id` FKs
- **Changes:** Update `accept_bounty()` to validate team captain acceptance
- **App:** `user_profile`, `teams`
- **Migration:** Add team FKs, update escrow logic (team wallet)

### 10. Clip Thumbnail Caching
- **Changes:** Create `apps/user_profile/services/thumbnail_service.py` with `fetch_thumbnail()` (YouTube/Twitch API)
- **Changes:** Add `HighlightClip.thumbnail_url` cached field
- **Changes:** Add Celery task: `refresh_clip_thumbnails()` (runs weekly)
- **App:** `user_profile`
- **Storage:** S3 or CDN for thumbnails

---

## TESTING REQUIREMENTS (All Priorities)

### P0 Tests (Critical)
- `test_bounty_escrow.py` - idempotency, race conditions, double refund prevention
- `test_bounty_service.py` - create, accept, complete, expire, cancel, dispute flows
- `test_url_validation.py` - whitelist enforcement, HTTPS, XSS prevention
- `test_wallet_permissions.py` - owner-only gating, context filtering

### P1 Tests (High Priority)
- `test_endorsement_service.py` - match signal, teammate validation, uniqueness
- `test_showcase_service.py` - badge unlock, equip validation, unlock immutability
- `test_loadout_service.py` - hardware validation, DPI checks, game config schema
- `test_highlight_service.py` - URL parsing, reordering atomicity, pin logic

### P2 Tests (Medium Priority)
- `test_collusion_detector.py` - mutual endorsement farming detection
- `test_bounty_dispute.py` - moderator workflow, resolution outcomes
- `test_loadout_search.py` - full-text search accuracy

---

## MIGRATION SEQUENCE

1. `0001_bounty_models.py` - Bounty, BountyAcceptance, BountyProof, BountyDispute
2. `0002_economy_constraints.py` - Wallet check constraint, transaction indexes
3. `0003_endorsement_models.py` - SkillEndorsement, EndorsementOpportunity
4. `0004_showcase_models.py` - ProfileFrame, ProfileBanner, UnlockedCosmetic + Badge FKs
5. `0005_loadout_models.py` - HardwareProduct, UserHardware, GameConfig, GameSettingsSchema
6. `0006_highlight_models.py` - HighlightClip + UserProfile.pinned_clip_id FK
7. `0007_match_is_public.py` - Add Match.is_public boolean
8. `0008_performance_indexes.py` - All composite indexes, GIN indexes for search

---

## ROLLBACK PLAN

**If Critical Issues Detected:**
1. Revert URL routing to `public_v4.html` (1 line change in `urls.py`)
2. Disable bounty creation endpoint via feature flag (`ENABLE_BOUNTY_SYSTEM=False` in settings)
3. Archive new models but keep migrations applied (data preserved)
4. Monitor error logs for template rendering failures (target <5% error rate)

**Rollback Triggers:**
- Template errors >5%
- Page load time >3 seconds
- Bounce rate increase >20%
- CSP violations detected
- User complaints >10 in first 24 hours

---

**END OF EXECUTION PLAN**

**Status:** ✅ Ready for Implementation  
**Next Step:** Begin P0 - Item 1 (Archive Current Templates)
