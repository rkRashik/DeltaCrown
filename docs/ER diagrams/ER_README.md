# DeltaCrown ER Overview

## Entities by app
### `accounts`
- **accounts.EmailOTP** — 6 attributes, 1 relations

### `corelib`
- **corelib.IdempotencyKey** — 3 attributes, 1 relations

### `ecommerce`
- **ecommerce.Order** — 3 attributes, 1 relations
- **ecommerce.OrderItem** — 2 attributes, 2 relations
- **ecommerce.Product** — 5 attributes, 0 relations

### `economy`
- **economy.CoinPolicy** — 7 attributes, 1 relations
- **economy.DeltaCrownTransaction** — 5 attributes, 5 relations
- **economy.DeltaCrownWallet** — 3 attributes, 1 relations

### `game_efootball`
- **game_efootball.EfootballConfig** — 6 attributes, 1 relations

### `game_valorant`
- **game_valorant.ValorantConfig** — 9 attributes, 1 relations

### `teams`
- **teams.EfootballTeamPreset** — 8 attributes, 1 relations
- **teams.Team** — 16 attributes, 1 relations
- **teams.TeamAchievement** — 5 attributes, 2 relations
- **teams.TeamInvite** — 6 attributes, 3 relations
- **teams.TeamMembership** — 3 attributes, 2 relations
- **teams.TeamStats** — 6 attributes, 1 relations
- **teams.ValorantPlayerPreset** — 4 attributes, 1 relations
- **teams.ValorantTeamPreset** — 7 attributes, 1 relations

### `tournaments`
- **tournaments.Bracket** — 4 attributes, 1 relations
- **tournaments.CalendarFeedToken** — 2 attributes, 1 relations
- **tournaments.Match** — 8 attributes, 7 relations
- **tournaments.MatchAttendance** — 4 attributes, 2 relations
- **tournaments.MatchComment** — 2 attributes, 2 relations
- **tournaments.MatchDispute** — 5 attributes, 3 relations
- **tournaments.MatchDisputeEvidence** — 4 attributes, 2 relations
- **tournaments.MatchEvent** — 3 attributes, 1 relations
- **tournaments.PaymentVerification** — 12 attributes, 2 relations
- **tournaments.PinnedTournament** — 2 attributes, 1 relations
- **tournaments.Registration** — 7 attributes, 4 relations
- **tournaments.SavedMatchFilter** — 9 attributes, 1 relations
- **tournaments.TournamentSettings** — 35 attributes, 1 relations

### `user_profile`
- **user_profile.UserProfile** — 15 attributes, 1 relations

## Relationships (plain English)
- **ecommerce.Order.user** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **ecommerce.OrderItem.order** is a **many‑to‑one** relation to **ecommerce.Order**.
- **ecommerce.OrderItem.product** is a **many‑to‑one** relation to **ecommerce.Product**.
- **economy.DeltaCrownTransaction.wallet** is a **many‑to‑one** relation to **economy.DeltaCrownWallet**.
- **economy.DeltaCrownTransaction.match** is a **many‑to‑one** relation to **tournaments.Match**.
- **economy.DeltaCrownTransaction.registration** is a **many‑to‑one** relation to **tournaments.Registration**.
- **economy.DeltaCrownWallet.profile** is a **one‑to‑one** relation to **user_profile.UserProfile**.
- **teams.EfootballTeamPreset.profile** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **teams.Team.captain** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **teams.TeamAchievement.team** is a **many‑to‑one** relation to **teams.Team**.
- **teams.TeamInvite.team** is a **many‑to‑one** relation to **teams.Team**.
- **teams.TeamInvite.invited_user** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **teams.TeamInvite.inviter** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **teams.TeamMembership.team** is a **many‑to‑one** relation to **teams.Team**.
- **teams.TeamMembership.profile** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **teams.TeamStats.team** is a **many‑to‑one** relation to **teams.Team**.
- **teams.ValorantPlayerPreset.preset** is a **many‑to‑one** relation to **teams.ValorantTeamPreset**.
- **teams.ValorantTeamPreset.profile** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **tournaments.Match.team_a** is a **many‑to‑one** relation to **teams.Team**.
- **tournaments.Match.team_b** is a **many‑to‑one** relation to **teams.Team**.
- **tournaments.Match.winner_team** is a **many‑to‑one** relation to **teams.Team**.
- **tournaments.Match.user_a** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **tournaments.Match.user_b** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **tournaments.Match.winner_user** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **tournaments.MatchAttendance.match** is a **many‑to‑one** relation to **tournaments.Match**.
- **tournaments.MatchComment.match** is a **many‑to‑one** relation to **tournaments.Match**.
- **tournaments.MatchComment.author** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **tournaments.MatchDispute.match** is a **many‑to‑one** relation to **tournaments.Match**.
- **tournaments.MatchDispute.opened_by** is a **many‑to‑one** relation to **user_profile.UserProfile**.
- **tournaments.MatchDisputeEvidence.dispute** is a **many‑to‑one** relation to **tournaments.MatchDispute**.
- **tournaments.MatchEvent.match** is a **many‑to‑one** relation to **tournaments.Match**.
- **tournaments.PaymentVerification.registration** is a **one‑to‑one** relation to **tournaments.Registration**.
- **tournaments.Registration.team** is a **many‑to‑one** relation to **teams.Team**.
- **tournaments.Registration.user** is a **many‑to‑one** relation to **user_profile.UserProfile**.