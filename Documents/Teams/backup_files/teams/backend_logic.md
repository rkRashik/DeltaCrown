# 📄 **FILE 7/8**

# **apps/teams/backend_logic.md**

### (*Complete backend architecture, logic rules, workflows, validation, invariants, services, permissions, database consistency, and all backend rules the Teams App must follow.*)

---

# 🟩 **1. Backend Architecture (High-Level)**

The Teams app backend is built on top of:

* **Django ORM**
* **Advanced business rules**
* **Multiple subsystems** (roster, invites, join requests, ranking, analytics, tournaments, chat, discussions, sponsorship, merch)
* **Heavy signal-driven automation**

This file documents *all current backend behavior* and the *rules Copilot must preserve* during the rebuild.

---

# 🟦 **2. Core Domain Models**

## 2.1 Team

A Team is the primary entity.
Key responsibilities:

* Identity: name, tag, slug
* Game-specific: game, region
* Media: logo, banner, roster image
* Visibility: public/private
* Recruiting: is_recruiting, allow_join_requests
* Points system: total_points, adjust_points
* Social: followers, posts
* Hero templates / esports appearance

**Critical invariants Copilot must preserve:**

1. **One unique slug per game**
2. **Only one primary game per team**
3. **Max roster = 8 active members**
4. ** Captain / owner roles must remain unique**
5. **Team cannot be left by the owner without transferring ownership**
6. **Team detail pages depend heavily on computed data** (ranking, stats, membership roles, etc.)

---

## 2.2 TeamMembership

Represents a user’s involvement in a team.

Roles include:

* **OWNER** (exactly 1)
* **MANAGER**
* **COACH**
* **CAPTAIN** (legacy or new title)
* **PLAYER**
* **SUBSTITUTE**

Statuses:

* **ACTIVE**
* **PENDING**
* **REMOVED**

**Critical rules:**

### Uniqueness Constraints (MUST be preserved)

* One active owner per team
* One active captain title per team
* One membership per profile+team
* Status matters — no double ACTIVE memberships

### Permissions

Membership stores cached permissions:

* can_edit_team
* can_manage_roster
* can_register_tournaments

These fields must be correctly calculated when:

* New membership is created
* Roles are changed
* Captaincy is transferred
* User is promoted to owner

Copilot must maintain correct recalculations.

---

## 2.3 TeamInvite

Invite to join a team.

**Logic details:**

* Unique invite token
* Optional email invite
* Expiry date
* Role required
* Invite cannot exceed roster capacity
* Pending invites count as potential members
* Accepting creates a TeamMembership

---

## 2.4 TeamJoinRequest

A join request created by the applicant.

**Logic:**

* Only 1 pending request per team
* Request may include message, role, game ID
* Approval creates a membership
* Rejection stores reviewed_by and review_note
* Cancellation allowed by the user

---

## 2.5 Ranking Models

3 parts:

### RankingCriteria

Default point system (configurable by admin)

### TeamRankingHistory

Audit of all changes
(critical for rollback, analytics)

### TeamRankingBreakdown

Cached computed total points

Copilot must preserve:

* audit trail
* recalculation signals
* leaderboard indexes

---

# 🟦 **3. Validation & Rules**

These are *not optional*.
They are business-critical.

## 3.1 One-Team-Per-Game Rule

User can belong to **exactly 1 active team per game**.

Checked in:

* TeamMembership.clean()
* TeamCreationForm.clean_game()
* join_team_view
* create_team_view

Copilot must maintain this across:

* forms
* API
* AJAX views
* DB queries

---

## 3.2 Roster Lock Rule (Tournament Integration)

If a team is registered for a tournament, roster changes must be restricted.

**Copilot must enforce:**

### During LOCK:

* User cannot leave
* Cannot invite
* Cannot accept join requests
* Cannot remove members
* Membership editing disabled

### When UNLOCKED:

* Normal behavior resumes

This rule is deeply integrated with:

* TournamentRosterLock
* TeamTournamentRegistration

---

## 3.3 Captain / Owner Logic

### Owner rules:

