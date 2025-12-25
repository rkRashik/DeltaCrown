"""
Management command to seed GamePassportSchema records for all supported games.

Usage:
    python manage.py seed_game_passport_schemas
    python manage.py seed_game_passport_schemas --reset  # Delete existing and recreate
"""

from django.core.management.base import BaseCommand
from apps.games.models import Game
from apps.user_profile.models import GamePassportSchema


class Command(BaseCommand):
    help = "Seed GamePassportSchema records for all supported games (GP-1)"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete all existing schemas and recreate them',
        )
    
    def handle(self, *args, **options):
        reset = options['reset']
        
        if reset:
            self.stdout.write(self.style.WARNING("🗑️  Deleting all existing GamePassportSchema records..."))
            deleted_count, _ = GamePassportSchema.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f"✅ Deleted {deleted_count} schemas"))
        
        games = Game.objects.all()
        
        if not games.exists():
            self.stdout.write(self.style.ERROR("❌ No Game records found. Please seed games first."))
            return
        
        self.stdout.write(f"📦 Found {games.count()} games in database")
        
        # Schema definitions per game
        schema_configs = {
            'valorant': {
                'identity_fields': {
                    'riot_name': {
                        'label': 'Riot ID',
                        'required': True,
                        'max_length': 50,
                        'help_text': 'Your Riot ID (e.g., Player123)'
                    },
                    'tagline': {
                        'label': 'Tagline',
                        'required': True,
                        'max_length': 5,
                        'help_text': 'Your Riot tagline without # (e.g., NA1)'
                    }
                },
                'identity_format': '{riot_name}#{tagline}',
                'identity_key_format': '{riot_name_lower}#{tagline_lower}',
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'KR', 'label': 'Korea'},
                    {'value': 'BR', 'label': 'Brazil'},
                    {'value': 'LATAM', 'label': 'Latin America'},
                    {'value': 'AP', 'label': 'Asia-Pacific'},
                ],
                'region_required': True,
                'role_choices': [
                    {'value': 'duelist', 'label': 'Duelist'},
                    {'value': 'controller', 'label': 'Controller'},
                    {'value': 'sentinel', 'label': 'Sentinel'},
                    {'value': 'initiator', 'label': 'Initiator'},
                ],
                'rank_choices': [
                    {'value': 'iron', 'label': 'Iron', 'tier': 1},
                    {'value': 'bronze', 'label': 'Bronze', 'tier': 2},
                    {'value': 'silver', 'label': 'Silver', 'tier': 3},
                    {'value': 'gold', 'label': 'Gold', 'tier': 4},
                    {'value': 'platinum', 'label': 'Platinum', 'tier': 5},
                    {'value': 'diamond', 'label': 'Diamond', 'tier': 6},
                    {'value': 'ascendant', 'label': 'Ascendant', 'tier': 7},
                    {'value': 'immortal', 'label': 'Immortal', 'tier': 8},
                    {'value': 'radiant', 'label': 'Radiant', 'tier': 9},
                ],
                'rank_system': 'valorant_competitive',
                'normalization_rules': {
                    'riot_name': {'strip': True, 'lowercase': True, 'max_length': 50},
                    'tagline': {'strip': True, 'lowercase': True, 'max_length': 5},
                },
            },
            'cs2': {
                'identity_fields': {
                    'steam_id64': {
                        'label': 'Steam ID64',
                        'required': True,
                        'max_length': 20,
                        'help_text': 'Your 17-digit Steam ID64 (e.g., 76561198012345678)'
                    }
                },
                'identity_format': '{steam_id64}',
                'identity_key_format': '{steam_id64}',
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'SA', 'label': 'South America'},
                    {'value': 'ASIA', 'label': 'Asia'},
                    {'value': 'OCE', 'label': 'Oceania'},
                ],
                'region_required': False,
                'role_choices': [
                    {'value': 'entry', 'label': 'Entry Fragger'},
                    {'value': 'awp', 'label': 'AWPer'},
                    {'value': 'support', 'label': 'Support'},
                    {'value': 'lurk', 'label': 'Lurker'},
                    {'value': 'igl', 'label': 'IGL'},
                ],
                'rank_choices': [
                    {'value': 'silver', 'label': 'Silver', 'tier': 1},
                    {'value': 'gold_nova', 'label': 'Gold Nova', 'tier': 2},
                    {'value': 'mg', 'label': 'Master Guardian', 'tier': 3},
                    {'value': 'le', 'label': 'Legendary Eagle', 'tier': 4},
                    {'value': 'lem', 'label': 'Legendary Eagle Master', 'tier': 5},
                    {'value': 'supreme', 'label': 'Supreme', 'tier': 6},
                    {'value': 'global', 'label': 'Global Elite', 'tier': 7},
                ],
                'rank_system': 'cs2_premier',
                'normalization_rules': {
                    'steam_id64': {'strip': True},
                },
            },
            'dota2': {
                'identity_fields': {
                    'steam_id64': {
                        'label': 'Steam ID64',
                        'required': True,
                        'max_length': 20,
                        'help_text': 'Your 17-digit Steam ID64'
                    }
                },
                'identity_format': '{steam_id64}',
                'identity_key_format': '{steam_id64}',
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'CN', 'label': 'China'},
                    {'value': 'SEA', 'label': 'Southeast Asia'},
                    {'value': 'SA', 'label': 'South America'},
                ],
                'region_required': False,
                'role_choices': [
                    {'value': 'carry', 'label': 'Carry'},
                    {'value': 'mid', 'label': 'Mid'},
                    {'value': 'offlane', 'label': 'Offlane'},
                    {'value': 'soft_support', 'label': 'Soft Support'},
                    {'value': 'hard_support', 'label': 'Hard Support'},
                ],
                'rank_choices': [
                    {'value': 'herald', 'label': 'Herald', 'tier': 1},
                    {'value': 'guardian', 'label': 'Guardian', 'tier': 2},
                    {'value': 'crusader', 'label': 'Crusader', 'tier': 3},
                    {'value': 'archon', 'label': 'Archon', 'tier': 4},
                    {'value': 'legend', 'label': 'Legend', 'tier': 5},
                    {'value': 'ancient', 'label': 'Ancient', 'tier': 6},
                    {'value': 'divine', 'label': 'Divine', 'tier': 7},
                    {'value': 'immortal', 'label': 'Immortal', 'tier': 8},
                ],
                'rank_system': 'dota2_mmr',
                'normalization_rules': {
                    'steam_id64': {'strip': True},
                },
            },
            'mlbb': {
                'identity_fields': {
                    'numeric_id': {
                        'label': 'Numeric ID',
                        'required': True,
                        'max_length': 20,
                        'help_text': 'Your MLBB numeric ID (e.g., 123456789)'
                    },
                    'zone_id': {
                        'label': 'Zone ID',
                        'required': True,
                        'max_length': 10,
                        'help_text': 'Your server zone ID (e.g., 1234)'
                    }
                },
                'identity_format': '{numeric_id} ({zone_id})',
                'identity_key_format': '{numeric_id}_{zone_id}',
                'region_choices': [
                    {'value': 'SEA', 'label': 'Southeast Asia'},
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'SA', 'label': 'South America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'MENA', 'label': 'Middle East & North Africa'},
                ],
                'region_required': True,
                'role_choices': [
                    {'value': 'tank', 'label': 'Tank'},
                    {'value': 'fighter', 'label': 'Fighter'},
                    {'value': 'assassin', 'label': 'Assassin'},
                    {'value': 'mage', 'label': 'Mage'},
                    {'value': 'marksman', 'label': 'Marksman'},
                    {'value': 'support', 'label': 'Support'},
                ],
                'rank_choices': [
                    {'value': 'warrior', 'label': 'Warrior', 'tier': 1},
                    {'value': 'elite', 'label': 'Elite', 'tier': 2},
                    {'value': 'master', 'label': 'Master', 'tier': 3},
                    {'value': 'grandmaster', 'label': 'Grandmaster', 'tier': 4},
                    {'value': 'epic', 'label': 'Epic', 'tier': 5},
                    {'value': 'legend', 'label': 'Legend', 'tier': 6},
                    {'value': 'mythic', 'label': 'Mythic', 'tier': 7},
                    {'value': 'mythical_glory', 'label': 'Mythical Glory', 'tier': 8},
                ],
                'rank_system': 'mlbb_ranked',
                'normalization_rules': {
                    'numeric_id': {'strip': True},
                    'zone_id': {'strip': True},
                },
                'platform_specific': True,
            },
            'codm': {
                'identity_fields': {
                    'player_id': {
                        'label': 'Player ID',
                        'required': True,
                        'max_length': 20,
                        'help_text': 'Your COD Mobile Player ID'
                    }
                },
                'identity_format': '{player_id}',
                'identity_key_format': '{player_id_lower}',
                'region_choices': [
                    {'value': 'GLOBAL', 'label': 'Global'},
                    {'value': 'CHINA', 'label': 'China'},
                ],
                'region_required': False,
                'role_choices': [
                    {'value': 'slayer', 'label': 'Slayer'},
                    {'value': 'obj', 'label': 'Objective'},
                    {'value': 'support', 'label': 'Support'},
                    {'value': 'sniper', 'label': 'Sniper'},
                ],
                'rank_choices': [
                    {'value': 'rookie', 'label': 'Rookie', 'tier': 1},
                    {'value': 'veteran', 'label': 'Veteran', 'tier': 2},
                    {'value': 'elite', 'label': 'Elite', 'tier': 3},
                    {'value': 'pro', 'label': 'Pro', 'tier': 4},
                    {'value': 'master', 'label': 'Master', 'tier': 5},
                    {'value': 'grandmaster', 'label': 'Grandmaster', 'tier': 6},
                    {'value': 'legendary', 'label': 'Legendary', 'tier': 7},
                ],
                'rank_system': 'codm_ranked',
                'normalization_rules': {
                    'player_id': {'strip': True, 'lowercase': True},
                },
                'platform_specific': True,
            },
            'pubgm': {
                'identity_fields': {
                    'player_id': {
                        'label': 'Player ID',
                        'required': True,
                        'max_length': 20,
                        'help_text': 'Your PUBG Mobile Player ID'
                    }
                },
                'identity_format': '{player_id}',
                'identity_key_format': '{player_id_lower}',
                'region_choices': [
                    {'value': 'GLOBAL', 'label': 'Global'},
                    {'value': 'KR', 'label': 'Korea'},
                    {'value': 'VN', 'label': 'Vietnam'},
                ],
                'region_required': False,
                'role_choices': [
                    {'value': 'assaulter', 'label': 'Assaulter'},
                    {'value': 'support', 'label': 'Support'},
                    {'value': 'sniper', 'label': 'Sniper'},
                    {'value': 'medic', 'label': 'Medic'},
                ],
                'rank_choices': [
                    {'value': 'bronze', 'label': 'Bronze', 'tier': 1},
                    {'value': 'silver', 'label': 'Silver', 'tier': 2},
                    {'value': 'gold', 'label': 'Gold', 'tier': 3},
                    {'value': 'platinum', 'label': 'Platinum', 'tier': 4},
                    {'value': 'diamond', 'label': 'Diamond', 'tier': 5},
                    {'value': 'crown', 'label': 'Crown', 'tier': 6},
                    {'value': 'ace', 'label': 'Ace', 'tier': 7},
                    {'value': 'conqueror', 'label': 'Conqueror', 'tier': 8},
                ],
                'rank_system': 'pubgm_ranked',
                'normalization_rules': {
                    'player_id': {'strip': True, 'lowercase': True},
                },
                'platform_specific': True,
            },
            'freefire': {
                'identity_fields': {
                    'player_id': {
                        'label': 'Player ID',
                        'required': True,
                        'max_length': 20,
                        'help_text': 'Your Free Fire Player ID'
                    }
                },
                'identity_format': '{player_id}',
                'identity_key_format': '{player_id}',
                'region_choices': [
                    {'value': 'SEA', 'label': 'Southeast Asia'},
                    {'value': 'LATAM', 'label': 'Latin America'},
                    {'value': 'MENA', 'label': 'Middle East & North Africa'},
                    {'value': 'IND', 'label': 'India'},
                ],
                'region_required': False,
                'role_choices': [
                    {'value': 'rusher', 'label': 'Rusher'},
                    {'value': 'support', 'label': 'Support'},
                    {'value': 'sniper', 'label': 'Sniper'},
                    {'value': 'igl', 'label': 'IGL'},
                ],
                'rank_choices': [
                    {'value': 'bronze', 'label': 'Bronze', 'tier': 1},
                    {'value': 'silver', 'label': 'Silver', 'tier': 2},
                    {'value': 'gold', 'label': 'Gold', 'tier': 3},
                    {'value': 'platinum', 'label': 'Platinum', 'tier': 4},
                    {'value': 'diamond', 'label': 'Diamond', 'tier': 5},
                    {'value': 'heroic', 'label': 'Heroic', 'tier': 6},
                    {'value': 'grandmaster', 'label': 'Grandmaster', 'tier': 7},
                ],
                'rank_system': 'freefire_ranked',
                'normalization_rules': {
                    'player_id': {'strip': True},
                },
                'platform_specific': True,
            },
            'r6siege': {
                'identity_fields': {
                    'ubisoft_username': {
                        'label': 'Ubisoft Username',
                        'required': True,
                        'max_length': 50,
                        'help_text': 'Your Ubisoft Connect username'
                    }
                },
                'identity_format': '{ubisoft_username}',
                'identity_key_format': '{ubisoft_username_lower}',
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'ASIA', 'label': 'Asia'},
                    {'value': 'SA', 'label': 'South America'},
                ],
                'region_required': False,
                'role_choices': [
                    {'value': 'entry', 'label': 'Entry Fragger'},
                    {'value': 'support', 'label': 'Support'},
                    {'value': 'anchor', 'label': 'Anchor'},
                    {'value': 'flex', 'label': 'Flex'},
                    {'value': 'roamer', 'label': 'Roamer'},
                ],
                'rank_choices': [
                    {'value': 'copper', 'label': 'Copper', 'tier': 1},
                    {'value': 'bronze', 'label': 'Bronze', 'tier': 2},
                    {'value': 'silver', 'label': 'Silver', 'tier': 3},
                    {'value': 'gold', 'label': 'Gold', 'tier': 4},
                    {'value': 'platinum', 'label': 'Platinum', 'tier': 5},
                    {'value': 'emerald', 'label': 'Emerald', 'tier': 6},
                    {'value': 'diamond', 'label': 'Diamond', 'tier': 7},
                    {'value': 'champion', 'label': 'Champion', 'tier': 8},
                ],
                'rank_system': 'r6siege_ranked',
                'normalization_rules': {
                    'ubisoft_username': {'strip': True, 'lowercase': True},
                },
            },
            'rocketleague': {
                'identity_fields': {
                    'epic_id': {
                        'label': 'Epic Games ID',
                        'required': True,
                        'max_length': 50,
                        'help_text': 'Your Epic Games account ID'
                    }
                },
                'identity_format': '{epic_id}',
                'identity_key_format': '{epic_id_lower}',
                'region_choices': [
                    {'value': 'NA', 'label': 'North America'},
                    {'value': 'EU', 'label': 'Europe'},
                    {'value': 'OCE', 'label': 'Oceania'},
                    {'value': 'SA', 'label': 'South America'},
                    {'value': 'ASIA', 'label': 'Asia'},
                ],
                'region_required': False,
                'role_choices': [
                    {'value': 'striker', 'label': 'Striker'},
                    {'value': 'midfielder', 'label': 'Midfielder'},
                    {'value': 'defender', 'label': 'Defender'},
                    {'value': 'flex', 'label': 'Flex'},
                ],
                'rank_choices': [
                    {'value': 'bronze', 'label': 'Bronze', 'tier': 1},
                    {'value': 'silver', 'label': 'Silver', 'tier': 2},
                    {'value': 'gold', 'label': 'Gold', 'tier': 3},
                    {'value': 'platinum', 'label': 'Platinum', 'tier': 4},
                    {'value': 'diamond', 'label': 'Diamond', 'tier': 5},
                    {'value': 'champion', 'label': 'Champion', 'tier': 6},
                    {'value': 'grand_champion', 'label': 'Grand Champion', 'tier': 7},
                    {'value': 'ssl', 'label': 'Supersonic Legend', 'tier': 8},
                ],
                'rank_system': 'rocketleague_competitive',
                'normalization_rules': {
                    'epic_id': {'strip': True, 'lowercase': True},
                },
            },
            'ea-fc': {
                'identity_fields': {
                    'ea_id': {
                        'label': 'EA Account ID',
                        'required': True,
                        'max_length': 50,
                        'help_text': 'Your EA Account username'
                    }
                },
                'identity_format': '{ea_id}',
                'identity_key_format': '{ea_id_lower}',
                'region_choices': [],
                'region_required': False,
                'role_choices': [
                    {'value': 'st', 'label': 'Striker'},
                    {'value': 'cam', 'label': 'CAM'},
                    {'value': 'cm', 'label': 'CM'},
                    {'value': 'cdm', 'label': 'CDM'},
                    {'value': 'cb', 'label': 'CB'},
                    {'value': 'fb', 'label': 'Fullback'},
                    {'value': 'gk', 'label': 'Goalkeeper'},
                ],
                'rank_choices': [],
                'rank_system': 'eafc_fut_champions',
                'normalization_rules': {
                    'ea_id': {'strip': True, 'lowercase': True},
                },
            },
            'efootball': {
                'identity_fields': {
                    'konami_id': {
                        'label': 'Konami ID',
                        'required': True,
                        'max_length': 50,
                        'help_text': 'Your Konami ID'
                    }
                },
                'identity_format': '{konami_id}',
                'identity_key_format': '{konami_id_lower}',
                'region_choices': [],
                'region_required': False,
                'role_choices': [
                    {'value': 'cf', 'label': 'CF'},
                    {'value': 'amf', 'label': 'AMF'},
                    {'value': 'cmf', 'label': 'CMF'},
                    {'value': 'dmf', 'label': 'DMF'},
                    {'value': 'cb', 'label': 'CB'},
                    {'value': 'sb', 'label': 'Sidebacks'},
                    {'value': 'gk', 'label': 'Goalkeeper'},
                ],
                'rank_choices': [],
                'rank_system': 'efootball_rating',
                'normalization_rules': {
                    'konami_id': {'strip': True, 'lowercase': True},
                },
            },
        }
        
        created_count = 0
        updated_count = 0
        
        for game in games:
            slug = game.slug
            
            if slug not in schema_configs:
                self.stdout.write(self.style.WARNING(f"⚠️  No schema config for '{slug}'. Skipping..."))
                continue
            
            config = schema_configs[slug]
            
            schema, created = GamePassportSchema.objects.update_or_create(
                game=game,
                defaults={
                    'identity_fields': config['identity_fields'],
                    'identity_format': config['identity_format'],
                    'identity_key_format': config['identity_key_format'],
                    'region_choices': config['region_choices'],
                    'region_required': config['region_required'],
                    'role_choices': config['role_choices'],
                    'rank_choices': config['rank_choices'],
                    'rank_system': config['rank_system'],
                    'normalization_rules': config['normalization_rules'],
                    'platform_specific': config.get('platform_specific', False),
                    'requires_verification': False,  # Phase 2+
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"✅ Created schema for '{game.display_name}'"))
            else:
                updated_count += 1
                self.stdout.write(f"🔄 Updated schema for '{game.display_name}'")
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"🎉 Seeding complete!"))
        self.stdout.write(self.style.SUCCESS(f"   Created: {created_count}"))
        self.stdout.write(self.style.SUCCESS(f"   Updated: {updated_count}"))
        self.stdout.write(self.style.SUCCESS(f"   Total: {created_count + updated_count}"))
