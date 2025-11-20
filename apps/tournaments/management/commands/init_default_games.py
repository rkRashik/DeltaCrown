"""
Django Management Command: Initialize Default Games
===================================================

Ensures the 9 canonical games for DeltaCrown platform exist in the database
with correct configuration. This command is idempotent and safe to run multiple times.

Usage:
    python manage.py init_default_games

What it does:
- Creates missing canonical games
- Updates existing games with canonical configuration
- Preserves uploaded media files (icon, logo, banner, card_image)
- Preserves active status if already set
- Logs legacy slugs that should be migrated

Canonical Games:
1. Valorant (valorant)
2. Counter-Strike 2 (cs2)
3. Dota 2 (dota2)
4. eFootball (efootball)
5. EA SPORTS FC (fc26)
6. Mobile Legends: Bang Bang (mlbb)
7. Call of Duty: Mobile (codm)
8. Free Fire (freefire)
9. PUBG Mobile (pubg)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.tournaments.models import Game


class Command(BaseCommand):
    help = 'Initialize or update the 9 canonical default games for DeltaCrown platform'
    
    # Canonical game specifications
    CANONICAL_GAMES = [
        {
            'slug': 'valorant',
            'name': 'VALORANT',
            'category': 'FPS',
            'platform': 'PC',
            'description': 'VALORANT is a free-to-play first-person tactical hero shooter developed by Riot Games.',
            'default_team_size': 5,
            'min_team_size': 5,
            'max_team_size': 7,
            'profile_id_field': 'riot_id',
            'default_result_type': 'map_score',
            'result_logic': {
                'primary_type': 'team_vs_team',
                'default_format': 'bo3',
                'supports_map_veto': True
            }
        },
        {
            'slug': 'cs2',
            'name': 'Counter-Strike 2',
            'category': 'FPS',
            'platform': 'PC',
            'description': 'Counter-Strike 2 is the latest installment in the legendary tactical FPS series.',
            'default_team_size': 5,
            'min_team_size': 5,
            'max_team_size': 7,
            'profile_id_field': 'steam_id',
            'default_result_type': 'map_score',
            'result_logic': {
                'primary_type': 'team_vs_team',
                'default_format': 'bo3',
                'supports_map_veto': True
            }
        },
        {
            'slug': 'dota2',
            'name': 'Dota 2',
            'category': 'MOBA',
            'platform': 'PC',
            'description': 'Dota 2 is a multiplayer online battle arena (MOBA) game developed by Valve Corporation.',
            'default_team_size': 5,
            'min_team_size': 5,
            'max_team_size': 7,
            'profile_id_field': 'steam_id',
            'default_result_type': 'best_of',
            'result_logic': {
                'primary_type': 'team_vs_team',
                'default_format': 'bo3',
                'supports_draft_phase': True
            }
        },
        {
            'slug': 'efootball',
            'name': 'eFootball',
            'category': 'Sports',
            'platform': 'Multi',
            'description': 'eFootball is a free-to-play football simulation game by Konami.',
            'default_team_size': 1,
            'min_team_size': 1,
            'max_team_size': 2,
            'profile_id_field': 'konami_id',
            'default_result_type': 'map_score',
            'result_logic': {
                'primary_type': 'solo',
                'default_format': 'bo1',
                'supports_crossplay': True
            }
        },
        {
            'slug': 'fc26',
            'name': 'EA SPORTS FC',
            'category': 'Sports',
            'platform': 'Multi',
            'description': 'EA SPORTS FC is the latest football simulation game from EA Sports.',
            'default_team_size': 1,
            'min_team_size': 1,
            'max_team_size': 2,
            'profile_id_field': 'ea_id',
            'default_result_type': 'map_score',
            'result_logic': {
                'primary_type': 'solo',
                'default_format': 'bo1',
                'season': '26'
            }
        },
        {
            'slug': 'mlbb',
            'name': 'Mobile Legends: Bang Bang',
            'category': 'MOBA',
            'platform': 'Mobile',
            'description': 'Mobile Legends: Bang Bang is a mobile multiplayer online battle arena game.',
            'default_team_size': 5,
            'min_team_size': 5,
            'max_team_size': 7,
            'profile_id_field': 'mlbb_id',
            'default_result_type': 'best_of',
            'result_logic': {
                'primary_type': 'team_vs_team',
                'default_format': 'bo3',
                'supports_draft_phase': True
            }
        },
        {
            'slug': 'codm',
            'name': 'Call of Duty: Mobile',
            'category': 'FPS',
            'platform': 'Mobile',
            'description': 'Call of Duty: Mobile brings the iconic FPS experience to mobile devices.',
            'default_team_size': 5,
            'min_team_size': 5,
            'max_team_size': 7,
            'profile_id_field': 'codm_id',
            'default_result_type': 'best_of',
            'result_logic': {
                'primary_type': 'team_vs_team',
                'default_format': 'bo5',
                'supports_mode_rotation': True,
                'modes_rotation': ['Hardpoint', 'Search and Destroy', 'Domination']
            }
        },
        {
            'slug': 'freefire',
            'name': 'Free Fire',
            'category': 'Battle Royale',
            'platform': 'Mobile',
            'description': 'Free Fire is a mobile battle royale game with fast-paced action.',
            'default_team_size': 4,
            'min_team_size': 4,
            'max_team_size': 4,
            'profile_id_field': 'freefire_id',
            'default_result_type': 'point_based',
            'result_logic': {
                'primary_type': 'battle_royale',
                'points_scheme_type': 'placement_plus_kills'
            }
        },
        {
            'slug': 'pubg',
            'name': 'PUBG Mobile',
            'category': 'Battle Royale',
            'platform': 'Mobile',
            'description': 'PUBG Mobile is a battle royale game where 100 players fight to be the last one standing.',
            'default_team_size': 4,
            'min_team_size': 4,
            'max_team_size': 4,
            'profile_id_field': 'pubg_id',
            'default_result_type': 'point_based',
            'result_logic': {
                'primary_type': 'battle_royale',
                'points_scheme_type': 'placement_plus_kills'
            }
        },
    ]
    
    # Legacy slugs to watch for
    LEGACY_SLUGS = {
        'pubg-mobile': 'pubg',
        'pubgmobile': 'pubg',
        'fifa': 'fc26',
        'fifa26': 'fc26',
        'csgo': 'cs2',
        'counter-strike': 'cs2',
        'mobile-legends': 'mlbb',
        'call-of-duty-mobile': 'codm',
        'free-fire': 'freefire',
        'e-football': 'efootball',
    }
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )
        parser.add_argument(
            '--force-update',
            action='store_true',
            help='Force update all fields (including media if they exist)',
        )
    
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', False)
        force_update = options.get('force_update', False)
        
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        
        self.stdout.write(self.style.SUCCESS('🎮 Initializing Default Games for DeltaCrown'))
        self.stdout.write('=' * 70)
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        results = []
        
        with transaction.atomic():
            for game_spec in self.CANONICAL_GAMES:
                slug = game_spec['slug']
                name = game_spec['name']
                
                try:
                    # Try to find by slug first (canonical lookup)
                    game = Game.objects.get(slug=slug)
                    action = 'EXISTS'
                    
                    # Update existing game
                    updated = self._update_game(game, game_spec, force_update, dry_run)
                    
                    if updated:
                        updated_count += 1
                        action = 'UPDATED'
                        self.stdout.write(
                            self.style.WARNING(f'  ✏️  Updated: {game_spec["name"]} ({slug})')
                        )
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            self.style.NOTICE(f'  ⏭️  Skipped: {game_spec["name"]} ({slug}) - No changes needed')
                        )
                    
                    results.append({
                        'slug': slug,
                        'name': game_spec['name'],
                        'action': action
                    })
                    
                except Game.DoesNotExist:
                    # Game not found by canonical slug
                    # Check if a game with this name exists with a different slug
                    try:
                        game = Game.objects.get(name=name)
                        # Found game with same name but different slug - update it
                        old_slug = game.slug
                        self.stdout.write(
                            self.style.WARNING(
                                f'  🔄 Migrating: {name} from slug "{old_slug}" → "{slug}"'
                            )
                        )
                        
                        if not dry_run:
                            game.slug = slug
                            self._update_game(game, game_spec, force_update, dry_run=False)
                        
                        updated_count += 1
                        results.append({
                            'slug': slug,
                            'name': game_spec['name'],
                            'action': 'MIGRATED'
                        })
                    
                    except Game.DoesNotExist:
                        # Create new game
                        if not dry_run:
                            game = Game.objects.create(
                                slug=slug,
                                name=game_spec['name'],
                                description=game_spec.get('description', ''),
                                category=game_spec.get('category'),
                                platform=game_spec.get('platform'),
                                default_team_size=game_spec['default_team_size'],
                                min_team_size=game_spec['min_team_size'],
                                max_team_size=game_spec['max_team_size'],
                                profile_id_field=game_spec.get('profile_id_field', 'game_id'),
                                default_result_type=game_spec['default_result_type'],
                                result_logic=game_spec.get('result_logic', {}),
                                is_active=True,
                            )
                        
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✅ Created: {game_spec["name"]} ({slug})')
                        )
                        
                        results.append({
                            'slug': slug,
                            'name': game_spec['name'],
                            'action': 'CREATED'
                        })
            
            # Check for legacy slugs
            self._check_legacy_slugs()
            
            if dry_run:
                self.stdout.write(self.style.WARNING('\n⚠️  DRY RUN - No changes were saved'))
                # Rollback transaction in dry run mode
                transaction.set_rollback(True)
        
        # Print summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('📊 SUMMARY'))
        self.stdout.write('=' * 70)
        self.stdout.write(f'  Created: {created_count} games')
        self.stdout.write(f'  Updated: {updated_count} games')
        self.stdout.write(f'  Skipped: {skipped_count} games (no changes needed)')
        self.stdout.write(f'  Total canonical games: {len(self.CANONICAL_GAMES)}')
        
        if created_count > 0 or updated_count > 0:
            self.stdout.write('\n' + self.style.SUCCESS('✨ Game registry is now synchronized!'))
            self.stdout.write('\n💡 Next steps:')
            self.stdout.write('  1. Upload game icons/logos via Django admin')
            self.stdout.write('  2. Set custom colors for each game')
            self.stdout.write('  3. Define roles in the admin interface')
        else:
            self.stdout.write('\n' + self.style.SUCCESS('✅ All games are already up to date!'))
    
    def _update_game(self, game, game_spec, force_update, dry_run):
        """
        Update an existing game with canonical values.
        Returns True if any changes were made, False otherwise.
        """
        changed = False
        
        # Fields to always update
        if game.name != game_spec['name']:
            if not dry_run:
                game.name = game_spec['name']
            changed = True
        
        if game.category != game_spec.get('category'):
            if not dry_run:
                game.category = game_spec.get('category')
            changed = True
        
        if game.platform != game_spec.get('platform'):
            if not dry_run:
                game.platform = game_spec.get('platform')
            changed = True
        
        if game.default_team_size != game_spec['default_team_size']:
            if not dry_run:
                game.default_team_size = game_spec['default_team_size']
            changed = True
        
        if game.min_team_size != game_spec['min_team_size']:
            if not dry_run:
                game.min_team_size = game_spec['min_team_size']
            changed = True
        
        if game.max_team_size != game_spec['max_team_size']:
            if not dry_run:
                game.max_team_size = game_spec['max_team_size']
            changed = True
        
        if game.profile_id_field != game_spec.get('profile_id_field', 'game_id'):
            if not dry_run:
                game.profile_id_field = game_spec.get('profile_id_field', 'game_id')
            changed = True
        
        if game.default_result_type != game_spec['default_result_type']:
            if not dry_run:
                game.default_result_type = game_spec['default_result_type']
            changed = True
        
        # Update result_logic (always update to keep in sync)
        if game.result_logic != game_spec.get('result_logic', {}):
            if not dry_run:
                game.result_logic = game_spec.get('result_logic', {})
            changed = True
        
        # Update description if empty
        if not game.description and game_spec.get('description'):
            if not dry_run:
                game.description = game_spec['description']
            changed = True
        
        # Save if changes were made
        if changed and not dry_run:
            game.save()
        
        return changed
    
    def _check_legacy_slugs(self):
        """Check for games with legacy slugs and suggest migration."""
        legacy_games = Game.objects.filter(slug__in=self.LEGACY_SLUGS.keys())
        
        if legacy_games.exists():
            self.stdout.write('\n' + '=' * 70)
            self.stdout.write(self.style.WARNING('⚠️  LEGACY SLUGS DETECTED'))
            self.stdout.write('=' * 70)
            
            for game in legacy_games:
                canonical_slug = self.LEGACY_SLUGS.get(game.slug)
                self.stdout.write(
                    self.style.WARNING(
                        f'  ⚠️  Legacy slug "{game.slug}" → Should migrate to "{canonical_slug}"'
                    )
                )
                self.stdout.write(
                    f'     Game: {game.name} (ID: {game.id})'
                )
            
            self.stdout.write('\n💡 Recommendation:')
            self.stdout.write('  These legacy games should be migrated to canonical slugs.')
            self.stdout.write('  You can manually update them in Django admin or create a migration script.')
            self.stdout.write('  DO NOT delete them if they have associated tournaments!')
