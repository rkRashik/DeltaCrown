# DeltaCrown Esports Platform — The Complete Guide

> **Document Version:** 4.0  
> **Last Updated:** February 27, 2026  
> **Classification:** Public Documentation  
> **Author:** DeltaCrown Platform Team  

---

> *"From the Delta to the Crown — Where Champions Rise."*

---

## About This Guide

This is the definitive guide to DeltaCrown — South Asia's premier esports tournament platform. It is written for everyone who will ever interact with DeltaCrown: the curious newcomer, the serious competitor, the team captain, the tournament organizer, and the administrator who keeps it all running.

This guide is organized into three volumes, each telling the DeltaCrown story from a different perspective:

**Volume I — The Master Platform Guide**  
The complete picture. What DeltaCrown is, why it exists, how every piece fits together, and the philosophy behind every decision. If you want to understand the soul of the platform, start here.

**Volume II — The Player & Community Guide**  
The journey of a player. From creating an account to winning a tournament — told as a story of progression, from a teenager's first click to a champion's final match. This is the guide for users, players, team members, and community participants.

**Volume III — The Operations Guide: For Admins, Staff & Organizers**  
The machinery behind the stage. How tournaments are created, how staff manages operations, how disputes are resolved, and how the platform is governed. This is the guide for tournament organizers, referees, moderators, and platform administrators.

---

# Volume I — The Master Platform Guide

## The Story of DeltaCrown

---

### Chapter 1: The Problem — A Broken Ecosystem

Imagine a young gamer in Dhaka. She is sixteen years old, and she is exceptional at Valorant. She can outshoot players twice her age, and her game sense is beyond reproach. But here is her reality:

She practices on one platform. She finds tournaments on another — usually through a Facebook group where the organizer is someone's friend-of-a-friend, the rules are unclear, and the prize money may or may not materialize. She communicates with her teammates on Discord, but their team exists nowhere officially. There is no record of her victories. No ranking that follows her from tournament to tournament. No way to prove, to anyone, that she is as good as she knows she is.

Her stats live in screenshots. Her trophy shelf is a folder on her phone. Her team is a WhatsApp group that dissolves and reforms every few months. When she wins, nobody outside her immediate circle notices. When she loses, there's no review, no growth feedback, no path to improvement.

This is the reality for millions of competitive gamers across South Asia. Not because they lack talent — but because they lack infrastructure.

Professional esports in Europe and North America has FACEIT, ESEA, Start.gg, ESL, and a dozen other platforms backed by millions in venture capital. These platforms don't just host tournaments — they build careers. They create verified, persistent identities. They track performance across seasons. They connect players to teams, teams to sponsors, and sponsors to audiences.

South Asia has none of this. And the gap is not shrinking — it is growing.

This is the problem DeltaCrown was built to solve.

### Chapter 2: The Vision — Infrastructure for Everyone

DeltaCrown is not a tournament website. It is an **esports infrastructure platform** — the digital foundation upon which careers, communities, and competitions are built.

The vision is deceptively simple: **Build a world where geography does not define destiny.** Where a gamer on a mobile phone in Bangladesh has the same trusted path to recognition as a professional on the main stage in Los Angeles.

DeltaCrown achieves this through nine interconnected systems:

1. **The Tournament Engine** — Where competitions come to life
2. **The Team & Organization System** — Where competitive units form and endure
3. **The Player Identity System** — Where careers are built and verified
4. **The Rankings & Leaderboards** — Where performance is measured and remembered
5. **The DeltaCoin Economy** — Where effort is rewarded and circulated
6. **The Payment System** — Where money flows securely and transparently
7. **The Community Platform** — Where connections are made and culture grows
8. **The Challenge Hub** — Where players test themselves beyond tournaments
9. **The Crown Store & Marketplace** — Where achievement meets expression

Each of these systems is powerful on its own. Together, they form something greater: a coherent ecosystem where every action contributes to a player's permanent, portable, verifiable competitive identity.

### Chapter 3: The Eleven Games

DeltaCrown launches with support for eleven competitive titles, spanning five categories:

| Category | Games |
|----------|-------|
| **First-Person Shooters (FPS)** | Valorant, Counter-Strike 2, Call of Duty Mobile, Rainbow Six Siege |
| **Battle Royale** | PUBG Mobile, Free Fire |
| **MOBA** | Mobile Legends: Bang Bang, Dota 2 |
| **Sports Simulation** | EA SPORTS FC 26, eFootball 2026 |
| **Vehicle/Action** | Rocket League |

What makes DeltaCrown's game support remarkable is not the number of titles — it is the architecture. Games are not hardcoded into the platform. They are **configuration-driven data records** in the database. Each game carries its own:

- **Roster configuration:** How many starters, substitutes, and coaches a team needs
- **Player roles:** Duelist, Controller, Sentinel, Initiator for Valorant; Marksman, Tank, Support for MLBB
- **Identity fields:** Riot ID for Valorant, Steam ID for CS2, PUBG Mobile ID with character ID
- **Scoring rules:** Kill-based for Battle Royale, round-based for FPS, goal-based for sports
- **Ranking weights:** How tournament placements translate to leaderboard points
- **Tournament defaults:** Standard team sizes, match formats, and rule templates

Adding a new game to DeltaCrown requires no code changes — only a database entry and a seed command. The platform is, by design, **game-agnostic infrastructure**.

### Chapter 4: The Architecture — How It All Fits Together

DeltaCrown is a Django monolith — deliberately so. While the industry trend toward microservices has its merits, DeltaCrown prioritizes **transactional integrity and developer productivity** over distributed complexity. A tournament registration that debits a wallet, creates a roster lock, sends a notification, and updates a leaderboard happens in a single, atomic database transaction. No eventual consistency. No distributed saga. No partial failures.

**The technology stack:**

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | Django 5.x (Python) | Application logic, ORM, admin |
| **Database** | PostgreSQL (Neon Cloud) | All persistent data, JSONB for flexible config |
| **Task Queue** | Celery + Redis | Async tasks: notifications, Discord sync, leaderboard computation |
| **Cache** | Redis | Session cache, rate limiting, real-time data |
| **Real-Time** | Django Channels (WebSocket) + SSE | Live match updates, chat, notifications |
| **Frontend** | Django Templates + Tailwind CSS + Vanilla JS | Server-rendered, progressive enhancement |
| **API** | Django REST Framework + SimpleJWT | Mobile/bot/third-party integrations |
| **API Docs** | drf-spectacular (OpenAPI 3.0) | Swagger UI + ReDoc |
| **Admin** | Django Admin + Unfold Theme | Staff operations, content management |
| **Monitoring** | Prometheus + Grafana + Sentry | Metrics, dashboards, error tracking |
| **Deployment** | Docker + Render + Gunicorn | Containerized, scalable |

**The application structure** is organized into focused Django apps, each owning a bounded domain:

| App | Domain | Key Models |
|-----|--------|-----------|
| `accounts` | Authentication | User, PendingSignup, EmailOTP |
| `user_profile` | Player Identity | UserProfile, GameProfile, Badge, Follow, KYCSubmission, PrivacySettings |
| `organizations` | Teams & Orgs | Organization, Team, TeamMembership, TeamInvite, DiscordChatMessage |
| `tournaments` | Competition | Tournament, Registration, Bracket, Match, Dispute, Certificate, PrizeClaim |
| `games` | Game Registry | Game, GameRosterConfig, GameRole, GameMatchResultSchema |
| `economy` | DeltaCoin | DeltaCrownWallet, DeltaCrownTransaction |
| `ecommerce` | Crown Store | Product, Category, Cart, Brand |
| `shop` | DeltaCoin Shop | ShopItem, ReservationHold |
| `leaderboards` | Rankings | LeaderboardEntry, LeaderboardSnapshot, UserStats |
| `notifications` | Alerts | Notification, NotificationPreference, NotificationDigest |
| `challenges` | Challenges | Challenge (wagers, bounties, scrims, duels) |
| `competition` | Match Ranking | GameRankingConfig, MatchReport, RankingSnapshot |
| `moderation` | Trust & Safety | ModerationSanction, ModerationAudit, AbuseReport |
| `spectator` | Public Viewing | Read-only tournament/match views |
| `support` | Help | FAQ, ContactMessage, Testimonial |
| `dashboard` | Hub | User dashboard, team management views |

**Design principles that govern every line of code:**

