"""
Generate realistic match data for all tournaments.

This script:
1. Creates group stage matches for group_knockout tournaments (VALORANT, MLBB, FC26)
2. Creates knockout bracket matches
3. Generates realistic scores based on game type
4. Creates partial results for LIVE tournaments
5. Calculates standings and determines winners

Run after seed_realistic_production_data.py
"""

import os
import sys
import django
import random
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.utils import timezone
from apps.tournaments.models import Tournament, Match, Registration
from apps.accounts.models import User
from apps.teams.models import Team

def get_random_score(game, is_bo3=False, is_bo5=False):
    """Generate realistic score based on game type"""
    
    # Handle Game object or string
    game_slug = game.slug if hasattr(game, 'slug') else game
    
    if game_slug in ['valorant', 'cs2', 'mlbb']:
        # Map-based games (Bo3 or Bo5)
        if is_bo5:
            # Bo5: Winner gets 3, loser gets 0-2
            winner_score = 3
            loser_score = random.choices([0, 1, 2], weights=[20, 40, 40])[0]
        elif is_bo3:
            # Bo3: Winner gets 2, loser gets 0-1
            winner_score = 2
            loser_score = random.choices([0, 1], weights=[40, 60])[0]
        else:
            # Single map
            winner_score = 1
            loser_score = 0
        return winner_score, loser_score
    
    elif game_slug in ['fc26', 'efootball']:
        # Football games: Goal scores
        winner_goals = random.choices([1, 2, 3, 4, 5], weights=[15, 30, 30, 20, 5])[0]
        goal_diff = random.choices([1, 2, 3], weights=[60, 30, 10])[0]
        loser_goals = max(0, winner_goals - goal_diff)
        return winner_goals, loser_goals
    
    elif game_slug == 'pubg':
        # Battle royale: Placement + kill points
        # Winner team: 15-25 points, loser: 5-20 points
        winner_points = random.randint(15, 25)
        loser_points = random.randint(5, min(20, winner_points - 3))
        return winner_points, loser_points
    
    elif game_slug == 'dota2':
        # MOBA: Winner 1, Loser 0 (map score)
        return 1, 0
    
    elif game_slug in ['freefire', 'codm']:
        # Battle royale style: Points
        winner_points = random.randint(18, 30)
        loser_points = random.randint(8, min(25, winner_points - 4))
        return winner_points, loser_points
    
    else:
        # Default: 1-0
        return 1, 0


def create_group_stage_matches(tournament, teams):
    """Create round-robin group stage matches"""
    print(f"  Creating group stage matches for {tournament.name}...")
    
    # Divide teams into 4 groups
    num_groups = 4
    teams_per_group = len(teams) // num_groups
    groups = [teams[i:i + teams_per_group] for i in range(0, len(teams), teams_per_group)]
    
    match_counter = 1
    matches_created = 0
    
    for group_idx, group_teams in enumerate(groups, 1):
        print(f"    Group {group_idx}: {len(group_teams)} teams")
        
        # Round-robin within group
        for i, team1 in enumerate(group_teams):
            for team2 in group_teams[i+1:]:
                # Determine winner randomly (70% to higher-indexed team for variety)
                if random.random() < 0.7:
                    winner_team, loser_team = team1, team2
                else:
                    winner_team, loser_team = team2, team1
                
                # Get scores based on game
                winner_score, loser_score = get_random_score(
                    tournament.game,
                    is_bo3=True  # Group stage typically Bo3
                )
                
                # Create match
                match = Match.objects.create(
                    tournament=tournament,
                    bracket=None,  # Group stage has no bracket
                    round_number=1,  # All group matches are "round 1"
                    match_number=match_counter,
                    participant1_id=team1.id,
                    participant1_name=team1.name,
                    participant2_id=team2.id,
                    participant2_name=team2.name,
                    participant1_score=winner_score if winner_team == team1 else loser_score,
                    participant2_score=winner_score if winner_team == team2 else loser_score,
                    winner_id=winner_team.id,
                    loser_id=loser_team.id,
                    state=Match.COMPLETED,
                    scheduled_time=timezone.now() - timedelta(days=random.randint(7, 30)),
                    started_at=timezone.now() - timedelta(days=random.randint(5, 25)),
                    completed_at=timezone.now() - timedelta(days=random.randint(3, 20)),
                )
                match_counter += 1
                matches_created += 1
    
    print(f"    [OK] Created {matches_created} group stage matches")
    return match_counter


