# 📄 **FILE 2/8**

## **apps/teams/README.md**

Below is the complete README for the **Teams App root directory**.
This document explains the purpose, architecture, flow, and entry points for the entire module.

---

# **Teams App — Root README**

**Location:** `apps/teams/README.md`
**Module:** DeltaCrown Esports Platform — Teams System
**Purpose:** Explain the entire Teams App ecosystem for future developers

---

# 📌 **1. What is the Teams App?**

The **Teams App** is the largest and most complex module inside the DeltaCrown platform. It powers:

* Team creation
* Membership & roles
* Invites & join requests
* Rosters & permissions
* Competitive game identity
* Team analytics
* Match performance
* Tournament registration
* Team-level discussions
* Chat system
* Social hubs
* Sponsorship & merchandising
* Ranking & points system
* Full team management dashboards

This app is central to gameplay, progression, collaboration, and tournament participation.

---

# 📌 **2. Directory Structure Overview**

```
apps/teams/
│
├── api/                         # Optional DRF APIs
├── analytics/                   # Team and player analytics engine
├── discussions/                 # Team discussion board
├── sponsorship/                 # Sponsors, merch, promotions
├── chat/                        # Realtime team chat (Channels)
├── tournaments/                 # Tournament registration + roster locks
├── ranking/                     # Ranking system + history + settings
├── views/                       # All Django views
│   ├── public.py                # Public-facing team pages
│   ├── create.py                # Team creation wizard
│   ├── dashboard.py             # Team dashboards
│   ├── dashboard_api.py         # AJAX endpoints for dashboard
│   ├── analytics.py             # Analytics views
│   ├── role_management.py       # Manager/Owner role tools
│   ├── discussions.py           # Forum-like team discussions
│   ├── sponsorship.py           # Sponsors, merch
│   ├── chat.py                  # Chat views
│
├── models/                      # Data models
│   ├── _legacy.py               # Original core models (Team, Membership, Invite)
│   ├── team.py                  # Re-exporting of Team model
│   ├── membership.py            # Re-exporting of Membership
│   ├── ... (ranking, analytics, etc.)
│
├── permissions/                 # Permission system for role-based actions
│   ├── permissions.py           # TeamPermissions class
│
├── forms/                       # Forms for creation, invites, settings
├── services/                    # Business logic (ranking, recalculation, etc.)
├── utils/                       # Helpers: region mapping, slugs, game mapping
├── templates/teams/             # UI templates
├── static/teams/                # Frontend JS/CSS assets
├── urls.py                      # All team routes
└── __init__.py
```

---

# 📌 **3. Conceptual Architecture**

The Teams App operates under **Clean Modular Architecture**:

### **3.1 Layer Breakdown**

* **Models**
  → Database entities & constraints
* **Forms**
  → Validation & user input rules
* **Services**
  → Core business logic (ranking, roster rules)
* **Views**
  → Web controllers
* **Permissions**
  → Role and privilege system
* **Templates**
  → UI rendering
* **Static JS/CSS**
  → Frontend logic
* **Integrations**
  → Tournaments, Analytics, Events, Social, Chat

Everything is broken into modules so the domain stays maintainable.

---

# 📌 **4. Key Business Rules (Simplified)**

### 1️⃣ **One Team Per Game**

A user **cannot** join or create another team of the same game without leaving the existing one.

### 2️⃣ **Owner Uniqueness**

Every team must have exactly **one OWNER**.

### 3️⃣ **Roster Capacity**

Max 8 active players (TEAM_MAX_ROSTER).

### 4️⃣ **Invite & Join Request Rules**

* Only one pending request per user per team
* Team cannot invite if full
* User cannot join if already in another team for that game

### 5️⃣ **Tournament Roster Lock**

If a team enters a tournament:

* Joins/leaves may be LOCKED
* Only managers/owner can modify roster

### 6️⃣ **Permissions**

Actions such as:

* Kick
* Invite
* Edit settings
* Register tournaments
* Manage sponsor deals

are controlled by **TeamPermissions** class.

---

# 📌 **5. Important Features Provided by the Teams App**

### ⭐ Team Creation Wizard

Dynamic steps:

1. Basic info
2. Game + region selection
3. Media
4. Terms acceptance
5. Summary

Game IDs are required for:

* VALORANT
* CS2
* MLBB
* PUBG
* Free Fire
* CODM
  (and more)

### ⭐ Team Detail Page

* Beautiful modern esports UI
* Team Hub (owner)
* Member dashboard (new requirement)
* Roster, stats, analytics, tournaments

### ⭐ Team Social

* Posts
* Following
* Reactions

### ⭐ Team Chat

Real-time messaging using Django Channels.

### ⭐ Team Discussions

Forum-like discussion board.

### ⭐ Sponsorship & Merch

* Sponsors pages
* Merchandise store
* Tracking clicks

### ⭐ Ranking System

* Points
* Breakdown
* History
* Ranking settings
* Recalculation tools

### ⭐ Analytics

Team and player analytics dashboards.

---

# 📌 **6. URLs Structure**

Documented fully in:
`apps/teams/urls.md`

Most important endpoints:

```
/teams/
/teams/create/
/teams/<slug>/         # Team detail
/teams/<slug>/join/
/teams/<slug>/leave/
/teams/<slug>/manage/
/teams/<slug>/tournaments/
/teams/<slug>/analytics/
```

---

# 📌 **7. Templates Overview**

Templates live in `templates/teams/`.

Key templates:

* `team_detail_new.html`
* `team_create_esports.html`
* `list.html`
* `dashboard_modern.html`
* `invite_member.html`
* `my_invites.html`
* `collect_game_id.html`
* `discussion_*`
* `team_chat.html`

---

# 📌 **8. Static Files Overview**

Found in `static/teams/`.

Key JS files:

* `team-create-esports.js`
* `team-leave-modern.js`
* `team-list.js`
* `team-dashboard.js`

Key CSS files:

* `team-create-esports.css`
* `team-detail-new.css`
* `roster-esports.css`

---

# 📌 **9. Known Issues (Documented for Copilot)**

List of issues Copilot must fix is maintained in:
**Documents/Teams/TEAM_APP_FUNCTIONAL_SPEC.md**

But summary:

* Missing game card images
* quickJoin global not exported
* Region not updating
* Hardcoded URLs
* Duplicate leave_team_view
* Errors during team creation not shown properly
* Unsupported game mappings
* Dashboard not showing member tools

---

# 📌 **10. Developer Installation Notes**

### **Static Files**

```
python manage.py collectstatic
```

Make sure `ManifestStaticFilesStorage` is used to prevent missing assets.

### **Migrations**

```
python manage.py makemigrations
python manage.py migrate
```

### **Test URL**

Use:

```
/teams/test/
```

to test asset pipeline.

---

# 📌 **11. Testing Requirements**

Developers must test:

### **Team creation**

* All steps work
* Game cards load
* Region selector updates

### **Team membership**

* Join → Leave
* Invite → Accept/Decline
* Owner/Manager permissions

### **Team detail**

* Owner dashboard visible only to owner
* Member dashboard visible only to members

### **JS errors**

* Console must show **zero errors**

---

# 📌 **12. Maintenance Notes**

* All logic should eventually be moved out of `_legacy.py`
* Plan a future cleanup to consolidate models
* Keep game definitions in one place only
* Keep terms/policies in external Markdown files
* Document all config in `Documents/Teams/`

---

# 📌 **13. Appendix Links**

* Game specification: `Documents/Games/Game_Spec.md`
* Team specification: `Documents/Teams/TEAM_APP_FUNCTIONAL_SPEC.md`
* Copilot instructions: `Documents/Teams/COPILOT_TASK_INSTRUCTIONS.md`

---