1. **Configuration over Code:** Games, scoring rules, roster sizes, ranking weights — all stored as database records, not Python constants.
2. **Event-Driven Workflows:** When something happens (tournament published, match completed, player joins team), Celery tasks fan out to handle consequences: notifications, Discord sync, leaderboard updates, badge grants.
3. **Audit Everything:** Every state change on every critical model is logged. Match results have hash-based integrity checks. Transactions are append-only. Admin actions are recorded.
4. **Soft Deletes:** Nothing is ever truly deleted. Teams, tournaments, profiles — all use soft delete patterns with `deleted_at` timestamps. Data is preserved for compliance and historical analysis.
5. **Progressive Enhancement:** The frontend works without JavaScript. Then JavaScript makes it better — AJAX for form submissions, WebSocket for real-time updates, lazy loading for performance.

### Chapter 5: The User Roles — Who Does What

DeltaCrown recognizes that an esports ecosystem involves many different roles, each with distinct needs and permissions. The platform implements a comprehensive role-based access control (RBAC) system at multiple levels.

**Platform-Level Roles:**

| Role | Description |
|------|-------------|
| **Player** | The foundation. Creates an account, builds a profile, joins teams, enters tournaments, earns DeltaCoin. Every user is a player. |
| **Team Owner** | Creates and owns a competitive team. Full control over team settings, roster, and operations. |
| **Team Member** | A member of a team (player, substitute, coach, analyst, etc.) with role-specific permissions. |
| **Tournament Organizer** | A verified user who can create and manage tournaments through the Tournament Operations Center (TOC). |
| **Referee** | Assigned to specific tournaments or matches. Can verify results, resolve disputes, and enforce rules. |
| **Moderator** | Community moderator. Can review reports, issue sanctions, and manage content. |
| **Admin** | Platform administrator. Full access to the admin panel, system configuration, and operational tools. |
| **Super Admin** | God mode. Everything an admin can do, plus staff management and irreversible actions. |

**Team-Level Roles (13 distinct roles):**

DeltaCrown models real-world esports team structures with unprecedented granularity:

| Role | Responsibility |
|------|---------------|
| **Owner** | Team creator. Ultimate authority. Can transfer ownership. |
| **General Manager** | Day-to-day operations lead. Nearly full permissions. |
| **Team Manager** | Operational support. Manages roster changes, schedules. |
| **Head Coach** | Strategic lead. Reviews performance, designs plays. |
| **Assistant Coach** | Supports head coach. Focuses on specific aspects (aim, positioning). |
| **Performance Coach** | Mental and physical performance optimization. |
| **Analyst** | Data-driven performance analysis. Reviews match footage and statistics. |
| **Strategist** | Counter-strat development, opponent research, meta analysis. |
| **Player** | Active competitor. The core roster member. |
| **Substitute** | Ready to play when a starter cannot. Attends practice, knows the playbook. |
| **Content Creator** | Creates team content: streams, videos, social media posts. |
| **Social Media Manager** | Manages team's social media presence and engagement. |
| **Community Manager** | Manages team's fan community, events, and communications. |

Each role carries **granular, configurable permissions** across six domains: tournament operations, roster management, profile editing, content creation, financial access, and practice scheduling.

### Chapter 6: The DeltaCoin Economy — Value Without Currency

DeltaCoin is DeltaCrown's internal utility currency. It is not a cryptocurrency. It cannot be converted to real money. It exists for one purpose: to create a **circular economy of engagement** within the platform.

**How DeltaCoin is earned:**

| Activity | Reward |
|----------|--------|
| Tournament prizes (predefined per tournament) | 50–5,000 DC |
| Daily platform login | 5 DC |
| 7-day login streak | 25 DC bonus |
| Completing profile (100%) | 50 DC |
| First tournament entry | 25 DC |
| Match win | 5–10 DC |
| Achievement unlocked | 10–100 DC |
| Referral (invited user links account) | 20 DC |
| Community contribution (approved content) | 10 DC |
| Discord activity (daily engagement) | 5 DC |
| Discord server boost | 50 DC/month |

**How DeltaCoin is spent:**

| Item | Cost |
|------|------|
| Tournament entry fees (where DeltaCoin is accepted) | Varies |
| Profile customization (banners, themes, effects) | 50–500 DC |
| Post boosting (increase visibility in community feed) | 10–50 DC |
| Crown Store items (digital collectibles, badges) | 25–1,000 DC |
| Team branding upgrades | 100–500 DC |
| Coaching session booking | 50–200 DC |

**Economic design principles:**
- **Controlled issuance:** DeltaCoin enters the system only through defined channels. No arbitrary minting.
- **Clear sinks:** Spending opportunities ensure DeltaCoin circulates rather than accumulating infinitely.
- **Immutable ledger:** Every DeltaCoin transaction is recorded in an append-only log. Balance is computed from transaction history.
- **Anti-abuse:** Rate limits, caps, and anomaly detection prevent farming, bot abuse, and exploitation.
- **Transparency:** Users can view their complete transaction history at any time.

The `DeltaCrownWallet` model stores each user's cached balance alongside their Bangladesh mobile payment details (bKash, Nagad, Rocket) and bank information. The `DeltaCrownTransaction` model is the immutable ledger — with database-level CHECK constraints, idempotency keys for deduplication, and support for multiple transaction types: participation, prizes, entry fees, refunds, and peer-to-peer transfers.

### Chapter 7: Payments — Real Money, Real Trust

DeltaCrown is built for the Bangladeshi market first, and payments reflect that reality. While international payment gateways like Stripe and PayPal are planned for the future, the platform launches with the payment methods that matter most to its users:

| Method | Type | Coverage |
|--------|------|----------|
| **bKash** | Mobile financial service | ~65 million users in Bangladesh |
| **Nagad** | Mobile financial service | ~50 million users in Bangladesh |
| **Rocket** | Mobile financial service | ~35 million users in Bangladesh |
| **Bank Transfer** | Traditional banking | All banks in Bangladesh |

**How payments work on DeltaCrown:**

1. **Tournament Registration:** A player or team registers for a tournament that requires an entry fee. The fee is displayed in BDT (Bangladeshi Taka).
2. **Payment Method Selection:** The player selects bKash, Nagad, Rocket, or bank transfer.
3. **Manual Payment:** The player sends the payment to DeltaCrown's designated number/account (displayed clearly with copy-to-clipboard).
4. **Screenshot Upload:** The player uploads a screenshot of the payment confirmation as proof.
5. **Verification:** A DeltaCrown staff member reviews the screenshot, verifies the amount and transaction ID, and approves or rejects the payment.
6. **Confirmation:** Upon approval, the registration is confirmed, and the player receives a notification (in-app, email, and Discord if linked).

This manual verification workflow is a deliberate choice. In a market where automated payment gateway integration is complex and often unreliable, manual verification provides **trust and transparency**. Every payment has a human verifier. Every verification has an audit trail. Every rejection comes with a reason.

**Prize Distribution:**

When a tournament completes and prizes are determined:
1. Winner rankings are calculated and verified
2. Prize amounts are assigned per the tournament's prize structure
3. DeltaCoin prizes are credited instantly to winners' wallets
4. BDT prizes are queued for distribution via the same channels (bKash/Nagad/Rocket/bank)
5. Winners may need KYC verification for large prize claims
6. Distribution is tracked via `PrizeTransaction` records with full audit trail

### Chapter 8: The Notification Fabric

DeltaCrown communicates with its users through three channels, each serving a different purpose:

| Channel | Best For | Latency | User Control |
|---------|---------|---------|-------------|
| **In-App** | Everything. The primary channel. | Real-time (SSE/WebSocket) | Per-type toggle |
| **Email** | Formal notifications, receipts, security alerts | Minutes | Per-type toggle, digest option |
| **Discord** | Real-time competitive ops, community events | Seconds | Per-type toggle, DM or channel |

The `Notification` model supports 20+ event types:

- Registration confirmed / Registration cancelled
- Bracket ready / Match scheduled / Match reminder
- Check-in reminder / Check-in confirmed
- Match result confirmed / Match disputed
- Dispute resolved / Dispute escalated
- Prize distributed / DeltaCoin credited
- Team invite received / Team invite accepted/declined
- Join request received / Join request approved/rejected
- New follower / Follow request
- Achievement unlocked / Badge earned
- Leaderboard rank change
- Platform announcement / Security alert

Each user controls their notification preferences through the `NotificationPreference` model — choosing which events trigger which channels, with options for global opt-out per channel and daily digest batching.

### Chapter 9: The Moderation Philosophy — Fair Play Is Not Optional

DeltaCrown takes a principled stance on moderation: **the platform is a space for competition, not conflict.** Fair play is enforced at every layer.

**Three pillars of moderation:**

