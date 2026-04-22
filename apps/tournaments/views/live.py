"""
Sprint 3: Public Live Tournament Experience Views

FE-T-008: Live Bracket View
FE-T-009: Match Watch / Match Detail Page
FE-T-018: Tournament Results Page

Public-facing views for spectators and participants to view live tournaments,
watch matches, and view final results.
"""

from collections import defaultdict
from datetime import timedelta
import json
import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError
from django.db.models import Count, Prefetch
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import DetailView

from apps.tournaments.models import (
    Match,
    MatchCenterConfig,
    MatchMedia,
    Registration,
    Tournament,
    TournamentFanPredictionVote,
)
from apps.tournaments.models.bracket import BracketNode
from apps.tournaments.models.result import TournamentResult
from apps.user_profile.services.url_validator import validate_highlight_url, validate_stream_url


logger = logging.getLogger(__name__)


# Game-family routing for the public Match Center.
_BR_GAME_SLUGS = frozenset({
    'pubg', 'pubgm', 'pubg-mobile', 'pubgmobile',
    'freefire', 'free-fire', 'free_fire', 'ff',
    'apex-legends', 'apex',
})
_EFOOTBALL_GAME_SLUGS = frozenset({
    'efootball', 'fifa', 'pes', 'football',
})
_VS_GAME_SLUGS = frozenset({
    'valorant', 'val', 'cs2', 'csgo', 'cs:go',
    'counter-strike', 'counterstrike',
    'dota2', 'dota-2', 'lol', 'league-of-legends',
})

_STATS_PARTIAL_VS = 'tournaments/public/live/_partials/stats_valorant.html'
_STATS_PARTIAL_BR = 'tournaments/public/live/_partials/stats_br.html'
_STATS_PARTIAL_EFOOTBALL = 'tournaments/public/live/_partials/stats_efootball.html'

_HERO_PARTIAL_BR = 'tournaments/public/live/_partials/hero_br.html'


def _detect_game_family(game):
    """Return one of {'br', 'efootball', 'vs'} for the given game.

    Drives both hero layout selection and stats partial routing.
    Falls back to 'vs' when the game is unknown — that matches the
    pre-existing visual contract.
    """
    if game is None:
        return 'vs'

    slug = (getattr(game, 'slug', '') or '').lower().strip()
    if slug in _BR_GAME_SLUGS:
        return 'br'
    if slug in _EFOOTBALL_GAME_SLUGS:
        return 'efootball'
    if slug in _VS_GAME_SLUGS:
        return 'vs'

    category = (getattr(game, 'category', '') or '').upper().strip()
    game_type = (getattr(game, 'game_type', '') or '').upper().strip()
    if category == 'BR' or game_type == 'BATTLE_ROYALE':
        return 'br'
    if category == 'SPORTS':
        return 'efootball'
    return 'vs'


def _resolve_stats_partial(family):
    return {
        'br': _STATS_PARTIAL_BR,
        'efootball': _STATS_PARTIAL_EFOOTBALL,
        'vs': _STATS_PARTIAL_VS,
    }.get(family, _STATS_PARTIAL_VS)


def _resolve_match_stats_source(match):
    """Return 'api' or 'manual' for the stats badge.

    Derived from MatchIntegrityCheck: if the API was actually fetched
    and matched/mismatched, treat stats as API-sourced. Otherwise the
    operator entered them manually.
    """
    try:
        check = getattr(match, 'integrity_check', None)
    except (AttributeError, DatabaseError):
        return 'manual'
    if check is None:
        return 'manual'

    try:
        api_payload = check.api_payload if isinstance(check.api_payload, dict) else {}
        status = (check.status or '').lower()
    except (AttributeError, DatabaseError):
        return 'manual'

    if api_payload and status in {'match', 'mismatch'}:
        return 'api'
    return 'manual'


DOUBLE_ELIM_LABELS = {
    1: 'UB Round 1',
    2: 'UB Quarterfinals',
    3: 'UB Semifinals',
    4: 'UB Final',
    5: 'LB Round 1',
    6: 'LB Round 2',
    7: 'LB Round 3',
    8: 'LB Round 4',
    9: 'LB Semifinal',
    10: 'LB Final',
    11: 'Grand Final',
}


def _safe_text(value, *, fallback='', max_length=240):
    text_value = str(value or '').strip()
    if not text_value:
        return str(fallback or '')[:max_length]
    return text_value[:max_length]


def _safe_bool(value, *, fallback=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {'1', 'true', 'yes', 'on'}:
            return True
        if token in {'0', 'false', 'no', 'off'}:
            return False
    return bool(fallback)


def _safe_int(value, *, fallback=0, minimum=None, maximum=None):
    try:
        parsed = int(float(value))
    except (TypeError, ValueError):
        parsed = int(fallback)

    if minimum is not None:
        parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(maximum, parsed)
    return parsed


def _safe_poll_option(value, *, fallback='', max_length=80, placeholders=None):
    option = _safe_text(value, fallback=fallback, max_length=max_length)
    normalized = option.strip().lower()
    if placeholders and normalized in placeholders:
        return _safe_text(fallback, fallback='', max_length=max_length)
    return option


def _slug_token(value, *, fallback='token'):
    token = ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(value or ''))
    token = '-'.join(part for part in token.split('-') if part)
    if token:
        return token
    token = ''.join(ch.lower() if ch.isalnum() else '-' for ch in str(fallback or 'token'))
    token = '-'.join(part for part in token.split('-') if part)
    return token or 'token'


def _build_round_label(match, tournament):
    if tournament.format == 'double_elimination' and match.round_number:
        return DOUBLE_ELIM_LABELS.get(match.round_number, f'Round {match.round_number}')

    if getattr(match, 'bracket_id', None) and getattr(match, 'bracket', None):
        try:
            return match.bracket.get_round_name(match.round_number)
        except (AttributeError, DatabaseError):
            pass

    return f'Round {match.round_number}'


def _with_youtube_origin(embed_url, request=None):
    url = str(embed_url or '').strip()
    if not url:
        return ''

    parsed = urlparse(url)
    host = (parsed.netloc or '').lower()
    if 'youtube.com' not in host and 'youtu.be' not in host:
        return url

    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    query = defaultdict(list)
    for key, value in query_items:
        query[key].append(value)

    if 'enablejsapi' not in query:
        query['enablejsapi'] = ['1']
    if 'rel' not in query:
        query['rel'] = ['0']

    if request is not None:
        origin = f'{request.scheme}://{request.get_host()}'
        query['origin'] = [origin]
        query['widget_referrer'] = [origin]

    rebuilt_query = urlencode(
        [(key, value) for key, values in query.items() for value in values],
        doseq=True,
    )
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, rebuilt_query, parsed.fragment))


