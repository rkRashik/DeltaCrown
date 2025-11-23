"""
Complete Tournament Seeding Script (Fixed)
===========================================
Seeds 4 tournaments with complete realistic data:
1. PUBG Mobile Invitational 2025 (Battle Royale)
2. VALORANT Winter Cup Demo (Duel)
3. eFootball Champions Demo (Duel)
4. MLBB Rising Demo (Duel)

Includes:
- Tournament overview, prize pools, rules, streaming links
- User profiles with complete data
- Teams with rosters for each game
- Full registrations (tournament full)
"""

import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.utils import timezone
from apps.accounts.models import User
from apps.user_profile.models import UserProfile
from apps.teams.models import Team, TeamMembership
from apps.tournaments.models import Tournament, Registration
from apps.common.game_registry.registry import get_game

print("\n[*] Starting Complete Tournament Seeding...")
print("=" * 80)

# Helper functions
def get_or_create_user(username, email, first_name, last_name, country='BD'):
    """Create or get user with profile"""
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
        }
    )
    
    # Ensure profile exists
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={
            'country': country,
            'phone_number': f'+880170000{username[-4:]}',
            'bio': f'Professional esports player from {country}',
            'date_of_birth': datetime(1998, 1, 1).date(),
        }
    )
    
    return user

def create_team(name, game_slug, tag, captain, members, description):
    """Create team with roster"""
    game = get_game(game_slug)
    if not game:
        print(f"   ⚠️ Game not found: {game_slug}")
        return None
    
    # Get captain profile
    captain_profile = UserProfile.objects.get(user=captain)
    
    # Create team
    team, created = Team.objects.get_or_create(
        name=name,
        defaults={
            'tag': tag,
            'captain': captain_profile,
            'description': description,
            'game': game_slug,
            'region': 'Bangladesh',
        }
    )
    
    if created:
        # Add captain to roster
        TeamMembership.objects.get_or_create(
            team=team,
            profile=captain_profile,
            defaults={'role': TeamMembership.Role.OWNER, 'status': TeamMembership.Status.ACTIVE, 'is_captain': True}
        )
        
        # Add members to roster
        for member in members:
            member_profile = UserProfile.objects.get(user=member)
            TeamMembership.objects.get_or_create(
                team=team,
                profile=member_profile,
                defaults={'role': TeamMembership.Role.PLAYER, 'status': TeamMembership.Status.ACTIVE}
            )
    
    return team

def register_team(tournament, team, user):
    """Register team for tournament"""
    # For team tournaments, only set team_id, not user
    registration, created = Registration.objects.get_or_create(
        tournament=tournament,
        team_id=team.id,
        defaults={
            'status': 'confirmed',
            'registration_data': {},
        }
    )
    return registration

