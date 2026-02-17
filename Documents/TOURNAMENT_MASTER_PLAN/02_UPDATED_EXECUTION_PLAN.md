# Updated Execution Plan v2

*Updated: February 17, 2026*
*Supersedes: 01_EXECUTION_ROADMAP.md (still valid as architectural reference)*
*Incorporates: User requirements from Feb 17 session + Audit Reports 01-05*

---

## What Changed From v1

| Change | Impact |
|--------|--------|
| **Django Admin Modernization** added | New Phase 1.5 — Install & configure Django Unfold for SaaS-grade admin UX |
| **Tournament frontend full rebuild** confirmed | Phase 4 expanded — archive ALL old templates/static, rebuild from scratch using Tailwind CSS + vanilla JS + HTML5 |
| **Demo templates created by user** | `list_demo.html` and `tournamnt_detail_demo.html` serve as design reference for Phase 4 |
| **Phase numbering adjusted** | Admin work inserted at the right time (after cleanup, before service wiring touches views) |
| **Tracker compliance enforced** | Every task updates TRACKER.md before and after completion |

---

## Phase Overview

| Phase | Name | Duration | Description |
|-------|------|----------|-------------|
| **0** | Cleanup | 3-5 days | Remove dead code, fix broken refs, consolidate duplicates |
| **1** | Foundation Wiring | 1 week | Wire adapters (Economy, Notification, Team, User), publish events |
| **1.5** | Admin Modernization | 3-5 days | Install Django Unfold, configure all admin classes, custom dashboard, rich widgets |
| **2** | Service Consolidation | 2 weeks | Unify duplicate services, complete Swiss brackets |
| **3** | Views & URL Restructure | 2 weeks | Rewire views → tournament_ops services, clean URL patterns |
| **4** | Frontend Rebuild | 2-3 weeks | Archive old templates/static, rebuild from scratch (Tailwind + vanilla JS + HTML5) |
| **5** | Lifecycle & Automation | 1-2 weeks | State machine, Celery tasks, completion pipeline |
| **6** | Testing & Hardening | 1-2 weeks | Unit + integration + template tests |

**Total: ~11-16 weeks**

---

## Phase 0: Cleanup (3-5 days)

No changes from v1. Tasks:

| ID | Task | Notes |
|----|------|-------|
| 0.1 | Remove legacy Game model from tournaments | Partially done (managed=False set, imports redirected). Need to fully remove the class. |
| 0.2 | Remove all riot_id/steam_id references | ~30+ references across registration wizard, team registration, tests, autofill |
| 0.3 | Remove backup/deprecated files | `views_old_backup.py`, `registration_demo_backup/`, `marketplace/` templates |
| 0.4 | Consolidate duplicate services | Two registration services, two match services |
| 0.5 | Consolidate duplicate models | Two dispute systems, two staffing systems |
| 0.6 | Fix cross-app FK violations (FK → IntegerField) | Any remaining direct FKs to frozen apps |
| 0.7 | Fix tournament_ops adapter field bugs | Known field mismatches in adapters |

---

## Phase 1: Foundation Wiring (1 week) 

No changes from v1. Tasks:

| ID | Task | Notes |
|----|------|-------|
| 1.1 | Wire EconomyAdapter to economy.services | `charge()` → `debit()`, `refund()` → `credit()`, `get_balance()` |
| 1.2 | Wire NotificationAdapter to notifications.services | Map to `notify()` with 30+ existing types |
| 1.3 | Verify & fix TeamAdapter (organizations) | Dual-source: organizations (primary) + legacy teams (fallback) |
| 1.4 | Verify & fix UserAdapter (GameProfile) | Replace all profile.riot_id with GameProfile queries |
| 1.5 | Wire event publishing (EventBus) | Publish `match.completed`, lifecycle events from tournaments app |
| 1.6 | Add Celery beat task scheduling | 3 tasks: opponent_response_reminder, dispute_escalation, auto_confirm_submission |

