# apps/teams/urls.py
from django.urls import path, include
from django.shortcuts import render
from rest_framework.routers import DefaultRouter
from . import api_views  # Import API views for REST endpoints

# Phase 4: Member Management
from .views.member_management import (
    get_team_members,
    update_member_role,
    remove_member,
    transfer_captaincy,
    bulk_remove_members,
)

# Phase 3: Role Management (New Professional Hierarchy)
from .views.role_management import (
    transfer_ownership_view,
    assign_manager_view,
    remove_manager_view,
    assign_coach_view,
    assign_captain_title_view,
    remove_captain_title_view,
    change_member_organizational_role_view,
)

# Role-based dashboard views
from .views.role_dashboards import (
    manager_tools_view,
    coach_tools_view,
    team_safety_view,
)

# OTP-based leave team flow
from .views.otp_leave import (
    request_leave_otp,
    confirm_leave_with_otp,
)

# Player-specific views (new three-entry hub system)
from .views.player_views import (
    player_dashboard_view,
    player_settings_view,
    team_room_view,
)

# Rankings views (archived - used only when COMPETITION_APP_ENABLED=0)
from .views._legacy.rankings import (
    game_leaderboard_view,
    global_leaderboard_view,
)

# Dashboard API
from .views.dashboard_api import (
    get_pending_items,
    get_recent_activity,
    approve_join_request,
    reject_join_request,
    resend_team_invite,
    cancel_team_invite,
)

# Statistics API (Phase 1)
from .views.statistics_api import (
    get_team_statistics,
    get_match_history,
    get_win_rate_chart,
    get_player_statistics,
    get_ranking_history,
    get_performance_metrics,
)

from .views.public import (
    team_hub,
    team_list,
    team_detail,
    invite_member_view,
    my_invites,
    accept_invite_view,
    decline_invite_view,
    leave_team_view,
    manage_team_view,
    join_team_view,
    team_settings_view,
    delete_team_view,
    cancel_invite_view,
    about_teams,  # New about teams info page
    # New professional management views
    update_team_info_view,
    update_privacy_view,
    change_member_role_view,
    change_player_role_view,
    # New Quick Actions views
    export_team_data_view,
    tournament_history_view,
    # Game ID Collection views
    collect_game_id_view,
    create_team_resume_view,
)
# Import new dashboard and profile views
from .views.dashboard import (
    team_dashboard_view,
    team_profile_view,
    follow_team,
    unfollow_team,
    update_roster_order,
    resend_invite,
)
# Import team creation views and AJAX endpoints
from .views.create import (
    team_create_view,
    validate_team_name,
    validate_team_tag,
    check_existing_team,
    get_game_regions_api,
    save_draft_api,
    load_draft_api,
    clear_draft_api,
)
# Import team setup view (post-creation)
from .views.setup import team_setup_view, update_team_settings
# Import tournament integration views (Task 5)
from .views.tournaments import (
    tournament_registration_view,
    tournament_registration_status_view,
    cancel_tournament_registration,
    team_ranking_view,
    team_ranking_detail_view,
    team_tournaments_view,
    trigger_ranking_recalculation,
)
# Import analytics views (Task 6)
from .views.analytics import (
    TeamAnalyticsDashboardView,
    TeamPerformanceAPIView,
    ExportTeamStatsView,
    PlayerAnalyticsView,
    LeaderboardView,
    ExportLeaderboardView,
    TeamComparisonView,
    MatchDetailView,
    AnalyticsAPIEndpoint,
)
# Import chat and discussion views (Task 7)
from .views.chat import (
    TeamChatView,
    ChatAPIView,
    ChatTypingStatusView,
    ChatUnreadCountView,
)
from .views.discussions import (
    DiscussionBoardView,
    DiscussionPostDetailView,
    DiscussionPostCreateView,
    DiscussionPostEditView,
    DiscussionAPIView,
    MarkdownPreviewView,
)
# Import sponsorship views (Task 8)
from .views.sponsorship import (
    TeamSponsorsView,
    SponsorInquiryView,
    SponsorClickTrackingView,
    TeamMerchandiseView,
    MerchItemDetailView,
    MerchClickTrackingView,
    FeaturedTeamsView,
    TeamHubFeaturedView,
    PromotionClickTrackingView,
    SponsorshipAPIView,
    SponsorDashboardView,
)

# Import permission management views
from .views.permissions import (
    TeamPermissionManagementView,
    TeamPermissionBulkUpdateView,
    TeamMemberListView,
)

