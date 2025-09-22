"""
Team Social Features Views
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_http_methods, require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
import json

from ..models import Team
from ..models.social import (
    TeamPost, TeamPostComment, TeamPostLike, 
    TeamFollower, TeamActivity
)
from ..social_forms import (
    TeamPostForm, TeamPostCommentForm, TeamPostMediaForm,
    TeamFollowForm, TeamBannerForm
)
from apps.user_profile.models import UserProfile


@login_required
def team_social_detail(request, team_slug):
    """Enhanced team detail page with social features."""
    team = get_object_or_404(Team, slug=team_slug)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Check if user is following this team
    is_following = team.is_followed_by(user_profile)
    is_member = team.is_member(user_profile)
    is_captain = team.is_captain(user_profile)
    can_post = team.can_user_post(user_profile)
    
    # Get posts with pagination
    posts_list = TeamPost.objects.filter(
        team=team,
        published_at__isnull=False
    ).select_related('author__user').prefetch_related('media', 'likes')
    
    # Filter posts based on visibility and user permissions
    if not is_member:
        if is_following:
            posts_list = posts_list.filter(visibility__in=['public', 'followers'])
        else:
            posts_list = posts_list.filter(visibility='public')
    
    paginator = Paginator(posts_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    
    # Get recent activity
    activities = team.get_activity_feed(limit=5)
    
    # Forms
    post_form = TeamPostForm(team=team, author=user_profile) if can_post else None
    follow_form = TeamFollowForm(team=team, user_profile=user_profile)
    banner_form = TeamBannerForm(team=team) if is_captain else None
    
    context = {
        'team': team,
        'posts': posts,
        'activities': activities,
        'is_following': is_following,
        'is_member': is_member,
        'is_captain': is_captain,
        'can_post': can_post,
        'post_form': post_form,
        'follow_form': follow_form,
        'banner_form': banner_form,
        'user_profile': user_profile,
        'follower_count': team.get_follower_count(),
        'already_in_team_for_game': False,  # TODO: implement game-specific team check
    }
    
    return render(request, 'teams/team_social_detail.html', context)


@login_required
@require_POST
def create_team_post(request, team_slug):
    """Create a new team post."""
    team = get_object_or_404(Team, slug=team_slug)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    if not team.can_user_post(user_profile):
        return HttpResponseForbidden("You don't have permission to post to this team.")
    
    form = TeamPostForm(request.POST, team=team, author=user_profile)
    
    if form.is_valid():
        with transaction.atomic():
            post = form.save()
            
            # Handle media uploads if any
            if 'media' in request.FILES:
                media_files = request.FILES.getlist('media')
                for media_file in media_files:
                    # Create TeamPostMedia instance for each file
                    from ..models.social import TeamPostMedia
                    import os
                    
                    # Determine media type based on file extension
                    file_extension = os.path.splitext(media_file.name)[1].lower()
                    if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        media_type = 'image'
                    elif file_extension in ['.mp4', '.mov', '.avi', '.webm']:
                        media_type = 'video'
                    else:
                        media_type = 'document'
                    
                    # Create media object
                    TeamPostMedia.objects.create(
                        post=post,
                        file=media_file,
                        media_type=media_type,
                        file_size=media_file.size
                    )
            
            # Create activity
            TeamActivity.objects.create(
                team=team,
                activity_type='post_published',
                actor=user_profile,
                description=f"{user_profile.user.get_full_name() or user_profile.user.username} created a new post",
                related_post=post
            )
            
            messages.success(request, "Post created successfully!")
            
        return redirect('teams:teams_social:team_social_detail', team_slug=team.slug)
    else:
        # Debug: show specific form errors
        error_messages = []
        for field, errors in form.errors.items():
            for error in errors:
                error_messages.append(f"{field}: {error}")
        
        error_text = "Form errors: " + "; ".join(error_messages) if error_messages else "Unknown form validation error"
        messages.error(request, f"Error creating post: {error_text}")
        return redirect('teams:teams_social:team_social_detail', team_slug=team.slug)


@login_required
@require_POST
def create_post_comment(request, team_slug, post_id):
    """Create a comment on a team post."""
    team = get_object_or_404(Team, slug=team_slug)
    post = get_object_or_404(TeamPost, id=post_id, team=team)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Check if user can see this post
    if not post.can_user_view(user_profile):
        return HttpResponseForbidden("You don't have permission to comment on this post.")
    
    parent_id = request.POST.get('parent_id')
    parent = None
    if parent_id:
        parent = get_object_or_404(TeamPostComment, id=parent_id, post=post)
    
    form = TeamPostCommentForm(request.POST, post=post, author=user_profile, parent=parent)
    
    if form.is_valid():
        comment = form.save()
        
        # Create activity
        TeamActivity.objects.create(
            team=team,
            activity_type='comment_created',
            user=user_profile,
            description=f"{user_profile.user.get_full_name() or user_profile.user.username} commented on a post",
            metadata={'post_id': post.id, 'comment_id': comment.id}
        )
        
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({
                'success': True,
                'comment_id': comment.id,
                'author_name': user_profile.user.get_full_name() or user_profile.user.username,
                'content': comment.content,
                'created_at': comment.created_at.isoformat()
            })
        
        messages.success(request, "Comment added successfully!")
    else:
        if request.headers.get('Content-Type') == 'application/json':
            return JsonResponse({'success': False, 'errors': form.errors})
        messages.error(request, "Error adding comment.")
    
    return redirect('teams:teams_social:team_social_detail', team_slug=team.slug)


@login_required
@require_POST
def toggle_post_like(request, team_slug, post_id):
    """Toggle like on a team post."""
    team = get_object_or_404(Team, slug=team_slug)
    post = get_object_or_404(TeamPost, id=post_id, team=team)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Check if user can see this post
    if not post.can_user_view(user_profile):
        return HttpResponseForbidden("You don't have permission to like this post.")
    
    like, created = TeamPostLike.objects.get_or_create(
        post=post,
        user=user_profile
    )
    
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        # Create activity for likes (only for new likes)
        TeamActivity.objects.create(
            team=team,
            activity_type='post_liked',
            user=user_profile,
            description=f"{user_profile.user.get_full_name() or user_profile.user.username} liked a post",
            metadata={'post_id': post.id}
        )
    
    # Update like count
    like_count = post.likes.count()
    
    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': like_count
        })
    
    return redirect('teams:teams_social:team_social_detail', team_slug=team.slug)


@login_required
@require_POST
def toggle_team_follow(request, team_slug):
    """Toggle following a team."""
    team = get_object_or_404(Team, slug=team_slug)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    form = TeamFollowForm(team=team, user_profile=user_profile)
    is_following = form.toggle_follow()
    
    # Create activity
    if is_following:
        TeamActivity.objects.create(
            team=team,
            activity_type='team_followed',
            user=user_profile,
            description=f"{user_profile.user.get_full_name() or user_profile.user.username} started following the team",
            metadata={}
        )
        message = f"You are now following {team.name}!"
    else:
        message = f"You unfollowed {team.name}."
    
    if request.headers.get('Content-Type') == 'application/json':
        return JsonResponse({
            'success': True,
            'following': is_following,
            'follower_count': team.get_follower_count(),
            'message': message
        })
    
    messages.success(request, message)
    return redirect('teams:teams_social:team_social_detail', team_slug=team.slug)


@login_required
@require_POST
def upload_team_banner(request, team_slug):
    """Upload team banner image (captain only)."""
    team = get_object_or_404(Team, slug=team_slug)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    if not team.is_captain(user_profile):
        return HttpResponseForbidden("Only team captains can upload banner images.")
    
    form = TeamBannerForm(request.POST, request.FILES, team=team)
    
    if form.is_valid():
        form.save()
        
        # Create activity
        TeamActivity.objects.create(
            team=team,
            activity_type='banner_updated',
            user=user_profile,
            description=f"{user_profile.user.get_full_name() or user_profile.user.username} updated the team banner",
            metadata={}
        )
        
        messages.success(request, "Team banner updated successfully!")
    else:
        messages.error(request, "Error uploading banner. Please check your image.")
    
    return redirect('teams:teams_social:team_social_detail', team_slug=team.slug)


@login_required
def team_posts_feed(request, team_slug):
    """API endpoint for loading more posts (AJAX)."""
    team = get_object_or_404(Team, slug=team_slug)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    page = request.GET.get('page', 1)
    
    # Get posts with proper visibility filtering
    posts_list = TeamPost.objects.filter(
        team=team,
        published_at__isnull=False
    ).select_related('author__user').prefetch_related('media', 'likes')
    
    is_member = team.is_member(user_profile)
    is_following = team.is_followed_by(user_profile)
    
    if not is_member:
        if is_following:
            posts_list = posts_list.filter(visibility__in=['public', 'followers'])
        else:
            posts_list = posts_list.filter(visibility='public')
    
    paginator = Paginator(posts_list, 10)
    posts_page = paginator.get_page(page)
    
    posts_data = []
    for post in posts_page:
        post_data = {
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'author_name': post.author.user.get_full_name() or post.author.user.username,
            'created_at': post.created_at.isoformat(),
            'like_count': post.likes.count(),
            'comment_count': post.comments.count(),
            'user_liked': post.likes.filter(user=user_profile).exists(),
            'media': [{'url': media.file.url, 'alt_text': media.alt_text} for media in post.media.all()]
        }
        posts_data.append(post_data)
    
    return JsonResponse({
        'posts': posts_data,
        'has_next': posts_page.has_next(),
        'has_previous': posts_page.has_previous(),
        'current_page': posts_page.number,
        'total_pages': paginator.num_pages
    })


@login_required
def team_activity_feed(request, team_slug):
    """API endpoint for team activity feed."""
    team = get_object_or_404(Team, slug=team_slug)
    
    activities = team.get_activity_feed(limit=20)
    
    activities_data = []
    for activity in activities:
        activity_data = {
            'type': activity.activity_type,
            'description': activity.description,
            'user_name': activity.user.user.get_full_name() or activity.user.user.username,
            'created_at': activity.created_at.isoformat(),
            'metadata': activity.metadata
        }
        activities_data.append(activity_data)
    
    return JsonResponse({'activities': activities_data})


@login_required
@require_http_methods(["GET", "POST"])
def edit_team_post(request, team_slug, post_id):
    """Edit an existing team post."""
    team = get_object_or_404(Team, slug=team_slug)
    post = get_object_or_404(TeamPost, id=post_id, team=team)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Check permissions - only post author can edit
    if post.author != user_profile:
        messages.error(request, "You can only edit your own posts.")
        return redirect('teams:teams_social:team_social_detail', team_slug=team.slug)
    
    if request.method == 'POST':
        form = TeamPostForm(request.POST, request.FILES, instance=post, team=team, author=user_profile)
        
        if form.is_valid():
            with transaction.atomic():
                updated_post = form.save()
                updated_post.is_edited = True
                updated_post.save()
                
                # Handle new media uploads if any
                if 'media' in request.FILES:
                    media_files = request.FILES.getlist('media')
                    for media_file in media_files:
                        from ..models.social import TeamPostMedia
                        import os
                        
                        # Determine media type based on file extension
                        file_extension = os.path.splitext(media_file.name)[1].lower()
                        if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                            media_type = 'image'
                        elif file_extension in ['.mp4', '.mov', '.avi', '.webm']:
                            media_type = 'video'
                        else:
                            media_type = 'document'
                        
                        # Create media object
                        TeamPostMedia.objects.create(
                            post=updated_post,
                            file=media_file,
                            media_type=media_type,
                            file_size=media_file.size
                        )
                
                messages.success(request, "Post updated successfully!")
                return redirect('teams:teams_social:team_social_detail', team_slug=team.slug)
        else:
            # Debug: show specific form errors
            error_messages = []
            for field, errors in form.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            
            error_text = "Form errors: " + "; ".join(error_messages) if error_messages else "Unknown form validation error"
            print(f"DEBUG - Form data: {request.POST}")
            print(f"DEBUG - Form errors: {form.errors}")
            print(f"DEBUG - Form is_valid: {form.is_valid()}")
            messages.error(request, f"Error updating post: {error_text}")
    else:
        form = TeamPostForm(instance=post, team=team, author=user_profile)
    
    context = {
        'team': team,
        'post': post,
        'form': form,
        'user_profile': user_profile,
        'is_editing': True,
    }
    
    return render(request, 'teams/edit_post.html', context)


@login_required
@require_POST
def delete_team_post(request, team_slug, post_id):
    """Delete a team post."""
    team = get_object_or_404(Team, slug=team_slug)
    post = get_object_or_404(TeamPost, id=post_id, team=team)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Check permissions - post author or team captain can delete
    if post.author != user_profile and not team.is_captain(user_profile):
        return JsonResponse({"error": "You don't have permission to delete this post."}, status=403)
    
    try:
        post.delete()
        
        # Create activity for deletion (if not deleting own post)
        if post.author != user_profile:
            TeamActivity.objects.create(
                team=team,
                activity_type='post_deleted',
                actor=user_profile,
                description=f"{user_profile.user.get_full_name() or user_profile.user.username} deleted a team post"
            )
        
        return JsonResponse({"success": True, "message": "Post deleted successfully."})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_POST
def delete_post_media(request, team_slug, post_id, media_id):
    """Delete a specific media file from a post."""
    team = get_object_or_404(Team, slug=team_slug)
    post = get_object_or_404(TeamPost, id=post_id, team=team)
    user_profile = get_object_or_404(UserProfile, user=request.user)
    
    # Check permissions - only post author can delete media
    if post.author != user_profile:
        return JsonResponse({"error": "You can only delete media from your own posts."}, status=403)
    
    try:
        from ..models.social import TeamPostMedia
        media = get_object_or_404(TeamPostMedia, id=media_id, post=post)
        media.delete()
        
        return JsonResponse({"success": True, "message": "Media deleted successfully."})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)
