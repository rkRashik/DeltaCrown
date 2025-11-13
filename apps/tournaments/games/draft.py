# apps/tournaments/games/draft.py
"""
MOBA draft/ban phase validators for Dota 2 and Mobile Legends.

Validates draft structure, hero picks, and ban constraints.
"""

from typing import Optional


def validate_dota2_draft(draft_data: dict) -> tuple[bool, Optional[str]]:
    """
    Validate Dota 2 draft/ban structure.
    
    Rules:
    - Standard: 5 bans per team, 5 picks per team
    - All-Pick: No bans, 5 picks per team
    - Captain's Mode: 7 bans per team, 5 picks per team
    - No duplicate picks across teams
    - No banning already-picked heroes
    
    Args:
        draft_data: Dict with structure:
            {
                "mode": "captains_mode" | "all_pick",
                "team_a_bans": [hero_id1, hero_id2, ...],
                "team_b_bans": [hero_id1, hero_id2, ...],
                "team_a_picks": [hero_id1, hero_id2, ...],
                "team_b_picks": [hero_id1, hero_id2, ...],
                "draft_order": ["ban_a", "ban_b", "pick_a", ...]
            }
    
    Returns:
        (is_valid: bool, error_message: str | None)
        
    Examples:
        >>> validate_dota2_draft({
        ...     "mode": "captains_mode",
        ...     "team_a_bans": [1, 2, 3, 4, 5, 6, 7],
        ...     "team_b_bans": [8, 9, 10, 11, 12, 13, 14],
        ...     "team_a_picks": [15, 16, 17, 18, 19],
        ...     "team_b_picks": [20, 21, 22, 23, 24],
        ...     "draft_order": []
        ... })
        (True, None)
    """
    mode = draft_data.get('mode', 'all_pick')
    
    team_a_bans = draft_data.get('team_a_bans', [])
    team_b_bans = draft_data.get('team_b_bans', [])
    team_a_picks = draft_data.get('team_a_picks', [])
    team_b_picks = draft_data.get('team_b_picks', [])
    
    # Validate ban counts
    if mode == 'captains_mode':
        if len(team_a_bans) != 7:
            return False, "Team A must have exactly 7 bans in Captain's Mode"
        if len(team_b_bans) != 7:
            return False, "Team B must have exactly 7 bans in Captain's Mode"
    elif mode == 'all_pick':
        if team_a_bans or team_b_bans:
            return False, "All-Pick mode does not allow bans"
    else:
        # Standard mode: 5 bans each
        if len(team_a_bans) > 5:
            return False, "Team A cannot have more than 5 bans"
        if len(team_b_bans) > 5:
            return False, "Team B cannot have more than 5 bans"
    
    # Validate pick counts
    if len(team_a_picks) != 5:
        return False, "Team A must have exactly 5 hero picks"
    if len(team_b_picks) != 5:
        return False, "Team B must have exactly 5 hero picks"
    
    # Check for duplicate picks
    all_picks = team_a_picks + team_b_picks
    if len(all_picks) != len(set(all_picks)):
        return False, "Duplicate hero picks detected"
    
    # Check for duplicate bans
    all_bans = team_a_bans + team_b_bans
    if len(all_bans) != len(set(all_bans)):
        return False, "Duplicate hero bans detected"
    
    # Check picks don't overlap with bans
    banned_heroes = set(all_bans)
    picked_heroes = set(all_picks)
    
    if banned_heroes & picked_heroes:
        overlap = banned_heroes & picked_heroes
        return False, f"Heroes cannot be both banned and picked: {overlap}"
    
    return True, None


def validate_mlbb_draft(draft_data: dict) -> tuple[bool, Optional[str]]:
    """
    Validate Mobile Legends: Bang Bang draft/ban structure.
    
    Rules:
    - Draft Mode: 3 bans per team, 5 picks per team
    - Classic Mode: No bans, 5 picks per team
    - No duplicate picks across teams
    - No banning already-picked heroes
    
    Args:
        draft_data: Dict with structure:
            {
                "mode": "draft" | "classic",
                "team_a_bans": [hero_id1, hero_id2, hero_id3],
                "team_b_bans": [hero_id1, hero_id2, hero_id3],
                "team_a_picks": [hero_id1, hero_id2, ...],
                "team_b_picks": [hero_id1, hero_id2, ...],
                "draft_order": ["ban_a", "ban_b", "pick_a", ...]
            }
    
    Returns:
        (is_valid: bool, error_message: str | None)
        
    Examples:
        >>> validate_mlbb_draft({
        ...     "mode": "draft",
        ...     "team_a_bans": [1, 2, 3],
        ...     "team_b_bans": [4, 5, 6],
        ...     "team_a_picks": [10, 11, 12, 13, 14],
        ...     "team_b_picks": [20, 21, 22, 23, 24],
        ...     "draft_order": []
        ... })
        (True, None)
    """
    mode = draft_data.get('mode', 'classic')
    
    team_a_bans = draft_data.get('team_a_bans', [])
    team_b_bans = draft_data.get('team_b_bans', [])
    team_a_picks = draft_data.get('team_a_picks', [])
    team_b_picks = draft_data.get('team_b_picks', [])
    
    # Validate ban counts
    if mode == 'draft':
        if len(team_a_bans) != 3:
            return False, "Team A must have exactly 3 bans in Draft Mode"
        if len(team_b_bans) != 3:
            return False, "Team B must have exactly 3 bans in Draft Mode"
    elif mode == 'classic':
        if team_a_bans or team_b_bans:
            return False, "Classic mode does not allow bans"
    else:
        return False, f"Invalid mode: {mode}"
    
    # Validate pick counts
    if len(team_a_picks) != 5:
        return False, "Team A must have exactly 5 hero picks"
    if len(team_b_picks) != 5:
        return False, "Team B must have exactly 5 hero picks"
    
    # Check for duplicate picks
    all_picks = team_a_picks + team_b_picks
    if len(all_picks) != len(set(all_picks)):
        return False, "Duplicate hero picks detected"
    
    # Check for duplicate bans
    all_bans = team_a_bans + team_b_bans
    if len(all_bans) != len(set(all_bans)):
        return False, "Duplicate hero bans detected"
    
    # Check picks don't overlap with bans
    banned_heroes = set(all_bans)
    picked_heroes = set(all_picks)
    
    if banned_heroes & picked_heroes:
        overlap = banned_heroes & picked_heroes
        return False, f"Heroes cannot be both banned and picked: {overlap}"
    
    return True, None
