# TOC Execution Tracker — The Great Reset

**Version:** 1.7
**Started:** 2026-02-23
**Master Document:** `Documents/TOC/TOC_MASTER_PLANNING_DOCUMENT.md` v1.5
**Design Reference (TOC):** `templates/My drafts/TOC/demo_TOC.html` (2,083-line static prototype — use as visual/UX baseline)
**Design Reference (Match Lobby):** `templates/My drafts/TOC/match_lobby.html` (3,509-line match lobby prototype — future S6 reference)
**Tech Stack:** Tailwind CSS (CDN) + Vanilla JS — platform standard (NOT raw CSS)
**Tailwind Config:** `static/siteui/js/tailwind-config.js` — project-wide design tokens
**Status:** Sprint 0 — COMPLETE ✅ | Sprint 1 — COMPLETE ✅ | Sprint 2 — COMPLETE ✅ | Sprint 3 — COMPLETE ✅ | Sprint 4 — COMPLETE ✅ | Sprint 5 — NOT STARTED

---

## Tracker Discipline (MANDATORY)

> **These rules are non-negotiable. Violations invalidate the sprint.**

1. **After completing ANY task** → immediately update this tracker file (check the box, update completion counts)
2. **Before starting ANY new task** → re-read this tracker file first to confirm current state and avoid lost progress
3. **Zero tolerance for drift** — if a session resets or context is lost, the tracker is the single source of truth
4. **No duplicate code** — every new file must be justified; no copy-paste from legacy; no corrupted/half-written files
5. **No legacy remnants** — this is Version 1.0 of the TOC; there is no "old code to keep"; everything is built fresh and clean
6. **Clean project standard** — no bad code, no duplicate code, no corrupted files, no orphaned imports, no dead routes

---

## Design Reference

The demo prototype at `templates/My drafts/TOC/demo_TOC.html` (2,083 lines) serves as the **visual and UX baseline**. It is a static HTML file (Tailwind CDN + Lucide icons) — NOT production code. Key design patterns to extract:

| Pattern | Demo Implementation | Production Adaptation |
|---------|--------------------|-----------------------|
| **Color System** | `dc-bg: #050507`, `dc-surface: #0B0B0F`, `dc-panel: #121218`, `dc-border: #22222E` | Add to `tailwind.config` OR use CSS variables in minimal `toc-theme.css` |
| **Game Theming** | `[data-game="valorant"]` with `--color-primary: #00F0FF` | CSS variables via `[data-game]` attr + Tailwind `text-[var(--color-primary)]` |
| **Typography** | `Inter` (UI), `Outfit` (display/headings), `JetBrains Mono` (data) | Keep Inter + JetBrains Mono from project config; add Outfit as `font-corp` |
| **Ghost Icons** | `opacity-[0.02]`, positioned absolute, `-rotate-12` | Tailwind utilities: `absolute opacity-[0.02] -rotate-12 w-72 h-72` |
| **Glass Morphism** | `.glass-box` = `bg-dc-surface border border-dc-border shadow` | Tailwind classes directly in templates |
| **Data Grid** | `.data-grid` with sticky headers, hover rows, selected state | Tailwind table utilities + minimal CSS for sticky headers |
| **Sidebar** | 240px, collapsible, grouped nav (Management/Competition/Platform) | Tailwind flex/width + JS toggle, adapt to 9 TOC tabs |
| **Cmd+K Palette** | Fixed overlay, search + quick commands + recent entities | Keep pattern, wire to `TOC.cmdk` API |
| **Toast Stack** | Bottom-right, success/warning variants with dismiss | Keep pattern, wire to `TOC.toast` API |
| **Slide-out Drawer** | Right-side 500px panel with tabs | Keep pattern, wire to `TOC.drawer` API |
| **Freeze Modal** | Full-screen overlay, reason input, danger styling | Keep pattern for killswitch UX |
| **Views** | 8 views: dashboard, participants, financials, bracket, matches, medic, broadcast, config | Expand to 9 tabs per PRD |

> **NOTE:** The demo is incomplete and non-functional. It is a design direction, not a codebase. We build **exact design** from scratch using **Tailwind CSS utility classes** (the platform standard). A minimal `toc-theme.css` file is used ONLY for CSS custom properties (game themes, scrollbar) that Tailwind can't express.

### Match Lobby Reference

`templates/My drafts/TOC/match_lobby.html` (3,509 lines) is the design reference for the Match Lobby page (Sprint 6). Key design patterns:

| Pattern | Match Lobby Implementation |
|---------|---------------------------|
| **Game Theme Vars** | `:root, [data-game=*]` with `--ac` (accent), `--ar/--ag/--ab` (RGB components) |
| **Glass Panels** | `.glass` with `backdrop-filter: blur(24px)`, `bg-black/20`, border `rgba(--ar,--ag,--ab,0.15)` |
| **Accent Helpers** | `.ac` (text), `.ac-bg` (bg), `.ac-bd` (border), `.ac-glow` (shadow), `.ac-fill` (fill) |
| **Match Phases** | Coin flip → Map veto → Hero bans → Ready-up → Live → Score submission → Results |
| **Map Cards** | Pick/ban states with blur + overlay, selected ring |
| **Score Input** | Large mono-font score inputs with submission/upload |

> **NOTE:** Match lobby demo has corrupted code sections. Use for design direction only.

### Connected Pages

TOC is the organizer hub connected to the entire tournament ecosystem:
- **Tournament List** (`/tournaments/`) → navigates to TOC
- **Tournament Detail** (`/tournaments/<slug>/`) → public-facing; TOC is the private organizer counterpart
- **Tournament Hub** (`/tournaments/<slug>/hub/`) → player-facing hub
- **Registration** (`/tournaments/<slug>/register/`) → feeds into TOC Participants tab
- **Match Lobby** (`/tournaments/<slug>/match/<id>/`) → controlled from TOC Matches tab

---

## Directive Summary

| Directive | Status |
|-----------|--------|
| **D1 — The Great Purge** | ✅ Complete |
| **D2 — Execution Tracker** | ✅ This Document |
| **D3 — UI/UX Mandate** | ⬜ Enforced Per Sprint |

