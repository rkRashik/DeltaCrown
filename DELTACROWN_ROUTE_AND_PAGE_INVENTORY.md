# DeltaCrown Route And Page Inventory

Generated from the current DeltaCrown Django codebase and spot checks against `https://deltacrown.xyz/`.

Scope notes:

- This inventory focuses on user-facing pages and important internal/admin/API surfaces.
- Status is based on visible URL routes, templates, views, models, APIs, and limited safe live public checks.
- "Available" means the route/page exists and has visible code support. It does not guarantee every data state is complete.
- "Early version" means the route exists but the feature appears MVP, partial, API-heavy, or dependent on limited workflows.
- "In progress" means code exists but behavior is incomplete, inconsistent, or failed public live checks.
- "Unclear" means the codebase contains support, but current completeness or intended owner/audience is not fully clear.
- Do not capture or publish private user data, real proof files, payment proof images, KYC records, room passwords, admin secrets, or private messages from any route listed here.

## 1. Route Mount Summary

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/` | Site UI mount | Homepage, about, community, arena, legal/community APIs | Public visitors | Yes | Pitch deck, launch deck, project book | Available | Mounted from `apps.siteui.urls`; live `/`, `/about/`, `/community/`, `/arena/` returned 200. |
| `/account/` | Account/auth mount | Login, signup, logout, OTP verification, password reset/change, OAuth links | Players, organizers | Yes | User guide, launch deck | Available | Mounted from `apps.accounts.urls`; live login/signup returned 200. |
| `/accounts/` | Allauth/fallback auth mount | Optional allauth routes or redirects to `/account/` | Players | No | User guide appendix | Available | Fallback redirects exist if allauth unavailable. |
| `/teams/`, `/orgs/` | Organizations and Teams mount | Team hub, team directory, team creation, Team HQ, org directory/control surfaces | Players, teams, organizations | Yes | Sponsor deck, user guide, project book | Available | Mounted at root via `apps.organizations.urls`; live `/teams/` and `/orgs/` returned 200. |
| `/api/vnext/` | Organizations API mount | Team/org creation, Team HQ mutations, recruitment, scouting, training, community/media, invites | App frontend, team managers | No | Technical appendix | Available | API-only; do not screenshot JSON unless needed for technical docs. |
| `/competition/` | Competition mount | Match reports, rankings/leaderboards, challenge hub, bounty board | Competitors, teams | Yes | Launch deck, ecosystem overview | Early version | Public challenge hub returned 200; bounty board route exists but live `/competition/bounties/` returned 500. |
| `/tournaments/` | Tournament mount | Tournament discovery, detail, registration, player dashboard, lobby/hub, bracket, match room, result/dispute flows | Players, teams, organizers, spectators | Yes | Launch deck, sponsor deck, user guide | Available | Live `/tournaments/` returned 200. |
| `/toc/` | Tournament Operations Center shell | Organizer SPA shell and form configuration page | Organizers, staff | Yes | Organizer deck, technical case study | Early version | Requires auth; live unknown slug redirected to login as expected. |
| `/api/toc/` | TOC API mount | Organizer operations APIs: lifecycle, participants, payments, brackets, matches, disputes, settings, analytics, staff, audit, comms | Organizers, staff, frontend | No | Technical appendix, ops guide | Early version | Large API surface; label as organizer/staff/internal. |
| `/api/tournaments/` | Tournament REST API mount | Tournament CRUD, discovery, registrations, payments, brackets, matches, results, leaderboards, payouts, certificates, analytics | Frontend, integrations, staff | No | Technical appendix | Available | DRF router and additional APIs. |
| `/api/staffing/`, `/api/match-ops/`, `/api/audit-logs/`, `/api/organizer/help/` | Organizer service API mounts | Staffing, match operations, audit logs, help/onboarding | Organizers, staff, frontend | No | Organizer technical appendix | Early version | Backend/API surfaces, not standalone pages. |
| `/api/stats/v1/`, `/api/tournaments/v1/history/`, `/api/leaderboards/v2/`, `/api/stats/v2/` | Stats and analytics API mounts | User/team stats, match history, analytics, leaderboards, seasons | Frontend, analytics, product | No | Technical appendix | Available | API foundation for public/user stats. |
| `/api/v1/` | Challenge/Bounty API mount | Showdown/challenge and Bounty lifecycle APIs | Teams, competitive hub frontend | No | Technical appendix | Early version | Use "skill-based challenge/reward workflow"; avoid betting language. |
| `/api/v1/contracts/` | Missions/contracts API mount | Mission templates, enrollment, proof submission | Players, competitive hub frontend | No | Technical appendix | Early version | API exists; no dedicated public mission landing page found. |
| `/api/v1/royale/` | Dropzone API mount | Battle royale lobby listing, reservation, entries | Players, competitive hub frontend | No | Technical appendix | Early version | API and admin support exist; public dashboard details exist for entries/lobbies. |
| `/api/mobile/v1/` | Mobile API mount | Mobile health, auth, profile, Game Passports, tournaments, teams, matches, notifications | Mobile app/client | No | Mobile roadmap, technical appendix | Early version | Clean route foundation exists. |
| `/spectator/` | Spectator mount | Read-only tournament/match spectator pages and fragments | Public spectators | Yes | Public launch, sponsor deck | In progress | Code/templates exist, but live `/spectator/` returned 500. |
| `/notifications/` | Notifications mount | Notification inbox, feed, actions, SSE stream | Logged-in users | Yes | User guide | Available | Requires auth; live redirected to login as expected. |
| `/dashboard/` | User dashboard mount | User command center and my matches | Logged-in users | Yes | User guide, product deck | Available | Requires auth; live redirected to login as expected. |
| `/dashboard/competitive/` | Competitive Hub mount | Showdown, Missions, Bounty, Dropzone operation hub and detail pages | Logged-in competitors, team captains | Yes | Launch deck, project book | Early version | Requires auth; backed by APIs/models; label early where workflows are partial. |
| `/crownstore/` | Crown Store mount | Store home, products, cart, checkout, wishlist | Players, buyers | Yes | Sponsor deck, launch deck | Available | Live `/crownstore/` returned 200. |
| `/wallet/`, `/wallet/hub/`, `/deposit/`, `/withdraw/`, `/transactions/` | Economy mount | Wallet hub, transactions, deposit/withdrawal request pages, payment methods, inventory | Logged-in users | Yes | User guide, economy explainer | Available | Requires auth; DeltaCoin must be described as closed-loop platform utility. |
| `/fortress/command-center/` | Financial Fortress mount | Superadmin economy operations | Superadmins only | No | Internal ops documentation | Available | Live redirected to admin login as expected; do not capture sensitive balances or approval data. |
| `/admin/`, `/admin/game-passports/`, `/admin/competition/*`, `/admin/maintenance/` | Admin mounts | Django admin, Game Passport admin, competition ops/status, maintenance | Staff/admin only | No | Internal runbook only | Available | Internal/admin-only; do not use in public decks unless anonymized mock/demo state. |
| `/search/` | Search page | Site search | Public/auth users | Maybe | User guide | Available | Direct search view mounted in root URLconf. |
| `/privacy/`, `/terms/`, `/cookies/`, `/faq/`, `/contact/`, `/moderation/`, `/rules/` | Legal/support pages | Policies, help, contact, moderation and rules | Public visitors, players | Yes | User guide, trust section | Available | Live privacy/terms/FAQ/contact/rules returned 200. |
| `/@<username>/`, `/me/settings/`, `/profile/api/game-passports/*` | User profile mount | Public profiles, settings, privacy, follow lists, Game Passports, profile APIs | Players | Yes | Launch deck, user guide, portfolio case study | Available | User profile URLs are mounted last to avoid catch-all conflicts. |

## 2. Public Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/` | Homepage | Public ecosystem landing page | Public visitors, players, sponsors | Yes | Pitch deck, launch presentation, sponsor deck | Available | Live 200. Homepage copy positions DeltaCrown as an esports ecosystem. |
| `/about/` | About | Public platform/about page | Public visitors, sponsors | Yes | Project book, portfolio case study | Available | Live 200. |
| `/community/` | Community | Public/community feed surface with JSON feed APIs | Players, community visitors | Yes | Launch deck, user guide | Available | Live 200; community APIs support posts, comments, polls, sidebar, preferences. |
| `/legal/community-guidelines/` | Community Guidelines | Rules for public community behavior | Players, moderators | Yes | User guide, trust section | Available | Template exists under `templates/pages/community_guidelines.html`. |
| `/arena/` | Arena | Public watch/arena surface with async widget data and voting | Public spectators, fans | Yes | Launch deck, sponsor deck | Available | Live 200; `/watch/` redirects here. |
| `/watch/` | Watch redirect | Compatibility redirect to Arena | Public spectators | No | None | Available | Redirect route. |
| `/search/` | Search | Global site search | Players, visitors | Maybe | User guide | Available | Root-level route. |
| `/privacy/` | Privacy Policy | Legal/privacy content | Public visitors | Yes | Trust section | Available | Live 200. |
| `/terms/` | Terms of Service | Legal/terms content | Public visitors | Yes | Trust section | Available | Live 200. |
| `/cookies/` | Cookie Policy | Cookie policy content | Public visitors | Low | Trust appendix | Available | Code route exists. |
| `/faq/` | FAQ | Support FAQ | Players, organizers | Yes | User guide | Available | Live 200. |
| `/contact/` | Contact | Support/contact page | Players, partners | Yes | User guide, sponsor deck | Available | Live 200. |
| `/moderation/` | Moderation | Moderation/trust page | Players, moderators | Yes | Trust section | Available | Route/template exists. |
| `/rules/` | Rules | Platform rules | Players, organizers | Yes | User guide, trust section | Available | Live 200. |
| `/newsletter/subscribe/` | Newsletter subscribe | Newsletter signup endpoint | Public visitors | No | Launch checklist | Available | Endpoint, not a standalone deck screenshot. |
| `/riot.txt`, `/robots.txt`, `/sitemap.xml`, `/sitemap-<section>.xml` | SEO/crawler endpoints | Verification and SEO metadata | Crawlers, admins | No | Technical appendix | Available | Do not present as product pages. |

## 3. Account/Auth Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/account/login/` | Login | User login | Players, organizers, staff | Yes | User guide | Available | Live 200. |
| `/account/logout/` | Logout | User logout | Logged-in users | No | User guide appendix | Available | Route exists. |
| `/account/signup/` | Signup | New account registration | New users | Yes | Launch deck, user guide | Available | Live 200. |
| `/account/verify/`, `/account/verify/otp/` | Email OTP verification | Verify email/OTP after signup | New users | Yes | User guide | Available | OTP templates/routes exist. |
| `/account/verify/resend/` | Resend OTP | Resend verification OTP | New users | No | User guide | Available | Endpoint route. |
| `/account/password_reset/` | Password reset | Start password reset | Users | Yes | User guide | Available | Template route exists. |
| `/account/password_reset/done/` | Password reset sent | Confirmation after reset request | Users | No | User guide | Available | Template route exists. |
| `/account/reset/<uidb64>/<token>/` | Password reset confirm | Reset password from emailed token | Users | No | User guide | Available | Avoid screenshots containing real tokens. |
| `/account/reset/done/` | Password reset complete | Reset completion page | Users | No | User guide | Available | Route exists. |
| `/account/password_change/` | Password change | Change password while logged in | Logged-in users | Maybe | User guide | Available | Requires auth. |
| `/account/google/login/`, `/account/google/callback/` | Google OAuth | Google login/link flow | Players | No | User guide appendix | Available | Do not capture OAuth tokens or account emails. |
| `/account/discord/link`, `/account/discord/callback/`, `/account/discord/unlink/` | Discord account linking | Link/unlink Discord account | Players, teams | Maybe | User guide | Available | Also used by settings connection flows. |
| `/account/me/settings/account-deletion/*` | Account deletion API | Schedule, cancel, and query account deletion | Logged-in users | No | Trust/internal docs | Available | API-only; never screenshot real deletion state. |

## 4. Profile And Game Passport Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/@<username>/` | Public Profile | Public player profile with tabs and privacy-aware data | Players, scouts, teams, spectators | Yes | Launch deck, sponsor deck, user guide, portfolio | Available | Canonical profile route; legacy `/u/<username>/`, `/players/<username>/`, `/user/u/<username>/` redirect. |
| `/@<username>/activity/` | Profile Activity | Public/profile activity view | Players, scouts | Yes | User guide | Available | Route exists. |
| `/@<username>/followers/` | Followers | Follower list | Players | Maybe | User guide | Available | Privacy may affect content. |
| `/@<username>/following/` | Following | Following list | Players | Maybe | User guide | Available | Privacy may affect content. |
| `/@<username>/follow-requests/` | Follow Requests | Follow request page for private account flows | Players | Maybe | User guide | Available | Likely owner/auth sensitive; use demo data only. |
| `/me/settings/` | Profile Settings | Settings surface for profile, connections, career/LFT, privacy, platform prefs, passports, loadout, stream, security, notifications, community, wallet, inventory, danger zone | Logged-in users | Yes | User guide, product book | Available | Requires auth; current implementation is fragile. Preserve settings contracts. |
| `/me/settings/<section>/` | Settings deep link | Direct settings section route | Logged-in users | Yes | User guide | Available | Concrete API routes take precedence. |
| `/me/privacy/` | Profile Privacy | Owner privacy settings/profile privacy page | Logged-in users | Maybe | User guide | Available | Route exists. |
| `/game-passport-rules/` | Game Passport Rules | Policy/rules for Game Passport identity | Players | Yes | Trust section, user guide | Available | Public route. |
| `/api/game-passports/*`, `/profile/api/game-passports/*` | Game Passport API | List/create/update/delete passports, identity availability, OTP delete aliases | Settings frontend | No | Technical appendix | Available | Use only anonymized demo IDs in docs. |
| `/api/oauth/riot/*`, `/api/oauth/epic/*`, `/api/oauth/steam/*` and `/profile/api/oauth/*` | Game Passport OAuth | Riot/Epic/Steam OAuth connect/callback flows | Players | No | User guide appendix | Available | Never capture OAuth callbacks with real tokens. |
| `/api/passports/toggle-lft/`, `/set-visibility/`, `/pin/`, `/reorder/` | Passport actions | LFT, visibility, pinning, order actions | Players | No | Technical appendix | Available | API-only. |
| `/api/profile/showcase/*`, `/api/profile/about/*`, `/api/profile/highlights/*`, `/api/profile/posts/*` | Profile dynamic content APIs | Showcase, about items, highlights, posts | Profile frontend | No | Technical appendix | Early version | API surface exists; UI completeness depends on profile implementation. |
| `/api/profile/<username>/follow/`, `/unfollow/`, `/follow/status/`, `/followers/`, `/following/`, `/mutual/` | Follow APIs | Follow/unfollow and list data | Players | No | Technical appendix | Available | API-only. |
| `/legacy/@<username>/achievements/`, `/match-history/`, `/certificates/` | Legacy profile component pages | Older standalone profile subpages | Players | Low | Archive/reference only | Early version | Mark legacy; main profile route is canonical. |
| `/me/kyc/upload/`, `/me/kyc/resubmit/<id>/`, `/me/settings/security/kyc/status/` | KYC settings/support routes | User KYC upload/status/resubmit | Logged-in users | No | Internal/user guide only with mock state | Available | Do not capture real KYC records. |

## 5. Teams, Organizations, Team HQ, Recruitment, Scouting

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/teams/` | Teams Hub | Main teams landing/hub | Players, teams, scouts | Yes | Launch deck, sponsor deck | Available | Live 200. |
| `/teams/filter/` | Team Hub Filter | Filtered hub partial/data view | Players | No | Technical appendix | Available | Support route for hub filtering. |
| `/teams/directory/` | Team Directory | Public team listing | Players, scouts, sponsors | Yes | Sponsor deck, user guide | Available | Template exists. |
| `/teams/find/` | Find Team / Scouting Grounds | LFT/scouting/recruitment discovery surface | Players looking for teams, teams recruiting | Yes | Launch deck, user guide | Available | Name as Scouting Grounds/LFT where useful. |
| `/teams/invites/` | Team Invites | Team invite dashboard | Logged-in players | Yes | User guide | Available | Requires auth. |
| `/teams/create/` | Create Team | Team creation page | Players, team owners | Yes | User guide | Available | Requires auth. |
| `/teams/<team_slug>/` | Team Detail | Public team profile/detail page | Public visitors, players, sponsors | Yes | Sponsor deck, project book | Available | Code includes public team template. |
| `/teams/<team_slug>/manage/` | Team HQ / Manage HQ | Team roster, settings, training, competition hub, community/media, recruitment, treasury, sponsors, store sections | Team owners/managers | Yes | Sponsor deck, organizer/user guide | Available | Requires permissions; use demo team only. |
| `/orgs/` | Organization Directory | Public org listing/rankings | Players, sponsors | Yes | Sponsor deck | Available | Live 200. |
| `/orgs/create/` | Create Organization | Organization creation page | Team owners/org leaders | Yes | User guide | Available | Requires auth. |
| `/orgs/<org_slug>/` | Organization Detail | Public organization page | Public, sponsors, teams | Yes | Sponsor deck | Available | Route exists. |
| `/orgs/<org_slug>/hub/` | Organization Hub | Organization management/overview hub | Org members/leaders | Yes | Sponsor deck, ops guide | Available | Auth/permissions likely required. |
| `/orgs/<org_slug>/control-plane/` | Organization Control Plane | Organization control surface | Org owners/admins | Maybe | Internal/team guide | Available | Requires auth/permissions; avoid sensitive member data. |
| `/orgs/<org_slug>/teams/<team_slug>/` | Org-scoped Team Detail | Canonical team detail under org | Public/team viewers | Yes | Sponsor deck | Available | Route exists. |
| `/orgs/<org_slug>/teams/<team_slug>/manage/` | Org-scoped Team HQ | Team management under org context | Team managers | Yes | User guide | Available | Requires permissions. |
| `/api/vnext/system/players/lft/`, `/api/system/players/lft/` | Scout Radar API | LFT player feed | Teams, frontend | No | Technical appendix | Available | API-only. |
| `/api/vnext/system/scrims/active/`, `/api/system/scrims/active/` | Active Scrims API | Active scrim requests | Teams, frontend | No | Technical appendix | Early version | API-only. |
| `/api/vnext/teams/<slug>/training/*` | Team Training APIs | Scrims, tryouts, practice, VOD workflows | Team managers | No | Technical appendix | Early version | API-only; no standalone public page beyond Team HQ. |
| `/api/vnext/teams/<slug>/recruitment/*`, `/apply/`, `/join-requests/*`, `/tryout/*` | Recruitment APIs | Applications, join requests, positions, requirements, tryouts | Players, team managers | No | User guide appendix | Available | API backing for Team HQ/recruitment. |

## 6. Tournament Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/tournaments/`, `/tournaments/browse/` | Tournament Discovery | Browse tournament cards/list | Players, teams, spectators | Yes | Launch deck, sponsor deck, user guide | Available | Live 200. |
| `/tournaments/create/` | Tournament Creation Wizard | Public hosting/tournament creation page | Organizers | Yes | Organizer deck, sponsor deck | Available | Route/template exists. |
| `/tournaments/my/` | My Tournaments | Player tournament dashboard | Logged-in players | Yes | User guide | Available | Requires auth. |
| `/tournaments/my/matches/` | My Tournament Matches | Player tournament matches view | Logged-in players | Yes | User guide | Available | Requires auth. |
| `/tournaments/<slug>/` | Tournament Detail | Public tournament detail and CTA states | Players, teams, spectators | Yes | Launch deck, sponsor deck | Available | Template exists. |
| `/tournaments/<slug>/state/`, `/widgets/save/`, `/api/prizes/` | Tournament detail APIs | Mobile/detail widget state and prize overview | Frontend | No | Technical appendix | Available | API/JSON support routes. |
| `/tournaments/<slug>/register/`, `/register/smart/` | Smart Registration | Register for a tournament with profile/team autofill | Players, teams | Yes | User guide, launch deck | Available | Smart registration is primary. |
| `/tournaments/<slug>/register/smart/success/<id>/`, `/register/success/` | Registration Success | Successful registration confirmation | Players | Yes | User guide | Available | Use demo registration only. |
| `/tournaments/registration/<id>/payment/upload/` | Payment Proof Upload | Upload tournament registration payment proof | Players | No | Internal/user guide with mock state only | Available | Do not capture real payment proofs. |
| `/tournaments/registration/<id>/payment/complete/` | Payment Complete/Retry | Complete or retry registration payment | Players | No | User guide with mock state only | Available | Avoid real payment data. |
| `/tournaments/<slug>/withdraw/` | Withdraw Registration | Withdraw from tournament | Registered players/teams | Maybe | User guide | Available | Requires auth. |
| `/tournaments/<slug>/bracket/` | Live Bracket | Public bracket view | Players, spectators, sponsors | Yes | Launch deck, sponsor deck | Available | Template exists. |
| `/tournaments/<slug>/leaderboard/` | Tournament Leaderboard | Tournament standings/leaderboard | Players, spectators | Yes | Sponsor deck, launch deck | Available | Template exists. |
| `/tournaments/<slug>/results/` | Tournament Results | Final/active results page | Players, spectators, sponsors | Yes | Launch deck, project book | Available | Template exists. |
| `/tournaments/<slug>/lobby/` | Tournament Lobby | Participant lobby; current note says redirects to Hub v3 | Registered players | Yes | User guide | Available | Route exists; may redirect to hub behavior. |
| `/tournaments/<slug>/hub/` | Tournament Hub | Unified participant mission control: overview, squad, matches, bracket, standings, resources, prizes, support | Registered players, teams | Yes | Launch deck, user guide | Available | Rich template and APIs exist. |
| `/tournaments/<slug>/check-in/`, `/checkin/` | Tournament Check-in | Participant check-in actions | Registered players/teams | Maybe | User guide | Available | Use demo event only. |
| `/tournaments/<slug>/groups/standings/` | Group Standings | Public group standings | Players, spectators | Yes | Sponsor deck | Available | Route/template exists. |
| `/tournaments/<slug>/draw/director/` | Group Draw Director | Organizer/director draw control | Organizers | Maybe | Organizer guide | Available | Internal/organizer-oriented. |
| `/tournaments/<slug>/draw/live/` | Group Draw Live | Public draw ceremony | Spectators, players | Yes | Launch deck | Available | Template exists. |
| `/tournaments/<slug>/spectate/` | Tournament Spectate | Public spectator hub for a tournament | Spectators | Yes | Sponsor deck | Available | Separate from `/spectator/` app. |
| `/tournaments/hub/` | Legacy hub redirect | Redirect to tournament list | Public | No | None | Available | Compatibility route. |

## 7. Match Room, Result, Proof, Dispute Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/tournaments/<slug>/matches/<match_id>/` | Match Detail / Watch | Public match detail/watch page | Players, spectators | Yes | Launch deck, sponsor deck | Available | Template exists. |
| `/tournaments/<slug>/matches/<match_id>/state/` | Match Center State API | Live match state | Frontend | No | Technical appendix | Available | API-only. |
| `/tournaments/<slug>/matches/<match_id>/fan-pulse/vote/` | Fan Pulse Vote | Fan poll/vote action | Spectators | Maybe | Sponsor deck | Early version | Action endpoint; show only with demo data. |
| `/tournaments/<slug>/matches/<match_id>/room/` | Match Room | Participant-only room for check-in, lobby/setup phases, result submission, disputes | Registered players/teams | Yes | Launch deck, user guide, project book | Available | Requires auth/permissions; never capture room passwords/private lobby info. |
| `/tournaments/<slug>/matches/<match_id>/room/check-in/` | Match Room Check-in | Match-specific check-in | Participants | Maybe | User guide | Available | Endpoint route. |
| `/tournaments/<slug>/matches/<match_id>/room/workflow/` | Match Room Workflow | Match room workflow state/API | Participants/frontend | No | Technical appendix | Available | API/partial route. |
| `/tournaments/<slug>/matches/<match_id>/submit-result/` | Submit Result | Result submission form | Participants | Yes | User guide | Available | Do not capture private evidence or real proof uploads. |
| `/tournaments/<slug>/matches/<match_id>/report-dispute/` | Report Dispute | Dispute submission | Participants | Maybe | Trust/user guide | Available | Use fake/demo dispute only. |
| `/dashboard/competitive/proofs/<proof_id>/file/` | Mission proof file | Protected proof file delivery | Authorized users/staff | No | Internal only | Available | Never capture real proof files. |
| `/dashboard/competitive/match-proofs/<submission_id>/file/` | Match proof file | Protected match proof delivery | Authorized users/staff | No | Internal only | Available | Sensitive evidence route. |
| `/dashboard/competitive/dispute-evidence/<evidence_id>/file/` | Dispute evidence file | Protected dispute evidence delivery | Authorized users/staff | No | Internal only | Available | Sensitive evidence route. |
| `/dashboard/competitive/match-media/<media_id>/file/` | Match media file | Protected match media delivery | Authorized users/staff | No | Internal only | Available | Sensitive media route. |
| `/competition/matches/report/` | Competition Match Report Form | Report non-tournament competitive match | Logged-in users | Maybe | User guide | Available | Requires auth. |
| `/competition/matches/` | Competition Match Reports | List match reports | Players/staff | Maybe | User guide | Available | Route/template exists. |
| `/competition/matches/<id>/` | Competition Match Report Detail | Match report detail and verification state | Players/staff | Maybe | User guide | Available | Route/template exists. |
| `/competition/matches/<id>/confirm/`, `/dispute/` | Match report verification actions | Confirm/dispute reported match | Participants | No | Technical appendix | Available | Mutating routes; do not demo with real disputes. |

## 8. Competitive Hub Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/dashboard/competitive/` | Competitive Hub | Authenticated hub for Showdown, Missions, Bounty, Dropzone operations | Players, team captains | Yes | Launch deck, project book, user guide | Early version | Requires auth; route/template/API support exists. |
| `/dashboard/competitive/showdowns/<challenge_id>/` | Showdown Detail | Authenticated Showdown operation detail | Team captains/participants | Yes | User guide, project book | Early version | Use skill-based challenge wording; avoid gambling/betting language. |
| `/dashboard/competitive/missions/<enrollment_id>/` | Mission Detail | Authenticated Mission/contract enrollment detail | Players | Yes | User guide | Early version | API/model support exists; no dedicated public mission landing page found. |
| `/dashboard/competitive/bounties/<bounty_id>/` | Bounty Detail | Authenticated Bounty detail | Players/teams | Yes | User guide | Early version | Skill-based reward workflow. |
| `/dashboard/competitive/bounty-claims/<claim_id>/` | Bounty Claim Detail | Bounty claim review/detail | Claimants/staff | Maybe | User guide/internal | Early version | Avoid real claim proof data. |
| `/dashboard/competitive/dropzone/lobbies/<lobby_id>/` | Dropzone Lobby Detail | Authenticated Dropzone lobby detail | Players, staff | Yes | Launch deck/user guide | Early version | Code says operator scoring; use demo lobby. |
| `/dashboard/competitive/dropzone/entries/<entry_id>/` | Dropzone Entry Detail | Authenticated Dropzone entry detail | Players | Yes | User guide | Early version | Use demo entry only. |
| `/dashboard/competitive/review/` | Competitive Review Workspace | Review workspace for competitive operations | Staff/internal reviewers | No | Internal ops guide | Available | Staff member required. |
| `/dashboard/competitive/disputes/` | Competitive Dispute Center | User-facing/staff dispute review grouping | Logged-in users/staff | Maybe | Trust/internal docs | Available | Avoid private evidence screenshots. |
| `/api/v1/competitive/my-operations/` | My Competitive Operations API | Aggregated operations feed | Competitive Hub frontend | No | Technical appendix | Early version | API-only. |

## 9. Showdown, Missions, Bounty, Dropzone Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/competition/challenges/` | Challenge / Showdown Hub | Public challenge listing | Players, teams | Yes | Launch deck | Available | Live 200. Use "Showdown" when entry-fee/escrow workflow is relevant. |
| `/competition/challenges/<reference_code>/` | Challenge Detail | Public challenge detail by reference code | Players, teams | Yes | User guide | Available | Route/template exists. |
| `/api/v1/challenges/` | Challenge/Showdown API | Create/list challenges, including Showdown-style entry-fee workflows | Team captains/frontend | No | Technical appendix | Early version | DeltaCoin is closed-loop platform utility, not crypto/investment/cash-out. |
| `/api/v1/challenges/<ref>/`, `/accept/`, `/decline/`, `/cancel/`, `/schedule/`, `/result/`, `/dispute/` | Challenge lifecycle APIs | Challenge/Showdown lifecycle and disputes | Teams/frontend | No | Technical appendix | Early version | API-only. |
| `/competition/bounties/` | Bounty Board | Public active bounty board | Players, teams | Yes | Launch deck | In progress | Route/template exists, but live `/competition/bounties/` returned 500. Label early/in progress. |
| `/api/v1/bounties/`, `/api/v1/bounties/<bounty_id>/claim/` | Bounty APIs | Create/list bounties and submit claims | Players, teams/frontend | No | Technical appendix | Early version | Skill-based reward workflow; no betting language. |
| `/api/v1/teams/<team_slug>/bounties/` | Team Bounties API | Team-scoped bounty list | Teams/frontend | No | Technical appendix | Early version | API-only. |
| `/api/v1/contracts/templates/`, `/enroll/<template_id>/`, `/enrollments/<id>/`, `/proofs/`, `/my/` | Missions API | Mission templates, enrollments, proof submissions | Players/frontend | No | Technical appendix | Early version | No dedicated public mission page found; label as early version. |
| `/api/v1/royale/lobbies/`, `/lobbies/<id>/`, `/reserve/`, `/entries/<id>/cancel/`, `/my/` | Dropzone API | Dropzone lobby list/detail, reservation, entry cancellation, my entries | Players/frontend | No | Technical appendix | Early version | API-only plus dashboard detail pages; use demo data only. |

## 10. Wallet/Economy Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/wallet/` | Wallet | Legacy wallet entry | Logged-in users | Maybe | User guide | Available | Code comment says older page redirects/relates to settings; verify exact behavior in demo. |
| `/wallet/hub/` | Wallet Hub | Primary wallet/economy hub | Logged-in users | Yes | User guide, economy explainer | Available | Live redirects to login when logged out. Use "DeltaCoin closed-loop platform utility." |
| `/wallet/dashboard/` | Wallet Dashboard | Legacy wallet dashboard | Logged-in users | Low | Archive/user guide | Available | Legacy route. |
| `/deposit/` | Deposit/top-up transactions | Transaction/top-up page | Logged-in users | Maybe | User guide | Available | Avoid real payment details. |
| `/withdraw/`, `/withdrawal/request/` | Withdrawal Request | Withdrawal request page | Logged-in users | Maybe | Internal/user guide | Available | Do not imply DeltaCoin cash-out/investment; verify product wording before public use. |
| `/transactions/` | Transaction History | Wallet transaction history | Logged-in users | Yes | User guide | Available | Use safe demo transaction data. |
| `/withdrawal/<pk>/` | Withdrawal Status | Withdrawal status detail | Logged-in users | No | Internal/user guide | Available | Sensitive; avoid screenshots with real requests. |
| `/withdrawal/history/` | Withdrawal History | Withdrawal request history | Logged-in users | Maybe | User guide | Available | Demo data only. |
| `/payment-methods/` | Payment Methods | Payment method management page | Logged-in users | No | User guide/internal | Available | Avoid real methods or numbers. |
| `/pin/setup/` | Wallet PIN Setup | PIN setup page | Logged-in users | Maybe | User guide | Available | Do not capture real OTP/PIN. |
| `/me/inventory/` | My Inventory | User inventory | Logged-in users | Yes | User guide, project book | Available | Requires auth. |
| `/profiles/<username>/inventory/` | Public/User Inventory | Inventory view for a profile | Players | Maybe | User guide | Available | Privacy-sensitive; use demo public profile. |
| `/me/inventory/requests/` | Inventory Requests | Gift/trade requests inbox | Logged-in users | Maybe | User guide | Available | Use demo data. |
| `/me/inventory/gift/` | Gift Item | Gift inventory item action | Logged-in users | No | User guide appendix | Available | Mutation flow; avoid real transfers. |
| `/me/inventory/trade/request/`, `/trade/respond/` | Trade Flow | Propose/respond to trades | Logged-in users | Maybe | User guide | Available | Demo-only. |
| `/api/daily-reward/status/`, `/claim/` | Daily Reward API | Daily login reward status/claim | Logged-in users/frontend | No | Technical appendix | Early version | API-only. |
| `/fortress/command-center/` | Financial Fortress | Superadmin economy command center | Superadmins | No | Internal ops only | Available | Do not screenshot real balances, user search, approvals, or audit trail. |

## 11. Community And Arena Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/community/` | Community | Community feed/page | Players, fans | Yes | Launch deck, user guide | Available | Live 200. |
| `/community/create-post/` | Create Community Post | Legacy/form post creation endpoint | Logged-in users | Maybe | User guide | Available | Use demo account only. |
| `/community/api/feed/` | Community Feed API | Feed data | Frontend | No | Technical appendix | Available | API-only. |
| `/community/api/posts/create/`, `/like/`, `/comments/`, `/delete/`, `/vote/` | Community Post APIs | Post creation, engagement, deletion, poll votes | Logged-in users/frontend | No | Technical appendix | Available | Avoid private or real user content in screenshots. |
| `/community/api/sidebar/`, `/user-teams/`, `/preferences/`, `/my-tournaments/`, `/my-passports/` | Community Support APIs | Sidebar, user context, preferences | Frontend | No | Technical appendix | Available | API-only. |
| `/arena/` | Arena | Watch/arena experience | Public visitors, fans | Yes | Launch deck, sponsor deck | Available | Live 200. |
| `/arena/data/` | Arena Data API | Async arena data | Frontend | No | Technical appendix | Available | API-only. |
| `/arena/widget/<id>/vote/` | Arena Widget Vote | Vote on arena widgets | Fans/frontend | Maybe | Sponsor deck | Early version | Use demo widget only. |

## 12. Notification, Support, Trust Pages

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/notifications/` | Notification Inbox | User notification inbox | Logged-in users | Yes | User guide | Available | Requires auth; live redirected to login. |
| `/notifications/mark-all-read/`, `/<pk>/mark-read/`, `/<pk>/delete/`, `/clear-all/` | Notification actions | Mark/read/delete notification actions | Logged-in users | No | Technical appendix | Available | Mutation endpoints. |
| `/notifications/api/*` | Notification APIs | Unread counts, nav preview, feed, read/delete/clear/action endpoints | Frontend | No | Technical appendix | Available | API-only. |
| `/notifications/stream/`, `/api/notifications/stream/` | Notification SSE Stream | Real-time notification stream | Frontend | No | Technical appendix | Available | SSE endpoint. |
| `/notifications/api/follow-request/<id>/accept/`, `/reject/` | Follow request notification actions | Inline accept/reject actions | Logged-in users | No | Technical appendix | Available | API-only. |
| `/notifications/api/team-invite/<id>/accept/`, `/decline/` | Team invite notification actions | Inline team invite actions | Logged-in users | No | Technical appendix | Available | API-only. |
| `/faq/` | FAQ | Public support FAQ | Players, organizers | Yes | User guide | Available | Live 200. |
| `/contact/` | Contact Support | Public support/contact form | Players, partners | Yes | User guide | Available | Live 200. |
| `/moderation/` | Moderation | Trust/moderation surface | Players, moderators | Yes | Trust section | Available | Route/template exists. |
| `/rules/` | Rules | Platform rules | Players, organizers | Yes | User guide, trust section | Available | Live 200. |
| `/competition/ranking/about/` | Ranking About | Ranking documentation | Players, teams | Yes | User guide, trust section | Available | Route/template exists. |

## 13. Mobile API Foundation Routes

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/api/mobile/v1/health/` | Mobile API Health | Mobile API health check | Mobile client, ops | No | Technical appendix | Available | API-only. |
| `/api/mobile/v1/me/` | Mobile Me | Current mobile user envelope | Mobile client | No | Technical appendix | Early version | API-only. |
| `/api/mobile/v1/auth/login/`, `/register/`, `/verify-otp/`, `/resend-otp/`, `/refresh/`, `/logout/` | Mobile Auth API | Mobile login/register/OTP/token/logout flows | Mobile client | No | Mobile roadmap | Early version | API-only. |
| `/api/mobile/v1/me/profile/` | Mobile Profile API | Mobile profile view/update | Mobile client | No | Mobile roadmap | Early version | API-only. |
| `/api/mobile/v1/games/` | Mobile Games API | Active game list | Mobile client | No | Mobile roadmap | Early version | API-only. |
| `/api/mobile/v1/me/game-passports/`, `/<passport_id>/` | Mobile Game Passports API | Mobile passport list/create/detail | Mobile client | No | Mobile roadmap | Early version | API-only. |
| `/api/mobile/v1/tournaments/`, `/me/tournaments/`, `/tournaments/<id_or_slug>/`, `/join/` | Mobile Tournaments API | Mobile tournament listing/detail/join/my tournaments | Mobile client | No | Mobile roadmap | Early version | API-only. |
| `/api/mobile/v1/me/team-status/`, `/teams/`, `/teams/create/`, `/teams/<id_or_slug>/`, `/apply/`, `/requests/<id>/accept|decline/` | Mobile Teams API | Mobile team browse/create/apply/request actions | Mobile client | No | Mobile roadmap | Early version | API-only. |
| `/api/mobile/v1/me/matches/`, `/matches/<id>/`, `/lobby/`, `/check-in/`, `/submit-result/`, `/upload-proof/`, `/status/` | Mobile Matches API | Mobile match room/result/proof/check-in foundation | Mobile client | No | Mobile roadmap | Early version | API-only. |
| `/api/mobile/v1/notifications/`, `/unread-count/`, `/read-all/`, `/device-token/`, `/<id>/read/` | Mobile Notifications API | Mobile notification list/read/device token | Mobile client | No | Mobile roadmap | Early version | API-only. |

## 14. Organizer, Staff, Admin, Internal Surfaces

| URL / pattern | Page name | Purpose | Primary audience | Screenshot needed? | Future document/deck use | Current status | Notes |
|---|---|---|---|---|---|---|---|
| `/toc/<slug>/` | Tournament Operations Center | Organizer SPA shell for tournament operations | Organizers/staff | Yes | Organizer deck, internal ops guide | Early version | Requires auth. Use demo tournament only. |
| `/toc/<slug>/form-configuration/` | TOC Form Configuration | Organizer form configuration page | Organizers/staff | Maybe | Organizer guide | Early version | Requires auth. |
| `/api/toc/<slug>/overview/`, `/perf/summary/` | TOC Overview APIs | Tournament operational overview and performance summary | TOC frontend | No | Technical appendix | Early version | API-only. |
| `/api/toc/<slug>/lifecycle/*` | TOC Lifecycle APIs | Transition/freeze/finalize tournament state | Organizers/staff | No | Internal ops guide | Early version | Mutating routes; do not use production data. |
| `/api/toc/<slug>/participants/*`, `/payments/*`, `/prize-pool/*`, `/prizes/*`, `/kyc/*` | TOC Participants/Finance APIs | Participant, payment, prize, KYC operations | Organizers/staff | No | Internal ops guide | Early version | Sensitive; never capture real KYC/payment proof data. |
| `/api/toc/<slug>/brackets/*`, `/schedule/*`, `/groups/*`, `/pipelines/*`, `/matches/*` | TOC Competition Engine APIs | Bracket, scheduling, group, pipeline and match operations | Organizers/staff | No | Technical appendix | Early version | API-heavy surface. |
| `/api/toc/<slug>/disputes/*` | TOC Dispute APIs | Queue, detail, resolve/escalate/assign/evidence actions | Organizers/staff | No | Trust/internal guide | Early version | Sensitive evidence. |
| `/api/toc/<slug>/settings/*`, `/announcements/*`, `/notifications/*`, `/rules/*`, `/lobby/*`, `/streams/*`, `/analytics/*`, `/audit-log/*`, `/staff/*`, `/roles/*` | TOC Settings/Comms/Ops APIs | Tournament configuration, communications, lobby, streams, analytics, audit, staff roles | Organizers/staff | No | Internal ops guide | Early version | API-only. |
| `/admin/` | Django Admin | General model administration | Staff/admin | No | Internal docs only | Available | Do not capture real admin data. |
| `/admin/game-passports/` and detail/action routes | Game Passport Admin | Custom passport admin dashboard, verify, flag, reset, unlock, cooldown override | Staff/admin | No | Internal trust guide | Available | Internal only; sensitive identity/trust operations. |
| `/admin/competition/status/` | Competition Admin Status | Competition system status | Staff/admin | No | Internal ops guide | Available | Staff member required. |
| `/admin/competition/operations/` | Competitive Operations Admin | Admin operations console for Showdowns, Bounties, Dropzone | Staff/admin | No | Internal ops guide | Available | Internal-only. |
| `/admin/maintenance/` | Games Maintenance | Maintenance panel | Staff/admin | No | Internal ops guide | Available | Internal-only. |
| `/fortress/command-center/` and `/fortress/api/*` | Financial Fortress | Superadmin economy actions: approvals, mint/airdrop, audit, wallet search, PIN reset | Superadmins | No | Internal ops only | Available | Never capture secrets, balances, private users, or approval data. |
| `/api/lifecycle/cron/`, `/healthz/`, `/readiness/`, `/metrics/` if enabled | System ops endpoints | Health/readiness/lifecycle/metrics | Ops/admin | No | Technical ops appendix | Available | Metrics only exposed when enabled and staff protected per URL config. |
| `/api/schema/`, `/api/docs/`, `/api/redoc/` in DEBUG | API docs | Development API schema/docs | Developers | No | Developer docs | Available in DEBUG only | Do not assume public production availability. |

## 15. Uncertain Routes And Owner Confirmation Needed

- `/competition/bounties/`: code route and template exist, but the live public page returned 500. Owner should confirm whether this is a production data bug, deployment mismatch, or in-progress feature.
- `/spectator/`: code/templates exist for spectator pages, but the live list route returned 500. Owner should confirm launch readiness.
- `/dashboard/competitive/*`: strong model/API/dashboard support exists for Showdown, Missions, Bounty, and Dropzone, but many surfaces are authenticated detail pages or API-backed workflows. Label as early version unless demo data proves an end-to-end flow.
- `/api/v1/contracts/*`: Missions/contracts API exists, but no dedicated public Mission landing page was found. Owner should confirm whether Missions should be presented as API-backed Competitive Hub functionality only.
- `/wallet/`, `/withdraw/`, withdrawal pages: routes exist, but public-facing product wording should be owner-confirmed before deck use. DeltaCoin should only be described as a closed-loop platform utility.
- TOC `/toc/<slug>/` and `/api/toc/*`: large organizer surface exists, but many endpoints are API-first. Owner should confirm which tabs are pitch-ready before screenshots.
- Settings `/me/settings/`: available but known fragile. Any future screenshot or redesign must preserve current contracts documented in `Documents/DELTACROWN/SETTINGS_REDESIGN_SPEC.md`.