def create_knockout_matches(tournament, teams, start_match_num=1, is_bo5_finals=True):
    """Create single elimination knockout bracket"""
    print(f"  Creating knockout matches for {tournament.name}...")
    
    # For knockout, take top 8 teams (simulating advancement from groups)
    knockout_teams = teams[:8]
    
    matches_created = 0
    match_counter = start_match_num
    
    # Quarter Finals (8 teams → 4 teams)
    print(f"    Quarter Finals...")
    qf_winners = []
    for i in range(0, 8, 2):
        team1, team2 = knockout_teams[i], knockout_teams[i+1]
        
        # Determine winner (60% to higher seed)
        if random.random() < 0.6:
            winner_team, loser_team = team1, team2
        else:
            winner_team, loser_team = team2, team1
        
        winner_score, loser_score = get_random_score(tournament.game, is_bo3=True)
        
        match = Match.objects.create(
            tournament=tournament,
            bracket=None,
            round_number=2,  # Round 2 (after groups)
            match_number=match_counter,
            participant1_id=team1.id,
            participant1_name=team1.name,
            participant2_id=team2.id,
            participant2_name=team2.name,
            participant1_score=winner_score if winner_team == team1 else loser_score,
            participant2_score=winner_score if winner_team == team2 else loser_score,
            winner_id=winner_team.id,
            loser_id=loser_team.id,
            state=Match.COMPLETED,
            scheduled_time=timezone.now() - timedelta(days=random.randint(5, 15)),
            started_at=timezone.now() - timedelta(days=random.randint(4, 12)),
            completed_at=timezone.now() - timedelta(days=random.randint(2, 10)),
        )
        qf_winners.append(winner_team)
        match_counter += 1
        matches_created += 1
    
    # Semi Finals (4 teams → 2 teams)
    print(f"    Semi Finals...")
    sf_winners = []
    for i in range(0, 4, 2):
        team1, team2 = qf_winners[i], qf_winners[i+1]
        
        if random.random() < 0.55:
            winner_team, loser_team = team1, team2
        else:
            winner_team, loser_team = team2, team1
        
        winner_score, loser_score = get_random_score(tournament.game, is_bo3=True)
        
        match = Match.objects.create(
            tournament=tournament,
            bracket=None,
            round_number=3,
            match_number=match_counter,
            participant1_id=team1.id,
            participant1_name=team1.name,
            participant2_id=team2.id,
            participant2_name=team2.name,
            participant1_score=winner_score if winner_team == team1 else loser_score,
            participant2_score=winner_score if winner_team == team2 else loser_score,
            winner_id=winner_team.id,
            loser_id=loser_team.id,
            state=Match.COMPLETED,
            scheduled_time=timezone.now() - timedelta(days=random.randint(3, 8)),
            started_at=timezone.now() - timedelta(days=random.randint(2, 6)),
            completed_at=timezone.now() - timedelta(days=random.randint(1, 4)),
        )
        sf_winners.append(winner_team)
        match_counter += 1
        matches_created += 1
    
    # Grand Finals (2 teams → 1 champion)
    print(f"    Grand Finals...")
    team1, team2 = sf_winners[0], sf_winners[1]
    
    # Finals: Higher seed has slight advantage
    if random.random() < 0.52:
        winner_team, loser_team = team1, team2
    else:
        winner_team, loser_team = team2, team1
    
    winner_score, loser_score = get_random_score(tournament.game, is_bo5=is_bo5_finals)
    
    match = Match.objects.create(
        tournament=tournament,
        bracket=None,
        round_number=4,  # Finals
        match_number=match_counter,
        participant1_id=team1.id,
        participant1_name=team1.name,
        participant2_id=team2.id,
        participant2_name=team2.name,
        participant1_score=winner_score if winner_team == team1 else loser_score,
        participant2_score=winner_score if winner_team == team2 else loser_score,
        winner_id=winner_team.id,
        loser_id=loser_team.id,
        state=Match.COMPLETED,
        scheduled_time=timezone.now() - timedelta(days=2),
        started_at=timezone.now() - timedelta(days=1),
        completed_at=timezone.now() - timedelta(hours=12),
    )
    matches_created += 1
    
    print(f"    [OK] Created {matches_created} knockout matches")
    print(f"    [CHAMPION] {winner_team.name}")
    
    return match_counter


