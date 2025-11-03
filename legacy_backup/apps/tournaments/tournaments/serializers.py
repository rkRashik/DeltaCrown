"""
REST API Serializers for Tournament Models

This module provides comprehensive serializers for all tournament-related models
including the 6 new Phase 1 models.
"""

from rest_framework import serializers
from .models import (
    Tournament,
    TournamentSchedule,
    TournamentCapacity,
    TournamentFinance,
    TournamentMedia,
    TournamentRules,
    TournamentArchive
)


# ============================================================================
# CORE MODEL SERIALIZERS
# ============================================================================

class TournamentScheduleSerializer(serializers.ModelSerializer):
    """Serializer for TournamentSchedule model"""
    
    # Computed fields
    is_registration_open = serializers.BooleanField(read_only=True)
    is_checkin_open = serializers.BooleanField(read_only=True)
    is_in_progress = serializers.BooleanField(read_only=True)
    has_ended = serializers.BooleanField(read_only=True)
    registration_status = serializers.SerializerMethodField()
    
    class Meta:
        model = TournamentSchedule
        fields = [
            'id',
            'tournament',
            # Registration dates
            'registration_start',
            'registration_end',
            'early_bird_deadline',
            # Check-in dates
            'checkin_start',
            'checkin_end',
            # Tournament dates
            'tournament_start',
            'tournament_end',
            # Settings
            'timezone',
            'auto_close_registration',
            'auto_start_checkin',
            # Computed fields
            'is_registration_open',
            'is_checkin_open',
            'is_in_progress',
            'has_ended',
            'registration_status',
        ]
        read_only_fields = [
            'is_registration_open',
            'is_checkin_open',
            'is_in_progress',
            'has_ended',
            'registration_status',
        ]
    
    def get_registration_status(self, obj):
        """Get human-readable registration status"""
        if obj.is_registration_open():
            return "open"
        elif obj.is_registration_upcoming():
            return "upcoming"
        else:
            return "closed"


class TournamentCapacitySerializer(serializers.ModelSerializer):
    """Serializer for TournamentCapacity model"""
    
    # Computed fields
    fill_percentage = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    waitlist_available_slots = serializers.SerializerMethodField()
    
    class Meta:
        model = TournamentCapacity
        fields = [
            'id',
            'tournament',
            # Team capacity
            'min_teams',
            'max_teams',
            'current_teams',
            # Player limits
            'min_players_per_team',
            'max_players_per_team',
            # Waitlist
            'enable_waitlist',
            'waitlist_capacity',
            'current_waitlist',
            # Status
            'capacity_status',
            'is_full',
            'waitlist_full',
            # Computed fields
            'fill_percentage',
            'available_slots',
            'waitlist_available_slots',
        ]
        read_only_fields = [
            'current_teams',
            'current_waitlist',
            'capacity_status',
            'is_full',
            'waitlist_full',
            'fill_percentage',
            'available_slots',
            'waitlist_available_slots',
        ]
    
    def get_fill_percentage(self, obj):
        """Get capacity fill percentage"""
        return obj.get_fill_percentage()
    
    def get_available_slots(self, obj):
        """Get available team slots"""
        return obj.get_available_slots()
    
    def get_waitlist_available_slots(self, obj):
        """Get available waitlist slots"""
        return obj.get_waitlist_available_slots()


class TournamentFinanceSerializer(serializers.ModelSerializer):
    """Serializer for TournamentFinance model"""
    
    # Formatted display fields
    formatted_entry_fee = serializers.SerializerMethodField()
    formatted_prize_pool = serializers.SerializerMethodField()
    formatted_total_revenue = serializers.SerializerMethodField()
    formatted_total_paid_out = serializers.SerializerMethodField()
    
    # Computed fields
    profit = serializers.SerializerMethodField()
    estimated_revenue = serializers.SerializerMethodField()
    revenue_per_team = serializers.SerializerMethodField()
    
    class Meta:
        model = TournamentFinance
        fields = [
            'id',
            'tournament',
            # Entry fees
            'entry_fee',
            'currency',
            'early_bird_fee',
            'late_registration_fee',
            # Prize pool
            'prize_pool',
            'prize_currency',
            'prize_distribution',
            # Revenue tracking
            'total_revenue',
            'total_paid_out',
            # Formatted fields
            'formatted_entry_fee',
            'formatted_prize_pool',
            'formatted_total_revenue',
            'formatted_total_paid_out',
            # Computed fields
            'profit',
            'estimated_revenue',
            'revenue_per_team',
        ]
        read_only_fields = [
            'total_revenue',
            'total_paid_out',
            'formatted_entry_fee',
            'formatted_prize_pool',
            'formatted_total_revenue',
            'formatted_total_paid_out',
            'profit',
            'estimated_revenue',
            'revenue_per_team',
        ]
    
    def get_formatted_entry_fee(self, obj):
        """Get formatted entry fee"""
        return obj.get_formatted_entry_fee()
    
    def get_formatted_prize_pool(self, obj):
        """Get formatted prize pool"""
        return obj.get_formatted_prize_pool()
    
    def get_formatted_total_revenue(self, obj):
        """Get formatted total revenue"""
        return obj.get_formatted_total_revenue()
    
    def get_formatted_total_paid_out(self, obj):
        """Get formatted total paid out"""
        return obj.get_formatted_total_paid_out()
    
    def get_profit(self, obj):
        """Calculate profit/loss"""
        return obj.calculate_profit()
    
    def get_estimated_revenue(self, obj):
        """Calculate estimated revenue"""
        return obj.calculate_estimated_revenue()
    
    def get_revenue_per_team(self, obj):
        """Calculate revenue per team"""
        return obj.calculate_revenue_per_team()


