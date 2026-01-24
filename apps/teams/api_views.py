"""
REST API Views for Team Detail Page (Phase 2 & 3 Integration)
Provides JSON API endpoints for all frontend tabs
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Avg, Sum, Prefetch
from datetime import timedelta

from apps.teams.models import (
    Team,
    TeamSponsor,
    TeamDiscussionPost,
    TeamDiscussionComment,
    TeamChatMessage,
    ChatMessageReaction,
)


# ═══════════════════════════════════════════════════════════════════════════
# SPONSORS API (Phase 3C)
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([AllowAny])
def get_sponsors(request, team_slug):
    """Get all active sponsors for a team"""
    from django.core.cache import cache
    
    # Try cache first
    cache_key = f'team_sponsors_{team_slug}'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)
    
    team = get_object_or_404(Team, slug=team_slug)
    
    # Fixed N+1: Use queryset instead of values() to keep model methods
    sponsors = team.sponsors.filter(
        status='active',
        is_active=True
    ).order_by('display_order', '-sponsor_tier')
    
    # Map tier names to match frontend (gold, silver, bronze)
    sponsor_list = []
    for sponsor in sponsors:
        tier = sponsor.sponsor_tier
        # Convert platinum/gold/silver/bronze/partner to frontend tiers
        if tier in ['platinum', 'gold']:
            frontend_tier = 'gold'
        elif tier == 'silver':
            frontend_tier = 'silver'
        elif tier in ['bronze', 'partner']:
            frontend_tier = 'bronze'
        else:
            frontend_tier = 'bronze'
        
        # Parse benefits (stored as text, convert to list)
        benefits = []
        if sponsor.benefits:
            benefits = [b.strip() for b in sponsor.benefits.split('\n') if b.strip()]
        
        # Get logo URL (no extra query now)
        logo_url = sponsor.get_logo_url()
        
        # Calculate if expired
        is_expired = sponsor.end_date and sponsor.end_date < timezone.now().date()
        
        sponsor_list.append({
            'id': sponsor.id,
            'name': sponsor.sponsor_name,
            'tier': frontend_tier,
            'description': sponsor.notes or '',
            'logo_url': logo_url,
            'website': sponsor.sponsor_link,
            'start_date': sponsor.start_date.isoformat() if sponsor.start_date else None,
            'end_date': sponsor.end_date.isoformat() if sponsor.end_date else None,
            'benefits': benefits,
            'is_active': not is_expired,
        })
    
    # Cache for 5 minutes
    cache.set(cache_key, sponsor_list, 300)
    
    return Response(sponsor_list)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_sponsor(request, team_slug):
    """Add new sponsor (captain only) with validation"""
    from apps.teams.serializers import SponsorSerializer
    from django.core.cache import cache
    
    team = get_object_or_404(Team, slug=team_slug)
    
    # Check permission
    if not _is_team_captain(request.user, team):
        return Response(
            {'error': 'Only team captains can add sponsors'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Prepare data with mapping
    data = request.data.copy()
    tier_mapping = {'gold': 'gold', 'silver': 'silver', 'bronze': 'bronze'}
    data['sponsor_tier'] = tier_mapping.get(data.get('tier', 'bronze'), 'bronze')
    data['sponsor_name'] = data.get('name')
    data['sponsor_link'] = data.get('website')
    data['notes'] = data.get('description', '')
    
    # Validate with serializer
    serializer = SponsorSerializer(data=data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # Create sponsor
    sponsor = serializer.save(team=team, status='active', is_active=True)
    
    # Clear cache
    cache.delete(f'team_sponsors_{team_slug}')
    
    return Response({
        'success': True,
        'sponsor': {
            'id': sponsor.id,
            'name': sponsor.sponsor_name,
            'tier': sponsor.sponsor_tier,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_sponsor(request, team_slug, sponsor_id):
    """Update sponsor (captain only) with validation"""
    from apps.teams.serializers import SponsorSerializer
    from django.core.cache import cache
    
    team = get_object_or_404(Team, slug=team_slug)
    sponsor = get_object_or_404(TeamSponsor, id=sponsor_id, team=team)
    
    # Check permission
    if not _is_team_captain(request.user, team):
        return Response(
            {'error': 'Only team captains can edit sponsors'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Map frontend fields to backend fields
    data = request.data.copy()
    if 'name' in data:
        data['sponsor_name'] = data.pop('name')
    if 'tier' in data:
        tier_mapping = {'gold': 'gold', 'silver': 'silver', 'bronze': 'bronze'}
        data['sponsor_tier'] = tier_mapping.get(data.pop('tier'), 'bronze')
    if 'description' in data:
        data['notes'] = data.pop('description')
    if 'website' in data:
        data['sponsor_link'] = data.pop('website')
    
    # Validate
    serializer = SponsorSerializer(sponsor, data=data, partial=True)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    serializer.save()
    cache.delete(f'team_sponsors_{team_slug}')
    
    return Response({'success': True})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_sponsor(request, team_slug, sponsor_id):
    """Delete sponsor (captain only)"""
    from django.core.cache import cache
    
    team = get_object_or_404(Team, slug=team_slug)
    sponsor = get_object_or_404(TeamSponsor, id=sponsor_id, team=team)
    
    # Check permission
    if not _is_team_captain(request.user, team):
        return Response(
            {'error': 'Only team captains can delete sponsors'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    sponsor.delete()
    cache.delete(f'team_sponsors_{team_slug}')
    
    return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════════════════════════
# DISCUSSIONS API (Phase 3A)
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([AllowAny])
def get_discussions(request, team_slug):
    """Get discussions for a team with pagination"""
    from rest_framework.pagination import PageNumberPagination
    
    team = get_object_or_404(Team, slug=team_slug)
    
    # Get filter parameters
    category = request.GET.get('category')
    status_filter = request.GET.get('status')
    sort_by = request.GET.get('sort', 'recent')
    
    # Base query with optimizations
    discussions = TeamDiscussionPost.objects.filter(
        team=team,
        is_deleted=False
    ).select_related('author__user').prefetch_related('likes', 'comments')
    
    # Filter by category
    if category and category != 'all':
        discussions = discussions.filter(post_type=category)
    
    # Filter by status
    if status_filter == 'solved':
        discussions = discussions.filter(post_type='question')
    elif status_filter == 'open':
        discussions = discussions.filter(post_type='question')
    
    # Annotate counts for sorting
    discussions = discussions.annotate(
        like_count=Count('likes', distinct=True),
        comment_count=Count('comments', filter=Q(comments__is_deleted=False), distinct=True)
    )
    
    # Sort
    if sort_by == 'popular':
        discussions = discussions.order_by('-like_count', '-created_at')
    elif sort_by == 'unanswered':
        discussions = discussions.filter(comment_count=0).order_by('-created_at')
    else:  # recent
        discussions = discussions.order_by('-is_pinned', '-created_at')
    
    # Paginate
    paginator = PageNumberPagination()
    paginator.page_size = 20
    page = paginator.paginate_queryset(discussions, request)
    
    # Serialize
    discussion_list = []
    for disc in page:
        discussion_list.append({
            'id': disc.id,
            'title': disc.title,
            'category': disc.post_type,
            'content': disc.content[:200],  # Preview
            'author': {
                'id': disc.author.id,
                'username': disc.author.user.username,
                'avatar_url': None,
            },
            'created_at': disc.created_at.isoformat(),
            'views_count': disc.views_count,
            'like_count': disc.like_count,
            'comment_count': disc.comment_count,
            'is_pinned': disc.is_pinned,
            'is_locked': disc.is_locked,
        })
    
    return paginator.get_paginated_response(discussion_list)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_discussion(request, team_slug):
    """Create new discussion"""
    team = get_object_or_404(Team, slug=team_slug)
    
    # Check team membership
    if not _is_team_member(request.user, team):
        return Response(
            {'error': 'You must be a team member to create discussions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    data = request.data
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    category = data.get('category', 'general')
    
    if not title or not content:
        return Response(
            {'error': 'Title and content are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create discussion
    discussion = TeamDiscussionPost.objects.create(
        team=team,
        author=request.user.profile,
        title=title,
        content=content,
        post_type=category,
        is_public=False,
    )
    
    return Response({
        'success': True,
        'discussion': {
            'id': discussion.id,
            'title': discussion.title,
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def toggle_discussion_vote(request, team_slug, discussion_id):
    """Toggle upvote/downvote on discussion"""
    team = get_object_or_404(Team, slug=team_slug)
    discussion = get_object_or_404(TeamDiscussionPost, id=discussion_id, team=team)
    
    vote_type = request.data.get('vote_type', 'up')
    user_profile = request.user.profile
    
    # Check if already liked
    if user_profile in discussion.likes.all():
        discussion.likes.remove(user_profile)
        is_liked = False
    else:
        discussion.likes.add(user_profile)
        is_liked = True
    
    return Response({
        'success': True,
        'is_liked': is_liked,
        'vote_count': discussion.likes.count()
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_discussion(request, team_slug, discussion_id):
    """Delete discussion"""
    team = get_object_or_404(Team, slug=team_slug)
    discussion = get_object_or_404(TeamDiscussionPost, id=discussion_id, team=team)
    
    # Check permission (author or captain)
    if discussion.author.user != request.user and not _is_team_captain(request.user, team):
        return Response(
            {'error': 'You can only delete your own discussions'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    discussion.soft_delete()
    
    return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


# ═══════════════════════════════════════════════════════════════════════════
# CHAT API (Phase 3B)
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_messages(request, team_slug):
    """Get chat messages for a team with pagination"""
    team = get_object_or_404(Team, slug=team_slug)
    
    # Check team membership
    if not _is_team_member(request.user, team):
        return Response(
            {'error': 'You must be a team member to view chat'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get query parameters
    limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100
    before_id = request.GET.get('before_id')
    
    # Query messages with optimized joins
    messages = TeamChatMessage.objects.filter(
        team=team,
        is_deleted=False
    ).select_related('sender__user', 'reply_to').prefetch_related(
        'reactions__user'
    )
    
    if before_id:
        messages = messages.filter(id__lt=int(before_id))
    
    messages = messages.order_by('-created_at')[:limit]
    
    has_more = len(messages) == limit
    messages = list(reversed(messages))  # Oldest first
    
    # Serialize
    message_list = []
    for msg in messages:
        # Aggregate reactions
        reaction_dict = {}
        for reaction in msg.reactions.all():
            emoji = reaction.emoji
            if emoji not in reaction_dict:
                reaction_dict[emoji] = []
            reaction_dict[emoji].append(reaction.user.user.username)
        
        message_list.append({
            'id': msg.id,
            'sender': {
                'id': msg.sender.id,
                'username': msg.sender.user.username,
                'avatar_url': None,
            },
            'message': msg.message,
            'type': 'announcement' if msg.is_pinned else 'regular',
            'created_at': msg.created_at.isoformat(),
            'is_edited': msg.is_edited,
            'reactions': {
                emoji: {'users': users, 'count': len(users)}
                for emoji, users in reaction_dict.items()
            },
            'reply_to': msg.reply_to.id if msg.reply_to else None,
        })
    
    return Response({
        'messages': message_list,
        'has_more': has_more,
        'oldest_id': messages[0].id if messages else None,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_chat_message(request, team_slug):
    """Send chat message"""
    team = get_object_or_404(Team, slug=team_slug)
    
    # Check team membership
    if not _is_team_member(request.user, team):
        return Response(
            {'error': 'You must be a team member to chat'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    message_text = request.data.get('message', '').strip()
    
    if not message_text:
        return Response(
            {'error': 'Message cannot be empty'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create message
    message = TeamChatMessage.objects.create(
        team=team,
        sender=request.user.profile,
        message=message_text,
    )
    
    return Response({
        'success': True,
        'message': {
            'id': message.id,
            'sender': {
                'id': message.sender.id,
                'username': message.sender.user.username,
            },
            'message': message.message,
            'created_at': message.created_at.isoformat(),
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def edit_chat_message(request, team_slug, message_id):
    """Edit chat message"""
    team = get_object_or_404(Team, slug=team_slug)
    message = get_object_or_404(TeamChatMessage, id=message_id, team=team)
    
    # Check permission (only sender)
    if message.sender.user != request.user:
        return Response(
            {'error': 'You can only edit your own messages'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Check time limit (5 minutes)
    if message.created_at < timezone.now() - timedelta(minutes=5):
        return Response(
            {'error': 'Message can only be edited within 5 minutes'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    new_content = request.data.get('content', '').strip()
    if new_content:
        message.message = new_content
        message.mark_as_edited()
    
    return Response({'success': True})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_chat_message(request, team_slug, message_id):
    """Delete chat message"""
    team = get_object_or_404(Team, slug=team_slug)
    message = get_object_or_404(TeamChatMessage, id=message_id, team=team)
    
    # Check permission (sender or captain)
    if message.sender.user != request.user and not _is_team_captain(request.user, team):
        return Response(
            {'error': 'You can only delete your own messages'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    message.soft_delete()
    
    return Response({'success': True}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_message_reaction(request, team_slug, message_id):
    """Add reaction to message"""
    team = get_object_or_404(Team, slug=team_slug)
    message = get_object_or_404(TeamChatMessage, id=message_id, team=team)
    
    emoji = request.data.get('emoji')
    if not emoji:
        return Response(
            {'error': 'Emoji is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Create or get reaction
    reaction, created = ChatMessageReaction.objects.get_or_create(
        message=message,
        user=request.user.profile,
        emoji=emoji
    )
    
    return Response({
        'success': True,
        'reactions': message.reaction_summary
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def remove_message_reaction(request, team_slug, message_id):
    """Remove reaction from message"""
    team = get_object_or_404(Team, slug=team_slug)
    message = get_object_or_404(TeamChatMessage, id=message_id, team=team)
    
    emoji = request.data.get('emoji')
    
    # Remove reaction
    ChatMessageReaction.objects.filter(
        message=message,
        user=request.user.profile,
        emoji=emoji
    ).delete()
    
    return Response({
        'success': True,
        'reactions': message.reaction_summary
    })


# ═══════════════════════════════════════════════════════════════════════════
# Helper Functions
# ═══════════════════════════════════════════════════════════════════════════

def _is_team_captain(user, team):
    """Check if user is team captain/admin"""
    if not user.is_authenticated:
        return False
    try:
        # Check if user is team owner
        if hasattr(team, 'owner') and team.owner == user.profile:
            return True
        # Check team membership role
        from apps.teams.models.membership import TeamMembership
        membership = TeamMembership.objects.filter(
            team=team,
            user_profile=user.profile
        ).first()
        return membership and membership.role in ['owner', 'captain', 'admin', 'co_captain']
    except:
        return False


def _is_team_member(user, team):
    """Check if user is team member"""
    if not user.is_authenticated:
        return False
    try:
        from apps.teams.models.membership import TeamMembership
        return TeamMembership.objects.filter(
            team=team,
            user_profile=user.profile
        ).exists()
    except:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# ROSTER API
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([AllowAny])
def get_roster(request, team_slug):
    """Get team roster with member details and viewer context"""
    from django.core.cache import cache
    from apps.teams.models import TeamMembership
    from apps.teams.permissions import TeamPermissions
    from apps.user_profile.models import UserProfile
    
    # Note: Removed caching to always include fresh viewer context
    team = get_object_or_404(Team, slug=team_slug)
    
    # Get viewer information
    viewer_is_member = False
    viewer_membership = None
    viewer_permissions = {}
    
    if request.user.is_authenticated:
        try:
            profile = UserProfile.objects.get(user=request.user)
            viewer_membership = TeamMembership.objects.filter(
                team=team,
                profile=profile,
                status='ACTIVE'
            ).first()
            
            if viewer_membership:
                viewer_is_member = True
                viewer_permissions = TeamPermissions.get_permission_summary(viewer_membership)
        except UserProfile.DoesNotExist:
            pass
    
    # Try to get game-specific team and memberships first
    game_code = team.game
    membership_model = None
    team_instance = None
    
    # Map game codes to their membership models
    if game_code == 'valorant':
        from apps.teams.models.game_specific import ValorantTeam, ValorantPlayerMembership
        team_instance = ValorantTeam.objects.filter(slug=team_slug).first()
        membership_model = ValorantPlayerMembership
    elif game_code == 'cs2':
        from apps.teams.models.game_specific import CS2Team, CS2PlayerMembership
        team_instance = CS2Team.objects.filter(slug=team_slug).first()
        membership_model = CS2PlayerMembership
    elif game_code == 'dota2':
        from apps.teams.models.game_specific import Dota2Team, Dota2PlayerMembership
        team_instance = Dota2Team.objects.filter(slug=team_slug).first()
        membership_model = Dota2PlayerMembership
    elif game_code == 'mlbb':
        from apps.teams.models.game_specific import MLBBTeam, MLBBPlayerMembership
        team_instance = MLBBTeam.objects.filter(slug=team_slug).first()
        membership_model = MLBBPlayerMembership
    elif game_code == 'pubg':
        from apps.teams.models.game_specific import PUBGTeam, PUBGPlayerMembership
        team_instance = PUBGTeam.objects.filter(slug=team_slug).first()
        membership_model = PUBGPlayerMembership
    elif game_code == 'freefire':
        from apps.teams.models.game_specific import FreeFireTeam, FreeFirePlayerMembership
        team_instance = FreeFireTeam.objects.filter(slug=team_slug).first()
        membership_model = FreeFirePlayerMembership
    elif game_code == 'efootball':
        from apps.teams.models.game_specific import EFootballTeam, EFootballPlayerMembership
        team_instance = EFootballTeam.objects.filter(slug=team_slug).first()
        membership_model = EFootballPlayerMembership
    elif game_code == 'fc26':
        from apps.teams.models.game_specific import FC26Team, FC26PlayerMembership
        team_instance = FC26Team.objects.filter(slug=team_slug).first()
        membership_model = FC26PlayerMembership
    elif game_code == 'codm':
        from apps.teams.models.game_specific import CODMTeam, CODMPlayerMembership
        team_instance = CODMTeam.objects.filter(slug=team_slug).first()
        membership_model = CODMPlayerMembership
    
    active_players = []
    inactive_players = []
    
    # Try game-specific first, fall back to legacy TeamMembership
    if team_instance and membership_model:
        # Get memberships with related data
        memberships = membership_model.objects.filter(
            team=team_instance
        ).select_related('player__user').order_by('-is_active', 'role', 'joined_at')
        
        for membership in memberships:
            player_data = {
                'id': membership.player.id,
                'username': membership.player.user.username,
                'in_game_name': membership.in_game_name or membership.player.user.username,
                'avatar_url': membership.player.avatar.url if membership.player.avatar else None,
                'role': membership.role,
                'player_role': membership.player_role or '',
                'join_date': membership.joined_at.isoformat() if membership.joined_at else None,
                'is_captain': membership.role in ['captain', 'co_captain'] or (team_instance.captain and team_instance.captain.id == membership.player.id),
                'real_name': membership.player.user.get_full_name() or None,
                'stats': {
                    'matches_played': 0,
                    'win_rate': 0,
                    'mvp_count': 0
                }
            }
            
            if membership.is_active:
                active_players.append(player_data)
            else:
                inactive_players.append(player_data)
    else:
        # Fall back to legacy TeamMembership
        memberships = TeamMembership.objects.filter(
            team=team,
            status='ACTIVE'
        ).select_related('profile__user').order_by('role', '-joined_at')
        
        for membership in memberships:
            player_data = {
                'id': membership.profile.id,
                'username': membership.profile.user.username,
                'in_game_name': membership.profile.display_name or membership.profile.user.username,
                'avatar_url': membership.profile.avatar.url if membership.profile.avatar else None,
                'role': membership.role.lower(),
                'role_display': membership.get_role_display(),
                'player_role': membership.player_role or '',
                'is_captain': membership.is_captain,  # Use new is_captain field
                'join_date': membership.joined_at.isoformat() if membership.joined_at else None,
                'real_name': membership.profile.user.get_full_name() or None,
                'permissions': TeamPermissions.get_permission_summary(membership) if viewer_is_member else {},
                'stats': {
                    'matches_played': 0,
                    'win_rate': 0,
                    'mvp_count': 0
                }
            }
            
            active_players.append(player_data)
    
    response_data = {
        'active_players': active_players,
        'inactive_players': inactive_players,
        'viewer_context': {
            'is_authenticated': request.user.is_authenticated,
            'is_member': viewer_is_member,
            'permissions': viewer_permissions,
            'role': viewer_membership.role if viewer_membership else None,
            'role_display': viewer_membership.get_role_display() if viewer_membership else None,
            'is_captain': viewer_membership.is_captain if viewer_membership else False,
        },
        'statistics': {
            'total_members': len(active_players),
            'roles': {}
        }
    }
    
    # Note: No caching - always fresh viewer context
    return Response(response_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_roster_with_game_ids(request, team_slug):
    """
    Get team roster with game IDs included
    Only accessible to team members (captain/members) and staff
    Privacy: Game IDs are never displayed publicly
    """
    from apps.teams.models import TeamMembership
    
    team = get_object_or_404(Team, slug=team_slug)
    
    # Check if user is team member or staff
    is_member = TeamMembership.objects.filter(
        team=team,
        profile__user=request.user,
        status='ACTIVE'
    ).exists()
    
    is_captain = TeamMembership.objects.filter(
        team=team,
        profile__user=request.user,
        role='CAPTAIN',
        status='ACTIVE'
    ).exists()
    
    if not (is_member or request.user.is_staff):
        return Response(
            {'error': 'You must be a team member to view game IDs'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Get all active memberships with game IDs
    memberships = TeamMembership.objects.filter(
        team=team,
        status='ACTIVE'
    ).select_related('profile__user').order_by('role', '-joined_at')
    
    members_data = []
    for membership in memberships:
        profile = membership.profile
        
        # Get game ID for this team's game
        # Get game passport info
        from apps.user_profile.services.game_passport_service import GamePassportService
        passport = GamePassportService.get_passport(request.user, team.game)
        game_id = passport.in_game_name if passport else ''
        game_id_label = 'IGN'
        
        # Get MLBB server ID if applicable
        mlbb_server_id = None
        if team.game == 'mlbb' and profile.mlbb_server_id:
            mlbb_server_id = profile.mlbb_server_id
        
        member_data = {
            'profile_id': profile.id,
            'display_name': profile.display_name or profile.user.username,
            'username': profile.user.username,
            'avatar': profile.avatar.url if profile.avatar else None,
            'role': membership.role,
            'role_display': membership.get_role_display(),
            'player_role': membership.player_role or '',
            'game_id': game_id,
            'game_id_label': game_id_label,
            'mlbb_server_id': mlbb_server_id,
            'joined_at': membership.joined_at.isoformat() if membership.joined_at else None,
            'is_online': False,  # Can be implemented later with presence system
            # Social links (only visible to team members)
            'twitter': profile.twitter if profile.twitter else None,
            'discord_id': profile.discord_id if profile.discord_id else None,
            'youtube_link': profile.youtube_link if profile.youtube_link else None,
            'twitch_link': profile.twitch_link if profile.twitch_link else None,
            'instagram': profile.instagram if profile.instagram else None,
        }
        
        members_data.append(member_data)
    
    # Get game display name
    game_choices = dict(team._meta.get_field('game').choices)
    game_name = game_choices.get(team.game, team.game)
    
    response_data = {
        'members': members_data,
        'game_name': game_name,
        'is_captain': is_captain,
    }
    
    return Response(response_data)


# ═══════════════════════════════════════════════════════════════════════════
# TOURNAMENTS API
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([AllowAny])
def get_tournaments(request, team_slug):
    """Get team tournaments (active, upcoming, history)"""
    from django.apps import apps
    Tournament = apps.get_model('tournaments', 'Tournament')
    Registration = apps.get_model('tournaments', 'Registration')
    
    team = get_object_or_404(Team, slug=team_slug)
    
    # Get game-specific team instance
    game_code = team.game
    team_instance = None
    
    if game_code == 'valorant':
        from apps.teams.models.game_specific import ValorantTeam
        team_instance = ValorantTeam.objects.filter(slug=team_slug).first()
    elif game_code == 'cs2':
        from apps.teams.models.game_specific import CS2Team
        team_instance = CS2Team.objects.filter(slug=team_slug).first()
    elif game_code == 'dota2':
        from apps.teams.models.game_specific import Dota2Team
        team_instance = Dota2Team.objects.filter(slug=team_slug).first()
    elif game_code == 'mlbb':
        from apps.teams.models.game_specific import MLBBTeam
        team_instance = MLBBTeam.objects.filter(slug=team_slug).first()
    elif game_code == 'pubg':
        from apps.teams.models.game_specific import PUBGTeam
        team_instance = PUBGTeam.objects.filter(slug=team_slug).first()
    elif game_code == 'freefire':
        from apps.teams.models.game_specific import FreeFireTeam
        team_instance = FreeFireTeam.objects.filter(slug=team_slug).first()
    elif game_code == 'efootball':
        from apps.teams.models.game_specific import EFootballTeam
        team_instance = EFootballTeam.objects.filter(slug=team_slug).first()
    elif game_code == 'fc26':
        from apps.teams.models.game_specific import FC26Team
        team_instance = FC26Team.objects.filter(slug=team_slug).first()
    elif game_code == 'codm':
        from apps.teams.models.game_specific import CODMTeam
        team_instance = CODMTeam.objects.filter(slug=team_slug).first()
    
    active_tournaments = []
    history_tournaments = []
    
    if team_instance:
        # Get registrations using content type
        from django.contrib.contenttypes.models import ContentType
        team_ct = ContentType.objects.get_for_model(team_instance)
        
        registrations = Registration.objects.filter(
            team_content_type=team_ct,
            team_object_id=team_instance.id
        ).select_related('tournament').order_by('-tournament__start_date')
        
        now = timezone.now()
        
        for reg in registrations:
            tournament = reg.tournament
            tournament_data = {
                'id': tournament.id,
                'name': tournament.name,
                'game': tournament.game,
                'format': tournament.tournament_format,
                'prize_pool': str(tournament.prize_pool) if tournament.prize_pool else None,
                'start_date': tournament.start_date.isoformat() if tournament.start_date else None,
                'end_date': tournament.end_date.isoformat() if tournament.end_date else None,
                'status': tournament.status,
                'registration_status': reg.status,
                'placement': None,  # TODO: Add placement tracking
                'banner_url': tournament.media.banner.url if hasattr(tournament, 'media') and tournament.media.banner else None
            }
            
            # Categorize by tournament status
            if tournament.status in ['upcoming', 'registration_open', 'ongoing']:
                active_tournaments.append(tournament_data)
            else:
                history_tournaments.append(tournament_data)
    
    return Response({
        'active': active_tournaments,
        'history': history_tournaments,
        'upcomingMatches': []  # TODO: Add match schedule integration
    })


# ═══════════════════════════════════════════════════════════════════════════
# POSTS API
# ═══════════════════════════════════════════════════════════════════════════

@api_view(['GET'])
@permission_classes([AllowAny])
def get_posts(request, team_slug):
    """Get team posts with pagination"""
    from apps.teams.models.social import TeamPost, TeamPostLike
    from django.core.paginator import Paginator
    
    team = get_object_or_404(Team, slug=team_slug)
    
    # Get query params
    page = int(request.GET.get('page', 1))
    filter_type = request.GET.get('filter', 'all')
    sort_by = request.GET.get('sort', 'recent')
    
    # Base queryset
    posts = TeamPost.objects.filter(
        team=team
    ).select_related('author', 'author__user').prefetch_related('media', 'likes')
    
    # Apply filters
    if filter_type == 'announcements':
        posts = posts.filter(post_type='announcement')
    elif filter_type == 'media':
        posts = posts.filter(media__isnull=False).distinct()
    
    # Apply sorting
    if sort_by == 'recent':
        posts = posts.order_by('-created_at')
    elif sort_by == 'popular':
        posts = posts.annotate(like_count=Count('likes')).order_by('-like_count', '-created_at')
    elif sort_by == 'comments':
        posts = posts.annotate(comment_count=Count('comments')).order_by('-comment_count', '-created_at')
    
    # Paginate
    paginator = Paginator(posts, 10)
    page_obj = paginator.get_page(page)
    
    # Serialize posts
    user_profile = request.user.profile if request.user.is_authenticated else None
    posts_data = []
    
    for post in page_obj:
        # Check if user liked this post
        user_liked = False
        if user_profile:
            user_liked = post.likes.filter(user=user_profile).exists()
        
        post_data = {
            'id': post.id,
            'author': {
                'username': post.author.user.username,
                'avatar_url': post.author.avatar.url if post.author.avatar else None,
            },
            'content': post.content,
            'post_type': post.post_type,
            'created_at': post.created_at.isoformat(),
            'updated_at': post.updated_at.isoformat() if post.updated_at else None,
            'likes_count': post.likes.count(),
            'comments_count': post.comments.count(),
            'user_liked': user_liked,
            'media': [
                {
                    'id': media.id,
                    'type': media.media_type,
                    'url': media.file.url,
                    'thumbnail_url': media.thumbnail_url
                }
                for media in post.media.all()
            ] if hasattr(post, 'media') else []
        }
        posts_data.append(post_data)
    
    return Response({
        'posts': posts_data,
        'pagination': {
            'page': page,
            'total_pages': paginator.num_pages,
            'total_posts': paginator.count,
            'has_next': page_obj.has_next(),
            'has_previous': page_obj.has_previous()
        }
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_post(request, team_slug):
    """Create a new team post"""
    from apps.teams.models.social import TeamPost
    
    team = get_object_or_404(Team, slug=team_slug)
    
    # Check if user is team member
    if not _is_team_member(request.user, team):
        return Response(
            {'error': 'Only team members can create posts'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    content = request.data.get('content', '').strip()
    post_type = request.data.get('post_type', 'general')
    
    if not content:
        return Response(
            {'error': 'Content is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    post = TeamPost.objects.create(
        team=team,
        author=request.user.profile,
        content=content,
        post_type=post_type
    )
    
    return Response({
        'success': True,
        'post_id': post.id
    }, status=status.HTTP_201_CREATED)
