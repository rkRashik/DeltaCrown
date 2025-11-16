"""
Seed realistic data for DeltaCrown platform.
Creates users, teams, games, and tournaments with proper relationships.
"""
import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.tournaments.models import Game, Tournament, Registration
from apps.teams.models import Team, TeamMembership

User = get_user_model()

def create_users():
    """Create 10 realistic users"""
    print("Creating users...")
    users_data = [
        {'username': 'alex_gaming', 'email': 'alex.rahman@gmail.com', 'first_name': 'Alex', 'last_name': 'Rahman', 'password': 'secure123'},
        {'username': 'shadow_striker', 'email': 'shadow.striker@gmail.com', 'first_name': 'Shadman', 'last_name': 'Hossain', 'password': 'secure123'},
        {'username': 'nova_star', 'email': 'nova.star@yahoo.com', 'first_name': 'Nova', 'last_name': 'Ahmed', 'password': 'secure123'},
        {'username': 'phoenix_rising', 'email': 'phoenix.rising@gmail.com', 'first_name': 'Phoenix', 'last_name': 'Khan', 'password': 'secure123'},
        {'username': 'cyber_wolf', 'email': 'cyber.wolf@hotmail.com', 'first_name': 'Cyber', 'last_name': 'Islam', 'password': 'secure123'},
        {'username': 'thunder_bolt', 'email': 'thunder.bolt@gmail.com', 'first_name': 'Thunder', 'last_name': 'Ali', 'password': 'secure123'},
        {'username': 'viper_strike', 'email': 'viper.strike@gmail.com', 'first_name': 'Viper', 'last_name': 'Karim', 'password': 'secure123'},
        {'username': 'dragon_fury', 'email': 'dragon.fury@yahoo.com', 'first_name': 'Dragon', 'last_name': 'Chowdhury', 'password': 'secure123'},
        {'username': 'storm_rider', 'email': 'storm.rider@gmail.com', 'first_name': 'Storm', 'last_name': 'Siddique', 'password': 'secure123'},
        {'username': 'blaze_master', 'email': 'blaze.master@hotmail.com', 'first_name': 'Blaze', 'last_name': 'Mahmud', 'password': 'secure123'},
    ]
    
    users = []
    for data in users_data:
        user = User.objects.create_user(
            username=data['username'],
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name']
        )
        users.append(user)
        print(f"  ✓ Created user: {user.username}")
    
    return users

def create_games():
    """Create 3 popular games"""
    print("\nCreating games...")
    games_data = [
        {
            'name': 'VALORANT',
            'slug': 'valorant',
            'description': 'VALORANT is a free-to-play first-person tactical hero shooter developed and published by Riot Games. '
                          'Set in the near future, players take on the role of agents with unique abilities.',
            'is_active': True
        },
        {
            'name': 'PUBG Mobile',
            'slug': 'pubg-mobile',
            'description': 'PUBG Mobile is a battle royale game where 100 players fight to be the last one standing. '
                          'Players parachute onto an island, scavenge for weapons and equipment, and battle it out.',
            'is_active': True
        },
        {
            'name': 'Mobile Legends: Bang Bang',
            'slug': 'mlbb',
            'description': 'Mobile Legends: Bang Bang is a mobile multiplayer online battle arena (MOBA) game. '
                          'Two teams of five players compete to destroy the enemy\'s base while defending their own.',
            'is_active': True
        }
    ]
    
    games = []
    for data in games_data:
        game, created = Game.objects.get_or_create(
            slug=data['slug'],
            defaults=data
        )
        games.append(game)
        status = "Created" if created else "Already exists"
        print(f"  ✓ {status}: {game.name}")
    
    return games