# Tournament data
TOURNAMENTS = {
    'pubg-mobile-invitational-2025': {
        'description': '''The premier PUBG Mobile tournament of the year featuring the best teams from Bangladesh and South Asia. This invitational brings together 16 elite squads competing for a massive prize pool of 500,000 BDT.

Teams will battle across 12 intense rounds on classic PUBG Mobile maps including Erangel, Miramar, Sanhok, and Vikendi. Each match tests tactical prowess, combat skills, and survival instincts in the ultimate battle royale showdown.

Join us for three days of non-stop action as the region's finest PUBG Mobile talent fights for glory, honor, and championship supremacy. Will your favorite team claim the crown?''',
        'overview': '''## Tournament Format
- **Type**: Battle Royale
- **Teams**: 16 squads
- **Rounds**: 12 matches across 3 days
- **Maps**: Erangel, Miramar, Sanhok, Vikendi

## Points System
- **Winner**: 20 points
- **Top 5**: 15, 12, 10, 8, 6 points
- **Kills**: 1 point each
- **Total**: Placement + Kill points

## Schedule
- **Day 1**: Rounds 1-4 (Erangel, Miramar)
- **Day 2**: Rounds 5-8 (Sanhok, Vikendi)
- **Day 3**: Finals - Rounds 9-12 (All maps)''',
        'prize_pool': Decimal('500000.00'),
        'prize_distribution': {
            '1st': '200000',
            '2nd': '150000',
            '3rd': '80000',
            '4th': '40000',
            '5th-8th': '30000 total'
        },
        'rules': '''**General Rules**
1. All players must have valid PUBG Mobile accounts
2. Teams must check-in 30 minutes before match time
3. No cheating, hacking, or exploiting
4. English or Bengali communication only

**Gameplay Settings**
1. TPP (Third Person Perspective) mode
2. Classic battle royale format
3. Standard loot settings
4. No custom rooms modifications

**Equipment & Technical**
1. Players must use approved devices
2. Minimum 50ms stable connection required

**Disputes & Penalties**
1. Admin decisions are final
2. Disconnections: 5 minute rejoin window
3. Rule violations result in disqualification''',
        'additional_info': '''**Streaming & Broadcast**
- Live on DeltaCrown YouTube, Facebook, and Twitch
- Expert commentary by renowned casters
- Multi-language coverage

**Contact Information**
- Email: tournaments@deltacrown.gg
- Discord: discord.gg/deltacrown
- Phone: +880 1700-123456''',
        'streaming_links': {
            'youtube': 'https://youtube.com/@deltacrown/live',
            'twitch': 'https://twitch.tv/deltacrown',
            'facebook': 'https://facebook.com/gaming/deltacrown'
        }
    },
    'valorant-winter-cup-demo': {
        'description': '''The VALORANT Winter Cup brings together 16 top teams in an intense single-elimination tournament. With 300,000 BDT on the line, this championship showcases the best tactical FPS gameplay in the region.

Teams will compete in best-of-three matches leading to a best-of-five grand final. Every round counts as squads navigate the strategic depth of VALORANT's agent-based gameplay across a curated map pool.

Experience world-class VALORANT action as teams fight through the bracket for championship glory and their share of the substantial prize pool.''',
        'overview': '''## Tournament Format
- **Type**: Single Elimination
- **Teams**: 16 teams
- **Match Format**: BO3 (Best of 3)
- **Grand Final**: BO5 (Best of 5)

## Map Pool
- Haven, Bind, Split, Ascent, Icebox, Breeze, Fracture

## Tournament Stages
1. **Round of 16**: 8 matches (BO3)
2. **Quarter Finals**: 4 matches (BO3)
3. **Semi Finals**: 2 matches (BO3)
4. **Grand Final**: 1 match (BO5)''',
        'prize_pool': Decimal('300000.00'),
        'prize_distribution': {
            '1st': '150000',
            '2nd': '90000',
            '3rd': '40000',
            '4th': '20000'
        },
        'rules': '''**Competition Rules**
1. 5v5 competitive mode
2. Tournament Draft pick/ban system
3. No map repeats in BO3/BO5 until necessary
4. Standard competitive settings

**Technical Requirements**
1. Players must have PC capable of 144+ FPS
2. Ping must be below 50ms
3. All peripherals subject to admin approval

**Match Procedures**
1. Teams have 10 minutes for agent selection
2. Tactical timeout: 1 per half
3. Technical pause: Up to 10 minutes total

**Conduct**
1. Professional behavior required at all times
2. No toxic communication or BM
3. Violations result in penalties or DQ''',
        'additional_info': '''**Broadcast Schedule**
- Matches daily from 6 PM BDT
- English and Bengali commentary
- Watch parties at selected gaming cafes

**Social Media**
- Twitter: @DeltaCrown
- Instagram: @DeltaCrownGG
- Facebook: fb.com/DeltaCrown''',
        'streaming_links': {
            'youtube': 'https://youtube.com/@deltacrown/live',
            'twitch': 'https://twitch.tv/deltacrown',
            'facebook': 'https://facebook.com/gaming/deltacrown'
        }
    },
    'efootball-champions-demo': {
        'description': '''The eFootball Champions tournament features 16 skilled players competing in an intense double-elimination bracket for 150,000 BDT in prizes. This 1v1 championship showcases the highest level of competitive eFootball gameplay.

Players will battle through winners and losers brackets, with every match crucial to championship dreams. The double-elimination format ensures competitive integrity and exciting redemption storylines.

Join us for premium eFootball action as the region's top players compete for the championship title and substantial prize money.''',
        'overview': '''## Tournament Format
- **Type**: Double Elimination
- **Players**: 16 competitors
- **Match Format**: 1v1
- **Grand Final**: BO3 (Best of 3)

## Settings
- myClub teams allowed
- Standard match length: 6 minutes
- Extra time if needed
- Penalties for draws

## Bracket Structure
1. **Winners Bracket**: 8→4→2→1
2. **Losers Bracket**: Full 
3. **Grand Final**: WB vs LB Champion''',
        'prize_pool': Decimal('150000.00'),
        'prize_distribution': {
            '1st': '75000',
            '2nd': '45000',
            '3rd': '20000',
            '4th': '10000'
        },
        'rules': '''**Competition Rules**
1. All myClub teams must be pre-approved
2. No legend-only squads
3. Fair play and sportsmanship required

**Match Settings**
1. Regular time: 6 minutes
2. Extra time: 3 minutes
3. Penalties if still tied
4. No pausing without admin approval

**Disconnection Policy**
1. First DC: Rematch from beginning
2. Second DC: Forfeit
3. Intentional DC: Disqualification

**Player Conduct**
1. No toxic behavior or excessive celebration
2. Respect opponents and officials
3. Follow admin instructions''',
        'additional_info': '''**Event Details**
- **Venue**: DeltaCrown Gaming Arena (Finals only)
- **Dates**: Check schedule for your bracket
- **Tickets**: Available for in-person finals

**Merchandise**
- Tournament jerseys available
- Limited edition controller skins''',
        'streaming_links': {
            'youtube': 'https://youtube.com/@deltacrown/live',
            'twitch': 'https://twitch.tv/deltacrown',
            'facebook': 'https://facebook.com/gaming/deltacrown'
        }
    },
    'mlbb-rising-demo': {
        'description': '''MLBB Rising showcases 12 elite Mobile Legends: Bang Bang teams in a hybrid Swiss+Playoff format competing for 250,000 BDT. This tournament combines strategic Swiss rounds with high-stakes playoff action.

Teams will face off in five intense Swiss rounds before the top 8 advance to single-elimination playoffs. From best-of-three Swiss matches to best-of-seven grand finals, every game matters.

Experience top-tier MOBA action as teams draft, strategize, and battle for championship supremacy in Bangladesh's premier MLBB tournament.''',
        'overview': '''## Tournament Format
- **Type**: Swiss System + Playoffs
- **Teams**: 12 teams
- **Swiss Rounds**: 5 rounds (BO3)
- **Playoffs**: Top 8 teams (Single Elim)

## Swiss Stage
- 5 rounds of BO3 matches
- Match by current record
- Top 8 advance to playoffs

## Playoff Structure
1. **Quarter Finals**: BO5
2. **Semi Finals**: BO5
3. **3rd Place Match**: BO5
4. **Grand Final**: BO7''',
        'prize_pool': Decimal('250000.00'),
        'prize_distribution': {
            '1st': '125000',
            '2nd': '75000',
            '3rd': '35000',
            '4th': '15000'
        },
        'rules': '''**Team & Roster**
1. 5 players + 1 substitute maximum
2. No roster changes after tournament start
3. All players must be verified

**Draft & Hero Rules**
1. Standard competitive draft mode
2. No double hero picks
3. Banned heroes list to be announced
4. Coach allowed during draft phase

**Match Procedures**
1. Teams check in 15 minutes early
2. Draft phase: 10 minutes maximum
3. Pause limit: 5 minutes total per team
4. Rematch rules for critical bugs only

**Player Conduct**
1. Professional behavior required
2. No all-chat except "gg"
3. Respect opponents and officials
4. Violations = penalties/DQ''',
        'additional_info': '''**Production & Broadcast**
- Professional observer and casters
- Replays and highlights
- Player interviews after major matches

**Schedule**
- Swiss Rounds: Week 1-2
- Playoffs: Week 3
- Grand Final: Prime time Saturday

**Fan Engagement**
- Prediction contests with prizes
- Meet & greet with winning team
- Social media giveaways''',
        'streaming_links': {
            'youtube': 'https://youtube.com/@deltacrown/live',
            'twitch': 'https://twitch.tv/deltacrown',
            'facebook': 'https://facebook.com/gaming/deltacrown'
        }
    }
}

