# Skill Endorsements & Profile Showcase Design
**Date:** December 31, 2025  
**Architect:** Principal Backend Architect  
**Type:** Technical Design (No Implementation)  
**Scope:** Post-Match Endorsement System

---

## 1. System Intent

The Skill Endorsement system is a post-match, teammate-verified recognition mechanism where players award specific competitive skills (Shotcalling, Aim, Clutch, Support, IGL, Entry Fragging) to teammates immediately after completing a tournament match. Unlike social media "likes" or unverified endorsements, these awards are earned through actual gameplay with verified roster participation, creating an immutable reputation record tied to specific matches. Each player may award ONE skill to ONE teammate per match, preventing spam while encouraging meaningful peer recognition. The system is anonymous to reduce reciprocal voting pressure, and aggregated skill counts display on user profiles as authentic competitive credentials (e.g., "Shotcalling: 47 endorsements from 47 matches"), providing scouts and team captains with crowd-sourced performance insights that complement raw statistics.

---

## 2. When Endorsements Are Allowed

**Post-Match Window:**

- Endorsement opportunity opens only when a tournament match transitions to `COMPLETED` state
- Triggered by Django signal or service hook: `@receiver(post_save, sender=Match)` when `instance.state == 'COMPLETED'`
- Time window: 24 hours after match completion (endorsement window expires after 24h)
- Players receive notification: "Match completed! Recognize your teammate's performance"
- Modal or dedicated page prompts participants to select one skill for one teammate

**Expiry Behavior:**

- If player does not endorse within 24 hours, opportunity expires permanently
- Cannot retroactively endorse matches older than 24 hours (prevents coordinated manipulation)
- Expired endorsement opportunities are tracked but not resurrectable

**Match Types That Qualify:**

- Only **tournament matches** (from `apps/tournaments/models/match.py`)
- Excludes practice matches, scrims, or casual games (no verified roster)
- Match must have reached `COMPLETED` state (not `FORFEIT`, `CANCELLED`, or `DISPUTED`)
- If match result is later disputed and overturned, endorsements remain (based on gameplay that occurred, not final outcome)

---

## 3. Who Can Give Endorsements (Role Eligibility)

**Teammate Verification (Required):**

- Endorser and receiver must have been teammates in the **same completed match**
- Verification via `Match.participant1_id` and `Match.participant2_id` (if 1v1), or via team roster (if team match)
- For team matches: Both users must be members of the same team participating in that match
- Query: `TeamMembership.objects.filter(team_id=match.team_a_id, status='ACTIVE')` to get roster

**Role Restrictions:**

- **Cannot endorse yourself** (enforced at DB level with constraint, service-level validation)
- **Cannot endorse opponent** (only teammates from your side of the match)
- **One endorsement per match** (unique constraint: `unique_together=['match_id', 'endorser']`)
- **Must be match participant** (verified via match participant list or team roster)

**Account Standing Requirements:**

- Endorser account must be in good standing (not banned, not flagged for manipulation)
- If endorser account is later banned for cheating, their past endorsements remain (historical record)
- Receiver account can be any standing (even banned accounts show earned endorsements)

**Anonymous Attribution:**

- Endorsement records store `endorser_id` in database for audit trail
- Profile display shows aggregate count only: "Shotcalling: 47" (no list of who endorsed)
- Prevents social pressure: "You endorsed me, now endorse me back"
- Moderators can view endorser details if investigating manipulation

---

## 4. What Endorsements Represent (Earned Credentials)

**Competitive Recognition, Not Social Validation:**

- Endorsements are **performance awards** earned through verified gameplay, not popularity contests
- Each endorsement is tied to a specific match (immutable proof: "earned in Match #12345")
- Cannot be purchased, traded, or solicited (unlike social media likes)
- Aggregate counts reflect peer assessment across multiple matches and teammates

**Skill Categories (Predefined):**

