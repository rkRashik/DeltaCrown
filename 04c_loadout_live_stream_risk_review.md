# Loadout, Live Status & Stream Embed Risk Review
**Date:** December 31, 2025  
**Reviewer:** Security & Platform Engineer  
**Type:** Risk Assessment & Mitigation Strategy  
**Scope:** Pro-Settings Engine + Live Match Banner + Stream Embed System

---

## 1. LOADOUT / PRO-SETTINGS RISKS

### Risk 1.1: Fake "Pro" Claims (Fraudulent Equipment Listings)
**Description:** User claims to use expensive professional gear (e.g., "Logitech G Pro X Superlight") but actually uses budget mouse, misleading spectators and sponsors who believe profile represents genuine pro setup.

**Severity:** 🟡 **Low**

**Mitigation:**
- Curated hardware catalog only (admins add products, users cannot free-text "custom" gear)
- No verification required in MVP (honor system, similar to self-reported rank before API integration)
- Reputation context: High-reputation users (1000+) have more credible loadouts than new accounts
- Sponsored players: Require verification (screenshot of gear with signed paper, tournament photo showing setup)
- Community reporting: "Report inaccurate loadout" option flags profile for admin review
- Future: Partner with tournament organizers to verify gear at LAN events (photo validation)

### Risk 1.2: Config Spam (Frequent Setting Changes to Appear Active)
**Description:** User changes loadout settings every hour (sensitivity 0.45 → 0.46 → 0.45) to appear in "Recently Updated Loadouts" feed, spamming discovery section without meaningful changes.

**Severity:** 🟡 **Low**

**Mitigation:**
- Rate limit: Max 5 loadout updates per game per day (prevents excessive churn)
- Cooldown: 1-hour cooldown between updates to same game config
- Activity feed filters: Only show updates with substantial changes (>10% sensitivity change, hardware switch, not minor tweaks)
- "Recently Updated" feed: Show max 1 update per user per 24 hours (prevents feed domination)
- Admin review: Flag users with 20+ updates in one week (suspicious activity pattern)

### Risk 1.3: Searchable Index Performance Degradation
**Description:** JSON field queries on GameConfig.settings_json with complex filters (sensitivity range + crosshair style + resolution + rank) cause slow queries, profile search times out, users frustrated.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Pre-extract common search fields: Add `valorant_sensitivity` column extracted from JSON on save (indexed for fast range queries)
- Database indexes: GIN index on settings_json for broad searches, B-tree indexes on extracted columns for specific filters
- Query optimization: Limit joins, filter by game first (smallest set), then apply JSON filters
- Pagination: Max 20 results per page, cursor-based pagination for large result sets
- Caching: Popular searches cached for 1 hour: "Valorant loadouts, Diamond+, 0.3-0.5 sens" → cache key with TTL
- Query timeout: Set 5-second timeout, return partial results with "Search taking too long, refine filters" message

### Risk 1.4: Settings Visibility Privacy Leak
**Description:** User has private profile but loadout settings leaked via search API, opponent scouts their sensitivity and crosshair before match, gaining unfair advantage.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Privacy cascade: Loadout visibility inherits UserProfile.is_private setting (if profile private, loadout excluded from search)
- API endpoint validation: `/loadouts/search` queries join UserProfile, filter `WHERE is_private=False`
- Direct URL protection: `/loadouts/@username/valorant` returns 403 if profile private and requester not owner
- Team visibility exception: Team members can see private loadouts of teammates (roster context, not public)
- Search result filtering: Backend excludes private profiles before returning results (never expose IDs or partial data)

### Risk 1.5: Hardware Catalog Injection (Admin Compromise)
**Description:** Attacker gains admin access, adds malicious HardwareProduct entry with XSS payload in product name or affiliate URL, all users viewing catalog execute script.

**Severity:** 🔴 **High**

