"""
Tournament URL configuration.

Sprint 1 Frontend Implementation (November 15, 2025):
- FE-T-001: Tournament List Page (/tournaments/)
- FE-T-002: Tournament Detail Page (/tournaments/<slug>/)
- FE-T-003: Registration CTA States (part of detail page)
- FE-T-004: Registration Wizard (/tournaments/<slug>/register/)

Sprint 2 Frontend Implementation (November 15, 2025):
- FE-T-005: My Tournaments Dashboard (/tournaments/my/)
- My Matches View (/tournaments/my/matches/)

Sprint 3 Frontend Implementation (November 15, 2025):
- FE-T-008: Live Bracket View (/tournaments/<slug>/bracket/)
- FE-T-009: Match Detail Page (/tournaments/<slug>/matches/<id>/)
- FE-T-018: Tournament Results Page (/tournaments/<slug>/results/)

Sprint 4 Frontend Implementation (November 16, 2025):
- FE-T-010: Tournament Leaderboard Page (/tournaments/<slug>/leaderboard/)

Sprint 5 Frontend Implementation (November 16, 2025):
- FE-T-007: Tournament Lobby/Participant Hub (/tournaments/<slug>/lobby/)
- Check-In Action (/tournaments/<slug>/check-in/)
- Check-In Status Polling (/tournaments/<slug>/check-in-status/)
- Roster View (/tournaments/<slug>/roster/)

Sprint 8 Frontend Implementation (November 20, 2025):
- FE-T-014: Match Result Submission (/tournaments/<slug>/matches/<id>/submit-result/)
- FE-T-016: Dispute Submission (/tournaments/<slug>/matches/<id>/report-dispute/)

Backend APIs:
- Admin panel: /admin/tournaments/ (Django admin)
- API endpoints: /api/tournaments/ (Module 3.1)

Source Documents:
- Documents/ExecutionPlan/FrontEnd/Backlog/FRONTEND_TOURNAMENT_BACKLOG.md
- Documents/ExecutionPlan/FrontEnd/Screens/FRONTEND_TOURNAMENT_SITEMAP.md
- Documents/ExecutionPlan/FrontEnd/SPRINT_4_LEADERBOARDS_PLAN.md
- Documents/ExecutionPlan/FrontEnd/SPRINT_5_CHECK_IN_PLAN.md
"""

from django.urls import path
from django.views.generic import RedirectView
from apps.tournaments import views
from apps.tournaments.views import (
    TournamentRegistrationSuccessView,
)
from apps.tournaments.views.registration import (
    PaymentProofUploadView,
    PaymentRetryView,
)
# Form Builder - Registration Dashboard (player's "My Registrations")
from apps.tournaments.views.dynamic_registration import (
    RegistrationDashboardView,
)
# Permission Requests (Team Registration Permission Workflow)
from apps.tournaments.views.permission_requests import (
    request_permission,
    approve_permission,
    reject_permission,
    cancel_permission,
    my_permission_requests,
    team_permission_requests,
)
# Marketplace removed - admin-only feature now
# from apps.tournaments.views.template_marketplace import (
#     TemplateMarketplaceView,
#     TemplateDetailView,
#     CloneTemplateView,
#     RateTemplateView,
#     MarkRatingHelpfulView,
# )
from apps.tournaments.views.form_analytics_view import (
    FormAnalyticsDashboardView,
    FormAnalyticsAPIView,
)
from apps.tournaments.views.response_export_view import (
    ExportResponsesView,
    ExportPreviewView,
)
from apps.tournaments.views.bulk_operations_view import (
    BulkActionView,
    BulkActionPreviewView,
)
from apps.tournaments.views.webhook_views import (
    WebhookListView,
    WebhookDeliveryHistoryView,
    TestWebhookView,
)
from apps.tournaments.views.registration_ux_api import (
    SaveDraftAPIView,
    GetDraftAPIView,
    GetProgressAPIView,
    ValidateFieldAPIView,
)
from apps.tournaments.views.registration_dashboard import (
    RegistrationManagementDashboardView,
    ResponseDetailAPIView,
    QuickActionAPIView,
)
from apps.tournaments.views.player import (
    TournamentPlayerDashboardView,
    TournamentPlayerMatchesView,
)
from apps.tournaments.views.live import (
    TournamentBracketView,
    MatchDetailView,
    TournamentResultsView,
)
from apps.tournaments.views.leaderboard import (
    TournamentLeaderboardView,
)
from apps.tournaments.views import checkin
from apps.tournaments.views.match_room import (
    MatchRoomView,
    MatchCheckInView,
)
from apps.tournaments.views.result_submission import (
    SubmitResultView,
    report_dispute,
)
from apps.tournaments.views.group_stage import (
    GroupConfigurationView,
    GroupDrawView,
    GroupStandingsView,
)
from apps.tournaments.views.spectator import (
    PublicSpectatorView,
)
from apps.tournaments.views.hub import (
    TournamentHubView as HubMainView,
    HubStateAPIView,
    HubCheckInAPIView,
    HubAnnouncementsAPIView,
    HubRosterAPIView,
    HubSquadAPIView,
)
from apps.tournaments.views.organizer_results import (
    PendingResultsView,
    confirm_match_result,
    reject_match_result,
    override_match_result,
)