def _resolve_embed_stream(raw_url, request=None):
    source_url = _safe_text(raw_url, fallback='', max_length=500)
    if not source_url:
        return {
            'source_url': '',
            'embed_url': '',
            'platform': '',
            'has_stream': False,
            'iframe_referrer_policy': 'strict-origin-when-cross-origin',
        }

    highlight_result = validate_highlight_url(source_url)
    if highlight_result.get('valid'):
        embed_url = _safe_text(highlight_result.get('embed_url'), fallback='', max_length=1000)
        platform = _safe_text(highlight_result.get('platform'), fallback='', max_length=32)
    else:
        stream_result = validate_stream_url(source_url)
        if stream_result.get('valid'):
            embed_url = _safe_text(stream_result.get('embed_url'), fallback='', max_length=1000)
            platform = _safe_text(stream_result.get('platform'), fallback='', max_length=32)
        else:
            embed_url = ''
            platform = ''

    if platform == 'youtube' and embed_url:
        embed_url = _with_youtube_origin(embed_url, request=request)

    iframe_referrer_policy = 'origin' if platform == 'youtube' else 'strict-origin-when-cross-origin'
    return {
        'source_url': source_url,
        'embed_url': embed_url,
        'platform': platform,
        'has_stream': bool(embed_url),
        'iframe_referrer_policy': iframe_referrer_policy,
    }


def _resolve_match_center_presentation(match, request=None):
    tournament = match.tournament
    round_label = _build_round_label(match, tournament)
    team_a_name = _safe_text(match.participant1_name, fallback='Team A', max_length=100)
    team_b_name = _safe_text(match.participant2_name, fallback='Team B', max_length=100)

    base = {
        'enabled': True,
        'show_timeline': True,
        'show_media': True,
        'show_stats': True,
        'show_fan_pulse': True,
        'theme': 'cyber',
        'poll_question': 'Who takes the series?',
        'poll_option_a': team_a_name,
        'poll_option_b': team_b_name,
        'auto_refresh_seconds': 20,
        'headline': f'{team_a_name} vs {team_b_name}',
        'subline': f'{round_label} • Match {match.match_number}',
        'stream_url': _safe_text(match.stream_url, fallback='', max_length=500),
        'featured_media_url': '',
    }

    try:
        config = MatchCenterConfig.objects.filter(tournament=tournament).first()
    except DatabaseError:
        logger.exception('MatchCenterConfig lookup failed for tournament %s', tournament.pk)
        config = None

    if not config:
        base['stream'] = _resolve_embed_stream(base.get('stream_url') or match.stream_url, request=request)
        return base

    merged = dict(base)
    merged.update({
        'enabled': bool(config.enabled),
        'show_timeline': bool(config.show_timeline),
        'show_media': bool(config.show_media),
        'show_stats': bool(config.show_stats),
        'show_fan_pulse': bool(config.show_fan_pulse),
        'theme': _safe_text(config.theme, fallback='cyber', max_length=24).lower(),
        'poll_question': _safe_text(config.poll_question, fallback=base['poll_question'], max_length=180),
        'poll_option_a': _safe_poll_option(
            config.poll_option_a,
            fallback=team_a_name,
            max_length=80,
            placeholders={'team a', 'option a'},
        ),
        'poll_option_b': _safe_poll_option(
            config.poll_option_b,
            fallback=team_b_name,
            max_length=80,
            placeholders={'team b', 'option b'},
        ),
        'auto_refresh_seconds': _safe_int(config.auto_refresh_seconds, fallback=20, minimum=10, maximum=120),
    })

    overrides = config.match_overrides if isinstance(config.match_overrides, dict) else {}
    override = overrides.get(str(match.id)) if isinstance(overrides.get(str(match.id)), dict) else {}

    if override:
        text_limits = {
            'headline': 120,
            'subline': 120,
            'poll_question': 180,
            'poll_option_a': 80,
            'poll_option_b': 80,
            'stream_url': 500,
            'featured_media_url': 500,
        }
        for key in ('headline', 'subline', 'poll_question', 'poll_option_a', 'poll_option_b', 'stream_url', 'featured_media_url'):
            if key in override:
                merged[key] = _safe_text(
                    override.get(key),
                    fallback=merged.get(key),
                    max_length=text_limits.get(key, 120),
                )
        for key in ('show_timeline', 'show_media', 'show_stats', 'show_fan_pulse'):
            if key in override:
                merged[key] = _safe_bool(override.get(key), fallback=merged.get(key, True))

    merged['poll_option_a'] = _safe_poll_option(
        merged.get('poll_option_a'),
        fallback=team_a_name,
        max_length=80,
        placeholders={'team a', 'option a'},
    )
    merged['poll_option_b'] = _safe_poll_option(
        merged.get('poll_option_b'),
        fallback=team_b_name,
        max_length=80,
        placeholders={'team b', 'option b'},
    )

    stream_source = merged.get('stream_url') or match.stream_url
    merged['stream'] = _resolve_embed_stream(stream_source, request=request)
    return merged


def _collect_match_media(match, presentation):
    entries = []

    featured = _safe_text(presentation.get('featured_media_url'), fallback='', max_length=500)
    if featured:
        entries.append({
            'id': 'featured',
            'media_type': 'featured',
            'url': featured,
            'description': 'Featured media',
            'created_at': None,
        })

    try:
        media_rows = MatchMedia.objects.filter(match=match).order_by('-created_at')[:8]
    except DatabaseError:
        logger.exception('MatchMedia lookup failed for match %s', match.pk)
        media_rows = []

    for row in media_rows:
        file_url = ''
        try:
            file_url = row.file.url if row.file else ''
        except (AttributeError, ValueError):
            file_url = ''

        url = _safe_text(row.url, fallback=file_url, max_length=500)
        if not url:
            continue

        entries.append({
            'id': str(row.id),
            'media_type': _safe_text(row.media_type, fallback='media', max_length=32),
            'url': url,
            'description': _safe_text(row.description, fallback='', max_length=180),
            'created_at': row.created_at,
        })

    return entries


def _build_fan_pulse_payload(match, presentation, viewer=None):
    poll_id = f'match-{match.id}-winner'
    option_a_id = f'{poll_id}:a'
    option_b_id = f'{poll_id}:b'
    option_a_name = _safe_text(presentation.get('poll_option_a'), fallback='Team A', max_length=80)
    option_b_name = _safe_text(presentation.get('poll_option_b'), fallback='Team B', max_length=80)

    enabled = bool(presentation.get('enabled') and presentation.get('show_fan_pulse'))

    option_counts = {option_a_id: 0, option_b_id: 0}
    viewer_choice = ''
    if enabled:
        try:
            rows = (
                TournamentFanPredictionVote.objects.filter(
                    tournament=match.tournament,
                    poll_id=poll_id,
                )
                .values('option_id')
                .annotate(total=Count('id'))
            )
            for row in rows:
                option_id = _safe_text(row.get('option_id'), fallback='', max_length=120)
                if option_id in option_counts:
                    option_counts[option_id] = int(row.get('total') or 0)

            if viewer and getattr(viewer, 'is_authenticated', False):
                vote = TournamentFanPredictionVote.objects.filter(
                    tournament=match.tournament,
                    user=viewer,
                    poll_id=poll_id,
                ).values_list('option_id', flat=True).first()
                viewer_choice = _safe_text(vote, fallback='', max_length=120)
        except DatabaseError:
            enabled = False

    total_votes = int(option_counts[option_a_id] + option_counts[option_b_id])
    if total_votes > 0:
        a_percent = int(round((option_counts[option_a_id] / total_votes) * 100))
        a_percent = max(0, min(100, a_percent))
        b_percent = max(0, 100 - a_percent)
    else:
        a_percent = 0
        b_percent = 0

    options = [
        {
            'id': option_a_id,
            'label': option_a_name,
            'votes': int(option_counts[option_a_id]),
            'percent': a_percent,
            'is_user_choice': viewer_choice == option_a_id,
        },
        {
            'id': option_b_id,
            'label': option_b_name,
            'votes': int(option_counts[option_b_id]),
            'percent': b_percent,
            'is_user_choice': viewer_choice == option_b_id,
        },
    ]

    return {
        'enabled': enabled,
        'poll_id': poll_id,
        'question': _safe_text(presentation.get('poll_question'), fallback='Who takes the series?', max_length=180),
        'options': options,
        'total_votes': total_votes,
        'has_user_voted': bool(viewer_choice),
        'user_choice_id': viewer_choice,
    }