def create_battle_royale_matches(tournament, teams):
    """Create battle royale tournament matches (multiple rounds, points-based)"""
    print(f"  Creating battle royale matches for {tournament.name}...")
    
    num_rounds = 12  # 12 match rounds
    matches_created = 0
    
    # Track cumulative points for each team
    team_points = {team.id: 0 for team in teams}
    
    for round_num in range(1, num_rounds + 1):
        # Each round, shuffle teams and assign placements + kills
        round_teams = list(teams)
        random.shuffle(round_teams)
        
        # Placement points: 20 for 1st, 15 for 2nd, 12 for 3rd, etc.
        placement_points = [20, 15, 12, 10, 8, 6, 5, 4, 3, 2]
        
        for idx, team in enumerate(round_teams):
            placement = idx + 1
            base_points = placement_points[idx] if idx < len(placement_points) else 1
            kill_points = random.randint(0, 10)  # 0-10 kills
            total_points = base_points + kill_points
            
            team_points[team.id] += total_points
        
        # Create a match record for this round (use 1st vs 2nd as representative)
        top_team = round_teams[0]
        second_team = round_teams[1]
        
        match = Match.objects.create(
            tournament=tournament,
            bracket=None,
            round_number=round_num,
            match_number=round_num,
            participant1_id=top_team.id,
            participant1_name=top_team.name,
            participant2_id=second_team.id,
            participant2_name=second_team.name,
            participant1_score=placement_points[0] + random.randint(3, 10),
            participant2_score=placement_points[1] + random.randint(2, 8),
            winner_id=top_team.id,
            loser_id=second_team.id,
            state=Match.COMPLETED,
            scheduled_time=timezone.now() - timedelta(days=30-round_num),
            started_at=timezone.now() - timedelta(days=29-round_num),
            completed_at=timezone.now() - timedelta(days=28-round_num),
            lobby_info={
                'round': round_num,
                'total_rounds': num_rounds,
                'map': f'Erangel' if round_num % 3 == 0 else 'Miramar' if round_num % 3 == 1 else 'Sanhok'
            }
        )
        matches_created += 1
    
    # Determine champion (highest cumulative points)
    sorted_teams = sorted(team_points.items(), key=lambda x: x[1], reverse=True)
    champion_id = sorted_teams[0][0]
    champion = next(t for t in teams if t.id == champion_id)
    
    print(f"    [OK] Created {matches_created} battle royale rounds")
    print(f"    [CHAMPION] {champion.name} ({team_points[champion_id]} points)")
    
    return matches_created


