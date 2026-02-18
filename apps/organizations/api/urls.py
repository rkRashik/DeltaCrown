"""
API URLs for vNext Organization and Team creation + Management.

Endpoints:
    POST /api/vnext/organizations/create/ - Create organization
    POST /api/vnext/teams/create/ - Create team (independent or org-owned)
    
    # Organization Management (P3-T5)
    GET /api/vnext/orgs/<org_slug>/ - Get organization details
    POST /api/vnext/orgs/<org_slug>/members/add/ - Add member
    POST /api/vnext/orgs/<org_slug>/members/<member_id>/role/ - Update member role
    POST /api/vnext/orgs/<org_slug>/members/<member_id>/remove/ - Remove member
    POST /api/vnext/orgs/<org_slug>/settings/ - Update organization settings
    
    # Team Membership Management (P3-T6)
    GET /api/vnext/teams/<team_slug>/detail/ - Get team details with roster
    POST /api/vnext/teams/<team_slug>/members/add/ - Add team member
    POST /api/vnext/teams/<team_slug>/members/<member_id>/role/ - Update member role
    POST /api/vnext/teams/<team_slug>/members/<member_id>/remove/ - Remove team member
    POST /api/vnext/teams/<team_slug>/settings/ - Update team settings
    
    # Hub Live Widgets (Phase B)
    GET /api/system/ticker/ - Live ticker feed (matches, transfers, news)
    GET /api/players/lft/ - Scout radar (players looking for team)
    GET /api/scrims/active/ - Active scrim requests
    GET /api/teams/search/ - Team search autocomplete
"""

from django.urls import path
from apps.organizations.api import views, hub_endpoints
from apps.organizations.api.views import team_manage, user_history

app_name = 'organizations_api'

