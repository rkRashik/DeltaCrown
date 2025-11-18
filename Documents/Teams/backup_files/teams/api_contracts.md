# 📄 **FILE 8/8**

# **apps/teams/api_contracts.md**

### (*All endpoints, request/response shapes, AJAX contracts, and integration rules for the Teams app.*)

> **Important to Copilot:**
> This document defines how the **backend must behave** for all HTTP/API interactions used by the Teams app (forms + AJAX).
> You MUST keep these contracts stable while fixing bugs and refactoring.

---

## 🟩 1. General Principles

1. **Use Django URL names** everywhere (no hardcoded `/user/...` etc.).

2. **For normal HTML pages**:

   * Use standard Django templates.
   * Use `messages` framework for user feedback.

3. **For AJAX / fetch / XHR endpoints**:

   * Always return **JSON**.
   * Standard shape:

   ```json
   {
     "success": true,
     "message": "Human readable message",
     "data": { ... }      // optional
   }
   ```

   On error:

   ```json
   {
     "success": false,
     "error": "Short human readable description",
     "code": "ONE_TEAM_PER_GAME"  // optional machine-readable code
   }
   ```

4. Always honor **CSRF** for POST/PUT/PATCH/DELETE:

   * JS sends `X-CSRFToken: <csrftoken>`.
   * Django must have `@csrf_exempt` only where absolutely safe (prefer `@csrf_protect`).

5. **Permissions must be enforced server-side** using `TeamPermissions`.
   UI visibility is just a hint, not security.

---

## 🟦 2. Public HTML Views & Contracts

These endpoints **render HTML pages** and are accessed by normal links or redirects.

### 2.1 Team List

**URL name:** `teams:list` (and `teams:index`, `teams:hub`)
**Path:** `/teams/` or `/teams/list/`
**Method:** `GET`
**Template:** `teams/list.html`

**Query params (optional):**

* `q` – search term (team name / tag)
* `game` – filter by game code
* `region` – filter by region code
* `recruiting` – `true` / `false`
* `verified` – `true` / `false`
* `featured` – `true` / `false`
* `sort` – one of: `powerrank`, `points`, `recent`, `members`, `az`, `game`, `newest`
* `order` – `asc` / `desc`
* `page` – page number

**Context (must be present):**

* `teams` – paginated queryset
* `filters` – current filter values
* `active_filters` – list of active filter chips
* `game_options` – list of available game choices
* `region_options` – list of region choices
* `sort_options`, `order_options`
* `pagination` – page info for UI

---

### 2.2 Team Detail

**URL name:** `teams:detail`
**Path:** `/teams/<slug:slug>/`
**Method:** `GET`
**Template:** `teams/team_detail_new.html` (or social namespace view, but **the visual style must be preserved**)

**Context (minimum):**

* `team` – Team instance
* `membership` – TeamMembership for current user (or `None`)
* `is_owner` – bool
* `is_captain` – bool
* `is_manager` – bool
* `is_member` – bool
* `roster` – active memberships queryset
* `roster_count` – integer
* `can_manage_roster` – from `TeamPermissions`
* `can_edit_team_profile`
* `can_register_tournaments`
* `can_leave_team`
* `stats` – object or dict for basic team stats
* `tournament_history` – minimal list for overview
* Any data required by `_team_hub.html` and partials

**Behavior:**

* If team is **inactive or not public**, non-members should see a restricted or 404 page.
* Owner/captain see full “Full Dashboard” / management options.
* Non-owner members see member dashboard (future enhancement, but context must support it).

---

### 2.3 Create Team

**URL name:** `teams:create`
**Path:** `/teams/create/`
**Methods:** `GET`, `POST`
**Template:** `teams/team_create_esports.html` (or current esports version)

**Behavior:**

* `GET`: show multi-step wizard form (4 steps).
* `POST`: validate and either:

  * show detailed errors per field, staying on correct step
  * or create team and redirect to `teams:detail`.

**Errors must include:**

* **One-team-per-game violation**:

  * Show human-readable reason:

    > “You already belong to a team for this game. You must leave that team before creating another one.”
* **Roster/game ID issues**:

  * If game ID is required but missing, redirect to `teams:collect_game_id` with a friendly message.
* **Terms & Conditions**:

  * If terms checkbox not checked, show clear error.

---

## 🟦 3. AJAX / JSON Endpoints

These are **fetch / XHR** targets.
They must use **JSON** responses.

### 3.1 Team Name Validation

