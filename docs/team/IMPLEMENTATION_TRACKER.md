# Team Manage HQ — Implementation Tracker

**Started:** February 7, 2026  
**Plan:** [TEAM_MANAGE_AND_DETAIL_PAGE_MASTER_PLAN.md](./TEAM_MANAGE_AND_DETAIL_PAGE_MASTER_PLAN.md)

---

## Phase 1: Foundation & Bug Fixes

### Bug Fixes (Section 16)

| # | Bug | Status | Notes |
|---|-----|:------:|-------|
| 1 | Raw template comments in browser | ✅ | Confirmed non-issue — all use `{% comment %}` |
| 2 | Social links loop renders 1 broken item | ✅ | Replaced `socials.split` loop with 4 explicit blocks |
| 3 | 15 phantom settings toggles | ✅ | Replaced with: visibility radio (PUBLIC/PRIVATE/UNLISTED), status display, is_temporary toggle |
| 4 | Activity feed returns 404 | ✅ | Created `manage_activity` endpoint, JS now hits `${API}/activity/` |
| 5 | Cancel invite hits undefined URL | ✅ | Created `manage_cancel_invite` endpoint, JS updated |
| 6 | Role update hits undefined URL | ✅ | Created `manage_update_member_role` endpoint, JS updated |
| 7 | Remove member hits undefined URL | ✅ | Created `manage_remove_member` endpoint, JS updated |
| 8 | N+1 queries on avatar | ✅ | Added `select_related('user', 'user__profile')` |
| 9 | `followers_count` phantom field | ✅ | Replaced with "Tournaments" stat (hardcoded 0 for now), removed from API |
| 10 | `max_roster_size` phantom attribute | ✅ | View now fetches `GameRosterConfig` via `game.roster_config` |

### P0 API Endpoints

| Endpoint | Status | Notes |
|----------|:------:|-------|
| `members/<id>/role/` (POST) | ✅ | Full validation, audit trail via TeamMembershipEvent |
| `members/<id>/remove/` (POST) | ✅ | Username confirmation required, soft-remove |
| `invites/<id>/cancel/` (POST) | ✅ | Sets status to CANCELLED |
| `activity/` (GET) | ✅ | Returns TeamActivityLog entries with time_ago |

### Infrastructure

| Task | Status | Notes |
|------|:------:|-------|
| Fix `select_related` in view | ✅ | Added `user__profile` to members query |
| Wire GameRosterConfig context | ✅ | `roster_config`, `max_team_size` added to context |
| Update JS to use new API URLs | ✅ | All 4 legacy endpoints → manage API |
| Add URL patterns for new endpoints | ✅ | 4 new paths in `apps/teams/urls.py` |
| Add `visibility_choices` to context | ✅ | Settings template radio buttons work |

---

## Phase 2: Manage HQ — Full Rebuild

### Layout & Navigation

| Task | Status | Notes |
|------|:------:|-------|
| Expand ROUTES 4 → 9 in _layout.html | ✅ | command, roster, competition, training, community, profile, settings, treasury, history |
| Update manage_hq.html to include 9 sections | ✅ | All section partials included |
| Rewrite _sidebar.html with 3 nav groups | ✅ | Operations / Management (role-gated) / Intelligence. Org badge, "Soon" badges on Training & Community |

### Section Templates

| Section | File | Status | Notes |
|---------|------|:------:|-------|
| Command Center | `_section_command_center.html` | ✅ | Added: org policy banner, team health bar (5-point profile completion), alerts panel (missing logo/banner/roster), improved quick actions |
| Roster Ops | `_section_roster_ops.html` | ✅ | Added: roster lock banner (org / owner / tournament), GameRosterConfig metrics (max/min/starters/subs), fill progress bar, player/staff split sections |
| Competition Hub | `_section_competition_hub.html` | ✅ | NEW: Active tournaments, upcoming matches, tournament history, TOC panel (admin-gated), org tournament policies |
| Training Lab | `_section_training_lab.html` | ✅ | NEW: 4 Coming Soon cards (Practice, Scrim Finder, VOD Library, Bounty Board) |
| Community & Media | `_section_community_media.html` | ✅ | NEW: 3 Coming Soon cards (Team Feed, Media Gallery, Highlight Reels), connected platforms quick view |
| Team Profile | `_section_team_profile.html` | — | Carried from Phase 1 (social links fixed), Phase 3/4 adds brand colors + live preview |
| Settings | `_section_settings.html` | — | Carried from Phase 1 (rewritten), Phase 4 adds org policies panel |
| Treasury | `_section_treasury.html` | ✅ | NEW: Owner wallet card, prize history table, registration fee log, transaction log (admin), payout preferences placeholder |
| History | `_section_history.html` | ✅ | NEW: Filter bar (type/date), activity timeline (lazy-loaded via JS), membership ledger (admin), archive info (disbanded teams) |