### UI/UX Mandate Rules (Enforced Every Sprint)

| Rule | Specification |
|------|---------------|
| **Tech Stack** | **Tailwind CSS** (CDN) + **Vanilla JS** — platform standard. NOT raw/basic CSS. All styling via Tailwind utility classes in templates |
| **Typography** | `Inter` for all UI text; `JetBrains Mono` for data, seeds, IDs, scores; `Outfit` for display headings |
| **Font Sizing** | Dense SaaS sizing: `text-xs`, `text-sm`. No massive headers. Optimized for 1920×1080 |
| **Ghost Icons** | Massive Lucide SVGs at `opacity: 0.025` behind cards/modules |
| **Theming** | CSS variables (`var(--color-primary)`) — accent shifts per game (Cyan/Valorant, Red/eFootball, Amber/PUBGM, etc.) |
| **Layout** | Left sidebar (persistent) + Top bar (Cmd+K search, status) + Right main column |
| **Drawers** | Slide-out right drawers for Comms, Team Profiles, Match Medic |
| **Zero Reloads** | Every tab switch, action, and status change = async fetch + Vanilla JS DOM update |
| **CSS Policy** | Minimal `toc-theme.css` ONLY for CSS custom properties (game theme vars, scrollbar). Everything else = Tailwind classes |

---

## The Great Purge — Archive Manifest

All files below will be moved to `backups/toc_legacy_feb2026/`. Models, services, player-facing views, and public APIs are **PRESERVED** — only the organizer-facing management layer is purged.

### Organizer Views (8 files, ~3,205 lines)

- [x] `apps/tournaments/views/organizer.py` (980 lines)
- [x] `apps/tournaments/views/organizer_participants.py` (679 lines)
- [x] `apps/tournaments/views/organizer_brackets.py` (473 lines)
- [x] `apps/tournaments/views/organizer_results.py` (260 lines)
- [x] `apps/tournaments/views/organizer_match_ops.py` (235 lines)
- [x] `apps/tournaments/views/organizer_matches.py` (201 lines)
- [x] `apps/tournaments/views/organizer_payments.py` (192 lines)
- [x] `apps/tournaments/views/organizer_scheduling.py` (185 lines)

### Related Management Views (12 files, ~2,425 lines)

- [x] `apps/tournaments/views/registration_dashboard.py` (335 lines)
- [x] `apps/tournaments/views/payment_status.py` (319 lines)
- [x] `apps/tournaments/views/health_metrics.py` (287 lines)
- [x] `apps/tournaments/views/dispute_resolution.py` (255 lines)
- [x] `apps/tournaments/views/permission_requests.py` (241 lines)
- [x] `apps/tournaments/views/bulk_operations_view.py` (201 lines)
- [x] `apps/tournaments/views/registration_ux_api.py` (177 lines)
- [x] `apps/tournaments/views/response_export_view.py` (170 lines)
- [x] `apps/tournaments/views/webhook_views.py` (138 lines)
- [x] `apps/tournaments/views/form_analytics_view.py` (116 lines)
- [x] `apps/tournaments/views/permission_request.py` (108 lines)
- [x] `apps/tournaments/views/disputes_management.py` (78 lines)

### Manage Templates (10 files, ~4,619 lines)

- [x] `templates/tournaments/manage/_base.html` (747 lines)
- [x] `templates/tournaments/manage/participants.html` (819 lines)
- [x] `templates/tournaments/manage/matches.html` (546 lines)
- [x] `templates/tournaments/manage/overview.html` (514 lines)
- [x] `templates/tournaments/manage/payments.html` (466 lines)
- [x] `templates/tournaments/manage/brackets.html` (458 lines)
- [x] `templates/tournaments/manage/schedule.html` (430 lines)
- [x] `templates/tournaments/manage/settings.html` (282 lines)
- [x] `templates/tournaments/manage/disputes.html` (246 lines)
- [x] `templates/tournaments/manage/announcements.html` (111 lines)

### Organizer Templates (8 files, ~1,275 lines)

- [x] `templates/tournaments/organizer/create_tournament.html` (296 lines)
- [x] `templates/tournaments/organizer/tournament_detail.html` (206 lines)
- [x] `templates/tournaments/organizer/dashboard.html` (138 lines)
- [x] `templates/tournaments/organizer/health_metrics.html` (132 lines)
- [x] `templates/tournaments/organizer/groups/config.html` (132 lines)
- [x] `templates/tournaments/organizer/groups/draw.html` (129 lines)
- [x] `templates/tournaments/organizer/disputes.html` (126 lines)
- [x] `templates/tournaments/organizer/pending_results.html` (116 lines)

### Organizer Static Assets (3 files)

- [x] `static/tournaments/organizer/css/organizer-glassmorphism.css` (829 lines)
- [x] `static/tournaments/organizer/css/organizer.css` (83 lines)
- [x] `static/tournaments/organizer/js/organizer-tabs.js` (44 lines)

### Tournament Ops Module (170 files, ~20,000+ lines)

- [x] `apps/tournament_ops/` (entire directory → `backups/toc_legacy_feb2026/tournament_ops/`)

### Old Tournament Manage Page Frontend (COMPLETE REMOVAL)

The old organizer page at `/tournaments/organizer/<slug>/` (e.g., `http://127.0.0.1:8000/tournaments/organizer/valorant-scrims-44/`) must be completely removed. This includes all templates, static assets, and URL routes that serve this page. We are building from scratch — zero legacy frontend code survives.

- [x] Delete or archive `templates/tournaments/manage/` directory (10 templates, ~4,619 lines) — covered in Manage Templates above
- [x] Delete or archive `templates/tournaments/organizer/` directory (8 templates, ~1,275 lines) — covered in Organizer Templates above
- [x] Delete or archive `static/tournaments/organizer/` directory (3 files) — covered in Organizer Static Assets above
- [x] Remove all organizer URL patterns from `apps/tournaments/urls.py` that serve `/tournaments/organizer/*` routes
- [x] Remove all organizer view imports from `apps/tournaments/urls.py`
- [x] Verify the old page at `/tournaments/organizer/<slug>/` returns 404 after cleanup
- [x] Verify no broken imports or references remain anywhere in the codebase
- [x] Run `python manage.py check` to confirm zero Django system check errors

