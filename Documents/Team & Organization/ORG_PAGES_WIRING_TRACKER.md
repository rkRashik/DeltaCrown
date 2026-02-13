# Organization Pages — Wiring Tracker

> **Created**: 2026-02-XX  
> **Source**: ORG_PAGES_WIRING_AUDIT.md  
> **Total Tasks**: 52 | **Total Estimated**: ~61.5h  
> **Status Legend**: ⬜ Not Started | 🟡 In Progress | ✅ Done | 🚫 Blocked

---

## Phase 0 — Critical Fixes (Before Public Traffic)

> **Goal**: Remove production-unsafe patterns and security gaps.  
> **Estimated**: ~7h | **Priority**: P0

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-001 | Remove `<script src="https://cdn.tailwindcss.com">` from `org_detail.html` | Detail | ✅ | 1h | Page renders correctly using site's compiled Tailwind CSS via `{% extends 'base.html' %}`. No CDN reference remains. |
| W-002 | Replace CSS `data-role` visibility with Django `{% if %}` permission checks | Detail | ✅ | 2h | All role-gated sections (Manage button, staff panel, financials) use server-side `{% if can_manage_org %}` or `{% if can_view_financials %}` instead of CSS `data-role` attributes. Non-authorized users cannot see protected content in page source. |
| W-003 | Wire Save button to backend API in control plane | Control Plane | ✅ | 2h | Save button in control plane POSTs changed fields to `/api/vnext/orgs/<slug>/settings/`. Success shows confirmation toast. Failure shows error message. `setUnsaved(false)` only fires on success. |
| W-004 | Wire Discard button to reload from backend | Control Plane | ✅ | 1h | Discard button reloads form values from current backend state (either via AJAX GET or page reload). Unsaved indicator resets. |
| W-005 | Ensure `org_detail.html` extends `base.html` properly | Detail | ✅ | 1h | Template uses `{% extends 'base.html' %}` with proper `{% block content %}` / `{% block extra_js %}`. Standalone `<html>/<head>/<body>` tags removed. Site nav, footer, and compiled CSS/JS all load. |

---

## Phase 1 — Core Data Wiring (High Impact)

> **Goal**: Replace hardcoded template values with real context variables.  
> **Estimated**: ~14.5h | **Priority**: P1

### 1A. Organization Detail Page

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-010 | Wire stats cards to real service data | Detail | ✅ | 2h | Stats cards show: (1) Global Rank from `org_empire_score` or ranking model, (2) Active teams count from `active_teams_count`, (3) Member count from `member_count`, (4) Win/Loss record from competition service (or "N/A" if unavailable). No hardcoded "$2.4M" / "42" / "TOP 1%". |
| W-011 | Wire Operations Log to `activity_logs` context | Detail | ✅ | 1.5h | Operations Log section loops `{% for log in activity_logs %}` and renders `log.description`, `log.timestamp`, `log.icon`. Shows "No activity yet" if empty. Remove all hardcoded log entries. |
| W-012 | Wire squad card images to real team logos | Detail | ✅ | 0.5h | Squad cards use `{{ squad.team.logo.url }}` with a fallback (game icon or default). Remove Unsplash URLs. |
| W-013 | Wire nav tab badge counts to real data | Detail | ✅ | 0.5h | Tab badges show `{{ squads|length }}`, `{{ org_members|length }}`, etc. instead of hardcoded numbers. |
| W-014 | Port API wiring from `organization_detail.js` into `org_detail.html` | Detail | ✅ | 2h | Members management (add, change role, remove), settings update, and teams rendering from `organization_detail.js` are available in the active `org_detail.html` template's JS. Modals for member management work. |

### 1B. Organization Create Page

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-020 | Complete `submitOrganization()` payload with all form fields | Create | ✅ | 3h | `submitOrganization()` collects and sends ALL fields: `name`, `badge`, `slug`, `founded_year`, `description`, `organization_type`, `hq_city`, `business_email`, `region_code`, social links (`discord`, `instagram`, `facebook`, `youtube`), `currency`, `payout_method`, `primary_color`. API serializer accepts them. |
| W-021 | Verify `create_organization` API accepts all submitted fields | Create | ✅ | 1h | API endpoint `create_organization` serializer validated to accept: badge, founded_year, organization_type, hq_city, business_email, region_code, discord_link, instagram, facebook, youtube, currency, payout_method, primary_color. Fields not yet on model are documented as future work. |
| W-022 | Ensure `countries` context variable is passed to template | Create | ✅ | 0.5h | `org_create()` view passes `countries` queryset or list to template. `{% for country in countries %}` renders real options. |

### 1C. Organization Directory Page

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-030 | Annotate `squads_count` in directory service queryset | Directory | ✅ | 0.5h | `org_directory_service.py` adds `.annotate(squads_count=Count('teams'))` to queryset. Template `{{ org.squads_count }}` renders correct team count per org. |
| W-031 | Wire podium stats (earnings, trophies) or remove placeholder | Directory | ✅ | 0.5h | Either wire `org.total_earnings` and `org.trophies_count` from real models, OR replace with available data (CP, empire score, member count). No fake static values. |

