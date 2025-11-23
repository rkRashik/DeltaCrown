"""
Seed realistic match data for testing the redesigned Matches tab.
Creates appropriate match types based on game format (Duel vs Battle Royale).

Run: python manage.py shell < seed_realistic_matches.py
"""

from apps.tournaments.models import Tournament, Match
from apps.teams.models import Team
from apps.tournaments.models.bracket import Bracket
from django.utils import timezone
from datetime import timedelta
import random

# Clear existing matches first
print("🗑️  Clearing existing matches...")
Match.objects.all().delete()

# Get or create tournaments for each game type
tournaments_data = []

# Get some teams for seeding
all_teams = list(Team.objects.all()[:32])
if len(all_teams) < 8:
    print("❌ Not enough teams (need at least 8). Please create teams first.")
    exit()

print(f"📊 Found {len(all_teams)} teams to use")

# === DUEL GAMES (1v1/Team vs Team) ===
duel_games = ['valorant', 'cs2', 'dota2', 'mlbb', 'codm', 'fc26', 'efootball']

for game_slug in duel_games:
    # Find or create tournament for this game
    tournament = Tournament.objects.filter(
        game__slug=game_slug,
        status__in=['live', 'published']
    ).first()
    
    if not tournament:
        print(f"⏭️  Skipping {game_slug} - no active tournament found")
        continue
    
    print(f"\n🎮 Creating DUEL matches for: {tournament.name} ({game_slug})")
    
    # Get or create bracket
    bracket = Bracket.objects.filter(tournament=tournament).first()
    if not bracket:
        bracket = Bracket.objects.create(
            tournament=tournament,
            format=Bracket.SINGLE_ELIMINATION,
            seeding_method=Bracket.SLOT_ORDER,
            bracket_structure={'rounds': []}
        )
    
    # Use first 8 teams for this tournament
    teams = all_teams[:8]
    
    # === QUARTER FINALS (Round 3) - COMPLETED ===
    qf_matches = []
    for i in range(4):
        team1 = teams[i*2]
        team2 = teams[i*2+1]
        
        # Randomly determine winner
        scores = [[2, 0], [2, 1], [1, 2], [0, 2]]
        score = random.choice(scores)
        winner_id = team1.id if score[0] > score[1] else team2.id
        loser_id = team2.id if winner_id == team1.id else team1.id
        
        # Format-specific names
        if game_slug in ['valorant', 'cs2']:
            stage_label = f"Playoffs - QF {i+1}"
        elif game_slug in ['fc26', 'efootball']:
            stage_label = f"Round of 8 - Match {i+1}"
        else:
            stage_label = f"Quarter Final {i+1}"
        
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=3,
            match_number=i+1,
            participant1_id=team1.id,
            participant1_name=team1.name,
            participant2_id=team2.id,
            participant2_name=team2.name,
            state=Match.COMPLETED,
            participant1_score=score[0],
            participant2_score=score[1],
            winner_id=winner_id,
            loser_id=loser_id,
            scheduled_time=timezone.now() - timedelta(days=2, hours=random.randint(0, 12)),
            started_at=timezone.now() - timedelta(days=2, hours=random.randint(0, 12)),
            completed_at=timezone.now() - timedelta(days=2, hours=random.randint(0, 11)),
            lobby_info={'stage': stage_label, 'best_of': 3} if game_slug in ['valorant', 'cs2', 'dota2', 'mlbb'] else {'stage': stage_label}
        )
        qf_matches.append(match)
        print(f"  ✅ QF{i+1}: {team1.name} {score[0]}-{score[1]} {team2.name}")
    
    # === SEMI FINALS (Round 2) - COMPLETED ===
    sf_matches = []
    for i in range(2):
        # Get winners from quarter finals
        w1_match = qf_matches[i*2]
        w2_match = qf_matches[i*2+1]
        
        team1 = Team.objects.get(id=w1_match.winner_id)
        team2 = Team.objects.get(id=w2_match.winner_id)
        
        scores = [[2, 0], [2, 1], [1, 2], [0, 2]]
        score = random.choice(scores)
        winner_id = team1.id if score[0] > score[1] else team2.id
        loser_id = team2.id if winner_id == team1.id else team1.id
        
        if game_slug in ['valorant', 'cs2']:
            stage_label = f"Playoffs - Semi Final {i+1}"
        elif game_slug in ['fc26', 'efootball']:
            stage_label = f"Semi Final {i+1}"
        else:
            stage_label = f"Semi Final {i+1}"
        
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=2,
            match_number=i+1,
            participant1_id=team1.id,
            participant1_name=team1.name,
            participant2_id=team2.id,
            participant2_name=team2.name,
            state=Match.COMPLETED,
            participant1_score=score[0],
            participant2_score=score[1],
            winner_id=winner_id,
            loser_id=loser_id,
            scheduled_time=timezone.now() - timedelta(days=1, hours=random.randint(0, 12)),
            started_at=timezone.now() - timedelta(days=1, hours=random.randint(0, 12)),
            completed_at=timezone.now() - timedelta(days=1, hours=random.randint(0, 11)),
            lobby_info={'stage': stage_label, 'best_of': 5} if game_slug in ['valorant', 'cs2', 'dota2'] else {'stage': stage_label}
        )
        sf_matches.append(match)
        print(f"  ✅ SF{i+1}: {team1.name} {score[0]}-{score[1]} {team2.name}")
    
    # === GRAND FINAL (Round 1) - LIVE ===
    finalist1 = Team.objects.get(id=sf_matches[0].winner_id)
    finalist2 = Team.objects.get(id=sf_matches[1].winner_id)
    
    Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=1,
        match_number=1,
        participant1_id=finalist1.id,
        participant1_name=finalist1.name,
        participant2_id=finalist2.id,
        participant2_name=finalist2.name,
        state=Match.LIVE,
        participant1_score=1,
        participant2_score=0,
        scheduled_time=timezone.now() - timedelta(minutes=30),
        started_at=timezone.now() - timedelta(minutes=25),
        stream_url='https://twitch.tv/deltacrown',
        lobby_info={'stage': 'Grand Final', 'best_of': 5, 'map': random.choice(['Haven', 'Bind', 'Ascent']) if game_slug == 'valorant' else 'Stadium'}
    )
    print(f"  🔴 LIVE FINAL: {finalist1.name} 1-0 {finalist2.name}")
    
    # === UPCOMING MATCH - Third Place ===
    loser1 = Team.objects.get(id=sf_matches[0].loser_id)
    loser2 = Team.objects.get(id=sf_matches[1].loser_id)
    
    Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=2,  # Same round as semis
        match_number=3,  # 3rd match in that round
        participant1_id=loser1.id,
        participant1_name=loser1.name,
        participant2_id=loser2.id,
        participant2_name=loser2.name,
        state=Match.SCHEDULED,
        scheduled_time=timezone.now() + timedelta(hours=2, minutes=30),
        lobby_info={'stage': 'Third Place Match', 'best_of': 3}
    )
    print(f"  ⏰ UPCOMING: {loser1.name} vs {loser2.name} (3rd Place)")