def create_teams(users, games):
    """Create 5 competitive teams"""
    print("\nCreating teams...")
    
    # Get UserProfiles for the users
    from apps.user_profile.models import UserProfile
    
    teams_data = [
        {
            'name': 'Dhaka Dragons',
            'tag': 'DD',
            'description': 'Premier VALORANT team from Dhaka, Bangladesh. Known for aggressive playstyle and strategic excellence.',
            'game': games[0].slug,  # VALORANT
            'captain': users[0],
            'members': [users[0], users[1], users[2], users[3], users[4]]  # 5 players
        },
        {
            'name': 'Bengal Tigers',
            'tag': 'BT',
            'description': 'Professional PUBG Mobile squad with multiple championship titles. Dominating the Bangladesh esports scene.',
            'game': games[1].slug,  # PUBG Mobile
            'captain': users[5],
            'members': [users[5], users[6], users[7], users[8]]  # 4 players
        },
        {
            'name': 'Chittagong Cyclones',
            'tag': 'CC',
            'description': 'Elite Mobile Legends team representing Chittagong. Known for their coordinated team fights and map control.',
            'game': games[2].slug,  # MLBB
            'captain': users[9],
            'members': [users[9], users[0], users[1], users[2], users[3]]  # 5 players - reuse users from different teams
        },
        {
            'name': 'Sylhet Storm',
            'tag': 'SS',
            'description': 'Rising VALORANT team from Sylhet with young talented players. Future champions in the making.',
            'game': games[0].slug,  # VALORANT
            'captain': users[4],
            'members': [users[4], users[5], users[6], users[7], users[8]]  # 5 players
        },
        {
            'name': 'Rajshahi Raptors',
            'tag': 'RR',
            'description': 'Aggressive PUBG Mobile team known for hot-dropping and securing early eliminations.',
            'game': games[1].slug,  # PUBG Mobile
            'captain': users[9],
            'members': [users[9], users[0], users[1], users[2]]  # 4 players
        }
    ]
    
    teams = []
    for data in teams_data:
        # Get or create UserProfile for captain
        captain_profile, _ = UserProfile.objects.get_or_create(user=data['captain'])
        
        team = Team.objects.create(
            name=data['name'],
            tag=data['tag'],
            description=data['description'],
            game=data['game'],
            captain=captain_profile,
            is_verified=True
        )
        
        # Add team members
        for idx, member in enumerate(data['members']):
            is_captain = (member == data['captain'])
            member_profile, _ = UserProfile.objects.get_or_create(user=member)
            TeamMembership.objects.get_or_create(
                team=team,
                profile=member_profile,
                defaults={
                    'role': TeamMembership.Role.CAPTAIN if is_captain else TeamMembership.Role.PLAYER,
                    'is_captain': is_captain,
                    'status': TeamMembership.Status.ACTIVE,
                    'joined_at': timezone.now() - timedelta(days=30)
                }
            )
        
        teams.append(team)
        print(f"  ✓ Created team: {team.name} ({team.tag}) - {data['game']}")
        print(f"    Members: {', '.join([m.username for m in data['members']])}")
    
    return teams