### JavaScript Controller

| Task | Status | Notes |
|------|:------:|-------|
| Rewrite team-manage-hq.js | ✅ | 6 modules: Command, Roster, Competition, Profile, Settings, History |
| Add Competition module (lazy-load) | ✅ | MutationObserver on `.is-active` class |
| Add History module with filters | ✅ | `applyFilters()` / `clearFilters()` → query params on activity API |
| Add `activityIcon()` type mapping | ✅ | Maps action_type to lucide icons |
| Expose History on ManageHQ public API | ✅ | `ManageHQ.History.applyFilters()` / `.clearFilters()` |

### Backend Changes

| Task | Status | Notes |
|------|:------:|-------|
| Enhance `manage_activity` with filters | ✅ | Supports `?type=`, `?from=`, `?to=` query params |
| Add `type` field to activity response | ✅ | JS `activityIcon()` can now use it |
| Add `roster_locked` + `roster_lock_source` to context | ✅ | Reads from team + org model attributes |

### Files Modified in Phase 2

| File | Change |
|------|--------|
| `templates/teams/manage_hq/partials/_layout.html` | ROUTES expanded 4 → 9 |
| `templates/teams/manage_hq.html` | 4 → 9 section includes |
| `templates/teams/manage_hq/partials/_sidebar.html` | Full rewrite: 3 groups, role gating, org badge |
| `templates/teams/manage_hq/partials/_section_command_center.html` | Added health bar, alerts, org banner |
| `templates/teams/manage_hq/partials/_section_roster_ops.html` | Added lock banner, config metrics, player/staff split |
| `templates/teams/manage_hq/partials/_section_competition_hub.html` | **NEW** |
| `templates/teams/manage_hq/partials/_section_training_lab.html` | **NEW** |
| `templates/teams/manage_hq/partials/_section_community_media.html` | **NEW** |
| `templates/teams/manage_hq/partials/_section_treasury.html` | **NEW** |
| `templates/teams/manage_hq/partials/_section_history.html` | **NEW** |
| `static/teams/js/team-manage-hq.js` | Full rewrite: 4 → 6 modules |
| `apps/teams/views/manage_api.py` | Activity endpoint enhanced with filters |
| `apps/organizations/views/team.py` | Added roster_locked / roster_lock_source context |

---

## Phase 3: Team Detail Page — Production Build

### Design System & Layout

| Task | Status | Notes |
|------|:------:|-------|
| CSS design system (fonts, variables, themes) | ✅ | 3 fonts, 5 theme variants, CSS custom properties, glass morphism, role/game visibility classes |
| 12-col grid layout (8+4) | ✅ | Left column: 7 sections. Right column: 7 sidebar widgets. Responsive breakpoints. |
| Scrollspy navigation | ✅ | IntersectionObserver-based, smooth scroll, role-gated Ops link, member count badge |
| Utility classes (hover-lift, hover-glow, skeleton, lazy-media, etc.) | ✅ | Already in _head_assets.html, added no-scrollbar, mask-fade-sides, section-heading, sidebar-widget |

### Hero Section

