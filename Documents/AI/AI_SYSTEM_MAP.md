# DeltaCrown — System Map

**Last Updated:** 2026-03-16
**Purpose:** High-level architecture overview for AI session continuity

---

## Platform Identity

DeltaCrown is a Django 5.2.8 esports platform deployed on Render (512 MB starter plan).
Core value proposition: unified competitive gaming with Game Passports, automated API integrations, and persistent player identities.

---

## System Domains

```
┌─────────────────────────────────────────────────────────┐
│                    IDENTITY DOMAIN                       │
│  accounts ── user_profile ── players ── games            │
│  (auth)      (passports)    (bridge)   (definitions)     │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                  COMPETITION DOMAIN                       │
│  tournaments ── tournament_ops ── leaderboards            │
│  (70 models)   (result pipeline)  (rankings)              │
│  competition ── challenges                                │
│  (independent)  (1v1/team)                                │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                 ORGANIZATION DOMAIN                       │
│  organizations (vNext teams, org hierarchy, Discord)      │
│  teams (LEGACY — being deprecated)                        │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                   ECONOMY DOMAIN                          │
│  economy (wallets, DeltaCrown currency)                   │
│  shop / ecommerce (EMPTY — not implemented)               │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                  PLATFORM SERVICES                        │
│  notifications ── moderation ── search ── dashboard       │
│  siteui (community) ── support ── spectator               │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────┐
│                CORE INFRASTRUCTURE                        │
│  core (service registry, events, health, plugins)         │
│  corelib (brackets, utilities, idempotency)               │
│  common (event bus, API responses, game registry)         │
│  corepages (static/landing pages)                         │
└─────────────────────────────────────────────────────────┘
```

---

## Critical Data Flow

```
User Registration
  → accounts.User (Django auth)
  → user_profile.UserProfile (extended profile)
  → user_profile.GameProfile (per-game identity = Game Passport)
  → user_profile.GameOAuthConnection (OAuth tokens for Riot/Steam/Epic)

Tournament Flow
  → tournaments.Tournament (created by organizer)
  → tournaments.Registration (player/team signs up)
  → tournaments.Bracket + BracketNode (bracket generated)
  → tournaments.Match (scheduled per bracket node)
  → Match result via one of 3 pipelines:
      Pipeline A: MatchService.submit_result() → confirm_result() → signals
      Pipeline B: tournament_ops.ResultSubmissionService → verification → finalize
      Pipeline C: Riot API sync → MatchResultSubmission → finalize (reuses Pipeline B)
  → tournaments.TournamentResult (final placements)
  → tournaments.Certificate (generated on S3)
  → leaderboards (ranking snapshots)

External API Flow
  → OAuth initiate (redirect to Riot/Steam/Epic)
  → Callback → token exchange → GameOAuthConnection stored
  → Riot: periodic Celery sync → fetch match history → correlate to internal matches
  → Steam: link-only (no background sync)
  → Epic: link-only (no background sync)
```

---

## External Integrations

| Provider | Protocol | Status | Background Sync |
|----------|----------|--------|----------------|
| Riot Games | OAuth 2.0 (RSO) | Production-ready | Yes (Celery, every 20 min) |
| Steam | OpenID 2.0 | Functional | No |
| Epic Games | OAuth 2.0 | Functional | No |
| Google | OAuth 2.0 (allauth) | Functional | N/A |
| Discord | Bot + Webhooks | Functional | Yes (role sync, announcements) |
| Cloudinary | Storage API | Functional | N/A |
| S3 | Storage API | Functional | N/A |
| Sentry | Error tracking | Active | N/A |
| Prometheus | Metrics | Active | N/A |

---

## Infrastructure

| Component | Service | Tier |
|-----------|---------|------|
| Application | Render Web Service | Starter (512 MB) |
| Database | Neon PostgreSQL | — |
| Cache/Broker | Upstash Redis | — |
| Static files | WhiteNoise | Built-in |
| Media storage | Cloudinary + S3 | — |
| Monitoring | Sentry + Prometheus | — |
| Keep-alive | cron-job.org | — |

Single container runs: Daphne (ASGI) + Celery Worker (concurrency=1) + optional Discord Bot.

---

## Known Duplicate Systems

| System | Location A | Location B |
|--------|-----------|-----------|
| Teams | `teams/` (legacy) | `organizations/` (vNext) |
| Bounties | `user_profile/models/bounties.py` | `tournaments/models/bounty.py` |
| Notification Prefs | `notifications/models.py` | `user_profile/models/settings.py` |
| Game Identity Config | `games/models.py` | `user_profile/models/game_passport_schema.py` |
| Disputes | `tournaments/models/match.py` (legacy) | `tournaments/models/dispute.py` (Phase 6) |
| Certificates | `tournaments/models/certificate.py` | `tournaments/models/stats_certs.py` |
| Staffing | `tournaments/models/staff.py` (DEPRECATED) | `tournaments/models/staffing.py` |
| Challenges | `competition/` app | `challenges/` app |

---

## File Counts by App (approximate)

| App | Models | Migrations | Services | Tasks |
|-----|--------|-----------|----------|-------|
| tournaments | 70 classes in 42 files | 34 | 10+ | 11 |
| organizations | 15+ | 37 | 5+ | 15 |
| user_profile | 18 files | 37 | 10+ | 2 |
| tournament_ops | 5+ | 6 | 5+ | 3 |
| leaderboards | 5+ | — | — | 11 (unscheduled) |
| economy | 5+ | — | — | — |
| notifications | 5+ | — | — | 1 |
