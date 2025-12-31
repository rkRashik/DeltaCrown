# User Profile Expansion: System Understanding Document

**Date:** December 31, 2025  
**Role:** Principal Backend Architect  
**Type:** Analysis Only (No Code)

---

## 1. Executive Summary: What This Document Does

This document corrects misunderstandings from the initial audit report (`user_profile_audit_report_Dec.md`) and establishes the **true product design** for DeltaCrown's User Profile expansion. 

The previous audit made several incorrect assumptions about what features needed to be built. After re-reading the template documentation, analyzing existing apps, and understanding DeltaCrown's architecture, I now understand:

- **What doesn't need to be built** (cosmetic stores, media uploads, messaging)
- **What can be reused** (tournament system, economy integration)
- **What actually needs creation** (bounty escrow, post-match endorsements, achievement showcase)

---

## 2. Corrected Understanding: Feature-by-Feature Analysis

### 2.1 Bounty System (Peer-to-Peer Challenges)

#### **What I Previously Assumed (WRONG):**
- Tournament-style registration system
- Admin-managed events only
- Complex bracket generation

#### **What It Actually Is:**
**Escrow-based, peer-to-peer challenge system** where ANY user can:
1. Create a challenge ("1v1 me in Gridshot, first to 100k, 5000 DeltaCoins buy-in")
2. Lock their stake in escrow (deducted from wallet immediately)
3. Other users browse open bounties and accept them
4. Winner takes all (minus platform fee)

#### **Key Characteristics:**
- **Open to all users** (not limited to tournament participants)
- **All 11 supported games** (Valorant, PUBG, CS2, MLBB, Free Fire, etc.)
- **Expiry system** (if no one accepts within 7 days, refund stake)
- **Team notifications** (if bounty targets a specific player/team)
- **Anti-abuse**: Reputation thresholds, cooldown periods, dispute resolution

#### **Existing Infrastructure to Reuse:**
- ✅ `apps/economy/` - DeltaCrownWallet for escrow transactions
- ✅ `apps/games/` - Game model with 11 supported games
- ✅ `apps/tournaments/models/match.py` - Match result submission & dispute logic
- ✅ `apps/tournament_ops/services/match_service.py` - Match state machine

#### **What Needs Creation:**
- ❌ **Bounty model** (creator, target, game, stake_amount, requirements, status, escrow_transaction_id)
- ❌ **BountyService** (create, accept, resolve, refund, handle_dispute)
- ❌ **Escrow flow** (lock funds on creation, release on completion, refund on expiry)

---

### 2.2 Skill Endorsements (Post-Match Awards)

#### **What I Previously Assumed (WRONG):**
- LinkedIn-style anytime endorsements
- Vote on arbitrary skills without verification
- Spam-prone open system

#### **What It Actually Is:**
**Post-match, teammate-only skill awards** where:
1. After a **tournament match** completes, each player can award ONE skill to ONE teammate
2. Skills are predefined (Shotcalling, Aim, Clutch, Support, IGL, Entry)
3. Only teammates from the **same match roster** can endorse each other
4. Awards are anonymous to prevent reciprocal voting pressure
5. Aggregates display skill counts on profile (e.g., "Shotcalling: 47 endorsements")

#### **Key Characteristics:**
- **Post-match only** (not anytime voting)
- **Verified teammates** (must have played in same tournament match)
- **One skill per match** (prevents spam)
- **Anonymous** (reduces social pressure)
- **No self-endorsements** (enforced at DB level)

#### **Existing Infrastructure to Reuse:**
- ✅ `apps/tournaments/models/match.py` - Match completion hook
- ✅ `apps/teams/models/` - Team roster verification
- ✅ `apps/tournament_ops/` - Match participant tracking
- ✅ `apps/user_profile/models/activity.py` - UserActivity event tracking

#### **What Needs Creation:**
- ❌ **SkillEndorsement model** (match_id, receiver, endorser, skill_name, created_at)
  - `unique_together = ('match_id', 'endorser', 'receiver')` (one endorsement per match)