class TournamentMediaSerializer(serializers.ModelSerializer):
    """Serializer for TournamentMedia model"""
    
    # URL fields for media files
    logo_url = serializers.SerializerMethodField()
    banner_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TournamentMedia
        fields = [
            'id',
            'tournament',
            # Logo
            'logo',
            'logo_alt_text',
            'show_logo_on_card',
            'show_logo_on_detail',
            # Banner
            'banner',
            'banner_alt_text',
            'show_banner_on_card',
            'show_banner_on_detail',
            # Thumbnail
            'thumbnail',
            'thumbnail_alt_text',
            # Streaming
            'stream_url',
            'stream_embed_code',
            # URL fields
            'logo_url',
            'banner_url',
            'thumbnail_url',
        ]
        read_only_fields = [
            'logo_url',
            'banner_url',
            'thumbnail_url',
        ]
    
    def get_logo_url(self, obj):
        """Get absolute URL for logo"""
        if obj.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.logo.url)
            return obj.logo.url
        return None
    
    def get_banner_url(self, obj):
        """Get absolute URL for banner"""
        if obj.banner:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.banner.url)
            return obj.banner.url
        return None
    
    def get_thumbnail_url(self, obj):
        """Get absolute URL for thumbnail"""
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        return None


class TournamentRulesSerializer(serializers.ModelSerializer):
    """Serializer for TournamentRules model"""
    
    # Computed fields
    has_age_restriction = serializers.SerializerMethodField()
    has_region_restriction = serializers.SerializerMethodField()
    has_rank_restriction = serializers.SerializerMethodField()
    requirements_list = serializers.SerializerMethodField()
    
    class Meta:
        model = TournamentRules
        fields = [
            'id',
            'tournament',
            # Rule sections
            'general_rules',
            'eligibility_requirements',
            'match_rules',
            'scoring_system',
            'penalty_rules',
            'prize_distribution_rules',
            'additional_notes',
            'checkin_instructions',
            # Requirements
            'require_discord',
            'require_game_id',
            'require_team_logo',
            # Restrictions
            'min_age',
            'max_age',
            'region_restriction',
            'rank_restriction',
            # Computed fields
            'has_age_restriction',
            'has_region_restriction',
            'has_rank_restriction',
            'requirements_list',
        ]
        read_only_fields = [
            'has_age_restriction',
            'has_region_restriction',
            'has_rank_restriction',
            'requirements_list',
        ]
    
    def get_has_age_restriction(self, obj):
        """Check if age restriction exists"""
        return obj.has_age_restriction()
    
    def get_has_region_restriction(self, obj):
        """Check if region restriction exists"""
        return obj.has_region_restriction()
    
    def get_has_rank_restriction(self, obj):
        """Check if rank restriction exists"""
        return obj.has_rank_restriction()
    
    def get_requirements_list(self, obj):
        """Get list of requirements"""
        requirements = []
        if obj.require_discord:
            requirements.append('discord')
        if obj.require_game_id:
            requirements.append('game_id')
        if obj.require_team_logo:
            requirements.append('team_logo')
        return requirements