def create_tournaments(users, games, teams):
    """Create 3 exciting tournaments"""
    print("\nCreating tournaments...")
    
    now = timezone.now()
    
    tournaments_data = [
        {
            'name': 'DeltaCrown VALORANT Championship 2025',
            'slug': 'deltacrown-valorant-championship-2025',
            'description': 'The biggest VALORANT tournament in Bangladesh! Compete for a prize pool of 500,000 BDT. '
                          'Single elimination format with 16 teams battling for supremacy.',
            'game': games[0],  # VALORANT
            'organizer': users[0],
            'format': Tournament.SINGLE_ELIM,
            'participation_type': Tournament.TEAM,
            'status': Tournament.REGISTRATION_OPEN,
            'min_participants': 8,
            'max_participants': 16,
            'registration_start': now - timedelta(days=5),
            'registration_end': now + timedelta(days=10),
            'tournament_start': now + timedelta(days=15),
            'prize_pool': 500000.00,
            'prize_currency': 'BDT',
            'has_entry_fee': True,
            'entry_fee_amount': 5000.00,
            'entry_fee_currency': 'BDT',
            'is_official': True,
            'registered_teams': [teams[0], teams[3]]  # Dhaka Dragons, Sylhet Storm
        },
        {
            'name': 'PUBG Mobile Invitational 2025',
            'slug': 'pubg-mobile-invitational-2025',
            'description': 'Elite PUBG Mobile tournament featuring the best squads from Bangladesh. '
                          '16 teams, 6 matches, winner takes all! Prize pool: 300,000 BDT.',
            'game': games[1],  # PUBG Mobile
            'organizer': users[5],
            'format': Tournament.ROUND_ROBIN,
            'participation_type': Tournament.TEAM,
            'status': Tournament.REGISTRATION_OPEN,
            'min_participants': 8,
            'max_participants': 16,
            'registration_start': now - timedelta(days=3),
            'registration_end': now + timedelta(days=7),
            'tournament_start': now + timedelta(days=12),
            'prize_pool': 300000.00,
            'prize_currency': 'BDT',
            'has_entry_fee': True,
            'entry_fee_amount': 3000.00,
            'entry_fee_currency': 'BDT',
            'is_official': True,
            'registered_teams': [teams[1], teams[4]]  # Bengal Tigers, Rajshahi Raptors
        },
        {
            'name': 'Mobile Legends Spring Cup 2025',
            'slug': 'mlbb-spring-cup-2025',
            'description': 'Seasonal Mobile Legends tournament celebrating the spring season. '
                          'Double elimination bracket with 8 teams. Prize: 200,000 BDT + exclusive in-game rewards.',
            'game': games[2],  # MLBB
            'organizer': users[9],
            'format': Tournament.DOUBLE_ELIM,
            'participation_type': Tournament.TEAM,
            'status': Tournament.PUBLISHED,
            'min_participants': 4,
            'max_participants': 8,
            'registration_start': now + timedelta(days=2),
            'registration_end': now + timedelta(days=14),
            'tournament_start': now + timedelta(days=20),
            'prize_pool': 200000.00,
            'prize_currency': 'BDT',
            'has_entry_fee': True,
            'entry_fee_amount': 2000.00,
            'entry_fee_currency': 'BDT',
            'is_official': False,
            'registered_teams': [teams[2]]  # Chittagong Cyclones
        }
    ]
    
    tournaments = []
    for data in tournaments_data:
        registered_teams = data.pop('registered_teams')
        
        tournament = Tournament.objects.create(**data)
        
        # Register teams - For team registrations, only set team_id (not user)
        # The constraint is: user XOR team_id (exactly one must be set)
        for team in registered_teams:
            Registration.objects.create(
                tournament=tournament,
                user=None,  # For team registration, user should be None
                team_id=team.id,
                status=Registration.CONFIRMED
            )
        
        tournaments.append(tournament)
        print(f"  ✓ Created tournament: {tournament.name}")
        print(f"    Game: {tournament.game.name} | Format: {tournament.get_format_display()}")
        print(f"    Prize Pool: {tournament.prize_pool} {tournament.prize_currency}")
        print(f"    Registered: {len(registered_teams)} teams")
    
    return tournaments

def main():
    """Main seeding function"""
    print("=" * 80)
    print("DeltaCrown Platform - Realistic Data Seeding")
    print("=" * 80)
    
    # Check if data already exists
    if User.objects.filter(username='alex_gaming').exists():
        print("\n⚠️  Data already exists in database!")
        response = input("Do you want to delete existing data and reseed? (yes/no): ")
        if response.lower() != 'yes':
            print("Seeding cancelled.")
            return
        
        print("\nClearing existing data...")
        # Delete in proper order to avoid FK constraints
        from apps.tournaments.models import Registration, Tournament
        from apps.teams.models import TeamMembership
        
        Registration.objects.all().delete()
        print("  ✓ Cleared registrations")
        Tournament.objects.all().delete()
        print("  ✓ Cleared tournaments")
        TeamMembership.objects.all().delete()
        print("  ✓ Cleared team memberships")
        Team.objects.all().delete()
        print("  ✓ Cleared teams")
        Game.objects.all().delete()
        print("  ✓ Cleared games")
        User.objects.filter(username__in=[
            'alex_gaming', 'shadow_striker', 'nova_star', 'phoenix_rising',
            'cyber_wolf', 'thunder_bolt', 'viper_strike', 'dragon_fury',
            'storm_rider', 'blaze_master'
        ]).delete()
        print("  ✓ Cleared users")
    
    # Create data
    users = create_users()
    games = create_games()
    teams = create_teams(users, games)
    tournaments = create_tournaments(users, games, teams)
    
    print("\n" + "=" * 80)
    print("✅ Seeding Complete!")
    print("=" * 80)
    print(f"\nSummary:")
    print(f"  • Users: {len(users)}")
    print(f"  • Games: {len(games)}")
    print(f"  • Teams: {len(teams)}")
    print(f"  • Tournaments: {len(tournaments)}")
    print("\nYou can now login with any user:")
    print("  Username: alex_gaming (or any other username)")
    print("  Password: secure123")
    print("\n")

if __name__ == '__main__':
    main()
