# Generated manually for GP-2A: Structured Identity Columns
"""
GP-2A Migration: Move Identity from JSON to First-Class Columns

This migration:
1. Adds ign, discriminator, platform columns to GameProfile
2. Adds structured identity columns to GameProfileAlias  
3. Backfills from metadata JSON (if present) using game-specific mapping
4. Computes identity_key from structured fields
5. Handles conflicts gracefully (logs warnings, doesn't crash)

BACKFILL MAPPING:
- Valorant: riot_name → ign, tagline → discriminator
- League of Legends: riot_name → ign, tagline → discriminator
- TFT: riot_name → ign, tagline → discriminator
- MLBB: numeric_id → ign, zone_id → discriminator
- Steam games (CS2, Dota 2): steam_id64 → ign
- EA FC: ea_id → ign, platform → platform
- Konami games (eFootball): konami_id → ign, platform → platform
- Ubisoft games (R6): ubisoft_username → ign, platform → platform
- Epic games: epic_id → ign

IDENTITY_KEY COMPUTATION:
- Riot games: lowercase(ign) + "#" + lowercase(discriminator)
- MLBB: lowercase(ign) + "_" + discriminator
- Steam games: lowercase(ign)
- Others: lowercase(ign) + optional discriminator/platform

REGION HANDLING:
- Region already exists as separate field
- Will be used in identity_key for region-locked games
"""

from django.db import migrations, models
import logging

logger = logging.getLogger(__name__)


def backfill_structured_identity(apps, schema_editor):
    """
    Backfill structured identity fields from metadata JSON.
    
    Safe for empty DB (no-op if no records).
    Handles conflicts by logging warnings (doesn't crash migration).
    """
    GameProfile = apps.get_model('user_profile', 'GameProfile')
    Game = apps.get_model('games', 'Game')
    
    # Get all game profiles
    profiles = GameProfile.objects.select_related('game').all()
    
    if not profiles.exists():
        logger.info("GP-2A: No profiles to backfill (empty DB)")
        return
    
    logger.info(f"GP-2A: Backfilling {profiles.count()} profiles...")
    
    updated_count = 0
    skipped_count = 0
    conflict_count = 0
    
    for profile in profiles:
        # Skip if already has structured identity
        if profile.ign:
            skipped_count += 1
            continue
        
        # Get metadata
        metadata = profile.metadata or {}
        if not metadata:
            # No metadata, try to extract from in_game_name
            if profile.in_game_name:
                # Simple fallback: use in_game_name as ign
                profile.ign = profile.in_game_name
                if '#' in profile.in_game_name:
                    parts = profile.in_game_name.split('#', 1)
                    profile.ign = parts[0]
                    profile.discriminator = parts[1]
                profile.save(update_fields=['ign', 'discriminator'])
                updated_count += 1
            continue
        
        # Game-specific mapping
        game_slug = profile.game.slug if profile.game else None
        
        try:
            if game_slug in ['valorant', 'lol', 'tft']:
                # Riot games: riot_name → ign, tagline → discriminator
                if 'riot_name' in metadata:
                    profile.ign = metadata['riot_name']
                if 'tagline' in metadata:
                    profile.discriminator = metadata['tagline']
                
            elif game_slug == 'mlbb':
                # MLBB: numeric_id → ign, zone_id → discriminator
                if 'numeric_id' in metadata:
                    profile.ign = str(metadata['numeric_id'])
                if 'zone_id' in metadata:
                    profile.discriminator = str(metadata['zone_id'])
                
            elif game_slug in ['cs2', 'dota2']:
                # Steam games: steam_id64 → ign
                if 'steam_id64' in metadata:
                    profile.ign = metadata['steam_id64']
                
            elif game_slug == 'eafc':
                # EA FC: ea_id → ign, platform → platform
                if 'ea_id' in metadata:
                    profile.ign = metadata['ea_id']
                if 'platform' in metadata:
                    profile.platform = metadata['platform']
                
            elif game_slug == 'efootball':
                # eFootball: konami_id → ign, platform → platform
                if 'konami_id' in metadata:
                    profile.ign = metadata['konami_id']
                if 'platform' in metadata:
                    profile.platform = metadata['platform']
                
            elif game_slug == 'r6':
                # Rainbow Six: ubisoft_username → ign, platform → platform
                if 'ubisoft_username' in metadata:
                    profile.ign = metadata['ubisoft_username']
                if 'platform' in metadata:
                    profile.platform = metadata['platform']
                
            elif game_slug in ['fortnite', 'rocketleague']:
                # Epic games: epic_id → ign
                if 'epic_id' in metadata:
                    profile.ign = metadata['epic_id']
                
            else:
                # Unknown game: try common fields
                if 'player_id' in metadata:
                    profile.ign = metadata['player_id']
                elif 'username' in metadata:
                    profile.ign = metadata['username']
                elif 'in_game_name' in metadata:
                    profile.ign = metadata['in_game_name']
            
            # Compute identity_key from structured fields
            if profile.ign:
                identity_parts = []
                
                # Normalize ign (lowercase, strip)
                normalized_ign = profile.ign.lower().strip()
                identity_parts.append(normalized_ign)
                
                # Add discriminator for Riot/MLBB
                if profile.discriminator:
                    if game_slug in ['valorant', 'lol', 'tft']:
                        # Riot format: ign#tag
                        normalized_disc = profile.discriminator.lower().strip()
                        identity_parts.append(f"#{normalized_disc}")
                    elif game_slug == 'mlbb':
                        # MLBB format: ign_zoneid
                        identity_parts.append(f"_{profile.discriminator}")
                    else:
                        # Generic format
                        identity_parts.append(f"#{profile.discriminator.lower().strip()}")
                
                # Add platform if present
                if profile.platform:
                    identity_parts.append(f":{profile.platform.lower().strip()}")
                
                # Add region for region-locked games (optional, currently not used)
                # if profile.region:
                #     identity_parts.append(f"@{profile.region.lower().strip()}")
                
                new_identity_key = ''.join(identity_parts)
                
                # Check for conflicts before saving
                existing = GameProfile.objects.filter(
                    game=profile.game,
                    identity_key=new_identity_key
                ).exclude(id=profile.id)
                
                if existing.exists():
                    logger.warning(
                        f"GP-2A: Conflict detected for game={game_slug}, "
                        f"identity_key={new_identity_key}. Skipping profile {profile.id}"
                    )
                    conflict_count += 1
                    continue
                
                profile.identity_key = new_identity_key
                profile.save(update_fields=['ign', 'discriminator', 'platform', 'identity_key'])
                updated_count += 1
            
        except Exception as e:
            logger.error(f"GP-2A: Error backfilling profile {profile.id}: {e}")
            continue
    
    logger.info(
        f"GP-2A: Backfill complete. "
        f"Updated: {updated_count}, Skipped: {skipped_count}, Conflicts: {conflict_count}"
    )


