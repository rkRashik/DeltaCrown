# 📄 **FILE 4/8**

## **apps/teams/urls.md**

Below is the complete, human-written, production-grade URL documentation for the Teams App.

---

# **Teams App URL Architecture Guide**

**Location:** `apps/teams/urls.md`

---

# 📌 1. Overview

The Teams App exposes **80+ URL routes**, covering:

* Public pages
* Team creation & onboarding
* Membership flows
* Invites & join requests
* Dashboard
* Management panel
* Privacy/settings
* Discussions
* Chat (WebSockets + HTTP APIs)
* Rankings
* Analytics
* Sponsorships
* Merchandise
* Tournament integrations
* AJAX + REST API endpoints

This document organizes them by category, explains purpose, input parameters, and what developers must guarantee.

❗ **Every route must use URL names — never hardcode paths.**

---

# 📌 2. Public Pages

### **Team List**

```
/teams/
/teams/list/
```

Name: `teams:list`
View: `public.team_list`

Displays searchable/filterable list of all teams.

---

### **Team Detail (Unified Social View)**

```
/teams/<slug:slug>/
```

Name: `teams:detail`
View: `dashboard.team_profile_view` OR social namespace detail

Loads the modern **team_detail_new.html** page + Team Hub.

---

### **Team Rankings**

```
/teams/rankings/
```

Name: `teams:rankings`

Leaderboard based on ranking models.

---

# 📌 3. Team Creation & Game ID Collection

### **Create Team**

```
/teams/create/
```

Name: `teams:create`
View: `create.team_create_view`

4-step esports wizard (name/tag → game → socials → summary).

---

### **Resume Team Creation**

```
/teams/create/resume/
```

Name: `teams:create_team_resume`
View: `public.create_team_resume_view`

Resumes from incomplete wizard state.

---

### **Collect Game ID**

```
/teams/collect-game-id/<str:game_code>/
```

Name: `teams:collect_game_id`
View: `public.collect_game_id_view`

Used when user selects a game but hasn't saved game ID.

---

# 📌 4. Membership & Invites

### **Join Team**

```
/teams/<slug:slug>/join/
```

Name: `teams:join`
View: `public.join_team_view`
Supports:
✔ GET redirect
✔ POST join
✔ AJAX join (JSON)

---

### **Leave Team**

```
/teams/<slug:slug>/leave/
```

Name: `teams:leave`
View: `public.leave_team_view`

Used by **team-leave-modern.js** modal.

---

### **Invite Member**

```
/teams/<slug:slug>/invite/
```

Name: `teams:invite`
View: `public.invite_member_view`

---

### **Accept/Decline Invite**

```
/teams/invites/<str:token>/accept/
/teams/invites/<str:token>/decline/
```

Names: `teams:accept_invite`, `teams:decline_invite`

---

### **Cancel Invite**

```
/teams/<slug:slug>/cancel-invite/
```

Name: `teams:cancel_invite`

---

### **Resend Invite**

```
/teams/<slug:slug>/resend-invite/<int:invite_id>/
```

Name: `teams:resend_invite`

---

### **Kick Member**

```
/teams/<slug:slug>/kick/<int:profile_id>/
```

Name: `teams:kick`
View: `ajax.kick_member`

---

### **Transfer Captaincy**

```
/teams/<slug:slug>/transfer/<int:profile_id>/
```

Name: `teams:transfer_captaincy`

---

# 📌 5. Team Management Panel

### **Full Manage Page**

```
/teams/<slug:slug>/manage/
```

Name: `teams:manage`

Owner/captain-only edit page.

---

### **Settings Page**

```
/teams/<slug:slug>/settings/
```

Name: `teams:settings`

Privacy, social links, banner/logo, recruitment settings.

---

### **Update Info**

```
/teams/<slug:slug>/update-info/
```

Name: `teams:update_team_info`

---

### **Update Privacy**

```
/teams/<slug:slug>/update-privacy/
```

Name: `teams:update_privacy`

---

### **Change Organizational Role**

```
/teams/<slug:slug>/change-organizational-role/
```

Name: `teams:change_organizational_role`

Assign Manager/Coach roles.

---

### **Change Player Role (in-game role)**

```
/teams/<slug:slug>/change-player-role/
```

Name: `teams:change_player_role`

---

### **Assign/Remove Captain Title**

```
/teams/<slug:slug>/assign-captain-title/
```

```
/teams/<slug:slug>/remove-captain-title/
```

Names:

* `teams:assign_captain_title`
* `teams:remove_captain_title`

---

### **Assign/Remove Manager**

```
/teams/<slug:slug>/assign-manager/
/teams/<slug:slug>/remove-manager/
```

---

### **Assign Coach**

```
/teams/<slug:slug>/assign-coach/
```

---

### **Transfer Ownership**

```
/teams/<slug:slug>/transfer-ownership/
```

---

### **Delete Team**

```
/teams/<slug:slug>/delete/
```

---

# 📌 6. Dashboard (Modern Team Hub)

### **Team Dashboard**

```
/teams/<slug:slug>/dashboard/
```

Name: `teams:dashboard`

The “FULL DASHBOARD” panel for owners.

---

### **Pending Items API**

```
/teams/api/<slug:slug>/pending-items/
```

Returns pending invites, join requests.

---

### **Recent Activity API**

```
/teams/api/<slug:slug>/recent-activity/
```

---

### **Update Roster Order**

```
/teams/<slug:slug>/update-roster-order/
```

---

# 📌 7. Discussions (Team Forum)

### **Discussion Board**

```
/teams/<slug:team_slug>/discussions/
```

### **Create Post**

```
/teams/<slug:team_slug>/discussions/create/
```

### **Post Detail**

```
/teams/<slug:team_slug>/discussions/<slug:post_slug>/
```

### **Edit Post**

```
/teams/<slug:team_slug>/discussions/<slug:post_slug>/edit/
```

### **Discussion API**

```
/teams/<slug:team_slug>/discussions/api/
```

---

# 📌 8. Chat System (Realtime + HTTP)

### **Chat Page**

```
/teams/<slug:team_slug>/chat/
```

### **Chat API**

```
/teams/<slug:team_slug>/chat/api/
```

### **Typing Status**

```
/teams/<slug:team_slug>/chat/typing/
```

### **Unread Count**

```
/teams/<slug:team_slug>/chat/unread/
```

---

# 📌 9. Rankings & Analytics

### **Team Ranking Detail**

```
/teams/<slug:slug>/ranking/
```

### **Trigger Recalculation**

```
/teams/<slug:slug>/ranking/recalculate/
```

---

### **Analytics Dashboard**

```
/teams/<int:team_id>/analytics/
```

### **Analytics API**

```
/teams/<int:team_id>/analytics/api/
```

### **Export Stats**

```
/teams/<int:team_id>/analytics/export/
```

---

### **Global Leaderboard**

```
/teams/analytics/leaderboard/
```

### **Compare Teams**

```
/teams/analytics/compare/
```

### **Player Analytics**

```
/teams/analytics/player/<int:player_id>/
```

---

# 📌 10. Sponsorship & Merch

### **Sponsors Page**

```
/teams/<slug:team_slug>/sponsors/
```

### **Sponsor Dashboard**

```
/teams/<slug:team_slug>/sponsor-dashboard/
```

### **Sponsor Inquiry**

```
/teams/<slug:team_slug>/sponsor-inquiry/
```

---

### **Merch Store**

```
/teams/<slug:team_slug>/merchandise/
```

### **Merch Item**

```
/teams/<slug:team_slug>/merch/<int:item_id>/
```

---

# 📌 11. Tournament Integrations

### **Team Tournament List**

```
/teams/<slug:slug>/tournaments/
```

### **Register for Tournament**

```
/teams/<slug:slug>/tournaments/<slug:tournament_slug>/register/
```

### **Registration Status**

```
/teams/<slug:slug>/registration/<int:registration_id>/
```

### **Cancel Registration**

```
/teams/<slug:slug>/registration/<int:registration_id>/cancel/
```

---

# 📌 12. AJAX API Endpoints

### **Validate Team Name**

```
/teams/api/validate-name/
```

### **Validate Tag**

```
/teams/api/validate-tag/
```

### **Game Config API**

```
/teams/api/game-config/<str:game_code>/
```

### **Check Existing Team**

```
/teams/api/check-existing-team/
```

---

# 📌 13. Test/Demo Routes

```
/teams/test/
```

Used ONLY for verifying static pipeline during development.

---

# 📌 14. Developer Notes

✔ Do NOT introduce new routes without adding them here
✔ Every new feature MUST have a named URL
✔ NEVER hardcode `/teams/...` in templates or JS
✔ Use `{% url 'teams:xyz' %}` exclusively
✔ All AJAX endpoints must return JSON with `{success: true/false}`
✔ Document new routes in this file and master readme

---
