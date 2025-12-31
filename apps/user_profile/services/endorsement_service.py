# apps/user_profile/services/endorsement_service.py
"""
Endorsement Service Layer (P0 Feature).

Business logic for post-match skill endorsements:
- Permission validation (can user endorse in this match?)
- Teammate verification (are users on same team?)
- Endorsement creation with audit trail
- Aggregation queries for profile display
- Match participant resolution

Design: 03b_endorsements_and_showcase_design.md
"""

from django.db import transaction
from django.db.models import Count, Q, F, Exists, OuterRef
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils import timezone
from datetime import timedelta
from typing import Optional, List, Dict, Any

from apps.user_profile.models import (
    SkillEndorsement,
    EndorsementOpportunity,
    SkillType,
)

User = get_user_model()


# ============================================================================
# PERMISSION VALIDATION
# ============================================================================

def can_endorse(user: User, match) -> tuple[bool, Optional[str]]:
    """
    Check if user can endorse teammates from this match.
    
    Returns:
        (can_endorse: bool, error_message: str | None)
    
    Permission Rules:
    - User must be a participant in the match
    - Match must be in COMPLETED state
    - Endorsement window must not have expired (24 hours after completion)
    - User must not have already endorsed someone from this match
    
    Example:
    >>> can_endorse, error = can_endorse(user, match)
    >>> if not can_endorse:
    ...     print(f"Cannot endorse: {error}")
    """
    
    # 1. Match completion check
    if match.state != 'completed':
        return False, f'Match is not completed (current state: {match.state})'
    
    if not match.completed_at:
        return False, 'Match completion time not set'
    
    # 2. Time window check (24 hours after match completion)
    expiry_time = match.completed_at + timedelta(hours=24)
    if timezone.now() > expiry_time:
        time_passed = timezone.now() - match.completed_at
        hours_passed = time_passed.total_seconds() / 3600
        return False, f'Endorsement window expired ({hours_passed:.1f} hours after match completion, limit is 24 hours)'
    
    # 3. Participant verification
    is_participant, participant_error = is_match_participant(user, match)
    if not is_participant:
        return False, participant_error
    
    # 4. Already endorsed check
    existing_endorsement = SkillEndorsement.objects.filter(
        match=match,
        endorser=user,
    ).first()
    
    if existing_endorsement:
        return False, f'You already endorsed {existing_endorsement.receiver.username} for {existing_endorsement.get_skill_name_display()} in this match'
    
    return True, None


def is_match_participant(user: User, match) -> tuple[bool, Optional[str]]:
    """
    Check if user was a participant in the match.
    
    For 1v1 matches: Check participant1_id and participant2_id
    For team matches: Check team roster via tournament registration
    
    Returns:
        (is_participant: bool, error_message: str | None)
    """
    
    # Check if tournament is team-based
    if match.tournament.registration_type == 'team':
        # Team match: Check team rosters
        return is_team_match_participant(user, match)
    else:
        # Solo match: Check participant IDs directly
        # Note: Match model uses participant1_id/participant2_id as IntegerField
        # for User IDs (not team IDs)
        user_id = user.id
        
        if match.participant1_id == user_id or match.participant2_id == user_id:
            return True, None
        
        return False, f'You were not a participant in this match (participants: {match.participant1_name}, {match.participant2_name})'


def is_team_match_participant(user: User, match) -> tuple[bool, Optional[str]]:
    """
    Check if user was a team member in a team match.
    
    Looks up tournament registration to verify team roster membership.
    """
    from apps.tournaments.models import Registration
    from apps.teams.models import TeamMembership
    
    # Get team IDs for this match
    # Note: For team matches, participant1_id and participant2_id are team IDs
    team_a_id = match.participant1_id
    team_b_id = match.participant2_id
    
    if not team_a_id or not team_b_id:
        return False, 'Match teams not set'
    
    # Check if user is member of either team
    # We query TeamMembership to verify roster at time of match
    is_member = TeamMembership.objects.filter(
        team_id__in=[team_a_id, team_b_id],
        user=user,
        status='ACTIVE',
    ).exists()
    
    if is_member:
        return True, None
    
    return False, f'You were not a member of either team in this match (teams: {match.participant1_name} vs {match.participant2_name})'


