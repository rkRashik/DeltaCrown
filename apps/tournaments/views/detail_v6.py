# apps/tournaments/views/detail_v6.py
"""
Enhanced Detail View V6 -     # Format prize distribution for template
    prize_distribution_formatted = None
    if hasattr(tournament, 'finance') and tournament.finance:
        try:
            prize_dist = tournament.finance.prize_distribution
            if prize_dist and isinstance(prize_dist, dict):
                prize_distribution_formatted = [
                    {
                        'position': key,
                        'amount': value
                    }
                    for key, value in sorted(prize_dist.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999)
                ]
                # Attach to finance for easy template access
                tournament.finance.prize_distribution_formatted = prize_distribution_formatted
        except Exception as e:
            print(f"Error formatting prize distribution: {e}")
    
    # Format timeline for template
    timeline_formatted = None
    if hasattr(tournament, 'schedule') and tournament.schedule:
        try:
            timeline = tournament.schedule.timeline
            if timeline and isinstance(timeline, list):
                timeline_formatted = timeline
                # Attach to schedule for easy template access
                tournament.schedule.timeline_formatted = timeline_formatted
        except Exception as e:
            print(f"Error formatting timeline: {e}")
    
    # Check payment status if registered Information Display
Passes all tournament data including rules, media, finance, schedule, capacity to template
"""
from __future__ import annotations
from typing import Any, Dict

from django.apps import apps
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.core.cache import cache

# Models
Tournament = apps.get_model("tournaments", "Tournament")
Registration = apps.get_model("tournaments", "Registration")


def tournament_detail_v6(request: HttpRequest, slug: str) -> HttpResponse:
    """
    V6 Enhanced tournament detail view with comprehensive data loading.
    
    Loads all related models:
    - Tournament (main model)
    - TournamentSchedule (dates, timeline)
    - TournamentCapacity (slots, registration limits)
    - TournamentFinance (prizes, entry fees)
    - TournamentRules (rules, requirements, restrictions)
    - TournamentMedia (banner, promotional images, rules PDF)
    - Organizer (user profile)
    
    Args:
        request: HTTP request object
        slug: Tournament slug
        
    Returns:
        Rendered tournament detail page with complete data
    """
    # Optimize queryset with all related objects
    tournament = get_object_or_404(
        Tournament.objects.select_related(
            'schedule',
            'capacity',
            'finance',
            'rules',
            'media',
            'organizer',
            'organizer__user'
        ).prefetch_related(
            'registrations',
            'registrations__user',
            'registrations__team'
        ),
        slug=slug
    )
    
    # Check user registration status
    user_registered = False
    if request.user.is_authenticated:
        try:
            user_profile = request.user.userprofile
            user_registered = Registration.objects.filter(
                tournament=tournament,
                user=user_profile,
                status__in=['PENDING', 'CONFIRMED']
            ).exists()
        except Exception:
            pass
    
    # Format prize distribution for template
    prize_distribution_formatted = None
    if hasattr(tournament, 'finance') and tournament.finance:
        try:
            prize_dist = tournament.finance.prize_distribution
            if prize_dist and isinstance(prize_dist, dict):
                prize_distribution_formatted = [
                    {
                        'position': key,
                        'amount': value
                    }
                    for key, value in sorted(prize_dist.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 999)
                ]
                # Attach to finance for easy template access
                tournament.finance.prize_distribution_formatted = prize_distribution_formatted
        except Exception as e:
            print(f"Error formatting prize distribution: {e}")
    
    # Check payment status if registered
    user_payment_complete = False
    if user_registered and hasattr(tournament, 'finance') and tournament.finance:
        if tournament.finance.entry_fee_bdt > 0:
            try:
                user_profile = request.user.userprofile
                registration = Registration.objects.filter(
                    tournament=tournament,
                    user=user_profile,
                    status__in=['PENDING', 'CONFIRMED']
                ).first()
                if registration:
                    user_payment_complete = registration.payment_status == 'PAID'
            except Exception:
                pass
    
    # Build context
    context = {
        'tournament': tournament,
        'user_registered': user_registered,
        'user_payment_complete': user_payment_complete,
        'page_title': f"{tournament.name} - Tournament Details",
    }
    
    return render(request, 'tournaments/detail_v7.html', context)
