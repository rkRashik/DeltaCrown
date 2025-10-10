"""
Chat Views - Team chat interface and API endpoints (Task 7 Phase 3)

Provides web interface and REST API for team chat functionality.
"""
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.db.models import Prefetch, Q
from typing import Dict, Any, List

from apps.teams.models import Team, TeamChatMessage, ChatMessageReaction
from apps.teams.services import ChatService
from apps.user_profile.models import UserProfile


class TeamChatView(LoginRequiredMixin, TemplateView):
    """
    Main team chat interface.
    Displays chat messages and input form.
    """
    template_name = 'teams/team_chat.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get team
        team_slug = self.kwargs.get('team_slug')
        team = get_object_or_404(Team, slug=team_slug)
        
        # Check access
        user_profile = self.request.user.profile
        try:
            ChatService._check_team_access(user_profile, team)
        except PermissionDenied:
            raise PermissionDenied("You don't have access to this team's chat")
        
        # Get recent messages (initial load - 50 messages)
        messages = ChatService.get_team_messages(
            team=team,
            user=user_profile,
            limit=50
        )
        
        # Get unread count
        unread_count = ChatService.get_unread_count(team, user_profile)
        
        # Get currently typing users
        typing_users = ChatService.get_typing_users(team)
        typing_users = [u for u in typing_users if u != user_profile]
        
        context.update({
            'team': team,
            'messages': messages,
            'unread_count': unread_count,
            'typing_users': typing_users,
            'can_pin': self._can_moderate(user_profile, team),
        })
        
        return context
    
    def _can_moderate(self, user_profile: UserProfile, team: Team) -> bool:
        """Check if user can moderate chat (pin/delete others' messages)"""
        if team.owner == user_profile:
            return True
        
        try:
            from apps.teams.models import TeamMembership
            membership = TeamMembership.objects.get(team=team, user_profile=user_profile)
            return membership.role in ['owner', 'admin']
        except TeamMembership.DoesNotExist:
            return False


