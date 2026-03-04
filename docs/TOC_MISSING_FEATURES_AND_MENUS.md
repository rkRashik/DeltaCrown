# TOC — Missing Menus, Features & Competitive Analysis

> **Generated**: Sprint 28 Research  
> **Benchmark Platforms**: Toornament, FACEIT, start.gg (Smash.gg), Battlefy, ESEA, Challengermode, Repeat.gg  
> **Current TOC Tabs**: Overview, Participants, Payments, Brackets, Matches, Schedule, Disputes, Announcements, Settings (9 tabs)  
> **Current API Endpoints**: 117  

---

## Table of Contents

1. [Missing Tabs / Menus](#1-missing-tabs--menus)  
2. [Missing Features in Existing Tabs](#2-missing-features-in-existing-tabs)  
3. [Missing Tools & Utilities](#3-missing-tools--utilities)  
4. [Missing Integrations](#4-missing-integrations)  
5. [Missing Configuration Options](#5-missing-configuration-options)  
6. [Priority Matrix](#6-priority-matrix)  

---

## 1. Missing Tabs / Menus

These are **entirely new tabs/sections** that modern platforms have but DeltaCrown TOC currently lacks.

### 1.1 📊 Standings / Leaderboards Tab
**Available on**: Toornament, FACEIT, start.gg, Battlefy  
**Why it's needed**: Currently standings are only accessible inside the Brackets tab under Group Stage. Organizers need a dedicated, real-time leaderboard view that works across all formats (group stage, swiss, round-robin, BR scoring).

**Expected Features**:
- Live standings table with rank, W/L/D record, points, tiebreakers, goal diff
- Multi-stage views: Group → Playoff qualification tracker
- Export standings as image (for social media sharing)
- Public standings embed code (iframe/widget)
- Historical standings snapshots (after each round)
- Point breakdown tooltip per team
- Qualification line indicator (top N advance, highlighted in green)

---

### 1.2 📺 Streams & Media Tab
**Available on**: Toornament, start.gg, FACEIT  
**Why it's needed**: Stream management is currently just a URL field on matches. Modern TOs need a dedicated broadcast operations center.

**Expected Features**:
- **Broadcast Stations**: Assign casters/observers to streams
- **Stream Schedule**: Publish which matches are being streamed and when
- **Multi-Stream Dashboard**: Monitor all active streams in one view
- **VOD Library**: Auto-collect Twitch/YouTube VODs after matches
- **Stream Overlay Data API**: Provide real-time match data for OBS overlays (scores, team names, bracket position)
- **Clip Highlights**: Mark key moments during live matches
- **Restream Integration**: Manage multi-platform restreaming
- **Viewer Stats**: Track concurrent viewers per stream

---

### 1.3 ✅ Check-in Hub Tab
**Available on**: FACEIT, ESEA, Challengermode  
**Why it's needed**: Check-in is currently a toggle buried in Participants. High-stakes tournaments need a dedicated check-in operations view with countdowns, auto-DQ, and real-time monitoring.

**Expected Features**:
- **Real-time Check-in Dashboard**: Visual grid of all teams/players with check-in status (live updates via WebSocket)
- **Countdown Timer**: Configurable check-in window with visible countdown
- **Auto-DQ Engine**: Automatically disqualify teams that miss check-in deadline
- **Manual Override**: Admin force check-in for specific teams
- **Notification Blast**: "Check-in is OPEN" push notification to all participants
- **Per-Round Check-in**: Separate check-in per round/match (not just pre-tournament)
- **Check-in Stats**: % checked in, missing teams list, time-to-check-in analytics
- **Captain Confirmation**: Require team captain to confirm lineup for each match

---

### 1.4 🏠 Lobby / Server Management Tab
**Available on**: FACEIT, ESEA, Toornament (game-specific)  
**Why it's needed**: Currently lobby info is a simple text field on matches. Competitive esports needs proper server/lobby lifecycle management.

**Expected Features**:
- **Auto-Lobby Creation**: API integration with game servers to auto-create match lobbies
- **Server Pool**: Manage a pool of game servers/custom rooms
- **Server Health Monitoring**: Ping, region, capacity, status
- **Lobby Code Distribution**: Auto-send lobby codes to checked-in players
- **Anti-Cheat Status**: Show AC client status per player (FACEIT AC, ESEA Client, Vanguard)
- **Server Region Preferences**: Auto-assign servers based on team locations
- **Spectator Slots**: Manage observer/caster slots in game lobbies
- **Match Room Chat**: In-platform chat room per match (currently no in-app chat)

---

### 1.5 📈 Analytics & Insights Tab
**Available on**: Toornament (Organizer Dashboard), start.gg (Insights), Challengermode  
**Why it's needed**: Stats are currently embedded in Settings accordion. Organizers need proper analytics to understand their tournament's performance and grow.

**Expected Features**:
- **Tournament Analytics Dashboard**:
  - Registration funnel (views → start reg → complete reg → payment → check-in)
  - Participant demographics (region, rank distribution, new vs returning)
  - Revenue analytics (total, by method, refund rate, avg revenue per participant)
  - Match analytics (avg duration, OT rate, forfeit rate, dispute rate)
  - Engagement metrics (page views, bracket views, spectator count)
- **Comparison Charts**: Compare current tournament vs previous editions
- **Export Reports**: PDF/CSV tournament summary report
- **Real-time Dashboard**: Live KPIs during tournament execution
- **Heatmaps**: Activity heatmap (when participants are most active)
- **Conversion Tracking**: UTM parameter tracking for marketing campaigns

---

### 1.6 📝 Rules & Info Tab
**Available on**: Toornament, Battlefy, start.gg  
**Why it's needed**: Rules management is buried in Settings accordion section 9/15. Players and admins need a dedicated, well-organized rules reference.

**Expected Features**:
- **Rich Rulebook Editor**: Markdown/WYSIWYG editor with table of contents
- **Versioned Rules**: Show diff between versions, notify participants of changes
- **Rule Sections**: General Rules, Game-Specific Rules, Match Rules, Conduct Rules, Prize Rules
- **FAQ Section**: Common questions with answers
- **Quick Reference Card**: One-page summary of key rules (format, check-in time, etc.)
- **Player Acknowledgement Tracker**: See which players have read/accepted rules
- **Prize Information Page**: Detailed prize breakdown with distribution schedule
- **Tournament Info Page**: All key dates, format description, eligibility criteria in one view

---

### 1.7 👥 Teams / Roster Management Tab
**Available on**: FACEIT, start.gg, Battlefy  
**Why it's needed**: Team management is shared between Participants tab and the external Teams app. Need a dedicated roster management view inside TOC.

**Expected Features**:
- **Roster Overview**: Every registered team with full roster display
- **Roster Lock**: Lock/unlock rosters at specific stages
- **Lineup Submissions**: Teams submit match-day lineup (starting 5 + subs) before each round
- **Roster Change Log**: Track all roster changes with timestamps
- **Eligibility Verification**: Auto-check rank requirements, age restrictions, region locks
- **Anti-Smurf Detection**: Flag accounts with suspicious stats (new account, rank mismatch)
- **Team Communication**: Message all team captains at once
- **Captain Assignment**: Transfer captain role within a team
- **Import Rosters**: Import teams via CSV/API from other platforms

---

### 1.8 🔔 Notifications Center Tab
**Available on**: FACEIT, start.gg  
**Why it's needed**: Announcements tab is one-way broadcasting. Need a full communications management system.

**Expected Features**:
- **Notification Templates**: Pre-built templates for common messages (match ready, check-in open, bracket published)
- **Scheduled Notifications**: Queue notifications to send at specific times
- **Auto-Notifications**: Rule-based triggers (e.g., auto-remind 15min before match, auto-notify when opponent forfeits)
- **Delivery Channels**: In-app, Email, Discord webhook, SMS
- **Notification Log**: See all sent notifications with delivery status
- **Per-Team Messaging**: Send targeted messages to specific teams/players
- **Participant Inbox**: View the notification experience from a participant's perspective
- **Unsubscribe Management**: Handle opt-outs and preferences

---

## 2. Missing Features in Existing Tabs

### 2.1 Overview Tab
| Missing Feature | Platform Reference | Priority |
|---|---|---|
| **Tournament Countdown Timer** — visual countdown to registration close, tournament start, next match | Toornament, Battlefy | High |
| **Social Media Widget** — live Twitter/Discord feed embedded | start.gg | Low |
| **Participant Growth Chart** — registration trend over time | Toornament | Medium |
| **Quick Launch Actions** — one-click buttons for common flows (start next round, open check-in, broadcast update) | FACEIT | High |
| **Staff Online Indicator** — show which admins are currently active | FACEIT | Medium |
| **Tournament Sharing Tools** — copy public link, share to socials, QR code | Toornament, Battlefy | Medium |
| **Sponsor Logo Display** — show tournament sponsors with priority ordering | start.gg | Low |

### 2.2 Participants Tab
| Missing Feature | Platform Reference | Priority |
|---|---|---|
| **CSV/Excel Import** — bulk import participants from file | Toornament, Battlefy | High |
| **Seeding Import** — import seeding from external ranking (HLTV, Liquipedia, VLR) | start.gg | Medium |
| **Participant Communication** — DM individual participants from within TOC | FACEIT | Medium |
| **Registration Form Builder** — custom fields per tournament (e.g., Discord ID, Steam ID) | Toornament, Battlefy | High |
| **Team Size Validator** — auto-reject teams that don't meet min roster size | FACEIT | Medium |
| **Duplicate Account Detection** — flag registrations with same IP/device fingerprint | FACEIT, ESEA | High |
| **Invitation System** — invite specific teams/players by email, generate invite links | Toornament | Medium |
| **Transfer Slots** — transfer registration to another player/team | start.gg | Low |

### 2.3 Payments Tab
| Missing Feature | Platform Reference | Priority |
|---|---|---|
| **Automated Payout** — PayPal/Stripe integration for automatic prize distribution | start.gg, Challengermode | High |
| **Invoice Generation** — generate PDF invoices for entry fees | Toornament | Medium |
| **Payment Scheduling** — scheduled prize payouts (e.g., 7 days after tournament ends) | start.gg | Medium |
| **Currency Conversion** — auto-convert between currencies for international tournaments | Toornament | Low |
| **Sponsor Revenue Tracking** — track sponsor contributions separately | start.gg | Low |
| **Subscription/Season Pass** — recurring entry fees for league/season formats | FACEIT, ESEA | Medium |
| **Crowdfunded Prize Pool** — allow community contributions to prize pool | start.gg | Low |

### 2.4 Brackets Tab
| Missing Feature | Platform Reference | Priority |
|---|---|---|
| **Swiss Format** — full Swiss-system bracket support | start.gg, Challengermode | High |
| **Double Elimination** — winners + losers bracket with grand finals reset | start.gg, Battlefy | High |
| **Round Robin** — full round-robin format with automated scheduling | Toornament | Medium |
| **Bracket Embedding** — embeddable bracket widget (iframe) for external websites | Toornament, start.gg | High |
| **Live Bracket Updates** — WebSocket-powered real-time bracket visualization | start.gg, FACEIT | High |
| **Bracket Sharing** — public share link, social media preview image auto-generation | Toornament | Medium |
| **Bracket Reset** — selective reset (reset single match or from a point) vs full reset | start.gg | Medium |
| **Seeding Algorithms** — auto-seed by Elo/MMR/external ranking | start.gg, FACEIT | Medium |
| **Multi-Stage Progression** — auto-advance teams from one stage to the next | Toornament | High |
| **Third-Place Match** — automatic 3rd-place match generation for SE brackets | Toornament | Low |
| **Grand Finals Reset** — double-elim grand finals from losers bracket side | start.gg | Medium |

### 2.5 Matches Tab
| Missing Feature | Platform Reference | Priority |
|---|---|---|
| **VOD/Replay Management** — attach and review match VODs | FACEIT, ESEA | Medium |
| **Auto Screenshot Verification** — AI-assisted screenshot parsing for score extraction | FACEIT | Low |
| **Match Room Chat** — real-time chat between teams and admins per match | FACEIT, ESEA | High |
| **Anti-Cheat Integration** — FACEIT AC, ESEA Client, or game-native AC status | FACEIT, ESEA | Medium |
| **Map Veto Visualization** — visual map veto process (pick/ban with timer) | FACEIT | High |
| **Match Timeline** — visual timeline of match events (start, pause, score submit, dispute, resolve) | Toornament | Medium |
| **Auto-Result Detection** — API integration with game to auto-report match results | FACEIT, ESEA | High |
| **Overtime Rules Engine** — configurable OT rules (MR3, golden round, etc.) | FACEIT | Medium |
| **Player Stats Per Match** — K/D, damage, economy, etc. pulled from game API | FACEIT, ESEA | Medium |
| **Match Delay Tracking** — track how late matches start vs scheduled time | Toornament | Low |

### 2.6 Schedule Tab *(Just Enhanced in Sprint 28)*
| Missing Feature | Platform Reference | Priority |
|---|---|---|
| **Drag-and-Drop Scheduling** — drag match cards to time slots | Toornament | High |
| **Calendar Export** — .ics file export for Google Calendar/Outlook | Toornament | Medium |
| **Participant Schedule View** — "My Schedule" for individual teams | FACEIT | Medium |
| **Auto-Conflict Resolution** — suggest fixes when conflicts are detected | Toornament | Medium |
| **Multi-Day Tournament Setup** — configure different start times per day | Toornament, start.gg | Medium |
| **Schedule Publishing** — publish schedule publicly vs draft mode | Toornament | High |
| **Time Zone Selector** — display schedule in participant's local timezone | start.gg | Medium |

### 2.7 Disputes Tab
| Missing Feature | Platform Reference | Priority |
|---|---|---|
| **SLA Timer** — maximum response time per dispute with escalation triggers | Toornament | High |
| **Dispute Templates** — pre-built resolution templates (forfeit win, replay, split) | Toornament | Medium |
| **Admin Chat in Dispute** — threaded conversation between admin and disputing parties | FACEIT | High |
| **Evidence Comparison Tool** — side-by-side evidence viewer with annotation tools | FACEIT | Medium |
| **Dispute Analytics** — common dispute reasons, avg resolution time, admin performance | Toornament | Low |
| **Auto-Resolve Rules** — auto-resolve based on screenshot match / game API data | FACEIT | Medium |
| **Player Behavior Score** — factor in historical behavior when resolving disputes | FACEIT | Medium |

### 2.8 Announcements Tab
| Missing Feature | Platform Reference | Priority |
|---|---|---|
| **Rich Media Announcements** — images, videos, embedded content in announcements | Toornament | Medium |
| **Scheduled Publishing** — schedule announcements to go live at a specific time | Toornament | Medium |
| **Translation Support** — multi-language announcements | Toornament | Low |
| **Announcement Analytics** — read receipts, click-through rates | Custom | Low |
| **Discord Integration** — auto-post announcements to Discord channel via webhook | start.gg | High |
| **Announcement Reactions** — allow participants to react/comment | Custom | Low |

### 2.9 Settings Tab
| Missing Feature | Platform Reference | Priority |
|---|---|---|
| **Custom Branding** — custom colors, logo placement, themed tournament page | Toornament, start.gg | High |
| **Custom Registration Fields** — additional form fields beyond defaults | Toornament, Battlefy | High |
| **Webhook Configuration** — configure outgoing webhooks for external integration | start.gg, Toornament | High |
| **API Key Management** — issue API keys for third-party integrations | Toornament | Medium |
| **Tournament Templates** — save entire config as template for future tournaments | Toornament | Medium |
| **Tournament Cloning** — duplicate tournament with all settings | Toornament, Battlefy | High |
| **Feature Flags UI** — toggle experimental features per tournament | Custom | Low |
| **Danger Zone** — delete tournament, archive tournament, transfer ownership | start.gg | Medium |
| **SEO Preview** — live preview of how tournament appears in Google/social shares | Custom | Low |
| **Custom Domain** — custom URL for tournament page | Toornament | Low |

---

## 3. Missing Tools & Utilities

| Tool | Description | Platform Reference | Priority |
|---|---|---|---|
| **Command Palette** | Ctrl+K quick actions (partially exists in core) | start.gg | Low |
| **Bulk Email Tool** | Send bulk emails to all/filtered participants | Toornament | Medium |
| **Tournament Preview** | Preview public tournament page as a participant | Toornament | High |
| **Activity Timeline** | Global activity feed (all events across all tabs chronologically) | Custom | Medium |
| **Undo/Redo** | Undo last action (bracket reset, bulk action, etc.) | Custom | Medium |
| **Dark/Light Mode Toggle** | Per-user theme preference in TOC | Custom | Low |
| **Mobile TOC** | Responsive mobile-optimized version of key TOC functions | FACEIT, all | High |
| **Offline Mode** | Cache critical data for use in poor-connectivity LAN events | Custom | Low |
| **Keyboard Shortcuts Help** | Dedicated overlay showing all available shortcuts | Custom | Low |
| **Tournament Health Advisor** | AI-powered suggestions based on tournament state ("You have 3 teams that haven't paid") | Custom | Medium |
| **Batch Tournament Ops** | Manage multiple tournaments from one view (for multi-stage/season events) | Toornament | Medium |

---

## 4. Missing Integrations

| Integration | Description | Priority |
|---|---|---|
| **Discord Bot** | Auto-post results, brackets, check-in reminders to Discord server | High |
| **Twitch Extensions** | Bracket/match overlay as Twitch extension | Medium |
| **Game APIs** | Auto-report results from: Riot (Valorant/LoL), Steam (CS2/Dota2), Supercell (Clash), Garena (Free Fire) | High |
| **Stripe/PayPal** | Automated entry fee collection and prize payouts | High |
| **Google Sheets** | Export/sync participant lists and standings to Google Sheets | Medium |
| **OBS/Streamlabs** | Direct data feed for stream overlays (scores, bracket, timer) | Medium |
| **Zapier/n8n** | Webhook-based automation for external tools | Medium |
| **Email Service** | SendGrid/Mailgun integration for transactional emails | Medium |
| **SMS Gateway** | Twilio/Nexmo for SMS check-in reminders | Low |
| **Social Auth Verification** | Verify Discord/Steam/Riot accounts during registration | Medium |

---

## 5. Missing Configuration Options

| Config | Where | Description | Priority |
|---|---|---|---|
| **Match Best-of Format** | Per stage/round | BO1, BO3, BO5 per stage (currently global) | High |
| **Auto-Advance Rules** | Brackets | Configure auto-advance criteria per stage | High |
| **DQ Penalty System** | Settings | Configure forfeit penalties (point deduction, ban duration, etc.) | Medium |
| **Check-in Per Round** | Settings | Enable check-in before each round, not just once | Medium |
| **Roster Lock Schedule** | Settings | Auto-lock rosters at specific stages | Medium |
| **Stream Priority Rules** | Settings | Auto-assign featured stream to highest-seeded match | Low |
| **Tiebreaker Config** | Settings | Configurable tiebreaker priority per format | Medium |
| **Match Report Deadline** | Settings | Time limit for teams to submit match results | Medium |
| **No-Show Timer** | Settings | Auto-forfeit if team doesn't show within X minutes of match time | High |
| **Round Scheduling Mode** | Settings | All rounds at once vs round-by-round scheduling | Medium |
| **Minimum Check-in Age** | Settings | Minimum account age to participate (anti-smurf) | Medium |

---

## 6. Priority Matrix

### 🔴 Critical (Should Have Now)
1. **Standings / Leaderboards Tab** — core competitive feature
2. **Check-in Hub** — essential for competitive execution
3. **Double Elimination Bracket** — most popular format after SE and Groups
4. **Swiss Format** — growing in popularity (Valorant Champions Tour uses it)
5. **Bracket Embedding/Sharing** — marketing and community engagement
6. **Match Room Chat** — communication is critical during matches
7. **Discord Bot Integration** — #1 communication channel for esports
8. **Tournament Cloning** — huge time saver for recurring events
9. **Custom Registration Fields** — every TO needs different info
10. **No-Show Timer / Auto-DQ** — reduce manual intervention

### 🟡 High Priority (Next Quarter)
1. **Streams & Media Tab** — broadcast operations
2. **Analytics & Insights Tab** — data-driven tournament management
3. **Teams / Roster Management Tab** — proper roster lifecycle
4. **Drag-and-Drop Schedule** — UX improvement
5. **Auto-Result Detection** (Game API) — reduce manual score entry
6. **Webhook Configuration** — enable ecosystem integrations
7. **Automated Payouts** — reduce payout friction
8. **Map Veto Visualization** — competitive game feature
9. **Schedule Publishing** — draft vs published schedule
10. **Custom Branding** — tournament page differentiation

### 🟢 Nice-to-Have (Future)
1. **Notifications Center Tab** — full communications management
2. **Rules & Info Tab** — dedicated rules hub
3. **Lobby/Server Management** — game-specific automation
4. **Mobile TOC** — responsive management
5. **VOD Library** — post-tournament content
6. **AI-Powered Tournament Advisor** — smart suggestions
7. **Multi-Tournament Batch Ops** — season/league management
8. **Calendar Export (.ics)** — participant convenience
9. **Crowdfunded Prize Pool** — community engagement
10. **Custom Domain** — white-label tournaments

---

## Summary

| Category | Current | Missing | Coverage |
|---|---|---|---|
| **Tabs/Menus** | 9 | 8 | 53% |
| **API Endpoints** | 117 | ~80+ needed | ~59% |
| **JS Modules** | 15 | 8+ needed | ~65% |
| **Integrations** | 0 external | 10 identified | 0% |
| **Bracket Formats** | 2 (SE + Groups) | 3+ (DE, Swiss, RR) | 40% |

**DeltaCrown TOC is already one of the most feature-rich open-source tournament management backends.** The gaps above represent what separates a good TO tool from a world-class competitive platform like FACEIT or Toornament. The priority matrix above provides a phased roadmap for closing these gaps.
