"""
Certificate API Serializers - Module 5.3

Serializers for certificate API endpoints.

Related Planning:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-53
- Documents/Planning/PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md#sprint-6

Module: apps.tournaments.api.certificate_serializers
Implements: phase_5:module_5_3:milestone_3

PII Policy:
- No emails or usernames exposed
- Only display names (participant names)
- Registration IDs OK (not PII)
"""

from rest_framework import serializers
from apps.tournaments.models import Certificate


class CertificateSerializer(serializers.ModelSerializer):
    """
    Serializer for Certificate model (basic info, no PII).
    
    Used for list/detail views (if needed in future).
    
    Fields exposed:
    - id, tournament_id, tournament_name
    - certificate_type, placement
    - verification_code
    - generated_at, download_count
    - revoked status
    
    PII Protection: No emails, no usernames, no participant user_id
    """
    
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    certificate_type_display = serializers.CharField(source='get_certificate_type_display', read_only=True)
    is_revoked = serializers.BooleanField(read_only=True)
    is_downloaded = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Certificate
        fields = [
            'id',
            'tournament_id',  # FK ID is OK (not PII)
            'tournament_name',
            'certificate_type',
            'certificate_type_display',
            'placement',
            'verification_code',
            'generated_at',
            'downloaded_at',
            'download_count',
            'revoked_at',
            'revoked_reason',
            'is_revoked',
            'is_downloaded',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields  # All fields read-only (no POST/PUT)


class VerificationSerializer(serializers.Serializer):
    """
    Serializer for certificate verification response.
    
    Used by verify_certificate endpoint.
    
    PII Protection:
    - participant_name: Display name only (no email/username)
    - No user IDs exposed
    - No file URLs exposed
    
    Fields:
    - valid: Overall validity (false if revoked or tampered)
    - certificate_id: Certificate ID
    - tournament: Tournament name
    - participant_display_name: Participant display name (no PII)
    - certificate_type: Display name of certificate type
    - placement: Placement string (e.g., "1", "2", "3")
    - generated_at: Generation timestamp
    - revoked: Revocation status
    - revoked_reason: Reason for revocation (if applicable)
    - is_tampered: Tampering detection flag
    - verification_url: Public URL to this verification endpoint
    """
    
    valid = serializers.BooleanField(
        help_text="Overall validity (false if revoked or tampered)"
    )
    certificate_id = serializers.IntegerField()
    tournament = serializers.CharField(
        source='tournament_name',
        help_text="Tournament name"
    )
    participant_display_name = serializers.CharField(
        source='participant_name',
        help_text="Participant display name (no PII)"
    )
    certificate_type = serializers.CharField(
        help_text="Certificate type display name"
    )
    placement = serializers.CharField(
        allow_blank=True,
        help_text="Placement string (e.g., '1', '2', '3')"
    )
    generated_at = serializers.DateTimeField(
        help_text="Certificate generation timestamp"
    )
    revoked = serializers.BooleanField(
        help_text="Revocation status"
    )
    revoked_reason = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        required=False,
        help_text="Reason for revocation (if applicable)"
    )
    is_tampered = serializers.BooleanField(
        help_text="Tampering detection flag (hash mismatch)"
    )
    
    # Optional: Add verification_url if service provides it
    # For now, we construct it in the view if needed
