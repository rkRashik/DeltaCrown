Perfect — I’ll rewrite the **complete, updated, production-grade planning document** by **fully merging**:

* your original final plan  
* the **invite \+ tournament inheritance system**  
* the **team-scoped player identity system**  
* real-world esports tournament requirements (2025–2026 standard)

This version is **logically complete**, **platform-stable**, and **ready to be used by designers, backend engineers, and product managers**.

I’ve reviewed your attached planning document and extended it cleanly without breaking its structure or philosophy .

---

# **DeltaCrown Team HQ (Management Page)**

## **Final, Complete Planning Document (v1.0)**

---

## **1\) Product Definition**

**Team HQ** is the **private operating system** of a team after creation.  
It is the **single source of control** for how a team operates, competes, grows, and presents itself.

It must support:

* **Professional esports workflows**  
* **Tournament compliance**  
* **Role-based governance**  
* **Immutable competitive integrity**

### **Core Responsibilities**

* **Editable controls**  
  Team identity, roster, recruitment, scheduling, content, privacy, notifications.  
* **Operational workflows**  
  Tournament registration, check-ins, results, disputes, evidence, challenges.  
* **System-generated truth**  
  Stats, rankings, match history, trophies, performance analytics.  
* **Governance & security**  
  Roles, permissions, audit logs, sensitive actions.

---

## **2\) Non-Negotiable Platform Rules**

1. **Game immutability**  
   * A team is created **for one game**  
   * Game **cannot be changed** after creation  
   * Game determines:  
     * roster structure  
     * passport fields  
     * tournament eligibility  
2. **System-owned data is read-only**  
   * Stats, rankings, match results  
   * Tournament-earned trophies & titles  
   * Platform-verified bounties  
3. **Role-based access control (RBAC)**  
   * Visibility and actions depend on role  
   * UI reflects permissions  
   * Backend enforces permissions

---

## **3\) Design & UX Principles (Modern Standard)**

### **A) Short Sidebar, Deep Pages**

* **6–7 top-level menus only**  
* Each menu is a **workspace**  
* Complexity lives inside sections, not navigation

### **B) Three Data Zones (Everywhere)**

Each screen clearly shows:

1. **Editable** (team-controlled)  
2. **Actionable** (ops tasks)  
3. **Read-only** (system truth)

### **C) Progressive Disclosure**

* Important info first  
* Advanced controls hidden behind:  
  * tabs  
  * accordions  
  * role gates

### **D) Esports-First Visual Language**

* Team color system (primary \+ accent \+ neutral)  
* Hero header (banner, logo, tag, game icon)  
* Ghost/watermark icons per module  
* Clear typography, high contrast, breathable spacing

---

## **4\) Player Data Architecture (CRITICAL SYSTEM)**

### **4.1 Global User Profile (Foundation – One Time)**

Every user must complete this **once**.  
Applies to **all games and teams**.

**Mandatory Fields**

* Legal Name  
* Date of Birth  
* Email Address  
* Phone Number  
* Country / Region  
* Discord ID

**Why**

* Legal verification  
* Age eligibility  
* Communication  
* Anti-smurf & 2FA  
* Regional enforcement

This data is **owned by the user**, not by teams.

---

### **4.2 Game Passport System (Per Game)**

A user may have **multiple game passports**, one per game.

Each passport contains **only that game’s required data**  
(VALORANT, CS2, Dota 2, MLBB, PUBG Mobile, etc.)

#### **Rules**

* Passport is created **when joining a team for that game**  
* Teams can access **only the passport for their game**  
* Other game passports are **invisible**

---

### **4.3 Team-Scoped Player Profile (Per Team)**

Each team membership creates a **Team Member Profile**.

This solves:

* different display names per team  
* different avatars per team  
* branding alignment

**Editable Fields (Player)**

* Team display name  
* Team profile photo  
* In-game role (if allowed)  
* Visibility preferences

**Editable Fields (Admin/Manager)**

* Team role (Starter/Sub/Staff)  
* Roster slot  
* Permissions (if allowed)

**Read-Only References**

* Global profile (identity verification)  
* Game passport (tournament data)

---

## **5\) Tournament Readiness & Inheritance System**

### **5.1 Tournament Registration Logic**

When a team attempts to register:

1. System checks **team-level requirements**  
2. System checks **each rostered player**  
3. Data is auto-pulled from:  
   * Global User Profile  
   * Team-game Passport  
   * Team-scoped player profile (display only)

### **5.2 Validation States**

* ✅ **Ready** – all required fields present  
* ⚠️ **Incomplete** – optional fields missing  
* ❌ **Blocked** – required fields missing

Blocked registrations:

* Show **exact missing fields**  
* Allow admins to:  
  * notify players  
  * request completion

---

## **6\) Final Menu Architecture (Team HQ)**

### **1\) 🎯 Command Center**

**Purpose:** real-time team overview

**Includes**

* Today board (next match/scrim/practice)  
* Action Center (role-based)  
* Alerts & readiness  
* Recent activity summary

---

### **2\) 👥 Roster Ops**

**Purpose:** people \+ structure \+ control

**Sections**

* Active Roster  
* Staff & Roles  
* Invites & Join Requests  
  * invite by username / email / search  
  * assign initial team role  
* Tryouts & Recruitment Pipeline  
* Roster Lock Center  
* Roles & Permissions  
* Member Detail Sheet  
  * full tournament-relevant data view (permission-gated)

---

### **3\) 🏆 Competition Hub**

**Purpose:** competitive lifecycle

**Sections**

* Tournament Operations  
* Match Center  
* Results & Evidence  
* Disputes  
* Achievements (system-earned \+ curated pins)

---

### **4\) 🧠 Training Lab**

**Purpose:** improvement & preparation

**Sections**

* Practice Planner  
* Scrims  
* VOD & Review  
* Playbook

#### **Challenges & Bounties**

* Team Challenges  
* Player Challenges  
* Internal Bounties  
* Platform Bounties (system-verified)

---

### **5\) 📣 Community & Media**

**Purpose:** content \+ community app integration

**Sections**

* Community Spaces  
  * internal team  
  * public fans  
* Posts & Announcements  
* Highlights  
* Media Library  
* Engagement Insights (read-only)

---

### **6\) 🎨 Team Profile**

**Purpose:** public identity control

**Sections**

* Brand Identity  
* About (mission, style, pace, focus)  
* Region & Tags  
* Connect (socials)  
* Public Page Layout

**Locked**

* Game  
* Core identifiers

---

### **7\) 🛡️ Settings & Security**

**Purpose:** governance & safety

#### **A) Privacy Settings**

* profile visibility  
* roster/stat visibility  
* join/follow rules  
* member privacy

#### **B) Notification Settings**

* in-app / email / push  
* event toggles  
* per-role defaults

#### **C) Access Control**

* roles  
* permission matrix  
* overrides

#### **D) Integrations**

* game accounts  
* Discord  
* external tools

#### **E) Audit Logs (read-only)**

#### **F) Danger Zone**

* transfer ownership  
* archive team  
* delete team

---

## **7\) Optional Organization Layer**

### **🏢 Organization Console (Org Admin Only)**

* Org overview  
* All teams  
* Cross-team staff  
* Verification & compliance  
* Org-wide brand rules

---

## **8\) Role-Based Experience Summary**

### **👤 Member**

* view ops  
* limited actions  
* personal team profile edit

### **👔 Staff**

* training & competition support  
* moderation tools

### **👑 Owner**

* full team control  
* governance & danger zone

### **🏢 Org Admin**

* everything \+ org layer

---

## **9\) Demo Controller (Template Only)**

* Floating bottom-right button  
* Opens demo panel:  
  * role switch  
  * game preview switch (labelled demo)  
  * team color picker  
* **Does not exist in production**

---

Below is a **deep, implementation-ready document** focused **only** on **Menu Architecture** for the **DeltaCrown Team HQ**, written so it can be used by:

* product designers (UX / IA)  
* frontend engineers  
* backend / permission designers  
* future maintainers

This goes **menu by menu**, explains **why it exists**, **what lives inside**, **who can see it**, **what is editable vs read-only**, and **how it behaves in real esports workflows**.

---

# **DeltaCrown Team HQ**

## **Menu Architecture – Detailed Specification**

---

## **0\) Philosophy of the Menu System**

Before listing menus, these rules define *how* the menu works.

### **Core Principles**