---

## Phase 1.5: Admin Modernization (3-5 days) — NEW

### Why Here?
- After cleanup (Phase 0) so we're not decorating dead code
- After adapter wiring (Phase 1) so admin actions can use real services
- Before service consolidation (Phase 2) so admins can test/manage data during development
- The admin panel is a daily tool — modernizing it early pays dividends throughout all later phases

### Goal
Transform Django Admin from "raw database viewer" into a modern SaaS-grade management console using **Django Unfold** (the leading Django admin theme in 2025-2026, maintained, Tailwind-based, highly configurable).

### Tasks

| ID | Task | Description |
|----|------|-------------|
| 1.5.1 | Install & configure Django Unfold | Install package, add to INSTALLED_APPS, configure base theme (colors, branding, sidebar) |
| 1.5.2 | Custom Admin Dashboard | Build visual command center: tournament stats, recent registrations, match activity, payment overview, system health |
| 1.5.3 | Tournament Admin Polish | Status badges (Live=green pulse, Cancelled=red, Draft=gray), game color coding, inline expandable sections, organizer quick-links |
| 1.5.4 | Rich Form Widgets | WYSIWYG for description fields, searchable autocomplete for Game/User selects, JSON field GUI widgets (prize distribution, custom configs) |
| 1.5.5 | All App Admin Alignment | Apply Unfold styling to ALL registered apps (economy, games, organizations, user_profile, etc.), consistent look across the board |
| 1.5.6 | Admin User Guide | Contextual help tooltips, field descriptions, inline documentation so non-technical admins can navigate |

### Technical Approach
- **Package**: `django-unfold` (Tailwind-based, supports custom components, active development)
- **Custom widgets**: Unfold's `UnfoldAdminTextareaWidget` + CKEditor5 for rich text, `UnfoldAdminSelectWidget` for searchable dropdowns
- **JSON fields**: Custom widget or `django-jsoneditor` / inline key-value pair editor
- **Dashboard**: Unfold's built-in dashboard callback system with custom cards
- **Status badges**: Unfold's `display_` decorators with colored badges

---

## Phase 2: Service Consolidation (2 weeks)

No changes from v1. Tasks:

| ID | Task | Notes |
|----|------|-------|
| 2.1 | Unified Registration Service | Merge old (1,710 lines) + new (378 lines) into one clean service |
| 2.2 | Unified Match Service | Single service with event publishing |
| 2.3 | Unified Bracket Service + Swiss completion | Complete Swiss Rounds 2+ |
| 2.4 | Unified Check-In Service | |
| 2.5 | Unified Analytics Service | |
| 2.6 | Unified Staff Service | Pick Phase 7 models, deprecate OG models |

---

## Phase 3: Views & URL Restructure (2 weeks)

No changes from v1. Tasks:

| ID | Task | Notes |
|----|------|-------|
| 3.1 | Create new view files (clean structure) | |
| 3.2 | Rewrite urls.py (clean URL patterns) | |
| 3.3 | Registration view rewrite | Use GameProfile for auto-fill |
| 3.4 | Organizer hub views | |
| 3.5 | Verify all URLs (200/302/403 responses) | |

---

## Phase 4: Frontend Rebuild (2-3 weeks) — EXPANDED

### What Changed
- **Complete rebuild from scratch** — not patching old templates
- **All old templates archived** first (moved to `backups/template_archives/tournaments_legacy/`)
- **All old static files archived** (moved to `backups/static_archives/tournaments_legacy/`)
- **Design reference**: User's demo templates set the visual direction (glassmorphism, dark theme, Tailwind, Lucide icons, game-aware color theming)

