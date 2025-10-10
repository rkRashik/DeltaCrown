"""
Chat Service - Business logic for team chat functionality (Task 7 Phase 2)

Handles message operations, mentions, attachments, reactions, and read receipts.
"""
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import UploadedFile
from typing import Optional, List, Dict, Any
import re

from apps.teams.models import (
    Team,
    TeamMembership,
    TeamChatMessage,
    ChatMessageReaction,
    ChatReadReceipt,
    ChatTypingIndicator,
)
from apps.user_profile.models import UserProfile
from apps.notifications.models import Notification


class MentionParser:
    """
    Parse @mentions from chat messages and extract mentioned users.
    """
    
    # Match @username or @"username with spaces"
    MENTION_PATTERN = re.compile(r'@(?:"([^"]+)"|(\w+))')
    
    @classmethod
    def parse_mentions(cls, message_text: str, team: Team) -> List[UserProfile]:
        """
        Extract mentioned users from message text.
        
        Args:
            message_text: The message content
            team: The team context
            
        Returns:
            List of UserProfile objects that were mentioned
        """
        mentioned_users = []
        matches = cls.MENTION_PATTERN.finditer(message_text)
        
        for match in matches:
            # Get username from either quoted or unquoted format
            username = match.group(1) or match.group(2)
            
            try:
                # Find user in team members
                membership = TeamMembership.objects.select_related('user_profile__user').get(
                    team=team,
                    user_profile__user__username__iexact=username,
                    status='active'
                )
                mentioned_users.append(membership.user_profile)
            except TeamMembership.DoesNotExist:
                # Username not found or not an active member
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_mentions = []
        for user in mentioned_users:
            if user.id not in seen:
                seen.add(user.id)
                unique_mentions.append(user)
        
        return unique_mentions
    
    @classmethod
    def highlight_mentions(cls, message_text: str) -> str:
        """
        Replace @mentions with HTML highlighting for display.
        
        Args:
            message_text: The message content
            
        Returns:
            Message text with mentions highlighted
        """
        def replace_mention(match):
            username = match.group(1) or match.group(2)
            return f'<span class="mention">@{username}</span>'
        
        return cls.MENTION_PATTERN.sub(replace_mention, message_text)


class AttachmentValidator:
    """
    Validate chat message attachments.
    """
    
    # Allowed file types and their MIME types
    ALLOWED_TYPES = {
        'image': {
            'extensions': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
            'mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
            'max_size': 5 * 1024 * 1024,  # 5MB
        },
        'document': {
            'extensions': ['.pdf', '.doc', '.docx', '.txt', '.xlsx', '.xls', '.pptx', '.ppt'],
            'mime_types': [
                'application/pdf',
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'text/plain',
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            ],
            'max_size': 10 * 1024 * 1024,  # 10MB
        },
        'video': {
            'extensions': ['.mp4', '.webm', '.mov'],
            'mime_types': ['video/mp4', 'video/webm', 'video/quicktime'],
            'max_size': 50 * 1024 * 1024,  # 50MB
        },
        'audio': {
            'extensions': ['.mp3', '.wav', '.ogg'],
            'mime_types': ['audio/mpeg', 'audio/wav', 'audio/ogg'],
            'max_size': 10 * 1024 * 1024,  # 10MB
        },
    }
    
    @classmethod
    def validate_file(cls, file: UploadedFile) -> tuple[str, bool]:
        """
        Validate uploaded file.
        
        Args:
            file: The uploaded file
            
        Returns:
            Tuple of (attachment_type, is_valid)
            
        Raises:
            ValidationError: If file is invalid
        """
        # Get file extension
        file_name = file.name.lower()
        file_ext = '.' + file_name.split('.')[-1] if '.' in file_name else ''
        
        # Determine attachment type
        attachment_type = None
        for type_name, type_config in cls.ALLOWED_TYPES.items():
            if file_ext in type_config['extensions']:
                attachment_type = type_name
                break
        
        if not attachment_type:
            raise ValidationError(f"File type '{file_ext}' is not allowed")
        
        # Check MIME type
        type_config = cls.ALLOWED_TYPES[attachment_type]
        if file.content_type not in type_config['mime_types']:
            raise ValidationError(
                f"MIME type '{file.content_type}' does not match expected types for {attachment_type}"
            )
        
        # Check file size
        if file.size > type_config['max_size']:
            max_size_mb = type_config['max_size'] / (1024 * 1024)
            raise ValidationError(
                f"File size ({file.size / (1024 * 1024):.2f}MB) exceeds maximum allowed "
                f"size ({max_size_mb}MB) for {attachment_type}"
            )
        
        return attachment_type, True


