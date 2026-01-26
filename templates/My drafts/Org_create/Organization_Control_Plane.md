# **Organization Control Plane — Documentation**

---

## **Page Naming & Copy (Final – Use This Everywhere)**

### **Page Title (Browser / `<title>` tag)**

**Org Control Plane | DeltaCrown**

---

### **Navigation / CTA Button Label**

*(Used on Organization page, dashboard, or quick actions menu)*  
**Open Control Plane**

---

### **Page Headline (H1)**

**Org Control Plane**

---

### **Page Sub-headline / Description**

*(Replace the existing “Organization Sovereignty” description with this)*

**The centralized operating interface for your organization.**  
Manage identity, teams, roster governance, contracts, treasury automation, sponsor conflicts, recruitment logic, verification state, media integrations, audit trails, and staff permissions — all from a single control plane.

---

## **Implementation Notes for Developers (Required Changes)**

To align the UI, documentation, and routing with the new naming:

### **1\. Update Page Title**

Replace:

Organization Settings | DeltaCrown Enterprise

With:

Org Control Plane | DeltaCrown

---

### **2\. Update Main Page Heading (H1)**

Replace:

Organization Sovereignty

With:

Org Control Plane

---

### **3\. Update Page Description Text**

Replace:

Configure identity, teams, roster governance, contracts, treasury automation, sponsor conflicts, recruitment gatekeeping, verification state, media integrations, audit, and staff permissions.

With:

The centralized operating interface for your organization. Manage identity, teams, roster governance, contracts, treasury automation, sponsor conflicts, recruitment logic, verification state, media integrations, audit trails, and staff permissions — all from a single control plane.

---

### **4\. Update Navigation / CTA References**

Anywhere the organization links to this page (dashboard cards, dropdowns, buttons):

* Old label: **Settings**  
* New label: **Open Control Plane**

---

### **5\. (Optional but Recommended) URL & Route Naming**

If routing is configurable, prefer:

/org/control-plane

Instead of:

/org/settings

---

**Note for backend & product teams:**  
From this point forward, treat this page as the organization’s **primary operational interface**, not a passive settings screen.  
All permissions, approvals, audits, and system-critical changes should be conceptually tied to the **Org Control Plane**.

---

*(The remainder of this documentation continues unchanged and refers to this page as the “Org Control Plane.”)*

---

## **1\) Template overview**

### **What this template is**

A **single-page Organization Settings** dashboard with:

* Left sidebar navigation (tabs)  
* Multiple settings sections (General, Branding, Squads, Recruitment, Staff, Finance, Sponsors, Media, Notifications, Governance, Verification, Audit, Danger)  
* “Unsaved changes” indicator  
* Image upload previews (logo \+ banner)  
* A few interactive widgets (slider labels, color hex display)  
* Placeholder buttons intended to be wired to backend (Save/Discard and many action buttons)

### **Tech stack used (frontend)**

* TailwindCSS via CDN `https://cdn.tailwindcss.com`  
* Google Fonts: Outfit / Rajdhani / Space Mono  
* Font Awesome icons via CDN  
* Vanilla JS for:  
  * tab switching (`switchTab`)  
  * unsaved indicator (`setUnsaved`)  
  * slider label syncing  
  * file input preview with `URL.createObjectURL()`  
  * primary color hex syncing

### **Page identity**

Title indicates it’s “Organization Settings | DeltaCrown Enterprise” and uses brand color tokens under `delta` in Tailwind config .

---

## **2\) UI architecture & key behaviors**

### **2.1 Sidebar tabs**

Sidebar buttons call `switchTab('tabId')` via inline `onclick` attributes .

* Each content section is `<section id="...">` with class `section-tab`  
* Active tab has `section-tab active`  
* Buttons get `.settings-sidebar-link active` when selected

**Deep linking**:

* `switchTab()` writes `#tabId` into URL via `history.replaceState(null, "", "#" + tabId)`  
* On load, it checks `window.location.hash` and activates that tab

**Backend impact**: none; purely client-side navigation.

---

### **2.2 Unsaved changes indicator**

