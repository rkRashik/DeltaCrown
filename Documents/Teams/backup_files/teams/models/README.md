# 📄 **FILE 3/8**

## **apps/teams/models/README.md**

Below is the complete **Models README** for the Teams App.
This explains **every model group**, **how they interact**, **constraints**, and **what developers must never break**.

---

# **Teams App Models — Full Architecture Guide**

**Location:** `apps/teams/models/README.md`

---

# 📌 **1. Overview**

The **models layer** is the backbone of the entire Teams App.

It contains:

### ✔ Core models

* **Team**
* **TeamMembership**
* **TeamInvite**
* **TeamJoinRequest**

### ✔ Ranking system

* RankingCriteria
* TeamRankingHistory
* TeamRankingBreakdown
* TeamRankingSettings

### ✔ Analytics models

* TeamAnalytics
* PlayerStats
* MatchRecord
* MatchParticipation

### ✔ Team discussions

* TeamDiscussionPost
* TeamDiscussionComment

### ✔ Team chat

* TeamChatMessage
* ChatMessageReaction
* ChatReadReceipt
* TeamTypingIndicator

### ✔ Sponsorship & merch

* TeamSponsor
* SponsorInquiry
* TeamMerchItem
* TeamPromotion

### ✔ Tournament integration

* TeamTournamentRegistration
* TournamentParticipation
* TournamentRosterLock

### ✔ Game-specific subclass models

* ValorantTeam
* CS2Team
* MLBBTeam
* PUBGTeam
* etc.

Combined, these make the Teams App one of the most feature-rich ecosystem modules.

---

# 📌 **2. Core Models**

These define the **foundation** of team creation and membership.

---

## **2.1 Team**

Path: `apps/teams/models/_legacy.py`

The **Team** model is extremely large. It contains:

### **Identity Fields**

* name, tag, slug
* description, tagline
* game, region
* logo, banner, roster image

### **Social Attributes**

* discord
* twitch
* instagram
* youtube
* twitter
* linktree
* followers_count
* posts_count

### **Visibility & Privacy**

* is_active
* is_public
* allow_join_requests
* show_roster_publicly
* show_statistics_publicly

### **Competitive Game Integration**

* primary_game
* min_rank_requirement
* hide_member_stats
* hide_social_links

### **Recruiting & Member Settings**

* is_recruiting
* members_can_invite
* auto_accept_join_requests
* require_application_message
* require_post_approval
* members_can_post

### **Ranking & Achievements**

* total_points
* adjust_points
* hero_template

### **Constraints**

* Unique per game per slug
* Unique team name
* Unique tag
* Multiple DB indexes for performance

---

### 🔧 Notes for Developers

✔ Always use the **TeamPermissions** class to check edit rights
✔ Do not directly modify owner/captain fields—use service methods
✔ Avoid querying TeamMembership inside loops—use `.prefetch_related()`
✔ Keep game definitions in sync with `apps.common.game_assets.py`

---

## **2.2 TeamMembership**

Represents a user’s role and status inside a team.

### **Fields**

* member profile
* role (Owner, Manager, Coach, Player, Substitute)
* status (Active, Pending, Removed)
* joined_at
* is_captain (leadership flag)
* can_manage_roster
* can_edit_team
* can_register_tournaments

---

### **Critical Constraints**

🚨 **Only one OWNER is allowed**
🚨 **Only one CAPTAIN is allowed**
🚨 **One membership per user per team**

Django enforces this with:

* UniqueConstraint(condition=is_owner)
* UniqueConstraint(condition=is_captain)
* UniqueConstraint(condition=role=CAPTAIN)
* unique_together(team, profile)

---

### 🔧 Notes for Developers

✔ Do not manually create memberships
✔ Always call service methods:
`TeamMembershipService.create()`,
`promote_to_captain()`,
`transfer_ownership()`

✔ Never bypass DB constraints
✔ Always filter by `status='ACTIVE'`

---

## **2.3 TeamInvite**