def _build_match_timeline_rows(match, participant_resolver=None):
    timeline = []

    if match.scheduled_time:
        timeline.append({
            'timestamp': match.scheduled_time,
            'event': 'Match Scheduled',
            'icon': 'calendar',
            'description': f'Match scheduled for {match.scheduled_time.strftime("%B %d, %Y at %I:%M %p")}',
        })

    if match.state in [Match.LIVE, Match.COMPLETED, Match.PENDING_RESULT]:
        timeline.append({
            'timestamp': match.updated_at,
            'event': 'Match Started',
            'icon': 'play',
            'description': 'Match is now live',
        })

    if match.state == Match.COMPLETED and match.winner_id:
        winner_name = 'Unknown'
        if match.winner_id == match.participant1_id:
            winner_name = _safe_text(match.participant1_name, fallback='Participant 1', max_length=100)
        elif match.winner_id == match.participant2_id:
            winner_name = _safe_text(match.participant2_name, fallback='Participant 2', max_length=100)

        if participant_resolver is not None:
            try:
                winner_obj = participant_resolver(match.winner_id)
            except (AttributeError, DatabaseError):
                winner_obj = None
            if winner_obj is not None:
                winner_name = _safe_text(
                    getattr(winner_obj, 'username', ''),
                    fallback=winner_name,
                    max_length=100,
                )

        timeline.append({
            'timestamp': match.updated_at,
            'event': 'Match Completed',
            'icon': 'check',
            'description': f'{winner_name} won the match',
        })

    if match.state == Match.FORFEIT:
        timeline.append({
            'timestamp': match.updated_at,
            'event': 'Match Forfeit',
            'icon': 'alert',
            'description': 'Match ended by forfeit',
        })

    return timeline


