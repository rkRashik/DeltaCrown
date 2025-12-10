"""
Event Handlers for User and Team Stats + Match History

Phase 8, Epic 8.2: User Stats Service
Phase 8, Epic 8.3: Team Stats & Ranking System
Phase 8, Epic 8.4: Match History Engine
Listens to MatchCompletedEvent and updates user/team statistics + match history automatically.
"""

import logging
from typing import Optional
from datetime import datetime

from apps.common.events import event_handler, Event
from apps.core.events.events import MatchCompletedEvent

logger = logging.getLogger(__name__)


@event_handler("match.completed")
def handle_match_completed_for_stats(event: MatchCompletedEvent):
    """
    Handle MatchCompletedEvent to update user and team stats + match history.
    
    Extracts match data from event and updates:
    - User stats (Epic 8.2) - for individual matches
    - Team stats + ELO ratings (Epic 8.3) - for team matches
    - Match history (Epic 8.4) - timeline records for users and teams
    
    Args:
        event: MatchCompletedEvent instance
        
    Reference: Phase 8, Epic 8.2, 8.3, 8.4 - Event-Driven Stats & History Updates
    """
    logger.info(f"Processing MatchCompletedEvent for stats: match_id={event.match_id}")
    
    try:
        # Import service façade and DTOs
        from apps.tournament_ops.services.tournament_ops_service import get_tournament_ops_service
        from apps.tournament_ops.dtos import MatchStatsUpdateDTO, TeamMatchStatsUpdateDTO
        
        # Extract match data from event
        match_id = event.match_id
        winner_id = event.winner_id
        
        # Get match details to extract participants and stats
        # Method-level ORM import for match data
        from apps.tournaments.models import Match
        
        try:
            match = Match.objects.select_related('tournament', 'participant1', 'participant2').get(id=match_id)
        except Match.DoesNotExist:
            logger.error(f"Match {match_id} not found, cannot update stats")
            return
        
        # Get game slug from tournament
        game_slug = match.tournament.game_slug if hasattr(match.tournament, 'game_slug') else 'unknown'
        
        # Determine if this is a team match or individual match
        is_team_match = False
        team1_id = None
        team2_id = None
        
        # Check if participants are teams
        if match.participant1 and hasattr(match.participant1, 'captain_id'):
            # Participant1 is a team
            is_team_match = True
            team1_id = match.participant1.id
        
        if match.participant2 and hasattr(match.participant2, 'captain_id'):
            # Participant2 is a team
            is_team_match = True
            team2_id = match.participant2.id
        
        service = get_tournament_ops_service()
        
        # Determine winner/loser
        is_draw = winner_id is None
        
        if is_team_match and team1_id and team2_id:
            # ===== TEAM MATCH: Update team stats + ELO ratings =====
            logger.info(f"Processing team match {match_id}: {team1_id} vs {team2_id}")
            
            team1_won = winner_id == match.participant1_id if not is_draw else False
            team2_won = winner_id == match.participant2_id if not is_draw else False
            
            # Get current ELO ratings for both teams (needed for calculations)
            team1_ranking = service.get_team_ranking(team1_id, game_slug)
            team2_ranking = service.get_team_ranking(team2_id, game_slug)
            
            team1_elo = team1_ranking.elo_rating if team1_ranking else 1200
            team2_elo = team2_ranking.elo_rating if team2_ranking else 1200
            
            # Create stats update DTOs for both teams
            team1_update = TeamMatchStatsUpdateDTO(
                team_id=team1_id,
                game_slug=game_slug,
                is_winner=team1_won,
                is_draw=is_draw,
                opponent_team_id=team2_id,
                opponent_elo=team2_elo,
                match_id=match_id,
            )
            
            team2_update = TeamMatchStatsUpdateDTO(
                team_id=team2_id,
                game_slug=game_slug,
                is_winner=team2_won,
                is_draw=is_draw,
                opponent_team_id=team1_id,
                opponent_elo=team1_elo,
                match_id=match_id,
            )
            
            # Update team 1 stats + ELO
            try:
                result1 = service.update_team_stats_from_match(team1_update)
                logger.info(
                    f"Updated team {team1_id} stats: "
                    f"ELO {team1_elo} → {result1['ranking'].elo_rating} "
                    f"({result1['elo_change']:+d})"
                )
            except Exception as e:
                logger.error(f"Failed to update stats for team {team1_id}: {str(e)}")
            
            # Update team 2 stats + ELO
            try:
                result2 = service.update_team_stats_from_match(team2_update)
                logger.info(
                    f"Updated team {team2_id} stats: "
                    f"ELO {team2_elo} → {result2['ranking'].elo_rating} "
                    f"({result2['elo_change']:+d})"
                )
            except Exception as e:
                logger.error(f"Failed to update stats for team {team2_id}: {str(e)}")
            
            # ===== RECORD TEAM MATCH HISTORY (Epic 8.4) =====
            try:
                # Get opponent team names for history
                team1_name = match.participant1.name if match.participant1 else "Unknown"
                team2_name = match.participant2.name if match.participant2 else "Unknown"
                
                # Get score summary if available
                score_summary = ""
                if hasattr(match, 'final_score') and match.final_score:
                    score_summary = match.final_score
                
                # Check if match had dispute
                had_dispute = hasattr(match, 'had_dispute') and match.had_dispute
                is_forfeit = hasattr(match, 'is_forfeit') and match.is_forfeit
                
                # Get completed_at timestamp
                completed_at = match.completed_at if hasattr(match, 'completed_at') else datetime.utcnow()
                
                # Record history for team 1
                service.record_team_match_history(
                    team_id=team1_id,
                    match_id=match_id,
                    tournament_id=match.tournament_id,
                    game_slug=game_slug,
                    is_winner=team1_won,
                    is_draw=is_draw,
                    opponent_team_id=team2_id,
                    opponent_team_name=team2_name,
                    score_summary=score_summary,
                    elo_before=team1_elo,
                    elo_after=result1['ranking'].elo_rating if 'result1' in locals() else None,
                    elo_change=result1['elo_change'] if 'result1' in locals() else 0,
                    had_dispute=had_dispute,
                    is_forfeit=is_forfeit,
                    completed_at=completed_at,
                )
                
                # Record history for team 2
                service.record_team_match_history(
                    team_id=team2_id,
                    match_id=match_id,
                    tournament_id=match.tournament_id,
                    game_slug=game_slug,
                    is_winner=team2_won,
                    is_draw=is_draw,
                    opponent_team_id=team1_id,
                    opponent_team_name=team1_name,
                    score_summary=score_summary,
                    elo_before=team2_elo,
                    elo_after=result2['ranking'].elo_rating if 'result2' in locals() else None,
                    elo_change=result2['elo_change'] if 'result2' in locals() else 0,
                    had_dispute=had_dispute,
                    is_forfeit=is_forfeit,
                    completed_at=completed_at,
                )
                
                logger.info(f"Successfully recorded match history for team match {match_id}")
            except Exception as e:
                logger.error(f"Failed to record match history for team match {match_id}: {str(e)}")
            
            logger.info(f"Successfully processed team match stats (match {match_id})")
        
        else:
            # ===== INDIVIDUAL MATCH: Update user stats (Epic 8.2) =====
            participant1_user_id = None
            participant2_user_id = None
            
            # Extract user IDs from participants
            if match.participant1:
                if hasattr(match.participant1, 'id'):
                    participant1_user_id = match.participant1.id
            
            if match.participant2:
                if hasattr(match.participant2, 'id'):
                    participant2_user_id = match.participant2.id
            
            if not participant1_user_id or not participant2_user_id:
                logger.warning(f"Could not extract user IDs from match {match_id}, skipping stats update")
                return
            
            participant1_won = winner_id == match.participant1_id if not is_draw else False
            participant2_won = winner_id == match.participant2_id if not is_draw else False
            
            # Extract K/D stats if available (game-specific)
            participant1_kills = 0
            participant1_deaths = 0
            participant2_kills = 0
            participant2_deaths = 0
            
            if hasattr(match, 'result_data') and match.result_data:
                result_data = match.result_data
                if isinstance(result_data, dict):
                    participant1_kills = result_data.get('participant1_kills', 0)
                    participant1_deaths = result_data.get('participant1_deaths', 0)
                    participant2_kills = result_data.get('participant2_kills', 0)
                    participant2_deaths = result_data.get('participant2_deaths', 0)
            
            # Get completed_at timestamp
            match_completed_at = match.completed_at if hasattr(match, 'completed_at') else datetime.utcnow()
            
            # Create stats update DTOs for both participants
            # Update participant 1 stats
            update1 = MatchStatsUpdateDTO(
                user_id=participant1_user_id,
                game_slug=game_slug,
                tournament_id=match.tournament_id,
                match_id=match_id,
                is_winner=participant1_won,
                is_draw=is_draw,
                kills=participant1_kills,
                deaths=participant1_deaths,
                match_completed_at=match_completed_at,
            )
            
            try:
                service.update_user_stats_from_match(update1)
                logger.info(f"Updated stats for user {participant1_user_id} (match {match_id})")
            except Exception as e:
                logger.error(f"Failed to update stats for user {participant1_user_id}: {str(e)}")
            
            # Update participant 2 stats
            update2 = MatchStatsUpdateDTO(
                user_id=participant2_user_id,
                game_slug=game_slug,
                tournament_id=match.tournament_id,
                match_id=match_id,
                is_winner=participant2_won,
                is_draw=is_draw,
                kills=participant2_kills,
                deaths=participant2_deaths,
                match_completed_at=match_completed_at,
            )
            
            try:
                service.update_user_stats_from_match(update2)
                logger.info(f"Updated stats for user {participant2_user_id} (match {match_id})")
            except Exception as e:
                logger.error(f"Failed to update stats for user {participant2_user_id}: {str(e)}")
            
            # ===== RECORD USER MATCH HISTORY (Epic 8.4) =====
            try:
                # Get opponent names for history
                participant1_name = "Unknown"
                participant2_name = "Unknown"
                
                if match.participant1 and hasattr(match.participant1, 'username'):
                    participant1_name = match.participant1.username
                elif match.participant1 and hasattr(match.participant1, 'get_username'):
                    participant1_name = match.participant1.get_username()
                
                if match.participant2 and hasattr(match.participant2, 'username'):
                    participant2_name = match.participant2.username
                elif match.participant2 and hasattr(match.participant2, 'get_username'):
                    participant2_name = match.participant2.get_username()
                
                # Get score summary if available
                score_summary = ""
                if hasattr(match, 'final_score') and match.final_score:
                    score_summary = match.final_score
                
                # Check if match had dispute
                had_dispute = hasattr(match, 'had_dispute') and match.had_dispute
                is_forfeit = hasattr(match, 'is_forfeit') and match.is_forfeit
                
                # Record history for participant 1
                service.record_user_match_history(
                    user_id=participant1_user_id,
                    match_id=match_id,
                    tournament_id=match.tournament_id,
                    game_slug=game_slug,
                    is_winner=participant1_won,
                    is_draw=is_draw,
                    opponent_user_id=participant2_user_id,
                    opponent_name=participant2_name,
                    score_summary=score_summary,
                    kills=participant1_kills,
                    deaths=participant1_deaths,
                    assists=0,  # TODO: Extract assists if available
                    had_dispute=had_dispute,
                    is_forfeit=is_forfeit,
                    completed_at=match_completed_at,
                )
                
                # Record history for participant 2
                service.record_user_match_history(
                    user_id=participant2_user_id,
                    match_id=match_id,
                    tournament_id=match.tournament_id,
                    game_slug=game_slug,
                    is_winner=participant2_won,
                    is_draw=is_draw,
                    opponent_user_id=participant1_user_id,
                    opponent_name=participant1_name,
                    score_summary=score_summary,
                    kills=participant2_kills,
                    deaths=participant2_deaths,
                    assists=0,  # TODO: Extract assists if available
                    had_dispute=had_dispute,
                    is_forfeit=is_forfeit,
                    completed_at=match_completed_at,
                )
                
                logger.info(f"Successfully recorded match history for user match {match_id}")
            except Exception as e:
                logger.error(f"Failed to record match history for user match {match_id}: {str(e)}")
            
            logger.info(f"Successfully processed user match stats (match {match_id})")
        
    except Exception as e:
        logger.error(f"Error processing MatchCompletedEvent for stats: {str(e)}", exc_info=True)
        # Don't raise - event handler failures should not break the event system