def get_eligible_teammates(user: User, match) -> List[User]:
    """
    Get list of teammates user can endorse from this match.
    
    Rules:
    - Must be on same team as user
    - Cannot include user themselves (no self-endorsement)
    - For 1v1 matches: Returns empty list (no teammates)
    
    Returns:
        List of User objects
    """
    
    # Check if user can endorse
    can_endorse_flag, error = can_endorse(user, match)
    if not can_endorse_flag:
        return []
    
    # Check if team match
    if match.tournament.registration_type != 'team':
        # 1v1 match: No teammates (only opponent)
        return []
    
    # Get user's team in this match
    from apps.teams.models import TeamMembership
    
    team_a_id = match.participant1_id
    team_b_id = match.participant2_id
    
    # Find which team user is on
    user_membership = TeamMembership.objects.filter(
        team_id__in=[team_a_id, team_b_id],
        user=user,
        status='ACTIVE',
    ).first()
    
    if not user_membership:
        return []
    
    user_team_id = user_membership.team_id
    
    # Get all teammates from same team (exclude user)
    teammate_memberships = TeamMembership.objects.filter(
        team_id=user_team_id,
        status='ACTIVE',
    ).exclude(user=user).select_related('user')
    
    teammates = [membership.user for membership in teammate_memberships]
    
    return teammates


# ============================================================================
# ENDORSEMENT CREATION
# ============================================================================

