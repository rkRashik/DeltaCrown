"""
Tournament Archive Model

Handles tournament archiving, cloning, and historical data preservation.
Provides functionality for:
- Archiving completed tournaments
- Cloning tournaments for recurring events
- Restoring archived tournaments
- Tracking archive metadata and history
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from typing import Optional, Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from apps.tournaments.models import Tournament

User = get_user_model()


class TournamentArchive(models.Model):
    """
    Model to manage tournament archiving and cloning.
    
    Features:
    - Archive tournaments with metadata
    - Clone tournaments for recurring events
    - Track archive history and relationships
    - Restore archived tournaments
    - Preserve historical data
    
    Relationships:
    - OneToOne with Tournament (the archived/cloned tournament)
    - ForeignKey to Tournament (source tournament for clones)
    - ForeignKey to User (who archived/cloned it)
    
    Archive Types:
    - ARCHIVED: Tournament is archived (inactive)
    - CLONED: Tournament was cloned from another
    - ACTIVE: Normal active tournament (not archived)
    
    Usage:
        # Archive a tournament
        archive = TournamentArchive.objects.create(
            tournament=tournament,
            archive_type='ARCHIVED',
            archived_by=user,
            archive_reason='Tournament completed'
        )
        
        # Clone a tournament
        new_tournament = source_tournament.clone()
        archive = TournamentArchive.objects.create(
            tournament=new_tournament,
            archive_type='CLONED',
            source_tournament=source_tournament,
            archived_by=user
        )
    """
    
    # Archive Type Choices
    ARCHIVE_TYPE_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
        ('CLONED', 'Cloned'),
    ]
    
    # Core Relationship
    tournament = models.OneToOneField(
        'tournaments.Tournament',
        on_delete=models.CASCADE,
        related_name='archive',
        help_text="The tournament this archive record belongs to"
    )
    
    # Archive Status
    archive_type = models.CharField(
        max_length=20,
        choices=ARCHIVE_TYPE_CHOICES,
        default='ACTIVE',
        help_text="Type of archive status"
    )
    
    is_archived = models.BooleanField(
        default=False,
        help_text="Whether the tournament is archived"
    )
    
    # Archive Metadata
    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the tournament was archived"
    )
    
    archived_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='archived_tournaments',
        help_text="User who archived the tournament"
    )
    
    archive_reason = models.TextField(
        blank=True,
        help_text="Reason for archiving"
    )
    
    # Clone Relationships
    source_tournament = models.ForeignKey(
        'tournaments.Tournament',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='clones',
        help_text="Source tournament if this is a clone"
    )
    
    clone_number = models.PositiveIntegerField(
        default=0,
        help_text="Clone generation number (0 = original, 1 = first clone, etc.)"
    )
    
    cloned_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the tournament was cloned"
    )
    
    cloned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cloned_tournaments',
        help_text="User who cloned the tournament"
    )
    
    # Restore Tracking
    can_restore = models.BooleanField(
        default=True,
        help_text="Whether the tournament can be restored from archive"
    )
    
    restored_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the tournament was restored from archive"
    )
    
    restored_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='restored_tournaments',
        help_text="User who restored the tournament"
    )
    
    # Historical Data Preservation
    original_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Snapshot of tournament data at archive time"
    )
    
    preserve_participants = models.BooleanField(
        default=True,
        help_text="Whether to preserve participant data in archive"
    )
    
    preserve_matches = models.BooleanField(
        default=True,
        help_text="Whether to preserve match data in archive"
    )
    
    preserve_media = models.BooleanField(
        default=True,
        help_text="Whether to preserve media files in archive"
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When this archive record was created"
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="When this archive record was last updated"
    )
    
    # Notes
    notes = models.TextField(
        blank=True,
        help_text="Additional notes about the archive"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Tournament Archive'
        verbose_name_plural = 'Tournament Archives'
        indexes = [
            models.Index(fields=['archive_type', 'is_archived']),
            models.Index(fields=['source_tournament', 'clone_number']),
            models.Index(fields=['archived_at']),
            models.Index(fields=['cloned_at']),
        ]
    
    def __str__(self) -> str:
        """String representation showing tournament and status."""
        status = self.get_archive_type_display()
        return f"{self.tournament.name} - {status}"
    
    # ==================== Property Methods ====================
    
    @property
    def is_active(self) -> bool:
        """Check if tournament is active (not archived)."""
        return self.archive_type == 'ACTIVE' and not self.is_archived
    
    @property
    def is_clone(self) -> bool:
        """Check if tournament is a clone."""
        return self.archive_type == 'CLONED' or self.source_tournament is not None
    
    @property
    def is_original(self) -> bool:
        """Check if tournament is an original (not a clone)."""
        return self.source_tournament is None and self.clone_number == 0
    
    @property
    def has_clones(self) -> bool:
        """Check if this tournament has been cloned."""
        return self.tournament.clones.exists()
    
    @property
    def clone_count(self) -> int:
        """Get number of times this tournament has been cloned."""
        return self.tournament.clones.count()
    
    @property
    def has_been_restored(self) -> bool:
        """Check if tournament has been restored from archive."""
        return self.restored_at is not None
    
    @property
    def archive_age_days(self) -> Optional[int]:
        """Get number of days since archival."""
        if not self.archived_at:
            return None
        delta = timezone.now() - self.archived_at
        return delta.days
    
    @property
    def clone_age_days(self) -> Optional[int]:
        """Get number of days since cloning."""
        if not self.cloned_at:
            return None
        delta = timezone.now() - self.cloned_at
        return delta.days
    
    @property
    def has_original_data(self) -> bool:
        """Check if original data snapshot exists."""
        return bool(self.original_data)
    
    @property
    def preservation_settings(self) -> Dict[str, bool]:
        """Get all preservation settings as dictionary."""
        return {
            'participants': self.preserve_participants,
            'matches': self.preserve_matches,
            'media': self.preserve_media,
        }
    
    @property
    def is_fully_preserved(self) -> bool:
        """Check if all data types are set to be preserved."""
        return (
            self.preserve_participants and
            self.preserve_matches and
            self.preserve_media
        )
    
    @property
    def archive_metadata(self) -> Dict[str, Any]:
        """Get complete archive metadata as dictionary."""
        return {
            'archive_type': self.archive_type,
            'is_archived': self.is_archived,
            'archived_at': self.archived_at,
            'archived_by': self.archived_by.username if self.archived_by else None,
            'archive_reason': self.archive_reason,
            'can_restore': self.can_restore,
            'restored_at': self.restored_at,
            'restored_by': self.restored_by.username if self.restored_by else None,
            'archive_age_days': self.archive_age_days,
        }
    
    @property
    def clone_metadata(self) -> Dict[str, Any]:
        """Get complete clone metadata as dictionary."""
        return {
            'is_clone': self.is_clone,
            'source_tournament': self.source_tournament.name if self.source_tournament else None,
            'clone_number': self.clone_number,
            'cloned_at': self.cloned_at,
            'cloned_by': self.cloned_by.username if self.cloned_by else None,
            'clone_age_days': self.clone_age_days,
            'has_clones': self.has_clones,
            'clone_count': self.clone_count,
        }
    
    # ==================== Validation ====================
    
    def clean(self) -> None:
        """Validate archive data."""
        super().clean()
        
        # Validate archive type consistency
        if self.archive_type == 'ARCHIVED' and not self.is_archived:
            raise ValidationError(
                "Archive type is 'ARCHIVED' but is_archived is False"
            )
        
        if self.is_archived and self.archive_type == 'ACTIVE':
            raise ValidationError(
                "Cannot have archive type 'ACTIVE' when is_archived is True"
            )
        
        # Validate archive metadata
        if self.is_archived and not self.archived_at:
            raise ValidationError(
                "Archived tournaments must have archived_at timestamp"
            )
        
        if self.archived_at and not self.is_archived:
            raise ValidationError(
                "archived_at is set but tournament is not marked as archived"
            )
        
        # Validate clone relationships
        if self.archive_type == 'CLONED' and not self.source_tournament:
            raise ValidationError(
                "Clone tournaments must have a source_tournament"
            )
        
        if self.source_tournament and self.source_tournament == self.tournament:
            raise ValidationError(
                "Tournament cannot be its own source"
            )
        
        # Validate clone number
        if self.source_tournament and self.clone_number == 0:
            raise ValidationError(
                "Clone tournaments must have clone_number > 0"
            )
        
        if not self.source_tournament and self.clone_number > 0:
            raise ValidationError(
                "Only clone tournaments can have clone_number > 0"
            )
        
        # Validate restore capability
        if not self.is_archived and self.restored_at:
            raise ValidationError(
                "Only archived tournaments can have restored_at timestamp"
            )
        
        if self.restored_at and self.restored_at < self.archived_at:
            raise ValidationError(
                "Restore timestamp cannot be before archive timestamp"
            )
    
    # ==================== Archive Operations ====================
    
    def archive(self, user=None, reason: str = '') -> None:
        """
        Archive the tournament.
        
        Args:
            user: User performing the archive
            reason: Reason for archiving
        """
        if self.is_archived:
            raise ValidationError("Tournament is already archived")
        
        self.archive_type = 'ARCHIVED'
        self.is_archived = True
        self.archived_at = timezone.now()
        self.archived_by = user
        self.archive_reason = reason
        self.save()
    
    def restore(self, user=None) -> None:
        """
        Restore the tournament from archive.
        
        Args:
            user: User performing the restore
        """
        if not self.is_archived:
            raise ValidationError("Tournament is not archived")
        
        if not self.can_restore:
            raise ValidationError("Tournament cannot be restored")
        
        self.archive_type = 'ACTIVE'
        self.is_archived = False
        self.restored_at = timezone.now()
        self.restored_by = user
        self.save()
    
    def mark_as_clone(
        self,
        source: 'Tournament',
        user=None,
        clone_num: int = 1
    ) -> None:
        """
        Mark the tournament as a clone.
        
        Args:
            source: Source tournament
            user: User performing the clone
            clone_num: Clone generation number
        """
        if self.source_tournament:
            raise ValidationError("Tournament is already marked as a clone")
        
        self.archive_type = 'CLONED'
        self.source_tournament = source
        self.clone_number = clone_num
        self.cloned_at = timezone.now()
        self.cloned_by = user
        self.save()
    
    def save_snapshot(self, data: Dict[str, Any]) -> None:
        """
        Save a snapshot of tournament data.
        
        Args:
            data: Dictionary of tournament data to preserve
        """
        self.original_data = data
        self.save()
    
    # ==================== Query Methods ====================
    
    @classmethod
    def get_archived_tournaments(cls):
        """Get all archived tournaments."""
        return cls.objects.filter(is_archived=True)
    
    @classmethod
    def get_active_tournaments(cls):
        """Get all active (non-archived) tournaments."""
        return cls.objects.filter(archive_type='ACTIVE', is_archived=False)
    
    @classmethod
    def get_cloned_tournaments(cls):
        """Get all cloned tournaments."""
        return cls.objects.filter(archive_type='CLONED')
    
    @classmethod
    def get_original_tournaments(cls):
        """Get all original (non-cloned) tournaments."""
        return cls.objects.filter(source_tournament__isnull=True, clone_number=0)