Represents an invitation sent to a user.

### **Fields**

* invited_user or invited_email
* team
* inviter
* role to assign
* token (UUID)
* status
* expires_at

### **Constraints**

* Unique token
* Index for quick lookup
* Cannot exceed team roster capacity

### **Flow Supported**

1. Invite
2. Accept
3. Decline
4. Cancel
5. Auto-expire

---

## **2.4 TeamJoinRequest**

User applies to join a team.

### **Fields**

* applicant
* preferred role
* game_id
* message
* status
* review_note
* reviewed_at
* reviewed_by

### **Constraints**

* Unique pending request per team+applicant

### **Flows**

1. Submit request
2. Captain/Manager approval
3. Automatic membership creation

---

# 📌 **3. Ranking Models**

These determine global leaderboard positioning.

---

## **3.1 RankingCriteria**

Defines numeric points for:

* tournament wins
* runner-up
* top 4
* participation
* achievements
* per member
* per month age

Only one active criteria set is used.

---

## **3.2 TeamRankingBreakdown**

Stores granular point categories per team:

* tournament_participation_points
* member_count_points
* achievement_points
* final_total

Used to calculate `team.total_points`.

---

## **3.3 TeamRankingHistory**

Transaction log of all ranking changes.

Each entry stores:

* before/after
* change amount
* source
* related object

---

## **3.4 TeamRankingSettings**

Admin config for ranking multipliers / bonuses.

---

# 📌 **4. Analytics Models**

Contains match, performance, team and player analytics.

Common fields include:

* kills
* assists
* win rate
* tournaments played
* match recaps

---

# 📌 **5. Chat Models (Realtime)**

Provides private team chat.

Models include:

* ChatMessage
* MessageReactions
* ReadReceipts
* TypingIndicator

Backed by Django Channels.

---

# 📌 **6. Discussion Models**

Forum-like posts inside a team.

Models:

* DiscussionPost
* DiscussionComment
* DiscussionSubscription
* DiscussionNotification

---

# 📌 **7. Sponsorship / Merch Models**

Manages:

* Sponsors
* Sponsor inquiries
* Merchandise items
* Promotions
* Click tracking

---

# 📌 **8. Tournament Integration Models**

Core models that link Teams → Tournaments:

* TeamTournamentRegistration
* TournamentParticipation
* TournamentRosterLock
* MatchParticipation

These enforce roster lock rules.

---

# 📌 **9. Game-Specific Team Models**

The project includes sub-classes:

* ValorantTeam
* CS2Team
* Dota2Team
* MLBBTeam
* PUBGTeam
* FreeFireTeam
* CODMTeam
* FC26Team
* EFootballTeam

Purpose:

* Hold game-specific fields
* Store region mappings
* Extend detailed stats

---

# 📌 **10. Critical Developer Guidelines (Must Follow)**

### ❗ NEVER:

* Create memberships directly (`TeamMembership(...)`)
* Move logic into views
* Duplicate validation rules
* Modify _legacy.py without updating the spec
* Add new game types without updating `game_assets.py`

### ✔ ALWAYS:

* Use services to update roles
* Use TeamPermissions for access control
* Keep ranking consistent
* Use `select_related` & `prefetch_related`
* Use transactions when promoting/kicking
* Write migrations for schema changes
* Update documentation after edits

---

# 📌 **11. Where to Add New Models**

→ Create them inside the appropriate module:

* team-wide logic → `/models/team.py`
* membership logic → `/models/membership.py`
* game-specific logic → `/models/games/*.py`
* analytics logic → `/models/analytics/*.py`
* tournament integration → `/models/tournaments/*.py`

---

# 📌 **12. Additional Documentation**

Each of the following will explain in detail:

📄 **File 4/8 — urls.md**
📄 **File 5/8 — views.md**
📄 **File 6/8 — templates.md**
📄 **File 7/8 — static.md**
📄 **File 8/8 — TEAM_APP_MASTER_README.md**

---
