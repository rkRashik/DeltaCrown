"""
Prize Payout & Refund API Serializers

Serializers for payout/refund request/response validation.

Related Planning:
- Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md#module-52
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md#section-6

Module: apps.tournaments.api.payout_serializers
Implements: phase_5:module_5_2:milestone_3
"""

from rest_framework import serializers


class PayoutRequestSerializer(serializers.Serializer):
    """
    Request serializer for payout processing.
    
    Fields:
        dry_run: Boolean flag for validation-only mode
        notes: Optional processing notes for audit trail
    """
    dry_run = serializers.BooleanField(default=False, required=False)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)


class RefundRequestSerializer(serializers.Serializer):
    """
    Request serializer for refund processing.
    
    Fields:
        dry_run: Boolean flag for validation-only mode
        notes: Optional processing notes for audit trail
    """
    dry_run = serializers.BooleanField(default=False, required=False)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)


class PayoutResponseSerializer(serializers.Serializer):
    """
    Response serializer for successful payout processing.
    
    Fields:
        tournament_id: Tournament ID
        created_transaction_ids: List of created DeltaCrownTransaction IDs
        count: Number of transactions created
        mode: Processing mode ("payout")
        idempotent: Flag indicating idempotency handling
    """
    tournament_id = serializers.IntegerField()
    created_transaction_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of created DeltaCrownTransaction IDs"
    )
    count = serializers.IntegerField(help_text="Number of transactions created")
    mode = serializers.CharField(default="payout")
    idempotent = serializers.BooleanField(default=True)


class RefundResponseSerializer(serializers.Serializer):
    """
    Response serializer for successful refund processing.
    
    Fields:
        tournament_id: Tournament ID
        created_transaction_ids: List of created DeltaCrownTransaction IDs
        count: Number of transactions created
        mode: Processing mode ("refund")
        idempotent: Flag indicating idempotency handling
    """
    tournament_id = serializers.IntegerField()
    created_transaction_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="List of created DeltaCrownTransaction IDs"
    )
    count = serializers.IntegerField(help_text="Number of transactions created")
    mode = serializers.CharField(default="refund")
    idempotent = serializers.BooleanField(default=True)


class ReconciliationResponseSerializer(serializers.Serializer):
    """
    Response serializer for reconciliation verification.
    
    Fields:
        tournament_id: Tournament ID
        ok: Boolean indicating if reconciliation passed
        details: Nested reconciliation report with expected/actual/missing/duplicates
    """
    tournament_id = serializers.IntegerField()
    ok = serializers.BooleanField(help_text="True if reconciliation passed")
    details = serializers.DictField(
        help_text="Detailed reconciliation report with expected, actual, missing, amount_mismatches, duplicates, failed_transactions"
    )
