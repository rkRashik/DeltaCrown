# Tournament App Views & Templates Audit
**Date:** December 19, 2025  
**Scope:** User-facing layers in `apps/tournaments/`  
**Purpose:** Document all views, URL patterns, templates, and API endpoints

---

## 1. URL Configuration

### 1.1 Main URL Router
**File:** `apps/tournaments/urls.py`

**Total URL Patterns:** 78 routes (organized by feature)

#### Public Tournament Discovery
- `''` → `TournamentListView` (name: `list`) - FE-T-001
- `'browse/'` → `TournamentListView` (name: `browse`) - backward compatibility alias
- `'<slug:slug>/'` → `TournamentDetailView` (name: `detail`) - FE-T-002

#### Organizer Console (Protected Routes)
- `'organizer/'` → `OrganizerDashboardView` (name: `organizer_dashboard`)
- `'organizer/create/'` → `create_tournament` (function view)
- `'organizer/<slug:slug>/'` → `OrganizerHubView` (name: `organizer_tournament_detail`)
- `'organizer/<slug:slug>/<str:tab>/'` → `OrganizerHubView` (name: `organizer_hub`)

#### Organizer Result Management (FE-T-015)
- `'organizer/<slug:slug>/pending-results/'` → `PendingResultsView`
- `'organizer/<slug:slug>/confirm-result/<int:match_id>/'` → `confirm_match_result`
- `'organizer/<slug:slug>/reject-result/<int:match_id>/'` → `reject_match_result`
- `'organizer/<slug:slug>/override-result/<int:match_id>/'` → `override_match_result`

#### Organizer Hub Actions
- `'organizer/<slug:slug>/approve-registration/<int:registration_id>/'` → `approve_registration`
- `'organizer/<slug:slug>/reject-registration/<int:registration_id>/'` → `reject_registration`
- `'organizer/<slug:slug>/verify-payment/<int:payment_id>/'` → `verify_payment`
- `'organizer/<slug:slug>/reject-payment/<int:payment_id>/'` → `reject_payment`
- `'organizer/<slug:slug>/toggle-checkin/<int:registration_id>/'` → `toggle_checkin`

#### Organizer Dispute Resolution (FE-T-017, FE-T-025)
- `'organizer/<slug:slug>/disputes/manage/'` → `DisputeManagementView`
- `'organizer/<slug:slug>/resolve-dispute/<int:dispute_id>/'` → `resolve_dispute_view`
- `'organizer/<slug:slug>/update-dispute-status/<int:dispute_id>/'` → `update_dispute_status_view`
- `'organizer/<slug:slug>/submit-score/<int:match_id>/'` → `submit_match_score`

#### Organizer Health Metrics (FE-T-026)
- `'organizer/<slug:slug>/health/'` → `TournamentHealthMetricsView`

#### Organizer Participant Management (FE-T-022)
- `'organizer/<slug:slug>/bulk-approve-registrations/'` → `bulk_approve_registrations`
- `'organizer/<slug:slug>/bulk-reject-registrations/'` → `bulk_reject_registrations`
- `'organizer/<slug:slug>/disqualify/<int:registration_id>/'` → `disqualify_participant`
- `'organizer/<slug:slug>/export-roster/'` → `export_roster_csv`

#### Organizer Payment Management (FE-T-023)
- `'organizer/<slug:slug>/bulk-verify-payments/'` → `bulk_verify_payments`
- `'organizer/<slug:slug>/refund-payment/<int:payment_id>/'` → `process_refund`
- `'organizer/<slug:slug>/export-payments/'` → `export_payments_csv`
- `'organizer/<slug:slug>/registrations/<int:registration_id>/payment-history/'` → `payment_history`

#### Organizer Match Management (FE-T-024)
- `'organizer/<slug:slug>/reschedule-match/<int:match_id>/'` → `reschedule_match`
- `'organizer/<slug:slug>/forfeit-match/<int:match_id>/'` → `forfeit_match`
- `'organizer/<slug:slug>/override-score/<int:match_id>/'` → `override_match_score`
- `'organizer/<slug:slug>/cancel-match/<int:match_id>/'` → `cancel_match`

#### Player Dashboard (Protected Routes)
- `'my/'` → `TournamentPlayerDashboardView` (name: `my_tournaments`) - FE-T-005
- `'my/matches/'` → `TournamentPlayerMatchesView` (name: `my_matches`)
- `'my/registrations/'` → `RegistrationDashboardView`
- `'my/permissions/'` → `my_permission_requests`

#### Permission Request Workflows (Team Registration)
- `'permissions/<int:request_id>/approve/'` → `approve_permission`
- `'permissions/<int:request_id>/reject/'` → `reject_permission`
- `'permissions/<int:request_id>/cancel/'` → `cancel_permission`

#### Registration Workflows
- `'<slug:slug>/checkin/'` → `participant_checkin`
- `'<slug:slug>/register/wizard/'` → `RegistrationWizardView` (name: `registration_wizard`)
- `'<slug:slug>/register/wizard/success/'` → `WizardSuccessView`
- `'<slug:slug>/request-permission/'` → `request_permission`

#### Payment Status & Management
- `'<slug:slug>/registration/<int:registration_id>/status/'` → `RegistrationStatusView`
- `'<slug:slug>/registration/<int:registration_id>/resubmit/'` → `PaymentResubmitView`
- `'<slug:slug>/payment/<int:payment_id>/download/'` → `DownloadPaymentProofView`

#### Registration Withdrawal
- `'<slug:slug>/withdraw/'` → `withdraw_registration_view`

#### Tournament Team Registration (Professional)
- `'<slug:slug>/register/team/'` → `TeamRegistrationView`
- `'<slug:slug>/register/team/<int:step>/'` → `TeamRegistrationView`
- `'<slug:slug>/register/success/'` → `RegistrationSuccessView`

