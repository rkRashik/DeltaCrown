# Organization Pages — Frontend-Backend Wiring Audit

> **Date**: 2026-02-XX  
> **Scope**: 4 organization pages — directory, create, detail, control plane  
> **Auditor**: Engineering Session  
> **Verdict**: 70% of template content is hardcoded/placeholder. Only directory page is mostly wired.

---

## Executive Summary

| Page | URL | Wiring Score | Severity |
|------|-----|:----------:|:--------:|
| Org Directory | `/orgs/` | **75%** | 🟡 Low |
| Org Create | `/orgs/create/` | **60%** | 🟡 Medium |
| Org Detail | `/orgs/<slug>/` | **25%** | 🔴 High |
| Org Control Plane | `/orgs/<slug>/control-plane/` | **5%** | 🔴 Critical |

**Architecture**: `apps/organizations/` — views, services, models, API, permissions all exist.  
~40+ API endpoints are already built in `apps/organizations/api/urls.py`. The backend infrastructure is far more complete than the templates suggest — the gap is **template ↔ backend integration**, not missing backend logic.

---

## 1. Organization Directory — `/orgs/`

**Files**:
- Template: `templates/organizations/org/org_directory.html` (376 lines)
- View: `apps/organizations/views/org_directory.py` → `org_directory()`
- Service: `apps/organizations/services/org_directory_service.py` → `get_directory_context()`

### What's WIRED ✅

| Feature | Implementation | Notes |
|---------|---------------|-------|
| Search | `?q=` param → filter by org name | Service correctly chains `.filter(name__icontains=q)` |
| Region filter | `?region=` param | Service filters by `profile__headquarters_region` |
| Pagination | django `Paginator(queryset, per_page=12)` | `page_obj` passed to template, prev/next links work |
| Top 3 Podium | Real org data (`org.name`, `org.logo`, `org.ceo`) | `select_related('ranking', 'profile', 'ceo')` |
| Org Card Loop | `{% for org in page_obj %}` | Real names, slugs, regions, member_count |
| Links | `{% url 'organizations:org_create' %}`, `{% url 'organizations:organization_detail' org.slug %}` | Correct URL names |

### What's BROKEN / HARDCODED 🔴

| Issue | Location | Detail | Fix Effort |
|-------|----------|--------|:----------:|
| `squads_count` not annotated | Template uses `{{ org.squads_count }}` but service doesn't annotate it | Will always render as empty/0 | Small |
| Custom `tailwind.config` block | `org_directory.html` lines 10-50 | Standalone `<script>tailwind.config = {...}</script>` instead of site's shared config | Medium |
| Font Awesome CDN | `<link>` tag in `<head>` | Site standard is Lucide icons; this page uses FA exclusively | Medium |
| Pagination range hack | `{% for i in page_obj.paginator.page_range %}` mixed with `make_list` | Works for small counts but may break for 100+ pages | Small |

### Missing Backend Data

- `squads_count`: Needs `annotate(squads_count=Count('teams'))` in service queryset
- `total_earnings`: Referenced in template but not in service (shows "$0")
- `trophies_count`: Visual placeholder in podium, no backend field

---

## 2. Organization Create — `/orgs/create/`

**Files**:
- Template: `templates/organizations/org/org_create.html` (730 lines)
- View: `apps/organizations/views/org.py` → `org_create()`
- JS: `static/organizations/org/org_create.js` (569 lines)
- API: `apps/organizations/api/` → `create_organization` endpoint

### What's WIRED ✅

| Feature | Implementation | Notes |
|---------|---------------|-------|
| 5-step wizard navigation | JS `goToStep()` | Steps: Identity → Operations → Treasury → Branding → Ratification |
| Live dossier updates | `org_create.js` → `updateDossierField()` | Name, ticker, slug, region, currency flow to live preview |
| Name validation | `debouncedValidate('name', ...)` → `GET /api/vnext/orgs/validate-name/` | Real-time uniqueness check via API |
| Badge validation | `debouncedValidate('badge', ...)` → `GET /api/vnext/orgs/validate-badge/` | Real-time uniqueness check via API |
| Slug validation | `debouncedValidate('slug', ...)` → `GET /api/vnext/orgs/validate-slug/` | Real-time uniqueness check via API |
| Form submission | `submitOrganization()` → `POST /api/vnext/organizations/create/` | `demoMode: false` in config; real backend call |
| Error handling | `handleFieldErrors()` maps backend field errors to form fields | Navigates to step containing the error |
| Image previews | `previewImage()` for logo and banner | Client-side preview before upload |
| CSRF token | `getCsrfToken()` from hidden form field | Properly included in API calls |
| Config injection | `window.ORG_CREATE_CONFIG` set from template | URLs, demo mode flag, CSRF token |

