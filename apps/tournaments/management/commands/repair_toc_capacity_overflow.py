"""
Detect and repair TOC capacity overflows caused by accidental reactivation.

A common failure mode is: a disqualified registration gets re-confirmed by a
payment verification action, pushing active registrations above max_participants.

This command reports over-cap tournaments and can safely auto-correct entries
that carry disqualification metadata.

Usage:
    python manage.py repair_toc_capacity_overflow
    python manage.py repair_toc_capacity_overflow --slug efootball-genesis-cup
    python manage.py repair_toc_capacity_overflow --apply
    python manage.py repair_toc_capacity_overflow --slug efootball-genesis-cup --apply --reason "Restored DQ after verify bug"
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.tournaments.models.registration import Registration
from apps.tournaments.models.tournament import Tournament


ACTIVE_STATUSES = (
    Registration.PENDING,
    Registration.PAYMENT_SUBMITTED,
    Registration.CONFIRMED,
)


class Command(BaseCommand):
    help = "Detect/repair TOC capacity overflows by reverting suspicious reactivated registrations."

    def add_arguments(self, parser):
        parser.add_argument(
            '--slug',
            type=str,
            default='',
            help='Optional tournament slug scope. If omitted, scans all tournaments.',
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Apply repairs. Without this flag the command runs as dry-run only.',
        )
        parser.add_argument(
            '--reason',
            type=str,
            default='Restored disqualification after accidental reactivation.',
            help='Reason text recorded in registration_data when applying fixes.',
        )

    def handle(self, *args, **options):
        slug = (options.get('slug') or '').strip()
        apply_changes = bool(options.get('apply'))
        reason = (options.get('reason') or '').strip() or 'Restored disqualification after accidental reactivation.'

        t_qs = Tournament.objects.all().order_by('id')
        if slug:
            t_qs = t_qs.filter(slug=slug)

        tournaments = list(t_qs)
        if not tournaments:
            self.stdout.write(self.style.WARNING('No tournaments matched the provided scope.'))
            return

        checked = 0
        overflow_count = 0
        repaired_total = 0

        mode_label = 'APPLY' if apply_changes else 'DRY-RUN'
        self.stdout.write(self.style.WARNING(f'Running in {mode_label} mode'))

        for tournament in tournaments:
            checked += 1
            active_qs = Registration.objects.filter(
                tournament=tournament,
                is_deleted=False,
                status__in=ACTIVE_STATUSES,
            )
            active_count = active_qs.count()
            max_participants = int(getattr(tournament, 'max_participants', 0) or 0)

            if max_participants <= 0:
                continue
            if active_count <= max_participants:
                continue

            overflow = active_count - max_participants
            overflow_count += 1

            self.stdout.write('')
            self.stdout.write(self.style.WARNING(
                f"[{tournament.slug}] active={active_count} max={max_participants} overflow={overflow}"
            ))

            confirmed_regs = list(
                Registration.objects.filter(
                    tournament=tournament,
                    is_deleted=False,
                    status=Registration.CONFIRMED,
                ).order_by('-updated_at', '-id')
            )

            suspicious = []
            for reg in confirmed_regs:
                data = reg.registration_data if isinstance(reg.registration_data, dict) else {}
                has_disq_meta = bool(data.get('disqualified_at') or data.get('disqualification_reason'))
                was_rejected_before = bool(data.get('previous_status') == Registration.REJECTED)
                if has_disq_meta or was_rejected_before:
                    suspicious.append(reg)

            if not suspicious:
                self.stdout.write(self.style.ERROR(
                    '  No safe auto-repair candidate found (missing disqualification metadata). Manual review required.'
                ))
                continue

            candidates = suspicious[:overflow]
            self.stdout.write(f'  Safe candidate(s) detected: {len(suspicious)}; selecting {len(candidates)} for overflow correction')

            for reg in candidates:
                username = reg.user.username if reg.user else f'registration#{reg.id}'
                self.stdout.write(f'   - reg_id={reg.id} user={username} status={reg.status}')

            if not apply_changes:
                continue

            with transaction.atomic():
                for reg in candidates:
                    data = reg.registration_data if isinstance(reg.registration_data, dict) else {}
                    if not data.get('disqualified_at'):
                        data['disqualified_at'] = timezone.now().isoformat()
                    data['disqualification_reason'] = reason
                    data['disqualified_by'] = data.get('disqualified_by') or 'system-capacity-repair'
                    data['capacity_repair'] = {
                        'at': timezone.now().isoformat(),
                        'source': 'repair_toc_capacity_overflow',
                    }
                    reg.registration_data = data
                    reg.status = Registration.REJECTED
                    reg.save(update_fields=['status', 'registration_data', 'updated_at'])
                    repaired_total += 1

            new_active = Registration.objects.filter(
                tournament=tournament,
                is_deleted=False,
                status__in=ACTIVE_STATUSES,
            ).count()
            self.stdout.write(self.style.SUCCESS(
                f'  Applied: repaired={len(candidates)} new_active={new_active}'
            ))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Tournaments checked: {checked}'))
        self.stdout.write(self.style.SUCCESS(f'Over-cap tournaments: {overflow_count}'))
        self.stdout.write(self.style.SUCCESS(f'Registrations repaired: {repaired_total}'))

        if not apply_changes:
            self.stdout.write(self.style.WARNING('Dry-run complete. Re-run with --apply to persist fixes.'))
