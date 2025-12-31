# Highlights Embed Risk Review
**Date:** December 31, 2025  
**Reviewer:** Security Engineer  
**Type:** Risk Assessment & Mitigation Strategy  
**Scope:** Pinned Clip & Highlights Embed-Only Media System

---

## 1. URL VALIDATION & WHITELISTING RISKS

### Risk 1.1: Domain Whitelist Bypass (Subdomain Injection)
**Description:** Attacker registers malicious subdomain matching whitelist pattern (e.g., `youtube.com.evil.com` or `clips.twitch.tv.phishing.site`), validation logic checks if string contains `youtube.com` without verifying it's the actual domain, malicious URL passes validation.

**Severity:** 🔴 **High**

**Mitigation:**
- Exact domain matching: Parse URL with `urllib.parse.urlparse()`, validate `netloc` field exactly matches whitelist
- Regex validation: `^https://(www\.)?(youtube\.com|youtu\.be|twitch\.tv|clips\.twitch\.tv|medal\.tv)(/.*)?$`
- Reject subdomains: `evil.youtube.com` and `youtube.com.evil.com` both rejected (only exact domain match)
- Unit tests: Test cases for `https://youtube.com.phishing.site/watch?v=abc`, assert rejection
- Whitelist update procedure: New platforms require code review + security approval before adding

### Risk 1.2: Open Redirect via URL Parameter Injection
**Description:** User submits valid YouTube URL with redirect parameter: `https://youtube.com/watch?v=VIDEO_ID&redirect=https://evil.com`, embed construction includes malicious parameter, user clicks embed controls and gets redirected to phishing site.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Query parameter whitelist: Only preserve known-safe params (`v`, `t`, `start` for YouTube)
- Strip all other parameters before constructing embed URL: Use `urllib.parse.parse_qs()` to extract only `v` parameter
- Embed URL construction from scratch: Never append user-provided query string directly
- Example safe construction: `f"https://youtube.com/embed/{video_id}?autoplay=0"` (hardcoded params only)
- Test with injection attempts: `?v=ID&redirect=evil.com&javascript=alert(1)`, assert stripped

### Risk 1.3: Protocol Downgrade Attack (HTTP Embed)
**Description:** User submits `http://youtube.com/watch?v=ID` instead of `https://`, system accepts and embeds via HTTP, mixed content warnings, man-in-the-middle attack possible on embed traffic.

**Severity:** 🟠 **Medium**

**Mitigation:**
- HTTPS requirement: Validation rejects URLs not starting with `https://` (no `http://` allowed)
- Auto-upgrade: If user pastes HTTP URL, auto-convert to HTTPS before validation
- Error message: "Video URLs must use HTTPS for security. Please use https://"
- Embed construction: Always use `https://` in embed URL (even if extracted from HTTP source URL)
- Browser enforcement: Modern browsers block HTTP iframes on HTTPS pages (defense in depth)

### Risk 1.4: Video ID Extraction Regex Vulnerability
**Description:** Regex used to extract video ID from URL has catastrophic backtracking vulnerability (e.g., `(.*)*` pattern), attacker submits 10,000-character URL with repeated patterns, regex engine hangs, DOS attack on validation endpoint.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Input length limit: Reject URLs longer than 500 characters before regex processing
- Non-greedy regex: Use possessive quantifiers or atomic groups: `(?:...)++` instead of `(...)*`
- Timeout on regex: Wrap regex matching in timeout (e.g., 100ms limit), raise error if exceeded
- Alternative parsing: Use `urllib.parse` to extract query params instead of regex for YouTube (`parse_qs(url)['v'][0]`)
- Test with pathological input: `https://youtube.com/watch?v=` + "a"*10000, assert fast rejection

### Risk 1.5: Shortened URL Redirect Chain
**Description:** User submits bit.ly shortened URL pointing to valid YouTube link, system follows redirect chain, final URL is YouTube (passes validation), but intermediate redirects visit tracking/malware sites that log visitor IPs before final redirect.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Reject all shortened URLs: Validate domain is whitelisted BEFORE following any redirects
- No redirect following: System never calls `requests.get(url, allow_redirects=True)` on user-provided URL
- Error message: "Shortened URLs not supported. Please paste the full YouTube/Twitch URL"
- User education: FAQ explains "Copy URL from browser address bar after opening video"
- Whitelist only direct URLs: bit.ly, tinyurl.com, t.co all rejected at domain validation step

### Risk 1.6: Unicode Domain Homograph Attack (IDN Spoofing)
**Description:** Attacker registers IDN domain `youtubе.com` (Cyrillic 'е' instead of Latin 'e'), submits `https://youtubе.com/watch?v=ID`, visual inspection looks identical to `youtube.com`, passes basic string matching, embeds malicious site.

**Severity:** 🟠 **Medium**

