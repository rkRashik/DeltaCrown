# DeltaCrown Tournament Engine - Project Brief

**Date:** November 2, 2025  
**Project:** New Tournament System Development  
**Client:** DeltaCrown Esports Platform  
**Engagement Type:** Full Discovery, Architecture, Design & Implementation

---

## 1. Project Vision

I am looking to build a **new, production-ready tournament system** for DeltaCrown that is highly competitive in the current 2025 esports market.

This system must manage the **complete tournament lifecycle**:
- **Before:** Initial organizing, setup, and team registration
- **During:** Live match management, bracket progression, score reporting
- **After:** Final results, prize distribution, and ranking updates

### Critical Design Requirement

The system **must be modular, organized, and "pluggable"** to:
1. **Facilitate easy management** of complex tournament workflows
2. **Enable rapid addition of new games** without modifying core tournament logic
3. **Support diverse game mechanics** (1v1, 5v5, 4v4, squads, different scoring systems)
4. **Integrate seamlessly** with our existing DeltaCrown platform (Teams, Economy, Notifications)

**Why This Matters:** We're not building a "Valorant tournament system" or an "eFootball tournament system." We're building a **universal tournament engine** that works for any competitive game through pluggable game modules.

---

## 2. Your Role as Development Partner

### What We Expect From You

You are not just hired to type code. You are a **proactive development partner** responsible for:

#### 2.1 Market Research & Competitive Analysis

**Requirement:** Before designing a single feature, you must actively research and analyze successful tournament platforms:
- **Platforms to Study:** Battlefy, Challengermode, Toornament, FACEIT, ESL Play
- **Games to Understand:** Valorant, eFootball, EA Sports FC, PUBG Mobile, Free Fire, MLBB, CS2, Dota 2, Call of Duty Mobile, 
Fortnite, Rocket League, Apex Legends, and others. 


**Goal:** Understand how modern games and tournaments work **in 2025**, not 5 years ago. The information you gather must be used to build a system that is:
- ✅ **Updated** - Reflects current esports standards
- ✅ **Professional** - Competitive with leading platforms
- ✅ **Feature-complete** - Not missing critical functionality

**Deliverable:** A research report documenting:
- Feature comparison matrix (DeltaCrown vs. competitors)
- Best practices from each platform
- Recommended features to implement (with priorities)

---

#### 2.2 Frontend Design & User Experience (UI/UX)

**This is a 2025 esports platform.** The user interface is a **top priority**, just as important as backend logic.

**Design Standards:**
- 🎮 **Esports Gaming Vibe** - Modern, exciting, fast, cyberpunk-inspired aesthetics
- 🚀 **Not a Corporate Website** - This is an entertainment platform for gamers
- 💎 **Beautiful & Elegant** - High-quality, responsive, visually impressive
- ⚡ **Performance Matters** - Fast loading, smooth animations, real-time updates
- 📱 **Mobile-First** - Perfect experience on all devices

**Deliverables Required:**
1. **Complete Design System (Figma or similar):**
   - Component library (buttons, cards, brackets, scoreboards, etc.)
   - Color palette (with dark mode as primary)
   - Typography system
   - Icon set
   - Animation guidelines

2. **High-Fidelity Mockups:**
   - All tournament pages (Desktop & Mobile)
   - User flow diagrams
   - Interactive prototypes

3. **Responsive Design:**
   - Desktop (1920px, 1440px, 1280px)
   - Tablet (768px)
   - Mobile (375px, 414px)

**Inspiration:** Look at Valorant Champions Tour website, League of Legends Worlds site, BLAST Premier CS2 tournament pages.

---

## 3. Technical Context: Existing DeltaCrown Platform

### 3.1 Current Architecture

**Technology Stack:**
- **Framework:** Django 4.2+ (Python)
- **Database:** PostgreSQL
- **Cache/Broker:** Redis
- **Task Queue:** Celery
- **Real-time:** Django Channels (WebSocket)
- **Frontend:** Django Templates (not React/Vue SPA)

**Active Apps (15):**
```
apps/
├── accounts/          # User authentication (AUTH_USER_MODEL)
├── user_profile/      # Extended profiles with 9 game IDs
├── teams/             # Team management (794-line Team model)
├── economy/           # DeltaCoin wallet & transactions
├── ecommerce/         # DeltaStore (11 models)
├── siteui/            # UI + Community features (5 models)
├── notifications/     # 15+ notification types
├── dashboard/         # User dashboard
└── ... (7 more)
```