**Mitigation:**
- Input validation: Product name limited to alphanumeric + spaces (no HTML, no special chars except hyphen/space)
- URL whitelist: Affiliate URLs must match regex `^https://(www\.)?(amazon|logitech|razer|bestbuy)\.(com|co\.uk)/.*$`
- Template escaping: All product fields rendered with `{{ product.name|escape }}` (Django auto-escapes by default)
- Admin audit log: Track all HardwareProduct creations with admin user ID, timestamp, IP address
- Content Security Policy: CSP headers block inline scripts, restrict script sources to trusted CDN
- Product approval workflow: New products require two-admin approval (separation of duties)

### Risk 1.6: Specs JSON Manipulation (Invalid DPI Options)
**Description:** Admin typo in HardwareProduct.specs_json sets invalid DPI options (e.g., `{"dpi_options": [80000]}` instead of `[800]`), users select impossible DPI, loadout data corrupted.

**Severity:** 🟡 **Low**

**Mitigation:**
- JSON schema validation: Define JSONSchema for specs_json, validate on save: `{"dpi_options": {"type": "array", "items": {"type": "integer", "min": 100, "max": 32000}}}`
- Admin form validation: Show error if DPI outside realistic range (100-32000), polling rate not in [125, 250, 500, 1000]
- User selection validation: Frontend dropdown only shows valid options from specs_json (cannot free-text invalid value)
- Data migration: If invalid specs detected, log warning, reset to default specs for that product category
- Scheduled audit: Weekly job validates all specs_json against schema, alerts on violations

### Risk 1.7: Effective DPI Calculation Overflow
**Description:** User sets sensitivity 999.99 and DPI 32000, effective DPI calculation (sens * DPI) overflows integer limit, display shows negative or broken number.

**Severity:** 🟡 **Low**

**Mitigation:**
- Realistic input limits: Sensitivity capped at 10.0 (no game uses >10 sens), DPI capped at 32000
- Calculation uses float: `effective_dpi = float(sensitivity) * float(dpi)` → max 320,000 (well within bounds)
- Display formatting: Show as formatted integer: `f"{effective_dpi:,.0f}"` → "320,000 eDPI"
- Validation: If calculated eDPI exceeds 500,000, flag as unrealistic (likely data error)

### Risk 1.8: GameConfig JSON Bloat (Large Settings Object)
**Description:** Game settings schema grows to 500+ fields (all keybinds, graphics options, custom HUD settings), JSON field size exceeds PostgreSQL text limit or slows queries.

**Severity:** 🟡 **Low**

**Mitigation:**
- Schema design: Store only player-relevant settings (sensitivity, crosshair, keybinds), exclude auto-generated settings
- Field size limit: JSONField in PostgreSQL supports up to 1GB (effectively unlimited for settings), but validate JSON size < 50KB on save
- Compression: For large settings (e.g., CS2 config with 200 binds), compress JSON before storage (gzip in database column)
- Schema versioning: GameSettingsSchema.version tracks schema changes, migrate old configs on read
- Lazy loading: Don't load full settings_json on profile view, only load when user clicks "View Full Config"

### Risk 1.9: Popular Settings Manipulation (Fake Trends)
**Description:** Coordinated group creates 100 accounts, all set Valorant sensitivity to 9.99, aggregate stats show "Most popular sens: 9.99" misleading legitimate users.

**Severity:** 🟡 **Low**

**Mitigation:**
- Reputation filter: Aggregate stats only include users with reputation 100+ (excludes throwaway accounts)
- Outlier detection: Filter extreme values (sens > 5.0 or < 0.05) from aggregation as statistical outliers
- Activity filter: Only count users with recent match activity (played tournament in last 30 days)
- Sample size transparency: Show "Based on 1,247 Diamond+ players" (users can assess credibility)
- Admin review: Monitor sudden spikes in rare settings (alert if "9.99 sens" usage jumps 50% in one day)