**Mitigation:**
- ASCII-only domain validation: Reject URLs with non-ASCII characters in domain
- Punycode normalization: Convert IDN domains to punycode before whitelist check (e.g., `xn--youtu-5jf.com`)
- Character whitelist: Domain must match `[a-z0-9.-]+` (no Unicode, no special chars)
- Browser warning: Modern browsers show punycode in address bar (users see `xn--` prefix), but DeltaCrown shouldn't rely on this
- Unit test: Submit `https://youtubе.com` (Cyrillic), assert rejection

### Risk 1.7: Path Traversal in Video ID
**Description:** User submits URL with path traversal in video ID: `https://youtube.com/watch?v=../../../etc/passwd`, validation extracts ID as `../../../etc/passwd`, later file operations (if any) use this as filename, path traversal vulnerability.

**Severity:** 🟡 **Low** (mitigated by embed-only design)

**Mitigation:**
- Video ID character whitelist: Only allow `[a-zA-Z0-9_-]` (alphanumeric, underscore, hyphen)
- Reject path separators: `/`, `\`, `.`, `..` characters in video ID trigger validation error
- No filesystem operations: Video ID only used in URL construction (never as filename), but validate defensively
- Regex validation: `^[a-zA-Z0-9_-]{8,16}$` for YouTube IDs (11 chars), `^[a-zA-Z0-9_-]{10,50}$` for Medal.tv
- Database storage: Store video ID in VARCHAR field (no binary/blob that could interpret path chars)

### Risk 1.8: SQL Injection via Video ID (Defense in Depth)
**Description:** Video ID contains SQL keywords like `'; DROP TABLE highlights; --`, ORM fails to parameterize query, SQL injection executes.

**Severity:** 🟡 **Low** (Django ORM prevents this)

**Mitigation:**
- ORM-only queries: Never use raw SQL for clip operations (Django ORM parameterizes automatically)
- Character whitelist: Video ID validation rejects SQL keywords before database layer (defense in depth)
- Input sanitization: Strip quotes, semicolons, dashes from video ID during extraction
- Database user permissions: Application DB user lacks DROP TABLE privileges (even if injection succeeds)
- Monitoring: Log queries with unusual patterns (e.g., `DROP`, `DELETE FROM` in video_id field)

---

## 2. XSS & HTML INJECTION RISKS (TITLE/DESCRIPTION)

### Risk 2.1: Script Tag Injection in Clip Title
**Description:** User sets clip title to `<script>alert('XSS')</script>`, title rendered in profile HTML without escaping, all profile visitors execute malicious JavaScript.

**Severity:** 🔴 **High**

**Mitigation:**
- Template auto-escaping: Django templates escape by default: `{{ clip.title }}` renders `&lt;script&gt;`
- Never use `|safe` filter: Avoid marking user content as safe HTML
- Input sanitization: Strip all HTML tags from title on save: `bleach.clean(title, tags=[], strip=True)`
- Character blacklist: Reject titles containing `<`, `>`, `"`, `'` characters (alternative to stripping)
- CSP script-src: `Content-Security-Policy: script-src 'self'` blocks inline scripts (defense in depth)
- Output validation: Test that `<script>` in title renders as literal text, not executed

### Risk 2.2: Event Handler Injection in Description
**Description:** User sets description to `Click here<img src=x onerror="alert('XSS')">`, HTML img tag with onerror handler embeds malicious script, executes on profile view.

**Severity:** 🔴 **High**

**Mitigation:**
- HTML tag stripping: Use `bleach.clean(description, tags=['br'], strip=True)` (only allow `<br>` for line breaks)
- Attribute whitelist: If allowing tags (e.g., `<a>`), whitelist only safe attributes: `href` (no `onclick`, `onerror`, `onload`)
- Django auto-escaping: All dynamic content escaped unless explicitly marked safe
- Markdown alternative: Allow markdown syntax (links, bold), convert to safe HTML with markdown library
- Test injection vectors: `<img src=x onerror=alert(1)>`, `<svg/onload=alert(1)>`, `<iframe src=javascript:alert(1)>`, assert all stripped/escaped

### Risk 2.3: URL Injection in Description (Phishing Links)
**Description:** User includes phishing link in description: "Watch my other clips here: http://youtubе.com/fake-login" (homograph domain), visitors click, enter credentials on phishing site.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Linkification with validation: Auto-linkify URLs in description, but validate domains before making clickable
- External link warning: Links open with `target="_blank" rel="noopener noreferrer"` and show warning: "You are leaving DeltaCrown"
- Domain display: Show full URL in tooltip on hover (visitors see actual domain before clicking)
- User reporting: "Report malicious link" button on clips with URLs in description
- URL sanitization: Strip `javascript:`, `data:`, `file:` scheme URLs from description (only allow `http://`, `https://`)

### Risk 2.4: CSS Injection via Description Formatting
**Description:** User includes CSS in description: `<style>body { display: none; }</style>` or markdown with inline styles, breaks profile layout or hides content.

**Severity:** 🟡 **Low**

**Mitigation:**
- Strip `<style>` tags: `bleach.clean()` with empty `tags` list removes all HTML including style blocks
- No inline styles: If allowing HTML tags, strip `style` attribute from all tags
- CSP style-src: `Content-Security-Policy: style-src 'self'` blocks inline styles (defense in depth)
- Markdown parsing: If using markdown, render to safe HTML without style support (disable raw HTML in markdown parser)

