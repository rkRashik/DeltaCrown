# DeltaCrown Screenshot Capture Plan

Practical screenshot and media checklist for future pitch decks, launch presentations, public project books, sponsor decks, user guides, and portfolio case studies.

Use this plan with the current codebase inventory in `DELTACROWN_ROUTE_AND_PAGE_INVENTORY.md`.

## 1. Screenshot Capture Principles

- Capture the platform as an esports ecosystem, not only a tournament site.
- Prefer real UI screens backed by current routes, templates, models, or APIs.
- Use controlled demo accounts and demo entities only.
- Use representative flows: public discovery, profile/Game Passport, teams/Team HQ, tournaments, Match Room, proof/result/dispute workflow, Competitive Hub, economy, community, Arena, and organizer tools where supported.
- For early/in-progress features, visibly label the screenshot or deck caption as "early version".
- Capture desktop and mobile for core user journeys.
- Capture clean states, populated states, and one or two empty states where useful.
- Keep browser chrome hidden or consistent unless the document is a technical walkthrough.
- Prefer high-resolution desktop captures around 1440px wide, tablet around 768-1024px, and mobile around 390-430px.
- Keep screenshots current: if routes, UI, or copy change, refresh the deck media instead of reusing stale captures.

## 2. Safety Rules For Screenshots

Never capture or publish:

- Private user data.
- Real payment proofs.
- Private evidence or proof files.
- KYC documents or KYC review details.
- Admin secrets or credentials.
- Room passwords, lobby join codes, private server links, or private voice/chat links.
- Private messages, Discord chat content, private team chat, support conversations, or sensitive notifications.
- Real withdrawal/top-up approval data.
- Real user balances, emails, phone numbers, addresses, legal names, government IDs, or private social accounts.
- OAuth callback URLs with tokens or codes.
- Debug pages, environment variables, logs, database hostnames, API keys, or production settings.

When capturing admin/internal pages:

- Use seeded demo data or a local/safe staging environment.
- Blur or omit usernames, emails, wallet balances, proofs, KYC, and audit details unless they are fictional demo values.
- Do not run tests or screenshots against a production database.

## 3. Demo-Data Suggestions

- Demo users: `RavenPilot`, `NovaStriker`, `AstraCarry`, `ByteCaster`.
- Demo teams: `Crown Ravens`, `Azure Titans`, `Violet Guard`, `Delta Forge`.
- Demo organization: `CrownForge Esports`.
- Demo tournament: `DeltaCrown Valorant Open`.
- Demo match: `Crown Ravens vs Azure Titans`.
- Demo Game Passports: Riot, Steam, Epic entries with fake gamer tags.
- Demo economy: small fictional DeltaCoin balances and Crown Points totals.
- Demo Competitive Hub:
  - Showdown: "Crown Ravens vs Azure Titans Scrim Challenge".
  - Mission: "Submit three verified match results this week".
  - Bounty: "Best clutch highlight submission".
  - Dropzone: "Friday BR Custom Lobby".
- Demo proof/evidence: use placeholder images labeled "Demo proof" only.
- Demo payment proof: do not show a payment proof image; use a placeholder state or cropped UI that hides the file preview.
- Demo disputes: show high-level status and timeline only, not private evidence.

## 4. Screenshot Table

