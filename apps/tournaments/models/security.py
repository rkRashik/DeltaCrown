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
    
    Fields:
        user: User who performed the action
        action: Type of action performed (from AuditAction enum)
        timestamp: When the action occurred
        metadata: JSON field with action-specific data
        ip_address: IP address of user (if available)
        user_agent: User agent string (if available)
        
    Indexes:
        - timestamp (for time-based queries)
        - action (for filtering by action type)
        - user (for user activity tracking)
        - composite: (action, timestamp) for filtered queries
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
    
    class Meta:
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['action', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        username = self.user.username if self.user else 'SYSTEM'
        return f"{username} - {self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def __repr__(self):
        return f"<AuditLog(user={self.user_id}, action={self.action}, timestamp={self.timestamp})>"
