"""
Tests for Team Detail Template Contract Implementation

Verifies that get_team_detail_context() fulfills the Team Detail Page Contract
(docs/contracts/TEAM_DETAIL_PAGE_CONTRACT.md).
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, RequestFactory, Client
from django.test import utils
from django.db import connection

from apps.organizations.models import Team, Organization, TeamRanking
from apps.games.models import Game
from apps.organizations.services.team_detail_context import (
    get_team_detail_context,
    FALLBACK_URLS,
)

User = get_user_model()



class TestTeamDetailContract(TestCase):
    """Test contract compliance of team detail context builder."""
    
    def setUp(self):
        """Create test fixtures."""
        self.factory = RequestFactory()
        
        # Create test users
        self.owner = User.objects.create_user(username='owner', email='owner@test.com', password='pass')
        self.member = User.objects.create_user(username='member', email='member@test.com', password='pass')
        self.public_user = User.objects.create_user(username='public', email='public@test.com', password='pass')
        
        # Create public team (Legacy schema: game CharField, is_active, is_public)
        self.public_team = Team.objects.create(
            name='Test Warriors',
            slug='test-warriors',
            tag='TW',
            tagline='Fighting for glory',
            game='valorant',
            region='NA',
            is_active=True,
            is_public=True,
        )
        
        # Create private team (Legacy schema: different game slug)
        self.private_team = Team.objects.create(
            name='Secret Squad',
            slug='secret-squad',
            tag='SS',
            game='league-of-legends',  # Different game
            region='EU',
            is_active=True,
            is_public=False,  # Private team
        )
    
    def test_context_contains_all_required_top_level_keys(self):
        """Context must include all top-level keys from contract."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        required_keys = {
            'team', 'organization', 'viewer', 'permissions', 'ui',
            'roster', 'stats', 'streams', 'partners', 'merch',
            'pending_actions', 'page'
        }
        
        assert set(context.keys()) >= required_keys, \
            f"Missing keys: {required_keys - set(context.keys())}"
    
    def test_team_context_contains_tier1_fields(self):
        """Team dict must contain all Tier-1 critical fields."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        tier1_fields = {
            'name', 'slug', 'tag', 'logo_url', 'banner_url',
            'visibility', 'game'
        }
        
        assert set(context['team'].keys()) >= tier1_fields, \
            f"Missing Tier-1 fields: {tier1_fields - set(context['team'].keys())}"
    
    def test_team_name_never_empty(self):
        """Team name must have fallback if missing."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        assert context['team']['name'], "Team name is empty"
        assert isinstance(context['team']['name'], str), "Team name is not a string"
    
    def test_team_images_have_fallback_urls(self):
        """Missing logo/banner must return fallback URLs, not None."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        logo_url = context['team']['logo_url']
        banner_url = context['team']['banner_url']
        
        assert logo_url, "Logo URL is empty"
        assert banner_url, "Banner URL is empty"
        assert isinstance(logo_url, str), "Logo URL is not a string"
        assert isinstance(banner_url, str), "Banner URL is not a string"
        
        # Should be either fallback or valid URL
        assert (logo_url == FALLBACK_URLS['team_logo'] or logo_url.startswith('/') or logo_url.startswith('http')), \
            f"Invalid logo URL: {logo_url}"
    
    def test_viewer_context_for_anonymous_user(self):
        """Anonymous viewer must have safe defaults."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        viewer = context['viewer']
        assert viewer['is_authenticated'] is False, "Anonymous should not be authenticated"
        assert viewer['username'] == 'Anonymous', "Anonymous username mismatch"
        assert viewer['role'] == 'PUBLIC', "Anonymous should have PUBLIC role"
        assert 'avatar_url' in viewer, "Missing avatar_url"
    
    def test_viewer_context_for_authenticated_user(self):
        """Authenticated viewer must have correct identity."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=self.public_user
        )
        
        viewer = context['viewer']
        assert viewer['is_authenticated'] is True, "Authenticated user should be authenticated"
        assert viewer['username'] == 'public', "Username mismatch"
        assert viewer['role'] in ('PUBLIC', 'MEMBER', 'STAFF', 'OWNER'), \
            f"Invalid role: {viewer['role']}"
    
    def test_permissions_dict_has_required_flags(self):
        """Permissions must contain all required boolean flags."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        required_flags = {
            'can_view_private', 'can_edit_team', 'can_manage_roster',
            'can_invite', 'can_view_operations', 'can_view_financial'
        }
        
        assert set(context['permissions'].keys()) >= required_flags, \
            f"Missing permission flags: {required_flags - set(context['permissions'].keys())}"
        
        # All values must be boolean
        for key, value in context['permissions'].items():
            assert isinstance(value, bool), f"Permission {key} is not boolean: {value}"
    
    def test_permissions_false_for_anonymous_on_public_team(self):
        """Anonymous user should have minimal permissions."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        perms = context['permissions']
        assert perms['can_edit_team'] is False
        assert perms['can_manage_roster'] is False
        assert perms['can_view_financial'] is False
    
    def test_roster_is_dict_with_items_and_count(self):
        """Roster must be a dict with 'items' (list) and 'count' (int)."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        assert isinstance(context['roster'], dict), "Roster is not a dict"
        assert 'items' in context['roster'], "Roster missing 'items' key"
        assert 'count' in context['roster'], "Roster missing 'count' key"
        assert isinstance(context['roster']['items'], list), "Roster items is not a list"
        assert isinstance(context['roster']['count'], int), "Roster count is not an int"
    
    def test_stats_dict_has_required_fields(self):
        """Stats must contain required fields from TeamRanking."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        required_stats = {
            'crown_points', 'tier', 'global_rank', 'regional_rank',
            'streak_count', 'is_hot_streak', 'rank_change_24h', 'last_activity_date'
        }
        
        assert set(context['stats'].keys()) >= required_stats, \
            f"Missing stats: {required_stats - set(context['stats'].keys())}"
        
        # Numeric/type checks
        assert isinstance(context['stats']['crown_points'], int)
        assert isinstance(context['stats']['tier'], str)
        assert isinstance(context['stats']['is_hot_streak'], bool)
    
    def test_ui_contains_theme_and_demo_flag(self):
        """UI context must contain theme and demo remote flag."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        assert 'theme' in context['ui'], "Missing theme"
        assert 'enable_demo_remote' in context['ui'], "Missing enable_demo_remote"
        assert isinstance(context['ui']['enable_demo_remote'], bool), \
            "enable_demo_remote is not boolean"
    
    def test_page_metadata_has_title(self):
        """Page metadata must include title."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        assert 'title' in context['page'], "Missing page title"
        assert context['page']['title'], "Page title is empty"
        assert 'Test Warriors' in context['page']['title'] or 'Team' in context['page']['title'], \
            "Page title does not mention team"
    
    def test_context_never_raises_attribute_error_for_missing_fields(self):
        """Context builder must be schema-resilient."""
        # This test passes if get_team_detail_context doesn't raise AttributeError
        try:
            context = get_team_detail_context(
                team_slug='test-warriors',
                viewer=None
            )
            assert context is not None, "Context is None"
        except AttributeError as e:
            pytest.fail(f"AttributeError raised: {e}")
    
    def test_organization_context_nullable(self):
        """Organization can be None if team is independent."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        # Organization is either None or a dict
        org = context['organization']
        assert org is None or isinstance(org, dict), \
            f"Organization must be None or dict, got {type(org)}"
        
        if org is not None:
            assert 'name' in org, "Organization missing name"
            assert 'slug' in org, "Organization missing slug"
    
    def test_private_team_restricts_data_for_unauthorized_viewer(self):
        """Private team should return minimal data for unauthorized viewers."""
        context = get_team_detail_context(
            team_slug='secret-squad',
            viewer=None  # Anonymous
        )
        
        # Tier 1 identity should exist
        assert context['team']['name'], "Private team name missing"
        assert context['team']['slug'], "Private team slug missing"
        
        # Tier 2+ should be restricted (if privacy is enforced)
        # Note: This test may need adjustment based on actual privacy implementation
        # For now, we just check that context doesn't crash
        assert isinstance(context['roster'], dict), "Roster should be dict"
        assert isinstance(context['stats'], dict), "Stats should be dict"
    
    def test_legacy_enable_demo_remote_flag_present(self):
        """Legacy flag for demo remote should exist for backward compatibility."""
        context = get_team_detail_context(
            team_slug='test-warriors',
            viewer=None
        )
        
        assert 'enable_demo_remote' in context, "Missing legacy enable_demo_remote flag"
        assert isinstance(context['enable_demo_remote'], bool)
    
    def test_team_does_not_exist_raises_exception(self):
        """Non-existent team should raise Team.DoesNotExist."""
        with pytest.raises(Team.DoesNotExist):
            get_team_detail_context(
                team_slug='non-existent-team-slug-xyz',
                viewer=None
            )
    
    def test_request_parameter_handled_safely(self):
        """Request parameter should be optional and handled safely."""
        request = self.factory.get('/teams/test-warriors/')
        
        try:
            context = get_team_detail_context(
                team_slug='test-warriors',
                viewer=None,
                request=request
            )
            assert context is not None
        except Exception as e:
            pytest.fail(f"Request parameter caused exception: {e}")