- **Shotcalling** - Strategic leadership, decisive calls in clutch moments
- **Aim** - Mechanical precision, consistent kills, strong dueling
- **Clutch** - 1vX situation wins, composure under pressure
- **Support** - Utility usage, assists, enabling teammate success
- **IGL (In-Game Leader)** - Tactical planning, team coordination, mid-round adjustments
- **Entry Fragging** - First contact aggression, opening kills, space creation

**No Custom Skills:**

- Only predefined skills allowed (prevents dilution with joke categories)
- Skills are game-agnostic (apply across Valorant, CS2, PUBG, etc.)
- If skill categories need expansion, requires system-wide update (not per-user customization)

**Immutability & Audit Trail:**

- Once awarded, endorsements cannot be deleted or modified (like `DeltaCrownTransaction`)
- If match is voided by admin, endorsements remain (based on gameplay that occurred)
- Each endorsement links to source match: `source_model='Match', source_id=match.id`
- Full audit trail: Who endorsed, when, for which match (visible to moderators only)

**Aggregation Display:**

- Profile shows skill counts: "Aim: 89 | Clutch: 34 | Shotcalling: 12"
- Optionally show skill distribution chart (pie/bar chart of skill breakdown)
- "Most recognized for: Aim" (highest count skill displayed prominently)
- Total endorsements received: "142 endorsements from 98 matches"

**Not Reputation Score:**

- Endorsements are qualitative (which skills), not quantitative ranking
- No "endorsement power" weighting (veteran's endorsement = rookie's endorsement)
- Complements reputation score (separate system), does not replace it
- Cannot be used for matchmaking MMR or skill-based rankings (scout tool only)

---

## 5. Models Required

**Core Models:**

- **SkillEndorsement** - Main endorsement record linking endorser, receiver, skill type, and source match
- **EndorsementOpportunity** - Tracks 24-hour window for each player after match completion (expires_at, used for cleanup)

**Models NOT Needed (Reuse Existing):**

- ❌ **Match** - Use existing `apps/tournaments/models/match.py` as endorsement source
- ❌ **TeamMembership** - Use existing for teammate verification
- ❌ **UserActivity** - Use existing for endorsement event logging (SKILL_ENDORSED, SKILL_GAVE_ENDORSEMENT)
- ❌ **SkillCategory** - Use TextChoices enum in SkillEndorsement model (no separate table needed)

---

## 6. Match Linkage (Source Attribution)

**Direct Match Reference:**

- Each SkillEndorsement record stores `match_id` (ForeignKey to Match model)
- When match completes, system creates EndorsementOpportunity records for all participants
- Endorsement creation validates that endorser was participant in that specific match
- Match linkage enables: "View match where this skill was recognized" feature

**Participant Resolution:**

- For 1v1 matches: Participants are `match.participant1_id` and `match.participant2_id`
- For team matches: Participants resolved via `TeamMembership.objects.filter(team_id__in=[match.team_a_id, match.team_b_id], status='ACTIVE')`
- Teammate verification: Both endorser and receiver must be on same team in that match
- Opponent exclusion: Endorser cannot endorse player from opposing team

**Match State Requirements:**

- Only matches with `state='COMPLETED'` trigger endorsement opportunities
- Matches with `state='DISPUTED'` do not open endorsement window until resolved
- If match later moves to `DISPUTED` after endorsements given, endorsements remain valid (gameplay occurred)
- If match is `CANCELLED` or `FORFEIT`, no endorsement opportunities created

**Historical Audit Trail:**

- Endorsement record is immutable once created (cannot change match_id, skill_name, or receiver)
- Moderators can query: "Show all endorsements from Match #12345"
- Profile can show: "Last endorsed for Clutch in Match #12345 vs Team Phoenix (Jan 15, 2025)"
- If match is deleted (rare), endorsement remains with orphaned match_id (soft reference)

---

## 7. Duplicate Prevention

**Database-Level Constraints:**

