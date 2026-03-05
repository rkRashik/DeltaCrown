"""
Tournament Cloning Service
============================
Implements a deep-clone of a Tournament, copying all configuration fields
while resetting operational/status data.

Cloned:
  - Tournament core settings (format, rules, fees, prizes, features, social, etc.)
  - GameMatchConfig (scoring, veto, map settings) → includes MapPoolEntry + BRScoringMatrix
  - ServerRegion entries
  - TournamentPaymentMethod records
  - CustomField definitions

NOT cloned:
  - Registrations, Payments, Disputes
  - Brackets, Groups, Matches, Results
  - Certificates, Audit logs, Staff assignments
  - File uploads (banner_image, thumbnail_image, rules_pdf, terms_pdf)
  - Status flags: status, is_official, is_featured, published_at
  - Operational counters: total_registrations, total_matches, completed_matches
"""

import copy
import logging
import re

from django.db import transaction
from django.utils.text import slugify

logger = logging.getLogger(__name__)

# Fields copied verbatim from source tournament
_COPY_FIELDS = [
    # Identity
    "description",
    # Format
    "format", "participation_type", "platform", "mode",
    "max_participants", "min_participants",
    "max_guest_teams", "allow_display_name_override",
    # Venue
    "venue_name", "venue_address", "venue_city", "venue_map_url",
    # Fees
    "has_entry_fee", "entry_fee_amount", "entry_fee_currency",
    "entry_fee_deltacoin", "payment_deadline_hours",
    "payment_methods",
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
    "enable_no_show_timer", "no_show_timeout_minutes",
    # Waitlist
    "auto_forfeit_no_shows", "waitlist_auto_promote", "max_waitlist_size",
    # Social / contact
    "contact_email", "contact_phone",
    "social_discord", "social_twitter", "social_instagram",
    "social_youtube", "social_website", "social_facebook", "social_tiktok",
    "support_info",
    # Media (URL fields only — not file uploads)
    "promo_video_url", "stream_youtube_url", "stream_twitch_url",
    # SEO
    "meta_description", "meta_keywords",
    # Config JSON (notification rules, scoring presets, tiebreakers, etc.)
    "config",
    # Registration form overrides
    "registration_form_overrides",
]

# Fields on related models to skip when doing generic copy
_SKIP_FIELDS = frozenset({"id", "pk", "tournament", "tournament_id", "created_at", "updated_at"})


class TournamentCloningService:
    """
    Deep-clone a Tournament for reuse across recurring events.
    """

    @staticmethod
    @transaction.atomic
    def clone(source, organizer=None, overrides: dict = None):
        """
        Clone ``source`` Tournament into a new draft tournament.

        Args:
            source:    Source Tournament instance to copy from.
            organizer: User who owns the new tournament (defaults to source organizer).
            overrides: Dict of field overrides applied after copy (e.g. name, game_id).

        Returns:
            New Tournament instance (status='draft', no dates set).
        """
        from apps.tournaments.models import Tournament

        overrides = overrides or {}
        organizer = organizer or source.organizer

        # 1. Build new name & slug
        base_name = overrides.pop("name", None) or _generate_clone_name(source.name)
        new_slug = _unique_slug(slugify(base_name))

        # 2. Copy core fields
        new_t = Tournament(
            name=base_name,
            slug=new_slug,
            organizer=organizer,
            game=source.game,
            status="draft",
            is_featured=False,
            is_official=False,
            # Dates: start blank — organizer must set dates before publishing
            registration_start=None,
            registration_end=None,
            tournament_start=None,
            tournament_end=None,
            # Counters reset
            total_registrations=0,
            total_matches=0,
            completed_matches=0,
        )

        for field in _COPY_FIELDS:
            if field in overrides:
                continue  # caller-provided override takes precedence
            val = getattr(source, field, None)
            if val is not None:
                # Deep-copy mutable JSON / list values to avoid shared references
                if isinstance(val, (dict, list)):
                    val = copy.deepcopy(val)
                setattr(new_t, field, val)

        # Apply any remaining overrides
        for key, val in overrides.items():
            if hasattr(new_t, key):
                setattr(new_t, key, val)

        new_t.save()

        logger.info(
            "clone: tournament %s → %s (id=%s)",
            source.slug, new_t.slug, new_t.pk,
        )

        # 3. Clone related config records
        _clone_game_match_config(source, new_t)
        _clone_server_regions(source, new_t)
        _clone_payment_methods(source, new_t)
        _clone_custom_fields(source, new_t)

        return new_t


# ---------------------------------------------------------------------------
#  Internal helpers
# ---------------------------------------------------------------------------

def _generate_clone_name(original_name: str) -> str:
    """Append ' (Copy)' or increment the copy counter."""
    pattern = r"^(.*?)\s*\(Copy(?:\s+(\d+))?\)$"
    match = re.match(pattern, original_name)
    if match:
        base = match.group(1).strip()
        n = int(match.group(2) or 1) + 1
        return f"{base} (Copy {n})"
    return f"{original_name} (Copy)"