from apps.tournaments.views.smart_registration import (
    SmartRegistrationView,
    SmartRegistrationSuccessView,
    SmartDraftSaveAPIView,
    SmartDraftGetAPIView,
)
from apps.tournaments.views.withdrawal import (
    withdraw_registration_view,
)
from apps.tournaments.views.payment_status import (
    RegistrationStatusView,
    PaymentResubmitView,
    DownloadPaymentProofView,
)
from apps.tournaments.views.permission_request import RequestRegistrationPermissionView
from apps.tournaments.views.dispute_resolution import (
    resolve_dispute as resolve_dispute_view,
    update_dispute_status as update_dispute_status_view,
)
from apps.tournaments.views.disputes_management import (
    DisputeManagementView,
)
from apps.tournaments.views.health_metrics import (
    TournamentHealthMetricsView,
)
from apps.tournaments.views.organizer import (
    OrganizerDashboardView,
    OrganizerHubView,
    create_tournament,
)
from apps.tournaments.views.organizer_participants import (
    approve_registration,
    reject_registration,
    toggle_checkin,
    bulk_approve_registrations,
    bulk_reject_registrations,
    disqualify_participant,
    export_roster_csv,
    promote_registration,
    auto_promote_next,
    force_checkin,
    drop_noshow,
    close_drop_noshows,
    add_participant_manually,
    disqualify_with_cascade,
)
from apps.tournaments.views.organizer_payments import (
    verify_payment,
    reject_payment,
    bulk_verify_payments,
    process_refund,
    export_payments_csv,
    payment_history,
)
from apps.tournaments.views.organizer_matches import (
    submit_match_score,
    reschedule_match,
    forfeit_match,
    override_match_score,
    cancel_match,
)
from apps.tournaments.views.organizer_brackets import (
    generate_bracket,
    reset_bracket,
    reorder_seeds,
    publish_bracket,
)
from apps.tournaments.views.organizer_match_ops import (
    match_mark_live,
    match_pause,
    match_resume,
    match_force_complete,
    match_add_note,
    match_force_start,
)
from apps.tournaments.views.organizer_scheduling import (
    auto_schedule_round,
    bulk_shift_matches,
    add_schedule_break,
)

app_name = 'tournaments'