- ❌ **Post-match endorsement modal** (triggered after match completion)
- ❌ **Aggregation query** (count endorsements per skill per user)

---

### 2.3 Posts Tab (Community Integration)

#### **What I Previously Assumed (WRONG):**
- Need to build a new Post/PostMedia model from scratch
- Build upload system, like/comment features

#### **What It Actually Is:**
**Reuse existing `apps/community/` infrastructure** (if it exists) or link to external blog/feed system.

After checking `apps/` directory, I found:
- ❌ No `apps/community/` directory
- ❌ No `apps/posts/` directory
- ❌ No `apps/blog/` directory

#### **Clarification Needed from Product:**
Does the Posts tab need to be built, or is this a future feature? Template shows post creation UI, but no backend exists.

**Possible Approaches:**
1. **Build new Post system** (user-generated content with rich text, images)
2. **Link to external blog** (redirect to WordPress/Medium integration)
3. **Defer to Phase 2** (remove Posts tab for MVP)

---

### 2.4 Inventory/Cosmetics System (Achievement-Based Showcase)

#### **What I Previously Assumed (WRONG):**
- E-commerce cosmetic store
- User purchases avatar frames, themes, badges
- Equipped state tracking with monetization

#### **What It Actually Is:**
**Achievement-based showcase system** where cosmetics are **earned, not purchased**:
1. User earns badges from tournaments (e.g., "Season 1 Champion")
2. Badges unlock avatar frames/themes as rewards
3. Inventory displays earned cosmetics with rarity
4. User can equip ONE frame/theme at a time
5. No monetary transactions (all earned through gameplay)

#### **Key Characteristics:**
- **No store purchases** (all achievement-based)
- **Trophy cabinet display** (showcase tournament wins)
- **Rarity tiers** (Common/Rare/Epic/Legendary)
- **Equipped state** (one active frame, one active theme)

#### **Existing Infrastructure to Reuse:**
- ✅ `apps/user_profile/models_main.py` - Badge model (rarity, category, criteria)
- ✅ `apps/user_profile/models_main.py` - UserBadge model (earned_at, progress)
- ✅ `apps/user_profile/models_main.py` - Achievement model (tournament trophies)
- ✅ `apps/tournaments/models/` - Tournament win tracking

#### **What Needs Creation:**
- 🟡 **Extend Badge model** to include `unlocks_frame` field (points to frame asset)
- ❌ **CosmeticFrame model** (slug, name, asset_url, rarity)
- ❌ **ProfileTheme model** (slug, name, colors, rarity)
- 🟡 **UserProfile fields**: `equipped_frame_id`, `equipped_theme_id` (ForeignKeys)

---

### 2.5 Loadout/Gear System (Pro-Settings Engine)

#### **What I Previously Assumed (WRONG):**
- User manually enters hardware (mouse, keyboard, headset)
- Affiliate link tracking for purchases

#### **What It Actually Is:**
**Pro-settings database** where users link their hardware setup for transparency:
1. User selects from predefined hardware list (Logitech G Pro X, Razer DeathAdder, etc.)
2. Hardware includes specs (DPI, polling rate, switch type)
3. "View in Store" button links to DeltaCrown e-commerce (if `apps/shop/` exists)
4. Affiliate commission if spectator purchases (future monetization)

#### **Existing Infrastructure to Reuse:**
- ✅ `apps/shop/` or `apps/ecommerce/` (I saw these directories exist)
- ✅ Product catalog (if already built)

#### **What Needs Creation:**
- ❌ **UserGear model** (user, category, product_id, specs)
- ❌ **Hardware catalog** (Mouse/Keyboard/Headset products)
- 🟡 **Affiliate tracking** (future phase)

---

### 2.6 Live Status Widget (Streaming Integration)

#### **What I Previously Assumed (WRONG):**
- Build real-time tournament tracking from scratch
- WebSocket infrastructure for live updates