### What's BROKEN / HARDCODED 🔴

| Issue | Location | Detail | Fix Effort |
|-------|----------|--------|:----------:|
| Region hardcoded to "Bangladesh" | `org_create.html` ~line 150 | `selectedText` defaults to "Bangladesh" in dossier; region detection is not dynamic from user profile | Small |
| Payload only sends `name`, `slug`, `branding` | `org_create.js` line 402-410 | MANY form fields collected but NOT submitted: `organization_type`, `hq_city`, `business_email`, `trade_license`, `discord_link`, `instagram`, `facebook`, `youtube`, `currency`, `payout_method` | **Large** |
| Treasury step fields not submitted | Step 3 collects `walletCurrency`, `payoutMethod`, payout details | None of these are included in the `submitOrganization()` payload | Medium |
| Operations step fields not submitted | Step 2 collects `organization_type`, social links, HQ info | These exist in the UI but the JS only sends `name + slug + branding` | Medium |
| Logo/banner not uploaded | File inputs exist in Step 4 | `submitOrganization()` doesn't create `FormData` — only sends JSON, no file upload | Medium |
| Country dropdown | `org_create.html` | Template has `{% for country in countries %}` but view only passes `games` and `user_organizations` — `countries` may be missing from context | Small |
| Font Awesome CDN | `<head>` section | Same issue as directory — not using site Lucide standard | Low |

### Submission Gap Analysis

**Fields collected in UI but NOT in `submitOrganization()` payload:**

```
Step 1 (Identity):    name ✅, badge ❌, slug ✅, founded_year ❌, manifesto ✅ (as description)
Step 2 (Operations):  organization_type ❌, hq_city ❌, business_email ❌, trade_license ❌,
                      discord ❌, instagram ❌, facebook ❌, youtube ❌
Step 3 (Treasury):    currency ❌, payout_method ❌, payout_details ❌
Step 4 (Branding):    primary_color ✅, logo_file ❌, banner_file ❌
Step 5 (Ratification): terms_accepted ❌ (only client-side check)
```

**API endpoint `create_organization`** needs to be audited to confirm which fields it actually accepts and persists.

---

## 3. Organization Detail — `/orgs/<slug>/`

**Files**:
- Template: `templates/organizations/org/org_detail.html` (868 lines)
- View: `apps/organizations/views/org.py` → `organization_detail()`
- Service: `apps/organizations/services/org_detail_service.py` → `get_org_detail_context()`
- JS: `static/organizations/org/org_detail.js` (56 lines — nav/scroll only)
- Legacy template: `templates/organizations/org/organization_detail.html` (312 lines — NOT used by view)
- Legacy JS: `static/organizations/org/organization_detail.js` (468 lines — has real API calls but wrong template)

### What's WIRED ✅

| Feature | Implementation | Notes |
|---------|---------------|-------|
| Hero: Org name | `{{ organization.name }}` | Real data from context |
| Hero: Logo | `{{ organization.logo.url }}` with fallback | Conditional display |
| Hero: Banner | `{{ organization.banner.url }}` with fallback | Conditional display |
| Hero: Description | `{{ organization.description }}` | Real data |
| Hero: Country | `{{ organization.country }}` | Real data |
| Hero: Website | `{{ organization.website }}` | Real data, conditional |
| Hero: Socials | `{{ organization.twitter }}`, `{{ organization.discord }}`, etc. | Links render from model fields |
| Hero: Verified badge | `{% if organization.is_verified %}` | Proper conditional |
| Squads section | `{% for squad in squads %}` → `squad.team_name`, `squad.game_label` | Loops real teams from service |
| Squad rank | `squad.rank`, `squad.tier` | From CompetitionService (may be null) |
| Permission flag | `can_manage_org` | From `get_org_detail_context()` via centralized permissions |
| "Manage" link | `{% url 'organizations:org_control_plane' organization.slug %}` | Correct URL target |

### What's HARDCODED 🔴 (Critical)

