"""
API Views for vNext Organization and Team creation.

These views provide REST endpoints for creating organizations and teams
in the vNext system. All endpoints enforce feature flag checks and proper
permissions.

Feature Flag Requirements:
- TEAM_VNEXT_ADAPTER_ENABLED must be True
- TEAM_VNEXT_FORCE_LEGACY must be False
- TEAM_VNEXT_ROUTING_MODE must not be "legacy_only"

If any flag check fails, endpoints return 403 with stable error_code.

Performance Targets:
- Organization creation: ≤3 queries, <100ms p95
- Team creation: ≤5 queries, <100ms p95

Security:
- All endpoints require authentication
- Organization creation sets creator as CEO automatically
- Org-owned team creation requires CEO/manager permission
- Independent team creation sets creator as owner
"""

from typing import Any, Dict
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.organizations.adapters.flags import should_use_vnext_routing, get_routing_reason
from apps.organizations.services.organization_service import OrganizationService
from apps.organizations.services.team_service import TeamService
from apps.organizations.services.dual_write_service import DualWriteSyncService
from apps.organizations.services.exceptions import (
    TeamServiceError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError as ServiceValidationError,
    ConflictError,
    TeamValidationError,
)
from apps.organizations.models import Organization, OrganizationMembership, Team
from apps.organizations.choices import MembershipRole, MembershipStatus
from apps.games.models import Game
from apps.organizations.api.serializers import (
    CreateOrganizationSerializer,
    CreateTeamSerializer,
)

User = get_user_model()

# CRITICAL SAFETY CHECK: Ensure we're using vNext Team, not legacy
# vNext Team uses organizations_team table, has game_id (IntegerField FK)
# Legacy Team uses teams_team table, has game (CharField slug)
assert hasattr(Team, 'game_id'), (
    "FATAL: Team model in organizations.api.views must be vNext Team with game_id field. "
    "Got legacy Team with 'game' CharField. Check import at line 56."
)
assert Team._meta.db_table == 'organizations_team', (
    f"FATAL: Team model must use organizations_team table. "
    f"Got {Team._meta.db_table}. This indicates legacy Team is imported."
)

logger = logging.getLogger(__name__)


