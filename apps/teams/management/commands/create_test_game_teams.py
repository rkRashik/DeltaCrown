# apps/teams/management/commands/create_test_game_teams.py
"""
Management command to create test teams for all supported games.

Useful for testing the new game-specific roster management system.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import transaction

from apps.user_profile.models import UserProfile
from apps.teams.models.game_specific import (
    GAME_TEAM_MODELS, GAME_MEMBERSHIP_MODELS
)
from apps.teams.game_config import GAME_CONFIGS
from apps.teams.roster_manager import get_roster_manager


class Command(BaseCommand):
    help = 'Create test teams for all supported games'

    def add_arguments(self, parser):
        parser.add_argument(
            '--game',
            type=str,
            help='Create test team only for specific game (e.g., valorant, cs2)',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Delete existing test teams before creating new ones',
        )

    def handle(self, *args, **options):
        game_filter = options.get('game')
        cleanup = options.get('cleanup', False)
        
        if game_filter and game_filter not in GAME_CONFIGS:
            self.stdout.write(self.style.ERROR(
                f"Unknown game: {game_filter}. "
                f"Available: {', '.join(GAME_CONFIGS.keys())}"
            ))
            return
        
        games_to_process = [game_filter] if game_filter else list(GAME_CONFIGS.keys())
        
        self.stdout.write(self.style.SUCCESS(
            f"Creating test teams for: {', '.join(games_to_process)}"
        ))
        
        # Create test users if they don't exist
        test_users = self._create_test_users()
        
        for game_code in games_to_process:
            try:
                self._create_test_team(game_code, test_users, cleanup)
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f"Failed to create {game_code} team: {e}"
                ))
        
        self.stdout.write(self.style.SUCCESS("Test team creation complete!"))
    
    def _create_test_users(self):
        """Create test users for team members."""
        self.stdout.write("Creating test users...")
        
        test_users = []
        for i in range(1, 8):  # Create 7 test users (enough for max roster)
            username = f"testplayer{i}"
            email = f"testplayer{i}@example.com"
            
            user, created = User.objects.get_or_create(
                username=username,
                defaults={'email': email}
            )
            
            if created:
                user.set_password("testpassword123")
                user.save()
                self.stdout.write(f"  Created user: {username}")
            
            # Ensure UserProfile exists
            profile, _ = UserProfile.objects.get_or_create(user=user)
            test_users.append(profile)
        
        return test_users
    
    @transaction.atomic
    def _create_test_team(self, game_code, test_users, cleanup=False):
        """Create a test team for a specific game."""
        config = GAME_CONFIGS[game_code]
        team_model = GAME_TEAM_MODELS[game_code]
        
        team_name = f"Test {config.name} Team"
        team_tag = f"T{game_code.upper()[:3]}"
        
        # Cleanup existing test team if requested
        if cleanup:
            deleted = team_model.objects.filter(name=team_name).delete()
            if deleted[0] > 0:
                self.stdout.write(f"  Deleted existing {game_code} test team")
        
        # Check if team already exists
        if team_model.objects.filter(name=team_name).exists():
            self.stdout.write(self.style.WARNING(
                f"  {game_code} test team already exists, skipping..."
            ))
            return
        
        # Create team
        team = team_model.objects.create(
            name=team_name,
            tag=team_tag,
            description=f"Test team for {config.name} roster management",
            captain=test_users[0],
            region="Test Region",
            is_active=True,
            is_public=True,
        )
        
        self.stdout.write(self.style.SUCCESS(
            f"✓ Created {config.name} team: {team_name}"
        ))
        
        # Add players to roster
        manager = get_roster_manager(team)
        
        # Add starters
        num_starters = min(config.max_starters, len(test_users) - 1)
        for i in range(num_starters):
            role = config.roles[i % len(config.roles)]
            profile = test_users[i]
            
            try:
                membership = manager.add_player(
                    profile=profile,
                    role=role,
                    is_starter=True,
                    ign=f"{profile.user.username}_IGN"
                )
                self.stdout.write(
                    f"  + Added starter: {profile.user.username} as {role}"
                )
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"  Could not add {profile.user.username}: {e}"
                ))
        
        # Add substitutes if there are enough test users
        if len(test_users) > config.max_starters:
            num_subs = min(
                config.max_substitutes,
                len(test_users) - config.max_starters
            )
            
            for i in range(num_subs):
                idx = config.max_starters + i
                if idx < len(test_users):
                    role = config.roles[idx % len(config.roles)]
                    profile = test_users[idx]
                    
                    try:
                        membership = manager.add_player(
                            profile=profile,
                            role=role,
                            is_starter=False,
                            ign=f"{profile.user.username}_SUB"
                        )
                        self.stdout.write(
                            f"  + Added substitute: {profile.user.username} as {role}"
                        )
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(
                            f"  Could not add substitute {profile.user.username}: {e}"
                        ))
        
        # Display roster status
        status = manager.get_roster_status()
        self.stdout.write(
            f"  Roster: {status['starters']} starters + "
            f"{status['substitutes']} subs = {status['total_members']} total"
        )
        
        # Validate for tournament readiness
        validation = manager.validate_for_tournament()
        if validation['is_valid']:
            self.stdout.write(self.style.SUCCESS(
                "  ✓ Team is tournament-ready"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"  ⚠ Team has issues: {', '.join(validation['issues'])}"
            ))