| Issue | Location | Detail | Fix Effort |
|-------|----------|--------|:----------:|
| **Tailwind CDN** | Line 6 | `<script src="https://cdn.tailwindcss.com">` — **PRODUCTION UNSAFE**, no tree-shaking, blocking render | **Critical** |
| Stats cards: Earnings | ~Line 250 | `$2.4M` hardcoded text | Medium |
| Stats cards: Trophies | ~Line 260 | `42` hardcoded text | Medium |
| Stats cards: Global Rank | ~Line 240 | `TOP 1%` hardcoded text | Medium |
| Stats cards: Record | ~Line 270 | `187W / 23L` hardcoded text | Medium |
| Squad card images | ~Line 350+ | `src="https://images.unsplash.com/..."` hardcoded Unsplash URLs | Small |
| Operations Log section | ~Line 450+ | Likely all hardcoded entries | Large |
| Media section | ~Line 550+ | Likely all hardcoded stream/video data | Large |
| Financials section | ~Line 650+ | Likely all hardcoded treasury data | Large |
| Role-based visibility | CSS `data-role="..."` attributes | Uses CSS display rules instead of Django `{% if %}` permission checks — fragile, client-side only | Medium |
| Nav tab counts | Badge numbers (e.g., "3" squads) | Hardcoded numbers, not `{{ squads|length }}` | Small |
| Font Awesome CDN | `<head>` | Not using site Lucide standard | Low |

### Service Context vs Template Usage

**Context provided by `org_detail_service.py`:**
```python
{
    'organization': Organization,        # ✅ Used in hero
    'teams': [Team...],                  # ⚠️ Available but template uses 'squads' 
    'teams_count': int,                  # ❌ NOT used (hardcoded in template)
    'active_teams_count': int,           # ❌ NOT used
    'squads': [{team, team_name, ...}],  # ✅ Used in Active Squads loop
    'org_empire_score': int|None,        # ❌ NOT used (hardcoded stats)
    'org_members': [Membership...],      # ❌ NOT used (staff section hardcoded)
    'member_count': int,                 # ❌ NOT used
    'activity_logs': [],                 # Empty placeholder — NOT wired
    'staff_members': [],                 # Empty placeholder — NOT wired
    'streams': [],                       # Empty placeholder — NOT wired
    'can_manage_org': bool,              # ✅ Used for Manage button
    'ui_role': str,                      # ⚠️ Available but template uses CSS data-role
}
```

**Conclusion**: Service returns real data that the template ignores in favor of hardcoded values.

### Legacy Template Conflict

There are **two** org detail templates:
1. `org_detail.html` (868 lines) — **Active**, used by view. Mostly hardcoded.
2. `organization_detail.html` (312 lines) — **Inactive**. Uses `{{ org.name }}`, has modal system, tabs. Paired with `organization_detail.js` (468 lines) which has **real API wiring** (add member, change role, remove member, update settings via fetch).

The inactive `organization_detail.html` + `organization_detail.js` actually has BETTER backend wiring than the active template. Consider:
- **Option A**: Merge the wired JS logic from `organization_detail.js` into `org_detail.html`
- **Option B**: Port the visual design from `org_detail.html` into the wired `organization_detail.html`

---

## 4. Organization Control Plane — `/orgs/<slug>/control-plane/`

**Files**:
- Template: `templates/organizations/org/org_control_plane.html` (2264 lines)
- View: `apps/organizations/views/org.py` → `org_control_plane()`
- Service: Reuses `org_detail_service.get_org_detail_context()` (read-only context)
- JS: Inline `<script>` block at bottom (~100 lines — tab switching, unsaved indicator, image preview, split slider)

### What's WIRED ✅

| Feature | Implementation | Notes |
|---------|---------------|-------|
| Permission gate | View checks `can_access_control_plane()` | Redirects to org detail if unauthorized |
| Tab switching | JS `switchTab()` with hash routing | `history.replaceState` updates URL hash |
| Unsaved changes indicator | `.track-change` class → `setUnsaved(true)` | Detects form changes but cannot save them |
| Split slider labels | `splitRange` input → `orgTakeLabel`/`playerTakeLabel` | Visual-only, not persisted |
| Image preview | `previewImage()` for logo and banner | Client-side only, no upload API |
| Color picker sync | `primaryColor` → `primaryHex` text | Visual-only |

### What's HARDCODED 🔴 (CRITICAL — Nearly Everything)

This is the most severe page. **2264 lines of template with virtually zero Django template variables in form inputs.**