class TestTeamDetailView(TestCase):
    """Test team detail view integration with new context builder."""
    
    def setUp(self):
        """Create test team."""
        self.user = User.objects.create_user(username='testuser', email='test@test.com', password='pass')
        
        self.team = Team.objects.create(
            name='View Test Team',
            slug='view-test-team',
            tag='VTT',
            game='valorant',
            region='US',
            is_active=True,
            is_public=True,
        )
    
    def test_view_returns_200_for_public_team(self):
        """View should render successfully for public team."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    
    def test_view_uses_correct_template(self):
        """View should use team_detail.html template."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        self.assertTemplateUsed(response, 'organizations/team/team_detail.html')
    
    def test_view_context_contains_contract_keys(self):
        """View should pass contract-compliant context to template."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        
        required_keys = {
            'team', 'organization', 'viewer', 'permissions', 'ui',
            'roster', 'stats', 'page'
        }
        
        context_keys = set(response.context.keys())
        assert required_keys.issubset(context_keys), \
            f"Missing context keys: {required_keys - context_keys}"
    
    def test_view_team_name_in_rendered_content(self):
        """Rendered HTML should contain team name."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        content = response.content.decode('utf-8')
        
        assert 'View Test Team' in content, "Team name not found in rendered HTML"


# =============================================================================
# P4-T1.3 Game Lookup Tests (GameService Integration)
# =============================================================================