# Team names for each game
team_names = {
    'pubg': [
        'Team Liquid', 'FaZe Clan', 'Cloud9', 'G2 Esports', 'TSM', 'NRG',
        'Sentinels', 'OpTic Gaming', 'Bengal Tigers', 'Chittagong Warriors',
        'Dhaka Dragons', 'Sylhet Storm', 'Comilla Champions', 'Khulna Kings',
        'Rajshahi Rangers', 'Mymensingh Mavericks'
    ],
    'valorant': [
        'Bengal Tigers', 'Chittagong Cyclones', 'Demo Apex', 'Demo Blaze',
        'Demo Cobras', 'Demo Dragons', 'Demo Eagles', 'Demo Falcons',
        'Demo Gladiators', 'Demo Hawks', 'Demo Icons', 'Demo Jaguars',
        'Demo Knights', 'Demo Legends', 'Demo Mavericks', 'Demo Ninjas'
    ],
    'efootball': [
        'Bengal Ballers', 'Chittagong FC', 'Demo FC Alpha', 'Demo FC Beta',
        'Demo FC Gamma', 'Demo FC Delta', 'Demo FC Elite', 'Demo FC Force',
        'Demo FC Galaxy', 'Demo FC Heroes', 'Demo FC Impact', 'Demo FC Jets',
        'Demo FC Kings', 'Demo FC Lions', 'Demo FC Masters', 'Demo FC Nova'
    ],
    'mlbb': [
        'Bengal Legends', 'Chittagong Champions', 'Demo Titans', 'Demo Warriors',
        'Demo Vikings', 'Demo Spartans', 'Demo Phoenixes', 'Demo Wolves',
        'Demo Raptors', 'Demo Storm', 'Demo Thunder', 'Demo Blitz'
    ]
}

