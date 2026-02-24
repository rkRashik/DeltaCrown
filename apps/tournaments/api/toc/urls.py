"""
TOC API — URL Configuration.

All endpoints live under /api/toc/<slug>/...
Wired into the project via deltacrown/urls.py.

Sprint 1: Overview, Lifecycle, Alerts
Sprint 2: Participants (list, detail, actions, bulk, export)
Sprint 3: Participants Advanced (emergency subs, free agents, waitlist, guest, fee waiver)
Sprint 4: Financial Operations (payments, revenue, prizes, bounties, KYC)
Sprint 5: Competition Engine (brackets, groups, schedule, pipelines)
Sprint 6: Match Operations (matches, scoring, medic, reschedule, media)
Sprint 7: Disputes (queue, resolve, escalate, assign, evidence)
Sprint 8: Configuration & Communications (settings, game config, maps, veto, regions, rulebook, announcements, quick comms)
Sprint 9: Stats, Certificates & Trust Index
Sprint 10: RBAC & Economy Integration
Sprint 11: Audit Trail & Real-Time Infrastructure
"""

from django.urls import path

from apps.tournaments.api.toc import (
    overview, lifecycle, alerts, participants,
    participants_advanced, payments, brackets, matches, disputes,
    settings, announcements, stats, rbac, audit,
)

app_name = 'toc_api'

