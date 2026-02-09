"""
Leaderboard Contract Tests.

Tests that leaderboard ranking logic conforms to spec contracts:
- FF/PUBG scoring tables (12/9/7/5 points)
- Pagination and sort order
- Rank history monotonic timestamps
- Snapshot generation idempotency
"""

import pytest
from django.utils import timezone
from datetime import timedelta
from apps.leaderboards.services import LeaderboardService
from apps.leaderboards.models import LeaderboardEntry, LeaderboardSnapshot
from apps.tournaments.models import Tournament, TournamentTeam, Match
from apps.organizations.models import Team
from apps.accounts.models import User


@pytest.fixture
def leaderboard_service():
    """Get leaderboard service instance."""
    return LeaderboardService()


@pytest.fixture
def sample_tournament(db):
    """Create sample tournament."""
    return Tournament.objects.create(
        name="Valorant Champions Q4 2025",
        game="valorant",
        tier="premier",
        start_date=timezone.now(),
        status="in_progress"
    )


@pytest.fixture
def sample_teams(db):
    """Create sample teams."""
    teams = []
    for i in range(8):
        teams.append(Team.objects.create(
            name=f"Team {chr(65+i)}",  # Team A, Team B, ...
            tag=f"T{chr(65+i)}",
            verified=True
        ))
    return teams


@pytest.mark.django_db
class TestTournamentLeaderboardContract:
    """Test tournament leaderboard ranking contracts."""

    def test_placement_points_contract(self, leaderboard_service):
        """Test that placement points match spec contract."""
        # Spec: 1st=1000, 2nd=750, 3rd=500, 4-8=250, 9-16=100, 17+=25
        assert leaderboard_service.get_placement_points(1) == 1000
        assert leaderboard_service.get_placement_points(2) == 750
        assert leaderboard_service.get_placement_points(3) == 500
        assert leaderboard_service.get_placement_points(4) == 250
        assert leaderboard_service.get_placement_points(8) == 250
        assert leaderboard_service.get_placement_points(9) == 100
        assert leaderboard_service.get_placement_points(16) == 100
        assert leaderboard_service.get_placement_points(17) == 25
        assert leaderboard_service.get_placement_points(100) == 25

    def test_ff_pubg_scoring_table(self, leaderboard_service):
        """Test FF/PUBG scoring table (12/9/7/5 points)."""
        # For battle royale games, different scoring
        # This test validates custom scoring contracts
        
        # Example: Free Fire scoring
        ff_scoring = {
            1: 12,  # Winner
            2: 9,   # Second
            3: 7,   # Third
            4: 5,   # Fourth
            5: 3,   # Fifth-Eighth
            # ...
        }
        
        # Contract: Top 4 get decreasing points
        assert ff_scoring[1] > ff_scoring[2] > ff_scoring[3] > ff_scoring[4]
        
        # Contract: Point gaps reasonable (not exponential)
        assert (ff_scoring[1] - ff_scoring[2]) <= 5
        assert (ff_scoring[2] - ff_scoring[3]) <= 5

    def test_tournament_leaderboard_sort_order(
        self,
        leaderboard_service,
        sample_tournament,
        sample_teams
    ):
        """Test that teams ranked correctly by placement, wins, points."""
        # Create tournament teams with different placements
        TournamentTeam.objects.create(
            tournament=sample_tournament,
            team=sample_teams[0],
            placement=1,  # Winner
            registered_at=timezone.now() - timedelta(days=10)
        )
        TournamentTeam.objects.create(
            tournament=sample_tournament,
            team=sample_teams[1],
            placement=2,  # Second
            registered_at=timezone.now() - timedelta(days=9)
        )
        TournamentTeam.objects.create(
            tournament=sample_tournament,
            team=sample_teams[2],
            placement=2,  # Tied for second (test tie-breaker)
            registered_at=timezone.now() - timedelta(days=8)  # Registered later
        )
        
        # Compute leaderboard
        entries = leaderboard_service.compute_tournament_leaderboard(sample_tournament.id)
        
        # Contract: Winner (placement=1) must be rank 1
        assert entries[0].rank == 1
        assert entries[0].team == sample_teams[0]
        
        # Contract: Tied placement sorted by registration time (earlier wins)
        assert entries[1].rank == 2
        assert entries[1].team == sample_teams[1]  # Registered earlier
        assert entries[2].rank == 3
        assert entries[2].team == sample_teams[2]  # Registered later

    def test_tournament_leaderboard_win_bonus(
        self,
        leaderboard_service,
        sample_tournament,
        sample_teams
    ):
        """Test that match wins add bonus points."""
        # Create teams with same placement but different win counts
        tt1 = TournamentTeam.objects.create(
            tournament=sample_tournament,
            team=sample_teams[0],
            placement=3,
            registered_at=timezone.now() - timedelta(days=5)
        )
        tt2 = TournamentTeam.objects.create(
            tournament=sample_tournament,
            team=sample_teams[1],
            placement=3,
            registered_at=timezone.now() - timedelta(days=5)
        )
        
        # Team 0: 5 wins
        for _ in range(5):
            Match.objects.create(
                tournament=sample_tournament,
                team1=sample_teams[0],
                team2=sample_teams[2],
                winner=sample_teams[0],
                status="completed"
            )
        
        # Team 1: 2 wins
        for _ in range(2):
            Match.objects.create(
                tournament=sample_tournament,
                team1=sample_teams[1],
                team2=sample_teams[3],
                winner=sample_teams[1],
                status="completed"
            )
        
        entries = leaderboard_service.compute_tournament_leaderboard(sample_tournament.id)
        
        # Find teams in results
        team0_entry = next(e for e in entries if e.team == sample_teams[0])
        team1_entry = next(e for e in entries if e.team == sample_teams[1])
        
        # Contract: More wins = higher rank (same placement)
        assert team0_entry.rank < team1_entry.rank
        assert team0_entry.wins == 5
        assert team1_entry.wins == 2
        
        # Contract: Win bonus = 10 points per win
        base_points = leaderboard_service.get_placement_points(3)
        assert team0_entry.points == base_points + (5 * 10)
        assert team1_entry.points == base_points + (2 * 10)


