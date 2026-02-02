"""
DeltaCrown Competition App (Phase 3A-B)

Multi-game competitive ranking, match reporting, and leaderboard system.

Domain Boundaries:
- Match reporting and verification
- Per-game and global team rankings
- Ranking computation and snapshots
- Leaderboard generation

Does NOT handle:
- Team lifecycle management (see: apps.organizations)
- Tournament data storage (see: apps.tournaments - consumed via adapters)
- User profiles (see: apps.user_profile)
"""

default_app_config = 'apps.competition.apps.CompetitionConfig'