class TournamentArchiveSerializer(serializers.ModelSerializer):
    """Serializer for TournamentArchive model"""
    
    # Related tournament info
    source_tournament_name = serializers.CharField(
        source='source_tournament.name',
        read_only=True,
        allow_null=True
    )
    
    # Computed fields
    is_clone = serializers.SerializerMethodField()
    is_restored = serializers.SerializerMethodField()
    preservation_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = TournamentArchive
        fields = [
            'id',
            'tournament',
            # Archive status
            'archive_type',
            'is_archived',
            'archived_at',
            'archived_by',
            'archive_reason',
            # Clone fields
            'source_tournament',
            'source_tournament_name',
            'clone_number',
            'cloned_at',
            'cloned_by',
            # Restore fields
            'can_restore',
            'restored_at',
            'restored_by',
            # Preservation settings
            'preserve_participants',
            'preserve_matches',
            'preserve_media',
            'original_data',
            'notes',
            # Computed fields
            'is_clone',
            'is_restored',
            'preservation_summary',
        ]
        read_only_fields = [
            'archived_at',
            'cloned_at',
            'restored_at',
            'source_tournament_name',
            'is_clone',
            'is_restored',
            'preservation_summary',
        ]
    
    def get_is_clone(self, obj):
        """Check if this is a clone"""
        return obj.is_clone()
    
    def get_is_restored(self, obj):
        """Check if this has been restored"""
        return obj.is_restored()
    
    def get_preservation_summary(self, obj):
        """Get summary of what's being preserved"""
        preserved = []
        if obj.preserve_participants:
            preserved.append('participants')
        if obj.preserve_matches:
            preserved.append('matches')
        if obj.preserve_media:
            preserved.append('media')
        return preserved


# ============================================================================
# NESTED SERIALIZERS
# ============================================================================

class TournamentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for Tournament with all related models"""
    
    schedule = TournamentScheduleSerializer(read_only=True)
    capacity = TournamentCapacitySerializer(read_only=True)
    finance = TournamentFinanceSerializer(read_only=True)
    media = TournamentMediaSerializer(read_only=True)
    rules = TournamentRulesSerializer(read_only=True)
    archive = TournamentArchiveSerializer(read_only=True)
    
    # Game info
    game_name = serializers.CharField(source='game.name', read_only=True)
    game_slug = serializers.CharField(source='game.slug', read_only=True)
    
    # Organizer info
    organizer_username = serializers.CharField(source='organizer.username', read_only=True)
    
    class Meta:
        model = Tournament
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'game',
            'game_name',
            'game_slug',
            'organizer',
            'organizer_username',
            'tournament_type',
            'status',
            'format',
            'platform',
            'created_at',
            'updated_at',
            # Related models
            'schedule',
            'capacity',
            'finance',
            'media',
            'rules',
            'archive',
        ]
        read_only_fields = [
            'slug',
            'created_at',
            'updated_at',
            'game_name',
            'game_slug',
            'organizer_username',
        ]


class TournamentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for Tournament list views"""
    
    # Basic related info
    game_name = serializers.CharField(source='game.name', read_only=True)
    organizer_username = serializers.CharField(source='organizer.username', read_only=True)
    
    # Key status fields
    registration_status = serializers.SerializerMethodField()
    capacity_status = serializers.CharField(source='capacity.capacity_status', read_only=True)
    current_teams = serializers.IntegerField(source='capacity.current_teams', read_only=True)
    max_teams = serializers.IntegerField(source='capacity.max_teams', read_only=True)
    entry_fee = serializers.DecimalField(
        source='finance.entry_fee',
        max_digits=10,
        decimal_places=2,
        read_only=True
    )
    prize_pool = serializers.DecimalField(
        source='finance.prize_pool',
        max_digits=12,
        decimal_places=2,
        read_only=True
    )
    
    # Media URLs
    logo_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Tournament
        fields = [
            'id',
            'name',
            'slug',
            'game',
            'game_name',
            'organizer_username',
            'tournament_type',
            'status',
            'format',
            'platform',
            'created_at',
            # Status fields
            'registration_status',
            'capacity_status',
            'current_teams',
            'max_teams',
            'entry_fee',
            'prize_pool',
            # Media
            'logo_url',
            'thumbnail_url',
        ]
    
    def get_registration_status(self, obj):
        """Get registration status"""
        if hasattr(obj, 'schedule'):
            if obj.schedule.is_registration_open():
                return "open"
            elif obj.schedule.is_registration_upcoming():
                return "upcoming"
            else:
                return "closed"
        return None
    
    def get_logo_url(self, obj):
        """Get logo URL"""
        if hasattr(obj, 'media') and obj.media.logo:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.media.logo.url)
            return obj.media.logo.url
        return None
    
    def get_thumbnail_url(self, obj):
        """Get thumbnail URL"""
        if hasattr(obj, 'media') and obj.media.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.media.thumbnail.url)
            return obj.media.thumbnail.url
        return None