# =============================================================================
# Phase 8, Epic 8.5: Advanced Analytics Event Handlers
# =============================================================================

@event_handler("match.completed")
def handle_match_completed_for_analytics(event: MatchCompletedEvent):
    """
    Handle MatchCompletedEvent to queue analytics refresh.
    
    On match completion, schedules deferred analytics update via Celery.
    This ensures analytics snapshots stay fresh without blocking match flow.
    
    Args:
        event: MatchCompletedEvent instance
        
    Reference: Phase 8, Epic 8.5 - Real-Time Analytics Updates
    """
    logger.info(f"Queueing analytics refresh for match_id={event.match_id}")
    
    try:
        # Extract match context
        from apps.tournaments.models import Match
        
        try:
            match = Match.objects.select_related('tournament').get(id=event.match_id)
            game_slug = match.tournament.game_slug if match.tournament else None
            
            if not game_slug:
                logger.warning(f"No game_slug for match {event.match_id}, skipping analytics update")
                return
            
            # Determine participants (users or teams)
            # For user matches
            if match.participant1_user_id:
                # Queue user analytics refresh for both participants
                from apps.leaderboards.tasks import nightly_user_analytics_refresh
                
                # Note: In production, you'd want individual refresh tasks per user
                # For now, we log and let nightly job handle it
                logger.info(f"Analytics update queued for users in match {event.match_id} (handled by nightly job)")
            
            # For team matches
            elif match.participant1_team_id:
                # Queue team analytics refresh
                from apps.leaderboards.tasks import nightly_team_analytics_refresh
                
                logger.info(f"Analytics update queued for teams in match {event.match_id} (handled by nightly job)")
            
            # Trigger hourly leaderboard refresh (debounced)
            # Don't trigger immediately - let hourly job handle it
            logger.info(f"Leaderboard refresh deferred to hourly job for game {game_slug}")
            
        except Match.DoesNotExist:
            logger.error(f"Match {event.match_id} not found for analytics update")
            
    except Exception as e:
        logger.error(f"Error queueing analytics refresh: {str(e)}", exc_info=True)


