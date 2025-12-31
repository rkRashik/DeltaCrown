# Loadout & Live Status Design
**Date:** December 31, 2025  
**Architect:** Principal Backend Architect  
**Type:** Technical Design (No Implementation)  
**Scope:** Pro-Settings Engine & Live Tournament Tracking

---

## 1. System Intent (Loadout/Pro-Settings Engine)

The Loadout system is a pro-settings transparency database where competitive players document their hardware peripherals (mouse, keyboard, headset, monitor) and game-specific configurations (sensitivity, crosshair, keybinds, graphics settings) across all 11 supported games. Unlike manual text-entry systems prone to outdated or fabricated data, this system provides a structured, searchable catalog of verified gear and settings that spectators, aspiring players, and scouts can browse, filter, and copy to replicate successful player configurations. Each game has its own settings schema (Valorant sensitivity differs from CS2, PUBG has vehicle keybinds not in Aim Lab), and hardware selections are limited to predefined products from a curated catalog to ensure data quality and enable optional e-commerce integration. The primary goal is competitive transparency: "This is exactly what hardware and settings I use to compete" becomes a verifiable profile section, not a vague claim.

---

## 2. User Use Cases

**For Competitive Players (Profile Owners):**

- **Document Setup**: Select mouse (e.g., "Logitech G Pro X Superlight"), set DPI (800), polling rate (1000Hz), save to profile
- **Per-Game Configs**: Configure Valorant settings (sensitivity 0.45, crosshair style, 4:3 stretched res), separate from CS2 settings (sensitivity 1.2, native res)
- **Update Transparency**: When switching hardware or tweaking settings, update loadout to keep spectators informed
- **Professional Credibility**: Verified loadouts signal seriousness ("I'm not hiding my config, here's exactly what I use")

**For Spectators & Aspiring Players (Visitors):**

- **Copy Settings**: See top player's Valorant sens is 0.45/800 DPI, try same settings in own game
- **Hardware Research**: Browse what mouse most Diamond+ players use, discover trends (e.g., "80% use wireless lightweight mice")
- **Filter Configs**: Search "Show me all Valorant IGL loadouts with low sensitivity" to find similar playstyles
- **Purchase Links**: Click "View in Store" on mouse listing to buy same hardware (optional e-commerce integration)

**For Team Scouts & Analysts:**

- **Loadout Comparison**: Compare candidate players' settings to team's existing roster (e.g., "Do they use similar sens to our entry fragger?")
- **Equipment Verification**: Ensure player has proper gear (tournament-legal mouse, no macro-capable keyboards)
- **Consistency Check**: Verify player hasn't drastically changed settings recently (stability indicator)

**For Platform (DeltaCrown):**

- **E-commerce Revenue**: Affiliate commissions when spectators purchase hardware through loadout links
- **Sponsored Gear**: Partner with brands to feature products in catalog ("Official DeltaCrown Partner: Logitech")
- **Data Insights**: Aggregate statistics ("Top 100 players prefer 800 DPI by 73%") for content marketing

---

## 3. Constraints & Boundaries

**Per-Game Configuration:**

- Each of 11 games has separate loadout settings (cannot reuse Valorant config for CS2)
- Game schemas differ: Valorant has agent-specific crosshairs, PUBG has vehicle controls, MLBB has hero item builds
- User can have 0-11 game loadouts configured (not required to fill all games)
- Changing hardware (mouse) applies globally, but sensitivity is per-game

**Supported Games (11 Total):**

- Valorant, CS2, PUBG, Mobile Legends: Bang Bang, Free Fire, Call of Duty Mobile, Apex Legends, Rainbow Six Siege, Overwatch 2, Fortnite, Aim Lab
- Each game requires custom settings schema definition (one-time setup per game)
- Future games added via migration, not dynamically created by users

**Hardware Catalog (Curated, Not Open-Ended):**

- Users select from predefined hardware list (admins add products, not users)
- Categories: Mouse, Keyboard, Headset, Monitor, Mousepad
- Each product has structured specs: DPI range, polling rate options, switch type, connectivity
- No free-text "Other" option to maintain data quality (request new product via support if needed)