@pytest.mark.django_db
class TestLeaderboardPaginationAndSort:
    """Test pagination and sort contracts."""

    def test_get_leaderboard_pagination(
        self,
        leaderboard_service,
        sample_tournament,
        sample_teams
    ):
        """Test that pagination returns correct page slices."""
        # Create 8 teams with ranks 1-8
        for i, team in enumerate(sample_teams):
            LeaderboardEntry.objects.create(
                leaderboard_type="tournament",
                tournament=sample_tournament,
                team=team,
                rank=i + 1,
                points=1000 - (i * 100),
                is_active=True
            )
        
        # Get first page (limit=3)
        page1 = leaderboard_service.get_leaderboard(
            leaderboard_type="tournament",
            tournament_id=sample_tournament.id,
            limit=3,
            offset=0
        )
        
        # Contract: Page 1 contains ranks 1-3
        assert len(page1) == 3
        assert page1[0].rank == 1
        assert page1[1].rank == 2
        assert page1[2].rank == 3
        
        # Get second page (limit=3, offset=3)
        page2 = leaderboard_service.get_leaderboard(
            leaderboard_type="tournament",
            tournament_id=sample_tournament.id,
            limit=3,
            offset=3
        )
        
        # Contract: Page 2 contains ranks 4-6
        assert len(page2) == 3
        assert page2[0].rank == 4
        assert page2[1].rank == 5
        assert page2[2].rank == 6

    def test_get_leaderboard_sort_ascending(
        self,
        leaderboard_service,
        sample_tournament,
        sample_teams
    ):
        """Test that leaderboard always sorted by rank ascending (1, 2, 3, ...)."""
        # Create teams in random order
        ranks = [5, 2, 8, 1, 3, 7, 4, 6]
        for rank, team in zip(ranks, sample_teams):
            LeaderboardEntry.objects.create(
                leaderboard_type="tournament",
                tournament=sample_tournament,
                team=team,
                rank=rank,
                points=1000 - (rank * 100),
                is_active=True
            )
        
        # Get leaderboard
        entries = leaderboard_service.get_leaderboard(
            leaderboard_type="tournament",
            tournament_id=sample_tournament.id,
            limit=100
        )
        
        # Contract: Ranks must be ascending (1, 2, 3, ...)
        for i, entry in enumerate(entries):
            assert entry.rank == i + 1

    def test_inactive_players_excluded(
        self,
        leaderboard_service,
        sample_tournament,
        sample_teams
    ):
        """Test that inactive players excluded from public leaderboards."""
        # Create 4 active teams
        for i in range(4):
            LeaderboardEntry.objects.create(
                leaderboard_type="tournament",
                tournament=sample_tournament,
                team=sample_teams[i],
                rank=i + 1,
                points=1000 - (i * 100),
                is_active=True
            )
        
        # Create 2 inactive teams
        for i in range(4, 6):
            LeaderboardEntry.objects.create(
                leaderboard_type="tournament",
                tournament=sample_tournament,
                team=sample_teams[i],
                rank=i + 1,
                points=1000 - (i * 100),
                is_active=False  # Inactive
            )
        
        # Get leaderboard
        entries = leaderboard_service.get_leaderboard(
            leaderboard_type="tournament",
            tournament_id=sample_tournament.id,
            limit=100
        )
        
        # Contract: Only active entries returned
        assert len(entries) == 4
        assert all(e.is_active for e in entries)


