# apps/teams/views.py
"""
API Views for Teams application.
Handles team creation, roster management, and game configuration endpoints.
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404

from apps.teams.models import (
    ValorantTeam, CS2Team, Dota2Team, MLBBTeam, PUBGTeam,
    FreeFireTeam, EFootballTeam, FC26Team, CODMTeam,
    GAME_TEAM_MODELS
)
from apps.teams.serializers import (
    TEAM_SERIALIZERS, MEMBERSHIP_SERIALIZERS,
    TeamCreationSerializer,
    get_team_serializer_for_game,
    get_membership_serializer_for_game
)
from apps.games.services import game_service
from apps.teams.roster_manager import get_roster_manager
from apps.user_profile.models import UserProfile


# ═══════════════════════════════════════════════════════════════════════════
# Game Configuration Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([AllowAny])
def game_configs_list(request):
    """
    Get all game configurations.
    
    Returns roster rules, roles, and constraints for all supported games.
    """
    from apps.games.models import Game
    
    games = Game.objects.filter(is_active=True)
    configs = []
    
    for game in games:
        roster_limits = game_service.get_roster_limits(game)
        roles = game_service.get_roles(game)
        
        configs.append({
            'game_code': game.slug,
            'display_name': game.name,
            'min_starters': roster_limits.get('min_starters', 0),
            'max_starters': roster_limits.get('max_starters', 0),
            'min_substitutes': roster_limits.get('min_substitutes', 0),
            'max_substitutes': roster_limits.get('max_substitutes', 0),
            'max_roster_size': roster_limits.get('max_roster_size', 8),
            'roles': [role.name for role in roles],
            'requires_unique_roles': roster_limits.get('requires_unique_roles', False),
            'role_descriptions': {role.name: role.description for role in roles},
        })
    
    return Response({
        'count': len(configs),
        'games': configs
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def game_config_detail(request, game_code):
    """
    Get configuration for a specific game.
    
    Args:
        game_code: The game identifier (valorant, cs2, etc.)
    """
    game = game_service.get_game(game_code)
    
    if not game:
        return Response(
            {'error': f'Invalid game code: {game_code}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    roster_limits = game_service.get_roster_limits(game)
    roles = game_service.get_roles(game)
    
    return Response({
        'game_code': game.slug,
        'display_name': game.name,
        'min_starters': roster_limits.get('min_starters', 0),
        'max_starters': roster_limits.get('max_starters', 0),
        'min_substitutes': roster_limits.get('min_substitutes', 0),
        'max_substitutes': roster_limits.get('max_substitutes', 0),
        'max_roster_size': roster_limits.get('max_roster_size', 8),
        'roles': [role.name for role in roles],
        'requires_unique_roles': roster_limits.get('requires_unique_roles', False),
        'role_descriptions': {role.name: role.description for role in roles},
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def game_roles_list(request, game_code):
    """
    Get available roles for a specific game.
    
    Args:
        game_code: The game identifier
    """
    roles = get_available_roles(game_code)
    
    if roles is None:
        return Response(
            {'error': f'Invalid game code: {game_code}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get roles from GameService
    game = game_service.get_game(game_code)
    if not game:
        return Response(
            {'error': f'Invalid game code: {game_code}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    roles = game_service.get_roles(game)
    roster_limits = game_service.get_roster_limits(game)
    
    role_details = []
    for role in roles:
        role_details.append({
            'name': role.name,
            'description': role.description
        })
    
    return Response({
        'game_code': game.slug,
        'game_name': game.name,
        'roles': role_details,
        'requires_unique_roles': roster_limits.get('requires_unique_roles', False)
    })


# ═══════════════════════════════════════════════════════════════════════════
# Team Creation Endpoint (DEPRECATED)
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def _legacy_create_team_with_roster(request):
    """
    DEPRECATED: Create a new team with full roster in one transaction.
    Use apps.teams.api.views.TeamViewSet.create() instead.
    
    This function is deprecated and will be removed in Phase 2.
    """
    import warnings
    warnings.warn(
        "create_team_with_roster is deprecated. Use apps.teams.api.views.TeamViewSet.create() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return Response(
        {"error": "This endpoint is deprecated. Use /api/teams/ instead."},
        status=status.HTTP_410_GONE
    )


# Old function kept for backward compatibility - DO NOT USE
create_team_with_roster = _legacy_create_team_with_roster


# ═══════════════════════════════════════════════════════════════════════════
# Validation Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_team_name(request):
    """
    Check if team name is available.
    
    Body: {"game_code": "valorant", "name": "Team Alpha"}
    """
    game_code = request.data.get('game_code')
    name = request.data.get('name')
    
    if not game_code or not name:
        return Response(
            {'error': 'game_code and name are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    team_model = GAME_TEAM_MODELS.get(game_code)
    if not team_model:
        return Response(
            {'error': f'Invalid game code: {game_code}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    exists = team_model.objects.filter(name__iexact=name).exists()
    
    return Response({
        'available': not exists,
        'name': name,
        'game_code': game_code
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_team_tag(request):
    """
    Check if team tag is available.
    
    Body: {"game_code": "valorant", "tag": "ALPHA"}
    """
    game_code = request.data.get('game_code')
    tag = request.data.get('tag')
    
    if not game_code or not tag:
        return Response(
            {'error': 'game_code and tag are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    team_model = GAME_TEAM_MODELS.get(game_code)
    if not team_model:
        return Response(
            {'error': f'Invalid game code: {game_code}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    exists = team_model.objects.filter(tag__iexact=tag).exists()
    
    return Response({
        'available': not exists,
        'tag': tag,
        'game_code': game_code
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_ign_unique(request):
    """
    Check if IGN is unique within a team's roster.
    
    Body: {"roster": [{"ign": "Player1"}, {"ign": "Player2"}]}
    """
    roster = request.data.get('roster', [])
    
    if not roster:
        return Response({'valid': True})
    
    igns = [player.get('ign') for player in roster if player.get('ign')]
    duplicates = [ign for ign in igns if igns.count(ign) > 1]
    
    if duplicates:
        return Response({
            'valid': False,
            'duplicates': list(set(duplicates)),
            'error': f'Duplicate IGNs found: {", ".join(set(duplicates))}'
        })
    
    return Response({'valid': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_roster_composition(request):
    """
    Validate full roster composition for a game.
    
    Body: {
        "game_code": "valorant",
        "roster": [
            {"role": "Duelist", "is_starter": true, "ign": "Player1"},
            ...
        ]
    }
    """
    game_code = request.data.get('game_code')
    roster = request.data.get('roster', [])
    
    if not game_code:
        return Response(
            {'error': 'game_code is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    game = game_service.get_game(game_code)
    if not game:
        return Response(
            {'error': f'Invalid game code: {game_code}'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    roster_limits = game_service.get_roster_limits(game)
    roles = game_service.get_roles(game)
    valid_role_names = [role.name for role in roles]
    
    errors = []
    warnings = []
    
    # Count starters and subs
    starters = [p for p in roster if p.get('is_starter', True)]
    subs = [p for p in roster if not p.get('is_starter', True)]
    
    # Validate roster size
    min_starters = roster_limits.get('min_starters', 5)
    max_starters = roster_limits.get('max_starters', 5)
    max_substitutes = roster_limits.get('max_substitutes', 3)
    requires_unique_roles = roster_limits.get('requires_unique_roles', False)
    
    if len(starters) < min_starters:
        errors.append(
            f"Requires at least {min_starters} starters (currently {len(starters)})"
        )
    
    if len(starters) > max_starters:
        errors.append(
            f"Maximum {max_starters} starters allowed (currently {len(starters)})"
        )
    
    if len(subs) > max_substitutes:
        errors.append(
            f"Maximum {max_substitutes} substitutes allowed (currently {len(subs)})"
        )
    
    # Validate roles
    for i, player in enumerate(roster):
        role = player.get('role')
        if role and role not in valid_role_names:
            errors.append(
                f"Player {i+1} ({player.get('ign', 'Unknown')}): Invalid role '{role}'"
            )
    
    # Check unique positions if required
    if requires_unique_roles:
        starter_roles = [p.get('role') for p in starters if p.get('role')]
        if len(starter_roles) != len(set(starter_roles)):
            errors.append("All starter positions must be unique")
    
    # Warnings
    if len(subs) == 0 and max_substitutes > 0:
        warnings.append("No substitutes added. Consider adding backup players.")
    
    return Response({
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'roster_summary': {
            'total': len(roster),
            'starters': len(starters),
            'substitutes': len(subs),
            'max_starters': max_starters,
            'max_substitutes': max_substitutes,
        }
    })


# ═══════════════════════════════════════════════════════════════════════════
# Team ViewSets (for listing and detail views)
# ═══════════════════════════════════════════════════════════════════════════

class BaseTeamViewSet(viewsets.ReadOnlyModelViewSet):
    """Base viewset for team models."""
    permission_classes = [AllowAny]
    lookup_field = 'slug'
    
    @action(detail=True, methods=['get'])
    def roster_status(self, request, slug=None):
        """Get detailed roster status for a team."""
        team = self.get_object()
        manager = get_roster_manager(team)
        
        status_data = manager.get_roster_status()
        validation = manager.validate_for_tournament()
        available_roles = manager.get_available_roles(exclude_taken=True)
        
        return Response({
            'roster_status': status_data,
            'tournament_ready': validation,
            'available_roles': available_roles
        })


class ValorantTeamViewSet(BaseTeamViewSet):
    queryset = ValorantTeam.objects.filter(is_active=True)
    serializer_class = TEAM_SERIALIZERS['valorant']


class CS2TeamViewSet(BaseTeamViewSet):
    queryset = CS2Team.objects.filter(is_active=True)
    serializer_class = TEAM_SERIALIZERS['cs2']


class Dota2TeamViewSet(BaseTeamViewSet):
    queryset = Dota2Team.objects.filter(is_active=True)
    serializer_class = TEAM_SERIALIZERS['dota2']


class MLBBTeamViewSet(BaseTeamViewSet):
    queryset = MLBBTeam.objects.filter(is_active=True)
    serializer_class = TEAM_SERIALIZERS['mlbb']


class PUBGTeamViewSet(BaseTeamViewSet):
    queryset = PUBGTeam.objects.filter(is_active=True)
    serializer_class = TEAM_SERIALIZERS['pubg']


class FreeFireTeamViewSet(BaseTeamViewSet):
    queryset = FreeFireTeam.objects.filter(is_active=True)
    serializer_class = TEAM_SERIALIZERS['freefire']


class EFootballTeamViewSet(BaseTeamViewSet):
    queryset = EFootballTeam.objects.filter(is_active=True)
    serializer_class = TEAM_SERIALIZERS['efootball']


class FC26TeamViewSet(BaseTeamViewSet):
    queryset = FC26Team.objects.filter(is_active=True)
    serializer_class = TEAM_SERIALIZERS['fc26']


class CODMTeamViewSet(BaseTeamViewSet):
    queryset = CODMTeam.objects.filter(is_active=True)
    serializer_class = TEAM_SERIALIZERS['codm']