- Unique constraint: `unique_together = ['match_id', 'endorser', 'receiver']` (one endorsement per endorser-receiver pair per match)
- Alternative constraint: `unique_together = ['match_id', 'endorser']` (one endorsement per endorser per match, regardless of receiver)
- Second constraint is recommended: Forces endorser to choose ONE teammate to recognize per match

**Service-Level Validation:**

- Before creating endorsement, query existing: `SkillEndorsement.objects.filter(match_id=match_id, endorser=endorser).exists()`
- If exists, return error: "You already endorsed a teammate from this match"
- Cannot modify existing endorsement (no "change skill" or "change receiver")
- Must live with initial choice (encourages thoughtful selection)

**Self-Endorsement Prevention:**

- Validation: `if endorser == receiver: raise ValidationError("Cannot endorse yourself")`
- Database check constraint: `CHECK (endorser_id != receiver_id)` for additional safety
- Service-level check before DB insert to provide user-friendly error message

**Opponent Prevention:**

- Resolve endorser's team: `endorser_team = get_user_team_in_match(endorser, match)`
- Resolve receiver's team: `receiver_team = get_user_team_in_match(receiver, match)`
- Validate same team: `if endorser_team != receiver_team: raise ValidationError("Can only endorse teammates")`
- For 1v1 matches: Automatically same team (opponent is other participant)

**Time Window Enforcement:**

- Endorsement creation checks: `if now() > match.completed_at + timedelta(hours=24): raise ValidationError("Endorsement window expired")`
- EndorsementOpportunity records track expiry: `expires_at = match.completed_at + timedelta(hours=24)`
- Expired opportunities cannot be used (no backdating endorsements)
- Prevents coordinated manipulation weeks after match

---

## 8. Aggregation Logic (Profile Display)

**Real-Time Aggregation (Simple Queries):**

- Query all endorsements for user: `SkillEndorsement.objects.filter(receiver=user)`
- Group by skill and count: `.values('skill_name').annotate(count=Count('id'))`
- Result: `[{'skill_name': 'Aim', 'count': 89}, {'skill_name': 'Clutch', 'count': 34}, ...]`
- Order by count descending to show most recognized skill first
- Total endorsements: `.count()` on full queryset

**Profile Context Variables:**

- `endorsement_stats` (dict):
  - `total_endorsements` - Total count of all endorsements received
  - `skills` - List of dicts: `[{'name': 'Aim', 'count': 89, 'percentage': 35}, ...]`
  - `top_skill` - Most endorsed skill name (e.g., "Aim")
  - `top_skill_count` - Count for top skill
  - `unique_matches` - Count of distinct matches where user was endorsed
  - `unique_endorsers` - Count of distinct teammates who endorsed user

**Caching Strategy:**

- Endorsement counts rarely change (only after new matches), good candidate for caching
- Cache key: `endorsement_stats:{user_id}` with 1-hour TTL
- Invalidate cache when new endorsement created for that user
- Alternative: Store aggregates in UserProfile model (updated via signal on SkillEndorsement creation)

**Display Format:**

- Skill breakdown: "Aim: 89 (35%) | Clutch: 34 (13%) | Shotcalling: 67 (26%) | Support: 45 (18%) | IGL: 20 (8%)"
- Bar chart visualization with skill icons and counts
- "Most recognized for: Aim" badge/highlight
- "142 endorsements from 98 matches" summary stat

**Empty State Handling:**

- If user has 0 endorsements: Show "No endorsements yet. Play tournament matches to earn peer recognition!"
- If user has endorsements in only 1 skill: "Specialist: 100% Aim endorsements"
- If user has endorsements in all 6 skills: "Well-rounded player" badge

**Filtering Options (Future Enhancement):**

- Show endorsements by game: "Aim: 45 (Valorant) | 23 (CS2) | 21 (PUBG)"
- Show endorsements by time period: "Last 30 days: Clutch +12"
- Show endorsement trend: "Shotcalling endorsements increasing (was 40, now 67)"

---

## 9. Trophy Showcase System (Achievement-Based Display)

