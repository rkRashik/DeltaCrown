# Product features

## Product direction

OwnLobby is a connected esports ecosystem, not only a bracket tool: tournaments and match operations, teams and organizations, player profiles and Game Passports, Ranking Points rankings, a closed-loop Coins utility currency (not a financial asset), team recruitment and training, community, commerce and admin systems. Direction: premium, competitive, community-driven, skill-focused, accessible to Bangladesh-first gamers, mobile-first, with ranking/season depth, scouting, sponsor and commerce opportunities and regional tournament ecosystems as longer-term goals (proposals, not commitments).

Game support is configuration-driven (`apps/games`): FPS (Valorant, CS2, CODM, Rainbow Six), MOBA (Dota 2, Mobile Legends), battle royale (PUBG Mobile, Free Fire) and sports/arcade (eFootball, EA FC, Rocket League) are the targeted categories; a new game is added through the game registry and its passport schema and ranking config rather than new code paths. The supported launch journey is the free solo eFootball tournament flow; other modes are source-only until `BACKLOG.md` says otherwise.

What exists in source and how it behaves. "Implemented" means the code is present and covered by targeted tests; it is not a launch-acceptance claim (see `Documents/Development/STATUS.md` and `BACKLOG.md` for dated acceptance state).

## Accounts and player identity

* Signup with email OTP (pending signup -> 6-digit code -> user created), login by username or email, logout, password reset (generic response, single-use tokens) and signed-in password change; Google sign-in and Discord linking; rate limiting on login, reset and OTP; scheduled account deletion with a sign-in block.
* Public profile at `/@username/`: compact identity header, only widgets that have data (stats, teams, trophies, streams, connect links), follow / follow-request for private accounts, tabs for posts, career, highlights, gear and achievements. Owners see edit prompts; visitors do not see empty placeholders.
* Game Passports and game identities: per-game in-game ID with schema from the game registry, verification via Riot/Epic/Steam/Discord connections where configured, cooldown rules, public IDs (`DC-YY-NNNNNN`).
* Settings live at `/me/settings/` (privacy, platform, notifications, wallet, security). The settings page has its own design guardrails in `AGENTS.md`.

## Tournaments

Lifecycle (`Tournament.ALLOWED_TRANSITIONS`): `draft` -> `pending_approval`/`published` -> `registration_open` <-> `registration_closed` -> `live` -> `completed` -> `archived`; `cancelled` from most states. Formats: single elimination, double elimination, round robin, Swiss, group + playoff; battle-royale scoring services exist.

1. **Discovery**: list with filters, detail page (rules, prizes, schedule, eligibility), spectator and public bracket and results pages. Only published, non-deleted tournaments are public.
2. **Registration**: solo or team entry through a configurable registration form (smart registration / form builder), eligibility checks (game passport/identity, roster and per-tournament rules), free or coin/manual-payment entry, waitlist, organizer approval, check-in window. Registrations have a status workflow (pending -> payment_submitted -> confirmed/rejected/cancelled). Duplicate submissions must not duplicate entries or charges.
3. **Brackets**: generated and published by organizers (generators in `tournament_ops`), editable with an edit log, recovery/repair services, group stages and live draw (WebSocket).
4. **Matches** (`Match.status`): scheduled -> check_in -> ready -> live -> pending_result -> completed; also disputed, forfeit, cancelled. Participants submit results, opponents confirm or dispute, organizers resolve disputes (evidence upload), and `match_authority` decides who may change a score. A score correction cannot change a winner after the next round or the tournament is decided.
5. **Results**: completion pipeline computes standings and final placement; the public results page only shows verified results. Certificates (PDF, optionally S3) and prize claims follow completion.
6. **TOC (Tournament Operations Center)**: organizer console and API (`api/toc/`) for participants, payments, brackets, matches, disputes, announcements, staff, hosting and audit trail.

## Teams, organizations and rankings

* Organizations own teams; independent teams exist. Roles and membership (captain, manager, player, staff), invites, join requests, recruitment, team hub, follower system, announcements, training and media; custom team branding (colors/banner) is preserved on public pages.
* Public pages: `/teams/` hub, `/teams/<slug>/`, `/orgs/`, `/orgs/<slug>/` (verified facts only: founded year, teams, trophies, staff, streams). Manager-only controls are never rendered to visitors.
* Rankings (`competition`): global and per-game team rankings from match reports and verification, tier names and Ranking Points, compare and search on `/competition/rankings/`.

## Wallet and coins

* DeltaCoin wallet per user, ledger of transactions, top-up (manual review), withdrawal requests, prize claims and daily rewards; the shop and inventory spend coins.
* Wallet PIN protects withdrawals (policy and open work in [security.md](security.md)). Withdrawal requests are processed by staff in the Django admin; no payment gateway is called automatically.

## Community, notifications and discovery

* Community feed, posts/comments/likes, Arena, spectator pages and a homepage live feed.
* Notifications: bell popover (desktop) and bottom sheet (mobile), inbox page, categories (tournament, team, economy, social, system, warning), preferences and digests, SSE stream. Read/unread semantics and privacy are server-side.
* SEO: canonical URLs, JSON-LD, sitemaps and robots by `apps/common/seo.py` and `SearchIndexingMiddleware`; private routes are noindex.

## Other modules

Challenges and bounties, Crown Contracts (self-challenge missions), Crown Royale (paid battle-royale lobbies), mobile API v1, support (FAQ, contact), moderation (reports, sanctions). Their supported launch scope is not established; treat them as source-only until `BACKLOG.md` says otherwise.