#### Dynamic Registration System (Form Builder - FE-T-004)
- `'<slug:tournament_slug>/register/'` → `DynamicRegistrationView`
- `'<slug:tournament_slug>/register/success/<int:response_id>/'` → `RegistrationSuccessView`

#### Payment Handling
- `'registration/<int:registration_id>/payment/upload/'` → `PaymentProofUploadView`
- `'registration/<int:registration_id>/payment/retry/'` → `PaymentRetryView`

#### Live Tournament Experience (Sprint 3)
- `'<slug:slug>/bracket/'` → `TournamentBracketView` (name: `bracket`) - FE-T-008
- `'<slug:slug>/matches/<int:match_id>/'` → `MatchDetailView` (name: `match_detail`) - FE-T-009
- `'<slug:slug>/results/'` → `TournamentResultsView` (name: `results`) - FE-T-018

#### Match Result Submission & Disputes (Sprint 8: FE-T-014, FE-T-016)
- `'<slug:slug>/matches/<int:match_id>/submit-result/'` → `SubmitResultView`
- `'<slug:slug>/matches/<int:match_id>/report-dispute/'` → `report_dispute`

#### Leaderboard & Standings (Sprint 4: FE-T-010)
- `'<slug:slug>/leaderboard/'` → `TournamentLeaderboardView`

#### Check-In & Tournament Lobby (Sprint 5: FE-T-007)
- `'<slug:slug>/lobby/'` → `checkin.TournamentLobbyView`
- `'<slug:slug>/check-in/'` → `checkin.CheckInActionView`
- `'<slug:slug>/check-in-status/'` → `checkin.CheckInStatusView`
- `'<slug:slug>/roster/'` → `checkin.RosterView`

#### Group Stage Management (Sprint 10: FE-T-011, FE-T-012, FE-T-013)
- `'organizer/<slug:slug>/groups/configure/'` → `GroupConfigurationView`
- `'organizer/<slug:slug>/groups/draw/'` → `GroupDrawView`
- `'<slug:slug>/groups/standings/'` → `GroupStandingsView`

#### Enhanced Tournament Lobby (Sprint 10: FE-T-007)
- `'<slug:slug>/lobby/v2/'` → `TournamentLobbyView`
- `'<slug:slug>/lobby/check-in/'` → `CheckInView`
- `'api/<slug:slug>/lobby/roster/'` → `LobbyRosterAPIView`
- `'api/<slug:slug>/lobby/announcements/'` → `LobbyAnnouncementsAPIView`

#### Public Spectator View (Sprint 11: FE-T-006)
- `'<slug:slug>/spectate/'` → `PublicSpectatorView`

#### Form Analytics
- `'<slug:tournament_slug>/analytics/'` → `FormAnalyticsDashboardView`
- `'<slug:tournament_slug>/analytics/api/'` → `FormAnalyticsAPIView`

#### Response Export
- `'<slug:tournament_slug>/export/'` → `ExportResponsesView`
- `'<slug:tournament_slug>/export/preview/'` → `ExportPreviewView`

#### Bulk Operations
- `'<slug:tournament_slug>/bulk-action/'` → `BulkActionView`
- `'<slug:tournament_slug>/bulk-action/preview/'` → `BulkActionPreviewView`

#### Webhooks
- `'<slug:tournament_slug>/webhooks/'` → `WebhookListView`
- `'webhooks/<int:webhook_id>/history/'` → `WebhookDeliveryHistoryView`
- `'webhooks/<int:webhook_id>/test/'` → `TestWebhookView`

#### Registration UX APIs
- `'<slug:tournament_slug>/api/draft/save/'` → `SaveDraftAPIView`
- `'<slug:tournament_slug>/api/draft/get/'` → `GetDraftAPIView`
- `'<slug:tournament_slug>/api/progress/'` → `GetProgressAPIView`
- `'<slug:tournament_slug>/api/validate-field/'` → `ValidateFieldAPIView`

#### Registration Management Dashboard
- `'<slug:tournament_slug>/manage/'` → `RegistrationManagementDashboardView`
- `'responses/<int:response_id>/detail/'` → `ResponseDetailAPIView`
- `'responses/<int:response_id>/quick-action/'` → `QuickActionAPIView`

---

## 2. View Classes & Functions

### 2.1 Main Views (`apps/tournaments/views/main.py`)
1. **`TournamentListView(ListView)`**
   - Purpose: Public tournament discovery page with filters
   - Template: `tournaments/list_redesigned.html`
   - Context: Tournaments with status filtering (upcoming, live, completed)

2. **`TournamentDetailView(DetailView)`**
   - Purpose: Tournament detail page with registration CTA states
   - Template: `tournaments/detailPages/detail.html`
   - Context: Tournament object, registration status, CTA button logic

3. **`participant_checkin()`** (function view)
   - Purpose: Legacy check-in endpoint
   - Returns: Redirect or JSON response

### 2.2 Organizer Views (`apps/tournaments/views/organizer.py`)
1. **`OrganizerDashboardView(LoginRequiredMixin, OrganizerRequiredMixin, ListView)`**
   - Purpose: Organizer dashboard showing all tournaments created by user
   - Template: `tournaments/organizer/dashboard.html`
   - Permissions: Requires organizer role

2. **`OrganizerTournamentDetailView(LoginRequiredMixin, OrganizerRequiredMixin, DetailView)`**
   - Purpose: Organizer-specific tournament detail view
   - Template: `tournaments/organizer/tournament_detail.html`
   - Permissions: Requires tournament ownership

3. **`OrganizerHubView(LoginRequiredMixin, View)`**
   - Purpose: Multi-tab organizer hub (overview, participants, payments, brackets, disputes, settings)
   - Method: `get()` handles tab routing
   - Context: Dynamic based on `tab` parameter (overview, participants, payments, brackets, announcements, disputes, settings)

