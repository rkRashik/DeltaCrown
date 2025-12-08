"""
Game Validation Service for identity and registration validation.

This service provides game-specific validation logic for:
- Player identity fields (Riot ID, Steam ID, etc.)
- Registration eligibility (email, phone, region, team size)
- Match result validation (delegates to GameRulesEngine)

Phase 2, Epic 2.2: Game Validation Service
Reference: SMART_REG_AND_RULES_PART_3.md, ARCH_PLAN_PART_1.md
"""

import logging
import re
from typing import Any, Dict

from apps.tournament_ops.dtos.common import ValidationResult
from apps.tournament_ops.dtos.eligibility import EligibilityResultDTO
from apps.tournament_ops.dtos.team import TeamDTO
from apps.tournament_ops.dtos.user import UserProfileDTO

logger = logging.getLogger("games.validation_service")


class GameValidationService:
    """
    Service for validating player identities and registration eligibility.

    This service enforces game-specific rules from GamePlayerIdentityConfig
    and GameTournamentConfig models.

    Usage:
        validator = GameValidationService()
        result = validator.validate_identity("valorant", {"riot_id": "Player#1234"})
        eligibility = validator.validate_registration("valorant", user_dto, team_dto, config)
    """

    def validate_identity(
        self, game_slug: str, identity_payload: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate player identity fields against game configuration.

        Args:
            game_slug: Game identifier (e.g., "valorant", "pubg-mobile")
            identity_payload: Dict of identity fields (e.g., {"riot_id": "Name#1234"})

        Returns:
            ValidationResult with is_valid, errors list

        Validation checks:
        - Required fields present
        - Regex patterns match
        - Field immutability (if applicable - not checked here, needs existing data)
        """
        from apps.games.models import Game, GamePlayerIdentityConfig

        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            return ValidationResult(
                is_valid=False, errors=[f"Game '{game_slug}' not found"]
            )

        # Get all identity configs for this game
        identity_configs = GamePlayerIdentityConfig.objects.filter(game=game)

        if not identity_configs.exists():
            # No identity requirements - accept anything
            logger.warning(f"No identity config defined for {game_slug}")
            return ValidationResult(is_valid=True, errors=[])

        errors = []

        for config in identity_configs:
            field_name = config.field_name
            field_value = identity_payload.get(field_name)

            # Check required fields
            if config.is_required and not field_value:
                errors.append(
                    f"Required identity field '{config.display_name}' ({field_name}) missing"
                )
                continue

            # Skip further validation if field not provided and not required
            if not field_value:
                continue

            # Regex validation
            if config.validation_regex:
                try:
                    pattern = re.compile(config.validation_regex)
                    if not pattern.match(str(field_value)):
                        errors.append(
                            f"Identity field '{config.display_name}' has invalid format. "
                            f"Expected pattern: {config.help_text or config.placeholder}"
                        )
                except re.error as e:
                    logger.error(
                        f"Invalid regex in config for {game_slug}.{field_name}: {e}"
                    )
                    errors.append(f"Internal configuration error for '{field_name}'")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def validate_registration(
        self,
        game_slug: str,
        user_profile_dto: UserProfileDTO,
        team_dto: TeamDTO,
        tournament_config: Dict[str, Any],
    ) -> EligibilityResultDTO:
        """
        Validate complete registration eligibility.

        Args:
            game_slug: Game identifier
            user_profile_dto: User profile data
            team_dto: Team data (size, members, etc.)
            tournament_config: Tournament-level config (from GameTournamentConfig)

        Returns:
            EligibilityResultDTO with is_eligible, reason

        Validation checks:
        - Email verification requirements
        - Phone verification requirements
        - Team size constraints
        - Region restrictions
        - Identity field requirements
        """
        from apps.games.models import Game, GameTournamentConfig

        try:
            game = Game.objects.get(slug=game_slug)
        except Game.DoesNotExist:
            return EligibilityResultDTO(
                is_eligible=False, reason=f"Game '{game_slug}' not found"
            )

        # Get tournament config for this game
        try:
            config = GameTournamentConfig.objects.get(game=game)
        except GameTournamentConfig.DoesNotExist:
            # No config - use lenient defaults
            logger.warning(f"No tournament config for {game_slug}, using defaults")
            config = None

        errors = []

        # Email verification check
        if config and config.require_verified_email:
            if not user_profile_dto.email_verified:
                errors.append("Email address must be verified")

        # Phone verification check
        if config and config.require_verified_phone:
            if not getattr(user_profile_dto, "phone_verified", False):
                errors.append("Phone number must be verified")

        # Team size validation
        if config:
            team_size = len(team_dto.member_ids)
            if team_size < config.min_team_size:
                errors.append(
                    f"Team size ({team_size}) below minimum ({config.min_team_size})"
                )
            if team_size > config.max_team_size:
                errors.append(
                    f"Team size ({team_size}) exceeds maximum ({config.max_team_size})"
                )

        # Region restriction check (simplified - assumes team_dto has region field)
        if config and not config.allow_cross_region:
            # TODO: Implement cross-region check when team members have region data
            # For now, just log warning
            logger.debug(
                f"Cross-region check needed for {game_slug} but not implemented yet"
            )

        # Identity requirements check (additional custom checks)
        if config and config.identity_requirements:
            # Example: {"min_account_level": 30}
            # This would require fetching player's game account data
            # For Phase 2, just log TODO
            logger.debug(
                f"Identity requirements defined for {game_slug}: {config.identity_requirements}"
            )
            # TODO (Phase 3): Implement identity_requirements validation

        if errors:
            return EligibilityResultDTO(
                is_eligible=False, reasons=errors
            )

        return EligibilityResultDTO(is_eligible=True, reasons=[])

    def validate_match_result(
        self, game_slug: str, match_payload: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate match result schema (delegates to GameRulesEngine).

        Args:
            game_slug: Game identifier
            match_payload: Match result data

        Returns:
            ValidationResult with is_valid, errors
        """
        from apps.games.services.rules_engine import GameRulesEngine

        engine = GameRulesEngine()
        return engine.validate_result_schema(game_slug, match_payload)
