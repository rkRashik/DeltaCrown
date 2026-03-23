"""
TOC Sprint 10G — Settings & Configuration Service (1:1 Database Parity)

Provides organizer-level operations for:
  - Tournament basic settings (name, dates, capacity, prizes, etc.)
  - Media & uploads (banner, thumbnail, rules_pdf, terms_pdf)
  - Venue settings (conditional on tournament mode)
  - Entry fees & refund policy
  - Payment method CRUD (TournamentPaymentMethod)
  - Rules & Terms
  - Feature toggles (check-in, seeding, live updates, certificates, challenges, fan voting)
  - Social & contact links
  - SEO & metadata
  - Game match configuration (format, scoring rules)
  - Map pool management (CRUD, reorder)
  - Veto session management
  - Server region management
  - Rulebook versioning & consent
  - BR scoring matrix
"""

from __future__ import annotations

import logging
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator, validate_email
from django.db import transaction
from django.utils.dateparse import parse_datetime
from django.utils import timezone

from apps.tournaments.models import Tournament
from apps.tournaments.models.form_configuration import TournamentFormConfiguration
from apps.tournaments.models.game_config import (
    BRScoringMatrix,
    GameMatchConfig,
    MapPoolEntry,
    MatchVetoSession,
    RulebookConsent,
    RulebookVersion,
    ServerRegion,
)
from apps.tournaments.models.payment_config import TournamentPaymentMethod

logger = logging.getLogger("toc.settings")