#### **What It Actually Is:**
**Simple embed integration** where:
1. Check if user has an **active tournament match** (via `apps/tournament_ops/`)
2. If match is LIVE, fetch streaming URL from user's Twitch/YouTube social link
3. Display "WATCH STREAM" button in right sidebar
4. No custom video player (just redirect to Twitch/YouTube)

#### **Existing Infrastructure to Reuse:**
- ✅ `apps/tournament_ops/services/match_service.py` - Match state machine (LIVE status)
- ✅ `apps/user_profile/models_main.py` - SocialLink model (Twitch URL)
- ✅ `apps/tournaments/models/match.py` - Match.state == 'LIVE'

#### **What Needs Creation:**
- ✅ **Query logic only** (check if user has active match, fetch stream URL)
- ✅ **Context variable**: `live_tournament_status` dict with {match_name, opponent, stream_url}

---

### 2.7 Pinned Highlight/Media Gallery (Embed-Only)

#### **What I Previously Assumed (WRONG):**
- Build video upload system
- Media storage on S3
- Video transcoding pipeline

#### **What It Actually Is:**
**YouTube/Twitch embed-only system** where:
1. User pastes a YouTube/Twitch clip URL
2. System extracts video ID
3. Renders iframe embed player
4. No local video uploads (just URL storage)

#### **Existing Infrastructure to Reuse:**
- ✅ **YouTube/Twitch oEmbed API** (free, no backend needed)
- ✅ **URLField validation** (Django built-in)

#### **What Needs Creation:**
- 🟡 **UserProfile.pinned_highlight_url** (CharField for YouTube/Twitch URL)
- ❌ **MediaGallery model** (if multiple clips needed)
  - `user`, `title`, `video_url`, `created_at`

---

## 3. Architecture Deltas: What Changed from Audit Report

### 3.1 Major Corrections

| Feature | Previous Assumption | Actual Design | Impact |
|---------|---------------------|---------------|--------|
| **Bounty System** | Tournament registration | Peer-to-peer escrow challenges | Needs escrow transaction logic, not bracket system |
| **Endorsements** | LinkedIn-style anytime | Post-match teammate awards | Needs match completion hook, not open voting |
| **Inventory** | E-commerce cosmetics | Achievement-based showcase | No store purchases, just earned badges |
| **Loadout** | Manual entry | Pro-settings database | Needs hardware catalog, not free-text fields |
| **Media Gallery** | Upload system | Embed-only URLs | No storage/transcoding needed |
| **Posts** | Build from scratch | Reuse community app | **Blocker**: Community app doesn't exist yet |

### 3.2 Features That Don't Need Building

