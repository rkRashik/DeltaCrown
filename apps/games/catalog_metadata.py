"""Publisher-verified catalog copy, reviewed 2026-10-18.

Keep changing patch/event numbers out of evergreen descriptions. Sources and
release-date semantics are documented in docs/game-catalog-review-2026-10-18.md.
Only presentation metadata belongs here, never roster or gameplay rules.
"""

from datetime import date


CATALOG_METADATA = {
    'valorant': {
        'description': 'A free-to-play 5v5 tactical shooter from Riot Games, combining precise gunplay with agents and their unique abilities. Teams alternate attacking and defending in round-based matches.',
    },
    'cs2': {
        'description': 'A competitive tactical shooter from Valve built on Source 2. Teams coordinate utility, economy and gunplay in round-based attack-and-defence matches.',
    },
    'dota2': {
        'description': 'A free-to-play 5v5 strategy game from Valve. Choose from a fully available hero roster, coordinate abilities and items, and destroy the opposing Ancient.',
    },
    'pubgm': {
        'description': 'A mobile battle royale featuring Classic matches with up to 100 players, solo and squad play, and additional Arena modes. Loot equipment, navigate the shrinking play zone and fight to survive.',
    },
    'mlbb': {
        'description': 'A 5v5 mobile MOBA from MOONTON Games. Build a balanced hero lineup, coordinate across three lanes and destroy the opposing base. Ranked and organised esports play reward teamwork and strategy.',
    },
    'freefire': {
        'description': 'A free-to-play mobile survival shooter from Garena featuring Battle Royale and Clash Squad. Fast matches combine character abilities, resource gathering and squad tactics.',
    },
    'codm': {
        'description': 'A free-to-play mobile shooter featuring classic 5v5 Multiplayer, Battle Royale and DMZ: Recon. Multiplayer modes include Search & Destroy, Domination and Team Deathmatch.',
    },
    'rocketleague': {
        'description': 'A free-to-play vehicle-based football game from Psyonix. Use rocket-powered cars, aerial control and teamwork to score goals in casual and competitive matches.',
    },
    'r6siege': {
        'description': 'A tactical 5v5 attack-and-defence shooter from Ubisoft. Coordinate operators, specialised gadgets and destructible environments to secure objectives.',
    },
    'apex': {
        'name': 'Apex Legends',
        'display_name': 'Apex Legends',
        'description': 'A free-to-play hero battle royale from Respawn Entertainment, combining squad tactics, unique Legend abilities and fast-paced gunplay. Available on PC and supported consoles, including Nintendo Switch 2; original Nintendo Switch support ended on 4 August 2026.',
        'developer': 'Respawn Entertainment',
        'publisher': 'Electronic Arts',
        'official_website': 'https://www.ea.com/games/apex-legends/apex-legends',
        'release_date': date(2019, 2, 4),
        'platforms': ['PC', 'Console'],
    },
    'lol': {
        'name': 'League of Legends',
        'display_name': 'League of Legends',
        'description': 'A free-to-play 5v5 MOBA from Riot Games for Windows and macOS. Select a champion, coordinate roles and objectives on Summoner\'s Rift, and destroy the enemy Nexus. Wild Rift is a separate mobile game.',
        'developer': 'Riot Games',
        'publisher': 'Riot Games',
        'official_website': 'https://www.leagueoflegends.com/',
        'release_date': date(2009, 10, 27),
        'platforms': ['PC'],
    },
    'ow2': {
        'name': 'Overwatch',
        'display_name': 'Overwatch',
        'description': 'A free-to-play team-based hero shooter from Blizzard Entertainment for PC and consoles. Choose tank, damage and support heroes and coordinate around map objectives. Formerly titled Overwatch 2; current branding is Overwatch.',
        'developer': 'Blizzard Entertainment',
        'publisher': 'Blizzard Entertainment',
        'official_website': 'https://overwatch.blizzard.com/',
        # Launch of this live-service title, not the 2016 predecessor or 2026 rename.
        'release_date': date(2022, 10, 4),
        'platforms': ['PC', 'Console'],
    },
}