class TournamentBracketView(DetailView):
    """
    FE-T-008: Live Bracket View
    
    Displays tournament bracket structure with matches organized by round.
    Public access (no authentication required).
    
    URL: /tournaments/<slug>/bracket/
    Template: tournaments/live/bracket.html
    """
    model = Tournament
    template_name = 'tournaments/public/live/bracket.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        """Optimize queries with select_related and prefetch_related."""
        return Tournament.objects.filter(
            is_deleted=False
        ).select_related(
            'game',
            'organizer',
            'bracket'
        ).prefetch_related(
            Prefetch(
                'matches',
                queryset=Match.objects.filter(
                    is_deleted=False
                ).select_related(
                    'tournament'
                ).order_by('round_number', 'match_number')
            )
        )
    
    def get_context_data(self, **kwargs):
        """Add bracket-specific context."""
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        bracket_available = self._is_bracket_available(tournament)
        context['bracket_available'] = bracket_available
        
        if bracket_available:
            # Only include bracket matches for bracket visualization
            all_matches = list(
                Match.objects.filter(
                    tournament=tournament,
                    bracket=tournament.bracket,
                    is_deleted=False,
                ).order_by('round_number', 'match_number')
            )

            # Batch-load logos/avatars for participants
            teams_map = {}
            if all_matches:
                pids = set()
                for m in all_matches:
                    if m.participant1_id:
                        pids.add(m.participant1_id)
                    if m.participant2_id:
                        pids.add(m.participant2_id)
                if pids and tournament.participation_type == 'team':
                    from apps.organizations.models import Team
                    for t in Team.objects.filter(id__in=pids).only('id', 'name', 'logo', 'tag'):
                        try:
                            logo = t.logo.url if t.logo else ''
                        except Exception:
                            logo = ''
                        teams_map[t.id] = {'name': t.name, 'logo': logo, 'tag': t.tag}
                elif pids and tournament.participation_type == 'solo':
                    from apps.accounts.models import User
                    for u in User.objects.filter(id__in=pids).select_related('profile').only('id', 'username', 'profile__avatar'):
                        try:
                            logo = u.profile.avatar.url if u.profile.avatar else ''
                        except Exception:
                            logo = ''
                        teams_map[u.id] = {'name': u.username, 'logo': logo, 'tag': ''}

            node_slots = {}
            slot_participant_ids = set()
            if getattr(tournament, 'bracket', None):
                node_rows = BracketNode.objects.filter(bracket=tournament.bracket).only(
                    'round_number',
                    'match_number_in_round',
                    'participant1_id',
                    'participant1_name',
                    'participant2_id',
                    'participant2_name',
                )
                for node in node_rows:
                    slot_key = (node.round_number or 0, node.match_number_in_round or 0)
                    node_slots[slot_key] = {
                        'participant1_id': node.participant1_id,
                        'participant1_name': node.participant1_name or '',
                        'participant2_id': node.participant2_id,
                        'participant2_name': node.participant2_name or '',
                    }
                    if node.participant1_id:
                        slot_participant_ids.add(node.participant1_id)
                    if node.participant2_id:
                        slot_participant_ids.add(node.participant2_id)

            missing_slot_ids = [pid for pid in slot_participant_ids if pid and pid not in teams_map]
            if missing_slot_ids and tournament.participation_type == 'team':
                from apps.organizations.models import Team

                for t in Team.objects.filter(id__in=missing_slot_ids).only('id', 'name', 'logo', 'tag'):
                    try:
                        logo = t.logo.url if t.logo else ''
                    except Exception:
                        logo = ''
                    teams_map[t.id] = {'name': t.name, 'logo': logo, 'tag': t.tag}
            elif missing_slot_ids and tournament.participation_type == 'solo':
                from apps.accounts.models import User

                for u in User.objects.filter(id__in=missing_slot_ids).select_related('profile').only('id', 'username', 'profile__avatar'):
                    try:
                        logo = u.profile.avatar.url if u.profile.avatar else ''
                    except Exception:
                        logo = ''
                    teams_map[u.id] = {'name': u.username, 'logo': logo, 'tag': ''}

            # Organize matches by round with enriched data
            # Pre-build round name lookup to avoid O(n) scan per match
            _round_name_map = {}
            if hasattr(tournament, 'bracket') and tournament.bracket:
                for rd in (tournament.bracket.bracket_structure or {}).get('rounds', []):
                    if isinstance(rd, dict) and rd.get('round_number') is not None:
                        _round_name_map[rd['round_number']] = rd.get('round_name', f"Round {rd['round_number']}")

            matches_by_round = {}
            for match in all_matches:
                round_num = match.round_number
                if round_num not in matches_by_round:
                    matches_by_round[round_num] = {
                        'round_number': round_num,
                        'round_name': _round_name_map.get(round_num, f'Round {round_num}'),
                        'matches': []
                    }

                # Determine bracket type for double-elim
                if tournament.format == 'double_elimination' and match.round_number:
                    if 5 <= match.round_number <= 10:
                        bracket_type = 'losers'
                    elif match.round_number == 11:
                        bracket_type = 'grand_final'
                    else:
                        bracket_type = 'winners'
                else:
                    bracket_type = 'main'

                # Team info enrichment
                t1 = teams_map.get(match.participant1_id, {})
                t2 = teams_map.get(match.participant2_id, {})

                # Parse map scores
                map_scores = []
                gs = match.game_scores or {}
                gs_maps = gs.get('maps', []) if isinstance(gs, dict) else gs if isinstance(gs, list) else []
                for gm in gs_maps:
                    map_scores.append({
                        'map_name': gm.get('map', gm.get('map_name', '')),
                        'p1_score': gm.get('p1', gm.get('p1_score', gm.get('team1_rounds', 0))),
                        'p2_score': gm.get('p2', gm.get('p2_score', gm.get('team2_rounds', 0))),
                        'winner_side': gm.get('winner_side', gm.get('winner_slot', 0)),
                    })

                best_of_label = ''
                if match.best_of and match.best_of > 1:
                    best_of_label = f'BO{match.best_of}'

                match_data = {
                    'id': match.id,
                    'match_number': match.match_number,
                    'round_number': match.round_number,
                    'state': match.state,
                    'bracket_type': bracket_type,
                    'round_label': _round_name_map.get(round_num, f'Round {round_num}'),
                    'team1_name': t1.get('name') or match.participant1_name or 'TBD',
                    'team2_name': t2.get('name') or match.participant2_name or 'TBD',
                    'team1_logo': t1.get('logo', ''),
                    'team2_logo': t2.get('logo', ''),
                    'team1_tag': t1.get('tag', ''),
                    'team2_tag': t2.get('tag', ''),
                    'participant1_id': match.participant1_id,
                    'participant2_id': match.participant2_id,
                    'score1': match.participant1_score,
                    'score2': match.participant2_score,
                    'winner_id': match.winner_id,
                    'team1_is_winner': match.winner_id and match.participant1_id == match.winner_id,
                    'team2_is_winner': match.winner_id and match.participant2_id == match.winner_id,
                    'is_live': match.state == 'live',
                    'is_completed': match.state in ('completed', 'forfeit'),
                    'scheduled_time': match.scheduled_time,
                    'best_of_label': best_of_label,
                    'map_scores': mark_safe(json.dumps(map_scores)),
                }
                matches_by_round[round_num]['matches'].append(match_data)

            def _slot_team_payload(participant_id, participant_name):
                team_meta = teams_map.get(participant_id, {})
                return {
                    'id': participant_id,
                    'name': team_meta.get('name') or participant_name or 'TBD',
                    'logo': team_meta.get('logo', ''),
                    'tag': team_meta.get('tag', ''),
                }

            def _merge_slot_teams(match_payload, slot_payload):
                if not slot_payload:
                    return

                slot_team1 = _slot_team_payload(
                    slot_payload.get('participant1_id'),
                    slot_payload.get('participant1_name'),
                )
                slot_team2 = _slot_team_payload(
                    slot_payload.get('participant2_id'),
                    slot_payload.get('participant2_name'),
                )

                current_name_1 = str(match_payload.get('team1_name') or '').strip()
                current_name_2 = str(match_payload.get('team2_name') or '').strip()

                if match_payload.get('participant1_id') in (None, '') and slot_team1['id']:
                    match_payload['participant1_id'] = slot_team1['id']
                if match_payload.get('participant2_id') in (None, '') and slot_team2['id']:
                    match_payload['participant2_id'] = slot_team2['id']

                if (not current_name_1 or current_name_1 == 'TBD') and slot_team1['name']:
                    match_payload['team1_name'] = slot_team1['name']
                if (not current_name_2 or current_name_2 == 'TBD') and slot_team2['name']:
                    match_payload['team2_name'] = slot_team2['name']

                if not match_payload.get('team1_logo') and slot_team1['logo']:
                    match_payload['team1_logo'] = slot_team1['logo']
                if not match_payload.get('team2_logo') and slot_team2['logo']:
                    match_payload['team2_logo'] = slot_team2['logo']

                if not match_payload.get('team1_tag') and slot_team1['tag']:
                    match_payload['team1_tag'] = slot_team1['tag']
                if not match_payload.get('team2_tag') and slot_team2['tag']:
                    match_payload['team2_tag'] = slot_team2['tag']
            
            # Fill placeholder TBD entries for future bracket rounds
            bs = (tournament.bracket.bracket_structure or {})
            for sr in bs.get('rounds', []):
                try:
                    rn = int(sr.get('round_number', 0) or 0)
                except (TypeError, ValueError):
                    rn = 0
                round_name = sr.get('round_name') or _round_name_map.get(rn) or f'Round {rn}'
                round_payload = matches_by_round.get(rn)
                if round_payload is None:
                    round_payload = {
                        'round_number': rn,
                        'round_name': round_name,
                        'matches': [],
                    }
                    matches_by_round[rn] = round_payload
                elif not round_payload.get('round_name'):
                    round_payload['round_name'] = round_name

                existing_matches = {
                    m.get('match_number'): m
                    for m in round_payload.get('matches', [])
                    if m.get('match_number') is not None
                }

                try:
                    match_count = max(int(sr.get('matches', 0) or 0), 0)
                except (TypeError, ValueError):
                    match_count = 0

                if tournament.format == 'double_elimination' and rn:
                    if 5 <= rn <= 10:
                        placeholder_bracket_type = 'losers'
                    elif rn == 11:
                        placeholder_bracket_type = 'grand_final'
                    else:
                        placeholder_bracket_type = 'winners'
                else:
                    placeholder_bracket_type = 'main'

                placeholder_matches = []
                for mi in range(1, match_count + 1):
                    slot_payload = node_slots.get((rn, mi), {})
                    existing_match = existing_matches.get(mi)
                    if existing_match is not None:
                        _merge_slot_teams(existing_match, slot_payload)
                        continue

                    slot_team1 = _slot_team_payload(
                        slot_payload.get('participant1_id'),
                        slot_payload.get('participant1_name'),
                    )
                    slot_team2 = _slot_team_payload(
                        slot_payload.get('participant2_id'),
                        slot_payload.get('participant2_name'),
                    )

                    placeholder_matches.append({
                        'id': None,
                        'match_number': mi,
                        'round_number': rn,
                        'state': 'pending',
                        'bracket_type': placeholder_bracket_type,
                        'round_label': round_name,
                        'team1_name': slot_team1['name'],
                        'team2_name': slot_team2['name'],
                        'team1_logo': slot_team1['logo'],
                        'team2_logo': slot_team2['logo'],
                        'team1_tag': slot_team1['tag'],
                        'team2_tag': slot_team2['tag'],
                        'participant1_id': slot_team1['id'],
                        'participant2_id': slot_team2['id'],
                        'score1': 0,
                        'score2': 0,
                        'winner_id': None,
                        'team1_is_winner': False,
                        'team2_is_winner': False,
                        'is_live': False,
                        'is_completed': False,
                        'scheduled_time': None,
                        'best_of_label': '',
                        'map_scores': mark_safe('[]'),
                    })

                if placeholder_matches:
                    round_payload['matches'].extend(placeholder_matches)
                round_payload['matches'].sort(key=lambda row: row.get('match_number') or 0)

            context['matches_by_round'] = sorted(
                matches_by_round.values(),
                key=lambda x: x['round_number']
            )
            context['bracket'] = tournament.bracket
            context['is_double_elim'] = tournament.format == 'double_elimination'

            # Flatten all match dicts for the template
            all_match_dicts = []
            for rd in context['matches_by_round']:
                all_match_dicts.extend(rd['matches'])
            context['all_matches'] = all_match_dicts
        else:
            context['matches_by_round'] = []
            context['bracket'] = None
            context['not_ready_reason'] = self._get_not_ready_reason(tournament)
            context['is_double_elim'] = False
            context['all_matches'] = []
        
        # Effective status for template (stage-aware)
        effective_status = getattr(tournament, 'get_effective_status', lambda: tournament.status)()
        context['effective_status'] = effective_status
        context['effective_status_display'] = effective_status.replace('_', ' ').title()
        current_stage = getattr(tournament, 'get_current_stage', lambda: None)()
        stage_display = None
        if current_stage == 'group_stage':
            stage_display = 'Group Stage'
        elif current_stage == 'knockout_stage':
            stage_display = 'Knockout Stage'
        context['stage_display'] = stage_display

        return context
    
    def _is_bracket_available(self, tournament):
        """Determine if bracket can be displayed."""
        # Too early states
        if tournament.status in [
            Tournament.DRAFT,
            Tournament.PENDING_APPROVAL,
            Tournament.PUBLISHED,
            Tournament.REGISTRATION_OPEN
        ]:
            return False
        
        # Cancelled tournament
        if tournament.status == Tournament.CANCELLED:
            return False
        
        # No bracket generated
        if not hasattr(tournament, 'bracket') or not tournament.bracket:
            return False
        
        # Bracket generation not complete — show if finalized OR if generated_at is set
        if not tournament.bracket.is_finalized and not tournament.bracket.generated_at:
            return False
        
        return True
    
    def _get_not_ready_reason(self, tournament):
        """Get human-readable reason why bracket is not available."""
        if tournament.status == Tournament.CANCELLED:
            return "Tournament has been cancelled."
        
        if tournament.status in [Tournament.DRAFT, Tournament.PENDING_APPROVAL]:
            return "Tournament is not yet published."
        
        if tournament.status in [Tournament.PUBLISHED, Tournament.REGISTRATION_OPEN]:
            return "Tournament is still accepting registrations. Bracket will be generated once registration closes."
        
        if tournament.status == Tournament.REGISTRATION_CLOSED:
            return "Bracket is being generated. Please check back soon."
        
        if not hasattr(tournament, 'bracket') or not tournament.bracket:
            return "Bracket has not been generated yet."
        
        if hasattr(tournament, 'bracket') and not tournament.bracket.is_finalized and not tournament.bracket.generated_at:
            return "Bracket generation is in progress."
        
        return "Bracket is not available at this time."
    
    def _get_round_name(self, round_number, tournament):
        """Get friendly name for round (e.g., 'Quarter Finals', 'Semi Finals')."""
        if hasattr(tournament, 'bracket') and tournament.bracket:
            bracket_structure = tournament.bracket.bracket_structure or {}
            rounds = bracket_structure.get('rounds', [])
            
            for round_data in rounds:
                if isinstance(round_data, dict) and round_data.get('round_number') == round_number:
                    return round_data.get('round_name', f'Round {round_number}')
        
        # Fallback naming
        return f'Round {round_number}'


