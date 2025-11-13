# apps/tournaments/api/serializers_payments.py
from rest_framework import serializers
from ..models import PaymentVerification


class PaymentVerificationSerializer(serializers.ModelSerializer):
    """Read-only serializer for payment verification responses (no PII)."""
    
    registration_id = serializers.IntegerField(source='registration.id', read_only=True)
    
    class Meta:
        model = PaymentVerification
        fields = [
            'id',
            'registration_id',
            'status',
            'method',
            'transaction_id',
            'payer_account_number',
            'amount_bdt',
            'verified_at',
            'rejected_at',
            'refunded_at',
            'notes',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields


class PaymentSubmitProofSerializer(serializers.ModelSerializer):
    """Serializer for registrants submitting payment proof."""
    
    proof_file = serializers.ImageField(source='proof_image', required=False, allow_null=True)
    
    class Meta:
        model = PaymentVerification
        fields = [
            'transaction_id',
            'payer_account_number',
            'amount_bdt',
            'proof_file',
            'notes',
        ]
    
    def validate_amount_bdt(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value
    
    def validate_transaction_id(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Transaction ID is required")
        return value.strip()
    
    def validate_payer_account_number(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Payer account number is required")
        return value.strip()


class PaymentModerateSerializer(serializers.Serializer):
    """Serializer for staff verify/reject actions."""
    
    amount_bdt = serializers.IntegerField(required=False, allow_null=True)
    reason_code = serializers.CharField(required=False, allow_blank=True, max_length=50)
    notes = serializers.JSONField(required=False, allow_null=True)
    
    def validate_amount_bdt(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Amount must be positive")
        return value


class PaymentRefundSerializer(serializers.Serializer):
    """Serializer for staff refund action."""
    
    amount_bdt = serializers.IntegerField(required=True)
    reason_code = serializers.CharField(required=True, max_length=50)
    notes = serializers.JSONField(required=False, allow_null=True)
    
    def validate_amount_bdt(self, value):
        if value <= 0:
            raise serializers.ValidationError("Refund amount must be positive")
        return value
    
    def validate_reason_code(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Reason code is required for refunds")
        return value.strip()
