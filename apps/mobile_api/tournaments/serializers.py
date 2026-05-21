"""Mobile tournament serializers."""
from __future__ import annotations

from django.core.paginator import EmptyPage, Paginator

from apps.tournaments.models import Registration, Tournament


ACTIVE_REGISTRATION_STATUSES = [
    Registration.DRAFT,
    Registration.SUBMITTED,
    Registration.PENDING,
    Registration.AUTO_APPROVED,
    Registration.NEEDS_REVIEW,
    Registration.PAYMENT_SUBMITTED,
    Registration.CONFIRMED,
    Registration.WAITLISTED,
]


def safe_file_url(field) -> str | None:
    try:
        return getattr(field, "url", None) if field else None
    except Exception:
        return None


def game_summary(game) -> dict | None:
    if not game:
        return None
    return {
        "id": game.id,
        "name": game.display_name or game.name,
        "slug": game.slug,
        "short_code": game.short_code,
        "category": game.category,
    }


def prize_summary(tournament: Tournament) -> dict:
    return {
        "amount": str(tournament.prize_pool),
        "currency": tournament.prize_currency,
        "deltacoin": tournament.prize_deltacoin,
        "distribution": tournament.prize_distribution or {},
    }


def entry_fee_summary(tournament: Tournament) -> dict:
    return {
        "required": tournament.has_entry_fee,
        "amount": str(tournament.entry_fee_amount),
        "currency": tournament.entry_fee_currency,
        "deltacoin": tournament.entry_fee_deltacoin,
        "payment_methods": list(tournament.payment_methods or []),
    }


def capacity_summary(tournament: Tournament) -> dict:
    active_count = tournament.active_registration_count()
    return {
        "registered": active_count,
        "capacity": tournament.max_participants,
        "min_participants": tournament.min_participants,
        "spots_remaining": max(0, tournament.max_participants - active_count),
        "is_full": tournament.max_participants > 0 and active_count >= tournament.max_participants,
    }


def media_summary(tournament: Tournament) -> dict:
    return {
        "banner_url": safe_file_url(tournament.banner_image),
        "thumbnail_url": safe_file_url(tournament.thumbnail_image),
    }


def user_registration_for(tournament: Tournament, user):
    if not user or not getattr(user, "is_authenticated", False):
        return None
    return (
        Registration.objects.filter(tournament=tournament, user=user, is_deleted=False)
        .exclude(status__in=[Registration.CANCELLED, Registration.REJECTED])
        .order_by("-updated_at", "-id")
        .first()
    )


def registration_summary(registration: Registration | None) -> dict | None:
    if registration is None:
        return None
    return {
        "id": registration.id,
        "status": registration.status,
        "current_step": registration.current_step,
        "completion_percentage": str(registration.completion_percentage),
        "registered_at": registration.registered_at.isoformat() if registration.registered_at else None,
        "checked_in": registration.checked_in,
        "registration_number": registration.registration_number,
    }


def tournament_card(tournament: Tournament, user=None) -> dict:
    registration = user_registration_for(tournament, user)
    return {
        "id": tournament.id,
        "slug": tournament.slug,
        "name": tournament.name,
        "title": tournament.name,
        "game": game_summary(tournament.game),
        "status": tournament.get_effective_status(),
        "format": tournament.format,
        "participation_type": tournament.participation_type,
        "platform": tournament.platform,
        "region": getattr(tournament, "venue_city", "") or "",
        "mode": tournament.mode,
        "registration_status": _registration_window_status(tournament),
        "start_at": tournament.tournament_start.isoformat() if tournament.tournament_start else None,
        "registration_start": tournament.registration_start.isoformat() if tournament.registration_start else None,
        "registration_end": tournament.registration_end.isoformat() if tournament.registration_end else None,
        "prize": prize_summary(tournament),
        "entry_fee": entry_fee_summary(tournament),
        "capacity": capacity_summary(tournament),
        "media": media_summary(tournament),
        "banner_url": safe_file_url(tournament.banner_image),
        "user_registration": registration_summary(registration),
        "user_registration_status": registration.status if registration else None,
    }


def tournament_detail(tournament: Tournament, user=None, eligibility: dict | None = None) -> dict:
    data = tournament_card(tournament, user=user)
    data.update(
        {
            "description": tournament.description,
            "schedule": {
                "timezone": tournament.timezone_name,
                "registration_start": tournament.registration_start.isoformat() if tournament.registration_start else None,
                "registration_end": tournament.registration_end.isoformat() if tournament.registration_end else None,
                "tournament_start": tournament.tournament_start.isoformat() if tournament.tournament_start else None,
                "tournament_end": tournament.tournament_end.isoformat() if tournament.tournament_end else None,
            },
            "finance": {
                "prize": prize_summary(tournament),
                "entry_fee": entry_fee_summary(tournament),
                "refund_policy": tournament.refund_policy,
                "refund_policy_text": tournament.refund_policy_text,
            },
            "rules": {
                "rules_text": tournament.rules_text,
                "terms_required": tournament.require_terms_acceptance,
                "terms_summary": tournament.terms_and_conditions,
                "rules_pdf_url": safe_file_url(tournament.rules_pdf),
            },
            "organizer": {
                "name": tournament.organizer.get_full_name() or tournament.organizer.username,
                "username": tournament.organizer.username,
                "is_official": tournament.is_official,
            },
            "eligibility": eligibility or {},
        }
    )
    return data


def paginate_queryset(queryset, page: int, page_size: int):
    page_size = max(1, min(page_size, 50))
    paginator = Paginator(queryset, page_size)
    try:
        page_obj = paginator.page(page)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages or 1)
    return page_obj, {
        "page": page_obj.number,
        "page_size": page_size,
        "total": paginator.count,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }


def _registration_window_status(tournament: Tournament) -> str:
    if tournament.is_registration_open():
        return "open"
    if tournament.status in [Tournament.CANCELLED, Tournament.COMPLETED, Tournament.ARCHIVED]:
        return "closed"
    if tournament.has_registration_started():
        return "closed"
    return "upcoming"
