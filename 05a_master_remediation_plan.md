# Master Remediation Plan
**Date:** December 31, 2025  
**Owner:** Principal Engineer  
**Type:** Implementation Roadmap (NO CODE)  
**Status:** Ready for Review

---

## 1. CURRENT STATE SUMMARY

### What Exists and is Reusable

**apps/economy/**
- ✅ `DeltaCrownWallet` with `pending_balance` field (ready for bounty escrow)
- ✅ `DeltaCrownTransaction` with idempotency_key (prevents double-spend)
- ✅ Atomic transaction services (`credit()`, `debit()`) with row locking
- ✅ Balance recalculation logic (`recalc_and_save()`)
- ✅ Transaction history queries with reason filtering

**apps/tournaments + apps/tournament_ops/**
- ✅ `Match` model with 9-state machine (SCHEDULED→LIVE→COMPLETED→DISPUTED)
- ✅ Match result submission workflow (`report_match_result()`)
- ✅ Dispute resolution patterns (moderator queue, evidence tracking)
- ✅ Post-match completion signals for triggering downstream events

**apps/teams/**
- ✅ `Team` model with captain property (OWNER role-based)
- ✅ `TeamMembership` with 6 roles (OWNER, ADMIN, MEMBER, etc.)
- ✅ Roster limits (max 8 members)
- ✅ Team notification system (captain alerts for roster changes)

**apps/user_profile/**
- ✅ `UserProfile` with privacy settings (`is_private`, `hide_earnings`)
- ✅ `ProfilePermissionChecker` with 4 viewer roles (owner, teammate, follower, anonymous)
- ✅ `UserActivity` immutable event log (17+ event types)
- ✅ `Badge` system with rarity tiers (Common/Rare/Epic/Legendary)
- ✅ `SocialLink` for external profiles (Twitter, Instagram, Discord)

**apps/games/**
- ✅ `Game` model (11 games: Valorant, CS2, PUBG, MLBB, etc.)
- ✅ `Rank` model with tier/division (Diamond II, Platinum I, etc.)
- ✅ Game-specific metadata (icon URLs, display names)

**What Does NOT Exist:**
- ❌ **apps/community/** - No Post/Feed models found (Posts tab feature deferred or not implemented)

---

## 2. CRITICAL GAPS

### New Models Required

**apps/user_profile/models/** (Bounty System)
- ❌ `Bounty` (9-state lifecycle, escrow tracking, expiry)
- ❌ `BountyAcceptance` (acceptor, accepted_at, proof submission)
- ❌ `BountyProof` (screenshot/video URLs, submitted_by, submission_time)
- ❌ `BountyDispute` (raised_by, reason, moderator_resolution)

**apps/user_profile/models/** (Endorsements + Showcase)
- ❌ `SkillEndorsement` (match_id FK, endorser, receiver, skill_name, anonymous)
- ❌ `EndorsementOpportunity` (match_id, participant_id, expires_at)
- ❌ `ProfileFrame` (asset_url, rarity, unlock_requirement)
- ❌ `ProfileBanner` (asset_url, rarity, unlock_requirement)
- ❌ `UnlockedCosmetic` (user, cosmetic_type, cosmetic_id, unlocked_at)
- **Extend** `Badge` with `unlocks_frame_id`, `unlocks_banner_id` FKs

**apps/user_profile/models/** (Loadout + Live Status)
- ❌ `HardwareProduct` (name, category, brand, specs_json, affiliate_url)
- ❌ `UserHardware` (user, category, product FK, custom_settings_json)
- ❌ `GameConfig` (user, game FK, settings_json, last_updated)
- ❌ `GameSettingsSchema` (game FK, schema_json, version)
- **Extend** `SocialLink` or `UserProfile` with stream config fields (platform, channel_id, is_live_override)

**apps/user_profile/models/** (Highlights)
- ❌ `HighlightClip` (user, platform, video_id, url, title, description, position, added_at)
- **Extend** `UserProfile` with `pinned_clip_id` FK (nullable, to HighlightClip)

### New Services Required

**apps/economy/services.py**
- ❌ `lock_bounty_stake(wallet, amount, bounty_id)` → debit + increment pending_balance
- ❌ `release_bounty_escrow(wallet, amount, bounty_id)` → decrement pending_balance
- ❌ `refund_bounty_stake(wallet, amount, bounty_id)` → decrement pending + credit
- ❌ `collect_platform_fee(bounty, fee_amount)` → credit platform wallet

**apps/user_profile/services/** (NEW FILE: bounty_service.py)
- ❌ `create_bounty(creator, stake, game, proof_requirement, expiry_hours)`
- ❌ `accept_bounty(bounty, acceptor)` → validate reputation, not blocked, not self
- ❌ `submit_bounty_result(bounty, submitter, result, proof_url)`
- ❌ `complete_bounty(bounty, winner)` → release escrow, award prize, platform fee
- ❌ `raise_bounty_dispute(bounty, disputer, reason)`
- ❌ `resolve_bounty_dispute(bounty, moderator, decision)`
- ❌ `expire_bounty(bounty)` → refund creator, called by Celery task
- ❌ `cancel_bounty(bounty, canceller)` → validate state, refund if OPEN

**apps/user_profile/services/** (NEW FILE: endorsement_service.py)
- ❌ `create_endorsement_opportunity(match)` → triggered on match COMPLETED signal
- ❌ `endorse_teammate(match, endorser, receiver, skill)` → validate teammate, unique per match
- ❌ `aggregate_endorsements(user)` → count by skill, total, top skill
- ❌ `unlock_cosmetic(user, badge)` → check badge.unlocks_frame_id, create UnlockedCosmetic

**apps/user_profile/services/** (NEW FILE: loadout_service.py)
- ❌ `set_user_hardware(user, category, product, custom_settings)` → validate DPI in product.specs
- ❌ `set_game_config(user, game, settings)` → validate against GameSettingsSchema
- ❌ `get_embed_url(platform, channel_identifier)` → construct Twitch/YouTube embed URL
- ❌ `get_live_match(user)` → query Match.filter(state='LIVE', participant=user)

**apps/user_profile/services/** (NEW FILE: highlight_service.py)
- ❌ `add_highlight_clip(user, url)` → validate URL whitelist, extract video_id, create HighlightClip
- ❌ `reorder_clips(user, clip_positions)` → bulk update positions atomically
- ❌ `pin_clip(user, clip)` → set UserProfile.pinned_clip_id
- ❌ `validate_video_url(url)` → check domain whitelist, extract platform + video_id

### New Views Required

**apps/user_profile/views/bounty_views.py**
- ❌ `BountyCreateView` (POST: form with stake, game, proof_requirement)
- ❌ `BountyAcceptView` (POST: bounty_id)
- ❌ `BountySubmitResultView` (POST: result, proof_url)
- ❌ `BountyDisputeView` (POST: bounty_id, reason)
- ❌ `BountyListView` (GET: active bounties feed, filters by game/stake)
- ❌ `BountyDetailView` (GET: bounty detail, proofs, dispute status)

**apps/user_profile/views/endorsement_views.py**
- ❌ `EndorseTeammateView` (POST: match_id, receiver_id, skill)
- ❌ `ShowcaseSettingsView` (GET/POST: equip frames/banners)
- ❌ `BadgePinView` (POST: badge_ids for 3 pinned slots)

**apps/user_profile/views/loadout_views.py**
- ❌ `LoadoutSettingsView` (GET/POST: hardware selection, game configs)
- ❌ `StreamConfigView` (POST: platform, channel, is_live_override)

**apps/user_profile/views/highlight_views.py**
- ❌ `HighlightAddView` (POST: video_url)
- ❌ `HighlightReorderView` (POST: clip_positions array)
- ❌ `HighlightPinView` (POST: clip_id)
- ❌ `HighlightDeleteView` (POST: clip_id)

### New Templates Required

**apps/user_profile/templates/user_profile/profile/**
- ❌ `_bounties_section.html` (Overview tab: active/completed bounties)
- ❌ `_endorsements_section.html` (Overview tab: skill breakdown chart)
- ❌ `_showcase_section.html` (Overview tab: pinned badges + equipped frame/banner)
- ❌ `_loadout_section.html` (Loadout tab: hardware + game configs)
- ❌ `_live_status_banner.html` (Overview tab: "🔴 LIVE in Tournament" banner)
- ❌ `_stream_embed.html` (Sidebar: Twitch/YouTube iframe embed)
- ❌ `_pinned_clip.html` (Overview tab: hero clip embed)
- ❌ `_highlights_grid.html` (Highlights tab: 3-column video grid)

**apps/user_profile/templates/user_profile/settings/**
- ❌ `bounty_settings.html` (Bounty cooldown, max pending, reputation display)
- ❌ `showcase_settings.html` (Frame/banner selection, badge pinning)
- ❌ `loadout_settings.html` (Hardware catalog, game config forms)
- ❌ `stream_settings.html` (Platform link, embed preferences)
- ❌ `highlight_settings.html` (Add clip form, reorder interface)

### New Celery Tasks Required

**apps/user_profile/tasks.py**
- ❌ `expire_bounties_task()` → runs every 15 minutes, select expired bounties, refund
- ❌ `expire_endorsement_opportunities_task()` → runs daily, cleanup 24h+ old opportunities
- ❌ `cleanup_broken_highlights_task()` → runs weekly, detect 404 embeds (optional)

### New Admin Interfaces Required

**apps/user_profile/admin.py**
- ❌ `BountyAdmin` (list view: status, stake, creator, acceptor; actions: force_complete, force_refund)
- ❌ `BountyDisputeAdmin` (moderation queue: view proofs, resolve disputes)
- ❌ `SkillEndorsementAdmin` (read-only audit: detect collusion patterns)
- ❌ `HardwareProductAdmin` (add products, edit specs_json, validate affiliate URLs)
- ❌ `GameSettingsSchemaAdmin` (define per-game settings schemas)
- ❌ `HighlightClipAdmin` (moderation: reported clips, disable user embed privilege)

---

## 3. FIX LIST BY MODULE

### apps/user_profile/

**Models to Create:**
- `models/bounty.py`: Bounty, BountyAcceptance, BountyProof, BountyDispute (4 models)
- `models/endorsement.py`: SkillEndorsement, EndorsementOpportunity (2 models)
- `models/showcase.py`: ProfileFrame, ProfileBanner, UnlockedCosmetic (3 models)
- `models/loadout.py`: HardwareProduct, UserHardware, GameConfig, GameSettingsSchema (4 models)
- `models/highlight.py`: HighlightClip (1 model)
- **Extend** `models/user_profile.py`: Add `pinned_clip_id` FK, stream config fields (if not using SocialLink)
- **Extend** `models/badge.py`: Add `unlocks_frame_id`, `unlocks_banner_id` FKs

**Services to Create:**
- `services/bounty_service.py`: 8 methods (create, accept, submit_result, complete, dispute, resolve, expire, cancel)
- `services/endorsement_service.py`: 4 methods (create_opportunity, endorse, aggregate, unlock_cosmetic)
- `services/loadout_service.py`: 4 methods (set_hardware, set_game_config, get_embed_url, get_live_match)
- `services/highlight_service.py`: 4 methods (add_clip, reorder, pin, validate_url)

**Views to Create:**
- `views/bounty_views.py`: 6 views (create, accept, submit_result, dispute, list, detail)
- `views/endorsement_views.py`: 3 views (endorse, showcase_settings, badge_pin)
- `views/loadout_views.py`: 2 views (loadout_settings, stream_config)
- `views/highlight_views.py`: 4 views (add, reorder, pin, delete)

**URLs to Add:**
- `urls.py`: 15+ new routes for bounty/endorsement/loadout/highlight endpoints

**Templates to Create:**
- `templates/user_profile/profile/`: 8 partial templates (_bounties, _endorsements, _showcase, _loadout, _live_status, _stream_embed, _pinned_clip, _highlights_grid)
- `templates/user_profile/settings/`: 5 settings pages (bounty, showcase, loadout, stream, highlight)

**Tasks to Create:**
- `tasks.py`: 3 Celery periodic tasks (expire_bounties, expire_endorsements, cleanup_highlights)

**Admin to Create:**
- `admin.py`: 6 admin interfaces (Bounty, BountyDispute, SkillEndorsement, HardwareProduct, GameSettingsSchema, HighlightClip)

**Context Processors to Update:**
- `context_processors.py`: Add `bounty_stats`, `endorsement_stats`, `live_match`, `stream_config`, `pinned_clip`, `highlight_clips`

**Tests to Create:**
- `tests/test_bounty_service.py`: Escrow flow, expiry, dispute resolution
- `tests/test_endorsement_service.py`: Match completion trigger, duplicate prevention
- `tests/test_loadout_service.py`: Hardware validation, game config schema
- `tests/test_highlight_service.py`: URL validation, XSS prevention, reordering

---

### apps/economy/

**Services to Extend:**
- `services.py`: Add 4 bounty-specific methods (lock_stake, release_escrow, refund_stake, collect_fee)

**Transaction Reasons to Add:**
- `models.py` → `DeltaCrownTransaction.Reason`: Add `BOUNTY_ESCROW`, `BOUNTY_WIN`, `BOUNTY_REFUND`, `BOUNTY_FEE`

**Queries to Optimize:**
- Add database index: `DeltaCrownTransaction.idempotency_key` (already unique, verify index exists)
- Add database check constraint: `DeltaCrownWallet.cached_balance >= pending_balance` (data integrity)

**Tests to Create:**
- `tests/test_bounty_transactions.py`: Idempotency, race conditions, double refund prevention

---

### apps/tournaments + apps/tournament_ops/

**Signals to Add:**
- `signals.py`: Connect to `Match.state` change → trigger `create_endorsement_opportunity()` when COMPLETED
- `signals.py`: Invalidate live_match cache when Match transitions to/from LIVE state

**Match Model to Extend:**
- `models/match.py`: Add `is_public` boolean field (default True, hide scrims from live status)

**Services to Update:**
- `match_service.py`: Ensure `complete_match()` triggers endorsement opportunity creation

**Tests to Create:**
- `tests/test_endorsement_trigger.py`: Verify signal fires, opportunities created for all participants

---

### apps/teams/

**No Critical Changes Required**
- ✅ Existing captain notification system can be reused for team bounty alerts
- ✅ TeamMembership queries already support roster verification for endorsements

**Optional Enhancements:**
- Team-level bounty challenges (one team vs another, not individual) - defer to Phase 2
- Team endorsement aggregation ("Most endorsed team for Shotcalling") - defer to Phase 2

---

### apps/community/ (MISSING)

**Status:** ❌ **DOES NOT EXIST**

**Impact on Profile Expansion:**
- "Posts" tab cannot be implemented until community app exists
- Post/Feed models would live in separate `apps/community/` module
- Defer Posts feature OR create minimal Post model in `apps/user_profile/` if needed urgently

**Recommendation:** Defer Posts tab to Phase 3, focus on Bounty/Endorsements/Loadout/Highlights first

---

## 4. SECURITY & PRIVACY MUST-HAVES

### Wallet & Escrow Security

**Critical (P0):**
- [ ] All bounty escrow operations wrapped in `@transaction.atomic`
- [ ] All wallet updates use `select_for_update()` row locking (prevent race conditions)
- [ ] Idempotency keys on ALL financial transactions: `f"bounty:{action}:{bounty_id}:{wallet_id}"`
- [ ] Database check constraint: `CHECK (cached_balance - pending_balance >= 0)` (no negative available balance)
- [ ] Platform fee calculation stored in database config (not hardcoded): `SiteSetting.get('bounty_platform_fee')` = 0.05
- [ ] Expiry task uses `select_for_update()` when querying bounties (lock rows during expiry check)
- [ ] Double refund prevention: Rely on idempotency_key unique constraint (second refund returns existing transaction)

### Permissions & Access Control

**Critical (P0):**
- [ ] Bounty creation: Check `creator.reputation >= 50` (prevent throwaway accounts)
- [ ] Bounty acceptance: Check `acceptor != creator` (no self-acceptance)
- [ ] Bounty acceptance: Check `not creator.blocked_users.filter(id=acceptor.id).exists()` (respect block lists)
- [ ] Endorsement creation: Verify endorser in match participant list (roster snapshot at match start)
- [ ] Endorsement creation: Verify receiver is teammate (same team side in match)
- [ ] Endorsement creation: Check unique constraint `(match_id, endorser)` enforced (one endorsement per match)
- [ ] Cosmetic unlock: Verify user owns prerequisite badge before creating UnlockedCosmetic
- [ ] Cosmetic equip: Verify UnlockedCosmetic record exists before setting UserProfile.equipped_frame_id
- [ ] Loadout visibility: Exclude from search if `UserProfile.is_private=True` (privacy cascade)
- [ ] Highlight clip operations: Verify `request.user == clip.user` (only owner can edit/delete/reorder)

### URL Validation & XSS Prevention

**Critical (P0):**
- [ ] Stream embed URL whitelist: Domain must be in `['player.twitch.tv', 'www.youtube.com', 'www.facebook.com']`
- [ ] Highlight URL whitelist: Domain must be in `['youtube.com', 'youtu.be', 'twitch.tv', 'clips.twitch.tv', 'medal.tv']`
- [ ] HTTPS enforcement: Reject URLs starting with `http://` (only `https://` allowed)
- [ ] Video ID character whitelist: Only `[a-zA-Z0-9_-]` allowed (no path separators, SQL keywords)
- [ ] Affiliate URL whitelist: `HardwareProduct.affiliate_url` must match `^https://(amazon|logitech|razer)\.com/.*$`
- [ ] User input sanitization: Strip ALL HTML tags from `HighlightClip.title` and `HighlightClip.description` (except `<br>` in description)
- [ ] Django template auto-escaping: NEVER use `|safe` filter on user-provided content (clip titles, bounty descriptions)

### Iframe Sandbox & CSP

**Critical (P0):**
- [ ] All iframe embeds include `sandbox="allow-scripts allow-same-origin"` (no allow-top-navigation, no allow-forms)
- [ ] Iframe lazy loading: `<iframe loading="lazy">` attribute on all embeds (performance + security)
- [ ] CSP frame-src directive: `Content-Security-Policy: frame-src https://youtube.com https://www.youtube.com https://clips.twitch.tv https://medal.tv`
- [ ] CSP script-src directive: `Content-Security-Policy: script-src 'self'` (no unsafe-inline, no unsafe-eval)
- [ ] CSP frame-ancestors directive: `Content-Security-Policy: frame-ancestors 'none'` (prevent clickjacking)
- [ ] Twitch parent parameter: All Twitch embeds include `&parent={SITE_DOMAIN}` (hardcoded, not user-provided)
- [ ] Referrer policy on iframes: `<iframe referrerpolicy="no-referrer">` (privacy, don't leak profile URL to platforms)

### Rate Limiting & Anti-Abuse

**Critical (P0):**
- [ ] Bounty creation: Max 10 bounties per user per 24 hours (enforced in `create_bounty()`)
- [ ] Bounty creation: 1-hour cooldown between bounty creations (`user.last_bounty_created_at` check)
- [ ] Bounty acceptance: Max 3 concurrent accepted bounties per user (prevents hoarding)
- [ ] Endorsement creation: Max 50 endorsements per user per day (prevents spam)
- [ ] Highlight clip creation: Max 5 clips per hour per user (prevents spam)
- [ ] Highlight reordering: Max 10 reorder actions per minute per user (prevents API abuse)
- [ ] Stream toggle: Max 5 stream enable/disable per hour per user (prevents notification spam)
- [ ] All rate limits enforced via Django cache or database timestamp checks (not just client-side)

### Data Integrity & Immutability

**Critical (P0):**
- [ ] SkillEndorsement immutable: No update/delete methods (once created, permanent audit trail)
- [ ] BountyProof immutable: No update after submission (timestamp and submitter cannot be changed)
- [ ] DeltaCrownTransaction immutable: Existing enforcement verified for bounty transactions
- [ ] Match completion timestamp immutable: `Match.completed_at` set by system (not user-editable), used for endorsement window
- [ ] Cosmetic unlock immutable: UnlockedCosmetic records never deleted (even if badge revoked)

---

## 5. PERFORMANCE MUST-HAVES

### Query Optimization Targets

**Critical (P0 - Profile View):**
- [ ] Bounty stats: `user.bounties_created.select_related('acceptor', 'game').prefetch_related('proofs')`
- [ ] Endorsement stats: Cached aggregation: `cache.get(f'endorsement_stats:{user.id}')` TTL=1 hour
- [ ] Live match: Cached query: `cache.get(f'live_match:{user.id}')` TTL=1 minute, invalidate on Match state change
- [ ] Highlight clips: `user.highlight_clips.order_by('position')[:20]` (limit 20, indexed on position)
- [ ] Pinned clip: `UserProfile.select_related('pinned_clip')` (avoid N+1 on profile load)
- [ ] Equipped cosmetics: `UserProfile.select_related('equipped_frame', 'equipped_banner')` (single query)

**High Priority (P1 - Settings Pages):**
- [ ] Unlocked cosmetics: `UnlockedCosmetic.filter(user=user).select_related('cosmetic')` (avoid N+1)
- [ ] Hardware catalog: `HardwareProduct.objects.all()` cached for 24 hours (rarely changes)
- [ ] Game configs: `GameConfig.filter(user=user).select_related('game')` (single query for all 11 games)
- [ ] Bounty feed: `Bounty.filter(status='OPEN').select_related('creator', 'game')[:50]` paginated

**Medium Priority (P2 - Admin):**
- [ ] Bounty disputes: `BountyDispute.select_related('bounty', 'raised_by', 'moderator')` (moderation queue)
- [ ] Endorsement collusion detection: Aggregation query with HAVING clause (flag pairs with >80% mutual endorsements)

### Database Indexes

**Critical (P0):**
- [ ] Bounty: Composite index on `(status, expires_at)` for expiry task query
- [ ] Bounty: Composite index on `(creator_id, status)` for user's active bounties
- [ ] SkillEndorsement: Composite index on `(match_id, endorser)` for uniqueness enforcement
- [ ] SkillEndorsement: Index on `receiver_id` for aggregation queries
- [ ] HighlightClip: Composite index on `(user_id, position)` for ordered retrieval
- [ ] GameConfig: Composite index on `(user_id, game_id)` for per-game lookups
- [ ] Match: Index on `state` for live match queries (`WHERE state='LIVE'`)
- [ ] EndorsementOpportunity: Composite index on `(participant_id, expires_at)` for expiry cleanup

**High Priority (P1):**
- [ ] UnlockedCosmetic: Composite index on `(user_id, cosmetic_type, cosmetic_id)` for unlock checks
- [ ] BountyAcceptance: Index on `acceptor_id` for user's accepted bounties
- [ ] UserHardware: Composite index on `(user_id, category)` for hardware lookout

### Caching Strategy

**Critical (P0):**
- [ ] Endorsement stats: `cache.set(f'endorsement_stats:{user_id}', stats, timeout=3600)` invalidate on new endorsement
- [ ] Live match status: `cache.set(f'live_match:{user_id}', match_id, timeout=60)` invalidate on Match state change
- [ ] Hardware catalog: `cache.set('hardware_catalog', products, timeout=86400)` (24 hours, rarely changes)
- [ ] Game settings schemas: `cache.set(f'game_schema:{game_id}', schema, timeout=86400)` (rarely changes)

**High Priority (P1):**
- [ ] Bounty feed: `cache.set('open_bounties_page_1', bounties, timeout=300)` (5 minutes, paginated)
- [ ] Profile cosmetics: `cache.set(f'equipped_cosmetics:{user_id}', cosmetics, timeout=3600)` invalidate on equip change

---

## 6. PRIORITY TABLE WITH EFFORT ESTIMATES

### P0 - CRITICAL (Launch Blockers)

| Feature | Module | Effort | Dependencies | Risk |
|---------|--------|--------|--------------|------|
| **Bounty Escrow** | economy/services | 3 days | DeltaCrownWallet, idempotency | HIGH - Money handling |
| **Bounty Models** | user_profile/models | 2 days | None | MEDIUM - Complex state machine |
| **Bounty Service** | user_profile/services | 5 days | Bounty models, escrow | HIGH - Business logic |
| **Bounty Expiry Task** | user_profile/tasks | 2 days | Bounty service, Celery | HIGH - Race conditions |
| **Bounty Views** | user_profile/views | 4 days | Bounty service | MEDIUM - CSRF, permissions |
| **Bounty Templates** | user_profile/templates | 3 days | Views | LOW - Frontend only |
| **URL Validation** | user_profile/services | 1 day | None | HIGH - XSS prevention |
| **Iframe Sandbox** | templates/base | 1 day | None | HIGH - Clickjacking |
| **CSP Headers** | settings/middleware | 1 day | None | HIGH - XSS prevention |
| **Wallet Locking** | economy/services | 1 day | SELECT FOR UPDATE | HIGH - Race conditions |
| **Idempotency Enforcement** | economy/tests | 2 days | Transaction service | HIGH - Double-spend |
| **Bounty Tests** | user_profile/tests | 4 days | Bounty service | MEDIUM - Coverage |

**P0 Total Effort: ~29 days (6 weeks with 1 engineer)**

---

### P1 - HIGH PRIORITY (MVP Features)

| Feature | Module | Effort | Dependencies | Risk |
|---------|--------|--------|--------------|------|
| **Endorsement Models** | user_profile/models | 2 days | Match, TeamMembership | LOW |
| **Endorsement Service** | user_profile/services | 3 days | Match signals | MEDIUM - Collusion detection |
| **Endorsement Views** | user_profile/views | 2 days | Endorsement service | LOW |
| **Endorsement Templates** | user_profile/templates | 2 days | Views | LOW |
| **Showcase Models** | user_profile/models | 2 days | Badge, UnlockedCosmetic | LOW |
| **Showcase Service** | user_profile/services | 2 days | Badge unlock logic | LOW |
| **Showcase Views** | user_profile/views | 2 days | Showcase service | LOW |
| **Showcase Templates** | user_profile/templates | 3 days | Views, asset display | MEDIUM - Responsive design |
| **Loadout Models** | user_profile/models | 3 days | Game, JSON schemas | MEDIUM - Schema validation |
| **Loadout Service** | user_profile/services | 3 days | Hardware catalog | MEDIUM - Validation logic |
| **Loadout Views** | user_profile/views | 3 days | Loadout service | LOW |
| **Loadout Templates** | user_profile/templates | 4 days | Views, hardware grid | MEDIUM - Complex forms |
| **Highlight Models** | user_profile/models | 1 day | UserProfile FK | LOW |
| **Highlight Service** | user_profile/services | 3 days | URL validation, platform APIs | MEDIUM - Embed construction |
| **Highlight Views** | user_profile/views | 2 days | Highlight service | LOW |
| **Highlight Templates** | user_profile/templates | 3 days | Views, grid layout | MEDIUM - Responsive embeds |
| **Live Status Service** | user_profile/services | 2 days | Match queries, caching | MEDIUM - Performance |
| **Stream Embed Service** | user_profile/services | 2 days | URL construction, Twitch parent | HIGH - Security |
| **Admin Interfaces** | user_profile/admin | 3 days | All models | LOW - Django admin |
| **Endorsement Expiry Task** | user_profile/tasks | 1 day | EndorsementOpportunity | LOW |
| **Performance Indexes** | migrations | 2 days | All models | MEDIUM - Query optimization |
| **Caching Layer** | services/middleware | 2 days | Redis/Memcached | MEDIUM - Cache invalidation |

**P1 Total Effort: ~52 days (10 weeks with 1 engineer)**

---

### P2 - MEDIUM PRIORITY (Post-MVP Enhancements)

| Feature | Module | Effort | Dependencies | Risk |
|---------|--------|--------|--------------|------|
| **Bounty Dispute Moderation** | user_profile/admin | 3 days | BountyDispute model | MEDIUM - Moderator workflow |
| **Endorsement Collusion Detection** | user_profile/services | 3 days | Aggregation queries | MEDIUM - False positives |
| **Hardware Catalog Seeding** | fixtures/scripts | 5 days | Product research (200+ items) | LOW - Data entry |
| **Game Settings Schemas** | fixtures/scripts | 8 days | 11 games × research | MEDIUM - Per-game accuracy |
| **Loadout Search** | user_profile/views | 4 days | Elasticsearch or Postgres FTS | MEDIUM - Performance |
| **Bounty Feed Filters** | user_profile/views | 2 days | Query optimization | LOW |
| **TikTok Embed Support** | highlight service | 2 days | TikTok API research | LOW - Optional platform |
| **Animated Frames** | showcase templates | 3 days | WebM/GIF assets | LOW - Optional cosmetics |
| **Stream Analytics** | user_profile/services | 4 days | Event tracking | LOW - Future phase |
| **Loadout Export** | user_profile/views | 2 days | JSON generation | LOW - Nice-to-have |
| **Team Bounties** | user_profile/models | 5 days | Team vs Team logic | MEDIUM - Complex validation |
| **Clip Categories** | highlight models | 2 days | Tags/filters | LOW |
| **Thumbnail Caching** | highlight service | 3 days | S3/CDN integration | MEDIUM - Storage costs |
| **Endorsement Trends** | user_profile/views | 2 days | Time-series queries | LOW |
| **Bounty Reputation Decay** | user_profile/services | 2 days | Reputation system | MEDIUM - Balancing |

**P2 Total Effort: ~50 days (10 weeks with 1 engineer)**

---

## 7. IMPLEMENTATION SEQUENCE

### Phase 1: Foundation (Weeks 1-6) - P0 Only
**Goal:** Launch Bounty System MVP with escrow security

1. **Week 1-2:** Bounty models + economy escrow services + tests
2. **Week 3-4:** Bounty service layer + expiry task + dispute model
3. **Week 5:** Bounty views + templates + admin
4. **Week 6:** Security hardening (CSP, sandbox, rate limits) + QA

**Deliverable:** Users can create/accept/complete bounties with real money escrow

---

### Phase 2: Enrichment (Weeks 7-16) - P1 Features
**Goal:** Complete profile expansion with Endorsements, Showcase, Loadout, Highlights

1. **Week 7-8:** Endorsement models + service + match signal integration
2. **Week 9-10:** Showcase models + cosmetic unlock flow + equip UI
3. **Week 11-13:** Loadout models + hardware catalog (100 products) + game configs (Valorant, CS2)
4. **Week 14-15:** Highlight models + URL validation + embed construction
5. **Week 16:** Live status + stream embed + admin moderation tools

**Deliverable:** Full profile feature set live, all tabs functional

---

### Phase 3: Optimization (Weeks 17-26) - P2 Enhancements
**Goal:** Performance tuning, advanced features, remaining game schemas

1. **Week 17-19:** Bounty dispute moderation + endorsement collusion detection
2. **Week 20-22:** Hardware catalog expansion (200+ products) + remaining 9 game schemas
3. **Week 23-24:** Loadout search + bounty feed filters + performance indexes
4. **Week 25-26:** Optional features (TikTok embeds, animated frames, analytics)

**Deliverable:** Production-ready system with full feature set

---

## 8. CRITICAL PATH & BLOCKERS

### Hard Dependencies (Must Complete in Order)

1. **Bounty escrow** → Requires economy service extensions → Blocks all bounty features
2. **Match COMPLETED signal** → Triggers endorsement opportunities → Blocks endorsement system
3. **Badge unlock logic** → Unlocks cosmetics → Blocks showcase display
4. **URL validation** → Security prerequisite → Blocks highlight/stream embeds
5. **CSP headers** → Security prerequisite → Blocks all iframe embeds

### Parallel Work Streams (Can Develop Simultaneously)

**Stream A (Bounty):** Models → Services → Views → Templates → Tests  
**Stream B (Endorsements):** Models → Services → Match signals → Views → Templates  
**Stream C (Loadout):** Models → Hardware catalog → Services → Views → Templates  
**Stream D (Highlights):** Models → URL validation → Services → Views → Templates  
**Stream E (Security):** CSP headers → Iframe sandbox → Rate limiting → Tests

**Recommendation:** Assign 3 engineers to Streams A/B/C simultaneously, 1 engineer to Stream E (security hardening across all features)

---

## 9. RISK MITIGATION CHECKLIST

### Before Launch (P0 Security)
- [ ] Penetration testing on bounty escrow (double-spend, race conditions)
- [ ] Load testing on expiry task (1000+ concurrent expirations)
- [ ] XSS fuzzing on all user input fields (titles, descriptions, URLs)
- [ ] CSP violation monitoring enabled (track blocked iframe attempts)
- [ ] Rate limit testing (automated spam scripts)
- [ ] Idempotency key collision testing (UUID generation)

### Post-Launch (P1 Monitoring)
- [ ] Bounty escrow balance reconciliation (nightly job)
- [ ] Endorsement collusion detection (weekly report)
- [ ] Highlight embed 404 monitoring (broken video detection)
- [ ] Stream toggle abuse detection (notification spam)
- [ ] Database query performance monitoring (slow query log)
- [ ] Cache hit rate tracking (optimize TTLs)

---

**END OF MASTER REMEDIATION PLAN**

**Status:** ✅ Ready for Engineering Team Review  
**Next Steps:**
1. Assign engineers to parallel work streams
2. Set up project tracking (Jira epics for Bounty/Endorsements/Loadout/Highlights)
3. Schedule weekly architecture reviews (Weeks 2, 6, 10, 16)
4. Plan security audit at end of Phase 1 (before Bounty launch)
5. Coordinate with DevOps for Celery task deployment (expiry jobs)
