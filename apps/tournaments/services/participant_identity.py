"""Canonical participant identity resolution for tournament read models.

Match rows in legacy tournaments may store participant IDs as user IDs or
team IDs while result/reward rows use Registration IDs. This service keeps the
display name and image resolution rules in one place so bracket, schedule,
matches, and rewards do not drift.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from django.contrib.auth import get_user_model

from apps.tournaments.models.registration import Registration


def _to_int(value: Any) -> Optional[int]:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _media_url(field: Any) -> str:
    if not field:
        return ''
    try:
        raw = field.url
    except Exception:
        raw = str(field or '')
    raw = str(raw or '').strip()
    if not raw:
        return ''
    if raw.startswith(('http://', 'https://', '/')):
        return raw
    return '/media/' + raw


def _user_name(user) -> str:
    if not user:
        return ''
    try:
        profile = getattr(user, 'profile', None)
        display_name = str(getattr(profile, 'display_name', '') or '').strip()
        if display_name:
            return display_name
    except Exception:
        pass
    return str(getattr(user, 'username', '') or getattr(user, 'email', '') or '').strip()


def _user_avatar(user) -> str:
    if not user:
        return ''
    try:
        profile = getattr(user, 'profile', None)
        avatar = getattr(profile, 'avatar', None)
        return _media_url(avatar)
    except Exception:
        return ''


def _registration_name(registration: Optional[Registration], *, team=None) -> str:
    if not registration:
        return ''
    if team and getattr(team, 'name', None):
        return str(team.name).strip()
    data = getattr(registration, 'registration_data', None) or {}
    if isinstance(data, dict):
        for key in (
            'display_name',
            'team_name',
            'participant_name',
            'captain_display_name',
        ):
            value = str(data.get(key) or '').strip()
            if value:
                return value
        guest_team = data.get('guest_team')
        if isinstance(guest_team, dict):
            value = str(guest_team.get('team_name') or guest_team.get('name') or '').strip()
            if value:
                return value
    return _user_name(getattr(registration, 'user', None)) or (
        f'Team {registration.team_id}' if registration.team_id else f'Registration #{registration.pk}'
    )


class ParticipantIdentityService:
    """Resolve participant names and images keyed for the calling surface."""

    @classmethod
    def for_match_participants(
        cls,
        tournament,
        participant_ids: Iterable[Any],
    ) -> Dict[int, Dict[str, Any]]:
        """Resolve IDs stored on Match/BracketNode rows.

        Solo events store user IDs in match slots. Team events store team IDs.
        As a defensive fallback, registration IDs are also accepted.
        """
        ids = {pid for pid in (_to_int(value) for value in participant_ids or []) if pid}
        if not ids or tournament is None:
            return {}

        is_team = str(getattr(tournament, 'participation_type', '') or '').lower() == 'team'
        out: Dict[int, Dict[str, Any]] = {}

        if is_team:
            out.update(cls._team_identities(tournament, ids))
            missing = ids - set(out.keys())
            if missing:
                for reg_id, identity in cls.for_registrations(tournament, missing).items():
                    out.setdefault(reg_id, identity)
            return out

        out.update(cls._user_identities(tournament, ids))
        missing = ids - set(out.keys())
        if missing:
            for reg_id, identity in cls.for_registrations(tournament, missing).items():
                out.setdefault(reg_id, identity)
        return out

    @classmethod
    def for_registrations(
        cls,
        tournament,
        registration_ids: Iterable[Any],
    ) -> Dict[int, Dict[str, Any]]:
        """Resolve identities keyed by Registration.id."""
        ids = {rid for rid in (_to_int(value) for value in registration_ids or []) if rid}
        if not ids or tournament is None:
            return {}

        registrations = list(
            Registration.objects.filter(
                tournament=tournament,
                id__in=ids,
                is_deleted=False,
            )
            .select_related('user', 'user__profile')
            .order_by('id')
        )
        team_ids = {int(reg.team_id) for reg in registrations if getattr(reg, 'team_id', None)}
        teams = cls._load_teams(team_ids)
        out: Dict[int, Dict[str, Any]] = {}
        for reg in registrations:
            team = teams.get(int(reg.team_id)) if getattr(reg, 'team_id', None) else None
            out[int(reg.id)] = cls._identity_from_registration(reg, team=team)
        return out

    @classmethod
    def _team_identities(cls, tournament, team_ids: set[int]) -> Dict[int, Dict[str, Any]]:
        teams = cls._load_teams(team_ids)
        registrations = {
            int(reg.team_id): reg
            for reg in Registration.objects.filter(
                tournament=tournament,
                team_id__in=team_ids,
                is_deleted=False,
            )
            .select_related('user', 'user__profile')
            .order_by('id')
            if getattr(reg, 'team_id', None)
        }
        out: Dict[int, Dict[str, Any]] = {}
        for team_id, team in teams.items():
            reg = registrations.get(team_id)
            logo = cls._team_logo(team)
            out[team_id] = {
                'id': team_id,
                'participant_id': team_id,
                'registration_id': int(reg.id) if reg else None,
                'team_id': team_id,
                'user_id': getattr(reg, 'user_id', None) if reg else None,
                'name': str(getattr(team, 'name', '') or _registration_name(reg) or f'Team {team_id}').strip(),
                'subtitle': str(getattr(team, 'tag', '') or '').strip(),
                'image_url': logo or _user_avatar(getattr(reg, 'user', None)),
                'logo_url': logo,
                'avatar_url': _user_avatar(getattr(reg, 'user', None)),
                'source': 'team',
            }
        return out

    @classmethod
    def _user_identities(cls, tournament, user_ids: set[int]) -> Dict[int, Dict[str, Any]]:
        User = get_user_model()
        users = {
            int(user.id): user
            for user in User.objects.filter(id__in=user_ids).select_related('profile')
        }
        registrations = {
            int(reg.user_id): reg
            for reg in Registration.objects.filter(
                tournament=tournament,
                user_id__in=user_ids,
                is_deleted=False,
            )
            .select_related('user', 'user__profile')
            .order_by('id')
            if getattr(reg, 'user_id', None)
        }
        out: Dict[int, Dict[str, Any]] = {}
        for user_id, user in users.items():
            reg = registrations.get(user_id)
            avatar = _user_avatar(user)
            out[user_id] = {
                'id': user_id,
                'participant_id': user_id,
                'registration_id': int(reg.id) if reg else None,
                'team_id': getattr(reg, 'team_id', None) if reg else None,
                'user_id': user_id,
                'name': _registration_name(reg) or _user_name(user) or f'User {user_id}',
                'subtitle': str(getattr(user, 'email', '') or '').strip(),
                'image_url': avatar,
                'logo_url': avatar,
                'avatar_url': avatar,
                'source': 'user',
            }
        return out

    @classmethod
    def _identity_from_registration(cls, registration: Registration, *, team=None) -> Dict[str, Any]:
        user = getattr(registration, 'user', None)
        team_logo = cls._team_logo(team) if team else ''
        avatar = _user_avatar(user)
        image = team_logo or avatar
        return {
            'id': int(registration.id),
            'participant_id': int(registration.team_id or registration.user_id or registration.id),
            'registration_id': int(registration.id),
            'team_id': int(registration.team_id) if getattr(registration, 'team_id', None) else None,
            'user_id': int(registration.user_id) if getattr(registration, 'user_id', None) else None,
            'name': _registration_name(registration, team=team),
            'subtitle': str(getattr(team, 'tag', '') or getattr(user, 'email', '') or '').strip(),
            'image_url': image,
            'logo_url': team_logo or avatar,
            'avatar_url': avatar,
            'source': 'registration',
        }

    @staticmethod
    def _load_teams(team_ids: Iterable[int]) -> Dict[int, Any]:
        ids = {tid for tid in (_to_int(value) for value in team_ids or []) if tid}
        if not ids:
            return {}
        try:
            from apps.organizations.models import Team

            return {
                int(team.id): team
                for team in Team.objects.filter(id__in=ids).select_related('organization')
            }
        except Exception:
            return {}

    @staticmethod
    def _team_logo(team) -> str:
        if not team:
            return ''
        logo = _media_url(getattr(team, 'logo', None))
        if logo:
            return logo
        try:
            organization = getattr(team, 'organization', None)
            if organization and getattr(organization, 'enforce_brand', False):
                return _media_url(getattr(organization, 'logo', None))
        except Exception:
            return ''
        return ''


__all__ = ['ParticipantIdentityService']