**URL name:** `teams:validate_team_name`
**Path:** `/teams/api/validate-name/`
**Method:** `POST` (or `GET` if already used like that – Copilot must preserve current method)

**Request payload:**

```json
{
  "name": "Team Name"
}
```

**Response (success):**

```json
{
  "success": true,
  "available": true,
  "message": "Team name is available"
}
```

If not available:

```json
{
  "success": false,
  "available": false,
  "error": "This team name is already taken"
}
```

---

### 3.2 Team Tag Validation

**URL name:** `teams:validate_team_tag`
**Path:** `/teams/api/validate-tag/`
**Method:** `POST`

Payload & response same shape as name validation, but with `tag`.

---

### 3.3 Game Config API

**URL name:** `teams:game_config_api`
**Path:** `/teams/api/game-config/<str:game_code>/`
**Method:** `GET`

**Response example (must be JSON):**

```json
{
  "success": true,
  "game_code": "valorant",
  "has_game_id": true,
  "game_ids": {
    "riot_id": {
      "label": "Riot ID",
      "placeholder": "YourName#TAG",
      "required": true,
      "max_length": 32
    }
  },
  "regions": [
    { "code": "ap", "name": "Asia-Pacific" },
    { "code": "eu", "name": "Europe" }
  ]
}
```

**Requirements:**

* This is used by `/teams/create/` **Step 2** to:

  * Build game ID fields dynamically
  * Populate the **Region** dropdown based on selected game
* Must read from **a single source of truth**, ideally `apps.common.game_assets` + `game_config`.

---

### 3.4 Check Existing Team (One-Team-Per-Game UX)

**URL name:** `teams:check_existing_team`
**Path:** `/teams/api/check-existing-team/`
**Method:** `POST`

**Payload:**

```json
{
  "game_code": "valorant"
}
```

**Response if user already has a team for that game:**

```json
{
  "success": true,
  "has_team": true,
  "can_create": false,
  "team": {
    "name": "Bengal Tigers",
    "slug": "bengal-tigers",
    "game": "valorant",
    "detail_url": "/teams/bengal-tigers/"
  },
  "message": "You already belong to 'Bengal Tigers' for VALORANT. You must leave that team before creating another one."
}
```

If user has no team for that game:

```json
{
  "success": true,
  "has_team": false,
  "can_create": true,
  "message": "You can create a new team for this game."
}
```

**This must be used in:**

* Team create wizard (Step 2/3)
* Join team flows (to block joining multiple teams in same game)

---

### 3.5 My Teams / My Invites Data

**URL names:**

* `teams:my_teams_ajax` → `/teams/my-teams-data/`
* `teams:my_invites_ajax` → `/teams/my-invites-data/`

**Method:** `GET`

**Response example for `my-teams-data`:**

```json
{
  "success": true,
  "teams": [
    {
      "name": "Bengal Tigers",
      "slug": "bengal-tigers",
      "game": "valorant",
      "role": "PLAYER",
      "is_owner": false,
      "is_captain": true,
      "detail_url": "/teams/bengal-tigers/"
    }
  ]
}
```

**Use:**

* Dashboard widgets (“My Teams”)
* Quick navigation menus.

---

### 3.6 Join Request Actions (Organizer/Dashboard API)

**URL names:**

* `teams:api_approve_join_request`
* `teams:api_reject_join_request`

**Paths:**

* `/teams/api/join-requests/<int:request_id>/approve/`
* `/teams/api/join-requests/<int:request_id>/reject/`

**Method:** `POST`

**Payload (optional):**

```json
{
  "reason": "We already have full roster."
}
```

**Response (success):**

```json
{
  "success": true,
  "status": "APPROVED",
  "message": "Join request approved and member added to roster."
}
```

Or:

```json
{
  "success": true,
  "status": "REJECTED",
  "message": "Join request rejected."
}
```

Server must:

* Check `TeamPermissions.can_manage_roster`
* Respect **roster lock**
* Respect **max roster limit**
* Respect **one-team-per-game rule**

On violation:

```json
{
  "success": false,
  "error": "Roster is locked for an active tournament.",
  "code": "ROSTER_LOCKED"
}
```

---

### 3.7 Invite Management API

**URL names:**

* `teams:api_resend_invite` → `/teams/api/invites/<int:invite_id>/resend/`
* `teams:api_cancel_invite` → `/teams/api/invites/<int:invite_id>/cancel/`

**Method:** `POST`

**Response:**

```json
{
  "success": true,
  "message": "Invite resent successfully."
}
```