### Design System (from user's demos)
- **Colors**: `dc-cyan (#06b6d4)`, `dc-purple (#8b5cf6)`, `dc-gold (#facc15)`, dark backgrounds (#050505, #0a0a0a)
- **Typography**: Inter (body), Space Grotesk (display), Rajdhani (gaming accents)
- **Patterns**: Glassmorphism, noise texture overlay, game-color theming via CSS variables
- **Icons**: Lucide icons
- **Framework**: Tailwind CSS (CDN for dev, compiled for prod)
- **JS**: Vanilla JS only (no jQuery, no React/Vue)

### Tasks

| ID | Task | Description |
|----|------|-------------|
| 4.0 | Archive all old tournament frontend files | Move 158 templates + 49 static files to `backups/` |
| 4.1 | Build component library (partials) | Base layout, navbar, cards, badges, modals, status pills, game icons, form components |
| 4.2 | Tournament List page (landing) | Hero carousel, game filter sidebar, tournament cards grid, "My Tournaments" sidebar — reference: `list_demo.html` |
| 4.3 | Tournament Detail page | Cinematic hero, tabbed navigation (Overview, Participants, Bracket, Rules, Media), registration CTA — reference: `tournamnt_detail_demo.html` |
| 4.4 | Registration wizard | Multi-step with progress, GameProfile auto-fill, persistent draft, payment upload |
| 4.5 | Lobby & match pages | Check-in, match cards, live score display, result submission |
| 4.6 | Bracket & standings views | Visual bracket (single/double elim), group stage tables, Swiss pairings |
| 4.7 | Organizer dashboard (10+ pages) | Overview, participants, brackets, matches, payments, disputes, announcements, settings, health |
| 4.8 | Player section | My tournaments, my matches, my results, registration status |
| 4.9 | Archive view | Past tournaments with search/filter |
| 4.10 | Mobile responsiveness pass | All pages tested on mobile/tablet/desktop, touch-friendly |

---

## Phase 5: Lifecycle & Automation (1-2 weeks)

No changes from v1. Tasks:

| ID | Task | Notes |
|----|------|-------|
| 5.1 | Tournament state machine service | |
| 5.2 | Scheduled transitions (Celery) | |
| 5.3 | Tournament completion pipeline | |
| 5.4 | Archive generation | |

---

## Phase 6: Testing & Hardening (1-2 weeks)

No changes from v1. Tasks:

| ID | Task | Notes |
|----|------|-------|
| 6.1 | Adapter unit tests | |
| 6.2 | Service integration tests | |
| 6.3 | View tests | |
| 6.4 | Template rendering tests | All new templates render without errors |
| 6.5 | Lifecycle integration test (end-to-end) | |

---

## Execution Rules

1. **TRACKER.md is the single source of truth** — update it before starting and after completing every task
2. **No task starts without marking it `🔄 In Progress` in the tracker**
3. **No task is "done" until marked `✅ Done` with notes in the tracker**
4. **Files Changed Log** in TRACKER.md is updated after every task
5. **Demo templates** (`My drafts/tournament_demo/`) are design references, not production code — production templates go in `templates/tournaments/`
6. **Every phase has a verification step** before moving to the next phase

---

## Quick Reference: What Gets Archived in Phase 4.0

### Templates to Archive (158 files)
Everything currently under `templates/tournaments/` except:
- Keep `emails/` (notification templates are still valid)
- Move everything else to `backups/template_archives/tournaments_legacy_feb2026/`

### Static Files to Archive (49 files)
- `static/tournaments/` → all files
- `static/siteui/tournament-*.css`, `tournaments-*.css` → all files
- `static/siteui/tournament-*.js`, `tournaments-*.js` → all files  
- `static/js/tournament_detail.js`, `tournament-card-dynamic.js`, `tournament-detail-modern.js`, `tournaments-v7-polish.js`
- `static/css/team-detail/tabs/tournaments-enhanced.css`
- Move all to `backups/static_archives/tournaments_legacy_feb2026/`

### What Stays
- `templates/tournaments/emails/` — notification email templates
- `static/admin/js/tournament_admin.js` — admin JS (will be updated in Phase 1.5)
- `apps/tournaments/templatetags/` — template tags (will be updated for new templates)