### URL Cleanup

- [x] Comment out all organizer imports in `apps/tournaments/urls.py` (8 import blocks, ~70 lines)
- [x] Comment out all `organizer/` URL patterns in `apps/tournaments/urls.py` (~100 URL paths)
- [x] Verify syntax with `ast.parse()` after cleanup

### Files PRESERVED (not purged)

| Category | Reason |
|----------|--------|
| `apps/tournaments/models/` | Models are the foundation — extended, not rewritten |
| `apps/tournaments/services/` (44 files) | Core services (registration, bracket, match, payment, lifecycle) reused by new TOC APIs |
| `apps/tournaments/views/hub.py`, `detail.py`, `live.py`, `checkin.py`, etc. | Public/player-facing views — not part of TOC |
| `apps/tournaments/api/` | REST API layer — refactored per sprint, not wholesale replaced |
| `apps/games/models/game.py` | Game model with `slug`, `short_code`, `primary_color` used for theming |

---

## Sprint Plan — 13 Sprints (0–12)

### PRD Coverage Matrix

| Sprint | PRD Pillars | TOC Tabs | New Models | Est. Effort |
|--------|-------------|----------|------------|-------------|
| **S0** | — | Shell/Layout | — | Foundation |
| **S1** | Pillar 1 (§2) | Overview | — | Medium |
| **S2** | Pillar 2 core (§3.1–3.9) | Participants | — | Heavy |
| **S3** | Pillar 2 adv (§3.10–3.14) | Participants+ | EmergencySubRequest, FreeAgentRegistration | Heavy |
| **S4** | Pillar 3 (§4) | Payments | TournamentBounty, KYCSubmission | Heavy |
| **S5** | Pillar 4 (§5) | Brackets + Schedule | QualifierPipeline, PipelineStage, PromotionRule | Heavy |
| **S6** | Pillar 5 (§6) | Matches | RescheduleRequest, MatchMedia, BroadcastStation, MatchServerSelection | Heavy |
| **S7** | Pillar 6 (§7) | Disputes | — (existing DisputeRecord) | Medium |
| **S8** | Pillar 7 (§8) | Settings + Announcements | GameMatchConfig, MapPoolEntry, MatchVetoSession, ServerRegion, RulebookVersion, RulebookConsent, BRScoringMatrix | Heavy |
| **S9** | Pillar 8 (§9) | — (cross-tab) | CertificateTemplate, CertificateRecord, ProfileTrophy, UserTrophy, TrustEvent | Heavy |
| **S10** | Pillars 9+10 (§10–11) | — (RBAC layer) | — | Medium |
| **S11** | Pillars 11+12 (§12–13) | — (infra) | — | Medium |
| **S12** | §14, §18 | — | — | Polish |

---

## Sprint 0 — The Foundation Shell

**Goal:** Execute the Great Purge, build the empty SPA shell — layout, theming, routing, design system. No data, no APIs. The skeleton every subsequent sprint plugs into.

**PRD Sections:** §1.2, §1.3 (architecture/tabs)

### Backend

- [x] **S0-B1** Execute The Great Purge — archive 211 files to `backups/toc_legacy_feb2026/`
- [x] **S0-B2** Clean `apps/tournaments/urls.py` — comment out organizer imports + URL patterns
- [x] **S0-B3** Create `apps/tournaments/views/toc.py` — Single entry-point CBV (`TOCView`) with LoginRequiredMixin, permission checks, game_slug context
- [x] **S0-B4** Create `apps/tournaments/urls_toc.py` — Clean URL conf: `path('<slug:slug>/', TOCView.as_view())`
- [x] **S0-B5** Wire `urls_toc.py` into `deltacrown/urls.py` — `path("toc/", include(...))`

### Frontend — Template

- [x] **S0-F1** Create `templates/tournaments/toc/base.html` — Master SPA shell (sidebar + topbar + main + drawer + toast stack)
- [x] **S0-F2** Left sidebar: 9 tab nav items with inline SVG icons (Overview, Participants, Payments, Brackets, Matches, Schedule, Disputes, Announcements, Settings)
- [x] **S0-F3** Top bar: tournament name, status pill (color-coded per state), game tag, `Cmd+K` search trigger, user chip
- [x] **S0-F4** Main content area: 9 `data-tab-content` panels, each with ghost icon + empty state placeholder showing target sprint
- [x] **S0-F5** Right slide-out drawer shell (empty, toggled via JS)
- [x] **S0-F6** `Cmd+K` command palette overlay (search input, navigation shortcuts, keyboard navigation)
- [x] **S0-F7** Freeze banner (hidden by default, shown when tournament status = frozen)
- [x] **S0-F8** `window.TOC_CONFIG` injection: tournamentSlug, csrfToken, apiBase, status, gameSlug, isOrganizer

### Frontend — CSS Theme File (Minimal — Tailwind handles everything else)

- [x] **S0-C1** Create `static/tournaments/toc/css/toc-theme.css` — CSS custom properties ONLY (game themes, scrollbar, Tailwind-inexpressible styles)
- [x] **S0-C2** Game-specific accent themes via CSS variables: `[data-game="valorant"]` (`--color-primary: #00F0FF`), `[data-game="efootball"]` (`--color-primary: #EF4444`), `[data-game="pubgm"]` (`--color-primary: #F59E0B`), `[data-game="codm"]` (`--color-primary: #10B981`), `[data-game="freefire"]` (`--color-primary: #F97316`), `[data-game="mlbb"]` (`--color-primary: #8B5CF6`), `[data-game="default"]` (`--color-primary: #3B82F6`) with RGB component vars for rgba()
- [x] **S0-C3** Custom scrollbar styles (6px, dark theme, Firefox + WebKit)
- [x] **S0-C4** Animated live pulse dot keyframe (for status pills)
- [x] **S0-C5** Ghost icon base positioning (absolute, centered, large size) — Tailwind handles opacity/rotation

