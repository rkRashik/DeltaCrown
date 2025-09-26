from django.db.models.signals import pre_save, post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.apps import apps
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


def _lower_or_none(value):
    if value is None:
        return None
    s = str(value).strip()
    return s.lower() if s else None


@receiver(pre_save)
def team_ci_autofill(sender, instance, **kwargs):
    """
    Populate Team.name_ci / Team.tag_ci from name/tag without touching the legacy model code.
    Only runs for the Team model.
    """
    Team = apps.get_model("teams", "Team")
    if sender is not Team:
        return

    # Only set if fields exist on the model (during migrations they might not)
    if hasattr(instance, "name_ci") and hasattr(instance, "name"):
        instance.name_ci = _lower_or_none(getattr(instance, "name", None))
    if hasattr(instance, "tag_ci") and hasattr(instance, "tag"):
        instance.tag_ci = _lower_or_none(getattr(instance, "tag", None))


# Team Ranking Signals
# Import ranking service lazily to avoid circular imports
def get_ranking_service():
    try:
        from .services.ranking_service import ranking_service
        return ranking_service
    except ImportError:
        logger.warning("Ranking service not available")
        return None


@receiver(post_save, sender='teams.TeamMembership')
def update_team_points_on_membership_change(sender, instance, created, **kwargs):
    """Update team points when membership changes (add/remove members)."""
    ranking_service = get_ranking_service()
    if not ranking_service:
        return
        
    try:
        if instance.team:
            # Recalculate points for the team
            result = ranking_service.recalculate_team_points(
                instance.team,
                reason=f"Membership change: {'added' if created else 'updated'} member {instance.profile}"
            )
            
            if result['success'] and result['points_change'] != 0:
                logger.info(f"Team {instance.team.name} points updated due to membership change: {result['points_change']:+d}")
                
    except Exception as e:
        logger.error(f"Failed to update team points on membership change: {e}")


@receiver(post_delete, sender='teams.TeamMembership')
def update_team_points_on_membership_deletion(sender, instance, **kwargs):
    """Update team points when a member is removed."""
    ranking_service = get_ranking_service()
    if not ranking_service:
        return
        
    try:
        if instance.team:
            result = ranking_service.recalculate_team_points(
                instance.team,
                reason=f"Member removed: {instance.profile}"
            )
            
            if result['success'] and result['points_change'] != 0:
                logger.info(f"Team {instance.team.name} points updated due to member removal: {result['points_change']:+d}")
                
    except Exception as e:
        logger.error(f"Failed to update team points on membership deletion: {e}")


@receiver(post_save, sender='teams.RankingCriteria')
def recalculate_all_teams_on_criteria_change(sender, instance, **kwargs):
    """Recalculate all team points when ranking criteria change."""
    ranking_service = get_ranking_service()
    if not ranking_service:
        return
        
    try:
        if instance.is_active:  # Only recalculate if this is the active criteria
            logger.info("Ranking criteria changed, recalculating all team points...")
            
            result = ranking_service.recalculate_all_teams(
                reason="Ranking criteria updated"
            )
            
            logger.info(f"Bulk recalculation completed: {result['teams_processed']} teams processed, {result['teams_updated']} updated")
            
    except Exception as e:
        logger.error(f"Failed to recalculate all teams after criteria change: {e}")


# Tournament-related signals (if tournaments app is available)
def connect_tournament_signals():
    """Connect tournament-related signals if the tournaments app is available."""
    ranking_service = get_ranking_service()
    if not ranking_service:
        return
        
    try:
        Tournament = apps.get_model('tournaments', 'Tournament')
        Registration = apps.get_model('tournaments', 'Registration')
        
        @receiver(post_save, sender=Registration)
        def update_team_points_on_tournament_registration(sender, instance, created, **kwargs):
            """Award participation points when a team registers for a tournament."""
            try:
                if created and instance.team and instance.status in ['APPROVED', 'CONFIRMED']:
                    result = ranking_service.award_tournament_points(
                        team=instance.team,
                        tournament=instance.tournament,
                        achievement_type='participation'
                    )
                    
                    if result['success']:
                        logger.info(f"Awarded participation points to team {instance.team.name} for tournament {instance.tournament.name}")
                    elif 'already awarded' in result.get('error', '').lower():
                        # This is expected for duplicate registrations
                        pass
                    else:
                        logger.warning(f"Could not award participation points: {result.get('error')}")
                        
            except Exception as e:
                logger.error(f"Failed to award tournament participation points: {e}")

        logger.info("Tournament signals connected successfully")
        
    except Exception as e:
        logger.warning(f"Could not connect tournament signals (tournaments app may not be available): {e}")


def connect_achievement_signals():
    """Connect achievement-related signals if available."""
    ranking_service = get_ranking_service()
    if not ranking_service:
        return
        
    try:
        TeamAchievement = apps.get_model('teams', 'TeamAchievement')
        
        @receiver(post_save, sender=TeamAchievement)
        def update_team_points_on_achievement(sender, instance, created, **kwargs):
            """Award points when a team earns an achievement."""
            try:
                if created and instance.team:
                    criteria = ranking_service.get_active_criteria()
                    breakdown = ranking_service.get_team_breakdown(instance.team)
                    old_total = breakdown.final_total
                    
                    # Add achievement points
                    breakdown.achievement_points += criteria.achievement_points
                    breakdown.save()
                    
                    # Record in history
                    ranking_service.TeamRankingHistory.objects.create(
                        team=instance.team,
                        points_change=criteria.achievement_points,
                        points_before=old_total,
                        points_after=breakdown.final_total,
                        source='achievement',
                        reason=f"Achievement earned: {instance.title or 'Achievement'}",
                        related_object_type='achievement',
                        related_object_id=instance.id
                    )
                    
                    logger.info(f"Awarded achievement points to team {instance.team.name}")
                    
            except Exception as e:
                logger.error(f"Failed to award achievement points: {e}")
                
        logger.info("Achievement signals connected successfully")
        
    except Exception as e:
        logger.warning(f"Could not connect achievement signals: {e}")


# Connect additional signals when this module is imported
try:
    connect_tournament_signals()
    connect_achievement_signals()
except Exception as e:
    logger.warning(f"Some signals could not be connected: {e}")