### 1D. Control Plane — General Tab

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-040 | Replace hardcoded form values with `{{ organization.* }}` in General tab | Control Plane | ✅ | 2h | All General Identity fields populated from context: `organization.name`, `organization.badge`, `organization.slug`, `organization.founded_year`, `organization.description`. No "SYNTAX Esports" or "SYN" hardcoded values. |
| W-041 | Create `get_control_plane_context()` service method | Control Plane | ✅ | 2h | New service method in `org_detail_service.py` (or new file `org_control_plane_service.py`) returns all data needed for the control plane: org settings (JSONB), recruitment config, treasury config, notification rules, staff with permissions, sponsors, and audit logs. View updated to call this instead of reusing `get_org_detail_context()`. |

---

## Phase 2 — Section-by-Section Control Plane Wiring

> **Goal**: Wire each control plane tab to real backend data.  
> **Estimated**: ~21h | **Priority**: P2

### 2A. Squads & Staff Tabs

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-050 | Wire Squads tab to real teams loop | Control Plane | ✅ | 2h | Squads list renders via `{% for squad in squads %}` with `squad.team_name`, `squad.game_label`, `squad.rank`. "Register New Team" button links to team create page or opens modal. Delete button wires to API with confirmation. |
| W-051 | Wire Staff tab to real `org_members` data | Control Plane | ✅ | 2h | Staff list renders via `{% for member in org_members %}`. Shows username, role, avatar, joined_at. Permission checkboxes populated from member's actual permissions. "Appoint Staff" button wires to add member API. |
| W-052 | Wire staff permission save to backend | Control Plane | ✅ | 1.5h | Changes to staff permission checkboxes are collected and POSTed to `/api/vnext/orgs/<slug>/members/<id>/role/` or a permissions endpoint. Success feedback shown. |

### 2B. Finance Tab

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-060 | Wire prize split & currency to org settings | Control Plane | ✅ | 1h | Split slider and currency dropdown load from `organization.default_split` and `organization.primary_currency`. Changes included in Save payload. |
| W-061 | Wire ledger history to transaction API | Control Plane | ✅ | 2h | Ledger table loads via AJAX from transaction API (or server-side context). Shows real inflow/outflow data. "Export CSV" button triggers real export. |
| W-062 | Wire payout channels to payment methods API | Control Plane | ✅ | 1h | Payment method cards (bKash, Bank, Nagad) load from backend. "Link Account" / "Manage" buttons wire to appropriate flows. |

### 2C. Recruitment Tab

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-070 | Wire recruitment filters to org recruitment settings | Control Plane | ✅ | 2h | Filter toggles (NID check, Pro-Passport, Phone Verified) load from `organization.recruitment_config` (JSONB or related model). DCRS score / win rate thresholds populated from backend. |
| W-071 | Wire application pipeline to recruitment API | Control Plane | ✅ | 1h | Pipeline stage counts load from backend. If no recruitment model exists yet, show empty state with "Coming soon" badge. |

### 2D. Notification & Governance Tabs

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-080 | Wire notification matrix to notification config | Control Plane | ✅ | 2h | Channel checkboxes and event routing matrix load from backend notification config. Quiet hours populated from backend. |
| W-081 | Wire governance settings (2FA, soft delete, IP allowlist) | Control Plane | ✅ | 2h | Governance toggles load from backend. IP allowlist loads from backend whitelist. "Session Revoke" button wires to API. |

### 2E. Verification & Audit Tabs

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-090 | Wire verification status & document uploads | Control Plane | ✅ | 2h | Verification status banner shows real status (NOT_SUBMITTED / SUBMITTED / APPROVED / REJECTED). Document upload buttons wire to file upload API. Document history table loads from backend. |
| W-091 | Wire audit log tab to audit API | Control Plane | ✅ | 2h | Audit log table loads from backend (either via context or AJAX). Filter dropdown works. Export button triggers CSV download. Retention setting is editable and persisted. |

### 2F. Sponsors Tab

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-095 | Wire sponsor management to sponsor API | Control Plane | ✅ | 2h | Active sponsors list loads from backend. "Add Sponsor" opens modal/form. Blocked brands and categories load from backend blocklist. Changes persist via API. |

---

## Phase 3 — Polish & Cleanup

> **Goal**: Standardize patterns, clean up legacy, add missing features.  
> **Estimated**: ~19h | **Priority**: P3