* Can’t leave without appointing new owner
* Cannot be removed by other members
* Full permissions always

### Captain rules:

* One per team
* Promoting someone demotes existing captain
* Captain can be PLAYER or SUBSTITUTE only
* Cannot assign captain title to owner

Copilot must enforce these exactly.

---

## 3.4 Membership Removal Rules

Removing member must check:

* roster lock
* user role
* cannot remove owner
* cannot remove captain (unless reassigning)
* capacity constraints

---

# 🟦 **4. Services Layer (Implicit)**

Teams app does not have a formal “services” directory but uses model methods + helper classes:

## Important helper files:

### 📌 teams.permissions.TeamPermissions

Controls all permissions across the app.

Copilot must NEVER hardcode permission checks in views.
Must always call:

```
TeamPermissions.can_edit_team_profile(membership)
TeamPermissions.can_manage_roster(membership)
TeamPermissions.can_leave_team(membership)
...
```

---

### 📌 teams.game_config (dynamic validators)

Used for:

* Game-specific ID fields
* Region lists
* Game rules
* Meta-data
* Validation logic

Copilot must preserve dynamic behavior.

---

### 📌 Post-cleanup & ranking recalculation functions

Signals manage:

* Points update
* Social stats
* Team analytics
* Event-driven achievements

Copilot must not break any signal wiring.

---

# 🟦 **5. Views & Endpoints**

Key views:

### 5.1 Creation

* `/teams/create/`
* `/teams/create/resume/`
* `/teams/collect-game-id/<game>/`
* AJAX validation: validate-name/tag, game-config, check-existing-team

### 5.2 Detail pages

* `/teams/<slug>/` (dashboard-view or social-view)
* `_team_hub.html` partial
* modern esports hero section

### 5.3 Management

* `/manage/`
* `/settings/`
* `/update-info/`
* `/update-privacy/`
* `/kick/`
* `/assign-manager/`, `/assign-coach/`, etc.
* `/transfer-ownership/`

### 5.4 Invites & Join requests

* `/invite/`
* `/invites/`
* `/join/`
* `/leave/`

### 5.5 Tournament integration

* `/tournaments/`
* `/ranking/`
* `/tournament-history/`

### 5.6 Advanced modules

* Chat
* Discussions
* Sponsorship
* Merch
* Analytics
* Leaderboards

---

# 🟥 **6. Backend Bugs Found**

(This section tells Copilot exactly what MUST be fixed.)

## 🚨 Critical

1. Duplicate leave_team_view function → one must be deleted
2. Leave view returns redirect, but JS expects JSON
3. Hardcoded user profile URL
4. Incorrect reference to membership.user (should be membership.profile)
5. Two conflicting clean_logo methods (one overwritten)
6. Game ID validation can crash if userprofile missing method
7. Membership unique_together ignores status → DB risk of duplicate “removed” memberships

---

# 🟧 **7. Backend Rules Copilot Must Preserve**

1. NEVER break the esports UI (backend should support it, not conflict)
2. ALWAYS use slug-based URLs
3. ALWAYS enforce one-team-per-game
4. ALWAYS use TeamPermissions
5. ALWAYS return JSON for AJAX endpoints
6. All errors must return human-readable messages
7. Respect roster lock global rule
8. Maintain event-driven architecture
9. NEVER remove security checks
10. No hardcoded URLs, no duplicated views

---

# 🟩 **8. Required Improvements & Enhancements**

These are mandatory for Copilot to implement:

### ✔ Make leave-team endpoint fully JSON aware

### ✔ Fix all incorrect references (`profile` vs `user`)

### ✔ Add DB constraint to prevent duplicate active memberships

### ✔ Improve error messages for membership rules

### ✔ Standardize join/create error flow

### ✔ Optimize _base_team_queryset performance

### ✔ Add select_related/prefetch_related where needed

### ✔ Create a central service module to unify business rules

### ✔ Implement validation for game assets & config sync

### ✔ Ensure tournament roster locks are respected everywhere

### ✔ Improve join request reviewer notes

### ✔ Update region logic to follow new game_config map

---