**1. Prevention — Make Bad Behavior Difficult**
- Account verification via email OTP prevents throwaway accounts
- KYC verification for prize claims ensures real identities
- Roster locks prevent mid-tournament manipulation
- Rate limiting prevents spam and abuse
- Progressive disclosure means new accounts have limited access

**2. Detection — See Everything That Matters**
- Automated content filtering (profanity, spam, link abuse)
- Community reporting (AbuseReport model with state machine: open → triaged → resolved/rejected)
- Cross-platform monitoring (Discord ↔ Platform)
- Anomaly detection on DeltaCoin transactions
- Result integrity checks (hash-based, timestamp verification)

**3. Enforcement — Swift, Fair, Proportionate**
- The `ModerationSanction` model supports: global ban, tournament-specific suspension, temporary mute, feature restriction
- Time-bounded sanctions with automatic expiry
- Scope control: a tournament sanction doesn't prevent social features
- Full audit trail via `ModerationAudit` (append-only, compliance-grade)
- Admin override and revocation capability
- **Reputation Score** impact: sanctions reduce a player's reputation score, affecting matchmaking priority and tournament eligibility

### Chapter 10: The Spectator Experience

Not everyone on DeltaCrown competes. Many come to watch — and watching should be as compelling as playing.

The `spectator` app provides public, read-only views of:
- **Tournament listings** — Browse upcoming, live, and completed tournaments
- **Live brackets** — Watch brackets update in real-time as matches are completed
- **Match details** — View scores, statistics, and timelines for individual matches
- **Leaderboards** — Track the best players and teams across all games
- **Team profiles** — View team rosters, history, and achievements
- **Player profiles** — View competitive stats, match history, and career progression

Spectator views require no account and no login. They are SEO-optimized, fast-loading, and mobile-friendly. This is deliberate: the spectator experience is the **front door** to the platform. A fan who watches a tournament bracket should be one click away from creating an account and entering the next one.

### Chapter 11: The Support System

When things go wrong — or when users simply have questions — DeltaCrown provides structured support:

**FAQ System:**
- Categorized knowledge base: General, Tournaments, Payments, Technical, Teams, Rules
- Searchable, regularly updated
- Synced to Discord's `#faq` channel

**Contact Form:**
- Structured submission with category, priority, and message
- Status tracking: open → in-progress → resolved
- Staff assignment and response tracking

**Testimonials:**
- Users can submit testimonials with star ratings
- Featured testimonials appear on the homepage
- Prize-winning players can showcase their earnings

**Discord Support:**
- `#open-a-ticket` channel creates private threads for individual support
- `#payment-help` for payment verification assistance
- `#faq` mirrors the web FAQ

### Chapter 12: The Road Ahead

DeltaCrown is a platform built for evolution. The architecture is designed to grow:

**Near-Term (2026):**
- Mobile apps (React Native, sharing the API layer)
- Advanced matchmaking (skill-based, latency-aware)
- Streaming integration (embed Twitch/YouTube streams in tournament pages)
- Sponsorship analytics dashboard
- Multi-language support (English + Bangla)

**Mid-Term (2026–2027):**
- Coaching marketplace (find coaches, book sessions, track progress)
- Talent pipeline (connect top players with professional teams and scouts)
- Regional expansion (India, Pakistan, Nepal, Sri Lanka, Southeast Asia)
- White-label tournament platform (organizations run DeltaCrown-powered tournaments under their own brand)

**Long-Term (2027+):**
- Global esports infrastructure
- Cross-region tournaments and rankings
- Esports career certification and credentialing
- AI-powered performance analytics
- VR/AR spectator experiences
- Esports betting integration (where legally permitted)

---

*Volume I establishes the foundation. Now, let us walk through DeltaCrown from the perspectives of those who use it every day.*

---

# Volume II — The Player & Community Guide

## Your Journey on DeltaCrown

---

### Chapter 1: The First Click — Creating Your Account

Every legend begins with a single step. On DeltaCrown, that step is creating your account.

Picture this: you have heard about DeltaCrown from a friend, or perhaps you saw a tournament announcement on Discord, or maybe you stumbled upon a leaderboard while searching for your favorite game. Whatever brought you here, the door is open.

You navigate to **deltacrown.gg** and click "Sign Up." The registration form is deliberately simple — DeltaCrown asks only for what it needs to get you started:

- **Username** — Your permanent identity on the platform. Choose wisely; this is how the community will know you. It must be unique, between 3 and 20 characters, and can include letters, numbers, and underscores.
- **Email Address** — Your primary contact and account recovery method. Must be a valid, accessible email.
- **Password** — Your key to the kingdom. Must meet security requirements (minimum 8 characters, mix of types).

You click "Create Account" and within seconds, a **six-digit verification code** arrives in your email inbox. This is DeltaCrown's EmailOTP system — a time-limited, one-time password that proves you own the email address you provided. The code expires in 10 minutes, and you have a limited number of attempts before the system locks the request (to prevent brute-force attacks).

You enter the code. Your account is verified. You are in.

But you are not yet a *player*. You are a user with an empty profile, no team, no tournament history, and no reputation. The journey from here to the crown is long — and every step is tracked, rewarded, and celebrated.

### Chapter 2: Building Your Identity — The Profile

Your DeltaCrown profile is not a settings page. It is your **competitive passport** — a living document of who you are, what you play, and what you have achieved.

When you first log in after verification, DeltaCrown gently guides you toward completing your profile. Not because it is mandatory (you can compete with a bare profile), but because a complete profile unlocks opportunities: better team matches, higher visibility, and the full power of the platform.

**Your profile has several sections:**

**Personal Information:**
Your display name (separate from your username — your username is permanent, your display name can be changed). Your bio — a short paragraph that tells the world who you are. Your avatar and banner — the visual identity that represents you across the platform.

**Location:**
Your country (selected from an international database), region, and city. This matters for regional tournaments, local matchmaking, and community connections. A player in Dhaka can find tournaments near them. A player in Chittagong can connect with local teams.

**Contact & Social:**
Your phone number, WhatsApp (optional, for team communication), and social media links — Discord (critical for integration), YouTube, Twitch, Twitter/X, Facebook, Instagram, TikTok. These links appear on your public profile and help teams evaluate you during recruitment.

**Game Preferences:**
Which of the eleven supported games you play, and what device you play on (PC, Mobile, Console). Your play style (Aggressive, Balanced, Tactical, Support). Your preferred roles (these are game-specific: Duelist in Valorant, Marksman in MLBB, etc.).

**Looking For Team (LFT) Status:**
A toggle that tells the world: "I am actively looking for a team." When enabled, your profile appears in the LFT directory, and team captains searching for players of your skill level, role, and game will find you. You can specify your availability, preferred team size, and competitive ambitions.

**Your DeltaCrown ID:**
Upon profile creation, you receive a unique **DeltaCrown Public ID** in the format `DC-YY-NNNNNN` (e.g., `DC-26-001234`). This is your permanent identifier — it appears on certificates, leaderboards, team rosters, and official communications. It is the closest thing competitive esports has to a professional license number.

### Chapter 3: The Game Passport — Your Cross-Game Identity

The Game Passport is one of DeltaCrown's most distinctive features. For each game you play, you create a **game-specific identity** that links your DeltaCrown account to your in-game identity.

When you add a game passport, DeltaCrown asks for the identity information specific to that game:

| Game | Identity Fields |
|------|----------------|
| **Valorant** | Riot ID (Name#Tag) |
| **CS2** | Steam ID / Friend Code |
| **PUBG Mobile** | PUBG Mobile ID, Character ID, IGN |
| **Mobile Legends** | MLBB ID, Server ID |
| **Free Fire** | Free Fire ID, IGN |
| **Call of Duty Mobile** | CODM UID, IGN |
| **Dota 2** | Steam ID / Friend Code |
| **Rocket League** | Platform-specific ID |
| **Rainbow Six Siege** | Ubisoft ID |
| **EA SPORTS FC 26** | EA ID / Platform Tag |
| **eFootball 2026** | Konami ID / Platform Tag |

Each game passport also records your **current in-game rank** (if applicable), your **preferred roles** for that game, and any **aliases** you've used previously. This creates a verifiable chain of identity — when you register for a Valorant tournament, the organizer can confirm your Riot ID matches your DeltaCrown profile.

**Passport security:**
- Deleting a game passport requires a separate OTP verification (to prevent account hijacking from removing identity data)
- A cooldown period applies after deletion before a new passport can be created for the same game
- Passport changes are logged in the audit trail

### Chapter 4: Privacy — You Control What The World Sees

DeltaCrown believes your data belongs to you. The `PrivacySettings` model gives you **field-level control** over who can see what:

| Setting | Options |
|---------|---------|
| Profile visibility | Public, Followers Only, Private |
| Real name visibility | Hidden, Followers Only, Public |
| Location visibility | Hidden, Country Only, Full |
| Contact info visibility | Hidden, Team Only, Public |
| Game IDs visibility | Public, Followers Only, Hidden |
| Match history visibility | Public, Followers Only, Hidden |
| DeltaCoin balance visibility | Hidden, Public |
| Online status | Show, Hide |

**Follow System:**
DeltaCrown implements a social follow system. When your profile is public, anyone can follow you to see your activity. When your profile is private or followers-only, they must send a **Follow Request** that you can approve or reject. This mirrors the social media patterns users already understand, but applied to a competitive context.

### Chapter 5: Your First Team — Finding Your People

Competitive esports is a team sport. Even solo-queue warriors eventually seek the structure, strategy, and camaraderie of a dedicated team. DeltaCrown's team system is designed to make that as natural as possible.

**Finding a Team:**

There are three paths to joining a team:

**Path 1: The LFT Directory.**
Enable "Looking For Team" in your profile. Specify the game, your role, your rank, and your availability. Team captains browsing the LFT directory (or using DeltaCrown's Smart Recruitment matching) will find you. When they're interested, they send you a **Team Invite** — a formal invitation that appears in your notifications and on your dashboard.

**Path 2: The Team's Recruitment Post.**
Many teams actively recruit by posting recruitment positions. These posts specify what the team is looking for: game, role, minimum rank, play schedule, competitive goals. You browse these in the community feed or game-specific channels and submit a **Quick Apply** — your profile, a short message, and your availability.

**Path 3: Direct Invite.**
If a captain knows you — from a tournament, from Discord, from a friend's recommendation — they can send you a direct invite from the team management panel.

**Accepting an Invite:**

When you accept a team invite, several things happen simultaneously:
1. A `TeamMembership` record is created with your assigned role (Player, Substitute, etc.)
2. You gain access to the team's private channels (web team chat and, if Discord is integrated, the team's Discord channel)
3. Your profile updates to show your team affiliation
4. The team's roster page reflects your addition
5. If your Discord account is linked, you receive the `@Team: [Name]` role on Discord
6. A `TeamMembershipEvent` log entry records the action

**The Team Experience:**

Once you're on a team, DeltaCrown becomes a different platform for you. You gain access to:

- **Team Chat** — Real-time messaging with your teammates, synced between the website and Discord. Support for @mentions, file attachments, emoji reactions, threaded replies, and pinned messages.
- **Team Discussion Board** — Longer-form discussions organized by category: Announcements, Strategy, Recruitment, Questions, Feedback, Events, General.
- **Team Announcements** — Official team news posted by owners and managers.
- **Team Media Gallery** — Shared screenshots, clips, and highlights.
- **Team Journey Milestones** — Achievement tracking for the team as a whole.

### Chapter 6: The Competitive Heart — Entering Your First Tournament

The moment has arrived. You've built your profile, linked your game passports, joined a team, and practiced for weeks. It's time to enter a tournament.

**Discovering Tournaments:**

DeltaCrown surfaces tournaments through multiple channels:
- **The Tournament Hub** — The main listing page, filterable by game, format, region, entry fee, and date
- **Discord** — Auto-announcements in `#tournament-announcements` with game role pings
- **Dashboard** — Your personalized dashboard highlights tournaments relevant to your games and skill level
- **Notifications** — If you've opted in, DeltaCrown notifies you about new tournaments in your games
- **Spectator Pages** — Even before you log in, you can browse public tournament listings

**The Smart Registration Process:**

DeltaCrown's registration system is not a simple "click to join" form. It is a **smart, multi-step process** designed to eliminate errors, prevent fraud, and ensure every participant is ready to compete.

**Step 1: Tournament Selection.**
You click "Register" on a tournament page. DeltaCrown immediately checks:
- Is registration open? (Date-based gating)
- Is there capacity? (Team count vs. maximum)
- Are you eligible? (Game passport exists for this game, no active bans, reputation score meets minimum)

**Step 2: Team Selection (for team tournaments).**
If the tournament is team-based, you select which of your teams to register. DeltaCrown checks:
- Does the team have enough active players for this game's roster requirement?
- Is the team already registered for this tournament?
- Is the team's game passport valid?

**Step 3: Roster Confirmation.**
You confirm the starting lineup and substitutes. DeltaCrown auto-fills from your team's roster but allows adjustments. Each player's game ID for the tournament's game is verified.

**Step 4: Registration Form (if required).**
Some tournaments have custom registration forms created by the organizer — additional fields like "What's your team's scrim schedule?" or "Do you consent to stream broadcasting?" These are dynamic forms built using DeltaCrown's form builder.

**Step 5: Payment (if entry fee required).**
If the tournament has an entry fee:
1. The fee amount is displayed in BDT (and optionally DeltaCoin)
2. You select your payment method: bKash, Nagad, Rocket, bank transfer, or DeltaCoin
3. For mobile payment methods, DeltaCrown displays the recipient number and instructions
4. You complete the payment on your banking app
5. You return to DeltaCrown and upload a screenshot of the payment confirmation
6. Your registration enters "Payment Pending" status

**Step 6: Confirmation.**
Once payment is verified (by staff or automatically for DeltaCoin payments), your registration is confirmed. You receive:
- An in-app notification
- A confirmation email
- A Discord DM (if linked)
- Your tournament role on Discord (if applicable)
- The tournament appears on your dashboard with match schedules

**Draft Auto-Save:**
At every step, DeltaCrown auto-saves your registration progress every 30 seconds. If you close the browser, lose internet, or switch devices, you can resume exactly where you left off. The `RegistrationDraft` model captures every field as you go.

### Chapter 7: Match Day — The Stage Is Set

Match day on DeltaCrown is a carefully orchestrated experience, whether you're on the website, on Discord, or both.

**Before the Match:**

Thirty minutes before your scheduled match, DeltaCrown sends a reminder:
- In-app notification (banner + sound)
- Email (with match details, opponent info, and voice channel link)
- Discord DM: "⏰ Your match starts in 30 minutes! Team Phoenix vs Team Dragon — Match Room #3"

**Check-In:**

DeltaCrown uses a **check-in system** to confirm that teams are actually present and ready to play. The check-in window is configurable (typically 15–30 minutes before match time).

You can check in through:
- The website (a button on the match page)
- Discord (`/check-in [tournament-id]`)

Both teams must check in to proceed. If one team fails to check in before the window closes, they may be auto-disqualified (depending on tournament rules), and the opponent advances.

**During the Match:**

The match itself happens in the game — but DeltaCrown provides the operational layer:
- Voice channels on Discord for communication
- A match page on the website showing live status
- Staff monitoring in the match operations channel

**After the Match — Score Reporting:**

When the match concludes, the team captain reports the score:
- On the website: Navigate to the match page, enter scores, optionally upload screenshots
- On Discord: `/report-score [match-id]` opens a modal for score entry

DeltaCrown uses a **dual-confirmation system**: both teams must submit their version of the result. If the submissions match, the result is auto-approved. If they conflict, a dispute is automatically created.

**Result Confirmation Flow:**
```
Captain A reports: Team A wins 2-1
Captain B reports: Team A wins 2-1
→ Match confirmed automatically ✅

Captain A reports: Team A wins 2-1
Captain B reports: Team B wins 2-0
→ Conflict detected → Auto-dispute created ⚠️
```

### Chapter 8: When Things Go Wrong — Disputes

Disputes are inevitable in competitive play. DeltaCrown handles them with a structured, evidence-based process:

1. **Filing:** A dispute is filed (manually via the website or `/dispute` on Discord, or automatically when scores conflict).
2. **Thread Creation:** A private thread is created on Discord pulling in both captains, the assigned referee, and the tournament organizer.
3. **Evidence Phase:** Both teams submit evidence: screenshots, video clips, game logs.
4. **Review:** The referee reviews the evidence, optionally consulting the organizer.
5. **Resolution:** The referee issues a ruling via the platform (or `/resolve-dispute` on Discord).
6. **Notification:** Both teams are notified of the ruling with the referee's notes.
7. **Audit Trail:** Every step is logged in the `DisputeRecord` and `DisputeEvidence` models.

The ruling is final for that tournament (with escalation to platform admins for exceptional cases). The process is designed to be **fast** (target: < 30 minutes for standard disputes) and **transparent** (both parties see the evidence and reasoning).

### Chapter 9: Climbing the Ladder — Rankings & Leaderboards

Every match you play, every tournament you enter, every victory and defeat — it all feeds into DeltaCrown's ranking system.

**How Rankings Work:**

DeltaCrown computes rankings across multiple dimensions:

| Dimension | Description |
|-----------|-------------|
| **Game-Specific Player Ranking** | Your performance in a specific game (e.g., your Valorant rank on DeltaCrown) |
| **Game-Specific Team Ranking** | Your team's standing in a specific game |
| **Global Player Ranking** | Your aggregate performance across all games |
| **Global Team Ranking** | Your team's aggregate standing |
| **Seasonal Ranking** | Performance within a defined season (reset periodically) |
| **All-Time Ranking** | Lifetime cumulative performance |
| **MMR / ELO** | Skill-based matchmaking rating |

**The Leaderboard Points (LP) system:**
- All players start at **1,000 LP** in each game
- Tournament placements, match wins, and losses adjust LP
- Higher-stakes tournaments grant more LP (weighting by prize pool, participant count, and tournament tier)
- **LP decay:** Inactive players slowly lose LP over time, ensuring the leaderboard reflects current form, not past glory
- LP determines your **tier**: Bronze → Silver → Gold → Platinum → Diamond → Master → GrandMaster → Champion

**Leaderboard visibility:**
- Global leaderboards are public (spectator-accessible)
- Your personal rank appears on your profile
- Weekly leaderboard snapshots are posted to Discord game channels
- Historical trend charts show your LP curve over time (via `LeaderboardSnapshot`)

### Chapter 10: Badges, Achievements & Trophies

DeltaCrown rewards engagement and achievement through a layered recognition system:

**Badges:**
Earned through platform milestones: first tournament entry, first win, 10 wins, 100 matches played, profile completion, team creation, DeltaCoin milestones, community contributions. You can **pin up to 5 badges** on your profile to showcase your identity.

**Trophies:**
Earned through tournament victories. Each tournament awards trophies to top placements (1st, 2nd, 3rd). Trophies are permanent and cumulative — your trophy case grows with every competition.

**Certificates:**
DeltaCrown generates digital certificates for tournament participants and winners. These are professional-grade, customizable documents that display the player's name, DeltaCrown ID, tournament name, placement, date, and a verification link. They can be shared on social media and used in personal portfolios.

**Skill Endorsements:**
Other players and teammates can endorse your skills. If a teammate thinks you're an exceptional strategist, they can endorse your "Strategy" skill. Endorsements are visible on your profile and contribute to your reputation.

### Chapter 11: The Challenge Hub — Competition Beyond Tournaments

Tournaments are the main stage, but the Challenge Hub is the **training ground, the proving ground, and the playground**.

The `Challenge` model supports four types of competitive engagement:

| Type | Description |
|------|-------------|
| **Wager Match** | Two teams/players put up DeltaCoin and compete. Winner takes the pot. |
| **Community Bounty** | A community-posted challenge with a reward. "Beat this score on this map." |
| **Scrim** | A practice match between two teams. No stakes, just preparation. |
| **1v1 Duel** | Head-to-head competition between individual players. |

Challenges are less formal than tournaments — no brackets, no multi-round structures. They are quick, competitive engagements that keep the community active between tournament seasons.

### Chapter 12: The Crown Store — Express Yourself

The DeltaCrown Crown Store (`ecommerce` app) and DeltaCoin Shop (`shop` app) offer two layers of commerce:

**Crown Store (BDT):**
- Physical merchandise: Branded apparel, gaming accessories, stickers
- Digital products: Premium profile themes, custom banners, avatar frames
- Subscriptions: Premium features (future)
- Team merchandise: Official team gear (teams can list their own merch)

Products have categories, brands, variants (size, color), and rarity levels (Common, Uncommon, Rare, Epic, Legendary, Mythic). The rarity system gamifies the shopping experience — rare items carry prestige.

**DeltaCoin Shop:**
- Items purchasable with DeltaCoin only
- Profile effects, limited-edition badges, tournament entry fee discounts
- Reservation hold system: DeltaCoin is "held" during checkout and either captured (purchase completes) or released (purchase cancelled/expired)

### Chapter 13: The Social Layer — Following, Connecting, Community

DeltaCrown is more than a competition platform — it is a community. The social features that bind it together include:

**Following:**
Follow players and teams to see their activity in your feed. When they win a tournament, post content, or climb the leaderboard — you know about it. For private profiles, follow requests are required.

**Content & Media:**
Players can share blog posts, strategy guides, match highlights, and team announcements in the community feed. Content is moderated (auto-flag at 5+ reports, manual review, appeal process) and engagement-tracked (views, likes, comments, shares).

**The Community Feed:**
A curated stream of activity: tournament announcements, match results, leaderboard changes, team news, and user content. Algorithmic trending surfaces the most engaging content, while chronological view keeps things honest.

**Discord Integration:**
Your Discord identity is a first-class citizen on DeltaCrown. When your accounts are linked:
- Your Discord appears on your profile
- You receive platform notifications as Discord DMs
- Your team chat syncs between web and Discord
- Tournament operations flow seamlessly between both platforms
- Your activity on Discord can earn you DeltaCoin

### Chapter 14: The DeltaCrown Wallet — Managing Your Money

The DeltaCrown Wallet is your financial hub on the platform:

**Wallet Features:**
- **Balance Overview:** DeltaCoin balance, pending payouts, lifetime earnings
- **Transaction History:** Every in, every out, searchable and filterable
- **Payment Methods:** Registered bKash, Nagad, Rocket numbers and bank details
- **PIN Security:** A separate PIN protects withdrawal operations
- **Withdrawal:** Request DeltaCoin-to-BDT payouts (where applicable to prize winnings)

**Wallet Security:**
- PIN-protected withdrawals
- Email confirmation for large transactions
- Rate limiting on withdrawal requests
- Suspicious activity detection
- Full transaction audit trail

### Chapter 15: Getting Help — Support & FAQ

DeltaCrown is complex, and questions will arise. Here's where to find answers:

**FAQ (Web + Discord):**
Categorized knowledge base covering: General platform questions, Tournament rules, Payment procedures, Technical troubleshooting, Team management, and Game rules.

**Contact Form:**
Submit a support request with your category and priority. Staff responds within the target SLA.

**Discord Support:**
Open a support ticket via `/ticket` in `#open-a-ticket`. Payment-specific issues get private threads in `#payment-help`.

**Community:**
Often, the fastest answer comes from fellow players. Game-specific channels on Discord are excellent places to ask questions, and the community is encouraged to help each other.

---

*Volume II has traced the journey of a player from first click to tournament champion. Now let us step behind the curtain and see how the platform is operated.*

---

# Volume III — The Operations Guide: For Admins, Staff & Organizers

## Running the Machine

---

### Chapter 1: The Tournament Operations Center — Command Central

If the tournament engine is the heart of DeltaCrown, the **Tournament Operations Center (TOC)** is the brain. It is the interface through which tournament organizers create, configure, manage, and conclude competitive events — and it is one of the most sophisticated tools on the platform.

The TOC lives at `/toc/` on the website and is accessible only to verified tournament organizers and platform administrators. It is a single-page application (SPA) within the larger DeltaCrown ecosystem, designed for efficiency: every button, every dropdown, every status indicator is positioned for speed during live tournament operations.

**Accessing the TOC:**
To become a tournament organizer on DeltaCrown, a user must apply and be approved by platform administrators. This is a deliberate gatekeeping measure — tournaments involve real money (entry fees and prizes), and DeltaCrown holds organizers to a high standard. Once approved, the `@Organizer` role is synced to Discord, and the TOC becomes accessible.

### Chapter 2: Creating a Tournament — The Ten Steps

Creating a tournament on DeltaCrown is a ten-step guided process. Each step is clearly defined, with validation at every stage to prevent misconfigured tournaments from going live.

**Step 1: Basic Information**
- Tournament name (unique, descriptive)
- Description (rich text editor with CKEditor 5 — supports formatting, images, links)
- Game selection (from DeltaCrown's 11 supported games — auto-loads game-specific configuration)
- Participation type: Solo or Team
- Tournament format: Single Elimination, Double Elimination, Round Robin, Swiss System, Group Stage → Playoffs

**Step 2: Schedule & Dates**
- Registration opens (date/time)
- Registration closes (date/time)
- Tournament start date
- Tournament end date (estimated)
- Check-in window duration (15 min, 30 min, 45 min, 1 hour)
- Timezone selection (default: BST — Bangladesh Standard Time)

**Step 3: Capacity & Eligibility**
- Maximum teams/players (2 to 256, powers of 2 recommended for elimination formats)
- Minimum teams/players required to proceed
- Region restriction (open, South Asia, Bangladesh only, etc.)
- Minimum reputation score (default: none)
- Rank restrictions (e.g., "Diamond and above only")
- Age restrictions (if applicable)

**Step 4: Prize Structure**
- Prize pool currency: BDT and/or DeltaCoin
- Distribution: 1st place, 2nd place, 3rd place, MVP award, etc.
- Custom prize tiers (e.g., "Best Clutch" bonus)
- Sponsor prizes (if sponsor is attached)
- Entry fee split: Platform percentage vs. Prize pool contribution

**Step 5: Entry Fee & Payment**
- Entry fee amount (BDT and/or DeltaCoin)
- Payment methods enabled: bKash, Nagad, Rocket, bank transfer, DeltaCoin
- For each method: recipient account number, account holder name, instructions
- Refund policy: Full refund before tournament starts / Partial refund / No refund
- Fee waiver rules (e.g., "Top 5 ranked teams enter free")

**Step 6: Rules & Documents**
- Tournament rulebook (upload PDF or use the built-in rich text rules editor)
- Specific rules: Match format (BO1, BO3, BO5), map pool, banned agents/characters, permitted equipment
- Code of conduct reference
- Stream broadcasting consent
- Rulebook versioning (if rules are updated mid-registration, all registrants are notified)

**Step 7: Staff Assignment**
- Assign staff roles: Referee, Moderator, Commentator, Observer
- Each role comes from DeltaCrown's capability-based staff system:
  - `StaffRole` defines capabilities (can_report_results, can_manage_disputes, can_modify_brackets, etc.)
  - `TournamentStaffAssignment` links users to tournaments with specific roles
  - `MatchRefereeAssignment` links referees to specific matches

**Step 8: Registration Form (Optional)**
- Use the dynamic form builder to create custom registration questions
- Question types: text, number, select, multi-select, checkbox, file upload
- Required vs optional fields
- Form responses are stored per-registration and viewable in the organizer's dashboard

**Step 9: Streaming & Media**
- Streaming URLs: YouTube Live, Twitch channels
- Social media links for the tournament
- Tournament logo and banner upload
- Sponsor logos and display configuration

**Step 10: Review & Publish**
- Preview the tournament page as it will appear to players
- Final validation check (all required fields filled, dates logical, prize pool ≥ 0)
- Save as draft (can be returned to later)
- Publish → tournament status changes to "Published" → auto-announcement fires to Discord

**Templates:**
Organizers who run recurring tournaments can save their configuration as a `TournamentTemplate` — a reusable blueprint that pre-fills all ten steps. "Clone last tournament" with one click.

### Chapter 3: Managing Registration — The Organizer Dashboard

Once a tournament is published and registration is open, the organizer monitors and manages registrations through the TOC dashboard:

**Registration Queue View:**
- List of all registrations: team name, captain, registration date, payment status
- Filters: confirmed, pending payment, cancelled, rejected
- Quick actions: approve, reject, refund

**Payment Verification:**
For entry fees paid via bKash/Nagad/Rocket:
1. Player uploads payment screenshot
2. Screenshot appears in the verification queue with payment details
3. Staff reviews: checks amount, transaction ID, sender info
4. Staff approves (registration confirmed) or rejects (with reason — e.g., "Amount doesn't match," "Screenshot is unclear," "Duplicate transaction ID")
5. Player is notified of the outcome

**Registration Analytics:**
- Total registrations vs. capacity (progress bar)
- Registration velocity (signups per day/hour)
- Payment conversion rate (% who complete payment)
- Common rejection reasons
- Geographic distribution of participants

### Chapter 4: Seeding & Bracket Generation

When registration closes (or at the organizer's discretion), brackets are generated.

**Seeding Methods:**

| Method | Description | Best For |
|--------|-------------|----------|
| **Slot Order** | Teams are placed in bracket positions based on registration order | Casual tournaments |
| **Random** | Teams are randomly assigned to bracket positions | Fairness when no ranking data exists |
| **Ranked** | Teams are seeded based on their DeltaCrown ranking (LP) | Competitive tournaments where top teams shouldn't meet early |
| **Manual** | Organizer manually places teams in each position | Invitational tournaments, showmatches |

**Bracket Formats:**

| Format | How It Works |
|--------|-------------|
| **Single Elimination** | Lose once, you're out. 32 teams → 5 rounds → 1 champion |
| **Double Elimination** | Upper and lower brackets. Two losses to eliminate. More matches, fairer results |
| **Round Robin** | Every team plays every other team. Final standings by W/L record |
| **Swiss System** | Fixed number of rounds. Teams matched against opponents with similar records. Efficient for large fields |
| **Group Stage → Playoffs** | Teams divided into groups (round robin), top finishers advance to elimination playoffs |

**Bracket Management:**
- `Bracket` and `BracketNode` models represent the bracket structure
- `BracketEditLog` records every manual edit (audit trail)
- Brackets can be shared publicly (spectator view) or kept hidden until match day
- Live bracket updates push to the website (WebSocket) and Discord (webhook)

### Chapter 5: Live Tournament Operations

When the tournament goes live, the TOC transforms into a **real-time operations dashboard**.

**Match Flow (for staff):**

```
MATCH CREATED (auto-generated from bracket)
  └── Match assigned to referee (if manual assignment is configured)
  └── Match visible in #match-ops on Discord

MATCH SCHEDULED
  └── Both teams notified (30 min, 15 min, 5 min before)
  └── Check-in window opens

CHECK-IN PHASE
  └── Both teams check in → match proceeds
  └── One team fails → no-show protocol:
      ├── Grace period (configurable: 5–15 min)
      ├── If still absent → auto-disqualification
      └── Opponent advances

MATCH IN PROGRESS
  └── Referee monitors (Discord voice + match ops channel)
  └── Players compete in-game
  └── Real-time status updates in TOC dashboard

SCORE SUBMISSION
  └── Captain A submits result
  └── Captain B submits result
  └── If match → auto-confirm
  └── If mismatch → auto-dispute

MATCH CONFIRMED
  └── Bracket updated
  └── Next match generated
  └── Leaderboard points queued for calculation
  └── Result embed posted to Discord
```

**Match Operations Commands (staff):**

| Action | Where | Description |
|--------|-------|-------------|
| Override result | TOC web | Staff manually sets match result (with mandatory reason) |
| Restart match | TOC web | Nullify result, reset match to scheduled state |
| Reassign referee | TOC web | Change referee assignment |
| Add moderator note | TOC web | Attach internal note to match record (not visible to players) |
| Force check-in | TOC web | Mark a team as checked in (for technical issues) |
| Emergency substitution | TOC + Discord | Process an emergency player swap |
| DQ team | TOC web | Disqualify a team from the tournament |

All staff actions are logged in `MatchOperationLog` with the acting staff member, timestamp, action type, and reason.

### Chapter 6: Dispute Management — The Referee's Guide

Disputes are the referee's primary responsibility. DeltaCrown provides a structured workflow:

**Dispute Lifecycle:**

```
FILED
  └── Dispute record created (DisputeRecord model)
  └── Discord private thread auto-created (if Discord integration active)
  └── Referee notified

EVIDENCE PHASE
  └── Both parties upload evidence (screenshots, clips, timestamps)
  └── Evidence stored in DisputeEvidence model
  └── Referee reviews in TOC dispute panel

UNDER REVIEW
  └── Referee examines:
      ├── Both score submissions (with timestamps)
      ├── Uploaded evidence
      ├── Match server logs (if available)
      ├── Player history (past disputes, reputation score)
      └── Game-specific rules

RESOLVED
  └── Referee issues ruling:
      ├── Winner determined + correct score
      ├── Written explanation (visible to both teams)
      ├── Optional sanction recommendation
      └── Resolution method: /resolve-dispute on Discord or TOC web panel
  └── Match result updated
  └── Both teams notified
  └── Dispute thread archived on Discord
  └── Leaderboard adjusted

ESCALATED (rare)
  └── If standard resolution fails (referee conflict of interest, etc.)
  └── Escalated to tournament organizer → platform admin
  └── Higher authority reviews and overrides
```

**Referee Best Practices:**
- Always acknowledge the dispute within 10 minutes ("I've received your dispute and am reviewing it")
- Request specific evidence ("Please upload a screenshot of the final scoreboard")
- Explain the ruling clearly ("Based on the screenshots from both teams, the scoreboard shows Team A winning 13-9 on Haven")
- Be neutral, factual, and professional
- If uncertain, consult the organizer before ruling
- Document everything — your future self (and auditors) will thank you

### Chapter 7: Staff Roles & The Permission Model

DeltaCrown's staff system is **capability-based**, not title-based. This means permissions are not hardcoded to role names — they are assigned via the `StaffRole` model, which defines individual capabilities:

| Capability | Description |
|-----------|-------------|
| `can_report_results` | Submit or override match results |
| `can_manage_disputes` | File, review, and resolve disputes |
| `can_modify_brackets` | Edit bracket positions, reseed |
| `can_manage_registrations` | Approve/reject registrations |
| `can_manage_payments` | Verify payments, process refunds |
| `can_assign_staff` | Add/remove staff from tournaments |
| `can_make_announcements` | Post official tournament announcements |
| `can_manage_settings` | Modify tournament settings |
| `can_view_audit_logs` | Access operational audit trails |
| `can_manage_certificates` | Generate and distribute certificates |

A "Referee" role might have: `can_report_results`, `can_manage_disputes`, `can_view_audit_logs`.
A "Head Admin" role might have all capabilities.
A "Registration Manager" role might have only: `can_manage_registrations`, `can_manage_payments`.

This flexibility means tournament organizers can create custom staff configurations that match their specific operational needs.

### Chapter 8: Multi-Stage Tournaments & Advanced Formats

For large-scale events, DeltaCrown supports **multi-stage tournaments** through the `TournamentStage`, `Group`, `GroupStanding`, and `QualifierPipeline` models:

**Group Stage → Playoffs:**
1. Teams are divided into groups (manually or automatically)
2. Each group plays round-robin (all teams face each other)
3. `GroupStanding` tracks wins, losses, map difference, head-to-head records
4. Top N teams from each group advance to the elimination bracket
5. The bracket is seeded based on group stage performance

**Qualifier Pipeline:**
For massive events that need progressive filtering:
1. `QualifierPipeline` defines the overall structure
2. `PipelineStage` defines each qualifier wave (e.g., "Open Qualifier #1", "Open Qualifier #2", "Closed Qualifier")
3. `PromotionRule` defines how teams advance between stages (top 4 from each open qualifier → closed qualifier)
4. Teams progress through stages until the final roster of qualified teams is assembled

**Map Veto System:**
For FPS and tactical games, DeltaCrown supports a full map pick-ban system:
- `MapPoolEntry` defines the available maps for a tournament/game
- `MatchVetoSession` tracks the veto process:
  - Team A bans a map
  - Team B bans a map
  - Team A picks a map (their home map)
  - Team B picks a map (their home map)
  - Remaining map is the decider
- The veto process can be managed via the TOC or through Discord bot interactions

### Chapter 9: Post-Tournament Operations

A tournament doesn't end when the final match is played. Post-tournament operations are critical:

**Prize Distribution:**
1. Tournament results are finalized and verified
2. Prize amounts are assigned based on the prize structure:
   - DeltaCoin prizes are credited instantly to winners' wallets
   - BDT prizes enter the distribution queue
3. For BDT payouts:
   - Winners must have registered a payment method (bKash/Nagad/Rocket/bank)
   - For prize amounts above the KYC threshold, winners must complete KYC verification
   - Payments are processed by platform finance staff
   - Each payout is tracked via `PrizeTransaction`
4. Prize claim workflow (`PrizeClaim` model): winners confirm their payout details, staff processes, system records

**Certificate Generation:**
- DeltaCrown generates digital certificates for participants and winners
- Templates are customizable per tournament (`CertificateTemplate`)
- Certificates include: player name, DeltaCrown ID, tournament name, placement, date, QR code for verification
- `CertificateRecord` tracks issuance

**Post-Tournament Analytics:**
The TOC provides an analytics dashboard showing:
- **Participation Metrics:** Registration count, show-up rate, completion rate
- **Engagement Metrics:** Matches played, disputes filed, average match duration
- **Financial Metrics:** Entry fees collected, prize pool distributed, platform revenue
- **Satisfaction Indicators:** Dispute rate, no-show rate, forfeit rate
- **Community Impact:** New accounts created, new teams formed, leaderboard movement

**Cleanup:**
- Tournament-specific Discord roles are removed (with 48hr grace period for post-event discussion)
- Temporary channels are archived
- Tournament status moves to "Completed" → eventually "Archived"

### Chapter 10: The Admin Panel — Platform Governance

Platform administrators have access to the Django Admin panel, enhanced with the Unfold theme for a modern, intuitive interface.

**Admin Capabilities:**

| Area | What Admins Control |
|------|-------------------|
| **Users** | Account management, verification status, ban/unban, KYC review |
| **Tournaments** | Override tournament settings, force status changes, manage disputes |
| **Teams/Orgs** | Verify organizations, manage team disputes, handle ownership transfers |
| **Economy** | DeltaCoin issuance, wallet management, transaction auditing |
| **Payments** | Payment verification queue, refund processing, financial reports |
| **Games** | Game configuration, roster settings, scoring rules |
| **Leaderboards** | Manual rank adjustments, snapshot management, decay configuration |
| **Content** | Content moderation, featured content, blog management |
| **Moderation** | Sanction management, abuse report review, appeal processing |
| **Notifications** | System announcements, broadcast messages, notification system health |
| **Support** | Support ticket management, FAQ editing, testimonial approval |
| **System** | Health checks, metrics, error logs, feature flags |

**Admin Audit Trail:**
Every admin action is logged. The `ModerationAudit` and `UserAuditEvent` models create an append-only record of who did what, when, and why. This is not optional — it is structural. There is no way to make a consequential change on DeltaCrown without it being recorded.

### Chapter 11: Moderation Operations — The Moderator's Handbook

Moderators are the guardians of community health. Their tools include:

**Abuse Report Processing:**
1. Users flag content or behavior via the report system
2. Reports appear in the moderator queue (`AbuseReport` model: open → triaged → resolved/rejected)
3. Moderators review: check the reported content, the reporter's history, the defendant's history
4. Take action: dismiss, warn, mute, suspend, or escalate to admin

**Sanction System:**
The `ModerationSanction` model is the enforcement tool:

| Sanction | Scope | Duration | Effect |
|----------|-------|----------|--------|
| **Warning** | Global | Permanent record | No functional restriction, but documented |
| **Mute** | Channel or Global | Time-bounded | Cannot send messages in specified scope |
| **Tournament Suspension** | Specific tournament | Until tournament ends | Cannot participate in the specified tournament |
| **Platform Suspension** | Global | Time-bounded | Cannot access platform features (can still view public pages) |
| **Ban** | Global | Permanent or time-bounded | Full access revocation + Discord kick/ban |

**Progressive Enforcement:**
Moderators follow a progressive discipline model:
1. First offense (minor): Verbal warning
2. Second offense: Written warning (logged sanction)
3. Third offense: Temporary mute (24hr–7d)
4. Persistent violations: Suspension (7d–30d)
5. Severe or repeated violations: Permanent ban

**Cross-Platform Enforcement:**
When a sanction is applied on DeltaCrown:
- If the user's Discord account is linked, the sanction can be mirrored on Discord
- Discord timeouts for temporary mutes
- Discord kick/ban for platform bans
- All synced via Celery tasks

### Chapter 12: The Organizer's Financial Lifecycle

Tournament organizers manage real money on DeltaCrown, and the platform provides full financial transparency:

**Revenue Flow:**
```
Player pays Entry Fee (e.g., ৳200)
  │
  ├── Platform Fee (configurable, e.g., 30%): ৳60 → DeltaCrown revenue
  │
  └── Prize Pool Contribution (e.g., 70%): ৳140 → Tournament prize pool
```

**Financial Dashboard (Organizer View):**
- Total entry fees collected
- Platform fee deductions
- Net prize pool available
- Prize distribution status (pending, processing, completed)
- Refund log (cancelled registrations)
- Revenue per tournament (historical)

**For Platform Admins (Finance View):**
- Cross-tournament revenue reports
- Payment method breakdown (% bKash, % Nagad, etc.)
- Collection rate (% of registered who completed payment)
- Payout processing queue
- DeltaCoin economy health: circulation, velocity, sink-to-source ratio

### Chapter 13: Game Configuration Management

Adding or modifying a game on DeltaCrown is a database operation, not a code deployment:

**The `Game` model captures:**
- Display information: name, slug, short code, description, category
- Visual assets: icon, logo, banner, card image
- Branding: primary and secondary colors
- Identity configuration: what game ID fields to ask for (label, placeholder, validation regex)
- Platform support: which platforms the game runs on

**The `GameRosterConfig` model captures:**
- Minimum and maximum team sizes
- Starter count, substitute count, coach count
- Required roles (e.g., a Valorant team needs at least one IGL)

**The `GameRole` model captures:**
- Available in-game roles (Duelist, Controller, Sentinel, Initiator for Valorant)
- Role descriptions and icons

**The `GameMatchResultSchema` model captures:**
- What fields to collect for match results (kills, deaths, assists, rounds won, maps won)
- Scoring rules for leaderboard point calculation

**Seed Commands:**
```bash
python manage.py seed_games                    # Load all 11 games with full config
python manage.py seed_game_passport_schemas     # Load game-specific identity field configs
python manage.py seed_game_ranking_configs      # Load ranking weights and tier thresholds
python manage.py backfill_game_profiles         # Optional: backfill existing users
```

These seed commands are **idempotent** — running them multiple times updates existing records without creating duplicates.

### Chapter 14: Monitoring & Observability

DeltaCrown provides operational visibility through multiple channels:

**Health Checks:**
- `/healthz/` — Basic application health (database connection, cache, task queue)
- `/readiness/` — Readiness probe for deployment orchestration

**Prometheus Metrics (`/metrics/`):**
- HTTP request latency, throughput, and error rates
- Database query performance
- Celery task queue depth and processing time
- DeltaCoin transaction volume
- Active WebSocket connections
- Tournament status distribution (how many live, how many registering)

**Grafana Dashboards:**
Pre-built dashboards for:
- Platform overview (users, tournaments, revenue)
- Tournament engine health (registration velocity, match throughput)
- Economy health (DeltaCoin circulation, transaction velocity)
- Discord integration health (sync success rate, bot uptime)
- Error tracking (via Sentry integration)

**Structured Logging:**
All application logs are JSON-formatted, including:
- Request ID for distributed tracing
- User ID for auditing
- Event type for filtering
- Timestamp for ordering

### Chapter 15: Security Architecture

DeltaCrown's security is layered and comprehensive:

| Layer | Mechanism |
|-------|-----------|
| **Authentication** | Custom User model + email OTP verification + JWT tokens for API |
| **Authorization** | RBAC at view, service, and model layers. Principle of least privilege. |
| **Data Integrity** | Hash-based match result verification, append-only transaction logs |
| **Session Security** | Secure cookies, CSRF protection, session timeout |
| **API Security** | JWT with refresh tokens, rate limiting, CORS whitelist |
| **Payment Security** | PIN-protected withdrawals, screenshot verification, staff approval |
| **Identity Security** | Game passport OTP deletion, cooldown periods, audit logging |
| **Infrastructure** | HTTPS everywhere, PostgreSQL with encrypted connections (Neon), Docker isolation |
| **Monitoring** | Anomaly detection, failed login tracking, suspicious activity alerts |
| **Compliance** | Audit trails on all state changes, soft deletes for data retention, GDPR-aware privacy controls |

**The Trust Index:**
DeltaCrown maintains a `TrustEvent` system that tracks positive and negative signals for each user:
- Positive: Verified email, completed KYC, clean dispute history, consistent match reporting
- Negative: Disputes lost, sanctions received, suspicious activity flags
- The aggregate trust score influences matchmaking priority, tournament eligibility, and staff confidence in dispute rulings

---

## Epilogue: The Living Platform

DeltaCrown is not a finished product. It is a **living ecosystem** — growing, adapting, and evolving with its community. Every tournament that runs teaches us something about operations. Every dispute that's resolved improves the process. Every player who goes from "just browsing" to "tournament champion" validates the vision.

The platform you've read about in these three volumes is the foundation. What gets built on top of it — the tournaments that create legends, the teams that become dynasties, the rivalries that define seasons, the stories that inspire the next generation — that comes from you.

From the teenager in a Dhaka internet cafe to the professional representing Bangladesh on the world stage, the journey starts here. The infrastructure is ready. The community is growing. The stage is set.

**From the Delta to the Crown — Where Champions Rise.**

---

## Appendices

### Appendix A: Supported Games Quick Reference

| Game | Category | Platforms | Team Size | Key Roles |
|------|----------|-----------|-----------|-----------|
| Valorant | FPS | PC | 5 | Duelist, Controller, Sentinel, Initiator, Flex, IGL |
| CS2 | FPS | PC | 5 | Entry Fragger, AWPer, Support, Lurker, IGL |
| PUBG Mobile | Battle Royale | Mobile | 4 | IGL, Fragger, Scout, Support |
| Mobile Legends | MOBA | Mobile | 5 | Tank, Marksman, Mage, Assassin, Support, Fighter |
| Free Fire | Battle Royale | Mobile | 4 | IGL, Fragger, Rusher, Support |
| Call of Duty Mobile | FPS | Mobile | 5 | Slayer, OBJ, Support, Anchor, Flex |
| Dota 2 | MOBA | PC | 5 | Carry, Mid, Offlane, Soft Support, Hard Support |
| Rocket League | Vehicle | PC/Console | 3 | Striker, Midfielder, Defender |
| Rainbow Six Siege | FPS | PC/Console | 5 | Hard Breach, Soft Breach, Intel, Anchor, Roamer |
| EA SPORTS FC 26 | Sports | PC/Console/Mobile | 1 (solo) | — |
| eFootball 2026 | Sports | PC/Console/Mobile | 1 (solo) | — |

### Appendix B: Tournament Format Comparison

| Format | Best For | Teams | Rounds | Matches | Fairness |
|--------|---------|-------|--------|---------|---------|
| Single Elimination | Speed, excitement | 4–256 | log₂(N) | N-1 | Low (one bad day eliminates) |
| Double Elimination | Fairness, second chances | 4–64 | ~2×log₂(N) | 2(N-1) | High (must lose twice) |
| Round Robin | True best team | 4–16 | N-1 | N(N-1)/2 | Highest (plays everyone) |
| Swiss | Large fields, time-limited | 8–128 | log₂(N) | N/2 per round | Good (matched by record) |
| Group + Playoff | Balance of fairness/excitement | 8–256 | Group + bracket | Varies | Good |

### Appendix C: DeltaCrown URLs & Navigation Map

| Path | Description | Access |
|------|-------------|--------|
| `/` | Homepage | Public |
| `/account/login/` | Login | Public |
| `/account/signup/` | Registration | Public |
| `/u/<slug>/` | Player profile | Profile privacy setting |
| `/tournaments/` | Tournament hub | Public |
| `/tournaments/<slug>/` | Tournament detail | Public |
| `/toc/` | Tournament Operations Center | Organizers + Admin |
| `/crownstore/` | Crown Store | Public (purchase requires login) |
| `/dashboard/` | User dashboard | Authenticated |
| `/notifications/` | Notification center | Authenticated |
| `/spectator/` | Spectator views | Public |
| `/search/` | Search | Public |
| `/support/` | FAQ & Contact | Public |
| `/players/<username>/` | Player detail | Public |
| `/api/docs/` | Swagger API docs | Public |
| `/api/redoc/` | ReDoc API docs | Public |
| `/admin/` | Admin panel | Staff + Admin |
| `/competition/` | Rankings & match reporting | Authenticated |

### Appendix D: Glossary

| Term | Definition |
|------|-----------|
| **DeltaCoin (DC)** | DeltaCrown's internal utility currency. Not convertible to real money. |
| **DeltaCrown ID (DC-YY-NNNNNN)** | Your unique identifier on the platform. |
| **TOC** | Tournament Operations Center — the organizer's dashboard. |
| **Game Passport** | Your game-specific identity (Riot ID, Steam ID, etc.) linked to your DeltaCrown account. |
| **LP** | Leaderboard Points — your competitive ranking metric. |
| **SR** | Skill Rating — your ELO-like matchmaking rating. |
| **KYC** | Know Your Customer — identity verification for prize claims. |
| **LFT** | Looking For Team — you're a free agent seeking a team. |
| **LFP** | Looking For Player — a team is recruiting. |
| **BO1 / BO3 / BO5** | Best of 1 / Best of 3 / Best of 5 matches in a series. |
| **Bracket** | The elimination tournament structure showing matchups. |
| **Seeding** | How teams are placed in the bracket based on ranking or random draw. |
| **Check-In** | Confirming your presence before a match. Required to proceed. |
| **Crown Store** | DeltaCrown's e-commerce marketplace for merchandise and digital products. |
| **Smart Recruitment** | DeltaCrown's AI-assisted player-team matching system. |
| **SSoT** | Single Source of Truth — the authoritative data record. |
| **Crown Points (CP)** | Points used for team/organization rankings. |
| **Reputation Score** | A trust metric (0–100) reflecting fair play behavior. |

---

**End of Document**  
**DeltaCrown Esports Platform — The Complete Guide v4.0**  
**© 2026 DeltaCrown. All rights reserved.**