class ChatAPIView(LoginRequiredMixin, View):
    """
    REST API for chat operations.
    Handles: send, edit, delete, react, typing, mark_read
    """
    
    def post(self, request, team_slug: str):
        """Handle chat API POST requests"""
        team = get_object_or_404(Team, slug=team_slug)
        user_profile = request.user.profile
        
        # Get action
        action = request.POST.get('action')
        
        if action == 'send_message':
            return self._send_message(request, team, user_profile)
        elif action == 'edit_message':
            return self._edit_message(request, team, user_profile)
        elif action == 'delete_message':
            return self._delete_message(request, team, user_profile)
        elif action == 'add_reaction':
            return self._add_reaction(request, team, user_profile)
        elif action == 'remove_reaction':
            return self._remove_reaction(request, team, user_profile)
        elif action == 'pin_message':
            return self._pin_message(request, team, user_profile)
        elif action == 'set_typing':
            return self._set_typing(request, team, user_profile)
        elif action == 'clear_typing':
            return self._clear_typing(request, team, user_profile)
        elif action == 'mark_read':
            return self._mark_read(request, team, user_profile)
        else:
            return JsonResponse({'error': 'Invalid action'}, status=400)
    
    def get(self, request, team_slug: str):
        """Handle chat API GET requests (load more messages)"""
        team = get_object_or_404(Team, slug=team_slug)
        user_profile = request.user.profile
        
        # Get before_id for pagination
        before_id = request.GET.get('before_id')
        limit = int(request.GET.get('limit', 50))
        
        try:
            messages = ChatService.get_team_messages(
                team=team,
                user=user_profile,
                limit=limit,
                before_message_id=int(before_id) if before_id else None
            )
            
            # Serialize messages
            messages_data = [self._serialize_message(msg) for msg in messages]
            
            return JsonResponse({
                'success': True,
                'messages': messages_data,
                'has_more': len(messages) == limit
            })
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def _send_message(self, request, team, user_profile):
        """Send a new message"""
        message_text = request.POST.get('message', '').strip()
        reply_to_id = request.POST.get('reply_to')
        attachment = request.FILES.get('attachment')
        
        try:
            # Get reply_to message if provided
            reply_to = None
            if reply_to_id:
                reply_to = TeamChatMessage.objects.get(id=reply_to_id, team=team)
            
            # Send message
            message = ChatService.send_message(
                team=team,
                sender=user_profile,
                message=message_text,
                reply_to=reply_to,
                attachment=attachment
            )
            
            # Mark as read automatically
            ChatService.mark_as_read(team, user_profile, message)
            
            return JsonResponse({
                'success': True,
                'message': self._serialize_message(message)
            })
        except (ValidationError, PermissionDenied) as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def _edit_message(self, request, team, user_profile):
        """Edit an existing message"""
        message_id = request.POST.get('message_id')
        new_content = request.POST.get('content', '').strip()
        
        try:
            message = TeamChatMessage.objects.get(id=message_id, team=team)
            message = ChatService.edit_message(message, user_profile, new_content)
            
            return JsonResponse({
                'success': True,
                'message': self._serialize_message(message)
            })
        except TeamChatMessage.DoesNotExist:
            return JsonResponse({'error': 'Message not found'}, status=404)
        except (ValidationError, PermissionDenied) as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def _delete_message(self, request, team, user_profile):
        """Delete a message"""
        message_id = request.POST.get('message_id')
        
        try:
            message = TeamChatMessage.objects.get(id=message_id, team=team)
            ChatService.delete_message(message, user_profile)
            
            return JsonResponse({'success': True})
        except TeamChatMessage.DoesNotExist:
            return JsonResponse({'error': 'Message not found'}, status=404)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
    
    def _add_reaction(self, request, team, user_profile):
        """Add emoji reaction to message"""
        message_id = request.POST.get('message_id')
        emoji = request.POST.get('emoji')
        
        try:
            message = TeamChatMessage.objects.get(id=message_id, team=team)
            reaction = ChatService.add_reaction(message, user_profile, emoji)
            
            return JsonResponse({
                'success': True,
                'reaction_summary': message.reaction_summary
            })
        except TeamChatMessage.DoesNotExist:
            return JsonResponse({'error': 'Message not found'}, status=404)
        except (ValidationError, PermissionDenied) as e:
            return JsonResponse({'error': str(e)}, status=400)
    
    def _remove_reaction(self, request, team, user_profile):
        """Remove emoji reaction from message"""
        message_id = request.POST.get('message_id')
        emoji = request.POST.get('emoji')
        
        try:
            message = TeamChatMessage.objects.get(id=message_id, team=team)
            removed = ChatService.remove_reaction(message, user_profile, emoji)
            
            return JsonResponse({
                'success': True,
                'removed': removed,
                'reaction_summary': message.reaction_summary
            })
        except TeamChatMessage.DoesNotExist:
            return JsonResponse({'error': 'Message not found'}, status=404)
    
    def _pin_message(self, request, team, user_profile):
        """Pin/unpin a message"""
        message_id = request.POST.get('message_id')
        
        try:
            message = TeamChatMessage.objects.get(id=message_id, team=team)
            message = ChatService.pin_message(message, user_profile)
            
            return JsonResponse({
                'success': True,
                'is_pinned': message.is_pinned
            })
        except TeamChatMessage.DoesNotExist:
            return JsonResponse({'error': 'Message not found'}, status=404)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
    
    def _set_typing(self, request, team, user_profile):
        """Set user as typing"""
        try:
            ChatService.set_typing(team, user_profile)
            return JsonResponse({'success': True})
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
    
    def _clear_typing(self, request, team, user_profile):
        """Clear typing indicator"""
        ChatService.clear_typing(team, user_profile)
        return JsonResponse({'success': True})
    
    def _mark_read(self, request, team, user_profile):
        """Mark messages as read"""
        message_id = request.POST.get('message_id')
        
        try:
            message = TeamChatMessage.objects.get(id=message_id, team=team)
            ChatService.mark_as_read(team, user_profile, message)
            
            unread_count = ChatService.get_unread_count(team, user_profile)
            
            return JsonResponse({
                'success': True,
                'unread_count': unread_count
            })
        except TeamChatMessage.DoesNotExist:
            return JsonResponse({'error': 'Message not found'}, status=404)
    
    def _serialize_message(self, message: TeamChatMessage) -> Dict[str, Any]:
        """Serialize message to JSON"""
        from apps.teams.services import MentionParser
        
        return {
            'id': message.id,
            'sender': {
                'id': message.sender.id,
                'username': message.sender.user.username,
                'avatar_url': message.sender.get_avatar_url() if hasattr(message.sender, 'get_avatar_url') else None,
            },
            'message': message.message,
            'message_html': MentionParser.highlight_mentions(message.message),
            'reply_to': {
                'id': message.reply_to.id,
                'sender_username': message.reply_to.sender.user.username,
                'message_preview': message.reply_to.message[:50]
            } if message.reply_to else None,
            'attachment': {
                'url': message.attachment.url,
                'type': message.attachment_type,
                'name': message.attachment.name.split('/')[-1]
            } if message.attachment else None,
            'mentions': [
                {
                    'id': u.id,
                    'username': u.user.username
                } for u in message.mentions.all()
            ],
            'reactions': message.reaction_summary,
            'is_edited': message.is_edited,
            'is_pinned': message.is_pinned,
            'created_at': message.created_at.isoformat(),
            'edited_at': message.edited_at.isoformat() if message.edited_at else None,
        }


class ChatTypingStatusView(LoginRequiredMixin, View):
    """
    API endpoint for checking typing status.
    Used for polling typing indicators.
    """
    
    def get(self, request, team_slug: str):
        """Get list of currently typing users"""
        team = get_object_or_404(Team, slug=team_slug)
        user_profile = request.user.profile
        
        try:
            # Check access
            ChatService._check_team_access(user_profile, team)
            
            # Get typing users (exclude self)
            typing_users = ChatService.get_typing_users(team)
            typing_users = [u for u in typing_users if u != user_profile]
            
            return JsonResponse({
                'success': True,
                'typing_users': [
                    {
                        'id': u.id,
                        'username': u.user.username
                    } for u in typing_users
                ]
            })
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)


class ChatUnreadCountView(LoginRequiredMixin, View):
    """
    API endpoint for getting unread message count.
    Used for badge updates.
    """
    
    def get(self, request, team_slug: str):
        """Get unread message count"""
        team = get_object_or_404(Team, slug=team_slug)
        user_profile = request.user.profile
        
        unread_count = ChatService.get_unread_count(team, user_profile)
        
        return JsonResponse({
            'success': True,
            'unread_count': unread_count
        })
