"""
Management command: simulate_matches — generate match data and feed the CP pipeline.

Creates a simulation tournament, random matches between existing (or auto-created)
teams, marks them completed, and runs each through the ranking pipeline.

Usage:
    python manage.py simulate_matches                  # 100 matches, auto-create teams
    python manage.py simulate_matches --count 200      # 200 matches
    python manage.py simulate_matches --teams 30       # ensure 30 teams exist
    python manage.py simulate_matches --dry-run        # preview without writing
    python manage.py simulate_matches --reset          # wipe rankings first
"""

import random
import logging
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

logger = logging.getLogger(__name__)

# Defaults
DEFAULT_MATCH_COUNT = 100
DEFAULT_TEAM_COUNT = 24
GAME_DEFAULTS = {
    'name': 'Valorant',
    'display_name': 'VALORANT',
    'slug': 'valorant',
    'short_code': 'VAL',
    'category': 'FPS',
}


class Command(BaseCommand):
    help = "Generate simulated matches and feed the CP ranking pipeline."

    def add_arguments(self, parser):
        parser.add_argument(
            '--count', type=int, default=DEFAULT_MATCH_COUNT,
            help=f'Number of matches to generate (default: {DEFAULT_MATCH_COUNT})',
        )
        parser.add_argument(
            '--teams', type=int, default=DEFAULT_TEAM_COUNT,
            help=f'Ensure at least this many active teams exist (default: {DEFAULT_TEAM_COUNT})',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Show plan without creating anything.',
        )
        parser.add_argument(
            '--reset', action='store_true',
            help='Reset all TeamRanking CP/streaks to zero before simulating.',
        )
        parser.add_argument(
            '--seed', type=int, default=42,
            help='Random seed for reproducibility (default: 42)',
        )

    def handle(self, *args, **options):
        count = options['count']
        team_target = options['teams']
        dry_run = options['dry_run']
        reset = options['reset']
        seed = options['seed']

        random.seed(seed)
        self.stdout.write(f"Seed: {seed}  |  Matches: {count}  |  Teams target: {team_target}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — no changes will be made.\n"))
            self._plan(count, team_target)
            return

        # Step 1: Ensure infrastructure
        game = self._ensure_game()
        organizer = self._ensure_organizer()
        tournament = self._ensure_tournament(game, organizer)
        teams = self._ensure_teams(team_target, game)

        if reset:
            self._reset_rankings()

        # Step 2: Bootstrap rankings for all teams
        self._bootstrap_rankings(teams)

        # Step 3: Generate and process matches
        results = self._simulate(tournament, teams, count)

        # Step 4: Final rank computation
        from apps.organizations.services.ranking_service import compute_global_ranks
        compute_global_ranks()

        # Step 5: Report
        self._report(results, teams)

    # ------------------------------------------------------------------
    # Plan (dry-run)
    # ------------------------------------------------------------------
    def _plan(self, count, team_target):
        from apps.organizations.models import Team
        existing = Team.objects.filter(status='ACTIVE').count()
        to_create = max(0, team_target - existing)
        self.stdout.write(f"  Existing active teams: {existing}")
        self.stdout.write(f"  Teams to create:       {to_create}")
        self.stdout.write(f"  Matches to simulate:   {count}")
        self.stdout.write(f"  Approx CP distribution: varied (skill-weighted)")

    # ------------------------------------------------------------------
    # Infrastructure setup
    # ------------------------------------------------------------------
    def _ensure_game(self):
        from apps.games.models import Game
        game, created = Game.objects.get_or_create(
            slug=GAME_DEFAULTS['slug'],
            defaults=GAME_DEFAULTS,
        )
        if created:
            self.stdout.write(f"  Created game: {game.display_name}")
        return game

    def _ensure_organizer(self):
        user, created = User.objects.get_or_create(
            username='sim_organizer',
            defaults={
                'email': 'sim@deltacrown.local',
                'is_staff': True,
            },
        )
        if created:
            user.set_unusable_password()
            user.save(update_fields=['password'])
            self.stdout.write("  Created simulation organizer user")
        return user

    def _ensure_tournament(self, game, organizer):
        from apps.tournaments.models import Tournament
        now = timezone.now()
        slug = 'sim-season-1'
        tournament, created = Tournament.objects.get_or_create(
            slug=slug,
            defaults={
                'name': 'Simulation Season 1',
                'description': 'Auto-generated for CP pipeline validation.',
                'organizer': organizer,
                'game': game,
                'format': Tournament.ROUND_ROBIN,
                'status': Tournament.LIVE,
                'registration_start': now - timedelta(days=30),
                'registration_end': now - timedelta(days=25),
                'tournament_start': now - timedelta(days=20),
                'participation_type': Tournament.TEAM,
            },
        )
        if created:
            self.stdout.write(f"  Created tournament: {tournament.name}")
        return tournament

    def _ensure_teams(self, target, game):
        from apps.organizations.models import Team
        from apps.organizations.models.organization import Organization

        existing = list(Team.objects.filter(status='ACTIVE').order_by('id'))
        to_create = max(0, target - len(existing))

        TEAM_NAMES = [
            'Phoenix Rising', 'Shadow Wolves', 'Nova Strike', 'Crimson Elite',
            'Thunder Hawks', 'Frost Titans', 'Blaze Squad', 'Iron Vipers',
            'Storm Raiders', 'Dark Phoenix', 'Omega Force', 'Apex Legends',
            'Night Stalkers', 'Royal Guard', 'Cyber Knights', 'Blood Ravens',
            'Steel Panthers', 'Ghost Recon', 'Solar Flare', 'Arctic Fox',
            'Venom Strike', 'Dragon Slayers', 'Wild Cards', 'Rogue Knights',
            'Phantom Ops', 'Titan Squad', 'Blitz Team', 'Inferno Rising',
            'Eclipse Gaming', 'Neon Pulse', 'Valor Point', 'Death Wish',
        ]

        for i in range(to_create):
            idx = len(existing) + i
            name = TEAM_NAMES[idx % len(TEAM_NAMES)]
            # Avoid duplicate names
            if Team.objects.filter(name=name).exists():
                name = f"{name} {idx}"

            # Create a minimal org for the team
            org_user, _ = User.objects.get_or_create(
                username=f'sim_ceo_{idx}',
                defaults={'email': f'sim_ceo_{idx}@deltacrown.local'},
            )
            org = Organization.objects.create(
                name=f'Org {name}',
                ceo=org_user,
            )
            team = Team.objects.create(
                name=name,
                organization=org,
                game_id=game.id,
                region='BD',
            )
            existing.append(team)

        if to_create:
            self.stdout.write(f"  Created {to_create} teams (total: {len(existing)})")
        else:
            self.stdout.write(f"  {len(existing)} active teams (no creation needed)")

        return existing

    def _bootstrap_rankings(self, teams):
        from apps.organizations.models import TeamRanking
        created = 0
        for t in teams:
            _, was_created = TeamRanking.objects.get_or_create(team_id=t.id)
            if was_created:
                created += 1
        if created:
            self.stdout.write(f"  Bootstrapped {created} TeamRanking rows")

    def _reset_rankings(self):
        from apps.organizations.models import TeamRanking
        TeamRanking.objects.all().update(
            current_cp=0, season_cp=0, all_time_cp=0,
            tier='ROOKIE', streak_count=0, is_hot_streak=False,
            global_rank=None, activity_score=0,
            matches_today=0, recent_opponents={},
            elo_rating=1200,
        )
        self.stdout.write(self.style.WARNING("  All rankings reset to zero (ELO -> 1200)."))

    # ------------------------------------------------------------------
    # Match simulation
    # ------------------------------------------------------------------
    def _simulate(self, tournament, teams, count):
        from apps.tournaments.models import Match
        from apps.organizations.services.ranking_service import RankingService
        from apps.organizations.models import TeamRanking

        now = timezone.now()
        stats = defaultdict(lambda: {'wins': 0, 'losses': 0, 'cp': 0})

        # Assign hidden "skill" values so better teams win more often
        skill = {}
        for i, t in enumerate(teams):
            # Distribute skill 30-90 (some variance)
            skill[t.id] = random.gauss(60, 15)

        ok = 0
        failed = 0

        def _elo_aware_pair(teams_list):
            """70% chance of pairing teams within close ELO, 30% random."""
            if random.random() < 0.3 or len(teams_list) < 4:
                return random.sample(teams_list, 2)
            # Refresh ELO cache every 25 matches (cheap enough)
            if not hasattr(_elo_aware_pair, '_cache') or _elo_aware_pair._ttl <= 0:
                _elo_aware_pair._cache = dict(
                    TeamRanking.objects.values_list('team_id', 'elo_rating')
                )
                _elo_aware_pair._ttl = 25
            _elo_aware_pair._ttl -= 1
            elo_cache = _elo_aware_pair._cache
            sorted_teams = sorted(teams_list, key=lambda t: elo_cache.get(t.id, 1200))
            idx = random.randint(0, len(sorted_teams) - 2)
            # Pick from a nearby window of ±3 positions
            window_end = min(len(sorted_teams) - 1, idx + 6)
            partner_idx = random.randint(idx + 1, window_end)
            return [sorted_teams[idx], sorted_teams[partner_idx]]

        for i in range(count):
            t1, t2 = _elo_aware_pair(teams)

            # Determine winner based on hidden skill (+ noise)
            s1 = skill[t1.id] + random.gauss(0, 10)
            s2 = skill[t2.id] + random.gauss(0, 10)
            if s1 >= s2:
                winner, loser = t1, t2
            else:
                winner, loser = t2, t1

            # Determine scores
            winner_score = random.choice([2, 3, 13, 13])
            loser_score = random.randint(0, max(0, winner_score - 1))

            match_time = now - timedelta(
                days=random.randint(0, 20),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59),
            )

            # Create completed match directly
            match = Match(
                tournament=tournament,
                round_number=1,
                match_number=i + 1,
                participant1_id=winner.id,
                participant1_name=winner.name,
                participant2_id=loser.id,
                participant2_name=loser.name,
                state='completed',
                participant1_score=winner_score,
                participant2_score=loser_score,
                winner_id=winner.id,
                loser_id=loser.id,
                completed_at=match_time,
                best_of=random.choice([1, 3]),
            )
            match.save()

            # Feed through ranking pipeline directly
            try:
                delta = RankingService.apply_match_result(
                    winner_team_id=winner.id,
                    loser_team_id=loser.id,
                    match_id=match.id,
                    is_tournament_match=True,
                )
                stats[winner.id]['wins'] += 1
                stats[winner.id]['cp'] += delta.winner_cp_gain
                stats[loser.id]['losses'] += 1
                stats[loser.id]['cp'] -= delta.loser_cp_loss
                ok += 1
            except Exception as exc:
                failed += 1
                self.stderr.write(f"  Match {i+1} failed: {exc}")

            if (i + 1) % 50 == 0:
                self.stdout.write(f"  ... {i+1}/{count} matches processed")

        self.stdout.write(self.style.SUCCESS(
            f"\n  Simulation complete: {ok} ok, {failed} failed"
        ))
        return stats

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------
    def _report(self, stats, teams):
        from apps.organizations.models import TeamRanking

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("  TOP 10 TEAMS BY CROWN POINTS")
        self.stdout.write("=" * 70)
        self.stdout.write(
            f"  {'Rank':<5} {'Team':<22} {'CP':>6} {'ELO':>5} "
            f"{'Tier':<12} {'W':>3} {'L':>3} {'Str':>3} {'Act':>3}"
        )
        self.stdout.write("-" * 70)

        top = TeamRanking.objects.select_related('team').order_by(
            '-current_cp'
        )[:10]

        for r in top:
            s = stats.get(r.team_id, {'wins': 0, 'losses': 0})
            self.stdout.write(
                f"  {r.global_rank or '-':<5} {r.team.name:<22} "
                f"{r.current_cp:>6,} {r.elo_rating:>5} "
                f"{r.tier:<12} "
                f"{s['wins']:>3} {s['losses']:>3} "
                f"{r.streak_count:>3} {r.activity_score:>3}"
            )

        self.stdout.write("")

        # Tier distribution
        self.stdout.write("  TIER DISTRIBUTION")
        self.stdout.write("-" * 40)
        from django.db.models import Count
        tiers = (
            TeamRanking.objects
            .values('tier')
            .annotate(count=Count('team_id'))
            .order_by('-count')
        )
        for t in tiers:
            self.stdout.write(f"    {t['tier']:<12} {t['count']:>4} teams")

        # NULL rank check
        null_count = TeamRanking.objects.filter(global_rank__isnull=True).count()
        total = TeamRanking.objects.count()
        if null_count == 0:
            self.stdout.write(self.style.SUCCESS(
                f"\n  All {total} teams have global_rank assigned. Zero NULLs."
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"\n  WARNING: {null_count}/{total} teams have NULL global_rank!"
            ))

        # ELO stats
        from django.db.models import Avg, Min, Max, StdDev
        elo_stats = TeamRanking.objects.aggregate(
            avg=Avg('elo_rating'), mn=Min('elo_rating'),
            mx=Max('elo_rating'), sd=StdDev('elo_rating'),
        )
        self.stdout.write(
            f"\n  ELO STATS  avg={elo_stats['avg']:.0f}  "
            f"min={elo_stats['mn']}  max={elo_stats['mx']}  "
            f"stddev={elo_stats['sd']:.0f}"
        )

        # NULL check
        nulls = TeamRanking.objects.filter(global_rank__isnull=True).count()
        total = TeamRanking.objects.count()
        if nulls == 0:
            self.stdout.write(self.style.SUCCESS(
                f"\n  All {total} teams have global_rank assigned. Zero NULLs."
            ))
        else:
            self.stdout.write(self.style.ERROR(
                f"\n  WARNING: {nulls}/{total} teams have NULL global_rank!"
            ))
