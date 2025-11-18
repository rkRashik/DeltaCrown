# **TEAM APP — Functional Specification (DeltaCrown Platform)**

**Document Version:** 1.0
**Project:** DeltaCrown Tournament Ecosystem
**Module:** Teams App (Full Rebuild — Professional Version)
**Author:** ChatGPT (Architect)
**Audience:** GitHub Copilot, Engineers, Future Developers
**Purpose:** Define the complete logic, rules, architecture, UI/UX expectations, and rebuild plan for the Teams App.

---

# **1. Overview**

The **Teams App** is a core module of the DeltaCrown esports ecosystem.
Teams represent competitive groups created by players to participate in tournaments, compete for rankings, unlock achievements, and engage in social/community features.

This specification replaces all scattered logic with a **single canonical source of truth**.

This document contains:

* Full business rules
* Data model (as-is + required refactor rules)
* UI/UX expectations
* Validation rules
* Full user flows
* Member role system
* Roster, permissions, invites, joins
* Tournament integration
* Ranking/analytics integration
* Game-specific logic
* Terms & policies
* Required pages
* Required backend behaviors
* Required frontend behaviors
* Rebuild tasks for Copilot

This is the **definitive blueprint**.
Copilot must implement all tasks exactly as defined here.

---

# **2. Core Principles**

1. **Preserve existing front-end design**

   * Keep current esports-styled visual themes.
   * Keep current team-detail, creation wizard, roster UI.
   * Upgrade styling, fix broken layouts, improve animations.

2. **Zero breaking changes to existing UI**

   * But fix bugs, polish CSS, add missing assets, correct paths.

3. **Strict professional quality**

   * Industry-level UX.
   * Strong backend validation.
   * Fully functional flows.
   * Zero console errors.
   * Zero runtime errors.

4. **Code must follow:**

   * Django best practices
   * Clean architecture
   * Atomic operations
   * Proper error handling
   * Unification of validation logic

5. **All features must be fully functional**

   * No “shell” pages.
   * Everything must work end to end.

---

# **3. Data Model Rules**

The following rules MUST be enforced across models, views, services, forms, APIs, and templates.

## **3.1 Team Entity Rules**

A Team:

* Is unique per game.
* Has a name and tag with uniqueness enforced.
* Has a slug that is unique per game.
* Has a region depending on the game.
* Has media properties (logo/banner).
* Has public/private visibility rules.
* Can be verified, featured, or recruiting.
* Has ranking points & breakdown.
* Has achievements, sponsors, merch.
* Has analytics and tournament history.

## **3.2 Membership Rules**

A user:

* Can ONLY be in **ONE active team per game**.
* Can only create a team for a game if not already a member of a team for that game.
* Must meet any rank requirements.

Membership roles:

* OWNER (1 per team)
* MANAGER
* COACH
* PLAYER
* SUBSTITUTE

Uniqueness:

* ONE active owner (strict)
* ONE captain (optional)
* No duplicate memberships
* Removed members cannot rejoin without process

## **3.3 Invite & Join Request Rules**

* A team may invite users.
* A user may request to join.
* Only one pending join request per user per team.
* Cannot invite if roster is full.
* Cannot join if roster is full.
* Cannot join if already in another team (same game).

## **3.4 Tournament Integration Rules**

Teams:

* Can register for tournaments
* Must follow roster locks
* Must satisfy roster requirements
* Must enforce lock during tournament phases

---

# **4. UX/UI Rules**

## **4.1 Team Create — Step Wizard**

Step 1 → Basic info
Step 2 → Game selection & related region picker
Step 3 → Media (logo/banner)
Step 4 → Terms & policies acceptance
Step 5 → Summary screen

Enhance with:

* Game card images from `apps/common/game_assets.py`
* Dynamic region selection based on game
* Modern esports UI enhancements
* Proper error messaging
* Clear validation messages (one-team-per-game)
* Terms & conditions modal

## **4.2 Game Cards (Step 2)**

Games must show:

* Image
* Name
* Short description
* Supported platforms
* Supported regions

Game configs fetched from:

* `Documents/Games/Game_Spec.md`
* `apps/common/game_assets.py` (must be updated)

Must support:

* valorant
* cs2
* dota2
* mlbb
* pubg
* freefire
* efootball
* fc26
* codm

## **4.3 Region Selection**

Rules:

* Region list differs by game
* Region selector must update dynamically
* Should have beautiful UI (map-style optional)
* Must not break UX if map not implemented

## **4.4 Terms & Conditions**

Team creation requires:

* Organization Terms
* Game Terms
* DeltaCrown esports policies
* Age requirement
* Fair play rules
* Anti-cheating policies