❌ **Messaging/DM System** - Not required (template shows button but it's future-phase)  
❌ **Cosmetic Store** - No monetization via purchases (all achievement-based)  
❌ **Video Upload** - Just URL embeds (YouTube/Twitch only)  
❌ **Advanced Analytics Premium Lock** - Future monetization (Phase 2)  

### 3.3 Features That Can Reuse Existing Apps

✅ **Wallet Integration** - `apps/economy/` fully functional  
✅ **Match System** - `apps/tournaments/models/match.py` already exists  
✅ **Team Verification** - `apps/teams/` has roster tracking  
✅ **Game Catalog** - `apps/games/` supports 11 games  

---

## 4. App-by-App Reusability Matrix

### 4.1 `apps/games/`

**What Exists:**
- Game model (11 supported games: Valorant, PUBG, CS2, etc.)
- Game categories (FPS, MOBA, BR, etc.)
- Rank/tier system per game
- Platform support (PC, Mobile, Console)

**What We Can Reuse:**
- ✅ Bounty creation dropdown (select from 11 games)
- ✅ GameProfile rank display
- ✅ Game icons/branding for UI

**What's Missing:**
- Hardware catalog (for pro-settings)

---

### 4.2 `apps/economy/`

**What Exists:**
- DeltaCrownWallet (balance, transactions, Bangladesh payment methods)
- Transaction ledger (credits/debits)
- Withdrawal system (bKash, Nagad, Rocket, bank transfer)
- Lifetime earnings tracking

**What We Can Reuse:**
- ✅ Bounty escrow (deduct stake, lock in pending_balance)
- ✅ Prize distribution (release to winner)
- ✅ Wallet tab display (balance, transaction history)

**What's Missing:**
- Escrow-specific transaction types (needs new `type='BOUNTY_ESCROW'`)

---

### 4.3 `apps/tournaments/`

**What Exists:**
- Tournament model (name, game, prize pool, status)
- Match model (state machine, score tracking, disputes)
- Registration system (eligibility checks)
- Result submission & verification

**What We Can Reuse:**
- ✅ Match completion hook (trigger endorsement modal)
- ✅ Participant roster (verify teammates for endorsements)
- ✅ Dispute resolution (adapt for bounty disputes)

**What's Missing:**
- Bounty-specific match tracking (bounties are NOT tournaments)

---

### 4.4 `apps/tournament_ops/`

**What Exists:**
- MatchService (state machine, lifecycle)
- Match scheduling
- Live status tracking

**What We Can Reuse:**
- ✅ Live tournament widget (query active matches)
- ✅ Match state checking (is user in LIVE match?)

**What's Missing:**
- Bounty match coordination (who hosts the lobby?)

---

### 4.5 `apps/teams/`

**What Exists:**
- Team model (name, game, roster)
- TeamMembership (user, role, join date)
- Team career history

**What We Can Reuse:**
- ✅ Teammate verification (for endorsements)
- ✅ Career timeline display
- ✅ Team affiliations sidebar

**What's Missing:**
- Nothing (fully reusable)

---

### 4.6 `apps/user_profile/`

**What Exists:**
- UserProfile (avatar, bio, level, XP)
- GameProfile (game accounts with ranks)
- Badge/UserBadge (rarity, progress)
- Achievement (tournament trophies)
- Follow system
- PrivacySettings

**What We Can Reuse:**
- ✅ Badge showcase (Inventory tab)
- ✅ Trophy cabinet (Achievement display)
- ✅ Game passport system

**What's Missing:**
- Bounty model
- SkillEndorsement model
- UserGear model
- CosmeticFrame/ProfileTheme models
- pinned_highlight_url field

---

### 4.7 `apps/shop/` or `apps/ecommerce/`

**Status:** Exists in directory listing but not explored

**Assumed Functionality:**
- Product catalog
- Checkout system
- Order tracking

**What We Can Reuse (if functional):**
- ✅ Hardware product catalog (for loadout)
- ✅ Affiliate link generation

**What's Missing (needs verification):**
- Hardware-specific products (mice, keyboards, headsets)

---

## 5. Implementation Priorities (Revised)

### Phase 1: Core Profile Functionality (Week 1-2)

**Goal:** Make template render without errors

1. **Bounty System (5 days)**
   - Create Bounty model with escrow logic
   - Add bounty query to profile context
   - Create acceptance API endpoint
   - Test escrow transaction flow

2. **Skill Endorsements (3 days)**
   - Create SkillEndorsement model
   - Hook into match completion signal
   - Add aggregation query for skill counts
   - Build post-match endorsement modal

3. **Achievement Showcase (2 days)**
   - Extend Badge model with frame unlocking
   - Add equipped_frame_id to UserProfile
   - Create trophy cabinet query
   - Display rarity colors in template

4. **Live Status Widget (1 day)**
   - Query active matches via tournament_ops
   - Fetch stream URL from social links
   - Add live_status to profile context

**Total Phase 1: ~11 days**

---

### Phase 2: Enhancement Features (Week 3)

5. **Pro-Settings Loadout (3 days)**
   - Create UserGear model
   - Build hardware catalog (if shop app functional)
   - Add gear management to settings
   - Link to store products

6. **Pinned Highlight (1 day)**
   - Add pinned_highlight_url field to UserProfile
   - Validate YouTube/Twitch URL
   - Render iframe embed in template

7. **Wallet Tab Privacy (1 day)**
   - Verify server-side conditional rendering
   - Test wallet data leakage scenarios
   - Add permission checks

**Total Phase 2: ~5 days**

---

### Phase 3: Deferred/Future (No Timeline)

8. **Posts Tab** - Requires decision on whether to build or defer
9. **Media Gallery** - Multiple embeds (if needed beyond pinned highlight)
10. **Messaging System** - Not required for MVP
11. **Advanced Analytics** - Premium monetization (Phase 4)

---

## 6. Critical Questions Requiring Product Decisions

### 6.1 Posts Tab

**Question:** Should we build a Post system, or defer this tab to Phase 2?  
**Context:** No `apps/community/` or `apps/posts/` exists currently.  
**Options:**
- A) Build new Post/PostMedia models (5 days)
- B) Stub the tab with "Coming Soon" (1 day)
- C) Remove the tab from template (1 hour)