### Risk 1.10: Affiliate Link Hijacking (URL Replacement Attack)
**Description:** Attacker modifies HardwareProduct.affiliate_url to redirect to phishing site or competitor store, DeltaCrown loses commission, users exposed to malicious site.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Database access control: Only specific admin accounts can edit affiliate URLs (not general moderators)
- URL integrity check: Store hash of affiliate_url on creation: `url_hash = sha256(affiliate_url)`, verify on read
- Domain whitelist: Affiliate URLs must be from approved partners (Amazon, Logitech, Razer, BestBuy), reject others
- Link expiry: Affiliate URLs have expiration date, require periodic re-validation
- Monitoring: Track click-through rates, alert if suddenly drops to zero (indicates broken/replaced link)
- Version control: Log all affiliate_url changes with diff, admin can rollback to previous version

---

## 2. LIVE MATCH BANNER RISKS

### Risk 2.1: Private Match Exposure (Leaking Scrims/Practice)
**Description:** User's team plays private scrim match (marked LIVE for tracking), live status banner shows "🔴 LIVE - Scrim vs Team Alpha" on public profile, reveals opponent and strategy prep to scouts.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Match visibility flag: Add `Match.is_public` boolean (only public matches show in live banner)
- Private match types: Scrims, practice matches set `is_public=False` by default, excluded from live status query
- Query filter: `Match.objects.filter(state='LIVE', is_public=True)` ensures only public tournament matches shown
- User opt-out: Setting "Hide live status during matches" disables banner even for public matches (privacy override)
- Tournament context: Only matches in official brackets/tournaments trigger live banner, exclude custom matches
- Team consent: If team match, require majority team approval to show live status (prevents one member exposing team)

### Risk 2.2: Stale Live Status (Match Ended But Banner Persists)
**Description:** Match transitions from LIVE → COMPLETED, but cache doesn't invalidate, profile shows "🔴 LIVE" for 5 minutes after match ended, confusing visitors who expect active match.

**Severity:** 🟡 **Low**

**Mitigation:**
- Cache TTL: Set short cache expiration (1 minute) on live status to ensure freshness
- Signal-based invalidation: When match state changes, publish event to invalidate cache for all participants
- Cache key granularity: Use `live_match:{user_id}:{timestamp_minute}` so cache naturally expires every minute
- Graceful staleness: Banner shows "Match recently ended" if queried within 5 minutes of completion (acknowledges timing lag)
- Client-side fallback: JavaScript checks match started_at, shows warning if > 3 hours old (indicates stale cache)

### Risk 2.3: Opponent Scouting (Stream Sniping Facilitation)
**Description:** Live banner links to user's stream, opponent opens stream during match, sees user's screen in real-time (wallhacks via stream snipe), gains unfair advantage.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Stream delay: Recommend 3-5 minute delay on stream during competitive matches (Twitch/YouTube setting)
- Banner warning: "⚠️ Streaming with delay recommended during competitive matches to prevent sniping"
- User education: FAQ explains stream sniping risk, suggests delay or disabling stream for high-stakes matches
- Tournament rules: Official tournaments require stream delay or ban streaming during matches (policy enforcement)
- Detection: If match reports stream sniping claim, admin reviews match timeline + stream timestamps

### Risk 2.4: Multiple Live Matches Race Condition
**Description:** User joins Match A (LIVE), banner shows Match A, simultaneously joins Match B (LIVE), banner flickers between A and B due to concurrent queries, confusing display.

**Severity:** 🟡 **Low**

**Mitigation:**
- Priority sorting: Query returns most important match (highest tournament tier, then most recent start time)
- Single match guarantee: `.first()` on query ensures only one match displayed (no flickering)
- Edge case acceptance: Multiple concurrent matches rare (user cannot physically play two matches simultaneously)
- Admin alert: Flag users with 2+ concurrent LIVE matches (likely data error, investigate)

### Risk 2.5: Match State Transition Timing Attack
**Description:** Opponent monitors user's profile, sees live status disappear, infers match ended, checks tournament bracket before official announcement, gains intel on team elimination.

**Severity:** 🟡 **Low**