Any element with class `.track-change` triggers unsaved changes:

el.addEventListener("input", () \=\> setUnsaved(true));  
el.addEventListener("change", () \=\> setUnsaved(true));  
\`\`\` :contentReference\[oaicite:10\]{index=10}

\- Indicator text toggles between:  
  \- \`"Unsaved changes"\`  
  \- \`"All changes saved"\` :contentReference\[oaicite:11\]{index=11}

\*\*Important note\*\*: the template currently sets \`setUnsaved(false)\` when Save is clicked, but does not actually persist anything (“TODO: wire to backend”) :contentReference\[oaicite:12\]{index=12}.

\---

\#\#\# 2.3 Save / Discard buttons  
\- \`\#saveBtn\` click:  
  \- TODO wire to backend  
  \- then \`setUnsaved(false)\` :contentReference\[oaicite:13\]{index=13}  
\- \`\#discardBtn\` click:  
  \- TODO reload values from backend  
  \- then \`setUnsaved(false)\` :contentReference\[oaicite:14\]{index=14}

\*\*Recommended wiring pattern\*\*  
\- Save should:  
  1\) validate front-end basic rules (optional)  
  2\) submit a payload to backend  
  3\) on success, refresh the form from server response (authoritative) \+ clear unsaved state  
\- Discard should:  
  1\) re-fetch org settings from backend  
  2\) replace all inputs with server values \+ clear unsaved state

\---

\#\#\# 2.4 Branding previews (logo/banner)  
File inputs:  
\- \`\#logoFile\` updates:  
  \- \`\#logo-prev\` and \`\#hubLogo\`  
\- \`\#bannerFile\` updates:  
  \- \`\#banner-prev\` and \`\#hubBanner\` :contentReference\[oaicite:15\]{index=15}

Uses \`URL.createObjectURL(file)\` for local preview only.

\*\*Backend requirement\*\*: you must upload the file to server storage (S3/R2/etc.) and return a permanent URL; then store that URL in org settings.

\---

\#\#\# 2.5 Finance slider labels  
\`\#splitRange\` controls:  
\- \`\#orgTakeLabel\` \= slider value  
\- \`\#playerTakeLabel\` \= 100 \- slider value :contentReference\[oaicite:16\]{index=16}

\*\*Backend field mapping\*\*: store as integer \`org\_take\_percent\` (0–100). Player take is derived.

\---

\#\#\# 2.6 Primary color hex display  
\`\#primaryColor\` input updates \`\#primaryHex\` :contentReference\[oaicite:17\]{index=17}

\*\*Backend mapping\*\*: store as a hex string like \`\#FFD700\`.

\---

\#\# 3\) Sections, fields, and backend mapping

Below is the complete map of what each section contains, what to store, and recommended validation.

\> Naming note: I’ll refer to a top-level object \`org\_settings\`.

\---

\#\# 3.1 General Identity (\`\#general\`)  
\#\#\# Corporate Profile  
\- Organization Name (text)  
\- Short ticker/tag (text, maxlength=5)  
\- Public Handle / slug (\`\#slugInput\`, text)  
  \- UI suggests rate-limited slug change (cooldown) :contentReference\[oaicite:18\]{index=18}  
\- Manifesto (textarea)

\*\*Recommended backend fields\*\*  
\`\`\`json  
{  
  "name": "SYNTAX Esports",  
  "tag": "SYN",  
  "slug": "syntax-official",  
  "manifesto": "..."  
}

**Validations**

* `tag`: 2–5 chars; uppercase recommended  
* `slug`: lowercase \+ hyphen, unique, 3–40 chars  
* slug cooldown: store `slug_last_changed_at`

### **Social & Community**

* Discord invite  
* Facebook URL  
* Instagram handle  
* Website URL

**Fields**

{  
  "social": {  
    "discord\_invite": "",  
    "facebook\_url": "",  
    "instagram": "",  
    "website": ""  
  }  
}

### **SEO & Discovery**

* Meta title  
* Meta description  
* Keywords (comma-separated)  
* Public org page toggle (checkbox)  
* Search engine indexing toggle (checkbox)

**Fields**

{  
  "seo": {  
    "meta\_title": "",  
    "meta\_description": "",  
    "keywords": \["valorant", "cs2"\],  
    "public\_page\_enabled": true,  
    "search\_indexing\_enabled": true  
  }  
}

---

## **3.2 Brand Assets (`#branding`)**

