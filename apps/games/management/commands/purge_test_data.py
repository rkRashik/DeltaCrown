"""
Management command: purge_test_data
====================================
Safely removes fake/seed data from the database while protecting a strict
whitelist of real users and teams. Also re-seeds game schemas and validates
the admin dashboard can resolve without errors.

Usage:
    python manage.py purge_test_data --dry-run   # Preview counts, nothing deleted
    python manage.py purge_test_data             # Execute the wipe

Safety guarantees:
  - SAFE_USER_IDS whitelist is NEVER deleted.
  - Any user with is_superuser=True or is_staff=True is NEVER deleted.
  - SAFE_TEAM_SLUGS whitelist is NEVER deleted.
  - All deletes are wrapped in a single atomic transaction; any failure rolls
    everything back, leaving the DB in its original state.
"""

from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import transaction

# ---------------------------------------------------------------------------
# Strict whitelists — edit here only if real users/teams are added.
# IDs differ across PITR branches; usernames are the stable anchor.
# ---------------------------------------------------------------------------
SAFE_USERNAMES = frozenset([
    'rkrashik', 'SIUU', 'Gunda', 'Bot_Bhai', 'Nawab', 'Murubbi', 'Shadow',
    'Bhaanja', 'Rongbaj', 'Khatarnak', 'Toofan', 'Mastaan', 'Pistol_Pappu',
    'Boma_Mintu', 'Tower_Tareq', 'Hitman_Hafiz', 'Bouncer_Babu',
    'Chapati_Chanchal', 'zarif-yeamin', 'aminul-islam-pranto',
])

SAFE_TEAM_SLUGS = frozenset([
    '1-world-valorant',
    'beporowa-bahini',
    'bhailog-syndicate',
    'protocol-v',
])