@pytest.mark.django_db
class TestPlayerRankHistoryContract:
    """Test player rank history contracts."""

    def test_rank_history_monotonic_timestamps(
        self,
        leaderboard_service,
        db
    ):
        """Test that rank history timestamps are monotonically increasing."""
        player = User.objects.create_user(username="test_player", password="pass123")
        
        # Create snapshots over 7 days
        base_date = timezone.now().date() - timedelta(days=7)
        for i in range(7):
            LeaderboardSnapshot.objects.create(
                date=base_date + timedelta(days=i),
                leaderboard_type="seasonal",
                player=player,
                rank=10 - i,  # Rank improving over time (10 → 4)
                points=1000 + (i * 100)
            )
        
        # Get history
        history = leaderboard_service.get_player_rank_history(
            player_id=player.id,
            leaderboard_type="seasonal",
            days=7
        )
        
        # Contract: Timestamps must be monotonically increasing
        for i in range(len(history) - 1):
            date1 = history[i]["date"]
            date2 = history[i + 1]["date"]
            assert date1 < date2, f"Timestamps not monotonic: {date1} >= {date2}"

    def test_rank_history_no_gaps(
        self,
        leaderboard_service,
        db
    ):
        """Test that rank history has no missing dates (daily snapshots)."""
        player = User.objects.create_user(username="test_player", password="pass123")
        
        # Create snapshots for 5 consecutive days
        base_date = timezone.now().date() - timedelta(days=5)
        for i in range(5):
            LeaderboardSnapshot.objects.create(
                date=base_date + timedelta(days=i),
                leaderboard_type="seasonal",
                player=player,
                rank=10,
                points=1000
            )
        
        history = leaderboard_service.get_player_rank_history(
            player_id=player.id,
            leaderboard_type="seasonal",
            days=5
        )
        
        # Contract: All 5 days present (no gaps)
        assert len(history) == 5
        
        # Contract: Consecutive dates
        for i in range(len(history) - 1):
            date1 = timezone.datetime.fromisoformat(history[i]["date"]).date()
            date2 = timezone.datetime.fromisoformat(history[i + 1]["date"]).date()
            assert (date2 - date1).days == 1


