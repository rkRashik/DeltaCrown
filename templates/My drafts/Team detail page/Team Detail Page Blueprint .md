# **DeltaCrown — Team Detail Page Blueprint** 

## **Part 1: Foundations, Roles, Team Types, Game-Adaptive Architecture, Global Layout**

---

## **0\) What this page is (and what it is NOT)**

### **This page is**

A **role-adaptive Team Profile** that:

* markets the team publicly (identity, roster, results, community)  
* provides interactive surfaces for fans (follow, notifications, supporter actions)  
* provides limited operational tools for members/staff (scrim calendar, match reports, tryout pipeline entry points)  
* stays **clean \+ modern** while still being “advanced” for esports

### **This page is NOT**

The Team Control Plane.  
The control plane is where **settings and management** live (permissions, recruitment rules, sponsor conflicts, treasury, contracts templates, etc.).  
This page should only expose “profile \+ performance \+ engagement” plus a few gated “light ops” shortcuts (e.g., staff can create match report, owner can open control plane).

---

## **1\) Entities & page variants (Team can be standalone or under an org)**

### **1.1 Team ownership types**

**A) Independent Team (standalone)**

* Has its own brand identity (logo/banner/colors)  
* Has its own sponsor surface (but weaker governance)  
* Has its own recruitment pipeline  
* Has its own verification possibility (optional, depending on platform rules)

**B) Organization Team (sub-team)**

* Always linked to an `org_id`  
* Inherits:  
  * verification tier/badge rules  
  * sponsor conflict rules & whitelist  
  * brand inheritance rules (if enabled)  
  * governance/security requirements (2FA for sensitive actions)  
* Has a **Team Tier**:  
  * **Pro**  
  * **Academy**  
  * **Community / Casual**

### **1.2 Page “presentation modes”**

A team page can render one of these “modes” (they can stack):

* **Public Profile Mode** (default for everyone)  
* **Competitive Mode** (tournaments \+ stats emphasized)  
* **Community Mode** (posts, clips, fans, merch emphasized)  
* **Academy Mode** (development metrics, tryouts, coaching emphasized)  
* **Casual Mode** (social, scrims, challenges emphasized)

**Rule of thumb**:  
Team Tier \+ Game \+ Viewer Role determines which modules appear and their visual priority.

---

## **2\) Viewer Roles (dynamic UX rules)**

You already have: Public/Fan, Member, Staff, Owner, Org-level roles. Keep it, but formalize it.

### **2.1 Roles and what changes on the Team Detail page**

**PUBLIC / Fan**

* Sees: identity, roster (public), results summary, public stats, media, sponsors, community, store  
* Can: follow, share, apply/tryout (if open), view schedule, buy merch, join community  
* Cannot: private notes, contracts, finance, internal ops tools, audit logs

**LOGGED-IN NON-MEMBER (fan/applicant)**

* Same as Public \+:  
  * personalized actions (follow \+ notify)  
  * “Apply” flow \+ application status tracking  
  * supporter perks (badges, membership tiers, etc.)

**TEAM MEMBER (player)**

* Adds:  
  * scrim calendar & availability submission  
  * internal announcements  
  * team-only media uploads (if permitted)  
  * view personal performance breakdown (self)

**TEAM STAFF (coach/scout/manager)**

* Adds:  
  * roster operations shortcuts (invite, trial → contract entry point)  
  * applicant list / pipeline entry (but not full config)  
  * match report creation \+ scouting notes  
  * disputes entry points (if allowed)

**TEAM OWNER**

* Adds:  
  * “Open Team Control Plane” primary CTA  
  * finance snapshot (if enabled)  
  * staff/permissions summary entry point  
  * audit/logs entry point (read-only here; full controls elsewhere)

**ORG OWNER / ORG ADMIN (when team is under org)**

* Same as Team Owner \+:  
  * org override badges (e.g., verified)  
  * sponsor conflict enforcement indicator  
  * ability to “detach team” / change tier (usually only in control plane)

**TOURNAMENT ORGANIZER / REFEREE (platform role)**

* Only sees tournament-relevant team data:  
  * roster snapshot export  
  * eligibility status \+ verification flags  
  * match evidence/dispute UI  