### **Visual Assets**

* Corporate Emblem upload (logo)  
  * Hint: “PNG or SVG, Min 512x512px”  
* Empire Banner upload  
  * Hint: “Recommended: 1920x400px”  
* Live preview widgets (Org Card \+ Banner Strip) update instantly via JS

**Fields**

{  
  "branding": {  
    "logo\_url": "https://...",  
    "banner\_url": "https://...",  
    "logo\_mime": "image/png",  
    "banner\_mime": "image/jpeg"  
  }  
}

**Backend validation**

* mime whitelist: image/png, image/jpeg, image/webp, image/svg+xml (if you allow svg)  
* size limit (e.g., 2–5MB)  
* dimension checks:  
  * logo \>= 512x512  
  * banner recommended 1920x400 (enforce aspect ratio range instead of exact)  
* store variants (thumb, medium) if needed

### **Theme Signature**

* Primary color (`#primaryColor`)  
* Banner inheritance toggle (“Force Org Banner on all sub-teams”)  
* Brand safety: auto watermark toggle

**Fields**

{  
  "branding": {  
    "primary\_color": "\#FFD700",  
    "banner\_inheritance": true,  
    "auto\_watermark": false  
  }  
}

---

## **3.3 Squad Control (`#squads`)**

### **Active Roster Registry (teams list)**

UI shows example teams (Valorant, eFootball) with:

* “Register New Team” button  
* Each team row has:  
  * external/open button (icon)  
  * delete button (trash)

**Backend entities**  
You should model squads/teams separately from org settings:

`teams` table:

* id, org\_id  
* name, game  
* status (active/archived)  
* roster\_count (derived)  
* ranking info (optional)

### **Transfer & Buyout Policy**

* Open to acquisition (checkbox)  
* Roster locked / hard lock (checkbox)  
* Global minimum buyout (number, BDT)  
* Auto-approve transfers under (number)  
* Per-team buyout overrides (list rows):  
  * team selector  
  * minimum buyout  
  * offer type (player/team/both)  
* “Add Override” button

**Suggested fields**

{  
  "transfer\_policy": {  
    "market\_enabled": true,  
    "roster\_hard\_lock": false,  
    "global\_min\_buyout\_bdt": 50000,  
    "auto\_approve\_under\_bdt": 15000,  
    "team\_overrides": \[  
      { "team\_id": "t1", "min\_buyout\_bdt": 120000, "offer\_type": "player\_buyout" }  
    \]  
  }  
}

**Validation**

* all currency values \>= 0  
* `auto_approve_under_bdt <= global_min_buyout_bdt` (recommended)  
* overrides must reference team in same org

### **Competitive Integrity**

* Transfer window mode: Open/Closed/Scheduled  
* Lock policy: Registration close / Check-in / First match start  
* Emergency subs allowed (0/1/2/unlimited)  
* Dispute escalation timeout (12/24/48h)  
* Auto-block mid-tournament roster moves toggle

**Fields**

{  
  "integrity": {  
    "transfer\_window\_mode": "open",  
    "tournament\_lock\_policy": "registration\_close",  
    "emergency\_subs\_policy": "1\_per\_tournament",  
    "dispute\_escalation\_hours": 24,  
    "block\_mid\_tournament\_roster\_moves": true  
  }  
}

If you implement “Scheduled Windows”, you’ll also need:

* `transfer_windows: [{start_at, end_at}]`

---

## **3.4 Recruitment & Growth (`#recruitment`)**

### **Strategic Recruitment**

Automatic filtering toggles:

* Strict NID/Passport check (checkbox)  
* Pro-passport holders only (checkbox)  
* Require phone verified (checkbox)

Other fields:

* Talent search vibe (aggressive/passive/closed)  
* Minimum DCRS score (number)  
* Minimum win rate (%) (number)  
* Auto-reject if (enum)