**Recommendation:** Option B (stub for MVP)

---

### 6.2 Bounty Match Hosting

**Question:** Who hosts the game lobby for bounty matches?  
**Context:** Tournament matches have organizers/admins; bounties are peer-to-peer.  
**Options:**
- A) Challenge creator hosts
- B) First acceptor hosts
- C) DeltaCrown provides dedicated servers (future)

**Recommendation:** Option A (creator hosts, shares lobby code)

---

### 6.3 Endorsement Anti-Abuse

**Question:** How do we prevent smurf accounts from farming endorsements?  
**Context:** User could create alt accounts, join same tournament, endorse main account.  
**Options:**
- A) Require account age > 30 days
- B) Require minimum match count > 10
- C) Require reputation score > 50
- D) All of the above

**Recommendation:** Option D (layered anti-abuse)

---

### 6.4 Hardware Catalog Ownership

**Question:** Does DeltaCrown maintain its own hardware catalog, or link to external store?  
**Context:** Pro-settings loadout needs product data (names, specs, images).  
**Options:**
- A) Build catalog in `apps/shop/` (ownership, affiliate revenue)
- B) Link to Amazon/Newegg (simpler, less revenue)

**Recommendation:** Option A (long-term revenue potential)

---

### 6.5 Inventory Monetization

**Question:** Will cosmetics EVER be purchasable, or always earned?  
**Context:** Template shows "Open Store" button in Inventory tab.  
**Options:**
- A) Pure achievement-based (no monetization)
- B) Hybrid (earn common items, buy rare/legendary)
- C) Full store (all items purchasable)

**Recommendation:** Option B (balanced monetization model)

---

## 7. Database Schema Additions (High-Level)

### 7.1 New Models Required

```python
# apps/user_profile/models/bounty.py
class Bounty(models.Model):
    creator = ForeignKey(User)
    target_user = ForeignKey(User, null=True)  # Optional targeted challenge
    game = ForeignKey(Game)
    title = CharField(max_length=200)
    requirements = TextField()  # "First to 100k on Gridshot"
    stake_amount = IntegerField()  # DeltaCoins
    escrow_transaction = ForeignKey(DeltaCrownTransaction)
    status = CharField(choices=['OPEN', 'ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'DISPUTED', 'EXPIRED'])
    expires_at = DateTimeField()  # Auto-refund if not accepted
    winner = ForeignKey(User, null=True)
    created_at = DateTimeField()

# apps/user_profile/models/endorsement.py
class SkillEndorsement(models.Model):
    match = ForeignKey(Match)  # Ensures post-match only
    receiver = ForeignKey(User, related_name='endorsements_received')
    endorser = ForeignKey(User, related_name='endorsements_given')
    skill_name = CharField(choices=['Shotcalling', 'Aim', 'Clutch', 'Support', 'IGL', 'Entry'])
    created_at = DateTimeField()
    
    class Meta:
        unique_together = ('match', 'endorser', 'receiver')  # One endorsement per match

# apps/user_profile/models/cosmetics.py
class CosmeticFrame(models.Model):
    slug = CharField(unique=True)  # 'dragon_fire'
    name = CharField()  # "Dragon Fire"
    asset_url = URLField()  # S3 image
    rarity = CharField(choices=['common', 'rare', 'epic', 'legendary'])
    unlocked_by_badge = ForeignKey(Badge, null=True)  # Earn via achievement

class ProfileTheme(models.Model):
    slug = CharField(unique=True)  # 'aurora_zenith'
    name = CharField()
    primary_color = CharField()
    secondary_color = CharField()
    rarity = CharField()

# apps/user_profile/models/gear.py
class UserGear(models.Model):
    user_profile = ForeignKey(UserProfile)
    category = CharField(choices=['mouse', 'keyboard', 'headset', 'monitor'])
    product = ForeignKey(Product)  # Link to shop app
    specs = TextField()  # "800 DPI, Superlight"
    is_active = BooleanField(default=True)
```

