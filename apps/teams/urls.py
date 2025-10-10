# apps/teams/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
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
    kick_member_view,
    transfer_captaincy_view,
    team_settings_view,
    delete_team_view,
    cancel_invite_view,
    # New professional management views
    update_team_info_view,
    update_privacy_view,
    # New Quick Actions views
    export_team_data_view,
    tournament_history_view,
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
    get_game_config_api,
    validate_user_identifier,
)
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
from .views.ajax import (
    my_teams_data,
    update_team_info,
    update_team_privacy,
    kick_member,
    transfer_captaincy,
    leave_team,
)

# Import API views for new REST endpoints (optional - requires DRF)
try:
    from rest_framework.routers import DefaultRouter
    from apps.teams import views as api_views
    # Check if views have the necessary viewsets
    if hasattr(api_views, 'ValorantTeamViewSet'):
        HAS_DRF = True
        # Create router for API viewsets
        router = DefaultRouter()
        router.register(r'valorant', api_views.ValorantTeamViewSet, basename='valorant-team')
        router.register(r'cs2', api_views.CS2TeamViewSet, basename='cs2-team')
        router.register(r'dota2', api_views.Dota2TeamViewSet, basename='dota2-team')
        router.register(r'mlbb', api_views.MLBBTeamViewSet, basename='mlbb-team')
        router.register(r'pubg', api_views.PUBGTeamViewSet, basename='pubg-team')
        router.register(r'freefire', api_views.FreeFireTeamViewSet, basename='freefire-team')
        router.register(r'efootball', api_views.EFootballTeamViewSet, basename='efootball-team')
        router.register(r'fc26', api_views.FC26TeamViewSet, basename='fc26-team')
        router.register(r'codm', api_views.CODMTeamViewSet, basename='codm-team')
    else:
        HAS_DRF = False
except (ImportError, AttributeError):
    HAS_DRF = False

app_name = "teams"

urlpatterns = [
    # Team List - Now the main landing page (removed hub redirect)
    path("", team_list, name="index"),
    path("", team_list, name="hub"),
    path("list/", team_list, name="list"),
    path("rankings/", team_ranking_view, name="rankings"),  # Updated to use ranking view
    
    path("create/", team_create_view, name="create"),

    # Detail + captain actions (slug-based)
    path("<slug:slug>/", team_profile_view, name="detail"),  # New public profile
    path("<slug:slug>/dashboard/", team_dashboard_view, name="dashboard"),  # New dashboard
    path("<slug:slug>/manage/", manage_team_view, name="manage"),
    # Aliases commonly referenced by templates
    path("<slug:slug>/manage/", manage_team_view, name="edit"),
    path("<slug:slug>/invite/", invite_member_view, name="invite_member"),
    path("<slug:slug>/invite/", invite_member_view, name="invite"),
    path("<slug:slug>/leave/", leave_team_view, name="leave"),
    path("<slug:slug>/join/", join_team_view, name="join"),
    path("<slug:slug>/kick/<int:profile_id>/", kick_member_view, name="kick"),
    path("<slug:slug>/transfer/<int:profile_id>/", transfer_captaincy_view, name="transfer_captaincy"),
    path("<slug:slug>/settings/", team_settings_view, name="settings"),
    path("<slug:slug>/delete/", delete_team_view, name="delete"),
    path("<slug:slug>/cancel-invite/", cancel_invite_view, name="cancel_invite"),
    
    # New dashboard actions
    path("<slug:slug>/follow/", follow_team, name="follow"),
    path("<slug:slug>/unfollow/", unfollow_team, name="unfollow"),
    path("<slug:slug>/update-roster-order/", update_roster_order, name="update_roster_order"),
    path("<slug:slug>/resend-invite/<int:invite_id>/", resend_invite, name="resend_invite"),
    
    # New professional management endpoints (kept from public.py)
    path("<slug:slug>/update-info/", update_team_info_view, name="update_team_info"),
    path("<slug:slug>/update-privacy/", update_privacy_view, name="update_privacy"),
    # New Quick Actions endpoints
    path("<slug:slug>/export-data/", export_team_data_view, name="export_team_data"),
    path("<slug:slug>/tournament-history/", tournament_history_view, name="tournament_history"),
    
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
    
    # AJAX endpoints (modularized)
    path("<slug:slug>/kick-member/", kick_member, name="kick_member"),
    path("<slug:slug>/transfer-captaincy/", transfer_captaincy, name="transfer_captaincy"),
    path("<slug:slug>/leave-team/", leave_team, name="leave_team"),
    path("my-teams-data/", my_teams_data, name="my_teams_ajax"),
    
    # Invites
    path("invites/", my_invites, name="my_invites"),
    # Alias for 'invitations' link
    path("invitations/", my_invites, name="invitations"),
    path("invites/<str:token>/accept/", accept_invite_view, name="accept_invite"),
    path("invites/<str:token>/decline/", decline_invite_view, name="decline_invite"),
    
    # AJAX endpoints for team creation
    path("api/validate-name/", validate_team_name, name="validate_team_name"),
    path("api/validate-tag/", validate_team_tag, name="validate_team_tag"),
    path("api/game-config/<str:game_code>/", get_game_config_api, name="game_config_api"),
    path("api/validate-user/", validate_user_identifier, name="validate_user_identifier"),
    
    # Social features namespace
    path("", include("apps.teams.urls_social", namespace="teams_social")),
]

# Add API endpoints if Django REST Framework is available
if HAS_DRF:
    api_patterns = [
        # Game configuration endpoints
        path('api/games/', api_views.game_configs_list, name='game-configs-list'),
        path('api/games/<str:game_code>/', api_views.game_config_detail, name='game-config-detail'),
        path('api/games/<str:game_code>/roles/', api_views.game_roles_list, name='game-roles-list'),
        
        # Team creation
        path('api/create/', api_views.create_team_with_roster, name='api-create-team'),
        
        # Validation endpoints
        path('api/validate/name/', api_views.validate_team_name, name='validate-team-name'),
        path('api/validate/tag/', api_views.validate_team_tag, name='validate-team-tag'),
        path('api/validate/ign/', api_views.validate_ign_unique, name='validate-ign'),
        path('api/validate/roster/', api_views.validate_roster_composition, name='validate-roster'),
        
        # Team viewsets (list and detail)
        path('api/', include(router.urls)),
    ]
    urlpatterns += api_patterns