### Risk 2.5: Prototype Pollution via JSON Metadata
**Description:** If clip metadata stored/rendered as JSON, attacker injects `{"__proto__": {"isAdmin": true}}` in title/description, JavaScript prototype pollution vulnerability.

**Severity:** 🟡 **Low** (Python backend not vulnerable)

**Mitigation:**
- Python JSON handling: Python's `json` module not vulnerable to prototype pollution (JavaScript-specific issue)
- Frontend JSON parsing: If rendering metadata in JavaScript, use `JSON.parse()` with reviver function to strip `__proto__`
- Avoid eval: Never use `eval()` or `new Function()` on user-provided metadata
- Type validation: Ensure metadata fields are strings (not objects) before parsing

### Risk 2.6: Template Injection (SSTI)
**Description:** If user input rendered in template without escaping, attacker injects template syntax: `{{ 7*7 }}` in title, server-side template injection executes arbitrary code.

**Severity:** 🔴 **High** (if vulnerable)

**Mitigation:**
- Use template auto-escaping: Django default escaping prevents SSTI (user input never interpreted as template code)
- Never render user input as template: Don't call `Template(user_input).render()` (use variables, not template strings)
- Avoid render_to_string with user context: If dynamically rendering templates, sanitize variable names
- Test injection: Submit `{{7*7}}` in title, assert renders as literal text "{{7*7}}", not "49"

### Risk 2.7: Newline/Whitespace Exploitation (Layout Breaking)
**Description:** User sets title to 1000 newlines or 10,000 spaces, profile layout breaks, scrolling issues, visual DOS attack.

**Severity:** 🟡 **Low**

**Mitigation:**
- Character limits: Title max 100 chars, description max 500 chars (enforced at model level)
- Whitespace normalization: Replace multiple consecutive spaces with single space: `re.sub(r'\s+', ' ', title)`
- Newline limits: Allow max 10 `<br>` tags in description (strip excess)
- CSS truncation: Profile template uses `text-overflow: ellipsis` and `max-height` for long text
- Validation: Reject titles/descriptions with more than 20% whitespace characters

---

## 3. IFRAME SANDBOX & CSP MISCONFIGURATION RISKS

### Risk 3.1: Missing Sandbox Attribute (Full Iframe Privileges)
**Description:** Iframe rendered without `sandbox` attribute, embedded YouTube player has full browser privileges, can navigate top window, submit forms, open popups, access cookies.

**Severity:** 🔴 **High**

**Mitigation:**
- Mandatory sandbox: All embed iframes include `sandbox="allow-scripts allow-same-origin"` attribute
- Template enforcement: Create reusable template tag/component that always includes sandbox
- Automated testing: Selenium/Playwright test loads profile, asserts all iframes have sandbox attribute
- Allowlist minimal permissions: Only enable `allow-scripts` (video playback) and `allow-same-origin` (API calls)
- Explicitly deny: No `allow-top-navigation`, `allow-forms`, `allow-popups`, `allow-pointer-lock`

### Risk 3.2: Overly Permissive Sandbox (allow-top-navigation)
**Description:** Developer adds `allow-top-navigation` to sandbox for convenience, embedded video can hijack browser with `window.top.location = "https://evil.com"`, full-page redirect to phishing site.

**Severity:** 🔴 **High**

**Mitigation:**
- Sandbox policy review: Document which permissions required for video playback, prohibit all others
- Code review: PR checklist item "Iframe sandbox does not include allow-top-navigation"
- Linting rule: Static analysis checks for `allow-top-navigation` in iframe tags, fails CI build
- User-initiated navigation only: Use `allow-top-navigation-by-user-activation` if top navigation needed (requires user click)
- Alternative: Use `allow-popups-to-escape-sandbox` if external navigation required (opens new tab instead of hijacking current)

### Risk 3.3: CSP frame-src Wildcard (`frame-src *`)
**Description:** CSP header set to `frame-src *` or `frame-src https://*`, allows any domain to load in iframes, negates URL validation, attacker embeds malicious site via different attack vector.

**Severity:** 🔴 **High**

**Mitigation:**
- Explicit frame-src whitelist: `Content-Security-Policy: frame-src https://youtube.com https://www.youtube.com https://clips.twitch.tv https://medal.tv`
- No wildcards: Never use `*` or `https://*` in frame-src (defeats CSP purpose)
- Subdomain restriction: `https://youtube.com` does NOT match `https://evil.youtube.com` (CSP is strict)
- CSP reporting: Use `frame-src ... ; report-uri /csp-report` to log violations (detects bypass attempts)
- Automated testing: Load profile with various embed URLs, check browser console for CSP violations

### Risk 3.4: Missing frame-ancestors Directive (Clickjacking)
**Description:** DeltaCrown profile can be embedded in malicious site's iframe, attacker overlays transparent DeltaCrown iframe over "Free Prize" button, user thinks they're clicking prize button, actually clicking "Delete Account" on DeltaCrown.