or

```json
{
  "success": true,
  "message": "Invite cancelled."
}
```

Permission: `TeamPermissions.can_manage_roster`.

---

### 3.8 Leave Team (Critical AJAX Contract)

**URL name:** `teams:leave`
**Path:** `/teams/<slug:slug>/leave/`
**Method:** `POST` (via fetch)

**Request (current JS expectation):**

```js
fetch("/teams/<slug>/leave/", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "X-CSRFToken": getCookie("csrftoken")
  },
  body: JSON.stringify({ reason: "optional text" })
})
```

**Copilot must update view to:**

* Parse JSON body
* On success return:

```json
{
  "success": true,
  "message": "You have left the team.",
  "redirect_url": "/teams/"
}
```

* On **blocked** (ownership, roster lock, etc.):

```json
{
  "success": false,
  "error": "As the team owner, you must transfer ownership before leaving.",
  "code": "CANNOT_LEAVE_OWNER"
}
```

* On **not a member**:

```json
{
  "success": false,
  "error": "You are not a member of this team.",
  "code": "NOT_A_MEMBER"
}
```

> **Important:**
> There are two `leave_team_view` functions in the code.
> Copilot must keep **only one**, aligned with this API contract.

---

### 3.9 Kick Member (AJAX)

**URL name:** `teams:kick`
**Path:** `/teams/<slug:slug>/kick/<int:profile_id>/`
**Method:** `POST`

**Response:**

```json
{
  "success": true,
  "message": "Member removed from team."
}
```

Errors (roster lock, permissions, trying to kick owner) must return:

```json
{
  "success": false,
  "error": "You are not allowed to remove this member.",
  "code": "PERMISSION_DENIED"
}
```

---

### 3.10 Transfer Captaincy / Ownership (AJAX)

**URL names & paths:**

* `teams:transfer_captaincy` → `/teams/<slug:slug>/transfer/<int:profile_id>/`
* `teams:transfer_ownership` → `/teams/<slug:slug>/transfer-ownership/`

Both must:

* Check permissions
* Enforce **unique owner** and **unique captain**
* Respect roster lock when appropriate

**Response (success):**

```json
{
  "success": true,
  "message": "Captaincy has been transferred."
}
```

Errors with proper codes (`OWNER_MUST_EXIST`, `INVALID_TARGET_ROLE`, etc.).

---

## 🟦 4. Tournament-Related Contracts

These endpoints are more about views, but logic needs to be clear.

### 4.1 Team Tournament Registration

**Key URL names:**

* `teams:team_tournaments`
* `teams:tournament_registration_status`
* `teams:tournament_register`
* `teams:cancel_tournament_registration`

Even if some are not AJAX, rules:

* Respect roster lock windows
* Use the same one-team-per-game rule where relevant
* Show clear messaging for blocked actions
* Integrate with tournament app models cleanly

---

## 🟦 5. Error Codes (Recommended Standard)

To make frontend UX consistent, Copilot should standardize error codes, for example:

* `ONE_TEAM_PER_GAME`
* `ROSTER_LOCKED`
* `ALREADY_MEMBER`
* `NOT_A_MEMBER`
* `CANNOT_LEAVE_OWNER`
* `CANNOT_LEAVE_CAPTAIN_LOCKED`
* `PERMISSION_DENIED`
* `INVALID_GAME_CODE`
* `MISSING_GAME_ID`
* `INVITE_EXPIRED`
* `INVITE_NOT_FOUND`
* `JOIN_REQUEST_ALREADY_PENDING`

Front-end will still show **human-readable messages**, but codes will help debugging.

---

## 🟦 6. Security Requirements

All API endpoints must:

1. Validate **authentication** (no anonymous access to team actions).
2. Use **TeamPermissions** for all team-specific actions.
3. Enforce **CSRF** on write operations.
4. Be resilient to:

   * Direct URL tampering
   * Cross-team access (user should not manage teams they aren’t part of)
   * Bypass of UI by calling endpoints directly.

---

## 🟩 7. What Copilot Must Do With This Contract

When Copilot fixes / refactors:

1. **Do not change paths or URL names** unless absolutely necessary.
2. If you must change something, also update:

   * Templates
   * JS (team-create, team-list, team-leave, etc.)
3. Ensure **all AJAX endpoints actually return JSON**.
4. Ensure all **error conditions are explicit**, not silent failures.
5. Ensure **one-team-per-game**, **roster lock**, and **ownership rules** are enforced everywhere consistently.

---
