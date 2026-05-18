"""Competition app Django admin configuration.

This admin module uses lazy schema detection to prevent crashes when
COMPETITION_APP_ENABLED=1 but migrations not applied.

CRITICAL: Do NOT access database during module import - that breaks migrations!
"""
from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from django.shortcuts import render
from django.contrib import messages
from django.utils.html import format_html
from django.utils import timezone
from django.db import connection
from django.db.models import Count
from django.urls import NoReverseMatch, reverse
import logging
from datetime import timedelta

from django.http import HttpResponseRedirect
from django.utils.dateparse import parse_datetime

logger = logging.getLogger(__name__)


def _linked_match_result_admin_summary(match):
    if not match:
        return 'No linked match'

    try:
        submissions = list(match.result_submissions.all())
    except Exception:
        submissions = []

    open_disputes = 0
    for submission in submissions:
        try:
            disputes = submission.disputes.all()
        except Exception:
            disputes = []
        for dispute in disputes:
            is_open = getattr(dispute, 'is_open', None)
            if callable(is_open):
                open_disputes += 1 if is_open() else 0
            else:
                status = str(getattr(dispute, 'status', '') or '').lower()
                open_disputes += 1 if status in {'open', 'under_review', 'escalated'} else 0

    lobby_info = getattr(match, 'lobby_info', None)
    workflow = {}
    if isinstance(lobby_info, dict):
        raw_workflow = lobby_info.get('match_lobby_workflow') or lobby_info.get('premium_lobby_workflow')
        workflow = raw_workflow if isinstance(raw_workflow, dict) else {}

    result_status = str(workflow.get('result_status') or '').strip() or 'not submitted'
    proof_count = sum(
        1 for submission in submissions
        if getattr(submission, 'proof_screenshot_url', '') or getattr(submission, 'proof_screenshot', None)
    )

    return format_html(
        '{} | result: {} | submissions: {} | proof: {} | open disputes: {}',
        getattr(match, 'state', '') or 'unknown',
        result_status,
        len(submissions),
        proof_count,
        open_disputes,
    )


def competition_admin_status(request):
    """Admin status page showing competition schema state (no model queries)."""
    # Check schema without querying models
    try:
        with connection.cursor() as cursor:
            table_names = connection.introspection.table_names(cursor)
            
            required_tables = {
                'competition_game_ranking_config',
                'competition_match_report',
                'competition_match_verification',
                'competition_team_game_ranking_snapshot',
                'competition_team_global_ranking_snapshot',
            }
            
            existing = required_tables & set(table_names)
            missing = required_tables - set(table_names)
            schema_ready = len(missing) == 0
    except Exception as e:
        schema_ready = False
        existing = set()
        missing = set()
        error = str(e)
    else:
        error = None
    
    context = {
        'title': 'Competition Schema Status',
        'schema_ready': schema_ready,
        'existing_tables': sorted(existing),
        'missing_tables': sorted(missing),
        'error': error,
        'site_header': 'DeltaCrown Admin',
        'site_title': 'Competition Status',
    }
    return render(request, 'admin/competition/status.html', context)


def _admin_link(name, fallback="#"):
    try:
        return reverse(name)
    except NoReverseMatch:
        return fallback


def _admin_change_link(name, obj_id, fallback="#"):
    try:
        return reverse(name, args=[obj_id])
    except NoReverseMatch:
        return fallback


def _safe_count(queryset):
    try:
        if isinstance(queryset, (list, tuple)):
            return len(queryset)
        return queryset.count()
    except Exception:
        return None


def _time_label(value):
    if not value:
        return "No timestamp"
    try:
        return timezone.localtime(value).strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(value)


def _queue_health(count):
    count = count or 0
    if count >= 12:
        return "overloaded"
    if count >= 5:
        return "moderate"
    return "low"


def _parse_console_datetime(value):
    raw = str(value or "").strip()
    if not raw:
        return None
    parsed = parse_datetime(raw)
    if not parsed:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _int_from_post(request, name, default=0, minimum=0):
    try:
        value = int(request.POST.get(name, default) or default)
    except (TypeError, ValueError):
        value = default
    return max(minimum, value)


def _mission_goal_spec(goal_type, target_value, cadence):
    metric_map = {
        "TOP_N_FINISH": "top_n_finish",
        "WIN_STREAK": "win_streak",
        "MATCHES_PLAYED": "matches_played",
        "KILL_THRESHOLD": "kills",
        "CUSTOM": "custom",
    }
    spec = {
        "metric": metric_map.get(goal_type, "custom"),
        "target_value": target_value,
        "cadence": cadence,
        "source": "competitive_operator_console",
    }
    if goal_type == "TOP_N_FINISH":
        spec.update({"n": max(1, target_value), "count": 1})
    elif goal_type == "WIN_STREAK":
        spec.update({"streak": max(1, target_value)})
    elif goal_type == "MATCHES_PLAYED":
        spec.update({"count": max(1, target_value)})
    elif goal_type == "KILL_THRESHOLD":
        spec.update({"kills": max(1, target_value)})
    return spec


def _handle_console_mission_create(request):
    from apps.contracts.models import ContractTemplate
    from apps.games.models import Game

    title = str(request.POST.get("mission_title") or "").strip()
    game_id = request.POST.get("mission_game")
    goal_type = str(request.POST.get("mission_goal_type") or "CUSTOM").strip()
    cadence = str(request.POST.get("mission_cadence") or "custom").strip().lower()
    description = str(request.POST.get("mission_description") or "").strip()
    duration_hours = _int_from_post(request, "mission_duration_hours", 24, 1)
    target_value = _int_from_post(request, "mission_target_value", 1, 1)
    entry_fee = _int_from_post(request, "mission_entry_fee_dc", 0, 0)
    reward = _int_from_post(request, "mission_reward_dc", 0, 0)
    valid_from = _parse_console_datetime(request.POST.get("mission_valid_from"))
    valid_until = _parse_console_datetime(request.POST.get("mission_valid_until"))
    is_active = request.POST.get("mission_is_active") == "on"

    if not title:
        raise ValueError("Mission title is required.")
    if goal_type not in {choice[0] for choice in ContractTemplate.GOAL_TYPE_CHOICES}:
        raise ValueError("Unsupported Mission goal type.")
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist as exc:
        raise ValueError("Select a valid game.") from exc
    if valid_from and not valid_until and cadence in {"daily", "weekly"}:
        valid_until = valid_from + timedelta(days=7 if cadence == "weekly" else 1)

    mission = ContractTemplate(
        title=title,
        description=description,
        game=game,
        entry_fee_dc=entry_fee,
        reward_dc=reward,
        goal_type=goal_type,
        goal_spec=_mission_goal_spec(goal_type, target_value, cadence),
        duration_hours=duration_hours,
        valid_from=valid_from,
        valid_until=valid_until,
        is_active=is_active,
    )
    mission.full_clean()
    mission.save()
    return mission


