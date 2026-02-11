"""
Milestone Suggestion Service — auto-detects significant team achievements
and generates suggestion cards for the Hall of Fame manager.

Scans:
 1. Tournament placements (1st/2nd/3rd from TournamentResult in last 90 days)
 2. Ranking point milestones (large jumps from TeamRankingHistory in last 60 days)
 3. Team creation date (if not already a milestone)
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List

from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_milestone_suggestions(team) -> List[Dict[str, Any]]:
    """
    Return a list of suggested milestone dicts that haven't been added yet.
    Each dict: { key, title, description, date, milestone_type, icon }
    """
    suggestions: List[Dict[str, Any]] = []

    try:
        suggestions.extend(_suggest_tournament_placements(team))
    except Exception as e:
        logger.debug("Milestone suggestions: tournament scan error: %s", e)

    try:
        suggestions.extend(_suggest_ranking_milestones(team))
    except Exception as e:
        logger.debug("Milestone suggestions: ranking scan error: %s", e)

    try:
        suggestions.extend(_suggest_team_founded(team))
    except Exception as e:
        logger.debug("Milestone suggestions: founded scan error: %s", e)

    # Filter out any that already exist as journey milestones
    suggestions = _filter_existing(team, suggestions)

    # Also filter out dismissed suggestions
    suggestions = _filter_dismissed(team, suggestions)

    return suggestions[:8]  # Cap at 8 suggestions


def _suggest_tournament_placements(team) -> List[Dict[str, Any]]:
    """Find 1st/2nd/3rd place finishes in the last 90 days."""
    from apps.tournaments.models.result import TournamentResult

    cutoff = timezone.now() - timedelta(days=90)
    results = []

    # Winner (1st place)
    winners = TournamentResult.objects.filter(
        winner__team_id=team.id,
        created_at__gte=cutoff,
    ).select_related('tournament', 'winner')

    for r in winners:
        t_name = r.tournament.name if r.tournament else 'Tournament'
        results.append({
            'key': f'trophy-win-{r.tournament_id}',
            'title': f'Champions: {t_name}',
            'description': f'Won 1st place in {t_name}',
            'date': r.created_at.date().isoformat(),
            'milestone_type': 'TROPHY',
            'icon': '🏆',
        })

    # Runner-up (2nd place)
    runners = TournamentResult.objects.filter(
        runner_up__team_id=team.id,
        created_at__gte=cutoff,
    ).select_related('tournament')

    for r in runners:
        t_name = r.tournament.name if r.tournament else 'Tournament'
        results.append({
            'key': f'trophy-2nd-{r.tournament_id}',
            'title': f'Runner-Up: {t_name}',
            'description': f'Achieved 2nd place in {t_name}',
            'date': r.created_at.date().isoformat(),
            'milestone_type': 'TROPHY',
            'icon': '🥈',
        })

    # Third place
    thirds = TournamentResult.objects.filter(
        third_place__team_id=team.id,
        created_at__gte=cutoff,
    ).select_related('tournament')

    for r in thirds:
        t_name = r.tournament.name if r.tournament else 'Tournament'
        results.append({
            'key': f'trophy-3rd-{r.tournament_id}',
            'title': f'Top 3: {t_name}',
            'description': f'Achieved 3rd place in {t_name}',
            'date': r.created_at.date().isoformat(),
            'milestone_type': 'TROPHY',
            'icon': '🥉',
        })

    return results


def _suggest_ranking_milestones(team) -> List[Dict[str, Any]]:
    """Find significant ranking point gains in last 60 days."""
    from apps.teams.models.ranking import TeamRankingHistory

    cutoff = timezone.now() - timedelta(days=60)
    results = []

    # Big positive point changes (>= 100 points from tournament wins/placements)
    big_gains = TeamRankingHistory.objects.filter(
        team_id=team.id,
        created_at__gte=cutoff,
        points_change__gte=100,
        source__in=['tournament_winner', 'tournament_runner_up', 'tournament_top_4', 'achievement'],
    ).order_by('-points_change')[:3]

    for h in big_gains:
        source_labels = {
            'tournament_winner': 'Tournament Victory',
            'tournament_runner_up': 'Runner-Up Finish',
            'tournament_top_4': 'Top 4 Finish',
            'achievement': 'Achievement Unlocked',
        }
        label = source_labels.get(h.source, 'Ranking Milestone')
        results.append({
            'key': f'rank-{h.pk}',
            'title': f'{label}: +{h.points_change} pts',
            'description': h.reason or f'Ranking points increased from {h.points_before} to {h.points_after}',
            'date': h.created_at.date().isoformat(),
            'milestone_type': 'RANK_UP',
            'icon': '📈',
        })

    return results


def _suggest_team_founded(team) -> List[Dict[str, Any]]:
    """Suggest 'Team Established' if team creation isn't already a milestone."""
    if not team.created_at:
        return []

    return [{
        'key': f'founded-{team.id}',
        'title': f'{team.name} Established',
        'description': f'The beginning of the {team.name} journey',
        'date': team.created_at.date().isoformat(),
        'milestone_type': 'FOUNDED',
        'icon': '🏁',
    }]


def _filter_existing(team, suggestions: List[Dict]) -> List[Dict]:
    """Remove suggestions that already exist as journey milestones (by title similarity)."""
    from apps.organizations.models.journey import TeamJourneyMilestone

    existing = set(
        TeamJourneyMilestone.objects.filter(team=team)
        .values_list('title', flat=True)
    )
    # Also check by date+type combo
    existing_keys = set()
    for m in TeamJourneyMilestone.objects.filter(team=team).values('milestone_date', 'milestone_type'):
        existing_keys.add(f"{m['milestone_date'].isoformat()}-{m['milestone_type']}")

    filtered = []
    for s in suggestions:
        # Skip if exact title match
        if s['title'] in existing:
            continue
        # Skip if same date+type already exists
        date_type_key = f"{s['date']}-{s['milestone_type']}"
        if date_type_key in existing_keys:
            continue
        filtered.append(s)

    return filtered


def _filter_dismissed(team, suggestions: List[Dict]) -> List[Dict]:
    """Remove suggestions the user has previously dismissed (stored in team metadata)."""
    meta = getattr(team, 'metadata', None) or {}
    dismissed = set(meta.get('dismissed_milestone_suggestions', []))
    return [s for s in suggestions if s['key'] not in dismissed]
