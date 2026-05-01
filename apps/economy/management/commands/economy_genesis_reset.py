# apps/economy/management/commands/economy_genesis_reset.py
"""
Genesis Reset — wipes all coin transaction history and zeroes every wallet.

USE CASE: One-time data cleanup to remove coins that were minted without a
corresponding Master Treasury debit (the "void minting" bug identified in the
Phase 1 audit). After running this command all wallets start from zero with
a valid Master Treasury in place.

DANGER LEVEL: IRREVERSIBLE. Requires explicit --confirm flag.

Usage:
    python manage.py economy_genesis_reset --confirm
    python manage.py economy_genesis_reset --confirm --dry-run   # preview only
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction as db_transaction


class Command(BaseCommand):
    help = (
        "⚠️  DESTRUCTIVE: Delete all DeltaCrown transaction history and reset every "
        "wallet balance to zero. Ensures the Master Treasury wallet exists. "
        "Requires --confirm to execute."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            default=False,
            help="Must be passed explicitly to authorise the destructive reset.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            dest="dry_run",
            help="Print what would happen without making any database changes.",
        )

    def handle(self, *args, **options):
        confirmed = options["confirm"]
        dry_run = options["dry_run"]

        # ------------------------------------------------------------------ #
        # Safety gate                                                          #
        # ------------------------------------------------------------------ #
        if not confirmed:
            raise CommandError(
                "\n"
                "[ERROR] Refusing to run without --confirm.\n"
                "\n"
                "This command will:\n"
                "  * DELETE every DeltaCrownTransaction row (complete ledger wipe)\n"
                "  * Reset cached_balance, pending_balance, lifetime_earnings -> 0\n"
                "    on EVERY DeltaCrownWallet (users and treasury)\n"
                "  * Ensure the Master Treasury wallet exists\n"
                "\n"
                "This action is IRREVERSIBLE. If you understand the consequences, run:\n"
                "\n"
                "    python manage.py economy_genesis_reset --confirm\n"
            )

        # Lazy imports so management framework loads before models
        from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
        from apps.economy.services import get_master_treasury

        # ------------------------------------------------------------------ #
        # Gather pre-reset stats for the summary                               #
        # ------------------------------------------------------------------ #
        tx_count = DeltaCrownTransaction.objects.count()
        user_wallets = DeltaCrownWallet.objects.filter(is_treasury=False)
        treasury_exists = DeltaCrownWallet.objects.filter(is_treasury=True).exists()

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("  DeltaCrown Economy -- Genesis Reset")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Transactions to delete : {tx_count:,}")
        self.stdout.write(f"  User wallets to reset  : {user_wallets.count():,}")
        self.stdout.write(f"  Treasury wallet exists : {'Yes' if treasury_exists else 'No (will be created)'}")
        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n  [DRY RUN] No changes will be made.\n")
            )
        self.stdout.write("=" * 60 + "\n")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry run complete. Pass --confirm without --dry-run to execute."))
            return

        # ------------------------------------------------------------------ #
        # Execute atomically — all-or-nothing                                  #
        # ------------------------------------------------------------------ #
        from django.db import transaction as db_transaction

        with db_transaction.atomic():

            # Step 1 — Wipe the entire ledger
            self.stdout.write("  [1/3] Deleting all transaction rows...", ending="")
            deleted, _ = DeltaCrownTransaction.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f" OK  ({deleted:,} rows deleted)"))

            # Step 2 — Zero every user wallet
            self.stdout.write("  [2/3] Resetting all user wallet balances to 0...", ending="")
            updated = DeltaCrownWallet.objects.filter(is_treasury=False).update(
                cached_balance=0,
                pending_balance=0,
                lifetime_earnings=0,
            )
            self.stdout.write(self.style.SUCCESS(f" OK  ({updated:,} wallets reset)"))

            # Step 3 — Ensure treasury exists and is also zeroed
            self.stdout.write("  [3/3] Ensuring Master Treasury wallet exists and is reset...", ending="")
            treasury = get_master_treasury()
            DeltaCrownWallet.objects.filter(pk=treasury.pk).update(
                cached_balance=0,
                pending_balance=0,
                lifetime_earnings=0,
            )
            self.stdout.write(self.style.SUCCESS(f" OK  (Treasury wallet pk={treasury.pk})"))

        # ------------------------------------------------------------------ #
        # Final summary                                                        #
        # ------------------------------------------------------------------ #
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("  [DONE] Genesis Reset complete."))
        self.stdout.write("=" * 60)
        self.stdout.write(
            "  All wallets are now at zero. The ledger is empty.\n"
            "  The Master Treasury is ready to accept fiat deposits.\n"
            "  Next step: mint initial DC via the Economy Dashboard.\n"
            "  URL: /admin/economy/economyconfig/dashboard/\n"
        )
        self.stdout.write("=" * 60 + "\n")

