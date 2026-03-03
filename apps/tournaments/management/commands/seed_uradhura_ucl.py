"""
UraDhura Champions League (UCL) — Group Stage Stress-Test Seeder
=================================================================

Provisions a full 32-player, 8-group, double-round-robin tournament that
exercises every layer of the TOC pipeline via real service calls:

Pipeline:
  1.  Resolve / create 32 synthetic player accounts
  2.  Resolve / create the target Game (default: eFootball)
  3.  Create Tournament (group_playoff, registration_open, entry_fee=100 BDT)
  4.  Create TournamentPaymentMethod (bKash, account 01780008001)
  5.  GroupStageService.create_groups()  → GroupStage + 8 × Group
  6.  RegistrationService.register_participant() × 32
  7.  RegistrationService.submit_payment() × 32 (mock bKash txn IDs)
  8.  RegistrationService.verify_payment() × 27  (leave 5 as SUBMITTED)
  9.  GroupStageService.assign_participant() × 32
  10. GroupStageService.generate_group_matches(rounds=2) → 96 double-RR matches
  11. [--with-results]  simulate random outcomes + calculate_group_standings()

Usage:
    python manage.py seed_uradhura_ucl
    python manage.py seed_uradhura_ucl --purge
    python manage.py seed_uradhura_ucl --purge --with-results
    python manage.py seed_uradhura_ucl --purge --pre-draw
    python manage.py seed_uradhura_ucl --game cs2
    python manage.py seed_uradhura_ucl --dry-run
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.games.models import Game
from apps.tournaments.models import (
    Group,
    GroupStanding,
    Match,
    Registration,
    Tournament,
)
from apps.tournaments.models.payment_config import TournamentPaymentMethod
from apps.tournaments.models.registration import Payment
from apps.tournaments.services.group_stage_service import GroupStageService
from apps.tournaments.services.registration_service import RegistrationService

User = get_user_model()

# ─── Constants ──────────────────────────────────────────────────────────────

TOURNAMENT_NAME = "UraDhura Champions League S1"
TOURNAMENT_SLUG_PREFIX = "uradhura-ucl-s1"
PLAYER_PASSWORD = "UCL_seed_2025!"
# Prefer the real user 'rkrashik' as organizer; fall back to seed account
PREFERRED_ORGANIZER = "rkrashik"
FALLBACK_ORGANIZER = "ucl_organizer_seed"
NUM_GROUPS = 8
GROUP_SIZE = 4          # 4 players × 8 groups = 32
ADVANCEMENT_PER_GROUP = 2
ENTRY_FEE = Decimal("100.00")
ENTRY_FEE_CURRENCY = "BDT"
BKASH_ACCOUNT = "01780008001"
# Number of payments left in SUBMITTED state (for manual TOC testing)
UNVERIFIED_COUNT = 5
RR_ROUNDS = 2          # Double round-robin (home + away)

# Synthetic player roster (32 entrants, UCL-flavoured codenames)
UCL_ROSTER = [
    ("ucl_kronos",     "Kronos"),
    ("ucl_phantom_x",  "Phantom_X"),
    ("ucl_void_step",  "VoidStep"),
    ("ucl_ironwall",   "IronWall"),
    ("ucl_surge",      "Surge.GG"),
    ("ucl_eclipse_bd", "Eclipse_BD"),
    ("ucl_nova_00",    "Nova00"),
    ("ucl_cipher",     "Cipher"),
    ("ucl_spectre_9",  "Spectre9"),
    ("ucl_blaze_fx",   "BlazeFX"),
    ("ucl_delta_one",  "DeltaOne"),
    ("ucl_grimshard",  "GrimShard"),
    ("ucl_neon_ghost", "NeonGhost"),
    ("ucl_titan_bd",   "Titan_BD"),
    ("ucl_redshift",   "RedShift"),
    ("ucl_axiom",      "Axiom.BD"),
    ("ucl_warpzone",   "WarpZone"),
    ("ucl_frostbyte",  "FrostByte"),
    ("ucl_shadowrun",  "ShadowRun"),
    ("ucl_corevault",  "CoreVault"),
    ("ucl_tachyon",    "Tachyon"),
    ("ucl_sentinel_x", "SentinelX"),
    ("ucl_fluxgate",   "FluxGate"),
    ("ucl_vector_bd",  "Vector_BD"),
    ("ucl_overdrive",  "Overdrive"),
    ("ucl_nullcode",   "NullCode"),
    ("ucl_pulsefx",    "PulseFX"),
    ("ucl_stormcore",  "StormCore"),
    ("ucl_magnafield", "MagnaField"),
    ("ucl_quantmhop",  "QuantmHop"),
    ("ucl_hexedge",    "HexEdge"),
    ("ucl_xray_bd",    "Xray_BD"),
]

assert len(UCL_ROSTER) == 32, "Roster must have exactly 32 entries"


# ─── Helpers ────────────────────────────────────────────────────────────────

def _header(text: str) -> str:
    bar = "=" * (len(text) + 4)
    return f"\n+{bar}+\n|  {text}  |\n+{bar}+"


def _ok(msg: str) -> str:
    return f"  [OK] {msg}"


def _warn(msg: str) -> str:
    return f"  [!!] {msg}"


# ─── Command ────────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = "Seed a 32-player UCL-style group stage tournament (TOC stress-test)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--purge",
            action="store_true",
            default=False,
            help="Delete existing UCL seed tournament and all related data before re-seeding.",
        )
        parser.add_argument(
            "--game",
            type=str,
            default="efootball",
            help='Game slug to attach to the tournament (default: "efootball"). '
                 'The game will be created if it does not exist.',
        )
        parser.add_argument(
            "--with-results",
            action="store_true",
            default=False,
            help="After generating matches, inject random match results and recalculate standings.",
        )
        parser.add_argument(
            "--pre-draw",
            action="store_true",
            default=False,
            help="Stop BEFORE group assignment (step 9). Leaves 32 confirmed "
                 "participants in the pending queue and 8 groups empty — "
                 "ready for the Live Draw Director.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Print the plan without committing any DB changes.",
        )

    # ── entry point ──────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        # Force UTF-8 on Windows to avoid cp1252 encoding errors
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')

        purge        = options["purge"]
        game_slug    = options["game"]
        with_results = options["with_results"]
        pre_draw     = options["pre_draw"]
        dry_run      = options["dry_run"]

        self.stdout.write(_header("UraDhura UCL Seeder"))

        if dry_run:
            self.stdout.write(self.style.WARNING("\n  DRY-RUN mode -- no DB writes.\n"))

        # --- purge -----------------------------------------------------------
        if purge and not dry_run:
            self._purge_existing()

        if dry_run:
            self._print_plan(game_slug, with_results, pre_draw)
            return

        # --- run inside a single atomic block --------------------------------
        try:
            with transaction.atomic():
                self._seed_staff_roles()
                organizer   = self._get_or_create_organizer()
                game        = self._get_or_create_game(game_slug)
                tournament  = self._create_tournament(organizer, game)
                self._create_payment_method(tournament)
                stage       = self._create_group_stage(tournament)
                players     = self._get_or_create_players()
                regs        = self._register_players(tournament, players)
                payments    = self._submit_payments(regs, tournament)
                self._verify_payments(payments, organizer)

                if pre_draw:
                    # ── STOP before group assignment ──
                    # Leave 32 confirmed participants in the pending queue
                    # and 8 groups completely empty for Live Draw testing.
                    groups = list(
                        Group.objects.filter(tournament=stage.tournament)
                        .order_by("display_order")
                    )
                    self._print_pre_draw_summary(tournament, stage, groups)
                else:
                    groups      = self._assign_to_groups(stage, players)
                    match_count = self._generate_matches(stage)

                    if with_results:
                        self._inject_results(tournament, stage)

                    self._print_summary(tournament, stage, groups, match_count, with_results)

        except Exception as exc:
            raise CommandError(f"Seeder failed: {exc}") from exc

    # ── step implementations ──────────────────────────────────────────────────

    def _seed_staff_roles(self):
        """Seed industry-standard esports staff roles into StaffRole table."""
        from apps.tournaments.models.staffing import StaffRole

        ROLES = [
            {
                "code": "head_admin",
                "name": "Head Admin",
                "description": "Full access to all TOC tabs and destructive actions.",
                "capabilities": {
                    "full_access": True,
                    "edit_settings": True,
                    "manage_registrations": True,
                    "approve_payments": True,
                    "manage_brackets": True,
                    "resolve_disputes": True,
                    "make_announcements": True,
                    "view_all": True,
                },
                "is_referee_role": False,
            },
            {
                "code": "registration_manager",
                "name": "Registration Manager",
                "description": "Can approve/reject players and verify payments.",
                "capabilities": {
                    "manage_registrations": True,
                    "approve_payments": True,
                    "view_all": True,
                },
                "is_referee_role": False,
            },
            {
                "code": "match_referee",
                "name": "Match Referee",
                "description": "Can generate brackets, submit scores, and resolve disputes.",
                "capabilities": {
                    "manage_brackets": True,
                    "resolve_disputes": True,
                    "can_referee_matches": True,
                    "view_all": True,
                },
                "is_referee_role": True,
            },
            {
                "code": "scorekeeper",
                "name": "Scorekeeper",
                "description": "Can only submit match results.",
                "capabilities": {
                    "manage_brackets": True,
                    "view_all": True,
                },
                "is_referee_role": False,
            },
            {
                "code": "media_comms",
                "name": "Media & Comms",
                "description": "Can post announcements and manage social/media content.",
                "capabilities": {
                    "make_announcements": True,
                    "view_all": True,
                },
                "is_referee_role": False,
            },
            {
                "code": "observer",
                "name": "Observer",
                "description": "Read-only access to the TOC.",
                "capabilities": {
                    "view_all": True,
                },
                "is_referee_role": False,
            },
        ]

        created_count = 0
        for role_def in ROLES:
            obj, created = StaffRole.objects.update_or_create(
                code=role_def["code"],
                defaults={
                    "name": role_def["name"],
                    "description": role_def["description"],
                    "capabilities": role_def["capabilities"],
                    "is_referee_role": role_def["is_referee_role"],
                },
            )
            if created:
                created_count += 1

        self.stdout.write(_ok(
            f"Staff roles: {created_count} created, "
            f"{len(ROLES) - created_count} updated."
        ))

    def _purge_existing(self):
        """Delete any tournament whose slug starts with TOURNAMENT_SLUG_PREFIX."""
        qs = Tournament.objects.filter(slug__startswith=TOURNAMENT_SLUG_PREFIX)
        count = qs.count()
        if count:
            qs.delete()
            self.stdout.write(_ok(f"Purged {count} existing UCL tournament(s)."))
        else:
            self.stdout.write(_warn("No existing UCL tournaments found to purge."))

    def _get_or_create_organizer(self) -> User:
        # Prefer the real user if they exist in the database
        preferred = User.objects.filter(username=PREFERRED_ORGANIZER).first()
        if preferred:
            self.stdout.write(_ok(f"Using preferred organizer: {PREFERRED_ORGANIZER}"))
            return preferred

        # Fall back to creating a seed account
        user, created = User.objects.get_or_create(
            username=FALLBACK_ORGANIZER,
            defaults={
                "email": f"{FALLBACK_ORGANIZER}@seed.deltacrown.dev",
                "is_staff": False,
            },
        )
        if created:
            user.set_password(PLAYER_PASSWORD)
            user.save()
            self.stdout.write(_ok(f"Created organizer: {FALLBACK_ORGANIZER}"))
        else:
            self.stdout.write(_ok(f"Reused organizer: {FALLBACK_ORGANIZER}"))
        return user

    def _get_or_create_game(self, slug: str) -> Game:
        normalized_slug = slugify(slug)
        game, created = Game.objects.get_or_create(
            slug=normalized_slug,
            defaults={
                "name": slug.replace("-", " ").title(),
                "is_active": True,
            },
        )
        if created:
            self.stdout.write(_ok(f"Created game: {game.name} (slug={normalized_slug})"))
        else:
            self.stdout.write(_ok(f"Resolved game: {game.name} (slug={normalized_slug})"))
        return game

    def _create_tournament(self, organizer: User, game: Game) -> Tournament:
        """Create a fresh UCL seed tournament with bKash entry fee."""
        now = timezone.now()
        base_slug = TOURNAMENT_SLUG_PREFIX
        slug = base_slug
        counter = 1
        while Tournament.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        tournament = Tournament.objects.create(
            name=TOURNAMENT_NAME,
            slug=slug,
            organizer=organizer,
            game=game,
            format=Tournament.GROUP_PLAYOFF,
            participation_type=Tournament.SOLO,
            status=Tournament.REGISTRATION_OPEN,
            max_participants=NUM_GROUPS * GROUP_SIZE,   # 32
            min_participants=NUM_GROUPS * GROUP_SIZE,   # 32
            registration_start=now - timedelta(days=2),
            registration_end=now + timedelta(days=1),
            tournament_start=now + timedelta(days=3),
            has_entry_fee=True,
            entry_fee_amount=ENTRY_FEE,
            entry_fee_currency=ENTRY_FEE_CURRENCY,
            payment_methods=['bkash'],
            description=(
                "UraDhura Champions League — 32-player group stage seeder "
                "for TOC stress-testing. Entry fee: BDT 100 via bKash."
            ),
        )
        self.stdout.write(_ok(
            f"Created tournament '{tournament.name}' (id={tournament.id}, slug={tournament.slug})"
            f" — entry fee: {ENTRY_FEE} {ENTRY_FEE_CURRENCY}"
        ))
        return tournament

    def _create_payment_method(self, tournament: Tournament):
        """Create TournamentPaymentMethod for bKash."""
        tpm, created = TournamentPaymentMethod.objects.get_or_create(
            tournament=tournament,
            method=TournamentPaymentMethod.BKASH,
            defaults={
                "is_enabled": True,
                "display_order": 0,
                "bkash_account_number": BKASH_ACCOUNT,
                "bkash_account_type": TournamentPaymentMethod.PERSONAL,
                "bkash_account_name": "DeltaCrown UCL Seed",
                "bkash_instructions": (
                    "1. Open bKash app\n"
                    "2. Send Money to **01780008001**\n"
                    "3. Amount: **BDT 100**\n"
                    "4. Copy the Transaction ID and submit below"
                ),
                "bkash_reference_required": True,
            },
        )
        status_str = "Created" if created else "Reused"
        self.stdout.write(_ok(
            f"{status_str} bKash payment method (account={BKASH_ACCOUNT})"
        ))

    def _create_group_stage(self, tournament: Tournament):
        """GroupStageService.create_groups() → GroupStage + 8 Group records."""
        stage = GroupStageService.create_groups(
            tournament_id=tournament.id,
            num_groups=NUM_GROUPS,
            group_size=GROUP_SIZE,
            advancement_count_per_group=ADVANCEMENT_PER_GROUP,
            config={
                "points_system": {"win": 3, "draw": 1, "loss": 0},
                "tiebreaker_rules": ["points", "wins", "goal_difference", "goals_for"],
                "seeding_method": "snake",
                "match_format": "double_round_robin",
            },
        )
        # Mark format on the GroupStage record itself
        from apps.tournaments.models.group import GroupStage as GS
        GS.objects.filter(id=stage.id).update(format='double_round_robin')

        self.stdout.write(_ok(
            f"Created GroupStage id={stage.id} with {NUM_GROUPS} groups "
            f"(size={GROUP_SIZE}, advancers={ADVANCEMENT_PER_GROUP}, format=double_round_robin)"
        ))
        return stage

    def _get_or_create_players(self) -> list:
        """Get or create all 32 UCL players. Returns list of User objects."""
        players = []
        created_count = 0
        for username, display_name in UCL_ROSTER:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@seed.deltacrown.dev",
                    "first_name": display_name,
                },
            )
            if created:
                user.set_password(PLAYER_PASSWORD)
                user.save()
                created_count += 1
            players.append(user)
        self.stdout.write(_ok(
            f"Roster ready: {len(players)} players "
            f"({created_count} new, {len(players) - created_count} existing)"
        ))
        return players

    def _register_players(self, tournament: Tournament, players: list) -> list:
        """Call RegistrationService.register_participant() for each player."""
        registrations = []
        for idx, user in enumerate(players, start=1):
            # Skip if already registered (idempotent re-runs after partial failure)
            existing = Registration.objects.filter(
                tournament=tournament, user=user
            ).first()
            if existing:
                registrations.append(existing)
                continue

            reg = RegistrationService.register_participant(
                tournament_id=tournament.id,
                user=user,
                registration_data={
                    "game_id": f"UCL#{idx:03d}",
                    "notes": "Auto-registered by seed_uradhura_ucl",
                },
            )
            registrations.append(reg)

        self.stdout.write(_ok(f"Registered {len(registrations)} players"))
        return registrations

    def _submit_payments(self, registrations: list, tournament: Tournament) -> list:
        """
        Create bKash Payment records for all 32 registrations via
        RegistrationService.submit_payment().

        Returns list of Payment objects.
        """
        payments = []
        for idx, reg in enumerate(registrations, start=1):
            # Skip if payment already exists (idempotent)
            if hasattr(reg, 'payment') and reg.payment:
                payments.append(reg.payment)
                continue
            # Registration must be PENDING to submit payment
            if reg.status not in (Registration.PENDING, Registration.PAYMENT_SUBMITTED):
                payments.append(getattr(reg, 'payment', None))
                continue
            txn_id = f"BKASH_TXN_{idx:03d}"
            payment = RegistrationService.submit_payment(
                registration_id=reg.id,
                payment_method='bkash',
                amount=ENTRY_FEE,
                transaction_id=txn_id,
            )
            payments.append(payment)

        self.stdout.write(_ok(
            f"Submitted {len([p for p in payments if p])} bKash payments "
            f"(txn IDs: BKASH_TXN_001 … BKASH_TXN_{len(registrations):03d})"
        ))
        return payments

    def _verify_payments(self, payments: list, verified_by: User):
        """
        Auto-verify 27 payments, leave last 5 in SUBMITTED state.

        The 5 unverified payments are left for manual TOC testing
        (Verify / Reject buttons in the Payments tab).
        """
        verified = 0
        left_submitted = 0
        for idx, payment in enumerate(payments):
            if payment is None:
                continue
            if payment.status == Payment.VERIFIED:
                verified += 1
                continue
            if payment.status != Payment.SUBMITTED:
                continue
            # Leave the last UNVERIFIED_COUNT payments as SUBMITTED
            if idx >= len(payments) - UNVERIFIED_COUNT:
                left_submitted += 1
                continue
            RegistrationService.verify_payment(
                payment_id=payment.id,
                verified_by=verified_by,
                admin_notes="Auto-verified by seed_uradhura_ucl",
            )
            verified += 1

        self.stdout.write(_ok(
            f"Payment verification: {verified} verified, "
            f"{left_submitted} left as SUBMITTED for TOC testing"
        ))

    def _assign_to_groups(self, stage, players: list) -> list:
        """
        Assign players to groups deterministically: players 0-3 → Group A,
        4-7 → Group B, …, 28-31 → Group H.

        Uses GroupStageService.assign_participant() so GroupStanding records
        are created the same way the live system would.
        """
        groups = list(
            Group.objects.filter(tournament=stage.tournament)
            .order_by("display_order")
        )
        if len(groups) != NUM_GROUPS:
            raise CommandError(
                f"Expected {NUM_GROUPS} groups, found {len(groups)}. "
                "Did create_groups() run correctly?"
            )

        for idx, user in enumerate(players):
            group_index = idx // GROUP_SIZE      # 0-7
            group = groups[group_index]
            # Skip if already assigned (idempotent)
            already = GroupStanding.objects.filter(
                group=group, user=user, is_deleted=False
            ).exists()
            if already:
                continue
            GroupStageService.assign_participant(
                stage_id=stage.id,
                participant_id=user.id,
                group_id=group.id,
                is_team=False,
            )

        self.stdout.write(_ok(
            f"Assigned {len(players)} players to {NUM_GROUPS} groups "
            f"({GROUP_SIZE} per group)"
        ))
        return groups

    def _generate_matches(self, stage) -> int:
        """
        GroupStageService.generate_group_matches(rounds=2) — double round-robin.
        8 groups × C(4,2) × 2 rounds = 8 × 6 × 2 = 96 matches expected.
        """
        total = GroupStageService.generate_group_matches(
            stage_id=stage.id, rounds=RR_ROUNDS,
        )
        pairings_per_group = GROUP_SIZE * (GROUP_SIZE - 1) // 2  # 6
        expected = NUM_GROUPS * pairings_per_group * RR_ROUNDS   # 96
        if total != expected:
            self.stdout.write(_warn(
                f"Generated {total} matches (expected {expected}). "
                "Check if duplicate GroupStanding rows existed."
            ))
        else:
            self.stdout.write(_ok(
                f"Generated {total} matches "
                f"({pairings_per_group * RR_ROUNDS} per group, double RR)"
            ))
        return total

    # ── optional: inject random results ──────────────────────────────────────

    def _inject_results(self, tournament: Tournament, stage):
        """
        Simulate match outcomes:
          - Each match gets a random scoreline (goals 0-4 each side).
          - A winner is determined (or draw).
          - Match.state → COMPLETED.
          - GroupStageService.calculate_group_standings() is called to verify.

        NOTE: This deliberately exercises calculate_group_standings (Epic 3.2 path)
        which correctly uses state=Match.COMPLETED (confirmed working).
        The OLD calculate_standings() path is intentionally NOT called here —
        its status/state bug is documented in Phase 2 audit.
        """
        matches = Match.objects.filter(
            tournament=tournament,
            state=Match.SCHEDULED,
        )

        completed = 0
        now = timezone.now()
        for match in matches:
            # Generate scores — re-roll ties to guarantee a winner
            # (DB CHECK constraint requires winner_id + loser_id when COMPLETED)
            while True:
                g1 = random.randint(0, 4)
                g2 = random.randint(0, 4)
                if g1 != g2:
                    break

            if g1 > g2:
                winner_id = match.participant1_id
                loser_id = match.participant2_id
            else:
                winner_id = match.participant2_id
                loser_id = match.participant1_id

            # Store scoreline in lobby_info alongside existing group metadata
            existing = match.lobby_info or {}
            existing.update({"score_p1": g1, "score_p2": g2})

            # Use .update() instead of .save() to bypass post_save signals
            # that trigger Celery/Redis (broadcast_match_update, discord_sync)
            # which are unavailable on staging and cause transaction rollback.
            Match.objects.filter(pk=match.pk).update(
                state=Match.COMPLETED,
                winner_id=winner_id,
                loser_id=loser_id,
                participant1_score=g1,
                participant2_score=g2,
                completed_at=now,
                lobby_info=existing,
            )
            completed += 1

        self.stdout.write(_ok(
            f"Injected results: {completed} matches completed (all decisive)"
        ))

        # Recalculate standings using the Epic 3.2 method
        try:
            standings_data = GroupStageService.calculate_group_standings(stage_id=stage.id)
            self.stdout.write(_ok(
                f"calculate_group_standings() returned data for {len(standings_data)} groups [OK]"
            ))
        except Exception as exc:
            self.stdout.write(_warn(f"calculate_group_standings() raised: {exc}"))

    # ── summary output ────────────────────────────────────────────────────────

    def _print_pre_draw_summary(self, tournament, stage, groups):
        """Summary when --pre-draw stops BEFORE group assignment."""
        verified = Payment.objects.filter(
            registration__tournament=tournament, status=Payment.VERIFIED
        ).count()
        submitted = Payment.objects.filter(
            registration__tournament=tournament, status=Payment.SUBMITTED
        ).count()
        confirmed_regs = Registration.objects.filter(
            tournament=tournament, status=Registration.CONFIRMED
        ).count()
        assigned = sum(
            g.standings.filter(is_deleted=False).count() for g in groups
        )

        self.stdout.write(_header("Pre-Draw Seed Complete"))
        self.stdout.write(f"  Tournament : {tournament.name}")
        self.stdout.write(f"  ID         : {tournament.id}")
        self.stdout.write(f"  Slug       : {tournament.slug}")
        self.stdout.write(f"  Format     : {tournament.format}")
        self.stdout.write(f"  Status     : {tournament.status}")
        self.stdout.write(f"  Game       : {tournament.game.name}")
        self.stdout.write(f"  Entry fee  : {ENTRY_FEE} {ENTRY_FEE_CURRENCY} (bKash)")
        self.stdout.write(f"  GroupStage : id={stage.id} (double round-robin)")
        self.stdout.write(f"  Groups     : {len(groups)} ({GROUP_SIZE} slots each)")
        self.stdout.write(f"  Assigned   : {assigned} (should be 0)")
        self.stdout.write(f"  Matches    : 0 (not generated yet)")
        self.stdout.write(f"  Payments   : {verified} verified, {submitted} pending verification")
        self.stdout.write(f"  Confirmed  : {confirmed_regs} / 32 registrations")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            "  [OK] Pre-draw seed complete. Groups are EMPTY.\n"
        ))
        self.stdout.write(
            "  Ready for Live Draw:\n"
            "    \u2022 Director  : /tournaments/{slug}/draw/director/\n"
            "    \u2022 Spectator : /tournaments/{slug}/draw/live/\n"
            "    \u2022 Click \u2018Start Live Draw\u2019 to begin the WebSocket ceremony.\n"
            "    \u2022 All 32 confirmed players will appear in the pending queue.\n"
            .format(slug=tournament.slug)
        )

    def _print_summary(self, tournament, stage, groups, match_count, with_results):
        verified = Payment.objects.filter(
            registration__tournament=tournament, status=Payment.VERIFIED
        ).count()
        submitted = Payment.objects.filter(
            registration__tournament=tournament, status=Payment.SUBMITTED
        ).count()
        confirmed_regs = Registration.objects.filter(
            tournament=tournament, status=Registration.CONFIRMED
        ).count()
        total_revenue = verified * ENTRY_FEE

        self.stdout.write(_header("Seed Complete"))
        self.stdout.write(f"  Tournament : {tournament.name}")
        self.stdout.write(f"  ID         : {tournament.id}")
        self.stdout.write(f"  Slug       : {tournament.slug}")
        self.stdout.write(f"  Format     : {tournament.format}")
        self.stdout.write(f"  Status     : {tournament.status}")
        self.stdout.write(f"  Game       : {tournament.game.name}")
        self.stdout.write(f"  Entry fee  : {ENTRY_FEE} {ENTRY_FEE_CURRENCY} (bKash)")
        self.stdout.write(f"  GroupStage : id={stage.id} (double round-robin)")
        self.stdout.write(f"  Groups     : {len(groups)} ({GROUP_SIZE} players each)")
        self.stdout.write(f"  Matches    : {match_count} (double RR)")
        self.stdout.write(f"  Payments   : {verified} verified, {submitted} pending verification")
        self.stdout.write(f"  Confirmed  : {confirmed_regs} / 32 registrations")
        self.stdout.write(f"  Revenue    : BDT {total_revenue} collected")
        if with_results:
            completed = Match.objects.filter(
                tournament=tournament, state=Match.COMPLETED
            ).count()
            self.stdout.write(f"  Completed  : {completed} matches")
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("  [OK] UCL group stage seeded successfully.\n"))
        self.stdout.write(
            "  Next steps:\n"
            "    • TOC Overview  : /api/toc/{slug}/overview/\n"
            "    • TOC Payments  : /api/toc/{slug}/payments/  (5 unverified for manual test)\n"
            "    • TOC Groups    : /api/toc/{slug}/groups/\n"
            "    • TOC Standings : /api/toc/{slug}/groups/standings/\n"
            "    • Or re-run with --purge --with-results to stress-test the full pipeline\n"
            .format(slug=tournament.slug)
        )

    def _print_plan(self, game_slug: str, with_results: bool, pre_draw: bool = False):
        pairings = GROUP_SIZE * (GROUP_SIZE - 1) // 2
        self.stdout.write(_header("Dry-Run Plan"))
        self.stdout.write(f"  Game slug       : {game_slug}")
        self.stdout.write(f"  Tournament name : {TOURNAMENT_NAME}")
        self.stdout.write(f"  Format          : group_playoff (double round-robin)")
        self.stdout.write(f"  Entry fee       : {ENTRY_FEE} {ENTRY_FEE_CURRENCY} via bKash")
        self.stdout.write(f"  Groups          : {NUM_GROUPS}")
        self.stdout.write(f"  Players/group   : {GROUP_SIZE}")
        self.stdout.write(f"  Total players   : {NUM_GROUPS * GROUP_SIZE}")
        self.stdout.write(f"  Advancers/group : {ADVANCEMENT_PER_GROUP}")
        self.stdout.write(f"  Total advancers : {NUM_GROUPS * ADVANCEMENT_PER_GROUP}")
        self.stdout.write(f"  Expected matches: {NUM_GROUPS * pairings * RR_ROUNDS} (double RR)")
        self.stdout.write(f"  Payment plan    : 27 auto-verified, {UNVERIFIED_COUNT} left as SUBMITTED")
        self.stdout.write(f"  Pre-draw mode   : {pre_draw}")
        self.stdout.write(f"  With results    : {with_results}")
        self.stdout.write("")
        self.stdout.write("  Steps that WOULD run:")
        steps = [
            "1.  get_or_create organizer user",
            "2.  get_or_create Game (slug)",
            "3.  Tournament.objects.create(has_entry_fee=True, entry_fee=100 BDT)",
            "4.  TournamentPaymentMethod.objects.create(bKash, 01780008001)",
            "5.  GroupStageService.create_groups(8, 4, 2)",
            "6.  RegistrationService.register_participant() × 32",
            "7.  RegistrationService.submit_payment(bkash, BKASH_TXN_xxx) × 32",
            f"8.  RegistrationService.verify_payment() × 27  (leave {UNVERIFIED_COUNT} SUBMITTED)",
        ]
        if pre_draw:
            steps.append("──  STOP (--pre-draw): groups left empty for Live Draw")
        else:
            steps += [
                "9.  GroupStageService.assign_participant() × 32",
                "10. GroupStageService.generate_group_matches(rounds=2) → 96 matches",
            ]
            if with_results:
                steps += [
                    "11. Inject random match scores (Match.state → COMPLETED)",
                    "12. GroupStageService.calculate_group_standings(stage_id)",
                ]
        for s in steps:
            self.stdout.write(f"    {s}")
        self.stdout.write("")
