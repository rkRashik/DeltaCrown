# Quick Reference — What Lives Where

*Use this to instantly find which app/service/model handles what.*  
*Updated: February 14, 2026*

---

## Model Ownership

| Domain | Model | App | File |
|--------|-------|-----|------|
| **Tournament Core** | Tournament | tournaments | models/tournament.py |
| | TournamentVersion | tournaments | models/tournament.py |
| | CustomField | tournaments | models/tournament.py |
| | TournamentTemplate | tournaments | models/template.py |
| | TournamentStage | tournaments | models/stage.py |
| | TournamentAnnouncement | tournaments | models/announcement.py |
| | AuditLog | tournaments | models/security.py |
| **Registration** | Registration | tournaments | models/registration.py |
| | Payment | tournaments | models/registration.py |
| | PaymentVerification | tournaments | models/payment_verification.py |
| | TournamentPaymentMethod | tournaments | models/payment_config.py |
| | RegistrationDraft | tournaments | models/smart_registration.py |
| | RegistrationQuestion | tournaments | models/smart_registration.py |
| | RegistrationRule | tournaments | models/smart_registration.py |
| | RegistrationFormTemplate | tournaments | models/form_template.py |
| | TournamentRegistrationForm | tournaments | models/form_template.py |
| | FormResponse | tournaments | models/form_template.py |
| | TournamentFormConfiguration | tournaments | models/form_configuration.py |
| **Bracket** | Bracket | tournaments | models/bracket.py |
| | BracketNode | tournaments | models/bracket.py |
| | BracketEditLog | tournaments | models/bracket_edit_log.py |
| **Match** | Match | tournaments | models/match.py |
| | MatchResultSubmission | tournaments | models/result_submission.py |
| | ResultVerificationLog | tournaments | models/result_submission.py |
| | MatchOperationLog | tournaments | models/match_ops.py |
| | MatchModeratorNote | tournaments | models/match_ops.py |
| **Dispute** | DisputeRecord | tournaments | models/dispute.py |
| | DisputeEvidence | tournaments | models/dispute.py |
| **Group Stage** | Group | tournaments | models/group.py |
| | GroupStanding | tournaments | models/group.py |
| | GroupStage | tournaments | models/group.py |
| **Results** | TournamentResult | tournaments | models/result.py |
| | PrizeTransaction | tournaments | models/prize.py |
| | Certificate | tournaments | models/certificate.py |
| **Lobby** | TournamentLobby | tournaments | models/lobby.py |
| | CheckIn | tournaments | models/lobby.py |
| | LobbyAnnouncement | tournaments | models/lobby.py |
| **Staff (Phase 7)** | StaffRole | tournaments | models/staffing.py |
| | TournamentStaffAssignment | tournaments | models/staffing.py |
| | MatchRefereeAssignment | tournaments | models/staffing.py |
| **Webhooks** | FormWebhook | tournaments | models/webhooks.py |
| | WebhookDelivery | tournaments | models/webhooks.py |
| **Invitations** | TournamentTeamInvitation | tournaments | models/team_invitation.py |
| | TeamRegistrationPermissionRequest | tournaments | models/permission_request.py |

---

## Service Ownership (After Consolidation)

| Domain | Definitive Service | App | Status |
|--------|-------------------|-----|--------|
| Registration | RegistrationService | tournament_ops | Phase 2 |
| Eligibility | (merged into RegistrationService) | tournament_ops | Phase 2 |
| Match | MatchService (state) + ResultSubmissionService | tournament_ops | Phase 2 |
| Bracket | BracketEngineService | tournament_ops | Phase 2 |
| Dispute | DisputeService (661 lines) | tournament_ops | ✅ Complete |
| Result Verification | ResultVerificationService | tournament_ops | ✅ Complete |
| Review Inbox | ReviewInboxService | tournament_ops | ✅ Complete |
| Staffing | StaffingService | tournament_ops | ✅ Complete |
| Match Ops | MatchOpsService | tournament_ops | ✅ Complete |
| Audit Log | AuditLogService | tournament_ops | ✅ Complete |
| Analytics | AnalyticsEngineService | tournament_ops | Phase 2 |
| Check-In | CheckInService | tournaments | Phase 2 |
| Lobby | LobbyService | tournaments | ✅ Existing |
| Group Stage | GroupStageService | tournaments | Phase 2 (remove hardcoded) |
| Winner Determination | WinnerService | tournaments | ✅ Existing |
| Certificate | CertificateService | tournaments | ✅ Existing |
| Payout | PayoutService | tournaments | ✅ Existing |
| Tournament Discovery | TournamentDiscoveryService | tournaments | ✅ Existing |
| Template | TemplateService | tournaments | ✅ Existing |
| Lifecycle | TournamentLifecycleService | tournament_ops | Phase 5 |
| Payment Orchestration | PaymentOrchestrationService | tournament_ops | Phase 1 |
| Smart Registration | SmartRegistrationService | tournament_ops | Phase 2 |
| Help / Onboarding | HelpService | tournament_ops | ✅ Complete |
| Stats (User) | UserStatsService | tournament_ops | ✅ Existing |
| Stats (Team) | TeamStatsService | tournament_ops | ✅ Existing |
| Match History | MatchHistoryService | tournament_ops | ✅ Existing |