#### General Identity Tab (Lines 80-310)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Organization Name | `value="SYNTAX Esports"` | `value="{{ organization.name }}"` |
| Badge / Ticker | `value="SYN"` | `value="{{ organization.badge }}"` |
| Slug | `value="syntax-official"` | `value="{{ organization.slug }}"` |
| Founded Year | `value="2024"` | `value="{{ organization.founded_year }}"` |
| Manifesto textarea | Hardcoded 3-paragraph text about SYNTAX | `{{ organization.description }}` |
| Meta Title | Placeholder only | `value="{{ organization.meta_title }}"` |
| Meta Description | Placeholder only | `{{ organization.meta_description }}` |
| SEO Keywords | Placeholder only | `value="{{ organization.meta_keywords }}"` |

#### Branding Tab (Lines 310-490)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Logo image | DiceBear identicon URL | `{{ organization.logo.url }}` |
| Banner image | Unsplash stock photo | `{{ organization.banner.url }}` |
| Hub preview org name | `"SYNTAX Esports ✓"` | `{{ organization.name }}` |
| Hub preview URL | `"deltacrown.gg/org/syntax-official"` | Dynamic slug |
| Primary Color | `value="#FFD700"` | `value="{{ organization.primary_color\|default:'#FFD700' }}"` |

#### Squads Tab (Lines 490-610)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Squad 1 | "Protocol V (Valorant)" with icon URL | `{% for squad in squads %}` loop |
| Squad 2 | "Syntax FC (eFootball)" with FA icon | Same loop |
| DCRS Rank text | "#1 Regional • 5 Active Members" | `{{ squad.rank }}` |
| Register New Team button | No action | Wire to team create API |
| Buyout values | `value="50000"`, `value="120000"` etc. | Backend org settings |
| Transfer window selects | `<option>Open (Always)</option>` | Backend org policy |

#### Recruitment Tab (Lines 610-800)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| All filter toggles | Hardcoded checked/unchecked | Backend recruitment settings |
| DCRS Score threshold | `value="1500"` | `{{ org.recruitment_min_dcrs }}` |
| Win Rate threshold | `value="70"` | `{{ org.recruitment_min_winrate }}` |
| Application pipeline stages | Hardcoded 4-stage pipeline | From backend config (JSONB) |
| Contract templates | "Standard Player Agreement (v2)" etc. | From backend document store |

#### Staff Tab (Lines 800-1100)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Staff card 1 | "Tactical_X" - General Manager | `{% for member in org_members %}` |
| Staff card 2 | "EagleEye_101" - Lead Scout | Same loop |
| Avatars | DiceBear URLs | `{{ member.user.avatar.url }}` |
| Permission checkboxes | Hardcoded checked/unchecked | Backend role permissions |
| Appointment dates | "Dec 12, 2025" / "Jan 02, 2026" | `{{ member.joined_at }}` |
| Approval rules | Hardcoded select defaults | Backend governance settings |
| Role templates | General Manager, Lead Scout, Finance Officer | From backend if custom roles exist |

#### Finance Tab (Lines 1100-1450)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Prize split slider | `value="20"` (20% org / 80% player) | Backend split config |
| Currency select | "BDT" selected | `{{ organization.primary_currency }}` |
| Per-team overrides | Protocol V 10/90, Syntax FC 0/100 | Backend per-team rules |
| Payroll frequency | "Monthly" selected | Backend payroll config |
| Auto-pay day | `value="25"` | Backend payroll config |
| Freeze threshold | `value="15000"` | Backend treasury config |
| Salary pools | "40000" / "8000" | Backend payroll pools |
| Ledger history table | 5 hardcoded transactions | `{% for tx in transactions %}` from API |
| Payout channels | bKash `****5928`, Nagad, Bank | Backend payment methods |
| Daily withdrawal cap | `value="50000"` | Backend treasury policy |

#### Sponsors Tab (Lines 1450-1600)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Sponsor entries | "Logitech" (Primary), "Energy Partner" (Draft) | `{% for sponsor in sponsors %}` |
| Blocked brands | "Razer", "SteelSeries" chips | Backend blocklist |
| Blocked categories | "Competitor Peripherals" | Backend blocklist |

#### Media Tab (Lines 1600-1700)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Twitch/YouTube URLs | Placeholder text only | `value="{{ organization.twitch_url }}"` |
| Stream overlay settings | Hardcoded toggles | Backend media config |

#### Notifications Tab (Lines 1700-1800)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Channel checkboxes | Hardcoded checked/unchecked | Backend notification config |
| Quiet hours | `value="23:00"` / `value="08:00"` | Backend notification config |
| Event routing matrix | Hardcoded checkbox states | Backend notification rules |

