"""
Registration Verification Service
=================================
Automated pre-verification checks for tournament registrations.
Detects issues that organizers need to review before confirming teams.

Checks performed:
  - Duplicate game IDs across registrations in the same tournament
  - Missing/empty game IDs on starters
  - Roster size compliance (min/max)
  - Banned/suspended players
  - Captain/IGL assignment
  - Duplicate user across multiple teams
  - Player role completeness
"""
import logging
from collections import defaultdict
from typing import Any

from django.db.models import Q

from apps.tournaments.models import Registration

logger = logging.getLogger(__name__)


class RegistrationVerificationService:
    """Run automated integrity checks on tournament registrations."""

    SEVERITY_CRITICAL = 'critical'   # Blocks confirmation
    SEVERITY_WARNING = 'warning'     # Needs review
    SEVERITY_INFO = 'info'           # Informational

    @classmethod
    def verify_tournament(cls, tournament) -> dict[str, Any]:
        """
        Run all checks for a tournament.
        Returns dict with:
          - flags: list of {reg_id, severity, code, message, details}
          - summary: {critical: int, warning: int, info: int, clean: int}
          - per_registration: {reg_id: [flags]}
        """
        registrations = Registration.objects.filter(
            tournament=tournament,
            is_deleted=False,
        ).exclude(status__in=['rejected', 'cancelled']).select_related('user')

        flags = []
        per_reg = defaultdict(list)

        # Collect all game IDs and lineup data
        game_id_map = defaultdict(list)  # game_id -> [(reg_id, display_name)]
        user_team_map = defaultdict(list)  # user_id -> [(reg_id, team_id)]

        for reg in registrations:
            reg_flags = []
            snapshot = reg.lineup_snapshot or []
            rd = reg.registration_data or {}

            # ── Solo registrations ──
            if not reg.team_id:
                game_id = rd.get('game_id', '').strip()
                if game_id:
                    game_id_map[game_id.lower()].append((reg.id, rd.get('display_name', reg.user.username if reg.user else 'Unknown')))
                else:
                    reg_flags.append(cls._flag(
                        reg.id, cls.SEVERITY_WARNING, 'missing_game_id',
                        'Missing game ID',
                        'No game ID provided in registration.'
                    ))
                if reg.user_id:
                    user_team_map[reg.user_id].append((reg.id, None))
                continue

            # ── Team registrations ──
            has_captain = False
            starters = 0
            subs = 0

            for entry in snapshot:
                uid = entry.get('user_id')
                name = entry.get('display_name', entry.get('username', 'Unknown'))
                slot = entry.get('roster_slot', 'STARTER')
                gid_val = entry.get('game_id', '').strip()

                if uid:
                    user_team_map[uid].append((reg.id, reg.team_id))

                # Track game IDs for duplicates
                if gid_val:
                    game_id_map[gid_val.lower()].append((reg.id, name))
                elif slot in ('STARTER', 'SUBSTITUTE'):
                    reg_flags.append(cls._flag(
                        reg.id, cls.SEVERITY_WARNING, 'missing_game_id',
                        f'{name}: Missing game ID',
                        f'Player {name} ({slot}) has no game ID set.'
                    ))

                if slot == 'STARTER':
                    starters += 1
                elif slot == 'SUBSTITUTE':
                    subs += 1

                if entry.get('is_igl'):
                    has_captain = True

            # Check captain assignment from registration_data too
            coord_role = rd.get('coordinator_role', '')
            if 'captain' in coord_role.lower() or 'igl' in coord_role.lower():
                has_captain = True

            if not has_captain:
                reg_flags.append(cls._flag(
                    reg.id, cls.SEVERITY_WARNING, 'no_captain',
                    'No Captain/IGL assigned',
                    'This team has no designated captain or IGL.'
                ))

            # Roster size check
            try:
                from apps.core.services import game_service
                rl = game_service.get_roster_limits(tournament.game)
                min_size = rl.get('min_team_size', 1)
                max_size = rl.get('max_roster_size', 20)
            except Exception:
                min_size = 1
                max_size = 20

            total = starters + subs
            if starters < min_size:
                reg_flags.append(cls._flag(
                    reg.id, cls.SEVERITY_CRITICAL, 'roster_undersize',
                    f'Not enough starters ({starters}/{min_size})',
                    f'Team needs at least {min_size} starters but only has {starters}.'
                ))
            if total > max_size:
                reg_flags.append(cls._flag(
                    reg.id, cls.SEVERITY_CRITICAL, 'roster_oversize',
                    f'Roster exceeds max ({total}/{max_size})',
                    f'Team has {total} members but max allowed is {max_size}.'
                ))

            # Player role completeness
            missing_roles = [
                e.get('display_name', 'Unknown')
                for e in snapshot
                if e.get('roster_slot') == 'STARTER' and not e.get('player_role')
            ]
            if missing_roles:
                reg_flags.append(cls._flag(
                    reg.id, cls.SEVERITY_INFO, 'missing_player_role',
                    f'{len(missing_roles)} player(s) missing in-game role',
                    f'Players without roles: {", ".join(missing_roles[:5])}'
                ))

            flags.extend(reg_flags)
            per_reg[reg.id].extend(reg_flags)

        # ── Cross-registration checks ──

        # Duplicate game IDs
        for gid, entries in game_id_map.items():
            if len(entries) > 1:
                reg_ids = list({e[0] for e in entries})
                names = [e[1] for e in entries]
                for rid in reg_ids:
                    f = cls._flag(
                        rid, cls.SEVERITY_CRITICAL, 'duplicate_game_id',
                        f'Duplicate game ID: {gid}',
                        f'Game ID "{gid}" appears in {len(entries)} registrations. '
                        f'Players: {", ".join(names[:5])}'
                    )
                    flags.append(f)
                    per_reg[rid].append(f)

        # Duplicate users across teams
        for uid, entries in user_team_map.items():
            if len(entries) > 1:
                team_ids = [e[1] for e in entries if e[1]]
                if len(set(team_ids)) > 1:  # Same user in different teams
                    reg_ids = list({e[0] for e in entries})
                    for rid in reg_ids:
                        f = cls._flag(
                            rid, cls.SEVERITY_CRITICAL, 'duplicate_user',
                            f'Player registered in multiple teams',
                            f'User #{uid} appears in {len(entries)} different team registrations.'
                        )
                        flags.append(f)
                        per_reg[rid].append(f)

        # ── Banned/suspended player check ──
        try:
            from apps.moderation.models import UserSanction
            active_bans = UserSanction.objects.filter(
                is_active=True,
                sanction_type__in=['ban', 'suspension', 'tournament_ban'],
            ).values_list('user_id', flat=True)
            banned_ids = set(active_bans)

            for uid in banned_ids:
                if uid in user_team_map:
                    for rid, _ in user_team_map[uid]:
                        f = cls._flag(
                            rid, cls.SEVERITY_CRITICAL, 'banned_player',
                            f'Banned/suspended player detected',
                            f'User #{uid} has an active platform ban or suspension.'
                        )
                        flags.append(f)
                        per_reg[rid].append(f)
        except Exception:
            pass  # Moderation module may not exist

        # ── Summary ──
        critical = sum(1 for f in flags if f['severity'] == cls.SEVERITY_CRITICAL)
        warning = sum(1 for f in flags if f['severity'] == cls.SEVERITY_WARNING)
        info = sum(1 for f in flags if f['severity'] == cls.SEVERITY_INFO)
        clean = registrations.count() - len(per_reg)

        return {
            'flags': flags,
            'summary': {
                'critical': critical,
                'warning': warning,
                'info': info,
                'clean': max(0, clean),
                'total_registrations': registrations.count(),
            },
            'per_registration': dict(per_reg),
        }

    @classmethod
    def verify_single(cls, registration) -> list[dict]:
        """Run checks for a single registration. Returns list of flags."""
        # Quick single-reg check
        result = cls.verify_tournament(registration.tournament)
        return result['per_registration'].get(registration.id, [])

    @staticmethod
    def _flag(reg_id, severity, code, message, details=''):
        return {
            'reg_id': reg_id,
            'severity': severity,
            'code': code,
            'message': message,
            'details': details,
        }