**No Overengineering:**

- No version history tracking ("when did you change your sens?") in MVP - just current state
- No "copy loadout to clipboard" API in MVP - users manually transcribe settings
- No cross-game sensitivity converter ("convert Valorant sens to CS2") - out of scope
- No gear performance analytics ("players with this mouse have 12% higher win rate") - future phase

**Privacy Considerations:**

- Loadout visibility respects profile privacy settings (if profile private, loadout hidden)
- No "hide loadout but show profile" granular control (MVP uses profile-level privacy)
- Hardware purchases NOT tracked per-user (affiliate link is generic, not personalized tracking)

---

## 4. Data Models Required

**Core Models:**

- **HardwareProduct** - Catalog of available hardware (name, category, brand, model, specs_json, affiliate_url)
  - Responsibility: Store master list of purchasable gear (admin-managed, users select from this list)
  - Examples: "Logitech G Pro X Superlight", "Razer DeathAdder V3 Pro", "HyperX Cloud II"
  - Specs stored as JSON: `{"dpi_options": [800, 1600, 3200], "polling_rate": [1000], "weight_grams": 63}`

- **UserHardware** - User's selected hardware (user, category, product, custom_settings_json)
  - Responsibility: Store which hardware user owns/uses (one entry per category per user)
  - Custom settings: DPI selected (from product's available options), polling rate, RGB disabled, etc.
  - Example: User selects "Logitech G Pro X Superlight", sets DPI to 800 (from allowed [400, 800, 1600, 3200])

- **GameConfig** - Per-game settings for a user (user, game, settings_json, last_updated)
  - Responsibility: Store game-specific configurations (sensitivity, crosshair, keybinds, graphics)
  - Settings schema varies by game: Valorant has agent crosshairs, CS2 has viewmodel FOV, PUBG has vehicle controls
  - Example: `{"sensitivity": 0.45, "dpi": 800, "crosshair_style": "small_dot", "resolution": "1920x1080"}`

- **GameSettingsSchema** - Definition of what fields each game supports (game, schema_json, version)
  - Responsibility: Define structure of settings for each game (used for form validation and rendering)
  - Schema defines: field names, types, validation rules, default values, display labels
  - Example: `{"sensitivity": {"type": "float", "min": 0.1, "max": 5.0, "label": "Mouse Sensitivity"}}`
  - Allows adding new games without code changes (admins define schema via admin panel)

**Models NOT Needed (Reuse Existing):**

- ❌ **Game** - Use existing `apps/games/` Game model for game references
- ❌ **UserProfile** - Use existing for user linkage
- ❌ **ProductCategory** - Use TextChoices enum in HardwareProduct (MOUSE, KEYBOARD, HEADSET, MONITOR, MOUSEPAD)

**Optional/Future Models:**

- **LoadoutPreset** - Saved loadout configurations for quick switching (e.g., "Tournament Setup" vs "Practice Setup")
- **PopularSettings** - Aggregated statistics (e.g., "73% of Diamond+ players use 800 DPI")
- **HardwareReview** - User reviews of products (requires moderation, defer to Phase 2)

---

## 5. Searchability & Index Strategy

**Search Use Cases:**

- "Show all Valorant loadouts with sensitivity between 0.3-0.5"
- "Find players using Logitech G Pro X Superlight"
- "Show loadouts from Diamond+ ranked players"
- "Filter by game and mouse DPI range"

**Index Requirements (Conceptual):**

- **GameConfig.settings_json**: Index on extracted values for common search fields
  - Valorant: `settings_json->>'sensitivity'` (cast to numeric for range queries)
  - CS2: `settings_json->>'resolution'` (for exact match filters)
  - Use JSON GIN index for broad searches, extracted columns for specific filters

- **UserHardware.product_id**: Index for "show all users with product X" queries
  - Foreign key index (auto-created) enables efficient product-to-users lookup
  - Composite index: (category, product_id) for "show all mouse users of brand X"

- **GameConfig + UserProfile**: Join index for rank-based filtering
  - Composite index: (user_id, game_id) for profile-to-loadout lookup
  - Filter by user's rank via UserProfile join: `WHERE user.rank >= 'diamond'`

**Query Performance Considerations:**

- GameConfig table grows linearly with users (max 11 rows per user, one per game)
- HardwareProduct catalog small (~200 products), fully cacheable
- UserHardware limited (5 categories * user count = manageable size)
- Most expensive query: "Show all Valorant configs with sens 0.3-0.5 AND rank Diamond+" (requires JSON extraction + join)
- Mitigation: Pre-extract common search fields to dedicated columns (e.g., `valorant_sensitivity` column for fast range queries)

**Search Endpoint Design (Conceptual):**

- GET `/loadouts/search?game=valorant&sens_min=0.3&sens_max=0.5&rank_min=diamond`
- Backend: Filter GameConfig by game, extract sensitivity from JSON, filter by range, join UserProfile for rank filter
- Return: List of user profiles with matching loadouts (paginated, 20 per page)
- Cache: Popular searches cached for 1 hour (e.g., "Top 100 Valorant loadouts")

**Aggregation Queries:**

- "Most popular mouse": `SELECT product_id, COUNT(*) FROM UserHardware WHERE category='MOUSE' GROUP BY product_id ORDER BY count DESC LIMIT 10`
- "Average Valorant sensitivity": `SELECT AVG((settings_json->>'sensitivity')::numeric) FROM GameConfig WHERE game_id='valorant'`
- "DPI distribution": Aggregate custom_settings_json->>'dpi' from UserHardware where category='MOUSE'

---

## 6. "Copy Pro Settings" Support

**Data Requirements for Copy Feature:**

- User must be able to view complete settings JSON in readable format
- Settings display should include:
  - Hardware: Brand, model, DPI, polling rate, other specs
  - Game settings: Sensitivity, crosshair, keybinds, graphics options
  - Calculated effective sensitivity (eDPI = sens * DPI) for comparison across configs

**Display Format (Template Context):**

- `pro_loadout` object with:
  - `hardware`: Dict of hardware by category `{"mouse": {"product": "Logitech G Pro", "dpi": 800, "polling_rate": 1000}}`
  - `game_settings`: Dict per game `{"valorant": {"sensitivity": 0.45, "crosshair_style": "small_dot", ...}}`
  - `effective_dpi`: Calculated value for easy comparison

**Copy Interaction (UI Flow):**

- User clicks "View Loadout" on pro player's profile
- Modal or dedicated page shows structured settings table
- Each setting has "Copy" button (copies value to clipboard)
- Or "Copy All" button (copies formatted text of entire config)
- Future: "Import to My Loadout" button (pre-fills user's own loadout form)

**Export Format (Future Enhancement):**

- JSON export: User downloads `player_name_valorant_config.json` with all settings
- Config file export: User downloads game-specific config file (e.g., `config.cfg` for CS2) if game supports it
- Shareable link: `/@username/loadout/valorant` generates permalink to specific game config

**Validation on Import (Future):**

- If user imports pro's settings, validate against GameSettingsSchema
- Ensure DPI matches one of their mouse's supported DPI options
- Warn if resolution higher than user's monitor supports
- Prevent importing settings for game user doesn't own/play

**Privacy for Copy:**

- Only publicly visible profiles allow loadout copying
- Private profiles: Loadout hidden entirely (no "copy" option)
- No tracking of "who copied my settings" (privacy consideration)
- Optional: User can disable loadout on public profile (future granular privacy control)

---

## 7. Live Status System (Tournament Match Tracking)

**System Intent:**

- Display "🔴 LIVE - Playing in Tournament" banner on user profile when they have an active tournament match
- Provides context for profile visitors: "This player is competing right now"
- Increases engagement: Spectators can follow match or find stream link
- Not a streaming integration (just match status indicator)
- Simple query-based detection, no WebSocket or real-time updates required

**What "Live" Means:**

- User is a participant in a tournament match currently in `LIVE` or `IN_PROGRESS` state
- Match exists in `apps/tournaments/models/match.py` with `state='LIVE'`
- Match has not completed (`state != 'COMPLETED'`, `!= 'FORFEIT'`, `!= 'CANCELLED'`)
- User is either participant1 or participant2 (1v1), or member of team_a/team_b (team match)

---

## 8. Live Match Detection Strategy

**Query Logic (High-Level):**

- When rendering profile, check for active matches: `Match.objects.filter(state='LIVE')`
- Filter by participant: `Q(participant1_id=user.id) | Q(participant2_id=user.id)` for 1v1 matches
- For team matches: Join through TeamMembership to find matches where user's team is competing
- If match found: User is currently live, extract match details for banner display
- If no match found: No banner, profile renders normally

**State Transitions to Monitor:**

- `SCHEDULED` → `CHECK_IN` → `READY` → `LIVE` (banner appears)
- `LIVE` → `PENDING_RESULT` (banner remains, shows "Match Ending Soon")
- `PENDING_RESULT` → `COMPLETED` (banner disappears)
- Only `LIVE` state triggers banner (not `SCHEDULED` or `CHECK_IN`)

**Multi-Match Handling:**

- Edge case: User in multiple concurrent tournaments (rare but possible)
- Show banner for most recent live match (order by `match.started_at DESC`)
- Or show count: "🔴 LIVE in 2 Tournaments" if multiple matches active
- Banner links to most important match (highest stakes, higher round, etc.)

**Performance Considerations:**

- Live match query runs on every profile view (potential bottleneck)
- Optimization: Cache live match status for 1 minute (match state rarely changes during match)
- Cache key: `live_match:{user_id}` → stores match_id or None
- Invalidate cache when match transitions to/from `LIVE` state (via signal)
- Alternative: Only query live status on public profiles, skip for owner viewing own profile

---

## 9. Live Status Profile Context

**Required Context Variables:**

- `is_live_in_tournament` (bool):
  - True if user has active match in `LIVE` state
  - False otherwise (no banner displayed)

- `live_match` (Match object or None):
  - Full match details if `is_live_in_tournament=True`
  - Includes: match_id, tournament_name, opponent_name, game, round, started_at
  - None if no active match

- `live_tournament_info` (dict or None):
  - Structured data for banner display
  - Example: `{"tournament_name": "Season 2 Playoffs", "game": "Valorant", "opponent": "Team Phoenix", "round": "Semifinals", "match_url": "/tournaments/123/match/456"}`
  - Includes link to match detail page for spectators to follow

**Banner Display Data:**

- Tournament name: "DeltaCrown Season 2 Playoffs"
- Game icon: Valorant logo
- Opponent: "vs. @username" (1v1) or "vs. Team Phoenix" (team match)
- Round/bracket: "Semifinals - Best of 3"
- Time elapsed: "Started 15 minutes ago" (calculated from match.started_at)
- Action button: "Watch Match" → links to match detail or tournament bracket page

**Optional Enhancements:**

- Stream link: If user has Twitch/YouTube in SocialLink, show "🎥 Watch Stream" button
- Score update: If match reports scores incrementally, show "Team A: 10 - Team B: 8"
- Match chat: Link to tournament match chat for spectators (if chat feature exists)

---

## 10. Permissions & Privacy

**Public Profile (Default):**

- Live status banner visible to all visitors (logged in or anonymous)
- Rationale: Tournament matches are public events, match results are public record
- Showing live status increases spectator engagement and platform visibility

**Private Profile:**

- Live status banner HIDDEN from visitors (respects profile privacy setting)
- Only profile owner sees banner when viewing their own profile
- Rationale: If user wants profile private, they don't want visitors knowing their tournament schedule

**Team Context:**

- If user is in team match, team profile may also show "Team member @username is LIVE"
- Team notifications sent when member goes live (optional, defer to Phase 2)
- Captain can see all team members' live status on team dashboard

**Anti-Stalking Considerations:**

- Live status does not reveal user's physical location or device IP
- Match start time shown, but not duration prediction (prevents timing attacks)
- If user concerned about opponents scouting their stream, they can delay stream by 3+ minutes

**Opt-Out Option (Future):**

- Allow users to disable live status banner even on public profile
- Setting: "Hide tournament activity while playing" (off by default)
- Use case: Pro players practicing new strategies in smaller tournaments, don't want scouts watching

---

## 11. Integration with Tournament System

**Signal Hook (Match State Change):**

- When Match.state transitions to `LIVE`, trigger signal: `match_went_live.send(sender=Match, match=match)`
- Signal receiver invalidates cached live status for all participants
- Recalculate `is_live_in_tournament` on next profile view

**Match Service Integration:**

- `MatchService.start_match(match_id)` transitions state to `LIVE`
- Service also publishes event: `MatchStartedEvent` to event bus
- Event consumed by notification service, profile cache invalidation, analytics

**Tournament Bracket Display:**

- Tournament bracket page highlights matches in `LIVE` state with red indicator
- Click on live match redirects to match detail page
- Profile live banner links back to tournament bracket for context

**Post-Match Cleanup:**

- When match completes, state transitions to `PENDING_RESULT` or `COMPLETED`
- Live status banner disappears automatically on next profile view (cache expires)
- No manual cleanup required (state-driven display logic)

---

## 12. Open Questions & Design Decisions

**Question 1: Should "Check-In" state show banner?**
- Match is not yet live (lobby not started), but players are confirmed present
- Option A: Show "🟡 Checking In - Match Starting Soon" (yellow banner)
- Option B: No banner until `LIVE` state (less clutter)
- **Recommendation**: Option B for MVP, add check-in indicator in Phase 2 if user feedback requests it

**Question 2: How long to cache live status?**
- Shorter cache (30 seconds): More accurate, higher DB load
- Longer cache (5 minutes): Less accurate, lower DB load
- **Recommendation**: 1 minute cache (balance between accuracy and performance)

**Question 3: Should banner auto-refresh during viewing?**
- Option A: Static banner on page load (user refreshes to see status change)
- Option B: JavaScript polls every 30 seconds to update banner dynamically
- **Recommendation**: Option A for MVP (simpler), Option B if real-time feel is critical

**Question 4: Multiple live matches - which to display?**
- Priority: Tournament tier (higher tier first), then round (semifinals > quarterfinals), then start time (most recent)
- Or show count: "LIVE in 2 tournaments" with dropdown to select which match to follow
- **Recommendation**: Single banner showing highest priority match (avoid overwhelming visitors)

---

## 13. Stream Embed System (Manual Stream Display)

**System Intent:**

- Allow users to link their Twitch/YouTube/Facebook Gaming stream channel
- When user marks "I'm streaming now" or has live tournament match, display embedded stream player on profile
- Simple embed strategy: No polling external APIs to check if stream is live (trust user input)
- User controls when stream is displayed via manual toggle or automatic tournament match detection
- Embed uses platform's iframe player (Twitch Player, YouTube Embed, Facebook Video)

**Why Not Auto-Detect Stream Status:**

- Polling Twitch/YouTube APIs every profile view is expensive (rate limits, API costs)
- No webhooks from Twitch to DeltaCrown (requires OAuth, server callbacks, complex setup)
- MVP solution: User manually toggles "Show Stream" when they go live
- Alternative: Auto-show stream only when tournament match is `LIVE` state (high confidence user is actually streaming)

---

## 14. StreamConfig Model Responsibilities

**Model Purpose:**

- Store user's streaming channel information (platform, channel URL/username)
- Track manual stream visibility toggle (is_live_override)
- Store embed configuration (chat enabled, autoplay, muted by default)
- Not a separate model necessarily - can extend UserProfile or SocialLink

**Core Responsibilities:**

- **Platform identification** - Which streaming service (Twitch, YouTube, Facebook Gaming)
- **Channel reference** - Username or channel URL for that platform
- **Manual visibility** - Boolean: "Show stream on my profile right now" (user-controlled toggle)
- **Embed preferences** - Chat visible, autoplay enabled, volume muted, quality setting

**Storage Options:**

- Option A: Extend existing `SocialLink` model with `is_streaming_now` boolean field
- Option B: New `StreamConfig` model: `(user, platform, channel_id, is_live_now, embed_settings_json)`
- Option C: Add fields to `UserProfile`: `stream_platform`, `stream_channel`, `show_stream_now`
- **Recommendation**: Option A (minimal new infrastructure, reuses social links)

**Key Fields (Conceptual):**

- `platform` - TextChoices: TWITCH, YOUTUBE, FACEBOOK_GAMING, TROVO
- `channel_identifier` - Username or channel ID (e.g., "ninja" for Twitch)
- `is_live_override` - Boolean: User manually set "I'm streaming now" (overrides auto-detection)
- `show_stream_on_profile` - Boolean: Global setting, "Always show stream player on my profile"
- `embed_settings` - JSONField: `{"chat": true, "autoplay": false, "muted": true}`

---

## 15. Embed URL Conversion Logic

**Platform-Specific Embed URLs:**

Each platform has a specific iframe embed URL format that must be constructed from user's channel identifier.

**Twitch:**
- User provides: Channel username (e.g., "ninja")
- Embed URL: `https://player.twitch.tv/?channel=ninja&parent=deltacrown.com`
- Parameters: `channel` (username), `parent` (domain whitelist for Twitch API), optional: `muted=true`, `autoplay=false`

**YouTube:**
- User provides: Channel URL or video URL (e.g., "https://youtube.com/@username" or "https://youtu.be/VIDEO_ID")
- Extract channel ID or video ID from URL
- Embed URL: `https://www.youtube.com/embed/live_stream?channel=CHANNEL_ID` (for live streams)
- Or for specific video: `https://www.youtube.com/embed/VIDEO_ID`
- Parameters: `autoplay=0`, `muted=1`, `enablejsapi=1`

**Facebook Gaming:**
- User provides: Gaming creator page URL (e.g., "https://fb.gg/username")
- Extract username from URL
- Embed URL: `https://www.facebook.com/plugins/video.php?href=https://fb.gg/username/live`
- Parameters: `width`, `height`, `autoplay=false`

**Conversion Method (Conceptual):**

- Service method: `get_embed_url(platform, channel_identifier, embed_settings)`
- Input validation: Verify channel_identifier is alphanumeric (no injection attacks)
- URL construction: Use f-string or template with whitelist of allowed parameters
- Output: Safe embed iframe URL with parameters

**Example Logic Flow:**
```
if platform == 'TWITCH':
    embed_url = f"https://player.twitch.tv/?channel={channel_identifier}&parent={request.get_host()}&muted=true"
elif platform == 'YOUTUBE':
    embed_url = f"https://www.youtube.com/embed/live_stream?channel={channel_identifier}&autoplay=0"
elif platform == 'FACEBOOK_GAMING':
    embed_url = f"https://www.facebook.com/plugins/video.php?href={channel_url}/live"
```

**Fallback Handling:**

- If platform not supported: Return None (no embed displayed)
- If channel_identifier invalid: Log error, return None
- If embed URL fails to load (404): Show "Stream Offline" message instead of broken iframe

---

## 16. Supported Streaming Platforms

**Tier 1 (MVP - Must Support):**

- **Twitch** - Most popular gaming streaming platform, embed API well-documented
- **YouTube Live** - Second most popular, supports live streams and VODs
- **Facebook Gaming** - Growing platform, especially in Southeast Asia (Bangladesh audience)

**Tier 2 (Phase 2 - Nice to Have):**

- **Trovo** - Emerging platform, similar to Twitch
- **Nimo TV** - Popular in Asia, especially for mobile games
- **Kick** - New Twitch competitor, growing in 2024-2025

**Tier 3 (Future - Low Priority):**

- **TikTok Live** - Mobile-first, less common for PC gaming
- **Instagram Live** - Not gaming-focused, low priority
- **Custom RTMP** - Advanced users with own streaming server (complex, defer)

**Platform Requirements:**

- Must support iframe embed (no proprietary plugins)
- Must allow third-party domain embedding (some platforms restrict)
- Must have stable embed API (URL format doesn't change frequently)

**Not Supported:**

- Platforms without embed support (e.g., Discord Go Live - internal only)
- Adult content platforms (violates terms of service)
- Platforms requiring OAuth to view streams (adds complexity)

---

## 17. Abuse & Security Considerations

**URL Validation:**

- Whitelist allowed domains: `twitch.tv`, `youtube.com`, `facebook.com`, `fb.gg`
- Reject non-streaming URLs: No embedding `evil.com/malware.html`
- Validate URL format with regex: `^https://(www\.)?(twitch\.tv|youtube\.com|facebook\.com)/.*$`
- Strip dangerous parameters: Remove `javascript:`, `data:`, `file:` schemes

**XSS Prevention:**

- Never render user-provided URLs directly in HTML
- Use Django template escaping: `{{ embed_url|escape }}`
- Construct iframe with hardcoded template: `<iframe src="{{ embed_url }}" sandbox="allow-scripts allow-same-origin">`
- Sandbox iframe: Restrict `allow-top-navigation`, `allow-forms` (only allow video playback)

**Rate Limiting:**

- Limit stream toggle changes: User can only enable "Show Stream" 5 times per hour (prevents spam)
- If user repeatedly toggles, temporary cooldown (30 minutes)
- Prevents abuse: User showing offensive stream, disabling, re-enabling to evade moderation

**Content Moderation:**

- Embedded streams display platform's native content (not DeltaCrown-hosted)
- Trust platform's content moderation (Twitch TOS, YouTube Community Guidelines)
- If user reports inappropriate stream: Admin can disable user's stream embed privilege
- Moderation action: Flag user, disable `show_stream_on_profile`, send warning

**Performance Protection:**

- Iframe lazy loading: `loading="lazy"` attribute (only load when scrolled into view)
- No autoplay by default: Requires user interaction to start video (saves bandwidth)
- Limit embed dimensions: Max 1280x720 (prevent giant iframes breaking layout)

**Privacy Concerns:**

- Embedding stream may expose visitor IP to platform (Twitch sees viewer IP)
- No tracking cookies from DeltaCrown side (platform's cookies only)
- User consent: "By linking stream, you acknowledge embeds will be shown to profile visitors"

**Fake Stream Prevention:**

- User claims "I'm live" but stream is offline: Visitors see "Stream Offline" player
- No penalty for false positive (user forgot to toggle off after stream ended)
- If repeatedly abused (always shows offline stream): Moderator can disable feature

---

## 18. Profile Context Variables (Streaming)

**For Profile View (public_v3.html):**

- `stream_embed_config` (dict or None):
  - If user has stream configured AND (`is_live_override=True` OR `is_live_in_tournament=True`): Return config
  - If no stream or not live: Return None (no embed displayed)
  - Structure: `{"platform": "twitch", "embed_url": "https://player.twitch.tv/?channel=...", "chat_enabled": true, "autoplay": false}`

- `show_stream_player` (bool):
  - True if `stream_embed_config` is not None
  - False otherwise
  - Template: `{% if show_stream_player %}<iframe src="{{ stream_embed_config.embed_url }}">{% endif %}`

- `stream_offline_message` (string or None):
  - If `is_live_override=True` but embed fails to load: "Stream may be offline"
  - If `is_live_in_tournament=True` but no stream configured: "Player is competing but not streaming"

**For Profile Settings (stream_settings.html):**

- `stream_config` (StreamConfig object or None):
  - User's current stream configuration
  - Includes: platform, channel_identifier, is_live_override, embed_settings

- `supported_platforms` (list):
  - Available streaming platforms for selection
  - Example: `[{"value": "twitch", "label": "Twitch"}, {"value": "youtube", "label": "YouTube Live"}]`

- `stream_preview_url` (string):
  - Preview embed URL for user to test before saving
  - Renders in settings page: "Preview how your stream will appear"

**For Live Status Banner Enhancement:**

- `stream_available` (bool):
  - True if user has stream configured (regardless of live status)
  - Used to show "🎥 Watch Stream" button on live tournament banner
  - Button links to profile scroll position of stream embed

- `stream_platform_icon` (string):
  - Platform logo URL for display: `/static/icons/twitch.svg`
  - Shown next to "Watch Stream" button

---

## 19. Integration Points

**Tournament Match Integration:**

- When match transitions to `LIVE` state, check if user has `stream_config.platform` set
- If yes, automatically set `show_stream_player=True` on profile (no manual toggle needed)
- When match completes, automatically set `show_stream_player=False` (cleanup)
- User can manually override: Toggle off stream even during live match (privacy control)

**Social Link Integration:**

- Reuse existing `SocialLink` model infrastructure if extending it
- User's Twitch link in social section also becomes stream embed source
- Consistent UX: "Add stream link" in social links, "Enable stream embed" in settings

**Notification Integration:**

- When user enables stream: Notify followers "[@username is now streaming!]"
- Optional: Push notification to mobile app (if follower has notifications enabled)
- Prevents spam: Only send notification once per stream session (not every toggle)

**Analytics Integration (Future):**

- Track embed views: How many visitors watched stream on profile
- Track click-through: How many clicked "Watch on Twitch" to leave DeltaCrown
- Data used for: Demonstrating value to streamers, encouraging more to link streams

---

## 20. Implementation Priority

**Phase 1 (MVP - Week 1-2):**
- HardwareProduct catalog (100 initial products)
- UserHardware model and selection interface
- GameConfig model for Valorant and CS2 only (2 games)
- Basic loadout display on profile (hardware + one game)

**Phase 2 (Expansion - Week 3-4):**
- GameSettingsSchema for remaining 9 games
- Loadout search/filter endpoint
- "Copy Pro Settings" display format
- Live status banner (tournament match detection)
- StreamConfig integration with SocialLink

**Phase 3 (Enhancement - Week 5+):**
- Stream embed with Twitch/YouTube support
- Automatic stream display during live matches
- Follower notifications when user goes live
- Loadout analytics (popular hardware, average DPI)
- Export config file feature
- Facebook Gaming embed support

---

## 21. Open Questions & Design Decisions

**Question 1: Should stream embed be main feature or sidebar widget?**
- Option A: Full-width embed at top of profile (prominent, but pushes content down)
- Option B: Sidebar widget (less intrusive, but smaller player)
- **Recommendation**: Option B (sidebar widget, matches template mockup)

**Question 2: How to handle stream ending during profile view?**
- Embed shows "Stream Offline" automatically (platform handles it)
- DeltaCrown doesn't know stream ended (no polling)
- User must manually toggle off, or auto-disable after tournament match ends
- **Recommendation**: Accept limitation (MVP), add auto-cleanup in Phase 2

**Question 3: Should we show VOD (past broadcast) when stream offline?**
- Twitch/YouTube embeds can show last VOD if live stream offline
- Pro: Visitors always see content, Con: May show old/irrelevant content
- **Recommendation**: Show VOD as fallback (free engagement), let user disable in settings

**Question 4: What if user has multiple streaming channels (Twitch + YouTube)?**
- Allow configuring both, user selects primary platform for embed
- Or show both embeds side-by-side (complex, cluttered)
- **Recommendation**: Single primary platform (user chooses), add multi-platform in Phase 3

**Question 5: Should non-streamers see loadout/live status?**
- Live status yes (everyone competes in tournaments)
- Stream embed no (only if user has stream configured)
- Loadout yes (everyone can document their setup, even if not streaming)
- **Recommendation**: All features available to all users, streaming is optional

---

**DESIGN COMPLETE**

**Document Status:** ✅ Ready for Technical Review  
**Next Steps:**
1. Review streaming platform embed policies (ensure compliance with Twitch/YouTube terms)
2. Define HardwareProduct catalog initial seed data (100 products, 5 categories)
3. Create GameSettingsSchema for Valorant (reference schema for other games)
4. Design loadout settings page UI mockup
5. Plan stream embed moderation workflow (reporting, disabling)
6. Coordinate with frontend team on iframe lazy loading and responsive sizing

---

**END OF LOADOUT & LIVE STATUS DESIGN**