| Screenshot name | Page / URL | What to show | Why needed | Used in which document/deck | Priority | Notes |
|---|---|---|---|---|---|---|
| Homepage ecosystem hero | `/` | Hero and first ecosystem sections | Establish DeltaCrown as an esports ecosystem | Pitch deck, launch presentation, sponsor deck | High | Live public page is available. |
| Homepage competitive modes | `/` | Section mentioning Showdown, Missions, Bounty, Dropzone | Shows ecosystem beyond tournaments | Pitch deck, project book | High | Label individual modes as early version where needed. |
| About page | `/about/` | Platform overview/content | Brand/project context | Project book, portfolio case study | Medium | Public page available. |
| Public community feed | `/community/` | Community feed with safe demo posts | Shows community layer | Launch presentation, user guide | High | Use demo posts only. |
| Community guidelines | `/legal/community-guidelines/` | Guidelines/rules page | Trust and moderation proof point | Trust section, user guide | Medium | No private data. |
| Arena page | `/arena/` | Watch/Arena widgets and public activity | Shows public fan/spectator surface | Sponsor deck, launch presentation | High | Live public page available. |
| Tournament discovery | `/tournaments/` | Tournament listing/cards and filters | Core marketplace/discovery experience | Launch presentation, sponsor deck, user guide | High | Live public page available. |
| Tournament detail | `/tournaments/<demo-slug>/` | Tournament hero, registration CTA, rules/prizes | Explains what a tournament looks like | Sponsor deck, user guide | High | Use demo tournament. |
| Smart registration | `/tournaments/<demo-slug>/register/` | Registration steps with autofill | Shows player onboarding into events | User guide, launch deck | High | Avoid real payment proof; use demo account. |
| Registration success | `/tournaments/<demo-slug>/register/success/` or smart success URL | Confirmation state | Completes registration flow | User guide | Medium | Demo registration only. |
| Tournament bracket | `/tournaments/<demo-slug>/bracket/` | Live bracket view | Core competitive output | Sponsor deck, launch presentation | High | Use populated demo bracket. |
| Tournament leaderboard | `/tournaments/<demo-slug>/leaderboard/` | Standings/leaderboard | Shows ranking and progression | Sponsor deck, user guide | High | Demo names only. |
| Tournament results | `/tournaments/<demo-slug>/results/` | Final results and placements | Shows outcome/archive value | Launch presentation, project book | Medium | Demo event only. |
| Tournament Hub overview | `/tournaments/<demo-slug>/hub/` | Participant hub overview tabs | Shows player command center | User guide, launch deck | High | Use registered demo player. |
| Tournament Hub squad/matches | `/tournaments/<demo-slug>/hub/` | Squad and matches tabs | Shows team coordination | User guide | High | Avoid private chats or contact details. |
| Match detail/watch | `/tournaments/<demo-slug>/matches/<demo-id>/` | Public match detail/state | Shows match spectator layer | Sponsor deck | Medium | Demo match. |
| Match Room overview | `/tournaments/<demo-slug>/matches/<demo-id>/room/` | Participant room without passwords | Shows operational match workflow | Launch deck, user guide, project book | High | Hide room passwords, private server links, and chat. |
| Match Room result phase | `/tournaments/<demo-slug>/matches/<demo-id>/room/` | Result submission phase UI | Shows proof/result workflow | User guide | High | Use placeholder proof; do not show real evidence. |
| Submit result form | `/tournaments/<demo-slug>/matches/<demo-id>/submit-result/` | Result form fields | Explains result submission | User guide | High | No real proof files. |
| Dispute form | `/tournaments/<demo-slug>/matches/<demo-id>/report-dispute/` | Dispute entry state | Demonstrates trust workflow | User guide, trust section | Medium | Use fake dispute text only. |
| Public profile | `/@<demo-user>/` | Profile hero, tabs, achievements/career | Shows player identity layer | Launch deck, sponsor deck, user guide | High | Demo user only. |
| Game Passport on profile/settings | `/@<demo-user>/` or `/me/settings/` | Passport cards with verified/demo game IDs | Shows identity and game-account layer | Launch deck, sponsor deck | High | Use fake IDs and demo OAuth state. |
| Game Passport rules | `/game-passport-rules/` | Rules/policy content | Shows trust around identity | Trust section, user guide | Medium | Public page. |
| Settings profile section | `/me/settings/` | Profile/settings form with calm demo data | User account management | User guide | Medium | Current page is fragile; screenshot only, no redesign. |
| Settings privacy/safety | `/me/settings/privacy-safety/` if available, or `/me/settings/` tab | Privacy toggles and safety controls | Shows user control | Trust section, user guide | Medium | Verify section route locally/staging. |
| Settings Game Passports | `/me/settings/game-passports/` if available, or `/me/settings/` tab | Passport manager/modal | Game identity management | User guide | High | Use demo IDs; no real OAuth callback. |
| Teams Hub | `/teams/` | Teams landing/hub | Shows team ecosystem | Launch deck, sponsor deck | High | Live public page available. |
| Team Directory | `/teams/directory/` | Browseable team listing | Shows discovery/scouting | Sponsor deck, user guide | High | Demo teams preferred. |
| Find Team / Scouting Grounds | `/teams/find/` | LFT/scouting UI | Shows recruitment workflow | Launch deck, user guide | High | Use demo profiles only. |
| Team detail | `/teams/<demo-team>/` | Public team profile | Sponsor-ready team surface | Sponsor deck, project book | High | Demo team only. |
| Create Team | `/teams/create/` | Team creation form | Player onboarding into teams | User guide | Medium | Demo account. |
| Team HQ overview | `/teams/<demo-team>/manage/` | Manage HQ overview/sidebar | Shows serious team operations | Sponsor deck, user guide | High | Hide sensitive roster/member/contact data. |
| Team HQ recruitment | `/teams/<demo-team>/manage/` | Join requests/recruitment positions | Shows scouting and team-building | User guide, sponsor deck | High | Use demo applications. |
| Team HQ training | `/teams/<demo-team>/manage/` | Training/scrim/practice section | Shows org operations depth | Sponsor deck | Medium | Label early version if incomplete. |
| Team HQ competition hub | `/teams/<demo-team>/manage/` | Competition settings/showdown authority | Shows team competitive control | Sponsor deck, project book | Medium | Use early-version label if workflows are partial. |
| Organization directory | `/orgs/` | Organization listing | Shows org ecosystem | Sponsor deck | Medium | Live public page available. |
| Organization detail | `/orgs/<demo-org>/` | Org profile | Sponsor/organization view | Sponsor deck | Medium | Demo org only. |
| Organization control plane | `/orgs/<demo-org>/control-plane/` | High-level admin surface | Shows org management | Internal deck, sponsor appendix | Low | Avoid private member data. |
| Competitive Hub overview | `/dashboard/competitive/` | Hub cards for Showdown/Missions/Bounty/Dropzone | Shows daily competitive ecosystem | Launch deck, project book | High | Requires auth; label early version. |
| Showdown detail | `/dashboard/competitive/showdowns/<demo-id>/` | Showdown state/timeline | Shows skill-based challenge workflow | User guide, project book | High | Avoid betting language; demo only. |
| Missions detail | `/dashboard/competitive/missions/<demo-id>/` | Mission objective/proof state | Shows repeatable challenge layer | User guide | Medium | Label as early version. |
| Bounty detail | `/dashboard/competitive/bounties/<demo-id>/` | Bounty objective/claim state | Shows skill-based reward workflow | Launch deck, user guide | Medium | Label as early version. |
| Bounty board | `/competition/bounties/` | Public bounty listing | Shows public bounty discovery | Launch deck | Low | Live route returned 500; capture only after fixed, label early version. |
| Dropzone lobby detail | `/dashboard/competitive/dropzone/lobbies/<demo-id>/` | Lobby state and entry/scoring info | Shows BR/custom lobby workflow | Launch deck, user guide | Medium | Label early version; demo only. |
| Dropzone entry detail | `/dashboard/competitive/dropzone/entries/<demo-id>/` | Player entry state | Shows participant view | User guide | Medium | Demo only. |
| Challenge hub | `/competition/challenges/` | Public challenge listing | Shows challenge discovery | Launch deck | Medium | Live public page available. |
| Competition leaderboards | `/competition/leaderboards/` | Global leaderboard/ranking | Shows competitive rankings | Sponsor deck, launch deck | High | Live public page available. |
| Ranking about | `/competition/ranking/about/` | Ranking explanation | Trust/transparency | User guide, trust section | Medium | Public route. |
| Dashboard home | `/dashboard/` | User command center | Shows logged-in player home | User guide, project book | Medium | Requires auth; demo account. |
| My matches | `/dashboard/matches/` or `/my/matches/` | User match list | Shows personal match workflow | User guide | Medium | Current view may be sparse; label early if empty. |
| Wallet Hub | `/wallet/hub/` | Wallet, DeltaCoin, requests, balances | Explains closed-loop utility | User guide, project book | High | Use safe demo balances; do not imply crypto/investment/cash-out. |
| Transaction history | `/transactions/` | Demo transactions | Shows economy audit trail | User guide | Medium | Demo transactions only. |
| Inventory | `/me/inventory/` | Items/inventory | Shows assets layer | Launch deck, user guide | Medium | Demo inventory only. |
| Inventory requests | `/me/inventory/requests/` | Gift/trade requests | Shows social asset flow | User guide | Low | Demo only. |
| Crown Store home | `/crownstore/` | Store home | Shows commerce/store surface | Sponsor deck, launch deck | Medium | Live public page available. |
| Product listing | `/crownstore/products/` | Products grid | Shows marketplace depth | Sponsor deck | Medium | Demo/safe products only. |
| Cart/checkout | `/crownstore/cart/`, `/crownstore/checkout/` | Cart or checkout state | Shows purchase flow | User guide | Low | No real payment details. |
| Notifications inbox | `/notifications/` | Notification list | Shows action center | User guide | Medium | Demo account; no private messages. |
| Notification dropdown/sheet | Any page with nav dropdown | Bell preview and mobile sheet | Shows real-time UX | User guide | Medium | Demo notifications only. |
| Support FAQ | `/faq/` | FAQ content | User support | User guide | Medium | Live public page available. |
| Contact support | `/contact/` | Contact form | Support channel | User guide | Medium | Live public page available. |
| Rules page | `/rules/` | Fair play/platform rules | Trust | User guide, sponsor deck | Medium | Live public page available. |
| Moderation page | `/moderation/` | Moderation policy/surface | Trust | Trust section | Medium | Public route. |
| Spectator tournament list | `/spectator/` | Public spectator list | Spectator mode | Sponsor deck | Low | Live route returned 500; capture only after fixed, label early version. |
| Spectator match | `/spectator/matches/<demo-id>/` | Read-only match scoreboard | Sponsor/spectator story | Sponsor deck | Low | Verify route after spectator fix. |
| TOC shell | `/toc/<demo-slug>/` | Organizer operations shell | Organizer value proposition | Organizer deck, case study | High | Demo tournament only; requires auth. |
| TOC participants/payments/brackets/matches | `/toc/<demo-slug>/` plus API-backed tabs | Organizer workflow sections | Shows operational depth | Organizer deck | Medium | Use demo data; no real payment proof/KYC. |
| TOC dispute queue | `/toc/<demo-slug>/` or API-backed tab | Dispute/review queue | Trust/ops proof | Internal deck | Low | Never show real evidence. |
| TOC analytics | `/toc/<demo-slug>/` or API-backed tab | Registration/match/revenue charts | Sponsor/organizer analytics | Organizer deck | Medium | Demo analytics only. |
| Game Passport admin | `/admin/game-passports/` | Admin dashboard with anonymized demo passports | Trust/admin tooling | Internal ops case study | Low | Internal only; avoid real identity data. |
| Competition admin operations | `/admin/competition/operations/` | Admin review/action cards | Internal operations | Internal ops deck | Low | Staff only; demo data. |
| Financial Fortress | `/fortress/command-center/` | Superadmin economy command center | Internal ops | Internal ops only | Low | Do not use in public decks; never capture real balances/approvals. |
| Mobile API proof | `/api/mobile/v1/health/` or generated API docs | API response or architecture diagram | Mobile roadmap evidence | Technical appendix | Low | Screenshot UI is optional; API routes are not user-facing. |