class MatchDetailView(DetailView):
    """
    FE-T-009: Match Watch / Match Detail Page
    
    Displays detailed match information including participants, scores,
    timeline, and lobby info (for participants only).
    Public access (no authentication required).
    
    URL: /tournaments/<slug>/matches/<int:match_id>/
    Template: tournaments/live/match_detail.html
    """
    model = Match
    template_name = 'tournaments/public/live/match_detail.html'
    context_object_name = 'match'
    pk_url_kwarg = 'match_id'
    
    def get_queryset(self):
        """Filter by tournament slug for security and optimize queries."""
        tournament_slug = self.kwargs.get('slug')
        return Match.objects.filter(
            tournament__slug=tournament_slug,
            is_deleted=False
        ).select_related(
            'tournament',
            'tournament__game',
            'tournament__organizer'
        )
    
    def get_object(self, queryset=None):
        """Override to validate tournament slug matches."""
        if queryset is None:
            queryset = self.get_queryset()
        
        match_id = self.kwargs.get(self.pk_url_kwarg)
        tournament_slug = self.kwargs.get('slug')
        
        try:
            obj = queryset.get(pk=match_id)
        except Match.DoesNotExist:
            raise Http404(f"Match not found in tournament '{tournament_slug}'")
        
        return obj
    
    def get_context_data(self, **kwargs):
        """Add match-specific context with team data, player stats, and map scores."""
        context = super().get_context_data(**kwargs)
        match = self.object
        tournament = match.tournament

        context['tournament'] = tournament

        # ── Round label ──
        context['round_label'] = _build_round_label(match, tournament)

        # ── Team info (for team tournaments) ──
        team1 = self._get_team(match.participant1_id)
        team2 = self._get_team(match.participant2_id)
        context['team1'] = team1
        context['team2'] = team2
        context['is_team_tournament'] = team1 is not None or team2 is not None

        # Fallback: participant details (for 1v1)
        if not context['is_team_tournament']:
            context['participant1'] = self._get_participant_details(match.participant1_id)
            context['participant2'] = self._get_participant_details(match.participant2_id)

        # ── Map scores from game_scores JSON ──
        maps = []
        game_scores = match.game_scores or {}
        if isinstance(game_scores, dict):
            raw_maps = game_scores.get('maps', []) if isinstance(game_scores.get('maps'), list) else []
            best_of_value = game_scores.get('best_of', match.best_of or 1)
        elif isinstance(game_scores, list):
            raw_maps = game_scores
            best_of_value = match.best_of or 1
        else:
            raw_maps = []
            best_of_value = match.best_of or 1

        for m in raw_maps:
            if not isinstance(m, dict):
                continue
            maps.append({
                'map_name': m.get('map_name') or m.get('map') or '',
                'team1_rounds': _safe_int(m.get('team1_rounds', m.get('p1', 0)), fallback=0, minimum=0),
                'team2_rounds': _safe_int(m.get('team2_rounds', m.get('p2', 0)), fallback=0, minimum=0),
                'winner_side': m.get('winner_side', m.get('winner_slot')),
            })
        context['maps'] = maps
        context['best_of'] = _safe_int(best_of_value, fallback=match.best_of or 1, minimum=1, maximum=9)

        # ── Per-player stats (MatchPlayerStat + MatchMapPlayerStat) ──
        try:
            from apps.tournaments.models.match_player_stats import MatchPlayerStat, MatchMapPlayerStat
            has_match_stat_soft_delete = any(
                f.name == 'is_deleted' for f in MatchPlayerStat._meta.get_fields()
            )

            player_stats_qs = MatchPlayerStat.objects.filter(match=match)
            if has_match_stat_soft_delete:
                player_stats_qs = player_stats_qs.filter(is_deleted=False)
            player_stats_qs = player_stats_qs.order_by('-acs')

            team1_stats = []
            team2_stats = []
            for ps in player_stats_qs:
                stat_dict = {
                    'id': ps.id,
                    'player_name': ps.player_name,
                    'display_name': ps.display_name or ps.player_name,
                    'agent': ps.agent or '',
                    'kills': ps.kills or 0,
                    'deaths': ps.deaths or 0,
                    'assists': ps.assists or 0,
                    'kd_ratio': float(ps.kd_ratio) if ps.kd_ratio else 0.0,
                    'acs': float(ps.acs) if ps.acs else 0.0,
                    'adr': float(ps.adr) if ps.adr else 0.0,
                    'hs_pct': float(ps.hs_pct) if ps.hs_pct else 0.0,
                    'first_kills': ps.first_kills or 0,
                    'first_deaths': ps.first_deaths or 0,
                    'clutches': ps.clutches or 0,
                    'is_mvp': ps.is_mvp,
                }
                if ps.team_id == match.participant1_id:
                    team1_stats.append(stat_dict)
                elif ps.team_id == match.participant2_id:
                    team2_stats.append(stat_dict)

            # If team_id matching fails, split by order
            if not team1_stats and not team2_stats and player_stats_qs.exists():
                all_stats = [s for s in player_stats_qs]
                mid = len(all_stats) // 2
                for ps in all_stats[:mid]:
                    team1_stats.append({
                        'player_name': ps.player_name,
                        'display_name': ps.display_name or ps.player_name,
                        'agent': ps.agent or '', 'kills': ps.kills or 0,
                        'deaths': ps.deaths or 0, 'assists': ps.assists or 0,
                        'kd_ratio': float(ps.kd_ratio) if ps.kd_ratio else 0.0,
                        'acs': float(ps.acs) if ps.acs else 0.0,
                        'adr': float(ps.adr) if ps.adr else 0.0,
                        'hs_pct': float(ps.hs_pct) if ps.hs_pct else 0.0,
                        'first_kills': ps.first_kills or 0, 'first_deaths': ps.first_deaths or 0,
                        'clutches': ps.clutches or 0, 'is_mvp': ps.is_mvp,
                    })
                for ps in all_stats[mid:]:
                    team2_stats.append({
                        'player_name': ps.player_name,
                        'display_name': ps.display_name or ps.player_name,
                        'agent': ps.agent or '', 'kills': ps.kills or 0,
                        'deaths': ps.deaths or 0, 'assists': ps.assists or 0,
                        'kd_ratio': float(ps.kd_ratio) if ps.kd_ratio else 0.0,
                        'acs': float(ps.acs) if ps.acs else 0.0,
                        'adr': float(ps.adr) if ps.adr else 0.0,
                        'hs_pct': float(ps.hs_pct) if ps.hs_pct else 0.0,
                        'first_kills': ps.first_kills or 0, 'first_deaths': ps.first_deaths or 0,
                        'clutches': ps.clutches or 0, 'is_mvp': ps.is_mvp,
                    })

            context['team1_stats'] = sorted(team1_stats, key=lambda x: -x['acs'])
            context['team2_stats'] = sorted(team2_stats, key=lambda x: -x['acs'])

            # Per-map stats
            map_stat_field_names = {f.name for f in MatchMapPlayerStat._meta.get_fields()}
            uses_match_stat_relation = 'match_stat' in map_stat_field_names

            if uses_match_stat_relation:
                map_stats_qs = MatchMapPlayerStat.objects.filter(match_stat__match=match)
                if has_match_stat_soft_delete:
                    map_stats_qs = map_stats_qs.filter(match_stat__is_deleted=False)
                map_stats_qs = map_stats_qs.select_related('match_stat').order_by('map_number', '-kills')
            else:
                map_stats_qs = MatchMapPlayerStat.objects.filter(match=match).select_related('player').order_by('map_number', '-kills')

            map_player_stats = {}
            for mps in map_stats_qs:
                mn = mps.map_number
                if mn not in map_player_stats:
                    map_player_stats[mn] = {
                        'map_number': mn,
                        'map_name': maps[mn - 1]['map_name'] if mn <= len(maps) else f'Map {mn}',
                        'players': [],
                    }

                if uses_match_stat_relation:
                    player_name = mps.match_stat.display_name or mps.match_stat.player_name
                    team_id = mps.match_stat.team_id
                else:
                    player_name = mps.player.username if getattr(mps, 'player', None) else ''
                    team_id = getattr(mps, 'team_id', None)

                map_player_stats[mn]['players'].append({
                    'player_name': player_name,
                    'team_id': team_id,
                    'kills': mps.kills or 0, 'deaths': mps.deaths or 0, 'assists': mps.assists or 0,
                    'acs': float(mps.acs) if mps.acs else 0.0,
                    'adr': float(mps.adr) if mps.adr else 0.0,
                })
            context['map_player_stats'] = sorted(map_player_stats.values(), key=lambda x: x['map_number'])
        except ImportError:
            context['team1_stats'] = []
            context['team2_stats'] = []
            context['map_player_stats'] = []

        # MVP
        mvp_stat = next((s for s in (context.get('team1_stats', []) + context.get('team2_stats', [])) if s.get('is_mvp')), None)
        context['mvp'] = mvp_stat

        # Is participant?
        lobby_window_opens_at = None
        lobby_open_for_participant = False
        if self.request.user.is_authenticated:
            is_part = (
                match.participant1_id == self.request.user.id or
                match.participant2_id == self.request.user.id
            )
            if not is_part and getattr(tournament, 'participation_type', '') == 'team':
                from apps.organizations.models import TeamMembership
                active_teams = set(TeamMembership.objects.filter(user=self.request.user, status=TeamMembership.Status.ACTIVE).values_list('team_id', flat=True))
                if match.participant1_id in active_teams or match.participant2_id in active_teams:
                    is_part = True

            if is_part:
                from apps.tournaments.services.match_lobby_service import resolve_lobby_state
                lobby = resolve_lobby_state(match)
                lobby_open_for_participant = lobby['is_open']
                lobby_window_opens_at = lobby['opens_at']

            context['is_participant'] = is_part
        else:
            context['is_participant'] = False
        context['lobby_open_for_participant'] = bool(context['is_participant'] and lobby_open_for_participant)
        context['lobby_window_opens_at'] = lobby_window_opens_at
        context['show_lobby_info'] = bool(context['lobby_open_for_participant'] and match.lobby_info)

        # Timeline
        context['timeline'] = self._build_match_timeline(match)

        # Match Center presentation and fan pulse state
        viewer = self.request.user if self.request.user.is_authenticated else None
        presentation = _resolve_match_center_presentation(match, request=self.request)
        poll_payload = _build_fan_pulse_payload(match, presentation, viewer=viewer)
        media_items = _collect_match_media(match, presentation)

        team1_name = (
            (context.get('team1') or {}).get('name')
            if isinstance(context.get('team1'), dict)
            else _safe_text(match.participant1_name, fallback='Team A', max_length=100)
        )
        team2_name = (
            (context.get('team2') or {}).get('name')
            if isinstance(context.get('team2'), dict)
            else _safe_text(match.participant2_name, fallback='Team B', max_length=100)
        )

        team1_logo = ''
        team2_logo = ''
        if isinstance(context.get('team1'), dict):
            team1_logo = _safe_text((context.get('team1') or {}).get('logo_url'), fallback='', max_length=500)
        if isinstance(context.get('team2'), dict):
            team2_logo = _safe_text((context.get('team2') or {}).get('logo_url'), fallback='', max_length=500)

        participant1 = context.get('participant1')
        participant2 = context.get('participant2')
        if not team1_logo and participant1 is not None:
            try:
                team1_logo = participant1.profile.avatar.url if participant1.profile.avatar else ''
            except (AttributeError, ValueError):
                team1_logo = ''
        if not team2_logo and participant2 is not None:
            try:
                team2_logo = participant2.profile.avatar.url if participant2.profile.avatar else ''
            except (AttributeError, ValueError):
                team2_logo = ''

        context['match_state_api_url'] = reverse(
            'tournaments:match_center_state',
            kwargs={'slug': tournament.slug, 'match_id': match.id},
        )
        context['match_fan_pulse_vote_url'] = reverse(
            'tournaments:match_center_fan_pulse_vote',
            kwargs={'slug': tournament.slug, 'match_id': match.id},
        )

        game_family = _detect_game_family(getattr(tournament, 'game', None))
        is_br_layout = game_family == 'br'
        stats_partial = _resolve_stats_partial(game_family)
        stats_source = _resolve_match_stats_source(match)

        context['game_family'] = game_family
        context['is_br_layout'] = is_br_layout
        context['hero_br_partial'] = _HERO_PARTIAL_BR

        context['match_core'] = {
            'id': match.id,
            'state': match.state,
            'state_display': match.get_state_display() if hasattr(match, 'get_state_display') else _safe_text(match.state, fallback='Unknown', max_length=32),
            'round_label': context['round_label'],
            'match_number': match.match_number,
            'best_of': context['best_of'],
            'scheduled_time': match.scheduled_time,
            'participant1_id': match.participant1_id,
            'participant2_id': match.participant2_id,
            'participant1_name': _safe_text(team1_name, fallback='Team A', max_length=100),
            'participant2_name': _safe_text(team2_name, fallback='Team B', max_length=100),
            'participant1_score': int(match.participant1_score or 0),
            'participant2_score': int(match.participant2_score or 0),
            'winner_id': match.winner_id,
            'updated_at': match.updated_at,
            'game_family': game_family,
            'is_br_layout': is_br_layout,
        }

        context['match_presentation'] = {
            'enabled': bool(presentation.get('enabled')),
            'theme': _safe_text(presentation.get('theme'), fallback='cyber', max_length=24),
            'headline': _safe_text(presentation.get('headline'), fallback=f'{team1_name} vs {team2_name}', max_length=120),
            'subline': _safe_text(presentation.get('subline'), fallback=f"{context['round_label']} • Match {match.match_number}", max_length=120),
            'show_timeline': bool(presentation.get('show_timeline')),
            'show_media': bool(presentation.get('show_media')),
            'show_stats': bool(presentation.get('show_stats')),
            'show_fan_pulse': bool(presentation.get('show_fan_pulse')),
            'auto_refresh_seconds': _safe_int(presentation.get('auto_refresh_seconds'), fallback=20, minimum=10, maximum=120),
        }

        context['match_media'] = {
            'stream': presentation.get('stream') if isinstance(presentation.get('stream'), dict) else _resolve_embed_stream(match.stream_url, request=self.request),
            'items': media_items,
            'has_items': bool(media_items),
        }

        context['match_stats'] = {
            'team1': context.get('team1_stats', []),
            'team2': context.get('team2_stats', []),
            'maps': context.get('map_player_stats', []),
            'mvp': context.get('mvp'),
            'partial': stats_partial,
            'source': stats_source,
            'game_family': game_family,
        }

        context['match_poll'] = {
            **poll_payload,
            'vote_url': context['match_fan_pulse_vote_url'],
            'viewer_can_vote': bool(self.request.user.is_authenticated),
        }

        context['match_assets'] = {
            'team1_logo_url': team1_logo,
            'team2_logo_url': team2_logo,
            'team1_tag': _safe_text((context.get('team1') or {}).get('tag') if isinstance(context.get('team1'), dict) else '', fallback='', max_length=24),
            'team2_tag': _safe_text((context.get('team2') or {}).get('tag') if isinstance(context.get('team2'), dict) else '', fallback='', max_length=24),
        }

        context['viewer_login_url'] = f"{settings.LOGIN_URL}?next={self.request.path}"

        return context

    def _get_team(self, participant_id):
        """Get team details for a participant ID. Returns None if not found."""
        if not participant_id:
            return None
        try:
            from apps.organizations.models import Team
            team = Team.objects.filter(id=participant_id).first()
            if team:
                return {
                    'id': team.id,
                    'name': team.name,
                    'tag': getattr(team, 'tag', ''),
                    'logo_url': team.logo.url if team.logo else None,
                }
        except (ImportError, Exception):
            pass
        return None
    
    def _get_participant_details(self, user_id):
        """Get user details for a participant."""
        if not user_id:
            return None
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
    
    def _build_match_timeline(self, match):
        """Build timeline of match events."""
        return _build_match_timeline_rows(match, participant_resolver=self._get_participant_details)