**Legacy System (Moved to `legacy_backup/` on November 2, 2025):**
- `apps/tournaments/` - Old tournament system (deprecated)
- `apps/game_valorant/` - Valorant-specific logic (deprecated)
- `apps/game_efootball/` - eFootball-specific logic (deprecated)

**Why Rebuilt?** Old system was:
- ❌ Too tightly coupled to specific games
- ❌ Not modular (adding new games required core changes)
- ❌ Incomplete features (dispute resolution never finished)
- ❌ Poor separation of concerns

---

### 3.2 Critical Integration Points

The new tournament engine **must integrate** with these existing apps:

#### Integration 1: `apps/economy` (Prize Distribution)

**Model:** `DeltaCrownTransaction`
```python
class DeltaCrownTransaction(models.Model):
    class Reason(models.TextChoices):
        TOURNAMENT_PARTICIPATION = 'TOURNAMENT_PARTICIPATION', 'Tournament Participation'
        TOURNAMENT_PLACEMENT = 'TOURNAMENT_PLACEMENT', 'Tournament Placement'
        # ... more reasons
    
    wallet = models.ForeignKey('DeltaCrownWallet', on_delete=models.PROTECT)
    amount = models.IntegerField()  # DeltaCoin amount
    reason = models.CharField(max_length=50, choices=Reason.choices)
    idempotency_key = models.CharField(max_length=100, unique=True)  # Prevents double-payment
    tournament_id = models.IntegerField(null=True, db_index=True)  # Reference to tournament
```

**Service Layer:** `apps/economy/services.py`
```python
def award(*, profile, amount, reason, note, idempotency_key, tournament_id=None):
    """Award DeltaCoin with idempotency guarantee"""
    # ... implementation
```

**Your Responsibility:**
- Design how tournament engine calls `economy.services.award()` after tournament completion
- Define coin amounts for each placement (1st, 2nd, 3rd, participation)
- Ensure idempotency (tournament payouts must never duplicate)

---

#### Integration 2: `apps/teams` (Ranking Updates)

**Models:** `Team`, `TeamRankingBreakdown`, `TeamRankingHistory`
```python
class Team(models.Model):
    total_points = models.IntegerField(default=0)  # Cumulative ranking points
    wins = models.IntegerField(default=0)
    losses = models.IntegerField(default=0)
    # ... 794 lines total

class TeamRankingBreakdown(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    source = models.CharField(max_length=50)  # e.g., 'tournament_win', 'tournament_participation'
    points = models.IntegerField()
    tournament_id = models.IntegerField(null=True, db_index=True)
```

**Ranking Service:** `apps/teams/services/ranking_service.py`
```python
def recalculate_team_points(team, reason):
    """Recalculate team ranking points from all sources"""
    # ... implementation
```

**Your Responsibility:**
- Design how tournament engine triggers ranking updates
- Define point values for tournament placements
- Handle team vs. solo tournament results

---

#### Integration 3: `apps/notifications` (Tournament Notifications)

**Model:** `Notification`
```python
class Notification(models.Model):
    class NotificationType(models.TextChoices):
        TOURNAMENT_REMINDER = 'TOURNAMENT_REMINDER', 'Tournament Reminder'
        MATCH_SCHEDULED = 'MATCH_SCHEDULED', 'Match Scheduled'
        MATCH_RESULT = 'MATCH_RESULT', 'Match Result'
        # ... 15+ types total
    
    recipient = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=50, choices=NotificationType.choices)
    tournament_id = models.IntegerField(null=True, db_index=True)
```

**Your Responsibility:**
- Design notification triggers for tournament events
- Define which actions send notifications (match start, score submission, disputes, etc.)
- Support 4 delivery channels (Email, SMS, Push, In-App)

---

#### Integration 4: `apps/user_profile` (Game IDs)

**Model:** `UserProfile`
```python
class UserProfile(models.Model):
    # 9 game ID fields
    riot_id = models.CharField(max_length=50, blank=True)  # Valorant, LoL
    riot_tagline = models.CharField(max_length=20, blank=True)  # e.g., #NA1
    steam_id = models.CharField(max_length=50, blank=True)  # CS2, Dota 2
    efootball_id = models.CharField(max_length=50, blank=True)  # eFootball
    ea_id = models.CharField(max_length=50, blank=True)  # FIFA, Apex
    mlbb_id = models.CharField(max_length=50, blank=True)  # Mobile Legends
    codm_uid = models.CharField(max_length=50, blank=True)  # COD Mobile
    pubg_mobile_id = models.CharField(max_length=50, blank=True)  # PUBG Mobile
    free_fire_id = models.CharField(max_length=50, blank=True)  # Free Fire
```

