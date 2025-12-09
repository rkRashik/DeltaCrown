"""
Epic 7.1: Organizer Results Inbox API Serializers

DRF serializers for organizer results inbox API endpoints.

Serializers:
1. OrganizerReviewItemAPISerializer - Serializes OrganizerReviewItemDTO for API responses
2. BulkActionRequestSerializer - Validates bulk action requests (finalize/reject)

Planning References:
- ROADMAP_AND_EPICS_PART_4.md Epic 7.1 (Results Inbox & Queue Management)
- FRONTEND_DEVELOPER_SUPPORT_PART_5.md (Organizer Console specs)
- CLEANUP_AND_TESTING_PART_6.md §9.7 (Results inbox acceptance criteria)

Architecture:
- Serializes DTOs from tournament_ops package (no ORM imports)
- Uses TournamentOpsService façade (no direct service access)
- IDs-only discipline (tournament_id, match_id, submission_id)
"""

from rest_framework import serializers
from typing import List, Optional


class OrganizerReviewItemAPISerializer(serializers.Serializer):
    """
    Serializer for OrganizerReviewItemDTO.
    
    Maps DTO fields to JSON response format for organizer results inbox.
    Used by GET /api/v1/organizer/results-inbox/ endpoint.
    
    Fields:
    - submission_id: MatchResultSubmission ID
    - match_id: Match ID
    - tournament_id: Tournament ID
    - tournament_name: Tournament name (optional, for multi-tournament view)
    - status: Submission status (pending/confirmed/finalized/rejected/disputed)
    - dispute_status: Dispute status if any (open/under_review/escalated/resolved_*/dismissed)
    - created_at: Submission creation timestamp
    - auto_confirm_deadline: Auto-confirmation deadline (optional)
    - is_overdue: Whether auto-confirm deadline has passed
    - priority: Computed priority score for sorting
    - age_in_hours: Submission age in hours
    
    Source: apps/tournament_ops/dtos/review.py (OrganizerReviewItemDTO)
    """
    
    submission_id = serializers.IntegerField(
        help_text="Match result submission ID"
    )
    
    match_id = serializers.IntegerField(
        help_text="Match ID"
    )
    
    tournament_id = serializers.IntegerField(
        help_text="Tournament ID"
    )
    
    tournament_name = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="Tournament name (for multi-tournament views)"
    )
    
    status = serializers.CharField(
        help_text="Submission status (pending/confirmed/finalized/rejected/disputed)"
    )
    
    dispute_status = serializers.CharField(
        allow_null=True,
        required=False,
        help_text="Dispute status if any (open/under_review/escalated/resolved_*/dismissed)"
    )
    
    created_at = serializers.DateTimeField(
        help_text="Submission creation timestamp"
    )
    
    auto_confirm_deadline = serializers.DateTimeField(
        allow_null=True,
        required=False,
        help_text="Auto-confirmation deadline"
    )
    
    is_overdue = serializers.BooleanField(
        help_text="Whether auto-confirm deadline has passed"
    )
    
    priority = serializers.IntegerField(
        help_text="Computed priority score for sorting"
    )
    
    age_in_hours = serializers.FloatField(
        help_text="Submission age in hours"
    )
    
    @classmethod
    def from_dto(cls, dto):
        """
        Convert OrganizerReviewItemDTO to serializer data.
        
        Args:
            dto: OrganizerReviewItemDTO instance
            
        Returns:
            Serialized data dict
        """
        return cls({
            'submission_id': dto.submission_id,
            'match_id': dto.match_id,
            'tournament_id': dto.tournament_id,
            'tournament_name': dto.tournament_name,
            'status': dto.status,
            'dispute_status': dto.dispute_status,
            'created_at': dto.created_at,
            'auto_confirm_deadline': dto.auto_confirm_deadline,
            'is_overdue': dto.is_overdue,
            'priority': dto.priority,
            'age_in_hours': dto.age_in_hours(),
        }).data


class BulkActionRequestSerializer(serializers.Serializer):
    """
    Serializer for bulk action requests.
    
    Used by POST /api/v1/organizer/results-inbox/bulk-action/ endpoint.
    
    Fields:
    - action: Action to perform ('finalize' or 'reject')
    - submission_ids: List of submission IDs to process
    - notes: Optional notes (required for reject action)
    
    Validation:
    - action must be 'finalize' or 'reject'
    - submission_ids must be non-empty list
    - notes required for reject action
    """
    
    action = serializers.ChoiceField(
        choices=['finalize', 'reject'],
        help_text="Action to perform (finalize or reject)"
    )
    
    submission_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        help_text="List of submission IDs to process"
    )
    
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="Optional notes (required for reject action)"
    )
    
    def validate(self, attrs):
        """
        Cross-field validation.
        
        Validates:
        - notes required for reject action
        """
        action = attrs.get('action')
        notes = attrs.get('notes')
        
        if action == 'reject' and not notes:
            raise serializers.ValidationError({
                'notes': ['Notes are required for reject action.']
            })
        
        return attrs


class BulkActionResponseSerializer(serializers.Serializer):
    """
    Serializer for bulk action responses.
    
    Used to serialize bulk action results.
    
    Fields:
    - processed: Number of successfully processed submissions
    - failed: List of failed submissions with errors
    - items: List of processed submission items (OrganizerReviewItemDTO)
    """
    
    processed = serializers.IntegerField(
        help_text="Number of successfully processed submissions"
    )
    
    failed = serializers.ListField(
        child=serializers.DictField(),
        help_text="List of failed submissions with error messages"
    )
    
    items = OrganizerReviewItemAPISerializer(
        many=True,
        help_text="List of processed submission items"
    )