**Mitigation:**
- Public information: Match results are public once completed (not sensitive data)
- Timing delay acceptable: 1-minute cache lag doesn't leak significant competitive intel
- Tournament broadcasts: Official streams announce results simultaneously with match completion
- No mitigation needed: This is not a security vulnerability (match outcome is public record)

### Risk 2.6: Database Load from Live Status Queries
**Description:** 10,000 concurrent profile views all query `Match.objects.filter(state='LIVE')` on every page load, database overloaded, site slows down.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Query caching: Cache live status check for 1 minute per user (max 10K cache entries, manageable)
- Index optimization: Composite index on `(state, participant1_id, participant2_id)` for fast filtering
- Read replica: Route live status queries to read replica database (offload primary DB)
- Lazy loading: Only fetch live status for users with recent activity (last login < 7 days), assume inactive users not live
- Throttling: If site under heavy load, increase cache TTL to 5 minutes temporarily (graceful degradation)

---

## 3. STREAMING EMBED RISKS

### Risk 3.1: Malicious Embed URL (XSS via iframe src)
**Description:** Attacker sets stream URL to `javascript:alert('XSS')` or `data:text/html,<script>...</script>`, profile visitors execute malicious script when iframe loads.

**Severity:** 🔴 **High**

**Mitigation:**
- URL scheme whitelist: Only allow `https://` URLs (reject `javascript:`, `data:`, `file:`, `ftp:`)
- Domain whitelist: Embed URL must match regex `^https://(player\.twitch\.tv|www\.youtube\.com|www\.facebook\.com)/.*$`
- Input sanitization: Strip all query parameters except whitelisted ones (e.g., `channel`, `video`, `autoplay`)
- Django template escaping: Use `{{ embed_url|escape }}` (though `src` attribute is less vulnerable than innerHTML)
- CSP frame-src directive: `Content-Security-Policy: frame-src https://player.twitch.tv https://www.youtube.com https://www.facebook.com`
- Iframe sandbox: `<iframe src="..." sandbox="allow-scripts allow-same-origin">` (no top navigation, no forms)

### Risk 3.2: Phishing via Fake Stream Player
**Description:** Attacker creates look-alike phishing site `twitch-login.evil.com`, embeds on profile, visitors think it's legitimate Twitch login, enter credentials.

**Severity:** 🔴 **High**

**Mitigation:**
- Platform verification: Only embed from official domains (player.twitch.tv, not twitch-player.com or similar typosquats)
- Visual indicators: Show platform logo above embed: "🟣 Twitch Stream" to clarify source
- Domain display: Show embed domain below player: "Streaming on twitch.tv" (transparency)
- No custom embed HTML: Users cannot provide raw iframe code, only channel identifier (platform + username)
- Content Security Policy: CSP frame-ancestors prevents DeltaCrown from being embedded in phishing site
- User education: FAQ warns "Never enter passwords in embedded players, visit platform directly"

### Risk 3.3: Stream Embed Clickjacking
**Description:** Attacker overlays invisible iframe on "Save Settings" button, user thinks they're saving profile settings, actually clicking "Follow" on attacker's Twitch channel.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Iframe sandbox: `sandbox="allow-scripts allow-same-origin"` blocks top-level navigation (cannot hijack clicks outside iframe)
- Z-index isolation: Embed iframe has fixed z-index, UI buttons have higher z-index (cannot overlap)
- Pointer-events CSS: Critical buttons have `pointer-events: auto` with overlay protection
- Frame-ancestors: Embed platforms set `X-Frame-Options: SAMEORIGIN` (prevents nesting in malicious iframe)
- Visual separation: Embed player in clearly bordered container, distinct from surrounding UI (user knows where iframe boundary is)