# === BATTLE ROYALE GAMES (Multi-team rounds) ===
br_games = ['pubg', 'freefire']

for game_slug in br_games:
    tournament = Tournament.objects.filter(
        game__slug=game_slug,
        status__in=['live', 'published']
    ).first()
    
    if not tournament:
        print(f"⏭️  Skipping {game_slug} - no active tournament found")
        continue
    
    print(f"\n🎮 Creating BATTLE ROYALE matches for: {tournament.name} ({game_slug})")
    
    bracket = Bracket.objects.filter(tournament=tournament).first()
    if not bracket:
        bracket = Bracket.objects.create(
            tournament=tournament,
            format='points_based',
            seeding_method=Bracket.SLOT_ORDER,
            bracket_structure={'rounds': []}
        )
    
    # Use first 16 teams for battle royale
    br_teams = all_teams[:16]
    
    # Map names based on game
    maps = {
        'pubg': ['Erangel', 'Miramar', 'Sanhok', 'Vikendi'],
        'freefire': ['Bermuda', 'Purgatory', 'Kalahari', 'Alpine']
    }
    
    # === Round 1-3: COMPLETED ===
    for round_num in range(1, 4):
        # Create detailed leaderboard
        leaderboard = []
        for rank, team in enumerate(br_teams, 1):
            points = random.randint(15, 35) if rank <= 3 else random.randint(0, 25)
            kills = random.randint(0, 12)
            placement_points = max(0, 20 - (rank * 2))
            total_points = placement_points + kills
            
            leaderboard.append({
                'rank': rank,
                'team_id': team.id,
                'team_name': team.name,
                'placement_points': placement_points,
                'kills': kills,
                'total_points': total_points
            })
        
        # Sort by total points
        leaderboard.sort(key=lambda x: x['total_points'], reverse=True)
        
        # Winner is team with highest points
        winner = leaderboard[0]
        
        match = Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=round_num,
            match_number=1,
            participant1_id=winner['team_id'],  # Winner stored here
            participant1_name=winner['team_name'],
            state=Match.COMPLETED,
            participant1_score=winner['total_points'],
            winner_id=winner['team_id'],
            scheduled_time=timezone.now() - timedelta(days=4-round_num, hours=14),
            started_at=timezone.now() - timedelta(days=4-round_num, hours=14),
            completed_at=timezone.now() - timedelta(days=4-round_num, hours=13, minutes=30),
            lobby_info={
                'map': random.choice(maps[game_slug]),
                'round': round_num,
                'total_rounds': 6,
                'leaderboard': leaderboard[:16]  # Top 16 teams
            }
        )
        print(f"  ✅ Round {round_num}: Winner - {winner['team_name']} ({winner['total_points']} pts) on {match.lobby_info['map']}")
    
    # === Round 4: LIVE ===
    current_leaderboard = []
    for rank, team in enumerate(br_teams, 1):
        kills = random.randint(0, 8)
        placement_points = max(0, 20 - (rank * 2))
        total_points = placement_points + kills
        
        current_leaderboard.append({
            'rank': rank,
            'team_id': team.id,
            'team_name': team.name,
            'placement_points': placement_points,
            'kills': kills,
            'total_points': total_points,
            'alive': rank <= 5  # Top 5 still alive
        })
    
    Match.objects.create(
        tournament=tournament,
        bracket=bracket,
        round_number=4,
        match_number=1,
        state=Match.LIVE,
        scheduled_time=timezone.now() - timedelta(minutes=15),
        started_at=timezone.now() - timedelta(minutes=12),
        stream_url='https://twitch.tv/deltacrown',
        lobby_info={
            'map': random.choice(maps[game_slug]),
            'round': 4,
            'total_rounds': 6,
            'alive_teams': 5,
            'leaderboard': current_leaderboard
        }
    )
    print(f"  🔴 LIVE Round 4: {current_leaderboard[0]['team_name']} leading with {current_leaderboard[0]['total_points']} pts")
    
    # === Round 5-6: UPCOMING ===
    for round_num in range(5, 7):
        Match.objects.create(
            tournament=tournament,
            bracket=bracket,
            round_number=round_num,
            match_number=1,
            state=Match.SCHEDULED,
            scheduled_time=timezone.now() + timedelta(hours=(round_num-4)*2),
            lobby_info={
                'map': random.choice(maps[game_slug]),
                'round': round_num,
                'total_rounds': 6
            }
        )
        print(f"  ⏰ Round {round_num}: Scheduled for {timezone.now() + timedelta(hours=(round_num-4)*2)}")

print("\n✨ Done! Realistic match data seeded successfully.")
print(f"📊 Total matches created: {Match.objects.count()}")
print(f"   - Duel matches: {Match.objects.filter(tournament__game__slug__in=duel_games).count()}")
print(f"   - Battle Royale matches: {Match.objects.filter(tournament__game__slug__in=br_games).count()}")