@require_GET
def match_center_state(request, slug, match_id):
    """Lightweight public state endpoint for match center live refresh."""
    match = get_object_or_404(
        Match.objects.select_related('tournament').filter(is_deleted=False),
        tournament__slug=slug,
        pk=match_id,
    )

    viewer = request.user if getattr(request, 'user', None) and request.user.is_authenticated else None
    presentation = _resolve_match_center_presentation(match, request=request)
    poll_payload = _build_fan_pulse_payload(match, presentation, viewer=viewer)
    game_family = _detect_game_family(getattr(match.tournament, 'game', None))
    stats_source = _resolve_match_stats_source(match)

    return JsonResponse({
        'success': True,
        'match': {
            'id': match.id,
            'state': match.state,
            'state_display': match.get_state_display() if hasattr(match, 'get_state_display') else _safe_text(match.state, fallback='Unknown', max_length=32),
            'participant1_name': _safe_text(match.participant1_name, fallback='Team A', max_length=100),
            'participant2_name': _safe_text(match.participant2_name, fallback='Team B', max_length=100),
            'participant1_score': int(match.participant1_score or 0),
            'participant2_score': int(match.participant2_score or 0),
            'winner_id': match.winner_id,
            'updated_at': match.updated_at.isoformat() if match.updated_at else None,
            'game_family': game_family,
            'is_br_layout': game_family == 'br',
        },
        'presentation': {
            'headline': _safe_text(presentation.get('headline'), fallback='', max_length=120),
            'subline': _safe_text(presentation.get('subline'), fallback='', max_length=120),
            'show_timeline': bool(presentation.get('show_timeline')),
            'show_media': bool(presentation.get('show_media')),
            'show_stats': bool(presentation.get('show_stats')),
            'show_fan_pulse': bool(presentation.get('show_fan_pulse')),
            'has_stream': bool((presentation.get('stream') or {}).get('has_stream')) if isinstance(presentation.get('stream'), dict) else bool(_resolve_embed_stream(match.stream_url, request=request).get('has_stream')),
        },
        'stream': presentation.get('stream') if isinstance(presentation.get('stream'), dict) else _resolve_embed_stream(match.stream_url, request=request),
        'stats_meta': {
            'source': stats_source,
            'game_family': game_family,
        },
        'poll': poll_payload,
    })