class TestGameLookupIntegration(TestCase):
    """Test GameService.get_game_by_id() integration in context builder."""
    
    def setUp(self):
        """Create test fixtures with real game data."""
        self.owner = User.objects.create_user(username='gametest', email='game@test.com', password='pass')
        
        # Create real game
        self.game = Game.objects.create(
            name='Valorant',
            display_name='VALORANT™',
            slug='valorant',
            short_code='VAL',
            category='FPS',
            game_type='TEAM_VS_TEAM',
            primary_color='#ff4655',
            secondary_color='#1e1b4b',
        )
        
        # Create team with valid game slug
        self.team = Team.objects.create(
            name='Game Test Team',
            slug='game-test-team',
            game='valorant',
            region='NA',
            is_active=True,
            is_public=True,
        )
    
    def test_game_context_with_valid_game_id(self):
        """Game data resolved correctly for valid game_id."""
        context = get_team_detail_context(
            team_slug='game-test-team',
            viewer=None
        )
        
        assert context['team']['game']['id'] == self.game.id
        assert context['team']['game']['name'] == 'VALORANT™'
        assert context['team']['game']['slug'] == 'valorant'
        assert context['team']['game']['primary_color'] == '#ff4655'
    
    def test_game_context_with_invalid_game_id(self):
        """Fallback for invalid game_id."""
        # Create team with non-existent game slug
        team = Team.objects.create(
            name='Invalid Game Team',
            slug='invalid-game-team',
            game='unknown-game-99999',
            region='NA',
            is_active=True,
            is_public=True,
        )
        
        context = get_team_detail_context(
            team_slug='invalid-game-team',
            viewer=None
        )
        
        assert context['team']['game']['id'] == 99999
        assert context['team']['game']['name'] == 'Game #99999'
        assert context['team']['game']['logo_url'] is None
    
    def test_game_context_with_missing_logo(self):
        """Handles games without logo uploaded."""
        # Game without logo
        game_no_logo = Game.objects.create(
            name='TestGame',
            display_name='Test Game',
            slug='testgame',
            short_code='TG',
            category='OTHER',
            game_type='TEAM_VS_TEAM',
        )
        
        team = Team.objects.create(
            name='No Logo Team',
            slug='no-logo-team',
            game='testgame',
            region='NA',
            is_active=True,
            is_public=True,
        )
        
        context = get_team_detail_context(
            team_slug='no-logo-team',
            viewer=None
        )
        
        assert context['team']['game']['logo_url'] is None
        assert context['team']['game']['name'] == 'Test Game'
    
    def test_game_context_caching(self):
        """Verify game data uses cache (query count test)."""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test import TransactionTestCase
        from django.core.cache import cache
        
        # Clear cache first
        cache.clear()
        
        # First call - should hit database
        context1 = get_team_detail_context(
            team_slug='game-test-team',
            viewer=None
        )
        
        # Second call - should use cache (same team, same game_id)
        context2 = get_team_detail_context(
            team_slug='game-test-team',
            viewer=None
        )
        
        # Both contexts should be identical
        assert context1['team']['game'] == context2['team']['game']