from .views.ajax import (
    my_teams_data,
    my_invites_data,
    update_team_info,
    update_team_privacy,
    kick_member,
    transfer_captaincy,
    leave_team,
)

# Import Team Management Console
from .views.manage_console import team_management_console

# Import API views for new REST endpoints (optional - requires DRF)
try:
    from rest_framework.routers import DefaultRouter
    from apps.teams import views as team_views
    # Check if views have the necessary viewsets
    if hasattr(team_views, 'ValorantTeamViewSet'):
        HAS_DRF = True
        # Create router for API viewsets
        router = DefaultRouter()
        router.register(r'valorant', team_views.ValorantTeamViewSet, basename='valorant-team')
        router.register(r'cs2', team_views.CS2TeamViewSet, basename='cs2-team')
        router.register(r'dota2', team_views.Dota2TeamViewSet, basename='dota2-team')
        router.register(r'mlbb', team_views.MLBBTeamViewSet, basename='mlbb-team')
        router.register(r'pubg', team_views.PUBGTeamViewSet, basename='pubg-team')
        router.register(r'freefire', team_views.FreeFireTeamViewSet, basename='freefire-team')
        router.register(r'efootball', team_views.EFootballTeamViewSet, basename='efootball-team')
        router.register(r'fc26', team_views.FC26TeamViewSet, basename='fc26-team')
        router.register(r'codm', team_views.CODMTeamViewSet, basename='codm-team')
    else:
        HAS_DRF = False
        router = None
except (ImportError, AttributeError):
    HAS_DRF = False
    router = None

# Always set HAS_DRF to True since we have api_views module
HAS_DRF = True

app_name = "teams"

# Phase 5 Migration: Redirect handler for legacy teams when ORG_APP_ENABLED
from django.conf import settings
from django.shortcuts import redirect

def _teams_index_redirect(request):
    """
    Phase 6: Strict redirect/lockdown for /teams/ index.
    - ORG_APP_ENABLED=1 → redirect to /orgs/
    - ORG_APP_ENABLED=0 + LEGACY_TEAMS_ENABLED=1 → show legacy teams list
    - LEGACY_TEAMS_ENABLED=0 → 404 (legacy locked down)
    """
    if getattr(settings, 'ORG_APP_ENABLED', False):
        return redirect('organizations:org_directory')
    
    # Check if legacy teams are allowed as fallback
    if not getattr(settings, 'LEGACY_TEAMS_ENABLED', False):
        from django.http import Http404
        raise Http404("Legacy Teams has been disabled. Use Organizations app.")
    
    # Fallback to legacy teams list view
    return team_list(request)

def _teams_rankings_redirect(request, game_slug=None):
    """
    Phase 6: Strict redirect/lockdown for /teams/rankings/.
    - COMPETITION_APP_ENABLED=1 → redirect to /competition/rankings/
    - COMPETITION_APP_ENABLED=0 + LEGACY_TEAMS_ENABLED=1 → show legacy leaderboards
    - Both disabled → 404 (legacy rankings locked down)
    """
    if getattr(settings, 'COMPETITION_APP_ENABLED', False):
        if game_slug:
            return redirect('competition:rankings_game', game_id=game_slug)
        return redirect('competition:rankings_global')
    
    # Check if legacy rankings are allowed as fallback
    if not getattr(settings, 'LEGACY_TEAMS_ENABLED', False):
        from django.http import Http404
        raise Http404("Legacy Leaderboards disabled. Use Competition app.")
    
    # Fallback to legacy rankings view
    if game_slug:
        return game_leaderboard_view(request, game_slug)
    return global_leaderboard_view(request)

def _teams_hub_redirect(request):
    """
    Phase 6: Canonical Teams Hub routing.
    - ORG_APP_ENABLED=1 → redirect to Organizations vnext_hub
    - ORG_APP_ENABLED=0 + LEGACY_TEAMS_ENABLED=1 → show legacy teams hub
    - LEGACY_TEAMS_ENABLED=0 → 404
    """
    if getattr(settings, 'ORG_APP_ENABLED', False):
        return redirect('organizations:vnext_hub')
    
    # Check if legacy teams hub is allowed as fallback
    if not getattr(settings, 'LEGACY_TEAMS_ENABLED', False):
        from django.http import Http404
        raise Http404("Legacy Teams has been disabled. Use Organizations app.")
    
    # Fallback to legacy teams hub
    return team_hub(request)