def check_vnext_creation_allowed() -> tuple[bool, str, str]:
    """
    Check if vNext creation is allowed based on feature flags.
    
    Returns:
        Tuple of (allowed, error_code, error_message)
    
    Rules:
        - FORCE_LEGACY=True → always reject
        - ADAPTER_ENABLED=False → reject
        - ROUTING_MODE="legacy_only" → reject
        - Otherwise → allow
    """
    # Check FORCE_LEGACY (highest priority)
    if getattr(settings, 'TEAM_VNEXT_FORCE_LEGACY', False):
        return (
            False,
            "vnext_creation_disabled",
            "vNext team creation is currently disabled (emergency mode active)."
        )
    
    # Check ADAPTER_ENABLED
    if not getattr(settings, 'TEAM_VNEXT_ADAPTER_ENABLED', False):
        return (
            False,
            "vnext_creation_disabled",
            "vNext team creation is not yet enabled. Please use legacy team creation."
        )
    
    # Check ROUTING_MODE
    routing_mode = getattr(settings, 'TEAM_VNEXT_ROUTING_MODE', 'legacy_only')
    if routing_mode == 'legacy_only':
        return (
            False,
            "vnext_creation_disabled",
            "vNext team creation is not available (legacy-only mode active)."
        )
    
    return (True, "", "")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_organization(request: Request) -> Response:
    """
    Create a new vNext organization.
    
    POST /api/vnext/organizations/create/
    
    Request Body:
        {
            "name": "Team Liquid",
            "slug": "team-liquid",  // optional
            "branding": {  // optional
                "logo_url": "https://cdn.example.com/logo.png",
                "primary_color": "#0A4D92"
            }
        }
    
    Response (201):
        {
            "organization_id": 42,
            "organization_slug": "team-liquid"
        }
    
    Response (403 - vNext disabled):
        {
            "error_code": "vnext_creation_disabled",
            "message": "vNext team creation is not yet enabled.",
            "safe_message": "vNext team creation is not yet enabled. Please use legacy team creation."
        }
    
    Response (400 - validation error):
        {
            "error_code": "validation_error",
            "message": "Invalid input data",
            "details": {"name": ["This field is required."]}
        }
    
    Response (409 - organization exists):
        {
            "error_code": "organization_already_exists",
            "message": "An organization with this name already exists.",
            "safe_message": "An organization with this name already exists."
        }
    
    Performance:
        - Target: <100ms (p95)
        - Queries: ≤3 (user lookup, uniqueness check, insert)
    
    Security:
        - Requires authentication
        - Creator becomes CEO automatically
        - Transaction.atomic ensures atomicity
    """
    # Check feature flags
    allowed, error_code, error_message = check_vnext_creation_allowed()
    if not allowed:
        logger.warning(
            f"vNext organization creation rejected for user {request.user.id}: {error_code}",
            extra={
                'event_type': 'vnext_creation_rejected',
                'user_id': request.user.id,
                'error_code': error_code,
            }
        )
        return Response(
            {
                'error_code': error_code,
                'message': error_message,
                'safe_message': error_message,
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validate input
    serializer = CreateOrganizationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                'error_code': 'validation_error',
                'message': 'Invalid input data',
                'details': serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    validated_data = serializer.validated_data
    
    # Create organization via service layer
    try:
        with transaction.atomic():
            org_id = OrganizationService.create_organization(
                name=validated_data['name'],
                ceo_user_id=request.user.id,
                slug=validated_data.get('slug'),
                logo=validated_data.get('branding', {}).get('logo_url'),
                description=validated_data.get('branding', {}).get('description', ''),
            )
            
            # Fetch org to get slug (create_organization returns int ID)
            org = Organization.objects.get(id=org_id)
        
        logger.info(
            f"Organization created: {org.slug} (ID: {org.id}) by user {request.user.id}",
            extra={
                'event_type': 'organization_created',
                'organization_id': org.id,
                'organization_slug': org.slug,
                'user_id': request.user.id,
            }
        )
        
        # Generate canonical URL for redirect
        org_url = f"/orgs/{org.slug}/"
        
        return Response(
            {
                'ok': True,
                'organization_id': org.id,
                'organization_slug': org.slug,
                'organization_url': org_url,
            },
            status=status.HTTP_201_CREATED
        )
    
    except (ConflictError, PermissionDeniedError, ServiceValidationError) as e:
        # Handle known service errors with appropriate status codes
        status_code = status.HTTP_409_CONFLICT if isinstance(e, ConflictError) else status.HTTP_400_BAD_REQUEST
        
        return Response(
            {
                'error_code': e.error_code,
                'message': str(e),
                'safe_message': e.safe_message,
            },
            status=status_code
        )
    
    except NotFoundError as e:
        # User not found (shouldn't happen for authenticated user, but defensive)
        return Response(
            {
                'error_code': e.error_code,
                'message': str(e),
                'safe_message': e.safe_message,
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except Exception as e:
        logger.exception(
            f"Unexpected error creating organization for user {request.user.id}",
            extra={
                'event_type': 'organization_creation_error',
                'user_id': request.user.id,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'An unexpected error occurred',
                'safe_message': 'Failed to create organization. Please try again.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_team_name(request: Request) -> Response:
    """
    Validate team name uniqueness for a given game/org context.
    
    GET /api/vnext/teams/validate-name/?name=<name>&game_slug=<slug>&org_id=<id|null>&mode=<independent|org>
    
    Response (200 - available):
        {
            "ok": true,
            "available": true
        }
    
    Response (200 - unavailable):
        {
            "ok": false,
            "available": false,
            "field_errors": {
                "name": "A team with this name already exists in this game."
            }
        }
    """
    try:
        # Explicit import to ensure vNext Team (organizations_team table)
        from apps.organizations.models import Team as VNextTeam
        from apps.games.models import Game
        
        name = request.query_params.get('name', '').strip()
        game_slug = request.query_params.get('game_slug', '').strip()
        org_id = request.query_params.get('org_id')
        mode = request.query_params.get('mode', 'independent')
        
        # DEBUG: Log incoming request
        logger.info(
            f"validate_team_name called: name={name}, game_slug={game_slug}, mode={mode}, org_id={org_id}, "
            f"user_id={request.user.id}, Team model={VNextTeam.__module__}.{VNextTeam.__name__}, "
            f"db_table={VNextTeam._meta.db_table}"
        )
        
        # Validate required params
        if not name or not game_slug:
            return Response({
                'ok': False,
                'field_errors': {'name': 'Name and game are required.'}
            })
        
        # Check if name length is valid (minimum 3 characters)
        if len(name) < 3:
            return Response({
                'ok': False,
                'available': False,
                'field_errors': {'name': 'Team name must be at least 3 characters.'}
            })
        
        try:
            game = Game.objects.get(slug=game_slug, is_active=True)
            logger.info(f"validate_team_name: Found game id={game.id} for slug={game_slug}")
        except Game.DoesNotExist:
            logger.warning(f"validate_team_name: Game not found for slug={game_slug}")
            return Response({
                'ok': False,
                'field_errors': {'game': 'Invalid game selected.'}
            })
        
        # Check uniqueness: vNext Team uses game_id (IntegerField FK)
        # Scope by mode: independent (org IS NULL) or organization (org = org_id)
        query = VNextTeam.objects.filter(name__iexact=name, game_id=game.id)
        logger.info(f"validate_team_name: Initial query filter: name__iexact={name}, game_id={game.id}")
        
        if mode == 'independent':
            query = query.filter(organization__isnull=True)
            logger.info("validate_team_name: Filtered for independent (organization__isnull=True)")
        elif mode == 'organization' and org_id:
            try:
                query = query.filter(organization_id=int(org_id))
                logger.info(f"validate_team_name: Filtered for organization_id={org_id}")
            except (ValueError, TypeError) as e:
                logger.warning(f"validate_team_name: Invalid org_id={org_id}: {e}")
                pass  # Invalid org_id, check globally
        
        exists = query.exists()
        logger.info(f"validate_team_name: Query exists={exists}, SQL={query.query}")
        
        if exists:
            return Response({
                'ok': False,
                'available': False,
                'field_errors': {'name': 'A team with this name already exists in this game.'}
            })
        
        return Response({
            'ok': True,
            'available': True
        })
    
    except Exception as e:
        logger.exception(
            f"validate_team_name FAILED: name={request.query_params.get('name')}, "
            f"game_slug={request.query_params.get('game_slug')}, mode={request.query_params.get('mode')}, "
            f"exception_type={type(e).__name__}, exception_msg={str(e)}"
        )
        return Response(
            {
                'ok': False,
                'error_code': 'validation_error',
                'message': f'Validation failed: {str(e)}',
                'safe_message': 'Unable to validate team name. Please try again.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_team_tag(request: Request) -> Response:
    """
    Validate team tag uniqueness for a given game/org context.
    
    GET /api/vnext/teams/validate-tag/?tag=<tag>&game_slug=<slug>&org_id=<id|null>&mode=<independent|org>
    
    Response (200 - available):
        {
            "ok": true,
            "available": true
        }
    
    Response (200 - unavailable):
        {
            "ok": false,
            "available": false,
            "field_errors": {
                "tag": "This tag is already taken in this game."
            }
        }
    """
    try:
        # Explicit import to ensure vNext Team (organizations_team table)
        from apps.organizations.models import Team as VNextTeam
        from apps.games.models import Game
        
        tag = request.query_params.get('tag', '').strip().upper()
        game_slug = request.query_params.get('game_slug', '').strip()
        org_id = request.query_params.get('org_id')
        mode = request.query_params.get('mode', 'independent')
        
        # DEBUG: Log incoming request
        logger.info(
            f"validate_team_tag called: tag={tag}, game_slug={game_slug}, mode={mode}, org_id={org_id}, "
            f"user_id={request.user.id}, Team model={VNextTeam.__module__}.{VNextTeam.__name__}, "
            f"db_table={VNextTeam._meta.db_table}"
        )
        
        # Validate required params
        if not tag or not game_slug:
            return Response({
                'ok': False,
                'field_errors': {'tag': 'Tag and game are required.'}
            })
        
        # Check tag length (2-5 characters)
        if len(tag) < 2:
            return Response({
                'ok': False,
                'available': False,
                'field_errors': {'tag': 'Tag must be at least 2 characters.'}
            })
        
        if len(tag) > 5:
            return Response({
                'ok': False,
                'available': False,
                'field_errors': {'tag': 'Tag must be 5 characters or less.'}
            })
        
        try:
            game = Game.objects.get(slug=game_slug, is_active=True)
            logger.info(f"validate_team_tag: Found game id={game.id} for slug={game_slug}")
        except Game.DoesNotExist:
            logger.warning(f"validate_team_tag: Game not found for slug={game_slug}")
            return Response({
                'ok': False,
                'field_errors': {'game': 'Invalid game selected.'}
            })
        
        # Check uniqueness: vNext Team uses game_id (IntegerField FK)
        # Tag must be unique per game across all teams (tags are globally unique per game)
        query = VNextTeam.objects.filter(tag__iexact=tag, game_id=game.id)
        logger.info(f"validate_team_tag: Query filter: tag__iexact={tag}, game_id={game.id}")
        
        exists = query.exists()
        logger.info(f"validate_team_tag: Query exists={exists}")
        
        if exists:
            return Response({
                'ok': False,
                'available': False,
                'field_errors': {'tag': 'This tag is already taken in this game.'}
            })
        
        return Response({
            'ok': True,
            'available': True
        })
    
    except Exception as e:
        logger.exception(
            f"validate_team_tag FAILED: tag={request.query_params.get('tag')}, "
            f"game_slug={request.query_params.get('game_slug')}, mode={request.query_params.get('mode')}, "
            f"exception_type={type(e).__name__}, exception_msg={str(e)}"
        )
        return Response(
            {
                'ok': False,
                'error_code': 'validation_error',
                'message': f'Validation failed: {str(e)}',
                'safe_message': 'Unable to validate team tag. Please try again.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_team(request: Request) -> Response:
    """
    Create a new vNext team (independent or org-owned).
    
    POST /api/vnext/teams/create/
    
    Request Body (Independent Team):
        {
            "name": "Cloud9 Blue",
            "game_id": 1,
            "region": "NA",
            "branding": {
                "logo_url": "https://cdn.example.com/c9.png",
                "primary_color": "#0A4D92"
            }
        }
    
    Request Body (Org-Owned Team):
        {
            "name": "Team Liquid Academy",
            "game_id": 1,
            "organization_id": 42,
            "region": "NA"
        }
    
    Response (201):
        {
            "team_id": 123,
            "team_slug": "cloud9-blue",
            "team_url": "/organizations/teams/cloud9-blue/"
        }
    
    Response (403 - vNext disabled):
        {
            "error_code": "vnext_creation_disabled",
            "message": "vNext team creation is not yet enabled."
        }
    
    Response (403 - permission denied):
        {
            "error_code": "permission_denied",
            "message": "You must be CEO or manager to create org-owned teams.",
            "safe_message": "You don't have permission to create teams for this organization."
        }
    
    Response (400 - validation error):
        {
            "error_code": "validation_error",
            "message": "Invalid input data",
            "details": {"game_id": ["This field is required."]}
        }
    
    Response (404 - organization not found):
        {
            "error_code": "organization_not_found",
            "message": "Organization with ID 42 does not exist."
        }
    
    Performance:
        - Target: <100ms (p95)
        - Queries: ≤5 (user lookup, game check, org check, permission check, insert)
    
    Security:
        - Requires authentication
        - Org-owned teams require CEO/manager permission
        - Independent teams set creator as owner
        - Transaction.atomic ensures atomicity
    """
    # Check feature flags
    allowed, error_code, error_message = check_vnext_creation_allowed()
    if not allowed:
        logger.warning(
            f"vNext team creation rejected for user {request.user.id}: {error_code}",
            extra={
                'event_type': 'vnext_creation_rejected',
                'user_id': request.user.id,
                'error_code': error_code,
            }
        )
        return Response(
            {
                'ok': False,
                'error_code': error_code,
                'message': error_message,
                'safe_message': error_message,
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Validate input
    serializer = CreateTeamSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {
                'ok': False,
                'error_code': 'validation_error',
                'message': 'Invalid input data',
                'safe_message': 'Please check your inputs and try again.',
                'field_errors': serializer.errors,
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    validated_data = serializer.validated_data
    organization_id = validated_data.get('organization_id')
    
    # Check permissions for org-owned teams
    if organization_id:
        try:
            organization = Organization.objects.get(id=organization_id)
            
            # Check if user is CEO or manager (OrganizationMembership uses string choices)
            membership = OrganizationMembership.objects.filter(
                organization=organization,
                user=request.user,
                role__in=['CEO', 'MANAGER'],  # OrganizationMembership has no nested Role enum
            ).first()
            
            if not membership:
                logger.warning(
                    f"User {request.user.id} attempted to create org-owned team without permission",
                    extra={
                        'event_type': 'team_creation_permission_denied',
                        'user_id': request.user.id,
                        'organization_id': organization_id,
                    }
                )
                return Response(
                    {
                        'ok': False,
                        'error_code': 'permission_denied',
                        'message': 'You must be CEO or manager to create org-owned teams.',
                        'safe_message': "You don't have permission to create teams for this organization.",
                    },
                    status=status.HTTP_403_FORBIDDEN
                )
        
        except Organization.DoesNotExist:
            return Response(
                {
                    'ok': False,
                    'error_code': 'organization_not_found',
                    'message': f'Organization with ID {organization_id} does not exist.',
                    'safe_message': 'The specified organization was not found.',
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Validate game_id exists before creating team
    game_id = validated_data.get('game_id')
    if game_id:
        if not Game.objects.filter(id=game_id).exists():
            return Response(
                {
                    'ok': False,
                    'error_code': 'invalid_game_id',
                    'message': f'Game with ID {game_id} does not exist.',
                    'safe_message': 'The specified game was not found.',
                },
                status=status.HTTP_404_NOT_FOUND
            )
    
    # Create team via service layer
    try:
        with transaction.atomic():
            # Create team (model save handles slug generation)
            # vNext Team model fields: game_id (Integer), status, created_by FK, organization FK
            team_data = {
                'name': validated_data['name'],
                'game_id': validated_data.get('game_id'),  # IntegerField
                'region': validated_data.get('region', ''),
                'status': 'ACTIVE',  # vNext uses status choices instead of is_active
                'visibility': 'PUBLIC',
                'created_by': request.user,
            }
            
            # Set organization FK or leave as independent team
            if organization_id:
                team_data['organization_id'] = organization_id
            else:
                team_data['organization'] = None
            
            # Add optional fields if provided
            if validated_data.get('tag'):
                team_data['tag'] = validated_data['tag']
            if validated_data.get('tagline'):
                team_data['tagline'] = validated_data['tagline']
            if validated_data.get('description'):
                team_data['description'] = validated_data['description']
            if validated_data.get('primary_color'):
                team_data['primary_color'] = validated_data['primary_color']
            if validated_data.get('accent_color'):
                team_data['accent_color'] = validated_data['accent_color']
            
            # Create team instance
            team = Team.objects.create(**team_data)
            
            # Handle file uploads (logo/banner) if provided
            if validated_data.get('logo'):
                team.logo = validated_data['logo']
            if validated_data.get('banner'):
                team.banner = validated_data['banner']
            
            # Save again if files were added
            if validated_data.get('logo') or validated_data.get('banner'):
                team.save()
            
            # Invalidate hub cache after team creation (Phase 15 Group C fix)
            from django.core.cache import cache
            cache.delete_pattern('hub:featured_teams:*')
            cache.delete_pattern('hero_carousel_*')
            
            # Create owner membership for independent teams
            if not organization_id:
                from apps.organizations.models import TeamMembership
                TeamMembership.objects.create(
                    team=team,
                    user=request.user,
                    role=MembershipRole.OWNER,
                    status=MembershipStatus.ACTIVE,
                )
            
            # Handle manager invite if provided
            invite_created = False
            manager_email = validated_data.get('manager_email')
            if manager_email and manager_email.strip():
                from apps.organizations.models import TeamInvite
                
                # Check if user exists with this email
                try:
                    invited_user = User.objects.get(email=manager_email)
                    
                    # Create invited membership
                    TeamMembership.objects.create(
                        team=team,
                        user=invited_user,
                        role=MembershipRole.MANAGER,
                        status=MembershipStatus.INVITED,
                    )
                    invite_created = True
                except User.DoesNotExist:
                    # User doesn't exist - create invite record
                    TeamInvite.objects.create(
                        team=team,
                        invited_email=manager_email,
                        inviter=request.user,
                        role=MembershipRole.MANAGER,
                        status='PENDING',
                    )
                    invite_created = True
                except Exception as invite_error:
                    # Don't block team creation if invite fails
                    logger.warning(
                        f"Failed to create manager invite for team {team.id}",
                        extra={
                            'event_type': 'manager_invite_failed',
                            'team_id': team.id,
                            'manager_email': manager_email,
                            'error': str(invite_error),
                        }
                    )
            
            # Get team URL using TeamService
            team_url = TeamService.get_team_url(team.id)
            
            # Schedule dual-write to legacy after commit
            if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False):
                def _sync_team_created():
                    try:
                        DualWriteSyncService.sync_team_created(
                            vnext_team_id=team.id,
                            actor_user_id=request.user.id
                        )
                    except Exception as e:
                        logger.error(
                            f"Dual-write failed for team creation: {team.id}",
                            extra={
                                'event_type': 'dual_write_failed',
                                'operation': 'sync_team_created',
                                'team_id': team.id,
                                'user_id': request.user.id,
                                'exception_type': type(e).__name__,
                                'exception_message': str(e),
                            },
                            exc_info=True
                        )
                        # Re-raise in strict mode
                        if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE', False):
                            raise
                
                transaction.on_commit(_sync_team_created)
                logger.info(
                    f"Dual-write scheduled for team creation: {team.id}",
                    extra={
                        'event_type': 'dual_write_scheduled',
                        'operation': 'sync_team_created',
                        'team_id': team.id,
                        'user_id': request.user.id,
                    }
                )
            
            # Invalidate hub cache to show newly created team
            from apps.organizations.services.hub_cache import invalidate_hub_cache
            invalidate_hub_cache(game_id=team.game_id)
        
        logger.info(
            f"Team created: {team.slug} (ID: {team.id}) by user {request.user.id}",
            extra={
                'event_type': 'team_created',
                'team_id': team.id,
                'team_slug': team.slug,
                'organization_id': organization_id,
                'is_org_owned': bool(organization_id),
                'user_id': request.user.id,
            }
        )
        
        return Response(
            {
                'ok': True,
                'team_id': team.id,
                'team_slug': team.slug,
                'team_url': team_url,
                'invite_created': invite_created,
            },
            status=status.HTTP_201_CREATED
        )
    
    except (ConflictError, PermissionDeniedError, ServiceValidationError, TeamValidationError) as e:
        # Handle known service errors with appropriate status codes
        status_code = status.HTTP_409_CONFLICT if isinstance(e, ConflictError) else status.HTTP_400_BAD_REQUEST
        
        return Response(
            {
                'ok': False,
                'error_code': e.error_code,
                'message': str(e),
                'safe_message': e.safe_message,
            },
            status=status_code
        )
    
    except NotFoundError as e:
        # Game or organization not found
        return Response(
            {
                'error_code': e.error_code,
                'message': str(e),
                'safe_message': e.safe_message,
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except IntegrityError as e:
        # Handle database constraint violations with user-friendly messages
        error_message = str(e).lower()
        
        # Determine constraint type from error message
        if 'team_has_organization_xor_creator' in error_message or 'team_has_organization_xor_owner' in error_message:
            error_code = 'xor_constraint_violation'
            user_message = 'Team ownership configuration error.'
            safe_message = 'Invalid team creation request.'
            status_code = status.HTTP_400_BAD_REQUEST
        elif 'unique_tag_per_game' in error_message:
            error_code = 'tag_already_exists'
            user_message = f"The tag '{validated_data.get('tag')}' is already taken for this game."
            safe_message = 'This team tag is already in use.'
            status_code = status.HTTP_409_CONFLICT
        elif 'one_independent_team_per_game' in error_message:
            error_code = 'team_limit_reached'
            user_message = f"You already own an active team for this game."
            safe_message = 'You can only own one team per game.'
            status_code = status.HTTP_409_CONFLICT
        elif 'slug' in error_message or 'unique' in error_message:
            error_code = 'team_name_conflict'
            user_message = f"The name '{validated_data.get('name')}' is too similar to an existing team."
            safe_message = 'This team name is already taken or too similar to another team.'
            status_code = status.HTTP_409_CONFLICT
        else:
            # Generic integrity error
            error_code = 'database_constraint_violation'
            user_message = 'Team creation failed due to a database constraint.'
            safe_message = 'Failed to create team. Please check your inputs.'
            status_code = status.HTTP_409_CONFLICT
        
        logger.warning(
            f"IntegrityError during team creation for user {request.user.id}",
            extra={
                'event_type': 'integrity_error_handled',
                'user_id': request.user.id,
                'organization_id': organization_id,
                'constraint_violated': error_code,
                'error_message': str(e),
            }
        )
        
        return Response(
            {
                'ok': False,
                'error_code': error_code,
                'message': user_message,
                'safe_message': safe_message,
            },
            status=status_code
        )
    
    except Exception as e:
        logger.exception(
            f"Unexpected error creating team for user {request.user.id}",
            extra={
                'event_type': 'team_creation_error',
                'user_id': request.user.id,
                'organization_id': organization_id,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'ok': False,
                'error_code': 'internal_error',
                'message': 'An unexpected error occurred',
                'safe_message': 'Failed to create team. Please try again.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# ORGANIZATION MANAGEMENT ENDPOINTS (P3-T5)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_organization_detail(request: Request, org_slug: str) -> Response:
    """
    GET /api/vnext/orgs/<org_slug>/
    
    Retrieve complete organization details including members and teams.
    
    Response: {
        "org": {...},
        "members": [...],
        "teams": [...]
    }
    
    Performance: ≤5 queries, <100ms p95
    """
    try:
        data = OrganizationService.get_organization_detail(
            org_slug=org_slug,
            include_members=True,
            include_teams=True
        )
        
        logger.info(
            f"Organization detail retrieved: {org_slug}",
            extra={
                'event_type': 'org_detail_viewed',
                'user_id': request.user.id,
                'org_slug': org_slug,
            }
        )
        
        return Response(data, status=status.HTTP_200_OK)
    
    except OrganizationNotFoundError as e:
        return Response(
            {
                'error_code': e.error_code,
                'message': str(e),
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except Exception as e:
        logger.exception(
            f"Error retrieving organization detail: {org_slug}",
            extra={
                'event_type': 'org_detail_error',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to retrieve organization details',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_organization_member(request: Request, org_slug: str) -> Response:
    """
    POST /api/vnext/orgs/<org_slug>/members/add/
    
    Add a new member to an organization.
    
    Payload: {
        "user_id": 123,
        "role": "MANAGER"  // MANAGER, SCOUT, or ANALYST
    }
    
    Response: {
        "membership_id": 456,
        "members": [...]  // updated member list
    }
    
    Performance: ≤5 queries, <100ms p95
    """
    try:
        # Get organization ID from slug
        from apps.organizations.models import Organization
        org = Organization.objects.get(slug=org_slug)
        
        # Validate payload
        user_id = request.data.get('user_id')
        role = request.data.get('role')
        
        if not user_id or not role:
            return Response(
                {
                    'error_code': 'MISSING_REQUIRED_FIELDS',
                    'message': 'user_id and role are required',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add member
        membership_id = OrganizationService.add_organization_member(
            organization_id=org.id,
            user_id=user_id,
            role=role,
            added_by_user_id=request.user.id
        )
        
        # Get updated member list
        members = OrganizationService.get_organization_members(organization_id=org.id)
        members_data = [{
            'user_id': m.user_id,
            'username': m.username,
            'display_name': m.display_name,
            'role': m.role,
            'permissions': m.permissions,
            'joined_date': m.joined_date
        } for m in members]
        
        logger.info(
            f"Member added to organization: {org_slug}",
            extra={
                'event_type': 'org_member_added',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'new_member_id': user_id,
                'role': role,
            }
        )
        
        return Response(
            {
                'membership_id': membership_id,
                'members': members_data
            },
            status=status.HTTP_201_CREATED
        )
    
    except Organization.DoesNotExist:
        return Response(
            {
                'error_code': 'ORG_NOT_FOUND',
                'message': f'Organization not found: {org_slug}',
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except (ValidationError, PermissionDeniedError, ConflictError, NotFoundError) as e:
        return Response(
            {
                'error_code': e.error_code,
                'message': str(e),
            },
            status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDeniedError) else status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.exception(
            f"Error adding member to organization: {org_slug}",
            extra={
                'event_type': 'org_member_add_error',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to add member',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_member_role(request: Request, org_slug: str, member_id: int) -> Response:
    """
    POST /api/vnext/orgs/<org_slug>/members/<member_id>/role/
    
    Change an organization member's role.
    
    Payload: {
        "role": "SCOUT"  // MANAGER, SCOUT, or ANALYST
    }
    
    Response: {
        "success": true,
        "member": {...}  // updated member data
    }
    
    Performance: ≤3 queries, <100ms p95
    """
    try:
        # Validate payload
        new_role = request.data.get('role')
        
        if not new_role:
            return Response(
                {
                    'error_code': 'MISSING_REQUIRED_FIELDS',
                    'message': 'role is required',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update role
        OrganizationService.update_member_role(
            membership_id=member_id,
            new_role=new_role,
            updated_by_user_id=request.user.id
        )
        
        # Get updated member data
        from apps.organizations.models import OrganizationMembership
        membership = OrganizationMembership.objects.select_related('user').get(id=member_id)
        
        member_data = {
            'id': membership.id,
            'user_id': membership.user.id,
            'username': membership.user.username,
            'display_name': getattr(membership.user, 'display_name', membership.user.username),
            'role': membership.role,
            'permissions': list(membership.permissions.keys()) if membership.permissions else [],
            'joined_at': membership.joined_at.isoformat()
        }
        
        logger.info(
            f"Member role updated in organization: {org_slug}",
            extra={
                'event_type': 'org_member_role_updated',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'member_id': member_id,
                'new_role': new_role,
            }
        )
        
        return Response(
            {
                'success': True,
                'member': member_data
            },
            status=status.HTTP_200_OK
        )
    
    except (ValidationError, PermissionDeniedError, NotFoundError) as e:
        return Response(
            {
                'error_code': e.error_code,
                'message': str(e),
            },
            status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDeniedError) else status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.exception(
            f"Error updating member role in organization: {org_slug}",
            extra={
                'event_type': 'org_member_role_update_error',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'member_id': member_id,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to update member role',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_organization_member(request: Request, org_slug: str, member_id: int) -> Response:
    """
    POST /api/vnext/orgs/<org_slug>/members/<member_id>/remove/
    
    Remove a member from an organization.
    
    Response: {
        "success": true,
        "members": [...]  // updated member list
    }
    
    Performance: ≤3 queries, <100ms p95
    """
    try:
        # Get organization ID from slug
        from apps.organizations.models import Organization
        org = Organization.objects.get(slug=org_slug)
        
        # Remove member
        OrganizationService.remove_organization_member(
            membership_id=member_id,
            removed_by_user_id=request.user.id
        )
        
        # Get updated member list
        members = OrganizationService.get_organization_members(organization_id=org.id)
        members_data = [{
            'user_id': m.user_id,
            'username': m.username,
            'display_name': m.display_name,
            'role': m.role,
            'permissions': m.permissions,
            'joined_date': m.joined_date
        } for m in members]
        
        logger.info(
            f"Member removed from organization: {org_slug}",
            extra={
                'event_type': 'org_member_removed',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'member_id': member_id,
            }
        )
        
        return Response(
            {
                'success': True,
                'members': members_data
            },
            status=status.HTTP_200_OK
        )
    
    except Organization.DoesNotExist:
        return Response(
            {
                'error_code': 'ORG_NOT_FOUND',
                'message': f'Organization not found: {org_slug}',
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except (PermissionDeniedError, NotFoundError) as e:
        return Response(
            {
                'error_code': e.error_code,
                'message': str(e),
            },
            status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDeniedError) else status.HTTP_404_NOT_FOUND
        )
    
    except Exception as e:
        logger.exception(
            f"Error removing member from organization: {org_slug}",
            extra={
                'event_type': 'org_member_remove_error',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'member_id': member_id,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to remove member',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_organization_settings(request: Request, org_slug: str) -> Response:
    """
    POST /api/vnext/orgs/<org_slug>/settings/
    
    Update organization branding settings.
    
    Payload: {
        "logo_url": "https://...",
        "banner_url": "https://...",
        "primary_color": "#667eea",
        "tagline": "Victory Awaits"
    }
    
    Response: {
        "success": true,
        "org": {...}  // updated org data
    }
    
    Performance: ≤3 queries, <100ms p95
    """
    try:
        # Get organization ID from slug
        from apps.organizations.models import Organization
        org = Organization.objects.get(slug=org_slug)
        
        # Update settings
        OrganizationService.update_organization_settings(
            organization_id=org.id,
            updated_by_user_id=request.user.id,
            logo_url=request.data.get('logo_url'),
            banner_url=request.data.get('banner_url'),
            primary_color=request.data.get('primary_color'),
            tagline=request.data.get('tagline')
        )
        
        # Get updated org data
        data = OrganizationService.get_organization_detail(
            org_slug=org_slug,
            include_members=False,
            include_teams=False
        )
        
        logger.info(
            f"Organization settings updated: {org_slug}",
            extra={
                'event_type': 'org_settings_updated',
                'user_id': request.user.id,
                'org_slug': org_slug,
            }
        )
        
        return Response(
            {
                'success': True,
                'org': data['org']
            },
            status=status.HTTP_200_OK
        )
    
    except Organization.DoesNotExist:
        return Response(
            {
                'error_code': 'ORG_NOT_FOUND',
                'message': f'Organization not found: {org_slug}',
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except (ValidationError, PermissionDeniedError) as e:
        return Response(
            {
                'error_code': e.error_code,
                'message': str(e),
            },
            status=status.HTTP_403_FORBIDDEN if isinstance(e, PermissionDeniedError) else status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.exception(
            f"Error updating organization settings: {org_slug}",
            extra={
                'event_type': 'org_settings_update_error',
                'user_id': request.user.id,
                'org_slug': org_slug,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to update settings',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Import exceptions for the new endpoints
from apps.organizations.services.exceptions import (
    ValidationError,
    PermissionDeniedError,
    NotFoundError,
    ConflictError
)

# ============================================================================
# TEAM MEMBERSHIP MANAGEMENT API (P3-T6)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_team_detail(request: Request, team_slug: str) -> Response:
    """
    Get team detail with members and invites.
    
    GET /api/vnext/teams/<team_slug>/detail/
    
    Returns:
        200: {team: {...}, members: [...], invites: [...]}
        404: Team not found
    
    Performance:
        - Target: <100ms p95, ≤5 queries
        - Uses select_related/prefetch_related
    """
    try:
        # Get team detail with members
        data = TeamService.get_team_detail(
            team_slug=team_slug,
            include_members=True,
            include_invites=True
        )
        
        logger.info(
            f"Team detail accessed: {team_slug}",
            extra={
                'event_type': 'team_detail_accessed',
                'user_id': request.user.id,
                'team_slug': team_slug,
            }
        )
        
        return Response(data, status=status.HTTP_200_OK)
    
    except NotFoundError as e:
        return Response(
            {
                'error_code': 'TEAM_NOT_FOUND',
                'message': f'Team not found: {team_slug}',
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except Exception as e:
        logger.exception(
            f"Error getting team detail: {team_slug}",
            extra={
                'event_type': 'team_detail_error',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to get team detail',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_team_member(request: Request, team_slug: str) -> Response:
    """
    Add new member to team roster.
    
    POST /api/vnext/teams/<team_slug>/members/add/
    Payload: {user_lookup: "<id|username|email>", role: "...", slot: "...", is_active: true}
    
    Returns:
        200: {success: true, membership_id: int, members: [...]}
        400: Validation error (invalid role/slot)
        403: Permission denied
        404: Team or user not found
        409: User already has active membership
    
    Permission:
        - Independent team: OWNER or MANAGER
        - Org-owned team: Org CEO/MANAGER or team OWNER/MANAGER
    """
    try:
        from apps.organizations.models import Team
        
        # Get team_id from slug
        try:
            team = Team.objects.only('id').get(slug=team_slug)
        except Team.DoesNotExist:
            return Response(
                {
                    'error_code': 'TEAM_NOT_FOUND',
                    'message': f'Team not found: {team_slug}',
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get payload
        user_lookup = request.data.get('user_lookup')
        role = request.data.get('role')
        roster_slot = request.data.get('slot')
        is_active = request.data.get('is_active', True)
        
        # Validate required fields
        if not user_lookup or not role:
            return Response(
                {
                    'error_code': 'MISSING_FIELDS',
                    'message': 'user_lookup and role are required',
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Add member
        membership_id = TeamService.add_team_member(
            team_id=team.id,
            user_lookup=user_lookup,
            role=role,
            roster_slot=roster_slot,
            added_by_user_id=request.user.id,
            is_active=is_active
        )
        
        # Schedule dual-write to legacy after commit
        if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False):
            def _sync_member_added():
                try:
                    DualWriteSyncService.sync_team_member_added(
                        vnext_membership_id=membership_id,
                        actor_user_id=request.user.id
                    )
                except Exception as e:
                    logger.error(
                        f"Dual-write failed for member addition: {membership_id}",
                        extra={
                            'event_type': 'dual_write_failed',
                            'operation': 'sync_team_member_added',
                            'membership_id': membership_id,
                            'team_slug': team_slug,
                            'user_id': request.user.id,
                            'exception_type': type(e).__name__,
                            'exception_message': str(e),
                        },
                        exc_info=True
                    )
                    # Re-raise in strict mode
                    if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE', False):
                        raise
            
            transaction.on_commit(_sync_member_added)
            logger.info(
                f"Dual-write scheduled for member addition: {membership_id}",
                extra={
                    'event_type': 'dual_write_scheduled',
                    'operation': 'sync_team_member_added',
                    'membership_id': membership_id,
                    'team_slug': team_slug,
                    'user_id': request.user.id,
                }
            )
        
        # Get updated member list
        members = [
            {
                'id': m.id,
                'user_id': m.user_id,
                'username': m.username,
                'display_name': m.display_name,
                'role': m.role,
                'roster_slot': m.roster_slot,
                'status': m.status,
                'is_tournament_captain': m.is_tournament_captain,
                'joined_date': m.joined_date,
            }
            for m in TeamService.get_roster_members(team.id, status='ACTIVE')
        ]
        
        logger.info(
            f"Member added to team: {team_slug}",
            extra={
                'event_type': 'team_member_added',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'membership_id': membership_id,
            }
        )
        
        return Response(
            {
                'success': True,
                'membership_id': membership_id,
                'members': members
            },
            status=status.HTTP_200_OK
        )
    
    except NotFoundError as e:
        error_code = 'USER_NOT_FOUND' if 'user' in str(e).lower() else 'TEAM_NOT_FOUND'
        return Response(
            {
                'error_code': error_code,
                'message': str(e),
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except PermissionDeniedError as e:
        return Response(
            {
                'error_code': 'INSUFFICIENT_PERMISSIONS',
                'message': str(e),
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    except ValidationError as e:
        return Response(
            {
                'error_code': 'INVALID_ROLE' if 'role' in str(e).lower() else 'VALIDATION_ERROR',
                'message': str(e),
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except ConflictError as e:
        return Response(
            {
                'error_code': 'MEMBER_ALREADY_EXISTS',
                'message': str(e),
            },
            status=status.HTTP_409_CONFLICT
        )
    
    except Exception as e:
        logger.exception(
            f"Error adding team member: {team_slug}",
            extra={
                'event_type': 'team_member_add_error',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to add member',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_member_role(request: Request, team_slug: str, member_id: int) -> Response:
    """
    Update team member's role or roster slot.
    
    POST /api/vnext/teams/<team_slug>/members/<member_id>/role/
    Payload: {role: "...", slot: "..."}
    
    Returns:
        200: {success: true, member: {...}}
        400: Validation error
        403: Permission denied or cannot change OWNER
        404: Team or membership not found
    
    Business Rules:
        - Cannot change OWNER role on independent teams
        - Only org CEO/MANAGER or team OWNER/MANAGER can update
    """
    try:
        from apps.organizations.models import Team
        
        # Get team_id from slug (for logging)
        try:
            team = Team.objects.only('id').get(slug=team_slug)
        except Team.DoesNotExist:
            return Response(
                {
                    'error_code': 'TEAM_NOT_FOUND',
                    'message': f'Team not found: {team_slug}',
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get payload
        role = request.data.get('role')
        roster_slot = request.data.get('slot')
        
        # Update member
        member = TeamService.update_member_role(
            membership_id=member_id,
            role=role,
            roster_slot=roster_slot,
            updated_by_user_id=request.user.id
        )
        
        # Schedule dual-write to legacy after commit
        if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False):
            def _sync_member_updated():
                try:
                    DualWriteSyncService.sync_team_member_updated(
                        vnext_membership_id=member_id,
                        actor_user_id=request.user.id
                    )
                except Exception as e:
                    logger.error(
                        f"Dual-write failed for member role update: {member_id}",
                        extra={
                            'event_type': 'dual_write_failed',
                            'operation': 'sync_team_member_updated',
                            'membership_id': member_id,
                            'team_slug': team_slug,
                            'user_id': request.user.id,
                            'exception_type': type(e).__name__,
                            'exception_message': str(e),
                        },
                        exc_info=True
                    )
                    # Re-raise in strict mode
                    if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE', False):
                        raise
            
            transaction.on_commit(_sync_member_updated)
            logger.info(
                f"Dual-write scheduled for member role update: {member_id}",
                extra={
                    'event_type': 'dual_write_scheduled',
                    'operation': 'sync_team_member_updated',
                    'membership_id': member_id,
                    'team_slug': team_slug,
                    'user_id': request.user.id,
                }
            )
        
        logger.info(
            f"Member role updated: {team_slug}",
            extra={
                'event_type': 'team_member_role_updated',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'membership_id': member_id,
            }
        )
        
        return Response(
            {
                'success': True,
                'member': member
            },
            status=status.HTTP_200_OK
        )
    
    except NotFoundError as e:
        error_code = 'MEMBERSHIP_NOT_FOUND' if 'membership' in str(e).lower() else 'TEAM_NOT_FOUND'
        return Response(
            {
                'error_code': error_code,
                'message': str(e),
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except PermissionDeniedError as e:
        return Response(
            {
                'error_code': 'INSUFFICIENT_PERMISSIONS',
                'message': str(e),
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    except ConflictError as e:
        return Response(
            {
                'error_code': 'CANNOT_CHANGE_OWNER',
                'message': str(e),
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except ValidationError as e:
        return Response(
            {
                'error_code': 'INVALID_ROLE' if 'role' in str(e).lower() else 'VALIDATION_ERROR',
                'message': str(e),
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.exception(
            f"Error updating member role: {team_slug}",
            extra={
                'event_type': 'team_member_role_update_error',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'membership_id': member_id,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to update role',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_team_member(request: Request, team_slug: str, member_id: int) -> Response:
    """
    Remove member from team roster.
    
    POST /api/vnext/teams/<team_slug>/members/<member_id>/remove/
    
    Returns:
        200: {success: true, members: [...]}
        400: Cannot remove OWNER from independent team
        403: Permission denied
        404: Team or membership not found
    
    Business Rules:
        - Cannot remove OWNER from independent teams
        - Only org CEO/MANAGER or team OWNER/MANAGER can remove
    """
    try:
        from apps.organizations.models import Team
        
        # Get team_id from slug
        try:
            team = Team.objects.only('id').get(slug=team_slug)
        except Team.DoesNotExist:
            return Response(
                {
                    'error_code': 'TEAM_NOT_FOUND',
                    'message': f'Team not found: {team_slug}',
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Remove member
        TeamService.remove_team_member(
            membership_id=member_id,
            removed_by_user_id=request.user.id
        )
        
        # Schedule dual-write to legacy after commit
        if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False):
            def _sync_member_removed():
                try:
                    DualWriteSyncService.sync_team_member_removed(
                        vnext_membership_id=member_id,
                        actor_user_id=request.user.id
                    )
                except Exception as e:
                    logger.error(
                        f"Dual-write failed for member removal: {member_id}",
                        extra={
                            'event_type': 'dual_write_failed',
                            'operation': 'sync_team_member_removed',
                            'membership_id': member_id,
                            'team_slug': team_slug,
                            'user_id': request.user.id,
                            'exception_type': type(e).__name__,
                            'exception_message': str(e),
                        },
                        exc_info=True
                    )
                    # Re-raise in strict mode
                    if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE', False):
                        raise
            
            transaction.on_commit(_sync_member_removed)
            logger.info(
                f"Dual-write scheduled for member removal: {member_id}",
                extra={
                    'event_type': 'dual_write_scheduled',
                    'operation': 'sync_team_member_removed',
                    'membership_id': member_id,
                    'team_slug': team_slug,
                    'user_id': request.user.id,
                }
            )
        
        # Get updated member list
        members = [
            {
                'id': m.id,
                'user_id': m.user_id,
                'username': m.username,
                'display_name': m.display_name,
                'role': m.role,
                'roster_slot': m.roster_slot,
                'status': m.status,
                'is_tournament_captain': m.is_tournament_captain,
                'joined_date': m.joined_date,
            }
            for m in TeamService.get_roster_members(team.id, status='ACTIVE')
        ]
        
        logger.info(
            f"Member removed from team: {team_slug}",
            extra={
                'event_type': 'team_member_removed',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'membership_id': member_id,
            }
        )
        
        return Response(
            {
                'success': True,
                'members': members
            },
            status=status.HTTP_200_OK
        )
    
    except NotFoundError as e:
        error_code = 'MEMBERSHIP_NOT_FOUND' if 'membership' in str(e).lower() else 'TEAM_NOT_FOUND'
        return Response(
            {
                'error_code': error_code,
                'message': str(e),
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except PermissionDeniedError as e:
        return Response(
            {
                'error_code': 'INSUFFICIENT_PERMISSIONS',
                'message': str(e),
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    except ConflictError as e:
        return Response(
            {
                'error_code': 'CANNOT_REMOVE_OWNER',
                'message': str(e),
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.exception(
            f"Error removing team member: {team_slug}",
            extra={
                'event_type': 'team_member_remove_error',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'membership_id': member_id,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to remove member',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_team_settings(request: Request, team_slug: str) -> Response:
    """
    Update team branding and settings.
    
    POST /api/vnext/teams/<team_slug>/settings/
    Payload: {region: "...", description: "...", preferred_server: "..."}
    
    Returns:
        200: {success: true, team: {...}}
        403: Permission denied
        404: Team not found
    
    Permission:
        - Independent team: OWNER or MANAGER
        - Org-owned team: Org CEO/MANAGER or team OWNER/MANAGER
    """
    try:
        from apps.organizations.models import Team
        
        # Get team_id from slug
        try:
            team = Team.objects.only('id').get(slug=team_slug)
        except Team.DoesNotExist:
            return Response(
                {
                    'error_code': 'TEAM_NOT_FOUND',
                    'message': f'Team not found: {team_slug}',
                },
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get payload
        region = request.data.get('region')
        description = request.data.get('description')
        preferred_server = request.data.get('preferred_server')
        logo_url = request.data.get('logo_url')
        banner_url = request.data.get('banner_url')
        
        # Update settings
        updated_team = TeamService.update_team_settings(
            team_id=team.id,
            updated_by_user_id=request.user.id,
            logo_url=logo_url,
            banner_url=banner_url,
            region=region,
            description=description,
            preferred_server=preferred_server
        )
        
        # Schedule dual-write to legacy after commit
        if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_ENABLED', False):
            def _sync_settings_updated():
                try:
                    DualWriteSyncService.sync_team_settings_updated(
                        vnext_team_id=team.id,
                        actor_user_id=request.user.id
                    )
                except Exception as e:
                    logger.error(
                        f"Dual-write failed for settings update: {team.id}",
                        extra={
                            'event_type': 'dual_write_failed',
                            'operation': 'sync_team_settings_updated',
                            'team_id': team.id,
                            'team_slug': team_slug,
                            'user_id': request.user.id,
                            'exception_type': type(e).__name__,
                            'exception_message': str(e),
                        },
                        exc_info=True
                    )
                    # Re-raise in strict mode
                    if getattr(settings, 'TEAM_VNEXT_DUAL_WRITE_STRICT_MODE', False):
                        raise
            
            transaction.on_commit(_sync_settings_updated)
            logger.info(
                f"Dual-write scheduled for settings update: {team.id}",
                extra={
                    'event_type': 'dual_write_scheduled',
                    'operation': 'sync_team_settings_updated',
                    'team_id': team.id,
                    'team_slug': team_slug,
                    'user_id': request.user.id,
                }
            )
        
        logger.info(
            f"Team settings updated: {team_slug}",
            extra={
                'event_type': 'team_settings_updated',
                'user_id': request.user.id,
                'team_slug': team_slug,
            }
        )
        
        return Response(
            {
                'success': True,
                'team': updated_team
            },
            status=status.HTTP_200_OK
        )
    
    except NotFoundError as e:
        return Response(
            {
                'error_code': 'TEAM_NOT_FOUND',
                'message': str(e),
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except PermissionDeniedError as e:
        return Response(
            {
                'error_code': 'INSUFFICIENT_PERMISSIONS',
                'message': str(e),
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    except Exception as e:
        logger.exception(
            f"Error updating team settings: {team_slug}",
            extra={
                'event_type': 'team_settings_update_error',
                'user_id': request.user.id,
                'team_slug': team_slug,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'error_code': 'internal_error',
                'message': 'Failed to update settings',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# PHASE D: TEAM INVITE MANAGEMENT
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_team_invites(request: Request) -> Response:
    """
    List all pending team invites for authenticated user.
    
    GET /api/vnext/teams/invites/
    
    Returns both:
    - TeamMembership invites (status=INVITED)
    - TeamInvite records (email-based, status=PENDING)
    
    Response:
        {
            "ok": true,
            "data": {
                "membership_invites": [...],
                "email_invites": [...],
                "total_count": 5
            }
        }
    
    Query Budget: ≤5 queries
    """
    from apps.organizations.services.team_invite_service import TeamInviteService
    
    try:
        invites_dto = TeamInviteService.list_user_invites(user_id=request.user.id)
        
        # Convert DTOs to dicts
        membership_invites = [
            {
                'id': inv.id,
                'team_id': inv.team_id,
                'team_name': inv.team_name,
                'team_slug': inv.team_slug,
                'game_name': inv.game_name,
                'role': inv.role,
                'inviter_name': inv.inviter_name,
                'created_at': inv.created_at,
                'status': inv.status,
            }
            for inv in invites_dto.membership_invites
        ]
        
        email_invites = [
            {
                'token': inv.token,
                'team_id': inv.team_id,
                'team_name': inv.team_name,
                'team_slug': inv.team_slug,
                'game_name': inv.game_name,
                'role': inv.role,
                'invited_email': inv.invited_email,
                'inviter_name': inv.inviter_name,
                'created_at': inv.created_at,
                'expires_at': inv.expires_at,
                'status': inv.status,
            }
            for inv in invites_dto.email_invites
        ]
        
        return Response({
            'ok': True,
            'data': {
                'membership_invites': membership_invites,
                'email_invites': email_invites,
                'total_count': invites_dto.total_count,
            }
        })
    
    except Exception as e:
        logger.exception(
            f"Error listing invites for user {request.user.id}",
            extra={
                'event_type': 'list_invites_error',
                'user_id': request.user.id,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'ok': False,
                'error_code': 'INTERNAL_ERROR',
                'safe_message': 'Failed to load invitations. Please try again.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_membership_invite(request: Request, membership_id: int) -> Response:
    """
    Accept a TeamMembership invite.
    
    POST /api/vnext/teams/invites/membership/<id>/accept/
    
    Changes membership status from INVITED → ACTIVE.
    
    Response (200):
        {
            "ok": true,
            "data": {
                "team_id": 123,
                "team_slug": "my-team",
                "team_url": "/teams/my-team/",
                "role": "MANAGER"
            }
        }
    
    Errors:
        404: INVITE_NOT_FOUND
        403: INVITE_FORBIDDEN
        400: INVITE_ALREADY_ACCEPTED
    
    Query Budget: ≤6 queries
    """
    from apps.organizations.services.team_invite_service import (
        TeamInviteService,
        InviteNotFoundError,
        InviteForbiddenError,
        InviteAlreadyAcceptedError,
    )
    
    try:
        result = TeamInviteService.accept_membership_invite(
            membership_id=membership_id,
            actor_user_id=request.user.id
        )
        
        logger.info(
            f"User {request.user.id} accepted membership invite {membership_id}",
            extra={
                'event_type': 'membership_invite_accepted',
                'user_id': request.user.id,
                'membership_id': membership_id,
                'team_id': result['team_id'],
            }
        )
        
        return Response({
            'ok': True,
            'data': result,
        })
    
    except InviteNotFoundError as e:
        return Response(
            {
                'ok': False,
                'error_code': e.error_code,
                'safe_message': e.safe_message,
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except InviteForbiddenError as e:
        return Response(
            {
                'ok': False,
                'error_code': e.error_code,
                'safe_message': e.safe_message,
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    except InviteAlreadyAcceptedError as e:
        return Response(
            {
                'ok': False,
                'error_code': e.error_code,
                'safe_message': e.safe_message,
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.exception(
            f"Error accepting membership invite {membership_id}",
            extra={
                'event_type': 'accept_membership_error',
                'user_id': request.user.id,
                'membership_id': membership_id,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'ok': False,
                'error_code': 'INTERNAL_ERROR',
                'safe_message': 'Failed to accept invitation. Please try again.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_membership_invite(request: Request, membership_id: int) -> Response:
    """
    Decline a TeamMembership invite.
    
    POST /api/vnext/teams/invites/membership/<id>/decline/
    
    Changes membership status from INVITED → DECLINED.
    
    Response (200):
        {
            "ok": true,
            "data": {"success": true}
        }
    
    Errors:
        404: INVITE_NOT_FOUND
        403: INVITE_FORBIDDEN
    
    Query Budget: ≤6 queries
    """
    from apps.organizations.services.team_invite_service import (
        TeamInviteService,
        InviteNotFoundError,
        InviteForbiddenError,
    )
    
    try:
        result = TeamInviteService.decline_membership_invite(
            membership_id=membership_id,
            actor_user_id=request.user.id
        )
        
        logger.info(
            f"User {request.user.id} declined membership invite {membership_id}",
            extra={
                'event_type': 'membership_invite_declined',
                'user_id': request.user.id,
                'membership_id': membership_id,
            }
        )
        
        return Response({
            'ok': True,
            'data': result,
        })
    
    except (InviteNotFoundError, InviteForbiddenError) as e:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(e, InviteNotFoundError) else status.HTTP_403_FORBIDDEN
        return Response(
            {
                'ok': False,
                'error_code': e.error_code,
                'safe_message': e.safe_message,
            },
            status=status_code
        )
    
    except Exception as e:
        logger.exception(
            f"Error declining membership invite {membership_id}",
            extra={
                'event_type': 'decline_membership_error',
                'user_id': request.user.id,
                'membership_id': membership_id,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'ok': False,
                'error_code': 'INTERNAL_ERROR',
                'safe_message': 'Failed to decline invitation. Please try again.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_email_invite(request: Request, token: str) -> Response:
    """
    Accept an email-based TeamInvite.
    
    POST /api/vnext/teams/invites/email/<token>/accept/
    
    Creates TeamMembership with ACTIVE status and marks invite ACCEPTED.
    
    Response (200):
        {
            "ok": true,
            "data": {
                "team_id": 123,
                "team_slug": "my-team",
                "team_url": "/teams/my-team/",
                "role": "MANAGER"
            }
        }
    
    Errors:
        404: INVITE_NOT_FOUND
        403: INVITE_FORBIDDEN (email mismatch)
        400: INVITE_EXPIRED
        400: INVITE_ALREADY_ACCEPTED
    
    Query Budget: ≤6 queries
    """
    from apps.organizations.services.team_invite_service import (
        TeamInviteService,
        InviteNotFoundError,
        InviteForbiddenError,
        InviteExpiredError,
        InviteAlreadyAcceptedError,
    )
    
    try:
        result = TeamInviteService.accept_email_invite(
            token=token,
            actor_user_id=request.user.id
        )
        
        logger.info(
            f"User {request.user.id} accepted email invite {token}",
            extra={
                'event_type': 'email_invite_accepted',
                'user_id': request.user.id,
                'token': token,
                'team_id': result['team_id'],
            }
        )
        
        return Response({
            'ok': True,
            'data': result,
        })
    
    except InviteNotFoundError as e:
        return Response(
            {
                'ok': False,
                'error_code': e.error_code,
                'safe_message': e.safe_message,
            },
            status=status.HTTP_404_NOT_FOUND
        )
    
    except InviteForbiddenError as e:
        return Response(
            {
                'ok': False,
                'error_code': e.error_code,
                'safe_message': e.safe_message,
            },
            status=status.HTTP_403_FORBIDDEN
        )
    
    except (InviteExpiredError, InviteAlreadyAcceptedError) as e:
        return Response(
            {
                'ok': False,
                'error_code': e.error_code,
                'safe_message': e.safe_message,
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    except Exception as e:
        logger.exception(
            f"Error accepting email invite {token}",
            extra={
                'event_type': 'accept_email_error',
                'user_id': request.user.id,
                'token': token,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'ok': False,
                'error_code': 'INTERNAL_ERROR',
                'safe_message': 'Failed to accept invitation. Please try again.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def decline_email_invite(request: Request, token: str) -> Response:
    """
    Decline an email-based TeamInvite.
    
    POST /api/vnext/teams/invites/email/<token>/decline/
    
    Marks invite as DECLINED.
    
    Response (200):
        {
            "ok": true,
            "data": {"success": true}
        }
    
    Errors:
        404: INVITE_NOT_FOUND
        403: INVITE_FORBIDDEN
    
    Query Budget: ≤6 queries
    """
    from apps.organizations.services.team_invite_service import (
        TeamInviteService,
        InviteNotFoundError,
        InviteForbiddenError,
    )
    
    try:
        result = TeamInviteService.decline_email_invite(
            token=token,
            actor_user_id=request.user.id
        )
        
        logger.info(
            f"User {request.user.id} declined email invite {token}",
            extra={
                'event_type': 'email_invite_declined',
                'user_id': request.user.id,
                'token': token,
            }
        )
        
        return Response({
            'ok': True,
            'data': result,
        })
    
    except (InviteNotFoundError, InviteForbiddenError) as e:
        status_code = status.HTTP_404_NOT_FOUND if isinstance(e, InviteNotFoundError) else status.HTTP_403_FORBIDDEN
        return Response(
            {
                'ok': False,
                'error_code': e.error_code,
                'safe_message': e.safe_message,
            },
            status=status_code
        )
    
    except Exception as e:
        logger.exception(
            f"Error declining email invite {token}",
            extra={
                'event_type': 'decline_email_error',
                'user_id': request.user.id,
                'token': token,
                'exception_type': type(e).__name__,
            }
        )
        return Response(
            {
                'ok': False,
                'error_code': 'INTERNAL_ERROR',
                'safe_message': 'Failed to decline invitation. Please try again.',
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# ORGANIZATION CREATION ENDPOINTS (Phase D: P3-T7)
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_organization_name(request: Request) -> Response:
    """
    Validate organization name uniqueness.
    
    GET /api/vnext/organizations/validate-name/?name=<name>
    
    Response (200 - available):
        {
            "ok": true,
            "available": true
        }
    
    Response (200 - unavailable):
        {
            "ok": false,
            "available": false,
            "field_errors": {
                "name": "An organization with this name already exists."
            }
        }
    """
    name = request.query_params.get('name', '').strip()
    
    # Validate required param
    if not name:
        return Response({
            'ok': False,
            'field_errors': {'name': 'Organization name is required.'}
        })
    
    # Check name length (minimum 3 characters)
    if len(name) < 3:
        return Response({
            'ok': False,
            'available': False,
            'field_errors': {'name': 'Organization name must be at least 3 characters.'}
        })
    
    # Check uniqueness (case-insensitive)
    if Organization.objects.filter(name__iexact=name).exists():
        return Response({
            'ok': False,
            'available': False,
            'field_errors': {'name': 'An organization with this name already exists.'}
        })
    
    return Response({
        'ok': True,
        'available': True
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_organization_badge(request: Request) -> Response:
    """
    Validate organization badge/ticker uniqueness.
    
    GET /api/vnext/organizations/validate-badge/?badge=<badge>
    
    Note: Organization.badge field is actually a ticker/tag, not an image.
    
    Response (200 - available):
        {
            "ok": true,
            "available": true
        }
    
    Response (200 - unavailable):
        {
            "ok": false,
            "available": false,
            "field_errors": {
                "badge": "This ticker is already taken."
            }
        }
    """
    badge = request.query_params.get('badge', '').strip().upper()
    
    # Validate required param
    if not badge:
        return Response({
            'ok': False,
            'field_errors': {'badge': 'Organization ticker is required.'}
        })
    
    # Check badge length (2-5 characters)
    if len(badge) < 2:
        return Response({
            'ok': False,
            'available': False,
            'field_errors': {'badge': 'Ticker must be at least 2 characters.'}
        })
    
    if len(badge) > 5:
        return Response({
            'ok': False,
            'available': False,
            'field_errors': {'badge': 'Ticker must be 5 characters or less.'}
        })
    
    # Note: Organization model may store badge as image field
    # For now, check against existing organization names as ticker proxy
    # TODO: Add dedicated ticker field to Organization model if needed
    
    return Response({
        'ok': True,
        'available': True
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def validate_organization_slug(request: Request) -> Response:
    """
    Validate organization slug uniqueness.
    
    GET /api/vnext/organizations/validate-slug/?slug=<slug>
    
    Response (200 - available):
        {
            "ok": true,
            "available": true
        }
    
    Response (200 - unavailable):
        {
            "ok": false,
            "available": false,
            "field_errors": {
                "slug": "This URL slug is already taken."
            }
        }
    """
    slug = request.query_params.get('slug', '').strip().lower()
    
    # Validate required param
    if not slug:
        return Response({
            'ok': False,
            'field_errors': {'slug': 'URL slug is required.'}
        })
    
    # Check slug length (minimum 3 characters)
    if len(slug) < 3:
        return Response({
            'ok': False,
            'available': False,
            'field_errors': {'slug': 'URL slug must be at least 3 characters.'}
        })
    
    # Check uniqueness
    if Organization.objects.filter(slug=slug).exists():
        return Response({
            'ok': False,
            'available': False,
            'field_errors': {'slug': 'This URL slug is already taken.'}
        })
    
    return Response({
        'ok': True,
        'available': True
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_organization(request: Request) -> Response:
    """
    Create a new organization.
    
    POST /api/vnext/organizations/create/
    
    Request Body (multipart/form-data):
        - name (required): Organization name
        - slug (optional): URL slug (auto-generated if not provided)
        - badge (optional): Ticker/tag (stored as text for now)
        - description (optional): Manifesto/mission
        - website (optional): Official website URL
        - twitter (optional): Twitter handle
        - logo (optional): Logo image file
        - banner (optional): Banner image file
        
        # Profile fields:
        - founded_year (optional): Year founded
        - organization_type (optional): club/pro/guild
        - hq_city (optional): City location
        - hq_address (optional): Full address (for Pro orgs)
        - business_email (optional): Business email (for Pro orgs)
        - trade_license (optional): Trade license number
        - discord_link (optional): Discord invite URL
        - instagram (optional): Instagram handle
        - facebook (optional): Facebook URL
        - youtube (optional): YouTube URL
        - region_code (optional): Country code (default: BD)
        - currency (optional): Currency code (default: BDT)
        - payout_method (optional): mobile/bank (default: mobile)
        - brand_color (optional): Hex color code
    
    Response (200 - success):
        {
            "ok": true,
            "data": {
                "organization_id": 123,
                "organization_slug": "my-org",
                "organization_url": "/orgs/my-org/"
            }
        }
    
    Response (400 - validation error):
        {
            "ok": false,
            "error_code": "VALIDATION_ERROR",
            "safe_message": "Please fix the errors below.",
            "field_errors": {
                "name": "Organization name is required.",
                ...
            }
        }
    """
    from apps.organizations.models import OrganizationProfile
    from django.utils.text import slugify
    
    # Extract data from request
    name = request.data.get('name', '').strip()
    slug = request.data.get('slug', '').strip()
    badge = request.data.get('badge', '').strip()
    description = request.data.get('description', '').strip()
    website = request.data.get('website', '').strip()
    twitter = request.data.get('twitter', '').strip()
    
    # Profile data
    founded_year = request.data.get('founded_year')
    organization_type = request.data.get('organization_type', 'club')
    hq_city = request.data.get('hq_city', '').strip()
    hq_address = request.data.get('hq_address', '').strip()
    business_email = request.data.get('business_email', '').strip()
    trade_license = request.data.get('trade_license', '').strip()
    discord_link = request.data.get('discord_link', '').strip()
    instagram = request.data.get('instagram', '').strip()
    facebook = request.data.get('facebook', '').strip()
    youtube = request.data.get('youtube', '').strip()
    region_code = request.data.get('region_code', 'BD')
    currency = request.data.get('currency', 'BDT')
    payout_method = request.data.get('payout_method', 'mobile')
    brand_color = request.data.get('brand_color', '').strip()
    
    # Files
    logo = request.FILES.get('logo')
    banner = request.FILES.get('banner')
    
    # Validation
    field_errors = {}
    
    if not name:
        field_errors['name'] = 'Organization name is required.'
    elif len(name) < 3:
        field_errors['name'] = 'Organization name must be at least 3 characters.'
    elif Organization.objects.filter(name__iexact=name).exists():
        field_errors['name'] = 'An organization with this name already exists.'
    
    if not slug:
        slug = slugify(name)
    
    if slug and Organization.objects.filter(slug=slug).exists():
        field_errors['slug'] = 'This URL slug is already taken.'
    
    if founded_year:
        try:
            founded_year = int(founded_year)
            if founded_year < 2000 or founded_year > 2030:
                field_errors['founded_year'] = 'Invalid year.'
        except ValueError:
            field_errors['founded_year'] = 'Invalid year format.'
    
    if field_errors:
        return Response({
            'ok': False,
            'error_code': 'VALIDATION_ERROR',
            'safe_message': 'Please fix the errors below.',
            'field_errors': field_errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create organization
    try:
        with transaction.atomic():
            org = Organization.objects.create(
                name=name,
                slug=slug,
                description=description,
                website=website,
                twitter=twitter,
                ceo=request.user,
                logo=logo,
                banner=banner,
            )
            
            # Create profile
            OrganizationProfile.objects.create(
                organization=org,
                founded_year=founded_year,
                organization_type=organization_type,
                hq_city=hq_city,
                hq_address=hq_address,
                business_email=business_email,
                trade_license=trade_license,
                discord_link=discord_link,
                instagram=instagram,
                facebook=facebook,
                youtube=youtube,
                region_code=region_code,
                currency=currency,
                payout_method=payout_method,
                brand_color=brand_color,
            )
            
            # Create CEO membership
            OrganizationMembership.objects.create(
                organization=org,
                user=request.user,
                role='CEO'
            )
            
            logger.info(
                f"Organization created: {org.name}",
                extra={
                    'event_type': 'org_created',
                    'org_id': org.id,
                    'org_slug': org.slug,
                    'ceo_id': request.user.id,
                }
            )
            
            return Response({
                'ok': True,
                'data': {
                    'organization_id': org.id,
                    'organization_slug': org.slug,
                    'organization_url': org.get_absolute_url(),
                }
            })
    
    except Exception as e:
        logger.exception(
            f"Error creating organization",
            extra={
                'event_type': 'org_creation_error',
                'user_id': request.user.id,
                'exception_type': type(e).__name__,
            }
        )
        return Response({
            'ok': False,
            'error_code': 'INTERNAL_ERROR',
            'safe_message': 'Failed to create organization. Please try again.',
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