def competitive_operations_console(request):
    """Staff console for competitive operations entry points.

    This is intentionally a queue/link surface. Sensitive lifecycle actions
    remain in model admins where existing service-backed actions are wired.
    """
    if request.method == "POST" and request.POST.get("console_action") == "create_mission":
        try:
            mission = _handle_console_mission_create(request)
        except Exception as exc:
            messages.error(request, f"Mission creation failed: {exc}")
            return HttpResponseRedirect(reverse("competitive_operations_admin"))
        messages.success(request, f"Mission Template created: {mission.title}")
        return HttpResponseRedirect(_admin_change_link("admin:contracts_contracttemplate_change", mission.pk, reverse("competitive_operations_admin")))

    stats = {}
    priority_items = []
    games = []
    last_activity_at = None
    resolved_labels = {
        "proofs": "No resolved item tracked",
        "showdowns": "No resolved item tracked",
        "bounty": "No resolved item tracked",
        "dropzone": "No resolved item tracked",
        "match_disputes": "No resolved item tracked",
    }
    try:
        from apps.contracts.models import ContractEnrollment, ContractProofSubmission, ContractTemplate
        from apps.games.models import Game
        from apps.organizations.models import TeamCompetitiveSettings
        from apps.royale.models import RoyaleEntry, RoyaleLobby
        from apps.tournaments.models import DisputeRecord
        now = timezone.now()
        games = list(Game.objects.filter(is_active=True).order_by("name").values("id", "name", "short_code")[:200])

        mission_proofs = ContractProofSubmission.objects.filter(
            status="PENDING_REVIEW",
        ).select_related("enrollment", "enrollment__template", "submitted_by")
        if MODELS_IMPORTED:
            disputed_showdowns = Challenge.objects.filter(status="DISPUTED").select_related(
                "challenger_team", "challenged_team", "game",
            )
            pending_claims = BountyClaim.objects.filter(status="PENDING").select_related(
                "bounty", "bounty__issuer_team", "bounty__game", "claiming_team",
            )
        else:
            disputed_showdowns = []
            pending_claims = []
        scoring_lobbies = RoyaleLobby.objects.filter(status="SCORING").select_related("game")
        open_disputes = DisputeRecord.objects.filter(
            status__in=[DisputeRecord.OPEN, DisputeRecord.UNDER_REVIEW, DisputeRecord.ESCALATED],
        ).select_related("submission", "opened_by_user")

        recent_candidates = [
            mission_proofs.order_by("-submitted_at").values_list("submitted_at", flat=True).first(),
            disputed_showdowns.order_by("-updated_at").values_list("updated_at", flat=True).first() if hasattr(disputed_showdowns, "order_by") else None,
            pending_claims.order_by("-claimed_at").values_list("claimed_at", flat=True).first() if hasattr(pending_claims, "order_by") else None,
            scoring_lobbies.order_by("-updated_at").values_list("updated_at", flat=True).first(),
            open_disputes.order_by("-updated_at").values_list("updated_at", flat=True).first(),
        ]
        recent_candidates = [value for value in recent_candidates if value]
        last_activity_at = max(recent_candidates) if recent_candidates else None
        resolved_labels.update({
            "proofs": _time_label(
                ContractProofSubmission.objects.exclude(reviewed_at__isnull=True)
                .order_by("-reviewed_at")
                .values_list("reviewed_at", flat=True)
                .first()
            ),
            "showdowns": _time_label(
                Challenge.objects.exclude(settled_at__isnull=True)
                .order_by("-settled_at")
                .values_list("settled_at", flat=True)
                .first()
            ) if MODELS_IMPORTED else "No resolved item tracked",
            "bounty": _time_label(
                BountyClaim.objects.exclude(verified_at__isnull=True)
                .order_by("-verified_at")
                .values_list("verified_at", flat=True)
                .first()
            ) if MODELS_IMPORTED else "No resolved item tracked",
            "dropzone": _time_label(
                RoyaleEntry.objects.exclude(resolved_at__isnull=True)
                .order_by("-resolved_at")
                .values_list("resolved_at", flat=True)
                .first()
            ),
            "match_disputes": _time_label(
                DisputeRecord.objects.exclude(resolved_at__isnull=True)
                .order_by("-resolved_at")
                .values_list("resolved_at", flat=True)
                .first()
            ),
        })

        stats.update({
            "mission_templates": _safe_count(ContractTemplate.objects.all()),
            "mission_enrollments": _safe_count(ContractEnrollment.objects.all()),
            "mission_proofs_pending": _safe_count(mission_proofs),
            "mission_enrollments_active": _safe_count(ContractEnrollment.objects.filter(status="ACTIVE")),
            "showdowns_open": _safe_count(Challenge.objects.filter(status="OPEN")) if MODELS_IMPORTED else 0,
            "showdowns_active": _safe_count(Challenge.objects.filter(status__in=["OPEN", "ACCEPTED", "SCHEDULED", "IN_PROGRESS", "PENDING_CONFIRMATION"])) if MODELS_IMPORTED else 0,
            "showdowns_disputed": _safe_count(disputed_showdowns),
            "bounties_active": _safe_count(Bounty.objects.filter(status="ACTIVE")) if MODELS_IMPORTED else 0,
            "bounty_claims_pending": _safe_count(pending_claims),
            "dropzone_lobbies": _safe_count(RoyaleLobby.objects.all()),
            "dropzone_entries": _safe_count(RoyaleEntry.objects.all()),
            "dropzone_scoring": _safe_count(scoring_lobbies),
            "dropzone_upcoming": _safe_count(RoyaleLobby.objects.filter(status__in=["ANNOUNCED", "FILLING", "FULL"], scheduled_at__gte=now)),
            "match_disputes_open": _safe_count(open_disputes),
            "team_settings": _safe_count(TeamCompetitiveSettings.objects.all()),
        })

        for proof in mission_proofs.order_by("-submitted_at")[:5]:
            priority_items.append({
                "type": "Mission Proof",
                "title": getattr(getattr(proof, "enrollment", None), "template", None).title if getattr(getattr(proof, "enrollment", None), "template", None) else "Mission proof",
                "status": proof.get_status_display() if hasattr(proof, "get_status_display") else proof.status,
                "when": _time_label(proof.submitted_at),
                "next_step": "Review proof, then accept/reject. Completing the Mission is a separate service-backed action.",
                "href": _admin_change_link("admin:contracts_contractproofsubmission_change", proof.pk),
                "tone": "amber",
                "icon": "fact_check",
            })

        showdown_queue = disputed_showdowns.order_by("-updated_at")[:5] if hasattr(disputed_showdowns, "order_by") else []
        for showdown in showdown_queue:
            priority_items.append({
                "type": "Showdown",
                "title": showdown.title or showdown.reference_code,
                "status": showdown.get_status_display() if hasattr(showdown, "get_status_display") else showdown.status,
                "when": _time_label(showdown.updated_at),
                "next_step": "Inspect submissions and resolve through Showdown admin actions.",
                "href": _admin_change_link("admin:competition_challenge_change", showdown.pk),
                "tone": "rose",
                "icon": "swords",
            })

        claim_queue = pending_claims.order_by("-claimed_at")[:5] if hasattr(pending_claims, "order_by") else []
        for claim in claim_queue:
            priority_items.append({
                "type": "Bounty Claim",
                "title": getattr(claim.bounty, "title", "Bounty claim"),
                "status": claim.get_status_display() if hasattr(claim, "get_status_display") else claim.status,
                "when": _time_label(claim.claimed_at),
                "next_step": "Verify or reject the claim through Bounty Claim admin actions.",
                "href": _admin_change_link("admin:competition_bountyclaim_change", claim.pk),
                "tone": "rose",
                "icon": "verified",
            })

        for lobby in scoring_lobbies.order_by("scheduled_at")[:5]:
            priority_items.append({
                "type": "Dropzone",
                "title": lobby.title or lobby.reference_code,
                "status": lobby.get_status_display() if hasattr(lobby, "get_status_display") else lobby.status,
                "when": _time_label(lobby.scheduled_at),
                "next_step": "Confirm placements/kills, record scores, then settle through lobby admin actions.",
                "href": _admin_change_link("admin:royale_royalelobby_change", lobby.pk),
                "tone": "cyan",
                "icon": "air",
            })

        for dispute in open_disputes.order_by("-updated_at")[:5]:
            priority_items.append({
                "type": "Match Room Dispute",
                "title": f"Dispute #{dispute.pk}",
                "status": dispute.get_status_display() if hasattr(dispute, "get_status_display") else dispute.status,
                "when": _time_label(dispute.updated_at),
                "next_step": "Review evidence and resolve from the Match Room dispute admin.",
                "href": _admin_change_link("admin:tournaments_disputerecord_change", dispute.pk),
                "tone": "rose",
                "icon": "gavel",
            })
    except Exception as exc:
        logger.warning("competitive admin console stats unavailable: %s", exc)
        stats = {}

    cards = [
        {
            "title": "Mission Templates",
            "icon": "flag",
            "count": stats.get("mission_templates"),
            "description": "Create and tune solo objectives.",
            "href": _admin_link("admin:contracts_contracttemplate_changelist"),
        },
        {
            "title": "Mission Enrollments",
            "icon": "assignment",
            "count": stats.get("mission_enrollments"),
            "description": "Track enrolled user Missions.",
            "href": _admin_link("admin:contracts_contractenrollment_changelist"),
        },
        {
            "title": "Mission Proof Reviews",
            "icon": "fact_check",
            "count": stats.get("mission_proofs_pending"),
            "description": "Accept or reject submitted Mission proof.",
            "href": _admin_link("admin:contracts_contractproofsubmission_changelist"),
            "tone": "amber",
        },
        {
            "title": "Showdowns",
            "icon": "swords",
            "count": stats.get("showdowns_open"),
            "description": "Create, inspect, settle, refund, or resolve team matches.",
            "href": _admin_link("admin:competition_challenge_changelist"),
        },
        {
            "title": "Showdown Result Submissions",
            "icon": "scoreboard",
            "description": "Review submitted Showdown results.",
            "href": _admin_link("admin:competition_challengeresultsubmission_changelist"),
        },
        {
            "title": "Bounties",
            "icon": "target",
            "count": stats.get("bounties_active"),
            "description": "Manage team-posted Bounties.",
            "href": _admin_link("admin:competition_bounty_changelist"),
        },
        {
            "title": "Bounty Claims",
            "icon": "verified",
            "count": stats.get("bounty_claims_pending"),
            "description": "Verify, reject, or respawn claim Match Rooms.",
            "href": _admin_link("admin:competition_bountyclaim_changelist"),
            "tone": "rose",
        },
        {
            "title": "Dropzone Lobbies",
            "icon": "air",
            "count": stats.get("dropzone_lobbies"),
            "description": "Create lobbies, manage credentials, scoring, settlement.",
            "href": _admin_link("admin:royale_royalelobby_changelist"),
        },
        {
            "title": "Dropzone Entries",
            "icon": "list_alt",
            "count": stats.get("dropzone_entries"),
            "description": "Enter placement/kills and inspect entry state.",
            "href": _admin_link("admin:royale_royaleentry_changelist"),
        },
        {
            "title": "Match Room Disputes",
            "icon": "gavel",
            "count": stats.get("match_disputes_open"),
            "description": "Open tournament Match Room disputes.",
            "href": _admin_link("admin:tournaments_disputerecord_changelist"),
            "tone": "rose",
        },
        {
            "title": "Review Workspace",
            "icon": "dashboard",
            "description": "Staff queue for proof/review/dispute links.",
            "href": "/dashboard/competitive/review/",
        },
        {
            "title": "Team Competitive Settings",
            "icon": "admin_panel_settings",
            "count": stats.get("team_settings"),
            "description": "Team caps, authority rules, public scrim/tryout flags.",
            "href": _admin_link("admin:organizations_teamcompetitivesettings_changelist"),
        },
    ]

    summary_cards = [
        {"title": "Pending Mission Proofs", "value": stats.get("mission_proofs_pending"), "icon": "fact_check", "href": _admin_link("admin:contracts_contractproofsubmission_changelist"), "tone": "amber"},
        {"title": "Disputed Showdowns", "value": stats.get("showdowns_disputed"), "icon": "swords", "href": _admin_link("admin:competition_challenge_changelist"), "tone": "rose"},
        {"title": "Pending Bounty Claims", "value": stats.get("bounty_claims_pending"), "icon": "verified", "href": _admin_link("admin:competition_bountyclaim_changelist"), "tone": "rose"},
        {"title": "Dropzone Scoring", "value": stats.get("dropzone_scoring"), "icon": "air", "href": _admin_link("admin:royale_royalelobby_changelist"), "tone": "cyan"},
        {"title": "Match Room Disputes", "value": stats.get("match_disputes_open"), "icon": "gavel", "href": _admin_link("admin:tournaments_disputerecord_changelist"), "tone": "rose"},
        {"title": "Active Missions", "value": stats.get("mission_enrollments_active"), "icon": "flag", "href": _admin_link("admin:contracts_contractenrollment_changelist"), "tone": "violet"},
        {"title": "Active Showdowns", "value": stats.get("showdowns_active"), "icon": "sports_mma", "href": _admin_link("admin:competition_challenge_changelist"), "tone": "cyan"},
        {"title": "Active Bounties", "value": stats.get("bounties_active"), "icon": "target", "href": _admin_link("admin:competition_bounty_changelist"), "tone": "rose"},
        {"title": "Upcoming Dropzone", "value": stats.get("dropzone_upcoming"), "icon": "event", "href": _admin_link("admin:royale_royalelobby_changelist"), "tone": "cyan"},
    ]
    overview_cards = summary_cards[:5]

    creation_cards = [
        {"title": "Create Mission Template", "description": "Publish a new solo objective.", "icon": "add_task", "href": _admin_link("admin:contracts_contracttemplate_add"), "primary": True, "count": stats.get("mission_templates")},
        {"title": "Create Dropzone Lobby", "description": "Schedule a battle royale lobby.", "icon": "add_location_alt", "href": _admin_link("admin:royale_royalelobby_add"), "primary": True, "count": stats.get("dropzone_upcoming")},
        {"title": "Review Mission Proofs", "description": "Accept or reject submitted proof.", "icon": "fact_check", "href": _admin_link("admin:contracts_contractproofsubmission_changelist"), "count": stats.get("mission_proofs_pending")},
        {"title": "Review Bounty Claims", "description": "Verify or reject pending claims.", "icon": "verified", "href": _admin_link("admin:competition_bountyclaim_changelist"), "count": stats.get("bounty_claims_pending")},
        {"title": "Resolve Showdowns", "description": "Settle, refund, or resolve disputes.", "icon": "swords", "href": _admin_link("admin:competition_challenge_changelist"), "count": stats.get("showdowns_disputed")},
        {"title": "Review Match Room Disputes", "description": "Inspect tournament dispute records.", "icon": "gavel", "href": _admin_link("admin:tournaments_disputerecord_changelist"), "count": stats.get("match_disputes_open")},
        {"title": "Team Competitive Settings", "description": "Team limits and authority rules.", "icon": "admin_panel_settings", "href": _admin_link("admin:organizations_teamcompetitivesettings_changelist"), "count": stats.get("team_settings")},
    ]

    workflow_steps = [
        {
            "title": "Mission Systems",
            "icon": "flag",
            "description": "Solo objectives created by staff, completed by users, and reviewed through proof/admin workflow.",
            "steps": ["Create template", "User enrolls", "Proof", "Review", "Complete/fail"],
            "safety_note": "Proof review is evidence review only. Complete or fail enrollments through Mission admin actions.",
            "checkpoint": "Confirm objective, proof requirement, reward, and active window before publishing.",
            "operator_error": "Publishing vague proof rules creates review disputes.",
            "escalation": "Escalate repeated suspicious proof or reward abuse to staff review.",
            "review_time": "2-5 min per proof",
            "dependency": "Mission Enrollment and Proof Review admin",
        },
        {
            "title": "Showdown",
            "icon": "swords",
            "description": "Team matches that move through Match Room, result submission, confirmation, and review.",
            "steps": ["Created", "Accepted", "Match Room", "Result", "Dispute/settle"],
            "safety_note": "Resolve disputed or confirmed results through service-backed Showdown admin actions.",
            "checkpoint": "Check both teams, Match Room state, result submissions, and escrow state.",
            "operator_error": "Direct status edits can bypass settlement safeguards.",
            "escalation": "Escalate conflicting proof or repeated no-show behavior.",
            "review_time": "5-10 min per dispute",
            "dependency": "Showdown admin, result submissions, Match Room disputes",
        },
        {
            "title": "Bounty",
            "icon": "target",
            "description": "Teams post Bounties on themselves; challengers claim them and staff verifies the claim.",
            "steps": ["Team posts", "Challenger claims", "Match Room", "Verify/reject"],
            "safety_note": "Verification and rejection must use Bounty Claim admin actions.",
            "checkpoint": "Confirm claim team, linked Match Room, evidence, and Bounty reward state.",
            "operator_error": "Treating Bounty as a solo flow or target-team placement creates product confusion.",
            "escalation": "Escalate unclear evidence or duplicate claim attempts.",
            "review_time": "3-8 min per claim",
            "dependency": "Bounty Claim admin and linked Match Room",
        },
        {
            "title": "Dropzone",
            "icon": "air",
            "description": "Battle royale lobbies with reservations, room reveal, operator scoring, and settlement.",
            "steps": ["Create lobby", "Reserve slots", "Reveal room", "Score", "Settle"],
            "safety_note": "Record scoring first, then settle or cancel from the Dropzone Lobby admin.",
            "checkpoint": "Confirm lobby capacity, room reveal state, placements, kills, and score completeness.",
            "operator_error": "Settling before scores are complete creates payout errors.",
            "escalation": "Escalate missing score sheets or participant disputes.",
            "review_time": "10-20 min per lobby",
            "dependency": "Dropzone Lobby and Entry admins",
        },
    ]

    priority_groups = [
        {
            "key": "proofs",
            "title": "Proofs waiting review",
            "description": "Mission proof submissions that need accept/reject decisions.",
            "count": stats.get("mission_proofs_pending"),
            "items": [item for item in priority_items if item["type"] == "Mission Proof"],
            "icon": "fact_check",
            "health": _queue_health(stats.get("mission_proofs_pending")),
            "last_resolved": resolved_labels["proofs"],
        },
        {
            "key": "showdowns",
            "title": "Disputed Showdowns",
            "description": "Showdown matches waiting for operator resolution.",
            "count": stats.get("showdowns_disputed"),
            "items": [item for item in priority_items if item["type"] == "Showdown"],
            "icon": "swords",
            "health": _queue_health(stats.get("showdowns_disputed")),
            "last_resolved": resolved_labels["showdowns"],
        },
        {
            "key": "bounty",
            "title": "Bounty claims",
            "description": "Claim verification queue for team-posted Bounties.",
            "count": stats.get("bounty_claims_pending"),
            "items": [item for item in priority_items if item["type"] == "Bounty Claim"],
            "icon": "verified",
            "health": _queue_health(stats.get("bounty_claims_pending")),
            "last_resolved": resolved_labels["bounty"],
        },
        {
            "key": "dropzone",
            "title": "Dropzone scoring",
            "description": "Lobbies in scoring/review state before settlement.",
            "count": stats.get("dropzone_scoring"),
            "items": [item for item in priority_items if item["type"] == "Dropzone"],
            "icon": "air",
            "health": _queue_health(stats.get("dropzone_scoring")),
            "last_resolved": resolved_labels["dropzone"],
        },
        {
            "key": "match_disputes",
            "title": "Match Room disputes",
            "description": "Open tournament Match Room disputes.",
            "count": stats.get("match_disputes_open"),
            "items": [item for item in priority_items if item["type"] == "Match Room Dispute"],
            "icon": "gavel",
            "health": _queue_health(stats.get("match_disputes_open")),
            "last_resolved": resolved_labels["match_disputes"],
        },
    ]

    cards_by_title = {card["title"]: card for card in cards}
    surface_groups = [
        {
            "title": "Missions",
            "description": "Templates, enrollments, and proof review.",
            "risk": "Medium",
            "purpose": "Create solo objectives and resolve user progress/proof review.",
            "entities": "Templates, enrollments, proof submissions",
            "cards": [
                cards_by_title["Mission Templates"],
                cards_by_title["Mission Enrollments"],
                cards_by_title["Mission Proof Reviews"],
            ],
        },
        {
            "title": "Match Systems",
            "description": "Team matches, results, disputes, settlement actions.",
            "risk": "High",
            "purpose": "Operate team-vs-team matches through Match Room and service-backed settlement.",
            "entities": "Showdowns, result submissions",
            "cards": [
                cards_by_title["Showdowns"],
                cards_by_title["Showdown Result Submissions"],
            ],
        },
        {
            "title": "Reward Systems",
            "description": "Team-posted Bounties and claim verification.",
            "risk": "High",
            "purpose": "Verify team Bounty claims and review linked evidence.",
            "entities": "Bounties, Bounty claims",
            "cards": [
                cards_by_title["Bounties"],
                cards_by_title["Bounty Claims"],
            ],
        },
        {
            "title": "Lobby Systems",
            "description": "Battle royale lobby setup, entries, scoring, settlement.",
            "risk": "High",
            "purpose": "Schedule lobbies, manage entries, record scores, and settle safely.",
            "entities": "Lobbies, entries, scoring",
            "cards": [
                cards_by_title["Dropzone Lobbies"],
                cards_by_title["Dropzone Entries"],
            ],
        },
        {
            "title": "Team Governance",
            "description": "Team authority, caps, and public team operation flags.",
            "risk": "Medium",
            "purpose": "Control who can start team competitive operations and configure limits.",
            "entities": "Team competitive settings",
            "cards": [
                cards_by_title["Team Competitive Settings"],
            ],
        },
        {
            "title": "Dispute Systems",
            "description": "Staff queue and Match Room dispute surfaces.",
            "risk": "High",
            "purpose": "Route staff into review queues and dispute records without bypassing services.",
            "entities": "Review workspace, Match Room disputes",
            "cards": [
                cards_by_title["Match Room Disputes"],
                cards_by_title["Review Workspace"],
            ],
        },
    ]

    urgent_count = sum(
        value or 0 for value in [
            stats.get("mission_proofs_pending"),
            stats.get("showdowns_disputed"),
            stats.get("bounty_claims_pending"),
            stats.get("dropzone_scoring"),
            stats.get("match_disputes_open"),
        ]
    )
    last_activity_label = _time_label(last_activity_at)

    mission_presets = [
        {
            "name": "Daily Mission",
            "title": "Daily Skill Mission",
            "cadence": "daily",
            "goal_type": "MATCHES_PLAYED",
            "duration_hours": 24,
            "target_value": 3,
            "entry_fee_dc": 0,
            "reward_dc": 100,
            "description": "Complete today's objective and submit proof if requested.",
        },
        {
            "name": "Weekly Mission",
            "title": "Weekly Progress Mission",
            "cadence": "weekly",
            "goal_type": "MATCHES_PLAYED",
            "duration_hours": 168,
            "target_value": 10,
            "entry_fee_dc": 0,
            "reward_dc": 500,
            "description": "Complete the weekly objective during the active window.",
        },
        {
            "name": "Headshot Challenge",
            "title": "Precision Challenge",
            "cadence": "custom",
            "goal_type": "CUSTOM",
            "duration_hours": 24,
            "target_value": 1,
            "entry_fee_dc": 0,
            "reward_dc": 250,
            "description": "Submit proof for the configured precision objective.",
        },
        {
            "name": "Win Streak",
            "title": "Win Streak Mission",
            "cadence": "custom",
            "goal_type": "WIN_STREAK",
            "duration_hours": 48,
            "target_value": 3,
            "entry_fee_dc": 0,
            "reward_dc": 400,
            "description": "Win consecutive matches within the Mission window.",
        },
        {
            "name": "Damage / Kill Objective",
            "title": "Elimination Objective",
            "cadence": "custom",
            "goal_type": "KILL_THRESHOLD",
            "duration_hours": 24,
            "target_value": 15,
            "entry_fee_dc": 0,
            "reward_dc": 300,
            "description": "Reach the target elimination count and submit proof.",
        },
        {
            "name": "Custom Mission",
            "title": "Custom Mission",
            "cadence": "custom",
            "goal_type": "CUSTOM",
            "duration_hours": 24,
            "target_value": 1,
            "entry_fee_dc": 0,
            "reward_dc": 100,
            "description": "Define a custom skill objective for staff review.",
        },
    ]

    dropzone_add_url = _admin_link("admin:royale_royalelobby_add")

    context = {
        **admin.site.each_context(request),
        "title": "Competitive Operations",
        "cards": cards,
        "summary_cards": summary_cards,
        "overview_cards": overview_cards,
        "creation_cards": creation_cards,
        "priority_items": priority_items[:12],
        "priority_groups": priority_groups,
        "workflow_steps": workflow_steps,
        "surface_groups": surface_groups,
        "mission_presets": mission_presets,
        "games": games,
        "goal_type_choices": [
            ("TOP_N_FINISH", "Top-N finish"),
            ("WIN_STREAK", "Win streak"),
            ("MATCHES_PLAYED", "Matches played"),
            ("KILL_THRESHOLD", "Kills objective"),
            ("CUSTOM", "Custom"),
        ],
        "dropzone_add_url": dropzone_add_url,
        "contract_template_add_url": _admin_link("admin:contracts_contracttemplate_add"),
        "stats": stats,
        "urgent_count": urgent_count,
        "last_activity_label": last_activity_label,
    }
    return render(request, "admin/competition/operations.html", context)