4. **Function Views (POST actions):**
   - `approve_registration(request, slug, registration_id)`
   - `reject_registration(request, slug, registration_id)`
   - `verify_payment(request, slug, payment_id)`
   - `reject_payment(request, slug, payment_id)`
   - `toggle_checkin(request, slug, registration_id)`
   - `submit_match_score(request, slug, match_id)`
   - `create_tournament(request)`
   - `bulk_approve_registrations(request, slug)` - FE-T-022
   - `bulk_reject_registrations(request, slug)` - FE-T-022
   - `disqualify_participant(request, slug, registration_id)` - FE-T-022
   - `export_roster_csv(request, slug)` - FE-T-022
   - `bulk_verify_payments(request, slug)` - FE-T-023
   - `process_refund(request, slug, payment_id)` - FE-T-023
   - `export_payments_csv(request, slug)` - FE-T-023
   - `payment_history(request, slug, registration_id)` - FE-T-023
   - `reschedule_match(request, slug, match_id)` - FE-T-024
   - `forfeit_match(request, slug, match_id)` - FE-T-024
   - `override_match_score(request, slug, match_id)` - FE-T-024
   - `cancel_match(request, slug, match_id)` - FE-T-024

### 2.3 Organizer Results Views (`apps/tournaments/views/organizer_results.py`)
1. **`PendingResultsView(LoginRequiredMixin, ListView)`**
   - Purpose: List pending match results requiring organizer review (FE-T-015)
   - Template: `tournaments/organizer/pending_results.html`
   - Context: MatchResultSubmission objects with STATUS_PENDING

2. **Function Views:**
   - `confirm_match_result(request, slug, match_id)` - Approve submitted result
   - `reject_match_result(request, slug, match_id)` - Reject submitted result
   - `override_match_result(request, slug, match_id)` - Override with organizer score

### 2.4 Player Dashboard Views (`apps/tournaments/views/player.py`)
1. **`TournamentPlayerDashboardView(LoginRequiredMixin, ListView)`**
   - Purpose: Player's personal tournament dashboard (FE-T-005)
   - Template: `tournaments/public/player/my_tournaments.html`
   - Context: User's registrations (active, upcoming, completed)

2. **`TournamentPlayerMatchesView(LoginRequiredMixin, ListView)`**
   - Purpose: Player's upcoming and past matches
   - Template: `tournaments/public/player/my_matches.html`
   - Context: Match objects for user's registrations

### 2.5 Registration Views (`apps/tournaments/views/registration.py`)
1. **`TournamentRegistrationView(LoginRequiredMixin, View)`**
   - Purpose: Legacy registration wizard (kept for backward compatibility)
   - Template: `tournaments/public/registration/wizard.html`

2. **`TournamentRegistrationSuccessView(LoginRequiredMixin, View)`**
   - Purpose: Registration success confirmation page
   - Template: `tournaments/public/registration/success.html`

3. **`PaymentProofUploadView(LoginRequiredMixin, View)`**
   - Purpose: Upload payment proof after registration
   - Template: `tournaments/public/registration/payment_upload.html`

4. **`PaymentRetryView(LoginRequiredMixin, View)`**
   - Purpose: Retry payment proof upload after rejection
   - Template: `tournaments/public/registration/payment_retry.html`

### 2.6 Dynamic Registration Views (`apps/tournaments/views/dynamic_registration.py`)
1. **`DynamicRegistrationView(LoginRequiredMixin, View)`**
   - Purpose: Form Builder-based registration system (FE-T-004)
   - Template: `tournaments/form_builder/form_step.html`
   - Context: Dynamic form fields from TournamentTemplate

2. **`RegistrationSuccessView(LoginRequiredMixin, View)`**
   - Purpose: Success page after dynamic registration
   - Template: `tournaments/form_builder/registration_success.html`

3. **`RegistrationDashboardView(LoginRequiredMixin, View)`**
   - Purpose: Organizer view of all registrations with form responses
   - Template: `tournaments/form_builder/registration_dashboard.html`

### 2.7 Registration Wizard Views (`apps/tournaments/views/registration_wizard.py`)
1. **`RegistrationWizardView(LoginRequiredMixin, View)`**
   - Purpose: Beautiful multi-step registration wizard (Production)
   - Templates: Uses team_registration templates dynamically
   - Context: Step-based form rendering

2. **`RegistrationSuccessView(LoginRequiredMixin, View)`**
   - Purpose: Success confirmation after wizard completion
   - Template: Rendered inline or redirected

### 2.8 Team Registration Views (`apps/tournaments/views/tournament_team_registration.py`)
1. **`SoloRegistrationDemoView(LoginRequiredMixin, View)`**
   - Purpose: Solo player registration demo
   - Templates: Multiple step templates (solo_step1.html, solo_step2.html, solo_step3.html)

2. **`TeamRegistrationView(LoginRequiredMixin, View)`**
   - Purpose: Team registration with roster management
   - Templates: Multiple step templates (team_step1.html, team_step2.html, team_step3.html)

3. **`RegistrationSuccessView(LoginRequiredMixin, View)`**
   - Purpose: Success page for team/solo registration
   - Templates: solo_success.html, team_success.html

### 2.9 Live Views (`apps/tournaments/views/live.py`)
1. **`TournamentBracketView(DetailView)`**
   - Purpose: Live bracket visualization (FE-T-008)
   - Template: `tournaments/public/live/bracket.html`
   - Context: Bracket structure, matches, BracketNode tree

2. **`MatchDetailView(DetailView)`**
   - Purpose: Match detail page with live updates (FE-T-009)
   - Template: `tournaments/public/live/match_detail.html`
   - Context: Match object, participants, scores, lobby info

