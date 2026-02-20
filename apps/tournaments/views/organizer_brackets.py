"""
Organizer — Bracket Generation & Seeding (P3-T01, P3-T02).

Provides endpoints for:
- Bracket generation (format selection, seeding method, config)
- Bracket reset / regeneration
- Drag-and-drop seed reordering
- Bracket publish (finalize/lock)

Wires to existing services — NO new business logic:
- BracketEngineService (apps.tournament_ops.services.bracket_engine_service)
- BracketEditorService (apps.tournaments.services.bracket_editor_service)
"""
import json
import math
import random

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.utils import timezone

from apps.tournaments.models import (
    Tournament,
    Registration,
    Match,
    Bracket,
    TournamentStage,
)
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker
from apps.tournament_ops.services.bracket_engine_service import BracketEngineService
from apps.tournament_ops.dtos import TournamentDTO, StageDTO, TeamDTO
from apps.tournaments.services.bracket_editor_service import BracketEditorService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_confirmed_participants(tournament):
    """Return confirmed registrations for bracket generation."""
    return Registration.objects.filter(
        tournament=tournament,
        is_deleted=False,
        status='confirmed',
    ).select_related('user').order_by('created_at')


def _build_bracket_data(tournament, bracket):
    """Build bracket_data dict for template rendering."""
    matches = Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
    ).order_by('round_number', 'match_number')

    if not matches.exists():
        return None

    rounds_dict = {}
    for m in matches:
        rn = m.round_number
        if rn not in rounds_dict:
            rounds_dict[rn] = {'number': rn, 'matches': []}
        rounds_dict[rn]['matches'].append({
            'id': m.id,
            'match_number': m.match_number,
            'participant1_id': m.participant1_id,
            'participant1_name': m.participant1_name or 'TBD',
            'participant2_id': m.participant2_id,
            'participant2_name': m.participant2_name or 'TBD',
            'score1': m.participant1_score,
            'score2': m.participant2_score,
            'winner_id': m.winner_id,
            'state': m.state,
        })

    rounds = [rounds_dict[k] for k in sorted(rounds_dict.keys())]
    return {'rounds': rounds, 'format': bracket.format if bracket else 'unknown'}


def _any_match_started(tournament):
    """True if any match has progressed past SCHEDULED."""
    return Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
        state__in=['live', 'pending_result', 'completed', 'disputed'],
    ).exists()


def _participants_to_team_dtos(registrations, seeding_method='slot-order'):
    """Convert registrations to TeamDTOs for bracket engine."""
    teams = []
    for idx, reg in enumerate(registrations, start=1):
        if reg.team_id:
            # Team registration — team_id is an IntegerField (not FK)
            team_name = f'Team {reg.team_id}'
            # Try to resolve the team name
            try:
                from apps.teams.models import Team
                team_obj = Team.objects.filter(id=reg.team_id).first()
                if team_obj:
                    team_name = team_obj.name
            except Exception:
                pass

            teams.append(TeamDTO(
                id=reg.team_id,
                name=team_name,
                captain_id=reg.user_id,
                captain_name=reg.user.username if reg.user else '',
                member_ids=[reg.user_id] if reg.user else [],
                member_names=[reg.user.username] if reg.user else [],
                game=getattr(reg.tournament.game, 'slug', '') if hasattr(reg.tournament, 'game') and reg.tournament.game else '',
                is_verified=True,
                logo_url=None,
            ))
        else:
            # Solo registration
            teams.append(TeamDTO(
                id=reg.user_id or idx,
                name=reg.user.username if reg.user else f'Player {idx}',
                captain_id=reg.user_id or 0,
                captain_name=reg.user.username if reg.user else '',
                member_ids=[reg.user_id] if reg.user else [],
                member_names=[reg.user.username] if reg.user else [],
                game=getattr(reg.tournament.game, 'slug', '') if hasattr(reg.tournament, 'game') and reg.tournament.game else '',
                is_verified=True,
                logo_url=None,
            ))

    if seeding_method == 'random':
        random.shuffle(teams)

    return teams