**Your Responsibility:**
- Design how game modules validate player IDs during registration
- Handle missing game IDs (user must add before registering)
- Support future game ID additions

---

## 4. Core Feature Requirements

### 4.1 The "Pluggable Game Module" Architecture 🎮

**This is the most critical technical requirement.**

You must design a system where adding a new game is as simple as:
1. Create a new `GameModule` class
2. Implement required interfaces (team size, player IDs, scoring logic, settings)
3. Register the module
4. Done - tournament engine now supports the game

#### Game Module Interface (Design Required)

Each `GameModule` must provide:

**1. Game Metadata:**
```python
class GameModule:
    game_name: str  # "Valorant", "eFootball", "PUBG Mobile"
    game_slug: str  # "valorant", "efootball", "pubgm"
    icon: str  # Icon identifier
    category: str  # "FPS", "Sports", "Battle Royale"
```

**2. Player ID Requirements:**
```python
def get_required_player_ids(self) -> List[PlayerIDField]:
    """
    Example for Valorant:
    [
        PlayerIDField(name="riot_id", label="Riot ID", required=True),
        PlayerIDField(name="riot_tagline", label="Tagline", required=True),
    ]
    
    Example for PUBG Mobile:
    [
        PlayerIDField(name="pubg_mobile_id", label="In-Game UID", required=True),
    ]
    """
```

**3. Team Structure:**
```python
def get_team_config(self) -> TeamConfig:
    """
    Example for Valorant:
    TeamConfig(
        players_per_team=5,
        min_roster_size=5,
        max_roster_size=7,  # 5 starters + 2 subs
        allows_substitutions=True,
    )
    
    Example for 1v1 eFootball:
    TeamConfig(
        players_per_team=1,
        min_roster_size=1,
        max_roster_size=1,
        allows_substitutions=False,
    )
    """
```

**4. Result Logic (Most Complex):**
```python
def parse_match_result(self, result_data: dict) -> MatchResult:
    """
    Handle different scoring systems:
    
    Map Score (Valorant/CS2):
    - Input: {"team_a_score": 13, "team_b_score": 9}
    - Winner: Team with higher score
    
    Best of X (Dota 2/MLBB):
    - Input: {"team_a_wins": 2, "team_b_wins": 1}
    - Winner: First to X wins
    
    Point-Based (PUBG Mobile/Free Fire):
    - Input: [
        {"team": "Team A", "kills": 12, "placement": 1},
        {"team": "Team B", "kills": 8, "placement": 2},
      ]
    - Winner: Highest points (kills + placement formula)
    """
```

**5. Game-Specific Settings:**
```python
def get_tournament_settings(self) -> List[TournamentSetting]:
    """
    Example for Valorant:
    [
        TournamentSetting(
            key="map_pool",
            type="multi_select",
            options=["Bind", "Haven", "Ascent", "Icebox", "Breeze", "Fracture", "Pearl"],
            required=True,
        ),
        TournamentSetting(
            key="map_veto",
            type="boolean",
            label="Enable Map Veto System",
            default=True,
        ),
    ]
    
    Example for eFootball:
    [
        TournamentSetting(
            key="match_duration",
            type="select",
            options=["6 minutes", "10 minutes", "Full Match"],
            default="10 minutes",
        ),
    ]
    """
```

**Your Design Challenge:**
- How do you structure `GameModule` classes?
- How does the tournament engine discover and load modules?
- How do you handle versioning (game updates)?
- How do you validate game-specific data?

**Games to Support at Launch:**
1. **Valorant** (5v5, Map Score)
2. **eFootball** (1v1, Match Score)
3. **PUBG Mobile** (Squad, Point-Based)
4. **Free Fire** (Squad, Point-Based)
5. **Mobile Legends** (5v5, Best of X)

---

### 4.2 Tournament Lifecycle: Phase 1 - Organization (Before)

#### User Roles & Permissions

**Role Hierarchy:**
1. **Super Admin** (you) - Can do everything
2. **Tournament Organizer (TO)** - Can create and manage tournaments
3. **Team Captain** - Can register team, submit scores
4. **Team Member** - Can view tournament info
5. **Spectator** - Can view public tournaments

