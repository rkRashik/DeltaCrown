"""
Management command to repair denormalized participant names in BracketNode and Match.

Fixes "Team #XX" placeholder names by resolving real team names from OrgTeam.
Safe to run multiple times (idempotent).

Usage:
    python manage.py repair_bracket_names
    python manage.py repair_bracket_names --dry-run
"""
import re

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.tournaments.models.bracket import BracketNode
from apps.tournaments.models.match import Match


TEAM_HASH_PATTERN = re.compile(r'^Team #(\d+)$')


class Command(BaseCommand):
    help = 'Repair "Team #XX" placeholder names in BracketNode and Match records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without modifying the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        prefix = '[DRY RUN] ' if dry_run else ''

        # Collect all broken node participant names
        broken_nodes = BracketNode.objects.filter(
            participant1_name__regex=r'^Team #\d+$'
        ) | BracketNode.objects.filter(
            participant2_name__regex=r'^Team #\d+$'
        )

        broken_matches = Match.objects.filter(
            participant1_name__regex=r'^Team #\d+$'
        ) | Match.objects.filter(
            participant2_name__regex=r'^Team #\d+$'
        )

        # Collect all team IDs that need resolution
        team_ids = set()
        for node in broken_nodes:
            for name in (node.participant1_name, node.participant2_name):
                m = TEAM_HASH_PATTERN.match(name or '')
                if m:
                    team_ids.add(int(m.group(1)))

        for match in broken_matches:
            for name in (match.participant1_name, match.participant2_name):
                m = TEAM_HASH_PATTERN.match(name or '')
                if m:
                    team_ids.add(int(m.group(1)))

        if not team_ids:
            self.stdout.write(self.style.SUCCESS('No broken names found. Nothing to repair.'))
            return

        # Resolve team names
        from apps.organizations.models.team import Team as OrgTeam
        team_map = dict(
            OrgTeam.objects.filter(id__in=team_ids).values_list('id', 'name')
        )

        self.stdout.write(f'{prefix}Found {len(team_ids)} team IDs to resolve: {team_ids}')
        self.stdout.write(f'{prefix}Resolved {len(team_map)} team names: {team_map}')

        node_count = 0
        match_count = 0

        with transaction.atomic():
            # Fix BracketNode records
            for node in broken_nodes:
                changed = False
                for field in ('participant1_name', 'participant2_name'):
                    val = getattr(node, field) or ''
                    m = TEAM_HASH_PATTERN.match(val)
                    if m:
                        tid = int(m.group(1))
                        real_name = team_map.get(tid)
                        if real_name:
                            self.stdout.write(
                                f'{prefix}  BracketNode {node.id} {field}: '
                                f'"{val}" -> "{real_name}"'
                            )
                            if not dry_run:
                                setattr(node, field, real_name)
                            changed = True
                if changed and not dry_run:
                    node.save(update_fields=['participant1_name', 'participant2_name'])
                    node_count += 1

            # Fix Match records
            for match in broken_matches:
                changed = False
                for field in ('participant1_name', 'participant2_name'):
                    val = getattr(match, field) or ''
                    m = TEAM_HASH_PATTERN.match(val)
                    if m:
                        tid = int(m.group(1))
                        real_name = team_map.get(tid)
                        if real_name:
                            self.stdout.write(
                                f'{prefix}  Match {match.id} {field}: '
                                f'"{val}" -> "{real_name}"'
                            )
                            if not dry_run:
                                setattr(match, field, real_name)
                            changed = True
                if changed and not dry_run:
                    match.save(update_fields=['participant1_name', 'participant2_name'])
                    match_count += 1

            if dry_run:
                # Roll back in dry-run mode
                transaction.set_rollback(True)

        self.stdout.write(self.style.SUCCESS(
            f'{prefix}Repaired {node_count} BracketNode(s) and {match_count} Match(es).'
        ))
