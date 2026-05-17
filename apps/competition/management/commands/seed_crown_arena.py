"""Seed the Crown Arena with realistic data, routed through the live services.

Goes through ChallengeService / BountyService so the real escrow locks,
RBAC checks, and Match Room spawn all execute end-to-end.  Wallets are
topped up to a known floor before any creation call so the lock_funds()
path can never trip on insufficient balance.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


SEED_FUNDING_FLOOR_DC = 5_000


class Command(BaseCommand):
    help = "Seed the Crown Arena via live services (escrow + RBAC + match-room hooks)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--game",
            default=None,
            help="Game short_code to bind clashes/bounties to (default: first VAL/CS2/etc with 2+ team captains).",
        )
        parser.add_argument(
            "--wipe",
            action="store_true",
            help="Delete previously-seeded rows (matched by title) before seeding.",
        )

    # ── output helpers ────────────────────────────────────────────────────

    def _ok(self, msg):  self.stdout.write(self.style.SUCCESS(f"  [+] {msg}"))
    def _warn(self, msg): self.stdout.write(self.style.WARNING(f"  [-] {msg}"))
    def _err(self, msg):  self.stderr.write(self.style.ERROR(f"  [!] {msg}"))
    def _hdr(self, msg):  self.stdout.write(self.style.HTTP_INFO(f"\n{msg}"))

    # ── main ──────────────────────────────────────────────────────────────

    def handle(self, *args, **options):
        from apps.competition.models import Bounty, Challenge
        from apps.competition.services.challenge_service import (
            BountyService,
            ChallengeService,
        )
        from apps.contracts.models import ContractTemplate
        from apps.economy.models import DeltaCrownTransaction, DeltaCrownWallet
        from apps.games.models import Game
        from apps.organizations.models import TeamMembership
        from apps.royale.models import RoyaleLobby
        from apps.tournaments.models import Tournament

        User = get_user_model()

        self._hdr("=== Seeding Crown Arena (live services) ===")

        if options.get("wipe"):
            self._wipe(
                Bounty=Bounty,
                Challenge=Challenge,
                ContractTemplate=ContractTemplate,
                RoyaleLobby=RoyaleLobby,
            )

        # ── (a) Pick a game with at least two OWNER/MANAGER captains ──
        game = self._select_game(Game, TeamMembership, options.get("game"))
        if game is None:
            self._err("No active game has two OWNER/MANAGER captains.  Aborting.")
            return

        captains = self._select_captains(TeamMembership, game)
        if len(captains) < 2:
            self._err(
                f"Need at least 2 team captains for {game.short_code}; "
                f"found {len(captains)}.  Aborting."
            )
            return
        captain_a, captain_b = captains[0], captains[1]
        self._ok(
            f"Game = {game.short_code} ({game.display_name}).  "
            f"Captain A = '{captain_a['user'].username}' on '{captain_a['team'].name}', "
            f"Captain B = '{captain_b['user'].username}' on '{captain_b['team'].name}'."
        )

        # ── (b) Top up both captains' personal wallets to the floor ──
        self._top_up(DeltaCrownWallet, DeltaCrownTransaction, captain_a["user"])
        self._top_up(DeltaCrownWallet, DeltaCrownTransaction, captain_b["user"])

        counts = {
            "contract_templates": 0,
            "clashes_open": 0,
            "clashes_accepted": 0,
            "match_rooms": 0,
            "hitlist_bounties": 0,
            "royale_lobbies": 0,
        }

        # ── (1) Crown Contracts ──────────────────────────────────────────
        self._hdr("[1/4] Crown Contracts")
        contract_specs = [
            {
                "title": "The Survivor's Path",
                "description": "Outlast the chaos.  Finish in the Top 5 across three Battle Royale matches inside 24 hours.",
                "entry_fee_dc": 50,
                "reward_dc": 200,
                "goal_type": "TOP_N_FINISH",
                "duration_hours": 24,
                "badge_slug": "survivor",
                "goal_spec": {"metric": "top_n_finish", "n": 5, "count": 3, "window_hours": 24},
            },
            {
                "title": "Headhunter",
                "description": "Stack 50 confirmed eliminations across five matches.  Precision over panic.",
                "entry_fee_dc": 50,
                "reward_dc": 200,
                "goal_type": "KILL_THRESHOLD",
                "duration_hours": 24,
                "badge_slug": "headhunter",
                "goal_spec": {"metric": "total_kills", "threshold": 50, "matches": 5},
            },
        ]
        for spec in contract_specs:
            try:
                tpl, created = ContractTemplate.objects.get_or_create(
                    title=spec["title"],
                    game=game,
                    defaults={
                        "description": spec["description"],
                        "entry_fee_dc": spec["entry_fee_dc"],
                        "reward_dc": spec["reward_dc"],
                        "goal_type": spec["goal_type"],
                        "goal_spec": spec["goal_spec"],
                        "duration_hours": spec["duration_hours"],
                        "is_active": True,
                        "badge_slug": spec["badge_slug"],
                    },
                )
                if created:
                    counts["contract_templates"] += 1
                    self._ok(
                        f"Contract  '{tpl.title}' [{game.short_code}] "
                        f"— {tpl.entry_fee_dc} DC entry / {tpl.reward_dc} DC reward"
                    )
                else:
                    self._warn(f"Contract  '{tpl.title}' already exists — skipped")
            except Exception as e:
                self._err(f"Contract '{spec['title']}': {e}")

        # ── (2) Showdowns (via service) ──────────────────────────────────
        self._hdr("[2/4] Showdown (via ChallengeService)")
        ENTRY_FEE = 300
        open_clash_title = "Friday Night Showdown"
        direct_clash_title = "Neon District Qualifiers"

        # 2a — open clash from Captain A (no opponent specified)
        try:
            open_clash = self._create_clash_or_skip(
                ChallengeService=ChallengeService,
                Challenge=Challenge,
                title=open_clash_title,
                description="Open call to any team brave enough to step up.  BO3 on the standard map pool.",
                actor=captain_a["user"],
                challenger_team=captain_a["team"],
                challenged_team=None,
                game=game,
                challenge_type="OPEN",
                best_of=3,
                entry_fee_dc=ENTRY_FEE,
            )
            if open_clash and not open_clash._existing:
                counts["clashes_open"] += 1
                self._ok(
                    f"Clash     [{open_clash.reference_code}] '{open_clash.title}' "
                    f"— {ENTRY_FEE} DC × 2 (status={open_clash.status}, OPEN)"
                )
        except Exception as e:
            self._err(f"Open clash '{open_clash_title}': {e}")

        # 2b — direct clash + accept it from Captain B
        try:
            direct_clash = self._create_clash_or_skip(
                ChallengeService=ChallengeService,
                Challenge=Challenge,
                title=direct_clash_title,
                description="Direct duel for bracket seeding.  Pot is locked, scoreboard is live.",
                actor=captain_a["user"],
                challenger_team=captain_a["team"],
                challenged_team=captain_b["team"],
                game=game,
                challenge_type="DIRECT",
                best_of=5,
                entry_fee_dc=ENTRY_FEE,
            )
            if direct_clash:
                if not direct_clash._existing:
                    counts["clashes_open"] += 1
                    self._ok(
                        f"Clash     [{direct_clash.reference_code}] '{direct_clash.title}' "
                        f"— {ENTRY_FEE} DC × 2 (status={direct_clash.status}, "
                        f"vs {captain_b['team'].name})"
                    )
                # Accept (transitions OPEN -> ACCEPTED, locks opponent entry, spawns Match Room).
                if direct_clash.status == "OPEN":
                    accepted = ChallengeService.accept_challenge(
                        challenge_id=direct_clash.pk,
                        accepted_by=captain_b["user"],
                        accepting_team=captain_b["team"],
                    )
                    counts["clashes_accepted"] += 1
                    if getattr(accepted, "match_id", None):
                        counts["match_rooms"] += 1
                    self._ok(
                        f"Accepted  [{accepted.reference_code}] by '{captain_b['user'].username}' "
                        f"— status={accepted.status}, escrow_locked={accepted.escrow_locked}, "
                        f"match_id={accepted.match_id}"
                    )
                else:
                    self._warn(
                        f"Direct clash already in status {direct_clash.status} — skipped accept"
                    )
        except Exception as e:
            self._err(f"Direct clash '{direct_clash_title}': {e}")

        # ── (3) Bounty (via service) ─────────────────────────────────────
        self._hdr("[3/4] Bounty (via BountyService)")
        hitlist_title = "Can You Beat the Kings?"
        try:
            existing = Bounty.objects.filter(
                title=hitlist_title, issuer_team=captain_a["team"]
            ).first()
            if existing:
                self._warn(f"Hitlist   '{hitlist_title}' already exists — skipped")
            else:
                bounty = BountyService.create_bounty(
                    created_by=captain_a["user"],
                    issuer_team=captain_a["team"],
                    game=game,
                    title=hitlist_title,
                    description=(
                        "We hold the top spot.  Pay the entry fee, run the gauntlet, "
                        "take the crown if you can."
                    ),
                    bounty_type="BEAT_US",
                    reward_type="CP",
                    reward_amount=Decimal("1000"),
                    reward_amount_dc=1000,
                    max_claims=1,
                    is_hitlist=True,
                    challenger_entry_fee_dc=200,
                    is_public=True,
                )
                counts["hitlist_bounties"] += 1
                self._ok(
                    f"Hitlist   [{bounty.reference_code}] '{bounty.title}' "
                    f"— {bounty.reward_amount_dc} DC bounty / "
                    f"{bounty.challenger_entry_fee_dc} DC entry "
                    f"(escrow_locked={bounty.escrow_locked}, "
                    f"funded_by={getattr(bounty.funded_by, 'username', None)})"
                )
        except Exception as e:
            self._err(f"Hitlist '{hitlist_title}': {e}")

        # ── (4) Dropzone ─────────────────────────────────────────────────
        self._hdr("[4/4] Dropzone")
        try:
            tournament = (
                Tournament.objects
                .filter(royale_lobby__isnull=True)
                .order_by("id")
                .first()
            )
            if tournament is None:
                self._warn("No tournament without an existing Royale lobby — skipping.")
            else:
                title = "Friday Night Bermuda Drop"
                if RoyaleLobby.objects.filter(title=title, game=game).exists():
                    self._warn(f"Royale    '{title}' already exists — skipped")
                else:
                    sched = timezone.now() + timedelta(days=1)
                    lobby = RoyaleLobby.objects.create(
                        tournament=tournament,
                        game=game,
                        title=title,
                        slot_capacity=48,
                        entry_fee_dc=20,
                        scheduled_at=sched,
                        registration_opens_at=timezone.now() - timedelta(hours=1),
                        registration_closes_at=sched,
                        status="FILLING",
                        prize_distribution={
                            "mode": "PERCENT",
                            "splits": {"1": 50, "2": 25, "3": 10},
                        },
                        is_public=True,
                        is_featured=True,
                        created_by=captain_a["user"],
                    )
                    counts["royale_lobbies"] += 1
                    self._ok(
                        f"Royale    [{lobby.reference_code}] '{lobby.title}' "
                        f"— {lobby.slot_capacity} slots × {lobby.entry_fee_dc} DC, "
                        f"scheduled {sched:%a %d %b %H:%M}"
                    )
        except Exception as e:
            self._err(f"Royale lobby: {e}")

        # ── Summary ──────────────────────────────────────────────────────
        self._hdr("=== Summary ===")
        for label, count in counts.items():
            line = f"  {label:<22} {count}"
            self.stdout.write(
                self.style.SUCCESS(line) if count else self.style.WARNING(line)
            )
        self.stdout.write(self.style.HTTP_INFO(
            f"\nWallets now: "
            f"{captain_a['user'].username}={self._wallet_balance(DeltaCrownWallet, captain_a['user'])} DC, "
            f"{captain_b['user'].username}={self._wallet_balance(DeltaCrownWallet, captain_b['user'])} DC"
        ))
        self.stdout.write(self.style.HTTP_INFO(
            "Visit /dashboard/competitive/ to see the cards populate.\n"
        ))

    # ── helpers ──────────────────────────────────────────────────────────

    def _select_game(self, Game, TeamMembership, requested_short_code):
        if requested_short_code:
            game = Game.objects.filter(
                is_active=True, short_code__iexact=requested_short_code
            ).first()
            if game and self._captain_count(TeamMembership, game) >= 2:
                return game
            return None
        for game in Game.objects.filter(is_active=True).order_by("id"):
            if self._captain_count(TeamMembership, game) >= 2:
                return game
        return None

    def _captain_count(self, TeamMembership, game):
        return TeamMembership.objects.filter(
            status="ACTIVE", role__in=["OWNER", "MANAGER"], game_id=game.id,
        ).values("team_id").distinct().count()

    def _select_captains(self, TeamMembership, game):
        seen_teams = set()
        out = []
        for m in (
            TeamMembership.objects
            .filter(status="ACTIVE", role__in=["OWNER", "MANAGER"], game_id=game.id)
            .select_related("user", "team")
            .order_by("id")
        ):
            if not m.team or m.team_id in seen_teams:
                continue
            seen_teams.add(m.team_id)
            out.append({"user": m.user, "team": m.team, "role": m.role})
            if len(out) == 2:
                break
        return out

    def _wallet_balance(self, DeltaCrownWallet, user):
        try:
            return DeltaCrownWallet.objects.get(profile__user=user).cached_balance
        except DeltaCrownWallet.DoesNotExist:
            return None

    def _top_up(self, DeltaCrownWallet, DeltaCrownTransaction, user):
        """Ensure user has at least SEED_FUNDING_FLOOR_DC in their wallet.

        Posts a clean ledger row + recalculates from the ledger so the
        ``cached_balance`` ↔ ledger-sum invariant stays intact.
        """
        try:
            wallet = DeltaCrownWallet.objects.get(profile__user=user)
        except DeltaCrownWallet.DoesNotExist:
            self._err(
                f"User '{user.username}' has no DeltaCrownWallet — cannot fund.  "
                "Showdown creation will fail downstream."
            )
            return

        with transaction.atomic():
            wallet.refresh_from_db()
            current = wallet.cached_balance
            if current >= SEED_FUNDING_FLOOR_DC:
                self._ok(
                    f"Wallet    {user.username} already at {current} DC — no top-up needed"
                )
                return
            top_up = SEED_FUNDING_FLOOR_DC - current
            DeltaCrownTransaction.objects.create(
                wallet=wallet,
                amount=top_up,
                reason=DeltaCrownTransaction.Reason.TOP_UP,
                note="Crown Arena seed funding",
                cached_balance_after=current + top_up,
            )
            wallet.recalc_and_save()
            self._ok(
                f"Wallet    {user.username} topped up "
                f"{current} -> {wallet.cached_balance} DC (+{top_up})"
            )

    SEEDED_TITLES = {
        "contracts": [
            "The Survivor's Path", "Headhunter", "Flawless Victory",
        ],
        "clashes": [
            "Friday Night Showdown", "Neon District Qualifiers",
            "Midnight Duel - Aim Only",
        ],
        "bounties": [
            "Can You Beat the Kings?", "The Crown Awaits - Open Hitlist",
        ],
        "royale": [
            "Friday Night Bermuda Drop", "Saturday Skywars - Headliner",
        ],
    }

    def _wipe(self, *, Bounty, Challenge, ContractTemplate, RoyaleLobby):
        """Hard-delete previously-seeded rows by title.

        Auto-spawned synthetic Tournaments + Matches cascade off the
        Challenge / BountyClaim / RoyaleLobby on delete (FKs are
        SET_NULL, so the Tournament rows themselves are left intact —
        not a problem, they're tiny and hidden).
        """
        from apps.contracts.models import ContractEnrollment

        try:
            ContractEnrollment.objects.filter(
                template__title__in=self.SEEDED_TITLES["contracts"]
            ).delete()
            ContractTemplate.objects.filter(
                title__in=self.SEEDED_TITLES["contracts"]
            ).delete()
            Challenge.objects.filter(
                title__in=self.SEEDED_TITLES["clashes"]
            ).delete()
            Bounty.objects.filter(
                title__in=self.SEEDED_TITLES["bounties"]
            ).delete()
            RoyaleLobby.objects.filter(
                title__in=self.SEEDED_TITLES["royale"]
            ).delete()
            self._ok("Wipe complete — Phase-9 + Phase-11 seed rows deleted.")
        except Exception as e:
            self._err(f"Wipe failed: {e}")

    def _create_clash_or_skip(
        self, *, ChallengeService, Challenge, title, description, actor,
        challenger_team, challenged_team, game, challenge_type, best_of,
        entry_fee_dc,
    ):
        existing = Challenge.objects.filter(
            title=title, challenger_team=challenger_team
        ).first()
        if existing:
            self._warn(f"Clash      '{title}' already exists — using existing row")
            existing._existing = True
            return existing
        ch = ChallengeService.create_challenge(
            created_by=actor,
            challenger_team=challenger_team,
            challenged_team=challenged_team,
            game=game,
            title=title,
            description=description,
            challenge_type=challenge_type,
            best_of=best_of,
            entry_fee_dc=entry_fee_dc,
            is_public=True,
        )
        ch._existing = False
        return ch