### Risk 3.4: Bandwidth Exhaustion (Autoplay All Streams)
**Description:** Malicious user sets autoplay=true on stream, profile visitors automatically load high-bitrate video stream, exhausts DeltaCrown bandwidth quota, CDN costs spike.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Autoplay disabled by default: `embed_settings.autoplay = false` hardcoded, user cannot override
- Lazy loading: Embed iframe has `loading="lazy"` attribute (only loads when scrolled into view)
- Visitor consent: "Click to play stream" overlay on embed player (requires user interaction before loading)
- Bandwidth monitoring: Alert if CDN bandwidth spikes 50% above baseline (indicates abuse or viral traffic)
- Embed throttling: Max 1 stream embed per profile (no multi-stream sidebar abuse)
- Platform bandwidth: Stream traffic goes through Twitch/YouTube CDN (not DeltaCrown servers), DeltaCrown only serves iframe HTML

### Risk 3.5: Stream Content Moderation Bypass
**Description:** User streams pornographic or violent content on Twitch, embeds stream on DeltaCrown profile before Twitch moderators take down stream, DeltaCrown displays ToS-violating content.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Platform trust: Rely on Twitch/YouTube content moderation (ToS violation results in account ban on their platform)
- User reporting: "Report inappropriate stream" button on embed player, alerts DeltaCrown moderators
- Rapid response: If stream reported, immediately disable user's stream embed privilege (revoke show_stream permission)
- Terms update: DeltaCrown ToS states "Embedded content subject to platform's community guidelines, violations result in embed removal"
- Proactive monitoring: Scheduled job checks if embedded Twitch channel is banned, auto-disables embed
- Age restrictions: Embed players inherit platform's age restrictions (YouTube age-gate, Twitch mature content filter)

### Risk 3.6: CSP Violation (Embed Domain Not Whitelisted)
**Description:** Admin adds new streaming platform (Trovo), forgets to update CSP frame-src directive, embed blocked by browser, users see blank iframe.

**Severity:** 🟡 **Low**

**Mitigation:**
- CSP config management: Store frame-src domains in Django settings: `STREAM_EMBED_DOMAINS = ['player.twitch.tv', 'www.youtube.com', ...]`
- Automated testing: Integration test loads profile with stream embed, asserts no CSP violation errors in console
- CSP reporting: `Content-Security-Policy-Report-Only` header logs violations to monitoring endpoint before enforcing
- Admin checklist: "Add platform to STREAM_EMBED_DOMAINS" step in platform integration guide
- Fallback handling: If embed blocked by CSP, show error message: "Stream embed blocked. Contact support."

### Risk 3.7: Embed Parameter Injection (Malicious Query Params)
**Description:** Attacker manipulates channel identifier to inject params: `ninja&autoplay=1&parent=evil.com`, embed URL becomes `https://player.twitch.tv/?channel=ninja&autoplay=1&parent=evil.com`, bypasses domain restriction.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Input validation: Channel identifier limited to alphanumeric + underscores (no `&`, `?`, `=`, `/`)
- Regex validation: `^[a-zA-Z0-9_]{3,25}$` for Twitch usernames (official format)
- URL encoding: Encode channel identifier before inserting: `urllib.parse.quote(channel_identifier)`
- Allowlist params: Only append whitelisted params: `channel`, `muted`, `autoplay` (ignore user-provided extras)
- Template construction: Use Django template tags with auto-escaping: `{% url 'twitch_embed' channel=channel_id %}`

### Risk 3.8: Third-Party Embed Script Injection
**Description:** Streaming platform's embed player loads third-party analytics scripts (Google Analytics, ad trackers), these scripts have XSS vulnerability, compromise DeltaCrown visitors.

**Severity:** 🟡 **Low**

**Mitigation:**
- Iframe isolation: Embed runs in sandboxed iframe, scripts cannot access parent window (origin isolation)
- CSP script-src: DeltaCrown's CSP restricts script sources, iframe scripts cannot load on main page
- No eval in iframe: Sandbox disables `eval()` and inline scripts in embedded content (if sandbox supports it)
- Platform trust: Twitch/YouTube responsible for securing their embed players (established platforms with security teams)
- Risk acceptance: Third-party script vulnerability is platform's responsibility, not DeltaCrown's (standard iframe embed risk)