## 5. Minimum Screenshot Set For Public Launch Presentation

1. Homepage ecosystem hero (`/`).
2. Tournament discovery (`/tournaments/`).
3. Tournament detail with CTA (`/tournaments/<demo-slug>/`).
4. Smart registration (`/tournaments/<demo-slug>/register/`).
5. Public profile with Game Passport (`/@<demo-user>/`).
6. Teams Hub or Team Directory (`/teams/` or `/teams/directory/`).
7. Find Team / Scouting Grounds (`/teams/find/`).
8. Match Room overview without private room data.
9. Tournament bracket or leaderboard.
10. Competitive Hub overview (`/dashboard/competitive/`) labeled early version where needed.
11. Wallet Hub with DeltaCoin as closed-loop platform utility.
12. Community or Arena (`/community/` or `/arena/`).

## 6. Minimum Screenshot Set For Sponsor Deck

1. Homepage ecosystem overview.
2. Tournament discovery with populated event cards.
3. Tournament detail with sponsor/prize/rules sections.
4. Live bracket or leaderboard.
5. Public team detail page.
6. Organization or Team Directory.
7. Public profile/Game Passport.
8. Arena spectator surface.
9. Competitive Hub overview with Showdown/Missions/Bounty/Dropzone labeled early where appropriate.
10. Community feed with demo content.
11. TOC organizer shell or analytics section using demo data.