urlpatterns = [
    # Phase 6: Canonical Teams Hub - Routes to Organizations vnext_hub when ORG_APP_ENABLED=1
    path("vnext/", _teams_hub_redirect, name="teams_hub"),
    
    # Phase 5: Legacy Teams Migration - Conditional Redirect
    # When ORG_APP_ENABLED=True, /teams/ redirects to /orgs/
    # This makes Organizations the canonical owner, legacy teams is fallback only
    path("", _teams_index_redirect, name="index"),
    path("", _teams_index_redirect, name="hub"),
    
    # Team Management Console (Admin/Staff only)
    path("management/", team_management_console, name="management_console"),
    
    # Legacy teams list views (only used when ORG_APP_ENABLED=False)
    path("list/", team_list, name="list"),
    # Backwards-compatibility alias: 'teams:browse' used across multiple templates
    path('browse/', team_list, name='browse'),
    
    # Phase 5: Legacy Rankings Migration - Conditional Redirect
    # When COMPETITION_APP_ENABLED=True, /teams/rankings/ redirects to /competition/rankings/
    # This makes Competition the canonical owner of rankings/leaderboards
    path("rankings/", _teams_rankings_redirect, name="rankings"),
    path("rankings/", _teams_rankings_redirect, name="global_rankings"),
    path("rankings/<slug:game_slug>/", _teams_rankings_redirect, name="game_rankings"),
    
    # About Teams Information Page
    path("about/", about_teams, name="about"),
    
    # Team Creation - Redirects to Organizations canonical route when ORG_APP_ENABLED
    # Legacy /teams/create/ is deprecated - use /teams/create/ (handled by Organizations app)
    # This redirect ensures any hardcoded /teams/create/ links route to canonical UI
    path("create/", lambda request: redirect('organizations:team_create') if getattr(settings, 'ORG_APP_ENABLED', False) else team_create_view(request), name="create"),
    path("setup/<slug:slug>/", team_setup_view, name="setup"),  # Post-creation setup
    path("<slug:slug>/update-settings/", update_team_settings, name="update_settings"),  # Settings update
    path("create/resume/", create_team_resume_view, name="create_team_resume"),
    path("collect-game-id/<str:game_code>/", collect_game_id_view, name="collect_game_id"),

    # IMPORTANT: Specific AJAX endpoints MUST come before slug patterns
    # AJAX endpoints (modularized)
    path("my-teams-data/", my_teams_data, name="my_teams_ajax"),
    path("my-invites-data/", my_invites_data, name="my_invites_ajax"),
    
    # Invites
    path("invites/", my_invites, name="my_invites"),
    path("invitations/", my_invites, name="invitations"),  # Alias
    path("invites/<str:token>/accept/", accept_invite_view, name="accept_invite"),
    path("invites/<str:token>/decline/", decline_invite_view, name="decline_invite"),
    
    # AJAX endpoints for team creation
    path("api/validate-name/", validate_team_name, name="validate_team_name"),
    path("api/validate-tag/", validate_team_tag, name="validate_team_tag"),
    path("api/game-regions/<str:game_code>/", get_game_regions_api, name="game_regions_api"),
    path("api/check-existing-team/", check_existing_team, name="check_existing_team"),
    path("api/save-draft/", save_draft_api, name="save_draft"),
    path("api/load-draft/", load_draft_api, name="load_draft"),
    path("api/clear-draft/", clear_draft_api, name="clear_draft"),

    # Detail + captain actions (slug-based) - MUST come after specific paths
    path("<slug:slug>/", team_profile_view, name="detail"),  # New public profile
    path("<slug:slug>/dashboard/", team_dashboard_view, name="dashboard"),  # New dashboard
    path("<slug:slug>/manage/", manage_team_view, name="manage"),
    # Aliases commonly referenced by templates
    path("<slug:slug>/manage/", manage_team_view, name="edit"),
    path("<slug:slug>/invite/", invite_member_view, name="invite_member"),
    path("<slug:slug>/invite/", invite_member_view, name="invite"),
    path("<slug:slug>/leave/", leave_team_view, name="leave"),
    path("<slug:slug>/join/", join_team_view, name="join"),
    path("<slug:slug>/kick/<int:profile_id>/", kick_member, name="kick"),
    path("<slug:slug>/transfer/<int:profile_id>/", transfer_captaincy, name="transfer_captaincy"),
    path("<slug:slug>/settings/", team_settings_view, name="settings"),
    path("<slug:slug>/delete/", delete_team_view, name="delete"),
    path("<slug:slug>/cancel-invite/", cancel_invite_view, name="cancel_invite"),
    
    # New dashboard actions
    path("<slug:slug>/follow/", follow_team, name="follow"),
    path("<slug:slug>/unfollow/", unfollow_team, name="unfollow"),
    path("<slug:slug>/update-roster-order/", update_roster_order, name="update_roster_order"),
    path("<slug:slug>/resend-invite/<int:invite_id>/", resend_invite, name="resend_invite"),
    
    # Dashboard API endpoints
    path("api/<slug:slug>/pending-items/", get_pending_items, name="api_pending_items"),
    path("api/<slug:slug>/recent-activity/", get_recent_activity, name="api_recent_activity"),
    path("api/join-requests/<int:request_id>/approve/", approve_join_request, name="api_approve_join_request"),
    path("api/join-requests/<int:request_id>/reject/", reject_join_request, name="api_reject_join_request"),
    path("api/invites/<int:invite_id>/resend/", resend_team_invite, name="api_resend_invite"),
    path("api/invites/<int:invite_id>/cancel/", cancel_team_invite, name="api_cancel_invite"),
    
    # New professional management endpoints (kept from public.py)
    path("<slug:slug>/update-info/", update_team_info_view, name="update_team_info"),
    path("<slug:slug>/update-privacy/", update_privacy_view, name="update_privacy"),
    path("<slug:slug>/change-role/", change_member_role_view, name="change_role"),
    path("<slug:slug>/change-player-role/", change_player_role_view, name="change_player_role"),
    
    # Phase 3: Professional Role Management Endpoints
    path("<slug:slug>/transfer-ownership/", transfer_ownership_view, name="transfer_ownership"),
    path("<slug:slug>/assign-manager/", assign_manager_view, name="assign_manager"),
    path("<slug:slug>/remove-manager/", remove_manager_view, name="remove_manager"),
    path("<slug:slug>/assign-coach/", assign_coach_view, name="assign_coach"),
    path("<slug:slug>/assign-captain-title/", assign_captain_title_view, name="assign_captain_title"),
    path("<slug:slug>/remove-captain-title/", remove_captain_title_view, name="remove_captain_title"),
    path("<slug:slug>/change-organizational-role/", change_member_organizational_role_view, name="change_organizational_role"),
    
    # New Quick Actions endpoints
    path("<slug:slug>/export-data/", export_team_data_view, name="export_team_data"),
    path("<slug:slug>/tournament-history/", tournament_history_view, name="tournament_history"),
    
    # Role-based dashboard views
    path("<slug:slug>/manager-tools/", manager_tools_view, name="manager_tools"),
    path("<slug:slug>/coach-tools/", coach_tools_view, name="coach_tools"),
    path("<slug:slug>/team-safety/", team_safety_view, name="team_safety"),
    
    # OTP-protected leave team flow
    path("<slug:slug>/leave/request-otp/", request_leave_otp, name="leave_request_otp"),
    path("<slug:slug>/leave/confirm-otp/", confirm_leave_with_otp, name="leave_confirm_otp"),
    
    # Player-specific views (new three-entry hub system)
    path("<slug:slug>/me/dashboard/", player_dashboard_view, name="player_dashboard"),
    path("<slug:slug>/me/settings/", player_settings_view, name="player_settings"),
    path("<slug:slug>/room/", team_room_view, name="team_room"),
    
    # Tournament Integration (Task 5)
    path("<slug:slug>/tournaments/", team_tournaments_view, name="team_tournaments"),
    path("<slug:slug>/tournaments/<slug:tournament_slug>/register/", tournament_registration_view, name="tournament_register"),
    path("<slug:slug>/registration/<int:registration_id>/", tournament_registration_status_view, name="tournament_registration_status"),
    path("<slug:slug>/registration/<int:registration_id>/cancel/", cancel_tournament_registration, name="cancel_tournament_registration"),
    path("<slug:slug>/ranking/", team_ranking_detail_view, name="team_ranking_detail"),
    path("<slug:slug>/ranking/recalculate/", trigger_ranking_recalculation, name="trigger_ranking_recalculation"),
    
    # Analytics (Task 6)
    path("analytics/leaderboard/", LeaderboardView.as_view(), name="analytics_leaderboard"),
    path("analytics/leaderboard/export/", ExportLeaderboardView.as_view(), name="export_leaderboard"),
    path("analytics/compare/", TeamComparisonView.as_view(), name="team_comparison"),
    path("analytics/player/<int:player_id>/", PlayerAnalyticsView.as_view(), name="player_analytics"),
    path("analytics/match/<int:match_id>/", MatchDetailView.as_view(), name="match_detail"),
    path("analytics/api/", AnalyticsAPIEndpoint.as_view(), name="analytics_api"),
    path("<int:team_id>/analytics/", TeamAnalyticsDashboardView.as_view(), name="team_analytics"),
    path("<int:team_id>/analytics/api/", TeamPerformanceAPIView.as_view(), name="team_performance_api"),
    path("<int:team_id>/analytics/export/", ExportTeamStatsView.as_view(), name="export_team_stats"),
    
    # Chat & Discussions (Task 7)
    path("<slug:team_slug>/chat/", TeamChatView.as_view(), name="team_chat"),
    path("<slug:team_slug>/chat/api/", ChatAPIView.as_view(), name="chat_api"),
    path("<slug:team_slug>/chat/typing/", ChatTypingStatusView.as_view(), name="chat_typing_status"),
    path("<slug:team_slug>/chat/unread/", ChatUnreadCountView.as_view(), name="chat_unread_count"),
    path("<slug:team_slug>/discussions/", DiscussionBoardView.as_view(), name="discussion_board"),
    path("<slug:team_slug>/discussions/create/", DiscussionPostCreateView.as_view(), name="discussion_post_create"),
    path("<slug:team_slug>/discussions/<slug:post_slug>/", DiscussionPostDetailView.as_view(), name="discussion_post_detail"),
    path("<slug:team_slug>/discussions/<slug:post_slug>/edit/", DiscussionPostEditView.as_view(), name="discussion_post_edit"),
    path("<slug:team_slug>/discussions/api/", DiscussionAPIView.as_view(), name="discussion_api"),
    path("markdown-preview/", MarkdownPreviewView.as_view(), name="markdown_preview"),
    
    # Sponsorship & Monetization URLs (Task 8)
    path("<slug:team_slug>/sponsors/", TeamSponsorsView.as_view(), name="team_sponsors"),
    path("<slug:team_slug>/sponsor-inquiry/", SponsorInquiryView.as_view(), name="sponsor_inquiry"),
    path("sponsor/<int:sponsor_id>/click/", SponsorClickTrackingView.as_view(), name="sponsor_click"),
    path("<slug:team_slug>/merchandise/", TeamMerchandiseView.as_view(), name="team_merchandise"),
    path("<slug:team_slug>/merch/<int:item_id>/", MerchItemDetailView.as_view(), name="merch_item_detail"),
    path("merch/<int:item_id>/click/", MerchClickTrackingView.as_view(), name="merch_click"),
    path("<slug:team_slug>/sponsor-dashboard/", SponsorDashboardView.as_view(), name="sponsor_dashboard"),
    path("featured/", FeaturedTeamsView.as_view(), name="featured_teams"),
    path("hub/featured/", TeamHubFeaturedView.as_view(), name="hub_featured"),
    path("promotion/<int:promotion_id>/click/", PromotionClickTrackingView.as_view(), name="promotion_click"),
    path("sponsorship/api/", SponsorshipAPIView.as_view(), name="sponsorship_api"),
    
    # Permission Management
    path("<slug:slug>/members/", TeamMemberListView.as_view(), name="member_list"),
    path("<slug:slug>/permissions/<int:member_id>/", TeamPermissionManagementView.as_view(), name="manage_permissions"),
    path("<slug:slug>/permissions/bulk-update/", TeamPermissionBulkUpdateView.as_view(), name="bulk_update_permissions"),
    
    # Social features namespace
    path("", include("apps.teams.urls_social", namespace="teams_social")),
]

