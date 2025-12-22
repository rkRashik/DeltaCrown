# UP-05: Stats, History & Activity Model

**Status:** Target Architecture  
**Owner:** UserProfile + Tournaments + Games Apps  
**Last Updated:** 2025-12-22

---

## 1. Problem Statement

**Anti-Pattern (Current State):**
- UserProfile has denormalized fields like `tournaments_won`, `matches_played`
- No source-of-truth linkage → fields never update (audit found 0% accuracy)
- Cannot drill down (e.g., "show me tournaments won" → no data)
- Cannot filter (e.g., "Valorant tournaments only" → impossible)
- Cannot audit (e.g., "when did this stat change?" → no history)

**Why Stats Don't Belong on UserProfile:**
- UserProfile = identity + settings + cached aggregates
- Stats = domain data owned by domain apps (tournaments, games, matches)
- Profile should CACHE aggregates, not OWN raw data
- Source of truth must be queryable, filterable, auditable

**Architecture Principle:**
- **Source apps own data** → tournaments app owns participation records
- **UserProfile caches summaries** → total tournaments count, win rate percentage
- **Services compute on-demand** → detailed breakdowns queried from source
- **Signals keep caches fresh** → tournament ends → profile cache updates

---

## 2. Source of Truth vs Cached Aggregates

| Data Type | Source of Truth | Cached in Profile | Update Trigger |
|-----------|-----------------|-------------------|----------------|
| **Match Results** | `games.Match` model | `total_matches_played` (int) | Match completion signal |
| **Tournament Participation** | `tournaments.TournamentParticipation` (NEW) | `tournaments_participated` (int) | Registration signal |
| **Tournament Placements** | `tournaments.TournamentResult` (EXTEND) | `tournaments_won` (int) | Tournament end signal |
| **Disputes Filed** | `moderation.Dispute` model | `disputes_filed` (int) | Dispute creation signal |
| **Achievements Unlocked** | `user_profile.UserAchievement` model | `achievement_count` (int) | Achievement award signal |
| **Activity Events** | `user_profile.UserActivity` (NEW) | None (query live) | Various signals |

**Key Distinction:**
- **Source records = full history, filterable, auditable** → query from source app
- **Cached aggregates = fast reads, leaderboards, overview stats** → read from profile
- Never update source from cache (one-way flow only)

---

## 3. Data Ownership Rules

### Tournaments App Owns:
- **TournamentParticipation** model (NEW):
  - Links: user, tournament, team (nullable), registration_date, status
  - Tracks: every registration (even if tournament cancelled)
  - Purpose: "Show all tournaments this user registered for"

- **TournamentResult** model (EXTEND existing):
  - Add fields: user (nullable for team events), placement, prize_amount, stats (JSON)
  - Purpose: "Show final results per user per tournament"

- **TournamentMatchResult** model (if exists):
  - Game-specific stats per match within tournament
  - Purpose: "Show K/D, score, etc. per match"

### Games App Owns:
- **Match** model (EXTEND existing):
  - Currently unused → needs population logic
  - Fields: user, game, result (win/loss/draw), stats (JSON), played_at
  - Purpose: "Show casual match history outside tournaments"

### Moderation App Owns:
- **Dispute** model:
  - Already exists, links to user (reporter)
  - Purpose: "Track disputes filed by user"

### UserProfile App Owns:
- **UserActivity** model (NEW):
  - Generic activity feed (cross-app events)
  - Fields: user, activity_type, description, metadata (JSON), created_at
  - Purpose: "Show timeline of major events"

- **UserAchievement** model (existing):
  - Tracks earned achievements
  - Purpose: "Show badges/milestones"

**Ownership = Write Authority:**
- Only owning app can create/update records
- Other apps query read-only via services
- Profile caches only via signals (never writes to source)

---

## 4. What UserProfile Caches vs Queries Live

### Cached in Profile (Denormalized for Speed):

**Simple Counters (IntegerField):**
- `total_matches_played` → SUM of games.Match records
- `matches_won` → COUNT of games.Match WHERE result=WIN
- `tournaments_participated` → COUNT of tournaments.TournamentParticipation
- `tournaments_won` → COUNT of tournaments.TournamentResult WHERE placement=1
- `disputes_filed` → COUNT of moderation.Dispute WHERE reporter=user
- `achievement_count` → COUNT of user_profile.UserAchievement