def _seed_list_from_matches(tournament):
    """Build ordered seed list from existing first-round matches."""
    first_round = Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
        round_number=1,
    ).order_by('match_number')

    seeds = []
    seed_num = 1
    for m in first_round:
        if m.participant1_id:
            seeds.append({
                'seed': seed_num,
                'id': m.participant1_id,
                'name': m.participant1_name or 'TBD',
                'match_id': m.id,
                'slot': 1,
                'is_bye': False,
            })
        else:
            seeds.append({
                'seed': seed_num,
                'id': None,
                'name': 'BYE',
                'match_id': m.id,
                'slot': 1,
                'is_bye': True,
            })
        seed_num += 1

        if m.participant2_id:
            seeds.append({
                'seed': seed_num,
                'id': m.participant2_id,
                'name': m.participant2_name or 'TBD',
                'match_id': m.id,
                'slot': 2,
                'is_bye': False,
            })
        else:
            seeds.append({
                'seed': seed_num,
                'id': None,
                'name': 'BYE',
                'match_id': m.id,
                'slot': 2,
                'is_bye': True,
            })
        seed_num += 1

    return seeds


# ---------------------------------------------------------------------------
# P3-T01: Bracket Generation
# ---------------------------------------------------------------------------

@login_required
@require_POST
def generate_bracket(request, slug):
    """
    Generate bracket for tournament.

    POST body (JSON):
        format: str  — single-elimination | double-elimination | round-robin | swiss
        seeding_method: str — slot-order | random | ranked | manual
        config: dict — optional format-specific config
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    # Parse body
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    bracket_format = data.get('format', 'single-elimination')
    seeding_method = data.get('seeding_method', 'slot-order')
    config = data.get('config', {})

    # Cannot generate if locked
    if _any_match_started(tournament):
        return JsonResponse({
            'success': False,
            'error': 'Cannot generate bracket — matches already in progress.'
        }, status=400)

    # Minimum participants check
    participants = _get_confirmed_participants(tournament)
    if participants.count() < 2:
        return JsonResponse({
            'success': False,
            'error': 'At least 2 confirmed participants are required.'
        }, status=400)

    # Remove existing bracket + matches if regenerating
    Match.objects.filter(tournament=tournament, is_deleted=False).update(is_deleted=True)
    Bracket.objects.filter(tournament=tournament).delete()

    # Prepare DTOs
    team_dtos = _participants_to_team_dtos(participants, seeding_method)

    # Map format string to engine key
    format_map = {
        'single-elimination': 'single_elim',
        'double-elimination': 'double_elim',
        'round-robin': 'round_robin',
        'swiss': 'swiss',
    }
    engine_key = format_map.get(bracket_format, 'single_elim')

    # Create stage DTO
    stage_dto = StageDTO(
        id=0,
        name='Main Stage',
        type=engine_key,
        order=1,
        config=config,
        metadata=config,
    )

    tournament_dto = TournamentDTO.from_model(tournament)

    # Generate via BracketEngineService
    engine = BracketEngineService()
    try:
        match_dtos = engine.generate_bracket_for_stage(
            tournament=tournament_dto,
            stage=stage_dto,
            participants=team_dtos,
        )
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

    # Calculate total rounds
    total_rounds = max((m.round_number for m in match_dtos), default=1)

    # Create Bracket record
    bracket = Bracket.objects.create(
        tournament=tournament,
        format=bracket_format,
        total_rounds=total_rounds,
        total_matches=len(match_dtos),
        bracket_structure={
            'format': bracket_format,
            'total_participants': len(team_dtos),
            'seeding_method': seeding_method,
            'config': config,
        },
        seeding_method=seeding_method,
        is_finalized=False,
    )

    # Persist Match records
    for dto in match_dtos:
        Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=dto.round_number,
            match_number=dto.match_number or 1,
            participant1_id=dto.team_a_id,
            participant1_name=dto.team1_name or '',
            participant2_id=dto.team_b_id,
            participant2_name=dto.team2_name or '',
            state='scheduled',
        )

    return JsonResponse({
        'success': True,
        'message': f'Bracket generated: {len(match_dtos)} matches across {total_rounds} rounds.',
        'bracket_id': bracket.id,
        'match_count': len(match_dtos),
        'total_rounds': total_rounds,
    })


@login_required
@require_POST
def reset_bracket(request, slug):
    """Reset (destroy) bracket and all matches, allowing regeneration."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    if _any_match_started(tournament):
        return JsonResponse({
            'success': False,
            'error': 'Cannot reset — matches already in progress.'
        }, status=400)

    Match.objects.filter(tournament=tournament).update(is_deleted=True)
    Bracket.objects.filter(tournament=tournament).delete()

    return JsonResponse({'success': True, 'message': 'Bracket reset successfully.'})