#### Governance Tab (Lines 1800-1900)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| IP allowlist entries | "103.12.34.0/24", "45.11.92.10" | Backend security config |
| Soft delete window | "24 hours" selected | Backend governance config |

#### Verification Tab (Lines 1900-2050)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Verification status | "NOT SUBMITTED" | `{{ organization.verification_status }}` |
| Document history | 2 "Missing" rows | Backend document store |

#### Audit Tab (Lines 2050-2150)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Audit log entries | 5 hardcoded rows | `{% for log in audit_logs %}` from API |
| Retention setting | "90 days" selected | Backend audit config |

#### Danger Zone (Lines 2150-2200)
| Field | Hardcoded Value | Should Be |
|-------|----------------|-----------|
| Transfer Ownership button | No action | Wire to ownership transfer API |
| Decommission button | No action | Wire to org purge API (with 2FA) |

### Save/Discard Buttons

```javascript
saveBtn.addEventListener("click", () => {
    // TODO: wire to backend    ← THIS IS THE SINGLE BIGGEST GAP
    setUnsaved(false);
});

discardBtn.addEventListener("click", () => {
    // TODO: reload values from backend
    setUnsaved(false);
});
```

The Save button **resets the "unsaved" indicator without saving anything**. The Discard button **doesn't reload from backend**.

### View Context Gap

The `org_control_plane` view reuses `get_org_detail_context()` — a service designed for the **read-only detail page**. It returns:
- `organization`, `teams`, `squads`, `org_members`, `permissions`

But the control plane needs MUCH more:
- Org settings (recruitment config, treasury config, notification rules, governance policies)
- Sponsor data, blocked brands
- Payment methods, payroll config
- Audit logs, verification documents
- Staff permission matrices

**None of these exist in the current service context.**

---

## Cross-Cutting Issues

### 1. Tailwind CDN Usage (CRITICAL)

| Page | Uses CDN? | Impact |
|------|-----------|--------|
| org_directory.html | Custom `tailwind.config` block | Medium — divergent from site theme |
| org_create.html | Via site base template (`{% extends %}`) | ✅ OK if base uses compiled CSS |
| org_detail.html | `<script src="https://cdn.tailwindcss.com">` | 🔴 PRODUCTION UNSAFE |
| org_control_plane.html | Via `{% extends 'base.html' %}` | ✅ OK |

**Fix**: Remove all CDN references. Ensure all 4 pages use the site's compiled Tailwind build.

### 2. Icon Library Inconsistency

| Page | Icon Library |
|------|-------------|
| org_directory.html | Font Awesome (CDN) |
| org_create.html | Font Awesome (CDN) |
| org_detail.html | Font Awesome (CDN) |
| org_control_plane.html | Font Awesome (CDN) |
| Team Hub (reference) | Lucide |

All org pages use Font Awesome while the Team Hub uses Lucide. Decide on one standard.

### 3. Two Competing Detail Page Implementations

- **Active**: `org_detail.html` (868 lines) — Beautiful design, mostly hardcoded
- **Inactive**: `organization_detail.html` (312 lines) + `organization_detail.js` (468 lines) — Simpler design, fully wired with real API calls (members CRUD, settings update, teams rendering)

The inactive version has working:
- `handleAddMember()` → `POST /api/vnext/orgs/<slug>/members/add/`
- `handleChangeRole()` → `POST /api/vnext/orgs/<slug>/members/<id>/role/`
- `handleRemoveMember()` → `POST /api/vnext/orgs/<slug>/members/<id>/remove/`
- `handleUpdateSettings()` → `POST /api/vnext/orgs/<slug>/settings/`
- `renderMembers()` and `renderTeams()` from `window.ORG_DATA`

**Recommendation**: Port the API wiring from `organization_detail.js` into `org_detail.html`. The visual design of `org_detail.html` is superior but its data layer is empty.

### 4. Backend API Endpoints Already Exist

From `apps/organizations/api/urls.py` (~40+ endpoints), many are already built:

```
POST   /api/vnext/organizations/create/
GET    /api/vnext/orgs/validate-name/
GET    /api/vnext/orgs/validate-badge/
GET    /api/vnext/orgs/validate-slug/
POST   /api/vnext/orgs/<slug>/settings/
POST   /api/vnext/orgs/<slug>/members/add/
POST   /api/vnext/orgs/<slug>/members/<id>/role/
POST   /api/vnext/orgs/<slug>/members/<id>/remove/
GET    /api/vnext/orgs/<slug>/members/
POST   /api/vnext/orgs/<slug>/leave/
POST   /api/vnext/orgs/<slug>/transfer-ownership/
POST   /api/vnext/orgs/<slug>/teams/create/
```