**Fields**

{  
  "recruitment": {  
    "filters": {  
      "strict\_id\_check": true,  
      "passport\_only": false,  
      "require\_phone\_verified": true  
    },  
    "talent\_mode": "aggressive",  
    "min\_dcrs": 1500,  
    "min\_win\_rate": 70,  
    "auto\_reject\_rule": "no\_game\_passport"  
  }  
}

### **Application Pipeline (display)**

UI shows pipeline stages (New, Screening, Trial, Contract). This is visual, but you probably want a backend-driven pipeline:

* stages array with ids and order  
* allowed transitions  
* automation flags (auto tags, checks)

There are also toggles:

* Enable tryout scheduling  
* Auto-grant scrim access on trial

**Fields**

{  
  "recruitment": {  
    "tryout\_scheduling\_enabled": true,  
    "auto\_scrim\_access\_on\_trial": false  
  }  
}

### **Contract Templates (Legal Library)**

* Default contract duration (enum)  
* Default trial duration (enum)  
* “Upload Template” button  
* Template list with actions: View, Set Default

**Backend entities**  
`contract_templates`:

* id, org\_id  
* name, version, file\_url  
* updated\_at, owner\_user\_id  
* type (player\_agreement, nda, buyout\_addendum, etc.)  
* status (active/draft)  
* is\_default\_for(type)

---

## **3.5 Command Staff (`#staff`)**

### **Admin Delegation**

* “Appoint Staff” button  
* Role templates cards with Edit/Duplicate  
* Staff list cards with:  
  * user avatar  
  * role badge  
  * appointed date  
  * permission checkboxes grouped (Roster/Treasury/Operations)  
  * scope selector for a staff member (org-wide vs specific team)  
* Approval rules for high-risk actions:  
  * Treasury withdrawal approvals rule  
  * Player kick approvals rule  
  * Transfer approval rule

**Recommended backend model**  
You’ll want RBAC \+ scoped permissions:

Tables:

* `org_roles` (role templates): id, org\_id, name, permissions (json)  
* `org_staff_members`: id, org\_id, user\_id, role\_id, scope\_type (org/team), scope\_team\_id nullable, appointed\_at  
* `org_approval_policies`: org\_id, action\_key, required\_approvals, eligible\_roles

Example permissions JSON:

{  
  "permissions": {  
    "roster.edit": true,  
    "roster.transfer.approve": true,  
    "treasury.withdraw.request": true,  
    "treasury.payout.approve": true  
  }  
}

Approval policy example:

{  
  "approval\_policies": {  
    "treasury.withdraw": { "mode": "1\_approval", "allowed\_roles": \["finance", "ceo"\] },  
    "roster.kick": { "mode": "none" },  
    "transfer.approve": { "mode": "manager\_approval" }  
  }  
}

**Critical**: Every permission toggle/change should generate an audit log entry.

---

## **3.6 Empire Treasury (`#finance`)**

### **Financial infrastructure**

* Default prize split slider (`#splitRange`)  
* Primary ledger currency (BDT/USD)  
* Per-team prize split overrides (rows)  
  * includes “Apply: All Prize Pools / Tournament / Scrim”  
* Payroll:  
  * pay frequency (weekly/monthly/quarterly)  
  * auto-pay day (1–28)  
  * payroll freeze below threshold  
  * per-squad salary pools (team, amount, distribution method)  
* Ledger history (table)  
* Export/Tags/Filters buttons  
* External payout channels:  
  * withdrawal approvals  
  * daily withdrawal cap  
  * payout freeze toggle  
  * payout methods list (“bKash configured”, others not configured)

**Backend structure suggestion**  
This section implies you need both:

1. configuration (settings)  
2. financial ledger (transactions)

Config:

{  
  "finance": {  
    "default\_org\_take\_percent": 20,  
    "currency": "BDT",  
    "team\_split\_rules": \[  
      { "team\_id": "t1", "org\_percent": 10, "player\_percent": 90, "applies\_to": "all\_prize\_pools" }  
    \],  
    "payroll": {  
      "frequency": "monthly",  
      "auto\_pay\_day": 25,  
      "freeze\_below\_bdt": 15000,  
      "salary\_pools": \[  
        { "team\_id": "t1", "amount\_bdt": 40000, "distribution": "manual" }  
      \]  
    },  
    "withdrawals": {  
      "approval\_mode": "1\_approval",  
      "daily\_cap\_bdt": 50000,  
      "freeze\_outgoing": false  
    },  
    "payout\_channels": \[  
      { "type": "bkash", "masked": "\*\*\*\* \*\*\*\* 5928", "label": "Personal", "status": "active" },  
      { "type": "beftn", "status": "not\_configured" },  
      { "type": "nagad", "status": "not\_configured" }  
    \]  
  }  
}

Ledger tables:

* `ledger_transactions` (append-only): id, org\_id, type, amount, currency, reference, created\_at, metadata json  
* `payout_requests`: id, org\_id, requested\_by, channel\_id, amount, status, approvals, created\_at

**Validation**

* split rules must sum to 100 (template explicitly suggests this)  
* payroll auto day: 1–28  
* daily cap \>= 0  
* if freeze\_outgoing=true, block creation/execution of payouts

---

## **3.7 Partners & Sponsors (`#sponsors`)**

* Enable sponsor slots toggle  
* Auto-apply sponsor to sub-teams toggle  
* Active sponsors list with “Visibility” and “Edit”  
* Sponsor conflicts:  
  * Blocked brands (input \+ Add)  
  * Blocked categories (select)  
  * Enforce on sub-team pages toggle

**Backend design**

* `sponsors`: id, org\_id, name, category, tier, status  
* `sponsor_visibility_rules`: org\_id, applies\_to (org/team/overlay), enabled  
* `sponsor_conflicts`:  
  * blocked\_brand\_names array  
  * blocked\_categories array  
  * enforce\_on\_subteams boolean

---

## **3.8 Media & Streaming (`#media`)**

* Twitch URL  
* YouTube URL  
* Auto-feature live players toggle  
* Auto-post match results highlights toggle  
* Overlay sponsor routing checkboxes:  
  * Org page  
  * Team pages  
  * Stream overlay

**Backend requirements**

* OAuth / tokens if you truly integrate Twitch/YouTube  
* A “match completed” event pipeline if you want auto highlights

Minimal settings:

{  
  "media": {  
    "twitch\_url": "",  
    "youtube\_url": "",  
    "auto\_feature\_live\_players": true,  
    "auto\_post\_match\_highlights": false,  
    "sponsor\_routing": {  
      "org\_page": true,  
      "team\_pages": true,  
      "stream\_overlay": false  
    }  
  }  
}

---

## **3.9 Notification Matrix (`#notifications`)**

* Channels toggles: In-App, Email, SMS, Discord Webhook  
* Quiet hours start/end  
* Escalation timeout (off/30m/2h/24h)  
* Event routing matrix table (events x roles)

**Backend model**

* `notification_settings`:  
  * enabled\_channels  
  * quiet\_hours (start, end, timezone)  
  * escalation\_timeout\_seconds  
* `notification_routes`:  
  * event\_key  
  * role\_key \-\> enabled boolean  
* `webhooks` (for discord): url, secret, enabled

---

## **3.10 Governance & Security (`#governance`)**

* Require 2FA for sensitive actions toggle  
* Session revoke button (“Revoke All”)  
* IP allowlist (input CIDR \+ applies to select \+ Add)  
* Soft delete grace window (off/1h/6h/24h/72h)

**Backend requirements**

* 2FA enforcement on certain endpoints (treasury, ownership transfer, decommission)  
* session revocation endpoint  
* IP allowlist evaluation during:  
  * login OR admin actions (based on “Applies”)  
* soft delete policy: store grace duration and ensure deletes are reversible during window

---

## **3.11 Verification (`#verification`)**

UI describes verification as a state machine: “Submitted → Approved/Rejected”, with expiry reminders and history

Fields shown:

* Trade License upload \+ expiry date \+ reminder (off/7d/30d/60d)  
* Founder ID upload (NID or Passport) \+ review priority  
* Document History table (status: missing)