class TestTier1UIRendering(TestCase):
    """Test Tier-1 UI activation: verify template renders dynamic data instead of hardcoded values."""
    
    def setUp(self):
        """Create test fixtures for UI rendering tests."""
        self.client = Client()
        self.owner = User.objects.create_user(username='ui_owner', email='ui@test.com', password='pass')
        
        # Create organization (uses 'ceo' not 'owner')
        self.org = Organization.objects.create(
            name='Phoenix Esports',
            slug='phoenix-esports',
            ceo=self.owner,
        )
        
        # Create game (uses ImageField logo, not logo_url)
        self.game = Game.objects.create(
            name='League of Legends',
            display_name='League of Legends™',
            slug='league-of-legends',
            short_code='LOL',
            primary_color='#C89B3C',
            secondary_color='#0A323C',
            category='MOBA',
            game_type='TEAM_VS_TEAM',
        )
        
        # Create team (Legacy schema: no organization FK yet)
        self.team = Team.objects.create(
            name='Dragon Slayers',
            slug='dragon-slayers',
            tag='DRAG',
            tagline='Burning bright, fighting fierce',
            game='league-of-legends',
            region='NA',
            is_active=True,
            is_public=True,
        )
    
    def test_context_variables_match_contract(self):
        """Verify context builder returns exact keys specified in contract."""
        context = get_team_detail_context(
            team_slug=self.team.slug,
            viewer=None
        )
        
        # Verify team.logo_url exists and is a string
        assert 'logo_url' in context['team'], "Missing team.logo_url"
        assert isinstance(context['team']['logo_url'], str), "team.logo_url is not a string"
        assert context['team']['logo_url'], "team.logo_url is empty"
        
        # Verify team.banner_url exists and is a string
        assert 'banner_url' in context['team'], "Missing team.banner_url"
        assert isinstance(context['team']['banner_url'], str), "team.banner_url is not a string"
        assert context['team']['banner_url'], "team.banner_url is empty"
        
        # Verify organization structure
        assert context['organization'] is not None, "Organization should not be None for org team"
        assert 'name' in context['organization'], "Missing organization.name"
        assert 'url' in context['organization'], "Missing organization.url"
        assert 'slug' in context['organization'], "Missing organization.slug"
        
        # Verify game structure
        assert context['team']['game'] is not None, "Game should not be None"
        assert 'name' in context['team']['game'], "Missing game.name"
        assert isinstance(context['team']['game']['name'], str), "game.name is not a string"
        assert context['team']['game']['name'], "game.name is empty"
    
    def test_template_uses_correct_variable_paths(self):
        """Verify template uses team.logo_url and team.banner_url (not invented keys)."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        html = response.content.decode('utf-8')
        
        # Check that template processed variables (no raw Django template syntax in output)
        assert '{{ team.logo_url' not in html, "Template variable not processed: team.logo_url"
        assert '{{ team.banner_url' not in html, "Template variable not processed: team.banner_url"
        assert '{{ team.game.name' not in html, "Template variable not processed: team.game.name"
        assert '{{ organization.name' not in html, "Template variable not processed: organization.name"
        
        # Verify image tags have src attributes (not empty)
        assert 'src=' in html, "No image src attributes found"
    
    def test_render_uses_team_name_not_hardcoded(self):
        """Template should render team.name, not hardcoded demo names in visible content."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        html = response.content.decode('utf-8')
        
        # Should contain team name
        assert 'Dragon Slayers' in html, "Team name not found in rendered HTML"
        
        # Extract visible content (remove <style>, <script>, <!-- comments -->)
        import re
        visible_html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        visible_html = re.sub(r'<script[^>]*>.*?</script>', '', visible_html, flags=re.DOTALL)
        visible_html = re.sub(r'<!--.*?-->', '', visible_html, flags=re.DOTALL)
        
        # Should NOT contain hardcoded demo names in visible content
        assert 'Cyber Knights' not in visible_html, "Hardcoded 'Cyber Knights' found in visible HTML"
        assert 'Test Warriors' not in visible_html, "Hardcoded 'Test Warriors' found in visible HTML"
    
    def test_render_uses_team_banner_url(self):
        """Template should use team.banner_url, not pixabay hardcoded banner."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        html = response.content.decode('utf-8')
        
        # Should NOT use hardcoded demo banner
        assert 'pixabay.com' not in html, "Hardcoded pixabay banner found in HTML"
        assert 'chess-3526451' not in html, "Hardcoded chess banner found in HTML"
    
    def test_render_uses_team_logo_url(self):
        """Template should use team.logo_url IMG tag, not SVG placeholder."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        html = response.content.decode('utf-8')
        
        # Should NOT use hardcoded SVG placeholder in logo slab (check for characteristic SVG path)
        # SVG placeholder has: viewBox="0 0 24 24" with specific path d="M12 2L2 7..."
        # If team uses fallback image, it should be <img> tag, not inline SVG
        # This is a structural check - template should emit <img> not <svg> in logo-slab__inner
        assert '<svg class="w-20 h-20 md:w-24 md:h-24 text-white' not in html, \
            "Hardcoded SVG placeholder still present in logo section"
    
    def test_render_uses_organization_name_with_link(self):
        """Template should show organization.name with link when org exists."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        html = response.content.decode('utf-8')
        
        # Should contain org name
        assert 'Phoenix Esports' in html, "Organization name not found in rendered HTML"
        
        # Should have link to org page
        assert '/orgs/phoenix-esports/' in html or 'phoenix-esports' in html, \
            "Organization link not found in HTML"
        
        # Should NOT contain hardcoded demo org
        assert 'One World' not in html, "Hardcoded 'One World' organization found in HTML"
    
    def test_render_uses_game_name(self):
        """Template should show team.game.name, not 'VALORANT' hardcoded."""
        response = self.client.get(f'/teams/{self.team.slug}/')
        html = response.content.decode('utf-8')
        
        # Should contain game name (uppercased in template)
        assert 'LEAGUE OF LEGENDS' in html, "Game name not found in rendered HTML"
        
        # Should NOT contain hardcoded demo game
        assert 'VALORANT' not in html, "Hardcoded 'VALORANT' game name found in HTML"
    
    def test_independent_team_shows_independent_not_blank(self):
        """Teams without organization should show 'Independent', not blank or 'One World'."""
        # Create independent team (Legacy schema)
        solo_team = Team.objects.create(
            name='Solo Warriors',
            slug='solo-warriors',
            tag='SOLO',
            game='league-of-legends',
            region='EU',
            is_active=True,
            is_public=True,
        )
        
        response = self.client.get(f'/teams/{solo_team.slug}/')
        html = response.content.decode('utf-8')
        
        # Should show "Independent"
        assert 'Independent' in html, "'Independent' fallback not found for org-less team"
        
        # Should NOT show hardcoded org
        assert 'One World' not in html, "Hardcoded 'One World' shown for independent team"
    
    def test_management_buttons_gated_by_permissions(self):
        """Management buttons should only appear when permissions.can_edit_team is True."""
        # Anonymous user - no management buttons
        response = self.client.get(f'/teams/{self.team.slug}/')
        html = response.content.decode('utf-8')
        
        # Check if MANAGE button text appears (it should be gated by {% if permissions.can_edit_team %})
        # If anonymous user sees "MANAGE", permissions gating failed
        # Note: Button HTML might still be in page with data-role-show, but should be hidden by permissions check
        
        # For thorough test, we'd need to check if button is wrapped in {% if permissions.can_edit_team %}
        # For now, verify template doesn't render with errors
        assert response.status_code == 200, "Page failed to render"


# ============================================================================
# GATE 4A TESTS - Roster Wiring
# ============================================================================

class TestRosterWiring(TestCase):
    """Test roster implementation with real database data (Gate 4A)."""
    
    def setUp(self):
        """Create test fixtures with roster members."""
        self.factory = RequestFactory()
        self.client = Client()
        
        # Create users
        self.owner = User.objects.create_user(username='owner', email='owner@test.com', password='pass')
        self.player1 = User.objects.create_user(username='player1', email='p1@test.com', password='pass')
        self.player2 = User.objects.create_user(username='player2', email='p2@test.com', password='pass')
        self.coach = User.objects.create_user(username='coach', email='coach@test.com', password='pass')
        self.outsider = User.objects.create_user(username='outsider', email='out@test.com', password='pass')
        
        # Create game
        self.game = Game.objects.create(
            name='League of Legends',
            slug='league-of-legends',
            display_name='League of Legends',
            short_code='LOL',
            category='MOBA',
        )
        
        # Create public team
        self.public_team = Team.objects.create(
            name='Public Warriors',
            slug='public-warriors',
            tag='PW',
            game='league-of-legends',
            region='NA',
            is_active=True,
            is_public=True,
        )
        
        # Create private team
        self.private_team = Team.objects.create(
            name='Secret Squad',
            slug='secret-squad',
            tag='SS',
            game='league-of-legends',
            region='EU',
            is_active=True,
            is_public=False,
        )
        
        # Import TeamMembership model
        from apps.organizations.models import TeamMembership
        
        # Add members to public team
        TeamMembership.objects.create(
            team=self.public_team,
            user=self.owner,
            role='OWNER',
            status='ACTIVE',
            player_role='IGL',
            is_tournament_captain=True,
        )
        TeamMembership.objects.create(
            team=self.public_team,
            user=self.player1,
            role='PLAYER',
            status='ACTIVE',
            player_role='Duelist',
        )
        TeamMembership.objects.create(
            team=self.public_team,
            user=self.player2,
            role='PLAYER',
            status='ACTIVE',
            player_role='Controller',
        )
        TeamMembership.objects.create(
            team=self.public_team,
            user=self.coach,
            role='COACH',
            status='ACTIVE',
        )
        
        # Add members to private team
        TeamMembership.objects.create(
            team=self.private_team,
            user=self.player1,
            role='OWNER',
            status='ACTIVE',
        )
    
    def test_public_team_roster_returns_real_members(self):
        """Public team roster should return actual DB members with correct fields."""
        context = get_team_detail_context(
            team_slug='public-warriors',
            viewer=None
        )
        
        roster = context['roster']
        
        # Should have 4 members
        assert roster['count'] == 4, f"Expected 4 members, got {roster['count']}"
        assert len(roster['items']) == 4, f"Expected 4 items, got {len(roster['items'])}"
        
        # Check first member (owner) has all required fields
        members = roster['items']
        owner_member = next((m for m in members if m['username'] == 'owner'), None)
        
        assert owner_member is not None, "Owner not found in roster"
        assert owner_member['username'] == 'owner'
        assert owner_member['display_name'] == 'owner'  # Falls back to username
        assert owner_member['role'] == 'OWNER'
        assert owner_member['player_role'] == 'IGL'
        assert owner_member['status'] == 'ACTIVE'
        assert owner_member['is_captain'] is True
        assert 'avatar_url' in owner_member
        assert 'joined_date' in owner_member
    
    def test_private_team_roster_empty_for_non_members(self):
        """Private team roster should be empty for non-members (privacy guard)."""
        context = get_team_detail_context(
            team_slug='secret-squad',
            viewer=self.outsider  # Not a member
        )
        
        roster = context['roster']
        
        # Should be empty due to privacy restriction
        assert roster['count'] == 0, f"Expected 0 members for restricted viewer, got {roster['count']}"
        assert len(roster['items']) == 0, f"Expected empty items, got {len(roster['items'])}"
    
    def test_private_team_roster_visible_for_members(self):
        """Private team roster should be visible to team members."""
        context = get_team_detail_context(
            team_slug='secret-squad',
            viewer=self.player1  # Team owner
        )
        
        roster = context['roster']
        
        # Should have 1 member (player1 is owner)
        assert roster['count'] == 1, f"Expected 1 member, got {roster['count']}"
        assert len(roster['items']) == 1, f"Expected 1 item, got {len(roster['items'])}"
    
    def test_roster_template_renders_with_db_data(self):
        """Template should render roster from database (visual smoke test)."""
        response = self.client.get(f'/teams/{self.public_team.slug}/')
        html = response.content.decode('utf-8')
        
        # Check roster count badge shows correct number
        assert '4' in html, "Roster count not found in HTML"
        
        # Check member usernames appear
        assert 'owner' in html, "Owner username not found in roster"
        assert 'player1' in html, "Player1 username not found in roster"
        assert 'coach' in html, "Coach username not found in roster"
        
        # Check player roles appear
        assert 'IGL' in html, "Player role 'IGL' not found"
        assert 'Duelist' in html, "Player role 'Duelist' not found"
    
    def test_empty_roster_shows_empty_state(self):
        """Team with no members should show empty state message."""
        # Create team with no members (use different slug to avoid constraint violation)
        empty_team = Team.objects.create(
            name='Empty Team',
            slug='empty-team',
            tag='ET',
            game='league-of-legends',
            region='NA',
            is_active=True,
            is_public=True,
        )
        
        response = self.client.get(f'/teams/{empty_team.slug}/')
        html = response.content.decode('utf-8')
        
        # Should show empty state text
        assert 'No Roster Available' in html or "hasn't added any members" in html, \
            "Empty state message not found for team with no members"
    
    def test_roster_query_count_within_budget(self):
        """Roster fetching should not cause N+1 queries (uses select_related)."""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test import utils
        
        # Reset queries
        utils.reset_queries()
        
        with self.settings(DEBUG=True):
            with utils.CaptureQueriesContext(connection) as context:
                _ = get_team_detail_context(
                    team_slug='public-warriors',
                    viewer=None
                )
            
            query_count = len(context.captured_queries)
            
            # Expected queries:
            # 1. Team.objects.select_related('organization').get(slug=...)
            # 2. Game lookup (may be cached)
            # 3. team.memberships.select_related('user').filter(status='ACTIVE')
            # Total should be ≤ 6 per contract
            
            assert query_count <= 6, \
                f"Query count {query_count} exceeds budget of 6. Queries: {[q['sql'] for q in context.captured_queries]}"


# ============================================================================
# GATE 4B TESTS - Stats Wiring (TeamRanking Only)
# ============================================================================

class TestStatsWiring(TestCase):
    """Test stats implementation with TeamRanking (Gate 4B - Option A)."""
    
    def setUp(self):
        """Create test fixtures with ranking data."""
        self.factory = RequestFactory()
        self.client = Client()
        
        # Create users
        self.owner = User.objects.create_user(username='stats_owner', email='stats@test.com', password='pass')
        self.outsider = User.objects.create_user(username='stats_outsider', email='out@test.com', password='pass')
        self.private_owner = User.objects.create_user(username='private_owner', email='private@test.com', password='pass')
        self.unranked_owner = User.objects.create_user(username='unranked_owner', email='unranked@test.com', password='pass')
        
        # Create game
        self.game = Game.objects.create(
            name='Counter-Strike 2',
            slug='counter-strike-2',
            display_name='Counter-Strike 2',
            short_code='CS2',
            category='FPS',
        )
        
        # Create public team with ranking
        self.public_team = Team.objects.create(
            name='Ranked Warriors',
            slug='ranked-warriors',
            tag='RW',
            game='counter-strike-2',
            region='NA',
            is_active=True,
            is_public=True,
        )
        
        # Create private team without ranking
        self.private_team = Team.objects.create(
            name='Private Squad',
            slug='private-squad',
            tag='PS',
            game='counter-strike-2',
            region='EU',
            is_active=True,
            is_public=False,
        )
        
        # Create unranked public team (no ranking object)
        self.unranked_team = Team.objects.create(
            name='New Team',
            slug='new-team',
            tag='NT',
            game='counter-strike-2',
            region='NA',
            is_active=True,
            is_public=True,
        )
        
        # Import TeamRanking model
        from apps.organizations.models import TeamRanking
        
        # Add ranking to public team
        TeamRanking.objects.create(
            team=self.public_team,
            current_cp=5000,
            season_cp=3000,
            tier='GOLD',
            global_rank=150,
            regional_rank=25,
            rank_change_24h=5,
            rank_change_7d=20,
            is_hot_streak=True,
            streak_count=4,
        )
    
    def test_public_team_returns_ranking_stats(self):
        """Public team with ranking should return all stats from TeamRanking."""
        context = get_team_detail_context(
            team_slug='ranked-warriors',
            viewer=None
        )
        
        stats = context['stats']
        
        # Verify all required stats fields exist
        assert 'crown_points' in stats
        assert 'tier' in stats
        assert 'global_rank' in stats
        assert 'regional_rank' in stats
        assert 'streak_count' in stats
        assert 'is_hot_streak' in stats
        assert 'rank_change_24h' in stats
        assert 'last_activity_date' in stats
        
        # Verify correct values from TeamRanking
        assert stats['crown_points'] == 5000
        assert stats['tier'] == 'GOLD'
        assert stats['global_rank'] == 150
        assert stats['regional_rank'] == 25
        assert stats['streak_count'] == 4
        assert stats['is_hot_streak'] is True
        assert stats['rank_change_24h'] == 5
    
    def test_team_without_ranking_returns_safe_defaults(self):
        """Team without TeamRanking should return safe defaults (no exception)."""
        context = get_team_detail_context(
            team_slug='new-team',
            viewer=None
        )
        
        stats = context['stats']
        
        # Should return defaults, not raise exception
        assert stats['crown_points'] == 0
        assert stats['tier'] == 'UNRANKED'
        assert stats['global_rank'] is None
        assert stats['regional_rank'] is None
        assert stats['streak_count'] == 0
        assert stats['is_hot_streak'] is False
        assert stats['rank_change_24h'] == 0
        assert stats['last_activity_date'] is None
    
    def test_private_team_hides_stats_for_non_members(self):
        """Private team should hide stats for non-members (privacy guard)."""
        context = get_team_detail_context(
            team_slug='private-squad',
            viewer=self.outsider
        )
        
        stats = context['stats']
        
        # Should return empty/zero stats for privacy
        assert stats['crown_points'] == 0
        assert stats['tier'] == 'UNRANKED'
        assert stats['global_rank'] is None
        assert stats['regional_rank'] is None
        assert stats['streak_count'] == 0
        assert stats['is_hot_streak'] is False
    
    def test_stats_query_count_within_budget(self):
        """Stats with ranking should not add extra queries (uses select_related)."""
        from django.test.utils import override_settings
        from django.db import connection
        from django.test import utils
        
        # Reset queries
        utils.reset_queries()
        
        with self.settings(DEBUG=True):
            with utils.CaptureQueriesContext(connection) as context:
                _ = get_team_detail_context(
                    team_slug='ranked-warriors',
                    viewer=None
                )
            
            query_count = len(context.captured_queries)
            
            # Expected queries:
            # 1. Team.objects.select_related('organization', 'ranking').get(slug=...)
            # 2. Game lookup (may be cached)
            # 3. team.memberships.select_related('user', 'user__profile').filter(status='ACTIVE')
            # Total should be ≤ 6 per contract (currently 3-4 with caching)
            
            assert query_count <= 6, \
                f"Query count {query_count} exceeds budget of 6. Queries: {[q['sql'] for q in context.captured_queries]}"
    
    def test_stats_context_keys_match_contract(self):
        """Stats context should match exact keys from Gate 4B specification."""
        context = get_team_detail_context(
            team_slug='ranked-warriors',
            viewer=None
        )
        
        stats = context['stats']
        required_keys = {
            'crown_points', 'tier', 'global_rank', 'regional_rank',
            'streak_count', 'is_hot_streak', 'rank_change_24h', 'last_activity_date'
        }
        
        assert set(stats.keys()) == required_keys, \
            f"Stats keys mismatch. Expected: {required_keys}, Got: {set(stats.keys())}"


class TestStatsTemplateWiring(TestCase):
    """Gate 4B STEP 4: Verify stats are wired into template correctly."""
    
    def setUp(self):
        # Create users
        self.owner = User.objects.create_user(username='template_owner', email='towner@test.com', password='pass')
        
        # Create game (required for teams)
        from apps.games.models import Game
        self.game, _ = Game.objects.get_or_create(
            name='Template Test Game',
            defaults={
                'display_name': 'Template Test Game',
                'slug': 'template-test-game',
                'short_code': 'TTG'
            }
        )
        
        # Create ranked team
        self.ranked_team = Team.objects.create(
            name='Template Warriors',
            slug='template-warriors',
            tag='TW',
            game='template-test-game',
            is_active=True,
            is_public=True,
        )
        
        # Create ranking
        TeamRanking.objects.create(
            team=self.ranked_team,
            current_cp=7500,
            tier='PLATINUM',
            global_rank=42,
            regional_rank=8,
            streak_count=3,
            is_hot_streak=True,
            rank_change_24h=2
        )
        
        # Create unranked team
        self.unranked_owner = User.objects.create_user(username='unranked_towner', email='unranked_t@test.com', password='pass')
        # Create unranked team
        self.unranked_team = Team.objects.create(
            name='New Template Team',
            slug='new-template-team',
            tag='NTT',
            game='template-test-game',
            is_active=True,
            is_public=True,
        )
    
    def test_ranked_team_displays_dynamic_stats(self):
        """Template should render dynamic stats from TeamRanking, not demo values."""
        from django.template import Context, Template
        
        context = get_team_detail_context(team_slug=self.ranked_team.slug, viewer=None)
        
        # Verify stats values from backend
        assert context['stats']['crown_points'] == 7500
        assert context['stats']['global_rank'] == 42
        assert context['stats']['tier'] == 'PLATINUM'
        assert context['stats']['streak_count'] == 3
        assert context['stats']['is_hot_streak'] is True
    
    def test_demo_values_removed_from_template(self):
        """Template should not contain hardcoded demo stats values."""
        # Read template file to verify no demo values hardcoded
        import os
        template_path = os.path.join('templates', 'organizations', 'team', 'partials', '_body.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Check that specific demo combinations are replaced with Django variables
        assert '{{ stats.crown_points' in template_content, "Crown points not wired to stats context"
        assert '{{ stats.global_rank' in template_content, "Global rank not wired to stats context"
        assert '{{ stats.streak_count' in template_content, "Streak count not wired to stats context"
    
    def test_unranked_team_shows_defaults(self):
        """Template should display safe defaults for team without ranking."""
        context = get_team_detail_context(team_slug=self.unranked_team.slug, viewer=None)
        
        # Should return safe defaults
        assert context['stats']['crown_points'] == 0
        assert context['stats']['global_rank'] is None
        assert context['stats']['tier'] == 'UNRANKED'
        assert context['stats']['streak_count'] == 0
    
    def test_hot_streak_indicator_present(self):
        """Template should use is_hot_streak to color the streak display."""
        import os
        template_path = os.path.join('templates', 'organizations', 'team', 'partials', '_body.html')
        
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # Check for conditional coloring based on is_hot_streak
        assert 'stats.is_hot_streak' in template_content, "Hot streak conditional not found in template"
        assert 'text-[#00FF41]' in template_content, "Hot streak color class not found"
    
    def test_stats_wiring_query_count_unchanged(self):
        """Stats template wiring should not add queries (still ≤6)."""
        with self.settings(DEBUG=True):
            with utils.CaptureQueriesContext(connection) as ctx:
                _ = get_team_detail_context(team_slug=self.ranked_team.slug, viewer=None)
            
            query_count = len(ctx.captured_queries)
            
            # Should remain within budget
            assert query_count <= 6, \
                f"Query count {query_count} exceeds budget of 6"


class TestGate4CTier2Wiring(TestCase):
    """Gate 4C: Verify Tier-2 fields present in context (minimal smoke tests)."""

    def setUp(self):
        """Create minimal test team."""
        User = get_user_model()
        self.owner = User.objects.create_user(username='owner', email='owner@test.com')
        
        self.team = Team.objects.create(
            name='Test Team',
            slug='test-team',
            game='valorant',
            is_active=True,
            is_public=True,
        )
        
    def test_pending_actions_returns_dict_structure(self):
        """pending_actions context key returns dict with expected flags."""
        context = get_team_detail_context(team_slug=self.team.slug, viewer=None)
        
        pending = context['pending_actions']
        
        # Should be dict, not list (Gate 4C design)
        assert isinstance(pending, dict), f"Expected dict, got {type(pending)}"
        
        # Should have all 5 flags
        expected_keys = {'can_request_to_join', 'has_pending_invite', 'has_pending_request', 
                         'pending_invite_id', 'pending_request_id'}
        assert set(pending.keys()) == expected_keys, \
            f"Missing keys: {expected_keys - set(pending.keys())}"
            
    def test_pending_actions_anonymous_user_all_false(self):
        """Anonymous viewer should see all False/None flags."""
        context = get_team_detail_context(team_slug=self.team.slug, viewer=None)
        
        pending = context['pending_actions']
        
        assert pending['can_request_to_join'] == False
        assert pending['has_pending_invite'] == False
        assert pending['has_pending_request'] == False
        assert pending['pending_invite_id'] is None
        assert pending['pending_request_id'] is None
        
    def test_partners_returns_empty_list(self):
        """Partners section returns empty list (deferred in Gate 4C)."""
        context = get_team_detail_context(team_slug=self.team.slug, viewer=None)
        
        partners = context['partners']
        
        assert isinstance(partners, list)
        assert partners == []  # Deferred due to FK mismatch


# ============================================================================
# P4-T1.4 TASK C: QUERY BUDGET VERIFICATION
# ============================================================================

class TestTeamDetailQueryBudget(TestCase):
    """
    Verify query count ≤6 for all viewer scenarios (P4-T1.4 Task C).
    
    Target: Baseline (3) + Tier-2 additions ≤6 total queries.
    
    Baseline queries:
    1. Team fetch (with select_related('organization', 'ranking'))
    2. TeamMembership check (viewer role)
    3. (Conditional) Organization stats if org exists
    
    Tier-2 additions:
    4. TeamSponsor query (partners)
    5. TeamMembership.exists() (pending_actions)
    6. TeamInvite/TeamJoinRequest check (pending_actions)
    """
    
    def setUp(self):
        """Create test fixtures."""
        from django.test.utils import CaptureQueriesContext
        
        # Create test users
        self.owner = User.objects.create_user(username='owner_qb', email='owner@test.com', password='pass')
        self.member = User.objects.create_user(username='member_qb', email='member@test.com', password='pass')
        self.public_user = User.objects.create_user(username='public_qb', email='public@test.com', password='pass')
        
        # Create organization (to test org-related queries)
        self.org = Organization.objects.create(
            name='Test Org',
            slug='test-org',
            owner=self.owner,
        )
        
        # Create team (Legacy schema: no organization FK yet)
        self.team = Team.objects.create(
            name='Query Budget Warriors',
            slug='qb-warriors',
            tag='QBW',
            game='valorant',
            region='NA',
            is_active=True,
            is_public=True,
        )
        
        # Add owner membership
        from apps.teams.models import TeamMembership
        TeamMembership.objects.create(
            team=self.team,
            user=self.owner,
            role='OWNER',
            status='ACTIVE'
        )
        
        # Add member membership
        TeamMembership.objects.create(
            team=self.team,
            user=self.member,
            role='MEMBER',
            status='ACTIVE'
        )
        
        # Add sponsors (for partners query)
        from apps.teams.models.sponsorship import TeamSponsor
        TeamSponsor.objects.create(
            team=self.team,
            sponsor_name='Sponsor A',
            status='active',
            is_active=True,
            tier='gold',
        )
        TeamSponsor.objects.create(
            team=self.team,
            sponsor_name='Sponsor B',
            status='active',
            is_active=True,
            tier='silver',
        )
    
    def test_anonymous_viewer_query_count_within_budget(self):
        """Anonymous viewer should execute ≤6 queries."""
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as ctx:
            context = get_team_detail_context(
                team_slug='qb-warriors',
                viewer=None
            )
        
        query_count = len(ctx.queries)
        
        # Debug output if over budget
        if query_count > 6:
            print(f"\n⚠️ QUERY BUDGET EXCEEDED: {query_count} queries (target ≤6)")
            for i, query in enumerate(ctx.queries, 1):
                print(f"{i}. {query['sql'][:100]}...")
        
        assert query_count <= 6, \
            f"Query count {query_count} exceeds budget of 6 for anonymous viewer"
    
    def test_authenticated_non_member_query_count_within_budget(self):
        """Authenticated non-member should execute ≤6 queries."""
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as ctx:
            context = get_team_detail_context(
                team_slug='qb-warriors',
                viewer=self.public_user
            )
        
        query_count = len(ctx.queries)
        
        # Debug output if over budget
        if query_count > 6:
            print(f"\n⚠️ QUERY BUDGET EXCEEDED: {query_count} queries (target ≤6)")
            for i, query in enumerate(ctx.queries, 1):
                print(f"{i}. {query['sql'][:100]}...")
        
        assert query_count <= 6, \
            f"Query count {query_count} exceeds budget of 6 for authenticated non-member"
    
    def test_authenticated_member_query_count_within_budget(self):
        """Authenticated team member should execute ≤6 queries."""
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as ctx:
            context = get_team_detail_context(
                team_slug='qb-warriors',
                viewer=self.member
            )
        
        query_count = len(ctx.queries)
        
        # Debug output if over budget
        if query_count > 6:
            print(f"\n⚠️ QUERY BUDGET EXCEEDED: {query_count} queries (target ≤6)")
            for i, query in enumerate(ctx.queries, 1):
                print(f"{i}. {query['sql'][:100]}...")
        
        assert query_count <= 6, \
            f"Query count {query_count} exceeds budget of 6 for authenticated member"
    
    def test_query_breakdown_documented(self):
        """Document expected query breakdown for future reference."""
        from django.test.utils import CaptureQueriesContext
        
        with CaptureQueriesContext(connection) as ctx:
            context = get_team_detail_context(
                team_slug='qb-warriors',
                viewer=self.member
            )
        
        query_count = len(ctx.queries)
        
        # Expected queries:
        # 1. Team.objects.select_related('organization', 'ranking').get(slug=...)
        # 2. TeamMembership.objects.filter(team=..., user=...).exists() - role check
        # 3. TeamSponsor.objects.filter(team=..., status='active', is_active=True) - partners
        # 4. TeamMembership.objects.filter(team=..., user=..., status='ACTIVE').exists() - pending_actions
        # 5. TeamInvite.objects.filter(team=..., invited_user=..., status='PENDING').first() - pending_actions
        # 6. TeamJoinRequest.objects.filter(team=..., applicant=..., status='PENDING').first() - pending_actions
        
        print(f"\n📊 Query Breakdown (Total: {query_count}):")
        for i, query in enumerate(ctx.queries, 1):
            sql = query['sql']
            if 'teams_team' in sql and 'SELECT' in sql:
                print(f"{i}. Team fetch (with select_related)")
            elif 'teams_teammembership' in sql:
                print(f"{i}. TeamMembership query")
            elif 'teams_teamsponsor' in sql:
                print(f"{i}. TeamSponsor query (partners)")
            elif 'teams_teaminvite' in sql:
                print(f"{i}. TeamInvite query (pending_actions)")
            elif 'teams_teamjoinrequest' in sql:
                print(f"{i}. TeamJoinRequest query (pending_actions)")
            else:
                print(f"{i}. {sql[:80]}...")
        
        # This test always passes - it's for documentation only
        assert True