3. **`TournamentResultsView(DetailView)`**
   - Purpose: Final tournament results page (FE-T-018)
   - Template: `tournaments/public/live/results.html`
   - Context: Final standings, winners, prizes

### 2.10 Leaderboard Views (`apps/tournaments/views/leaderboard.py`)
1. **`TournamentLeaderboardView(DetailView)`**
   - Purpose: Live leaderboard with rankings (FE-T-010)
   - Template: `tournaments/public/leaderboard/index.html`
   - Context: Participant rankings sorted by score/seed

### 2.11 Check-In Views (`apps/tournaments/views/checkin.py`)
1. **`TournamentLobbyView(LoginRequiredMixin, DetailView)`**
   - Purpose: Pre-tournament lobby for participants (FE-T-007)
   - Template: `tournaments/lobby/hub.html`
   - Context: Tournament object, check-in status, rules, discord link

2. **`CheckInActionView(LoginRequiredMixin, View)`**
   - Purpose: POST endpoint for check-in action
   - Returns: JSON response with check-in status

3. **`CheckInStatusView(LoginRequiredMixin, View)`**
   - Purpose: GET endpoint for polling check-in status
   - Returns: JSON response with is_checked_in boolean

4. **`RosterView(View)`**
   - Purpose: Public roster view showing checked-in participants
   - Returns: JSON response with participant list

### 2.12 Enhanced Lobby Views (`apps/tournaments/views/lobby.py`)
1. **`TournamentLobbyView(LoginRequiredMixin, View)`**
   - Purpose: Enhanced lobby with announcements and roster (Sprint 10)
   - Template: `tournaments/lobby/hub.html`

2. **`CheckInView(LoginRequiredMixin, View)`**
   - Purpose: POST endpoint for check-in with validation
   - Returns: JSON response

3. **`LobbyRosterAPIView(LoginRequiredMixin, View)`**
   - Purpose: GET endpoint for lobby roster data
   - Returns: JSON response with participant list

4. **`LobbyAnnouncementsAPIView(LoginRequiredMixin, View)`**
   - Purpose: GET endpoint for lobby announcements
   - Returns: JSON response with announcements array

### 2.13 Result Submission Views (`apps/tournaments/views/result_submission.py`)
1. **`SubmitResultView(LoginRequiredMixin, View)`**
   - Purpose: Player-submitted match result form (FE-T-014)
   - Template: `tournaments/public/live/submit_result_form.html`
   - Context: Match object, proof upload form

2. **`report_dispute()` (function view)**
   - Purpose: Report match dispute (FE-T-016)
   - Returns: Redirect or JSON response

### 2.14 Group Stage Views (`apps/tournaments/views/group_stage.py`)
1. **`GroupConfigurationView(LoginRequiredMixin, View)`**
   - Purpose: Configure group stage settings (FE-T-011)
   - Template: `tournaments/organizer/groups/config.html`

2. **`GroupDrawView(LoginRequiredMixin, View)`**
   - Purpose: Perform group draw/seeding (FE-T-012)
   - Template: `tournaments/organizer/groups/draw.html`

3. **`GroupStandingsView(View)`**
   - Purpose: Public group standings view (FE-T-013)
   - Template: `tournaments/groups/standings.html`

### 2.15 Spectator Views (`apps/tournaments/views/spectator.py`)
1. **`PublicSpectatorView(TemplateView)`**
   - Purpose: Public spectator hub with live updates (FE-T-006)
   - Template: `tournaments/spectator/hub.html`
   - Context: Tournament matches, bracket, leaderboard

### 2.16 Payment Status Views (`apps/tournaments/views/payment_status.py`)
1. **`RegistrationStatusView(LoginRequiredMixin, View)`**
   - Purpose: View registration and payment status
   - Template: `tournaments/registration/status.html`

2. **`PaymentResubmitView(LoginRequiredMixin, View)`**
   - Purpose: Resubmit payment proof after rejection
   - Template: `tournaments/registration/resubmit_payment.html`

3. **`DownloadPaymentProofView(LoginRequiredMixin, View)`**
   - Purpose: Download payment proof file
   - Returns: FileResponse

### 2.17 Withdrawal Views (`apps/tournaments/views/withdrawal.py`)
1. **`withdraw_registration_view()` (function view)**
   - Purpose: Withdraw registration with refund calculation
   - Template: `tournaments/registration/withdraw.html`

### 2.18 Permission Request Views (`apps/tournaments/views/permission_requests.py`)
1. **Function Views (Team Registration Permission Workflow):**
   - `request_permission(request, tournament_slug)` - Request registration permission from team captain
   - `approve_permission(request, request_id)` - Captain approves permission request
   - `reject_permission(request, request_id)` - Captain rejects permission request
   - `cancel_permission(request, request_id)` - Requester cancels permission request
   - `my_permission_requests(request)` - List user's permission requests
   - `team_permission_requests(request)` - List team's incoming permission requests

2. **`RequestRegistrationPermissionView(LoginRequiredMixin, View)`**
   - Purpose: Alternative permission request view
   - File: `apps/tournaments/views/permission_request.py`

### 2.19 Dispute Management Views (`apps/tournaments/views/disputes_management.py`)
1. **`DisputeManagementView(LoginRequiredMixin, UserPassesTestMixin, TemplateView)`**
   - Purpose: Organizer dispute management dashboard (FE-T-025)
   - Template: `tournaments/organizer/disputes.html`
   - Context: Open disputes, resolution workflow

### 2.20 Health Metrics Views (`apps/tournaments/views/health_metrics.py`)
1. **`TournamentHealthMetricsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView)`**
   - Purpose: Tournament health dashboard with SLI/SLO metrics (FE-T-026)
   - Template: `tournaments/organizer/health_metrics.html`
   - Context: Registration rate, check-in rate, dispute rate, match completion rate