@login_required
@require_POST
def match_center_fan_pulse_vote(request, slug, match_id):
    """Persist a fan pulse vote for the public match center page."""
    match = get_object_or_404(
        Match.objects.select_related('tournament').filter(is_deleted=False),
        tournament__slug=slug,
        pk=match_id,
    )

    try:
        body = request.body.decode('utf-8') if request.body else '{}'
        payload = json.loads(body or '{}')
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON payload.'}, status=400)

    if not isinstance(payload, dict):
        return JsonResponse({'success': False, 'error': 'Request body must be a JSON object.'}, status=400)

    presentation = _resolve_match_center_presentation(match, request=request)
    poll_payload = _build_fan_pulse_payload(match, presentation, viewer=request.user)
    if not poll_payload.get('enabled'):
        return JsonResponse({'success': False, 'error': 'Fan Pulse is currently disabled.'}, status=400)

    submitted_option_id = _safe_text(payload.get('option_id'), fallback='', max_length=120)
    if not submitted_option_id:
        return JsonResponse({'success': False, 'error': 'option_id is required.'}, status=400)

    option_ids = {
        str(option.get('id') or '').strip()
        for option in (poll_payload.get('options') if isinstance(poll_payload.get('options'), list) else [])
        if isinstance(option, dict)
    }

    shorthand_map = {}
    options = poll_payload.get('options') if isinstance(poll_payload.get('options'), list) else []
    if len(options) >= 2:
        shorthand_map = {
            'a': _safe_text(options[0].get('id'), fallback='', max_length=120),
            'b': _safe_text(options[1].get('id'), fallback='', max_length=120),
        }
    normalized_option_id = shorthand_map.get(submitted_option_id.lower(), submitted_option_id)

    if normalized_option_id not in option_ids:
        return JsonResponse({'success': False, 'error': 'Poll option is invalid.'}, status=400)

    try:
        TournamentFanPredictionVote.objects.update_or_create(
            tournament=match.tournament,
            user=request.user,
            poll_id=_safe_text(poll_payload.get('poll_id'), fallback=f'match-{match.id}-winner', max_length=64),
            defaults={'option_id': normalized_option_id},
        )
    except DatabaseError:
        return JsonResponse(
            {
                'success': False,
                'error': 'Fan Pulse is temporarily unavailable. Please try again shortly.',
            },
            status=503,
        )

    refreshed_poll = _build_fan_pulse_payload(match, presentation, viewer=request.user)
    return JsonResponse(
        {
            'success': True,
            'message': 'Fan Pulse vote saved.',
            'poll': refreshed_poll,
        },
        status=200,
    )