**Computed Metrics (DecimalField/FloatField):**
- `overall_win_rate` → (matches_won / total_matches_played) * 100
- `average_placement` → AVG of TournamentResult.placement WHERE placement <= 10

**Update Strategy:**
- All cached fields updated via signals (atomic F() expressions)
- Nightly reconciliation verifies accuracy (recompute from source)
- Mismatch → log + repair

### Queried Live (Never Cached):

**Detailed Breakdowns:**
- Match history (pagination required) → query `games.Match.objects.filter(user=user)`
- Tournament history (filterable) → query `tournaments.TournamentParticipation.objects.filter(user=user)`
- Game-specific stats (drill-down) → query with filters (game, date range, etc.)
- Activity timeline → query `user_profile.UserActivity.objects.filter(user=user)`

**Why Not Cached:**
- Too much data (100+ matches per user)
- Requires filtering/pagination
- Changes frequently
- Users rarely view full history

**Service Layer Pattern:**
- `user_profile.services.stats_service.get_match_history(user, game=None, limit=10)`
- `user_profile.services.stats_service.get_tournament_breakdown(user, filters)`
- Services handle privacy, pagination, performance

---

## 5. Activity Timeline Model

### UserActivity Model (NEW)

**Purpose:** Unified feed of major events across platform

**Fields:**
- user (ForeignKey)
- activity_type (CharField: choices enum)
- description (TextField: human-readable)
- metadata (JSONField: structured data for rendering)
- visibility (CharField: PUBLIC / FOLLOWERS / PRIVATE)
- created_at (DateTimeField: indexed)

**Activity Types (Whitelist Only):**
- PROFILE_CREATED → "Joined DeltaCrown"
- ACHIEVEMENT_UNLOCKED → "Earned [badge name]"
- TOURNAMENT_REGISTERED → "Registered for [tournament name]"
- TOURNAMENT_WON → "🏆 Won [tournament name]" (placement ≤ 3 only)
- TEAM_JOINED → "Joined team [team name]"
- LEVEL_UP → "Reached level [N]" (every 5 levels only)
- KYC_VERIFIED → "Completed verification" (visible to self only)

**What Does NOT Appear:**
- Match results (too noisy, unless special event)
- Minor achievements (only "major" tier)
- Economy transactions (privacy)
- Disputes (privacy)
- Profile edits (too frequent)
- Login/logout (noise)

**Retention Policy:**
- Keep forever (cheap, useful for nostalgia)
- Paginate aggressively (10 per page)
- Archive old activities to separate table after 2 years (optional future optimization)

**Creation Strategy:**
- Signal handlers in each app create activities
- Example: tournament ends → signal creates TOURNAMENT_WON activities for top 3
- UserProfile app provides `create_activity()` service method

---

## 6. Performance Strategy

### Pagination (Mandatory for Lists):
- Match history: 10 per page (default), max 50 per page
- Tournament history: 20 per page
- Activity timeline: 10 per page
- Use `Paginator` or cursor-based pagination (id + created_at)

### Denormalization (Cached Aggregates):
- All counters pre-computed in profile
- Win rate computed on every match signal (incremental update)
- Leaderboards query profile counters (fast, indexed)

### Pre-Aggregation (Scheduled Jobs):
- Nightly: recompute all profile stats from source (reconciliation)
- Weekly: compute game-specific breakdowns (cache in Redis)
- Monthly: archive old match data to separate table

### Database Indexes (Required):
- `games.Match`: (user, played_at DESC), (user, game, played_at DESC)
- `tournaments.TournamentParticipation`: (user, tournament), (user, created_at DESC)
- `tournaments.TournamentResult`: (user, placement), (user, tournament)
- `user_profile.UserActivity`: (user, created_at DESC), (user, activity_type, created_at DESC)
- `user_profile.UserProfile`: (total_matches_played), (tournaments_won), (overall_win_rate)