### Risk 3.9: Stream Toggle Abuse (Spam Notifications)
**Description:** User enables "Show Stream" 50 times in one hour, each toggle triggers follower notification "[@username is now streaming!]", spams 10,000 followers with notifications.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Rate limiting: Max 5 stream toggles per hour (enforced at API level)
- Cooldown: 10-minute cooldown between notifications (even if user toggles, only one notification per 10 min)
- Notification deduplication: Track last notification timestamp, skip if < 10 minutes since previous
- Follower preference: Users can disable "streaming notifications" in their notification settings
- Temporary ban: If user exceeds rate limit 3+ times in one day, suspend stream embed feature for 24 hours
- Audit log: Track all stream toggle actions with user ID, timestamp, IP (detect abuse patterns)

### Risk 3.10: Embed Iframe Dimensions Exploit (Layout Breaking)
**Description:** Attacker sets embed dimensions to 10000x10000 pixels, profile layout breaks, page unscrollable, DOS attack on profile visibility.

**Severity:** 🟡 **Low**

**Mitigation:**
- Dimension limits: Embed iframe hardcoded to max 1280x720 (ignore user-provided dimensions)
- Responsive design: Iframe uses CSS percentage widths (max-width: 100%, height: auto), adapts to container
- Aspect ratio enforcement: CSS `aspect-ratio: 16/9` maintains proper proportions regardless of width
- Template control: Dimensions set in Django template, not user-configurable: `<iframe width="640" height="360">`
- Browser fallback: If dimensions exceed viewport, browser scrollbars appear (doesn't break layout)

### Risk 3.11: Platform API Key Exposure (Embed Params Leak Secrets)
**Description:** Twitch embed URL requires `parent` parameter set to DeltaCrown domain, attacker extracts this and uses for unauthorized embeds on malicious sites.

**Severity:** 🟡 **Low**

**Mitigation:**
- Public parameter: Twitch `parent` parameter is intentionally public (not a secret, designed for domain whitelisting)
- No secrets in URL: Never include API keys, OAuth tokens, or private identifiers in embed URL
- Domain restriction: Twitch validates `parent` domain server-side, rejects embeds from non-whitelisted domains
- No mitigation needed: This is expected behavior of Twitch embed API (public information)

### Risk 3.12: VOD Replay Manipulation (Inappropriate Past Content)
**Description:** User streams offensive content, Twitch bans stream, but VOD (recorded broadcast) still embeds on profile showing last stream, displays banned content.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Live-only embeds: Default to live stream embed (no VOD fallback), offline shows "Stream Offline" message
- VOD opt-in: User must explicitly enable "Show last VOD when offline" setting (disabled by default)
- Platform moderation: Twitch deletes VODs of banned streams (won't embed if deleted)
- Proactive check: If VOD embed returns 404 or banned error, hide embed and show "Stream unavailable"
- User reporting: "Report stream content" button remains visible even on VOD (admin can disable embed retroactively)

---

## 4. Risk Prioritization Matrix

**Critical (Address Before Launch):**
- 🔴 Risk 1.5: Hardware Catalog Injection (admin XSS)
- 🔴 Risk 3.1: Malicious Embed URL (XSS via iframe)
- 🔴 Risk 3.2: Phishing via Fake Stream Player

**High Priority (Address in MVP):**
- 🟠 Risk 1.4: Settings Visibility Privacy Leak
- 🟠 Risk 1.10: Affiliate Link Hijacking
- 🟠 Risk 2.1: Private Match Exposure
- 🟠 Risk 2.3: Opponent Scouting (stream sniping)
- 🟠 Risk 2.6: Database Load from Live Status Queries
- 🟠 Risk 3.3: Stream Embed Clickjacking
- 🟠 Risk 3.4: Bandwidth Exhaustion
- 🟠 Risk 3.5: Stream Content Moderation Bypass
- 🟠 Risk 3.7: Embed Parameter Injection
- 🟠 Risk 3.9: Stream Toggle Abuse
- 🟠 Risk 3.12: VOD Replay Manipulation

**Medium Priority (Address in Phase 2):**
- 🟡 Risk 1.1: Fake "Pro" Claims
- 🟡 Risk 1.2: Config Spam
- 🟡 Risk 1.3: Searchable Index Performance
- 🟡 Risk 1.6: Specs JSON Manipulation
- 🟡 Risk 1.7: Effective DPI Calculation Overflow
- 🟡 Risk 1.8: GameConfig JSON Bloat
- 🟡 Risk 1.9: Popular Settings Manipulation
- 🟡 Risk 2.2: Stale Live Status
- 🟡 Risk 2.4: Multiple Live Matches Race Condition
- 🟡 Risk 2.5: Match State Transition Timing
- 🟡 Risk 3.6: CSP Violation
- 🟡 Risk 3.8: Third-Party Embed Script Injection
- 🟡 Risk 3.10: Embed Iframe Dimensions Exploit
- 🟡 Risk 3.11: Platform API Key Exposure

---

## 5. Security Checklist (Pre-Launch)

**Loadout Security:**
- [ ] HardwareProduct.name validated (alphanumeric only, no HTML)
- [ ] Affiliate URLs whitelist enforced (Amazon, Logitech, Razer only)
- [ ] Specs JSON schema validation on save (realistic DPI/polling rate ranges)
- [ ] Privacy cascade: Loadout excluded from search if profile private
- [ ] Template escaping on all product fields (XSS prevention)
- [ ] Rate limiting: Max 5 loadout updates per game per day
- [ ] Admin two-factor authentication for product catalog access

**Live Status Security:**
- [ ] Query filters only public matches: `is_public=True`
- [ ] Cache TTL set to 1 minute (prevent stale status)
- [ ] Privacy setting: User can disable live status display
- [ ] Composite database index: `(state, participant1_id, participant2_id)`
- [ ] Team consent: Majority approval for team match live status (optional)

**Stream Embed Security:**
- [ ] URL scheme whitelist: Only `https://` allowed
- [ ] Domain whitelist: `player.twitch.tv`, `www.youtube.com`, `www.facebook.com`
- [ ] Channel identifier validation: `^[a-zA-Z0-9_]{3,25}$` regex
- [ ] CSP frame-src directive includes all embed domains
- [ ] Iframe sandbox: `allow-scripts allow-same-origin` (no navigation, no forms)
- [ ] Autoplay disabled by default: `autoplay=false` hardcoded
- [ ] Lazy loading: `<iframe loading="lazy">`
- [ ] Rate limiting: Max 5 stream toggles per hour
- [ ] Notification cooldown: 10 minutes between "now streaming" alerts
- [ ] Content reporting: "Report inappropriate stream" button functional
- [ ] Admin audit log: All stream toggle actions logged

**Operational Resilience:**
- [ ] Query caching for live status (1-minute TTL)
- [ ] Read replica for live status queries (offload primary DB)
- [ ] CSP violation reporting enabled (monitor embed domain issues)
- [ ] Affiliate link integrity check scheduled (weekly hash verification)
- [ ] Banned Twitch channel detection (daily job checks embed channels)
- [ ] Performance monitoring: Alert if loadout search queries exceed 5 seconds

---

**RISK REVIEW COMPLETE**

**Document Status:** ✅ Ready for Security Team Review  
**Next Steps:**
1. Schedule security review with backend and DevSecOps teams
2. Implement CSP headers with frame-src whitelist before stream embed goes live
3. Create admin workflow for hardware catalog management with input validation
4. Design stream embed moderation dashboard (reported streams, toggle abuse detection)
5. Test embed URL injection vectors (fuzzing with special characters)
6. Review streaming platform ToS for compliance (Twitch Developer Agreement, YouTube API Terms)
7. Conduct penetration testing on loadout search API (JSON injection, performance stress tests)

---

**END OF LOADOUT, LIVE STATUS & STREAM EMBED RISK REVIEW**
