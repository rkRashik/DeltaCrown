"""
Discussion Board Views - Forum interface and API (Task 7 Phase 3)

Provides discussion board interface for team forums.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.urls import reverse
from django.contrib import messages as django_messages
from typing import Dict, Any, Optional

from apps.teams.models import (
    Team, TeamDiscussionPost, TeamDiscussionComment,
    DiscussionSubscription, DiscussionNotification
)
from apps.teams.services import DiscussionService
from apps.user_profile.models import UserProfile


def _get_markdown_processor():
    """Lazy import of MarkdownProcessor to avoid circular import"""
    from apps.teams.services.markdown_processor import MarkdownProcessor
    return MarkdownProcessor


class DiscussionBoardView(LoginRequiredMixin, ListView):
    """
    Discussion board list view.
    Shows all posts for a team.
    """
    model = TeamDiscussionPost
    template_name = 'teams/discussion_board.html'
    context_object_name = 'posts'
    paginate_by = 20
    
    def get_queryset(self):
        self.team = get_object_or_404(Team, slug=self.kwargs['team_slug'])
        user_profile = self.request.user.profile
        
        # Filter by post type if provided
        post_type = self.request.GET.get('type')
        
        posts = DiscussionService.get_team_posts(
            team=self.team,
            user=user_profile,
            post_type=post_type,
            limit=self.paginate_by,
            offset=0
        )
        
        return posts
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_profile = self.request.user.profile
        
        context.update({
            'team': self.team,
            'post_types': TeamDiscussionPost.POST_TYPES,
            'selected_type': self.request.GET.get('type', ''),
            'can_create_announcement': self._can_create_announcement(user_profile, self.team),
        })
        
        return context
    
    def _can_create_announcement(self, user_profile: UserProfile, team: Team) -> bool:
        """Check if user can create announcements"""
        if team.owner == user_profile:
            return True
        
        try:
            from apps.teams.models import TeamMembership
            membership = TeamMembership.objects.get(team=team, user_profile=user_profile)
            return membership.role in ['owner', 'admin']
        except TeamMembership.DoesNotExist:
            return False


class DiscussionPostDetailView(LoginRequiredMixin, DetailView):
    """
    Discussion post detail view.
    Shows post content and comments.
    """
    model = TeamDiscussionPost
    template_name = 'teams/discussion_post_detail.html'
    context_object_name = 'post'
    
    def get_object(self):
        team_slug = self.kwargs['team_slug']
        post_slug = self.kwargs['post_slug']
        
        self.team = get_object_or_404(Team, slug=team_slug)
        post = get_object_or_404(
            TeamDiscussionPost,
            team=self.team,
            slug=post_slug
        )
        
        # Check if user can view
        user_profile = self.request.user.profile if self.request.user.is_authenticated else None
        if not DiscussionService._can_view_post(post, user_profile):
            raise PermissionDenied("You don't have permission to view this post")
        
        return post
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        user_profile = self.request.user.profile
        
        # Increment views
        DiscussionService.increment_views(post)
        
        # Get comments
        comments = TeamDiscussionComment.objects.filter(
            post=post,
            is_deleted=False
        ).select_related(
            'author__user'
        ).prefetch_related(
            'likes'
        ).order_by('created_at')
        
        # Check if user is subscribed
        is_subscribed = DiscussionSubscription.objects.filter(
            user=user_profile,
            post=post
        ).exists()
        
        # Check if user liked the post
        user_liked = user_profile in post.likes.all()
        
        # Render markdown
        MarkdownProcessor = _get_markdown_processor()
        post_html = MarkdownProcessor.render_with_embeds(post.content)
        
        # Calculate reading time
        reading_time = MarkdownProcessor.estimate_reading_time(post.content)
        
        context.update({
            'team': self.team,
            'post_html': post_html,
            'reading_time': reading_time,
            'comments': comments,
            'is_subscribed': is_subscribed,
            'user_liked': user_liked,
            'can_moderate': self._can_moderate(user_profile, self.team),
        })
        
        return context
    
    def _can_moderate(self, user_profile: UserProfile, team: Team) -> bool:
        """Check if user can moderate discussions"""
        if team.owner == user_profile:
            return True
        
        try:
            from apps.teams.models import TeamMembership
            membership = TeamMembership.objects.get(team=team, user_profile=user_profile)
            return membership.role in ['owner', 'admin']
        except TeamMembership.DoesNotExist:
            return False


class DiscussionPostCreateView(LoginRequiredMixin, View):
    """
    Create a new discussion post.
    """
    
    def get(self, request, team_slug: str):
        """Show create post form"""
        team = get_object_or_404(Team, slug=team_slug)
        user_profile = request.user.profile
        
        # Check access
        try:
            DiscussionService._check_team_access(user_profile, team)
        except PermissionDenied:
            raise PermissionDenied("You don't have access to this team's discussions")
        
        can_create_announcement = self._can_create_announcement(user_profile, team)
        
        return render(request, 'teams/discussion_post_form.html', {
            'team': team,
            'post_types': TeamDiscussionPost.POST_TYPES,
            'can_create_announcement': can_create_announcement,
        })
    
    def post(self, request, team_slug: str):
        """Create the post"""
        team = get_object_or_404(Team, slug=team_slug)
        user_profile = request.user.profile
        
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        post_type = request.POST.get('post_type', 'general')
        is_public = request.POST.get('is_public') == 'on'
        
        try:
            post = DiscussionService.create_post(
                team=team,
                author=user_profile,
                title=title,
                content=content,
                post_type=post_type,
                is_public=is_public
            )
            
            django_messages.success(request, 'Post created successfully!')
            return redirect('teams:discussion_post_detail', team_slug=team.slug, post_slug=post.slug)
        except (ValidationError, PermissionDenied) as e:
            django_messages.error(request, str(e))
            return redirect('teams:discussion_post_create', team_slug=team.slug)
    
    def _can_create_announcement(self, user_profile: UserProfile, team: Team) -> bool:
        """Check if user can create announcements"""
        if team.owner == user_profile:
            return True
        
        try:
            from apps.teams.models import TeamMembership
            membership = TeamMembership.objects.get(team=team, user_profile=user_profile)
            return membership.role in ['owner', 'admin']
        except TeamMembership.DoesNotExist:
            return False


class DiscussionPostEditView(LoginRequiredMixin, View):
    """
    Edit an existing discussion post.
    """
    
    def get(self, request, team_slug: str, post_slug: str):
        """Show edit post form"""
        team = get_object_or_404(Team, slug=team_slug)
        post = get_object_or_404(TeamDiscussionPost, team=team, slug=post_slug)
        user_profile = request.user.profile
        
        # Check if user can edit
        if post.author != user_profile and not self._can_moderate(user_profile, team):
            raise PermissionDenied("You don't have permission to edit this post")
        
        can_edit_type = self._can_moderate(user_profile, team)
        
        return render(request, 'teams/discussion_post_form.html', {
            'team': team,
            'post': post,
            'post_types': TeamDiscussionPost.POST_TYPES,
            'can_edit_type': can_edit_type,
            'is_edit': True,
        })
    
    def post(self, request, team_slug: str, post_slug: str):
        """Update the post"""
        team = get_object_or_404(Team, slug=team_slug)
        post = get_object_or_404(TeamDiscussionPost, team=team, slug=post_slug)
        user_profile = request.user.profile
        
        title = request.POST.get('title')
        content = request.POST.get('content')
        post_type = request.POST.get('post_type')
        is_public = request.POST.get('is_public') == 'on' if request.POST.get('is_public') is not None else None
        
        try:
            post = DiscussionService.edit_post(
                post=post,
                editor=user_profile,
                title=title,
                content=content,
                post_type=post_type,
                is_public=is_public
            )
            
            django_messages.success(request, 'Post updated successfully!')
            return redirect('teams:discussion_post_detail', team_slug=team.slug, post_slug=post.slug)
        except (ValidationError, PermissionDenied) as e:
            django_messages.error(request, str(e))
            return redirect('teams:discussion_post_edit', team_slug=team.slug, post_slug=post.slug)
    
    def _can_moderate(self, user_profile: UserProfile, team: Team) -> bool:
        """Check if user can moderate discussions"""
        if team.owner == user_profile:
            return True
        
        try:
            from apps.teams.models import TeamMembership
            membership = TeamMembership.objects.get(team=team, user_profile=user_profile)
            return membership.role in ['owner', 'admin']
        except TeamMembership.DoesNotExist:
            return False


class DiscussionAPIView(LoginRequiredMixin, View):
    """
    REST API for discussion operations.
    Handles: add_comment, edit_comment, delete_comment, toggle_like, subscribe, etc.
    """
    
    def post(self, request, team_slug: str):
        """Handle discussion API POST requests"""
        team = get_object_or_404(Team, slug=team_slug)
        user_profile = request.user.profile
        
        # Get action
        action = request.POST.get('action')
        
        if action == 'add_comment':
            return self._add_comment(request, team, user_profile)
        elif action == 'edit_comment':
            return self._edit_comment(request, team, user_profile)
        elif action == 'delete_comment':
            return self._delete_comment(request, team, user_profile)
        elif action == 'delete_post':
            return self._delete_post(request, team, user_profile)
        elif action == 'toggle_post_like':
            return self._toggle_post_like(request, team, user_profile)
        elif action == 'toggle_comment_like':
            return self._toggle_comment_like(request, team, user_profile)
        elif action == 'pin_post':
            return self._pin_post(request, team, user_profile)
        elif action == 'lock_post':
            return self._lock_post(request, team, user_profile)
        elif action == 'subscribe':
            return self._subscribe(request, team, user_profile)
        elif action == 'unsubscribe':
            return self._unsubscribe(request, team, user_profile)
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
    
    def _add_comment(self, request, team, user_profile):
        """Add a comment to a post"""
        post_id = request.POST.get('post_id')
        content = request.POST.get('content', '').strip()
        reply_to_id = request.POST.get('reply_to')
        
        try:
            post = TeamDiscussionPost.objects.get(id=post_id, team=team)
            
            reply_to = None
            if reply_to_id:
                reply_to = TeamDiscussionComment.objects.get(id=reply_to_id, post=post)
            
            comment = DiscussionService.add_comment(
                post=post,
                author=user_profile,
                content=content,
                reply_to=reply_to
            )
            
            # Render comment HTML
            MarkdownProcessor = _get_markdown_processor()
            comment_html = MarkdownProcessor.render_markdown(comment.content)
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'author': {
                        'username': comment.author.user.username,
                        'avatar_url': comment.author.get_avatar_url() if hasattr(comment.author, 'get_avatar_url') else None,
                    },
                    'content_html': comment_html,
                    'created_at': comment.created_at.isoformat(),
                    'like_count': 0,
                }
            })
        except TeamDiscussionPost.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)
        except (ValidationError, PermissionDenied) as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def _edit_comment(self, request, team, user_profile):
        """Edit a comment"""
        comment_id = request.POST.get('comment_id')
        new_content = request.POST.get('content', '').strip()
        
        try:
            comment = TeamDiscussionComment.objects.get(id=comment_id, post__team=team)
            comment = DiscussionService.edit_comment(comment, user_profile, new_content)
            
            MarkdownProcessor = _get_markdown_processor()
            comment_html = MarkdownProcessor.render_markdown(comment.content)
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'content_html': comment_html,
                    'is_edited': comment.is_edited,
                }
            })
        except TeamDiscussionComment.DoesNotExist:
            return JsonResponse({'error': 'Comment not found'}, status=404)
        except (ValidationError, PermissionDenied) as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def _delete_comment(self, request, team, user_profile):
        """Delete a comment"""
        comment_id = request.POST.get('comment_id')
        
        try:
            comment = TeamDiscussionComment.objects.get(id=comment_id, post__team=team)
            DiscussionService.delete_comment(comment, user_profile)
            
            return JsonResponse({'success': True})
        except TeamDiscussionComment.DoesNotExist:
            return JsonResponse({'error': 'Comment not found'}, status=404)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
    
    def _delete_post(self, request, team, user_profile):
        """Delete a post"""
        post_id = request.POST.get('post_id')
        
        try:
            post = TeamDiscussionPost.objects.get(id=post_id, team=team)
            DiscussionService.delete_post(post, user_profile)
            
            return JsonResponse({'success': True})
        except TeamDiscussionPost.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
    
    def _toggle_post_like(self, request, team, user_profile):
        """Toggle like on a post"""
        post_id = request.POST.get('post_id')
        
        try:
            post = TeamDiscussionPost.objects.get(id=post_id, team=team)
            is_liked, like_count = DiscussionService.toggle_post_like(post, user_profile)
            
            return JsonResponse({
                'success': True,
                'is_liked': is_liked,
                'like_count': like_count
            })
        except TeamDiscussionPost.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)
        except (ValidationError, PermissionDenied) as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def _toggle_comment_like(self, request, team, user_profile):
        """Toggle like on a comment"""
        comment_id = request.POST.get('comment_id')
        
        try:
            comment = TeamDiscussionComment.objects.get(id=comment_id, post__team=team)
            is_liked, like_count = DiscussionService.toggle_comment_like(comment, user_profile)
            
            return JsonResponse({
                'success': True,
                'is_liked': is_liked,
                'like_count': like_count
            })
        except TeamDiscussionComment.DoesNotExist:
            return JsonResponse({'error': 'Comment not found'}, status=404)
        except (ValidationError, PermissionDenied) as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def _pin_post(self, request, team, user_profile):
        """Pin/unpin a post"""
        post_id = request.POST.get('post_id')
        
        try:
            post = TeamDiscussionPost.objects.get(id=post_id, team=team)
            post = DiscussionService.pin_post(post, user_profile)
            
            return JsonResponse({
                'success': True,
                'is_pinned': post.is_pinned
            })
        except TeamDiscussionPost.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
    
    def _lock_post(self, request, team, user_profile):
        """Lock/unlock a post"""
        post_id = request.POST.get('post_id')
        
        try:
            post = TeamDiscussionPost.objects.get(id=post_id, team=team)
            post = DiscussionService.lock_post(post, user_profile)
            
            return JsonResponse({
                'success': True,
                'is_locked': post.is_locked
            })
        except TeamDiscussionPost.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
    
    def _subscribe(self, request, team, user_profile):
        """Subscribe to post notifications"""
        post_id = request.POST.get('post_id')
        notify_comment = request.POST.get('notify_comment', 'true') == 'true'
        notify_like = request.POST.get('notify_like', 'false') == 'true'
        
        try:
            post = TeamDiscussionPost.objects.get(id=post_id, team=team)
            DiscussionService.subscribe_to_post(post, user_profile, notify_comment, notify_like)
            
            return JsonResponse({'success': True})
        except TeamDiscussionPost.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
    
    def _unsubscribe(self, request, team, user_profile):
        """Unsubscribe from post notifications"""
        post_id = request.POST.get('post_id')
        
        try:
            post = TeamDiscussionPost.objects.get(id=post_id, team=team)
            DiscussionService.unsubscribe_from_post(post, user_profile)
            
            return JsonResponse({'success': True})
        except TeamDiscussionPost.DoesNotExist:
            return JsonResponse({'error': 'Post not found'}, status=404)


class MarkdownPreviewView(LoginRequiredMixin, View):
    """
    API endpoint for markdown preview.
    Used by the markdown editor.
    """
    
    def post(self, request):
        """Render markdown to HTML preview"""
        content = request.POST.get('content', '')
        
        try:
            MarkdownProcessor = _get_markdown_processor()
            html = MarkdownProcessor.render_with_embeds(content)
            reading_time = MarkdownProcessor.estimate_reading_time(content)
            word_count = MarkdownProcessor.count_words(content)
            
            return JsonResponse({
                'success': True,
                'html': html,
                'reading_time': reading_time,
                'word_count': word_count
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
