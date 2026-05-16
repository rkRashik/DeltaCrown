# DeltaCrown

**From the Delta to the Crown - Where Champions Rise.**

DeltaCrown is a Bangladesh-first, globally ambitious esports platform for tournaments, teams, rankings, player identity, community, and competitive rewards.

It is built for the full competitive lifecycle: discovering games, forming teams, joining tournaments, proving results, climbing rankings, earning rewards, developing talent, and building a lasting esports identity.

## What DeltaCrown Is

DeltaCrown is not just a bracket tool or a profile site. It is a connected esports ecosystem.

The platform brings together:

- Tournaments and match operations
- Teams and esports organizations
- Player profiles and game passports
- Crown Point rankings and seasons
- DeltaCoin utility economy
- Competitive reward operations
- Team recruitment and training workflows
- Community, content, commerce, and admin systems

The product direction is premium, competitive, community-driven, and skill-focused, while staying accessible for Bangladesh-first gamers.

## Competitive Ecosystem

DeltaCrown's next-generation competitive hub is organized around four short product names:

| Feature | What It Does |
| --- | --- |
| Showdown | Head-to-head competitive reward matches for teams or players |
| Missions | Solo skill challenges, progression goals, and reward tasks |
| Bounty | Open skill-based reward challenges and community rivalry boards |
| Dropzone | Large battle royale custom lobbies with slots, room credentials, scoring, and settlement |

These systems are built around structured rules, team authority, match rooms, proof, escrow, and admin review. The unified My Operations feed is active, competitive detail pages now exist, and MVP admin controls now exist for Showdown result handling, Bounty claim verification, Missions proof/review, and Dropzone scoring/settlement. The public product layer is still being refined around file-upload proof, richer dispute review, Dropzone user reporting, notifications, and deeper game API verification.

## Tournaments

The tournament engine supports professional event workflows:

- Single elimination
- Double elimination
- Round robin
- Swiss
- Group to playoff
- Battle royale lobby formats
- Solo and team participation
- Registration and eligibility checks
- Match rooms and scheduling
- Check-in and result submission
- Dispute handling
- Prize and DeltaCoin configuration
- Certificates and historical records

Tournaments are designed to create lasting competitive history, not one-time event pages.

## Teams and Organizations

DeltaCrown treats teams as persistent esports entities.

Teams can manage:

- Rosters
- Owners, managers, coaches, analysts, players, and substitutes
- Tournament captain permissions
- Branding and public identity
- Recruitment positions
- Join requests and tryout scheduling
- Social links, milestones, sponsors, and media
- Rankings and match history

Organizations can own multiple teams and build a professional brand across games.

## Rankings

DeltaCrown uses Crown Points as the public ranking language.

Teams progress through:

- Rookie
- Challenger
- Elite
- Master
- Legend
- The Crown

The ranking direction includes verified match results, tournament placement rewards, seasons, activity score, anti-farming controls, same-opponent diminishing returns, daily match caps, and internal ELO-style balancing.

The public experience stays easy to understand: points, tiers, ranks, activity, and history.

## Player Identity

Players build competitive profiles that can grow over time.

Profiles support:

- Public identity and display branding
- Game passports and linked game identities
- Preferred games and playstyle signals
- Team affiliations
- Achievements and certificates
- Match history and reputation direction
- Privacy and account safety controls

The goal is to help players build a credible esports record, not just a username.

## DeltaCoin

DeltaCoin is DeltaCrown's closed-loop utility and reward currency.

It is used inside the platform for participation, entries, rewards, platform services, progression, and future store or premium experiences. DeltaCoin is positioned as an internal platform utility, not a financial asset.

The economy layer includes wallet records, transaction history, escrow locking, refunds, payout helpers, treasury support, local payment method fields, and wallet security direction.

## Team HQ and Training

Team HQ is the operating space for teams.

Training workflows are separate from competitive reward operations by default:

- Scrim: team vs team practice match
- Tryout: evaluation session for applicants or invited players
- Practice: internal team training
- VOD Review: review notes, clips, and improvement tracking

The current platform now includes a Team HQ Training foundation with Scrim requests/bookings, Tryout applications/sessions, Practice sessions, VOD reviews, RBAC, API wiring, public tryout/scrim entry points, and admin visibility. The tryout path can move from application to join offer, applicant accept/decline, and safe membership creation. Players also have a dashboard inbox for team applications, tryouts, and offers. Remaining work includes attendance, richer tryout scorecards, practice recurrence/reminders, notifications, VOD annotations, and advanced training admin tools.

## Architecture

DeltaCrown is built as a modular Django platform.

Core stack direction:

- Django backend
- Django REST Framework APIs
- PostgreSQL/Supabase database direction
- Redis/Upstash caching direction
- Tailwind CSS frontend
- Vanilla JavaScript for dashboard and interaction layers
- Domain apps for tournaments, organizations, profiles, rankings, economy, competitive operations, missions/contracts, Dropzone, admin, moderation, notifications, commerce, and community

Sensitive flows are organized through service layers, especially for escrow, rankings, tournament operations, and competitive lifecycle actions.

## Current Project State

DeltaCrown is an active product in development with substantial foundations already implemented:

- Tournament engine and match lifecycle
- Team and organization management
- Player profiles and game passport direction
- Crown Point ranking system
- Economy and escrow services
- Competitive hub foundation and unified My Operations feed
- Competitive detail pages for Showdown, Bounty, Missions, Dropzone entries, and Dropzone lobbies
- Showdown MVP result confirmation and admin control
- Bounty admin claim verification/control MVP
- Missions proof submission plus admin verification/control MVP
- Dropzone entry/lobby details and admin scoring/settlement MVP
- Team recruitment plus Team HQ Training foundation
- Public tryout/scrim entry points on team pages
- Tryout to join offer to applicant acceptance membership path
- Player-facing My Team Applications inbox
- Admin and moderation surfaces
- Public-facing dashboards, community, and commerce direction

Some systems are still evolving, especially file-upload proof, richer dispute/review UI, Dropzone user proof/reporting, notifications/reminders, advanced Team HQ training workflows, deeper game API verification, and internal legacy naming cleanup.

## Supported Game Direction

DeltaCrown is game-agnostic by design and currently targets major competitive categories:

- FPS: Valorant, CS2, CODM, Rainbow Six
- MOBA: Dota 2, Mobile Legends
- Battle Royale: PUBG Mobile, Free Fire
- Sports and arcade competition: eFootball, EA FC, Rocket League

New games can be added through the platform's game configuration layer without rebuilding the whole ecosystem.

## Product Vision

DeltaCrown is building the infrastructure layer for competitive gaming communities.

The long-term direction includes:

- Stronger mobile-first experiences
- Deeper team operations
- Better ranking and season systems
- Richer training and scouting workflows
- Sponsor and commerce opportunities
- Local and regional tournament ecosystems
- Global expansion from a Bangladesh-first foundation

DeltaCrown exists to make esports more professional, more trusted, and more accessible.

## Contact

**Founder:** Redwanul Rashik  
**Founded:** 2025  
**Email:** deltacrownhq@gmail.com  
**Tagline:** From the Delta to the Crown - Where Champions Rise.

## License

MIT