### 2.21 Form Analytics Views (`apps/tournaments/views/form_analytics_view.py`)
1. **`FormAnalyticsDashboardView(LoginRequiredMixin, UserPassesTestMixin, DetailView)`**
   - Purpose: Form Builder analytics dashboard
   - Template: `tournaments/analytics/dashboard.html`
   - Context: Response metrics, completion rates, field analytics

2. **`FormAnalyticsAPIView(LoginRequiredMixin, UserPassesTestMixin, DetailView)`**
   - Purpose: JSON API for form analytics data
   - Returns: JSON response

### 2.22 Export Views (`apps/tournaments/views/response_export_view.py`)
1. **`ExportResponsesView(LoginRequiredMixin, UserPassesTestMixin, View)`**
   - Purpose: Export registration responses to CSV
   - Returns: CSV file download

2. **`ExportPreviewView(LoginRequiredMixin, UserPassesTestMixin, View)`**
   - Purpose: Preview export data before download
   - Template: `tournaments/responses/export.html`

### 2.23 Bulk Operations Views (`apps/tournaments/views/bulk_operations_view.py`)
1. **`BulkActionView(LoginRequiredMixin, UserPassesTestMixin, View)`**
   - Purpose: Execute bulk actions on registrations
   - Returns: JSON response

2. **`BulkActionPreviewView(LoginRequiredMixin, UserPassesTestMixin, View)`**
   - Purpose: Preview bulk action before execution
   - Returns: JSON response

### 2.24 Webhook Views (`apps/tournaments/views/webhook_views.py`)
1. **`WebhookListView(LoginRequiredMixin, UserPassesTestMixin, ListView)`**
   - Purpose: List webhooks configured for tournament
   - Template: `tournaments/webhooks/list.html`

2. **`WebhookDeliveryHistoryView(LoginRequiredMixin, UserPassesTestMixin, ListView)`**
   - Purpose: View webhook delivery history
   - Template: `tournaments/webhooks/delivery_history.html`

3. **`TestWebhookView(LoginRequiredMixin, UserPassesTestMixin, View)`**
   - Purpose: Test webhook endpoint
   - Returns: JSON response

### 2.25 Registration UX API Views (`apps/tournaments/views/registration_ux_api.py`)
1. **`SaveDraftAPIView(LoginRequiredMixin, View)`**
   - Purpose: Save registration draft (autosave)
   - Returns: JSON response

2. **`GetDraftAPIView(LoginRequiredMixin, View)`**
   - Purpose: Retrieve saved registration draft
   - Returns: JSON response

3. **`GetProgressAPIView(LoginRequiredMixin, View)`**
   - Purpose: Calculate registration progress percentage
   - Returns: JSON response

4. **`ValidateFieldAPIView(View)`**
   - Purpose: Validate single form field (real-time validation)
   - Returns: JSON response

### 2.26 Registration Dashboard Views (`apps/tournaments/views/registration_dashboard.py`)
1. **`RegistrationManagementDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView)`**
   - Purpose: Organizer dashboard for managing registration responses
   - Template: `tournaments/registration_dashboard/dashboard.html`
   - Context: Registration responses with filtering

2. **`ResponseDetailAPIView(LoginRequiredMixin, UserPassesTestMixin, View)`**
   - Purpose: Get detailed registration response data
   - Returns: JSON response

3. **`QuickActionAPIView(LoginRequiredMixin, UserPassesTestMixin, View)`**
   - Purpose: Execute quick actions on registration (approve, reject, flag)
   - Returns: JSON response

### 2.27 Dispute Resolution Views (`apps/tournaments/views/dispute_resolution.py`)
**Function Views:**
- `resolve_dispute(request, slug, dispute_id)` - Resolve dispute with verdict
- `update_dispute_status(request, slug, dispute_id)` - Update dispute status

### 2.28 Template Marketplace Views (`apps/tournaments/views/template_marketplace.py`) - DEPRECATED
**Note:** Template marketplace removed - now admin-only feature

1. **`TemplateMarketplaceView(ListView)`** - Removed from URLs
2. **`TemplateDetailView(DetailView)`** - Removed from URLs
3. **`CloneTemplateView(LoginRequiredMixin, DetailView)`** - Removed from URLs
4. **`RateTemplateView(LoginRequiredMixin, CreateView)`** - Removed from URLs
5. **`MarkRatingHelpfulView(LoginRequiredMixin, DetailView)`** - Removed from URLs

---

## 3. REST API Endpoints

### 3.1 API URL Configuration
**File:** `apps/tournaments/api/urls.py`

### 3.2 DRF ViewSets (Router-based)
1. **`TournamentViewSet(viewsets.ModelViewSet)`**
   - File: `apps/tournaments/api/tournament_views.py`
   - Endpoints: `/api/tournaments/`
   - Actions: list, retrieve, create, update, partial_update, destroy
   - Custom Actions:
     - `@action POST /api/tournaments/{id}/publish/` - Publish tournament
     - `@action POST /api/tournaments/{id}/cancel/` - Cancel tournament

2. **`TournamentDiscoveryViewSet(viewsets.ViewSet)`**
   - File: `apps/tournaments/api/discovery_views.py`
   - Endpoints: `/api/tournaments/tournament-discovery/`
   - Custom Actions:
     - `@action GET /api/tournaments/tournament-discovery/upcoming/` - Upcoming tournaments
     - `@action GET /api/tournaments/tournament-discovery/live/` - Live tournaments
     - `@action GET /api/tournaments/tournament-discovery/featured/` - Featured tournaments
     - `@action GET /api/tournaments/tournament-discovery/by-game/{game_id}/` - Filter by game

