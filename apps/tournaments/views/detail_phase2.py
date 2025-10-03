"""
Phase 2 Enhanced Detail View with Complete Model Integration

This view integrates all 6 Phase 1 models (Schedule, Capacity, Finance, 
Media, Rules, Archive) while maintaining backward compatibility with existing code.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional

from django.apps import apps
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.core.cache import cache

# Phase 1 Models
Tournament = apps.get_model("tournaments", "Tournament")
TournamentSchedule = apps.get_model("tournaments", "TournamentSchedule")
TournamentCapacity = apps.get_model("tournaments", "TournamentCapacity")
TournamentFinance = apps.get_model("tournaments", "TournamentFinance")
TournamentMedia = apps.get_model("tournaments", "TournamentMedia")
TournamentRules = apps.get_model("tournaments", "TournamentRules")
TournamentArchive = apps.get_model("tournaments", "TournamentArchive")
Registration = apps.get_model("tournaments", "Registration")
Match = apps.get_model("tournaments", "Match")


def get_optimized_tournament(slug: str) -> Tournament:
    """
    Get tournament with all Phase 1 models preloaded.
    Prevents N+1 queries by eagerly loading all relationships.
    """
    return get_object_or_404(
        Tournament.objects.select_related(
            'game',
            'organizer',
            'schedule',      # Phase 1
            'capacity',      # Phase 1
            'finance',       # Phase 1
            'media',         # Phase 1
            'rules',         # Phase 1
            'archive',       # Phase 1
            'settings'       # Legacy (for backward compatibility)
        ).prefetch_related(
            'registrations',
            'matches'
        ),
        slug=slug
    )


def build_schedule_context_v2(tournament: Tournament) -> Dict[str, Any]:
    """
    Build schedule context using Phase 1 TournamentSchedule model.
    Falls back to legacy fields if schedule model doesn't exist.
    """
    context = {
        'registration_start': None,
        'registration_end': None,
        'early_bird_deadline': None,
        'checkin_start': None,
        'checkin_end': None,
        'tournament_start': None,
        'tournament_end': None,
        'timezone': None,
        # Status flags
        'is_registration_open': False,
        'is_registration_upcoming': False,
        'is_checkin_open': False,
        'is_in_progress': False,
        'has_ended': False,
        # Time until events
        'days_until_start': None,
        'days_until_registration_end': None,
        'hours_until_checkin': None,
    }
    
    # Try Phase 1 model first
    if hasattr(tournament, 'schedule') and tournament.schedule:
        schedule = tournament.schedule
        context.update({
            'registration_start': schedule.registration_start,
            'registration_end': schedule.registration_end,
            'early_bird_deadline': schedule.early_bird_deadline,
            'checkin_start': schedule.checkin_start,
            'checkin_end': schedule.checkin_end,
            'tournament_start': schedule.tournament_start,
            'tournament_end': schedule.tournament_end,
            'timezone': schedule.timezone,
            # Status flags (from helper methods)
            'is_registration_open': schedule.is_registration_open(),
            'is_registration_upcoming': schedule.is_registration_upcoming(),
            'is_checkin_open': schedule.is_checkin_open(),
            'is_in_progress': schedule.is_in_progress(),
            'has_ended': schedule.has_ended(),
            # Time calculations
            'days_until_start': schedule.get_days_until_start(),
            'days_until_registration_end': schedule.get_days_until_registration_end(),
        })
        
        # Calculate hours until checkin
        if schedule.checkin_start:
            now = timezone.now()
            if now < schedule.checkin_start:
                delta = schedule.checkin_start - now
                context['hours_until_checkin'] = int(delta.total_seconds() / 3600)
    
    # Fallback to legacy fields
    else:
        settings = tournament.settings if hasattr(tournament, 'settings') else None
        if settings:
            context['registration_start'] = getattr(settings, 'reg_open_at', None)
            context['registration_end'] = getattr(settings, 'reg_close_at', None)
        
        context['tournament_start'] = tournament.start_at if hasattr(tournament, 'start_at') else None
        context['tournament_end'] = tournament.end_at if hasattr(tournament, 'end_at') else None
        
        # Calculate basic status flags
        now = timezone.now()
        if context['registration_start'] and context['registration_end']:
            context['is_registration_open'] = (
                context['registration_start'] <= now <= context['registration_end']
            )
        
        if context['tournament_start']:
            if context['tournament_end']:
                context['is_in_progress'] = (
                    context['tournament_start'] <= now <= context['tournament_end']
                )
            context['has_ended'] = now > context['tournament_start']
    
    return context


def build_capacity_context_v2(tournament: Tournament) -> Dict[str, Any]:
    """
    Build capacity context using Phase 1 TournamentCapacity model.
    Falls back to legacy fields if capacity model doesn't exist.
    """
    context = {
        'min_teams': None,
        'max_teams': None,
        'current_teams': 0,
        'min_players_per_team': None,
        'max_players_per_team': None,
        'enable_waitlist': False,
        'waitlist_capacity': 0,
        'current_waitlist': 0,
        # Status
        'capacity_status': 'UNKNOWN',
        'is_full': False,
        'waitlist_full': False,
        # Computed
        'fill_percentage': 0,
        'available_slots': 0,
        'waitlist_available_slots': 0,
        'can_register': False,
    }
    
    # Try Phase 1 model first
    if hasattr(tournament, 'capacity') and tournament.capacity:
        capacity = tournament.capacity
        context.update({
            'min_teams': capacity.min_teams,
            'max_teams': capacity.max_teams,
            'current_teams': capacity.current_teams,
            'min_players_per_team': capacity.min_players_per_team,
            'max_players_per_team': capacity.max_players_per_team,
            'enable_waitlist': capacity.enable_waitlist,
            'waitlist_capacity': capacity.waitlist_capacity,
            'current_waitlist': capacity.current_waitlist,
            # Status
            'capacity_status': capacity.capacity_status,
            'is_full': capacity.is_full,
            'waitlist_full': capacity.waitlist_full,
            # Computed (from helper methods)
            'fill_percentage': capacity.get_fill_percentage(),
            'available_slots': capacity.get_available_slots(),
            'waitlist_available_slots': capacity.get_waitlist_available_slots(),
            'can_register': capacity.can_accept_more_teams(),
        })
    
    # Fallback to legacy fields
    else:
        settings = tournament.settings if hasattr(tournament, 'settings') else None
        if settings:
            context['max_teams'] = getattr(settings, 'slot_size', None) or getattr(settings, 'max_teams', None)
            context['min_players_per_team'] = getattr(settings, 'min_team_size', None)
            context['max_players_per_team'] = getattr(settings, 'max_team_size', None)
        
        # Count current registrations
        confirmed_count = Registration.objects.filter(
            tournament=tournament,
            status='CONFIRMED'
        ).count()
        context['current_teams'] = confirmed_count
        
        # Calculate basic metrics
        if context['max_teams']:
            context['fill_percentage'] = int((confirmed_count / context['max_teams']) * 100)
            context['available_slots'] = max(0, context['max_teams'] - confirmed_count)
            context['is_full'] = confirmed_count >= context['max_teams']
            context['can_register'] = confirmed_count < context['max_teams']
            
            if context['fill_percentage'] >= 100:
                context['capacity_status'] = 'FULL'
            elif context['fill_percentage'] >= 90:
                context['capacity_status'] = 'WAITLIST'
            elif context['fill_percentage'] >= 70:
                context['capacity_status'] = 'FILLING'
            else:
                context['capacity_status'] = 'AVAILABLE'
    
    return context


def build_finance_context_v2(tournament: Tournament) -> Dict[str, Any]:
    """
    Build finance context using Phase 1 TournamentFinance model.
    Falls back to legacy fields if finance model doesn't exist.
    """
    context = {
        'entry_fee': 0,
        'currency': 'BDT',
        'early_bird_fee': None,
        'late_registration_fee': None,
        'prize_pool': 0,
        'prize_currency': 'BDT',
        'prize_distribution': {},
        'total_revenue': 0,
        'total_paid_out': 0,
        # Formatted displays
        'entry_fee_formatted': 'Free',
        'prize_pool_formatted': 'TBD',
        'total_revenue_formatted': '৳0',
        # Computed
        'is_free': True,
        'has_prizes': False,
        'profit': 0,
        'estimated_revenue': 0,
        'revenue_per_team': 0,
    }
    
    # Try Phase 1 model first
    if hasattr(tournament, 'finance') and tournament.finance:
        finance = tournament.finance
        context.update({
            'entry_fee': finance.entry_fee,
            'currency': finance.currency,
            'early_bird_fee': finance.early_bird_fee,
            'late_registration_fee': finance.late_registration_fee,
            'prize_pool': finance.prize_pool,
            'prize_currency': finance.prize_currency,
            'prize_distribution': finance.prize_distribution,
            'total_revenue': finance.total_revenue,
            'total_paid_out': finance.total_paid_out,
            # Formatted displays (from helper methods)
            'entry_fee_formatted': finance.get_formatted_entry_fee(),
            'prize_pool_formatted': finance.get_formatted_prize_pool(),
            'total_revenue_formatted': finance.get_formatted_total_revenue(),
            # Computed
            'is_free': finance.is_free_tournament(),
            'has_prizes': finance.has_prize_pool(),
            'profit': finance.calculate_profit(),
            'estimated_revenue': finance.calculate_estimated_revenue(),
            'revenue_per_team': finance.calculate_revenue_per_team(),
        })
    
    # Fallback to legacy fields
    else:
        if hasattr(tournament, 'entry_fee_bdt'):
            context['entry_fee'] = tournament.entry_fee_bdt or 0
            context['is_free'] = context['entry_fee'] == 0
            context['entry_fee_formatted'] = f"৳{context['entry_fee']:,}" if context['entry_fee'] > 0 else 'Free'
        
        if hasattr(tournament, 'prize_pool_bdt'):
            context['prize_pool'] = tournament.prize_pool_bdt or 0
            context['has_prizes'] = context['prize_pool'] > 0
            context['prize_pool_formatted'] = f"৳{context['prize_pool']:,}" if context['prize_pool'] > 0 else 'TBD'
    
    return context


def build_media_context_v2(tournament: Tournament) -> Dict[str, Any]:
    """
    Build media context using Phase 1 TournamentMedia model.
    Falls back to legacy fields if media model doesn't exist.
    """
    context = {
        'logo': None,
        'logo_alt': '',
        'banner': None,
        'banner_alt': '',
        'thumbnail': None,
        'thumbnail_alt': '',
        'stream_url': None,
        'stream_embed_code': None,
        # Display settings
        'show_logo_on_card': True,
        'show_banner_on_card': True,
        'show_logo_on_detail': True,
        'show_banner_on_detail': True,
        # URLs
        'logo_url': None,
        'banner_url': None,
        'thumbnail_url': None,
    }
    
    # Try Phase 1 model first
    if hasattr(tournament, 'media') and tournament.media:
        media = tournament.media
        context.update({
            'logo': media.logo,
            'logo_alt': media.logo_alt_text,
            'banner': media.banner,
            'banner_alt': media.banner_alt_text,
            'thumbnail': media.thumbnail,
            'thumbnail_alt': media.thumbnail_alt_text,
            'stream_url': media.stream_url,
            'stream_embed_code': media.stream_embed_code,
            # Display settings
            'show_logo_on_card': media.show_logo_on_card,
            'show_banner_on_card': media.show_banner_on_card,
            'show_logo_on_detail': media.show_logo_on_detail,
            'show_banner_on_detail': media.show_banner_on_detail,
            # URLs
            'logo_url': media.logo.url if media.logo else None,
            'banner_url': media.banner.url if media.banner else None,
            'thumbnail_url': media.thumbnail.url if media.thumbnail else None,
        })
    
    # Fallback to legacy fields
    else:
        if hasattr(tournament, 'banner') and tournament.banner:
            context['banner'] = tournament.banner
            context['banner_url'] = tournament.banner.url
        
        if hasattr(tournament, 'thumbnail') and tournament.thumbnail:
            context['thumbnail'] = tournament.thumbnail
            context['thumbnail_url'] = tournament.thumbnail.url
    
    return context


def build_rules_context_v2(tournament: Tournament) -> Dict[str, Any]:
    """
    Build rules context using Phase 1 TournamentRules model.
    Falls back to legacy fields if rules model doesn't exist.
    """
    context = {
        'general_rules': '',
        'eligibility_requirements': '',
        'match_rules': '',
        'scoring_system': '',
        'penalty_rules': '',
        'prize_distribution_rules': '',
        'additional_notes': '',
        'checkin_instructions': '',
        # Requirements
        'require_discord': False,
        'require_game_id': False,
        'require_team_logo': False,
        # Restrictions
        'min_age': None,
        'max_age': None,
        'region_restriction': '',
        'rank_restriction': '',
        # Computed
        'has_age_restriction': False,
        'has_region_restriction': False,
        'has_rank_restriction': False,
        'requirements_list': [],
    }
    
    # Try Phase 1 model first
    if hasattr(tournament, 'rules') and tournament.rules:
        rules = tournament.rules
        context.update({
            'general_rules': rules.general_rules,
            'eligibility_requirements': rules.eligibility_requirements,
            'match_rules': rules.match_rules,
            'scoring_system': rules.scoring_system,
            'penalty_rules': rules.penalty_rules,
            'prize_distribution_rules': rules.prize_distribution_rules,
            'additional_notes': rules.additional_notes,
            'checkin_instructions': rules.checkin_instructions,
            # Requirements
            'require_discord': rules.require_discord,
            'require_game_id': rules.require_game_id,
            'require_team_logo': rules.require_team_logo,
            # Restrictions
            'min_age': rules.min_age,
            'max_age': rules.max_age,
            'region_restriction': rules.region_restriction,
            'rank_restriction': rules.rank_restriction,
            # Computed (from helper methods)
            'has_age_restriction': rules.has_age_restriction(),
            'has_region_restriction': rules.has_region_restriction(),
            'has_rank_restriction': rules.has_rank_restriction(),
        })
        
        # Build requirements list
        requirements = []
        if rules.require_discord:
            requirements.append('Discord account')
        if rules.require_game_id:
            requirements.append('Game ID verification')
        if rules.require_team_logo:
            requirements.append('Team logo')
        context['requirements_list'] = requirements
    
    # Fallback to legacy fields
    else:
        settings = tournament.settings if hasattr(tournament, 'settings') else None
        if settings:
            if hasattr(settings, 'rules_html'):
                context['general_rules'] = settings.rules_html
            elif hasattr(settings, 'rules_text'):
                context['general_rules'] = settings.rules_text
    
    return context


def build_archive_context_v2(tournament: Tournament) -> Dict[str, Any]:
    """
    Build archive context using Phase 1 TournamentArchive model.
    """
    context = {
        'archive_type': 'ACTIVE',
        'is_archived': False,
        'archived_at': None,
        'archive_reason': '',
        'is_clone': False,
        'clone_number': 0,
        'source_tournament': None,
        'can_restore': True,
        'preserve_participants': True,
        'preserve_matches': True,
        'preserve_media': True,
    }
    
    # Try Phase 1 model
    if hasattr(tournament, 'archive') and tournament.archive:
        archive = tournament.archive
        context.update({
            'archive_type': archive.archive_type,
            'is_archived': archive.is_archived,
            'archived_at': archive.archived_at,
            'archive_reason': archive.archive_reason,
            'is_clone': archive.is_clone(),
            'clone_number': archive.clone_number,
            'source_tournament': archive.source_tournament,
            'can_restore': archive.can_restore,
            'preserve_participants': archive.preserve_participants,
            'preserve_matches': archive.preserve_matches,
            'preserve_media': archive.preserve_media,
        })
    
    return context


def can_view_sensitive(user, tournament: Tournament) -> bool:
    """
    Check if user can view sensitive data (participants, bracket).
    Uses Phase 1 Schedule model if available.
    """
    # Staff can always view
    if user and hasattr(user, 'user') and getattr(user.user, 'is_staff', False):
        return True
    
    # Tournament must have started
    now = timezone.now()
    
    # Use Phase 1 Schedule model
    if hasattr(tournament, 'schedule') and tournament.schedule:
        if not tournament.schedule.has_started():
            return False
    # Fallback to legacy field
    elif hasattr(tournament, 'start_at'):
        if tournament.start_at and now < tournament.start_at:
            return False
    else:
        return False
    
    # User must be registered
    if not user or not user.is_authenticated:
        return False
    
    # Check if user is registered
    is_registered = Registration.objects.filter(
        tournament=tournament,
        user=user,
        status='CONFIRMED'
    ).exists()
    
    return is_registered


def detail_phase2(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Phase 2 Enhanced Tournament Detail View
    
    Integrates all 6 Phase 1 models while maintaining backward compatibility.
    
    Features:
    - Uses TournamentSchedule for all date/time logic
    - Uses TournamentCapacity for registration slots
    - Uses TournamentFinance for pricing and prizes
    - Uses TournamentMedia for all media assets
    - Uses TournamentRules for rules and requirements
    - Uses TournamentArchive for archive status
    - Falls back to legacy fields when Phase 1 models don't exist
    - Optimized queries (single DB hit with select_related)
    """
    
    # Get tournament with all Phase 1 models preloaded
    tournament = get_optimized_tournament(slug)
    
    # Build comprehensive context using Phase 1 models
    schedule_ctx = build_schedule_context_v2(tournament)
    capacity_ctx = build_capacity_context_v2(tournament)
    finance_ctx = build_finance_context_v2(tournament)
    media_ctx = build_media_context_v2(tournament)
    rules_ctx = build_rules_context_v2(tournament)
    archive_ctx = build_archive_context_v2(tournament)
    
    # Permission checks
    user_profile = getattr(request.user, 'profile', None) if request.user.is_authenticated else None
    user_can_view_sensitive = can_view_sensitive(user_profile, tournament)
    
    # Check if user is registered
    user_is_registered = False
    if user_profile:
        user_is_registered = Registration.objects.filter(
            tournament=tournament,
            user=user_profile,
            status__in=['PENDING', 'CONFIRMED']
        ).exists()
    
    # Build comprehensive context
    ctx = {
        # Tournament basics
        'tournament': tournament,
        'title': tournament.name,
        'description': tournament.description if hasattr(tournament, 'description') else '',
        'status': tournament.status if hasattr(tournament, 'status') else 'UNKNOWN',
        'game': tournament.game,
        
        # Phase 1 Model Contexts
        'schedule': schedule_ctx,
        'capacity': capacity_ctx,
        'finance': finance_ctx,
        'media': media_ctx,
        'rules': rules_ctx,
        'archive': archive_ctx,
        
        # Permissions
        'can_view_sensitive': user_can_view_sensitive,
        'is_registered_user': user_is_registered,
        'can_register': (
            schedule_ctx['is_registration_open'] and 
            capacity_ctx['can_register'] and
            not archive_ctx['is_archived']
        ),
        
        # UI State
        'active_tab': request.GET.get('tab', 'overview'),
        'show_live': tournament.status == 'RUNNING' if hasattr(tournament, 'status') else False,
        
        # URLs
        'register_url': f'/tournaments/register-modern/{slug}/',
        'api_state_url': f'/tournaments/api/{slug}/state/',
    }
    
    return render(request, 'tournaments/detail_phase2.html', ctx)