def reverse_backfill(apps, schema_editor):
    """
    Reverse migration: Clear structured identity fields.
    """
    GameProfile = apps.get_model('user_profile', 'GameProfile')
    
    # Clear structured identity fields (keep identity_key for safety)
    GameProfile.objects.all().update(
        ign=None,
        discriminator=None,
        platform=None
    )


class Migration(migrations.Migration):

    dependencies = [
        ('user_profile', '0025_gp1_step3_finalize_game_fk'),
        ('games', '0001_initial'),  # Ensure Game model exists
    ]

    operations = [
        # 1. Add structured identity columns to GameProfile
        migrations.AddField(
            model_name='gameprofile',
            name='ign',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="In-game name / username (e.g., 'Player123' for Riot, 'SteamID64' for Steam)",
                max_length=64,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='discriminator',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Discriminator / Tag / Zone (e.g., '#NA1' for Riot, Zone ID for MLBB)",
                max_length=32,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='gameprofile',
            name='platform',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Platform identifier (e.g., 'PC', 'PS5', 'Xbox', platform-specific ID)",
                max_length=32,
                null=True
            ),
        ),
        
        # 2. Update help text for existing fields
        migrations.AlterField(
            model_name='gameprofile',
            name='in_game_name',
            field=models.CharField(
                help_text="Display name (computed from ign+discriminator, e.g., 'Player#TAG')",
                max_length=100
            ),
        ),
        migrations.AlterField(
            model_name='gameprofile',
            name='identity_key',
            field=models.CharField(
                db_index=True,
                help_text="Normalized identity for uniqueness (computed from ign+discriminator+region+platform, lowercase)",
                max_length=100
            ),
        ),
        migrations.AlterField(
            model_name='gameprofile',
            name='metadata',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text="SHOWCASE/CONFIG ONLY - DO NOT store identity here (use ign/discriminator/region/platform columns)"
            ),
        ),
        migrations.AlterField(
            model_name='gameprofile',
            name='region',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text="Player region (part of identity for some games, used for join gating)",
                max_length=10
            ),
        ),
        
        # 3. Add structured identity columns to GameProfileAlias
        migrations.AddField(
            model_name='gameprofilealias',
            name='old_ign',
            field=models.CharField(
                blank=True,
                help_text="Previous IGN/username",
                max_length=64,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='gameprofilealias',
            name='old_discriminator',
            field=models.CharField(
                blank=True,
                help_text="Previous discriminator/tag/zone",
                max_length=32,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='gameprofilealias',
            name='old_platform',
            field=models.CharField(
                blank=True,
                help_text="Previous platform",
                max_length=32,
                null=True
            ),
        ),
        migrations.AddField(
            model_name='gameprofilealias',
            name='old_region',
            field=models.CharField(
                blank=True,
                default='',
                help_text="Previous region",
                max_length=10
            ),
        ),
        migrations.AlterField(
            model_name='gameprofilealias',
            name='old_in_game_name',
            field=models.CharField(
                help_text="Previous in-game name (display format)",
                max_length=100
            ),
        ),
        
        # 4. Backfill structured identity from metadata
        migrations.RunPython(
            backfill_structured_identity,
            reverse_backfill
        ),
    ]