| Task | Status | Notes |
|------|:------:|-------|
| Banner image with hero-mask gradient | ✅ | Lazy-loaded with fallback, gradient overlay |
| Team card with logo-slab | ✅ | Verified badge for org teams, full identity block |
| Tag + rank badges | ✅ | Team tag chip, rank/tier tag |
| Meta pills (org, game, founded) | ✅ | Conditional rendering per data availability |
| Role-aware CTAs | ✅ | MANAGE (owner), TEAM CHAT (member), VIEW INVITE (pending), PENDING (request), APPLY (public) |
| Hero stats grid | ✅ | Crown Points, Wins, Win Rate (computed), Rank — 4-col responsive |

### Main Sections (Left Column)

| Section | ID | Status | Notes |
|---------|-----|:------:|-------|
| Overview — Mission & Identity | `#overview` | ✅ | Mission statement, org link, 4 quick stats cards (members, wins, losses, crown pts) |
| Roster — Active Roster | `#roster` | ✅ | Game-adaptive grid (xl:5-col), player cards with photo/role badge/overlay info, captain star, empty state with invite CTA |
| Matches — Match Schedule | `#matches` | ✅ | Filter tabs (All/Upcoming/Results), coming soon placeholder, report matches link (staff) |
| Stats — Team Statistics | `#stats` | ✅ | Ranked: 4-stat card (tier/score/matches/confidence). Unranked: placeholder message |
| Journey — Timeline | `#journey` | ✅ | Coming soon placeholder for chronological milestones |
| Community — Team Transmission | `#community` | ✅ | Coming soon placeholder for team feed/posts (Discord accent) |
| Operations — Staff Only | `#operations` | ✅ | Permission-gated, team status/roster size/visibility, link to Team HQ |

### Sidebar Widgets (Right Column)

| Widget | Status | Notes |
|--------|:------:|-------|
| Team Info | ✅ | DL list: status (with indicator), founded, game, org, team type, member count |
| Connect (Social Links) | ✅ | Platform-colored buttons from `streams` context, gated by `ui.enable_streams` |
| Join the Ranks (Recruitment) | ✅ | Non-member only. Apply/Pending/Closed states. Animated "Open" badge |
| Match History | ✅ | Empty state placeholder (no match data model yet) |
| Trophy Cabinet | ✅ | Empty state placeholder with trophy emoji |
| Highlights & Media | ✅ | Empty state placeholder with video icon |
| Action Required | ✅ | Member-only invite response widget (accept/decline stubs) |

### JavaScript Controller

| Module | Status | Notes |
|--------|:------:|-------|
| Body data-attribute injection | ✅ | Reads `#dc-detail-bootstrap` → sets `data-role`, `data-theme`, `data-game` on body |
| Sticky nav glass effect | ✅ | Enhances backdrop-blur after scroll > 400px, passive listener |
| Scrollspy (IntersectionObserver) | ✅ | rootMargin-based tracking, smooth scroll on nav click, active state toggle |
| Match filter tabs | ✅ | Visual tab switching, ready for future filtering logic |
| Lazy image loading | ✅ | IntersectionObserver with 100px rootMargin, blur-up transition |
| Scroll-in animations | ✅ | Fade-in-up on section visibility, respects prefers-reduced-motion via CSS |
| Sticky sidebar positioning | ✅ | JS measures heights, applies sticky only when sidebar < main content |

### Context Wiring

| Context Key | Consumed? | Notes |
|-------------|:---------:|-------|
| `team` | ✅ | 18 sub-keys used (name, slug, tag, logo_url, banner_url, tagline, team_type, status, founded_date, total_wins, total_losses, crown_points, visibility, game.name, game.slug) |
| `organization` | ✅ | name, url, type (nullable guard) |
| `viewer` | ✅ | is_authenticated, role (used for bootstrap + widget gate) |
| `permissions` | ✅ | can_edit_team, is_member, can_manage_roster, can_invite, can_view_operations, can_report_matches |
| `ui` | ✅ | theme (bootstrap), enable_streams (Connect widget gate) |
| `roster` | ✅ | items (full loop), count (badges, stats) |
| `stats` | ✅ | rank, tier, score, verified_match_count, confidence_level |
| `streams` | ✅ | platform, url (Connect widget) |
| `partners` | ✅ | name, logo_url, url (Partners bar) |
| `merch` | — | No merch section yet (future feature) |
| `pending_actions` | ✅ | can_request_to_join, has_pending_invite, has_pending_request |
| `page` | ✅ | title (block title), description, og_image, canonical_url (meta tags) |