* Must not see contracts/finance unless explicitly granted

### **2.2 Permission flags (don’t rely only on role names)**

Every viewer gets explicit booleans in the payload:

* `can_view_private_roster_fields`  
* `can_manage_roster_shortcuts`  
* `can_create_match_report`  
* `can_view_scrims`  
* `can_review_applications`  
* `can_view_finance_summary`  
* `can_open_control_plane`  
* `can_view_audit_preview`  
* `can_view_disputes`  
* `can_publish_posts`  
* `can_upload_media`

This makes the UI resilient even if roles evolve.

---

## **3\) Game-adaptive architecture (critical requirement)**

You have 11 games. They share core concepts (roster, results, schedule) but differ in:

* roster size & roles  
* rank systems & stats  
* match structure (maps, rounds, sets, legs)  
* competitive modes (solo/duo/squad)  
* typical performance metrics

### **3.1 Build a “Game Profile” abstraction**

Define a `game_profile` object in code (frontend and backend) that controls:

**A) Display labels**

* `match_label` (Match / Series / Fixture / Scrim)  
* `map_label` (Map / Arena / Stadium)  
* `role_label` (Role / Position / Agent / Legend)  
* `season_label` (Season / Split / Phase / League)

**B) Roster structure**

* `roster_min`, `roster_max`  
* `lineup_size`  
* `allowed_roles`: array of role names per game (optional)  
* `supports_subs`: boolean  
* `supports_coach_slot`: boolean

**C) Match structure**

* `match_format_types`: BO1/BO3/BO5, legs, sets  
* `supports_map_pool`: boolean  
* `supports_veto`: boolean  
* `score_display_style`: rounds/goals/points/sets

**D) Stats modules**

* `public_team_stats`: list of stats cards to show  
* `player_stats_schema`: keys \+ labels  
* `team_charts`: list of charts to render

**E) Media modules**

* `supports_clips`, `supports_vod`, `supports_highlights`  
* recommended aspect ratios for media

This is what makes the Team Detail page truly dynamic without hardcoding per game everywhere.

---

## **4\) Game grouping (so you don’t build 11 completely separate pages)**

Group games by “page logic similarity” and allow small overrides per game.

### **Group A — Tactical FPS (map/round/BO series heavy)**

* **VALORANT**  
* **Counter-Strike 2**  
* **Rainbow Six Siege**

**Common modules**

* Map pool \+ veto history  
* Role/agent/operator picks  
* Round-based score UI  
* Scrim vs official analytics  
* “Opponent scouting” module (staff)

### **Group B — MOBAs (draft/meta/laning heavy)**

* **Dota 2**  
* **Mobile Legends: Bang Bang**

**Common modules**

* Hero picks/bans  
* Roles: carry/mid/offlane/support OR gold/exp/roam/etc  
* Draft summary card  
* Objective stats (towers, roshan/turtle/lord style)  
* Patch-based performance trend

### **Group C — Mobile Battle Royale / Survival shooter**

* **PUBG MOBILE**  
* **Free Fire**

**Common modules**

* Matches are often “rounds” across a day  
* Stats: placement, kills, damage, survival time  
* Team synergy / consistency charts  
* “Drop zones / map heat” later (advanced)

### **Group D — Sports & Football**

* **EA SPORTS FC 26**  
* **eFootball 2026**

**Common modules**

* Fixtures style schedule  
* Player is often 1v1 (or clubs, depending on your platform)  
* Stats: goals, assists, possession, shots, clean sheets  
* Season table / league standings visuals

### **Group E — Vehicle sports**

* **Rocket League**

**Common modules**

* Sets/series, goals, saves, shots  
* Rotation \+ pressure metrics (advanced)  
* Highlight-heavy media emphasis

### **Group F — Call of Duty Mobile (hybrid)**

* **Call of Duty: Mobile**

Often behaves like FPS group but with mode-based emphasis (Hardpoint/S\&D/etc). Treat it as FPS group with mode overrides.

---

## **5\) Page layout system (modern UI/UX plan)**

### **5.1 Global layout zones**

1. **Hero / Header**  
2. **Sticky Subnav (section tabs)**  
3. **Main Content (two-column on desktop)**  
4. **Right Rail (context widgets)** — collapses into bottom sheets on mobile