class ChatService:
    """
    Service class for team chat operations.
    """
    
    @staticmethod
    def _check_team_access(user_profile: UserProfile, team: Team, require_active: bool = True) -> TeamMembership:
        """
        Check if user has access to team chat.
        
        Args:
            user_profile: The user to check
            team: The team
            require_active: Whether to require active membership
            
        Returns:
            TeamMembership object
            
        Raises:
            PermissionDenied: If user doesn't have access
        """
        try:
            membership = TeamMembership.objects.get(
                team=team,
                user_profile=user_profile
            )
            
            if require_active and membership.status != 'active':
                raise PermissionDenied("You are not an active member of this team")
            
            return membership
        except TeamMembership.DoesNotExist:
            raise PermissionDenied("You are not a member of this team")
    
    @classmethod
    @transaction.atomic
    def send_message(
        cls,
        team: Team,
        sender: UserProfile,
        message: str,
        reply_to: Optional[TeamChatMessage] = None,
        attachment: Optional[UploadedFile] = None
    ) -> TeamChatMessage:
        """
        Send a new chat message.
        
        Args:
            team: The team to send message to
            sender: The user sending the message
            message: The message content
            reply_to: Optional message being replied to
            attachment: Optional file attachment
            
        Returns:
            The created TeamChatMessage
            
        Raises:
            PermissionDenied: If user cannot send messages
            ValidationError: If message or attachment is invalid
        """
        # Check access
        cls._check_team_access(sender, team)
        
        # Validate message
        if not message or not message.strip():
            raise ValidationError("Message cannot be empty")
        
        if len(message) > 5000:
            raise ValidationError("Message cannot exceed 5000 characters")
        
        # Validate attachment if present
        attachment_type = None
        if attachment:
            attachment_type, _ = AttachmentValidator.validate_file(attachment)
        
        # Create message
        chat_message = TeamChatMessage.objects.create(
            team=team,
            sender=sender,
            message=message.strip(),
            reply_to=reply_to,
            attachment=attachment,
            attachment_type=attachment_type
        )
        
        # Parse and save mentions
        mentioned_users = MentionParser.parse_mentions(message, team)
        if mentioned_users:
            chat_message.mentions.set(mentioned_users)
            
            # Create notifications for mentioned users
            for mentioned_user in mentioned_users:
                if mentioned_user != sender:  # Don't notify yourself
                    Notification.objects.create(
                        user_profile=mentioned_user,
                        notification_type='team_chat_mention',
                        title=f"Mentioned in {team.name}",
                        message=f"{sender.user.username} mentioned you in team chat",
                        link=f"/teams/{team.slug}/chat/",
                        related_object_id=chat_message.id
                    )
        
        return chat_message
    
    @classmethod
    @transaction.atomic
    def edit_message(
        cls,
        message: TeamChatMessage,
        editor: UserProfile,
        new_content: str
    ) -> TeamChatMessage:
        """
        Edit an existing message.
        
        Args:
            message: The message to edit
            editor: The user editing the message
            new_content: The new message content
            
        Returns:
            The updated message
            
        Raises:
            PermissionDenied: If user cannot edit message
            ValidationError: If new content is invalid
        """
        # Check if user can edit (must be sender)
        if message.sender != editor:
            raise PermissionDenied("You can only edit your own messages")
        
        if message.is_deleted:
            raise ValidationError("Cannot edit a deleted message")
        
        # Validate new content
        if not new_content or not new_content.strip():
            raise ValidationError("Message cannot be empty")
        
        if len(new_content) > 5000:
            raise ValidationError("Message cannot exceed 5000 characters")
        
        # Update message
        message.message = new_content.strip()
        message.mark_as_edited()
        
        # Update mentions
        mentioned_users = MentionParser.parse_mentions(new_content, message.team)
        message.mentions.set(mentioned_users)
        
        return message
    
    @classmethod
    @transaction.atomic
    def delete_message(
        cls,
        message: TeamChatMessage,
        deleter: UserProfile
    ) -> TeamChatMessage:
        """
        Soft delete a message.
        
        Args:
            message: The message to delete
            deleter: The user deleting the message
            
        Returns:
            The deleted message
            
        Raises:
            PermissionDenied: If user cannot delete message
        """
        # Check access
        membership = cls._check_team_access(deleter, message.team)
        
        # Can delete if: message sender, team owner, or team admin
        can_delete = (
            message.sender == deleter or
            message.team.owner == deleter or
            membership.role in ['owner', 'admin']
        )
        
        if not can_delete:
            raise PermissionDenied("You don't have permission to delete this message")
        
        # Soft delete
        message.soft_delete()
        
        return message
    
    @classmethod
    @transaction.atomic
    def add_reaction(
        cls,
        message: TeamChatMessage,
        user: UserProfile,
        emoji: str
    ) -> ChatMessageReaction:
        """
        Add an emoji reaction to a message.
        
        Args:
            message: The message to react to
            user: The user adding the reaction
            emoji: The emoji character
            
        Returns:
            The created or existing reaction
            
        Raises:
            PermissionDenied: If user cannot react
            ValidationError: If emoji is invalid
        """
        # Check access
        cls._check_team_access(user, message.team)
        
        if message.is_deleted:
            raise ValidationError("Cannot react to a deleted message")
        
        # Validate emoji (simple check - just ensure it's not empty and not too long)
        if not emoji or len(emoji) > 10:
            raise ValidationError("Invalid emoji")
        
        # Create or get reaction
        reaction, created = ChatMessageReaction.objects.get_or_create(
            message=message,
            user=user,
            emoji=emoji
        )
        
        return reaction
    
    @classmethod
    @transaction.atomic
    def remove_reaction(
        cls,
        message: TeamChatMessage,
        user: UserProfile,
        emoji: str
    ) -> bool:
        """
        Remove an emoji reaction from a message.
        
        Args:
            message: The message
            user: The user removing the reaction
            emoji: The emoji character
            
        Returns:
            True if reaction was removed, False if it didn't exist
        """
        deleted_count, _ = ChatMessageReaction.objects.filter(
            message=message,
            user=user,
            emoji=emoji
        ).delete()
        
        return deleted_count > 0
    
    @classmethod
    @transaction.atomic
    def mark_as_read(
        cls,
        team: Team,
        user: UserProfile,
        last_read_message: TeamChatMessage
    ) -> ChatReadReceipt:
        """
        Mark messages as read up to a specific message.
        
        Args:
            team: The team
            user: The user marking as read
            last_read_message: The last message read
            
        Returns:
            The updated or created read receipt
            
        Raises:
            PermissionDenied: If user cannot access team
        """
        # Check access
        cls._check_team_access(user, team)
        
        # Create or update read receipt
        receipt = ChatReadReceipt.mark_as_read(user, team, last_read_message)
        
        return receipt
    
    @classmethod
    def get_unread_count(cls, team: Team, user: UserProfile) -> int:
        """
        Get count of unread messages for user in team.
        
        Args:
            team: The team
            user: The user
            
        Returns:
            Number of unread messages
        """
        try:
            cls._check_team_access(user, team)
            return ChatReadReceipt.get_unread_count(user, team)
        except PermissionDenied:
            return 0
    
    @classmethod
    @transaction.atomic
    def set_typing(cls, team: Team, user: UserProfile) -> ChatTypingIndicator:
        """
        Set user as typing in team chat.
        
        Args:
            team: The team
            user: The user
            
        Returns:
            The typing indicator
            
        Raises:
            PermissionDenied: If user cannot access team
        """
        # Check access
        cls._check_team_access(user, team)
        
        # Set typing indicator
        indicator = ChatTypingIndicator.set_typing(user, team)
        
        return indicator
    
    @classmethod
    def get_typing_users(cls, team: Team) -> List[UserProfile]:
        """
        Get list of users currently typing in team chat.
        
        Args:
            team: The team
            
        Returns:
            List of UserProfile objects
        """
        return ChatTypingIndicator.get_typing_users(team)
    
    @classmethod
    @transaction.atomic
    def clear_typing(cls, team: Team, user: UserProfile) -> bool:
        """
        Clear typing indicator for user.
        
        Args:
            team: The team
            user: The user
            
        Returns:
            True if indicator was cleared
        """
        return ChatTypingIndicator.clear_typing(user, team)
    
    @classmethod
    @transaction.atomic
    def pin_message(
        cls,
        message: TeamChatMessage,
        user: UserProfile
    ) -> TeamChatMessage:
        """
        Toggle pin status of a message.
        
        Args:
            message: The message to pin/unpin
            user: The user performing the action
            
        Returns:
            The updated message
            
        Raises:
            PermissionDenied: If user cannot pin messages
        """
        # Check access - only owner/admin can pin
        membership = cls._check_team_access(user, message.team)
        
        if membership.role not in ['owner', 'admin'] and message.team.owner != user:
            raise PermissionDenied("Only team owners and admins can pin messages")
        
        if message.is_deleted:
            raise ValidationError("Cannot pin a deleted message")
        
        # Toggle pin
        message.toggle_pin()
        
        return message
    
    @classmethod
    def get_team_messages(
        cls,
        team: Team,
        user: UserProfile,
        limit: int = 50,
        before_message_id: Optional[int] = None
    ) -> List[TeamChatMessage]:
        """
        Get messages for team chat with pagination.
        
        Args:
            team: The team
            user: The user requesting messages
            limit: Maximum number of messages to return
            before_message_id: Get messages before this message ID (for pagination)
            
        Returns:
            List of TeamChatMessage objects
            
        Raises:
            PermissionDenied: If user cannot access team
        """
        # Check access
        cls._check_team_access(user, team)
        
        # Build query
        queryset = TeamChatMessage.objects.filter(
            team=team,
            is_deleted=False
        ).select_related(
            'sender__user',
            'reply_to__sender__user'
        ).prefetch_related(
            'mentions__user',
            'reactions__user'
        ).order_by('-created_at')
        
        # Apply pagination
        if before_message_id:
            queryset = queryset.filter(id__lt=before_message_id)
        
        # Limit results
        messages = list(queryset[:limit])
        
        # Reverse to get chronological order
        messages.reverse()
        
        return messages
