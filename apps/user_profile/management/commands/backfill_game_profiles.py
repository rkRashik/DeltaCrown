"""
Management command to backfill GameProfile instances for users.

This is a BACKFILL command - it creates GameProfile records for existing users
who don't have them yet. This is different from seed_game_passport_schemas.py
which creates per-game CONFIGURATION (GamePassportSchema).

Usage:
    # Dry-run to see what would be created
    python manage.py backfill_game_profiles --dry-run
    
    # Backfill for specific user
    python manage.py backfill_game_profiles --user <username_or_id>
    
    # Backfill for all users (limit to first 100)
    python manage.py backfill_game_profiles --all --limit 100
    
    # Backfill for specific game
    python manage.py backfill_game_profiles --all --game valorant

Requirements:
    - Games must exist (run: python manage.py seed_games first)
    - GamePassportSchemas must exist (run: python manage.py seed_game_passport_schemas first)
    - Users must exist (if no users, command exits gracefully)

Idempotency:
    - Only creates GameProfile if user doesn't have one for that game
    - Safe to run multiple times
    - Uses get_or_create for atomic operation
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.games.models import Game
from apps.user_profile.models import GameProfile, GamePassportSchema

User = get_user_model()


class Command(BaseCommand):
    help = "Backfill GameProfile instances for users (requires games + schemas)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be created without making changes',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Backfill for specific user (username or ID)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Backfill for all users (use with --limit)',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of users to process (safety guard)',
        )
        parser.add_argument(
            '--game',
            type=str,
            help='Only backfill for specific game (slug, e.g., "valorant")',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_filter = options['user']
        all_users = options['all']
        limit = options['limit']
        game_slug = options['game']

        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("🎮 GameProfile Backfill Command"))
        self.stdout.write("="*80 + "\n")

        # Validation: Ensure games exist
        if not Game.objects.exists():
            self.stdout.write(self.style.ERROR(
                "❌ No games found. Run: python manage.py seed_games"
            ))
            return

        # Validation: Ensure schemas exist
        if not GamePassportSchema.objects.exists():
            self.stdout.write(self.style.ERROR(
                "❌ No GamePassportSchema found. Run: python manage.py seed_game_passport_schemas"
            ))
            return

        # Determine which games to process
        if game_slug:
            try:
                games = [Game.objects.get(slug=game_slug)]
                self.stdout.write(f"🎯 Targeting game: {games[0].name}")
            except Game.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Game not found: {game_slug}"))
                return
        else:
            games = list(Game.objects.all())
            self.stdout.write(f"🎯 Processing all games: {len(games)} games")

        # Determine which users to process
        if user_filter:
            # Try to find user by username or ID
            try:
                if user_filter.isdigit():
                    users = User.objects.filter(id=int(user_filter))
                else:
                    users = User.objects.filter(username=user_filter)
                
                if not users.exists():
                    self.stdout.write(self.style.ERROR(f"❌ User not found: {user_filter}"))
                    return
                
                self.stdout.write(f"👤 Targeting user: {users.first().username}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error finding user: {e}"))
                return
        elif all_users:
            users = User.objects.all()
            if limit:
                users = users[:limit]
                self.stdout.write(f"👥 Processing users (limited to {limit})")
            else:
                self.stdout.write(f"👥 Processing ALL users: {users.count()}")
        else:
            self.stdout.write(self.style.ERROR(
                "❌ Must specify --user <username> OR --all"
            ))
            return

        # Check if any users exist
        user_count = users.count()
        if user_count == 0:
            self.stdout.write(self.style.WARNING(
                "⚠️  No users found. Nothing to backfill. This is OK for fresh database."
            ))
            return

        self.stdout.write(f"\n📊 Summary:")
        self.stdout.write(f"   Users to process: {user_count}")
        self.stdout.write(f"   Games to process: {len(games)}")
        self.stdout.write(f"   Max possible GameProfiles: {user_count * len(games)}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\n🔍 DRY RUN MODE - No changes will be made\n"))
        
        # Process users and games
        created_count = 0
        skipped_count = 0
        error_count = 0

        self.stdout.write("\n" + "-"*80)
        self.stdout.write("Processing...")
        self.stdout.write("-"*80 + "\n")

        for user in users:
            for game in games:
                try:
                    # Check if GameProfile already exists
                    exists = GameProfile.objects.filter(user=user, game=game).exists()
                    
                    if exists:
                        skipped_count += 1
                        self.stdout.write(
                            f"⏭️  Skipped: {user.username} already has {game.name} profile"
                        )
                        continue
                    
                    if dry_run:
                        self.stdout.write(
                            f"🔍 Would create: {user.username} → {game.name} profile"
                        )
                        created_count += 1
                    else:
                        # Create GameProfile with minimal data
                        # User will need to fill in ign/rank/stats later
                        with transaction.atomic():
                            game_profile, created = GameProfile.objects.get_or_create(
                                user=user,
                                game=game,
                                defaults={
                                    'game_display_name': game.name,
                                    'in_game_name': '',  # User fills this
                                    'identity_key': f"{user.username}_{game.slug}".lower(),
                                    'rank_name': '',
                                    'rank_tier': 0,
                                    'matches_played': 0,
                                    'win_rate': 0,
                                    'role': '',
                                    'region': 'BD',  # Default region
                                    'is_primary': False,
                                    'visibility': GameProfile.VISIBILITY_PUBLIC,
                                    'verified_at': None,
                                    'verification_method': '',
                                }
                            )
                            
                            if created:
                                created_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(f"✅ Created: {user.username} → {game.name}")
                                )
                            else:
                                skipped_count += 1
                                self.stdout.write(
                                    f"⏭️  Already exists: {user.username} → {game.name}"
                                )
                
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f"❌ Error for {user.username} → {game.name}: {e}")
                    )

        # Final summary
        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("📊 Backfill Complete"))
        self.stdout.write("="*80)
        self.stdout.write(f"\n✅ Created: {created_count}")
        self.stdout.write(f"⏭️  Skipped (already exist): {skipped_count}")
        self.stdout.write(f"❌ Errors: {error_count}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n🔍 This was a DRY RUN. Run without --dry-run to apply changes.\n"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                "\n🎉 GameProfile backfill complete!\n"
            ))
            self.stdout.write("📝 Next steps:")
            self.stdout.write("   1. Users can now fill in their in-game names via profile editor")
            self.stdout.write("   2. Users can verify their accounts via API")
            self.stdout.write("   3. Check admin: /admin/user_profile/gameprofile/\n")