@transaction.atomic
def create_endorsement(
    endorser: User,
    receiver: User,
    match,
    skill: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> SkillEndorsement:
    """
    Create a new skill endorsement with validation.
    
    Args:
        endorser: User giving endorsement
        receiver: User receiving endorsement
        match: Tournament match where skill was recognized
        skill: Skill category (from SkillType choices)
        ip_address: IP address of endorser (for fraud detection)
        user_agent: Browser user agent (for fraud detection)
    
    Returns:
        Created SkillEndorsement instance
    
    Raises:
        ValidationError: If validation fails
        PermissionDenied: If permission check fails
    
    Validation:
    - Endorser can endorse in this match (via can_endorse)
    - Receiver is eligible teammate (via get_eligible_teammates)
    - Skill is valid choice
    - No duplicate endorsement (enforced by DB constraint)
    
    Example:
    >>> endorsement = create_endorsement(
    ...     endorser=user1,
    ...     receiver=user2,
    ...     match=match,
    ...     skill=SkillType.AIM,
    ...     ip_address='192.168.1.1',
    ... )
    """
    
    # 1. Permission check
    can_endorse_flag, error = can_endorse(endorser, match)
    if not can_endorse_flag:
        raise PermissionDenied(error)
    
    # 2. Self-endorsement check
    if endorser.id == receiver.id:
        raise ValidationError('Cannot endorse yourself')
    
    # 3. Teammate verification
    eligible_teammates = get_eligible_teammates(endorser, match)
    
    # For 1v1 matches, opponent is the only other participant
    if match.tournament.registration_type != 'team':
        # In 1v1, can only endorse opponent (no teammates)
        # Get opponent user
        opponent_id = (
            match.participant2_id
            if match.participant1_id == endorser.id
            else match.participant1_id
        )
        
        if receiver.id != opponent_id:
            raise ValidationError(
                f'Can only endorse your opponent in 1v1 matches. '
                f'Expected user ID {opponent_id}, got {receiver.id}.'
            )
    else:
        # Team match: Verify receiver is teammate
        if receiver not in eligible_teammates:
            teammate_usernames = [t.username for t in eligible_teammates]
            raise ValidationError(
                f'{receiver.username} is not an eligible teammate from this match. '
                f'Eligible teammates: {", ".join(teammate_usernames) or "None"}'
            )
    
    # 4. Skill validation
    if skill not in dict(SkillType.choices):
        valid_skills = [choice[0] for choice in SkillType.choices]
        raise ValidationError(
            f'Invalid skill: {skill}. Must be one of: {", ".join(valid_skills)}'
        )
    
    # 5. Create endorsement
    endorsement = SkillEndorsement.objects.create(
        match=match,
        endorser=endorser,
        receiver=receiver,
        skill_name=skill,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    
    # 6. Mark endorsement opportunity as used (if exists)
    try:
        opportunity = EndorsementOpportunity.objects.get(
            match=match,
            player=endorser,
        )
        opportunity.mark_used()
    except EndorsementOpportunity.DoesNotExist:
        # Opportunity not tracked (manual endorsement or created before tracking system)
        pass
    
    return endorsement


# ============================================================================
# AGGREGATION QUERIES
# ============================================================================

def get_endorsement_stats(user: User) -> Dict[str, Any]:
    """
    Get aggregated endorsement statistics for user profile display.
    
    Returns dict with:
    - total_endorsements: Total count of endorsements received
    - skills: List of skill breakdowns with counts and percentages
    - top_skill: Most endorsed skill name (or None if no endorsements)
    - top_skill_count: Count for top skill
    - unique_matches: Count of distinct matches where user was endorsed
    - unique_endorsers: Count of distinct teammates who endorsed user
    - recent_endorsements: Last 5 endorsements with context
    
    Example:
    >>> stats = get_endorsement_stats(user)
    >>> print(f"Total: {stats['total_endorsements']}")
    >>> print(f"Top skill: {stats['top_skill']} ({stats['top_skill_count']})")
    >>> for skill in stats['skills']:
    ...     print(f"{skill['name']}: {skill['count']} ({skill['percentage']}%)")
    """
    
    # Query all endorsements for user
    endorsements = SkillEndorsement.objects.filter(
        receiver=user,
        is_flagged=False,  # Exclude flagged endorsements
    )
    
    total_endorsements = endorsements.count()
    
    # If no endorsements, return empty stats
    if total_endorsements == 0:
        return {
            'total_endorsements': 0,
            'skills': [],
            'top_skill': None,
            'top_skill_count': 0,
            'unique_matches': 0,
            'unique_endorsers': 0,
            'recent_endorsements': [],
        }
    
    # Skill breakdown
    skill_counts = endorsements.values('skill_name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    skills = []
    for skill_data in skill_counts:
        skill_name = skill_data['skill_name']
        count = skill_data['count']
        percentage = round((count / total_endorsements) * 100, 1)
        
        # Get display name from choices
        skill_display = dict(SkillType.choices).get(skill_name, skill_name)
        
        skills.append({
            'name': skill_name,
            'display_name': skill_display,
            'count': count,
            'percentage': percentage,
        })
    
    # Top skill
    top_skill_data = skills[0] if skills else None
    top_skill = top_skill_data['name'] if top_skill_data else None
    top_skill_count = top_skill_data['count'] if top_skill_data else 0
    
    # Unique counts
    unique_matches = endorsements.values('match').distinct().count()
    unique_endorsers = endorsements.values('endorser').distinct().count()
    
    # Recent endorsements (last 5)
    recent_endorsements = endorsements.select_related(
        'endorser',
        'match',
        'match__tournament',
    ).order_by('-created_at')[:5]
    
    recent_data = []
    for endorsement in recent_endorsements:
        recent_data.append({
            'id': endorsement.id,
            'skill': endorsement.skill_name,
            'skill_display': endorsement.get_skill_name_display(),
            'endorser_username': endorsement.endorser.username,
            'match_id': endorsement.match_id,
            'tournament_name': endorsement.match.tournament.name if endorsement.match.tournament else 'Unknown',
            'created_at': endorsement.created_at,
            'match_context': endorsement.get_match_context(),
        })
    
    return {
        'total_endorsements': total_endorsements,
        'skills': skills,
        'top_skill': top_skill,
        'top_skill_count': top_skill_count,
        'unique_matches': unique_matches,
        'unique_endorsers': unique_endorsers,
        'recent_endorsements': recent_data,
    }


def get_endorsements_summary(user: User) -> Dict[str, Any]:
    """
    Get endorsements summary for profile page display.
    
    Wrapper around get_endorsement_stats() that remaps keys to match
    the expected format in profile_context.py and public_profile_views.py.
    
    Returns dict with:
    - total_count: Total endorsements received
    - by_skill: List of skill breakdowns
    - top_skill: Most endorsed skill name (or None)
    - recent_endorsements: Last 5 endorsements with context
    
    Example:
    >>> summary = get_endorsements_summary(user)
    >>> print(f"Total: {summary['total_count']}")
    >>> print(f"Top: {summary['top_skill']}")
    """
    stats = get_endorsement_stats(user)
    
    return {
        'total_count': stats['total_endorsements'],
        'by_skill': stats['skills'],
        'top_skill': stats.get('top_skill'),
        'recent_endorsements': stats.get('recent_endorsements', []),
    }


def get_endorsements_by_skill(user: User, skill: str) -> List[SkillEndorsement]:
    """
    Get all endorsements for a specific skill.
    
    Args:
        user: User to query endorsements for
        skill: Skill category (from SkillType choices)
    
    Returns:
        List of SkillEndorsement instances
    """
    return SkillEndorsement.objects.filter(
        receiver=user,
        skill_name=skill,
        is_flagged=False,
    ).select_related('endorser', 'match', 'match__tournament').order_by('-created_at')


# ============================================================================
# ENDORSEMENT OPPORTUNITY MANAGEMENT
# ============================================================================

@transaction.atomic
def create_endorsement_opportunities(match) -> int:
    """
    Create endorsement opportunities for all match participants.
    
    Called when match transitions to COMPLETED state.
    Creates EndorsementOpportunity record for each participant with 24-hour expiry.
    
    Args:
        match: Completed tournament match
    
    Returns:
        Number of opportunities created
    
    Example:
    >>> # In match completion signal/service:
    >>> count = create_endorsement_opportunities(match)
    >>> print(f"Created {count} endorsement opportunities")
    """
    
    if match.state != 'completed' or not match.completed_at:
        return 0
    
    # Get all participants
    participants = get_match_participants(match)
    
    if not participants:
        return 0
    
    # Expiry time: 24 hours after match completion
    expires_at = match.completed_at + timedelta(hours=24)
    
    # Create opportunities for each participant
    opportunities_created = 0
    
    for participant in participants:
        # Check if opportunity already exists
        existing = EndorsementOpportunity.objects.filter(
            match=match,
            player=participant,
        ).exists()
        
        if not existing:
            EndorsementOpportunity.objects.create(
                match=match,
                player=participant,
                expires_at=expires_at,
            )
            opportunities_created += 1
    
    return opportunities_created


def get_match_participants(match) -> List[User]:
    """
    Get all participants (users) from a match.
    
    For solo matches: Returns participant1 and participant2 as User objects
    For team matches: Returns all team members from both teams
    
    Returns:
        List of User objects
    """
    participants = []
    
    if match.tournament.registration_type == 'team':
        # Team match: Get all team members
        from apps.teams.models import TeamMembership
        
        team_a_id = match.participant1_id
        team_b_id = match.participant2_id
        
        if team_a_id and team_b_id:
            memberships = TeamMembership.objects.filter(
                team_id__in=[team_a_id, team_b_id],
                status='ACTIVE',
            ).select_related('user')
            
            participants = [membership.user for membership in memberships]
    else:
        # Solo match: Get participant users directly
        participant_ids = [match.participant1_id, match.participant2_id]
        participant_ids = [pid for pid in participant_ids if pid]  # Filter None
        
        if participant_ids:
            participants = list(User.objects.filter(id__in=participant_ids))
    
    return participants


def get_pending_endorsement_opportunities(user: User) -> List[EndorsementOpportunity]:
    """
    Get all pending (unused, not expired) endorsement opportunities for user.
    
    Returns:
        List of EndorsementOpportunity instances
    """
    now = timezone.now()
    
    return EndorsementOpportunity.objects.filter(
        player=user,
        is_used=False,
        expires_at__gt=now,
    ).select_related('match', 'match__tournament').order_by('expires_at')


def cleanup_expired_opportunities(days_old: int = 7) -> int:
    """
    Delete expired endorsement opportunities older than X days.
    
    Keeps recent expired opportunities for analytics, but cleans up old records.
    
    Args:
        days_old: Delete opportunities expired more than this many days ago
    
    Returns:
        Number of opportunities deleted
    """
    cutoff_time = timezone.now() - timedelta(days=days_old)
    
    deleted_count, _ = EndorsementOpportunity.objects.filter(
        expires_at__lt=cutoff_time,
    ).delete()
    
    return deleted_count
