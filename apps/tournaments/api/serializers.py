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
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (API Standards)
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.tournaments.models.registration import Registration
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
