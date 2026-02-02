"""Management command to seed GameRankingConfig for 11 supported games."""
from django.core.management.base import BaseCommand
from apps.competition.models import GameRankingConfig


class Command(BaseCommand):
    """Seed GameRankingConfig with default configurations for 11 games."""
    
    help = 'Seed GameRankingConfig with defaults for 11 supported games (LOL, VAL, CS2, DOTA2, RL, APEX, OW2, FORT, COD, R6, PUBG)'
    
    def handle(self, *args, **options):
        """Execute seed command."""
        self.stdout.write('Seeding GameRankingConfig for 11 games...')
        
        # Default configurations (can be customized per game later)
        default_scoring_weights = {
            'tournament_win': 500,
            'verified_match_win': 10,
            'challenge_completion': 50,
            'activity_participation': 5,
        }
        
        default_tier_thresholds = {
            'DIAMOND': 2000,
            'PLATINUM': 1200,
            'GOLD': 600,
            'SILVER': 250,
            'BRONZE': 100,
            'UNRANKED': 0,
        }
        
        default_decay_policy = {
            'enabled': True,
            'inactivity_threshold_days': 30,
            'decay_rate_per_day': 0.01,  # 1% per day
        }
        
        default_verification_rules = {
            'require_opponent_confirmation': True,
            'auto_verify_after_hours': 72,
            'provisional_weight': 0.3,
        }
        
        games = [
            {'game_id': 'LOL', 'game_name': 'League of Legends'},
            {'game_id': 'VAL', 'game_name': 'VALORANT'},
            {'game_id': 'CS2', 'game_name': 'Counter-Strike 2'},
            {'game_id': 'DOTA2', 'game_name': 'Dota 2'},
            {'game_id': 'RL', 'game_name': 'Rocket League'},
            {'game_id': 'APEX', 'game_name': 'Apex Legends'},
            {'game_id': 'OW2', 'game_name': 'Overwatch 2'},
            {'game_id': 'FORT', 'game_name': 'Fortnite'},
            {'game_id': 'COD', 'game_name': 'Call of Duty'},
            {'game_id': 'R6', 'game_name': 'Rainbow Six Siege'},
            {'game_id': 'PUBG', 'game_name': 'PUBG: Battlegrounds'},
        ]
        
        created_count = 0
        updated_count = 0
        
        for game_data in games:
            config, created = GameRankingConfig.objects.update_or_create(
                game_id=game_data['game_id'],
                defaults={
                    'game_name': game_data['game_name'],
                    'scoring_weights': default_scoring_weights,
                    'tier_thresholds': default_tier_thresholds,
                    'decay_policy': default_decay_policy,
                    'verification_rules': default_verification_rules,
                    'is_active': True,
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'[OK] Created: {config.game_name} ({config.game_id})')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'[UPDATE] Updated: {config.game_name} ({config.game_id})')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSeed complete: {created_count} created, {updated_count} updated'
            )
        )