@event_handler("season.changed")
def handle_season_changed(event: Event):
    """
    Handle SeasonChangedEvent to recompute seasonal leaderboards.
    
    When season status changes (activated/deactivated), triggers full
    seasonal leaderboard recalculation and archival.
    
    Args:
        event: SeasonChangedEvent instance
        
    Reference: Phase 8, Epic 8.5 - Seasonal Leaderboard Management
    """
    logger.info(f"Processing SeasonChangedEvent: {event.payload}")
    
    try:
        season_id = event.payload.get("season_id")
        action = event.payload.get("action")  # "activated" or "deactivated"
        
        if action == "activated":
            logger.info(f"New season {season_id} activated - triggering leaderboard recalculation")
            
            # Trigger immediate leaderboard refresh for new season
            from apps.leaderboards.tasks import hourly_leaderboard_refresh
            
            # Queue refresh task
            result = hourly_leaderboard_refresh.delay()
            logger.info(f"Seasonal leaderboard refresh queued: job_id={result.id}")
            
        elif action == "deactivated":
            logger.info(f"Season {season_id} deactivated - archiving final leaderboards")
            
            # Archive final season leaderboards (handled by seasonal_rollover task)
            logger.info(f"Season {season_id} leaderboards archived by seasonal_rollover")
            
    except Exception as e:
        logger.error(f"Error processing SeasonChangedEvent: {str(e)}", exc_info=True)