urlpatterns = [
    # FE-T-001: Tournament List/Discovery Page
    path('', views.TournamentListView.as_view(), name='list'),
    # Backwards-compatibility alias used in templates: "tournaments:browse"
    path('browse/', views.TournamentListView.as_view(), name='browse'),
    
    # Organizer Console URLs (must be before <slug> pattern)
    path('organizer/', OrganizerDashboardView.as_view(), name='organizer_dashboard'),
    path('organizer/create/', create_tournament, name='create_tournament'),
    path('organizer/<slug:slug>/', OrganizerHubView.as_view(), {'tab': 'overview'}, name='organizer_tournament_detail'),
    
    # Organizer Result Management (FE-T-015)
    path('organizer/<slug:slug>/pending-results/', PendingResultsView.as_view(), name='pending_results'),
    path('organizer/<slug:slug>/confirm-result/<int:match_id>/', confirm_match_result, name='confirm_result'),
    path('organizer/<slug:slug>/reject-result/<int:match_id>/', reject_match_result, name='reject_result'),
    path('organizer/<slug:slug>/override-result/<int:match_id>/', override_match_result, name='override_result'),
    
    # Organizer Hub Actions
    path('organizer/<slug:slug>/approve-registration/<int:registration_id>/', approve_registration, name='approve_registration'),
    path('organizer/<slug:slug>/reject-registration/<int:registration_id>/', reject_registration, name='reject_registration'),
    path('organizer/<slug:slug>/verify-payment/<int:payment_id>/', verify_payment, name='verify_payment'),
    path('organizer/<slug:slug>/reject-payment/<int:payment_id>/', reject_payment, name='reject_payment'),
    path('organizer/<slug:slug>/toggle-checkin/<int:registration_id>/', toggle_checkin, name='toggle_checkin'),
    
    # Organizer Dispute Resolution (FE-T-017 + FE-T-025)
    path('organizer/<slug:slug>/disputes/manage/', DisputeManagementView.as_view(), name='disputes_manage'),
    path('organizer/<slug:slug>/resolve-dispute/<int:dispute_id>/', resolve_dispute_view, name='resolve_dispute'),
    path('organizer/<slug:slug>/update-dispute-status/<int:dispute_id>/', update_dispute_status_view, name='update_dispute_status'),
    path('organizer/<slug:slug>/submit-score/<int:match_id>/', submit_match_score, name='submit_match_score'),
    
    # Organizer Health Metrics (FE-T-026)
    path('organizer/<slug:slug>/health/', TournamentHealthMetricsView.as_view(), name='health_metrics'),
    
    # FE-T-022: Participant Management Actions
    path('organizer/<slug:slug>/bulk-approve-registrations/', bulk_approve_registrations, name='bulk_approve_registrations'),
    path('organizer/<slug:slug>/bulk-reject-registrations/', bulk_reject_registrations, name='bulk_reject_registrations'),
    path('organizer/<slug:slug>/disqualify/<int:registration_id>/', disqualify_participant, name='disqualify_participant'),
    path('organizer/<slug:slug>/promote-waitlist/<int:registration_id>/', promote_registration, name='promote_registration'),
    path('organizer/<slug:slug>/auto-promote-waitlist/', auto_promote_next, name='auto_promote_next'),
    path('organizer/<slug:slug>/export-roster/', export_roster_csv, name='export_roster_csv'),
    
    # P3-T06: Participant Data Control
    path('organizer/<slug:slug>/add-participant/', add_participant_manually, name='add_participant_manually'),
    path('organizer/<slug:slug>/dq-cascade/<int:registration_id>/', disqualify_with_cascade, name='disqualify_with_cascade'),
    
    # P2-T05: Check-In Control Panel Actions
    path('organizer/<slug:slug>/force-checkin/<int:registration_id>/', force_checkin, name='force_checkin'),
    path('organizer/<slug:slug>/drop-noshow/<int:registration_id>/', drop_noshow, name='drop_noshow'),
    path('organizer/<slug:slug>/close-drop-noshows/', close_drop_noshows, name='close_drop_noshows'),
    
    # FE-T-023: Payment Management Actions
    path('organizer/<slug:slug>/bulk-verify-payments/', bulk_verify_payments, name='bulk_verify_payments'),
    path('organizer/<slug:slug>/refund-payment/<int:payment_id>/', process_refund, name='process_refund'),
    path('organizer/<slug:slug>/export-payments/', export_payments_csv, name='export_payments_csv'),
    path('organizer/<slug:slug>/registrations/<int:registration_id>/payment-history/', payment_history, name='payment_history'),
    
    # FE-T-024: Match Management Actions
    path('organizer/<slug:slug>/reschedule-match/<int:match_id>/', reschedule_match, name='reschedule_match'),
    path('organizer/<slug:slug>/forfeit-match/<int:match_id>/', forfeit_match, name='forfeit_match'),
    path('organizer/<slug:slug>/override-score/<int:match_id>/', override_match_score, name='override_match_score'),
    path('organizer/<slug:slug>/cancel-match/<int:match_id>/', cancel_match, name='cancel_match'),
    
    # P3-T01: Bracket Generation & Reset
    path('organizer/<slug:slug>/generate-bracket/', generate_bracket, name='generate_bracket'),
    path('organizer/<slug:slug>/reset-bracket/', reset_bracket, name='reset_bracket'),
    
    # P3-T02: Seeding Reorder & Publish
    path('organizer/<slug:slug>/reorder-seeds/', reorder_seeds, name='reorder_seeds'),
    path('organizer/<slug:slug>/publish-bracket/', publish_bracket, name='publish_bracket'),
    
    # P3-T03: Match Operations (Match Medic)
    path('organizer/<slug:slug>/match-ops/<int:match_id>/mark-live/', match_mark_live, name='match_mark_live'),
    path('organizer/<slug:slug>/match-ops/<int:match_id>/pause/', match_pause, name='match_pause'),
    path('organizer/<slug:slug>/match-ops/<int:match_id>/resume/', match_resume, name='match_resume'),
    path('organizer/<slug:slug>/match-ops/<int:match_id>/force-complete/', match_force_complete, name='match_force_complete'),
    path('organizer/<slug:slug>/match-ops/<int:match_id>/add-note/', match_add_note, name='match_add_note'),
    path('organizer/<slug:slug>/match-ops/<int:match_id>/force-start/', match_force_start, name='match_force_start'),
    
    # P3-T04: Scheduling Panel
    path('organizer/<slug:slug>/auto-schedule-round/', auto_schedule_round, name='auto_schedule_round'),
    path('organizer/<slug:slug>/bulk-shift-matches/', bulk_shift_matches, name='bulk_shift_matches'),
    path('organizer/<slug:slug>/add-schedule-break/', add_schedule_break, name='add_schedule_break'),
    
    # Organizer Hub Tab (catch-all for tabs — MUST be after all specific organizer/ URLs)
    path('organizer/<slug:slug>/<str:tab>/', OrganizerHubView.as_view(), name='organizer_hub'),
    
    # Sprint 2: Player Dashboard URLs (must be before <slug> pattern)
    path('my/', TournamentPlayerDashboardView.as_view(), name='my_tournaments'),
    path('my/matches/', TournamentPlayerMatchesView.as_view(), name='my_matches'),
    path('my/registrations/', RegistrationDashboardView.as_view(), name='registration_dashboard'),
    path('my/permissions/', my_permission_requests, name='my_permissions'),
    
    # Permission Request Workflows (Team Registration)
    path('permissions/<int:request_id>/approve/', approve_permission, name='approve_permission'),
    path('permissions/<int:request_id>/reject/', reject_permission, name='reject_permission'),
    path('permissions/<int:request_id>/cancel/', cancel_permission, name='cancel_permission'),
    
    # FE-T-002: Tournament Detail Page (includes FE-T-003: CTA states)
    path('<slug:slug>/', views.TournamentDetailView.as_view(), name='detail'),
    
    # Participant check-in
    path('<slug:slug>/checkin/', views.participant_checkin, name='participant_checkin'),
    

    
    # Smart Registration (Production — One-Click Auto-Fill)
    path('<slug:slug>/register/smart/', SmartRegistrationView.as_view(), name='smart_registration'),
    path('<slug:slug>/register/smart/success/<int:registration_id>/', SmartRegistrationSuccessView.as_view(), name='smart_registration_success'),
    
    # P2-T07: Smart Registration Draft Auto-Save API
    path('<slug:slug>/api/smart-draft/save/', SmartDraftSaveAPIView.as_view(), name='smart_draft_save'),
    path('<slug:slug>/api/smart-draft/get/', SmartDraftGetAPIView.as_view(), name='smart_draft_get'),
    
    # Registration Permission Request (Team Members)
    path('<slug:slug>/request-permission/', request_permission, name='request_permission'),
    
    # Payment Status & Management
    path('<slug:slug>/registration/<int:registration_id>/status/', RegistrationStatusView.as_view(), name='registration_status'),
    path('<slug:slug>/registration/<int:registration_id>/resubmit/', PaymentResubmitView.as_view(), name='payment_resubmit'),
    path('<slug:slug>/payment/<int:payment_id>/download/', DownloadPaymentProofView.as_view(), name='download_payment_proof'),
    
    # Registration Withdrawal
    path('<slug:slug>/withdraw/', withdraw_registration_view, name='withdraw_registration'),
    

    
    # FE-T-004: SMART Registration (Primary — replaces dynamic and wizard flows)
    path('<slug:tournament_slug>/register/', SmartRegistrationView.as_view(), name='register'),
    path('<slug:tournament_slug>/register/success/<int:registration_id>/', SmartRegistrationSuccessView.as_view(), name='dynamic_registration_success'),


    
    # Payment handling for tournament registration
    path('registration/<int:registration_id>/payment/upload/', PaymentProofUploadView.as_view(), name='payment_upload'),
    path('registration/<int:registration_id>/payment/retry/', PaymentRetryView.as_view(), name='payment_retry'),
    
    # Legacy Registration success (backward compatibility)
    path('<slug:slug>/register/success/', TournamentRegistrationSuccessView.as_view(), name='register_success'),
    
    # Sprint 3: Public Live Tournament Experience
    # FE-T-008: Live Bracket View
    path('<slug:slug>/bracket/', TournamentBracketView.as_view(), name='bracket'),
    # FE-T-009: Match Watch / Match Detail Page
    path('<slug:slug>/matches/<int:match_id>/', MatchDetailView.as_view(), name='match_detail'),
    # Match Room / Battlefield (Participant-only interactive room)
    path('<slug:slug>/matches/<int:match_id>/room/', MatchRoomView.as_view(), name='match_room'),
    path('<slug:slug>/matches/<int:match_id>/room/check-in/', MatchCheckInView.as_view(), name='match_room_checkin'),
    # FE-T-018: Tournament Results Page
    path('<slug:slug>/results/', TournamentResultsView.as_view(), name='results'),
    
    # Sprint 8: Match Result Submission & Disputes (FE-T-014, FE-T-016)
    path('<slug:slug>/matches/<int:match_id>/submit-result/', SubmitResultView.as_view(), name='submit_result'),
    path('<slug:slug>/matches/<int:match_id>/report-dispute/', report_dispute, name='report_dispute'),
    
    # Sprint 4: Leaderboard & Standings
    # FE-T-010: Tournament Leaderboard Page
    path('<slug:slug>/leaderboard/', TournamentLeaderboardView.as_view(), name='leaderboard'),
    
    # Sprint 5: Check-In & Tournament Lobby (FE-T-007)
    # /lobby/ redirects to The Hub (v3) — see checkin.TournamentLobbyView
    path('<slug:slug>/lobby/', checkin.TournamentLobbyView.as_view(), name='lobby'),
    path('<slug:slug>/check-in/', checkin.CheckInActionView.as_view(), name='check_in'),
    
    # Sprint 10: Group Stage Management (FE-T-011, FE-T-012, FE-T-013)
    path('organizer/<slug:slug>/groups/configure/', GroupConfigurationView.as_view(), name='group_configure'),
    path('organizer/<slug:slug>/groups/draw/', GroupDrawView.as_view(), name='group_draw'),
    path('<slug:slug>/groups/standings/', GroupStandingsView.as_view(), name='group_standings'),
    
    # Sprint 11: Public Spectator View (FE-T-006)
    path('<slug:slug>/spectate/', PublicSpectatorView.as_view(), name='spectate'),
    
    # Sprint 12: The Hub — Unified Participant Mission Control (v3)
    path('<slug:slug>/hub/', HubMainView.as_view(), name='tournament_hub'),
    path('<slug:slug>/hub/api/state/', HubStateAPIView.as_view(), name='hub_state_api'),
    path('<slug:slug>/hub/api/check-in/', HubCheckInAPIView.as_view(), name='hub_checkin_api'),
    path('<slug:slug>/hub/api/announcements/', HubAnnouncementsAPIView.as_view(), name='hub_announcements_api'),
    path('<slug:slug>/hub/api/roster/', HubRosterAPIView.as_view(), name='hub_roster_api'),
    path('<slug:slug>/hub/api/squad/', HubSquadAPIView.as_view(), name='hub_squad_api'),

    # Legacy URL compatibility
    path('hub/', RedirectView.as_view(pattern_name='tournaments:list', permanent=True), name='hub'),
    
    # === Form Analytics ===
    path('<slug:tournament_slug>/analytics/', FormAnalyticsDashboardView.as_view(), name='form_analytics'),
    path('<slug:tournament_slug>/analytics/api/', FormAnalyticsAPIView.as_view(), name='form_analytics_api'),
    
    # === Response Export ===
    path('<slug:tournament_slug>/export/', ExportResponsesView.as_view(), name='export_responses'),
    path('<slug:tournament_slug>/export/preview/', ExportPreviewView.as_view(), name='export_preview'),
    
    # === Bulk Operations ===
    path('<slug:tournament_slug>/bulk-action/', BulkActionView.as_view(), name='bulk_action'),
    path('<slug:tournament_slug>/bulk-action/preview/', BulkActionPreviewView.as_view(), name='bulk_action_preview'),
    
    # === Webhooks ===
    path('<slug:tournament_slug>/webhooks/', WebhookListView.as_view(), name='webhooks'),
    path('webhooks/<int:webhook_id>/history/', WebhookDeliveryHistoryView.as_view(), name='webhook_history'),
    path('webhooks/<int:webhook_id>/test/', TestWebhookView.as_view(), name='webhook_test'),
    
    # === Registration UX APIs ===
    path('<slug:tournament_slug>/api/draft/save/', SaveDraftAPIView.as_view(), name='save_draft'),
    path('<slug:tournament_slug>/api/draft/get/', GetDraftAPIView.as_view(), name='get_draft'),
    path('<slug:tournament_slug>/api/progress/', GetProgressAPIView.as_view(), name='get_progress'),
    path('<slug:tournament_slug>/api/validate-field/', ValidateFieldAPIView.as_view(), name='validate_field'),
    
    # === Registration Management Dashboard ===
    path('<slug:tournament_slug>/manage/', RegistrationManagementDashboardView.as_view(), name='registration_management'),
    path('responses/<int:response_id>/detail/', ResponseDetailAPIView.as_view(), name='response_detail'),
    path('responses/<int:response_id>/quick-action/', QuickActionAPIView.as_view(), name='quick_action'),
]

# Note: Actual tournament management is done through:
# 1. Django Admin: /admin/tournaments/
# 2. REST API: /api/tournaments/ (Module 3.1)
# 3. Future frontend will be rebuilt from scratch