**System Intent (Why Not "Inventory"):**

- "Inventory" implies purchased items or loot drops (e-commerce connotation)
- "Trophy Showcase" better represents earned competitive achievements
- No cosmetic store, no purchases, no virtual economy for vanity items
- All display items (frames, borders, themes) are **unlocked through gameplay achievements**
- Think "trophy cabinet" displaying tournament wins, not "cosmetic shop" for skins

**Key Design Principle:**

- Every visual customization must be **earned, not bought**
- Frames/borders/badges are prestige indicators, not monetization hooks
- System rewards competitive success (tournament wins, rank milestones, achievement unlocks)
- No pay-to-look-cool mechanics (maintains competitive integrity)

---

## 10. Achievement → Cosmetic Unlocking

**Unlock Sources:**

- **Tournament Wins** - Winning a tournament unlocks special frame (e.g., "Season 1 Champion Frame")
- **Badge Completion** - Earning specific badges unlocks related cosmetics (e.g., "100 Wins" badge → Gold Border)
- **Rank Milestones** - Reaching certain ranks unlocks tier-based frames (e.g., Diamond rank → Diamond Frame)
- **Endorsement Milestones** - Accumulating endorsements unlocks skill-themed borders (e.g., 50 Aim endorsements → "Sharpshooter Border")
- **Anniversary Participation** - Playing during special events unlocks commemorative items

**Rarity Tiers (Existing System):**

- Common (gray) - Easy achievements (10 matches played)
- Rare (blue) - Moderate achievements (first tournament win)
- Epic (purple) - Difficult achievements (10 tournament wins)
- Legendary (gold) - Extreme achievements (season champion, 1000 wins)

**Unlocking Flow:**

- When user earns Badge X, check if badge has `unlocks_cosmetic_id` field
- If yes, auto-grant cosmetic to user's showcase collection
- Notification: "Achievement unlocked! You've earned the [Champion Frame]"
- Cosmetic appears in user's showcase selection interface
- User can equip immediately or save for later

**No Manual Purchases:**

- No "buy frame for 1000 DC" option (keeps DeltaCoins focused on competitive stakes)
- No "limited edition store" or FOMO sales tactics
- If player wants a cosmetic, they must earn the prerequisite achievement
- Maintains prestige: "That frame means they won X tournament, not just paid for it"

---

## 11. User Selection & Equipped State

**Equippable Items:**

- **Profile Frame** - Border around profile photo/avatar (one active at a time)
- **Profile Banner** - Background image behind profile header (one active at a time)
- **Badge Pins** - Up to 3 badges displayed prominently on profile (from earned badge collection)

**Selection Interface:**

- User navigates to "Showcase" or "Customization" tab in profile settings
- Grid display of all unlocked frames/banners with rarity indicators
- Locked items shown grayed out with unlock requirement tooltip: "Win 5 tournaments to unlock"
- Click to equip: Frame highlights, profile preview updates in real-time
- Save button commits changes, updates UserProfile equipped item IDs

**Equipped State Storage:**

- UserProfile model stores: `equipped_frame_id`, `equipped_banner_id`, `pinned_badge_1_id`, `pinned_badge_2_id`, `pinned_badge_3_id`
- Each is ForeignKey to respective cosmetic model (nullable, default frame if null)
- When profile loads, query equipped items and render assets
- Asset URL format: `static/frames/{frame_slug}.png` or S3 URL

**Default Items:**

- All users start with "Basic Frame" and "Default Banner" (always available)
- Cannot unequip all items (must have at least default equipped)
- New users see "Unlock more customization by playing tournaments and earning achievements!"

---

## 12. Minimal Models Needed

**New Models:**

- **ProfileFrame** - Available frame assets (slug, name, asset_url, rarity, unlock_requirement_description)
- **ProfileBanner** - Available banner assets (slug, name, asset_url, rarity, unlock_requirement_description)
- **UnlockedCosmetic** - Junction table tracking which users unlocked which cosmetics (user, cosmetic_type, cosmetic_id, unlocked_at)

