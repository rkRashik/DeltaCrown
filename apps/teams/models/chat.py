"""
Team Chat Models (Task 7 - Social & Community Integration)

Real-time team chat functionality with mentions, attachments, and reactions.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import FileExtensionValidator


class TeamChatMessage(models.Model):
    """
    Real-time chat messages within a team.
    Supports mentions, attachments, replies, and reactions.
    """
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='chat_messages',
        help_text="Team this message belongs to"
    )
    
    sender = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='sent_messages',
        help_text="User who sent the message"
    )
    
    message = models.TextField(
        help_text="Message content (supports markdown)"
    )
    
    # Reply/Thread Support
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        help_text="Original message if this is a reply"
    )
    
    # Mentions
    mentions = models.ManyToManyField(
        'user_profile.UserProfile',
        blank=True,
        related_name='mentioned_in_messages',
        help_text="Users mentioned in this message (@username)"
    )
    
    # Attachments
    attachment = models.FileField(
        upload_to='team_chat/%Y/%m/%d/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'pdf', 'doc', 'docx', 'txt']
            )
        ],
        help_text="Optional file attachment"
    )
    
    attachment_type = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('image', 'Image'),
            ('document', 'Document'),
            ('other', 'Other'),
        ],
        help_text="Type of attachment"
    )
    
    # Message State
    is_edited = models.BooleanField(
        default=False,
        help_text="Whether message has been edited"
    )
    
    is_deleted = models.BooleanField(
        default=False,
        help_text="Soft delete flag"
    )
    
    is_pinned = models.BooleanField(
        default=False,
        help_text="Whether message is pinned to chat"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'teams_chat_message'
        verbose_name = 'Team Chat Message'
        verbose_name_plural = 'Team Chat Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['team', 'created_at']),
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['is_deleted', 'created_at']),
        ]
    
    def __str__(self):
        preview = self.message[:50] + '...' if len(self.message) > 50 else self.message
        return f"{self.sender.user.username} in {self.team.name}: {preview}"
    
    def mark_as_edited(self):
        """Mark message as edited"""
        self.is_edited = True
        self.edited_at = timezone.now()
        self.save(update_fields=['is_edited', 'edited_at'])
    
    def soft_delete(self):
        """Soft delete message"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])
    
    def toggle_pin(self):
        """Toggle pin status"""
        self.is_pinned = not self.is_pinned
        self.save(update_fields=['is_pinned'])
    
    @property
    def reply_count(self):
        """Get number of replies to this message"""
        return self.replies.filter(is_deleted=False).count()
    
    @property
    def reaction_summary(self):
        """Get summary of reactions"""
        reactions = self.reactions.values('emoji').annotate(
            count=models.Count('id')
        ).order_by('-count')
        return list(reactions)


class ChatMessageReaction(models.Model):
    """
    Emoji reactions to chat messages.
    Users can react with emojis to messages.
    """
    
    message = models.ForeignKey(
        TeamChatMessage,
        on_delete=models.CASCADE,
        related_name='reactions'
    )
    
    user = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='chat_reactions'
    )
    
    emoji = models.CharField(
        max_length=50,
        help_text="Emoji or reaction identifier"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'teams_chat_reaction'
        verbose_name = 'Chat Message Reaction'
        verbose_name_plural = 'Chat Message Reactions'
        unique_together = ['message', 'user', 'emoji']
        indexes = [
            models.Index(fields=['message', 'emoji']),
        ]
    
    def __str__(self):
        return f"{self.user.user.username} reacted {self.emoji} to message {self.message_id}"


class ChatReadReceipt(models.Model):
    """
    Track which messages have been read by which users.
    Used for unread message badges.
    """
    
    user = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='chat_read_receipts'
    )
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='chat_read_receipts'
    )
    
    last_read_message = models.ForeignKey(
        TeamChatMessage,
        on_delete=models.CASCADE,
        help_text="Last message read by this user in this team"
    )
    
    last_read_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teams_chat_read_receipt'
        verbose_name = 'Chat Read Receipt'
        verbose_name_plural = 'Chat Read Receipts'
        unique_together = ['user', 'team']
        indexes = [
            models.Index(fields=['user', 'team']),
        ]
    
    def __str__(self):
        return f"{self.user.user.username} in {self.team.name} - last read: {self.last_read_at}"
    
    @classmethod
    def mark_as_read(cls, user_profile, team, message):
        """Mark messages as read up to a specific message"""
        receipt, created = cls.objects.update_or_create(
            user=user_profile,
            team=team,
            defaults={
                'last_read_message': message
            }
        )
        return receipt
    
    @classmethod
    def get_unread_count(cls, user_profile, team):
        """Get count of unread messages for user in team"""
        try:
            receipt = cls.objects.get(user=user_profile, team=team)
            unread_count = TeamChatMessage.objects.filter(
                team=team,
                is_deleted=False,
                created_at__gt=receipt.last_read_message.created_at
            ).count()
            return unread_count
        except cls.DoesNotExist:
            # User hasn't read any messages yet
            return TeamChatMessage.objects.filter(
                team=team,
                is_deleted=False
            ).count()


class ChatTypingIndicator(models.Model):
    """
    Track who is currently typing in team chat.
    Used for "X is typing..." indicators.
    """
    
    user = models.ForeignKey(
        'user_profile.UserProfile',
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    
    team = models.ForeignKey(
        'teams.Team',
        on_delete=models.CASCADE,
        related_name='typing_indicators'
    )
    
    started_typing_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teams_chat_typing'
        verbose_name = 'Chat Typing Indicator'
        verbose_name_plural = 'Chat Typing Indicators'
        unique_together = ['user', 'team']
        indexes = [
            models.Index(fields=['team', 'started_typing_at']),
        ]
    
    def __str__(self):
        return f"{self.user.user.username} typing in {self.team.name}"
    
    @classmethod
    def set_typing(cls, user_profile, team):
        """Mark user as typing in team"""
        indicator, created = cls.objects.update_or_create(
            user=user_profile,
            team=team
        )
        return indicator
    
    @classmethod
    def get_typing_users(cls, team, timeout_seconds=10):
        """Get list of users currently typing (within timeout)"""
        cutoff_time = timezone.now() - timezone.timedelta(seconds=timeout_seconds)
        typing_users = cls.objects.filter(
            team=team,
            started_typing_at__gte=cutoff_time
        ).select_related('user__user')
        return [indicator.user for indicator in typing_users]
    
    @classmethod
    def clear_typing(cls, user_profile, team):
        """Clear typing indicator for user"""
        cls.objects.filter(user=user_profile, team=team).delete()