3. **`GameConfigViewSet(viewsets.GenericViewSet)`**
   - File: `apps/tournaments/api/game_config_views.py`
   - Endpoints: `/api/tournaments/games/`
   - Custom Actions:
     - `@action GET /api/tournaments/games/{id}/config/` - Get game config
     - `@action PATCH /api/tournaments/games/{id}/config/` - Update game config (admin only)
     - `@action GET /api/tournaments/games/{id}/config-schema/` - Get config schema

4. **`TournamentTemplateViewSet(viewsets.GenericViewSet)`**
   - File: `apps/tournaments/api/template_views.py`
   - Endpoints: `/api/tournaments/tournament-templates/`
   - Custom Actions:
     - `@action POST /api/tournaments/tournament-templates/{id}/apply/` - Apply template to tournament

5. **`RegistrationViewSet(viewsets.GenericViewSet)`**
   - File: `apps/tournaments/api/registrations.py`
   - Endpoints: `/api/tournaments/registrations/`
   - Custom Actions:
     - `@action POST /api/tournaments/registrations/solo/` - Solo registration
     - `@action POST /api/tournaments/registrations/team/` - Team registration

6. **`PaymentVerificationViewSet(viewsets.GenericViewSet)`**
   - File: `apps/tournaments/api/payments.py`
   - Endpoints: `/api/tournaments/payments/`
   - Actions: Payment verification, refund processing

7. **`MatchViewSet(viewsets.ReadOnlyModelViewSet)`**
   - File: `apps/tournaments/api/matches.py`
   - Endpoints: `/api/tournaments/matches/`
   - Actions: list, retrieve (read-only)

8. **`MatchViewSet(viewsets.ModelViewSet)`** (Alternative in match_views.py)
   - File: `apps/tournaments/api/match_views.py`
   - Custom Actions:
     - `@action POST /api/tournaments/matches/{id}/start/` - Start match
     - `@action POST /api/tournaments/matches/bulk-schedule/` - Bulk schedule matches
     - `@action POST /api/tournaments/matches/{id}/assign-coordinator/` - Assign coordinator
     - `@action PATCH /api/tournaments/matches/{id}/lobby/` - Update lobby info

9. **`BracketViewSet(viewsets.ReadOnlyModelViewSet)`**
   - File: `apps/tournaments/api/bracket_views.py`
   - Endpoints: `/api/tournaments/brackets/`
   - Custom Actions:
     - `@action POST /api/tournaments/brackets/{tournament_id}/generate/` - Generate bracket
     - `@action POST /api/tournaments/brackets/{id}/finalize/` - Finalize bracket (admin)
     - `@action GET /api/tournaments/brackets/{id}/visualization/` - Get bracket visualization data

10. **`ResultViewSet(viewsets.GenericViewSet)`**
    - File: `apps/tournaments/api/result_views.py`
    - Endpoints: `/api/tournaments/results/`
    - Custom Actions:
      - `@action POST /api/tournaments/results/submit/` - Submit match result
      - `@action POST /api/tournaments/results/confirm/` - Confirm opponent result
      - `@action POST /api/tournaments/results/dispute/` - Dispute result

11. **`LeaderboardViewSet(viewsets.GenericViewSet)`**
    - File: `apps/tournaments/api/leaderboard_views.py`
    - Endpoints: `/api/tournaments/leaderboards/`
    - Custom Actions:
      - `@action GET /api/tournaments/leaderboards/tournament/{id}/` - Tournament leaderboard
      - `@action GET /api/tournaments/leaderboards/global/` - Global leaderboard
      - `@action GET /api/tournaments/leaderboards/player/{id}/` - Player leaderboard

12. **`CheckinViewSet(viewsets.GenericViewSet)`**
    - File: `apps/tournaments/api/checkin/views.py`
    - Endpoints: `/api/tournaments/checkin/`
    - Custom Actions:
      - `@action POST /api/tournaments/checkin/{registration_id}/check-in/` - Check in
      - `@action POST /api/tournaments/checkin/{registration_id}/undo/` - Undo check-in
      - `@action POST /api/tournaments/checkin/bulk/` - Bulk check-in (organizer)
      - `@action GET /api/tournaments/checkin/{registration_id}/status/` - Get check-in status

13. **`CustomFieldViewSet(viewsets.ModelViewSet)`** (Not currently routed)
    - File: `apps/tournaments/api/custom_field_views.py`
    - Note: Requires drf-nested-routers package

### 3.3 Function-Based API Views (`@api_view`)
1. **Leaderboard APIs** (`apps/tournaments/api/leaderboard_views.py`)
   - `@api_view GET /api/tournaments/leaderboards/tournament/{tournament_id}/` - `tournament_leaderboard()`
   - `@api_view GET /api/tournaments/leaderboards/player/{player_id}/history/` - `player_leaderboard_history()`
   - `@api_view GET /api/tournaments/leaderboards/{scope}/` - `scoped_leaderboard()`

2. **Payout APIs** (`apps/tournaments/api/payout_views.py`)
   - `@api_view POST /api/tournaments/{tournament_id}/payouts/` - `process_payouts()`
   - `@api_view POST /api/tournaments/{tournament_id}/refunds/` - `process_refunds()`
   - `@api_view GET /api/tournaments/{tournament_id}/payouts/verify/` - `verify_reconciliation()`

3. **Certificate APIs** (`apps/tournaments/api/certificate_views.py`)
   - `@api_view GET /api/tournaments/certificates/{pk}/` - `download_certificate()`
   - `@api_view GET /api/tournaments/certificates/verify/{code}/` - `verify_certificate()`

4. **Analytics APIs** (`apps/tournaments/api/analytics_views.py`)
   - `@api_view GET /api/tournaments/analytics/organizer/{tournament_id}/` - `organizer_analytics()`
   - `@api_view GET /api/tournaments/analytics/participant/{user_id}/` - `participant_analytics()`
   - `@api_view GET /api/tournaments/analytics/export/{tournament_id}/` - `export_tournament_csv()`

