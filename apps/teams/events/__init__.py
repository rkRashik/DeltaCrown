"""
Team Event Handlers

Replaces signal-based team operations with explicit event-driven architecture.
Handles team creation, membership changes, ranking updates, and notifications.
"""
import logging
from django.apps import apps
from django.utils import timezone

from apps.core.events import event_bus

logger = logging.getLogger(__name__)


def _lower_or_none(value):
    """Helper to normalize strings for case-insensitive fields"""
    if value is None:
        return None
    s = str(value).strip()
    return s.lower() if s else None


def get_ranking_service():
    """Lazy import ranking service to avoid circular imports"""
    try:
        from apps.teams.services.ranking_service import ranking_service
        return ranking_service
    except ImportError:
        logger.warning("Ranking service not available")
        return None


# ============================================================================
# Team Creation Handlers
# ============================================================================

def populate_team_ci_fields(event):
    """
    Populate case-insensitive fields (name_ci, tag_ci) when team is created/updated.
    
    Replaces: team_ci_autofill pre_save signal
    Triggered by: TeamCreatedEvent, TeamUpdatedEvent
    """
    try:
        team_id = event.data.get('team_id')
        Team = apps.get_model("teams", "Team")
        
        team = Team.objects.get(id=team_id)
        
        # Update case-insensitive fields
        changed = False
        if hasattr(team, "name_ci") and hasattr(team, "name"):
            new_name_ci = _lower_or_none(team.name)
            if team.name_ci != new_name_ci:
                team.name_ci = new_name_ci
                changed = True
        
        if hasattr(team, "tag_ci") and hasattr(team, "tag"):
            new_tag_ci = _lower_or_none(team.tag)
            if team.tag_ci != new_tag_ci:
                team.tag_ci = new_tag_ci
                changed = True
        
        if changed:
            team.save(update_fields=['name_ci', 'tag_ci'])
            logger.info(f"✅ Updated CI fields for team: {team.name}")
    
    except Exception as e:
        logger.error(f"❌ Failed to populate team CI fields: {e}", exc_info=True)


# ============================================================================
# Team Membership Handlers
# ============================================================================

def update_team_points_on_member_added(event):
    """
    Update team ranking points when member is added.
    
    Replaces: update_team_points_on_membership_change signal
    Triggered by: TeamMemberAddedEvent
    """
    try:
        team_id = event.data.get('team_id')
        user_id = event.data.get('user_id')
        Team = apps.get_model("teams", "Team")
        
        ranking_service = get_ranking_service()
        if not ranking_service:
            return
        
        team = Team.objects.get(id=team_id)
        
        result = ranking_service.recalculate_team_points(
            team,
            reason=f"Member added: user {user_id}"
        )
        
        if result.get('success') and result.get('points_change', 0) != 0:
            logger.info(
                f"✅ Team {team.name} points updated: {result['points_change']:+d} "
                f"(member added)"
            )
    
    except Exception as e:
        logger.error(f"❌ Failed to update team points on member add: {e}", exc_info=True)


def update_team_points_on_member_removed(event):
    """
    Update team ranking points when member is removed.
    
    Replaces: update_team_points_on_membership_deletion signal
    Triggered by: TeamMemberRemovedEvent
    """
    try:
        team_id = event.data.get('team_id')
        user_id = event.data.get('user_id')
        Team = apps.get_model("teams", "Team")
        
        ranking_service = get_ranking_service()
        if not ranking_service:
            return
        
        team = Team.objects.get(id=team_id)
        
        result = ranking_service.recalculate_team_points(
            team,
            reason=f"Member removed: user {user_id}"
        )
        
        if result.get('success') and result.get('points_change', 0) != 0:
            logger.info(
                f"✅ Team {team.name} points updated: {result['points_change']:+d} "
                f"(member removed)"
            )
    
    except Exception as e:
        logger.error(f"❌ Failed to update team points on member removal: {e}", exc_info=True)


# ============================================================================
# Ranking System Handlers
# ============================================================================

def recalculate_all_teams_on_criteria_change(event):
    """
    Recalculate all team rankings when ranking criteria change.
    
    Replaces: recalculate_all_teams_on_criteria_change signal
    Triggered by: RankingCriteriaChangedEvent
    """
    try:
        criteria_id = event.data.get('criteria_id')
        is_active = event.data.get('is_active', False)
        
        if not is_active:
            logger.info("Ranking criteria not active, skipping recalculation")
            return
        
        ranking_service = get_ranking_service()
        if not ranking_service:
            return
        
        logger.info("📊 Ranking criteria changed, recalculating all team points...")
        
        result = ranking_service.recalculate_all_teams(
            reason="Ranking criteria updated"
        )
        
        logger.info(
            f"✅ Bulk recalculation completed: {result['teams_processed']} teams processed, "
            f"{result['teams_updated']} updated"
        )
    
    except Exception as e:
        logger.error(f"❌ Failed to recalculate teams after criteria change: {e}", exc_info=True)