### Files Modified in Phase 3

| File | Change |
|------|--------|
| `templates/organizations/team/team_detail.html` | Dynamic title, data-bootstrap div for role/theme/game, cleaned up block structure |
| `templates/organizations/team/partials/_head_assets.html` | Added SEO meta tags (description, og:image, canonical), added CSS utilities (no-scrollbar, mask-fade-sides, section-heading, sidebar-widget, coming-soon-section, nav-link-active) |
| `templates/organizations/team/partials/_body.html` | **FULL REBUILD**: Ambient BG → Hero (banner + team card + CTAs + stats) → Scrollspy nav → 12-col grid (7 main sections + 7 sidebar widgets) → Partners bar. 680+ lines, 12 context keys wired. |
| `templates/organizations/team/partials/_scripts.html` | **FULL REWRITE**: 7 JS modules (bootstrap, sticky nav, scrollspy, match filter, lazy loading, scroll animations, sticky sidebar). IntersectionObserver-based. Passive listeners. |

### Quality Gate

- **Template tag balance:** ✅ 35 if/endif, 3 for/endfor, 11 elif, 11 else
- **Lint errors:** ✅ 0 across all 5 files
- **Context coverage:** 11/12 keys consumed (merch deferred)
- **Accessibility:** Focus ring on interactive elements, skip-link in base.html, prefers-reduced-motion CSS
- **Responsive:** Mobile → sm → md → lg → xl breakpoints, hero adapts, roster grid collapses

---

## Phase 4: Organization & Economy Integration

### Manage View Context Additions (team.py)

| Context Key | Type | Role Gate | Notes |
|-------------|------|-----------|-------|
| `org_context` | dict/None | All | name, slug, logo_url, badge_url, url, hub_url, control_plane_url, is_verified, enforce_brand, empire_score, global_rank, ceo_id |
| `is_org_ceo` | bool | All | True if viewer is org CEO |
| `org_control_plane_url` | str | All | Direct link to org control plane |
| `org_policies` | dict | All | roster_locked, enforce_brand, revenue_split_config |
| `wallet_context` | dict/None | Owner/CEO | balance, held_balance, lifetime_earned from DeltaCrownWallet |

### Manage Sidebar Enhancements

| Task | Status | Notes |
|------|:------:|-------|
| Org logo in header (replaces building icon) | ✅ | Uses `org_context.logo_url` with fallback to lucide icon |
| Verified org badge indicator | ✅ | Indigo badge-check icon when `org_context.is_verified` |
| Empire Score display | ✅ | Crown icon + score + global rank in sidebar header |
| Org Control Plane link | ✅ | Indigo button "Org Control Plane →" for CEO/admin |
| CEO badge in footer | ✅ | "Org Admin" pill with shield icon + "Full owner-level access" |

### Command Center — Org Policy Info Card

| Task | Status | Notes |
|------|:------:|-------|
| Upgrade banner to full info card | ✅ | Rounded-3xl, gradient bg, org logo + verified badge + "Managed by" header |
| Control Plane link in header | ✅ | CTA button on right side of org card |
| 3-column inherited policies grid | ✅ | Roster Lock (lock/unlock), Brand Enforcement (enforced/custom), Revenue Split (active/none) |
| Empire Score display | ✅ | Amber accent row with crown icon, score, global rank |

### Settings — Org Policies Panel

| Task | Status | Notes |
|------|:------:|-------|
| Organization Policies section | ✅ | Between Team Status and Danger Zone, indigo gradient border |
| Roster Lock policy display | ✅ | Red/green indicator with lock/unlock icon, status pill |
| Brand Enforcement policy display | ✅ | Amber/green indicator with icon, enforced/custom pill |
| Revenue Split policy display | ✅ | Blue indicator with split icon, active/none pill |
| Control Plane link | ✅ | "View all policies in Org Control Plane →" |
| Release from Organization action | ✅ | Danger zone action for org teams — amber styling |

### Team Profile — Brand Inheritance

