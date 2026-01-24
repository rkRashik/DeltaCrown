"""
Migration bridge model for legacy-to-vNext mapping.

TeamMigrationMap connects legacy apps/teams.Team IDs to vNext
apps/organizations.Team IDs during Phase 5-7 parallel operation.
"""

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class TeamMigrationMap(models.Model):
    """
    Bridge table mapping legacy Team IDs to vNext Team IDs.
    
    Purpose:
    - Enable service layer routing during Phase 5-7 dual-read period
    - Preserve URL redirects (legacy /teams/{slug}/ → vNext URL)
    - Provide audit trail for migration debugging
    - Support rollback scenarios
    
    Lifecycle:
    - Created in Phase 5 (data migration)
    - Used in Phase 5-7 (dual-system operation)
    - Retained indefinitely (minimum 12 months post-Phase 8)
    
    Critical Rules:
    - This is the ONLY foreign key relationship between vNext and legacy
    - Do NOT create direct FKs between other vNext/legacy models
    - Do NOT delete rows (breaks old notification links)
    
    Database Table: organizations_migration_map
    """
    
    # Legacy team reference (IntegerField to avoid FK dependency)
    legacy_team_id = models.IntegerField(
        unique=True,
        db_index=True,
        help_text="Original teams_team.id from legacy system"
    )
    
    # vNext team reference (IntegerField to maintain independence)
    vnext_team_id = models.IntegerField(
        unique=True,
        db_index=True,
        help_text="New organizations_team.id from vNext system"
    )
    
    # Legacy slug for URL redirects
    legacy_slug = models.SlugField(
        max_length=100,
        db_index=True,
        help_text="Legacy team slug (for URL redirect middleware)"
    )
    
    # Migration metadata
    migration_date = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when migration occurred"
    )
    migrated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Admin user who executed migration script"
    )
    
    # Data integrity verification
    verified = models.BooleanField(
        default=False,
        help_text="Data verification passed (roster, rankings, tournament history)"
    )
    verification_notes = models.TextField(
        blank=True,
        help_text="Any discrepancies found during verification"
    )
    
    class Meta:
        db_table = 'organizations_migration_map'
        ordering = ['-migration_date']
        indexes = [
            models.Index(fields=['legacy_team_id'], name='migration_legacy_idx'),
            models.Index(fields=['vnext_team_id'], name='migration_vnext_idx'),
            models.Index(fields=['legacy_slug'], name='migration_slug_idx'),
        ]
        verbose_name = 'Team Migration Map'
        verbose_name_plural = 'Team Migration Maps'
    
    def __str__(self):
        """Return human-readable migration mapping."""
        verified_badge = '✓' if self.verified else '⚠'
        return f"{verified_badge} Legacy ID {self.legacy_team_id} → vNext ID {self.vnext_team_id}"
    
    @classmethod
    def get_vnext_id(cls, legacy_id):
        """
        Return vNext ID for legacy team (or None if not migrated).
        
        Used by service layer to route reads to correct system.
        
        Args:
            legacy_id (int): Legacy teams_team.id
            
        Returns:
            int | None: vNext team ID, or None if not migrated yet
        """
        mapping = cls.objects.filter(legacy_team_id=legacy_id).first()
        return mapping.vnext_team_id if mapping else None
    
    @classmethod
    def get_legacy_id(cls, vnext_id):
        """
        Return legacy ID for vNext team (or None if new team).
        
        Used for reverse lookups when old integrations query by vNext ID.
        
        Args:
            vnext_id (int): vNext organizations_team.id
            
        Returns:
            int | None: Legacy team ID, or None if vNext-native team
        """
        mapping = cls.objects.filter(vnext_team_id=vnext_id).first()
        return mapping.legacy_team_id if mapping else None
    
    @classmethod
    def resolve_legacy_url(cls, legacy_slug):
        """
        Resolve legacy team slug to vNext team ID for URL redirects.
        
        Used by URL redirect middleware in Phase 6+.
        
        Args:
            legacy_slug (str): Legacy team slug from old URL
            
        Returns:
            int | None: vNext team ID for redirect, or None if not found
        """
        mapping = cls.objects.filter(legacy_slug=legacy_slug).first()
        return mapping.vnext_team_id if mapping else None
