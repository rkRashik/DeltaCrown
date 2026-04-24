"""
TOC Match Center service.

Persists and serves organizer-controlled presentation settings for the
public tournament match center page.

Override semantics
------------------
``match_overrides`` is a wholesale replacement on every save: whatever the
client sends becomes the new override map. Per text override field the
contract is:

* present-and-non-empty  → store the value
* present-and-empty      → drop the field (override cleared)
* absent                 → drop the field (override cleared)

If every text override is empty AND no boolean override is set for a match,
the entire per-match entry is removed from the map. This keeps the JSON
storage small and makes "Clear Selected Override" deterministic.
"""

import logging

from django.db import DatabaseError, transaction

from apps.tournaments.models import Match, MatchCenterConfig
from apps.user_profile.services.url_validator import validate_highlight_url, validate_stream_url


logger = logging.getLogger(__name__)


_BR_GAME_SLUGS = frozenset({
    'pubg', 'pubgm', 'pubg-mobile', 'pubgmobile',
    'freefire', 'free-fire', 'free_fire', 'ff',
    'apex-legends', 'apex',
})
_EFOOTBALL_GAME_SLUGS = frozenset({'efootball', 'fifa', 'pes', 'football'})
_VS_GAME_SLUGS = frozenset({
    'valorant', 'val', 'cs2', 'csgo', 'cs:go',
    'counter-strike', 'counterstrike',
    'dota2', 'dota-2', 'lol', 'league-of-legends',
})


def _detect_game_family(game):
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


