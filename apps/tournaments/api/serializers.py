# Implements: Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md#api-serializers
# Implements: Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md#registration-validation
# Implements: Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md#registration-model

"""
Tournament API - Serializers

DRF serializers for tournament registration endpoints.

Source Documents:
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (API Structure)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (Registration Validation)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Registration Model)
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md (API Standards)
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.services.registration_service import RegistrationService


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for Registration model.
    
    Handles:
    - Registration creation with eligibility validation
    - Auto-fill from UserProfile
    - Custom registration data (JSONB)
    
    Source: PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md Section 3
    """
    
    # Read-only fields
    id = serializers.IntegerField(read_only=True)
    tournament_name = serializers.CharField(source='tournament.name', read_only=True)
    tournament_slug = serializers.CharField(source='tournament.slug', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    registered_at = serializers.DateTimeField(read_only=True)
    
    # Write-only fields for creation
    tournament_id = serializers.IntegerField(write_only=True, required=False)
    tournament_slug_input = serializers.SlugField(write_only=True, required=False)
    
    class Meta:
        model = Registration
        fields = [
            # Read-only
            'id',
            'tournament_name',
            'tournament_slug',
            'status',
            'status_display',
            'registered_at',
            'slot_number',
            'seed',
            'checked_in',
            'check_in_time',
            
            # Read-write
            'registration_data',
            'team_id',
            
            # Write-only
            'tournament_id',
            'tournament_slug_input',
        ]
        read_only_fields = [
            'id',
            'tournament_name',
            'tournament_slug',
            'status',
            'status_display',
            'registered_at',
            'slot_number',
            'seed',
            'checked_in',
            'check_in_time',
        ]
    
    def validate(self, attrs):
        """
        Validate registration data.
        
        Validation Rules (PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.1):
        1. Tournament must exist (via slug or ID)
        2. Eligibility checks via RegistrationService
        3. Registration data schema validation
        
        Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.1
        """
        # Get tournament (either by ID or slug)
        tournament = None
        if 'tournament_id' in attrs:
            try:
                tournament = Tournament.objects.get(id=attrs['tournament_id'])
            except Tournament.DoesNotExist:
                raise serializers.ValidationError({
                    'tournament_id': f"Tournament with ID {attrs['tournament_id']} not found"
                })
        elif 'tournament_slug_input' in attrs:
            try:
                tournament = Tournament.objects.get(slug=attrs['tournament_slug_input'])
            except Tournament.DoesNotExist:
                raise serializers.ValidationError({
                    'tournament_slug': f"Tournament with slug '{attrs['tournament_slug_input']}' not found"
                })
        else:
            raise serializers.ValidationError({
                'tournament': "Either tournament_id or tournament_slug is required"
            })
        
        # Store tournament for create()
        attrs['tournament'] = tournament
        
        # Get user from context
        user = self.context['request'].user
        
        # Check eligibility via service layer
        team_id = attrs.get('team_id')
        is_eligible, error_message = RegistrationService.check_registration_eligibility(
            tournament=tournament,
            user=user,
            team_id=team_id
        )
        
        if not is_eligible:
            raise serializers.ValidationError({
                'non_field_errors': [error_message]
            })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create registration using RegistrationService.
        
        Delegates all business logic to service layer per ADR-002.
        
        Source: PART_2.2_SERVICES_INTEGRATION.md Section 6.1
        """
        # Remove write-only fields
        validated_data.pop('tournament_id', None)
        validated_data.pop('tournament_slug_input', None)
        
        # Extract tournament (set in validate())
        tournament = validated_data.pop('tournament')
        
        # Get user from context
        user = self.context['request'].user
        
        # Call service layer
        try:
            registration = RegistrationService.register_participant(
                tournament=tournament,
                user=user,
                team_id=validated_data.get('team_id'),
                registration_data=validated_data.get('registration_data', {})
            )
            return registration
        except DjangoValidationError as e:
            raise serializers.ValidationError(str(e))


class RegistrationDetailSerializer(RegistrationSerializer):
    """
    Detailed serializer for Registration with expanded fields.
    
    Used for retrieve/list endpoints where more context is needed.
    
    Source: PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md Section 3
    """
    
    # Expanded tournament info
    tournament = serializers.SerializerMethodField()
    
    # Payment info (if exists)
    payment_status = serializers.SerializerMethodField()
    
    class Meta(RegistrationSerializer.Meta):
        fields = RegistrationSerializer.Meta.fields + [
            'tournament',
            'payment_status',
        ]
    
    def get_tournament(self, obj):
        """Return minimal tournament info"""
        return {
            'id': obj.tournament.id,
            'name': obj.tournament.name,
            'slug': obj.tournament.slug,
            'game': obj.tournament.game.name if obj.tournament.game else None,
            'start_date': obj.tournament.start_date,
            'entry_fee': str(obj.tournament.entry_fee) if obj.tournament.entry_fee else '0.00',
            'status': obj.tournament.status,
            'status_display': obj.tournament.get_status_display(),
        }
    
    def get_payment_status(self, obj):
        """Return payment status if payment exists"""
        if hasattr(obj, 'payment'):
            return {
                'exists': True,
                'status': obj.payment.status,
                'status_display': obj.payment.get_status_display(),
                'amount': str(obj.payment.amount) if obj.payment.amount else '0.00',
                'payment_method': obj.payment.payment_method,
                'submitted_at': obj.payment.submitted_at,
            }
        return {
            'exists': False
        }


class RegistrationCancelSerializer(serializers.Serializer):
    """
    Serializer for registration cancellation requests.
    
    Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.2
    """
    
    reason = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional reason for cancellation"
    )
    
    def validate(self, attrs):
        """Validate cancellation request"""
        # Registration instance available via context
        registration = self.context.get('registration')
        
        if not registration:
            raise serializers.ValidationError("Registration not found in context")
        
        # Check if already cancelled
        if registration.status in [Registration.CANCELLED, Registration.NO_SHOW]:
            raise serializers.ValidationError(
                f"Registration is already {registration.get_status_display()}"
            )
        
        # Check if tournament has started
        if registration.tournament.status in [Tournament.LIVE, Tournament.COMPLETED]:
            raise serializers.ValidationError(
                "Cannot cancel registration after tournament has started"
            )
        
        return attrs


# ============================================================================
# Payment API Serializers (Module 3.2: Payment Processing)
# ============================================================================


class PaymentProofSubmitSerializer(serializers.Serializer):
    """
    Serializer for payment proof file upload (multipart/form-data).
    
    Handles:
    - File upload validation (size, type)
    - Reference number validation
    - Manual payment methods (bKash, Nagad, Rocket, Bank Transfer)
    
    Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.2
    """
    
    payment_proof = serializers.FileField(
        required=True,
        help_text="Payment proof file (JPG/PNG/PDF, max 5MB)",
        allow_empty_file=False
    )
    
    reference_number = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text="Payment reference number from receipt (e.g., TxnID from bKash)"
    )
    
    notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Additional notes about the payment"
    )
    
    def validate_payment_proof(self, value):
        """
        Validate uploaded file.
        
        Validation Rules (PART_4.4_REGISTRATION_PAYMENT_FLOW.md):
        - Maximum size: 5MB
        - Allowed types: JPG, PNG, PDF
        
        Note: File content validation happens in Payment model's clean() method.
        """
        # Check file size (5MB = 5 * 1024 * 1024 bytes)
        max_size = 5 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(
                f"File size ({value.size / 1024 / 1024:.1f}MB) exceeds maximum allowed size (5MB)"
            )
        
        # Check file extension
        allowed_extensions = ['jpg', 'jpeg', 'png', 'pdf']
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type '.{file_extension}' not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value
    
    def validate(self, attrs):
        """Cross-field validation"""
        # Registration instance passed via context
        registration = self.context.get('registration')
        
        if not registration:
            raise serializers.ValidationError("Registration not found in context")
        
        # Check if payment exists
        if not hasattr(registration, 'payment'):
            raise serializers.ValidationError({
                'non_field_errors': [
                    "No payment record found for this registration. "
                    "Payment must be created before submitting proof."
                ]
            })
        
        payment = registration.payment
        
        # Check payment method - only manual methods require proof
        manual_methods = ['bkash', 'nagad', 'rocket', 'bank_transfer']
        if payment.payment_method not in manual_methods:
            raise serializers.ValidationError({
                'payment_method': [
                    f"Payment method '{payment.payment_method}' does not require proof upload. "
                    f"Proof upload only required for: {', '.join(manual_methods)}"
                ]
            })
        
        # Check payment status - can only submit for pending/submitted/rejected
        allowed_statuses = [Payment.PENDING, Payment.SUBMITTED, Payment.REJECTED]
        if payment.status not in allowed_statuses:
            raise serializers.ValidationError({
                'status': [
                    f"Cannot submit proof for payment with status '{payment.get_status_display()}'. "
                    f"Proof can only be submitted for: Pending, Submitted, or Rejected payments."
                ]
            })
        
        return attrs


class PaymentStatusSerializer(serializers.ModelSerializer):
    """
    Serializer for payment status retrieval.
    
    Returns payment details including proof file URL, status, and verification info.
    
    Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.2
    """
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    proof_file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'registration',
            'payment_method',
            'payment_method_display',
            'amount',
            'transaction_id',
            'reference_number',
            'file_type',
            'status',
            'status_display',
            'proof_file_url',
            'admin_notes',
            'submitted_at',
            'verified_at',
            'verified_by',
        ]
        read_only_fields = fields
    
    def get_proof_file_url(self, obj):
        """Return payment proof file URL if available"""
        return obj.proof_file_url


class PaymentVerifySerializer(serializers.Serializer):
    """
    Serializer for payment verification by organizer/admin.
    
    Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.2
    """
    
    admin_notes = serializers.CharField(
        max_length=500,
        required=False,
        allow_blank=True,
        help_text="Optional notes about the verification"
    )
    
    def validate(self, attrs):
        """Validate verification request"""
        payment = self.context.get('payment')
        
        if not payment:
            raise serializers.ValidationError("Payment not found in context")
        
        # Check payment status - can only verify submitted payments
        if payment.status != Payment.SUBMITTED:
            raise serializers.ValidationError({
                'status': [
                    f"Cannot verify payment with status '{payment.get_status_display()}'. "
                    "Only submitted payments can be verified."
                ]
            })
        
        return attrs


class PaymentRejectSerializer(serializers.Serializer):
    """
    Serializer for payment rejection by organizer/admin.
    
    Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.2
    """
    
    admin_notes = serializers.CharField(
        max_length=500,
        required=True,
        help_text="Reason for rejection (required)"
    )
    
    def validate(self, attrs):
        """Validate rejection request"""
        payment = self.context.get('payment')
        
        if not payment:
            raise serializers.ValidationError("Payment not found in context")
        
        # Check payment status - can only reject submitted payments
        if payment.status != Payment.SUBMITTED:
            raise serializers.ValidationError({
                'status': [
                    f"Cannot reject payment with status '{payment.get_status_display()}'. "
                    "Only submitted payments can be rejected."
                ]
            })
        
        return attrs


class PaymentRefundSerializer(serializers.Serializer):
    """
    Serializer for payment refund processing by organizer/admin.
    
    Source: PART_4.4_REGISTRATION_PAYMENT_FLOW.md Section 6.2
    """
    
    admin_notes = serializers.CharField(
        max_length=500,
        required=True,
        help_text="Reason for refund (required)"
    )
    
    refund_method = serializers.ChoiceField(
        choices=[
            ('same', 'Same payment method'),
            ('deltacoin', 'DeltaCoin credit'),
            ('manual', 'Manual refund'),
        ],
        required=True,
        help_text="Method for processing refund"
    )
    
    def validate(self, attrs):
        """Validate refund request"""
        payment = self.context.get('payment')
        
        if not payment:
            raise serializers.ValidationError("Payment not found in context")
        
        # Check payment status - can only refund verified payments
        if payment.status != Payment.VERIFIED:
            raise serializers.ValidationError({
                'status': [
                    f"Cannot refund payment with status '{payment.get_status_display()}'. "
                    "Only verified payments can be refunded."
                ]
            })
        
        return attrs


# =============================================================================
# MODULE 4.1: BRACKET SERIALIZERS
# =============================================================================
# Implements: Documents/ExecutionPlan/PHASE_4_IMPLEMENTATION_PLAN.md#module-41


class BracketGenerationSerializer(serializers.Serializer):
    """
    Serializer for bracket generation request.
    
    Validates bracket generation parameters for POST /api/brackets/tournaments/{id}/generate/
    
    Module: 4.1 - Bracket Generation API
    Source: PHASE_4_IMPLEMENTATION_PLAN.md Module 4.1 Technical Requirements
    """
    
    bracket_format = serializers.ChoiceField(
        choices=[
            ('single-elimination', 'Single Elimination'),
            ('double-elimination', 'Double Elimination'),
            ('round-robin', 'Round Robin'),
        ],
        required=False,
        help_text="Bracket format (defaults to tournament.format)"
    )
    
    seeding_method = serializers.ChoiceField(
        choices=[
            ('slot-order', 'Slot Order (Registration order)'),
            ('random', 'Random'),
            ('manual', 'Manual (requires seed values)'),
            ('ranked', 'Ranked (from team rankings)'),
        ],
        default='slot-order',
        required=False,
        help_text="Seeding strategy for participant placement"
    )
    
    participant_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="Optional: Manual participant selection (registration IDs)"
    )
    
    def validate_bracket_format(self, value):
        """Validate bracket format."""
        # Double elimination deferred to future module
        if value == 'double-elimination':
            raise serializers.ValidationError(
                "Double elimination is not yet implemented. Use 'single-elimination' or 'round-robin'."
            )
        return value
    
    def validate_participant_ids(self, value):
        """Validate participant IDs list."""
        if value and len(value) < 2:
            raise serializers.ValidationError(
                "At least 2 participants required for bracket generation."
            )
        return value


class BracketNodeSerializer(serializers.Serializer):
    """
    Serializer for BracketNode (nested in BracketDetailSerializer).
    
    Read-only representation of bracket node.
    """
    
    id = serializers.IntegerField()
    position = serializers.IntegerField()
    round_number = serializers.IntegerField()
    match_number_in_round = serializers.IntegerField()
    participant1_id = serializers.IntegerField(allow_null=True)
    participant1_name = serializers.CharField(allow_null=True)
    participant2_id = serializers.IntegerField(allow_null=True)
    participant2_name = serializers.CharField(allow_null=True)
    winner_id = serializers.IntegerField(allow_null=True)
    is_bye = serializers.BooleanField()
    parent_slot = serializers.IntegerField(allow_null=True)
    match_id = serializers.SerializerMethodField()
    
    def get_match_id(self, obj):
        """Get match ID if match exists."""
        return obj.match.id if hasattr(obj, 'match') and obj.match else None


class BracketSerializer(serializers.Serializer):
    """
    Serializer for Bracket model (list view).
    
    Read-only basic bracket information without nodes.
    """
    
    id = serializers.IntegerField()
    tournament_id = serializers.IntegerField(source='tournament.id')
    tournament_name = serializers.CharField(source='tournament.name')
    format = serializers.CharField()
    format_display = serializers.CharField(source='get_format_display')
    seeding_method = serializers.CharField()
    seeding_method_display = serializers.CharField(source='get_seeding_method_display')
    total_rounds = serializers.IntegerField()
    total_matches = serializers.IntegerField()
    is_finalized = serializers.BooleanField()
    generated_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class BracketDetailSerializer(BracketSerializer):
    """
    Serializer for Bracket model (detail view with nodes).
    
    Includes full bracket structure with all nodes.
    """
    
    bracket_structure = serializers.JSONField()
    nodes = serializers.SerializerMethodField()
    
    def get_nodes(self, obj):
        """Get all bracket nodes."""
        from apps.tournaments.models.bracket import BracketNode
        nodes = BracketNode.objects.filter(bracket=obj).select_related('match').order_by('round_number', 'position')
        return BracketNodeSerializer(nodes, many=True).data
