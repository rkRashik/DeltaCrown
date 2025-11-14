"""
Management Command: recalc_all_wallets

Implements: MODULE_7.1_KICKOFF.md - Admin Integration (Step 5)

Detects and corrects balance drift between wallet.cached_balance and ledger sum.

Usage:
    python manage.py recalc_all_wallets [--dry-run]

Exit Codes:
    0: No drift detected (all wallets accurate)
    1: Drift detected (dry-run or corrected)
    2: Error (exception during execution)

PII Discipline: Output contains wallet IDs only (no usernames, emails, or PII).
"""
# Implements: Documents/ExecutionPlan/Modules/MODULE_7.1_KICKOFF.md

import sys
from django.core.management.base import BaseCommand
from django.db.models import Sum
from apps.economy.models import DeltaCrownWallet, DeltaCrownTransaction


class Command(BaseCommand):
    help = "Recalculate and reconcile all wallet balances (detect/fix drift)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Detect drift but do not modify database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 60)
        self.stdout.write(f"Wallet Balance Reconciliation {'(DRY RUN)' if dry_run else '(LIVE)'}")
        self.stdout.write("=" * 60)
        self.stdout.write("")

        # Fetch all wallets
        wallets = DeltaCrownWallet.objects.all().select_related('profile')
        total_wallets = wallets.count()
        drift_wallets = []
        corrected_wallets = []
        
        self.stdout.write(f"Scanning {total_wallets} wallets...")
        self.stdout.write("")

        for wallet in wallets:
            # Calculate ledger sum
            ledger_sum = DeltaCrownTransaction.objects.filter(wallet=wallet).aggregate(
                total=Sum('amount')
            )['total'] or 0
            
            cached = int(wallet.cached_balance)
            ledger = int(ledger_sum)
            
            if cached != ledger:
                drift_wallets.append((wallet.id, cached, ledger))
                
                if not dry_run:
                    # Correct drift using recalc_and_save (atomic with row lock)
                    wallet.recalc_and_save()
                    corrected_wallets.append(wallet.id)
                    self.stdout.write(
                        self.style.WARNING(
                            f"[CORRECTED] Wallet {wallet.id}: {cached} → {ledger} "
                            f"(drift: {ledger - cached:+d})"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"[DRIFT] Wallet {wallet.id}: cached={cached}, ledger={ledger}, "
                            f"drift={ledger - cached:+d}"
                        )
                    )

        self.stdout.write("")
        self.stdout.write("=" * 60)
        
        if drift_wallets:
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(
                        f"Drift detected in {len(drift_wallets)} wallet(s). "
                        f"Run without --dry-run to correct."
                    )
                )
                self.stdout.write("")
                self.stdout.write("Summary (would correct):")
                for wid, cached, ledger in drift_wallets:
                    self.stdout.write(f"  - Wallet {wid}: {cached} → {ledger}")
                
                # Exit code 1 (drift detected)
                sys.exit(1)
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Corrected {len(corrected_wallets)} wallet(s)."
                    )
                )
                self.stdout.write("")
                self.stdout.write("Summary (corrected):")
                for wid in corrected_wallets:
                    self.stdout.write(f"  - Wallet {wid}")
                
                # Exit code 1 (drift was detected, now corrected)
                sys.exit(1)
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"No drift detected. All {total_wallets} wallet(s) accurate."
                )
            )
            # Exit code 0 (no drift)
            sys.exit(0)