1. **Few menus, deep sections**  
   The sidebar is *not* a feature list. It is a **workspace switcher**.  
2. **Esports mental model, not SaaS mental model**  
   Real teams think in terms of:  
   * roster  
   * competition  
   * practice  
   * content  
   * governance  
3. **Action ≠ Edit ≠ View**  
   Every section clearly distinguishes:  
   * things you can **edit**  
   * things you can **do**  
   * things you can **only see**  
4. **Role-driven visibility**  
   If you don’t have permission:  
   * the menu may be hidden, OR  
   * the menu is visible but actions are disabled with explanation

---

## **1\) 🎯 Command Center (HQ)**

### **Purpose**

The **operational heartbeat** of the team.

This is **not** a dashboard full of charts.  
It answers one question:

“What does this team need to do right now?”

### **Who sees it**

* 👤 Member  
* 👔 Staff  
* 👑 Owner  
* 🏢 Org Admin

(Everyone)

---

### **Sections inside Command Center**

#### **1.1 Today Board**

**What it shows**

* Next match (time, opponent, tournament)  
* Next scrim  
* Next practice  
* Countdown timers

**Behavior**

* Read-only for most users  
* Click-through to Match Center / Training Lab

---

#### **1.2 Action Center (Role-gated)**

**What it shows**  
Contextual action buttons, such as:

* Invite member  
* Post announcement  
* Open recruitment  
* Register / Check-in tournament  
* Create practice session

**Rules**

* Buttons only appear if user has permission  
* Disabled buttons show *why* (e.g., “Roster locked”)

---

#### **1.3 Alerts & Readiness**

**What it shows**

* Tournament roster lock warnings  
* Missing player data (passport fields)  
* Pending join requests  
* Pending approvals

**Rules**

* This is **system-driven**  
* No editing, only resolution actions

---

#### **1.4 Recent Activity**

**What it shows**

* Roster changes  
* Role changes  
* Tournament registrations  
* Content posts  
* Admin actions

**Rules**

* Read-only  
* Filterable  
* Audit-friendly

---

## **2\) 👥 Roster Ops**

### **Purpose**

This is the **people management system** of the team.

If Command Center is the “what”,  
Roster Ops is the “who”.

### **Who sees it**

* 👤 Member → view-only (limited)  
* 👔 Staff → partial control  
* 👑 Owner → full control  
* 🏢 Org Admin → full control

---

### **Sections inside Roster Ops**

#### **2.1 Active Roster**

**What it shows**

* Starters / Subs / Bench (game-aware)  
* In-game roles  
* Status: Active / Pending / Locked

**Editable**

* Role assignment (admin)  
* Roster slot (admin)

**Read-only**

* Eligibility status  
* Lock indicators

---

#### **2.2 Staff & Roles**

**What it shows**

* Coaches  
* Analysts  
* Managers  
* Content staff

**Editable**

* Assign staff roles  
* Remove staff  
* Adjust permissions

---

#### **2.3 Invites & Join Requests**

**What it does**

* Invite by:  
  * username  
  * email  
  * search user  
* Assign **initial team role**  
* Approve / reject requests

**Rules**

* Invites are role-aware  
* Expired / pending states shown  
* Audit logged

---

#### **2.4 Tryouts & Recruitment Pipeline**

**What it shows**

* Applicants  
* Tryout stages  
* Notes & evaluations

**Purpose**  
Talent acquisition without cluttering roster.

---

#### **2.5 Roster Lock Center**

**What it shows**

* Active locks  
* Reason (tournament)  
* Lock duration

**Behavior**

* Disables roster changes  
* Explains *why* actions are blocked

---

#### **2.6 Roles & Permissions**

**What it shows**

* Role templates  
* Permission matrix  
* Member overrides

**Critical**  
This is where RBAC is managed.

---

#### **2.7 Member Detail Sheet**

**What it shows (permission-gated)**

* Global user profile (read-only)  
* Game passport (read-only)  
* Team-scoped profile (editable if allowed)  
* Tournament readiness status

This is **essential** for tournament admins.

---

## **3\) 🏆 Competition Hub**

### **Purpose**

Everything related to **official competition** lives here.

### **Who sees it**

* 👤 Member → mostly view  
* 👔 Staff → operations  
* 👑 Owner → full  
* 🏢 Org Admin → full

