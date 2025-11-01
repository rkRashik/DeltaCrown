"""
Common Event Definitions

Centralized event definitions for cross-app communication.
Apps publish these events, and other apps can subscribe to them.
"""

from .bus import Event
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# ============================================================================
# Tournament Events
# ============================================================================

@dataclass
class TournamentCreatedEvent(Event):
    """Published when a new tournament is created"""
    event_type: str = field(default='tournament.created', init=False)
    
    @property
    def tournament_id(self) -> int:
        return self.data['tournament_id']


@dataclass
class TournamentUpdatedEvent(Event):
    """Published when a tournament is updated"""
    event_type: str = field(default='tournament.updated', init=False)
    
    @property
    def tournament_id(self) -> int:
        return self.data['tournament_id']


@dataclass
class TournamentPublishedEvent(Event):
    """Published when a tournament is published"""
    event_type: str = field(default='tournament.published', init=False)
    
    @property
    def tournament_id(self) -> int:
        return self.data['tournament_id']


@dataclass
class TournamentStartedEvent(Event):
    """Published when a tournament starts"""
    event_type: str = field(default='tournament.started', init=False)
    
    @property
    def tournament_id(self) -> int:
        return self.data['tournament_id']


@dataclass
class TournamentCompletedEvent(Event):
    """Published when a tournament is completed"""
    event_type: str = field(default='tournament.completed', init=False)
    
    @property
    def tournament_id(self) -> int:
        return self.data['tournament_id']
    
    @property
    def winner_id(self) -> Optional[int]:
        return self.data.get('winner_id')


# ============================================================================
# Registration Events
# ============================================================================

@dataclass
class RegistrationCreatedEvent(Event):
    """Published when a new registration is created"""
    event_type: str = field(default='registration.created', init=False)
    
    @property
    def registration_id(self) -> int:
        return self.data['registration_id']
    
    @property
    def tournament_id(self) -> int:
        return self.data['tournament_id']
    
    @property
    def team_id(self) -> Optional[int]:
        return self.data.get('team_id')


@dataclass
class RegistrationConfirmedEvent(Event):
    """Published when a registration is confirmed (payment verified)"""
    event_type: str = field(default='registration.confirmed', init=False)
    
    @property
    def registration_id(self) -> int:
        return self.data['registration_id']
    
    @property
    def tournament_id(self) -> int:
        return self.data['tournament_id']
    
    @property
    def team_id(self) -> Optional[int]:
        return self.data.get('team_id')
    
    @property
    def user_id(self) -> Optional[int]:
        return self.data.get('user_id')


# ============================================================================
# Match Events
# ============================================================================

@dataclass
class MatchScheduledEvent(Event):
    """Published when a match is scheduled"""
    event_type: str = field(default='match.scheduled', init=False)
    
    @property
    def match_id(self) -> int:
        return self.data['match_id']
    
    @property
    def tournament_id(self) -> int:
        return self.data['tournament_id']


@dataclass
class MatchCompletedEvent(Event):
    """Published when a match is completed"""
    event_type: str = field(default='match.completed', init=False)
    
    @property
    def match_id(self) -> int:
        return self.data['match_id']
    
    @property
    def winner_id(self) -> Optional[int]:
        return self.data.get('winner_id')


@dataclass
class MatchResultVerifiedEvent(Event):
    """Published when a match result is verified"""
    event_type: str = field(default='match.result_verified', init=False)
    
    @property
    def match_id(self) -> int:
        return self.data['match_id']
    
    @property
    def tournament_id(self) -> int:
        return self.data['tournament_id']
    
    @property
    def winner_id(self) -> Optional[int]:
        return self.data.get('winner_id')


# ============================================================================
# Team Events
# ============================================================================

@dataclass
class TeamCreatedEvent(Event):
    """Published when a new team is created"""
    event_type: str = field(default='team.created', init=False)
    
    @property
    def team_id(self) -> int:
        return self.data['team_id']
    
    @property
    def captain_id(self) -> int:
        return self.data['captain_id']


@dataclass
class TeamUpdatedEvent(Event):
    """Published when a team is updated"""
    event_type: str = field(default='team.updated', init=False)
    
    @property
    def team_id(self) -> int:
        return self.data['team_id']


@dataclass
class TeamMemberJoinedEvent(Event):
    """Published when a member joins a team"""
    event_type: str = field(default='team.member_joined', init=False)
    
    @property
    def team_id(self) -> int:
        return self.data['team_id']
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


@dataclass
class TeamMemberLeftEvent(Event):
    """Published when a member leaves a team"""
    event_type: str = field(default='team.member_left', init=False)
    
    @property
    def team_id(self) -> int:
        return self.data['team_id']
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


@dataclass
class TeamInviteSentEvent(Event):
    """Published when a team invite is sent"""
    event_type: str = field(default='team.invite_sent', init=False)
    
    @property
    def invite_id(self) -> int:
        return self.data['invite_id']
    
    @property
    def team_id(self) -> int:
        return self.data['team_id']