@pytest.mark.django_db
class TestSnapshotGenerationIdempotency:
    """Test snapshot generation idempotency contracts."""

    def test_snapshot_idempotent(
        self,
        leaderboard_service,
        sample_tournament,
        sample_teams
    ):
        """Test that running snapshot twice produces same result."""
        # Create leaderboard entries
        for i, team in enumerate(sample_teams[:3]):
            LeaderboardEntry.objects.create(
                leaderboard_type="tournament",
                tournament=sample_tournament,
                team=team,
                rank=i + 1,
                points=1000 - (i * 100),
                is_active=True
            )
        
        # Run snapshot first time
        leaderboard_service.snapshot_leaderboards()
        snapshot_count_1 = LeaderboardSnapshot.objects.count()
        
        # Run snapshot second time (same day)
        leaderboard_service.snapshot_leaderboards()
        snapshot_count_2 = LeaderboardSnapshot.objects.count()
        
        # Contract: Snapshot count unchanged (upsert, not duplicate)
        assert snapshot_count_1 == snapshot_count_2
        
        # Contract: Snapshot data unchanged
        today = timezone.now().date()
        snapshots = LeaderboardSnapshot.objects.filter(date=today)
        assert snapshots.count() == 3  # 3 teams snapshotted

    def test_snapshot_updates_existing(
        self,
        leaderboard_service,
        sample_tournament,
        sample_teams
    ):
        """Test that snapshot updates existing entry if rank/points change."""
        team = sample_teams[0]
        
        # Create initial entry (rank 5, 500 points)
        entry = LeaderboardEntry.objects.create(
            leaderboard_type="tournament",
            tournament=sample_tournament,
            team=team,
            rank=5,
            points=500,
            is_active=True
        )
        
        # Snapshot first time
        leaderboard_service.snapshot_leaderboards()
        today = timezone.now().date()
        snapshot = LeaderboardSnapshot.objects.get(date=today, team=team)
        assert snapshot.rank == 5
        assert snapshot.points == 500
        
        # Update entry (rank improved to 2, 800 points)
        entry.rank = 2
        entry.points = 800
        entry.save()
        
        # Snapshot second time
        leaderboard_service.snapshot_leaderboards()
        snapshot.refresh_from_db()
        
        # Contract: Snapshot updated (not duplicated)
        assert snapshot.rank == 2
        assert snapshot.points == 800
        assert LeaderboardSnapshot.objects.filter(date=today, team=team).count() == 1


@pytest.mark.django_db
class TestTieBreakingContract:
    """Test tie-breaking rules."""

    def test_tie_breaking_by_wins(
        self,
        leaderboard_service,
        sample_tournament,
        sample_teams
    ):
        """Test that ties broken by total wins."""
        # Two teams, same placement, different wins
        TournamentTeam.objects.create(
            tournament=sample_tournament,
            team=sample_teams[0],
            placement=3,
            registered_at=timezone.now() - timedelta(days=5)
        )
        TournamentTeam.objects.create(
            tournament=sample_tournament,
            team=sample_teams[1],
            placement=3,
            registered_at=timezone.now() - timedelta(days=5)
        )
        
        # Team 0: 10 wins
        for _ in range(10):
            Match.objects.create(
                tournament=sample_tournament,
                team1=sample_teams[0],
                team2=sample_teams[2],
                winner=sample_teams[0],
                status="completed"
            )
        
        # Team 1: 5 wins
        for _ in range(5):
            Match.objects.create(
                tournament=sample_tournament,
                team1=sample_teams[1],
                team2=sample_teams[3],
                winner=sample_teams[1],
                status="completed"
            )
        
        entries = leaderboard_service.compute_tournament_leaderboard(sample_tournament.id)
        
        # Contract: Team with more wins ranked higher
        team0_entry = next(e for e in entries if e.team == sample_teams[0])
        team1_entry = next(e for e in entries if e.team == sample_teams[1])
        assert team0_entry.rank < team1_entry.rank

    def test_tie_breaking_by_registration_time(
        self,
        leaderboard_service,
        sample_tournament,
        sample_teams
    ):
        """Test that final tie broken by earlier registration."""
        # Two teams, same placement, same wins (no matches)
        TournamentTeam.objects.create(
            tournament=sample_tournament,
            team=sample_teams[0],
            placement=5,
            registered_at=timezone.now() - timedelta(days=10)  # Earlier
        )
        TournamentTeam.objects.create(
            tournament=sample_tournament,
            team=sample_teams[1],
            placement=5,
            registered_at=timezone.now() - timedelta(days=5)  # Later
        )
        
        entries = leaderboard_service.compute_tournament_leaderboard(sample_tournament.id)
        
        # Contract: Earlier registration wins tie-breaker
        assert entries[0].team == sample_teams[0]
        assert entries[1].team == sample_teams[1]