---

## Adapter Connections (After Phase 1)

| Adapter | Connects To | Real App/Service |
|---------|-------------|-----------------|
| TeamAdapter | apps.organizations | Team, TeamMembership, TeamService |
| UserAdapter | apps.user_profile | UserProfile, GameProfile, GamePassportService |
| GameAdapter | apps.games | Game, GameTournamentConfig, GameRulesEngine |
| EconomyAdapter | apps.economy | wallet_for(), award(), DeltaCrownTransaction |
| NotificationAdapter | apps.notifications | notify(), Notification model |
| TournamentAdapter | apps.tournaments | Tournament model (own app) |
| MatchAdapter | apps.tournaments | Match model (own app) |
| ResultSubmissionAdapter | apps.tournaments | MatchResultSubmission model |
| DisputeAdapter | apps.tournaments | DisputeRecord model |
| StaffingAdapter | apps.tournaments | StaffRole, TournamentStaffAssignment |
| MatchOpsAdapter | apps.tournaments | MatchOperationLog, MatchModeratorNote |
| AuditLogAdapter | apps.tournaments | AuditLog model |
| SmartRegistrationAdapter | apps.tournaments | RegistrationDraft, RegistrationQuestion |
| ReviewInboxAdapter | apps.tournaments | MatchResultSubmission (filtered) |
| UserStatsAdapter | apps.leaderboards | UserStats model |
| TeamStatsAdapter | apps.leaderboards | TeamStats model |
| TeamRankingAdapter | apps.leaderboards | TeamRanking model |
| MatchHistoryAdapter | apps.leaderboards | UserMatchHistory model |
| AnalyticsAdapter | apps.tournaments | Analytics materialized views |
| SchemaValidationAdapter | apps.games | GameMatchResultSchema, GameRulesEngine |
| HelpContentAdapter | apps.tournament_ops | HelpContent (static data) |

---

## Event Map

| Event Name | Published By | Consumed By |
|------------|-------------|-------------|
| `registration.confirmed` | RegistrationService | NotificationAdapter |
| `match.started` | MatchService | NotificationAdapter |
| `match.completed` | MatchService | Leaderboards (stats/ELO), NotificationAdapter |
| `result.submitted` | ResultSubmissionService | NotificationAdapter (to opponent) |
| `result.verified` | ResultVerificationService | MatchService (update bracket) |
| `dispute.opened` | DisputeService | NotificationAdapter, AuditLogService |
| `dispute.resolved` | DisputeService | NotificationAdapter, MatchService |
| `tournament.completed` | LifecycleService | PayoutService, CertificateService, NotificationAdapter |
| `checkin.completed` | CheckInService | LobbyService (update participant list) |
| `tournament.cancelled` | LifecycleService | EconomyAdapter (refunds), NotificationAdapter |

---

## URL Quick Reference (After Phase 3)

| URL Pattern | View | Access |
|-------------|------|--------|
| `/tournaments/` | Browse | Public |
| `/tournaments/create/` | Create wizard | Authenticated |
| `/tournaments/<slug>/` | Detail | Public |
| `/tournaments/<slug>/register/` | Registration | Authenticated |
| `/tournaments/<slug>/lobby/` | Lobby | Registered |
| `/tournaments/<slug>/bracket/` | Bracket | Public |
| `/tournaments/<slug>/standings/` | Group standings | Public |
| `/tournaments/<slug>/leaderboard/` | Leaderboard | Public |
| `/tournaments/<slug>/results/` | Archive/results | Public |
| `/tournaments/<slug>/match/<id>/` | Match detail | Public |
| `/tournaments/<slug>/match/<id>/submit-result/` | Result submission | Participant |
| `/tournaments/<slug>/match/<id>/dispute/` | Dispute filing | Participant |
| `/tournaments/<slug>/manage/` | Organizer hub | Organizer |
| `/tournaments/<slug>/manage/participants/` | Registrations | Organizer |
| `/tournaments/<slug>/manage/bracket/` | Bracket editor | Organizer |
| `/tournaments/<slug>/manage/matches/` | Match management | Organizer |
| `/tournaments/<slug>/manage/results/` | Result inbox | Organizer |
| `/tournaments/<slug>/manage/disputes/` | Dispute management | Organizer |
| `/tournaments/<slug>/manage/staff/` | Staff management | Organizer |
| `/tournaments/<slug>/manage/finances/` | Finances | Organizer |
| `/tournaments/<slug>/manage/analytics/` | Analytics | Organizer |
| `/tournaments/<slug>/manage/settings/` | Settings | Organizer |
| `/tournaments/my/` | My tournaments | Authenticated |
| `/tournaments/my/matches/` | My matches | Authenticated |