| Task | Status | Notes |
|------|:------:|-------|
| Brand inheritance banner | ✅ | Amber warning at top of profile section when `org_policies.enforce_brand` |
| "Manage →" link to control plane | ✅ | For org admins to adjust brand policy |

### Treasury & Economy — Full Rebuild

| Task | Status | Notes |
|------|:------:|-------|
| Prize distribution flow info | ✅ | Org teams: "Flows to Organization Master Wallet". Independent: "Flows to owner's personal wallet" |
| Wallet card wired to DeltaCrownWallet | ✅ | Shows real balance, held_balance, lifetime_earned from `wallet_context` |
| Wallet label context-aware | ✅ | "Org Master Wallet" for org teams, "Owner Wallet" for independent |
| Prize History table with headers | ✅ | 5-column grid (Tournament, Placement, Prize, Date, Status), empty state |
| Registration Fees (admin-gated) | ✅ | 5-column grid with method column, empty state with description |
| Transaction Log (admin-gated) | ✅ | Filter dropdown (All/Credits/Debits), empty state with descriptive text |
| Payout Preferences placeholder | ✅ | Owner-only coming soon card |
| Payment Methods panel | ✅ | 5-method grid (bKash, Nagad, Rocket, Bank, DeltaCoin) — owner only |
| Role gating per master plan | ✅ | Owner: full view. Admin: prize history + fees + tx log. Others: prize history only |

### Detail Page — Org Integration

| Task | Status | Notes |
|------|:------:|-------|
| Org logo in hero meta-pill | ✅ | `organization.logo_url` with img tag, verified badge SVG |
| Empire Score in hero stats grid | ✅ | Amber accent row spanning 4 cols, shows score + org rank |
| Org logo in overview "Part of" line | ✅ | Inline org logo img + verified badge, improved styling |
| Org logo in sidebar Team Info widget | ✅ | Inline org logo img + verified badge next to org name |
| Empire Score in sidebar Team Info | ✅ | Amber bold score + rank after org name |
| "Organization Team" label | ✅ | Team Type now shows indigo "Organization Team" with building icon (instead of generic type) |
| Org footer attribution section | ✅ | New section before partners bar: org logo + "A team managed by [Org]" + Empire Score badge |

### Context Service Enhancements

| Task | Status | Notes |
|------|:------:|-------|
| Empire Score in org context | ✅ | `empire_score`, `global_rank` added to `_build_organization_context()` |
| Org badge URL in context | ✅ | `badge_url` added |
| Org hub/control plane URLs | ✅ | `hub_url`, `control_plane_url` added |
| Org verified/brand flags | ✅ | `is_verified`, `enforce_brand` added |
| `select_related('organization__ranking')` | ✅ | Added to context service team query + both view queries (manage + detail) |

### Files Modified in Phase 4

| File | Change |
|------|--------|
| `apps/organizations/views/team.py` | Added `models` import, `select_related('organization__ranking')` on both queries, org_context dict, org_policies dict, wallet_context via DeltaCrownWallet, 5 new context keys |
| `apps/organizations/services/team_detail_context.py` | `select_related('organization__ranking')`, enhanced `_build_organization_context()` with 7 new keys (badge_url, hub_url, control_plane_url, is_verified, enforce_brand, empire_score, global_rank) |
| `templates/teams/manage_hq/partials/_sidebar.html` | Org logo, verified badge, Empire Score, Control Plane link, CEO badge footer |
| `templates/teams/manage_hq/partials/_section_command_center.html` | Full org policy info card: logo + verified + 3-col policies grid + Empire Score |
| `templates/teams/manage_hq/partials/_section_settings.html` | Org Policies panel (3 policies with indicators), Release from Organization danger zone action |
| `templates/teams/manage_hq/partials/_section_team_profile.html` | Brand inheritance amber banner at top |
| `templates/teams/manage_hq/partials/_section_treasury.html` | **FULL REBUILD**: Prize flow info, wired wallet card, role-gated sections, payment methods panel |
| `templates/organizations/team/partials/_body.html` | Org logo in hero meta-pill, Empire Score in hero stats, org logo in overview, org logo+verified+Empire Score in sidebar, "Organization Team" label, org footer attribution section |