# Add API endpoints if Django REST Framework is available
if HAS_DRF:
    # Import new API views
    from .api_views import (
        # Sponsors API
        get_sponsors, add_sponsor, update_sponsor, delete_sponsor,
        # Discussions API
        get_discussions, create_discussion, toggle_discussion_vote, delete_discussion,
        # Chat API
        get_chat_messages, send_chat_message, edit_chat_message, delete_chat_message,
        add_message_reaction, remove_message_reaction,
    )
    
    api_patterns = [
        # Game configuration endpoints - COMMENTED OUT (functions don't exist yet)
        # path('api/games/', api_views.game_configs_list, name='game-configs-list'),
        # path('api/games/<str:game_code>/', api_views.game_config_detail, name='game-config-detail'),
        # path('api/games/<str:game_code>/roles/', api_views.game_roles_list, name='game-roles-list'),
        
        # Team creation - COMMENTED OUT (function doesn't exist yet)
        # path('api/create/', api_views.create_team_with_roster, name='api-create-team'),
        
        # Validation endpoints - COMMENTED OUT (functions don't exist yet)
        # path('api/validate/name/', api_views.validate_team_name, name='validate-team-name'),
        # path('api/validate/tag/', api_views.validate_team_tag, name='validate-team-tag'),
        # path('api/validate/ign/', api_views.validate_ign_unique, name='validate-ign'),
        # path('api/validate/roster/', api_views.validate_roster_composition, name='validate-roster'),
        
        # Phase 3C: Sponsors API
        path('api/<slug:team_slug>/sponsors/', get_sponsors, name='api-get-sponsors'),
        path('api/<slug:team_slug>/sponsors/add/', add_sponsor, name='api-add-sponsor'),
        path('api/<slug:team_slug>/sponsors/<int:sponsor_id>/', update_sponsor, name='api-update-sponsor'),
        path('api/<slug:team_slug>/sponsors/<int:sponsor_id>/delete/', delete_sponsor, name='api-delete-sponsor'),
        
        # Phase 3A: Discussions API
        path('api/<slug:team_slug>/discussions/', get_discussions, name='api-get-discussions'),
        path('api/<slug:team_slug>/discussions/create/', create_discussion, name='api-create-discussion'),
        path('api/<slug:team_slug>/discussions/<int:discussion_id>/vote/', toggle_discussion_vote, name='api-toggle-vote'),
        path('api/<slug:team_slug>/discussions/<int:discussion_id>/delete/', delete_discussion, name='api-delete-discussion'),
        
        # Phase 3B: Chat API
        path('api/<slug:team_slug>/chat/messages/', get_chat_messages, name='api-get-chat-messages'),
        path('api/<slug:team_slug>/chat/send/', send_chat_message, name='api-send-message'),
        path('api/<slug:team_slug>/chat/<int:message_id>/edit/', edit_chat_message, name='api-edit-message'),
        path('api/<slug:team_slug>/chat/<int:message_id>/delete/', delete_chat_message, name='api-delete-message'),
        path('api/<slug:team_slug>/chat/<int:message_id>/react/', add_message_reaction, name='api-add-reaction'),
        path('api/<slug:team_slug>/chat/<int:message_id>/unreact/', remove_message_reaction, name='api-remove-reaction'),
        
        # Roster API
        path('api/<slug:team_slug>/roster/', api_views.get_roster, name='api-get-roster'),
        path('api/<slug:team_slug>/roster-with-game-ids/', api_views.get_roster_with_game_ids, name='api-get-roster-with-game-ids'),
        
        # Tournaments API
        path('api/<slug:team_slug>/tournaments/', api_views.get_tournaments, name='api-get-tournaments'),
        
        # Posts API
        path('api/<slug:team_slug>/posts/', api_views.get_posts, name='api-get-posts'),
        path('api/<slug:team_slug>/posts/create/', api_views.create_post, name='api-create-post'),
        
        # Member Management API (Phase 4)
        path('api/<slug:slug>/members/', get_team_members, name='api-get-members'),
        path('api/<slug:slug>/members/<int:membership_id>/update-role/', update_member_role, name='api-update-member-role'),
        path('api/<slug:slug>/members/<int:membership_id>/remove/', remove_member, name='api-remove-member'),
        path('api/<slug:slug>/members/transfer-captain/', transfer_captaincy, name='api-transfer-captain'),
        path('api/<slug:slug>/members/bulk-remove/', bulk_remove_members, name='api-bulk-remove-members'),
        
        # Statistics API (Phase 1 - Critical)
        path('api/<slug:slug>/statistics/', get_team_statistics, name='api-get-statistics'),
        path('api/<slug:slug>/match-history/', get_match_history, name='api-match-history'),
        path('api/<slug:slug>/charts/win-rate/', get_win_rate_chart, name='api-win-rate-chart'),
        path('api/<slug:slug>/player-stats/', get_player_statistics, name='api-player-stats'),
        path('api/<slug:slug>/ranking-history/', get_ranking_history, name='api-ranking-history'),
        path('api/<slug:slug>/performance/', get_performance_metrics, name='api-performance-metrics'),
    ]
    
    # Add router URLs only if router exists
    if router:
        api_patterns.append(path('api/', include(router.urls)))
    
    urlpatterns += api_patterns
