# apps/teams/serializers.py
"""
Serializers for Teams API endpoints.
Handles team creation, roster management, and game-specific validation.
"""

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction

from apps.teams.models import (
    ValorantTeam, CS2Team, Dota2Team, MLBBTeam, PUBGTeam,
    FreeFireTeam, EFootballTeam, FC26Team, CODMTeam,
    ValorantPlayerMembership, CS2PlayerMembership, Dota2PlayerMembership,
    MLBBPlayerMembership, PUBGPlayerMembership, FreeFirePlayerMembership,
    EFootballPlayerMembership, FC26PlayerMembership, CODMPlayerMembership,
    GAME_TEAM_MODELS, GAME_MEMBERSHIP_MODELS,
    TeamSponsor, TeamDiscussionPost, TeamChatMessage
)
from apps.teams.game_config import get_game_config, get_available_roles
from apps.teams.roster_manager import get_roster_manager
from apps.user_profile.models import UserProfile


# ═══════════════════════════════════════════════════════════════════════════
# Player Membership Serializers
# ═══════════════════════════════════════════════════════════════════════════

class BasePlayerMembershipSerializer(serializers.ModelSerializer):
    """Base serializer for player memberships with common fields."""
    
    profile_id = serializers.IntegerField(write_only=True, required=False)
    profile_username = serializers.CharField(source='profile.user.username', read_only=True)
    profile_avatar = serializers.ImageField(source='profile.avatar', read_only=True)
    profile_full_name = serializers.SerializerMethodField()
    
    class Meta:
        fields = [
            'id', 'profile_id', 'profile', 'profile_username', 
            'profile_avatar', 'profile_full_name',
            'role', 'secondary_role', 'is_starter', 'is_captain',
            'ign', 'jersey_number', 'status', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at', 'profile', 'is_captain']
    
    def get_profile_full_name(self, obj):
        """Get player's full name if available."""
        if obj.profile and obj.profile.user:
            full_name = obj.profile.user.get_full_name()
            return full_name if full_name else obj.profile.user.username
        return None


class ValorantPlayerMembershipSerializer(BasePlayerMembershipSerializer):
    class Meta(BasePlayerMembershipSerializer.Meta):
        model = ValorantPlayerMembership
        fields = BasePlayerMembershipSerializer.Meta.fields + [
            'competitive_rank', 'agent_pool'
        ]


class CS2PlayerMembershipSerializer(BasePlayerMembershipSerializer):
    class Meta(BasePlayerMembershipSerializer.Meta):
        model = CS2PlayerMembership
        fields = BasePlayerMembershipSerializer.Meta.fields + [
            'competitive_rank', 'weapon_pool'
        ]


class Dota2PlayerMembershipSerializer(BasePlayerMembershipSerializer):
    class Meta(BasePlayerMembershipSerializer.Meta):
        model = Dota2PlayerMembership
        fields = BasePlayerMembershipSerializer.Meta.fields + [
            'mmr', 'hero_pool'
        ]


class MLBBPlayerMembershipSerializer(BasePlayerMembershipSerializer):
    class Meta(BasePlayerMembershipSerializer.Meta):
        model = MLBBPlayerMembership
        fields = BasePlayerMembershipSerializer.Meta.fields + [
            'rank', 'hero_pool'
        ]


class PUBGPlayerMembershipSerializer(BasePlayerMembershipSerializer):
    class Meta(BasePlayerMembershipSerializer.Meta):
        model = PUBGPlayerMembership
        fields = BasePlayerMembershipSerializer.Meta.fields


class FreeFirePlayerMembershipSerializer(BasePlayerMembershipSerializer):
    class Meta(BasePlayerMembershipSerializer.Meta):
        model = FreeFirePlayerMembership
        fields = BasePlayerMembershipSerializer.Meta.fields


class EFootballPlayerMembershipSerializer(BasePlayerMembershipSerializer):
    class Meta(BasePlayerMembershipSerializer.Meta):
        model = EFootballPlayerMembership
        fields = BasePlayerMembershipSerializer.Meta.fields


class FC26PlayerMembershipSerializer(BasePlayerMembershipSerializer):
    class Meta(BasePlayerMembershipSerializer.Meta):
        model = FC26PlayerMembership
        fields = BasePlayerMembershipSerializer.Meta.fields


class CODMPlayerMembershipSerializer(BasePlayerMembershipSerializer):
    class Meta(BasePlayerMembershipSerializer.Meta):
        model = CODMPlayerMembership
        fields = BasePlayerMembershipSerializer.Meta.fields


# Membership serializer mapping
MEMBERSHIP_SERIALIZERS = {
    'valorant': ValorantPlayerMembershipSerializer,
    'cs2': CS2PlayerMembershipSerializer,
    'dota2': Dota2PlayerMembershipSerializer,
    'mlbb': MLBBPlayerMembershipSerializer,
    'pubg': PUBGPlayerMembershipSerializer,
    'freefire': FreeFirePlayerMembershipSerializer,
    'efootball': EFootballPlayerMembershipSerializer,
    'fc26': FC26PlayerMembershipSerializer,
    'codm': CODMPlayerMembershipSerializer,
}


# ═══════════════════════════════════════════════════════════════════════════
# Team Serializers
# ═══════════════════════════════════════════════════════════════════════════

class BaseTeamSerializer(serializers.ModelSerializer):
    """Base serializer for team models with common fields."""
    
    captain_id = serializers.IntegerField(write_only=True)
    captain_username = serializers.CharField(source='captain.user.username', read_only=True)
    captain_avatar = serializers.ImageField(source='captain.avatar', read_only=True)
    roster_status = serializers.SerializerMethodField()
    game_code = serializers.CharField(read_only=True)
    
    class Meta:
        fields = [
            'id', 'name', 'tag', 'slug', 'logo', 'banner', 'description',
            'captain', 'captain_id', 'captain_username', 'captain_avatar',
            'region', 'base_city', 'motto', 'founding_year',
            'is_active', 'status', 'game_code',
            'discord_server', 'twitter', 'instagram', 'youtube', 'website',
            'game_specific_data', 'roster_status',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'captain', 'created_at', 'updated_at']
    
    def get_roster_status(self, obj):
        """Get current roster capacity information."""
        try:
            manager = get_roster_manager(obj)
            return manager.get_roster_status()
        except Exception:
            return None
    
    def validate_captain_id(self, value):
        """Validate captain exists."""
        try:
            UserProfile.objects.get(id=value)
            return value
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError("Invalid captain profile ID.")
    
    def create(self, validated_data):
        """Create team with captain assignment."""
        captain_id = validated_data.pop('captain_id')
        validated_data['captain'] = UserProfile.objects.get(id=captain_id)
        
        return super().create(validated_data)


class ValorantTeamSerializer(BaseTeamSerializer):
    roster = ValorantPlayerMembershipSerializer(
        source='get_memberships', many=True, read_only=True
    )
    
    class Meta(BaseTeamSerializer.Meta):
        model = ValorantTeam
        fields = BaseTeamSerializer.Meta.fields + ['average_rank', 'roster']


class CS2TeamSerializer(BaseTeamSerializer):
    roster = CS2PlayerMembershipSerializer(
        source='get_memberships', many=True, read_only=True
    )
    
    class Meta(BaseTeamSerializer.Meta):
        model = CS2Team
        fields = BaseTeamSerializer.Meta.fields + ['average_rank', 'roster']


class Dota2TeamSerializer(BaseTeamSerializer):
    roster = Dota2PlayerMembershipSerializer(
        source='get_memberships', many=True, read_only=True
    )
    
    class Meta(BaseTeamSerializer.Meta):
        model = Dota2Team
        fields = BaseTeamSerializer.Meta.fields + ['roster']


class MLBBTeamSerializer(BaseTeamSerializer):
    roster = MLBBPlayerMembershipSerializer(
        source='get_memberships', many=True, read_only=True
    )
    
    class Meta(BaseTeamSerializer.Meta):
        model = MLBBTeam
        fields = BaseTeamSerializer.Meta.fields + ['roster']


class PUBGTeamSerializer(BaseTeamSerializer):
    roster = PUBGPlayerMembershipSerializer(
        source='get_memberships', many=True, read_only=True
    )
    
    class Meta(BaseTeamSerializer.Meta):
        model = PUBGTeam
        fields = BaseTeamSerializer.Meta.fields + ['roster']


class FreeFireTeamSerializer(BaseTeamSerializer):
    roster = FreeFirePlayerMembershipSerializer(
        source='get_memberships', many=True, read_only=True
    )
    
    class Meta(BaseTeamSerializer.Meta):
        model = FreeFireTeam
        fields = BaseTeamSerializer.Meta.fields + ['roster']


class EFootballTeamSerializer(BaseTeamSerializer):
    roster = EFootballPlayerMembershipSerializer(
        source='get_memberships', many=True, read_only=True
    )
    
    class Meta(BaseTeamSerializer.Meta):
        model = EFootballTeam
        fields = BaseTeamSerializer.Meta.fields + ['roster']


class FC26TeamSerializer(BaseTeamSerializer):
    roster = FC26PlayerMembershipSerializer(
        source='get_memberships', many=True, read_only=True
    )
    
    class Meta(BaseTeamSerializer.Meta):
        model = FC26Team
        fields = BaseTeamSerializer.Meta.fields + ['roster']


class CODMTeamSerializer(BaseTeamSerializer):
    roster = CODMPlayerMembershipSerializer(
        source='get_memberships', many=True, read_only=True
    )
    
    class Meta(BaseTeamSerializer.Meta):
        model = CODMTeam
        fields = BaseTeamSerializer.Meta.fields + ['roster']


# Team serializer mapping
TEAM_SERIALIZERS = {
    'valorant': ValorantTeamSerializer,
    'cs2': CS2TeamSerializer,
    'dota2': Dota2TeamSerializer,
    'mlbb': MLBBTeamSerializer,
    'pubg': PUBGTeamSerializer,
    'freefire': FreeFireTeamSerializer,
    'efootball': EFootballTeamSerializer,
    'fc26': FC26TeamSerializer,
    'codm': CODMTeamSerializer,
}


# ═══════════════════════════════════════════════════════════════════════════
# Team Creation with Roster Serializer
# ═══════════════════════════════════════════════════════════════════════════

class PlayerDataSerializer(serializers.Serializer):
    """Serializer for player data in team creation."""
    profile_id = serializers.IntegerField()
    role = serializers.CharField()
    secondary_role = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_starter = serializers.BooleanField(default=True)
    ign = serializers.CharField()
    jersey_number = serializers.IntegerField(required=False, allow_null=True)
    
    # Game-specific fields (optional)
    competitive_rank = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    agent_pool = serializers.ListField(child=serializers.CharField(), required=False)
    weapon_pool = serializers.ListField(child=serializers.CharField(), required=False)
    mmr = serializers.IntegerField(required=False, allow_null=True)
    hero_pool = serializers.ListField(child=serializers.CharField(), required=False)
    rank = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class TeamCreationSerializer(serializers.Serializer):
    """
    Comprehensive serializer for creating a team with roster in one transaction.
    """
    game_code = serializers.ChoiceField(choices=[
        'valorant', 'cs2', 'dota2', 'mlbb', 'pubg', 
        'freefire', 'efootball', 'fc26', 'codm'
    ])
    
    # Team Info
    name = serializers.CharField(max_length=100)
    tag = serializers.CharField(max_length=20)
    logo = serializers.ImageField(required=False, allow_null=True)
    banner = serializers.ImageField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    region = serializers.CharField(max_length=50)
    base_city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    motto = serializers.CharField(max_length=200, required=False, allow_blank=True)
    founding_year = serializers.IntegerField(required=False, allow_null=True)
    
    # Captain
    captain_id = serializers.IntegerField()
    
    # Social Links
    discord_server = serializers.URLField(required=False, allow_blank=True)
    twitter = serializers.URLField(required=False, allow_blank=True)
    instagram = serializers.URLField(required=False, allow_blank=True)
    youtube = serializers.URLField(required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    
    # Game-specific team fields
    average_rank = serializers.CharField(required=False, allow_blank=True)
    
    # Roster
    roster = PlayerDataSerializer(many=True)
    
    # Optional branding data
    team_philosophy = serializers.CharField(required=False, allow_blank=True)
    sponsors = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    achievements = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    
    def validate_captain_id(self, value):
        """Validate captain exists."""
        try:
            UserProfile.objects.get(id=value)
            return value
        except UserProfile.DoesNotExist:
            raise serializers.ValidationError("Invalid captain profile ID.")
    
    def validate_roster(self, value):
        """Validate roster data."""
        if not value:
            raise serializers.ValidationError("Roster cannot be empty.")
        
        # Check for duplicate IGNs
        igns = [player['ign'] for player in value]
        if len(igns) != len(set(igns)):
            raise serializers.ValidationError("Duplicate IGNs are not allowed.")
        
        # Check for duplicate profiles
        profile_ids = [player['profile_id'] for player in value]
        if len(profile_ids) != len(set(profile_ids)):
            raise serializers.ValidationError("A player cannot be added multiple times.")
        
        return value
    
    def validate(self, data):
        """Cross-field validation."""
        game_code = data['game_code']
        roster = data['roster']
        captain_id = data['captain_id']
        
        # Get game configuration
        game_config = get_game_config(game_code)
        if not game_config:
            raise serializers.ValidationError(
                {"game_code": f"Invalid game code: {game_code}"}
            )
        
        # Count starters and subs
        starters = [p for p in roster if p.get('is_starter', True)]
        subs = [p for p in roster if not p.get('is_starter', True)]
        
        # Validate roster size
        if len(starters) < game_config.min_starters:
            raise serializers.ValidationError(
                {"roster": f"{game_config.display_name} requires at least {game_config.min_starters} starters."}
            )
        
        if len(starters) > game_config.max_starters:
            raise serializers.ValidationError(
                {"roster": f"{game_config.display_name} allows maximum {game_config.max_starters} starters."}
            )
        
        if len(subs) > game_config.max_substitutes:
            raise serializers.ValidationError(
                {"roster": f"{game_config.display_name} allows maximum {game_config.max_substitutes} substitutes."}
            )
        
        # Validate captain is in roster
        roster_profile_ids = [p['profile_id'] for p in roster]
        if captain_id not in roster_profile_ids:
            raise serializers.ValidationError(
                {"captain_id": "Captain must be a member of the roster."}
            )
        
        # Validate roles
        valid_roles = game_config.roles
        for player in roster:
            role = player.get('role')
            if role and role not in valid_roles:
                raise serializers.ValidationError(
                    {"roster": f"Invalid role '{role}' for {game_config.display_name}. "
                               f"Valid roles: {', '.join(valid_roles)}"}
                )
            
            secondary_role = player.get('secondary_role')
            if secondary_role and secondary_role not in valid_roles:
                raise serializers.ValidationError(
                    {"roster": f"Invalid secondary role '{secondary_role}' for {game_config.display_name}."}
                )
        
        # Validate unique positions for Dota2
        if game_code == 'dota2' and game_config.requires_unique_roles:
            starter_roles = [p['role'] for p in starters if p.get('role')]
            if len(starter_roles) != len(set(starter_roles)):
                raise serializers.ValidationError(
                    {"roster": "Dota 2 requires unique positions for all starters."}
                )
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Create team and roster in atomic transaction."""
        game_code = validated_data.pop('game_code')
        roster_data = validated_data.pop('roster')
        captain_id = validated_data.pop('captain_id')
        
        # Extract optional branding data
        team_philosophy = validated_data.pop('team_philosophy', None)
        sponsors = validated_data.pop('sponsors', None)
        achievements = validated_data.pop('achievements', None)
        
        # Build game_specific_data JSON
        game_specific_data = {}
        if team_philosophy:
            game_specific_data['team_philosophy'] = team_philosophy
        if sponsors:
            game_specific_data['sponsors'] = sponsors
        if achievements:
            game_specific_data['achievements'] = achievements
        
        validated_data['game_specific_data'] = game_specific_data
        
        # Get captain profile
        captain_profile = UserProfile.objects.get(id=captain_id)
        validated_data['captain'] = captain_profile
        
        # Get team model
        team_model = GAME_TEAM_MODELS.get(game_code)
        if not team_model:
            raise serializers.ValidationError(f"No model found for game: {game_code}")
        
        # Create team
        team = team_model.objects.create(**validated_data)
        
        # Get roster manager
        manager = get_roster_manager(team)
        
        # Add players
        for player_data in roster_data:
            profile_id = player_data.pop('profile_id')
            profile = UserProfile.objects.get(id=profile_id)
            
            # Extract game-specific fields
            extra_fields = {}
            for field in ['competitive_rank', 'agent_pool', 'weapon_pool', 'mmr', 'hero_pool', 'rank']:
                if field in player_data:
                    extra_fields[field] = player_data.pop(field)
            
            try:
                manager.add_player(
                    profile=profile,
                    **player_data,
                    **extra_fields
                )
            except DjangoValidationError as e:
                # Rollback handled by transaction.atomic
                raise serializers.ValidationError(
                    {"roster": f"Error adding player {player_data.get('ign')}: {str(e)}"}
                )
        
        # Transfer captaincy if captain is not the first added player
        if team.captain != captain_profile:
            manager.transfer_captaincy(captain_profile)
        
        return team


def get_team_serializer_for_game(game_code):
    """Get appropriate team serializer for game."""
    return TEAM_SERIALIZERS.get(game_code)


def get_membership_serializer_for_game(game_code):
    """Get appropriate membership serializer for game."""
    return MEMBERSHIP_SERIALIZERS.get(game_code)


# ═══════════════════════════════════════════════════════════════════════════
# Phase 3 API Serializers (Sponsors, Discussions, Chat)
# ═══════════════════════════════════════════════════════════════════════════

class SponsorSerializer(serializers.ModelSerializer):
    """Serializer for team sponsors"""
    
    class Meta:
        model = TeamSponsor
        fields = [
            'id', 'sponsor_name', 'sponsor_tier', 'sponsor_link',
            'start_date', 'end_date', 'benefits', 'notes'
        ]
        read_only_fields = ['id']
    
    def validate_sponsor_name(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Sponsor name must be at least 2 characters")
        if len(value) > 100:
            raise serializers.ValidationError("Sponsor name too long (max 100)")
        return value
    
    def validate_sponsor_tier(self, value):
        valid_tiers = ['platinum', 'gold', 'silver', 'bronze', 'partner']
        if value not in valid_tiers:
            raise serializers.ValidationError(f"Invalid tier. Must be one of: {', '.join(valid_tiers)}")
        return value
    
    def validate_sponsor_link(self, value):
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Link must start with http:// or https://")
        if len(value) > 500:
            raise serializers.ValidationError("Link too long (max 500)")
        return value
    
    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({'end_date': "End date must be after start date"})
        return data


class DiscussionSerializer(serializers.ModelSerializer):
    """Serializer for discussions"""
    
    class Meta:
        model = TeamDiscussionPost
        fields = ['id', 'title', 'content', 'post_type', 'tags']
        read_only_fields = ['id']
    
    def validate_title(self, value):
        if len(value) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters")
        if len(value) > 200:
            raise serializers.ValidationError("Title too long (max 200)")
        return value.strip()
    
    def validate_content(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Content must be at least 10 characters")
        if len(value) > 10000:
            raise serializers.ValidationError("Content too long (max 10000)")
        return value.strip()
    
    def validate_post_type(self, value):
        valid_types = ['general', 'announcement', 'strategy', 'recruitment', 'question', 'feedback', 'event']
        if value not in valid_types:
            raise serializers.ValidationError(f"Invalid type. Must be one of: {', '.join(valid_types)}")
        return value


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""
    
    class Meta:
        model = TeamChatMessage
        fields = ['id', 'message', 'reply_to']
        read_only_fields = ['id']
    
    def validate_message(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        if len(value) > 2000:
            raise serializers.ValidationError("Message too long (max 2000)")
        return value.strip()
    
    def validate_reply_to(self, value):
        if value and value.is_deleted:
            raise serializers.ValidationError("Cannot reply to deleted message")
        return value


class ChatMessageEditSerializer(serializers.Serializer):
    """Serializer for editing chat messages"""
    content = serializers.CharField(min_length=1, max_length=2000)
    
    def validate_content(self, value):
        return value.strip()


class ReactionSerializer(serializers.Serializer):
    """Serializer for message reactions"""
    emoji = serializers.CharField(max_length=10)
    
    def validate_emoji(self, value):
        if not value:
            raise serializers.ValidationError("Emoji cannot be empty")
        return value
