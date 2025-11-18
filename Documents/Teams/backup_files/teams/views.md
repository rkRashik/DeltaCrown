# ✔ File 5/8 Sent in the Previous Turn?

It seems there was a misunderstanding — **File 5/8 has not been generated yet.**
You just responded “next,” so I will now generate:

---

# 📄 **FILE 5/8**

## **apps/teams/views.md**

### (*Full documentation of all Views in the Teams App*)

This is the **most complex file** in the documentation set — it fully explains every major view category, their inputs, outputs, permissions, side-effects, and cross-dependencies.

---

# 🟦 **Teams App — Views Architecture & Responsibilities**

**Location:** `apps/teams/views.md`
**Covers:**
✔ Public views
✔ Create wizard views
✔ Dashboard views
✔ Management views
✔ Membership flows
✔ Invite flows
✔ AJAX APIs
✔ Analytics
✔ Sponsorship
✔ Tournament integration
✔ Discussions & Chat

---

# 🔷 1. Public Views

---

## **1.1 Team List**

**View:** `apps.teams.views.public.team_list`
**Templates:** `teams/list.html`
**Purpose:** Display all teams with filters.

### **Accepts Query Params**

* `q` search
* `game`, `region`
* `sort`, `order`
* `recruiting`, `verified`, `featured`
* `founded_year_from`, `founded_year_to`
* Pagination: `page`

### **Returns**

* List of teams
* Filter state
* Pagination
* Game/Region lists

### **Side Effects: NONE**

---

## **1.2 Team Detail (Modern)**

**View:** `apps.teams.views.dashboard.team_profile_view`
**Template:** `teams/team_detail_new.html`

### Provides:

* Hero banner
* Tabs (Roster, Stats, Achievements, Social, Activity)
* Team Hub (role-aware)
* Leave button modal integration

### Injected Context:

* `team`
* `membership`
* `is_captain`
* `is_owner`
* `roster`
* `roster_count`
* `permissions` (TeamPermissions)

---

# 🔷 2. Team Creation Views

---

## **2.1 Create Team**

**View:** `create.team_create_view`
**Template:** `teams/team_create_esports.html` or `team_create.html`

### Steps (JS-driven wizard)

1. Team info
2. Game selection
3. Socials
4. Summary
5. Submit → Create team

### Validations:

* Unique name/tag
* One-team-per-game
* Required game ID?
* Conditions per game (from game_config)

### Redirects:

* To game ID page (if missing)
* To resume page (if session stored)

---

## **2.2 Resume Team Creation**

**View:** `public.create_team_resume_view`
**Template:** `team_create_esports.html`

Rehydrates:

* Name, tag
* Socials
* Game selection (but **not files**)

---

## **2.3 Collect Game ID**

**View:** `public.collect_game_id_view`
**Template:** `collect_game_id.html`

Triggered when:

* User selects a game (ex: Valorant)
* But their profile is missing Riot ID

---

# 🔷 3. Membership & Join/Leave Views

---

## **3.1 Join Team**

**View:** `public.join_team_view`

### Accepts:

* GET → redirect to team detail
* POST / AJAX → attempt join

### Validation:

* Not already member
* Must have required game ID
* Must not violate one-team-per-game
* Team must allow joining (`allow_join_requests` OR `is_open`)

### Returns:

JSON:

```json
{
  "success": true,
  "team_url": "/teams/<slug>/"
}
```

or HTML message.

---

## **3.2 Leave Team**

**View:** `public.leave_team_view`
**Template:** None (JSON or redirect)
**JS:** `team-leave-modern.js`

### Validates:

* User is ACTIVE member
* Not OWNER
* TeamPermissions.can_leave_team

### Side effects:

* Deletes TeamMembership
* Removes cached permissions

---

## **3.3 Kick Member (AJAX)**

**View:** `ajax.kick_member`

### Returns JSON:

```json
{
  "success": true,
  "removed_profile_id": 123
}
```

Requires:

* Captain/Manager permissions

---

## **3.4 Transfer Captaincy**

**View:** `ajax.transfer_captaincy`

### Validates:

* Caller is OWNER or CAPTAIN
* New captain is ACTIVE member

Side effects:

* Demote old captain
* Promote new one

---

# 🔷 4. Invite System Views