### 7.2 UserProfile Field Additions

```python
# apps/user_profile/models_main.py
class UserProfile(models.Model):
    # ... existing fields ...
    
    # New fields for profile expansion
    equipped_frame = ForeignKey(CosmeticFrame, null=True)
    equipped_theme = ForeignKey(ProfileTheme, null=True)
    pinned_highlight_url = URLField(blank=True)  # YouTube/Twitch embed
    pro_settings_visibility = CharField(
        choices=['public', 'friends', 'private'],
        default='public'
    )
```

---

## 8. API Endpoints Required

### 8.1 Bounty System

- `POST /api/bounties/create/` - Create challenge with escrow
- `GET /api/bounties/open/` - List available bounties (filtered by game)
- `POST /api/bounties/{id}/accept/` - Accept challenge
- `POST /api/bounties/{id}/submit-result/` - Submit match result
- `POST /api/bounties/{id}/dispute/` - Open dispute

### 8.2 Endorsements

- `GET /api/endorsements/{username}/` - Get skill aggregates
- `POST /api/matches/{match_id}/endorse/` - Award skill to teammate

### 8.3 Cosmetics

- `GET /api/inventory/` - List earned cosmetics
- `POST /api/inventory/equip/{slug}/` - Equip frame/theme
- `GET /api/inventory/frames/` - Browse available frames

### 8.4 Pro-Settings

- `GET /api/gear/{username}/` - Get user's loadout
- `POST /api/gear/` - Add hardware item
- `PUT /api/gear/{id}/` - Update item
- `DELETE /api/gear/{id}/` - Remove item

---

## 9. Migration Strategy

### 9.1 Backwards Compatibility

**Existing JSONField Data:**
- `UserProfile.inventory_items` → Migrate to CosmeticFrame/ProfileTheme models
- `UserProfile.pinned_badges` → Migrate to equipped_frame linkage

**Migration Steps:**
1. Create new models (Phase 1)
2. Run data migration script (parse JSON, create FK records)
3. Deprecate JSONField (Phase 2)
4. Remove JSONField (Phase 3, after 30 days)

### 9.2 Rollback Plan

- Keep JSONField for 30 days as backup
- If bugs found, revert to JSON-based rendering
- Once stable, drop columns

---

## 10. Testing Strategy

### 10.1 Bounty System Tests

- ✅ Create bounty deducts correct amount from wallet
- ✅ Expired bounties refund escrow automatically
- ✅ Winner receives prize minus platform fee
- ✅ Anti-spam: Can't accept own bounty
- ✅ Anti-spam: Requires minimum reputation

### 10.2 Endorsement Tests

- ✅ Can only endorse teammates from same match
- ✅ Unique constraint prevents double endorsements
- ✅ Endorsement counts update in real-time
- ✅ Post-match modal triggers after match completion
- ✅ Self-endorsements blocked

### 10.3 Cosmetics Tests