class TOCMatchCenterService:
    """Business logic for Match Center config APIs."""

    @staticmethod
    def get_config(tournament):
        try:
            config = MatchCenterConfig.objects.filter(tournament=tournament).first()
        except DatabaseError:
            logger.exception('MatchCenterConfig table unavailable for tournament %s', tournament.pk)
            config = None
        if config is None:
            config = MatchCenterConfig(tournament=tournament)
        return {
            'config': TOCMatchCenterService._serialize_config(config),
            'matches': TOCMatchCenterService._list_matches(tournament),
            'game_family': _detect_game_family(getattr(tournament, 'game', None)),
        }

    @staticmethod
    @transaction.atomic
    def update_config(tournament, payload):
        source = payload if isinstance(payload, dict) else {}
        try:
            config, _ = MatchCenterConfig.objects.get_or_create(tournament=tournament)
        except DatabaseError:
            logger.exception('MatchCenterConfig table unavailable on save for tournament %s', tournament.pk)
            # Echo the submitted payload (validated) so the UI does not appear to
            # silently revert to blank defaults when storage is unavailable.
            stub = MatchCenterConfig(tournament=tournament)
            TOCMatchCenterService._apply_payload_to_instance(stub, source)
            normalized, invalid_urls = TOCMatchCenterService._normalize_overrides(
                source.get('match_overrides') if isinstance(source.get('match_overrides'), dict) else {}
            )
            stub.match_overrides = normalized
            return {
                'success': False,
                'error': 'Match Center storage is not available yet. The configuration table needs to be migrated.',
                'config': TOCMatchCenterService._serialize_config(stub),
                'matches': TOCMatchCenterService._list_matches(tournament),
                'invalid_urls': invalid_urls,
                'game_family': _detect_game_family(getattr(tournament, 'game', None)),
            }

        TOCMatchCenterService._apply_payload_to_instance(config, source)
        raw_overrides = source.get('match_overrides') if isinstance(source.get('match_overrides'), dict) else {}
        normalized, invalid_urls = TOCMatchCenterService._normalize_overrides(raw_overrides)
        config.match_overrides = normalized

        config.save()

        return {
            'success': True,
            'config': TOCMatchCenterService._serialize_config(config),
            'matches': TOCMatchCenterService._list_matches(tournament),
            'invalid_urls': invalid_urls,
            'game_family': _detect_game_family(getattr(tournament, 'game', None)),
        }

    @staticmethod
    def _apply_payload_to_instance(config, source):
        """Apply validated scalar fields from the request payload to a config instance.

        Shared between the happy-path save and the DatabaseError fallback so the
        UI sees consistent echoed values either way. Does not touch
        ``match_overrides`` — callers normalize that separately.
        """
        config.enabled = TOCMatchCenterService._as_bool(source.get('enabled'), fallback=config.enabled)
        config.show_media = TOCMatchCenterService._as_bool(source.get('show_media'), fallback=config.show_media)
        config.show_stats = TOCMatchCenterService._as_bool(source.get('show_stats'), fallback=config.show_stats)
        config.show_fan_pulse = TOCMatchCenterService._as_bool(source.get('show_fan_pulse'), fallback=config.show_fan_pulse)

        next_theme = str(source.get('theme') or '').strip().lower()
        valid_themes = {choice[0] for choice in MatchCenterConfig.THEME_CHOICES}
        if next_theme in valid_themes:
            config.theme = next_theme

        config.poll_question = TOCMatchCenterService._as_text(
            source.get('poll_question'),
            fallback=config.poll_question,
            max_length=180,
        )
        config.poll_option_a = TOCMatchCenterService._as_text(
            source.get('poll_option_a'),
            fallback=config.poll_option_a,
            max_length=80,
        )
        config.poll_option_b = TOCMatchCenterService._as_text(
            source.get('poll_option_b'),
            fallback=config.poll_option_b,
            max_length=80,
        )
        config.auto_refresh_seconds = TOCMatchCenterService._as_int(
            source.get('auto_refresh_seconds'),
            fallback=config.auto_refresh_seconds,
            minimum=10,
            maximum=120,
        )

    @staticmethod
    def _serialize_config(config):
        return {
            'enabled': bool(config.enabled),
            'show_media': bool(config.show_media),
            'show_stats': bool(config.show_stats),
            'show_fan_pulse': bool(config.show_fan_pulse),
            'theme': config.theme,
            'poll_question': config.poll_question,
            'poll_option_a': config.poll_option_a,
            'poll_option_b': config.poll_option_b,
            'auto_refresh_seconds': int(config.auto_refresh_seconds or 20),
            'match_overrides': config.match_overrides if isinstance(config.match_overrides, dict) else {},
        }

    @staticmethod
    def _list_matches(tournament):
        try:
            rows = Match.objects.filter(
                tournament=tournament,
                is_deleted=False,
            ).order_by('round_number', 'match_number')[:120]
            rows = list(rows)
        except DatabaseError:
            logger.exception('Match list lookup failed for tournament %s', tournament.pk)
            return []

        matches = []
        for row in rows:
            lobby = row.lobby_info if isinstance(row.lobby_info, dict) else {}
            football = lobby.get('football_stats') if isinstance(lobby.get('football_stats'), dict) else None

            matches.append({
                'id': row.id,
                'round_number': row.round_number,
                'match_number': row.match_number,
                'participant1_name': row.participant1_name or 'Team A',
                'participant2_name': row.participant2_name or 'Team B',
                'participant1_score': int(row.participant1_score or 0),
                'participant2_score': int(row.participant2_score or 0),
                'state': row.state,
                'scheduled_time': row.scheduled_time.isoformat() if row.scheduled_time else None,
                'is_completed': row.state in ('completed', 'forfeit'),
                'has_football_stats': bool(football),
                'has_evidence': TOCMatchCenterService._has_match_evidence(row),
            })
        return matches

    @staticmethod
    def _has_match_evidence(match):
        """True if any media exists OR a result submission has a screenshot."""
        try:
            from apps.tournaments.models import MatchResultSubmission
        except (ImportError, AttributeError):
            MatchResultSubmission = None

        try:
            if match.media.exists():
                return True
        except (AttributeError, DatabaseError):
            pass

        if MatchResultSubmission is not None:
            try:
                qs = MatchResultSubmission.objects.filter(match=match)
                if qs.exclude(proof_screenshot_url='').exists():
                    return True
                if qs.exclude(proof_screenshot__isnull=True).exclude(proof_screenshot='').exists():
                    return True
            except (DatabaseError, AttributeError):
                pass
        return False

    @staticmethod
    def _normalize_overrides(raw_overrides):
        """Return ``(normalized_overrides, invalid_urls)``.

        ``invalid_urls`` lets the TOC UI surface URL validation failures
        instead of silently dropping them.
        """
        normalized = {}
        invalid_urls = []
        if not isinstance(raw_overrides, dict):
            return normalized, invalid_urls

        text_specs = (
            ('headline', 120),
            ('subline', 120),
            ('poll_question', 180),
            ('poll_option_a', 80),
            ('poll_option_b', 80),
        )
        url_specs = (
            ('stream_url', 'Stream / VOD URL'),
            ('featured_media_url', 'Featured Media URL'),
        )

        for raw_match_id, raw_payload in raw_overrides.items():
            match_id = str(raw_match_id or '').strip()
            if not match_id.isdigit():
                continue

            source = raw_payload if isinstance(raw_payload, dict) else {}
            item = {}

            for key, max_length in text_specs:
                if key not in source:
                    continue
                value = TOCMatchCenterService._as_text(
                    source.get(key),
                    fallback='',
                    max_length=max_length,
                )
                if value:
                    item[key] = value

            for key, label in url_specs:
                if key not in source:
                    continue
                raw = str(source.get(key) or '').strip()
                if not raw:
                    continue
                safe = TOCMatchCenterService._as_safe_url(raw)
                if safe:
                    item[key] = safe
                else:
                    invalid_urls.append({'match_id': match_id, 'field': key, 'label': label})
                    logger.info(
                        'Match Center override URL rejected for match %s field %s', match_id, key,
                    )

            for key in ('show_media', 'show_stats', 'show_fan_pulse'):
                if key in source:
                    item[key] = TOCMatchCenterService._as_bool(source.get(key), fallback=True)

            if item:
                normalized[match_id] = item

        return normalized, invalid_urls

    @staticmethod
    def _as_text(value, *, fallback='', max_length=240):
        text = str(value or '').strip()
        if not text:
            return str(fallback or '')[:max_length]
        return text[:max_length]

    @staticmethod
    def _as_int(value, *, fallback=0, minimum=None, maximum=None):
        try:
            parsed = int(float(value))
        except (TypeError, ValueError):
            parsed = int(fallback)

        if minimum is not None:
            parsed = max(minimum, parsed)
        if maximum is not None:
            parsed = min(maximum, parsed)
        return parsed

    @staticmethod
    def _as_bool(value, *, fallback=False):
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

    @staticmethod
    def _as_safe_url(value):
        url = str(value or '').strip()
        if not url:
            return ''

        highlight = validate_highlight_url(url)
        if highlight.get('valid'):
            return url[:500]

        stream = validate_stream_url(url)
        if stream.get('valid'):
            return url[:500]

        return ''