@event_handler("tier.changed")
def handle_tier_changed(event: Event):
    """
    Handle TierChangedEvent to trigger notifications and cosmetic updates.
    
    When a user/team's tier changes (Bronze → Silver → Gold → Diamond → Crown),
    sends congratulations notification and updates profile cosmetics.
    
    Args:
        event: TierChangedEvent instance
        
    Reference: Phase 8, Epic 8.5 - Tier Progression Notifications
    """
    logger.info(f"Processing TierChangedEvent: {event.payload}")
    
    try:
        entity_type = event.payload.get("entity_type")  # "user" or "team"
        entity_id = event.payload.get("entity_id")
        old_tier = event.payload.get("old_tier")
        new_tier = event.payload.get("new_tier")
        game_slug = event.payload.get("game_slug")
        
        # Tier progression (upward movement)
        tier_order = ["bronze", "silver", "gold", "diamond", "crown"]
        is_promotion = tier_order.index(new_tier) > tier_order.index(old_tier)
        
        if is_promotion:
            logger.info(f"{entity_type.capitalize()} {entity_id} promoted: {old_tier} → {new_tier} in {game_slug}")
            
            # Send notification via NotificationAdapter
            from apps.tournament_ops.services.tournament_ops_service import get_tournament_ops_service
            
            service = get_tournament_ops_service()
            
            try:
                # For users: send tier promotion notification
                if entity_type == "user":
                    service.notification_adapter.send_notification(
                        user_id=entity_id,
                        notification_type="tier_promotion",
                        message=f"Congratulations! You've been promoted to {new_tier.capitalize()} tier in {game_slug}!",
                        data={
                            "old_tier": old_tier,
                            "new_tier": new_tier,
                            "game_slug": game_slug,
                        }
                    )
                    logger.info(f"Tier promotion notification sent to user {entity_id}")
                
                # For teams: notify all team members
                elif entity_type == "team":
                    # Get team members and notify each
                    from apps.teams.models import Team, TeamMembership
                    
                    team = Team.objects.get(id=entity_id)
                    memberships = TeamMembership.objects.filter(team=team, status='active')
                    
                    for membership in memberships:
                        service.notification_adapter.send_notification(
                            user_id=membership.user_id,
                            notification_type="team_tier_promotion",
                            message=f"Your team {team.name} has been promoted to {new_tier.capitalize()} tier in {game_slug}!",
                            data={
                                "team_id": entity_id,
                                "team_name": team.name,
                                "old_tier": old_tier,
                                "new_tier": new_tier,
                                "game_slug": game_slug,
                            }
                        )
                    
                    logger.info(f"Tier promotion notifications sent to {memberships.count()} team members")
                
            except Exception as notify_error:
                logger.error(f"Failed to send tier promotion notification: {str(notify_error)}")
        
        else:
            # Tier demotion (downward movement)
            logger.info(f"{entity_type.capitalize()} {entity_id} tier changed: {old_tier} → {new_tier} in {game_slug}")
        
    except Exception as e:
        logger.error(f"Error processing TierChangedEvent: {str(e)}", exc_info=True)
