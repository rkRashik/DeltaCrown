"""
TOC Sprint 8 — Settings & Configuration Service

Provides organizer-level operations for:
  - Tournament basic settings (name, dates, capacity, prizes, etc.)
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

logger = logging.getLogger("toc.settings")


class TOCSettingsService:
    """All read/write operations for the Settings & Config tab."""

    # ------------------------------------------------------------------
    # Tournament Settings (basic info)
    # ------------------------------------------------------------------

    @staticmethod
    def get_settings(tournament: Tournament) -> dict:
        """Return editable tournament fields grouped by section."""
        t = tournament
        return {
            "basic": {
                "name": t.name,
                "slug": t.slug,
                "description": t.description or "",
                "status": t.status,
                "is_official": t.is_official,
                "is_featured": getattr(t, "is_featured", False),
            },
            "format": {
                "format": t.format,
                "participation_type": getattr(t, "participation_type", ""),
                "platform": getattr(t, "platform", ""),
                "mode": getattr(t, "mode", ""),
                "max_participants": t.max_participants,
                "min_participants": getattr(t, "min_participants", 0),
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
            },
            "prizes": {
                "prize_pool": str(t.prize_pool) if t.prize_pool else "0",
                "prize_currency": getattr(t, "prize_currency", "USD"),
                "prize_deltacoin": str(getattr(t, "prize_deltacoin", 0)),
                "prize_distribution": getattr(t, "prize_distribution", {}),
            },
            "registration_rules": {
                "has_entry_fee": getattr(t, "has_entry_fee", False),
                "entry_fee_amount": str(getattr(t, "entry_fee_amount", 0)),
                "payment_methods": getattr(t, "payment_methods", []),
                "refund_policy": getattr(t, "refund_policy", ""),
            },
            "features": {
                "enable_check_in": getattr(t, "enable_check_in", False),
                "enable_dynamic_seeding": getattr(t, "enable_dynamic_seeding", False),
                "enable_live_updates": getattr(t, "enable_live_updates", False),
                "enable_certificates": getattr(t, "enable_certificates", False),
                "require_terms_acceptance": getattr(t, "require_terms_acceptance", False),
            },
            "social": {
                "contact_email": getattr(t, "contact_email", ""),
                "social_discord": getattr(t, "social_discord", ""),
                "social_twitter": getattr(t, "social_twitter", ""),
            },
        }

    @staticmethod
    def update_settings(tournament: Tournament, data: dict) -> dict:
        """Flat-merge provided fields into the Tournament model."""
        updatable = {
            "name", "description", "format", "participation_type", "platform",
            "mode", "max_participants", "min_participants", "prize_pool",
            "prize_currency", "prize_deltacoin", "prize_distribution",
            "has_entry_fee", "entry_fee_amount", "payment_methods", "refund_policy",
            "enable_check_in", "enable_dynamic_seeding", "enable_live_updates",
            "enable_certificates", "require_terms_acceptance",
            "contact_email", "social_discord", "social_twitter",
            "registration_start", "registration_end",
            "tournament_start", "tournament_end",
            "is_official", "is_featured",
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
        return {
            "id": str(cfg.id),
            "game_id": cfg.game_id,
            "default_match_format": cfg.default_match_format,
            "scoring_rules": cfg.scoring_rules,
            "match_settings": cfg.match_settings,
            "enable_veto": cfg.enable_veto,
            "veto_type": cfg.veto_type,
        }

    @staticmethod
    def save_game_config(tournament: Tournament, data: dict) -> dict:
        cfg, created = GameMatchConfig.objects.update_or_create(
            tournament=tournament,
            defaults={
                "game_id": data.get("game_id"),
                "default_match_format": data.get("default_match_format", "bo1"),
                "scoring_rules": data.get("scoring_rules", {}),
                "match_settings": data.get("match_settings", {}),
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