@dataclass
class TeamInviteAcceptedEvent(Event):
    """Published when a team invite is accepted"""
    event_type: str = field(default='team.invite_accepted', init=False)
    
    @property
    def invite_id(self) -> int:
        return self.data['invite_id']
    
    @property
    def team_id(self) -> int:
        return self.data['team_id']


@dataclass
class RankingCriteriaChangedEvent(Event):
    """Published when team ranking criteria change"""
    event_type: str = field(default='team.ranking_criteria_changed', init=False)
    
    @property
    def criteria_id(self) -> int:
        return self.data['criteria_id']
    
    @property
    def is_active(self) -> bool:
        return self.data.get('is_active', False)


@dataclass
class TeamAchievementEarnedEvent(Event):
    """Published when a team earns an achievement"""
    event_type: str = field(default='team.achievement_earned', init=False)
    
    @property
    def achievement_id(self) -> int:
        return self.data['achievement_id']
    
    @property
    def team_id(self) -> int:
        return self.data['team_id']


@dataclass
class TeamSponsorApprovedEvent(Event):
    """Published when a team sponsor is approved"""
    event_type: str = field(default='team.sponsor_approved', init=False)
    
    @property
    def sponsor_id(self) -> int:
        return self.data['sponsor_id']
    
    @property
    def team_id(self) -> int:
        return self.data['team_id']


@dataclass
class TeamPromotionStartedEvent(Event):
    """Published when a team promotion starts"""
    event_type: str = field(default='team.promotion_started', init=False)
    
    @property
    def promotion_id(self) -> int:
        return self.data['promotion_id']
    
    @property
    def team_id(self) -> int:
        return self.data['team_id']


# ============================================================================
# Payment Events
# ============================================================================

@dataclass
class PaymentVerifiedEvent(Event):
    """Published when a payment is verified"""
    event_type: str = field(default='payment.verified', init=False)
    
    @property
    def payment_id(self) -> int:
        return self.data['payment_id']
    
    @property
    def registration_id(self) -> int:
        return self.data['registration_id']
    
    @property
    def amount(self) -> float:
        return self.data.get('amount', 0.0)


# ============================================================================
# User Events
# ============================================================================

@dataclass
class UserCreatedEvent(Event):
    """Published when a new user is created"""
    event_type: str = field(default='user.created', init=False)
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


@dataclass
class UserUpdatedEvent(Event):
    """Published when a user is updated"""
    event_type: str = field(default='user.updated', init=False)
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


@dataclass
class UserDeletedEvent(Event):
    """Published when a user is deleted"""
    event_type: str = field(default='user.deleted', init=False)
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


@dataclass
class UserGroupsChangedEvent(Event):
    """Published when user's groups change"""
    event_type: str = field(default='user.groups_changed', init=False)
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


# ============================================================================
# Community/Social Events
# ============================================================================

@dataclass
class PostLikedEvent(Event):
    """Published when a post is liked"""
    event_type: str = field(default='post.liked', init=False)
    
    @property
    def post_id(self) -> int:
        return self.data['post_id']
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


@dataclass
class PostUnlikedEvent(Event):
    """Published when a post is unliked"""
    event_type: str = field(default='post.unliked', init=False)
    
    @property
    def post_id(self) -> int:
        return self.data['post_id']
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


@dataclass
class PostCommentedEvent(Event):
    """Published when a comment is added to a post"""
    event_type: str = field(default='post.commented', init=False)
    
    @property
    def post_id(self) -> int:
        return self.data['post_id']
    
    @property
    def comment_id(self) -> int:
        return self.data['comment_id']


@dataclass
class PostCommentDeletedEvent(Event):
    """Published when a comment is deleted"""
    event_type: str = field(default='post.comment_deleted', init=False)
    
    @property
    def post_id(self) -> int:
        return self.data['post_id']
    
    @property
    def comment_id(self) -> int:
        return self.data['comment_id']


@dataclass
class PostSharedEvent(Event):
    """Published when a post is shared"""
    event_type: str = field(default='post.shared', init=False)
    
    @property
    def post_id(self) -> int:
        return self.data['post_id']
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


@dataclass
class PostUnsharedEvent(Event):
    """Published when a share is removed"""
    event_type: str = field(default='post.unshared', init=False)
    
    @property
    def post_id(self) -> int:
        return self.data['post_id']
    
    @property
    def user_id(self) -> int:
        return self.data['user_id']


# ============================================================================
# Notification Events (requests for notifications)
# ============================================================================

@dataclass
class SendNotificationEvent(Event):
    """Request to send a notification"""
    event_type: str = field(default='notification.send', init=False)
    
    @property
    def recipient_id(self) -> int:
        return self.data['recipient_id']
    
    @property
    def message(self) -> str:
        return self.data['message']
    
    @property
    def notification_type(self) -> str:
        return self.data.get('type', 'generic')