### Frontend — JavaScript Core

- [x] **S0-J1** Create `static/tournaments/toc/js/toc-core.js` — IIFE, `window.TOC` public namespace, `$()` / `$$()` helpers
- [x] **S0-J2** Hash-based tab router: `TOC.navigate(tabId)`, `hashchange` listener, sidebar active state + panel visibility toggle
- [x] **S0-J3** `TOC.fetch(url, opts)` — Async wrapper with CSRF token, JSON auto-serialize, timeout (30s), AbortController
- [x] **S0-J4** `TOC.drawer.open(title, html)` / `.close()` — Right slide-out with backdrop, `aria-hidden` toggle
- [x] **S0-J5** `TOC.toast(message, type, opts)` — 4 variants (success/error/warning/info), auto-dismiss, SVG icons, dismiss button
- [x] **S0-J6** `TOC.cmdk.open()` / `.close()` / `.toggle()` — Cmd+K palette with input filtering, arrow-key navigation, Enter to navigate
- [x] **S0-J7** `TOC.badge(tab, count)` — Nav badge counter API
- [x] **S0-J8** Sidebar collapse with `localStorage` persistence, keyboard shortcuts (Cmd+K, Escape)

### Validation Criteria

- [x] Navigate to `/toc/<slug>/` → see empty SPA shell with sidebar, topbar, 9 tabs
- [x] Click each tab → content area swaps, URL hash updates, zero page reloads
- [x] `Cmd+K` → command palette overlay appears with keyboard nav
- [x] Switch `data-game` attribute on `<html>` → all accent colors shift
- [x] Ghost icons visible at ultra-low opacity behind empty panel placeholders
- [x] Sidebar collapse button → sidebar shrinks to 60px, state persists on reload

---

## Sprint 1 — Command Center (Overview Tab)

**Goal:** The Overview tab becomes a live command center showing lifecycle status, alerts, stats, and upcoming events. First tab with real data.

**PRD Sections:** §2.1–§2.7 (Pillar 1 — Tournament Lifecycle & State Machine)

### Backend — API

- [x] **S1-B1** Create `apps/tournaments/api/toc/` package with `__init__.py`, `urls.py`
- [x] **S1-B2** `api/toc/overview.py` — `GET /api/toc/<slug>/overview/` — Dashboard payload: status, lifecycle stage, alerts, stats summary, upcoming events
- [x] **S1-B3** `api/toc/lifecycle.py` — `POST /api/toc/<slug>/lifecycle/transition/` — Trigger state transitions (validation from §2.2)
- [x] **S1-B4** `api/toc/lifecycle.py` — `POST /api/toc/<slug>/lifecycle/freeze/` — Global Killswitch (§2.7)
- [x] **S1-B5** `api/toc/lifecycle.py` — `POST /api/toc/<slug>/lifecycle/unfreeze/` — Unfreeze with audit reason
- [x] **S1-B6** `api/toc/alerts.py` — `GET /api/toc/<slug>/alerts/` — Alerts from CommandCenterService
- [x] **S1-B7** `api/toc/alerts.py` — `POST /api/toc/<slug>/alerts/<id>/dismiss/` — Dismiss/acknowledge alert
- [x] **S1-B8** Serializers: `OverviewSerializer`, `LifecycleTransitionSerializer`, `AlertSerializer`

### Backend — Service

- [x] **S1-S1** Wrap `CommandCenterService` to return structured alert DTOs for the new API
- [x] **S1-S2** Add lifecycle transition validation logic (§2.2 state machine conditions) as reusable service method
- [x] **S1-S3** Add killswitch service method with audit logging and timer suspension

### Frontend

- [x] **S1-F1** Overview tab layout: Status hero card (lifecycle stage + transition button) + 4-column stat grid
- [x] **S1-F2** Lifecycle State Machine visualizer: horizontal pipeline showing all states, current highlighted
- [x] **S1-F3** Transition modal: dropdown of valid next states, confirmation dialog with conditions checklist
- [x] **S1-F4** Alerts panel: prioritized cards (critical/warning/info) with dismiss/action buttons
- [x] **S1-F5** Global Killswitch: red emergency button (§2.7) with confirmation dialog + freeze banner activation
- [x] **S1-F6** Stat cards: Total Registrations, Verified Payments, Matches Played, Active Disputes (JetBrains Mono values)
- [x] **S1-F7** Upcoming Events timeline: next check-in window, next match, registration deadline
- [x] **S1-F8** Ghost icon: massive Shield SVG behind overview hero area
- [x] **S1-F9** Auto-refresh: poll `/api/toc/<slug>/overview/` every 30s, diff-update DOM

### Validation Criteria

- [x] Overview tab loads with real tournament data (status, counts, alerts)
- [x] Lifecycle transition: click "Advance to Live" → API call → status badge updates → no reload
- [x] Killswitch freezes tournament → FROZEN status → freeze banner appears across all tabs
- [x] Alerts auto-refresh and can be dismissed inline

---

## Sprint 2 — Participant Grid & Registration Ops

**Goal:** Dense, filterable, sortable data grid for all registrations with inline actions. The operator workhorse tab.

**PRD Sections:** §3.1–§3.9 (Registration, Smart Wizard, Pipeline, Organizer Tools, Verification, Check-In, Waitlist, Guest Teams, Fee Waivers)

### Backend — API