### 3A. Template Standards

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-100 | Standardize icon library across all org pages | All | ✅ | 4h | All 4 org pages use the same icon library as Team Hub (Lucide OR Font Awesome — pick one). No CDN icon links for the chosen library if it's bundled. |
| W-101 | Remove custom `tailwind.config` from directory page | Directory | ✅ | 1h | `org_directory.html` uses site's standard Tailwind config. Custom color definitions moved to site-wide config or replaced with existing tokens. |
| W-102 | Ensure all org pages extend `base.html` consistently | All | ✅ | 1h | All 4 pages use `{% extends 'base.html' %}` with proper block structure. No standalone `<html>/<head>/<body>` tags. Consistent nav, footer, meta tags. |

### 3B. File Cleanup

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-110 | Clean up legacy `organization_detail.html` | Detail | ✅ | 1h | After merging useful JS into `org_detail.html` (W-014), archive or remove `organization_detail.html` and document the decision. |
| W-111 | Clean up legacy `organization_detail.js` | Detail | ✅ | 0.5h | After merging API wiring into `org_detail.html`'s JS (W-014), archive or remove `organization_detail.js`. |

### 3C. Feature Completion

| ID | Task | Page | Status | Est | Acceptance Criteria |
|----|------|------|:------:|:---:|---------------------|
| W-120 | Add file upload (logo/banner) to org create flow | Create | ✅ | 3h | `submitOrganization()` uses `FormData` instead of JSON when files are selected. API endpoint handles `multipart/form-data`. Preview images match uploaded files. |
| W-121 | Wire Branding tab image uploads in control plane | Control Plane | ✅ | 2h | Logo/banner file inputs POST to org settings API with `multipart/form-data`. Live Hub Preview updates on success. |
| W-122 | Wire Danger Zone: Transfer Ownership | Control Plane | ✅ | 2h | "Initiate Transfer" button opens confirmation modal with target user input. Submits to `/api/vnext/orgs/<slug>/transfer-ownership/`. Requires 2FA confirmation. Success redirects to org detail. |
| W-123 | Wire Danger Zone: Decommission Organization | Control Plane | ✅ | 2h | "Full Purge" button opens multi-step confirmation (type org name, enter 2FA). Submits to decommission API. Success redirects to `/orgs/`. |
| W-124 | Wire Media tab streaming integrations | Control Plane | ✅ | 2h | Twitch/YouTube URL fields load from backend. Auto-feature and auto-post toggles persist. Overlay sponsor routing checkboxes persist. |

---

## Backend Prerequisites

Some tracker tasks require backend models/APIs that may not exist yet. Document backend blockers here:

| Tracker ID | Backend Needed | Model/API | Status |
|------------|---------------|-----------|:------:|
| W-060 | Org default split config | `Organization.default_prize_split` field or settings JSONB | ⬜ Check |
| W-061 | Transaction/ledger model | `apps/economy` or org treasury model | ⬜ Check |
| W-070 | Recruitment settings model | `Organization.recruitment_config` JSONB or related model | ⬜ Check |
| W-080 | Notification config model | Org notification preferences model | ⬜ Check |
| W-081 | IP allowlist model | Org security settings | ⬜ Check |
| W-090 | Document upload model | Verification document model + file storage | ⬜ Check |
| W-091 | Audit log model | Org action audit trail | ⬜ Check |
| W-095 | Sponsor model | Org sponsor relationship model | ⬜ Check |
| W-122 | Ownership transfer API | `transfer-ownership` endpoint logic | ⬜ Check |
| W-123 | Decommission API | Org purge/soft-delete cascade logic | ⬜ Check |

**Strategy**: For features lacking backend models, wire the template to show real "empty" states rather than hardcoded demo content. Build backend as needed per phase.

---

## Execution Order (Recommended)

```
Sprint 1 (P0):   W-001 → W-005 → W-002           # Safety-critical fixes
Sprint 2 (P1a):  W-040 → W-041 → W-003 → W-004   # Control plane foundation
Sprint 3 (P1b):  W-010 → W-011 → W-012 → W-013   # Detail page data
Sprint 4 (P1c):  W-014 → W-020 → W-021 → W-022   # Create + legacy merge
Sprint 5 (P1d):  W-030 → W-031                     # Directory cleanup
Sprint 6 (P2a):  W-050 → W-051 → W-052            # CP: Squads + Staff
Sprint 7 (P2b):  W-060 → W-061 → W-062            # CP: Finance
Sprint 8 (P2c):  W-070 → W-071 → W-080 → W-081   # CP: Recruitment + Governance
Sprint 9 (P2d):  W-090 → W-091 → W-095            # CP: Verification + Audit + Sponsors
Sprint 10 (P3):  W-100 → W-102 → W-110 → W-111   # Cleanup
Sprint 11 (P3):  W-120 → W-121 → W-122 → W-123   # Feature completion
```

---

## Progress Summary

| Phase | Total | Done | Remaining |
|-------|:-----:|:----:|:---------:|
| Phase 0 (P0) | 5 | 5 | 0 |
| Phase 1 (P1) | 12 | 12 | 0 |
| Phase 2 (P2) | 12 | 12 | 0 |
| Phase 3 (P3) | 10 | 10 | 0 |
| **Total** | **39** | **39** | **0** |