**Extended Existing Models:**

- **Badge** (existing model) - Add fields: `unlocks_frame_id`, `unlocks_banner_id` (nullable ForeignKeys)
- **UserProfile** (existing model) - Add fields: `equipped_frame_id`, `equipped_banner_id`, `pinned_badge_1_id`, `pinned_badge_2_id`, `pinned_badge_3_id`

**Models NOT Needed:**

- ❌ **CosmeticStore** - No purchases, all earned
- ❌ **CosmeticTransaction** - No buying/selling, just unlocking
- ❌ **CosmeticInventory** - UnlockedCosmetic serves this purpose
- ❌ **CosmeticRarity** - Use TextChoices enum (same as Badge.rarity)

**Alternative Simpler Design:**

- Skip ProfileFrame/ProfileBanner models entirely
- Store frame/banner as CharField slug in UserProfile: `equipped_frame = 'champion_s1'`
- Hardcode asset mappings in template: `{% static 'frames/' + equipped_frame + '.png' %}`
- Unlocks tracked in Badge model: `user.badges.filter(unlocks_frame='champion_s1').exists()`
- Pro: No cosmetic database tables, Con: Less flexible for adding new frames dynamically

---

## 13. Profile Context Variables (Showcase)

**For Profile Customization Page (settings/showcase.html):**

- `unlocked_frames` (QuerySet or list):
  - All frames user has unlocked via badge/achievement completion
  - Includes: frame_id, name, rarity, asset_url, is_equipped
  - Ordered by rarity descending, then unlock date

- `locked_frames` (QuerySet or list):
  - Frames not yet unlocked by user
  - Includes: frame_id, name, rarity, unlock_requirement (e.g., "Win Season 2 Championship")
  - Shows what user can work toward

- `unlocked_banners` (QuerySet or list):
  - Same structure as frames but for banners

- `equipped_frame` (ProfileFrame object):
  - Currently active frame, used for preview pane

- `equipped_banner` (ProfileBanner object):
  - Currently active banner, used for preview pane

- `pinned_badges` (list of Badge objects):
  - Current 3 pinned badges (or None if slot empty)

- `earned_badges_for_pinning` (QuerySet):
  - All badges user has earned, available for selection
  - Excludes already pinned badges
  - Ordered by rarity descending, then earned date

**For Public Profile View (public_v3.html):**

- `profile_frame_url` (string):
  - Asset URL for equipped frame: `/static/frames/champion_s1.png`
  - Used in template: `<img src="{{ profile_frame_url }}" class="profile-frame" />`

- `profile_banner_url` (string):
  - Asset URL for equipped banner: `/static/banners/phoenix_rising.jpg`
  - Used as CSS background-image

- `pinned_badges` (list):
  - 3 badge objects to display prominently
  - Each includes: name, icon_url, rarity, earned_at
  - Renders with tooltip: "Earned: Jan 15, 2025"

- `showcase_stats` (dict):
  - `total_unlocked_cosmetics` - Count of frames + banners unlocked
  - `rarest_cosmetic` - Highest rarity item owned (e.g., "Legendary")
  - `showcase_completion_percentage` - Unlocked / Total available * 100

**For Admin Management:**

- `all_cosmetics_catalog` (QuerySet):
  - All ProfileFrame and ProfileBanner records
  - Used for admin to create new frames/banners
  - Includes unlock requirement setup

---

## 14. Integration Points

**Badge System Integration:**

- When Badge is awarded (via BadgeService or signal), check for `unlocks_frame_id` or `unlocks_banner_id`
- If present, create UnlockedCosmetic record automatically
- Trigger notification: "New cosmetic unlocked! Check your Showcase tab"
- Log UserActivity event: `event_type='COSMETIC_UNLOCKED'`

**Tournament System Integration:**