5. **Organizer APIs** (`apps/tournaments/api/organizer_views.py`)
   - `@api_view GET /api/tournaments/organizer/dashboard/stats/` - `organizer_stats()`
   - `@api_view GET /api/tournaments/organizer/tournaments/{tournament_id}/health/` - `tournament_health()`
   - `@api_view GET /api/tournaments/organizer/tournaments/{tournament_id}/participants/` - `participant_breakdown()`

### 3.4 APIView Classes
1. **`OrganizerResultsInboxView(APIView)`**
   - File: `apps/tournaments/api/organizer_results_inbox_views.py`
   - Endpoint: `GET /api/tournaments/v1/organizer/results-inbox/`
   - Purpose: Get pending match results queue (Epic 7.1)

2. **`OrganizerResultsInboxBulkActionView(APIView)`**
   - File: `apps/tournaments/api/organizer_results_inbox_views.py`
   - Endpoint: `POST /api/tournaments/v1/organizer/results-inbox/bulk-action/`
   - Purpose: Bulk approve/reject match results (Epic 7.1)

### 3.5 Nested Check-In API
**Namespace:** `checkin`  
**File:** `apps/tournaments/api/checkin/urls.py`  
**Base URL:** `/api/tournaments/checkin/`

---

## 4. Template Structure

### 4.1 Template Directories
**Base Path:** `templates/tournaments/`

### 4.2 Template Inventory

#### Root Templates
- `list.html` - Legacy tournament list
- `list_redesigned.html` - Redesigned tournament list (current)
- `registration_ineligible.html` - Ineligibility error page

#### Detail Pages (`detailPages/`)
- `detail.html` - Tournament detail page
- `partials/` - Detail page partials/components

#### Public Pages (`public/`)
- `browse/` - Tournament browsing templates
- `detail/` - Detail page variations
- `leaderboard/` - Leaderboard templates
  - `index.html` - Leaderboard page
- `live/` - Live tournament experience
  - `bracket.html` - Bracket visualization (FE-T-008)
  - `match_detail.html` - Match detail page (FE-T-009)
  - `results.html` - Results page (FE-T-018)
  - `submit_result_form.html` - Result submission form (FE-T-014)
- `player/` - Player dashboard
  - `my_tournaments.html` - My tournaments page (FE-T-005)
  - `my_matches.html` - My matches page
- `registration/` - Registration templates
  - `wizard.html` - Legacy registration wizard
  - `success.html` - Registration success page
  - `payment_upload.html` - Payment proof upload
  - `payment_retry.html` - Payment retry after rejection

#### Registration (`registration/`)
- `status.html` - Registration status page
- `resubmit_payment.html` - Payment resubmission page
- `withdraw.html` - Registration withdrawal page
- `errors/` - Registration error pages

#### Organizer Console (`organizer/`)
- `dashboard.html` - Organizer dashboard
- `tournament_detail.html` - Organizer tournament detail
- `pending_results.html` - Pending results review (FE-T-015)
- `disputes.html` - Dispute management (FE-T-025)
- `health_metrics.html` - Health metrics dashboard (FE-T-026)
- `hub_overview.html` - Hub overview tab
- `hub_participants.html` - Hub participants tab (FE-T-022)
- `hub_payments.html` - Hub payments tab (FE-T-023)
- `hub_brackets.html` - Hub brackets tab
- `hub_disputes.html` - Hub disputes tab
- `hub_disputes_enhanced.html` - Enhanced disputes tab
- `hub_announcements.html` - Hub announcements tab
- `hub_settings.html` - Hub settings tab
- `create_tournament.html` - Tournament creation form
- `groups/` - Group stage templates

#### Groups (`groups/`)
- `standings.html` - Group standings view (FE-T-013)

#### Lobby (`lobby/`)
- `hub.html` - Tournament lobby (FE-T-007)
- `_announcements.html` - Announcements partial
- `_roster.html` - Roster partial

#### Spectator (`spectator/`)
- `hub.html` - Public spectator view (FE-T-006)

#### Team Registration (`team_registration/`)
- `base.html` - Registration base template
- Solo Registration:
  - `solo_step1.html` - Solo step 1
  - `solo_step1_enhanced.html` - Enhanced version
  - `solo_step1_new.html` - New version
  - `solo_step2.html` - Solo step 2
  - `solo_step2_new.html` - New version
  - `solo_step3.html` - Solo step 3
  - `solo_step3_new.html` - New version
  - `solo_step3_simple.html` - Simplified version
  - `solo_success.html` - Solo success page
- Team Registration:
  - `team_step1.html` - Team step 1
  - `team_step1_enhanced.html` - Enhanced version
  - `team_step1_new.html` - New version
  - `team_step2.html` - Team step 2
  - `team_step2_new.html` - New version
  - `team_step3.html` - Team step 3
  - `team_step3_enhanced.html` - Enhanced version
  - `team_step3_new.html` - New version
  - `team_success.html` - Team success page
- Error Pages:
  - `already_registered.html` - Already registered error
  - `team_already_registered.html` - Team already registered error
  - `team_eligibility_error.html` - Team eligibility error

#### Form Builder (`form_builder/`)
- `form_step.html` - Dynamic registration form step (FE-T-004)
- `registration_dashboard.html` - Registration dashboard
- `registration_success.html` - Dynamic registration success page
- `fields/` - Custom field templates

#### Registration Dashboard (`registration_dashboard/`)
- `dashboard.html` - Organizer registration dashboard

#### Analytics (`analytics/`)
- `dashboard.html` - Form analytics dashboard

#### Responses (`responses/`)
- `export.html` - Export preview page

#### Marketplace (`marketplace/`) - DEPRECATED
- `browse.html` - Template marketplace (removed from URLs)
- `template_detail.html` - Template detail (removed from URLs)