# DO NOT check schema at import time - that causes database access before migrations run
# Instead, we'll check lazily when Django actually tries to load admin classes
try:
    # Import models optimistically - if tables don't exist, admin just won't show them
    from .models import (
        GameRankingConfig,
        MatchReport,
        MatchVerification,
        TeamGameRankingSnapshot,
        TeamGlobalRankingSnapshot,
        Challenge,
        ChallengeResultSubmission,
        Bounty,
        BountyClaim,
    )
    from .services import BountyService, ChallengeService, VerificationService, SnapshotService

    Challenge._meta.verbose_name = "Showdown"
    Challenge._meta.verbose_name_plural = "Showdowns"
    ChallengeResultSubmission._meta.verbose_name = "Showdown Result Submission"
    ChallengeResultSubmission._meta.verbose_name_plural = "Showdown Result Submissions"
    
    MODELS_IMPORTED = True
except Exception as e:
    # Models can't be imported (likely because tables don't exist)
    logger.warning(
        f"Competition models not available: {e}. "
        "Run 'python manage.py migrate competition' to enable admin features."
    )
    MODELS_IMPORTED = False


# Only register admin if models were successfully imported
if MODELS_IMPORTED:
    @admin.register(GameRankingConfig)
    class GameRankingConfigAdmin(ModelAdmin):
        """Admin interface for GameRankingConfig."""
        
        list_display = ['game_id', 'game_name', 'is_active', 'updated_at']
        list_filter = ['is_active']
        search_fields = ['game_id', 'game_name']
        readonly_fields = ['created_at', 'updated_at']
        
        fieldsets = [
            ('Game Information', {
                'fields': ['game_id', 'game_name', 'is_active']
            }),
            ('Scoring Configuration', {
                'fields': ['scoring_weights'],
                'description': 'JSON field: {tournament_win: 500, verified_match_win: 10, ...}'
            }),
            ('Tier Thresholds', {
                'fields': ['tier_thresholds'],
                'description': 'JSON field: {DIAMOND: 2000, PLATINUM: 1200, ...}'
            }),
            ('Decay Policy', {
                'fields': ['decay_policy'],
                'description': 'JSON field: {enabled: true, inactivity_threshold_days: 30, ...}'
            }),
            ('Verification Rules', {
                'fields': ['verification_rules'],
                'description': 'JSON field: {require_opponent_confirmation: true, ...}'
            }),
            ('Metadata', {
                'fields': ['created_at', 'updated_at'],
                'classes': ['collapse']
            }),
        ]
    
    
    @admin.register(MatchReport)
    class MatchReportAdmin(ModelAdmin):
        """Admin interface for MatchReport."""
        
        list_display = ['id', 'game_id', 'team1', 'team2', 'result', 'match_type', 'played_at', 'submitted_at']
        list_filter = ['game_id', 'match_type', 'result', 'played_at']
        search_fields = ['team1__name', 'team2__name', 'submitted_by__username']
        readonly_fields = ['submitted_at']
        date_hierarchy = 'played_at'
        
        fieldsets = [
            ('Match Details', {
                'fields': ['game_id', 'match_type', 'result', 'played_at']
            }),
            ('Teams', {
                'fields': ['team1', 'team2']
            }),
            ('Evidence', {
                'fields': ['evidence_url', 'evidence_notes']
            }),
            ('Submission Info', {
                'fields': ['submitted_by', 'submitted_at'],
                'classes': ['collapse']
            }),
        ]
    
    
    @admin.register(MatchVerification)
    class MatchVerificationAdmin(ModelAdmin):
        """Admin interface for MatchVerification."""
        
        list_display = ['match_report', 'status', 'confidence_level', 'verified_at', 'verified_by']
        list_filter = ['status', 'confidence_level', 'verified_at']
        search_fields = ['match_report__team1__name', 'match_report__team2__name']
        readonly_fields = ['created_at', 'updated_at', 'verified_at']
        date_hierarchy = 'verified_at'
        
        fieldsets = [
            ('Verification Status', {
                'fields': ['match_report', 'status', 'confidence_level']
            }),
            ('Verification Details', {
                'fields': ['verified_at', 'verified_by']
            }),
            ('Dispute Information', {
                'fields': ['dispute_reason', 'admin_notes'],
                'classes': ['collapse']
            }),
            ('Metadata', {
                'fields': ['created_at', 'updated_at'],
                'classes': ['collapse']
            }),
        ]
        
        actions = ['mark_as_admin_verified', 'mark_as_rejected']
        
        @admin.action(description='Mark selected as Admin Verified')
        def mark_as_admin_verified(self, request, queryset):
            """Admin action to verify matches via VerificationService."""
            success_count = 0
            error_count = 0
            
            for verification in queryset:
                try:
                    VerificationService.admin_verify_match(request.user, verification.match_report.id)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(request, f"Failed to verify match {verification.match_report.id}: {str(e)}", level=messages.ERROR)
            
            if success_count:
                self.message_user(request, f"Successfully verified {success_count} match(es)", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed to verify {error_count} match(es)", level=messages.WARNING)
        
        @admin.action(description='Mark selected as Rejected')
        def mark_as_rejected(self, request, queryset):
            """Admin action to reject fraudulent matches via VerificationService."""
            success_count = 0
            error_count = 0
            
            for verification in queryset:
                try:
                    VerificationService.reject_match(request.user, verification.match_report.id, reason="Rejected by admin action")
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(request, f"Failed to reject match {verification.match_report.id}: {str(e)}", level=messages.ERROR)
            
            if success_count:
                self.message_user(request, f"Successfully rejected {success_count} match(es)", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed to reject {error_count} match(es)", level=messages.WARNING)
    
    
    @admin.register(TeamGameRankingSnapshot)
    class TeamGameRankingSnapshotAdmin(ModelAdmin):
        """Admin interface for TeamGameRankingSnapshot."""
        
        list_display = ['team', 'game_id', 'tier', 'score', 'rank', 'verified_match_count', 'confidence_level', 'snapshot_date']
        list_filter = ['game_id', 'tier', 'confidence_level']
        search_fields = ['team__name']
        readonly_fields = ['snapshot_date', 'created_at']
        date_hierarchy = 'snapshot_date'
        actions = ['recompute_selected_snapshots']
        
        fieldsets = [
            ('Team & Game', {
                'fields': ['team', 'game_id']
            }),
            ('Ranking', {
                'fields': ['score', 'tier', 'rank', 'percentile']
            }),
            ('Match Statistics', {
                'fields': ['verified_match_count', 'confidence_level', 'last_match_at']
            }),
            ('Score Breakdown', {
                'fields': ['breakdown'],
                'description': 'JSON field showing score sources',
                'classes': ['collapse']
            }),
            ('Metadata', {
                'fields': ['snapshot_date', 'created_at'],
                'classes': ['collapse']
            }),
        ]
        
        @admin.action(description='Recompute rankings for selected snapshots')
        def recompute_selected_snapshots(self, request, queryset):
            """Recompute rankings for selected game snapshots"""
            success_count = 0
            error_count = 0
            
            for snapshot in queryset:
                try:
                    SnapshotService.update_team_game_snapshot(snapshot.team, snapshot.game_id)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(
                        request, 
                        f"Failed to recompute {snapshot.team.slug}/{snapshot.game_id}: {str(e)}", 
                        level=messages.ERROR
                    )
            
            if success_count:
                self.message_user(
                    request, 
                    f"Successfully recomputed {success_count} snapshot(s)", 
                    level=messages.SUCCESS
                )
            if error_count:
                self.message_user(
                    request, 
                    f"Failed to recompute {error_count} snapshot(s)", 
                    level=messages.WARNING
                )
    
    
    @admin.register(TeamGlobalRankingSnapshot)
    class TeamGlobalRankingSnapshotAdmin(ModelAdmin):
        """Admin interface for TeamGlobalRankingSnapshot."""
        
        list_display = ['team', 'global_tier', 'global_score', 'global_rank', 'games_played', 'snapshot_date']
        list_filter = ['global_tier', 'games_played']
        search_fields = ['team__name']
        readonly_fields = ['snapshot_date', 'created_at']
        date_hierarchy = 'snapshot_date'
        actions = ['recompute_selected_global_snapshots']
        
        fieldsets = [
            ('Team', {
                'fields': ['team']
            }),
            ('Global Ranking', {
                'fields': ['global_score', 'global_tier', 'global_rank', 'games_played']
            }),
            ('Game Contributions', {
                'fields': ['game_contributions'],
                'description': 'JSON field showing per-game scores',
                'classes': ['collapse']
            }),
            ('Metadata', {
                'fields': ['snapshot_date', 'created_at'],
                'classes': ['collapse']
            }),
        ]
        
        @admin.action(description='Recompute global rankings for selected teams')
        def recompute_selected_global_snapshots(self, request, queryset):
            """Recompute global rankings for selected teams"""
            success_count = 0
            error_count = 0
            
            for snapshot in queryset:
                try:
                    SnapshotService.update_team_global_snapshot(snapshot.team)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    self.message_user(
                        request, 
                        f"Failed to recompute global for {snapshot.team.slug}: {str(e)}", 
                        level=messages.ERROR
                    )
            
            if success_count:
                self.message_user(
                    request, 
                    f"Successfully recomputed {success_count} global snapshot(s)", 
                    level=messages.SUCCESS
                )
            if error_count:
                self.message_user(
                    request, 
                    f"Failed to recompute {error_count} global snapshot(s)", 
                    level=messages.WARNING
                )

    # ── Challenge Admin ──────────────────────────────────────────────────
    class ChallengeResultSubmissionInline(TabularInline):
        model = ChallengeResultSubmission
        extra = 0
        can_delete = False
        readonly_fields = [
            'id', 'team', 'submitted_by', 'result', 'score_details',
            'evidence_url', 'created_at', 'updated_at',
        ]
        fields = readonly_fields

        def has_add_permission(self, request, obj=None):
            return False

    @admin.register(ChallengeResultSubmission)
    class ChallengeResultSubmissionAdmin(ModelAdmin):
        """Read-only admin surface for Showdown result submissions."""

        list_display = ['challenge', 'team', 'result', 'submitted_by', 'created_at', 'updated_at']
        list_filter = ['result', 'team', 'challenge__status']
        search_fields = ['challenge__reference_code', 'challenge__title', 'team__name', 'submitted_by__username']
        readonly_fields = [
            'id', 'challenge', 'team', 'submitted_by', 'result',
            'score_details', 'evidence_url', 'created_at', 'updated_at',
        ]
        raw_id_fields = ['challenge', 'team', 'submitted_by']
        date_hierarchy = 'created_at'

        def has_add_permission(self, request):
            return False

    @admin.register(Challenge)
    class ChallengeAdmin(ModelAdmin):
        """Admin interface for Challenge."""
        
        list_display = [
            'reference_code', 'title', 'challenger_team', 'challenged_team',
            'game', 'status', 'entry_fee_dc', 'result_submissions_count',
            'escrow_state', 'match_room_admin_link', 'linked_match_result_state', 'created_at',
        ]
        list_filter = ['status', 'challenge_type', 'game', 'is_featured', 'escrow_locked']
        search_fields = ['reference_code', 'title', 'challenger_team__name', 'challenged_team__name']
        readonly_fields = [
            'id', 'reference_code', 'status', 'result', 'score_details',
            'evidence_url', 'match_report', 'entry_fee_dc',
            'escrow_locked', 'challenger_lock_txn', 'challenged_lock_txn',
            'payout_txn', 'funded_by_challenger', 'funded_by_challenged',
            'resolved_by', 'closure_reason', 'closure_note', 'match',
            'match_room_admin_link', 'linked_match_result_state', 'result_submissions_count',
            'created_at', 'updated_at', 'accepted_at', 'completed_at', 'settled_at',
        ]
        raw_id_fields = [
            'challenger_team', 'challenged_team', 'game', 'match_report',
            'created_by', 'accepted_by', 'resolved_by', 'challenger_lock_txn',
            'challenged_lock_txn', 'payout_txn', 'funded_by_challenger',
            'funded_by_challenged', 'match',
        ]
        date_hierarchy = 'created_at'
        inlines = [ChallengeResultSubmissionInline]
        actions = [
            'settle_confirmed_showdowns',
            'resolve_disputes_as_challenger_win',
            'resolve_disputes_as_challenged_win',
            'resolve_disputes_as_draw',
            'void_refund_showdowns',
            'respawn_missing_match_rooms',
        ]
        
        fieldsets = [
            ('Showdown', {
                'fields': ['id', 'reference_code', 'title', 'description', 'status', 'challenge_type']
            }),
            ('Teams', {
                'fields': ['challenger_team', 'challenged_team']
            }),
            ('Game & Format', {
                'fields': ['game', 'best_of', 'game_config', 'platform', 'server_region']
            }),
            ('Reward', {
                'fields': ['prize_type', 'prize_amount', 'prize_description', 'entry_fee_dc']
            }),
            ('Result', {
                'fields': ['result', 'score_details', 'evidence_url', 'match_report'],
                'classes': ['collapse']
            }),
            ('Escrow & Settlement', {
                'fields': [
                    'escrow_locked', 'challenger_lock_txn', 'challenged_lock_txn',
                    'payout_txn', 'funded_by_challenger', 'funded_by_challenged',
                    'closure_reason', 'closure_note',
                ],
                'classes': ['collapse'],
            }),
            ('Match Room', {
                'fields': ['match', 'match_room_admin_link', 'linked_match_result_state'],
                'classes': ['collapse'],
            }),
            ('Scheduling', {
                'fields': ['scheduled_at', 'expires_at']
            }),
            ('Users & Actions', {
                'fields': ['created_by', 'accepted_by', 'resolved_by'],
                'classes': ['collapse']
            }),
            ('Visibility', {
                'fields': ['is_public', 'is_featured']
            }),
            ('Timestamps', {
                'fields': ['created_at', 'updated_at', 'accepted_at', 'completed_at', 'settled_at'],
                'classes': ['collapse']
            }),
        ]

        def get_queryset(self, request):
            return super().get_queryset(request).annotate(_result_submission_count=Count('result_submissions'))

        @admin.display(description='Submissions')
        def result_submissions_count(self, obj):
            return getattr(obj, '_result_submission_count', None) or obj.result_submissions.count()

        @admin.display(description='Escrow')
        def escrow_state(self, obj):
            if not obj.entry_fee_dc:
                return 'No entry'
            if obj.payout_txn_id:
                return 'Paid out'
            if obj.escrow_locked:
                return 'Locked'
            if obj.challenger_lock_txn_id:
                return 'Partial lock'
            return 'No lock'

        @admin.display(description='Match room')
        def match_room_admin_link(self, obj):
            if not obj.match_id or not getattr(obj.match, 'tournament_id', None):
                return '—'
            tournament = getattr(obj.match, 'tournament', None)
            if not tournament or not getattr(tournament, 'slug', ''):
                return '—'
            try:
                url = reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': obj.match_id})
            except NoReverseMatch:
                return '—'
            return format_html('<a href="{}" target="_blank">Open room</a>', url)

        @admin.display(description='Linked match result')
        def linked_match_result_state(self, obj):
            return _linked_match_result_admin_summary(getattr(obj, 'match', None))

        def _run_showdown_action(self, request, queryset, callback, success_label):
            success_count = 0
            error_count = 0
            for challenge in queryset:
                try:
                    callback(challenge)
                    success_count += 1
                except Exception as exc:
                    error_count += 1
                    self.message_user(
                        request,
                        f"{challenge.reference_code}: {exc}",
                        level=messages.ERROR,
                    )
            if success_count:
                self.message_user(request, f"{success_label}: {success_count}", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed: {error_count}", level=messages.WARNING)

        @admin.action(description='Settle selected confirmed Showdowns')
        def settle_confirmed_showdowns(self, request, queryset):
            self._run_showdown_action(
                request,
                queryset,
                lambda c: ChallengeService.admin_settle_confirmed_showdown(
                    challenge_id=c.pk,
                    resolved_by=request.user,
                    note=f"Settled from Django admin by {request.user.username}.",
                ),
                'Settled Showdowns',
            )

        @admin.action(description='Resolve disputed Showdowns: challenger wins')
        def resolve_disputes_as_challenger_win(self, request, queryset):
            self._resolve_disputes(request, queryset, 'CHALLENGER_WIN', 'Resolved as challenger win')

        @admin.action(description='Resolve disputed Showdowns: opponent wins')
        def resolve_disputes_as_challenged_win(self, request, queryset):
            self._resolve_disputes(request, queryset, 'CHALLENGED_WIN', 'Resolved as opponent win')

        @admin.action(description='Resolve disputed Showdowns: draw/refund')
        def resolve_disputes_as_draw(self, request, queryset):
            self._resolve_disputes(request, queryset, 'DRAW', 'Resolved as draw')

        def _resolve_disputes(self, request, queryset, result, success_label):
            self._run_showdown_action(
                request,
                queryset,
                lambda c: ChallengeService.admin_resolve_disputed_showdown(
                    challenge_id=c.pk,
                    resolved_by=request.user,
                    result=result,
                    note=f"{success_label} from Django admin by {request.user.username}.",
                ),
                success_label,
            )

        @admin.action(description='Void and refund selected Showdowns')
        def void_refund_showdowns(self, request, queryset):
            self._run_showdown_action(
                request,
                queryset,
                lambda c: ChallengeService.admin_void_refund_showdown(
                    challenge_id=c.pk,
                    resolved_by=request.user,
                    note=f"Voided and refunded from Django admin by {request.user.username}.",
                ),
                'Voided/refunded Showdowns',
            )

        @admin.action(description='Respawn missing Showdown match rooms')
        def respawn_missing_match_rooms(self, request, queryset):
            self._run_showdown_action(
                request,
                queryset.filter(match__isnull=True),
                lambda c: ChallengeService.admin_respawn_match_room(
                    challenge_id=c.pk,
                    actor=request.user,
                ),
                'Respawned match rooms',
            )

    # ── Bounty Admin ─────────────────────────────────────────────────────
    class BountyClaimInline(TabularInline):
        model = BountyClaim
        extra = 0
        can_delete = False
        readonly_fields = [
            'id', 'claiming_team', 'status', 'evidence_url', 'evidence_notes',
            'claimed_by', 'claimed_at', 'verified_by', 'verified_at',
            'entry_fee_lock_txn', 'outcome_txn', 'funded_by',
            'claim_match_room_link', 'closure_reason', 'closure_note',
        ]
        fields = readonly_fields

        def has_add_permission(self, request, obj=None):
            return False

        @admin.display(description='Match room')
        def claim_match_room_link(self, obj):
            return BountyClaimAdmin.match_room_admin_link_static(obj)

    @admin.register(Bounty)
    class BountyAdmin(ModelAdmin):
        """Admin interface for Bounty."""
        
        list_display = [
            'reference_code', 'title', 'issuer_team', 'game', 'status',
            'bounty_reward_display', 'claim_count', 'max_claims',
            'escrow_state', 'created_at',
        ]
        list_filter = ['status', 'bounty_type', 'reward_type', 'game', 'is_hitlist', 'escrow_locked', 'is_featured']
        search_fields = ['reference_code', 'title', 'issuer_team__name']
        readonly_fields = [
            'id', 'reference_code', 'status', 'reward_amount_dc',
            'escrow_locked', 'issuer_lock_txn', 'funded_by', 'claim_count',
            'is_hitlist', 'challenger_entry_fee_dc', 'closure_reason',
            'closure_note', 'created_at', 'updated_at', 'escrow_state',
        ]
        raw_id_fields = ['issuer_team', 'game', 'created_by', 'issuer_lock_txn', 'funded_by']
        date_hierarchy = 'created_at'
        inlines = [BountyClaimInline]
        actions = ['void_refund_bounties', 'expire_stale_bounties_action']
        
        fieldsets = [
            ('Bounty', {
                'fields': ['id', 'reference_code', 'title', 'description', 'status', 'bounty_type']
            }),
            ('Issuer & Game', {
                'fields': ['issuer_team', 'game']
            }),
            ('Criteria', {
                'fields': ['criteria'],
                'description': 'JSON defining achievement criteria for this bounty.'
            }),
            ('Reward', {
                'fields': ['reward_type', 'reward_amount', 'reward_amount_dc', 'reward_description']
            }),
            ('Escrow & Settlement', {
                'fields': [
                    'escrow_locked', 'issuer_lock_txn', 'funded_by',
                    'is_hitlist', 'challenger_entry_fee_dc',
                    'closure_reason', 'closure_note', 'escrow_state',
                ],
                'classes': ['collapse'],
            }),
            ('Limits', {
                'fields': ['max_claims', 'claim_count', 'expires_at']
            }),
            ('Visibility', {
                'fields': ['is_public', 'is_featured']
            }),
            ('Meta', {
                'fields': ['created_by', 'created_at', 'updated_at'],
                'classes': ['collapse']
            }),
        ]

        @admin.display(description='Reward')
        def bounty_reward_display(self, obj):
            if obj.reward_amount_dc:
                return f"{obj.reward_amount_dc} DC"
            return obj.reward_description or f"{obj.reward_amount} {obj.reward_type}"

        @admin.display(description='Escrow')
        def escrow_state(self, obj):
            if not obj.is_hitlist and not obj.reward_amount_dc:
                return 'No DC lock'
            if obj.status in ('CLAIMED', 'VERIFIED', 'PAID'):
                return 'Settled/consumed'
            if obj.escrow_locked:
                return 'Issuer reward locked'
            if obj.issuer_lock_txn_id:
                return 'Issuer lock released'
            return 'No lock'

        def _run_bounty_action(self, request, queryset, callback, success_label):
            success_count = 0
            error_count = 0
            for bounty in queryset:
                try:
                    callback(bounty)
                    success_count += 1
                except Exception as exc:
                    error_count += 1
                    self.message_user(
                        request,
                        f"{bounty.reference_code}: {exc}",
                        level=messages.ERROR,
                    )
            if success_count:
                self.message_user(request, f"{success_label}: {success_count}", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed: {error_count}", level=messages.WARNING)

        @admin.action(description='Void/refund selected Bounties')
        def void_refund_bounties(self, request, queryset):
            self._run_bounty_action(
                request,
                queryset,
                lambda b: BountyService.admin_void_refund_bounty(
                    bounty_id=b.pk,
                    resolved_by=request.user,
                    note=f"Voided/refunded from Django admin by {request.user.username}.",
                ),
                'Voided/refunded Bounties',
            )

        @admin.action(description='Expire selected stale Bounties')
        def expire_stale_bounties_action(self, request, queryset):
            self._run_bounty_action(
                request,
                queryset,
                lambda b: BountyService.admin_expire_bounty(
                    bounty_id=b.pk,
                    actor=request.user,
                    note=f"Expired from Django admin by {request.user.username}.",
                ),
                'Expired stale Bounties',
            )

    @admin.register(BountyClaim)
    class BountyClaimAdmin(ModelAdmin):
        """Admin interface for BountyClaim."""
        
        list_display = [
            'bounty', 'claiming_team', 'status', 'claim_escrow_state',
            'match_room_admin_link', 'linked_match_result_state', 'claimed_at', 'verified_at',
        ]
        list_filter = ['status', 'bounty__status', 'bounty__game', 'bounty__is_hitlist']
        search_fields = ['bounty__reference_code', 'claiming_team__name']
        readonly_fields = [
            'id', 'bounty', 'claiming_team', 'status', 'claimed_by',
            'claimed_at', 'verified_at', 'verified_by', 'entry_fee_lock_txn',
            'outcome_txn', 'funded_by', 'match', 'challenge', 'match_report',
            'closure_reason', 'closure_note', 'admin_notes',
            'match_room_admin_link', 'linked_match_result_state',
        ]
        raw_id_fields = [
            'bounty', 'claiming_team', 'claimed_by', 'verified_by',
            'challenge', 'match_report', 'entry_fee_lock_txn',
            'outcome_txn', 'funded_by', 'match',
        ]
        date_hierarchy = 'claimed_at'
        actions = [
            'approve_pending_claims',
            'reject_pending_claims',
            'respawn_missing_claim_match_rooms',
        ]

        fieldsets = [
            ('Claim', {
                'fields': ['id', 'bounty', 'claiming_team', 'status']
            }),
            ('Evidence', {
                'fields': ['evidence_url', 'evidence_notes']
            }),
            ('Review', {
                'fields': ['verified_by', 'verified_at', 'admin_notes', 'closure_reason', 'closure_note']
            }),
            ('Escrow & Settlement', {
                'fields': ['entry_fee_lock_txn', 'outcome_txn', 'funded_by'],
                'classes': ['collapse'],
            }),
            ('Match Room', {
                'fields': ['match', 'match_room_admin_link', 'linked_match_result_state', 'challenge', 'match_report'],
                'classes': ['collapse'],
            }),
            ('Submission', {
                'fields': ['claimed_by', 'claimed_at'],
                'classes': ['collapse'],
            }),
        ]

        @staticmethod
        def match_room_admin_link_static(obj):
            if not obj or not obj.match_id or not getattr(obj.match, 'tournament_id', None):
                return '—'
            tournament = getattr(obj.match, 'tournament', None)
            if not tournament or not getattr(tournament, 'slug', ''):
                return '—'
            try:
                url = reverse('tournaments:match_room', kwargs={'slug': tournament.slug, 'match_id': obj.match_id})
            except NoReverseMatch:
                return '—'
            return format_html('<a href="{}" target="_blank">Open room</a>', url)

        @admin.display(description='Match room')
        def match_room_admin_link(self, obj):
            return self.match_room_admin_link_static(obj)

        @admin.display(description='Linked match result')
        def linked_match_result_state(self, obj):
            match = getattr(obj, 'match', None) or getattr(getattr(obj, 'challenge', None), 'match', None)
            return _linked_match_result_admin_summary(match)

        @admin.display(description='Escrow')
        def claim_escrow_state(self, obj):
            if obj.outcome_txn_id:
                return 'Settled'
            if obj.entry_fee_lock_txn_id:
                return 'Entry locked'
            return 'No claim lock'

        def _run_claim_action(self, request, queryset, callback, success_label):
            success_count = 0
            error_count = 0
            for claim in queryset:
                try:
                    callback(claim)
                    success_count += 1
                except Exception as exc:
                    error_count += 1
                    self.message_user(
                        request,
                        f"{claim.pk}: {exc}",
                        level=messages.ERROR,
                    )
            if success_count:
                self.message_user(request, f"{success_label}: {success_count}", level=messages.SUCCESS)
            if error_count:
                self.message_user(request, f"Failed: {error_count}", level=messages.WARNING)

        @admin.action(description='Approve/verify selected pending Bounty claims')
        def approve_pending_claims(self, request, queryset):
            self._run_claim_action(
                request,
                queryset,
                lambda c: BountyService.admin_verify_claim(
                    claim_id=c.pk,
                    verified_by=request.user,
                    notes=f"Approved from Django admin by {request.user.username}.",
                ),
                'Approved Bounty claims',
            )

        @admin.action(description='Reject selected pending Bounty claims')
        def reject_pending_claims(self, request, queryset):
            self._run_claim_action(
                request,
                queryset,
                lambda c: BountyService.admin_reject_claim(
                    claim_id=c.pk,
                    verified_by=request.user,
                    notes=f"Rejected from Django admin by {request.user.username}.",
                ),
                'Rejected Bounty claims',
            )

        @admin.action(description='Respawn missing Bounty claim match rooms')
        def respawn_missing_claim_match_rooms(self, request, queryset):
            self._run_claim_action(
                request,
                queryset.filter(match__isnull=True),
                lambda c: BountyService.admin_respawn_claim_match_room(
                    claim_id=c.pk,
                    actor=request.user,
                ),
                'Respawned Bounty claim match rooms',
            )