**Backend model**

* `verification_profile`:  
  * status: not\_submitted/submitted/approved/rejected  
  * tier: none/bronze/silver/gold (if you implement tiers)  
  * submitted\_at, reviewed\_at, reviewer\_id, rejection\_reason  
* `verification_documents`:  
  * doc\_type: trade\_license, founder\_id  
  * file\_url, mime, uploaded\_at  
  * expiry\_date  
  * reminder\_policy\_days  
  * status: missing/pending/approved/rejected  
  * history log entries (immutable)

---

## **3.12 Audit & Logs (`#audit`)**

* Retention select (30/90/180/365 days)  
* Export logs button  
* Filters select (All, Treasury, Roster, Verification, Sponsors, Security)  
* Recent actions table with event keys like `roster.update`, `treasury.withdraw.request`, etc.

**Backend requirement**

* Append-only audit log store:  
  * event\_key  
  * actor\_user\_id  
  * org\_id  
  * payload diff/metadata json  
  * created\_at  
* retention enforcement job (or partitioning)

---

## **3.13 Terminal Actions (`#danger`)**

* Transfer ownership button (“Initiate Transfer”)  
* Decommission organization (“Full Purge”)

**Backend requirement**  
These should be heavily protected:

* Require 2FA (as governance section implies)  
* Require multi-approval (optional)  
* Require explicit confirmation step on UI \+ backend  
* Log everything

---

# **4\) Recommended backend API design (REST)**

You can wire the template with a small set of consistent endpoints.

## **4.1 Read settings**

`GET /api/orgs/:orgId/settings`

Returns a single object:

{  
  "general": {...},  
  "seo": {...},  
  "branding": {...},  
  "transfer\_policy": {...},  
  "integrity": {...},  
  "recruitment": {...},  
  "finance": {...},  
  "sponsors": {...},  
  "media": {...},  
  "notifications": {...},  
  "governance": {...},  
  "verification": {...},  
  "audit": {...}  
}

## **4.2 Save settings (bulk)**

`PUT /api/orgs/:orgId/settings`

* Accepts the same structure  
* Returns the canonical saved config (server is source of truth)  
* Creates an audit log entry for each changed category or field group

**Why bulk PUT works well here**  
Your UI has a top “Save All Changes” button .

## **4.3 Upload endpoints**

Because the UI has file inputs (logo/banner, verification docs, templates), handle uploads separately:

* `POST /api/uploads` (generic)  
  * returns `{ fileUrl, mime, width, height, sizeBytes }`

Or specialized:

* `POST /api/orgs/:orgId/branding/logo`  
* `POST /api/orgs/:orgId/branding/banner`  
* `POST /api/orgs/:orgId/verification/documents`

## **4.4 Teams/Squads endpoints**

* `GET /api/orgs/:orgId/teams`  
* `POST /api/orgs/:orgId/teams`  
* `DELETE /api/orgs/:orgId/teams/:teamId`

## **4.5 Staff \+ RBAC endpoints**

* `GET /api/orgs/:orgId/staff`  
* `POST /api/orgs/:orgId/staff` (appoint)  
* `PATCH /api/orgs/:orgId/staff/:staffId` (scope/permissions)  
* `GET /api/orgs/:orgId/roles`  
* `POST /api/orgs/:orgId/roles` (new template)  
* `PATCH /api/orgs/:orgId/roles/:roleId` (edit)  
* `POST /api/orgs/:orgId/roles/:roleId/duplicate`

## **4.6 Finance endpoints (runtime)**

Settings are one thing; money movement needs workflow:

* `POST /api/orgs/:orgId/withdrawals` (creates request)  
* `POST /api/orgs/:orgId/withdrawals/:id/approve`  
* `POST /api/orgs/:orgId/withdrawals/:id/execute`  
* `GET /api/orgs/:orgId/ledger?filters=...`  
* `POST /api/orgs/:orgId/ledger/export`

## **4.7 Audit endpoints**