- [x] **S2-B1** `api/toc/participants.py` — `GET /api/toc/<slug>/participants/` — Paginated, filterable list (status, payment, check-in, search, ordering)
- [x] **S2-B2** `POST /api/toc/<slug>/participants/<id>/approve/` — Approve registration
- [x] **S2-B3** `POST /api/toc/<slug>/participants/<id>/reject/` — Reject with reason
- [x] **S2-B4** `POST /api/toc/<slug>/participants/<id>/disqualify/` — DQ with reason + evidence
- [x] **S2-B5** `POST /api/toc/<slug>/participants/bulk-action/` — Bulk approve/reject/DQ/check-in
- [x] **S2-B6** `POST /api/toc/<slug>/participants/<id>/verify-payment/` — Manual payment verification
- [x] **S2-B7** `POST /api/toc/<slug>/participants/<id>/toggle-checkin/` — Toggle check-in status
- [x] **S2-B8** `GET /api/toc/<slug>/participants/<id>/` — Participant detail (drawer payload)
- [x] **S2-B9** `GET /api/toc/<slug>/participants/export/` — CSV export
- [x] **S2-B10** Serializers: `ParticipantListSerializer`, `ParticipantDetailSerializer`, `BulkActionSerializer`

### Backend — Service

- [x] **S2-S1** Wrap existing `registration_service`, `checkin_service`, `registration_verification` for TOC API layer
- [x] **S2-S2** Add filtering/ordering logic to participant queryset (status, payment_status, is_checked_in, search by team/player name)

### Frontend

- [x] **S2-F1** Participant grid: dense table with columns (Team/Player, Status, Payment, Check-In, Verified, Seed, Actions)
- [x] **S2-F2** Filter bar: status dropdown, payment dropdown, check-in toggle, search input, bulk action button
- [x] **S2-F3** Inline actions: Approve/Reject/DQ buttons per row with confirmation
- [x] **S2-F4** Bulk action toolbar: select all / checkbox per row, bulk action dropdown (approve/reject/DQ/check-in)
- [x] **S2-F5** Participant detail drawer: click row → right drawer with full registration data, payment proof, verification status, audit log
- [x] **S2-F6** Pagination: server-side, 50 per page, page nav at bottom
- [x] **S2-F7** Check-in toggle: inline switch with instant feedback
- [x] **S2-F8** Ghost icon: massive Users SVG behind participant grid
- [x] **S2-F9** Export button: CSV download trigger

### Validation Criteria

- [x] Participant tab loads with real paginated data
- [x] Filtering and search work without page reload
- [x] Approve/Reject/DQ actions update row state inline
- [x] Bulk actions process multiple registrations at once
- [x] Drawer opens with full participant detail on row click

---

## Sprint 3 — Participants Advanced (Emergency Subs, Free Agent Pool, Waitlist)

**Goal:** Advanced participant features: emergency substitution, Free Agent / LFG pool, waitlist auto-promotion, and guest team conversion.

**PRD Sections:** §3.10–§3.14 (Emergency Subs, Free Agents, Waitlist, Guest Teams, Fee Waivers)

### Backend — Models

- [x] **S3-M1** `EmergencySubRequest` model — requester, tournament, outgoing_player, incoming_player, reason, status, approved_by, timestamps
- [x] **S3-M2** `FreeAgentRegistration` model — user, tournament, position_preference, rank_info, notes, status, matched_team

### Backend — API

- [x] **S3-B1** `POST /api/toc/<slug>/participants/<id>/emergency-sub/` — Submit emergency sub request (§3.10)
- [x] **S3-B2** `POST /api/toc/<slug>/emergency-subs/<id>/approve/` — Approve sub request
- [x] **S3-B3** `GET /api/toc/<slug>/free-agents/` — Free Agent pool list (§3.11)
- [x] **S3-B4** `POST /api/toc/<slug>/free-agents/<id>/assign/` — Assign free agent to team
- [x] **S3-B5** `POST /api/toc/<slug>/participants/<id>/promote-waitlist/` — Manual waitlist promotion (§3.12)
- [x] **S3-B6** `POST /api/toc/<slug>/participants/auto-promote/` — Auto-promote next eligible (§3.12)
- [x] **S3-B7** `POST /api/toc/<slug>/participants/<id>/convert-guest/` — Convert guest team to verified (§3.13)
- [x] **S3-B8** `POST /api/toc/<slug>/participants/<id>/fee-waiver/` — Issue fee waiver (§3.14)

### Frontend

- [x] **S3-F1** Emergency Sub panel: pending sub requests list, approve/reject buttons, player swap visualization
- [x] **S3-F2** Free Agent Pool tab within Participants: searchable list of available free agents, "Assign to Team" action
- [x] **S3-F3** Waitlist management: ordered waitlist list, auto-promote button, manual promote per entry
- [x] **S3-F4** Guest team badge + "Convert to Verified" action button
- [x] **S3-F5** Fee waiver action button (opens drawer with waiver form)

### Validation Criteria

- [x] Emergency sub request flow: submit → review → approve → roster updated
- [x] Free agent assigned to team → pool updated, team roster updated
- [x] Waitlist auto-promote fills first available slot

---

## Sprint 4 — Financial Operations (Payments Tab)

**Goal:** Payment verification, refunds, revenue analytics, prize distribution planning, and bounty system.

**PRD Sections:** §4.1–§4.10 (Pillar 3 — Financial Operations)

### Backend — Models

- [x] **S4-M1** `TournamentBounty` model — tournament, title, description, prize_amount, condition, status, winner, awarded_at (§4.8)
- [x] **S4-M2** `KYCSubmission` model — user, tournament, document_type, document_url, status, reviewed_by, notes (§4.10)

### Backend — API

- [x] **S4-B1** `GET /api/toc/<slug>/payments/` — Paginated payment list with filters (status, method, date range)
- [x] **S4-B2** `POST /api/toc/<slug>/payments/<id>/verify/` — Verify payment with proof review
- [x] **S4-B3** `POST /api/toc/<slug>/payments/<id>/reject/` — Reject payment with reason
- [x] **S4-B4** `POST /api/toc/<slug>/payments/<id>/refund/` — Process refund (§4.3)
- [x] **S4-B5** `POST /api/toc/<slug>/payments/bulk-verify/` — Bulk payment verification
- [x] **S4-B6** `GET /api/toc/<slug>/payments/summary/` — Revenue summary: total collected, verified, pending, refunded (§4.4)
- [x] **S4-B7** `GET /api/toc/<slug>/payments/export/` — CSV export
- [x] **S4-B8** `GET /api/toc/<slug>/prize-pool/` — Prize distribution breakdown (§4.5)
- [x] **S4-B9** `POST /api/toc/<slug>/prize-pool/distribute/` — Trigger prize distribution
- [x] **S4-B10** Bounty CRUD endpoints (§4.8)
- [x] **S4-B11** KYC submission endpoints (§4.10)