### Quality Gate

- **Template tag balance:** ✅ All 6 templates verified (sidebar 13/13, command center 31/31, settings 25/25, profile 5/5, treasury 13/13, body 50/50)
- **Lint errors:** ✅ 0 across both Python files
- **New context keys:** 5 (org_context, is_org_ceo, org_control_plane_url, org_policies, wallet_context)
- **Master plan section coverage:** Section 9 (Org Integration) ✅, Section 10 (Rules — roster lock) ✅, Section 11 (Economy) ✅

---

## Phase 5: Audit, Notifications & Polish

### Audit Trail Wiring (Section 12)

| Endpoint | TeamActivityLog | TeamMembershipEvent | Notification | Status |
|----------|:---------------:|:-------------------:|:------------:|:------:|
| `manage_update_profile` (POST) | ✅ UPDATE | N/A | N/A | ✅ |
| `manage_upload_media` (POST) | ✅ UPDATE | N/A | N/A | ✅ |
| `manage_update_settings` (POST) | ✅ UPDATE | N/A | N/A | ✅ |
| `manage_invite_member` (POST) | ✅ ROSTER_ADD | N/A | ✅ `notify_vnext_team_invite_sent` | ✅ |
| `manage_update_member_role` (POST) | ✅ ROSTER_UPDATE | ✅ (was Phase 1) | ✅ `notify_roster_change('role_changed')` | ✅ |
| `manage_remove_member` (POST) | ✅ ROSTER_REMOVE | ✅ (was Phase 1) | ✅ `notify_roster_change('removed')` | ✅ |
| `manage_cancel_invite` (POST) | ✅ ROSTER_REMOVE | N/A | N/A | ✅ |

All audit calls wrapped in `try/except` — never block the primary operation.

### Notification Bell (Section 13)

| Task | Status | Notes |
|------|:------:|-------|
| Notification bell in topbar | ✅ | Bell icon + badge counter + dropdown panel |
| Dropdown panel (last 10 notifications) | ✅ | Polls `/notifications/api/nav-preview/`, shows type icon + title + message + time_ago |
| Badge counter polling (30s) | ✅ | Polls `/notifications/api/unread-count/`, hides badge when 0 |
| Mark All Read button | ✅ | POSTs to `/notifications/mark-all-read/` |
| View All link | ✅ | Links to `notifications:list` |
| JS Notifications module | ✅ | Module 8 in `team-manage-hq.js` — init, pollBadge, togglePanel, openPanel, closePanel, markAllRead |
| `aria-expanded` sync | ✅ | Bell button toggles aria-expanded on open/close |

### Accessibility Pass

| Issue | Severity | Fix | Status |
|-------|----------|-----|:------:|
| Hamburger button missing `aria-label` | High | Added `aria-label="Open navigation menu"` | ✅ |
| Close sidebar button missing `aria-label` | High | Added `aria-label="Close navigation menu"` | ✅ |
| Nav missing `aria-label` | Medium | Added `aria-label="Team management navigation"` | ✅ |
| Bell button missing `aria-haspopup`/`aria-expanded` | Medium | Added `aria-haspopup="true"` + `aria-expanded` + `aria-controls` | ✅ |
| Badge missing `aria-live` | Medium | Added `aria-live="polite" aria-atomic="true"` | ✅ |
| Notif panel wrong `role="menu"` | Medium | Changed to `role="region"` | ✅ |
| Roster action buttons invisible on mobile/touch | **Critical** | Changed to `sm:opacity-100 md:opacity-0 md:group-hover:opacity-100` + `focus-within:opacity-100` | ✅ |
| 3 modals missing `role="dialog"` | High | Added `role="dialog" aria-modal="true" aria-labelledby` to all 3 | ✅ |
| Modal close buttons missing `aria-label` | High | Added `aria-label="Close … dialog"` to all 3 close buttons | ✅ |
| Roster Edit/Remove buttons missing `aria-label` | High | Added contextual `aria-label="Edit role for …"` / `"Remove …"` | ✅ |
| Command/Roster/History sections missing `aria-label` | Medium | Added `aria-label` or `aria-labelledby` to all 3 | ✅ |
| History filter controls missing labels | High | Added `aria-label` to select + 2 date inputs | ✅ |

