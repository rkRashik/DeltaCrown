# Pinned Clip & Highlights Design
**Date:** December 31, 2025  
**Architect:** Principal Backend Architect  
**Type:** Technical Design (No Implementation)  
**Scope:** Embed-Only Media Gallery System

---

## 1. System Intent (Zero-Cost Media Vault)

The Pinned Clip & Highlights system is a zero-storage, embed-only media gallery where competitive players showcase their best gameplay moments by linking to existing YouTube/Twitch/Medal.tv clips hosted on external platforms. Instead of building expensive video upload infrastructure (transcoding, CDN distribution, storage costs, content moderation pipelines), DeltaCrown functions as a curated showcase layer: users paste video URLs, the system validates and extracts embed codes, and renders iframe players on profiles. This approach eliminates hosting costs while leveraging platforms' existing content delivery networks, moderation systems, and playback optimization. The primary UX goal is credibility signaling: "Here are my best clutches, tournament wins, and highlight-reel plays" becomes a one-click embed experience, not a multi-gigabyte upload process. Profile visitors can watch clips inline without leaving DeltaCrown, and if a clip is taken down or made private on the source platform, it automatically shows as unavailable (no broken state management needed).

---

## 2. Backend UX Contract (Data Requirements)

**Overview Tab - Pinned Clip Section:**

- **Single Featured Clip**: User selects one "hero" clip to display prominently at top of profile overview
- **Embed Player**: Must render full-size iframe player (16:9 aspect ratio, 640x360 minimum, responsive scaling)
- **Metadata Display**: Clip title (user-provided or scraped from platform), upload date, view count (if available from embed)
- **Fallback State**: If no pinned clip set, show placeholder: "Add your best play to your profile"
- **Update Frequency**: User can change pinned clip anytime (no rate limit, instant update)
- **Priority Context**: This is the "first impression" content - profile visitors see it immediately, should showcase user's peak performance

**Highlights Tab - Media Gallery Grid:**

- **Multiple Clips**: User can save 10-20 clips in their highlights collection (configurable limit to prevent spam)
- **Grid Display**: 3-column grid layout on desktop, 1-column on mobile, each cell shows video thumbnail + metadata
- **Ordering Control**: User can reorder clips (drag-and-drop or up/down arrows), default order is most recent first
- **Thumbnail Preview**: Extract video thumbnail from platform (YouTube/Twitch provide thumbnail APIs), or fallback to platform logo
- **Click to Play**: Clicking grid cell opens modal with full-size embed player, or navigates to dedicated clip detail page
- **Clip Metadata**: Each clip needs: title (max 100 chars), description (optional, max 500 chars), added_at timestamp, view_count (if trackable)
- **Empty State**: If highlights tab has 0 clips, show: "Build your highlight reel by adding your best plays"

**Both Sections Share:**

- **Platform Agnostic**: Must support YouTube (youtube.com, youtu.be), Twitch clips (clips.twitch.tv), Medal.tv, Streamable, and optionally TikTok gaming clips
- **Real-Time Validation**: When user pastes URL, immediately validate format and extract video ID (prevent broken embeds)
- **Responsive Embeds**: All iframes must be responsive (scale to container width, maintain 16:9 aspect ratio)
- **Privacy Respect**: If source video is deleted/private, embed shows platform's "Video Unavailable" message (no need for DeltaCrown to track deletion)

---

## 3. Constraints & Boundaries

**No Video Hosting Infrastructure:**

- DeltaCrown NEVER receives video files (no upload endpoints, no multipart form data handling)
- No video processing: No transcoding, no resolution conversion, no format normalization
- No CDN costs: All video bandwidth served by YouTube/Twitch/Medal.tv, not DeltaCrown servers
- No storage costs: Database stores only URL strings (200 bytes per clip), not multi-GB video files

**URL-Only Input:**

- User workflow: Copy YouTube/Twitch URL → Paste into "Add Highlight" form → Submit
- Backend workflow: Validate URL format → Extract video ID → Store ID + platform type → Construct embed URL on render
- No scraping video files: Never download source video, even temporarily
- No re-hosting: Never mirror content to DeltaCrown servers (respects platform terms of service)

**Platform Dependency Acceptance:**