### **5.2 Right rail widgets (dynamic)**

Right rail is your “modern dashboard feel” without cluttering the main feed:

* Next match / next scrim card  
* Live status (streaming now)  
* Rank / rating chip  
* “Apply/Tryout” card (if open)  
* Sponsor card (if needed)  
* Quick actions (role gated)

### **5.3 Mobile strategy**

* Hero stays  
* Subnav becomes horizontal scroll  
* Right-rail widgets become:  
  * stacked cards near top OR  
  * a floating “Actions” button that opens a bottom drawer

---

## **6\) Team Header/Hero (game \+ role adaptive)**

### **6.1 Always visible components (all roles)**

* Team banner (team-specific; fallback to org banner if inheritance enabled)  
* Team logo  
* Team name  
* Game badge (with icon)  
* Team tier (Pro/Academy/Community if org team)  
* Status chips:  
  * Active / On Break / Disbanded  
  * Roster Locked (if window closed)  
  * Verified (if org/team verified)  
  * “Recruiting” (if tryouts open)  
  * “Live” (if streaming now)  
* Quick facts row:  
  * Region \+ language  
  * Org association (clickable to org page if present)  
  * Founded date / season  
  * Social icons

### **6.2 CTAs (role gated)**

**PUBLIC / FAN**

* Follow  
* Notify Me (match alerts)  
* View Schedule  
* Apply / Tryout (if open)  
* Share

**MEMBER**

* Availability  
* Team chat / Discord  
* Upload highlight (if allowed)

**STAFF**

* Create match report  
* Review applications  
* Manage roster shortcuts (not full settings)

**OWNER**

* **Open Team Control Plane** (primary CTA)  
* Finance summary (if enabled)  
* Audit preview

### **6.3 Game-adaptive header content**

Some games want a “ranking” hero metric; others want a “record” hero metric.

Example rules:

* FPS/MOBA/Rocket League: show **rating \+ record**  
* BR: show **placement average \+ kills per match**  
* Football: show **W-D-L \+ goals** and optionally league standing

This is driven by `game_profile.hero_metrics`.

---

## **7\) Information Architecture (updated tabs \+ dynamic ordering)**

### **7.1 Recommended base tabs (always exist, may be hidden)**

* Overview  
* Roster  
* Matches  
* Tournaments  
* Scrims *(hidden for public if private)*  
* Performance  
* Media  
* Community  
* Challenges/Bounties  
* Sponsors  
* Store  
* Coaching  
* Economy *(usually gated)*  
* Operations *(staff/owner only)*  
* Audit *(staff/owner only)*

### **7.2 Dynamic tab ordering rules (very important)**

Ordering is not fixed. It adapts:

**Pro team**

* Overview → Roster → Matches → Tournaments → Performance → Media → Sponsors

**Academy team**

* Overview → Roster → Tryouts → Coaching → Scrims → Performance → Matches → Tournaments

**Community/Casual**

* Overview → Roster → Scrims → Challenges → Community → Media → Matches → Store

**Sports games**

* Overview → Roster/Player → Fixtures → Standings → Performance → Tournaments

This keeps the page feeling “made for the game”.

---

## **8\) Data contract (what the Team Detail page needs from backend)**

One payload is best for performance \+ clean wiring:

`GET /api/teams/{team_slug}/detail`

Returns:

{  
  "viewer": {  
    "role": "PUBLIC",  
    "permissions": {  
      "can\_open\_control\_plane": false,  
      "can\_view\_scrims": false  
    }  
  },  
  "team": {  
    "id": "t1",  
    "name": "Protocol V",  
    "game\_key": "VALORANT",  
    "tier": "PRO",  
    "org": { "id": "o1", "name": "SYNTAX Esports", "slug": "syntax-official" },  
    "branding": { "logo\_url": "", "banner\_url": "", "primary\_color": "\#FFD700" },  
    "status": { "state": "ACTIVE", "roster\_locked": true, "recruiting": false, "verified": true }  
  },  
  "game\_profile": {  
    "group": "FPS\_TAC",  
    "labels": { "match": "Series", "map": "Map", "role": "Agent" },  
    "roster": { "lineup\_size": 5, "supports\_subs": true },  
    "stats": { "hero\_metrics": \["rating\_90d", "winrate\_30d"\], "public\_cards": \["winrate", "streak"\] }  
  },  
  "modules": {  
    "tabs": \["overview", "roster", "matches", "tournaments", "performance", "media"\]  
  },  
  "preview": {  
    "next\_match": {},  
    "last\_result": {},  
    "top\_stats": {}  
  }  
}

