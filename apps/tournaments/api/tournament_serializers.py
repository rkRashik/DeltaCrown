"""
Tournament API - Serializers for Tournament CRUD

DRF serializers for tournament creation, update, and management.

Module: 2.1 - Tournament Creation & Management (Backend Only)
Source Documents:
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md (Tournament Service)
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (Tournament Models)
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md (API Standards)

Architecture Decisions:
- ADR-001: Service Layer Pattern - Validation in serializers, business logic in services
- ADR-002: API Design Patterns - RESTful, consistent error responses
- ADR-008: Security - IDs-only discipline, no PII exposure
"""

from decimal import Decimal
from typing import Dict, Any
from rest_framework import serializers
from django.contrib.postgres.fields import ArrayField
from apps.tournaments.models.tournament import Tournament, Game
from apps.tournaments.services.tournament_service import TournamentService


class GameSerializer(serializers.ModelSerializer):
    """Minimal game serializer for tournament relations."""
    
    class Meta:
        model = Game
        fields = ['id', 'name', 'slug', 'icon', 'default_team_size', 'is_active']
        read_only_fields = ['id', 'name', 'slug', 'icon', 'default_team_size', 'is_active']


class TournamentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for tournament list views.
    
    Returns minimal fields for list endpoints with pagination.
    Frontend can fetch full details via detail endpoint.
    """
    
    game_name = serializers.CharField(source='game.name', read_only=True)
    organizer_username = serializers.CharField(source='organizer.username', read_only=True)
    participant_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Tournament
        fields = [
            'id',
            'slug',
            'name',
            'game_name',
            'organizer_username',
            'status',
            'format',
            'participation_type',
            'max_participants',
            'participant_count',
            'registration_start',
            'registration_end',
            'tournament_start',
            'prize_pool',
            'prize_currency',
            'has_entry_fee',
            'entry_fee_amount',
            'thumbnail_image',
            'created_at',
        ]
    
    def get_participant_count(self, obj):
        """Count registered participants (cached via annotation if available)."""
        if hasattr(obj, 'participant_count'):
            return obj.participant_count
        return obj.registrations.filter(status='confirmed').count()


class TournamentDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for tournament detail views.
    
    Returns all fields needed for tournament detail page.
    Includes game details, organizer info, media URLs.
    """
    
    game = GameSerializer(read_only=True)
    organizer_id = serializers.IntegerField(source='organizer.id', read_only=True)
    organizer_username = serializers.CharField(source='organizer.username', read_only=True)
    participant_count = serializers.SerializerMethodField()
    can_register = serializers.SerializerMethodField()
    
    class Meta:
        model = Tournament
        fields = [
            # Basic info
            'id',
            'slug',
            'name',
            'description',
            'status',
            'is_official',
            
            # Game
            'game',
            
            # Organizer
            'organizer_id',
            'organizer_username',
            
            # Format
            'format',
            'participation_type',
            'max_participants',
            'min_participants',
            'participant_count',
            
            # Dates
            'registration_start',
            'registration_end',
            'tournament_start',
            'tournament_end',
            'published_at',
            'created_at',
            'updated_at',
            
            # Prize
            'prize_pool',
            'prize_currency',
            'prize_deltacoin',
            'prize_distribution',
            
            # Entry fee
            'has_entry_fee',
            'entry_fee_amount',
            'entry_fee_currency',
            'entry_fee_deltacoin',
            'payment_methods',
            
            # Fee waiver
            'enable_fee_waiver',
            'fee_waiver_top_n_teams',
            
            # Media
            'banner_image',
            'thumbnail_image',
            'rules_pdf',
            'promo_video_url',
            'stream_youtube_url',
            'stream_twitch_url',
            
            # Features
            'enable_check_in',
            'check_in_minutes_before',
            'enable_dynamic_seeding',
            'enable_live_updates',
            'enable_certificates',
            'enable_challenges',
            'enable_fan_voting',
            
            # Rules
            'rules_text',
            
            # SEO
            'meta_description',
            'meta_keywords',
            
            # Helper fields
            'can_register',
        ]
        read_only_fields = ['id', 'slug', 'status', 'created_at', 'updated_at', 'published_at']
    
    def get_participant_count(self, obj):
        """Count registered participants (cached via annotation if available)."""
        if hasattr(obj, 'participant_count'):
            return obj.participant_count
        return obj.registrations.filter(status='confirmed').count()
    
    def get_can_register(self, obj):
        """Check if tournament is accepting registrations."""
        if obj.status not in ['published', 'registration_open']:
            return False
        
        # Check participant limit
        participant_count = self.get_participant_count(obj)
        if participant_count >= obj.max_participants:
            return False
        
        # Check registration window
        from django.utils import timezone
        now = timezone.now()
        if now < obj.registration_start or now > obj.registration_end:
            return False
        
        return True


class TournamentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating tournaments (DRAFT status).
    
    Delegates to TournamentService.create_tournament() for business logic.
    Validates input but does not create model directly.
    """
    
    # Required fields
    name = serializers.CharField(max_length=200)
    game_id = serializers.IntegerField()
    format = serializers.ChoiceField(choices=Tournament.FORMAT_CHOICES)
    max_participants = serializers.IntegerField(min_value=2, max_value=256)
    registration_start = serializers.DateTimeField()
    registration_end = serializers.DateTimeField()
    tournament_start = serializers.DateTimeField()
    
    # Optional fields
    description = serializers.CharField(required=False, allow_blank=True, default='')
    participation_type = serializers.ChoiceField(
        choices=Tournament.PARTICIPATION_TYPE_CHOICES,
        default=Tournament.TEAM
    )
    min_participants = serializers.IntegerField(min_value=2, required=False, default=2)
    tournament_end = serializers.DateTimeField(required=False, allow_null=True)
    
    # Prize fields
    prize_pool = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=Decimal('0.00'))
    prize_currency = serializers.CharField(max_length=10, required=False, default='BDT')
    prize_deltacoin = serializers.IntegerField(min_value=0, required=False, default=0)
    prize_distribution = serializers.JSONField(required=False, default=dict)
    
    # Entry fee fields
    has_entry_fee = serializers.BooleanField(default=False)
    entry_fee_amount = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        default=Decimal('0.00')
    )
    entry_fee_currency = serializers.CharField(max_length=10, required=False, default='BDT')
    entry_fee_deltacoin = serializers.IntegerField(min_value=0, required=False, default=0)
    payment_methods = serializers.ListField(
        child=serializers.ChoiceField(choices=Tournament.PAYMENT_METHOD_CHOICES),
        required=False,
        default=list
    )
    
    # Fee waiver
    enable_fee_waiver = serializers.BooleanField(default=False)
    fee_waiver_top_n_teams = serializers.IntegerField(min_value=0, required=False, default=0)
    
    # Media fields
    banner_image = serializers.ImageField(required=False, allow_null=True)
    thumbnail_image = serializers.ImageField(required=False, allow_null=True)
    rules_pdf = serializers.FileField(required=False, allow_null=True)
    promo_video_url = serializers.URLField(required=False, allow_blank=True, default='')
    stream_youtube_url = serializers.URLField(required=False, allow_blank=True, default='')
    stream_twitch_url = serializers.URLField(required=False, allow_blank=True, default='')
    
    # Feature flags
    enable_check_in = serializers.BooleanField(default=True)
    check_in_minutes_before = serializers.IntegerField(min_value=5, max_value=120, required=False, default=15)
    enable_dynamic_seeding = serializers.BooleanField(default=False)
    enable_live_updates = serializers.BooleanField(default=True)
    enable_certificates = serializers.BooleanField(default=True)
    enable_challenges = serializers.BooleanField(default=False)
    enable_fan_voting = serializers.BooleanField(default=False)
    
    # Rules
    rules_text = serializers.CharField(required=False, allow_blank=True, default='')
    
    # SEO
    meta_description = serializers.CharField(max_length=300, required=False, allow_blank=True, default='')
    meta_keywords = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False,
        default=list
    )
    
    # Official status (staff only)
    is_official = serializers.BooleanField(default=False)
    
    def validate(self, attrs):
        """
        Cross-field validation.
        
        Validates:
        - Date order (reg_start < reg_end < tournament_start)
        - Participant counts (min <= max)
        - Game exists and is active
        """
        # Validate dates
        reg_start = attrs['registration_start']
        reg_end = attrs['registration_end']
        tour_start = attrs['tournament_start']
        
        if reg_start >= reg_end:
            raise serializers.ValidationError({
                'registration_end': 'Registration end must be after registration start'
            })
        if reg_end >= tour_start:
            raise serializers.ValidationError({
                'tournament_start': 'Tournament start must be after registration end'
            })
        
        # Validate participants
        min_parts = attrs.get('min_participants', 2)
        max_parts = attrs['max_participants']
        if min_parts > max_parts:
            raise serializers.ValidationError({
                'min_participants': 'Minimum participants cannot exceed maximum'
            })
        
        # Validate game exists
        try:
            game = Game.objects.get(id=attrs['game_id'], is_active=True)
        except Game.DoesNotExist:
            raise serializers.ValidationError({
                'game_id': f"Game with ID {attrs['game_id']} not found or is inactive"
            })
        
        return attrs
    
    def create(self, validated_data):
        """
        Create tournament via TournamentService.
        
        Args:
            validated_data: Validated input data
        
        Returns:
            Tournament instance in DRAFT status
        """
        user = self.context['request'].user
        tournament = TournamentService.create_tournament(
            organizer=user,
            data=validated_data
        )
        return tournament


class TournamentUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating tournaments (DRAFT status only).
    
    All fields are optional for partial updates.
    Delegates to TournamentService.update_tournament().
    """
    
    # Basic fields (optional)
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    format = serializers.ChoiceField(choices=Tournament.FORMAT_CHOICES, required=False)
    participation_type = serializers.ChoiceField(choices=Tournament.PARTICIPATION_TYPE_CHOICES, required=False)
    max_participants = serializers.IntegerField(min_value=2, max_value=256, required=False)
    min_participants = serializers.IntegerField(min_value=2, required=False)
    
    # Dates (optional)
    registration_start = serializers.DateTimeField(required=False)
    registration_end = serializers.DateTimeField(required=False)
    tournament_start = serializers.DateTimeField(required=False)
    tournament_end = serializers.DateTimeField(required=False, allow_null=True)
    
    # Prize fields (optional)
    prize_pool = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    prize_currency = serializers.CharField(max_length=10, required=False)
    prize_deltacoin = serializers.IntegerField(min_value=0, required=False)
    prize_distribution = serializers.JSONField(required=False)
    
    # Entry fee fields (optional)
    has_entry_fee = serializers.BooleanField(required=False)
    entry_fee_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    entry_fee_currency = serializers.CharField(max_length=10, required=False)
    entry_fee_deltacoin = serializers.IntegerField(min_value=0, required=False)
    payment_methods = serializers.ListField(
        child=serializers.ChoiceField(choices=Tournament.PAYMENT_METHOD_CHOICES),
        required=False
    )
    
    # Fee waiver (optional)
    enable_fee_waiver = serializers.BooleanField(required=False)
    fee_waiver_top_n_teams = serializers.IntegerField(min_value=0, required=False)
    
    # Media fields (optional)
    banner_image = serializers.ImageField(required=False, allow_null=True)
    thumbnail_image = serializers.ImageField(required=False, allow_null=True)
    rules_pdf = serializers.FileField(required=False, allow_null=True)
    promo_video_url = serializers.URLField(required=False, allow_blank=True)
    stream_youtube_url = serializers.URLField(required=False, allow_blank=True)
    stream_twitch_url = serializers.URLField(required=False, allow_blank=True)
    
    # Feature flags (optional)
    enable_check_in = serializers.BooleanField(required=False)
    check_in_minutes_before = serializers.IntegerField(min_value=5, max_value=120, required=False)
    enable_dynamic_seeding = serializers.BooleanField(required=False)
    enable_live_updates = serializers.BooleanField(required=False)
    enable_certificates = serializers.BooleanField(required=False)
    enable_challenges = serializers.BooleanField(required=False)
    enable_fan_voting = serializers.BooleanField(required=False)
    
    # Rules (optional)
    rules_text = serializers.CharField(required=False, allow_blank=True)
    
    # SEO (optional)
    meta_description = serializers.CharField(max_length=300, required=False, allow_blank=True)
    meta_keywords = serializers.ListField(
        child=serializers.CharField(max_length=50),
        required=False
    )
    
    # Game change (optional, but validated)
    game_id = serializers.IntegerField(required=False)
    
    def validate(self, attrs):
        """
        Cross-field validation for updates.
        
        Only validates fields that are present in the update.
        """
        # Validate game if provided
        if 'game_id' in attrs:
            try:
                Game.objects.get(id=attrs['game_id'], is_active=True)
            except Game.DoesNotExist:
                raise serializers.ValidationError({
                    'game_id': f"Game with ID {attrs['game_id']} not found or is inactive"
                })
        
        # Note: Date and participant validation will be done in the service layer
        # where we have access to the existing tournament object
        
        return attrs
    
    def update(self, instance, validated_data):
        """
        Update tournament via TournamentService.
        
        Args:
            instance: Tournament instance to update
            validated_data: Validated partial update data
        
        Returns:
            Updated Tournament instance
        """
        user = self.context['request'].user
        tournament = TournamentService.update_tournament(
            tournament_id=instance.id,
            user=user,
            data=validated_data
        )
        return tournament


class TournamentPublishSerializer(serializers.Serializer):
    """
    Serializer for publishing tournaments (DRAFT → PUBLISHED/REGISTRATION_OPEN).
    
    No input fields required, just triggers the publish action.
    """
    
    def save(self, **kwargs):
        """
        Publish tournament via TournamentService.
        
        Returns:
            Published Tournament instance
        """
        tournament = self.instance
        user = self.context['request'].user
        published_tournament = TournamentService.publish_tournament(
            tournament_id=tournament.id,
            user=user
        )
        return published_tournament


class TournamentCancelSerializer(serializers.Serializer):
    """
    Serializer for cancelling tournaments.
    
    Accepts optional reason field for audit trail.
    """
    
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    
    def save(self, **kwargs):
        """
        Cancel tournament via TournamentService.
        
        Returns:
            Cancelled Tournament instance
        """
        tournament = self.instance
        user = self.context['request'].user
        reason = self.validated_data.get('reason', '')
        
        cancelled_tournament = TournamentService.cancel_tournament(
            tournament_id=tournament.id,
            user=user,
            reason=reason
        )
        return cancelled_tournament