# ---------------------------------------------------------------------------
# P3-T02: Seeding Reorder (Drag-and-Drop)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def reorder_seeds(request, slug):
    """
    Reorder seeds via drag-and-drop.

    POST body (JSON):
        order: list[int] — new ordered list of participant IDs (top = seed 1)
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    # Cannot reorder if bracket is finalized
    try:
        bracket = Bracket.objects.get(tournament=tournament)
    except Bracket.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No bracket exists.'}, status=400)

    if bracket.is_finalized:
        return JsonResponse({'success': False, 'error': 'Bracket is published — seeding locked.'}, status=400)

    if _any_match_started(tournament):
        return JsonResponse({'success': False, 'error': 'Cannot reorder — matches in progress.'}, status=400)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    new_order = data.get('order', [])
    if not new_order or not isinstance(new_order, list):
        return JsonResponse({'success': False, 'error': 'order must be a non-empty list of participant IDs'}, status=400)

    # Get first round matches
    first_round = Match.objects.filter(
        tournament=tournament,
        is_deleted=False,
        round_number=1,
    ).order_by('match_number')

    if not first_round.exists():
        return JsonResponse({'success': False, 'error': 'No first-round matches found.'}, status=400)

    # Re-slot participants into matches by new order
    # Simple approach: fill matches sequentially in pairs
    slot_idx = 0
    for match in first_round:
        p1_id = new_order[slot_idx] if slot_idx < len(new_order) else None
        p2_id = new_order[slot_idx + 1] if (slot_idx + 1) < len(new_order) else None

        p1_name = _resolve_name(p1_id, tournament) if p1_id else ''
        p2_name = _resolve_name(p2_id, tournament) if p2_id else ''

        match.participant1_id = p1_id
        match.participant1_name = p1_name
        match.participant2_id = p2_id
        match.participant2_name = p2_name
        match.save(update_fields=[
            'participant1_id', 'participant1_name',
            'participant2_id', 'participant2_name',
        ])
        slot_idx += 2

    return JsonResponse({
        'success': True,
        'message': 'Seeds reordered successfully.',
    })


def _resolve_name(participant_id, tournament):
    """Resolve participant name from registration."""
    reg = Registration.objects.filter(
        tournament=tournament,
        is_deleted=False,
        status='confirmed',
    ).filter(
        Q(user_id=participant_id) | Q(team_id=participant_id)
    ).select_related('user').first()
    if reg:
        if reg.team_id:
            # Try to get team name
            try:
                from apps.teams.models import Team
                team_obj = Team.objects.filter(id=reg.team_id).first()
                if team_obj:
                    return team_obj.name
            except Exception:
                pass
            return f'Team {reg.team_id}'
        if reg.user:
            return reg.user.username
    return f'Participant {participant_id}'


@login_required
@require_POST
def publish_bracket(request, slug):
    """Finalize/lock bracket — no more seeding changes allowed."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_manage_brackets():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        bracket = Bracket.objects.get(tournament=tournament)
    except Bracket.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'No bracket to publish.'}, status=400)

    if bracket.is_finalized:
        return JsonResponse({'success': False, 'error': 'Bracket already published.'}, status=400)

    # Validate bracket before publishing
    validation = BracketEditorService.validate_bracket(bracket.id)
    if hasattr(validation, 'is_valid') and not validation.is_valid:
        return JsonResponse({
            'success': False,
            'error': 'Bracket validation failed.',
            'errors': validation.errors if hasattr(validation, 'errors') else [],
        }, status=400)

    bracket.is_finalized = True
    bracket.save(update_fields=['is_finalized'])

    return JsonResponse({'success': True, 'message': 'Bracket published and locked.'})