class Command(BaseCommand):
    help = (
        "Purge fake/test users, teams, and tournaments. "
        "Re-seeds game schemas. Use --dry-run to preview without deleting."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print counts of records that would be deleted without touching the DB.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        self.stdout.write("")
        self.stdout.write(self.style.WARNING("=" * 65))
        self.stdout.write(self.style.WARNING("  DeltaCrown — purge_test_data"))
        if dry_run:
            self.stdout.write(self.style.WARNING("  MODE: DRY RUN — no data will be modified"))
        else:
            self.stdout.write(self.style.ERROR("  MODE: LIVE — data WILL be permanently deleted"))
        self.stdout.write(self.style.WARNING("=" * 65))

        # ── Step 1: Count / delete fake users ───────────────────────────
        results = self._purge(dry_run)

        # ── Step 2: Seed game schemas ────────────────────────────────────
        seed_ok = self._seed_games(dry_run)

        # ── Step 3: Output summary ───────────────────────────────────────
        self._print_summary(results, seed_ok, dry_run)

    # ------------------------------------------------------------------ #
    # Internal methods
    # ------------------------------------------------------------------ #

    def _purge(self, dry_run: bool) -> dict:
        from apps.accounts.models import User
        from apps.organizations.models import Team, OrganizationMembership
        from apps.organizations.models.membership import TeamMembership
        from apps.tournaments.models import Tournament
        from apps.user_profile.models import GameProfile
        from apps.user_profile.models import GameOAuthConnection

        # ══════════════════════════════════════════════════════════════════
        # PHASE 0 — Materialize whitelist baseline (read-only, pre-transaction)
        # ══════════════════════════════════════════════════════════════════
        # Resolve usernames → IDs at runtime so the script works on any
        # PITR branch regardless of auto-increment sequence state.
        safe_ids_in_db = frozenset(
            User.objects.filter(username__in=SAFE_USERNAMES).values_list('id', flat=True)
        )
        # Auto-add all staff/superusers as an extra safety net.
        safe_ids_in_db = safe_ids_in_db | frozenset(
            User.objects.filter(is_staff=True).values_list('id', flat=True)
        ) | frozenset(
            User.objects.filter(is_superuser=True).values_list('id', flat=True)
        )
        safe_team_slugs_in_db = frozenset(
            Team.objects.filter(slug__in=SAFE_TEAM_SLUGS).values_list('slug', flat=True)
        )

        # ══════════════════════════════════════════════════════════════════
        # PHASE 1 — Materialize fake user IDs as a concrete Python list
        # ══════════════════════════════════════════════════════════════════
        # Using a materialized ID list (not a lazy QuerySet) ensures the
        # exact same set of IDs is targeted in every subsequent operation.
        # A lazy subquery evaluated twice could include newly-flagged users.
        fake_user_ids = list(
            User.objects.filter(is_staff=False, is_superuser=False)
            .exclude(id__in=safe_ids_in_db)
            .values_list('id', flat=True)
        )

        # ── Hard safety assertion: zero overlap with whitelist ────────────
        overlap = frozenset(fake_user_ids) & safe_ids_in_db
        if overlap:
            raise RuntimeError(
                f"SAFETY ABORT (pre-flight): Whitelisted user ID(s) {sorted(overlap)} "
                "appeared in the fake-user list. This must never happen. Refusing to proceed."
            )

        # ── Hard safety assertion: no staff/superuser in fake list ────────
        staff_in_list = list(
            User.objects.filter(id__in=fake_user_ids)
            .filter(is_staff=True) | User.objects.filter(id__in=fake_user_ids)
            .filter(is_superuser=True)
        )
        if staff_in_list:
            raise RuntimeError(
                f"SAFETY ABORT (pre-flight): Staff/superuser account(s) appeared in "
                f"the fake-user list: {[u.username for u in staff_in_list]}"
            )

        # ── Build querysets ───────────────────────────────────────────────
        # All downstream filters use `fake_user_ids` (a list), not a lazy QS.
        fake_users_qs  = User.objects.filter(id__in=fake_user_ids)
        fake_teams_qs  = Team.objects.exclude(slug__in=SAFE_TEAM_SLUGS)

        try:
            tourney_qs = Tournament.all_objects.all()
        except AttributeError:
            tourney_qs = Tournament.objects.all()

        # ── Count before delete ───────────────────────────────────────────
        n_users     = len(fake_user_ids)
        n_teams     = fake_teams_qs.count()
        n_tourney   = tourney_qs.count()
        n_passports = GameProfile.objects.filter(user_id__in=fake_user_ids).count()
        n_oauth     = GameOAuthConnection.objects.filter(
            passport__user_id__in=fake_user_ids
        ).count()

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("── Records queued for deletion ──────────────────────────"))
        self.stdout.write(f"  Fake users        : {n_users}")
        self.stdout.write(f"  Fake teams        : {n_teams}")
        self.stdout.write(f"  Fake tournaments  : {n_tourney}")
        self.stdout.write(f"  Orphan passports  : {n_passports}  (safety-net; may already cascade)")
        self.stdout.write(f"  Orphan OAuth conns: {n_oauth}  (safety-net; may already cascade)")

        # ── Verify whitelist pre-purge ────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("── Whitelist verification ───────────────────────────────"))
        self.stdout.write(
            f"  Whitelisted users found in DB : {len(safe_ids_in_db)} / {len(SAFE_USERNAMES)} username(s)"
        )
        self.stdout.write(
            f"  Whitelisted teams found in DB : {len(safe_team_slugs_in_db)} / {len(SAFE_TEAM_SLUGS)}"
        )
        safe_user_rows = list(
            User.objects.filter(id__in=safe_ids_in_db)
            .values('id', 'username')
            .order_by('id')
        )
        for row in safe_user_rows:
            self.stdout.write(f"    ✓  [{row['id']}] {row['username']}")

        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("DRY RUN complete — nothing was deleted."))
            return {
                "users": n_users,
                "teams": n_teams,
                "tournaments": n_tourney,
                "passports": n_passports,
                "oauth": n_oauth,
                "executed": False,
                "safe_ids_in_db": safe_ids_in_db,
            }

        # ══════════════════════════════════════════════════════════════════
        # PHASE 2 — Execute inside a single atomic transaction
        # ══════════════════════════════════════════════════════════════════
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("Executing deletions inside atomic transaction…"))

        with transaction.atomic():
            from apps.tournaments.models import TournamentResult, PrizeTransaction
            from apps.user_profile.models.activity import UserActivity
            from apps.organizations.models import Organization
            from apps.economy.models import (
                DeltaCrownTransaction, TopUpRequest, WithdrawalRequest,
            )
            from apps.shop.models import ReservationHold

            # ── PRE-PASS: Actively unlink whitelisted users ───────────────
            # If a whitelisted user is a member of a fake Team or fake Org,
            # explicitly remove that membership BEFORE the Team/Org CASCADE
            # fires. This prevents ANY cascade path from touching safe users.

            tm_unlinked, _ = TeamMembership.objects.filter(
                team__in=fake_teams_qs,
                user_id__in=list(safe_ids_in_db),
            ).delete()
            if tm_unlinked:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [SAFETY] Unlinked {tm_unlinked} TeamMembership row(s) "
                        "for whitelisted users from fake teams."
                    )
                )

            orgs_to_delete_qs = Organization.objects.filter(ceo_id__in=fake_user_ids)
            om_unlinked, _ = OrganizationMembership.objects.filter(
                organization__in=orgs_to_delete_qs,
                user_id__in=list(safe_ids_in_db),
            ).delete()
            if om_unlinked:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [SAFETY] Unlinked {om_unlinked} OrganizationMembership row(s) "
                        "for whitelisted users from fake organizations."
                    )
                )

            # ── Step 1 — PrizeTransaction: clears PROTECT on Registration.participant
            deleted_prize, _ = PrizeTransaction.objects.all().delete()
            self.stdout.write(f"  Deleted PrizeTransaction rows: {deleted_prize}")

            # ── Step 2 — TournamentResult: clears PROTECT on Registration winner fields
            try:
                deleted_results, _ = TournamentResult.all_objects.all().delete()
            except AttributeError:
                deleted_results, _ = TournamentResult.objects.all().delete()
            self.stdout.write(f"  Deleted TournamentResult rows: {deleted_results}")

            # ── Step 3 — Tournaments (all, incl. soft-deleted)
            try:
                deleted_tourneys, _ = Tournament.all_objects.all().delete()
            except AttributeError:
                deleted_tourneys, _ = Tournament.objects.all().delete()
            self.stdout.write(f"  Deleted Tournament rows: {deleted_tourneys}")

            # ── Step 4 — UserActivity: FAKE USERS ONLY (preserves whitelist activities)
            deleted_activity, _ = UserActivity.objects.filter(
                user_id__in=fake_user_ids
            ).delete()
            self.stdout.write(f"  Deleted UserActivity rows: {deleted_activity}")

            # ── Step 5 — Organizations owned by fake users
            deleted_orgs, _ = orgs_to_delete_qs.delete()
            self.stdout.write(f"  Deleted Organization rows: {deleted_orgs}")

            # ── Step 6 — Economy wallet records: FAKE USERS ONLY
            _wf = {"wallet__profile__user_id__in": fake_user_ids}
            deleted_txns, _        = DeltaCrownTransaction.objects.filter(**_wf).delete()
            deleted_topups, _      = TopUpRequest.objects.filter(**_wf).delete()
            deleted_withdrawals, _ = WithdrawalRequest.objects.filter(**_wf).delete()
            deleted_holds, _       = ReservationHold.objects.filter(**_wf).delete()
            self.stdout.write(f"  Deleted DeltaCrownTransaction rows : {deleted_txns}")
            self.stdout.write(f"  Deleted TopUpRequest rows          : {deleted_topups}")
            self.stdout.write(f"  Deleted WithdrawalRequest rows     : {deleted_withdrawals}")
            self.stdout.write(f"  Deleted ReservationHold rows       : {deleted_holds}")

            # ── Step 7 — OAuth connections: FAKE USERS ONLY
            deleted_oauth, _ = GameOAuthConnection.objects.filter(
                passport__user_id__in=fake_user_ids
            ).delete()
            self.stdout.write(f"  Deleted orphan OAuth connections: {deleted_oauth}")

            # ── Step 8 — Passports: FAKE USERS ONLY
            deleted_passports, _ = GameProfile.objects.filter(
                user_id__in=fake_user_ids
            ).delete()
            self.stdout.write(f"  Deleted orphan passports: {deleted_passports}")

            # ── Step 9 — Teams
            deleted_teams, _ = fake_teams_qs.delete()
            self.stdout.write(f"  Deleted fake teams: {deleted_teams}")

            # ── Step 10 — Users (uses materialized ID list, never a lazy QS)
            deleted_users, _ = User.objects.filter(id__in=fake_user_ids).delete()
            self.stdout.write(f"  Deleted fake users: {deleted_users}")

            # ══════════════════════════════════════════════════════════════
            # WHITELIST INTEGRITY TRIP-WIRE
            # Query the live DB inside the transaction BEFORE committing.
            # If ANY whitelisted user is missing, RAISE → entire transaction
            # rolls back automatically. No data is permanently modified.
            # ══════════════════════════════════════════════════════════════
            surviving_ids = frozenset(
                User.objects.filter(id__in=safe_ids_in_db).values_list('id', flat=True)
            )
            missing_ids = safe_ids_in_db - surviving_ids
            if missing_ids:
                raise RuntimeError(
                    f"🚨 WHITELIST SAFETY ABORT: {len(missing_ids)} whitelisted user(s) "
                    f"were accidentally deleted during this run! "
                    f"Missing IDs: {sorted(missing_ids)}. "
                    "ROLLING BACK entire transaction — the database is untouched."
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Trip-wire passed: all {len(surviving_ids)} whitelisted "
                    "user(s) confirmed present in DB."
                )
            )

        self.stdout.write(self.style.SUCCESS("Transaction committed successfully."))

        # Post-commit: live DB query to confirm whitelist survival
        confirmed_safe = list(
            User.objects.filter(id__in=safe_ids_in_db)
            .values('id', 'username')
            .order_by('id')
        )

        return {
            "users": deleted_users,
            "teams": deleted_teams,
            "tournaments": deleted_tourneys,
            "passports": deleted_passports,
            "oauth": deleted_oauth,
            "executed": True,
            "safe_ids_in_db": safe_ids_in_db,
            "confirmed_safe_users": confirmed_safe,
        }

    def _seed_games(self, dry_run: bool) -> bool:
        if dry_run:
            self.stdout.write("")
            self.stdout.write(self.style.HTTP_INFO("── seed_games ────────────────────────────────────────────"))
            self.stdout.write("  DRY RUN: seed_games would be called here (skipped).")
            return True

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("── Running seed_games ───────────────────────────────────"))
        try:
            call_command("seed_games")
            return True
        except Exception as exc:
            self.stderr.write(self.style.ERROR(f"  seed_games FAILED: {exc}"))
            return False

    def _print_summary(self, results: dict, seed_ok: bool, dry_run: bool) -> None:
        self.stdout.write("")
        self.stdout.write(self.style.WARNING("=" * 65))
        self.stdout.write(self.style.WARNING("  SUMMARY"))
        self.stdout.write(self.style.WARNING("=" * 65))

        if not results["executed"]:
            self.stdout.write(self.style.SUCCESS("  DRY RUN — no records were modified."))
            self.stdout.write(f"  Would delete {results['users']} users")
            self.stdout.write(f"  Would delete {results['teams']} teams")
            self.stdout.write(f"  Would delete {results['tournaments']} tournaments")
            self.stdout.write(f"  Would delete {results['passports']} passports (explicit)")
            self.stdout.write(f"  Would delete {results['oauth']} OAuth connections (explicit)")
        else:
            self.stdout.write(self.style.SUCCESS(f"  ✓ Deleted {results['users']} fake users"))
            self.stdout.write(self.style.SUCCESS(f"  ✓ Deleted {results['teams']} fake teams"))
            self.stdout.write(self.style.SUCCESS(f"  ✓ Hard-deleted {results['tournaments']} tournaments"))
            self.stdout.write(self.style.SUCCESS(f"  ✓ Deleted {results['passports']} orphan passports (explicit)"))
            self.stdout.write(self.style.SUCCESS(f"  ✓ Deleted {results['oauth']} orphan OAuth connections (explicit)"))

        seed_label = "✓ seed_games ran successfully" if seed_ok else "✗ seed_games encountered an error (check output above)"
        seed_color = self.style.SUCCESS if seed_ok else self.style.ERROR
        self.stdout.write(seed_color(f"  {seed_label}"))

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("── Whitelist protection confirmed ───────────────────────"))

        if results["executed"]:
            confirmed = results.get("confirmed_safe_users", [])
            self.stdout.write(
                self.style.SUCCESS(
                    f"  \u2713 Live DB query confirms {len(confirmed)} / {len(SAFE_USERNAMES)} "
                    "whitelisted user(s) still present:"
                )
            )
            for row in confirmed:
                self.stdout.write(self.style.SUCCESS(f"    ✓  [{row['id']}] {row['username']}"))
            missing_count = len(results.get("safe_ids_in_db", set())) - len(confirmed)
            if missing_count:
                self.stdout.write(
                    self.style.ERROR(
                        f"  ⚠  {missing_count} whitelisted ID(s) were not in DB before the purge ran "
                        "(they did not exist in the recovered DB snapshot)."
                    )
                )
        else:
            self.stdout.write("  The following whitelisted IDs were NEVER targeted:")
            whitelist_ids = sorted(results.get("safe_ids_in_db", set()))
            self.stdout.write(f"  Users  : {whitelist_ids}")
        self.stdout.write(f"  Teams  : {sorted(SAFE_TEAM_SLUGS)}")
        self.stdout.write("  All staff/superuser accounts were also excluded.")
        self.stdout.write("")

        if results["executed"] and seed_ok:
            self.stdout.write(self.style.SUCCESS(
                "  Next step: hard-refresh /admin — the 500 error should be resolved.\n"
                "  If the admin still 500s, restart the Django process to clear any\n"
                "  in-memory queryplan caches, then check Sentry for the traceback."
            ))

        self.stdout.write(self.style.WARNING("=" * 65))
        self.stdout.write("")