## 7. Minimum Screenshot Set For User Guide

1. Signup and login.
2. Email/OTP verification.
3. Profile/settings basics.
4. Game Passport manager.
5. Find Team / Scouting Grounds.
6. Create Team and/or Team Invites.
7. Tournament discovery.
8. Smart registration.
9. Tournament Hub.
10. Match Room.
11. Submit result.
12. Report dispute.
13. Wallet Hub and transaction history with demo data.
14. Notifications inbox.
15. FAQ/support/rules pages.

## 8. Early/In-Progress Feature Labeling

Add "early version" or "in progress" captions for:

- Competitive Hub workflows where end-to-end demo data is limited.
- Missions/contracts surfaces.
- Bounty Board until `/competition/bounties/` live 500 is resolved.
- Dropzone pages and APIs.
- Spectator app pages until `/spectator/` live 500 is resolved.
- Team HQ training/tryout/scrim sections if demo data is sparse.
- TOC API-backed tabs that are not fully polished as user-facing screens.
- Mobile API routes, which are API foundations rather than public UI pages.

Suggested caption:

> Early version shown with safe demo data. Final production content, permissions, and data states may differ.

## 9. Wording Constraints For Deck Captions

- Do not claim DeltaCrown is Bangladesh's first esports platform.
- Do not describe DeltaCoin as crypto, an investment, cash-out money, or gambling currency.
- Use "DeltaCoin closed-loop platform utility" where economy wording is needed.
- Do not use betting/gambling language for Bounty or Showdown.
- Use "skill-based challenge/reward workflow" where relevant.
- Use "early version" for MVP or partially implemented surfaces.