def award_tournament_participation_points(event):
    """
    Award points when team registers for tournament.
    
    Replaces: update_team_points_on_tournament_registration signal
    Triggered by: RegistrationCreatedEvent (from tournaments)
    """
    try:
        registration_id = event.data.get('registration_id')
        team_id = event.data.get('team_id')
        tournament_id = event.data.get('tournament_id')
        
        if not team_id:  # Solo registration, not team
            return
        
        Registration = apps.get_model('tournaments', 'Registration')
        registration = Registration.objects.select_related('team', 'tournament').get(id=registration_id)
        
        if registration.status not in ['APPROVED', 'CONFIRMED']:
            return
        
        ranking_service = get_ranking_service()
        if not ranking_service:
            return
        
        result = ranking_service.award_tournament_points(
            team=registration.team,
            tournament=registration.tournament,
            achievement_type='participation'
        )
        
        if result.get('success'):
            logger.info(
                f"✅ Awarded participation points to team {registration.team.name} "
                f"for tournament {registration.tournament.name}"
            )
        elif 'already awarded' not in result.get('error', '').lower():
            logger.warning(f"⚠️ Could not award participation points: {result.get('error')}")
    
    except Exception as e:
        logger.error(f"❌ Failed to award tournament participation points: {e}", exc_info=True)


def award_achievement_points(event):
    """
    Award points when team earns achievement.
    
    Replaces: update_team_points_on_achievement signal
    Triggered by: TeamAchievementEarnedEvent
    """
    try:
        achievement_id = event.data.get('achievement_id')
        team_id = event.data.get('team_id')
        
        TeamAchievement = apps.get_model('teams', 'TeamAchievement')
        Team = apps.get_model('teams', 'Team')
        
        achievement = TeamAchievement.objects.get(id=achievement_id)
        team = Team.objects.get(id=team_id)
        
        ranking_service = get_ranking_service()
        if not ranking_service:
            return
        
        criteria = ranking_service.get_active_criteria()
        breakdown = ranking_service.get_team_breakdown(team)
        old_total = breakdown.final_total
        
        # Add achievement points
        breakdown.achievement_points += criteria.achievement_points
        breakdown.save()
        
        # Record in history
        ranking_service.TeamRankingHistory.objects.create(
            team=team,
            points_change=criteria.achievement_points,
            points_before=old_total,
            points_after=breakdown.final_total,
            source='achievement',
            reason=f"Achievement earned: {achievement.title or 'Achievement'}",
            related_object_type='achievement',
            related_object_id=achievement.id
        )
        
        logger.info(f"✅ Awarded achievement points to team {team.name}")
    
    except Exception as e:
        logger.error(f"❌ Failed to award achievement points: {e}", exc_info=True)


# ============================================================================
# Notification Handlers
# ============================================================================

def notify_team_invite_sent(event):
    """
    Send notification when team invite is sent.
    
    Replaces: handle_team_invite_notification signal (created case)
    Triggered by: TeamInviteSentEvent
    """
    try:
        invite_id = event.data.get('invite_id')
        TeamInvite = apps.get_model('teams', 'TeamInvite')
        
        invite = TeamInvite.objects.select_related('team', 'invitee').get(id=invite_id)
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_invite_sent(invite)
        
        logger.info(f"✅ Invite sent notification triggered for invite {invite.id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to send invite notification: {e}", exc_info=True)


def notify_team_invite_accepted(event):
    """
    Send notification when team invite is accepted.
    
    Replaces: handle_team_invite_notification signal (accepted case)
    Triggered by: TeamInviteAcceptedEvent
    """
    try:
        invite_id = event.data.get('invite_id')
        TeamInvite = apps.get_model('teams', 'TeamInvite')
        
        invite = TeamInvite.objects.select_related('team', 'invitee').get(id=invite_id)
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_invite_accepted(invite)
        
        logger.info(f"✅ Invite accepted notification triggered for invite {invite.id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to send invite accepted notification: {e}", exc_info=True)


def notify_roster_change_added(event):
    """
    Send notification when team member is added.
    
    Replaces: handle_team_member_notification signal
    Triggered by: TeamMemberAddedEvent
    """
    try:
        team_id = event.data.get('team_id')
        user_id = event.data.get('user_id')
        
        Team = apps.get_model('teams', 'Team')
        team = Team.objects.get(id=team_id)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id) if user_id else None
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_roster_change(
            team=team,
            change_type='added',
            affected_user=user
        )
        
        logger.info(f"✅ Roster change (added) notification triggered for team {team.id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to send roster change notification: {e}", exc_info=True)


def notify_roster_change_removed(event):
    """
    Send notification when team member is removed.
    
    Replaces: handle_team_member_removed_notification signal
    Triggered by: TeamMemberRemovedEvent
    """
    try:
        team_id = event.data.get('team_id')
        user_id = event.data.get('user_id')
        
        Team = apps.get_model('teams', 'Team')
        team = Team.objects.get(id=team_id)
        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id) if user_id else None
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_roster_change(
            team=team,
            change_type='removed',
            affected_user=user
        )
        
        logger.info(f"✅ Member removed notification triggered for team {team.id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to send member removed notification: {e}", exc_info=True)