print("\n[*] Step 1: Creating Users & Teams")
print("=" * 80)

# Create users
users = {}
print("\n[+] Creating users...")
for i in range(1, 51):
    username = f"player_{i}"
    first_name = f"Player"
    last_name = f"{i}"
    email = f"player{i}@deltacrown.gg"
    
    user = get_or_create_user(username, email, first_name, last_name, 'BD')
    users[username] = user

print(f"[+] Created/Updated {len(users)} users")

# Create teams
print("\n[+] Creating teams...")
teams_created = 0
all_teams = {}

for game_slug, names in team_names.items():
    game = get_game(game_slug)
    if not game:
        print(f"   [!] Skipping {game_slug} - game not found")
        continue
    
    user_index = 1
    for i, team_name in enumerate(names, 1):
        # Assign captain and 4 members
        captain_key = f"player_{user_index}"
        if captain_key not in users:
            break
            
        captain = users[captain_key]
        members = []
        for j in range(1, 5):
            member_key = f"player_{user_index + j}"
            if member_key in users:
                members.append(users[member_key])
        
        if len(members) < 4:
            break
        
        # Create team with unique tag based on team number and game
        tag = f"{game_slug.upper()[:2]}{i:02d}"  # e.g., PU01, VA01, EF01
        description = f"Professional {game.display_name} team from Bangladesh"
        
        team = create_team(team_name, game_slug, tag, captain, members, description)
        if team:
            all_teams[f"{game_slug}_{team_name}"] = team
            teams_created += 1
        
        user_index += 5

print(f"[+] Created {teams_created} teams across {len(team_names)} games")

print("\n[*] Step 2: Updating Tournaments")
print("=" * 80)

tournaments_updated = 0
total_registrations = 0

for slug, data in TOURNAMENTS.items():
    tournament = Tournament.objects.filter(slug=slug).first()
    if not tournament:
        print(f"\n⚠️ Tournament not found: {slug}")
        continue
    
    print(f"\n[+] Updating: {tournament.name}")
    
    # Update tournament fields
    tournament.description = data['description']
    tournament.overview = data['overview']
    tournament.prize_pool = data['prize_pool']
    tournament.prize_distribution = data['prize_distribution']
    tournament.rules = data['rules']
    tournament.additional_info = data['additional_info']
    tournament.streaming_links = data['streaming_links']
    tournament.save()
    
    print(f"   [+] Updated tournament details")
    
    # Register teams
    game_slug = tournament.game.slug if tournament.game else None
    if game_slug:
        # Find teams for this game
        relevant_teams = [
            team for key, team in all_teams.items()
            if key.startswith(f"{game_slug}_")
        ]
        
        registered = 0
        max_teams = tournament.max_participants or 16
        
        for team in relevant_teams[:max_teams]:
            registration = register_team(tournament, team, None)
            if registration:
                registered += 1
                total_registrations += 1
        
        print(f"   [+] Registered {registered} teams (FULL)")
    
    tournaments_updated += 1

print(f"\n[+] Tournament seeding complete!")
print("=" * 80)
print(f"\n[*] Summary:")
print(f"   Users created/updated: {len(users)}")
print(f"   Teams created: {teams_created}")
print(f"   Tournaments updated: {tournaments_updated}")
print(f"   Total registrations: {total_registrations}")
print(f"\n[+] All tournaments are now fully populated with realistic data!")