The wiring work is primarily **template-side** — connecting forms and JS to these existing endpoints.

### 5. Permission System

Centralized permission system in `apps/organizations/permissions.py` is solid:
- `get_org_role(user, org)` → CEO / MANAGER / ADMIN / STAFF / MEMBER / NONE
- `can_access_control_plane(user, org)` → bool
- `can_manage_org(user, org)` → bool
- `can_view_financials(user, org)` → bool
- `can_manage_staff(user, org)` → bool

**Issue**: `org_detail.html` uses **CSS-based** role visibility (`data-role` attributes) instead of Django `{% if can_manage_org %}` checks. This is client-side only and trivially bypassable.

---

## Priority Matrix

### P0 — Must Fix Before Any Public Traffic

| # | Issue | Page | Effort |
|---|-------|------|:------:|
| 1 | Remove Tailwind CDN from `org_detail.html` | Detail | 1h |
| 2 | Replace CSS role visibility with Django `{% if %}` | Detail | 2h |
| 3 | Wire Save/Discard buttons to API | Control Plane | 4h |

### P1 — Wire Core Data (High Impact)

| # | Issue | Page | Effort |
|---|-------|------|:------:|
| 4 | Replace all hardcoded form values with `{{ org.* }}` vars | Control Plane | 4h |
| 5 | Wire stats cards to real data (empire score, teams_count, etc.) | Detail | 3h |
| 6 | Complete `submitOrganization()` payload (all form fields) | Create | 3h |
| 7 | Add `squads_count` annotation to directory service | Directory | 30m |
| 8 | Wire squads tab to real data loop | Control Plane | 2h |
| 9 | Wire staff tab to real `org_members` data | Control Plane | 2h |

### P2 — Complete Sections

| # | Issue | Page | Effort |
|---|-------|------|:------:|
| 10 | Wire finance ledger to transaction API | Control Plane | 4h |
| 11 | Wire operations log to activity service | Detail | 3h |
| 12 | Wire audit log tab to audit API | Control Plane | 3h |
| 13 | Wire recruitment tab to recruitment settings API | Control Plane | 3h |
| 14 | Wire notification matrix to notification config API | Control Plane | 2h |
| 15 | Wire sponsor management to sponsor API | Control Plane | 3h |
| 16 | Wire verification tab to document upload API | Control Plane | 3h |

### P3 — Polish & Cleanup

| # | Issue | Page | Effort |
|---|-------|------|:------:|
| 17 | Consolidate icon library (FA vs Lucide) | All | 4h |
| 18 | Remove custom tailwind.config from directory | Directory | 1h |
| 19 | Clean up unused `organization_detail.html` + merge useful JS | Detail | 2h |
| 20 | Add file upload support to org create (logo/banner) | Create | 3h |
| 21 | Wire Danger Zone buttons (ownership transfer, decommission) | Control Plane | 4h |
| 22 | Wire media tab (Twitch/YouTube integration) | Control Plane | 2h |
| 23 | Wire governance tab (IP allowlist, soft delete, 2FA) | Control Plane | 3h |

---

## Estimated Total Effort

| Priority | Tasks | Estimated Hours |
|----------|:-----:|:---------------:|
| P0 | 3 | ~7h |
| P1 | 6 | ~14.5h |
| P2 | 7 | ~21h |
| P3 | 7 | ~19h |
| **Total** | **23** | **~61.5h** |

---

## Architectural Notes

Per the TEAM_ORG_VNEXT_MASTER_PLAN.md:
- Teams-first, Organizations-optional architecture
- Currently in approximately Phase 3 (vNext write-primary)
- `apps/organizations` is the vNext system; `apps/teams` is legacy
- Feature flags: `TEAM_VNEXT_ADAPTER_ENABLED`, `TEAM_VNEXT_ROUTING_MODE`
- Dual ownership: Teams can be independent (`organization=NULL`) or org-owned

The org_control_plane represents an **aspirational** interface — many tabs (finance, sponsors, governance, verification) map to features that may not have full model/API support yet. The wiring tracker should distinguish between:
1. **Template → existing API** wiring (most P0/P1 items)
2. **New backend needed** before template can wire (some P2/P3 items)