---

### **Sections inside Competition Hub**

#### **3.1 Tournament Operations**

**What it does**

* Register team  
* Check-in  
* View requirements  
* View eligibility status

**Rules**

* Registration blocked if readiness fails  
* Uses passport inheritance

---

#### **3.2 Match Center**

**What it shows**

* Upcoming  
* Live  
* Completed matches

**Actions**

* Submit results  
* Confirm scores

---

#### **3.3 Results & Evidence**

**What it does**

* Upload screenshots  
* Attach proof  
* View match evidence

---

#### **3.4 Disputes**

**What it does**

* Open dispute  
* View resolution steps  
* Upload additional proof

**Role-gated**

---

#### **3.5 Achievements**

**What it shows**

* Trophies  
* Badges  
* Titles

**Rules**

* System-earned \= read-only  
* Team-curated pins allowed

---

## **4\) 🧠 Training Lab**

### **Purpose**

Non-official competition improvement.

### **Who sees it**

* 👤 Member → view / attendance  
* 👔 Staff → manage  
* 👑 Owner → full

---

### **Sections inside Training Lab**

#### **4.1 Practice Planner**

* Sessions  
* Attendance  
* Goals

---

#### **4.2 Scrims**

* Requests  
* Confirmations  
* Notes

---

#### **4.3 VOD & Review**

* Links  
* Timestamps  
* Tasks

---

#### **4.4 Playbook**

* Strategies  
* Drafts  
* Roles  
* Protocols

---

#### **4.5 Challenges & Bounties**

**Team Challenges**

* Weekly/monthly goals

**Player Challenges**

* Performance targets

**Bounties**

* Internal (team)  
* Platform (verified)

---

## **5\) 📣 Community & Media**

### **Purpose**

Brand, fans, and internal communication.

### **Who sees it**

* 👤 Member → post (if allowed)  
* 👔 Staff → moderate  
* 👑 Owner → full

---

### **Sections inside Community & Media**

#### **5.1 Community Spaces**

* Internal team space  
* Public fan space  
* Category-based threads

---

#### **5.2 Posts & Announcements**

* Create  
* Edit  
* Pin  
* Schedule

---

#### **5.3 Highlights**

* Curated highlights  
* Tournament-linked highlights

---

#### **5.4 Media Library**

* Upload assets  
* Tag usage

---

#### **5.5 Engagement Insights**

* Followers  
* Views  
* Interaction (read-only)

---

## **6\) 🎨 Team Profile**

### **Purpose**

Controls the **public Team Detail page**.

### **Who sees it**

* 👤 Member → view  
* 👔 Staff → partial edit  
* 👑 Owner → full

---

### **Sections inside Team Profile**

#### **6.1 Brand Identity**

* Logo  
* Banner  
* Team colors  
* Brand marks

---

#### **6.2 About**

* Motto  
* Mission  
* Style / Pace / Focus  
* Description

---

#### **6.3 Region & Tags**

* Competitive region  
* Discoverability tags

---

#### **6.4 Connect**

* Social links  
* Discord, Twitch, YouTube

---

#### **6.5 Public Page Layout**

* Enable/disable modules  
* Order sections

---

#### **Locked Fields**

* Game  
* Core identifiers

---

## **7\) 🛡️ Settings & Security**

### **Purpose**

Governance, privacy, safety.

### **Who sees it**

* 👑 Owner  
* 🏢 Org Admin  
  (Some personal settings for Members)

---

### **Sections inside Settings & Security**

#### **7.1 Privacy Settings**

* Profile visibility  
* Module visibility  
* Join/follow rules  
* Member privacy

---

#### **7.2 Notification Settings**

* Channels  
* Event toggles  
* Role defaults

---

#### **7.3 Access Control**

* Roles  
* Permissions  
* Overrides

---

#### **7.4 Integrations**

* Game accounts  
* Discord  
* Tools

---

#### **7.5 Audit Logs**

* Immutable activity log

---

#### **7.6 Danger Zone**

* Transfer ownership  
* Archive team  
* Delete team

---

## **8\) 🏢 Organization Console (Conditional)**

Only visible to **Org Admin**.

### **Sections**

* Org overview  
* All teams  
* Cross-team staff  
* Verification  
* Brand rules

---