---

## **4.1 Invite Member**

**View:** `public.invite_member_view`
**Template:** `invite_member.html`

---

## **4.2 Accept/Decline Invite**

**Views:**

* `public.accept_invite_view`
* `public.decline_invite_view`

### Accept flow:

* Validate token
* Ensure roster capacity
* Ensure one-team-per-game
* Create membership
* Mark invite ACCEPTED

---

## **4.3 Cancel Invite**

**View:** `public.cancel_invite_view`

---

## **4.4 AJAX Resend Invite**

**View:** `dashboard.resend_invite`

---

# 🔷 5. Team Dashboard Views

The heart of the team backend.

---

## **5.1 Dashboard Main**

**View:** `dashboard.team_dashboard_view`
**Template:** `dashboard_modern.html`

Contains:

* Quick stats
* Recent activity
* Ranked power score
* Role-aware controls

---

## **5.2 Pending Items API (AJAX)**

**View:** `dashboard_api.get_pending_items`

Returns:

* Pending invites
* Pending join requests
* Unapproved posts

---

## **5.3 Recent Activity API**

**View:** `dashboard_api.get_recent_activity`

---

## **5.4 Update Roster Order (AJAX)**

**View:** `dashboard.update_roster_order`

---

# 🔷 6. Team Management Views

(Owner / Manager / Captain roles)

---

## **6.1 Manage Team**

**View:** `public.manage_team_view`
**Template:** `manage.html`

---

## **6.2 Settings Page**

**View:** `public.team_settings_view`
**Template:** `settings_enhanced.html`

---

## **6.3 Update Info**

**View:** `public.update_team_info_view`
(Update name, tag, description, socials)

---

## **6.4 Update Privacy**

**View:** `public.update_privacy_view`

---

## **6.5 Organizational Roles**

### Assign:

* Manager
* Coach
* Captain (title)

### Views:

```
assign_manager_view  
remove_manager_view  
assign_coach_view  
assign_captain_title_view  
remove_captain_title_view  
```

---

## **6.6 Transfer Ownership**

**View:** `role_management.transfer_ownership_view`

---

# 🔷 7. Discussions Views

(Team Forums)

---

## **7.1 Board**

```
DiscussionBoardView
```

## **7.2 Create/Edit Post**

```
DiscussionPostCreateView
DiscussionPostEditView
```

## **7.3 Post Detail**

```
DiscussionPostDetailView
```

## **7.4 Discussion API**

```
DiscussionAPIView
```

---

# 🔷 8. Chat Views

(WebSockets + HTTP APIs)

---

## **8.1 Chat UI**

```
TeamChatView
```

## **8.2 Chat API**

```
ChatAPIView
```

## **8.3 Typing Status**

```
ChatTypingStatusView
```

## **8.4 Unread Count**

```
ChatUnreadCountView
```

---

# 🔷 9. Analytics Views

---

## **9.1 Analytics Dashboard**

```
TeamAnalyticsDashboardView
```

## **9.2 Performance API**

```
TeamPerformanceAPIView
```

## **9.3 Export Stats**

```
ExportTeamStatsView
```

## **9.4 Global Leaderboard**

```
LeaderboardView
```

## **9.5 Compare Teams**

```
TeamComparisonView
```

---

# 🔷 10. Sponsorship Views

---

## **10.1 Sponsors**

```
TeamSponsorsView
```

## **10.2 Sponsor Dashboard**

```
SponsorDashboardView
```

## **10.3 Sponsor Inquiry**

```
SponsorInquiryView
```

## **10.4 Merch**

```
TeamMerchandiseView  
MerchItemDetailView
```

---

# 🔷 11. Tournament Integration Views

---

## **11.1 Team Tournaments Overview**

```
team_tournaments_view
```

## **11.2 Register Team**

```
tournament_registration_view
```

## **11.3 Registration Status**

```
tournament_registration_status_view
```

## **11.4 Cancel Registration**

```
cancel_tournament_registration
```

---

# 🔷 12. AJAX Utility Views

---

### Validate name:

```
validate_team_name
```

### Validate tag:

```
validate_team_tag
```

### Check user identifier:

```
validate_user_identifier
```

### Check existing team:

```
check_existing_team
```

### Game config:

```
get_game_config_api
```

---