**Questions for Your Design:**
- How do you approve/create Tournament Organizers?
- What permissions does each role have?
- Can TOs create tournaments for any game, or are they game-specific?

#### Tournament Creation

**Required Fields:**
- **Basic Info:**
  - Tournament Name
  - Game (from GameModule list)
  - Description/Rules
  - Banner Image
  - Start Date/Time
  - End Date/Time (or calculated from bracket size)
  - Region (Bangladesh, South Asia, Global)
  - Language (Bengali, English)

- **Format:**
  - Tournament Type (Single Elimination, Double Elimination, Round Robin, Swiss, etc.)
  - Team Size (from GameModule)
  - Max Teams (8, 16, 32, 64, 128)
  - Registration Deadline

- **Entry & Prizes:**
  - Entry Fee (DeltaCoin or Free)
  - Prize Pool (DeltaCoin)
  - Prize Distribution (1st: 50%, 2nd: 30%, 3rd: 20%, or custom)

- **Game-Specific Settings:**
  - Loaded from GameModule (e.g., Map Pool for Valorant)

**Questions for Your Design:**
- How do you validate tournament settings (e.g., prize pool ≤ entry fees × max teams)?
- How do you handle time zones?
- Can tournaments be "draft" mode before publishing?

#### Registration System

**Registration Types:**
- **Team Registration** - Existing team from `apps/teams` registers
- **Solo Registration** - Platform creates temporary team for solo players

**Registration Flow:**
1. Captain clicks "Register Team"
2. System validates:
   - ✅ Team exists in `apps/teams`
   - ✅ Team has enough players (min_roster_size)
   - ✅ All players have required Game IDs
   - ✅ Entry fee paid (if applicable)
   - ✅ Registration deadline not passed
3. System creates `TournamentRegistration` record
4. Status: `PENDING` → Organizer approves → `APPROVED`

