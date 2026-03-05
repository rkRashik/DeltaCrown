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

from django.db import transaction
from django.utils import timezone

from apps.tournaments.models import Tournament
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

    # ------------------------------------------------------------------
    # Tournament Settings (basic info)
    # ------------------------------------------------------------------

    @staticmethod
    def get_settings(tournament: Tournament) -> dict:
        """Return editable tournament fields grouped by section (1:1 model parity)."""
        t = tournament
        return {
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
    def update_settings(tournament: Tournament, data: dict) -> dict:
        """Flat-merge provided fields into the Tournament model (1:1 parity)."""
        updatable = {
            # Basic
            "name", "description", "is_official", "is_featured",
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
        changed: list[str] = []
        for key, value in data.items():
            if key in updatable and hasattr(tournament, key):
                setattr(tournament, key, value)
                changed.append(key)
        if changed:
            tournament.save(update_fields=changed + ["updated_at"] if hasattr(tournament, "updated_at") else changed)
        return {"updated_fields": changed}

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
                    "bank_instructions": m.bank_instructions,
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
                          "bank_account_name", "bank_routing_number", "bank_instructions"):
                if field in data:
                    kwargs[field] = data[field]
        elif method == "deltacoin":
            if "deltacoin_instructions" in data:
                kwargs["deltacoin_instructions"] = data["deltacoin_instructions"]

        pm = TournamentPaymentMethod.objects.create(**kwargs)
        return {"id": pm.id, "method": pm.method}

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