User must accept via:

* Checkbox
* Timestamp stored in DB
* Stored on membership as well

## **4.5 Team Detail Page**

Owner sees:

* Full dashboard
* Full management tools

Members see:

* Member dashboard (NEW)
* Tools based on role

Non-members see:

* Public team page

---

# **5. Team Member Dashboard (NEW)**

For MEMBERS (not captain/owner):

* View team summary
* Leave team button
* Invite members (if allowed)
* Edit their own team profile info
* View pending join requests (if manager)
* View team calendar (if implemented)
* See analytics summary
* Quick access to tournaments joined

Dashboard is dynamic based on:

* Role
* Permissions

---

# **6. Permissions System**

Group 1: Owner
Group 2: Manager
Group 3: Coach
Group 4: Player
Group 5: Substitute

Each role defines allowed actions:

* Invite
* Kick
* Manage settings
* Register for tournaments
* Edit team info
* Edit tactics
* View analytics
* Manage sponsors
* Manage merch

---

# **7. Error Handling / UX**

Bad errors such as:

* “Unsupported game”
* “quickJoin not defined”
* “form errors”

Should instead become:

* Clean toast notifications
* Clear, friendly messages
* Modern-style modal warnings
* Non-breaking flows

---

# **8. Bugs to Fix (Mandatory)**

Copilot MUST fix all of these:

### **8.1 Missing game card images**

* Update game_assets.py
* Fix static path
* Fix Step 2 UI

### **8.2 quickJoin is not defined**

* Global function export missing
* JS fix required

### **8.3 Unsupported game slug (“pubg-mobile”)**

* Fix game normalization layer
* Ensure mapping from slug → internal code

### **8.4 Team create form errors not shown properly**

* Show per-field messages
* Show reason for one-team-per-game error

### **8.5 Leave team AJAX mismatch**

* View must return JSON
* JS must interpret JSON
* Fix duplicate leave_team_view definitions

### **8.6 Hardcoded URLs**

* Remove "/user/{{username}}/"
* Replace with `{% url … %}`

### **8.7 Region not updating**

* Fix JS dynamic loader
* Fix API endpoint
* Integrate per-game region map

### **8.8 Dashboard missing member tools**

* Implement new module for member dashboard

---

# **9. Mandatory New Features**

## **9.1 Dynamic Region System**

* Based on game regions
* Full compatibility with new game_spec

## **9.2 Member Dashboard**

* Personalized control center
* Role-based feature loading

## **9.3 Terms & Conditions Module**

* Stored in DB or static file
* Required acceptance

## **9.4 Developer Documentation**

* Full README set
* One README per directory

## **9.5 Static Asset Fix**

* Ensure no missing JS/CSS
* Ensure collectstatic compatible

---

# **10. Refactor Rules**

Copilot must:

* NOT change UI design style
* May improve, clean, polish
* May optimize code
* Must remove duplicate functions
* Must unify game config logic
* Must unify permission checks
* Must fix all console errors
* Must fix all backend errors
* Must verify all flows end to end
* Must run migrations and ensure no conflicts

---

# **11. Required Pages to Fix/Enhance**

1. `/teams/create/`
2. `/teams/<slug>/`
3. `/teams/` list page
4. `/teams/<slug>/join/`
5. `/teams/<slug>/leave/`
6. `/teams/<slug>/manage/`
7. Dashboard pages
8. Social pages (depending on redirect module)
9. Game ID collection page
10. Tournament registration pages connected to team

---

# **12. Testing Requirements**

Copilot must:

* Run server after applying changes
* Ensure **zero runtime errors**
* Ensure **zero console errors**
* Ensure **all JS functions exist**
* Ensure **forms submit correctly**
* Ensure **all team flows are usable end-to-end**
* Ensure **team creation works**
* Ensure **team joining works**
* Ensure **roster management works**
* Ensure **leave team works**
* Ensure **game ID system works**
* Ensure **game region selector works**

---

# **13. Delivery Requirements for Copilot**

Copilot must:

* Perform FULL implementation in **one long response**
* Do al l modifications directly to project files
* NOT ask questions
* NOT stop midway
* NOT provide partial solutions
* After full implementation:
  → Provide a final report summarizing all changes + tests passed

---

# **14. Appendices**

Appendix A: Full game list
Appendix B: Region mapping
Appendix C: Terms & conditions categories
Appendix D: Ranking formulas
Appendix E: Roster lock rules

*(These sections auto-populate based on game_spec files and code comments — Copilot must not remove them.)*

---

# **End of Specification**

**This is the canonical source of truth.**

---