### Frontend

- [x] **S4-F1** Payments grid: table with columns (Team/Player, Amount, Method, Status, Proof, Date, Actions)
- [x] **S4-F2** Payment proof viewer: inline image/PDF preview in drawer
- [x] **S4-F3** Verify/Reject inline buttons with proof comparison
- [x] **S4-F4** Revenue summary cards: 4 stat cards (Total, Verified, Pending, Refunded) with JetBrains Mono values
- [x] **S4-F5** Prize distribution panel: visual breakdown of pool allocation
- [x] **S4-F6** Refund modal: amount, reason, confirmation
- [x] **S4-F7** Bounty management card: create/edit bounties, assign winners
- [x] **S4-F8** Ghost icon: massive Wallet SVG behind payments area

### Validation Criteria

- [x] Payment list loads with real payment data
- [x] Verify/reject updates payment status inline
- [x] Refund processes and shows in payment history
- [x] Revenue summary cards display accurate totals

---

## Sprint 5 — Competition Engine (Brackets + Schedule Tabs)

**Goal:** Bracket generation, seeding, group stages, Swiss rounds, multi-wave qualifiers, schedule management.

**PRD Sections:** §5.1–§5.12 (Pillar 4 — The Competition Engine)

### Backend — Models

- [x] **S5-M1** `QualifierPipeline` model — tournament, stages, promotion_rules, status (§5.7)
- [x] **S5-M2** `PipelineStage` model — pipeline, name, format, max_teams, order
- [x] **S5-M3** `PromotionRule` model — from_stage, to_stage, criteria, auto_promote

### Backend — API

