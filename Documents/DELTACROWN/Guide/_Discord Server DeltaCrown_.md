# DeltaCrown Discord Server — Complete Setup, Integration & Operations Guide

> **Document Version:** 3.0  
> **Last Updated:** February 27, 2026  
> **Classification:** Internal Operations + Community Blueprint  
> **Author:** DeltaCrown Platform Team  

---

## Table of Contents

- [Prologue: Why Discord? Why Now?](#prologue-why-discord-why-now)
- [Part 1: Strategic Foundation](#part-1-strategic-foundation)
  - [1.1 The DeltaCrown–Discord Philosophy](#11-the-deltacrowndiscord-philosophy)
  - [1.2 Discord's Role in the DeltaCrown Ecosystem](#12-discords-role-in-the-deltacrown-ecosystem)
  - [1.3 Integration Architecture Overview](#13-integration-architecture-overview)
  - [1.4 Core Objectives](#14-core-objectives)
- [Part 2: Server Identity & Branding](#part-2-server-identity--branding)
  - [2.1 Server Name & Vanity URL](#21-server-name--vanity-url)
  - [2.2 Visual Identity](#22-visual-identity)
  - [2.3 Server Banner & Splash Screen](#23-server-banner--splash-screen)
  - [2.4 Naming Conventions](#24-naming-conventions)
  - [2.5 Emoji & Sticker System](#25-emoji--sticker-system)
- [Part 3: User Personas & Experience Design](#part-3-user-personas--experience-design)
  - [3.1 Persona A — The Community Member](#31-persona-a--the-community-member)
  - [3.2 Persona B — The Competitive Player](#32-persona-b--the-competitive-player)
  - [3.3 Persona C — The Team Captain / Manager](#33-persona-c--the-team-captain--manager)
  - [3.4 Persona D — The Tournament Organizer](#34-persona-d--the-tournament-organizer)
  - [3.5 Persona E — The Content Creator](#35-persona-e--the-content-creator)
  - [3.6 Persona F — The Super Admin](#36-persona-f--the-super-admin)
- [Part 4: Role Hierarchy & Permission Architecture](#part-4-role-hierarchy--permission-architecture)
  - [4.1 Role Tier System](#41-role-tier-system)
  - [4.2 Complete Role List](#42-complete-role-list)
  - [4.3 Permission Matrix](#43-permission-matrix)
  - [4.4 Auto-Synced Roles from DeltaCrown Platform](#44-auto-synced-roles-from-deltacrown-platform)
- [Part 5: Server Structure — Complete Channel Blueprint](#part-5-server-structure--complete-channel-blueprint)
  - [5.1 Design Principles](#51-design-principles)
  - [5.2 Category & Channel Map](#52-category--channel-map)
  - [5.3 Channel Descriptions & Rules](#53-channel-descriptions--rules)
- [Part 6: DeltaCrown Sync Bot — Technical Architecture](#part-6-deltacrown-sync-bot--technical-architecture)
  - [6.1 Bot Overview](#61-bot-overview)
  - [6.2 System Architecture Diagram](#62-system-architecture-diagram)
  - [6.3 Slash Command Reference](#63-slash-command-reference)
  - [6.4 Event-Driven Workflows](#64-event-driven-workflows)
  - [6.5 Webhook Integration](#65-webhook-integration)
  - [6.6 OAuth2 Account Linking](#66-oauth2-account-linking)
- [Part 7: Tournament Operations via Discord](#part-7-tournament-operations-via-discord)
  - [7.1 Tournament Lifecycle on Discord](#71-tournament-lifecycle-on-discord)
  - [7.2 Match Day Operations](#72-match-day-operations)
  - [7.3 Check-In System](#73-check-in-system)
  - [7.4 Score Reporting](#74-score-reporting)
  - [7.5 Dispute Resolution](#75-dispute-resolution)
  - [7.6 Prize Distribution Announcements](#76-prize-distribution-announcements)
- [Part 8: Team & Organization Discord Integration](#part-8-team--organization-discord-integration)
  - [8.1 Team Channel Ecosystem](#81-team-channel-ecosystem)
  - [8.2 Organization Hub Channels](#82-organization-hub-channels)
  - [8.3 Bi-Directional Chat Sync](#83-bi-directional-chat-sync)
  - [8.4 Recruitment via Discord](#84-recruitment-via-discord)
- [Part 9: Community & Engagement Systems](#part-9-community--engagement-systems)
  - [9.1 Onboarding Flow](#91-onboarding-flow)
  - [9.2 DeltaCoin Economy on Discord](#92-deltacoin-economy-on-discord)
  - [9.3 Leaderboard & Ranking Feeds](#93-leaderboard--ranking-feeds)
  - [9.4 Content & Media Channels](#94-content--media-channels)
  - [9.5 Game-Specific Communities](#95-game-specific-communities)
  - [9.6 Events & Activations](#96-events--activations)
- [Part 10: Moderation & Safety](#part-10-moderation--safety)
  - [10.1 Auto-Moderation Rules](#101-auto-moderation-rules)
  - [10.2 Staff Moderation Workflow](#102-staff-moderation-workflow)
  - [10.3 Escalation Procedures](#103-escalation-procedures)
  - [10.4 Sanctions & Cross-Platform Enforcement](#104-sanctions--cross-platform-enforcement)
  - [10.5 Audit Logging](#105-audit-logging)
- [Part 11: Notification Routing — Discord as a Channel](#part-11-notification-routing--discord-as-a-channel)
  - [11.1 Notification Types Routed to Discord](#111-notification-types-routed-to-discord)
  - [11.2 DM vs Channel Notifications](#112-dm-vs-channel-notifications)
  - [11.3 User Preference Controls](#113-user-preference-controls)
- [Part 12: Analytics, Growth & Optimization](#part-12-analytics-growth--optimization)
  - [12.1 Metrics to Track](#121-metrics-to-track)
  - [12.2 Growth Strategies](#122-growth-strategies)
  - [12.3 Retention Mechanics](#123-retention-mechanics)
  - [12.4 Community Health Indicators](#124-community-health-indicators)
- [Part 13: Implementation Roadmap](#part-13-implementation-roadmap)
  - [13.1 Phase 1 — Foundation (Week 1–2)](#131-phase-1--foundation-week-12)
  - [13.2 Phase 2 — Bot Development (Week 2–4)](#132-phase-2--bot-development-week-24)
  - [13.3 Phase 3 — Integration (Week 4–6)](#133-phase-3--integration-week-46)
  - [13.4 Phase 4 — Community Launch (Week 6–7)](#134-phase-4--community-launch-week-67)
  - [13.5 Phase 5 — Advanced Features (Week 7–10)](#135-phase-5--advanced-features-week-710)
  - [13.6 Phase 6 — Optimization & Scale (Ongoing)](#136-phase-6--optimization--scale-ongoing)
- [Part 14: Appendices](#part-14-appendices)
  - [14.1 Full Permission Matrix Table](#141-full-permission-matrix-table)
  - [14.2 Bot Environment Variables](#142-bot-environment-variables)
  - [14.3 Webhook Payload Schemas](#143-webhook-payload-schemas)
  - [14.4 Embed Templates](#144-embed-templates)
  - [14.5 Emergency Procedures](#145-emergency-procedures)
  - [14.6 Media Asset Checklist](#146-media-asset-checklist)

---

## Prologue: Why Discord? Why Now?

In competitive esports, the game itself is only half the story. The other half — the conversations before a match, the strategy calls at midnight, the roar of a community when an underdog wins — that happens outside the game client. For millions of players worldwide, and especially across South and Southeast Asia, that happens on Discord.

DeltaCrown was built on a single conviction: **talent is universal, but opportunity is not.** The platform provides the infrastructure — tournaments, teams, rankings, economy — but infrastructure without community is like a stadium without fans. Discord is where the DeltaCrown community comes alive.

This document is not a simple "how to make a Discord server" checklist. It is the **complete architectural blueprint** for building a Discord server that functions as an extension of the DeltaCrown platform itself — where roles sync automatically, tournament announcements flow in real-time, match scores are reported through slash commands, disputes are resolved in private threads, and every interaction strengthens the competitive ecosystem.

The DeltaCrown Discord server is not a marketing side-channel. It is the **living, breathing heartbeat of the community**.

---

## Part 1: Strategic Foundation

### 1.1 The DeltaCrown–Discord Philosophy

DeltaCrown's approach to Discord is built on three pillars:

**Pillar 1: Seamless Integration, Not Duplication.**  
The Discord server does not replicate the platform. It extends it. A player does not "also" use Discord — their Discord identity *is* their DeltaCrown identity, linked via OAuth2. When they earn a badge on the platform, they unlock a role on Discord. When a tournament goes live on the website, an announcement fires in Discord before the player even refreshes their browser.

**Pillar 2: Progressive Disclosure.**  
A new member should never walk into a wall of 50 channels. They see the welcome channel, the rules, the general chat, and the game they care about. As they link their account, join a team, enter a tournament, or become staff — more channels reveal themselves naturally. The server grows *with* the user.

**Pillar 3: Community-Driven, Platform-Governed.**  
The community owns the culture. The platform owns the rules. Discord conversations are informal, but tournament operations flow through verified systems. Banter is human; match results are cryptographically consistent. This balance is what makes DeltaCrown's Discord different from every other esports server.

### 1.2 Discord's Role in the DeltaCrown Ecosystem

Discord serves seven distinct functions within DeltaCrown:

| Function | Description | Example |
|----------|-------------|---------|
| **Real-Time Notifications** | Platform events pushed to Discord channels and DMs | "Registration for Valorant Champions Cup closes in 2 hours" |
| **Tournament Operations** | Check-in, score reporting, dispute resolution via bot commands | `/check-in`, `/report-score`, `/dispute` |
| **Team Communication** | Synced team chat between web platform and Discord channels | Message sent on web appears in team's Discord channel |
| **Community Hub** | Game discussions, LFT/LFG boards, content sharing | `#valorant-general`, `#looking-for-team` |
| **Support Channel** | Payment verification help, technical support, FAQ | Private threads for bKash/Nagad screenshot verification |
| **Staff Operations** | Moderation coordination, organizer tools, admin commands | `#staff-ops`, `/ban-sync` |
| **Growth Engine** | Onboarding, events, giveaways, community engagement | Welcome flow → account link → game role → first tournament |

### 1.3 Integration Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DeltaCrown Platform                          │
│                                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │Tournament│  │  Teams/  │  │ Economy  │  │  Notifications   │   │
│  │  Engine  │  │  Orgs    │  │(DeltaCoin│  │     System       │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │              │             │                  │             │
│       └──────────────┴─────────────┴──────────────────┘             │
│                              │                                      │
│                     ┌────────▼────────┐                             │
│                     │  Celery Event   │                             │
│                     │     Bus         │                             │
│                     └────────┬────────┘                             │
│                              │                                      │
│                     ┌────────▼────────┐                             │
│                     │   Discord       │                             │
│                     │   Service Layer │                             │
│                     └────────┬────────┘                             │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   DeltaCrown Sync   │
                    │       Bot           │
                    │  (discord.py / JS)  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Discord API      │
                    │   (Gateway + REST)  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  DeltaCrown Discord │
                    │      Server         │
                    └─────────────────────┘
```

The architecture is **bidirectional**:
- **Platform → Discord:** Celery tasks fire when platform events occur (tournament published, match completed, team created). These tasks call the Discord Service Layer, which routes to the bot or webhooks.
- **Discord → Platform:** Slash commands and button interactions on Discord trigger HTTP calls to the DeltaCrown API (JWT-authenticated via linked accounts). Results flow back to Discord as ephemeral messages, embeds, or thread updates.

### 1.4 Core Objectives

1. **Reduce friction for competitive players** — Check in, report scores, and resolve disputes without leaving the voice call.
2. **Drive platform adoption** — Every Discord user is one `/link` command away from a full DeltaCrown account.
3. **Strengthen team identity** — Teams with Discord channels synced to the platform are more active, more organized, and more competitive.
4. **Enable real-time operations** — Tournament organizers and referees can manage live events through Discord, with instant feedback loops.
5. **Build the largest esports community in South Asia** — The Discord server becomes the home for competitive gamers across Bangladesh, India, Pakistan, Nepal, and beyond.

---

## Part 2: Server Identity & Branding

### 2.1 Server Name & Vanity URL

| Property | Value |
|----------|-------|
| **Server Name** | DeltaCrown Esports |
| **Vanity URL** | `discord.gg/deltacrown` |
| **Server Description** | The official Discord community for DeltaCrown — South Asia's premier esports tournament platform. Compete, connect, and rise. |
| **Server Category** | Gaming > Esports |

### 2.2 Visual Identity

All visual assets should align with the DeltaCrown brand identity:

- **Primary Color:** `#FFD700` (Crown Gold)
- **Secondary Color:** `#1A1A2E` (Deep Navy / Dark Background)
- **Accent Color:** `#E94560` (Alert Red — used for live events, urgent notices)
- **Tertiary Color:** `#0F3460` (Cool Blue — used for informational embeds)
- **Success Color:** `#00D26A` (Victory Green — match wins, approved actions)
- **Text on Dark:** `#E0E0E0` (Soft White)

**Server Icon:** The DeltaCrown crown logo on a `#1A1A2E` circular background with a subtle gold gradient edge. Dimensions: 512×512 PNG.

**Server Banner:** A wide banner (960×540) featuring the DeltaCrown tagline *"From the Delta to the Crown"* over a gradient from deep navy to crown gold, with silhouettes of competitive players.

### 2.3 Server Banner & Splash Screen

The invite splash screen (available at Community Level 1) should feature:
- The DeltaCrown logo, centered
- Server member count and online count
- A one-line call-to-action: *"Join 10,000+ competitive gamers across South Asia"*

### 2.4 Naming Conventions

Channels and categories follow a strict naming scheme for scannability:

| Element | Convention | Example |
|---------|-----------|---------|
| **Category** | `UPPER CASE` with emoji prefix | `🏆 TOURNAMENTS` |
| **Text Channel** | `lower-kebab-case` with context emoji | `📢┃announcements` |
| **Voice Channel** | `Title Case` with emoji | `🎙️ Match Room #1` |
| **Stage Channel** | `Title Case` with emoji | `🎤 Community Town Hall` |
| **Forum Channel** | `lower-kebab-case` with emoji | `💬┃game-strategy` |
| **Separator** | The pipe character `┃` (U+2503) | `📢┃announcements` |

### 2.5 Emoji & Sticker System

**Custom Emoji Set (60+ planned):**

| Category | Emojis |
|----------|--------|
| **Games** | `:valorant:` `:pubgm:` `:mlbb:` `:freefire:` `:codm:` `:cs2:` `:dota2:` `:rocketleague:` `:r6siege:` `:eafc:` `:efootball:` |
| **Ranks** | `:bronze:` `:silver:` `:gold:` `:platinum:` `:diamond:` `:master:` `:grandmaster:` `:champion:` |
| **Platform** | `:deltacrown:` `:deltacoin:` `:crown:` `:trophy:` `:verified:` `:live:` `:registration_open:` |
| **Reactions** | `:gg:` `:ez:` `:clutch:` `:ace:` `:mvp:` `:pog:` `:sadge:` `:copium:` |
| **Status** | `:check_green:` `:cross_red:` `:pending:` `:dispute:` `:live_red:` |
| **Teams** | `:team_captain:` `:team_coach:` `:team_analyst:` `:team_owner:` |
| **Payment** | `:bkash:` `:nagad:` `:rocket:` `:bank:` |

**Custom Stickers (15+ planned):**
- "GG WP" crown celebration
- "Tournament Winner" confetti crown
- "DeltaCoin Earned" coin animation
- "Match Day" countdown clock
- "Looking for Team" radar sweep
- "Dispute Filed" referee whistle
- Game-specific victory stickers for each supported title

---

## Part 3: User Personas & Experience Design

### 3.1 Persona A — The Community Member

**Who:** A casual gamer who loves esports but may not compete regularly. They follow tournaments, watch streams, and hang out in game-specific channels. Maybe they're a student in Dhaka who plays Valorant after class and dreams of going pro one day.

**Discord Experience:**
1. Joins via `discord.gg/deltacrown`
2. Lands in `#welcome` — greeted by a rich embed explaining the server
3. Reacts to game role selection in `#pick-your-games` (selects Valorant and PUBG Mobile)
4. Gains `@Valorant` and `@PUBG Mobile` roles → game-specific channels unlock
5. Browses `#valorant-general`, `#looking-for-team`, `#tournament-feed`
6. Types `/link` to connect their DeltaCrown account → gains `@Linked` role → profile stats visible
7. Browses community content, reacts, participates in events
8. Eventually sees a tournament announcement, clicks the registration link, and becomes Persona B

**Key Channels:** `#welcome`, `#rules`, `#pick-your-games`, `#general-chat`, `#valorant-general`, `#content-hub`, `#memes`

### 3.2 Persona B — The Competitive Player

**Who:** An active competitor who enters tournaments regularly. They might be a solo player looking for a team or already part of a roster. They use Discord to check in for matches, communicate with teammates, and track their standings.

**Discord Experience:**
1. Already linked their account (has `@Linked` role)
2. When they register for a tournament on the platform → Celery task fires → bot grants `@Tournament: [Name]` temporary role → tournament channels appear
3. On match day, they use `/check-in [tournament-id]` in the tournament's text channel
4. During the match, they're in a voice channel with teammates
5. After the match, the captain uses `/report-score` to submit results
6. If there's a dispute, a private thread is auto-created with both teams and a referee
7. When the tournament concludes, temporary roles are cleaned up automatically

**Key Channels:** `#tournament-feed`, `#match-lobby`, tournament-specific channels, team voice channels, `#leaderboard-updates`

### 3.3 Persona C — The Team Captain / Manager

**Who:** The leader of a competitive team registered on DeltaCrown. They manage roster, strategy, and tournament logistics. Discord is their command center.

**Discord Experience:**
1. When their team is created on DeltaCrown → bot creates a private team text channel and voice channel (or syncs with existing team Discord via webhook)
2. Team channel shows synced messages from DeltaCrown's web team chat (`DiscordChatMessage` model — bidirectional)
3. Uses `/roster` to view current team roster and status
4. Posts in `#looking-for-players` to recruit (synced with Smart Recruitment on the platform)
5. On tournament day, coordinates check-in, manages substitutions via `/emergency-sub`
6. Receives DM notifications for team invites, join requests, and match schedules

**Key Channels:** Private team channel, `#looking-for-players`, `#team-announcements`, tournament channels, team voice channels

### 3.4 Persona D — The Tournament Organizer

**Who:** A verified tournament organizer who uses the Tournament Operations Center (TOC) on the web but relies on Discord for real-time communication during live events.

**Discord Experience:**
1. Has `@Organizer` role (synced from platform when approved)
2. Accesses `#organizer-hub` — a private channel for all verified organizers
3. When they publish a tournament → bot posts a rich embed in `#tournament-announcements` with game role ping
4. During the event, monitors `#match-ops` for score submissions and disputes
5. Uses `/resolve-dispute [dispute-id] [ruling]` to resolve disputes from Discord
6. After the tournament, reviews auto-generated summary stats posted by the bot
7. Can use `/announce [tournament-id] [message]` to broadcast to tournament participants

**Key Channels:** `#organizer-hub`, `#match-ops`, `#tournament-announcements`, `#staff-chat`, tournament-specific channels

### 3.5 Persona E — The Content Creator

**Who:** A streamer, clip maker, or esports journalist who covers DeltaCrown tournaments and community events.

**Discord Experience:**
1. Has `@Content Creator` role (applied for and approved, or synced from team role)
2. Accesses `#content-hub` for sharing streams, highlights, and articles
3. Gets pinged for live tournament streams via `@Content Creator` role mentions
4. Can post in `#media-showcase` to share clips and get community engagement
5. Uses `#collaboration` channel to find co-streamers and content partners
6. Has access to tournament media kits, brand assets, and sponsor materials

**Key Channels:** `#content-hub`, `#media-showcase`, `#collaboration`, `#stream-notifications`

### 3.6 Persona F — The Super Admin

**Who:** A DeltaCrown staff member with full administrative authority. They oversee the server, manage the bot, handle escalations, and ensure operational integrity.

**Discord Experience:**
1. Has `@Super Admin` role with full administrator permissions
2. Accesses all staff channels: `#admin-ops`, `#mod-queue`, `#server-logs`, `#bot-status`
3. Can use administrator bot commands: `/ban-sync`, `/config`, `/maintenance`
4. Monitors `#log┃moderation` for auto-mod actions and manual mod logs
5. Reviews escalated reports from `#mod-queue`
6. Manages server configuration: roles, channels, permissions, bot settings
7. Can trigger platform-wide announcements via `/platform-announce`

**Key Channels:** All channels, `#admin-ops`, `#mod-queue`, `#server-logs`, `#bot-status`, all log channels

---

## Part 4: Role Hierarchy & Permission Architecture

### 4.1 Role Tier System

Roles are organized into **six tiers**, ordered from highest to lowest in Discord's role hierarchy:

```
Tier 0: System Roles (Bot-managed, never manually assigned)
  └── @DeltaCrown Bot
  └── @Server Booster

Tier 1: Administration (Full server control)
  └── @Super Admin
  └── @Admin

Tier 2: Staff (Operational permissions)
  └── @Organizer
  └── @Referee
  └── @Moderator

Tier 3: Community (Earned/applied roles)
  └── @Content Creator
  └── @Verified (KYC verified)
  └── @Linked (Account linked)

Tier 4: Game Roles (Self-assigned via reaction)
  └── @Valorant, @PUBG Mobile, @MLBB, @Free Fire, @CODM,
      @CS2, @Dota 2, @Rocket League, @R6 Siege, @EA FC, @eFootball

Tier 5: Temporary Event Roles (Auto-granted, auto-removed)
  └── @Tournament: [Name]
  └── @Match: [ID]
  └── @Team: [Name]

Tier 6: Base
  └── @everyone
```

### 4.2 Complete Role List

| Role | Color | Hoisted | Mentionable | Auto-Assign | Source |
|------|-------|---------|-------------|-------------|--------|
| `@DeltaCrown Bot` | `#FFD700` | Yes | No | — | Bot join |
| `@Super Admin` | `#FF0000` | Yes | No | Manual | Staff |
| `@Admin` | `#FF4500` | Yes | No | Manual | Staff |
| `@Organizer` | `#9B59B6` | Yes | Yes | Synced | Platform TOC approval |
| `@Referee` | `#3498DB` | Yes | Yes | Synced | Platform staff assignment |
| `@Moderator` | `#2ECC71` | Yes | Yes | Manual + synced | Staff selection |
| `@Content Creator` | `#E91E63` | No | Yes | Application | Approved |
| `@Verified` | `#00D26A` | No | No | Synced | Platform KYC |
| `@Linked` | `#7289DA` | No | No | Synced | `/link` command |
| `@Server Booster` | `#F47FFF` | Yes | No | Auto | Discord Nitro |
| `@Valorant` | `#FD4556` | No | Yes | Reaction | `#pick-your-games` |
| `@PUBG Mobile` | `#F2A900` | No | Yes | Reaction | `#pick-your-games` |
| `@MLBB` | `#0096FF` | No | Yes | Reaction | `#pick-your-games` |
| `@Free Fire` | `#FF6B00` | No | Yes | Reaction | `#pick-your-games` |
| `@CODM` | `#4CAF50` | No | Yes | Reaction | `#pick-your-games` |
| `@CS2` | `#DE9B35` | No | Yes | Reaction | `#pick-your-games` |
| `@Dota 2` | `#C23C2A` | No | Yes | Reaction | `#pick-your-games` |
| `@Rocket League` | `#0078F2` | No | Yes | Reaction | `#pick-your-games` |
| `@R6 Siege` | `#8B8B8B` | No | Yes | Reaction | `#pick-your-games` |
| `@EA FC` | `#1B5E20` | No | Yes | Reaction | `#pick-your-games` |
| `@eFootball` | `#002171` | No | Yes | Reaction | `#pick-your-games` |
| `@Tournament: [Name]` | `#FFD700` | No | Yes | Synced | Registration |
| `@Team: [Name]` | Varies | No | No | Synced | Team membership |

### 4.3 Permission Matrix

| Permission | Super Admin | Admin | Organizer | Referee | Moderator | Content Creator | Linked | Everyone |
|-----------|:-----------:|:-----:|:---------:|:-------:|:---------:|:---------------:|:------:|:--------:|
| Administrator | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Manage Server | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Manage Roles | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Manage Channels | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Kick Members | ✅ | ✅ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| Ban Members | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Manage Messages | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Manage Threads | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Mention @everyone | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Send Messages | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅* |
| Embed Links | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Attach Files | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| Use Slash Commands | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Use Voice | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Move Members (VC) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Mute Members (VC) | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |

> *`@everyone` can send messages only in designated open channels (e.g., `#general-chat`, `#introductions`). Most channels require at minimum the `@Linked` role.

### 4.4 Auto-Synced Roles from DeltaCrown Platform

These roles are automatically managed by the DeltaCrown Sync Bot based on platform events:

| Platform Event | Discord Action |
|---------------|---------------|
| User links Discord account via OAuth2 | Grant `@Linked` role |
| User completes KYC verification | Grant `@Verified` role |
| User approved as Tournament Organizer | Grant `@Organizer` role |
| User assigned as Referee on platform | Grant `@Referee` role |
| User registers for tournament | Grant `@Tournament: [Name]` role |
| User joins a team | Grant `@Team: [Name]` role |
| Tournament concludes | Remove `@Tournament: [Name]` role |
| User leaves/removed from team | Remove `@Team: [Name]` role |
| User is banned on platform | Discord ban notification sent to admin; optional auto-kick |
| User's organizer status revoked | Remove `@Organizer` role |

---

## Part 5: Server Structure — Complete Channel Blueprint

### 5.1 Design Principles

1. **Progressive Disclosure:** New users see only 6–8 channels. Additional channels unlock as they gain roles.
2. **Hierarchy:** Categories are ordered by importance and frequency of use.
3. **Separation of Concerns:** Community channels, competitive channels, and staff channels are in distinct categories.
4. **Noise Reduction:** Announcement channels are read-only. Discussion channels have slowmode where appropriate.
5. **Accessibility:** Every channel has a clear topic/description. No ambiguous names.

### 5.2 Category & Channel Map

```
╔══════════════════════════════════════════════════════════╗
║                  DELTACROWN ESPORTS                      ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ═══ 👑 WELCOME & INFO ═══                              ║
║  📢┃announcements          [Read-Only]                   ║
║  📋┃rules-and-guidelines   [Read-Only]                   ║
║  🎮┃pick-your-games        [Reaction Roles]              ║
║  🔗┃link-your-account      [Bot Commands Only]           ║
║  📌┃server-guide           [Read-Only]                   ║
║  🗳️┃polls-and-feedback     [Slowmode: 60s]              ║
║                                                          ║
║  ═══ 💬 COMMUNITY ═══                                   ║
║  💬┃general-chat           [Open]                        ║
║  👋┃introductions          [Open, Slowmode: 120s]        ║
║  🎬┃content-hub            [Linked+]                     ║
║  📸┃media-showcase         [Linked+]                     ║
║  😂┃memes-and-banter       [Linked+]                     ║
║  🎤 Community Town Hall    [Stage Channel]               ║
║                                                          ║
║  ═══ 🏆 TOURNAMENTS ═══                                 ║
║  📣┃tournament-announcements  [Read-Only, Bot Posts]     ║
║  📋┃tournament-feed           [Read-Only, Bot Posts]     ║
║  💬┃tournament-discussion     [Linked+]                  ║
║  📊┃brackets-and-results      [Read-Only, Bot Posts]     ║
║  ✅┃check-in                  [Linked+, Bot Commands]    ║
║  🏅┃winners-wall              [Read-Only, Bot Posts]     ║
║                                                          ║
║  ═══ ⚔️ MATCH OPERATIONS ═══                            ║
║  📝┃score-reporting        [Linked+, Bot Commands]       ║
║  ⚠️┃disputes               [Private Threads]            ║
║  🎙️ Match Room #1          [Voice, 10 max]              ║
║  🎙️ Match Room #2          [Voice, 10 max]              ║
║  🎙️ Match Room #3          [Voice, 10 max]              ║
║  🎙️ Match Room #4          [Voice, 10 max]              ║
║  🎙️ Casting Booth          [Voice, 5 max]               ║
║                                                          ║
║  ═══ 🎮 GAME ZONES ═══  (One per supported game)        ║
║  ── VALORANT ──                                          ║
║    💬┃valorant-general      [@Valorant]                  ║
║    🔍┃valorant-lft-lfg      [@Valorant, Forum]           ║
║    📊┃valorant-ranks        [@Valorant]                  ║
║    🎙️ Valorant Voice        [Voice]                     ║
║  ── PUBG MOBILE ──                                       ║
║    💬┃pubgm-general         [@PUBG Mobile]               ║
║    🔍┃pubgm-lft-lfg         [@PUBG Mobile, Forum]        ║
║    📊┃pubgm-ranks           [@PUBG Mobile]               ║
║    🎙️ PUBG Mobile Voice     [Voice]                     ║
║  ── MOBILE LEGENDS ──                                    ║
║    💬┃mlbb-general          [@MLBB]                      ║
║    🔍┃mlbb-lft-lfg          [@MLBB, Forum]               ║
║    🎙️ MLBB Voice            [Voice]                     ║
║  ── FREE FIRE ──                                         ║
║    💬┃freefire-general       [@Free Fire]                 ║
║    🔍┃freefire-lft-lfg       [@Free Fire, Forum]          ║
║    🎙️ Free Fire Voice        [Voice]                     ║
║  ── COD MOBILE ──                                        ║
║    💬┃codm-general           [@CODM]                     ║
║    🔍┃codm-lft-lfg           [@CODM, Forum]              ║
║    🎙️ CODM Voice             [Voice]                     ║
║  ── CS2 ──                                               ║
║    💬┃cs2-general            [@CS2]                       ║
║    🔍┃cs2-lft-lfg            [@CS2, Forum]                ║
║    🎙️ CS2 Voice              [Voice]                     ║
║  ── DOTA 2 ──                                            ║
║    💬┃dota2-general          [@Dota 2]                    ║
║    🔍┃dota2-lft-lfg          [@Dota 2, Forum]             ║
║    🎙️ Dota 2 Voice           [Voice]                     ║
║  ── ROCKET LEAGUE ──                                     ║
║    💬┃rocketleague-general   [@Rocket League]             ║
║    🔍┃rocketleague-lft-lfg   [@Rocket League, Forum]      ║
║    🎙️ Rocket League Voice    [Voice]                     ║
║  ── R6 SIEGE ──                                          ║
║    💬┃r6-general             [@R6 Siege]                  ║
║    🔍┃r6-lft-lfg             [@R6 Siege, Forum]           ║
║    🎙️ R6 Siege Voice         [Voice]                     ║
║  ── EA SPORTS FC ──                                      ║
║    💬┃eafc-general           [@EA FC]                     ║
║    🔍┃eafc-lft-lfg           [@EA FC, Forum]              ║
║    🎙️ EA FC Voice            [Voice]                     ║
║  ── eFOOTBALL ──                                         ║
║    💬┃efootball-general      [@eFootball]                  ║
║    🔍┃efootball-lft-lfg      [@eFootball, Forum]           ║
║    🎙️ eFootball Voice        [Voice]                     ║
║                                                          ║
║  ═══ 👥 TEAMS ═══  (Dynamic, auto-created per team)     ║
║  🔒┃team-[slug]-chat       [Team members only]           ║
║  🎙️ Team [Name] Voice      [Team members only]          ║
║                                                          ║
║  ═══ 🏢 ORGANIZATIONS ═══  (Dynamic, per org)           ║
║  🔒┃org-[slug]-general     [Org members only]            ║
║  🔒┃org-[slug]-management  [Org staff only]              ║
║  🎙️ Org [Name] Voice       [Org members only]           ║
║                                                          ║
║  ═══ 🛡️ STAFF ZONE ═══  (Staff roles only)             ║
║  💼┃staff-chat             [All Staff]                   ║
║  📋┃mod-queue              [Moderator+]                  ║
║  🏟️┃match-ops              [Referee+, Organizer]        ║
║  📣┃organizer-hub          [Organizer+]                  ║
║  🤖┃bot-status             [Admin+]                      ║
║  🔧┃admin-ops              [Admin+]                      ║
║  🎙️ Staff Voice             [All Staff]                  ║
║                                                          ║
║  ═══ 📊 LOGS ═══  (Admin only, read-only bot feeds)     ║
║  📝┃log-moderation         [Auto-mod & manual actions]   ║
║  📝┃log-ops-activity       [Tournament ops, result subs] ║
║  📝┃log-bot-commands       [All slash command usage]     ║
║  📝┃log-role-sync          [Role grant/revoke events]    ║
║  📝┃log-joins-leaves       [Member join/leave tracking]  ║
║                                                          ║
║  ═══ 🎫 SUPPORT ═══                                     ║
║  ❓┃faq                    [Read-Only, synced from web]   ║
║  🎫┃open-a-ticket          [Bot command, creates thread] ║
║  💳┃payment-help           [Private threads]             ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

### 5.3 Channel Descriptions & Rules

**Key channel configurations:**

| Channel | Topic / Description | Slowmode | Special |
|---------|-------------------|----------|---------|
| `📢┃announcements` | Official DeltaCrown announcements. Platform updates, partnerships, major news. | — | Read-only, @everyone ping for major events |
| `📋┃rules-and-guidelines` | Server rules, community guidelines, code of conduct. Read before participating. | — | Read-only, pinned |
| `🎮┃pick-your-games` | React to select your games and unlock game-specific channels! | — | Bot-managed reaction roles |
| `🔗┃link-your-account` | Link your DeltaCrown account with `/link` to unlock full features. | — | Bot commands only, ephemeral responses |
| `💬┃general-chat` | Hang out, talk about anything gaming. Keep it friendly! | 5s | Open to all, auto-mod active |
| `📣┃tournament-announcements` | Auto-posted when tournaments go live. Never miss an event! | — | Read-only, bot posts only |
| `✅┃check-in` | Use `/check-in [tournament-id]` when your match is ready. | — | Bot commands, ephemeral |
| `📝┃score-reporting` | Captains: Use `/report-score` after your match. | — | Bot commands, creates confirmation embeds |
| `⚠️┃disputes` | Disputes auto-create private threads. Do not post in main channel. | — | Private threads, referee access |
| `🏅┃winners-wall` | Celebrating tournament champions! Auto-posted by bot. | — | Read-only, rich embeds |
| `💳┃payment-help` | Need help with bKash/Nagad/Rocket payments? Open a private thread. | — | Private threads, staff respond |

---

## Part 6: DeltaCrown Sync Bot — Technical Architecture

### 6.1 Bot Overview

| Property | Value |
|----------|-------|
| **Name** | DeltaCrown Bot |
| **Avatar** | Crown logo with bot indicator |
| **Status** | `🏆 Watching DeltaCrown tournaments` |
| **Prefix** | Slash commands only (no prefix commands) |
| **Framework** | discord.py (Python) or discord.js (Node.js) — Python preferred for Django ecosystem alignment |
| **Hosting** | Same infrastructure as DeltaCrown (Render, Dockerized) |
| **Database** | Shares PostgreSQL with DeltaCrown (reads user/team/tournament data; writes to discord sync tables) |

**Bot Permissions Required (Integer: 1644971949559):**
- Manage Roles
- Manage Channels
- Kick Members
- Send Messages
- Send Messages in Threads
- Create Public Threads
- Create Private Threads
- Manage Messages
- Manage Threads
- Embed Links
- Attach Files
- Read Message History
- Add Reactions
- Use Slash Commands
- Connect (Voice)
- Speak (Voice)
- Move Members (Voice)

### 6.2 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     DeltaCrown Django                         │
│                                                              │
│  ┌─────────────┐   ┌──────────────┐   ┌─────────────────┐  │
│  │  Tournament  │   │ Organization │   │   Notification   │  │
│  │   Service    │   │   Service    │   │     Service      │  │
│  └──────┬───────┘   └──────┬───────┘   └────────┬────────┘  │
│         │                  │                     │           │
│         └──────────────────┼─────────────────────┘           │
│                            │                                  │
│                   ┌────────▼────────┐                        │
│                   │  Celery Tasks   │                        │
│                   │                 │                        │
│                   │ • send_discord_ │                        │
│                   │   announcement  │                        │
│                   │ • sync_discord_ │                        │
│                   │   role          │                        │
│                   │ • send_discord_ │                        │
│                   │   chat_message  │                        │
│                   │ • validate_bot_ │                        │
│                   │   presence      │                        │
│                   └────────┬────────┘                        │
│                            │                                  │
│                   ┌────────▼────────┐                        │
│                   │ Discord HTTP    │                        │
│                   │ Client (aiohttp)│                        │
│                   └────────┬────────┘                        │
└────────────────────────────┼─────────────────────────────────┘
                             │
                    ┌────────▼────────┐
                    │   Discord API   │
                    │   (REST + WS)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼──────┐  ┌───▼────────┐
     │  Webhooks  │  │  Bot Gateway│  │  OAuth2     │
     │ (one-way   │  │  (bidirect- │  │  (account   │
     │  announce- │  │   ional,    │  │   linking,  │
     │  ments)    │  │ slash cmds) │  │   identity) │
     └────────────┘  └─────────────┘  └────────────┘
```

**Three integration methods, each serving a distinct purpose:**

1. **Webhooks** — Fire-and-forget announcements. Used for tournament publications, match results, leaderboard updates. No bot presence required. Fast, resilient, write-only.

2. **Bot Gateway (WebSocket)** — Full bidirectional communication. Handles slash commands (score reporting, check-in, disputes), reaction-based role assignment, member join/leave events, message bridging for team chat sync. Requires the bot to be online.

3. **OAuth2** — Identity linking. Users authenticate via Discord on the DeltaCrown website, granting the platform their Discord user ID. This ID is stored in the `UserProfile.social_links` or a dedicated `discord_id` field, enabling role sync and DM notifications.

### 6.3 Slash Command Reference

| Command | Description | Permission | Response |
|---------|-------------|-----------|----------|
| `/link` | Link your DeltaCrown account via OAuth2 | Everyone | Ephemeral — opens auth URL, grants `@Linked` on success |
| `/profile [username]` | View a player's DeltaCrown profile summary | @Linked | Embed — avatar, rank, team, recent matches, DeltaCoin balance |
| `/check-in [tournament-id]` | Check in for your upcoming match | @Linked | Ephemeral — confirms check-in, updates platform |
| `/report-score [match-id]` | Submit match results (captain only) | @Linked + Captain | Modal — score input, screenshot upload, confirmation |
| `/dispute [match-id] [reason]` | File a dispute for a match result | @Linked | Creates private thread, notifies referee |
| `/roster [team-slug]` | View a team's current roster | @Linked | Embed — roster list with roles, status, game IDs |
| `/standings [tournament-id]` | View live tournament standings/bracket | Everyone | Embed — bracket image or standings table |
| `/leaderboard [game] [region]` | View top players/teams in a game | Everyone | Embed — top 10 with rank, rating, team |
| `/tournaments [game]` | View upcoming tournaments | Everyone | Embed — list of open/upcoming tournaments with reg links |
| `/balance` | Check your DeltaCoin balance | @Linked | Ephemeral — balance, recent transactions |
| `/lft [game] [role] [rank]` | Post a Looking For Team listing | @Linked | Posts in game's LFT channel, syncs to platform |
| `/lfp [game] [role] [rank]` | Post a Looking For Player listing (captain) | @Linked + Captain | Posts in game's LFT channel, syncs to platform |
| `/emergency-sub [match-id] [player]` | Request emergency substitution | @Linked + Captain | Starts sub request flow on platform |
| `/announce [tournament-id] [message]` | Broadcast to tournament participants | @Organizer | Sends to tournament channel + DMs to registered players |
| `/resolve-dispute [dispute-id] [ruling]` | Resolve an open dispute | @Referee / @Organizer | Updates platform, notifies involved parties |
| `/ban-sync [user] [reason] [duration]` | Sync a platform ban to Discord | @Admin | Applies Discord timeout/ban, logs to audit |
| `/config [setting] [value]` | Configure bot settings | @Super Admin | Updates bot configuration |
| `/maintenance [on/off] [message]` | Toggle maintenance mode | @Super Admin | Posts notice, disables non-essential commands |
| `/stats server` | View server analytics | @Admin | Embed — member count, active users, channel activity |

### 6.4 Event-Driven Workflows

**Workflow 1: Tournament Published → Discord Announcement**

```
1. Organizer clicks "Publish" on Tournament Operations Center (web)
2. Tournament status changes: draft → published
3. Django signal fires → Celery task `send_discord_announcement` queued
4. Task builds rich embed:
   ┌────────────────────────────────────────┐
   │ 🏆 NEW TOURNAMENT                      │
   │                                         │
   │ Valorant Champions Cup — Season 3       │
   │                                         │
   │ 📅 March 15, 2026                       │
   │ 🎮 Valorant • 5v5                       │
   │ 🏟️ Single Elimination                   │
   │ 💰 Prize: ৳50,000 + 500 DeltaCoin      │
   │ 🎟️ Entry: ৳200 per team                │
   │ 📍 Registration closes: March 12        │
   │ 👥 Capacity: 32 teams                   │
   │                                         │
   │ [Register Now] [View Details]           │
   │                                         │
   │ 🏅 Organized by: ProLeague BD          │
   └────────────────────────────────────────┘
5. Embed posted to #tournament-announcements with @Valorant role ping
6. If the tournament is for a specific game, only that game role is pinged
```

**Workflow 2: Match Completed → Result Announcement**

```
1. Both teams confirm match result on platform (or referee confirms)
2. Match status: in_progress → completed
3. Celery task fires → builds result embed
4. Embed posted to #brackets-and-results:
   ┌────────────────────────────────────────┐
   │ ⚔️ MATCH RESULT                        │
   │                                         │
   │ Valorant Champions Cup — Round 2        │
   │                                         │
   │ 🏆 Team Phoenix  2 — 1  Team Dragon 🐉│
   │                                         │
   │ Map 1: Haven    — Phoenix 13-9         │
   │ Map 2: Bind     — Dragon  13-11        │
   │ Map 3: Ascent   — Phoenix 13-7         │
   │                                         │
   │ ⭐ MVP: PlayerX (28 kills, 4 aces)     │
   │                                         │
   │ [View Match Details]                    │
   └────────────────────────────────────────┘
```

**Workflow 3: Registration → Role Assignment**

```
1. Player registers for tournament on website
2. Payment verified (bKash/Nagad/Rocket/bank)
3. Registration confirmed → Celery task `sync_discord_role`
4. Bot grants @Tournament: [Name] role to all team members' Discord accounts
5. Tournament-specific channels become visible to registered teams
6. Ephemeral DM sent: "✅ You're registered for Valorant Champions Cup! Check #match-schedule for your bracket."
```

**Workflow 4: Dispute Filed → Private Thread**

```
1. Player/Captain uses /dispute or files dispute on web
2. Platform creates Dispute record
3. Celery task fires → Bot creates private thread in #disputes:
   Thread name: "Dispute #D-2026-00142 — Team Phoenix vs Team Dragon"
4. Bot pulls in: Both team captains + assigned referee + organizer
5. Bot posts initial embed with match details, both score submissions, timestamp discrepancy
6. Evidence submission via file uploads in thread
7. Referee uses /resolve-dispute → Platform updates → Thread archived
8. Both teams notified of ruling via DM
```

**Workflow 5: Team Created → Channel Provisioning**

```
1. Team created on DeltaCrown platform with Discord integration enabled
2. Celery task → Bot creates:
   a. Private text channel: #team-[slug]-chat (under TEAMS category)
   b. Private voice channel: Team [Name] Voice
3. Bot sets permissions: only team members (via @Team: [Name] role) can access
4. When team members' DeltaCrown accounts are linked, they get the team role
5. Messages in web team chat → Celery → Bot → Discord channel (bidirectional via DiscordChatMessage model)
6. Messages in Discord team channel → Bot → DeltaCrown API → Web team chat
```

**Workflow 6: Player Joins Team → Cross-Platform Sync**

```
1. Player accepts team invite on DeltaCrown
2. TeamMembership created with role (Player, Substitute, Coach, etc.)
3. Celery task fires:
   a. Grant @Team: [Name] Discord role → team channels visible
   b. If Captain/Manager → grant additional team channel permissions (pin, manage)
   c. Bot posts welcome message in team channel:
      "👋 Welcome @PlayerName to Team Phoenix as Player!"
4. If player leaves team → reverse all of the above
```

### 6.5 Webhook Integration

For high-volume, one-way announcements where the bot's bidirectional capabilities aren't needed, DeltaCrown uses Discord webhooks:

| Webhook | Channel | Triggers |
|---------|---------|----------|
| `tournament-announcements` | `#tournament-announcements` | Tournament published, registration open/close, bracket ready |
| `match-results` | `#brackets-and-results` | Match completed, bracket updated |
| `winners` | `#winners-wall` | Tournament completed, champion crowned |
| `leaderboard-updates` | Game-specific `#ranks` channels | Weekly ranking snapshot published |
| `platform-updates` | `#announcements` | Platform feature releases, maintenance notices |

**Webhook payload structure (example):**

```json
{
  "username": "DeltaCrown",
  "avatar_url": "https://deltacrown.gg/static/img/bot-avatar.png",
  "embeds": [{
    "title": "🏆 Tournament Winner!",
    "description": "**Team Phoenix** has won the Valorant Champions Cup — Season 3!",
    "color": 16766720,
    "thumbnail": {"url": "https://deltacrown.gg/media/teams/phoenix/logo.png"},
    "fields": [
      {"name": "🥇 Champion", "value": "Team Phoenix", "inline": true},
      {"name": "🥈 Runner-Up", "value": "Team Dragon", "inline": true},
      {"name": "💰 Prize", "value": "৳50,000 + 500 DC", "inline": true},
      {"name": "🏟️ Format", "value": "Single Elimination (32 teams)", "inline": true},
      {"name": "⭐ Tournament MVP", "value": "PlayerX", "inline": true},
      {"name": "📊 Total Matches", "value": "31", "inline": true}
    ],
    "footer": {"text": "DeltaCrown Esports • From the Delta to the Crown"},
    "timestamp": "2026-03-15T18:00:00.000Z"
  }]
}
```

### 6.6 OAuth2 Account Linking

**Flow:**

```
1. User types /link in Discord
2. Bot responds with ephemeral message containing a unique auth URL:
   https://deltacrown.gg/account/discord/link?state=<unique-token>
3. User clicks link → redirected to DeltaCrown login (if not already logged in)
4. After login → Discord OAuth2 consent screen:
   "DeltaCrown wants to access your Discord account"
   Scopes: identify, guilds.members.read
5. User approves → DeltaCrown receives Discord user ID, username, avatar
6. Platform stores Discord ID in UserProfile
7. Callback confirms to bot → Bot grants @Linked role
8. Bot sends DM: "✅ Your DeltaCrown account (DC-26-001234) is now linked!
   You can now use all platform commands on Discord."
```

**Technical implementation (Django side):**

The existing DeltaCrown codebase already has the foundation:
- `DISCORD_CLIENT_ID` and `DISCORD_BOT_TOKEN` in settings
- `SocialLink` model in `user_profile` for storing Discord connection
- `NotificationPreference` model with `opt_out_discord` flag
- `sync_discord_role` Celery task in `organizations/tasks/discord_sync.py`

What needs to be added:
- OAuth2 callback view at `/account/discord/callback/`
- Discord ID field on `UserProfile` (or use existing `SocialLink` with platform="discord")
- Token exchange logic (authorization code → access token → user info)
- State parameter validation for CSRF protection

---

## Part 7: Tournament Operations via Discord

### 7.1 Tournament Lifecycle on Discord

Each tournament that touches Discord follows this lifecycle:

```
PUBLISHED          → Rich embed posted in #tournament-announcements
                     Game role pinged. Registration link included.

REGISTRATION OPEN  → Reminder embeds at: 7 days, 3 days, 1 day, 6 hours before close
                     Participant count updates on the embed (edited in place)

REGISTRATION CLOSED → Final embed edit: "Registration closed. X teams confirmed."
                      Bracket preview posted to #brackets-and-results

BRACKET READY      → Full bracket image posted
                     Match schedule posted with dates/times
                     Temporary voice channels created for match rooms (if needed)

LIVE               → Status update: "🔴 LIVE — [Tournament Name]"
                     Match results flow into #brackets-and-results in real-time
                     Check-in reminders sent via DM to upcoming match participants

COMPLETED          → Champion announcement in #winners-wall
                     Final bracket posted
                     Summary statistics embed
                     Temporary tournament roles cleaned up (48hr delay for post-event discussion)
                     Temporary channels archived

CANCELLED          → Notification to all registered participants via DM
                     Refund information included
                     Tournament role removed immediately
```

### 7.2 Match Day Operations

On match day, Discord becomes the operational command center:

**For Players:**
1. Receive DM reminder 30 minutes before match
2. Join designated voice channel for their match
3. Use `/check-in` in `#check-in` channel when ready
4. Play the match
5. Captain uses `/report-score` to submit results
6. If score disputes → `/dispute` creates private resolution thread

**For Referees:**
1. View assigned matches in `#match-ops`
2. Join match voice channels to observe if needed
3. Receive alerts for score submission mismatches
4. Resolve disputes via `/resolve-dispute`
5. Log notes via `/match-note [match-id] [note]`

**For Organizers:**
1. Monitor `#match-ops` for all tournament activity
2. View real-time tournament status via `/tournament-status [id]`
3. Broadcast messages via `/announce`
4. Handle emergency substitutions
5. Approve/reject manual payment verifications in `#payment-help` threads

### 7.3 Check-In System

```
/check-in [tournament-id]

Flow:
1. Bot verifies user is registered for the tournament
2. Bot checks if check-in window is open (configurable: 30min, 15min, etc.)
3. If valid → marks player/team as checked in on platform
4. Responds: "✅ Team Phoenix checked in for Valorant Champions Cup — Match #7
              Opponent: Team Dragon | Scheduled: 3:00 PM BST
              Join 🎙️ Match Room #3 when ready."
5. If check-in window expired → "❌ Check-in window has closed."
6. If already checked in → "ℹ️ You're already checked in."
7. When both teams check in → bot posts in #match-ops:
   "⚔️ Match #7 ready: Team Phoenix vs Team Dragon — Match Room #3"
```

### 7.4 Score Reporting

```
/report-score [match-id]

Flow:
1. Bot verifies user is a team captain for this match
2. Opens a Discord modal with fields:
   - Your team's score (number input)
   - Opponent's score (number input)
   - Screenshot upload URL (optional, or upload in thread)
   - Notes (optional text)
3. On submit → creates MatchResultSubmission on platform via API
4. Bot posts in match thread:
   "📊 Score submitted by Team Phoenix (Captain: @PlayerX):
    Phoenix 2 — 1 Dragon
    Awaiting confirmation from Team Dragon..."
5. Bot DMs Team Dragon captain:
   "📊 Team Phoenix reported: Phoenix 2 — 1 Dragon
    Reply to confirm or dispute. /report-score [match-id] to submit your version."
6. If both submissions match → Match automatically confirmed
   "✅ Match #7 confirmed: Team Phoenix 2 — 1 Team Dragon"
7. If submissions conflict → Auto-dispute triggered (Workflow 4)
```

### 7.5 Dispute Resolution

```
/dispute [match-id] [reason]

Flow:
1. Bot creates private thread: "Dispute #D-2026-XXXXX — [Team A] vs [Team B]"
2. Pulls in: Both captains, assigned referee, tournament organizer
3. Initial embed shows:
   - Match details (tournament, round, scheduled time)
   - Team A's score submission + timestamp
   - Team B's score submission + timestamp (if different)
   - Reason for dispute
4. Participants upload evidence (screenshots, clips) in thread
5. Referee reviews evidence
6. /resolve-dispute [dispute-id] [winner] [score] [notes]
7. Platform updates match result
8. Both teams notified via DM:
   "⚖️ Dispute #D-2026-XXXXX resolved: Team Phoenix wins 2-1.
    Ruling: [Referee's notes]
    This decision is final and logged in the audit trail."
9. Thread archived (read-only)
```

### 7.6 Prize Distribution Announcements

When a tournament concludes and prizes are distributed:

```
┌────────────────────────────────────────────────────────┐
│ 🎉 TOURNAMENT COMPLETE                                 │
│                                                         │
│ Valorant Champions Cup — Season 3                       │
│                                                         │
│ 🥇 1st Place: Team Phoenix                             │
│    Prize: ৳30,000 + 300 DeltaCoin + Gold Trophy Badge  │
│                                                         │
│ 🥈 2nd Place: Team Dragon                              │
│    Prize: ৳15,000 + 150 DeltaCoin + Silver Trophy Badge│
│                                                         │
│ 🥉 3rd Place: Team Falcon                              │
│    Prize: ৳5,000 + 50 DeltaCoin + Bronze Trophy Badge  │
│                                                         │
│ 📊 Tournament Stats:                                   │
│    Total Teams: 32 | Total Matches: 31                  │
│    Total Maps Played: 87 | Average Map Score: 13-9      │
│    Most Kills: PlayerX (287) | Most Aces: PlayerY (12)  │
│                                                         │
│ 💰 Prize Distribution Status:                          │
│    Processing via bKash/Nagad within 48 hours            │
│    DeltaCoin prizes credited instantly                   │
│                                                         │
│ [View Full Bracket] [View Certificates] [Full Stats]   │
│                                                         │
│ 🏅 Thank you to all 32 teams for competing!            │
│ 🎤 Next tournament: March 29 — PUBG Mobile Open        │
└────────────────────────────────────────────────────────┘
```

---

## Part 8: Team & Organization Discord Integration

### 8.1 Team Channel Ecosystem

Every team on DeltaCrown with Discord integration enabled gets:

**Auto-Created Channels:**
- `#team-[slug]-chat` — Private text channel, synced with web team chat
- `🎙️ Team [Name] Voice` — Private voice channel for practice and matches

**Channel Permissions:**
| Role in Team | Text Permissions | Voice Permissions |
|-------------|-----------------|-------------------|
| Owner | Full (manage, pin, delete) | Full (move, mute, deafen) |
| General Manager | Full | Full |
| Team Manager | Read, write, pin | Connect, speak, move |
| Head Coach | Read, write, pin | Connect, speak |
| Player | Read, write | Connect, speak |
| Substitute | Read, write | Connect, speak |
| Analyst | Read, write | Connect, listen (muted by default) |
| Content Creator | Read only | Connect, listen |

**Dynamic Channel Features:**
- When a team has an upcoming match → bot pins the match schedule in the team channel
- When a match goes live → bot creates a temporary strategy sub-thread
- When a new member joins → bot posts a welcome embed with the member's role and stats
- When a member leaves/is removed → bot posts a departure notice (for roster tracking)

### 8.2 Organization Hub Channels

Organizations (parent entities of teams) get additional channels:

- `#org-[slug]-general` — Cross-team communication for the organization
- `#org-[slug]-management` — Management-only (Owner, GM, Managers)
- `🎙️ Org [Name] Voice` — Organization-wide voice

**Use Case:** An organization like "Phoenix Esports" might have teams across Valorant, PUBG Mobile, and MLBB. The org channels let management coordinate across all three teams, share sponsor updates, and make org-wide announcements — while each team retains its own private channels.

### 8.3 Bi-Directional Chat Sync

This is one of DeltaCrown's most powerful integrations, already scaffolded in the codebase via the `DiscordChatMessage` model:

**Web → Discord:**
```
1. Player sends message in team chat on DeltaCrown website
2. Message stored in DiscordChatMessage (direction="outbound")
3. Celery task send_discord_chat_message fires
4. Bot posts the message in the team's Discord channel:
   [PlayerX | Team Phoenix] Hey team, practice at 8 PM tonight?
5. Message includes sender's avatar, name, and team badge
```

**Discord → Web:**
```
1. Player sends message in #team-phoenix-chat on Discord
2. Bot's on_message handler captures it
3. Bot calls DeltaCrown API: POST /api/vnext/teams/{slug}/chat/
4. Message stored in DiscordChatMessage (direction="inbound")
5. Appears in web team chat in real-time (via WebSocket/SSE)
6. Message shows Discord icon to indicate it came from Discord
```

**Supported content in sync:**
- Text messages (with markdown)
- @mentions (translated between Discord usernames and DeltaCrown usernames)
- File attachments (images, PDFs) — stored in DeltaCrown CDN, link posted
- Emoji reactions (basic set, custom emoji mapped to text)
- Reply threading (best-effort mapping)

### 8.4 Recruitment via Discord

DeltaCrown's Smart Recruitment system extends to Discord:

**Looking for Team (LFT) — Player posts:**
```
/lft valorant duelist diamond

Bot posts in #valorant-lft-lfg:
┌────────────────────────────────────────┐
│ 🔍 LOOKING FOR TEAM                    │
│                                         │
│ 👤 PlayerX (DC-26-001234)              │
│ 🎮 Valorant — Duelist                  │
│ 📊 Rank: Diamond 2 | SR: 1,850        │
│ 🌍 Region: South Asia                  │
│ ⏰ Available: Evenings BST             │
│                                         │
│ "Aggressive duelist main, 2 years comp │
│  experience. Looking for a serious team │
│  for upcoming DeltaCrown tournaments."  │
│                                         │
│ [View Profile] [Message on DeltaCrown] │
└────────────────────────────────────────┘

Also synced to DeltaCrown's web LFT board.
```

**Looking for Players (LFP) — Captain posts:**
```
/lfp valorant sentinel platinum+

Bot posts in #valorant-lft-lfg:
┌────────────────────────────────────────┐
│ 📣 TEAM RECRUITING                     │
│                                         │
│ 🏟️ Team Phoenix (verified)             │
│ 🎮 Valorant — Need: Sentinel           │
│ 📊 Required: Platinum+ | SR: 1,500+   │
│ 🌍 Region: Bangladesh                  │
│ 📅 Tryouts: March 10, 8 PM BST        │
│                                         │
│ "Top 8 team in DeltaCrown Season 2.    │
│  Looking for a Sentinel main. Serious  │
│  inquiries only."                       │
│                                         │
│ [Apply on DeltaCrown] [View Team]      │
└────────────────────────────────────────┘

Also synced to DeltaCrown's Smart Recruitment system.
```

---

## Part 9: Community & Engagement Systems

### 9.1 Onboarding Flow

The first 5 minutes on the DeltaCrown Discord server are designed to convert visitors into linked, engaged community members:

```
Step 1: ARRIVAL
├── User joins server
├── Bot sends welcome DM:
│   "👋 Welcome to DeltaCrown Esports!
│    Here's how to get started:
│    1️⃣ Read the rules in #rules-and-guidelines
│    2️⃣ Pick your games in #pick-your-games
│    3️⃣ Link your account with /link in #link-your-account
│    4️⃣ Introduce yourself in #introductions
│    Happy competing! 🏆"
├── Bot posts in #log-joins-leaves:
│   "[JOIN] UserName#1234 — Account age: 2 years"
│
Step 2: GAME SELECTION (within minutes)
├── User visits #pick-your-games
├── Reacts with game emojis: 🎯 (Valorant), 🔫 (PUBG Mobile), etc.
├── Bot grants game roles immediately
├── Game-specific channels appear in sidebar
│
Step 3: ACCOUNT LINKING (within first session)
├── User types /link in #link-your-account
├── OAuth2 flow → DeltaCrown account connected
├── @Linked role granted → more channels visible
├── Profile stats now accessible via /profile
│
Step 4: COMMUNITY INTEGRATION (first week)
├── Posts in #introductions (guided by template pinned message)
├── Joins game-specific discussions
├── Follows #tournament-announcements
├── Considers first tournament registration
```

### 9.2 DeltaCoin Economy on Discord

DeltaCoin, DeltaCrown's internal utility currency, has a Discord presence:

**Earning DeltaCoin via Discord:**
| Activity | Reward | Frequency |
|----------|--------|-----------|
| Daily server activity (5+ messages) | 5 DC | Daily |
| Weekly engagement streak (7 consecutive days active) | 25 DC | Weekly |
| Winning community events/trivia | 10–100 DC | Per event |
| Content creation (approved highlight in #content-hub) | 10 DC | Per post |
| Helping others in #support channels | 5 DC | Per verified help |
| Server boost | 50 DC/month | Monthly |

**Checking Balance:**
```
/balance

Ephemeral response:
┌────────────────────────────────┐
│ 💰 DeltaCoin Balance            │
│                                 │
│ 👤 PlayerX (DC-26-001234)      │
│ 💎 Balance: 1,250 DC           │
│ 📈 This Month: +150 DC         │
│ 📊 Lifetime: 3,400 DC          │
│                                 │
│ Recent:                         │
│ +50 DC — Tournament prize       │
│ +25 DC — Weekly streak          │
│ -200 DC — Entry fee             │
│                                 │
│ [View Full History on Web]      │
└────────────────────────────────┘
```

### 9.3 Leaderboard & Ranking Feeds

Game-specific ranking channels receive automated weekly updates:

```
Posted every Monday at 12:00 PM BST in #valorant-ranks:

┌────────────────────────────────────────┐
│ 📊 VALORANT RANKINGS — Week 12, 2026   │
│                                         │
│ 🏆 TOP PLAYERS                          │
│ 1. ⬆️2  PlayerX    — 2,450 LP (Master) │
│ 2. ━━   PlayerY    — 2,380 LP (Master) │
│ 3. ⬇️1  PlayerZ    — 2,290 LP (Diamond)│
│ 4. ⬆️3  PlayerA    — 2,210 LP (Diamond)│
│ 5. NEW  PlayerB    — 2,180 LP (Diamond)│
│                                         │
│ 🏟️ TOP TEAMS                           │
│ 1. ━━   Team Phoenix   — 4,820 CP      │
│ 2. ⬆️1  Team Dragon    — 4,650 CP      │
│ 3. ⬇️1  Team Falcon    — 4,590 CP      │
│                                         │
│ [Full Leaderboard on DeltaCrown]        │
└────────────────────────────────────────┘
```

### 9.4 Content & Media Channels

| Channel | Purpose | Rules |
|---------|---------|-------|
| `#content-hub` | Share streams, YouTube videos, articles, guides | Must be DeltaCrown-related or esports content. Self-promotion allowed with context. Slowmode 60s. |
| `#media-showcase` | Share clips, screenshots, fan art, memes | Esports/gaming content. Credit original creators. Slowmode 30s. |
| `#memes-and-banter` | Casual memes and jokes | Keep it clean. No hate speech. Auto-mod active. |
| `🎤 Community Town Hall` | Stage channel for AMAs, community discussions, announcements | Scheduled events. Moderated stage. |

### 9.5 Game-Specific Communities

Each of the 11 supported games has a dedicated mini-community within the server:

**Per-game channel set:**
- `💬┃[game]-general` — General discussion about the game
- `🔍┃[game]-lft-lfg` — Forum channel for LFT/LFG/recruitment posts
- `📊┃[game]-ranks` — Auto-posted leaderboard updates (read-only)  
- `🎙️ [Game] Voice` — Drop-in voice channel for the game community

**Game-specific channels are gated by game roles.** A player who only plays Valorant and PUBG Mobile will only see those two game zones, keeping the server clean and focused.

**Forum channel tags for LFT/LFG:**
- `LFT` (Looking for Team)
- `LFP` (Looking for Player)
- `Scrim Request`
- `Tournament Party`
- `Casual Play`

### 9.6 Events & Activations

Regular community events keep the server active and growing:

| Event | Frequency | Description | Rewards |
|-------|-----------|-------------|---------|
| **Trivia Night** | Weekly (Friday 9 PM BST) | Esports/gaming trivia in voice + text | 10–50 DC |
| **Clip of the Week** | Weekly | Community votes on best gameplay clip | 25 DC + Featured role |
| **Community Tournament** | Bi-weekly | Casual tournaments organized via Discord | 50–200 DC + bragging rights |
| **AMA Sessions** | Monthly | Pro players, organizers, or staff on stage | — |
| **Prediction League** | Per tournament | Predict match outcomes for DC rewards | 5–100 DC |
| **Game Night** | Weekly (Saturday) | Casual custom games across different titles | Community points |
| **Meme Contest** | Monthly | Best DeltaCrown meme wins | 50 DC + Custom role |
| **Recruitment Drive** | Quarterly | Organized team-finding events | — |

---

## Part 10: Moderation & Safety

### 10.1 Auto-Moderation Rules

Discord's built-in AutoMod + DeltaCrown Bot custom rules:

**Discord AutoMod (native):**

| Rule | Action | Details |
|------|--------|---------|
| Profanity filter | Block message + alert moderators | Custom word list: slurs, harassment terms (English + Bangla) |
| Spam filter | Block + timeout 5 min | Repeated messages (5+ identical in 10s) |
| Mention spam | Block + timeout 10 min | 5+ unique mentions in one message |
| Link filter | Block in specific channels | Only allow links in #content-hub, #media-showcase, game forums |
| Invite filter | Block everywhere except #introductions | Prevent advertising other servers |

**DeltaCrown Bot Custom Rules:**

| Rule | Action | Details |
|------|--------|---------|
| New account gate | Restrict to #welcome, #rules only | Accounts < 7 days old cannot post in most channels |
| Raid detection | Auto-lockdown | 10+ joins in 60 seconds triggers lockdown mode |
| Scam detection | Delete + warn + log | Known scam patterns (fake giveaways, phishing links) |
| NSFW detection | Delete + warn + escalate | Image scanning via Discord's built-in NSFW filter |
| Cross-platform check | Alert moderators | If user is banned on DeltaCrown platform, flag for review |

### 10.2 Staff Moderation Workflow

```
INCIDENT DETECTED
│
├── Auto-mod catches it → Message blocked/deleted → Logged to #log-moderation
│   └── If repeat offense → Auto-escalate to #mod-queue
│
├── User reports via right-click → Report modal
│   └── Report appears in #mod-queue with context
│
├── Staff observes violation → Manual action
│   └── Staff uses Discord moderation tools or bot commands
│
▼
MOD QUEUE REVIEW (#mod-queue)
│
├── Moderator reviews report
├── Checks user history (platform + Discord)
├── Takes action:
│   ├── Dismiss (false positive) → Log
│   ├── Warn (DM + log)
│   ├── Mute/Timeout (1hr / 24hr / 7d)
│   ├── Kick
│   └── Ban → Escalate to Admin for platform-wide ban consideration
│
▼
ACTION LOGGED
├── #log-moderation ← All actions recorded
├── Platform ModerationSanction ← Cross-platform sync
└── User notified via DM ← Reason + duration + appeal info
```

### 10.3 Escalation Procedures

| Severity | Examples | Handler | Action |
|----------|---------|---------|--------|
| **Low** | Minor spam, off-topic messages | Moderator | Verbal warning → timeout |
| **Medium** | Harassment, repeated rule violations | Moderator + Admin notification | Timeout → kick → ban consideration |
| **High** | Hate speech, threats, doxxing, CSAM | Admin immediate response | Instant ban + platform ban + Discord Trust & Safety report |
| **Critical** | Raid, coordinated attack, security breach | Super Admin | Server lockdown + incident response + Discord report |

### 10.4 Sanctions & Cross-Platform Enforcement

DeltaCrown enforces sanctions consistently across the web platform and Discord:

**Platform → Discord:**
- When a user is banned on DeltaCrown → Celery task → Bot DMs user ban notice → Auto-kick from server (or flag for admin review)
- When a user is muted for tournament misconduct → Bot applies timeout in tournament channels

**Discord → Platform:**
- When a user is banned on Discord → Alert in admin dashboard → Admin reviews for platform-level action
- Persistent Discord violations can affect a user's **Reputation Score** on DeltaCrown

**The `ModerationSanction` model supports:**
- `scope`: global, tournament-specific, or channel-specific
- `sanction_type`: ban, suspend, mute, restrict
- `starts_at` / `ends_at`: Time-bounded sanctions
- `revoked_by`: Admin override capability
- Full audit trail via `ModerationAudit`

### 10.5 Audit Logging

Five dedicated log channels ensure full accountability:

| Channel | What's Logged | Retention |
|---------|--------------|-----------|
| `#log-moderation` | Auto-mod actions, manual mod actions, warnings, timeouts, kicks, bans | Permanent |
| `#log-ops-activity` | Tournament operations: score submissions, dispute filings, bracket changes, results | Permanent |
| `#log-bot-commands` | Every slash command used: who, what, when, where | 90 days |
| `#log-role-sync` | Role grants, role removals, sync failures, retry attempts | 90 days |
| `#log-joins-leaves` | Member joins (with account age), member leaves, kicks, bans | 90 days |

**Log format (example):**
```
[2026-03-15 15:32:41 BST] [MOD] Moderator @StaffMember timed out @UserName 
for 24 hours in #general-chat. Reason: "Repeated spam after verbal warning." 
Context: 3 warnings in past 7 days. Platform reputation: 72/100.
```

---

## Part 11: Notification Routing — Discord as a Channel

### 11.1 Notification Types Routed to Discord

DeltaCrown's notification system supports three channels: **in-app**, **email**, and **Discord**. The following events can be routed to Discord:

| Notification Type | Discord Delivery | Default |
|------------------|-----------------|---------|
| Tournament registration confirmed | DM | On |
| Match scheduled | DM | On |
| Check-in reminder (30min before) | DM + Channel mention | On |
| Match result confirmed | DM | On |
| Dispute filed (as participant) | DM + Private thread | On |
| Dispute resolved | DM | On |
| Prize distributed | DM | On |
| Team invite received | DM | On |
| Team join request (for captains) | DM | On |
| New follower | DM | Off |
| New team member joined | Team channel | On |
| Tournament published (game match) | Channel (@game role) | On |
| Leaderboard rank change | DM | Off |
| DeltaCoin credited | DM | Off |
| Platform announcement | Channel (@everyone) | On |
| Account security alert | DM | On |

### 11.2 DM vs Channel Notifications

**DM Notifications:**
- Personal, time-sensitive events (match reminders, dispute updates, prize payouts)
- Requires user to have DMs open from server members
- Falls back to email if DMs are off
- Respects user preference settings

**Channel Notifications:**
- Community-wide events (tournament announcements, leaderboard updates, winners)
- Uses role mentions for targeted delivery (e.g., `@Valorant` for Valorant tournaments)
- Never uses `@everyone` except for critical platform announcements

### 11.3 User Preference Controls

Users control their Discord notifications from two places:

**On DeltaCrown website (Settings > Notifications):**
```
Discord Notifications
├── ☑️ Match reminders
├── ☑️ Tournament updates
├── ☑️ Dispute notifications
├── ☑️ Prize distributions
├── ☑️ Team activity
├── ☐ Social notifications (follows, likes)
├── ☐ Economy notifications (DeltaCoin)  
├── ☑️ Security alerts
└── ☐ Marketing & events
```

**On Discord (via bot command):**
```
/notifications

Ephemeral response with buttons to toggle each category.
```

---

## Part 12: Analytics, Growth & Optimization

### 12.1 Metrics to Track

| Metric | Tool | Target |
|--------|------|--------|
| Total members | Discord Insights | 1,000 in month 1, 10,000 in 6 months |
| Daily active members | Discord Insights | 20%+ of total |
| Messages per day | Discord Insights | 500+ |
| Account link rate | Bot analytics | 50%+ of members linked |
| Tournament registration from Discord | UTM tracking | 30%+ of total registrations |
| Slash command usage | Bot logs | 100+ commands/day |
| Voice channel usage | Discord Insights | Peak concurrent: 50+ |
| Retention (7-day) | Discord Insights | 60%+ |
| Retention (30-day) | Discord Insights | 40%+ |
| Support ticket resolution time | Bot analytics | < 24 hours |

### 12.2 Growth Strategies

**Organic Growth:**
1. **Website integration** — "Join our Discord" banner on every page, especially tournament pages
2. **Post-registration prompt** — After tournament registration: "Join Discord for real-time match updates"
3. **In-email links** — Every transactional email includes Discord invite
4. **Social media cross-promotion** — Regular Discord highlights on Twitter/X, Facebook, Instagram
5. **SEO-optimized server** — Proper Discovery listing with keywords: "esports Bangladesh", "Valorant tournament", "PUBG Mobile competitive"
6. **Content creator partnerships** — Streamers and YouTubers share invite in descriptions

**Incentivized Growth:**
1. **Link reward** — 50 DeltaCoin for linking Discord account
2. **Invite reward** — 10 DeltaCoin per invited member who links their account (capped at 500 DC/month)
3. **Boost reward** — 50 DeltaCoin/month for server boosters
4. **Discord-exclusive tournaments** — Small community tournaments only announced on Discord
5. **Early access** — New features announced on Discord 24 hours before public release

**Partnership Growth:**
1. **Game community partnerships** — Collaborate with existing Bangladeshi Valorant, PUBG Mobile, MLBB communities
2. **University esports clubs** — Dedicated channels for university teams
3. **Esports cafe partnerships** — Physical presence at gaming cafes with QR code invites
4. **Cross-server partnerships** — Partner with other South Asian esports Discord servers

### 12.3 Retention Mechanics

| Mechanic | Description |
|----------|-------------|
| **Activity streaks** | Daily login → DeltaCoin. 7-day streak → bonus. Encourages habitual visits. |
| **Weekly digest** | Bot DMs a weekly summary: upcoming tournaments, rank changes, team activity |
| **Prediction league** | Ongoing engagement through match outcome predictions |
| **Role progression** | Visible progress: Linked → Active → Verified → Competitor → Veteran |
| **Content pipeline** | Steady flow of new tournaments, leaderboard updates, and community events |
| **Personal investment** | Linked accounts, DeltaCoin balance, team membership = switching costs |

### 12.4 Community Health Indicators

Monitor these weekly and act on declining trends:

| Indicator | Healthy | Warning | Critical |
|-----------|---------|---------|----------|
| DAU/MAU ratio | > 20% | 10–20% | < 10% |
| Messages per member per week | > 5 | 2–5 | < 2 |
| New member 7-day retention | > 60% | 40–60% | < 40% |
| Mod actions per 1000 messages | < 5 | 5–15 | > 15 |
| Unlinked member % | < 40% | 40–60% | > 60% |
| Voice channel peak concurrent | > 20 | 10–20 | < 10 |
| Support ticket backlog | < 10 | 10–30 | > 30 |

---

## Part 13: Implementation Roadmap

### 13.1 Phase 1 — Foundation (Week 1–2)

**Goal:** Server exists, looks professional, core channels are ready.

- [ ] Create Discord server with Community features enabled
- [ ] Set up vanity URL (`discord.gg/deltacrown`) — requires 7 boosts / partner
- [ ] Upload all visual assets (icon, banner, splash)
- [ ] Create all categories and channels per the blueprint in Part 5
- [ ] Configure channel permissions per the matrix in Part 4
- [ ] Write and pin rules in `#rules-and-guidelines`
- [ ] Write and pin server guide in `#server-guide`
- [ ] Set up reaction role message in `#pick-your-games` using a reaction role bot (temporary, before custom bot is ready)
- [ ] Configure Discord's built-in AutoMod rules
- [ ] Create all roles (hierarchy as specified)
- [ ] Enable Community features: Welcome Screen, Server Discovery, Membership Screening
- [ ] Configure Membership Screening (agree to rules before posting)
- [ ] Set up Server Insights
- [ ] Invite initial staff team (2–3 moderators, 1 admin)
- [ ] Test all channel permissions with test accounts

**Deliverable:** A functional, branded server that early adopters can join.

### 13.2 Phase 2 — Bot Development (Week 2–4)

**Goal:** DeltaCrown Sync Bot is functional with core commands.

- [ ] Set up bot project (Python with discord.py or JavaScript with discord.js)
- [ ] Register bot application on Discord Developer Portal
- [ ] Configure bot permissions and intents (see Part 6.1)
- [ ] Implement OAuth2 `/link` command and callback
- [ ] Implement `/profile` command (reads from DeltaCrown API)
- [ ] Implement `/balance` command
- [ ] Implement `/tournaments` command
- [ ] Implement `/standings` and `/leaderboard` commands
- [ ] Implement reaction role management (replace temporary bot)
- [ ] Implement member join/leave logging
- [ ] Implement basic slash command logging
- [ ] Set up bot hosting (Docker container on Render)
- [ ] Configure environment variables (tokens, API URLs, etc.)
- [ ] Write bot health check endpoint
- [ ] Load test bot with simulated traffic

**Deliverable:** Bot online with read-only commands and account linking.

### 13.3 Phase 3 — Integration (Week 4–6)

**Goal:** Bidirectional platform integration is live.

- [ ] Implement tournament announcement webhooks (Workflow 1)
- [ ] Implement match result announcement webhooks (Workflow 2)
- [ ] Implement role sync from platform events (Workflow 3)
  - [ ] Registration → tournament role
  - [ ] Team membership → team role
  - [ ] KYC verification → verified role
  - [ ] Staff assignment → staff role
- [ ] Implement `/check-in` command (Workflow 3 — check-in)
- [ ] Implement `/report-score` command with modal (Workflow 4)
- [ ] Implement `/dispute` command with private thread creation (Workflow 5)
- [ ] Implement `/resolve-dispute` for staff
- [ ] Implement team channel auto-creation (Workflow 5)
- [ ] Implement bidirectional chat sync (DiscordChatMessage)
- [ ] Implement DM notification routing
- [ ] Test end-to-end with a mock tournament
- [ ] Cross-platform sanction sync

**Deliverable:** Full tournament lifecycle manageable from Discord.

### 13.4 Phase 4 — Community Launch (Week 6–7)

**Goal:** Server is open to the public with a launch event.

- [ ] Soft launch: Invite existing DeltaCrown users via email + website banner
- [ ] "Link your account" campaign: 50 DC reward for first 500 linkers
- [ ] Launch tournament: "Discord Launch Invitational" — free entry, DeltaCoin prizes
- [ ] Social media announcement across all channels
- [ ] YouTube/Twitch streamer partnerships for launch coverage
- [ ] First Community Town Hall (Stage event): Platform overview, Q&A, giveaways
- [ ] Monitor: member growth, link rate, channel activity, error rates
- [ ] Rapid bug fixing and UX improvements based on feedback

**Deliverable:** 500+ members in first week, 200+ linked accounts.

### 13.5 Phase 5 — Advanced Features (Week 7–10)

**Goal:** Add engagement features and polish.

- [ ] Implement `/lft` and `/lfp` commands synced with Smart Recruitment
- [ ] Implement `/emergency-sub` command
- [ ] Implement DeltaCoin earning via Discord activity
- [ ] Build prediction league system
- [ ] Create weekly trivia bot module
- [ ] Implement `/notifications` preference command
- [ ] Build weekly digest DM system
- [ ] Implement organization channel auto-provisioning
- [ ] Create forum channel templates for game-specific LFT/LFG
- [ ] Advanced embed templates with buttons and select menus
- [ ] Implement `/announce` for organizers
- [ ] Implement `/ban-sync` for admins

**Deliverable:** Rich, engaging server with deep platform integration.

### 13.6 Phase 6 — Optimization & Scale (Ongoing)

**Goal:** Continuous improvement based on data and community feedback.

- [ ] A/B test onboarding flows (different welcome messages, channel orders)
- [ ] Optimize bot response times (< 500ms for all commands)
- [ ] Implement rate limiting and queue management for high-traffic events
- [ ] Add multi-language support (English + Bangla)
- [ ] Build admin dashboard for Discord analytics (bot logs → Grafana)
- [ ] Create automated community health reports
- [ ] Scale voice channels dynamically based on demand
- [ ] Implement advanced anti-raid measures
- [ ] Community feedback loop: monthly survey, suggestion box channel
- [ ] Expand to multi-server model if needed (regional servers)

**Deliverable:** A mature, self-sustaining community that drives platform growth.

---

## Part 14: Appendices

### 14.1 Full Permission Matrix Table

**Category-Level Permissions:**

| Category | @everyone | @Linked | @Game Role | @Staff | @Admin |
|----------|:---------:|:-------:|:----------:|:------:|:------:|
| 👑 WELCOME & INFO | Read | Read + React | Read | Read + Manage | Full |
| 💬 COMMUNITY | Limited | Full | Full | Full + Manage | Full |
| 🏆 TOURNAMENTS | Read | Read + Commands | Read + Commands | Full + Manage | Full |
| ⚔️ MATCH OPERATIONS | Hidden | Commands only | Commands only | Full | Full |
| 🎮 GAME ZONES | Hidden | Hidden | Full (own game) | Full | Full |
| 👥 TEAMS | Hidden | Hidden | Hidden | Team members only | Full |
| 🛡️ STAFF ZONE | Hidden | Hidden | Hidden | Full | Full |
| 📊 LOGS | Hidden | Hidden | Hidden | Hidden | Read |
| 🎫 SUPPORT | Read | Full | Full | Full + Manage | Full |

### 14.2 Bot Environment Variables

```env
# Discord Configuration
DISCORD_BOT_TOKEN=<bot-token>
DISCORD_CLIENT_ID=<client-id>
DISCORD_CLIENT_SECRET=<client-secret>
DISCORD_GUILD_ID=<main-server-id>
DISCORD_REDIRECT_URI=https://deltacrown.gg/account/discord/callback/

# DeltaCrown API
DELTACROWN_API_URL=https://deltacrown.gg/api
DELTACROWN_API_KEY=<internal-api-key>

# Webhook URLs (per channel)
WEBHOOK_TOURNAMENT_ANNOUNCEMENTS=<webhook-url>
WEBHOOK_MATCH_RESULTS=<webhook-url>
WEBHOOK_WINNERS_WALL=<webhook-url>
WEBHOOK_PLATFORM_UPDATES=<webhook-url>

# Channel IDs
CHANNEL_ANNOUNCEMENTS=<snowflake>
CHANNEL_TOURNAMENT_FEED=<snowflake>
CHANNEL_CHECK_IN=<snowflake>
CHANNEL_SCORE_REPORTING=<snowflake>
CHANNEL_DISPUTES=<snowflake>
CHANNEL_WINNERS_WALL=<snowflake>
CHANNEL_MOD_QUEUE=<snowflake>
CHANNEL_MATCH_OPS=<snowflake>
CHANNEL_LOG_MODERATION=<snowflake>
CHANNEL_LOG_OPS=<snowflake>
CHANNEL_LOG_COMMANDS=<snowflake>
CHANNEL_LOG_ROLES=<snowflake>
CHANNEL_LOG_JOINS=<snowflake>

# Role IDs
ROLE_SUPER_ADMIN=<snowflake>
ROLE_ADMIN=<snowflake>
ROLE_ORGANIZER=<snowflake>
ROLE_REFEREE=<snowflake>
ROLE_MODERATOR=<snowflake>
ROLE_CONTENT_CREATOR=<snowflake>
ROLE_VERIFIED=<snowflake>
ROLE_LINKED=<snowflake>

# Game Role IDs
ROLE_VALORANT=<snowflake>
ROLE_PUBG_MOBILE=<snowflake>
ROLE_MLBB=<snowflake>
ROLE_FREE_FIRE=<snowflake>
ROLE_CODM=<snowflake>
ROLE_CS2=<snowflake>
ROLE_DOTA2=<snowflake>
ROLE_ROCKET_LEAGUE=<snowflake>
ROLE_R6_SIEGE=<snowflake>
ROLE_EA_FC=<snowflake>
ROLE_EFOOTBALL=<snowflake>

# Feature Flags
ENABLE_DELTACOIN_EARNING=true
ENABLE_BIDIRECTIONAL_CHAT=true
ENABLE_AUTO_TEAM_CHANNELS=true
ENABLE_DM_NOTIFICATIONS=true

# Operational
BOT_LOG_LEVEL=INFO
BOT_SHARD_COUNT=1
MAX_TEAM_CHANNELS=100
RAID_DETECTION_THRESHOLD=10
RAID_DETECTION_WINDOW_SECONDS=60
```

### 14.3 Webhook Payload Schemas

**Tournament Announcement:**
```json
{
  "username": "DeltaCrown",
  "avatar_url": "https://deltacrown.gg/static/img/bot-avatar.png",
  "content": "<@&ROLE_VALORANT>",
  "embeds": [{
    "title": "🏆 New Tournament: {tournament.name}",
    "url": "https://deltacrown.gg/tournaments/{tournament.slug}/",
    "color": 16766720,
    "description": "{tournament.description}",
    "thumbnail": {"url": "{tournament.game.icon_url}"},
    "fields": [
      {"name": "📅 Date", "value": "{tournament.start_date}", "inline": true},
      {"name": "🎮 Game", "value": "{tournament.game.name}", "inline": true},
      {"name": "🏟️ Format", "value": "{tournament.format}", "inline": true},
      {"name": "💰 Prize Pool", "value": "{tournament.prize_pool}", "inline": true},
      {"name": "🎟️ Entry Fee", "value": "{tournament.entry_fee}", "inline": true},
      {"name": "👥 Capacity", "value": "{tournament.current}/{tournament.max_teams}", "inline": true}
    ],
    "footer": {"text": "DeltaCrown Esports • From the Delta to the Crown"},
    "timestamp": "{tournament.created_at}"
  }]
}
```

**Match Result:**
```json
{
  "username": "DeltaCrown",
  "avatar_url": "https://deltacrown.gg/static/img/bot-avatar.png",
  "embeds": [{
    "title": "⚔️ Match Result — {tournament.name}",
    "color": 65280,
    "fields": [
      {"name": "Round", "value": "{match.round_label}", "inline": true},
      {"name": "Winner", "value": "🏆 {match.winner.name}", "inline": true},
      {"name": "Score", "value": "{match.team_a.name} {score_a} — {score_b} {match.team_b.name}", "inline": false}
    ],
    "footer": {"text": "Match #{match.id} • {match.completed_at}"}
  }]
}
```

### 14.4 Embed Templates

**Welcome Embed (posted in #welcome by bot):**
```
Title: 👑 Welcome to DeltaCrown Esports
Color: #FFD700 (Crown Gold)
Description:
  Welcome to the official home of DeltaCrown — South Asia's premier esports 
  tournament platform! Whether you're a casual player, a competitive grinder, 
  a team captain, or a tournament organizer, this is your community.

Fields:
  🚀 Getting Started:
    1. Read the rules → #rules-and-guidelines
    2. Pick your games → #pick-your-games
    3. Link your account → /link in #link-your-account
    4. Introduce yourself → #introductions

  🏆 What is DeltaCrown?
    A full-stack esports platform supporting 11 competitive games, 
    professional team management, tournament organization with real 
    prize pools, and the DeltaCoin virtual economy.

  🌐 Links:
    Website: https://deltacrown.gg
    Twitter/X: @DeltaCrownGG
    YouTube: DeltaCrown Esports
    Support: /support or #open-a-ticket

Thumbnail: DeltaCrown logo
Image: Server banner (wide)
Footer: "From the Delta to the Crown — Where Champions Rise" • deltacrown.gg
```

### 14.5 Emergency Procedures

**Bot Outage:**
1. Check `#bot-status` for last heartbeat
2. Check Render dashboard for container status
3. If container crashed → restart via Render dashboard
4. If API issue → check DeltaCrown backend health (`/healthz/`)
5. Post notice in `#announcements`: "⚠️ Bot temporarily unavailable. Tournament operations continue on the website."
6. For active tournaments → switch to manual score reporting on the website

**Raid Attack:**
1. Bot auto-detects raid (10+ joins in 60s) → enables lockdown
2. Lockdown actions: disable new member posting, enable highest verification level
3. Admin verifies in `#admin-ops`
4. Manual review of recent joins → remove suspicious accounts
5. Disable lockdown when safe
6. Post-incident report in `#log-moderation`

**Discord API Outage:**
1. All Celery discord tasks auto-retry with exponential backoff
2. After 3 failures → tasks are queued in Redis for later processing
3. Bot reconnects automatically via discord.py's reconnect logic
4. Notifications fall back to email channel
5. Critical platform operations (tournaments, matches) continue on web — Discord is an enhancement, never a dependency

### 14.6 Media Asset Checklist

| Asset | Dimensions | Format | Status |
|-------|-----------|--------|--------|
| Server icon | 512×512 | PNG | ☐ |
| Server banner | 960×540 | PNG | ☐ |
| Invite splash | 1920×1080 | PNG | ☐ |
| Game emojis (11) | 128×128 | PNG | ☐ |
| Rank emojis (8) | 128×128 | PNG | ☐ |
| Platform emojis (7) | 128×128 | PNG | ☐ |
| Reaction emojis (8) | 128×128 | PNG | ☐ |
| Status emojis (5) | 128×128 | PNG | ☐ |
| Team emojis (4) | 128×128 | PNG | ☐ |
| Payment emojis (4) | 128×128 | PNG | ☐ |
| Custom stickers (15) | 320×320 | APNG/Lottie | ☐ |
| Bot avatar | 512×512 | PNG | ☐ |
| Welcome banner image | 1200×400 | PNG | ☐ |
| Rules header image | 1200×400 | PNG | ☐ |
| Game zone banners (11) | 1200×400 | PNG | ☐ |
| Trophy/medal icons (3) | 256×256 | PNG | ☐ |

---

## Epilogue: The Living Server

A Discord server is never "done." It is a living organism that grows, evolves, and adapts alongside its community. This blueprint provides the foundation — the bones and organs — but the soul comes from the people who inhabit it.

The DeltaCrown Discord server will be the place where:
- A teenager in Sylhet finds their first team
- A captain in Chittagong coordinates a clutch match
- An organizer in Dhaka launches a tournament that changes someone's career
- A referee in Rajshahi ensures fair play with a single slash command
- A content creator in Comilla builds an audience by covering DeltaCrown events

This is not just a Discord server. This is the town square of South Asian esports. Build it with care. Moderate it with fairness. And let the community make it their home.

*From the Delta to the Crown — Where Champions Rise.*

---

**End of Document**  
**DeltaCrown Discord Server — Complete Setup, Integration & Operations Guide v3.0**  
**© 2026 DeltaCrown. All rights reserved.**
