"""
Security models for tournaments.

Module 2.4: Security Hardening
Provides audit logging and security tracking.
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib import admin

User = get_user_model()


class AuditLog(models.Model):
    """
    Audit log model for tracking sensitive operations.
    
    Phase 7, Epic 7.5: Enhanced audit trail with before/after state capture,
    tournament/match context, and organizer console integration.
    
    Fields:
        user: User who performed the action
        action: Type of action performed (from AuditAction enum)
        timestamp: When the action occurred
        metadata: JSON field with action-specific data
        ip_address: IP address of user (if available)
        user_agent: User agent string (if available)
        tournament_id: Tournament context (if applicable) - Epic 7.5
        match_id: Match context (if applicable) - Epic 7.5
        before_state: State before action (for change tracking) - Epic 7.5
        after_state: State after action (for change tracking) - Epic 7.5
        correlation_id: Request correlation ID for tracing - Epic 7.5
        
    Indexes:
        - timestamp (for time-based queries)
        - action (for filtering by action type)
        - user (for user activity tracking)
        - tournament_id (for per-tournament audit trails)
        - match_id (for per-match audit trails)
        - composite: (action, timestamp) for filtered queries
        - composite: (tournament_id, timestamp) for tournament audit queries
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text="User who performed the action (null if system action)"
    )
    
    action = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Action type (e.g., payment_verify, bracket_regenerate)"
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the action occurred"
    )
    
    metadata = models.JSONField(
        default=dict,
        help_text="Action-specific data (tournament_id, payment_id, etc.)"
    )
    
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of user"
    )
    
    user_agent = models.TextField(
        null=True,
        blank=True,
        help_text="User agent string from request"
    )
    
    # Epic 7.5: Enhanced context fields
    tournament_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Tournament ID for tournament-scoped actions (Epic 7.5)"
    )
    
    match_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Match ID for match-scoped actions (Epic 7.5)"
    )
    
    before_state = models.JSONField(
        null=True,
        blank=True,
        help_text="State before action (for change tracking, Epic 7.5)"
    )
    
    after_state = models.JSONField(
        null=True,
        blank=True,
        help_text="State after action (for change tracking, Epic 7.5)"
    )
    
    correlation_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Request correlation ID for distributed tracing (Epic 7.5)"
    )
    
    class Meta:
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['tournament_id', 'timestamp']),  # Epic 7.5
            models.Index(fields=['match_id', 'timestamp']),  # Epic 7.5
            models.Index(fields=['correlation_id']),  # Epic 7.5
        ]
    
    def __str__(self):
        username = self.user.username if self.user else 'SYSTEM'
        context = f"T:{self.tournament_id}" if self.tournament_id else ""
        context += f" M:{self.match_id}" if self.match_id else ""
        return f"{username} - {self.action} {context}- {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def __repr__(self):
        return f"<AuditLog(user={self.user_id}, action={self.action}, tournament={self.tournament_id}, timestamp={self.timestamp})>"