* `GET /api/orgs/:orgId/audit?type=...&limit=...`  
* `POST /api/orgs/:orgId/audit/export`

## **4.8 Governance endpoints**

* `POST /api/orgs/:orgId/security/sessions/revoke_all`  
* `POST /api/orgs/:orgId/security/ip_allowlist` (add/remove)  
* `POST /api/orgs/:orgId/security/2fa/verify` (if you do step-up auth)

## **4.9 Danger endpoints**

* `POST /api/orgs/:orgId/ownership/transfer` (requires 2FA \+ confirmation)  
* `POST /api/orgs/:orgId/decommission` (requires strongest controls)

---

# **5\) Data model blueprint (practical)**

A clean approach is:

## **5.1 Tables (minimum)**

* `organizations`  
* `org_settings` (json column for most config)  
* `teams`  
* `org_roles`  
* `org_staff_members`  
* `contract_templates`  
* `verification_profile`  
* `verification_documents`  
* `audit_logs`  
* `ledger_transactions`  
* `payout_requests`  
* `uploads` (optional tracking table)

## **5.2 Why JSON settings works here**

This UI has lots of “config-like” fields (toggles, thresholds, enums). A JSONB blob for `org_settings` is fast to iterate and matches “Save All Changes” semantics well, while transactional systems (ledger, payouts, staff) stay normalized.

---

# **6\) Wiring guide (frontend integration steps)**

## **Step A — Replace default hardcoded values**

Right now many inputs are hardcoded (e.g., org name “SYNTAX Esports”, slug “syntax-official”, manifesto text, etc.)

On page load:

1. call `GET /api/orgs/:orgId/settings`  
2. populate every input/checkbox/select with returned values  
3. call `setUnsaved(false)`

## **Step B — Serialize the form into a payload**

Recommended pattern:

* Give every input a `data-path="general.name"` style attribute  
* On Save, iterate all `[data-path]` elements and build the JSON object.

(Your current file uses `.track-change` only; it does not provide names/ids for every field, so adding `data-path` is the cleanest next step.)

## **Step C — Save action**

On Save click:

1. build payload  
2. `PUT /api/orgs/:orgId/settings`  
3. on success:  
   * repopulate UI from response  
   * `setUnsaved(false)`  
4. on validation error:  
   * show inline errors (next to inputs)

## **Step D — Discard action**

On Discard click:

* re-fetch settings and repopulate inputs  
* `setUnsaved(false)`

## **Step E — Upload wiring**

For `logoFile` / `bannerFile`, you currently only do local preview .  
To wire properly:

1. user selects file  
2. immediately `POST /api/uploads` (or branding endpoint)  
3. server returns permanent URL  
4. set preview to that URL  
5. store URL in pending settings payload (or update settings immediately)

---

# **7\) Validation & security rules implied by the UI**

The template strongly implies certain product rules (your backend should enforce them even if UI doesn’t yet):

* **Slug changes rate-limited / cooldown** (text hints this)  
* **Split rules must sum to 100** (explicit suggestion)  
* **Audit logs immutable** (explicit wording in Audit section)  
* **2FA required for sensitive actions** (Governance toggle \+ Danger section chips)  
* **Soft delete grace window** (Governance)  
* **Verification is a state machine** with history and accountability  
* **Least privilege** permissions principle is referenced in staff section

---

# **8\) What your developer should modify in the template (minimum changes)**

To make wiring easy, I recommend these small but high-impact changes (no framework required):

1. Add `data-path` to every input/select/checkbox/textarea  
   Example:  
   * org name input → `data-path="general.name"`  
   * slug input → `data-path="general.slug"`  
   * public page toggle → `data-path="seo.public_page_enabled"`  
2. Add `id` to missing important controls (many don’t have ids)  
3. Add a `renderSettings(settings)` function and `collectSettings()` function  
4. Add a simple `showToast(message, type)` helper for save success/errors

---

# **9\) Source file**

All of the above documentation is based on your template file: .

If you want, I can also produce a **ready-to-use JSON schema** (for validation) that exactly matches all the fields shown in the UI, plus a sample `GET /settings` response and `PUT /settings` request body aligned to this page.

