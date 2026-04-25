"""
Management command: repair_bracket_match_links

Safely links BracketNode.match_id and Match.bracket_id for legacy tournaments
where generation left the relationships half-populated. Idempotent and
non-destructive — can be run repeatedly without side effects.

Usage
-----

    # Single tournament, dry-run first:
    python manage.py repair_bracket_match_links --slug efootball-genesis-cup --dry-run

    # Actually repair:
    python manage.py repair_bracket_match_links --slug efootball-genesis-cup

    # All tournaments:
    python manage.py repair_bracket_match_links --all

Do NOT schedule this as a recurring task on Celery; the repair is a one-off
for each tournament whose bracket was generated before `match_id` linkage
was added to the generator.
"""

import json

from django.core.management.base import BaseCommand, CommandError

from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.bracket_repair_service import BracketRepairService


class Command(BaseCommand):
    help = 'Safely link missing BracketNode.match_id and Match.bracket_id FKs.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', help='Tournament slug to repair.')
        parser.add_argument('--all', action='store_true',
                            help='Repair every tournament (slow; use sparingly).')
        parser.add_argument('--dry-run', action='store_true',
                            help='Report would-be changes without writing.')
        parser.add_argument('--force-participants', action='store_true',
                            help=(
                                'OVERWRITE non-empty Match participant slots '
                                'from the linked BracketNode. Dangerous — only '
                                'pass when you know legacy participant data '
                                'on Match rows is wrong and the node tree is '
                                'authoritative. Default: off (safe).'
                            ))

    def handle(self, *args, **options):
        slug = options.get('slug')
        do_all = bool(options.get('all'))
        dry_run = bool(options.get('dry_run'))
        force_participants = bool(options.get('force_participants'))

        if not slug and not do_all:
            raise CommandError('Pass --slug <slug> or --all.')

        if slug:
            qs = Tournament.objects.filter(slug=slug)
            if not qs.exists():
                raise CommandError(f'No tournament found with slug={slug!r}.')
        else:
            qs = Tournament.objects.all()

        total = {
            'linked_nodes': 0,
            'backfilled_matches': 0,
            'participant_slots_backfilled': 0,
            'winners_backfilled': 0,
            'skipped_non_empty_participants': 0,
        }
        per_tournament = []
        for tournament in qs.iterator():
            report = BracketRepairService.repair(
                tournament,
                dry_run=dry_run,
                force_participants=force_participants,
            )
            total['linked_nodes'] += report.linked_nodes
            total['backfilled_matches'] += report.backfilled_matches
            total['participant_slots_backfilled'] += report.participant_slots_backfilled
            total['winners_backfilled'] += report.winners_backfilled
            total['skipped_non_empty_participants'] += report.skipped_non_empty_participants
            per_tournament.append({
                'slug': tournament.slug,
                **report.to_dict(),
            })
            self.stdout.write(
                f"{tournament.slug}: "
                f"linked={report.linked_nodes} "
                f"backfilled_bracket_fk={report.backfilled_matches} "
                f"slots_backfilled={report.participant_slots_backfilled} "
                f"winners_backfilled={report.winners_backfilled} "
                f"skipped={report.skipped_non_empty_participants} "
                f"unresolved={len(report.unresolved_nodes)} "
                f"ambiguous={len(report.ambiguous_matches)}"
                + (" [dry-run]" if dry_run else "")
                + (" [force-participants]" if force_participants else "")
            )
            for change in report.proposed_changes[:25]:
                self.stdout.write(
                    f"    match={change['match_id']} node={change['node_id']}: "
                    + "; ".join(change['changes'])
                )
            if len(report.proposed_changes) > 25:
                self.stdout.write(
                    f"    ... ({len(report.proposed_changes) - 25} more changes)"
                )
            for err in report.errors:
                self.stderr.write(f"  ! {err}")

        self.stdout.write(self.style.SUCCESS(
            "\nTotal "
            f"linked_nodes={total['linked_nodes']} "
            f"backfilled_matches={total['backfilled_matches']} "
            f"participant_slots_backfilled={total['participant_slots_backfilled']} "
            f"winners_backfilled={total['winners_backfilled']} "
            f"skipped={total['skipped_non_empty_participants']}"
            + (" (dry-run)" if dry_run else "")
        ))
        return json.dumps({'total': total, 'per_tournament': per_tournament})
