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
**Includes:** `templates/teams/_team_hub.html` (role-based dashboard)

### Provides:

* Hero banner
* Tabs (Roster, Stats, Achievements, Social, Activity)
* **Role-Based Team Hub** (fully implemented with 4 distinct sections)
* Leave button modal integration

### Injected Context:

* `team` - Team model instance
* `membership` - User's TeamMembership instance (if member)
* `is_member` - Boolean: user is active member
* `roster` - QuerySet of all active team members
* `roster_count` - Count of active members
* `permissions` - TeamPermissions instance for user

#### **Role Context Flags:**

* `is_owner` - Boolean: user is team owner (Role.OWNER)
* `is_captain` - Boolean: user is team captain
* `is_manager` - Boolean: user is team manager (Role.MANAGER)
* `is_coach` - Boolean: user is team coach (Role.COACH)
* `is_player` - Boolean: user is regular player (Role.PLAYER)

#### **Permission Context Flags:**

* `can_manage_roster` - Boolean: can invite/kick members
* `can_edit_team_profile` - Boolean: can edit team info
* `can_register_tournaments` - Boolean: can register team for tournaments
* `can_leave_team` - Boolean: can leave team (owners cannot)
* `can_view_team_settings` - Boolean: can view team settings page

### Role-Based Dashboard Sections:

The Team Hub (`_team_hub.html`) displays different tools based on user role:

#### **1. Captain Controls** (Owners/Captains Only)
* Full Dashboard access
* Team Settings
* Invite Members
* Manage Roster
* Register for Tournaments
* Team Analytics

#### **2. Manager Tools** (Managers Only, not shown to owners)
* Manage Roster
* Invite Members
* Edit Team Profile
* Register for Tournaments
* View Analytics
* View Settings (read-only)

#### **3. Coach Tools** (Coaches Only)
* Strategy Planner (coming soon)
* Schedule Practice (coming soon)
* Performance Analytics
* Training Materials (coming soon)

#### **4. Member/Player Tools** (All Members)
* Update Game ID
* View Personal Stats
* Notifications
* Team Calendar
* Practice Schedule
* Leave Team (not available to owners)

#### **5. Common Sections** (All Members)
* Communication (Team Chat, Announcements, Voice Channel)
* Quick Links (Tournaments, Leaderboards, Shop)
* Team Information
* Achievements
* Upcoming Events
* Resources

### Template Usage Example:

```django
{% if is_owner or is_captain %}
    <!-- Captain Controls Section -->
    <div class="dashboard-section captain-controls">
        <a href="{% url 'teams:settings' team.slug %}">Team Settings</a>
        <a href="{% url 'teams:invite_member' team.slug %}">Invite Members</a>
    </div>
{% elif is_manager %}
    <!-- Manager Tools Section -->
    <div class="dashboard-section manager-tools">
        <a href="{% url 'teams:manage' team.slug %}">Manage Roster</a>
    </div>
{% elif is_coach %}
    <!-- Coach Tools Section -->
    <div class="dashboard-section coach-tools">
        <span class="badge coming-soon">Strategy Planner (Coming Soon)</span>
    </div>
{% endif %}

<!-- All members see these tools -->
{% if is_member %}
    <div class="dashboard-section member-tools">
        <a href="{% url 'user_profile:update_game_id' %}">Update Game ID</a>
        {% if can_leave_team %}
            <button class="leave-team-btn">Leave Team</button>
        {% endif %}
    </div>
{% endif %}
```

### Side Effects:

* None (read-only view)
* All mutations happen through dedicated management views

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


---

# UPDATED: Modern Team Create (4-Step Wizard)

Added November 19, 2025

## Modern Team Create View

**File:** apps/teams/views/create.py -> team_create_view
**Template:** teams/team_create_modern.html
**URL:** /teams/create/
**Method:** GET, POST
**Auth:** @login_required

### Purpose
Modern 4-step wizard for team creation with:
- Real-time AJAX validation
- Visual game selection with card grid
- Dynamic region loading
- Live preview sidebar
- Terms acceptance

### Steps
1. Basic Info: Name, Tag, Tagline with AJAX validation
2. Game & Region: Visual game cards, one-team-per-game check, dynamic regions
3. Team Profile: Logo/banner uploads, description, socials, live preview
4. Terms & Confirm: Summary, full terms, required checkbox, submission

### Context
- form: TeamCreationForm
- game_configs: JSON of all 9 games with metadata
- available_games: List of game codes
- profile: UserProfile
- STATIC_URL: settings.STATIC_URL

### AJAX Endpoints
- /teams/api/validate-name/ - Check name uniqueness
- /teams/api/validate-tag/ - Check tag uniqueness
- /teams/api/check-existing-team/ - Check one-team-per-game
- /teams/api/game-regions/{code}/ - Get regions for game

### Form Validation
Enhanced clean_game() method:
- Checks existing team membership for game
- Validates game ID requirements (VALORANT, CS2, DOTA2, MLBB)
- Raises ValidationError with friendly messages

### Files
- Template: templates/teams/team_create_modern.html (~600 lines)
- CSS: static/teams/css/team-create-modern.css (1400+ lines)
- JS: static/teams/js/team-create-modern.js (~900 lines)

See TEAM_APP_FUNCTIONAL_SPEC.md Section 14 for complete documentation.