- ✅ Badge unlocks frame on earn
- ✅ Can only equip ONE frame at a time
- ✅ Rarity colors render correctly
- ✅ Trophy cabinet shows tournament wins

---

## 11. Performance Considerations

### 11.1 Query Optimization

**Endorsement Aggregation:**
```python
# Avoid N+1 queries
endorsements = SkillEndorsement.objects.filter(
    receiver=user
).values('skill_name').annotate(
    count=Count('id')
).order_by('-count')
```

**Bounty Expiry:**
```python
# Use Celery task to auto-refund expired bounties
# Run every 15 minutes
@periodic_task(run_every=crontab(minute='*/15'))
def process_expired_bounties():
    expired = Bounty.objects.filter(
        status='OPEN',
        expires_at__lt=timezone.now()
    )
    for bounty in expired:
        refund_escrow(bounty)
```

### 11.2 Caching Strategy

- **Endorsement counts:** Cache for 1 hour (updates infrequent)
- **Trophy cabinet:** Cache for 24 hours (rarely changes)
- **Open bounties:** Cache for 5 minutes (real-time feel)
- **Live status widget:** No cache (real-time required)

---

## 12. Security Considerations

### 12.1 Bounty System

- **Escrow safety:** Atomic transactions (use database locks)
- **Dispute resolution:** Admin review for amounts > 10,000 DeltaCoins
- **Anti-fraud:** Flag accounts accepting >10 bounties/day

### 12.2 Endorsements

- **Smurf prevention:** Require account age + match count
- **Collusion detection:** Flag if same users endorse each other repeatedly
- **Privacy:** Endorsements are anonymous (don't show who endorsed)

### 12.3 Cosmetics

- **Asset security:** S3 bucket signed URLs (prevent hotlinking)
- **Unlocking validation:** Server-side check that badge was actually earned

---

## 13. Documentation Deliverables

After this analysis, the following documents should be created:

1. ✅ **01_system_understanding.md** (this document)
2. ⬜ **02_bounty_system_spec.md** (detailed escrow flow diagrams)
3. ⬜ **03_endorsement_system_spec.md** (match completion hooks)
4. ⬜ **04_cosmetics_spec.md** (achievement-based unlocking)
5. ⬜ **05_api_contracts.md** (request/response schemas)
6. ⬜ **06_migration_plan.md** (step-by-step database changes)

---

## 14. Final Recommendations

### 14.1 Immediate Actions (This Week)

1. **Product Decision:** Confirm Posts tab strategy (build/stub/remove)
2. **Product Decision:** Confirm bounty match hosting logic
3. **Product Decision:** Confirm cosmetics monetization model
4. **Technical:** Begin Bounty model implementation (highest priority)

### 14.2 Risk Mitigation

**Highest Risk:** Bounty escrow bugs (money loss)  
**Mitigation:** Extensive testing with test wallets, manual admin review for large amounts

**Medium Risk:** Endorsement spam/collusion  
**Mitigation:** Anti-abuse checks, reputation thresholds, monitoring dashboard

**Low Risk:** Cosmetics rendering bugs  
**Mitigation:** CSS fallbacks, default frame if asset missing

---

## 15. Conclusion

The User Profile expansion is **achievable in 2-3 weeks** if we:
- Reuse existing tournament/economy infrastructure
- Build only the 4 core missing models (Bounty, Endorsement, Cosmetics, Gear)
- Defer Posts tab to Phase 2
- Use embed-only approach for media

The previous audit report overestimated scope by assuming we needed to build:
- ❌ Cosmetic store (it's achievement-based)
- ❌ Video uploads (it's embed-only)
- ❌ Messaging system (not MVP)
- ❌ Tournament registration (bounties are separate)

This document corrects those assumptions and provides a clear path forward.

---

**Document Status:** ✅ Complete  
**Next Steps:** Review with product team, create detailed specs for Phase 1 features  
**Questions:** See Section 6 (7 critical product decisions needed)
