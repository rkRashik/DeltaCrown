# Data model (conceptual)

Purpose: how the main entities relate, so you know where to look in the code. This is a map, not a schema dump; the source of truth is each app's `models/` and `migrations/`.

```
User (accounts)
 ├─ 1:1 UserProfile (user_profile) ─ GameProfile/GamePassport per Game, privacy, follows, career, showcase
 ├─ 1:1 DeltaCrownWallet (economy, via profile) ─ DeltaCrownTransaction (ledger), TopUp/Withdrawal/PrizeClaim requests
 ├─ TeamMembership ─ Team ─ Organization (optional parent)
 └─ Registration (user_id, or team_id for team entries) ─ Tournament ─ Game

Organization 1─* Team 1─* TeamMembership *─1 User
Tournament 1─* Registration (exactly one of user_id / team_id) 1─1 Payment
Tournament 1─* TournamentStage / Bracket 1─* Match ─ result submissions, DisputeRecord (+ evidence, notes)
Match (competition reports) ─ ranking snapshots per Team and Game
User 1─* Notification (recipient), NotificationPreference
```

## Where each area lives

| Area | Key models | Files |
|---|---|---|
| Identity | `User`, `GoogleIdentity`, `PendingSignup`, `EmailOTP`, `AccountDeletionRequest` | `apps/accounts/models.py` |
| Profile | `UserProfile`, `GameProfile`/passports, `PrivacySettings`, follow models, `SocialLink`, achievements, career, showcase | `apps/user_profile/models/` |
| Teams and organizations | `Organization`, `Team`, `TeamMembership`, `TeamInvite`, join requests, activity, recruitment, `TeamRanking`, `OrganizationRanking` | `apps/organizations/models/` |
| Games | `Game`, roles, roster config, rules, map pools, tournament config, passport schema | `apps/games/models/` |
| Tournaments | `Tournament` (status machine), `Registration`, `Payment`, `Bracket`, `Match`, `DisputeRecord`, `TournamentLobby`, `CheckIn`, `TournamentStage`, `Prize`/`PrizeClaim`, staffing, certificates, form templates, announcements | `apps/tournaments/models/` |
| Rankings | `GameRankingConfig`, `TeamGlobalRankingSnapshot`, `TeamGameRankingSnapshot`, `MatchReport`, `MatchVerification` | `apps/competition/models/` |
| Economy | `DeltaCrownWallet`, `DeltaCrownTransaction`, `TopUpRequest`, `WithdrawalRequest`, `PrizeClaim`, inventory, daily rewards | `apps/economy/models/` |
| Notifications | `Notification`, `NotificationPreference`, `NotificationDigest` | `apps/notifications/models.py` |

## Conventions

* Many financial and request records use soft deletion (`SoftDeleteModel`, `apps/common`); deleted rows are hidden by default managers, not removed.
* `Tournament.status` and `Match.status` are explicit state machines; allowed transitions are defined on the model (`Tournament.ALLOWED_TRANSITIONS`) and enforced by services (see [tournaments](tournaments.md)).
* The wallet is the single balance holder; every change goes through a ledger row. Use the economy services, never edit balances directly.
* Public IDs: users carry `DC-YY-NNNNNN` public IDs (`apps/user_profile/services/public_id.py`).
* The wallet relates to `UserProfile`, not directly to `User`. `Registration.team_id` is a plain integer (the team app is separate), so there is no database-level foreign key to `Team`.
* Some legacy tables keep `deltacrown`-era names and an unusual `db_table` (for example matches use `tournament_engine_match_match`). Do not rename tables.