**Severity:** 🟠 **Medium**

**Mitigation:**
- frame-ancestors directive: `Content-Security-Policy: frame-ancestors 'none'` (DeltaCrown cannot be iframed)
- Alternative: `frame-ancestors 'self'` if iframing within DeltaCrown needed (e.g., admin panel)
- X-Frame-Options header: `X-Frame-Options: DENY` (older browser compatibility)
- Test clickjacking: Try embedding DeltaCrown in external iframe, assert browser blocks

### Risk 3.5: CSP script-src Allows Inline Scripts
**Description:** CSP set to `script-src 'self' 'unsafe-inline'`, XSS vulnerability in title/description exploited despite other protections, inline scripts execute.

**Severity:** 🟠 **Medium**

**Mitigation:**
- No unsafe-inline: `Content-Security-Policy: script-src 'self'` (no inline scripts allowed)
- Nonce-based CSP: If inline scripts needed, use nonce: `script-src 'self' 'nonce-{RANDOM}'`, attach nonce to trusted scripts
- Hash-based CSP: Allow specific inline scripts via hash: `script-src 'self' 'sha256-{HASH}'`
- External scripts only: Move all JavaScript to external .js files served from `/static/`
- Template review: Ensure no `<script>` tags in Django templates (use separate JS files)

### Risk 3.6: Mixed Content via HTTP Iframe
**Description:** Embed URL constructed with `http://` instead of `https://`, browser blocks mixed content (HTTPS page loading HTTP iframe), embed doesn't load, but security warning shown.

**Severity:** 🟡 **Low** (user experience issue, not vulnerability)