- [x] **S5-B1** `POST /api/toc/<slug>/brackets/generate/` — Generate bracket from registrations + seeding
- [x] **S5-B2** `POST /api/toc/<slug>/brackets/reset/` — Reset bracket (with confirmation)
- [x] **S5-B3** `POST /api/toc/<slug>/brackets/publish/` — Publish bracket to participants
- [x] **S5-B4** `PUT /api/toc/<slug>/brackets/seeds/` — Reorder seeding (drag-and-drop payload)
- [x] **S5-B5** `GET /api/toc/<slug>/brackets/` — Current bracket state (tree structure)
- [x] **S5-B6** `POST /api/toc/<slug>/schedule/auto-generate/` — Auto-schedule round(s
- [x] **S5-B7** `POST /api/toc/<slug>/schedule/bulk-shift/` — Bulk shift match times
- [x] **S5-B8** `POST /api/toc/<slug>/schedule/add-break/` — Insert schedule break
- [x] **S5-B9** `GET /api/toc/<slug>/schedule/` — Full schedule with match times, stations, status
- [x] **S5-B10** Group stage CRUD endpoints (configure, draw, standings)
- [x] **S5-B11** Qualifier pipeline CRUD endpoints (§5.7)

### Frontend

- [x] **S5-F1** Bracket visualizer: interactive bracket tree (SE/DE), match cards with scores, winner highlighting
- [x] **S5-F2** Seeding editor: drag-and-drop reorder with numbered seeds
- [x] **S5-F3** Generate/Reset/Publish action buttons with confirmation modals
- [x] **S5-F4** Group stage view: group cards → match tables → standings table
- [x] **S5-F5** Schedule tab: timeline/grid view of all matches with time slots, status badges
- [x] **S5-F6** Auto-schedule button, bulk shift form, break insertion
- [x] **S5-F7** Ghost icons: Git-Branch behind brackets, Calendar behind schedule

### Validation Criteria

- [x] Bracket generates correctly, displays interactive tree
- [x] Seeding drag-and-drop updates order and re-renders bracket
- [x] Schedule auto-generates and shows timeline view
- [x] Group stage draw assigns teams to groups, shows standings

---

## Sprint 6 — Match Operations (Matches Tab)

**Goal:** Live match management, scoring, Match Medic, station dispatch, server selection, and media handling.

**PRD Sections:** §6.1–§6.10 (Pillar 5 — Live Match Operations & Match Medic)

### Backend — Models

- [x] **S6-M1** `RescheduleRequest` model — match, requested_by, old_time, new_time, reason, status (§6.4)
- [x] **S6-M2** `MatchMedia` model — match, uploaded_by, media_type, file, description, is_evidence (§6.9)
- [x] **S6-M3** `BroadcastStation` model — name, stream_url, assigned_match, status (§6.10)
- [x] **S6-M4** `MatchServerSelection` model — match, region, server_ip, selected_at (§6.8)

### Backend — API

- [x] **S6-B1** `GET /api/toc/<slug>/matches/` — Paginated match list with filters (round, status, team)
- [x] **S6-B2** `POST /api/toc/<slug>/matches/<id>/score/` — Submit/override match score
- [x] **S6-B3** `POST /api/toc/<slug>/matches/<id>/mark-live/` — Mark match as live
- [x] **S6-B4** `POST /api/toc/<slug>/matches/<id>/pause/` — Pause match (Match Medic)
- [x] **S6-B5** `POST /api/toc/<slug>/matches/<id>/resume/` — Resume match
- [x] **S6-B6** `POST /api/toc/<slug>/matches/<id>/force-complete/` — Force-complete match
- [x] **S6-B7** `POST /api/toc/<slug>/matches/<id>/reschedule/` — Reschedule request
- [x] **S6-B8** `POST /api/toc/<slug>/matches/<id>/forfeit/` — Declare forfeit
- [x] **S6-B9** `POST /api/toc/<slug>/matches/<id>/add-note/` — Add match note
- [x] **S6-B10** Match media upload/list endpoints

### Frontend

- [x] **S6-F1** Match grid: table with columns (Round, Match #, Team A vs Team B, Score, Status, Station, Actions)
- [x] **S6-F2** Match Medic inline controls: Live/Pause/Resume/Force-Complete buttons per row
- [x] **S6-F3** Score submission drawer: opens with score form, proof upload
- [x] **S6-F4** Reschedule request modal: time picker, reason input
- [x] **S6-F5** Match detail drawer: full match state, timeline, notes, media
- [x] **S6-F6** Station dispatch panel: assign matches to broadcast stations
- [x] **S6-F7** Ghost icon: massive Swords SVG behind match area

### Validation Criteria

- [x] Match list loads with accurate data
- [x] Score submission updates match + bracket
- [x] Match Medic controls work (live → pause → resume → complete)
- [x] Reschedule request creates and shows pending status

---

## Sprint 7 — Disputes (Disputes Tab)

**Goal:** Dispute queue, evidence review, rulings, escalation, and protest bond management.

**PRD Sections:** §7.1–§7.6 (Pillar 6 — Disputes, Evidence & Resolution)

### Backend — API

- [x] **S7-B1** `GET /api/toc/<slug>/disputes/` — Dispute queue with filters (status, severity, match)
- [x] **S7-B2** `GET /api/toc/<slug>/disputes/<id>/` — Full dispute detail with evidence, timeline
- [x] **S7-B3** `POST /api/toc/<slug>/disputes/<id>/resolve/` — Issue ruling
- [x] **S7-B4** `POST /api/toc/<slug>/disputes/<id>/escalate/` — Escalate dispute
- [x] **S7-B5** `POST /api/toc/<slug>/disputes/<id>/assign/` — Assign to staff member
- [x] **S7-B6** `POST /api/toc/<slug>/disputes/<id>/add-evidence/` — Add evidence to dispute
- [x] **S7-B7** `POST /api/toc/<slug>/disputes/<id>/update-status/` — Change dispute status

### Frontend

- [x] **S7-F1** Dispute queue: prioritized list with severity badges (Critical/High/Medium/Low)
- [x] **S7-F2** Dispute detail drawer: evidence gallery (images/video), timeline, participant statements
- [x] **S7-F3** Resolution form: ruling dropdown, penalty selection, reason text, confidence level
- [x] **S7-F4** Escalation button with escalation reason form
- [x] **S7-F5** Staff assignment dropdown per dispute
- [x] **S7-F6** Alert badge on Disputes nav showing open count
- [x] **S7-F7** Ghost icon: massive Scale SVG behind dispute area

### Validation Criteria

- [x] Dispute queue loads with accurate data, severity-sorted
- [x] Resolve dispute → updates status, notifies parties
- [x] Nav badge shows accurate open dispute count
- [x] Evidence viewer displays uploaded media

---

## Sprint 8 — Configuration & Communications (Settings + Announcements Tabs)

**Goal:** Tournament settings, game config, map/server veto, rulebook versioning, and announcement broadcasting.

**PRD Sections:** §8.1–§8.11 (Pillar 7 — Tournament Configuration & Communications)

### Backend — Models

- [x] **S8-M1** `GameMatchConfig` — game, default_match_format, default_map_pool, scoring_rules (§8.1)
- [x] **S8-M2** `MapPoolEntry` — config, map_name, image, is_active, order (§8.2)
- [x] **S8-M3** `MatchVetoSession` — match, veto_type, current_turn, completed_at (§8.3)
- [x] **S8-M4** `ServerRegion` — name, code, ping_endpoint, is_active (§8.5)
- [x] **S8-M5** `RulebookVersion` — tournament, version, content, published_at, is_active (§8.6)
- [x] **S8-M6** `RulebookConsent` — user, rulebook_version, consented_at (§8.7)
- [x] **S8-M7** `BRScoringMatrix` — config, placement_points, kill_points, tiebreaker_rules (§8.10)

### Backend — API

- [x] **S8-B1** Tournament settings CRUD (basic info, registration rules, format, prizes)
- [x] **S8-B2** Game match config CRUD
- [x] **S8-B3** Map pool management endpoints
- [x] **S8-B4** Veto session management
- [x] **S8-B5** Server region management
- [x] **S8-B6** Rulebook version CRUD + consent tracking
- [x] **S8-B7** Announcement CRUD + broadcast endpoint
- [x] **S8-B8** Quick Comms endpoint (§8.9)

### Frontend

- [x] **S8-F1** Settings tab: organized into collapsible sections (Basic Info, Registration Rules, Format, Prizes, Integrations)
- [x] **S8-F2** Map pool editor: drag-and-drop ordering, add/remove maps, image previews
- [x] **S8-F3** Veto builder: visual veto sequence designer (ban/pick/decider)
- [x] **S8-F4** Server region selector: region list with ping indicators
- [x] **S8-F5** Rulebook editor: rich text editor, version history, publish/draft toggle
- [x] **S8-F6** Announcements tab: compose form, recipient targeting, broadcast history
- [x] **S8-F7** Quick Comms panel: pre-built message templates, one-click broadcast
- [x] **S8-F8** Ghost icons: Settings gear behind Settings, Megaphone behind Announcements

### Validation Criteria

- [x] Settings changes save without reload
- [x] Map pool drag-and-drop persists order
- [x] Announcements broadcast and appear in recipient views
- [x] Rulebook version history tracks changes

---

## Sprint 9 — Stats, Certificates & Trust Index

**Goal:** Cross-tab stats integration, certificate generation, trophies/achievements, Player Trust Index.

**PRD Sections:** §9.1–§9.6 (Pillar 8 — Data, Stats & Leaderboards)

### Backend — Models

- [x] **S9-M1** `CertificateTemplate` — tournament, template_html, variables (§9.1)
- [x] **S9-M2** `CertificateRecord` — user, tournament, template, generated_pdf, issued_at (§9.1)
- [x] **S9-M3** `ProfileTrophy` — name, icon, description, criteria (§9.3)
- [x] **S9-M4** `UserTrophy` — user, trophy, earned_at, tournament (§9.3)
- [x] **S9-M5** `TrustEvent` — user, event_type, delta, reason, tournament (§9.5)

### Backend — API

- [x] **S9-B1** Stats summary endpoint (per-tournament: matches, rounds, avg duration, DQ rate)
- [x] **S9-B2** Certificate template CRUD + generate/download
- [x] **S9-B3** Trophy/achievement endpoints
- [x] **S9-B4** Player Trust Index read endpoint
- [x] **S9-B5** Trust event log endpoint

### Frontend

- [x] **S9-F1** Stats dashboard cards integrated across relevant tabs (Participants, Matches, Overview)
- [x] **S9-F2** Certificate template editor (basic HTML preview)
- [x] **S9-F3** Bulk certificate generation button + download
- [x] **S9-F4** Trust Index display on participant detail drawer

### Validation Criteria

- [x] Stats display accurately across tabs
- [x] Certificate generates as PDF with correct data
- [x] Trust Index reflects historical events

---

## Sprint 10 — RBAC & Economy Integration

**Goal:** Staff role management, granular permissions, DeltaCoin wallet integration.

**PRD Sections:** §10.1–§10.4 (Pillar 9 — RBAC), §11.1–§11.4 (Pillar 10 — Economy)

### Backend — API

- [x] **S10-B1** Staff role assignment endpoints (assign/remove staff to tournament roles)
- [x] **S10-B2** Permission checker middleware for all TOC API endpoints
- [x] **S10-B3** DeltaCoin balance check endpoint
- [x] **S10-B4** DeltaCoin transaction endpoint (entry fees, prizes, bounties)

### Frontend

- [x] **S10-F1** Staff management section in Settings tab: role grid, invite, remove
- [x] **S10-F2** Permission-gated UI: hide/disable actions based on role
- [x] **S10-F3** DeltaCoin balance display in Payments tab
- [x] **S10-F4** Wallet transaction history in participant drawer

### Validation Criteria

- [x] Non-organizer staff see only tabs/actions matching their role
- [x] DeltaCoin entry fees deducted correctly
- [x] Prize distribution uses DeltaCoin when configured

---

## Sprint 11 — Audit Trail & Real-Time Infrastructure

**Goal:** Full audit logging, action versioning, and WebSocket foundation for live updates.

**PRD Sections:** §12.1–§12.4 (Pillar 11 — Audit), §13.1–§13.4 (Pillar 12 — WebSocket)

### Backend

- [x] **S11-B1** Audit log middleware — capture all TOC write operations with user, action, timestamp, diff
- [x] **S11-B2** Audit log API endpoint — `GET /api/toc/<slug>/audit-log/` with filters
- [x] **S11-B3** WebSocket consumer for TOC — `ws/toc/<slug>/` using Django Channels
- [x] **S11-B4** Real-time event dispatch: match score updated, registration approved, status changed → push to connected clients

### Frontend

- [x] **S11-F1** Audit log viewer in Settings tab: filterable action log
- [x] **S11-F2** WebSocket connection manager in `toc-core.js` — auto-connect, reconnect, message dispatch
- [x] **S11-F3** Real-time indicators: live dot on topbar when WebSocket connected, toast on incoming events
- [x] **S11-F4** Tab badges update in real-time via WebSocket push

### Validation Criteria

- [x] All write actions create audit log entries
- [x] WebSocket connects and receives real-time updates
- [x] Multiple operator sessions see live updates simultaneously

---

## Sprint 12 — Polish, Edge Cases & Tier-1 Hardening

**Goal:** Final polish, edge case handling, performance optimization, and Tier-1 esports readiness.

**PRD Sections:** §14 (Cross-Cutting Concerns), §18 (Edge Cases & Tier-1 Requirements)

### Tasks

- [x] **S12-T1** Loading skeleton states for all tabs (shimmer placeholders)
- [x] **S12-T2** Error boundary: graceful error states per tab with retry button
- [x] **S12-T3** Empty states: contextual messaging when tables have zero rows
- [x] **S12-T4** Keyboard accessibility audit: all interactive elements focusable, `aria-*` attributes complete
- [x] **S12-T5** Performance: lazy-load tab content on first visit, debounce search inputs, virtual scroll for large tables
- [x] **S12-T6** Mobile/tablet responsive fallback (sidebar collapses, tables scroll horizontally)
- [x] **S12-T7** Dark mode consistency audit: ensure all components meet WCAG contrast ratios on dark canvas
- [x] **S12-T8** Edge cases from §18: simultaneous organizer edits, stale data warnings, concurrent bracket operations
- [x] **S12-T9** Stress test: TOC with 1000+ registrations, 500+ matches, 50+ disputes
- [x] **S12-T10** Final review: all checkboxes in S0–S11 verified, tracker updated to 100%

### Validation Criteria

- [x] All tabs handle empty state, loading state, and error state gracefully
- [x] Keyboard-only navigation works end-to-end
- [x] TOC performs acceptably with large datasets
- [x] All Sprint 0–11 checkboxes complete

---

## Progress Summary

| Sprint | Status | Completion |
|--------|--------|------------|
| **S0 — Foundation Shell** | ✅ Complete | 23/23 |
| **S1 — Command Center** | ✅ Complete | 24/24 |
| **S2 — Participant Grid** | ✅ Complete | 26/26 |
| **S3 — Participants Advanced** | ✅ Complete | 18/18 |
| **S4 — Financial Operations** | ✅ Complete | 25/25 |
| **S5 — Competition Engine** | ✅ Complete | 25/25 |
| **S6 — Match Operations** | ✅ Complete | 25/25 |
| **S7 — Disputes** | ✅ Complete | 18/18 |
| **S8 — Config & Comms** | ✅ Complete | 27/27 |
| **S9 — Stats & Certificates** | ✅ Complete | 17/17 |
| **S10 — RBAC & Economy** | ✅ Complete | 11/11 |
| **S11 — Audit & Real-Time** | ✅ Complete | 11/11 |
| **S12 — Polish & Hardening** | ✅ Complete | 14/14 |
| **TOTAL** | **✅ ALL COMPLETE** | **264/264** |