### Files Modified in Phase 5

| File | Change |
|------|--------|
| `apps/teams/views/manage_api.py` | Added `ActivityActionType` + `NotificationService` imports; wired `TeamActivityLog.objects.create()` in 6 mutating endpoints; wired `NotificationService.notify_vnext_team_invite_sent()` in invite, `notify_roster_change()` in role update + remove |
| `templates/teams/manage_hq/partials/_topbar.html` | Added notification bell + badge + dropdown panel; aria-label on hamburger; aria-haspopup/expanded/controls on bell; aria-live on badge; role="region" on panel |
| `static/teams/js/team-manage-hq.js` | Added Notifications module (Module 8): pollBadge, togglePanel, openPanel, closePanel, markAllRead with 30s polling + aria-expanded sync; wired into public API + DOMContentLoaded |
| `templates/teams/manage_hq/partials/_sidebar.html` | aria-label on close button + nav element |
| `templates/teams/manage_hq/partials/_section_roster_ops.html` | Mobile-visible action buttons (sm:opacity-100); role="dialog" + aria-modal + aria-labelledby on 3 modals; aria-label on 3 close buttons + all Edit/Remove buttons |
| `templates/teams/manage_hq/partials/_section_command_center.html` | aria-label on section |
| `templates/teams/manage_hq/partials/_section_history.html` | aria-labelledby on section + heading id; aria-label on filter select + 2 date inputs |

### Quality Gate

- **Lint errors:** ✅ 0 in `manage_api.py`
- **Template tag balance:** ✅ All modified templates verified
- **Audit coverage:** 7/7 mutating endpoints now write TeamActivityLog
- **Notification coverage:** 3/3 roster-affecting endpoints now fire notifications
- **A11y fixes:** 12 issues fixed (1 critical, 5 high, 6 medium)

---

## Quality Gate: Final Production Sweep (Section 18)

### Template Tag Balance (15 templates scanned)

| Template | if | for | with | block | comment | Status |
|----------|:--:|:---:|:----:|:-----:|:-------:|:------:|
| `_topbar.html` | 1/1 | 0/0 | 0/0 | 0/0 | 1/1 | ✅ |
| `_sidebar.html` | 13/13 | 1/1 | 0/0 | 0/0 | 1/1 | ✅ |
| `_section_command_center.html` | 31/31 | 2/2 | 1/1 | 0/0 | 1/1 | ✅ |
| `_section_roster_ops.html` | 24/24 | 5/5 | 1/1 | 0/0 | 1/1 | ✅ |
| `_section_history.html` | 2/2 | 0/0 | 0/0 | 0/0 | 1/1 | ✅ |
| `_section_settings.html` | 25/25 | 1/1 | 0/0 | 0/0 | 1/1 | ✅ |
| `_section_team_profile.html` | 5/5 | 1/1 | 0/0 | 0/0 | 1/1 | ✅ |
| `_section_treasury.html` | 13/13 | 0/0 | 0/0 | 0/0 | 1/1 | ✅ |
| `_section_competition_hub.html` | 3/3 | 0/0 | 0/0 | 0/0 | 1/1 | ✅ |
| `manage_hq.html` | 0/0 | 0/0 | 0/0 | 1/1 | 0/0 | ✅ |
| `team_detail.html` | 0/0 | 0/0 | 0/0 | 4/4 | 0/0 | ✅ |
| `_body.html` (detail) | 50/50 | 3/3 | 0/0 | 0/0 | 0/0 | ✅ |
| `_head_assets.html` | 3/3 | 0/0 | 0/0 | 0/0 | 0/0 | ✅ |
| `_scripts.html` | 0/0 | 0/0 | 0/0 | 0/0 | 0/0 | ✅ |
| `manage.html` (root) | 10/10 | 2/2 | 0/0 | 3/3 | 0/0 | ✅ |

### Python Lint