The key is: backend decides **visibility \+ ordering**, frontend renders it.

---

## **Part 2: Section-by-Section Deep Blueprint (Complete, Game-Adaptive, Role-Adaptive)**

This part continues directly from **Part 1** and defines **every section**, **what appears inside**, **how it adapts by game**, and **how it changes by viewer role**.  
Nothing here overlaps with the Team Control Plane — this is the **Team Profile / Team Hub** surface.

---

## **9\) Overview Section (High-Signal Summary)**

### **Purpose**

Give **instant understanding** of:

* who this team is  
* how they perform  
* what they’re doing right now

This section must be **scan-friendly**, visually rich, and data-driven.

---

### **9.1 Components (all viewers)**

#### **A) Team Bio Block**

* Short bio (2–3 lines)  
* Expandable long bio (“Read more”)  
* Optional **mission / philosophy** (org teams often use this)

**Visibility**

* Public: visible  
* Staff/Owner: editable shortcut (opens control plane)

---

#### **B) Identity & Playstyle Cards (game-adaptive)**

Rendered as compact cards/chips.

Examples:

* **FPS**  
  * Playstyle: Aggressive / Default-heavy / Execute-focused  
  * Preferred maps  
* **MOBA**  
  * Draft identity: Early-game / Scaling / Objective control  
* **BR**  
  * Style: Edge / Center / Hybrid  
* **Sports**  
  * Formation / Play style

---

#### **C) KPI Tiles (game-adaptive)**

Use the same visual system as Org KPIs.

Examples by game group:

**FPS**

* Win rate (30 / 90 days)  
* Avg rounds won  
* Current streak

**MOBA**

* Win rate  
* Avg game length  
* Objective control %

**BR**

* Avg placement  
* Avg kills  
* Consistency score

**Sports**

* W-D-L  
* Goals scored / conceded  
* Clean sheets

---

#### **D) Activity Snapshot**

* Last match result  
* Next scheduled match / scrim  
* Live indicator (if streaming now)

---

### **9.2 Role-based behavior**

* **Public**: read-only  
* **Member**: can add availability note  
* **Staff**: quick “Create Match Report”  
* **Owner**: “Open Team Control Plane” shortcut

---

## **10\) Roster Section (Core of the page)**

### **Purpose**

Show who represents the team — publicly and operationally.

---

### **10.1 Public Roster View**

#### **Components**

* **Starting lineup**  
* **Substitutes / reserves**  
* Player cards:  
  * IGN  
  * Role / position / agent class (game-adaptive)  
  * Country flag  
  * Join date  
  * Status badge (Starter / Sub / Trial)

#### **Privacy rules**

* Real names hidden unless player opted-in  
* Age hidden unless required for tournament compliance

---

### **10.2 Member / Staff Roster View (Enhanced)**

#### **A) Roster Table**

Additional columns:

* Contract state (Trial / Active / Ending Soon)  
* Eligibility status (Verified / Pending / Issue)  
* Availability (last updated)  
* Attendance indicator

#### **B) Player Drawer (click player)**

* Performance snapshot (recent form)  
* Staff notes (staff+)  
* Discipline flags (owner only)  
* Payroll line (owner only)

---

### **10.3 Actions by role**

* **Member**: view own data only  
* **Staff**:  
  * Invite player  
  * Promote trial → contracted  
  * Bench / release (if allowed)  
* **Owner**:  
  * Transfer / buyout handling  
  * Contract overrides (shortcut only)

---

## **11\) Matches Section (Schedule & Results)**

### **Purpose**

Public competitive history \+ internal reporting entry points.

---

### **11.1 Public View**

* Upcoming matches (cards)  
* Recent results (last 10\)  
* Tournament badges  
* Links: match page, VOD, scoreboard

---

### **11.2 Game-adaptive rendering**