urlpatterns = [
    # ── Overview (S1-B2) ──
    path('<slug:slug>/overview/', overview.OverviewAPIView.as_view(), name='overview'),

    # ── Lifecycle (S1-B3/B4/B5) ──
    path('<slug:slug>/lifecycle/transition/', lifecycle.LifecycleTransitionView.as_view(), name='lifecycle-transition'),
    path('<slug:slug>/lifecycle/freeze/', lifecycle.FreezeView.as_view(), name='lifecycle-freeze'),
    path('<slug:slug>/lifecycle/unfreeze/', lifecycle.UnfreezeView.as_view(), name='lifecycle-unfreeze'),

    # ── Alerts (S1-B6/B7) ──
    path('<slug:slug>/alerts/', alerts.AlertListView.as_view(), name='alerts'),
    path('<slug:slug>/alerts/<int:alert_id>/dismiss/', alerts.AlertDismissView.as_view(), name='alert-dismiss'),

    # ── Participants (S2-B1 through S2-B9) ──
    path('<slug:slug>/participants/', participants.ParticipantListView.as_view(), name='participants'),
    path('<slug:slug>/participants/bulk-action/', participants.BulkActionView.as_view(), name='participants-bulk-action'),
    path('<slug:slug>/participants/export/', participants.ExportCSVView.as_view(), name='participants-export'),
    path('<slug:slug>/participants/<int:pk>/', participants.ParticipantDetailView.as_view(), name='participant-detail'),
    path('<slug:slug>/participants/<int:pk>/approve/', participants.ApproveView.as_view(), name='participant-approve'),
    path('<slug:slug>/participants/<int:pk>/reject/', participants.RejectView.as_view(), name='participant-reject'),
    path('<slug:slug>/participants/<int:pk>/disqualify/', participants.DisqualifyView.as_view(), name='participant-disqualify'),
    path('<slug:slug>/participants/<int:pk>/verify-payment/', participants.VerifyPaymentView.as_view(), name='participant-verify-payment'),
    path('<slug:slug>/participants/<int:pk>/toggle-checkin/', participants.ToggleCheckinView.as_view(), name='participant-toggle-checkin'),

    # ── Participants Advanced (S3-B1 through S3-B8) ──
    path('<slug:slug>/participants/auto-promote/', participants_advanced.WaitlistAutoPromoteView.as_view(), name='participants-auto-promote'),
    path('<slug:slug>/participants/<int:pk>/emergency-sub/', participants_advanced.EmergencySubSubmitView.as_view(), name='participant-emergency-sub'),
    path('<slug:slug>/participants/<int:pk>/promote-waitlist/', participants_advanced.WaitlistPromoteView.as_view(), name='participant-promote-waitlist'),
    path('<slug:slug>/participants/<int:pk>/convert-guest/', participants_advanced.ConvertGuestView.as_view(), name='participant-convert-guest'),
    path('<slug:slug>/participants/<int:pk>/fee-waiver/', participants_advanced.FeeWaiverView.as_view(), name='participant-fee-waiver'),

    # ── Emergency Subs (S3-B1/B2) ──
    path('<slug:slug>/emergency-subs/', participants_advanced.EmergencySubListView.as_view(), name='emergency-subs'),
    path('<slug:slug>/emergency-subs/<str:sub_id>/approve/', participants_advanced.EmergencySubApproveView.as_view(), name='emergency-sub-approve'),
    path('<slug:slug>/emergency-subs/<str:sub_id>/deny/', participants_advanced.EmergencySubDenyView.as_view(), name='emergency-sub-deny'),

    # ── Free Agents (S3-B3/B4) ──
    path('<slug:slug>/free-agents/', participants_advanced.FreeAgentListView.as_view(), name='free-agents'),
    path('<slug:slug>/free-agents/<str:fa_id>/assign/', participants_advanced.FreeAgentAssignView.as_view(), name='free-agent-assign'),

    # ── Waitlist (S3-B5/B6 — list helper) ──
    path('<slug:slug>/waitlist/', participants_advanced.WaitlistListView.as_view(), name='waitlist'),

    # ── Payments (S4-B1 through S4-B7) ──
    path('<slug:slug>/payments/', payments.PaymentListView.as_view(), name='payments'),
    path('<slug:slug>/payments/summary/', payments.PaymentSummaryView.as_view(), name='payments-summary'),
    path('<slug:slug>/payments/export/', payments.PaymentExportView.as_view(), name='payments-export'),
    path('<slug:slug>/payments/bulk-verify/', payments.PaymentBulkVerifyView.as_view(), name='payments-bulk-verify'),
    path('<slug:slug>/payments/<int:pk>/verify/', payments.PaymentVerifyView.as_view(), name='payment-verify'),
    path('<slug:slug>/payments/<int:pk>/reject/', payments.PaymentRejectView.as_view(), name='payment-reject'),
    path('<slug:slug>/payments/<int:pk>/refund/', payments.PaymentRefundView.as_view(), name='payment-refund'),

    # ── Prize Pool (S4-B8/B9) ──
    path('<slug:slug>/prize-pool/', payments.PrizePoolView.as_view(), name='prize-pool'),
    path('<slug:slug>/prize-pool/distribute/', payments.PrizeDistributeView.as_view(), name='prize-distribute'),

    # ── Bounties (S4-B10) ──
    path('<slug:slug>/bounties/', payments.BountyListCreateView.as_view(), name='bounties'),
    path('<slug:slug>/bounties/<str:bounty_id>/', payments.BountyDetailView.as_view(), name='bounty-detail'),
    path('<slug:slug>/bounties/<str:bounty_id>/assign/', payments.BountyAssignView.as_view(), name='bounty-assign'),

    # ── KYC (S4-B11) ──
    path('<slug:slug>/kyc/', payments.KYCListView.as_view(), name='kyc'),
    path('<slug:slug>/kyc/<str:kyc_id>/review/', payments.KYCReviewView.as_view(), name='kyc-review'),

    # ── Brackets (S5-B1 through S5-B5) ──
    path('<slug:slug>/brackets/', brackets.BracketGetView.as_view(), name='brackets'),
    path('<slug:slug>/brackets/generate/', brackets.BracketGenerateView.as_view(), name='brackets-generate'),
    path('<slug:slug>/brackets/reset/', brackets.BracketResetView.as_view(), name='brackets-reset'),
    path('<slug:slug>/brackets/publish/', brackets.BracketPublishView.as_view(), name='brackets-publish'),
    path('<slug:slug>/brackets/seeds/', brackets.BracketSeedsView.as_view(), name='brackets-seeds'),

    # ── Schedule (S5-B6 through S5-B9) ──
    path('<slug:slug>/schedule/', brackets.ScheduleGetView.as_view(), name='schedule'),
    path('<slug:slug>/schedule/auto-generate/', brackets.ScheduleAutoGenerateView.as_view(), name='schedule-auto-generate'),
    path('<slug:slug>/schedule/bulk-shift/', brackets.ScheduleBulkShiftView.as_view(), name='schedule-bulk-shift'),
    path('<slug:slug>/schedule/add-break/', brackets.ScheduleAddBreakView.as_view(), name='schedule-add-break'),

    # ── Group Stage (S5-B10) ──
    path('<slug:slug>/groups/', brackets.GroupStageView.as_view(), name='groups'),
    path('<slug:slug>/groups/configure/', brackets.GroupConfigureView.as_view(), name='groups-configure'),
    path('<slug:slug>/groups/draw/', brackets.GroupDrawView.as_view(), name='groups-draw'),
    path('<slug:slug>/groups/standings/', brackets.GroupStandingsView.as_view(), name='groups-standings'),

    # ── Qualifier Pipelines (S5-B11) ──
    path('<slug:slug>/pipelines/', brackets.PipelineListCreateView.as_view(), name='pipelines'),
    path('<slug:slug>/pipelines/<str:pipeline_id>/', brackets.PipelineDetailView.as_view(), name='pipeline-detail'),

    # ── Matches (S6-B1 through S6-B10) ──
    path('<slug:slug>/matches/', matches.MatchListView.as_view(), name='matches'),
    path('<slug:slug>/matches/<int:pk>/score/', matches.MatchScoreView.as_view(), name='match-score'),
    path('<slug:slug>/matches/<int:pk>/mark-live/', matches.MatchMarkLiveView.as_view(), name='match-mark-live'),
    path('<slug:slug>/matches/<int:pk>/pause/', matches.MatchPauseView.as_view(), name='match-pause'),
    path('<slug:slug>/matches/<int:pk>/resume/', matches.MatchResumeView.as_view(), name='match-resume'),
    path('<slug:slug>/matches/<int:pk>/force-complete/', matches.MatchForceCompleteView.as_view(), name='match-force-complete'),
    path('<slug:slug>/matches/<int:pk>/reschedule/', matches.MatchRescheduleView.as_view(), name='match-reschedule'),
    path('<slug:slug>/matches/<int:pk>/forfeit/', matches.MatchForfeitView.as_view(), name='match-forfeit'),
    path('<slug:slug>/matches/<int:pk>/add-note/', matches.MatchNoteView.as_view(), name='match-add-note'),
    path('<slug:slug>/matches/<int:pk>/media/', matches.MatchMediaView.as_view(), name='match-media'),

    # ── Disputes (S7-B1 through S7-B7) ──
    path('<slug:slug>/disputes/', disputes.DisputeListView.as_view(), name='disputes'),
    path('<slug:slug>/disputes/<int:pk>/', disputes.DisputeDetailView.as_view(), name='dispute-detail'),
    path('<slug:slug>/disputes/<int:pk>/resolve/', disputes.DisputeResolveView.as_view(), name='dispute-resolve'),
    path('<slug:slug>/disputes/<int:pk>/escalate/', disputes.DisputeEscalateView.as_view(), name='dispute-escalate'),
    path('<slug:slug>/disputes/<int:pk>/assign/', disputes.DisputeAssignView.as_view(), name='dispute-assign'),
    path('<slug:slug>/disputes/<int:pk>/add-evidence/', disputes.DisputeAddEvidenceView.as_view(), name='dispute-add-evidence'),
    path('<slug:slug>/disputes/<int:pk>/update-status/', disputes.DisputeUpdateStatusView.as_view(), name='dispute-update-status'),

    # ── Settings (S8-B1) ──
    path('<slug:slug>/settings/', settings.SettingsView.as_view(), name='settings'),

    # ── Game Config (S8-B2) ──
    path('<slug:slug>/settings/game-config/', settings.GameConfigView.as_view(), name='settings-game-config'),

    # ── Map Pool (S8-B3) ──
    path('<slug:slug>/settings/map-pool/', settings.MapPoolListView.as_view(), name='settings-map-pool'),
    path('<slug:slug>/settings/map-pool/reorder/', settings.MapPoolReorderView.as_view(), name='settings-map-pool-reorder'),
    path('<slug:slug>/settings/map-pool/<str:pk>/', settings.MapPoolDetailView.as_view(), name='settings-map-pool-detail'),

    # ── Veto (S8-B4) ──
    path('<slug:slug>/settings/veto/<int:match_pk>/', settings.VetoSessionView.as_view(), name='settings-veto'),
    path('<slug:slug>/settings/veto/<int:match_pk>/advance/', settings.VetoAdvanceView.as_view(), name='settings-veto-advance'),

    # ── Server Regions (S8-B5) ──
    path('<slug:slug>/settings/regions/', settings.RegionListView.as_view(), name='settings-regions'),
    path('<slug:slug>/settings/regions/<str:pk>/', settings.RegionDeleteView.as_view(), name='settings-region-delete'),

    # ── Rulebook (S8-B6) ──
    path('<slug:slug>/settings/rulebook/', settings.RulebookListView.as_view(), name='settings-rulebook'),
    path('<slug:slug>/settings/rulebook/<str:pk>/', settings.RulebookDetailView.as_view(), name='settings-rulebook-detail'),
    path('<slug:slug>/settings/rulebook/<str:pk>/publish/', settings.RulebookPublishView.as_view(), name='settings-rulebook-publish'),

    # ── BR Scoring (S8-B7) ──
    path('<slug:slug>/settings/br-scoring/', settings.BRScoringView.as_view(), name='settings-br-scoring'),

    # ── Announcements (S8-B7 comms) ──
    path('<slug:slug>/announcements/', announcements.AnnouncementListView.as_view(), name='announcements'),
    path('<slug:slug>/announcements/<int:pk>/', announcements.AnnouncementDetailView.as_view(), name='announcement-detail'),
    path('<slug:slug>/announcements/broadcast/', announcements.AnnouncementBroadcastView.as_view(), name='announcements-broadcast'),

    # ── Quick Comms (S8-B8) ──
    path('<slug:slug>/announcements/quick-comms/', announcements.QuickCommsView.as_view(), name='announcements-quick-comms'),

    # ── Stats Summary (S9-B1) ──
    path('<slug:slug>/stats/', stats.StatsOverviewView.as_view(), name='stats-overview'),

    # ── Certificate Templates (S9-B2) ──
    path('<slug:slug>/certificates/', stats.CertificateTemplateListView.as_view(), name='certificate-templates'),
    path('<slug:slug>/certificates/<str:pk>/', stats.CertificateTemplateDetailView.as_view(), name='certificate-template-detail'),
    path('<slug:slug>/certificates/<str:pk>/generate/', stats.CertificateGenerateView.as_view(), name='certificate-generate'),
    path('<slug:slug>/certificates/<str:pk>/bulk-generate/', stats.CertificateBulkGenerateView.as_view(), name='certificate-bulk-generate'),

    # ── Trophies (S9-B3) ──
    path('<slug:slug>/trophies/', stats.TrophyListView.as_view(), name='trophies'),
    path('<slug:slug>/trophies/<str:pk>/', stats.TrophyAwardView.as_view(), name='trophy-award'),
    path('<slug:slug>/trophies/user/<int:user_id>/', stats.UserTrophiesView.as_view(), name='user-trophies'),

    # ── Trust Index (S9-B4 / B5) ──
    path('<slug:slug>/trust/<int:user_id>/', stats.TrustIndexView.as_view(), name='trust-index'),
    path('<slug:slug>/trust/<int:user_id>/events/', stats.TrustEventListView.as_view(), name='trust-events'),

    # ── Staff Roles (S10-B1) ──
    path('<slug:slug>/staff/', rbac.StaffListView.as_view(), name='staff'),
    path('<slug:slug>/staff/<int:pk>/', rbac.StaffDetailView.as_view(), name='staff-detail'),
    path('<slug:slug>/roles/', rbac.RoleListView.as_view(), name='roles'),

    # ── Permissions (S10-B2) ──
    path('<slug:slug>/permissions/', rbac.PermissionsView.as_view(), name='permissions'),

    # ── DeltaCoin Economy (S10-B3 / B4) ──
    path('<slug:slug>/economy/balance/<int:user_id>/', rbac.DeltaCoinBalanceView.as_view(), name='deltacoin-balance'),
    path('<slug:slug>/economy/transactions/<int:user_id>/', rbac.DeltaCoinTransactionsView.as_view(), name='deltacoin-transactions'),
    path('<slug:slug>/economy/entry-fee/', rbac.EntryFeeView.as_view(), name='entry-fee'),
    path('<slug:slug>/economy/distribute-prize/', rbac.PrizeDistributeView.as_view(), name='distribute-prize'),

    # ── Audit Log (S11-B2) ──
    path('<slug:slug>/audit-log/', audit.AuditLogView.as_view(), name='audit-log'),
]