class TournamentResultsView(DetailView):
    """
    FE-T-018: Tournament Results Page
    
    Displays final tournament results including winners podium,
    final leaderboard, and match history.
    Public access (no authentication required).
    
    URL: /tournaments/<slug>/results/
    Template: tournaments/live/results.html
    """
    model = Tournament
    template_name = 'tournaments/public/live/results.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        """Only show results for completed tournaments. Optimize queries."""
        return Tournament.objects.filter(
            is_deleted=False
        ).select_related(
            'game',
            'organizer',
            'result',  # OneToOne TournamentResult
            'result__winner',
            'result__winner__user',
            'result__runner_up',
            'result__runner_up__user',
            'result__third_place',
            'result__third_place__user'
        ).prefetch_related(
            Prefetch(
                'registrations',
                queryset=Registration.objects.filter(
                    is_deleted=False
                ).select_related('user').order_by('seed')
            ),
            Prefetch(
                'matches',
                queryset=Match.objects.filter(
                    is_deleted=False,
                    state=Match.COMPLETED
                ).select_related('tournament').order_by('round_number', 'match_number')
            )
        )
    
    def get_object(self, queryset=None):
        """Override to provide better error message for incomplete tournaments."""
        obj = super().get_object(queryset)
        
        # Check if tournament is completed
        if obj.status not in [Tournament.COMPLETED, Tournament.ARCHIVED]:
            # Allow viewing results if TournamentResult exists (manual finalization)
            if not hasattr(obj, 'result') or not obj.result:
                raise Http404("Tournament results are not available yet. Tournament is still in progress.")
        
        return obj
    
    def get_context_data(self, **kwargs):
        """Add results-specific context."""
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Results
        has_results = hasattr(tournament, 'result') and tournament.result is not None
        context['has_results'] = has_results
        context['result'] = tournament.result if has_results else None
        
        if has_results:
            result = tournament.result
            
            # Winners (with user details)
            context['winner'] = result.winner
            context['runner_up'] = result.runner_up
            context['third_place'] = result.third_place
            
            # Determination method (for display)
            context['determination_method'] = result.get_determination_method_display()
        
        # All completed matches
        context['completed_matches'] = tournament.matches.filter(state=Match.COMPLETED)
        
        # Leaderboard (all registrations)
        # Note: In production, this would be sorted by final placement
        # For now, we use seed as proxy
        context['leaderboard'] = tournament.registrations.all()
        
        # Tournament stats
        context['stats'] = self._calculate_tournament_stats(tournament)
        
        return context
    
    def _calculate_tournament_stats(self, tournament):
        """Calculate tournament statistics."""
        stats = {
            'total_participants': tournament.registrations.count(),
            'total_matches': tournament.matches.count(),
            'completed_matches': tournament.matches.filter(state=Match.COMPLETED).count(),
        }
        
        # Tournament duration
        if tournament.tournament_start and tournament.tournament_end:
            duration = tournament.tournament_end - tournament.tournament_start
            stats['duration_days'] = duration.days
            stats['duration_hours'] = duration.total_seconds() / 3600
        
        return stats