def notify_sponsor_approved(event):
    """
    Send notification when sponsor is approved.
    
    Replaces: handle_sponsor_approved_notification signal
    Triggered by: TeamSponsorApprovedEvent
    """
    try:
        sponsor_id = event.data.get('sponsor_id')
        TeamSponsor = apps.get_model('teams', 'TeamSponsor')
        
        sponsor = TeamSponsor.objects.select_related('team').get(id=sponsor_id)
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_sponsor_approved(sponsor)
        
        logger.info(f"✅ Sponsor approved notification triggered for sponsor {sponsor.id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to send sponsor approved notification: {e}", exc_info=True)


def notify_promotion_started(event):
    """
    Send notification when promotion starts.
    
    Replaces: handle_promotion_started_notification signal
    Triggered by: TeamPromotionStartedEvent
    """
    try:
        promotion_id = event.data.get('promotion_id')
        TeamPromotion = apps.get_model('teams', 'TeamPromotion')
        
        promotion = TeamPromotion.objects.select_related('team').get(id=promotion_id)
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_promotion_started(promotion)
        
        logger.info(f"✅ Promotion started notification triggered for promotion {promotion.id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to send promotion started notification: {e}", exc_info=True)


def notify_achievement_earned(event):
    """
    Send notification when team earns achievement.
    
    Replaces: handle_achievement_earned_notification signal
    Triggered by: TeamAchievementEarnedEvent
    """
    try:
        achievement_id = event.data.get('achievement_id')
        team_id = event.data.get('team_id')
        
        TeamAchievement = apps.get_model('teams', 'TeamAchievement')
        Team = apps.get_model('teams', 'Team')
        
        achievement = TeamAchievement.objects.get(id=achievement_id)
        team = Team.objects.get(id=team_id)
        
        from apps.notifications.services import NotificationService
        NotificationService.notify_achievement_earned(team, achievement)
        
        logger.info(f"✅ Achievement earned notification triggered for team {team.id}")
    
    except Exception as e:
        logger.error(f"❌ Failed to send achievement notification: {e}", exc_info=True)


# ============================================================================
# Registration Function
# ============================================================================

def register_team_event_handlers():
    """Register all team event handlers with the event bus"""
    
    # Team creation/update
    event_bus.subscribe(
        'team.created',
        populate_team_ci_fields,
        name='populate_team_ci_fields',
        priority=10  # Run early
    )
    
    event_bus.subscribe(
        'team.updated',
        populate_team_ci_fields,
        name='populate_team_ci_fields_on_update',
        priority=10
    )
    
    # Team membership
    event_bus.subscribe(
        'team.member_joined',
        update_team_points_on_member_added,
        name='update_team_points_on_member_added',
        priority=20
    )
    
    event_bus.subscribe(
        'team.member_joined',
        notify_roster_change_added,
        name='notify_roster_change_added',
        priority=50
    )
    
    event_bus.subscribe(
        'team.member_left',
        update_team_points_on_member_removed,
        name='update_team_points_on_member_removed',
        priority=20
    )
    
    event_bus.subscribe(
        'team.member_left',
        notify_roster_change_removed,
        name='notify_roster_change_removed',
        priority=50
    )
    
    # Ranking system
    event_bus.subscribe(
        'team.ranking_criteria_changed',
        recalculate_all_teams_on_criteria_change,
        name='recalculate_all_teams_on_criteria_change',
        priority=10
    )
    
    event_bus.subscribe(
        'registration.created',  # Listen to tournament events
        award_tournament_participation_points,
        name='award_tournament_participation_points',
        priority=30
    )
    
    event_bus.subscribe(
        'team.achievement_earned',
        award_achievement_points,
        name='award_achievement_points',
        priority=20
    )
    
    event_bus.subscribe(
        'team.achievement_earned',
        notify_achievement_earned,
        name='notify_achievement_earned',
        priority=50
    )
    
    # Team invites
    event_bus.subscribe(
        'team.invite_sent',
        notify_team_invite_sent,
        name='notify_team_invite_sent',
        priority=50
    )
    
    event_bus.subscribe(
        'team.invite_accepted',
        notify_team_invite_accepted,
        name='notify_team_invite_accepted',
        priority=50
    )
    
    # Team sponsors/promotions
    event_bus.subscribe(
        'team.sponsor_approved',
        notify_sponsor_approved,
        name='notify_sponsor_approved',
        priority=50
    )
    
    event_bus.subscribe(
        'team.promotion_started',
        notify_promotion_started,
        name='notify_promotion_started',
        priority=50
    )
    
    logger.info("📢 Registered team event handlers")


# Export handlers for testing
__all__ = [
    'populate_team_ci_fields',
    'update_team_points_on_member_added',
    'update_team_points_on_member_removed',
    'recalculate_all_teams_on_criteria_change',
    'award_tournament_participation_points',
    'award_achievement_points',
    'notify_team_invite_sent',
    'notify_team_invite_accepted',
    'notify_roster_change_added',
    'notify_roster_change_removed',
    'notify_sponsor_approved',
    'notify_promotion_started',
    'notify_achievement_earned',
    'register_team_event_handlers',
]