- If YouTube changes embed API, highlights break until DeltaCrown updates embed logic (acceptable risk)
- If user's clip gets DMCA'd or deleted, it disappears from profile (no backup, acceptable trade-off)
- If platform rate-limits embeds, some clips may not play (acceptable, users contact platform support)
- No guaranteed uptime: DeltaCrown relies on third-party platform availability

**Content Moderation Delegation:**

- DeltaCrown does NOT moderate video content (trust YouTube/Twitch moderation)
- If user embeds offensive clip: Report to DeltaCrown → Admin disables clip embed privilege → User's clips hidden
- No proactive content scanning: Only reactive moderation based on user reports
- Platform's age-restriction/NSFW flags respected (embed shows "Sign in to confirm age" if required)

**Metadata Limitations:**

- View counts may be stale (embed API provides snapshot, not real-time count)
- Video titles may be platform-provided (if user doesn't override), may not match user's intent
- No analytics: DeltaCrown cannot track "how many people watched this clip on my profile" (iframe sandbox limits tracking)
- Thumbnail images cached locally (optional optimization), but not required (can hotlink platform thumbnails)

**Supported Platforms (MVP):**

- **YouTube**: Standard videos + Shorts (both use youtube.com/embed/ API)
- **Twitch Clips**: clips.twitch.tv URLs (different from live streams, fixed content)
- **Medal.tv**: Gaming clip hosting popular with competitive players

**Not Supported (Out of Scope):**

- Vimeo (less common for gaming content, defer to Phase 2)
- Twitter/X videos (embed restrictions, platform instability)
- Instagram Reels (no public embed API)
- Direct video file uploads (.mp4/.mov/.avi) - explicitly prohibited
- Screen recordings from user's device - must be pre-uploaded to supported platform

---

## 4. Models Required

**Core Models:**

- **HighlightClip** - Individual video clip record (user, platform, video_id, url, title, description, position, added_at)
  - Responsibility: Store user's collection of highlight clips with ordering and metadata

- **UserProfile Extension** - Add pinned_clip field (FK to HighlightClip, nullable)
  - Responsibility: Track which single clip is featured on overview tab (if any)

**Models NOT Needed:**

- ❌ **PinnedClip** - Separate model unnecessary (just FK from UserProfile to HighlightClip)
- ❌ **VideoMetadata** - Embed URL construction and thumbnail extraction handled in service layer
- ❌ **PlatformConfig** - Platform detection logic lives in service/utility function, not separate model
- ❌ **ClipCategory** - No categorization needed (all highlights are gameplay clips)
- ❌ **ClipPlaylist** - No playlist grouping (just ordered list per user)

**Alternative Design Consideration:**

- Could add `is_pinned` boolean field to HighlightClip instead of UserProfile FK
- Trade-off: Simpler query (`clips.filter(is_pinned=True)`), but allows multiple pinned clips if validation fails
- Recommendation: Use FK approach (database enforces single pinned clip constraint)

---

## 5. Platform Embed Rules

**YouTube:**

- **URL Patterns to Recognize:**
  - Standard: `https://www.youtube.com/watch?v=VIDEO_ID`
  - Short: `https://youtu.be/VIDEO_ID`
  - Shorts: `https://www.youtube.com/shorts/VIDEO_ID`
  - Mobile: `https://m.youtube.com/watch?v=VIDEO_ID`
- **Video ID Extraction:**
  - Standard/mobile: Extract from `v=` query parameter (11-character alphanumeric)
  - Short URLs: Extract from path after `youtu.be/`
  - Shorts: Extract from path after `/shorts/`
- **Embed URL Construction:**
  - Format: `https://www.youtube.com/embed/{VIDEO_ID}`
  - Parameters: `?autoplay=0&muted=1&rel=0` (disable autoplay, mute by default, hide related videos)
  - Works for both standard videos and Shorts (YouTube API handles both)
- **Thumbnail Extraction:**
  - YouTube provides: `https://img.youtube.com/vi/{VIDEO_ID}/maxresdefault.jpg`
  - Fallback: `https://img.youtube.com/vi/{VIDEO_ID}/hqdefault.jpg` if maxres doesn't exist
- **Edge Cases:**
  - Playlist URLs: Extract `v=` parameter, ignore `list=` parameter (embed single video)
  - Timestamp URLs (`&t=30s`): Preserve timestamp in embed with `?start=30` parameter

**Twitch Clips:**

- **URL Patterns to Recognize:**
  - Clip URL: `https://clips.twitch.tv/CLIP_SLUG`
  - Alternate: `https://www.twitch.tv/{CHANNEL}/clip/CLIP_SLUG`
  - Mobile: `https://m.twitch.tv/{CHANNEL}/clip/CLIP_SLUG`
- **Clip Slug Extraction:**
  - Clip slug is alphanumeric + hyphens (e.g., `FunnyCleverCatGrammarKing`)
  - Extract from path after `/clip/` or directly from `clips.twitch.tv/`
- **Embed URL Construction:**
  - Format: `https://clips.twitch.tv/embed?clip={CLIP_SLUG}&parent=deltacrown.com`
  - Must include `parent` parameter (Twitch requires domain whitelist)
  - Parameters: `&autoplay=false&muted=true`
- **Thumbnail Extraction:**
  - Twitch Clips API provides thumbnail, but requires API call (optional optimization)
  - Fallback: Use generic Twitch logo placeholder (no free thumbnail endpoint)
- **NOT Supported (Clarification):**
  - Live stream embeds (`https://www.twitch.tv/{CHANNEL}` - only clips, not VODs or live)
  - Reason: Live streams covered by separate streaming feature, highlights are for fixed clips

**Medal.tv:**

- **URL Patterns to Recognize:**
  - Clip URL: `https://medal.tv/games/{GAME}/clips/{CLIP_ID}`
  - Short URL: `https://medal.tv/clip/{CLIP_ID}`
  - User clip: `https://medal.tv/users/{USERNAME}/clips/{CLIP_ID}`
- **Clip ID Extraction:**
  - Clip ID is alphanumeric string (8-12 characters)
  - Extract from path after `/clips/` or `/clip/`
- **Embed URL Construction:**
  - Format: `https://medal.tv/clip/{CLIP_ID}?embed=1`
  - Parameters: `&autoplay=0&muted=1&width=640&height=360`
  - Medal.tv automatically serves responsive iframe
- **Thumbnail Extraction:**
  - Medal.tv embeds include poster image by default (no separate thumbnail fetch needed)
  - Fallback: Medal.tv logo placeholder
- **Platform Notes:**
  - Very popular with competitive gamers (Valorant, CS2, Apex clips)
  - No parent domain restriction (easier than Twitch)

**TikTok Gaming Clips (Optional/Phase 2):**

- **URL Patterns to Recognize:**
  - Video URL: `https://www.tiktok.com/@username/video/VIDEO_ID`
  - Short URL: `https://vm.tiktok.com/SHORT_CODE`
- **Video ID Extraction:**
  - Extract numeric VIDEO_ID from `/video/` path
  - Short URLs require redirect resolution (follow 302 to get full URL)
- **Embed URL Construction:**
  - Format: `https://www.tiktok.com/embed/v2/{VIDEO_ID}`
  - Parameters: `?lang=en-US`
  - TikTok embed API less stable than YouTube/Twitch (may break)
- **Limitations:**
  - TikTok primarily mobile-first (embed may look awkward on desktop)
  - Age-restricted content requires sign-in (embed shows login wall)
  - Defer to Phase 2 unless user demand is high

---

## 6. URL Validation & Safety

**Pre-Save Validation:**

- Check URL is well-formed: Starts with `https://` (reject `http://`, `javascript:`, `data:`)
- Check domain whitelist: Must be `youtube.com`, `youtu.be`, `twitch.tv`, `medal.tv`, `tiktok.com` (exact match)
- Check video ID extracted successfully: If extraction fails, reject with error "Invalid video URL"
- Check video ID format: Alphanumeric + hyphens/underscores only (no special characters)

**Handling Unknown Platforms:**

- If URL domain not in whitelist: Show error "Platform not supported. Use YouTube, Twitch, or Medal.tv"
- Do NOT attempt to embed unknown domains (XSS risk)
- Do NOT use generic iframe embed (prevents malicious sites)
- Provide helpful message: "Upload your clip to YouTube/Twitch first, then add the link here"

**Handling Malformed URLs:**

- If video ID extraction fails: "Could not recognize video ID. Check URL format"
- If URL has extra parameters: Strip and validate (e.g., remove `&feature=share` from YouTube)
- If URL is shortened (bit.ly, tinyurl): Reject (user must provide full platform URL)
- Reason: Following shortened links risks redirect to malicious site

**Sandbox Iframe Attributes:**

- All embeds use: `<iframe sandbox="allow-scripts allow-same-origin">`
- Disallow: `allow-top-navigation` (prevent embed hijacking browser)
- Disallow: `allow-forms` (prevent phishing forms in embed)
- Disallow: `allow-popups` (prevent ad popups)
- Allow: `allow-scripts` (required for video playback)
- Allow: `allow-same-origin` (required for embed API communication)

**Content Security Policy:**

- CSP header allows iframe sources: `frame-src https://www.youtube.com https://clips.twitch.tv https://medal.tv`
- Blocks all other iframe sources at HTTP level (defense in depth)
- If new platform added, must update CSP whitelist

**User-Provided Metadata Sanitization:**

- Clip title input: Escape HTML entities (prevent `<script>` injection)
- Clip description: Strip all HTML tags except `<br>` for line breaks
- Max length enforcement: Title 100 chars, description 500 chars (prevent spam)

**Broken Embed Handling:**

- If embed fails to load (video deleted, private, copyright strike): Platform shows native error
- DeltaCrown does NOT validate video exists before saving (avoid API calls on every add)
- If user reports broken clip: Admin can delete or user can remove themselves
- No automatic cleanup of broken clips (would require periodic API polling, expensive)

---

## 7. Ordering Strategy

**Position-Based Ordering:**

- Each HighlightClip has `position` field (integer, default to max+1 on creation)
- Clips displayed in ascending position order: `clips.order_by('position')`
- New clips added to end of list (position = highest existing position + 1)

**Drag-and-Drop Reordering (User Workflow):**

- User drags clip from position 3 to position 1
- Frontend sends: "Move clip ID 123 to position 1"
- Backend updates: Clip 123 gets position 1, clips 1-2 increment positions by 1
- All positions recalculated to maintain sequence without gaps

**Bulk Position Update:**

- When moving clip, update multiple clips' positions in single transaction
- Lock user's clip set during update (prevent concurrent reorder conflicts)
- Recalculate positions 1, 2, 3, ... N to eliminate gaps
- Alternative: Allow gaps (positions 1, 5, 8, 12), simpler update logic

**Up/Down Arrows (Alternative to Drag-Drop):**

- "Move Up" button: Swap position with clip above (position - 1)
- "Move Down" button: Swap position with clip below (position + 1)
- Simpler implementation, less intuitive UX than drag-drop
- Recommendation: Support both (drag-drop for desktop, arrows for mobile)

**Default Sort:**

- If user never reorders: Newest clips appear first (position = created_at descending)
- Option to reset order: "Sort by newest" button recalculates positions based on added_at

---

## 8. Pin/Unpin Rules

**Single Pinned Clip Constraint:**

- Only ONE clip can be pinned at a time (enforced by UserProfile.pinned_clip FK)
- When user pins clip B while clip A already pinned: Unpin A, pin B (single transaction)
- Database enforces uniqueness (only one FK value per user)

**Pin Workflow:**

- User clicks "Pin to Overview" on clip in Highlights tab
- Backend: `user.profile.pinned_clip = selected_clip; user.profile.save()`
- Previous pinned clip automatically unpinned (FK overwritten)
- No separate "unpin" action needed when changing pin (implicit)

**Unpin Workflow:**

- User clicks "Unpin" on Overview pinned clip
- Backend: `user.profile.pinned_clip = None; user.profile.save()`
- Overview shows placeholder: "Add your best play to your profile"

**Pin from Highlights Tab:**

- Highlights grid shows "Pinned" badge on currently pinned clip (if any)
- Click "Pin" on different clip: Instant swap, old pin badge moves
- Pin action does NOT reorder clips in Highlights (pin status separate from position)

**Constraints:**

- Cannot pin clip that doesn't belong to user (permission check)
- Cannot pin deleted clip (integrity constraint handles this)
- Pinned clip remains in Highlights collection (not removed, just has special status)

**Auto-Unpin on Delete:**

- If user deletes pinned clip: `pinned_clip` FK set to NULL automatically (database ON DELETE SET NULL)
- Overview reverts to placeholder state
- No orphaned pin reference

---

## 9. Profile Context Variables

**For Overview Tab (public_v3.html):**

- `pinned_clip` (HighlightClip object or None):
  - If user has clip pinned: Full clip details (title, description, embed_url, platform, added_at)
  - If no pinned clip: None (template shows placeholder)
  - Includes: `embed_url` (pre-constructed iframe URL), `thumbnail_url`, `video_id`, `platform`

- `pinned_clip_embed` (string or None):
  - Fully-formed iframe HTML: `<iframe src="..." width="640" height="360" allowfullscreen>`
  - Or just embed URL if template constructs iframe: `https://youtube.com/embed/VIDEO_ID`
  - Includes sandbox attributes and CSP-compliant source

**For Highlights Tab (highlights.html):**

- `highlight_clips` (QuerySet):
  - All user's clips ordered by position: `user.highlight_clips.order_by('position')`
  - Includes: id, title, description, thumbnail_url, embed_url, platform, position, added_at
  - Limit: Max 20 clips (enforced at creation, query doesn't need filter)

- `can_add_more_clips` (bool):
  - True if `highlight_clips.count() < 20` (max limit)
  - False if at limit (disable "Add Clip" button)
  - Prevents spam and database bloat

- `pinned_clip_id` (int or None):
  - ID of currently pinned clip (for showing "Pinned" badge in grid)
  - Used in template: `{% if clip.id == pinned_clip_id %}<span>Pinned</span>{% endif %}`

**For Clip Detail Modal/Page:**

- `clip` (HighlightClip object):
  - Full details for single clip (if modal or dedicated page)
  - Includes: title, description, embed_url, platform, added_at, is_pinned

- `is_owner` (bool):
  - True if current viewer is clip owner (show edit/delete/pin buttons)
  - False if visitor (show only watch button)

**For Add/Edit Clip Form:**

- `form_data` (dict):
  - Pre-filled if editing: existing title, description, url
  - Empty if adding new: placeholder text prompts

- `platform_detected` (string or None):
  - After URL validation: "YouTube", "Twitch", "Medal.tv"
  - Shows user: "✓ Platform detected: YouTube"

- `thumbnail_preview` (string or None):
  - Thumbnail URL extracted from video ID (shown in form preview)
  - Updates live as user pastes URL

---

## 10. Abuse & Security Controls

**URL Whitelisting (Already Covered in Section 6):**

- Only `youtube.com`, `youtu.be`, `twitch.tv`, `clips.twitch.tv`, `medal.tv` domains allowed
- Reject all other domains at validation layer (before saving to database)
- CSP enforces at HTTP layer: `frame-src` directive limits embed sources

**Rate Limiting:**

- **Clip Creation**: Max 5 clips added per hour per user (prevents spam)
- **Clip Deletion**: No limit (user can remove own content freely)
- **Reordering**: Max 10 reorder actions per minute (prevents API abuse via automation)
- **Pin/Unpin**: Max 20 pin changes per hour (prevents toggle spam)

**Per-User Limits:**

- Max 20 clips total per user (prevents database bloat)
- Max 100 character title (prevents layout break)
- Max 500 character description (prevents wall of text)
- No limit on clip views (passive action, not abuse vector)

**XSS Prevention:**

- **User Input Sanitization**:
  - Title: Escape all HTML entities (`<` → `&lt;`, `>` → `&gt;`)
  - Description: Strip all HTML tags except `<br>` (or allow markdown, sanitize output)
  - URL: Validate against whitelist, never render raw in HTML attribute
  
- **Iframe Sandboxing**:
  - All embeds use `sandbox` attribute: `<iframe sandbox="allow-scripts allow-same-origin">`
  - Prevents: top-level navigation, form submission, popups, pointer lock
  - Allows: video playback, API calls within iframe
  
- **CSP Headers**:
  - `frame-src` directive: Only whitelisted domains can load in iframes
  - `script-src` directive: Only DeltaCrown scripts execute (no inline scripts from embeds)
  - `style-src` directive: Prevent CSS injection attacks

**CSRF Protection:**

- All clip creation/edit/delete/reorder actions require CSRF token
- Django middleware validates token on POST requests
- Prevents: Malicious site tricking user into adding clips

**SQL Injection Prevention:**

- Django ORM handles parameterization (no raw SQL for clip operations)
- Video ID validation: Alphanumeric + hyphens only (reject SQL keywords)
- Position field: Integer type enforced at model level

**Content Moderation:**

- User can report clip: "Report Inappropriate Content" button on each clip
- Admin reviews report: View embed, check if violates terms
- Moderator actions: Delete clip, disable user's highlights feature, ban user
- No automated content scanning (trust platform's moderation, reactive approach)

**Embed Tampering Prevention:**

- Embed URLs constructed server-side (user never provides full embed URL)
- User provides source URL → Backend extracts ID → Backend constructs embed URL
- Prevents: User injecting malicious parameters or different video ID

**Deleted Account Cleanup:**

- On user account deletion: Cascade delete all HighlightClips (database ON DELETE CASCADE)
- Unpins pinned clip automatically (FK set to NULL)
- No orphaned clips remain in database

---

## 11. Implementation Priority

**Phase 1 (MVP - Week 1-2):**
- HighlightClip model with position field
- UserProfile.pinned_clip FK
- YouTube embed support only (most common platform)
- Basic add/delete clip functionality
- Pin/unpin from Highlights tab
- Overview pinned clip display

**Phase 2 (Enhancement - Week 2-3):**
- Twitch Clips embed support
- Medal.tv embed support
- Drag-and-drop reordering (or up/down arrows)
- Thumbnail preview in add form
- Clip detail modal (instead of inline embed)

**Phase 3 (Polish - Week 4+):**
- TikTok embed support (if user demand exists)
- Bulk delete clips (select multiple, delete all)
- Clip categories/tags (Tournament, Practice, Funny Moments)
- Clip statistics (views, if trackable via platform API)
- Export clip collection as JSON (backup feature)

---

## 12. Open Questions & Design Decisions

**Question 1: Should clips auto-embed or require click to play?**
- Option A: Embed visible immediately on page load (multiple iframes, heavy bandwidth)
- Option B: Show thumbnail, click to expand embed (lighter, better performance)
- **Recommendation**: Option B for Highlights grid, Option A for pinned clip

**Question 2: Should pinned clip be separate from Highlights collection?**
- Current design: Pinned clip is one of the Highlights (FK reference)
- Alternative: Pinned clip is separate record (can pin external clip not in Highlights)
- **Recommendation**: Keep current design (simpler, avoids duplicate storage)

**Question 3: Should users be able to add clips to other users' profiles?**
- Use case: Teammate wants to feature shared tournament win on both profiles
- Option A: Allow tagging/sharing (complex permissions)
- Option B: Each user manages own clips (simpler)
- **Recommendation**: Option B (user-owned content only), defer sharing to Phase 3

**Question 4: What if user pins clip then deletes it?**
- Already handled: FK with ON DELETE SET NULL unpins automatically
- Question: Should deletion require confirmation if clip is pinned?
- **Recommendation**: Yes, show warning: "This clip is pinned to your Overview. Delete anyway?"

**Question 5: Should there be a "Featured Clips" section separate from Highlights?**
- Current design: All clips in Highlights, one can be pinned to Overview
- Alternative: "Featured" collection (3-5 clips) separate from full Highlights
- **Recommendation**: Current design sufficient (pin = featured), avoid over-engineering

---

**DESIGN COMPLETE**

**Document Status:** ✅ Ready for Technical Review  
**Next Steps:**
1. Review embed URL formats with platform documentation (ensure CSP compliance)
2. Design thumbnail caching strategy (hotlink vs local cache)
3. Create clip management UI mockups (drag-drop, pin badge placement)
4. Define rate limit error messages (user-friendly, actionable)
5. Plan moderation workflow (report handling, bulk clip removal)
6. Test iframe sandbox restrictions (ensure video playback not broken)

---

**END OF PINNED CLIP & HIGHLIGHTS DESIGN**