- When tournament completes and winner determined, award tournament-specific badge
- Badge automatically unlocks associated frame (e.g., "Season 1 Champion Frame")
- Championship frames are one-time unlocks (cannot be re-earned, permanent prestige)

**Endorsement Milestone Integration:**

- When user reaches endorsement threshold (e.g., 50 Aim endorsements), trigger badge award
- Badge unlocks skill-themed border (e.g., "Sharpshooter Border")
- Endorsement-based cosmetics encourage continued competitive play

**Profile Permission Integration:**

- Respect privacy settings: If profile is private, showcase customization still visible (not sensitive data)
- Anonymous viewers see equipped cosmetics (public branding, not hidden)
- Locked cosmetics list NOT shown to visitors (only user sees what they can unlock)

---

## 15. Open Questions & Design Decisions

**Question 1: Should frames be game-specific or universal?**
- Option A: Valorant tournament wins unlock Valorant-themed frame only
- Option B: Any tournament win unlocks universal frames (game-agnostic)
- **Recommendation**: Option A for championship frames (prestige), Option B for milestone frames (flexibility)

**Question 2: Can users unlock same cosmetic multiple times?**
- Scenario: User wins Season 1 and Season 2, both award "Champion Frame" (same asset)
- Option A: Unlock is binary (once unlocked, subsequent wins don't re-grant)
- Option B: Track unlock count, show "2x Champion" badge
- **Recommendation**: Option A (simpler), use separate frames for different seasons

**Question 3: Should banners be animated or static images?**
- Animated: WebM/GIF loops, more engaging but higher bandwidth
- Static: PNG/JPG, performant but less impressive
- **Recommendation**: Start with static (MVP), add animated for legendary tier later

**Question 4: How many frames/banners to launch with?**
- Minimum viable: 5 frames + 5 banners (1 per rarity + 1 default)
- Target launch: 20 frames + 10 banners (multiple per rarity, diverse themes)
- **Recommendation**: Start with 10 frames + 5 banners (quality over quantity)

**Question 5: Should users be able to gift cosmetics?**
- No purchases, but could allow gifting unlocked items to friends
- Risks: Black market for rare frames, dilutes prestige
- **Recommendation**: No gifting (maintain "you earned it" integrity)

**Question 6: What if user loses rank that unlocked cosmetic?**
- Scenario: User reaches Diamond, unlocks Diamond Frame, then drops to Platinum
- Option A: Revoke cosmetic (enforces current standing)
- Option B: Keep cosmetic (reward peak achievement)
- **Recommendation**: Option B (once earned, permanently owned)

---

## 16. Implementation Priority

**Phase 1 (MVP - Week 1-2):**
- SkillEndorsement model and post-match endorsement flow
- EndorsementOpportunity 24-hour window
- Profile display: Endorsement stats aggregation
- Basic anti-duplicate validation

**Phase 2 (Showcase - Week 2-3):**
- ProfileFrame and ProfileBanner models
- Equipped state in UserProfile
- Badge-to-cosmetic unlock mapping
- Showcase selection interface (settings page)
- Public profile rendering with equipped cosmetics

**Phase 3 (Enrichment - Week 4+):**
- Endorsement milestone badges (50/100/500 endorsements)
- Advanced showcase stats (completion percentage, rarest item)
- Animated frames (legendary tier only)
- Endorsement trends and filtering
- Team captain "Scout View" with endorsement breakdowns

---

**DESIGN COMPLETE**

**Document Status:** ✅ Ready for Technical Review  
**Next Steps:**
1. Review endorsement skill categories with game design team (are 6 skills sufficient?)
2. Design frame/banner asset specifications (dimensions, file formats, naming conventions)
3. Create detailed model schemas with fields and constraints
4. Define service method signatures (EndorsementService, ShowcaseService)
5. Plan endorsement notification UI flow (modal vs dedicated page)
6. Coordinate with frontend team on showcase preview component

---

**END OF ENDORSEMENTS & SHOWCASE DESIGN**


