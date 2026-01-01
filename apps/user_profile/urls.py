# apps/user_profile/urls.py
from django.urls import path
from .views import (
    MyProfileUpdateView, profile_view, my_tournaments_view,
    kyc_upload_view, kyc_status_view, privacy_settings_view, settings_view,
    save_game_profiles,
    # Phase 4: Modal Action Views
    update_bio, add_social_link, add_game_profile, edit_game_profile, delete_game_profile,
    # Phase 4: Follow System
    follow_user, unfollow_user, followers_list, following_list,
    # Phase 4: Full Page Views
    achievements_view, match_history_view, certificates_view,
    # UP-CLEANUP-04 Phase C Part 1: Safe mutation endpoints
    privacy_settings_save_safe, follow_user_safe, unfollow_user_safe,
    # UP-CLEANUP-04 Phase C Part 2: Safe game profile endpoints
    save_game_profiles_safe, update_game_id_safe
)
# UP-FE-MVP-01: Public Profile Views
from .views.public_profile_views import (
    public_profile_view, profile_activity_view,
    profile_settings_view, profile_privacy_view,
    # UP-FE-MVP-02: Mutation endpoints
    update_basic_info, update_social_links
)
# GP-FE-MVP-01: Game Passport API
from .views.passport_api import (
    toggle_lft, set_visibility, pin_passport, reorder_passports, delete_passport
)
# UP-SETTINGS-MVP-01: Settings API endpoints
from .views.settings_api import (
    upload_media, update_social_links_api, update_privacy_settings, 
    remove_media_api, get_privacy_settings, get_social_links,
    update_platform_settings, get_platform_settings, get_profile_data,
    # UP-PHASE6-C: New settings endpoints
    update_notification_preferences, get_notification_preferences,
    update_platform_preferences, get_platform_preferences,
    update_wallet_settings, get_wallet_settings
)
# UP-PHASE15-SESSION3: Social Links CRUD API
from .views.social_links_api import (
    social_link_create_api, social_link_update_single_api,
    social_link_delete_api, social_links_list_api
)
# UP-PHASE15-SESSION3: Game Passports API
from .views.game_passports_api import (
    list_game_passports_api, create_game_passport_api,
    update_game_passport_api, delete_game_passport_api
)
# UP-PASSPORT-CREATE-01: Passport creation endpoint
from .views.passport_create import create_passport

# UP-PHASE2F: Follower/Following API with privacy controls
from .views.follower_api import (
    get_followers, get_following, follow_user as follow_user_v2, unfollow_user as unfollow_user_v2
)

# UP-PHASE14B: Dynamic content API (no hardcoded dropdowns)
from .views.dynamic_content_api import (
    get_available_games, get_social_platforms, 
    get_privacy_presets, get_visibility_options,
    get_game_metadata  # UP-PHASE15: Game metadata for dynamic admin forms
)

# UP-PHASE14C: Showcase API (Facebook-style About section)
from .views.showcase_api import (
    get_showcase, update_showcase, toggle_showcase_section,
    set_featured_team, set_featured_passport,
    add_showcase_highlight, remove_showcase_highlight
)

# UP-PHASE15: About API (Facebook-style About section CRUD)
from .views.about_api import (
    get_about_items, create_about_item, update_about_item,
    delete_about_item, reorder_about_items
)

# UP-PHASE2D: Interactive Owner Flows (Bounties, Loadout, Trophy Showcase)
from .views.bounty_api import (
    create_bounty, accept_bounty,
    # UP-PHASE2E: Match progression
    start_match, submit_proof, confirm_result, raise_dispute
)
from .views.endorsement_api import award_bounty_endorsement
from .views.loadout_api import (
    save_hardware, save_game_config,
    delete_hardware, delete_game_config
)
from .views.trophy_showcase_api import update_trophy_showcase

from .views_public import public_profile, profile_api
from .api_views import get_game_id, update_game_id
from .api.game_id_api import (
    check_game_id_api,
    save_game_id_api,
    get_all_game_ids_api,
    delete_game_id_api
)

# Phase B: Import redirect functions
from django.http import HttpResponsePermanentRedirect
from django.urls import reverse as url_reverse
import logging

logger = logging.getLogger(__name__)


def redirect_to_modern_profile(request, username):
    """301 redirect from legacy /u/<username>/ or /<username>/ to /@<username>/"""
    target_url = url_reverse('user_profile:public_profile', kwargs={'username': username})
    if request.GET:
        target_url = f"{target_url}?{request.GET.urlencode()}"
    user_id = request.user.id if request.user.is_authenticated else None
    logger.info(f"LEGACY_PROFILE_REDIRECT: {request.path} → {target_url} (user_id={user_id})")
    return HttpResponsePermanentRedirect(target_url)