**Questions for Your Design:**
- How do you handle roster locks (can't change players after registration)?
- What if a player is on multiple teams registering for same tournament?
- How do you refund entry fees if tournament is cancelled?

---

### 4.3 Tournament Lifecycle: Phase 2 - Management (During)

#### Bracket Generation

**Required Features:**
- **Automatic Generation:**
  - Single Elimination (8, 16, 32, 64 teams)
  - Double Elimination (Winners + Losers brackets)
  - Round Robin (all teams play all teams)
  - Swiss System (Buchholz/Tie-Break scoring)

- **Seeding:**
  - Random seeding
  - Ranked seeding (based on `apps/teams` ranking points)
  - Manual seeding (TO sets positions)

- **Bye Handling:**
  - What happens if teams < bracket size? (e.g., 13 teams in 16-team bracket)

**Questions for Your Design:**
- How do you represent brackets in database? (Tree structure? Node table?)
- How do you handle bracket visualization? (SVG? Canvas? HTML?)
- Can brackets be regenerated if teams drop out before tournament starts?

#### Player Check-In

**Check-In Flow:**
1. 30 minutes before tournament starts, check-in opens
2. All players in a team must click "Check In"
3. If team doesn't check in by tournament start → Disqualified
4. System sends notifications (Email + In-App)

**Questions for Your Design:**
- How do you track check-in status per player vs. per team?
- What if only 4/5 players check in? (Grace period? Auto-DQ?)
- Can TOs manually mark teams as checked-in?

#### Match Management

**Match States:**
```
SCHEDULED → READY (both teams checked in) → LIVE → PENDING_RESULT → 
COMPLETED (or DISPUTED)
```

**Match Workflow:**
1. **Match Start:**
   - System sends notification to both teams
   - Shows match lobby info (e.g., "Join custom game: Code XYZ")
   - Timer starts

2. **Score Submission:**
   - After match ends, **winning captain** submits result
   - System validates result against GameModule logic
   - Losing team has 10 minutes to **dispute** or **auto-confirm**

3. **Dispute Handling:**
   - If losing team clicks "Dispute", match status → `DISPUTED`
   - TO receives notification
   - TO reviews evidence (screenshots, VODs)
   - TO manually sets winner → Match status → `COMPLETED`

**Questions for Your Design:**
- How do you store match evidence (screenshots, VOD links)?
- What if both teams submit different scores?
- How do you handle no-shows (team doesn't join match)?
- Can spectators view live match status?

#### Live Bracket Updates

**Real-Time Requirements:**
- When match completes, bracket updates automatically
- Next match unlocks if dependencies met
- All viewers see update instantly (WebSocket)

**Questions for Your Design:**
- How do you calculate next match dependencies?
- How do you handle double-elimination losers bracket?
- What's the real-time architecture? (Django Channels? Pusher? Redis PubSub?)

---

### 4.4 Tournament Lifecycle: Phase 3 - Conclusion (After)

#### Final Results Page

**Must Display:**
- Final Standings (1st, 2nd, 3rd, Top 4, Top 8)
- Complete Bracket (all matches)
- Stats Summary:
  - Total teams participated
  - Total matches played
  - Tournament duration
  - MVP (if applicable)

**Questions for Your Design:**
- How do you determine 3rd place in single elimination? (3rd place match? Both semi-final losers?)
- Can results page be customized per game? (e.g., PUBG shows kill leaderboard)

#### Prize Distribution (Economy Integration)

**Automatic Prize Flow:**
1. Tournament status → `COMPLETED`
2. System triggers Celery task: `distribute_tournament_prizes(tournament_id)`
3. For each winning team (1st, 2nd, 3rd):
   ```python
   economy.services.award(
       profile=team.captain.profile,
       amount=prize_amount,
       reason='TOURNAMENT_PLACEMENT',
       note=f"1st Place - {tournament.name}",
       idempotency_key=f"tournament_{tournament.id}_prize_1st",
       tournament_id=tournament.id
   )
   ```
4. All participants get participation coins:
   ```python
   economy.services.award(
       profile=participant.profile,
       amount=participation_coins,
       reason='TOURNAMENT_PARTICIPATION',
       idempotency_key=f"tournament_{tournament.id}_participation_{team.id}",
       tournament_id=tournament.id
   )
   ```

**Questions for Your Design:**
- How do you split prizes in team tournaments? (Captain only? Split among all players?)
- What if prize distribution fails? (Retry logic? Manual intervention?)
- How do you prevent double-payouts? (Idempotency is critical)

#### Ranking Updates (Teams Integration)

**Automatic Ranking Flow:**
1. Tournament status → `COMPLETED`
2. System triggers Celery task: `update_tournament_rankings(tournament_id)`
3. For each team:
   ```python
   # Create ranking breakdown entry
   TeamRankingBreakdown.objects.create(
       team=team,
       source='tournament_win',  # or 'tournament_participation'
       points=points_earned,
       tournament_id=tournament.id,
       reason=f"1st Place - {tournament.name}"
   )
   
   # Trigger recalculation
   ranking_service.recalculate_team_points(team, reason="Tournament completion")
   ```

**Questions for Your Design:**
- How many points for each placement? (1st: 100, 2nd: 50, 3rd: 25, Participation: 10?)
- Do points scale with tournament size? (16-team tournament worth more than 8-team?)
- How do you handle solo tournaments? (Update individual player ranking?)

---

## 5. Advanced Features (Design Considerations)

### 5.1 Dispute Resolution System

**Critical Requirement:** The old system never completed this feature. It's a top priority.

**Dispute Flow:**
1. Losing team clicks "Dispute Result"
2. System prompts: "Upload evidence (screenshots, VOD link, description)"
3. Dispute status → `PENDING_REVIEW`
4. TO receives notification (Email + Dashboard)
5. TO reviews:
   - Submitted scores from both teams
   - Evidence from both teams
   - Match chat logs (if available)
6. TO makes decision:
   - **Approve Original Result** → Match status → `COMPLETED`
   - **Overturn Result** → Winner changes → Match status → `COMPLETED`
   - **Declare Draw** → Both teams advance (if possible) or replay match
   - **Disqualify Team** → Team removed from tournament

**Questions for Your Design:**
- How do you store dispute evidence?
- Can TOs request more evidence from teams?
- What's the dispute deadline? (10 minutes? 1 hour?)
- Can disputes be appealed?

---

### 5.2 Tournament Templates & Recurring Events

**Feature:** TOs can save tournament configs as templates for reuse.

**Use Case:**
- "Weekly Valorant 5v5" runs every Saturday
- TO clicks "Create from template" → All settings pre-filled
- Only needs to change dates

**Questions for Your Design:**
- How do you version templates? (GameModule updates might break old templates)
- Can templates be shared publicly?

---

### 5.3 Team vs. Solo Tournaments

**Requirement:** Support both team-based and solo tournaments.

**Solo Tournament Logic:**
- Player registers individually (not with a team)
- System creates temporary "team" with 1 member
- Bracket treats them as 1-person teams
- Prizes go directly to player (not split)

**Questions for Your Design:**
- How do you handle solo tournaments for team games? (e.g., 1v1 Valorant)
- Do solo players get ranking points? (Individual ranking system needed?)

---

### 5.4 Spectator Features

**Public Tournaments:**
- Anyone can view bracket
- Anyone can view live match status
- Anyone can view final results

**Private Tournaments:**
- Only participants can view
- TO can invite specific spectators

**Questions for Your Design:**
- How do you handle spectator load? (Caching? CDN?)
- Can spectators comment on matches?

---

### 5.5 Multi-Stage Tournaments

**Advanced Feature:** Support tournaments with multiple stages.

**Example:**
1. **Stage 1:** Round Robin (all teams play each other)
2. **Stage 2:** Top 8 advance to Single Elimination

**Questions for Your Design:**
- How do you model multi-stage brackets?
- How do you carry points/stats between stages?

---

## 6. Technical Deliverables Required

You are responsible for delivering a **complete blueprint** that I can use to implement the system. This includes:

### 6.1 Software Architecture Document

**Required Content:**
- **System Overview:** How does the tournament engine fit into DeltaCrown?
- **Architecture Decision:** 
  - Build as new Django app in monolith? (`apps/tournaments_v2/`)
  - Build as separate microservice with API?
  - Your recommendation with pros/cons
- **High-Level Diagram:** Show all components and their relationships
- **Integration Points:** Detailed diagrams showing how tournament engine communicates with Economy, Teams, Notifications
- **Data Flow Diagrams:** For each major workflow (registration, match management, prize distribution)

---

### 6.2 Complete Database Schema (ERD)

**Required Models (Minimum):**
- `Tournament` - Core tournament metadata
- `TournamentRule` - Custom rules per tournament
- `GameModule` - Pluggable game configurations
- `TournamentRegistration` - Team/player registrations
- `Bracket` - Bracket structure
- `Match` - Individual matches
- `MatchResult` - Match outcomes
- `Dispute` - Dispute records
- `DisputeEvidence` - Evidence files/links
- `TournamentPrize` - Prize distribution records
- `TournamentStats` - Aggregated statistics

**Your Deliverable:**
- Complete ERD with all relationships
- Field definitions (type, constraints, indexes)
- Sample data for each model

---

### 6.3 API Specification

**Required APIs:**

**1. Public APIs (for frontend):**
- `GET /api/tournaments/` - List tournaments
- `GET /api/tournaments/{id}/` - Tournament details
- `POST /api/tournaments/{id}/register/` - Register team
- `GET /api/tournaments/{id}/bracket/` - Get bracket
- `POST /api/matches/{id}/submit_result/` - Submit match result
- `POST /api/matches/{id}/dispute/` - Raise dispute
- ... (full spec required)

**2. Internal Service APIs (for integration):**
- How does tournament engine call `economy.services.award()`?
- How does tournament engine call `ranking_service.recalculate_team_points()`?
- How does tournament engine trigger notifications?

**Your Deliverable:**
- OpenAPI/Swagger specification
- Request/response examples
- Error handling documentation

---

### 6.4 UI/UX Design System (High Priority)

**Required Deliverables:**

**1. Design System (Figma/Sketch):**
- Color palette (dark mode primary)
- Typography system
- Component library:
  - Tournament cards
  - Bracket visualizations
  - Match cards
  - Score submission forms
  - Dispute resolution interface
  - Registration forms
- Animation guidelines
- Responsive breakpoints

**2. Complete Page Mockups (Desktop & Mobile):**
- **Public Pages:**
  - Tournament listing page
  - Tournament detail page
  - Bracket view page
  - Match detail page
  - Final results page

- **Team Captain Pages:**
  - Registration page
  - My Tournaments dashboard
  - Match lobby page
  - Score submission page
  - Dispute filing page

- **Tournament Organizer Pages:**
  - Tournament creation page
  - Tournament management dashboard
  - Registration approval page
  - Dispute resolution page
  - Analytics page

- **Admin Pages:**
  - Game module management
  - TO approval page
  - System monitoring

**3. User Flow Diagrams:**
- Registration flow (start to finish)
- Match management flow (scheduled → completed)
- Dispute resolution flow
- Prize distribution flow

---

### 6.5 Implementation Roadmap

**Required Content:**
- **Feature Backlog:** All features broken into user stories (Agile format)
- **Priority Levels:** P0 (must-have), P1 (should-have), P2 (nice-to-have)
- **Development Phases:**
  - Phase 1: Core tournament CRUD + basic brackets
  - Phase 2: Match management + check-in
  - Phase 3: Score submission + disputes
  - Phase 4: Prize distribution + ranking integration
  - Phase 5: Advanced features (templates, multi-stage, etc.)
- **Estimated Timeline:** Rough estimates for each phase
- **Testing Strategy:** Unit tests, integration tests, E2E tests

---

### 6.6 Market Research Report

**Required Content:**
- **Competitor Analysis:**
  - Battlefy (features, UX, strengths, weaknesses)
  - Challengermode (features, UX, strengths, weaknesses)
  - Toornament (features, UX, strengths, weaknesses)
  - FACEIT (features, UX, strengths, weaknesses)
  - ESL Play (features, UX, strengths, weaknesses)

- **Feature Comparison Matrix:**
  - Which features do all platforms have? (table stakes)
  - Which features differentiate top platforms? (competitive advantages)
  - Which features should DeltaCrown implement? (recommendations)

- **Game-Specific Research:**
  - How does Valorant competitive work? (Ranked system, map veto, etc.)
  - How does eFootball competitive work?
  - How do PUBG Mobile tournaments work? (Point system, multiple matches)
  - How do Free Fire tournaments work?
  - How do MLBB tournaments work?

- **UX Best Practices:**
  - What makes a good bracket visualization?
  - How do top platforms handle disputes?
  - What real-time features do users expect?
  - Mobile vs. desktop experience (usage patterns)

**Your Deliverable:**
- 20-30 page research report with screenshots, analysis, and recommendations

---

## 7. Project Constraints & Guidelines

### 7.1 Technical Constraints

**Must-Have Technologies:**
- Django 4.2+ (Python)
- PostgreSQL (database)
- Redis (cache + Celery broker)
- Celery (background tasks)
- Django Channels (real-time features)

**Frontend:**
- Django Templates (primary)
- Can use Alpine.js or HTMX for interactivity
- Can use React/Vue for complex components (bracket visualization)
- Must be responsive (mobile-first)

**No Microservices (for now):**
- Build as Django app within monolith
- Can be extracted to microservice later if needed

---

### 7.2 Code Quality Standards

**Required:**
- ✅ **Type Hints** - All functions must have type annotations
- ✅ **Docstrings** - All functions, classes, modules documented
- ✅ **Tests** - 80%+ code coverage
- ✅ **Linting** - Pass flake8, black, isort
- ✅ **Security** - No SQL injection, XSS, CSRF vulnerabilities
- ✅ **Performance** - No N+1 queries, proper indexing

---

### 7.3 Timeline Expectations

**Discovery & Design Phase (This Deliverable):**
- **Duration:** 3-4 weeks
- **Deliverables:** All items in Section 6

**Implementation Phase (After Blueprint Delivered):**
- **Phase 1 (MVP):** 6-8 weeks
  - Basic tournament CRUD
  - Single/Double elimination brackets
  - Match management
  - Score submission
  - Prize distribution

- **Phase 2 (Full Features):** 4-6 weeks
  - Dispute resolution
  - Advanced brackets (Round Robin, Swiss)
  - Tournament templates
  - Analytics

- **Phase 3 (Polish):** 2-4 weeks
  - Performance optimization
  - Mobile experience
  - Edge case handling
  - Testing & QA

**Total Estimated Timeline:** 14-18 weeks (including design phase)

---

## 8. Budget & Engagement Terms

### 8.1 Engagement Model

**Option 1: Fixed-Price Blueprint**
- You deliver complete blueprint (all Section 6 deliverables)
- Fixed price for discovery + design phase
- I implement the system based on your blueprint

**Option 2: Full Development Partnership**
- You deliver blueprint + implement the system
- Fixed price or time & materials
- You provide ongoing support and maintenance

**I prefer:** [Please provide pricing for both options]

---

### 8.2 Payment Terms

**Discovery & Design Phase:**
- 30% upfront (upon contract signing)
- 40% upon first deliverable review (architecture + ERD + API spec)
- 30% upon final deliverable approval (complete blueprint)

**Implementation Phase (if applicable):**
- To be negotiated upon blueprint approval

---

## 9. Questions for Your Proposal

Please address these in your proposal:

### 9.1 Experience
- Have you built tournament systems before? (links/case studies)
- Experience with esports/gaming platforms?
- Experience with Django + PostgreSQL + Celery?
- Experience with real-time features (WebSockets)?
- Team size and roles (designers, backend devs, frontend devs)

### 9.2 Process
- Your discovery & research process
- Design iterations (how many rounds of feedback?)
- Tools you use (Figma, Miro, etc.)
- Communication cadence (weekly calls? Slack?)

### 9.3 Deliverables
- Confirm you can deliver all items in Section 6
- Timeline for each deliverable
- What format will deliverables be in? (PDF, Figma, Markdown, etc.)

### 9.4 Pricing
- Fixed price for discovery + design phase
- (Optional) Fixed price or hourly rate for implementation phase
- Any additional costs? (tools, licenses, etc.)

### 9.5 Post-Engagement Support
- Will you be available for Q&A during implementation?
- Hourly rate for ad-hoc support?
- Ongoing maintenance options?

---

## 10. Next Steps

**If you're interested in this project:**

1. **Review this brief thoroughly**
2. **Research the referenced platforms** (Battlefy, etc.)
3. **Prepare your proposal** addressing Section 9 questions
4. **Send proposal to:** [Your Email]
5. **Include:**
   - Company overview + portfolio
   - Team bios
   - Proposed timeline
   - Fixed-price quote (discovery + design)
   - (Optional) Implementation quote
   - Contract terms

**Timeline:**
- Proposals due: [Date - 2 weeks from now]
- Proposal review: [Date - 1 week]
- Kickoff call: [Date - as soon as contract signed]
- First deliverable: [Date - 2 weeks after kickoff]

---

## 11. Contact Information

**Project Owner:** [Your Name]  
**Email:** [Your Email]  
**Discord/Telegram:** [Your Handle]  
**GitHub:** [rkRashik/DeltaCrown](https://github.com/rkRashik/DeltaCrown)  
**Platform:** [DeltaCrown.gg](https://deltacrown.gg) (if live)

---

## Appendix A: Existing Codebase References

For your research, these are the key files in the current DeltaCrown codebase:

**Configuration:**
- `deltacrown/settings.py` - App configuration, INSTALLED_APPS
- `deltacrown/urls.py` - URL routing
- `deltacrown/celery.py` - Celery configuration

**Active Apps:**
- `apps/teams/models/_legacy.py` - Team model (794 lines)
- `apps/economy/models.py` - Wallet, Transaction models
- `apps/economy/services.py` - Economy service layer
- `apps/notifications/models.py` - Notification models
- `apps/user_profile/models.py` - UserProfile with game IDs

**Legacy (For Reference Only):**
- `legacy_backup/apps/tournaments/` - Old tournament system
- `legacy_backup/apps/game_valorant/` - Old Valorant logic
- `legacy_backup/apps/game_efootball/` - Old eFootball logic

**Documentation:**
- `Documents/For_New_Tournament_Design/` - Complete system documentation (v2.0)
  - 01-project-overview-and-scope.md
  - 02-architecture-and-tech-stack.md
  - 03-domain-model-erd-and-storage.md
  - 04-modules-services-and-apis.md
  - 05-user-flows-ui-and-frontend.md
  - 06-teams-economy-ecommerce-integration.md
  - 07-permissions-notifications-and-realtime.md
  - 08-operations-environments-and-observability.md
  - EVIDENCE_MATRIX.md (maps all claims to code)

---

## Appendix B: Glossary

**DeltaCoin** - Platform currency (NOT "DeltaCrown Coins")  
**TO** - Tournament Organizer  
**GameModule** - Pluggable game configuration interface  
**ForeignKey → IntegerField** - Legacy decoupling pattern (remove FK, keep ID reference)  
**Idempotency Key** - Unique key preventing duplicate transactions  
**Roster Lock** - Freezing team roster after registration deadline  
**Map Veto** - Teams banning maps before match starts  

---

**End of Project Brief**

**Version:** 1.0  
**Date:** November 2, 2025  
**Status:** Ready for Developer Proposals

---

**Good luck with your proposal! I'm excited to see your vision for the new DeltaCrown Tournament Engine.** 🎮🏆