**Mitigation:**
- HTTPS enforcement: All embed URLs use `https://` scheme (hardcoded in URL construction)
- Browser automatic upgrade: Modern browsers auto-upgrade HTTP to HTTPS (but don't rely on this)
- CSP upgrade-insecure-requests: `Content-Security-Policy: upgrade-insecure-requests` forces HTTP→HTTPS
- Validation: Unit test asserts embed URLs start with `https://`

### Risk 3.7: Iframe Referrer Leak
**Description:** Embedded YouTube player receives full referrer URL (e.g., `https://deltacrown.com/@username`), YouTube analytics track which DeltaCrown profiles viewed video, privacy concern for profile visitors.

**Severity:** 🟡 **Low** (informational, not high-impact)

**Mitigation:**
- Referrer policy: `<iframe referrerpolicy="no-referrer">` or `referrerpolicy="origin"` (send only domain, not full path)
- Privacy-conscious default: Use `no-referrer` to avoid leaking profile username to platforms
- User transparency: FAQ explains "Embedded videos may log your view on the platform (YouTube, Twitch)"
- Alternative: Use `origin-when-cross-origin` (send full referrer to same-origin, only origin to cross-origin)

---

## 4. ABUSIVE CONTENT & MODERATION RISKS

### Risk 4.1: Embedding Extremist/Hateful Content
**Description:** User embeds YouTube video with extremist propaganda, racist speech, or violent content, DeltaCrown profile displays this content, platform liability for hosting hate speech.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Platform trust: Rely on YouTube/Twitch content moderation (videos violating their ToS get removed)
- User reporting: "Report inappropriate content" button on each clip, sends to DeltaCrown moderation queue
- Reactive moderation: Moderators review reported clips, delete from DeltaCrown (doesn't delete from YouTube, just removes embed)
- Disable user embed privilege: If user repeatedly embeds offensive content, revoke highlights feature
- Terms of Service: DeltaCrown ToS states "Embedded content must comply with platform's community guidelines and DeltaCrown's ToS"
- Automated flagging: If YouTube video is age-restricted or has content warning, show warning badge on DeltaCrown embed

### Risk 4.2: Copyright Infringement (DMCA Takedowns)
**Description:** User embeds copyrighted content (e.g., music video, movie clip) on profile, copyright holder sends DMCA takedown to DeltaCrown, legal compliance burden.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Platform responsibility: YouTube handles DMCA for videos hosted there, if video removed from YouTube, embed shows "Video Unavailable"
- DMCA policy page: DeltaCrown has DMCA agent registered, takedown requests forwarded to platform (not DeltaCrown's content)
- Safe harbor protection: DeltaCrown is content aggregator/linker (not host), safe harbor under DMCA 512(d) (information location tools)
- User agreement: Terms state "User responsible for ensuring embedded content does not violate copyright"
- Repeat infringer policy: User with 3+ DMCA complaints has highlights feature disabled

### Risk 4.3: Misleading/Fraudulent Clips (Fake Achievements)
**Description:** User embeds someone else's tournament win clip, claims it as their own achievement, misleads scouts/sponsors/teams into thinking user is more skilled than reality.

**Severity:** 🟡 **Low** (platform trust issue, not security vulnerability)

**Mitigation:**
- Community verification: Team members/opponents can report "This clip doesn't feature this user"
- Clip watermarks: Some platforms (Medal.tv) embed username in video, helps verify ownership
- Manual review: Moderators check reported clips, compare in-game username to profile username
- Account linking: Future feature to verify clips via game account integration (Riot API, Steam API)
- Reputation penalty: Users caught embedding fake clips lose reputation points, flagged in profile
- Transparency: Show original video uploader name (if available from platform metadata) next to embed

### Risk 4.4: Spam Clip Reordering (API Abuse)
**Description:** Attacker scripts 10,000 reorder requests per minute, changes clip positions rapidly, overwhelms database, DOS attack on reorder endpoint.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Rate limiting: Max 10 reorder actions per minute per user (enforced at API endpoint)
- Authentication required: Reorder endpoint requires CSRF token + login session (prevents unauthenticated spam)
- Database transaction locking: Reorder operation locks user's clip set with `SELECT FOR UPDATE` (prevents concurrent reorder conflicts)
- Cloudflare rate limiting: WAF rules block IPs with excessive reorder requests (Layer 7 DOS protection)
- Monitoring: Alert if reorder endpoint receives 100+ requests/min from single user (indicates abuse)

### Risk 4.5: Profile Spam via Highlights Feed
**Description:** User creates 100 accounts, each adds max clips, floods "Recently Added Highlights" feed with spam content, crowds out legitimate users.

**Severity:** 🟡 **Low**

**Mitigation:**
- Account requirements: Highlights feature requires verified email + reputation 10+ (prevents throwaway accounts)
- Feed filtering: "Recently Added" feed only shows clips from users with activity (played matches, not just created account)
- Report button: Users can report spam profiles, moderators bulk-delete highlights from spam accounts
- Heuristic detection: Flag accounts that add 20 clips within 1 hour of account creation (suspicious pattern)
- CAPTCHA on clip add: If user adds 5+ clips in short time, require CAPTCHA before additional clips

### Risk 4.6: Harassment via Pinned Clip (Targeted Content)
**Description:** User pins clip that mocks or targets another user (e.g., video titled "Destroying @victim_username"), harassment via profile content.

**Severity:** 🟡 **Low**

**Mitigation:**
- User reporting: "Report harassment" option on clips mentioning other users
- Moderator review: If reported, moderator watches clip context, deletes if violates harassment policy
- Title moderation: Flag clips with "@username" mentions in title for manual review (potential targeted harassment)
- Block interaction: If User A blocks User B, User B's profile (including clips) hidden from User A
- Terms enforcement: Repeated harassment via clips results in permanent highlights feature revocation

---

## 5. PERFORMANCE & PAGE WEIGHT RISKS

### Risk 5.1: Highlights Grid with 20 Embeds (Slow Page Load)
**Description:** User adds max 20 clips, Highlights tab renders 20 iframes simultaneously, each iframe loads ~500KB assets, page weight 10MB+, mobile users timeout or exhaust data plan.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Lazy loading: Use `<iframe loading="lazy">` attribute, only load iframes when scrolled into view
- Thumbnail preview: Show video thumbnail + "Click to Play" overlay, load iframe only on click
- Pagination: Show 6 clips per page with "Load More" button (don't render all 20 at once)
- Embed on demand: Highlights grid shows static thumbnails, clicking opens modal with embed (single iframe at a time)
- Bandwidth warning: Show message "This profile has 20 clips (approx 8MB). Load anyway?" on mobile connections

### Risk 5.2: Autoplay All Clips (Bandwidth Exhaustion)
**Description:** If embeds set to autoplay, user visits profile, all 20 clips start playing simultaneously, 20 video streams consume 100+ Mbps, crashes browser, exhausts bandwidth.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Autoplay disabled: All embeds have `autoplay=0` parameter (user must click play)
- Single autoplay: Pinned clip on Overview can autoplay (muted), but Highlights grid never autoplays
- User consent: Autoplay only with user interaction (click thumbnail), respects browser autoplay policies
- Mobile detection: Disable autoplay entirely on mobile devices (save data)
- Volume muted: If autoplay enabled, always muted by default (`muted=1` parameter)

### Risk 5.3: Thumbnail Hotlinking (External Bandwidth)
**Description:** Profile displays 20 video thumbnails hotlinked from YouTube (`img.youtube.com`), YouTube rate-limits or blocks hotlinking, thumbnails break, profile shows broken images.

**Severity:** 🟡 **Low**

**Mitigation:**
- Thumbnail caching: Fetch thumbnail once on clip creation, store in DeltaCrown CDN (Cloudflare/S3)
- Graceful degradation: If thumbnail 404, show platform logo placeholder (YouTube/Twitch icon)
- Lazy image loading: Use `loading="lazy"` on thumbnail images (don't load all 20 thumbnails at once)
- Hotlink fallback: If cached thumbnail expires, fallback to hotlink from platform (accept occasional failures)
- Platform API: Use official thumbnail endpoints (less likely to be rate-limited than hotlinking)

### Risk 5.4: Database Query Inefficiency (N+1 Queries)
**Description:** Profile loads 20 clips, each clip triggers separate query for platform metadata, 20+ database queries for single page load, slow response time.

**Severity:** 🟡 **Low**

**Mitigation:**
- Query optimization: Use `select_related()` or `prefetch_related()` to load clips in single query
- Eager loading: Fetch all 20 clips with metadata in one database call: `user.highlight_clips.select_related('user').all()`
- Caching: Cache clip collection for 5 minutes: `cache.get(f'clips:{user_id}')`, avoid DB queries for every page view
- Database indexing: Index on `(user_id, position)` for fast ordered retrieval
- Query monitoring: Use Django Debug Toolbar to detect N+1 queries, refactor before production

### Risk 5.5: Concurrent Embed Rendering (Browser Tab Limit)
**Description:** Browser limits concurrent iframe loads to 6-8, profile with 20 clips tries to load all at once, some iframes stall indefinitely waiting for previous loads to complete.

**Severity:** 🟡 **Low**

**Mitigation:**
- Progressive loading: Load first 6 clips immediately, remaining clips load as user scrolls (lazy loading)
- Thumbnail grid: Don't embed iframes in grid, show thumbnails, embed only when clicked
- Browser limits respected: Lazy loading naturally respects browser concurrency limits (loads as previous complete)
- User experience: Even if stalling occurs, eventually all embeds load (patience required, but not broken)

### Risk 5.6: Infinite Scroll / Memory Leak
**Description:** If Highlights tab uses infinite scroll (load more clips on scroll down), user scrolls through 100+ clips, browser memory exhausted by accumulated iframes, browser crashes.

**Severity:** 🟡 **Low**

**Mitigation:**
- Pagination instead: Use "Load More" button (explicit user action), not infinite scroll
- Clip limit: Max 20 clips per user (prevents accumulation issue)
- Unload off-screen iframes: As user scrolls down, remove iframes that scrolled out of viewport (free memory)
- Virtual scrolling: Use library (e.g., react-virtualized) that only renders visible clips (infinite scroll without memory leak)

---

## 6. TWITCH "PARENT" PARAMETER & DOMAIN RISKS

### Risk 6.1: Missing Parent Parameter (Twitch Embed Blocked)
**Description:** Twitch Clips embed URL doesn't include `parent=deltacrown.com` parameter, Twitch API rejects embed, iframe shows "Embedding disabled" error, clips broken for all users.

**Severity:** 🔴 **High** (feature completely broken)

**Mitigation:**
- Hardcoded parent param: All Twitch embed URLs include `&parent={SITE_DOMAIN}` parameter
- Dynamic domain: Use `request.get_host()` to set parent param based on current domain (supports staging/prod)
- Unit test: Test Twitch embed URL construction, assert parent parameter present
- Integration test: Selenium test loads profile with Twitch clip, asserts video plays (not error message)
- Documentation: Twitch embed docs require parent param, developer onboarding checklist includes this

### Risk 6.2: Wrong Parent Domain (Localhost/Staging)
**Description:** Production site uses `parent=localhost` in Twitch embeds (copy-paste from dev environment), Twitch rejects embeds on production domain, clips broken on deltacrown.com.

**Severity:** 🔴 **High**

**Mitigation:**
- Environment-based config: Parent param set via Django settings: `TWITCH_PARENT_DOMAIN = os.getenv('SITE_DOMAIN', 'deltacrown.com')`
- Multi-domain support: Include all domains in parent: `&parent=deltacrown.com&parent=staging.deltacrown.com&parent=localhost`
- Deployment checklist: Verify `SITE_DOMAIN` env var set correctly before deploying
- Monitoring: Alert if Twitch embeds return 403 errors (indicates parent mismatch)
- User-facing error: If embed fails, show message "Twitch clip unavailable. Try viewing on Twitch.tv"

### Risk 6.3: Parent Domain Spoofing (Unauthorized Embed)
**Description:** Attacker discovers DeltaCrown's Twitch embed URLs include `parent=deltacrown.com`, copies URL to malicious site, sets fake referrer header to spoof `deltacrown.com`, embeds DeltaCrown users' clips without permission.

**Severity:** 🟡 **Low** (Twitch handles this)

**Mitigation:**
- Twitch server-side validation: Twitch validates parent param against actual HTTP referer header (cannot be spoofed by client)
- Browser enforcement: Referer header set by browser (attacker cannot forge to bypass Twitch validation)
- No DeltaCrown action needed: Twitch API handles parent validation, not DeltaCrown's responsibility
- Acceptable risk: If attacker embeds DeltaCrown user's clips elsewhere, original clip on Twitch gets views (not harmful)

### Risk 6.4: Multiple Parent Domains (CDN/Proxy)
**Description:** DeltaCrown uses CDN (Cloudflare) or reverse proxy, Twitch sees requests from `cdn.deltacrown.com` instead of `deltacrown.com`, parent parameter mismatch, embeds blocked.

**Severity:** 🟠 **Medium**

**Mitigation:**
- Include all domains: `&parent=deltacrown.com&parent=cdn.deltacrown.com&parent=www.deltacrown.com`
- Wildcard parent (if supported): Check if Twitch allows `parent=*.deltacrown.com` (likely not supported)
- Proxy configuration: Ensure reverse proxy forwards original `Host` header (so Twitch sees actual domain)
- Testing: Test embeds from all possible domains (naked domain, www subdomain, CDN subdomain)
- Twitch documentation: Review parent param rules for CDN/proxy scenarios

### Risk 6.5: Parent Parameter Injection
**Description:** Attacker submits Twitch clip URL with malicious parent param: `https://clips.twitch.tv/SLUG?parent=evil.com`, DeltaCrown extracts and uses this param, allows unauthorized embedding.

**Severity:** 🟡 **Low**

**Mitigation:**
- Hardcoded parent: Never extract parent param from user-provided URL (always use `SITE_DOMAIN`)
- URL parsing: Extract only `CLIP_SLUG` from user URL, construct embed URL from scratch with trusted parent
- Validation: Reject URLs already containing `parent=` parameter (suspicious)
- Example safe construction: `f"https://clips.twitch.tv/embed?clip={validated_slug}&parent={SITE_DOMAIN}"`

### Risk 6.6: Twitch API Changes (Parent Param Deprecated)
**Description:** Twitch deprecates `parent` parameter in favor of new authentication method (OAuth, API key), all DeltaCrown embeds break overnight without warning.

**Severity:** 🟠 **Medium** (dependency risk)

**Mitigation:**
- Monitor Twitch developer blog: Subscribe to Twitch Developer announcements for API changes
- Version pinning: Use specific Twitch embed API version if available (avoid automatic breaking changes)
- Fallback to direct links: If embed fails, show "View on Twitch" button linking to `twitch.tv/clip/SLUG`
- Graceful degradation: If embed error detected, show thumbnail + link instead of broken iframe
- User notification: If widespread Twitch embed failure, show banner "Twitch clips temporarily unavailable"

### Risk 6.7: Parent Parameter Length Limit
**Description:** DeltaCrown adds 10 staging/preview domains to parent param, URL exceeds Twitch's parameter length limit, embed fails with 414 URL Too Long error.

**Severity:** 🟡 **Low**

**Mitigation:**
- Prioritize domains: Include only production + primary staging domain (max 2-3 parent params)
- URL length testing: Test embed URL with all parent params, ensure < 2000 characters (common limit)
- Dynamic selection: Include parent param based on current environment (only one domain per embed)
- Twitch documentation: Check if multiple parent params supported, or if only one allowed

---

## 7. Risk Prioritization Matrix

**Critical (Address Before Launch):**
- 🔴 Risk 1.1: Domain Whitelist Bypass (subdomain injection)
- 🔴 Risk 2.1: Script Tag Injection in Clip Title
- 🔴 Risk 2.2: Event Handler Injection in Description
- 🔴 Risk 2.6: Template Injection (SSTI)
- 🔴 Risk 3.1: Missing Iframe Sandbox Attribute
- 🔴 Risk 3.2: Overly Permissive Sandbox (allow-top-navigation)
- 🔴 Risk 3.3: CSP frame-src Wildcard
- 🔴 Risk 6.1: Missing Twitch Parent Parameter
- 🔴 Risk 6.2: Wrong Twitch Parent Domain

**High Priority (Address in MVP):**
- 🟠 Risk 1.2: Open Redirect via URL Parameter Injection
- 🟠 Risk 1.3: Protocol Downgrade Attack (HTTP embed)
- 🟠 Risk 1.4: Video ID Extraction Regex Vulnerability
- 🟠 Risk 1.5: Shortened URL Redirect Chain
- 🟠 Risk 1.6: Unicode Domain Homograph Attack
- 🟠 Risk 2.3: URL Injection in Description (phishing links)
- 🟠 Risk 3.4: Missing frame-ancestors Directive (clickjacking)
- 🟠 Risk 3.5: CSP script-src Allows Inline Scripts
- 🟠 Risk 4.1: Embedding Extremist/Hateful Content
- 🟠 Risk 4.2: Copyright Infringement (DMCA)
- 🟠 Risk 4.4: Spam Clip Reordering (API abuse)
- 🟠 Risk 5.1: Highlights Grid with 20 Embeds (page weight)
- 🟠 Risk 5.2: Autoplay All Clips (bandwidth exhaustion)
- 🟠 Risk 6.4: Multiple Parent Domains (CDN/proxy)
- 🟠 Risk 6.6: Twitch API Changes

**Medium Priority (Address in Phase 2):**
- 🟡 Risk 1.7: Path Traversal in Video ID
- 🟡 Risk 1.8: SQL Injection via Video ID
- 🟡 Risk 2.4: CSS Injection via Description
- 🟡 Risk 2.5: Prototype Pollution via JSON
- 🟡 Risk 2.7: Newline/Whitespace Exploitation
- 🟡 Risk 3.6: Mixed Content via HTTP Iframe
- 🟡 Risk 3.7: Iframe Referrer Leak
- 🟡 Risk 4.3: Misleading/Fraudulent Clips
- 🟡 Risk 4.5: Profile Spam via Highlights Feed
- 🟡 Risk 4.6: Harassment via Pinned Clip
- 🟡 Risk 5.3: Thumbnail Hotlinking
- 🟡 Risk 5.4: Database Query Inefficiency (N+1)
- 🟡 Risk 5.5: Concurrent Embed Rendering
- 🟡 Risk 5.6: Infinite Scroll Memory Leak
- 🟡 Risk 6.3: Parent Domain Spoofing
- 🟡 Risk 6.5: Parent Parameter Injection
- 🟡 Risk 6.7: Parent Parameter Length Limit

---

## 8. Security Checklist (Pre-Launch)

**URL Validation:**
- [ ] Domain whitelist enforced: `youtube.com`, `youtu.be`, `twitch.tv`, `clips.twitch.tv`, `medal.tv` only
- [ ] HTTPS requirement: URLs starting with `http://` rejected or auto-upgraded
- [ ] Video ID character whitelist: `[a-zA-Z0-9_-]` only (no path separators, SQL keywords)
- [ ] URL length limit: Max 500 characters before regex processing
- [ ] Query parameter sanitization: Only known-safe params preserved (`v`, `t` for YouTube)
- [ ] Shortened URLs rejected: bit.ly, tinyurl.com, t.co domains blocked
- [ ] Unicode domain detection: IDN domains converted to punycode before validation

**XSS Prevention:**
- [ ] Django template auto-escaping enabled (default setting)
- [ ] Title/description HTML tag stripping: `bleach.clean(text, tags=[], strip=True)`
- [ ] No `|safe` filter on user-provided content
- [ ] Character limits: Title 100 chars, description 500 chars (enforced at model level)
- [ ] Whitespace normalization: Multiple spaces/newlines collapsed to single

**Iframe Security:**
- [ ] Sandbox attribute on all iframes: `sandbox="allow-scripts allow-same-origin"`
- [ ] No `allow-top-navigation` or `allow-forms` in sandbox
- [ ] Autoplay disabled: `autoplay=0` parameter in all embed URLs
- [ ] Lazy loading: `<iframe loading="lazy">` attribute
- [ ] Referrer policy: `referrerpolicy="no-referrer"` or `origin` only

**CSP Configuration:**
- [ ] frame-src whitelist: `https://youtube.com https://www.youtube.com https://clips.twitch.tv https://medal.tv`
- [ ] No wildcards in frame-src: `*` or `https://*` rejected
- [ ] script-src: `'self'` only (no `unsafe-inline`, no `unsafe-eval`)
- [ ] frame-ancestors: `'none'` (prevent DeltaCrown being iframed)
- [ ] upgrade-insecure-requests: Force HTTP→HTTPS
- [ ] CSP reporting: `report-uri /csp-report` logs violations

**Twitch-Specific:**
- [ ] Parent parameter hardcoded: `parent={SITE_DOMAIN}` on all Twitch embeds
- [ ] Environment-based config: `SITE_DOMAIN` set correctly for staging/prod
- [ ] Multi-domain support: Include `www.deltacrown.com` and naked domain
- [ ] Integration test: Twitch clip plays successfully in profile

**Rate Limiting:**
- [ ] Clip creation: Max 5 clips per hour per user
- [ ] Clip reordering: Max 10 reorder actions per minute
- [ ] Pin/unpin: Max 20 pin changes per hour
- [ ] CAPTCHA after 5 rapid clip additions

**Content Moderation:**
- [ ] User reporting: "Report inappropriate content" button on each clip
- [ ] Moderation queue: Reported clips visible to admin with watch/delete actions
- [ ] Embed privilege revocation: Admins can disable user's highlights feature
- [ ] DMCA agent registered: Contact info on Terms page
- [ ] Repeat infringer policy: 3+ DMCA complaints = highlights disabled

**Performance:**
- [ ] Lazy iframe loading: Only load iframes in viewport
- [ ] Thumbnail preview: Grid shows thumbnails, embed on click (not auto-embed)
- [ ] Pagination: Show 6-10 clips per page (not all 20 at once)
- [ ] Query optimization: `select_related()` for clip fetching (no N+1 queries)
- [ ] Database indexing: Index on `(user_id, position)` for fast ordering

---

**RISK REVIEW COMPLETE**

**Document Status:** ✅ Ready for Security Team Review  
**Next Steps:**
1. Schedule security review with engineering and DevSecOps teams
2. Implement CSP headers with strict frame-src whitelist before embedding feature goes live
3. Create input validation test suite (fuzzing URL patterns, injection payloads)
4. Design content moderation workflow dashboard (reported clips, bulk actions)
5. Test Twitch parent parameter across all environments (localhost, staging, production)
6. Conduct penetration testing on embed system (XSS, SSTI, CSRF on reorder endpoint)
7. Review platform Terms of Service (YouTube, Twitch, Medal.tv embed policies)

---

**END OF HIGHLIGHTS EMBED RISK REVIEW**