def redirect_get_game_id(request):
    """301 redirect from /api/profile/get-game-id/ to /api/profile/game-ids/"""
    target_url = url_reverse('user_profile:get_all_game_ids_api')
    if request.GET:
        target_url = f"{target_url}?{request.GET.urlencode()}"
    user_id = request.user.id if request.user.is_authenticated else None
    logger.info(f"LEGACY_API_REDIRECT: {request.path} → {target_url} (user_id={user_id})")
    return HttpResponsePermanentRedirect(target_url)

app_name = "user_profile"

urlpatterns = [
    # ============================================
    # UP-FE-MVP-01: PUBLIC PROFILE ROUTES (Privacy-Safe)
    # ============================================
    # Public Profile Routes (@ prefix)
    path("@<str:username>/", public_profile_view, name="public_profile"),
    path("@<str:username>/", public_profile_view, name="profile"),  # Alias for backward compatibility
    path("@<str:username>/activity/", profile_activity_view, name="profile_activity"),
    
    # Owner Pages (/me/ prefix)
    path("me/settings/", profile_settings_view, name="profile_settings"),
    path("me/settings/", profile_settings_view, name="settings"),  # Alias for template compatibility
    path("me/privacy/", profile_privacy_view, name="profile_privacy"),
    # UP-PHASE2E-HOTFIX: Backward compatibility alias for old route name
    path("me/privacy-v2/", profile_privacy_view, name="profile_privacy_v2"),
    
    # UP-FE-MVP-02: Settings mutation endpoints
    path("me/settings/basic/", update_basic_info, name="update_basic_info"),
    path("me/settings/social/", update_social_links, name="update_social_links"),
    path("me/settings/media/", upload_media, name="upload_media"),
    path("me/settings/media/remove/", remove_media_api, name="remove_media"),
    path("me/settings/privacy/", get_privacy_settings, name="get_privacy_settings"),
    path("me/settings/privacy/save/", update_privacy_settings, name="update_privacy_settings"),
    
    # GP-FE-MVP-01: Game Passport management API
    path("api/passports/toggle-lft/", toggle_lft, name="passport_toggle_lft"),
    path("api/passports/set-visibility/", set_visibility, name="passport_set_visibility"),
    path("api/passports/pin/", pin_passport, name="passport_pin"),
    path("api/passports/reorder/", reorder_passports, name="passport_reorder"),
    path("api/passports/create/", create_passport, name="passport_create"),
    path("api/passports/<int:passport_id>/delete/", delete_passport, name="passport_delete"),
    
    # UP-SETTINGS-MVP-01: Additional settings API
    path("api/social-links/", social_links_list_api, name="social_links_list_api"),  # UP-PHASE15: New list API
    path("api/social-links/legacy/", get_social_links, name="get_social_links"),  # Legacy dict format
    path("api/social-links/create/", social_link_create_api, name="social_link_create_api"),
    path("api/social-links/update/", social_link_update_single_api, name="social_link_update_single_api"),
    path("api/social-links/delete/", social_link_delete_api, name="social_link_delete_api"),
    path("api/social-links/bulk-update/", update_social_links_api, name="update_social_links_api"),  # Legacy bulk
    # UP-PHASE15-SESSION3: Game Passports API
    path("api/game-passports/", list_game_passports_api, name="list_game_passports_api"),
    path("api/game-passports/create/", create_game_passport_api, name="create_game_passport_api"),
    path("api/game-passports/update/", update_game_passport_api, name="update_game_passport_api"),
    path("api/game-passports/delete/", delete_game_passport_api, name="delete_game_passport_api"),
    # Frontend compatibility aliases (template expects /profile/api/game-passports/)
    path("profile/api/game-passports/", list_game_passports_api, name="game_passports_list_alias"),
    path("profile/api/game-passports/create/", create_game_passport_api, name="game_passports_create_alias"),
    path("profile/api/game-passports/delete/", delete_game_passport_api, name="game_passports_delete_alias"),
    path("api/platform-settings/", get_platform_settings, name="get_platform_settings"),
    path("me/settings/platform/", update_platform_settings, name="update_platform_settings"),
    path("api/profile/data/", get_profile_data, name="get_profile_data"),
    
    # UP-PHASE14B: Dynamic content APIs (eliminate hardcoded dropdowns)
    path("api/games/", get_available_games, name="get_available_games"),
    path("api/games/<int:game_id>/metadata/", get_game_metadata, name="get_game_metadata"),  # UP-PHASE15: Dynamic admin
    path("api/social-links/platforms/", get_social_platforms, name="get_social_platforms"),
    path("api/privacy/presets/", get_privacy_presets, name="get_privacy_presets"),
    path("api/privacy/visibility-options/", get_visibility_options, name="get_visibility_options"),
    
    # UP-PHASE14C: Showcase APIs (Facebook-style About management)
    path("api/profile/showcase/", get_showcase, name="get_showcase"),
    path("api/profile/showcase/update/", update_showcase, name="update_showcase"),
    path("api/profile/showcase/toggle/", toggle_showcase_section, name="toggle_showcase_section"),
    path("api/profile/showcase/featured-team/", set_featured_team, name="set_featured_team"),
    path("api/profile/showcase/featured-passport/", set_featured_passport, name="set_featured_passport"),
    path("api/profile/showcase/highlights/add/", add_showcase_highlight, name="add_showcase_highlight"),
    path("api/profile/showcase/highlights/remove/", remove_showcase_highlight, name="remove_showcase_highlight"),
    
    # UP-PHASE15: About APIs (Facebook-style About CRUD)
    path("api/profile/about/", get_about_items, name="get_about_items"),
    path("api/profile/about/create/", create_about_item, name="create_about_item"),
    path("api/profile/about/<int:item_id>/update/", update_about_item, name="update_about_item"),
    path("api/profile/about/<int:item_id>/delete/", delete_about_item, name="delete_about_item"),
    path("api/profile/about/reorder/", reorder_about_items, name="reorder_about_items"),
    
    # UP-PHASE2D: Interactive Owner Flows (Bounties, Loadout, Trophy Showcase)
    path("api/bounties/create/", create_bounty, name="create_bounty"),
    path("api/bounties/<int:bounty_id>/accept/", accept_bounty, name="accept_bounty"),
    
    # UP-PHASE2E: Bounty Match Progression
    path("api/bounties/<int:bounty_id>/start/", start_match, name="start_match"),
    path("api/bounties/<int:bounty_id>/submit-proof/", submit_proof, name="submit_proof"),
    path("api/bounties/<int:bounty_id>/confirm-result/", confirm_result, name="confirm_result"),
    path("api/bounties/<int:bounty_id>/dispute/", raise_dispute, name="raise_dispute"),
    
    # UP-PHASE2E PART 2: Skill Endorsements
    path("api/bounties/<int:bounty_id>/endorse/", award_bounty_endorsement, name="award_bounty_endorsement"),
    
    # UP-PHASE2F: Follower/Following API with privacy controls
    path("api/profile/<str:username>/followers/", get_followers, name="get_followers"),
    path("api/profile/<str:username>/following/", get_following, name="get_following"),
    path("api/profile/<str:username>/follow/", follow_user_v2, name="follow_user_v2"),
    path("api/profile/<str:username>/unfollow/", unfollow_user_v2, name="unfollow_user_v2"),
    
    path("api/profile/loadout/hardware/", save_hardware, name="save_hardware"),
    path("api/profile/loadout/game-config/", save_game_config, name="save_game_config"),
    path("api/profile/loadout/hardware/<int:hardware_id>/", delete_hardware, name="delete_hardware"),
    path("api/profile/loadout/game-config/<int:config_id>/", delete_game_config, name="delete_game_config"),
    path("api/profile/trophy-showcase/update/", update_trophy_showcase, name="update_trophy_showcase"),
    
    # UP-PHASE6-C: Settings redesign endpoints
    path("me/settings/notifications/", update_notification_preferences, name="update_notification_preferences"),
    path("api/settings/notifications/", get_notification_preferences, name="get_notification_preferences"),
    path("me/settings/platform-prefs/", update_platform_preferences, name="update_platform_preferences"),
    path("api/settings/platform-prefs/", get_platform_preferences, name="get_platform_preferences"),
    path("me/settings/wallet/", update_wallet_settings, name="update_wallet_settings"),
    path("api/settings/wallet/", get_wallet_settings, name="get_wallet_settings"),
    
    # ============================================
    # LEGACY OWNER PAGES (me/...)
    # ============================================
    path("me/edit/", MyProfileUpdateView.as_view(), name="edit"),
    path("me/tournaments/", my_tournaments_view, name="my_tournaments"),
    
    # KYC Verification
    path("me/kyc/upload/", kyc_upload_view, name="kyc_upload"),
    path("me/kyc/status/", kyc_status_view, name="kyc_status"),
    
    # LEGACY: Privacy Settings (old route - redirects to v2)
    # path("me/privacy/", privacy_settings_view, name="privacy_settings"),  # Replaced by profile_privacy_v2
    
    # LEGACY: Modular Settings Page (old route - redirects to v2)
    # path("me/settings/", settings_view, name="settings"),  # Replaced by profile_settings_v2
    
    # Save Game Profiles
    path("actions/save-game-profiles/", save_game_profiles, name="save_game_profiles"),

    # ============================================
    # PHASE 4: MODAL ACTION ENDPOINTS (POST handlers)
    # ============================================
    path("actions/update-bio/", update_bio, name="update_bio"),
    path("actions/add-social-link/", add_social_link, name="add_social_link"),
    path("actions/add-game-profile/", add_game_profile, name="add_game_profile"),
    path("actions/edit-game-profile/<int:profile_id>/", edit_game_profile, name="edit_game_profile"),
    path("actions/delete-game-profile/<int:profile_id>/", delete_game_profile, name="delete_game_profile"),
    
    # Follow System
    path("actions/follow/<str:username>/", follow_user, name="follow_user"),
    path("actions/unfollow/<str:username>/", unfollow_user, name="unfollow_user"),
    path("@<str:username>/followers/", followers_list, name="followers_list"),
    path("@<str:username>/following/", following_list, name="following_list"),

    # ============================================
    # API ENDPOINTS (api/...)
    # Specific paths BEFORE catch-all patterns
    # ============================================
    # UP-CLEANUP-04 PHASE C PART 2: Safe game ID API endpoint
    path("api/profile/update-game-id-safe/", update_game_id_safe, name="update_game_id_safe"),
    
    # Phase B: Legacy API redirects (read-only endpoints safe for 301)
    path("api/profile/get-game-id/", redirect_get_game_id, name="get_game_id_legacy"),
    
    # Phase B: Mutation endpoint remains wrapper-based (will migrate in Phase C)
    path("api/profile/update-game-id/", update_game_id, name="update_game_id"),
    
    # Modern Game ID API endpoints
    path("api/profile/check-game-id/<str:game_code>/", check_game_id_api, name="check_game_id_api"),
    path("api/profile/save-game-id/<str:game_code>/", save_game_id_api, name="save_game_id_api"),
    path("api/profile/game-ids/", get_all_game_ids_api, name="get_all_game_ids_api"),
    path("api/profile/delete-game-id/<str:game_code>/", delete_game_id_api, name="delete_game_id_api"),
    
    # Catch-all profile API (MUST BE AFTER SPECIFIC ROUTES)
    path("api/profile/<str:profile_id>/", profile_api, name="profile_api"),

    # ============================================
    # PHASE 4: PUBLIC PROFILE PAGES (LEGACY)
    # IMPORTANT: These must come AFTER specific paths to avoid conflicts
    # NOTE: Main profile route (@<username>/) moved to V2 (profile_public_v2)
    # ============================================
    
    # Full-page component views (legacy - still active)
    path("legacy/@<str:username>/achievements/", achievements_view, name="achievements"),
    path("legacy/@<str:username>/match-history/", match_history_view, name="match_history"),
    path("legacy/@<str:username>/certificates/", certificates_view, name="certificates"),
    
    # LEGACY: Main profile page (replaced by profile_public_v2)
    # path("@<str:username>/", profile_view, name="profile"),  # Replaced by profile_public_v2
    
    # ============================================
    # UP-CLEANUP-04 PHASE C PART 1: SAFE MUTATION ENDPOINTS
    # ============================================
    
    # Safe endpoints with audit trail + privacy enforcement
    path("actions/privacy-settings/save/", privacy_settings_save_safe, name="privacy_settings_save_safe"),
    path("actions/follow-safe/<str:username>/", follow_user_safe, name="follow_user_safe"),
    path("actions/unfollow-safe/<str:username>/", unfollow_user_safe, name="unfollow_user_safe"),
    
    # ============================================
    # UP-CLEANUP-04 PHASE C PART 2: SAFE GAME PROFILE ENDPOINTS
    # ============================================
    
    # Safe game profile batch save with validation + audit
    path("actions/game-profiles/save/", save_game_profiles_safe, name="save_game_profiles_safe"),
    
    # ============================================
    # LEGACY COMPATIBILITY ROUTES (Phase B: 301 Redirects)
    # ============================================
    
    # Phase B: Legacy profile URLs redirect to canonical @username format
    path("u/<str:username>/", redirect_to_modern_profile, name="public_profile"),
    path("<str:username>/", redirect_to_modern_profile, name="profile_legacy"),
]