def create_single_elim_tournament(tournament, teams):
    """Create simple single elimination (no groups)"""
    print(f"  Creating single elimination for {tournament.name}...")
    
    # 8 team bracket
    bracket_teams = teams[:8]
    matches_created = 0
    match_counter = 1
    
    # Round 1: Quarter Finals
    print(f"    Quarter Finals...")
    qf_winners = []
    for i in range(0, 8, 2):
        team1, team2 = bracket_teams[i], bracket_teams[i+1]
        
        if random.random() < 0.6:
            winner_team, loser_team = team1, team2
        else:
            winner_team, loser_team = team2, team1
        
        winner_score, loser_score = get_random_score(tournament.game)
        
        match = Match.objects.create(
            tournament=tournament,
            bracket=None,
            round_number=1,
            match_number=match_counter,
            participant1_id=team1.id,
            participant1_name=team1.name,
            participant2_id=team2.id,
            participant2_name=team2.name,
            participant1_score=winner_score if winner_team == team1 else loser_score,
            participant2_score=winner_score if winner_team == team2 else loser_score,
            winner_id=winner_team.id,
            loser_id=loser_team.id,
            state=Match.COMPLETED,
            scheduled_time=timezone.now() - timedelta(days=random.randint(10, 20)),
            started_at=timezone.now() - timedelta(days=random.randint(8, 18)),
            completed_at=timezone.now() - timedelta(days=random.randint(6, 16)),
        )
        qf_winners.append(winner_team)
        match_counter += 1
        matches_created += 1
    
    # Round 2: Semi Finals
    print(f"    Semi Finals...")
    sf_winners = []
    for i in range(0, 4, 2):
        team1, team2 = qf_winners[i], qf_winners[i+1]
        
        if random.random() < 0.55:
            winner_team, loser_team = team1, team2
        else:
            winner_team, loser_team = team2, team1
        
        winner_score, loser_score = get_random_score(tournament.game)
        
        match = Match.objects.create(
            tournament=tournament,
            bracket=None,
            round_number=2,
            match_number=match_counter,
            participant1_id=team1.id,
            participant1_name=team1.name,
            participant2_id=team2.id,
            participant2_name=team2.name,
            participant1_score=winner_score if winner_team == team1 else loser_score,
            participant2_score=winner_score if winner_team == team2 else loser_score,
            winner_id=winner_team.id,
            loser_id=loser_team.id,
            state=Match.COMPLETED,
            scheduled_time=timezone.now() - timedelta(days=random.randint(5, 10)),
            started_at=timezone.now() - timedelta(days=random.randint(4, 8)),
            completed_at=timezone.now() - timedelta(days=random.randint(2, 6)),
        )
        sf_winners.append(winner_team)
        match_counter += 1
        matches_created += 1
    
    # Round 3: Finals
    print(f"    Grand Finals...")
    team1, team2 = sf_winners[0], sf_winners[1]
    
    if random.random() < 0.52:
        winner_team, loser_team = team1, team2
    else:
        winner_team, loser_team = team2, team1
    
    winner_score, loser_score = get_random_score(tournament.game)
    
    match = Match.objects.create(
        tournament=tournament,
        bracket=None,
        round_number=3,
        match_number=match_counter,
        participant1_id=team1.id,
        participant1_name=team1.name,
        participant2_id=team2.id,
        participant2_name=team2.name,
        participant1_score=winner_score if winner_team == team1 else loser_score,
        participant2_score=winner_score if winner_team == team2 else loser_score,
        winner_id=winner_team.id,
        loser_id=loser_team.id,
        state=Match.COMPLETED,
        scheduled_time=timezone.now() - timedelta(days=2),
        started_at=timezone.now() - timedelta(days=1),
        completed_at=timezone.now() - timedelta(hours=12),
    )
    matches_created += 1
    
    print(f"    [OK] Created {matches_created} matches")
    print(f"    [CHAMPION] {winner_team.name}")