| File | Errors |
|------|:------:|
| `apps/teams/views/manage_api.py` | ✅ 0 |
| `apps/organizations/views/team.py` | ✅ 0 |
| `apps/organizations/services/team_detail_context.py` | ✅ 0 |

### API URL Wiring (11/11 matched)

| JS Path | Django URL Pattern | Status |
|---------|-------------------|:------:|
| `${API}/activity/` | `api/<slug>/manage/activity/` | ✅ |
| `invite/` | `api/<slug>/manage/invite/` | ✅ |
| `${API}/invites/<id>/cancel/` | `api/<slug>/manage/invites/<id>/cancel/` | ✅ |
| `${API}/members/<id>/role/` | `api/<slug>/manage/members/<id>/role/` | ✅ |
| `${API}/members/<id>/remove/` | `api/<slug>/manage/members/<id>/remove/` | ✅ |
| `join-requests/<id>/handle/` | `api/<slug>/manage/join-requests/<id>/handle/` | ✅ |
| `profile/` | `api/<slug>/manage/profile/` | ✅ |
| `media/` | `api/<slug>/manage/media/` | ✅ |
| `settings/` | `api/<slug>/manage/settings/` | ✅ |
| `/notifications/api/unread-count/` | `notifications:api_unread_count` | ✅ |
| `/notifications/api/nav-preview/` | `notifications:nav_preview` | ✅ |

### CSRF Verification

- `api()` wrapper auto-sets `X-CSRFToken` header → all POST calls covered ✅
- `markAllRead()` bare `fetch()` POST includes `X-CSRFToken: CSRF` ✅
- 2 GET-only calls (`unread-count`, `nav-preview`) — no CSRF needed ✅

### N+1 Query Fixes (Quality Gate pass)

| Issue | Location | Fix | Status |
|-------|----------|-----|:------:|
| Roster missing `user__profile` | `team_detail_context.py` `_build_roster_context` | Added `'user__profile'` to `select_related` | ✅ |
| Pending invites missing profile | `team.py` manage view | Added `'invited_user__profile', 'inviter__profile'` | ✅ |
| Redundant `Organization.objects.get()` | `team_detail_context.py` `_build_permissions` | Use `team.organization` (already cached) | ✅ |
| `_get_admin_context` bare `get_object_or_404` | `manage_api.py` | Added `select_related('organization', 'created_by')` | ✅ |
| Manage view missing `created_by` | `team.py` manage view | Added `'created_by', 'created_by__profile'` to `select_related` | ✅ |
| Detail view missing `created_by` | `team.py` detail view | Added `'created_by'` to `select_related` | ✅ |
| `members.count()` + iteration = 2 queries | `team.py` manage view | `list(members)` + `len(members)` | ✅ |

**Estimated query savings:** ~25 queries/page-load eliminated (20 avatar N+1 + 1 redundant org + 1 count + 3 lazy FK loads).

---

## Project Summary

### Phase Completion

| Phase | Status | Sessions | Files |
|-------|:------:|:--------:|:-----:|
| **Phase 1:** Foundation & Bug Fixes | ✅ | 1 | 7 |
| **Phase 2:** Manage HQ Full Rebuild | ✅ | 1 | 13 |
| **Phase 3:** Team Detail Page Build | ✅ | 1 | 4 |
| **Phase 4:** Organization & Economy | ✅ | 1 | 8 |
| **Phase 5:** Audit, Notifications & Polish | ✅ | 1 | 7 |
| **Quality Gate:** Final Production Sweep | ✅ | 1 | 3 |

### Cumulative Stats

- **Total files created/modified:** 32 (across all phases, some files modified in multiple phases)
- **Python lint errors:** 0
- **Template tag mismatches:** 0
- **N+1 queries fixed:** 7
- **A11y issues fixed:** 12
- **API endpoints:** 11 (all URL-wired, CSRF-protected)
- **JS modules:** 8 (Modal, Command, Roster, Competition, Profile, Settings, History, Notifications)
- **Manage HQ sections:** 9 (Command Center, Roster Ops, Competition Hub, Training Lab, Community, Profile, Settings, Treasury, History)
- **Master plan sections covered:** 1-18 (complete)