### Caching Strategy (Redis):
- Profile overview stats: cache 5 minutes (high hit rate)
- Match history first page: cache 1 minute
- Activity timeline first page: cache 30 seconds
- Invalidate on new match/activity creation

---

## 7. Privacy Interaction

### What Respects Privacy Settings:

**Match History:**
- If `privacy_settings.show_match_history = False` → hide from everyone except self/staff
- API returns 403 or empty list with message "User has hidden match history"

**Tournament History:**
- If `privacy_settings.show_tournament_stats = False` → hide participation list
- BUT tournament results pages still show user (tournament data owns visibility)

**Activity Timeline:**
- Each activity has `visibility` field (PUBLIC / FOLLOWERS / PRIVATE)
- Filter queryset based on viewer relationship to user
- Anonymous → PUBLIC only
- Authenticated non-follower → PUBLIC only
- Follower → PUBLIC + FOLLOWERS
- Self/Staff → all activities

**Profile Stats (Counters):**
- Always visible (cannot hide aggregate counts)
- Rationale: leaderboards require visibility, users opt-in to competitive platform

### What Ignores Privacy (Always Visible):

- Tournament placements (official results, public record)
- Achievements/badges (public by design, gaming culture norm)
- Team memberships (teams are public entities)
- Public ID (always visible, non-PII by design)

**Privacy Service Method:**
- `user_profile.services.privacy_service.filter_activity_by_visibility(activities, viewer)`
- Used in all activity/history views

---

## 8. Acceptance Criteria

### Data Models Complete
- [ ] TournamentParticipation model created in tournaments app
- [ ] TournamentResult extended with user and stats fields
- [ ] Match model populated on game completion
- [ ] UserActivity model created with visibility field
- [ ] All models have required indexes

### Signal Handlers Working
- [ ] Match completion updates profile.total_matches_played and profile.matches_won
- [ ] Tournament registration creates TournamentParticipation record
- [ ] Tournament end updates profile.tournaments_participated and profile.tournaments_won
- [ ] Achievement unlock updates profile.achievement_count
- [ ] Major events create UserActivity records

### Service Layer Implemented
- [ ] stats_service.get_match_history(user, filters, page) returns paginated matches
- [ ] stats_service.get_tournament_breakdown(user, filters) returns participation list
- [ ] stats_service.get_activity_timeline(user, viewer, page) respects privacy
- [ ] privacy_service.filter_activity_by_visibility(activities, viewer) works correctly

### Profile Caches Accurate
- [ ] Nightly reconciliation verifies cached counters match source counts
- [ ] Win rate updates correctly after each match
- [ ] Tournament stats update within 1 minute of tournament end
- [ ] Drift rate <1% across all cached stats

### Privacy Enforcement
- [ ] Match history respects privacy_settings.show_match_history flag
- [ ] Activity timeline filters by visibility and viewer relationship
- [ ] API returns 403 or empty list with message when privacy blocks access

### Performance Targets
- [ ] Profile page loads in <300ms (cached stats only)
- [ ] Match history page (10 items) loads in <200ms
- [ ] Activity timeline (10 items) loads in <150ms
- [ ] Leaderboard query (top 100) completes in <100ms

### Manual Checks
- [ ] Profile displays accurate match count
- [ ] Tournament history shows all participated tournaments
- [ ] Activity timeline shows major events only (no noise)
- [ ] Privacy toggle hides match history from non-self viewers
- [ ] Game-specific breakdown filters work correctly

---

## Implementation Notes

**Phase:** UP-4 (Stats & History) in execution plan

**Dependencies:**
- UP-1 (Invariant) → profile exists for all users
- UP-3 (Economy) → signals pattern established
- Tournaments app → TournamentParticipation model created

**Migration Strategy:**
- Create new models first (TournamentParticipation, UserActivity)
- Backfill historical data where possible (tournaments already completed)
- Enable signals going forward (new data automatically tracked)
- Nightly reconciliation fixes any gaps

**Risk Mitigation:**
- Paginate all history queries (prevent OOM on users with 1000+ matches)
- Cache first page aggressively (most users only view page 1)
- Activity timeline limited to major events (prevent feed spam)
- Privacy filters applied at queryset level (prevent leaks)

---

**End of Document**
