# apps/tournaments/games/points.py
"""
Battle Royale point calculators for Free Fire and PUBG Mobile.

Point systems:
- Kills: 1 point per kill
- Placement bonus: Rank-based bonus points

Placement bonus formula (per Planning Blueprint):
- 1st: 12 points
- 2nd: 9 points
- 3rd: 7 points
- 4th: 5 points
- 5th-6th: 4 points
- 7th-8th: 3 points
- 9th-10th: 2 points
- 11th-15th: 1 point
- 16th+: 0 points
"""


# Placement bonus lookup table (1-indexed)
# Per Planning Blueprint: 1st=12pts, 2nd=9pts, 3rd=7pts, 4th=5pts, 5th-6th=4pts...
PLACEMENT_BONUS = {
    1: 12,   # Winner chicken dinner
    2: 9,
    3: 7,
    4: 5,
    5: 4,
    6: 4,
    7: 3,
    8: 3,
    9: 2,
    10: 2,
    11: 1,
    12: 1,
    13: 1,
    14: 1,
    15: 1,
}


def _get_placement_bonus(placement: int) -> int:
    """
    Get placement bonus points.
    
    Args:
        placement: Team placement (1 = winner, 2 = second, etc.)
        
    Returns:
        Bonus points for the placement
    """
    if placement < 1:
        return 0
    return PLACEMENT_BONUS.get(placement, 0)


def calc_ff_points(kills: int, placement: int) -> int:
    """
    Calculate Free Fire match points.
    
    Formula: kills * 1 + placement_bonus
    
    Args:
        kills: Number of kills (0+)
        placement: Team placement rank (1 = winner)
        
    Returns:
        Total points for the match
        
    Examples:
        >>> calc_ff_points(5, 1)
        17  # 5 kills + 12 placement bonus
        >>> calc_ff_points(3, 4)
        8   # 3 kills + 5 placement bonus
        >>> calc_ff_points(10, 20)
        10  # 10 kills + 0 placement bonus (20th place)
    """
    if kills < 0:
        raise ValueError("Kills cannot be negative")
    if placement < 1:
        raise ValueError("Placement must be 1 or higher")
    
    kill_points = kills * 1
    bonus_points = _get_placement_bonus(placement)
    
    return kill_points + bonus_points


def calc_pubgm_points(kills: int, placement: int) -> int:
    """
    Calculate PUBG Mobile match points.
    
    Formula: kills * 1 + placement_bonus
    (Same as Free Fire formula)
    
    Args:
        kills: Number of kills (0+)
        placement: Team placement rank (1 = winner)
        
    Returns:
        Total points for the match
        
    Examples:
        >>> calc_pubgm_points(8, 2)
        17  # 8 kills + 9 placement bonus
        >>> calc_pubgm_points(4, 12)
        5   # 4 kills + 1 placement bonus
        >>> calc_pubgm_points(0, 1)
        12  # 0 kills + 12 placement bonus (pacifist win)
    """
    # Use same formula as Free Fire
    return calc_ff_points(kills, placement)


def get_br_leaderboard(match_results: list[dict]) -> list[dict]:
    """
    Sort Battle Royale results by total points (descending).
    
    Args:
        match_results: List of dicts with keys: team_id, kills, placement
        
    Returns:
        Sorted list with added 'points' field, highest first
        
    Example:
        >>> results = [
        ...     {'team_id': 1, 'kills': 5, 'placement': 3},
        ...     {'team_id': 2, 'kills': 8, 'placement': 2},
        ...     {'team_id': 3, 'kills': 3, 'placement': 1},
        ... ]
        >>> get_br_leaderboard(results)
        [
            {'team_id': 2, 'kills': 8, 'placement': 2, 'points': 14},
            {'team_id': 3, 'kills': 3, 'placement': 1, 'points': 13},
            {'team_id': 1, 'kills': 5, 'placement': 3, 'points': 10},
        ]
    """
    results_with_points = []
    
    for result in match_results:
        points = calc_ff_points(result['kills'], result['placement'])
        results_with_points.append({
            **result,
            'points': points
        })
    
    # Sort by points descending, then by placement ascending (tiebreaker)
    return sorted(
        results_with_points,
        key=lambda x: (-x['points'], x['placement'])
    )
