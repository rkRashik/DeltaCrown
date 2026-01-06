"""
Management command to clean up stale Game Passport schema fields.

PHASE 9A-20: Fix Issue #1 - eFootball has stale owner_id and ign fields

This command deletes GamePlayerIdentityConfig entries that no longer exist in 
seed_identity_configs_2026.py schema definition. Use with --apply to execute.

Usage:
    # Preview changes (dry run)
    python manage.py cleanup_passport_schema --game efootball
    
    # Apply cleanup
    python manage.py cleanup_passport_schema --game efootball --apply
    
    # Clean all games
    python manage.py cleanup_passport_schema --apply
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.games.models import Game, GamePlayerIdentityConfig


class Command(BaseCommand):
    help = 'Clean up stale passport schema fields (Phase 9A-20 Issue #1 fix)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--game',
            type=str,
            help='Clean only specific game slug (e.g., efootball)'
        )
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Apply cleanup (default is dry-run preview)'
        )

    def handle(self, *args, **options):
        game_slug = options.get('game')
        apply_changes = options.get('apply', False)
        
        if not apply_changes:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] Preview mode - use --apply to execute\n'))
        
        # Get canonical schemas from seed command
        canonical_schemas = self.get_canonical_schemas()
        
        if game_slug:
            try:
                game = Game.objects.get(slug=game_slug, is_active=True)
                self.clean_game(game, canonical_schemas, apply_changes)
            except Game.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'[ERROR] Game not found: {game_slug}'))
                return
        else:
            games = Game.objects.filter(is_active=True)
            self.stdout.write(f'[CLEANUP] Processing {games.count()} active games...\n')
            for game in games:
                self.clean_game(game, canonical_schemas, apply_changes)
        
        if apply_changes:
            self.stdout.write(self.style.SUCCESS('\n[SUCCESS] Schema cleanup complete!'))
            self.stdout.write('\nNext steps:')
            self.stdout.write('1. Clear browser cache to refresh frontend schema')
            self.stdout.write('2. Test passport creation for affected games')
        else:
            self.stdout.write(self.style.WARNING('\n[DRY RUN] No changes applied. Use --apply to execute cleanup.'))

    def clean_game(self, game, canonical_schemas, apply_changes):
        """Clean stale fields for a single game"""
        self.stdout.write(f'[{game.slug}] {game.display_name}')
        
        # Get canonical schema
        if game.slug not in canonical_schemas:
            self.stdout.write(f'  [SKIP] No canonical schema defined')
            return
        
        canonical_fields = canonical_schemas[game.slug]
        
        # Find stale configs
        existing_configs = GamePlayerIdentityConfig.objects.filter(game=game)
        stale_configs = existing_configs.exclude(field_name__in=canonical_fields)
        
        if not stale_configs.exists():
            self.stdout.write(f'  [OK] No stale fields found')
            return
        
        # Report stale fields
        stale_fields = list(stale_configs.values_list('field_name', flat=True))
        self.stdout.write(self.style.WARNING(f'  [STALE] Found {len(stale_fields)} stale fields:'))
        for field_name in stale_fields:
            self.stdout.write(f'    - {field_name}')
        
        # Apply cleanup if requested
        if apply_changes:
            with transaction.atomic():
                deleted_count, _ = stale_configs.delete()
                self.stdout.write(self.style.SUCCESS(f'  [DELETED] Removed {deleted_count} stale configs'))
        else:
            self.stdout.write(f'  [PREVIEW] Would delete {len(stale_fields)} configs (use --apply)')

    def get_canonical_schemas(self):
        """
        Return canonical field list from seed_identity_configs_2026.py.
        
        CRITICAL: This must match the 2026 seed file exactly.
        If you modify seed_identity_configs_2026.py, update this too.
        """
        return {
            'valorant': [
                'riot_id',
                'riot_tagline',
                'region',
                'rank',
                'role'
            ],
            'efootball': [
                'konami_id',
                'efootball_id',
                'username',
                'team_name',
                'platform',
                'division'
            ],
            'r6siege': [
                'uplay_id',
                'ign',
                'platform',
                'region',
                'rank'
            ],
            'dota2': [
                'steam_id',
                'dota_id',
                'ign',
                'server',
                'rank',
                'role'
            ],
            'cs2': [
                'steam_id',
                'ign',
                'region',
                'rank',
                'role',
                'premier_rating'
            ],
            'rocketleague': [
                'epic_id',
                'ign',
                'platform',
                'rank_1v1',
                'rank_2v2',
                'rank_3v3'
            ],
            'apexlegends': [
                'ea_id',
                'ign',
                'platform',
                'region',
                'rank',
                'legend'
            ],
            'leagueoflegends': [
                'riot_id',
                'riot_tagline',
                'region',
                'rank',
                'role'
            ],
            'mlbb': [
                'game_id',
                'ign',
                'server',
                'rank',
                'role'
            ],
            'codwarzone': [
                'activision_id',
                'ign',
                'platform',
                'region',
                'mode'
            ]
        }