#### Components (`components/`)
- `autofill_badge.html` - Autofill badge component
- `autofill_progress.html` - Autofill progress indicator
- `ineligibility_card.html` - Ineligibility card component
- `permission_request_modal.html` - Permission request modal

#### Emails (`emails/`)
- `custom_notification.html` - Custom email notification
- `payment_pending.html` - Payment pending email
- `payment_verified.html` - Payment verified email
- `registration_approved.html` - Registration approved email
- `registration_confirmed.html` - Registration confirmed email
- `registration_rejected.html` - Registration rejected email
- `waitlist_promotion.html` - Waitlist promotion email

#### Old Backups
- `old_backup/` - Legacy templates (archived)
- `registration_demo_backup/` - Demo registration templates (archived)

---

## 5. Key Findings & Patterns

### 5.1 View Organization
- **Total View Files:** 30+ view files in `apps/tournaments/views/`
- **View Pattern Mix:**
  - Class-Based Views (CBV): 67 classes (ListView, DetailView, TemplateView, View)
  - Function-Based Views (FBV): 26+ functions (POST actions, organizer operations)
- **Permission Mixins Used:**
  - `LoginRequiredMixin` - Authenticated users only
  - `UserPassesTestMixin` - Custom permission checks
  - `OrganizerRequiredMixin` - Organizer-only views

### 5.2 URL Patterns
- **Total URL Routes:** 78 patterns
- **Dynamic Parameters:**
  - `<slug:slug>` - Tournament identifier
  - `<int:match_id>` - Match identifier
  - `<int:registration_id>` - Registration identifier
  - `<int:payment_id>` - Payment identifier
  - `<int:dispute_id>` - Dispute identifier
  - `<str:tab>` - Tab parameter for multi-tab views

### 5.3 API Structure
- **ViewSets:** 13 DRF ViewSets (router-based)
- **Function-Based APIs:** 14+ `@api_view` decorated functions
- **APIView Classes:** 2 custom APIView classes
- **Nested APIs:** Check-In API uses separate namespace

### 5.4 Template Organization
- **Total Template Directories:** 20+ subdirectories
- **Template Count:** 100+ template files
- **Template Patterns:**
  - Base templates with step variations (step1, step2, step3)
  - Enhanced/new versions for A/B testing
  - Partials for reusable components (_announcements.html, _roster.html)
  - Email templates for notifications

### 5.5 Feature Implementation Status
**Completed Features:**
- ✅ FE-T-001: Tournament List Page
- ✅ FE-T-002: Tournament Detail Page
- ✅ FE-T-003: Registration CTA States
- ✅ FE-T-004: Dynamic Registration System
- ✅ FE-T-005: My Tournaments Dashboard
- ✅ FE-T-006: Public Spectator View
- ✅ FE-T-007: Tournament Lobby/Check-In
- ✅ FE-T-008: Live Bracket View
- ✅ FE-T-009: Match Detail Page
- ✅ FE-T-010: Tournament Leaderboard
- ✅ FE-T-011: Group Configuration
- ✅ FE-T-012: Group Draw
- ✅ FE-T-013: Group Standings
- ✅ FE-T-014: Match Result Submission
- ✅ FE-T-015: Organizer Results Inbox
- ✅ FE-T-016: Dispute Submission
- ✅ FE-T-017: Dispute Resolution
- ✅ FE-T-018: Tournament Results Page
- ✅ FE-T-022: Participant Management
- ✅ FE-T-023: Payment Management
- ✅ FE-T-024: Match Management
- ✅ FE-T-025: Dispute Management Dashboard
- ✅ FE-T-026: Tournament Health Metrics

### 5.6 Removed/Deprecated Features
- ❌ Template Marketplace (removed from URLs - now admin-only)
- ⚠️ Legacy Registration Views (kept for backward compatibility)

### 5.7 Multiple Implementations Found
1. **Registration Wizards:**
   - `registration.py` - Legacy wizard
   - `registration_wizard.py` - Production wizard (Beautiful Demo Templates)
   - `tournament_team_registration.py` - Team registration
   - `dynamic_registration.py` - Form Builder registration

2. **Lobby Views:**
   - `checkin.py` - Original lobby view
   - `lobby.py` - Enhanced lobby view (v2)

3. **Match ViewSets:**
   - `matches.py` - Read-only match viewset
   - `match_views.py` - Full CRUD match viewset

---

## 6. Summary Statistics

| Category | Count |
|----------|-------|
| **URLs** | 78 routes |
| **CBVs** | 67 classes |
| **FBVs** | 26+ functions |
| **DRF ViewSets** | 13 viewsets |
| **API Functions** | 14+ @api_view |
| **APIView Classes** | 2 classes |
| **Template Directories** | 20+ folders |
| **Template Files** | 100+ templates |
| **View Files** | 30+ Python files |

---

## 7. Integration Points

### 7.1 External Dependencies
- Django Admin: `/admin/tournaments/` - Admin panel for tournament management
- REST API Root: `/api/tournaments/` - RESTful API endpoints
- WebSocket: Real-time updates for check-in, match results, leaderboard
- Channels Layer: Used in `CheckinViewSet` for broadcasting events

### 7.2 Cross-App References
- `apps.teams` - Team management integration (team_id IntegerField references)
- `apps.accounts` - User authentication and profiles
- `apps.games` - Game configuration (GameConfigViewSet)
- `apps.players` - Player profile data
- `apps.leaderboards` - Leaderboard integration

### 7.3 File Upload Endpoints
- Payment proof upload: `PaymentProofUploadView`
- Match result screenshot upload: `SubmitResultView`
- Dispute evidence upload: Via dispute models (not exposed as separate view)

---

**End of Views & Templates Audit**