**FPS**

* Series score  
* Map breakdown

**MOBA**

* Draft summary  
* Game duration

**BR**

* Multi-round summary  
* Placement trend

**Sports**

* Fixture style (home/away)  
* League round

---

### **11.3 Staff / Owner additions**

* Internal match report button  
* Opponent scouting notes  
* Dispute button (with escalation timer)

---

## **12\) Tournaments Section**

### **Purpose**

Show competitive pedigree and credibility.

---

### **Components**

* Active tournaments  
* Past tournaments:  
  * Placement  
  * Prize won (if public)  
  * Event tier badge  
* Qualification history

---

### **Role differences**

* **Public**: view only  
* **Staff**: register/export roster snapshot  
* **Owner**: prize distribution shortcut

---

## **13\) Scrims Section (Semi-Private)**

### **Purpose**

Operational training visibility.

---

### **Visibility rules**

* Public: hidden or summary only  
* Members: visible  
* Staff/Owner: full

---

### **Components**

* Scrim calendar  
* Attendance tracker  
* Opponent list  
* Performance tags (staff only)

---

## **14\) Performance & Analytics Section**

### **Purpose**

Your **advanced differentiator**.

---

### **14.1 Public (sanitized)**

* Team rating chart (90-day)  
* Win rate by map/mode  
* Highlighted MVP players (opt-in)

---

### **14.2 Staff / Owner (full)**

* Player-by-player stats  
* Scrim vs official comparison  
* Strength-of-schedule  
* Trend alerts:  
  * role gaps  
  * underperformance  
  * burnout risk (future AI)

---

### **Game-adaptive metrics**

Driven entirely by `game_profile.stats`.

---

## **15\) Media Section**

### **Purpose**

Brand \+ storytelling \+ fan engagement.

---

### **Public**

* Highlights  
* VODs  
* Image gallery  
* Embedded streams  
* Social feed

---

### **Staff / Owner**

* Upload media  
* Feature/pin content  
* Brand compliance checks  
* Approval workflow (if org team)

---

## **16\) Community Section**

### **Purpose**

Turn viewers into supporters.

---

### **Components**

* Follow count  
* Fan posts (moderated)  
* Polls / votes  
* Membership tiers (future)  
* Discord integration

---

## **17\) Challenges / Bounties Section**

### **Purpose**

Competitive engagement & monetization.

---

### **Public**

* Open challenges  
* Accepted bounties  
* Results

---

### **Staff / Owner**

* Create challenge  
* Set rules/rewards  
* Review disputes

---

## **18\) Sponsors Section (Conflict-Aware)**

### **Public**

* Sponsor logos  
* Tier labels  
* “Powered by” branding

---

### **Staff / Owner**

* Conflict warnings (org rules)  
* Sponsor assignments per team  
* Allowed brand assets pack

---

## **19\) Store / Merch Section (Optional)**

### **Public**

* Team merch  
* Digital items (badges, banners)  
* Revenue transparency badge

---

### **Owner**

* Revenue summary shortcut

---

## **20\) Coaching & Development (Academy-heavy)**

### **Components**

* Coaches list  
* Training focus  
* Progress metrics  
* Curriculum (academy teams)

---

## **21\) Operations Section (Private)**

### **Staff / Owner only**

* Announcements  
* Scrim attendance  
* Task/checklists  
* Documents vault  
* Incident logs

---

## **22\) Economy Section (Owner-Only, Optional)**

* Team-level prize split override  
* Last 5 transactions  
* Payroll summary  
* Masked payout methods

---

## **23\) Audit Section (Owner / Org Admin)**

* Roster changes  
* Contract actions  
* Application decisions  
* Media publish history  
* Sponsor changes

---

## **24\) Final UX Principles (Critical)**

1. **Never overwhelm**: progressive disclosure  
2. **Game decides layout**, not hardcoded UI  
3. **Role decides visibility**, backend-first  
4. **Profile ≠ Control Plane**  
5. **Everything measurable, nothing fake**

---

### **Status**

✅ This is the **complete, final, production-grade Team Detail Page blueprint**  
✅ Fully compatible with your Org Control Plane  
✅ Scales across **11 games**, **org \+ standalone teams**, and **all roles**