urlpatterns = [
    # Organization creation (P3-T7)
    path('organizations/validate-name/', views.validate_organization_name, name='validate_organization_name'),
    path('organizations/validate-badge/', views.validate_organization_badge, name='validate_organization_badge'),
    path('organizations/validate-slug/', views.validate_organization_slug, name='validate_organization_slug'),
    path('organizations/create/', views.create_organization, name='create_organization'),
    
    # Team creation
    path('teams/validate-name/', views.validate_team_name, name='validate_team_name'),
    path('teams/validate-tag/', views.validate_team_tag, name='validate_team_tag'),
    path('teams/ownership-check/', views.check_team_ownership, name='check_team_ownership'),
    path('teams/create/', views.create_team, name='create_team'),
    
    # Organization management (P3-T5)
    path('orgs/<str:org_slug>/', views.get_organization_detail, name='org_detail'),
    path('orgs/<str:org_slug>/members/add/', views.add_organization_member, name='add_member'),
    path('orgs/<str:org_slug>/members/<int:member_id>/role/', views.update_member_role, name='update_role'),
    path('orgs/<str:org_slug>/members/<int:member_id>/remove/', views.remove_organization_member, name='remove_member'),
    path('orgs/<str:org_slug>/settings/', views.update_organization_settings, name='update_settings'),
    
    # Team Manage HQ (Journey 3 - Backend)
    path('teams/<str:slug>/detail/', team_manage.team_detail, name='team_manage_detail'),
    path('teams/<str:slug>/members/add/', team_manage.add_member, name='team_manage_add_member'),
    path('teams/<str:slug>/members/<int:membership_id>/role/', team_manage.change_role, name='team_manage_change_role'),
    path('teams/<str:slug>/members/<int:membership_id>/remove/', team_manage.remove_member, name='team_manage_remove_member'),
    path('teams/<str:slug>/members/<int:membership_id>/status/', team_manage.change_member_status, name='team_manage_change_status'),
    path('teams/<str:slug>/members/<int:membership_id>/roster-photo/', team_manage.upload_roster_photo, name='team_manage_roster_photo'),
    path('teams/<str:slug>/settings/', team_manage.update_settings, name='team_manage_update_settings'),
    path('teams/<str:slug>/profile/', team_manage.update_profile, name='team_manage_update_profile'),
    path('teams/<str:slug>/owner-privacy/', team_manage.toggle_owner_privacy, name='team_manage_owner_privacy'),
    path('teams/<str:slug>/roster/lock/', team_manage.toggle_roster_lock, name='team_manage_roster_lock'),
    path('teams/<str:slug>/leave/', team_manage.leave_team, name='team_manage_leave'),
    path('teams/<str:slug>/disband/', team_manage.disband_team, name='team_manage_disband'),
    path('teams/<str:slug>/transfer-ownership/', team_manage.transfer_ownership, name='team_manage_transfer'),
    path('teams/<str:slug>/invite-link/', team_manage.generate_invite_link, name='team_manage_invite_link'),
    path('teams/<str:slug>/invite/', team_manage.send_invite, name='team_manage_send_invite'),
    path('teams/<str:slug>/invites/<int:invite_id>/cancel/', team_manage.cancel_invite, name='team_manage_cancel_invite'),
    path('teams/<str:slug>/search-players/', team_manage.search_players, name='team_manage_search_players'),
    path('teams/<str:slug>/activity/', team_manage.activity_timeline, name='team_manage_activity'),
    path('teams/<str:slug>/payment-methods/', team_manage.update_payment_methods, name='team_manage_payment_methods'),
    
    # Discord integration (Phase B)
    path('teams/<str:slug>/discord/', team_manage.discord_config, name='team_discord_config'),
    path('teams/<str:slug>/discord/save/', team_manage.discord_config_save, name='team_discord_config_save'),
    path('teams/<str:slug>/discord/chat/', team_manage.discord_chat_messages, name='team_discord_chat'),
    path('teams/<str:slug>/discord/chat/send/', team_manage.discord_chat_send, name='team_discord_chat_send'),
    path('teams/<str:slug>/discord/voice/', team_manage.discord_voice_link, name='team_discord_voice'),
    path('teams/<str:slug>/discord/test-webhook/', team_manage.discord_test_webhook, name='team_discord_test_webhook'),
    
    # Community & Media (Phase B)
    path('teams/<str:slug>/media/', team_manage.profile_upload_media, name='team_profile_upload_media'),
    path('teams/<str:slug>/community/', team_manage.community_data, name='team_community_data'),
    path('teams/<str:slug>/community/posts/', team_manage.community_create_post, name='team_community_create_post'),
    path('teams/<str:slug>/community/media/', team_manage.community_upload_media, name='team_community_upload_media'),
    path('teams/<str:slug>/community/highlights/', team_manage.community_add_highlight, name='team_community_add_highlight'),
    
    # Join Requests — public applications (Phase B)
    path('teams/<str:slug>/apply/', team_manage.apply_to_team, name='team_apply'),
    path('teams/<str:slug>/apply/withdraw/', team_manage.withdraw_application, name='team_withdraw_application'),
    path('teams/<str:slug>/join-requests/', team_manage.list_join_requests, name='team_join_requests'),
    path('teams/<str:slug>/join-requests/<int:request_id>/review/', team_manage.review_join_request, name='team_review_join_request'),
    
    # Tryout workflow (5-Point Overhaul — Point 1B)
    path('teams/<str:slug>/join-requests/<int:request_id>/tryout/schedule/', team_manage.schedule_tryout, name='team_schedule_tryout'),
    path('teams/<str:slug>/join-requests/<int:request_id>/tryout/advance/', team_manage.advance_tryout, name='team_advance_tryout'),
    
    # Recruitment settings — Job Post builder (5-Point Overhaul — Point 1A)
    path('teams/<str:slug>/recruitment/positions/', team_manage.recruitment_positions, name='team_recruitment_positions'),
    path('teams/<str:slug>/recruitment/positions/save/', team_manage.recruitment_position_save, name='team_recruitment_position_save'),
    path('teams/<str:slug>/recruitment/positions/<int:position_id>/delete/', team_manage.recruitment_position_delete, name='team_recruitment_position_delete'),
    path('teams/<str:slug>/recruitment/requirements/', team_manage.recruitment_requirements, name='team_recruitment_requirements'),
    path('teams/<str:slug>/recruitment/requirements/save/', team_manage.recruitment_requirement_save, name='team_recruitment_requirement_save'),
    path('teams/<str:slug>/recruitment/requirements/<int:requirement_id>/delete/', team_manage.recruitment_requirement_delete, name='team_recruitment_requirement_delete'),
    
    # Activity pin/unpin (5-Point Overhaul — Point 2)
    path('teams/<str:slug>/activity/<int:activity_id>/pin/', team_manage.toggle_activity_pin, name='team_toggle_activity_pin'),
    
    # Trophy management (5-Point Overhaul — Point 4)
    path('teams/<str:slug>/trophies/', team_manage.list_trophies, name='team_trophies'),
    path('teams/<str:slug>/trophies/save/', team_manage.save_trophy, name='team_save_trophy'),
    path('teams/<str:slug>/trophies/<str:trophy_id>/delete/', team_manage.delete_trophy, name='team_delete_trophy'),
    
    # Merch management (5-Point Overhaul — Point 4)
    path('teams/<str:slug>/merch/', team_manage.list_merch, name='team_merch'),
    path('teams/<str:slug>/merch/save/', team_manage.save_merch, name='team_save_merch'),
    path('teams/<str:slug>/merch/<str:merch_id>/delete/', team_manage.delete_merch, name='team_delete_merch'),
    
    # Manual milestones (7-Point Overhaul — Point 3)
    path('teams/<str:slug>/milestones/add/', team_manage.add_manual_milestone, name='team_add_milestone'),
    
    # Sponsors / Partners (7-Point Overhaul — Point 6)
    path('teams/<str:slug>/sponsors/', team_manage.list_sponsors, name='team_sponsors'),
    path('teams/<str:slug>/sponsors/save/', team_manage.save_sponsor, name='team_save_sponsor'),
    path('teams/<str:slug>/sponsors/<str:sponsor_id>/delete/', team_manage.delete_sponsor, name='team_delete_sponsor'),
    
    # Journey Milestones — curated public timeline
    path('teams/<str:slug>/journey/', team_manage.list_journey_milestones, name='team_journey'),
    path('teams/<str:slug>/journey/save/', team_manage.save_journey_milestone, name='team_journey_save'),
    path('teams/<str:slug>/journey/suggestions/', team_manage.journey_suggestions, name='team_journey_suggestions'),
    path('teams/<str:slug>/journey/suggestions/dismiss/', team_manage.dismiss_journey_suggestion, name='team_journey_dismiss'),
    path('teams/<str:slug>/journey/<int:milestone_id>/delete/', team_manage.delete_journey_milestone, name='team_journey_delete'),
    path('teams/<str:slug>/journey/<int:milestone_id>/toggle/', team_manage.toggle_journey_visibility, name='team_journey_toggle'),
    
    # User team history (Profile journey, audits)
    path('users/<int:user_id>/team-history/', user_history.user_team_history, name='user_team_history'),
    
    # Phase D: Team invite management
    path('teams/invites/', views.list_team_invites, name='list_invites'),
    path('teams/invites/membership/<int:membership_id>/accept/', views.accept_membership_invite, name='accept_membership'),
    path('teams/invites/membership/<int:membership_id>/decline/', views.decline_membership_invite, name='decline_membership'),
    path('teams/invites/email/<uuid:token>/accept/', views.accept_email_invite, name='accept_email'),
    path('teams/invites/email/<uuid:token>/decline/', views.decline_email_invite, name='decline_email'),
    
    # Phase C: Hub live widget endpoints
    path('system/ticker/', hub_endpoints.ticker_feed, name='ticker_feed'),
    path('system/players/lft/', hub_endpoints.scout_radar, name='scout_radar'),
    path('system/scrims/active/', hub_endpoints.active_scrims, name='active_scrims'),
    path('system/teams/search/', hub_endpoints.team_search, name='team_search'),
]