def create_partial_matches_for_live(tournament, teams, rounds_completed=2):
    """Create partial matches for LIVE tournaments"""
    print(f"  Creating partial matches for LIVE tournament: {tournament.name}...")
    
    matches_created = 0
    match_counter = 1
    
    # Create completed rounds
    completed_teams = list(teams)
    random.shuffle(completed_teams)
    
    for round_num in range(1, rounds_completed + 1):
        print(f"    Round {round_num} (COMPLETED)...")
        for i in range(0, len(completed_teams), 2):
            if i + 1 >= len(completed_teams):
                break
            
            team1, team2 = completed_teams[i], completed_teams[i+1]
            
            if random.random() < 0.55:
                winner_team, loser_team = team1, team2
            else:
                winner_team, loser_team = team2, team1
            
            winner_score, loser_score = get_random_score(tournament.game, is_bo3=True)
            
            match = Match.objects.create(
                tournament=tournament,
                bracket=None,
                round_number=round_num,
                match_number=match_counter,
                participant1_id=team1.id,
                participant1_name=team1.name,
                participant2_id=team2.id,
                participant2_name=team2.name,
                participant1_score=winner_score if winner_team == team1 else loser_score,
                participant2_score=winner_score if winner_team == team2 else loser_score,
                winner_id=winner_team.id,
                loser_id=loser_team.id,
                state=Match.COMPLETED,
                scheduled_time=timezone.now() - timedelta(days=3 + round_num),
                started_at=timezone.now() - timedelta(days=2 + round_num),
                completed_at=timezone.now() - timedelta(days=1 + round_num),
            )
            match_counter += 1
            matches_created += 1
    
    # Create scheduled (upcoming) rounds
    scheduled_rounds = 2
    for round_num in range(rounds_completed + 1, rounds_completed + scheduled_rounds + 1):
        print(f"    Round {round_num} (SCHEDULED)...")
        random.shuffle(completed_teams)
        for i in range(0, min(8, len(completed_teams)), 2):
            team1, team2 = completed_teams[i], completed_teams[i+1]
            
            match = Match.objects.create(
                tournament=tournament,
                bracket=None,
                round_number=round_num,
                match_number=match_counter,
                participant1_id=team1.id,
                participant1_name=team1.name,
                participant2_id=team2.id,
                participant2_name=team2.name,
                participant1_score=0,
                participant2_score=0,
                winner_id=None,
                loser_id=None,
                state=Match.SCHEDULED,
                scheduled_time=timezone.now() + timedelta(days=round_num - rounds_completed),
            )
            match_counter += 1
            matches_created += 1
    
    print(f"    [OK] Created {matches_created} matches ({rounds_completed} completed rounds, {scheduled_rounds} scheduled rounds)")


def main():
    """Generate matches for all tournaments"""
    print("\n" + "="*80)
    print("GENERATING TOURNAMENT MATCHES")
    print("="*80 + "\n")
    
    # Get all tournaments
    tournaments = Tournament.objects.all().order_by('name')
    
    for tournament in tournaments:
        print(f"\n{tournament.name} ({tournament.game.slug.upper()}) - Format: {tournament.format}")
        print("-" * 80)
        
        # Get registered teams
        registrations = Registration.objects.filter(
            tournament=tournament,
            status='confirmed'
        )
        
        # Fetch teams by team_id
        team_ids = [reg.team_id for reg in registrations if reg.team_id]
        teams = list(Team.objects.filter(id__in=team_ids))
        
        if not teams:
            print(f"  [WARN] No registered teams found. Skipping...")
            continue
        
        print(f"  Registered teams: {len(teams)}")
        
        # Generate matches based on tournament format and status
        try:
            if tournament.status == Tournament.COMPLETED:
                if tournament.format == 'group_knockout':
                    # Group stage + knockout (VALORANT, MLBB, FC26)
                    match_num = create_group_stage_matches(tournament, teams)
                    create_knockout_matches(tournament, teams, start_match_num=match_num, is_bo5_finals=True)
                
                elif tournament.format == 'double_elim':
                    # Double elimination (CS2) - Simplified as single elim with more rounds
                    create_knockout_matches(tournament, teams, start_match_num=1, is_bo5_finals=True)
                
                elif tournament.format == 'battle_royale':
                    # Battle royale (PUBG)
                    create_battle_royale_matches(tournament, teams)
                
                elif tournament.format == 'single_elim':
                    # Single elimination (eFootball)
                    create_single_elim_tournament(tournament, teams)
                
                else:
                    print(f"  [WARN] Unknown format: {tournament.format}")
            
            elif tournament.status == Tournament.LIVE:
                # Create partial matches (some completed, some scheduled)
                create_partial_matches_for_live(tournament, teams, rounds_completed=2)
            
            else:
                print(f"  [INFO] Tournament status is {tournament.status} - no matches generated")
        
        except Exception as e:
            print(f"  [ERROR] Error generating matches: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print("MATCH GENERATION COMPLETE")
    print("="*80)
    
    # Summary
    total_matches = Match.objects.count()
    completed_matches = Match.objects.filter(state=Match.COMPLETED).count()
    scheduled_matches = Match.objects.filter(state=Match.SCHEDULED).count()
    
    print(f"\nTotal matches created: {total_matches}")
    print(f"  - Completed: {completed_matches}")
    print(f"  - Scheduled: {scheduled_matches}")
    print("\n[SUCCESS] All tournament matches generated successfully!\n")


if __name__ == '__main__':
    main()