def _unique_slug(base_slug: str) -> str:
    """Return a unique slug by appending a numeric suffix if needed."""
    from apps.tournaments.models import Tournament

    slug = base_slug[:48]  # keep slug reasonably short
    if not Tournament.objects.filter(slug=slug).exists():
        return slug
    i = 2
    while True:
        candidate = f"{slug[:45]}-{i}"
        if not Tournament.objects.filter(slug=candidate).exists():
            return candidate
        i += 1


def _clone_game_match_config(source, dest) -> None:
    """
    Clone the 1:1 GameMatchConfig and its children:
    - MapPoolEntry items (ordered)
    - BRScoringMatrix (if present)
    """
    try:
        from apps.tournaments.models.game_config import (
            BRScoringMatrix, GameMatchConfig, MapPoolEntry,
        )
        cfg = GameMatchConfig.objects.filter(tournament=source).first()
        if not cfg:
            return

        new_cfg = GameMatchConfig.objects.create(
            tournament=dest,
            game=cfg.game,
            default_match_format=cfg.default_match_format,
            scoring_rules=copy.deepcopy(cfg.scoring_rules),
            match_settings=copy.deepcopy(cfg.match_settings),
            enable_veto=cfg.enable_veto,
            veto_type=cfg.veto_type,
        )

        # Clone map pool entries
        map_entries = list(MapPoolEntry.objects.filter(config=cfg).order_by("order"))
        for entry in map_entries:
            try:
                MapPoolEntry.objects.create(
                    config=new_cfg,
                    map_name=entry.map_name,
                    map_code=entry.map_code,
                    image=entry.image,
                    is_active=entry.is_active,
                    order=entry.order,
                )
            except Exception:
                pass  # skip on unique constraint

        if map_entries:
            logger.debug("clone: %d MapPoolEntry cloned for %s", len(map_entries), dest.slug)

        # Clone BR scoring matrix (1:1 with config — may not exist)
        br = getattr(cfg, "br_scoring", None)
        if br is None:
            try:
                br = BRScoringMatrix.objects.get(config=cfg)
            except BRScoringMatrix.DoesNotExist:
                br = None
        if br:
            BRScoringMatrix.objects.create(
                config=new_cfg,
                placement_points=copy.deepcopy(br.placement_points),
                kill_points=br.kill_points,
                tiebreaker_rules=copy.deepcopy(br.tiebreaker_rules),
            )

        logger.debug("clone: GameMatchConfig cloned for %s", dest.slug)
    except Exception as exc:
        logger.warning("clone: GameMatchConfig failed for %s: %s", dest.slug, exc)


def _clone_server_regions(source, dest) -> None:
    """Clone ServerRegion entries."""
    try:
        from apps.tournaments.models.game_config import ServerRegion
        regions = list(ServerRegion.objects.filter(tournament=source))
        for region in regions:
            try:
                ServerRegion.objects.create(
                    tournament=dest,
                    name=region.name,
                    code=region.code,
                    ping_endpoint=region.ping_endpoint,
                    is_active=region.is_active,
                )
            except Exception:
                pass  # unique_together conflict — skip
        if regions:
            logger.debug("clone: %d ServerRegion cloned for %s", len(regions), dest.slug)
    except Exception as exc:
        logger.warning("clone: ServerRegion failed for %s: %s", dest.slug, exc)


def _clone_payment_methods(source, dest) -> None:
    """Clone TournamentPaymentMethod records using generic field copy."""
    try:
        from apps.tournaments.models.payment_config import TournamentPaymentMethod
        methods = list(TournamentPaymentMethod.objects.filter(tournament=source))
        for m in methods:
            kwargs = {"tournament": dest}
            for field in TournamentPaymentMethod._meta.get_fields():
                if not hasattr(field, "column"):
                    continue
                name = field.name
                if name in _SKIP_FIELDS:
                    continue
                val = getattr(m, name, None)
                if isinstance(val, (dict, list)):
                    val = copy.deepcopy(val)
                kwargs[name] = val
            TournamentPaymentMethod.objects.create(**kwargs)
        if methods:
            logger.debug("clone: %d PaymentMethod cloned for %s", len(methods), dest.slug)
    except Exception as exc:
        logger.warning("clone: PaymentMethod failed for %s: %s", dest.slug, exc)


def _clone_custom_fields(source, dest) -> None:
    """Clone CustomField registration question definitions."""
    try:
        from apps.tournaments.models.tournament import CustomField
        fields_qs = list(CustomField.objects.filter(tournament=source).order_by("order"))
        for f in fields_qs:
            CustomField.objects.create(
                tournament=dest,
                field_name=f.field_name,
                field_key=f.field_key,
                field_type=f.field_type,
                field_config=copy.deepcopy(f.field_config) if f.field_config else {},
                field_value=copy.deepcopy(f.field_value) if f.field_value else None,
                is_required=f.is_required,
                order=f.order,
                help_text=f.help_text,
            )
        if fields_qs:
            logger.debug("clone: %d CustomField cloned for %s", len(fields_qs), dest.slug)
    except Exception as exc:
        logger.warning("clone: CustomField failed for %s: %s", dest.slug, exc)