class TOCSettingsService:
    """All read/write operations for the Settings & Config tab."""

    CATEGORY_LABELS = {
        "FPS": "First-Person Shooter",
        "MOBA": "MOBA",
        "BR": "Battle Royale",
        "SPORTS": "Sports Simulation",
        "FIGHTING": "Fighting",
        "STRATEGY": "Strategy",
        "CCG": "Card Game",
        "OTHER": "Other",
    }

    GAME_TYPE_LABELS = {
        "TEAM_VS_TEAM": "Team vs Team",
        "1V1": "1 vs 1",
        "BATTLE_ROYALE": "Battle Royale",
        "FREE_FOR_ALL": "Free For All",
    }

    # ------------------------------------------------------------------
    # Registration Form Configuration
    # ------------------------------------------------------------------

    @staticmethod
    def get_form_configuration(tournament: Tournament) -> dict:
        cfg = TournamentFormConfiguration.get_or_create_for_tournament(tournament)
        game_context = TOCSettingsService._get_form_config_game_context(tournament)
        return {
            "id": cfg.id,
            "form_type": cfg.form_type,
            "enable_age_field": cfg.enable_age_field,
            "enable_country_field": cfg.enable_country_field,
            "enable_platform_field": cfg.enable_platform_field,
            "enable_rank_field": cfg.enable_rank_field,
            "enable_phone_field": cfg.enable_phone_field,
            "enable_discord_field": cfg.enable_discord_field,
            "enable_preferred_contact_field": cfg.enable_preferred_contact_field,
            "enable_team_logo_upload": cfg.enable_team_logo_upload,
            "enable_team_banner_upload": cfg.enable_team_banner_upload,
            "enable_team_bio": cfg.enable_team_bio,
            "enable_captain_whatsapp_field": cfg.enable_captain_whatsapp_field,
            "enable_captain_phone_field": cfg.enable_captain_phone_field,
            "enable_captain_discord_field": cfg.enable_captain_discord_field,
            "enable_payment_mobile_number_field": cfg.enable_payment_mobile_number_field,
            "enable_payment_screenshot_field": cfg.enable_payment_screenshot_field,
            "enable_payment_notes_field": cfg.enable_payment_notes_field,
            "enable_preferred_communication": cfg.enable_preferred_communication,
            "communication_channels": cfg.get_communication_channels(),
            "game_context": game_context,
            "smart_recommendations": TOCSettingsService._build_form_config_recommendations(
                tournament,
                game_context,
            ),
            "updated_at": cfg.updated_at.isoformat() if getattr(cfg, "updated_at", None) else None,
        }

    @staticmethod
    def _get_form_config_game_context(tournament: Tournament) -> dict:
        game = getattr(tournament, "game", None)
        if not game:
            return {}

        identity_fields = []
        try:
            identity_fields = list(
                game.identity_configs.order_by("order", "id").values(
                    "field_name",
                    "display_name",
                    "is_required",
                    "placeholder",
                    "help_text",
                )
            )
        except Exception:
            logger.exception("Failed to load game identity config for tournament=%s", tournament.id)

        return {
            "name": game.name,
            "display_name": game.display_name,
            "slug": game.slug,
            "category": game.category,
            "category_label": TOCSettingsService.CATEGORY_LABELS.get(game.category, game.category),
            "game_type": game.game_type,
            "game_type_label": TOCSettingsService.GAME_TYPE_LABELS.get(game.game_type, game.game_type),
            "platforms": game.platforms or [],
            "has_servers": bool(game.has_servers),
            "has_rank_system": bool(game.has_rank_system),
            "available_rank_count": len(game.available_ranks or []),
            "is_passport_supported": bool(getattr(game, "is_passport_supported", False)),
            "game_id_label": getattr(game, "game_id_label", "") or "Game ID",
            "game_id_placeholder": getattr(game, "game_id_placeholder", "") or "Enter your in-game identifier",
            "identity_fields": identity_fields,
        }

    @staticmethod
    def _build_form_config_recommendations(tournament: Tournament, game_context: dict) -> list[dict[str, Any]]:
        recommendations: list[dict[str, Any]] = []
        platforms = game_context.get("platforms") or []

        if game_context.get("game_type") in {"TEAM_VS_TEAM", "BATTLE_ROYALE"}:
            recommendations.append(
                {
                    "id": "team_competitive",
                    "title": "Team Competitive Blueprint",
                    "summary": "Prepare structured team intake with coordinator reliability.",
                    "reason": "Your game format often requires captain communication and team assets.",
                    "changes": {
                        "form_type": "default_team",
                        "enable_team_logo_upload": True,
                        "enable_team_bio": True,
                        "enable_captain_whatsapp_field": True,
                        "enable_captain_phone_field": True,
                        "enable_captain_discord_field": True,
                        "enable_preferred_communication": True,
                    },
                    "channels": [
                        {"key": "discord", "label": "Discord", "placeholder": "discord.gg/yourserver", "required": True},
                        {"key": "whatsapp", "label": "WhatsApp", "placeholder": "+8801XXXXXXXXX", "required": False},
                    ],
                }
            )

        if game_context.get("has_rank_system"):
            recommendations.append(
                {
                    "id": "ranked_verification",
                    "title": "Ranked Validation Layer",
                    "summary": "Collect rank signal for seeding and fair matchmaking.",
                    "reason": "This game has a rank ecosystem. Rank data improves bracket quality.",
                    "changes": {
                        "enable_rank_field": True,
                        "enable_platform_field": True,
                        "enable_country_field": True,
                    },
                    "channels": [],
                }
            )

        if game_context.get("has_servers") or len(platforms) > 1:
            recommendations.append(
                {
                    "id": "region_readiness",
                    "title": "Server & Region Readiness",
                    "summary": "Capture platform/server context to reduce scheduling friction.",
                    "reason": "Multi-platform or server-sensitive games need region-aware enrollment.",
                    "changes": {
                        "enable_platform_field": True,
                        "enable_country_field": True,
                        "enable_preferred_contact_field": True,
                    },
                    "channels": [
                        {"key": "telegram", "label": "Telegram", "placeholder": "@team_handle", "required": False},
                    ],
                }
            )

        if bool(getattr(tournament, "has_entry_fee", False)):
            recommendations.append(
                {
                    "id": "payment_proof_strict",
                    "title": "Payment Verification Safety",
                    "summary": "Add mandatory payment evidence to reduce manual disputes.",
                    "reason": "Entry-fee tournaments benefit from structured proof fields.",
                    "changes": {
                        "enable_payment_mobile_number_field": True,
                        "enable_payment_screenshot_field": True,
                        "enable_payment_notes_field": True,
                    },
                    "channels": [],
                }
            )

        if game_context.get("is_passport_supported"):
            recommendations.append(
                {
                    "id": "passport_ready",
                    "title": "Passport-Ready Identity",
                    "summary": "Guide players toward immutable contact and identity signals.",
                    "reason": "Game Passport support benefits from consistent player verification metadata.",
                    "changes": {
                        "enable_discord_field": True,
                        "enable_phone_field": True,
                        "enable_preferred_contact_field": True,
                    },
                    "channels": [
                        {"key": "email", "label": "Email", "placeholder": "name@example.com", "required": True},
                    ],
                }
            )

        return recommendations[:5]

    @staticmethod
    def update_form_configuration(tournament: Tournament, data: dict) -> dict:
        cfg = TournamentFormConfiguration.get_or_create_for_tournament(tournament)

        bool_fields = {
            "enable_age_field",
            "enable_country_field",
            "enable_platform_field",
            "enable_rank_field",
            "enable_phone_field",
            "enable_discord_field",
            "enable_preferred_contact_field",
            "enable_team_logo_upload",
            "enable_team_banner_upload",
            "enable_team_bio",
            "enable_captain_whatsapp_field",
            "enable_captain_phone_field",
            "enable_captain_discord_field",
            "enable_payment_mobile_number_field",
            "enable_payment_screenshot_field",
            "enable_payment_notes_field",
            "enable_preferred_communication",
        }
        changed = []

        for field in bool_fields:
            if field in data and hasattr(cfg, field):
                setattr(cfg, field, bool(data.get(field)))
                changed.append(field)

        if "form_type" in data:
            form_type = str(data.get("form_type") or "").strip()
            valid_form_types = {choice[0] for choice in TournamentFormConfiguration.FORM_TYPE_CHOICES}
            if form_type and form_type in valid_form_types:
                cfg.form_type = form_type
                changed.append("form_type")

        if "communication_channels" in data:
            raw_channels = data.get("communication_channels")
            if not isinstance(raw_channels, list):
                return {"error": "communication_channels must be an array."}

            normalized_channels = []
            seen_keys = set()
            for item in raw_channels:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key") or "").strip().lower().replace(" ", "_")
                label = str(item.get("label") or "").strip()
                if not key or not label:
                    continue
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                normalized_channels.append({
                    "key": key,
                    "label": label,
                    "placeholder": str(item.get("placeholder") or label).strip(),
                    "icon": str(item.get("icon") or "circle").strip(),
                    "required": bool(item.get("required")),
                    "type": str(item.get("type") or "text").strip() or "text",
                })

            cfg.communication_channels = normalized_channels
            changed.append("communication_channels")

        if changed:
            cfg.save(update_fields=sorted(set(changed + ["updated_at"])))

        return {
            "updated_fields": sorted(set(changed)),
            "configuration": TOCSettingsService.get_form_configuration(tournament),
        }

    # ------------------------------------------------------------------
    # Tournament Settings (basic info)
    # ------------------------------------------------------------------

    @staticmethod
    def get_settings(tournament: Tournament) -> dict:
        """Return editable tournament fields grouped by section (1:1 model parity)."""
        t = tournament
        return {
            "_meta": {
                "settings_version": t.updated_at.isoformat() if getattr(t, "updated_at", None) else None,
            },
            "basic": {
                "name": t.name,
                "slug": t.slug,
                "description": t.description or "",
                "status": t.status,
                "is_official": getattr(t, "is_official", False),
                "is_featured": getattr(t, "is_featured", False),
            },
            "media": {
                "banner_image": t.banner_image.url if getattr(t, "banner_image", None) and t.banner_image else "",
                "thumbnail_image": t.thumbnail_image.url if getattr(t, "thumbnail_image", None) and t.thumbnail_image else "",
                "promo_video_url": getattr(t, "promo_video_url", "") or "",
                "stream_twitch_url": getattr(t, "stream_twitch_url", "") or "",
                "stream_youtube_url": getattr(t, "stream_youtube_url", "") or "",
            },
            "format": {
                "format": t.format,
                "participation_type": getattr(t, "participation_type", ""),
                "platform": getattr(t, "platform", ""),
                "mode": getattr(t, "mode", "online"),
                "max_participants": t.max_participants,
                "min_participants": getattr(t, "min_participants", 0),
                "max_guest_teams": getattr(t, "max_guest_teams", 0),
                "allow_display_name_override": getattr(t, "allow_display_name_override", False),
            },
            "dates": {
                "registration_start": (
                    t.registration_start.isoformat() if t.registration_start else None
                ),
                "registration_end": (
                    t.registration_end.isoformat() if t.registration_end else None
                ),
                "tournament_start": (
                    t.tournament_start.isoformat() if t.tournament_start else None
                ),
                "tournament_end": (
                    t.tournament_end.isoformat() if t.tournament_end else None
                ),
                "timezone_name": getattr(t, "timezone_name", "Asia/Dhaka") or "Asia/Dhaka",
            },
            "venue": {
                "venue_name": getattr(t, "venue_name", "") or "",
                "venue_city": getattr(t, "venue_city", "") or "",
                "venue_address": getattr(t, "venue_address", "") or "",
                "venue_map_url": getattr(t, "venue_map_url", "") or "",
            },
            "fees": {
                "has_entry_fee": getattr(t, "has_entry_fee", False),
                "entry_fee_amount": str(getattr(t, "entry_fee_amount", 0)),
                "entry_fee_currency": getattr(t, "entry_fee_currency", "BDT"),
                "entry_fee_deltacoin": str(getattr(t, "entry_fee_deltacoin", 0)),
                "payment_deadline_hours": getattr(t, "payment_deadline_hours", 24),
                "refund_policy": getattr(t, "refund_policy", ""),
                "refund_policy_text": getattr(t, "refund_policy_text", "") or "",
                "enable_fee_waiver": getattr(t, "enable_fee_waiver", False),
                "fee_waiver_top_n_teams": getattr(t, "fee_waiver_top_n_teams", 0),
            },
            "prizes": {
                "prize_pool": str(t.prize_pool) if t.prize_pool else "0",
                "prize_currency": getattr(t, "prize_currency", "USD"),
                "prize_deltacoin": str(getattr(t, "prize_deltacoin", 0)),
                "prize_distribution": getattr(t, "prize_distribution", {}),
            },
            "rules": {
                "rules_text": getattr(t, "rules_text", "") or "",
                "terms_and_conditions": getattr(t, "terms_and_conditions", "") or "",
                "require_terms_acceptance": getattr(t, "require_terms_acceptance", False),
                "rules_pdf": t.rules_pdf.url if getattr(t, "rules_pdf", None) and t.rules_pdf else "",
                "terms_pdf": t.terms_pdf.url if getattr(t, "terms_pdf", None) and t.terms_pdf else "",
            },
            "features": {
                "enable_check_in": getattr(t, "enable_check_in", False),
                "check_in_minutes_before": getattr(t, "check_in_minutes_before", 30),
                "check_in_closes_minutes_before": getattr(t, "check_in_closes_minutes_before", 0),
                "enable_dynamic_seeding": getattr(t, "enable_dynamic_seeding", False),
                "enable_live_updates": getattr(t, "enable_live_updates", False),
                "enable_certificates": getattr(t, "enable_certificates", False),
                "enable_challenges": getattr(t, "enable_challenges", False),
                "enable_fan_voting": getattr(t, "enable_fan_voting", False),
            },
            "social": {
                "contact_email": getattr(t, "contact_email", ""),
                "contact_phone": getattr(t, "contact_phone", ""),
                "social_discord": getattr(t, "social_discord", ""),
                "discord_webhook_url": getattr(t, "discord_webhook_url", ""),
                "social_twitter": getattr(t, "social_twitter", ""),
                "social_instagram": getattr(t, "social_instagram", ""),
                "social_youtube": getattr(t, "social_youtube", ""),
                "social_website": getattr(t, "social_website", ""),
                "social_facebook": getattr(t, "social_facebook", ""),
                "social_tiktok": getattr(t, "social_tiktok", ""),
                "support_info": getattr(t, "support_info", ""),
            },
            "waitlist": {
                "auto_forfeit_no_shows": getattr(t, "auto_forfeit_no_shows", False),
                "waitlist_auto_promote": getattr(t, "waitlist_auto_promote", False),
                "enable_no_show_timer": getattr(t, "enable_no_show_timer", False),
                "no_show_timeout_minutes": getattr(t, "no_show_timeout_minutes", 10),
                "max_waitlist_size": getattr(t, "max_waitlist_size", 0),
            },
            "seo": {
                "meta_description": getattr(t, "meta_description", "") or "",
                "meta_keywords": getattr(t, "meta_keywords", []) or [],
            },
        }

    @staticmethod
    def update_settings(tournament: Tournament, data: dict, expected_settings_version: str | None = None) -> dict:
        """Flat-merge provided fields into the Tournament model with structured validation."""
        updatable = {
            # Basic
            "name", "description", "status", "is_official", "is_featured",
            # Format
            "format", "participation_type", "platform", "mode",
            "max_participants", "min_participants",
            "max_guest_teams", "allow_display_name_override",
            # Dates
            "registration_start", "registration_end",
            "tournament_start", "tournament_end",
            "timezone_name",
            # Venue
            "venue_name", "venue_city", "venue_address", "venue_map_url",
            # Fees
            "has_entry_fee", "entry_fee_amount", "entry_fee_currency",
            "entry_fee_deltacoin", "payment_deadline_hours",
            "refund_policy", "refund_policy_text",
            "enable_fee_waiver", "fee_waiver_top_n_teams",
            # Prizes
            "prize_pool", "prize_currency", "prize_deltacoin", "prize_distribution",
            # Rules
            "rules_text", "terms_and_conditions", "require_terms_acceptance",
            # Features
            "enable_check_in", "check_in_minutes_before", "check_in_closes_minutes_before",
            "enable_dynamic_seeding", "enable_live_updates", "enable_certificates",
            "enable_challenges", "enable_fan_voting",
            # Media (text URLs only; file uploads via separate endpoint)
            "promo_video_url", "stream_twitch_url", "stream_youtube_url",
            # Social & Contact
            "contact_email", "contact_phone",
            "social_discord", "discord_webhook_url", "social_twitter",
            "social_instagram", "social_youtube", "social_website",
            "social_facebook", "social_tiktok", "support_info",
            # Waitlist
            "auto_forfeit_no_shows", "waitlist_auto_promote",
            "enable_no_show_timer", "no_show_timeout_minutes", "max_waitlist_size",
            # SEO
            "meta_description", "meta_keywords",
        }

        if expected_settings_version is not None:
            parsed_expected = parse_datetime(str(expected_settings_version)) if expected_settings_version else None
            if parsed_expected is None:
                return {
                    "error": {
                        "type": "validation",
                        "code": "settings_validation_failed",
                        "message": "Please fix the highlighted settings fields and try again.",
                        "fields": {
                            "settings_version": ["Settings version is invalid. Refresh and try again."],
                        },
                        "sections": {},
                    }
                }

            current_version = getattr(tournament, "updated_at", None)
            if current_version:
                delta_seconds = abs((current_version - parsed_expected).total_seconds())
                if delta_seconds > 0.001:
                    return {
                        "error": {
                            "type": "conflict",
                            "code": "settings_version_conflict",
                            "message": "Settings changed elsewhere. Refresh and apply your changes again.",
                            "server_settings_version": current_version.isoformat(),
                        }
                    }

        field_errors, section_errors = TOCSettingsService._validate_settings_payload(data)
        if field_errors or section_errors:
            return {
                "error": {
                    "type": "validation",
                    "code": "settings_validation_failed",
                    "message": "Please fix the highlighted settings fields and try again.",
                    "fields": field_errors,
                    "sections": section_errors,
                }
            }

        changed: list[str] = []
        for key, value in data.items():
            if key in updatable and hasattr(tournament, key):
                setattr(tournament, key, value)
                changed.append(key)
        if changed:
            tournament.save(update_fields=changed + ["updated_at"] if hasattr(tournament, "updated_at") else changed)

        current_version = getattr(tournament, "updated_at", None)
        return {
            "updated_fields": changed,
            "settings_version": current_version.isoformat() if current_version else None,
        }

    @staticmethod
    def _validate_settings_payload(data: dict) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        field_errors: dict[str, list[str]] = {}
        section_errors: dict[str, list[str]] = {}

        def add_field_error(field: str, message: str) -> None:
            field_errors.setdefault(field, []).append(message)

        def add_section_error(section: str, message: str) -> None:
            section_errors.setdefault(section, []).append(message)

        def _as_int(value: Any) -> int | None:
            if value is None or value == "":
                return None
            try:
                return int(value)
            except (TypeError, ValueError):
                return None

        def _as_float(value: Any) -> float | None:
            if value is None or value == "":
                return None
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        name = data.get("name")
        if name is not None:
            if not str(name).strip():
                add_field_error("name", "Tournament name is required.")
            elif len(str(name).strip()) > 255:
                add_field_error("name", "Tournament name must be 255 characters or fewer.")

        max_participants = _as_int(data.get("max_participants"))
        min_participants = _as_int(data.get("min_participants"))
        if "max_participants" in data:
            if max_participants is None:
                add_field_error("max_participants", "Max participants must be a number.")
            elif max_participants < 2:
                add_field_error("max_participants", "Max participants must be at least 2.")

        if "min_participants" in data:
            if min_participants is None:
                add_field_error("min_participants", "Min participants must be a number.")
            elif min_participants < 0:
                add_field_error("min_participants", "Min participants cannot be negative.")

        if max_participants is not None and min_participants is not None and min_participants > max_participants:
            add_field_error("min_participants", "Min participants cannot exceed max participants.")
            add_section_error("settings-format", "Participant limits are inconsistent.")

        max_guest_teams = _as_int(data.get("max_guest_teams"))
        if "max_guest_teams" in data:
            if max_guest_teams is None:
                add_field_error("max_guest_teams", "Max guest teams must be a number.")
            elif max_guest_teams < 0:
                add_field_error("max_guest_teams", "Max guest teams cannot be negative.")

        if data.get("contact_email"):
            try:
                validate_email(data["contact_email"])
            except DjangoValidationError:
                add_field_error("contact_email", "Enter a valid email address.")

        url_fields = (
            "promo_video_url",
            "stream_twitch_url",
            "stream_youtube_url",
            "venue_map_url",
            "social_discord",
            "discord_webhook_url",
            "social_facebook",
            "social_tiktok",
            "social_instagram",
            "social_youtube",
            "social_website",
        )
        url_validator = URLValidator(schemes=["http", "https"])
        for field in url_fields:
            value = data.get(field)
            if not value:
                continue
            try:
                url_validator(str(value))
            except DjangoValidationError:
                add_field_error(field, "Enter a valid URL starting with http:// or https://.")

        timezone_name = data.get("timezone_name")
        if timezone_name:
            try:
                ZoneInfo(str(timezone_name))
            except ZoneInfoNotFoundError:
                add_field_error("timezone_name", "Select a valid timezone.")

        registration_start = parse_datetime(str(data.get("registration_start"))) if data.get("registration_start") else None
        registration_end = parse_datetime(str(data.get("registration_end"))) if data.get("registration_end") else None
        tournament_start = parse_datetime(str(data.get("tournament_start"))) if data.get("tournament_start") else None
        tournament_end = parse_datetime(str(data.get("tournament_end"))) if data.get("tournament_end") else None

        if data.get("registration_start") and registration_start is None:
            add_field_error("registration_start", "Registration start must be a valid datetime.")
        if data.get("registration_end") and registration_end is None:
            add_field_error("registration_end", "Registration end must be a valid datetime.")
        if data.get("tournament_start") and tournament_start is None:
            add_field_error("tournament_start", "Tournament start must be a valid datetime.")
        if data.get("tournament_end") and tournament_end is None:
            add_field_error("tournament_end", "Tournament end must be a valid datetime.")

        if registration_start and registration_end and registration_end < registration_start:
            add_field_error("registration_end", "Registration end cannot be before registration start.")
            add_section_error("settings-dates", "Registration dates are out of order.")
        if tournament_start and tournament_end and tournament_end < tournament_start:
            add_field_error("tournament_end", "Tournament end cannot be before tournament start.")
            add_section_error("settings-dates", "Tournament dates are out of order.")
        if registration_end and tournament_start and registration_end > tournament_start:
            add_field_error("registration_end", "Registration should close on or before tournament start.")
            add_section_error("settings-dates", "Registration closes after tournament start.")

        payment_deadline_hours = _as_int(data.get("payment_deadline_hours"))
        if "payment_deadline_hours" in data:
            if payment_deadline_hours is None:
                add_field_error("payment_deadline_hours", "Payment deadline must be a number of hours.")
            elif payment_deadline_hours < 0:
                add_field_error("payment_deadline_hours", "Payment deadline cannot be negative.")

        fee_waiver_top_n = _as_int(data.get("fee_waiver_top_n_teams"))
        if "fee_waiver_top_n_teams" in data:
            if fee_waiver_top_n is None:
                add_field_error("fee_waiver_top_n_teams", "Fee waiver value must be a number.")
            elif fee_waiver_top_n < 0:
                add_field_error("fee_waiver_top_n_teams", "Fee waiver value cannot be negative.")
            elif max_participants is not None and fee_waiver_top_n > max_participants:
                add_field_error("fee_waiver_top_n_teams", "Fee waiver teams cannot exceed max participants.")

        entry_fee_amount = _as_float(data.get("entry_fee_amount"))
        if data.get("has_entry_fee") is True:
            if entry_fee_amount is None:
                add_field_error("entry_fee_amount", "Entry fee amount is required when entry fee is enabled.")
            elif entry_fee_amount < 0:
                add_field_error("entry_fee_amount", "Entry fee amount cannot be negative.")

        no_show_timeout_minutes = _as_int(data.get("no_show_timeout_minutes"))
        max_waitlist_size = _as_int(data.get("max_waitlist_size"))
        if "no_show_timeout_minutes" in data and no_show_timeout_minutes is None:
            add_field_error("no_show_timeout_minutes", "No-show timeout must be a number.")
        if "max_waitlist_size" in data:
            if max_waitlist_size is None:
                add_field_error("max_waitlist_size", "Max waitlist size must be a number.")
            elif max_waitlist_size < 0:
                add_field_error("max_waitlist_size", "Max waitlist size cannot be negative.")

        if data.get("enable_no_show_timer") is True:
            if no_show_timeout_minutes is None or no_show_timeout_minutes < 1:
                add_field_error("no_show_timeout_minutes", "No-show timeout must be at least 1 minute when timer is enabled.")
                add_section_error("settings-waitlist", "No-show timer is enabled but timeout is invalid.")

        meta_keywords = data.get("meta_keywords")
        if meta_keywords is not None and not isinstance(meta_keywords, list):
            add_field_error("meta_keywords", "Meta keywords must be an array of strings.")

        return field_errors, section_errors

    # ------------------------------------------------------------------
    # Game Match Config
    # ------------------------------------------------------------------

    @staticmethod
    def get_game_config(tournament: Tournament) -> dict | None:
        try:
            cfg = tournament.game_match_config
        except GameMatchConfig.DoesNotExist:
            return None
        ms = cfg.match_settings or {}
        return {
            "id": str(cfg.id),
            "game_id": cfg.game_id,
            "default_match_format": cfg.default_match_format,
            "scoring_rules": cfg.scoring_rules,
            "match_settings": ms,
            "enable_veto": cfg.enable_veto,
            "veto_type": cfg.veto_type,
            "veto_sequence": ms.get("veto_sequence", []),
        }

    @staticmethod
    def save_game_config(tournament: Tournament, data: dict) -> dict:
        match_settings = data.get("match_settings", {})
        if not isinstance(match_settings, dict):
            match_settings = {}
        # Merge veto_sequence into match_settings if provided separately
        if "veto_sequence" in data:
            match_settings["veto_sequence"] = data["veto_sequence"]
        cfg, created = GameMatchConfig.objects.update_or_create(
            tournament=tournament,
            defaults={
                "game_id": data.get("game_id"),
                "default_match_format": data.get("default_match_format", "bo1"),
                "scoring_rules": data.get("scoring_rules", {}),
                "match_settings": match_settings,
                "enable_veto": data.get("enable_veto", False),
                "veto_type": data.get("veto_type", "standard"),
            },
        )
        return {"id": str(cfg.id), "created": created}

    # ------------------------------------------------------------------
    # Map Pool
    # ------------------------------------------------------------------

    @staticmethod
    def get_map_pool(tournament: Tournament) -> list[dict]:
        try:
            cfg = tournament.game_match_config
        except GameMatchConfig.DoesNotExist:
            return []
        return list(
            cfg.map_pool.values("id", "map_name", "map_code", "image", "is_active", "order")
            .order_by("order", "map_name")
        )

    @staticmethod
    def add_map(tournament: Tournament, data: dict) -> dict:
        cfg, _ = GameMatchConfig.objects.get_or_create(tournament=tournament)
        highest = cfg.map_pool.order_by("-order").values_list("order", flat=True).first() or 0
        entry = MapPoolEntry.objects.create(
            config=cfg,
            map_name=data["map_name"],
            map_code=data.get("map_code", ""),
            image=data.get("image", ""),
            is_active=data.get("is_active", True),
            order=data.get("order", highest + 1),
        )
        return {"id": str(entry.id), "map_name": entry.map_name}

    @staticmethod
    def update_map(map_id: str, data: dict) -> dict:
        entry = MapPoolEntry.objects.get(pk=map_id)
        for field in ("map_name", "map_code", "image", "is_active", "order"):
            if field in data:
                setattr(entry, field, data[field])
        entry.save()
        return {"id": str(entry.id)}

    @staticmethod
    def delete_map(map_id: str) -> dict:
        MapPoolEntry.objects.filter(pk=map_id).delete()
        return {"deleted": True}

    @staticmethod
    def reorder_maps(tournament: Tournament, ordered_ids: list[str]) -> dict:
        """Bulk-reorder map pool by list of IDs in desired order."""
        try:
            cfg = tournament.game_match_config
        except GameMatchConfig.DoesNotExist:
            return {"error": "No game config"}
        with transaction.atomic():
            for idx, mid in enumerate(ordered_ids):
                cfg.map_pool.filter(pk=mid).update(order=idx)
        return {"reordered": len(ordered_ids)}

    # ------------------------------------------------------------------
    # Veto Sessions
    # ------------------------------------------------------------------

    @staticmethod
    def get_veto_session(match_id: str) -> dict | None:
        try:
            vs = MatchVetoSession.objects.get(match_id=match_id)
        except MatchVetoSession.DoesNotExist:
            return None
        return {
            "id": str(vs.id),
            "match_id": str(vs.match_id),
            "veto_type": vs.veto_type,
            "sequence": vs.sequence,
            "picks": vs.picks,
            "current_step": vs.current_step,
            "status": vs.status,
        }

    @staticmethod
    def create_veto_session(match_id: str, data: dict) -> dict:
        vs, created = MatchVetoSession.objects.update_or_create(
            match_id=match_id,
            defaults={
                "veto_type": data.get("veto_type", "standard"),
                "sequence": data.get("sequence", []),
                "picks": [],
                "current_step": 0,
                "status": "pending",
            },
        )
        return {"id": str(vs.id), "created": created}

    @staticmethod
    def advance_veto(match_id: str, pick_data: dict) -> dict:
        """Record a pick/ban and advance the veto session."""
        vs = MatchVetoSession.objects.get(match_id=match_id)
        if vs.status == "completed":
            return {"error": "Veto already completed"}
        picks = vs.picks or []
        picks.append({
            "step": vs.current_step,
            **pick_data,
        })
        vs.picks = picks
        vs.current_step += 1
        if vs.current_step >= len(vs.sequence or []):
            vs.status = "completed"
            vs.completed_at = timezone.now()
        else:
            vs.status = "in_progress"
            if not vs.started_at:
                vs.started_at = timezone.now()
        vs.save()
        return {"current_step": vs.current_step, "status": vs.status, "picks": vs.picks}

    # ------------------------------------------------------------------
    # Server Regions
    # ------------------------------------------------------------------

    @staticmethod
    def get_regions(tournament: Tournament) -> list[dict]:
        return list(
            ServerRegion.objects.filter(tournament=tournament)
            .values("id", "name", "code", "ping_endpoint", "is_active")
            .order_by("name")
        )

    @staticmethod
    def save_region(tournament: Tournament, data: dict) -> dict:
        region_id = data.get("id")
        if region_id:
            ServerRegion.objects.filter(pk=region_id, tournament=tournament).update(
                name=data.get("name", ""),
                code=data.get("code", ""),
                ping_endpoint=data.get("ping_endpoint", ""),
                is_active=data.get("is_active", True),
            )
            return {"id": region_id, "updated": True}
        region = ServerRegion.objects.create(
            tournament=tournament,
            name=data["name"],
            code=data["code"],
            ping_endpoint=data.get("ping_endpoint", ""),
            is_active=data.get("is_active", True),
        )
        return {"id": str(region.id), "created": True}

    @staticmethod
    def delete_region(region_id: str) -> dict:
        ServerRegion.objects.filter(pk=region_id).delete()
        return {"deleted": True}

    # ------------------------------------------------------------------
    # Rulebook Versioning
    # ------------------------------------------------------------------

    @staticmethod
    def get_rulebook_versions(tournament: Tournament) -> list[dict]:
        return list(
            RulebookVersion.objects.filter(tournament=tournament)
            .values(
                "id", "version", "content", "changelog",
                "is_active", "published_at", "created_at",
            )
            .order_by("-created_at")
        )

    @staticmethod
    def create_rulebook_version(tournament: Tournament, data: dict, user=None) -> dict:
        rv = RulebookVersion.objects.create(
            tournament=tournament,
            version=data["version"],
            content=data.get("content", ""),
            changelog=data.get("changelog", ""),
            created_by=user,
        )
        return {"id": str(rv.id), "version": rv.version}

    @staticmethod
    def update_rulebook_version(version_id: str, data: dict) -> dict:
        rv = RulebookVersion.objects.get(pk=version_id)
        for field in ("content", "changelog", "version"):
            if field in data:
                setattr(rv, field, data[field])
        rv.save()
        return {"id": str(rv.id)}

    @staticmethod
    def publish_rulebook(version_id: str) -> dict:
        rv = RulebookVersion.objects.get(pk=version_id)
        rv.publish()
        return {"id": str(rv.id), "published_at": rv.published_at.isoformat()}

    @staticmethod
    def get_consent_count(version_id: str) -> int:
        return RulebookConsent.objects.filter(rulebook_version_id=version_id).count()

    # ------------------------------------------------------------------
    # BR Scoring Matrix
    # ------------------------------------------------------------------

    @staticmethod
    def get_br_scoring(tournament: Tournament) -> dict | None:
        try:
            cfg = tournament.game_match_config
            matrix = cfg.br_scoring
        except (GameMatchConfig.DoesNotExist, BRScoringMatrix.DoesNotExist):
            return None
        return {
            "id": str(matrix.id),
            "placement_points": matrix.placement_points,
            "kill_points": str(matrix.kill_points),
            "tiebreaker_rules": matrix.tiebreaker_rules,
        }

    @staticmethod
    def save_br_scoring(tournament: Tournament, data: dict) -> dict:
        cfg, _ = GameMatchConfig.objects.get_or_create(tournament=tournament)
        matrix, created = BRScoringMatrix.objects.update_or_create(
            config=cfg,
            defaults={
                "placement_points": data.get("placement_points", {}),
                "kill_points": data.get("kill_points", 1),
                "tiebreaker_rules": data.get("tiebreaker_rules", []),
            },
        )
        return {"id": str(matrix.id), "created": created}

    # ------------------------------------------------------------------
    # Payment Methods (TournamentPaymentMethod CRUD)
    # ------------------------------------------------------------------

    @staticmethod
    def get_payment_methods(tournament: Tournament) -> list[dict]:
        """Return all payment methods for the tournament."""
        methods = TournamentPaymentMethod.objects.filter(
            tournament=tournament
        ).order_by("display_order", "method")
        result = []
        for m in methods:
            entry = {
                "id": m.id,
                "method": m.method,
                "is_enabled": m.is_enabled,
                "display_order": m.display_order,
                "account_number": m.get_account_number(),
                "instructions": m.get_instructions(),
            }
            # Add provider-specific fields
            if m.method in ("bkash", "nagad", "rocket"):
                prefix = m.method
                entry.update({
                    f"{prefix}_account_number": getattr(m, f"{prefix}_account_number", ""),
                    f"{prefix}_account_name": getattr(m, f"{prefix}_account_name", ""),
                    f"{prefix}_account_type": getattr(m, f"{prefix}_account_type", "personal"),
                    f"{prefix}_instructions": getattr(m, f"{prefix}_instructions", ""),
                    f"{prefix}_reference_required": getattr(m, f"{prefix}_reference_required", True),
                })
            elif m.method == "bank_transfer":
                entry.update({
                    "bank_name": m.bank_name,
                    "bank_branch": m.bank_branch,
                    "bank_account_number": m.bank_account_number,
                    "bank_account_name": m.bank_account_name,
                    "bank_routing_number": m.bank_routing_number,
                    "bank_swift_code": m.bank_swift_code,
                    "bank_instructions": m.bank_instructions,
                    "bank_reference_required": m.bank_reference_required,
                })
            elif m.method == "deltacoin":
                entry["deltacoin_instructions"] = m.deltacoin_instructions
            result.append(entry)
        return result

    @staticmethod
    def add_payment_method(tournament: Tournament, data: dict) -> dict:
        """Create a new payment method for the tournament."""
        method = data.get("method", "deltacoin")
        # Get next display order
        highest = (
            TournamentPaymentMethod.objects.filter(tournament=tournament)
            .order_by("-display_order")
            .values_list("display_order", flat=True)
            .first()
        ) or 0
        kwargs = {
            "tournament": tournament,
            "method": method,
            "is_enabled": data.get("is_enabled", True),
            "display_order": highest + 1,
        }
        # Provider-specific fields
        if method in ("bkash", "nagad", "rocket"):
            for suffix in ("account_number", "account_name", "account_type", "instructions", "reference_required"):
                key = f"{method}_{suffix}"
                if key in data:
                    kwargs[key] = data[key]
        elif method == "bank_transfer":
            for field in ("bank_name", "bank_branch", "bank_account_number",
                          "bank_account_name", "bank_routing_number", "bank_swift_code",
                          "bank_instructions", "bank_reference_required"):
                if field in data:
                    kwargs[field] = data[field]
        elif method == "deltacoin":
            if "deltacoin_instructions" in data:
                kwargs["deltacoin_instructions"] = data["deltacoin_instructions"]

        pm = TournamentPaymentMethod.objects.create(**kwargs)
        return {"id": pm.id, "method": pm.method}

    @staticmethod
    def update_payment_method(tournament: Tournament, payment_method_id: int, data: dict) -> dict:
        """Update an existing payment method for the tournament."""
        try:
            pm = TournamentPaymentMethod.objects.get(pk=payment_method_id, tournament=tournament)
        except TournamentPaymentMethod.DoesNotExist:
            return {"error": "Payment method not found."}

        updatable = {"is_enabled", "display_order"}

        if pm.method in ("bkash", "nagad", "rocket"):
            prefix = pm.method
            updatable.update({
                f"{prefix}_account_number",
                f"{prefix}_account_name",
                f"{prefix}_account_type",
                f"{prefix}_instructions",
                f"{prefix}_reference_required",
            })
        elif pm.method == "bank_transfer":
            updatable.update({
                "bank_name",
                "bank_branch",
                "bank_account_number",
                "bank_account_name",
                "bank_routing_number",
                "bank_swift_code",
                "bank_instructions",
                "bank_reference_required",
            })
        elif pm.method == "deltacoin":
            updatable.add("deltacoin_instructions")

        changed = []
        for key, value in data.items():
            if key in updatable and hasattr(pm, key):
                setattr(pm, key, value)
                changed.append(key)

        if changed:
            pm.save(update_fields=changed + ["updated_at"])

        return {"id": pm.id, "method": pm.method, "updated_fields": changed}

    @staticmethod
    def delete_payment_method(payment_method_id: int) -> dict:
        """Delete a payment method."""
        TournamentPaymentMethod.objects.filter(pk=payment_method_id).delete()
        return {"deleted": True}

    # ------------------------------------------------------------------
    # File Upload (banner_image, thumbnail_image, rules_pdf, terms_pdf)
    # ------------------------------------------------------------------

    @staticmethod
    def upload_file(tournament: Tournament, field_name: str, uploaded_file) -> dict:
        """Save an uploaded file to the specified ImageField/FileField on the tournament."""
        allowed_fields = {"banner_image", "thumbnail_image", "rules_pdf", "terms_pdf"}
        if field_name not in allowed_fields:
            return {"error": f"Field '{field_name}' is not an allowed upload target."}
        if not hasattr(tournament, field_name):
            return {"error": f"Tournament model has no field '{field_name}'."}

        file_field = getattr(tournament, field_name)
        file_field.save(uploaded_file.name, uploaded_file, save=True)

        return {
            "field": field_name,
            "url": getattr(tournament, field_name).url,
            "filename": uploaded_file.name,
        }
