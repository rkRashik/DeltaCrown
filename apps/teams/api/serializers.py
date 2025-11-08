# apps/teams/api/serializers.py
"""
Team Management API Serializers (Module 3.3)

Serializers for team CRUD, invitations, and roster management.
Follows DRF conventions and Module 3.2 patterns.

Planning Reference: Documents/ExecutionPlan/MODULE_3.3_IMPLEMENTATION_PLAN.md

Traceability:
- Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md#api-design
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.teams.models._legacy import Team, TeamMembership, TeamInvite
from apps.user_profile.models import UserProfile

User = get_user_model()


# ════════════════════════════════════════════════════════════════════
# User/Profile Nested Serializers
# ════════════════════════════════════════════════════════════════════

class UserProfileNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for user profile info in team responses."""
    username = serializers.CharField(source="user.username", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ["id", "username", "email", "avatar"]
        read_only_fields = fields


# ════════════════════════════════════════════════════════════════════
# Team Serializers
# ════════════════════════════════════════════════════════════════════

class TeamListSerializer(serializers.ModelSerializer):
    """Serializer for team list view (minimal fields)."""
    captain_username = serializers.CharField(source="captain.user.username", read_only=True)
    members_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = [
            "id", "name", "tag", "slug", "game", "logo",
            "captain_username", "members_count", "is_active", "created_at"
        ]
        read_only_fields = fields
    
    def get_members_count(self, obj):
        """Get count of active members."""
        return TeamMembership.objects.filter(team=obj, status="active").count()


class TeamMembershipNestedSerializer(serializers.ModelSerializer):
    """Nested serializer for team members in detail view."""
    username = serializers.CharField(source="profile.user.username", read_only=True)
    avatar = serializers.ImageField(source="profile.avatar", read_only=True)
    
    class Meta:
        model = TeamMembership
        fields = ["id", "username", "avatar", "role", "joined_at"]
        read_only_fields = fields


class TeamDetailSerializer(serializers.ModelSerializer):
    """Serializer for team detail view (full fields)."""
    captain = UserProfileNestedSerializer(read_only=True)
    members = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = [
            "id", "name", "tag", "slug", "game", "description",
            "logo", "banner_image", "roster_image", "region",
            "captain", "members",
            "twitter", "instagram", "discord", "youtube", "twitch", "linktree",
            "is_active", "is_verified", "is_featured",
            "followers_count", "posts_count",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "slug", "captain", "members", "created_at", "updated_at"]
    
    def get_members(self, obj):
        """Get list of active team members."""
        memberships = TeamMembership.objects.filter(
            team=obj,
            status="active"
        ).select_related("profile__user").order_by("-joined_at")
        return TeamMembershipNestedSerializer(memberships, many=True).data


class TeamCreateSerializer(serializers.ModelSerializer):
    """Serializer for team creation."""
    
    class Meta:
        model = Team
        fields = [
            "name", "tag", "game", "description",
            "logo", "region"
        ]
    
    def validate_name(self, value):
        """Validate team name uniqueness."""
        if Team.objects.filter(name=value).exists():
            raise serializers.ValidationError(f"Team with name '{value}' already exists")
        return value
    
    def validate_tag(self, value):
        """Validate team tag uniqueness."""
        if value and Team.objects.filter(tag=value).exists():
            raise serializers.ValidationError(f"Team with tag '{value}' already exists")
        return value


class TeamUpdateSerializer(serializers.ModelSerializer):
    """Serializer for team updates (captain only)."""
    
    class Meta:
        model = Team
        fields = [
            "description", "logo", "banner_image", "roster_image", "region",
            "twitter", "instagram", "discord", "youtube", "twitch", "linktree"
        ]
    
    def validate(self, attrs):
        """Prevent update of restricted fields."""
        # This serializer already restricts fields via Meta.fields
        # Additional validation can go here if needed
        return attrs


# ════════════════════════════════════════════════════════════════════
# Invitation Serializers
# ════════════════════════════════════════════════════════════════════

class TeamInviteSerializer(serializers.ModelSerializer):
    """Serializer for team invitations."""
    team_name = serializers.CharField(source="team.name", read_only=True)
    invited_username = serializers.CharField(source="invited_user.user.username", read_only=True, allow_null=True)
    inviter_username = serializers.CharField(source="inviter.user.username", read_only=True, allow_null=True)
    
    class Meta:
        model = TeamInvite
        fields = [
            "id", "team", "team_name",
            "invited_user", "invited_username",
            "inviter", "inviter_username",
            "role", "status",
            "created_at", "expires_at"
        ]
        read_only_fields = [
            "id", "team_name", "invited_username", "inviter_username",
            "status", "created_at", "expires_at"
        ]


class InvitePlayerSerializer(serializers.Serializer):
    """Serializer for POST /api/teams/{id}/invite/."""
    invited_user_id = serializers.IntegerField(required=True)
    role = serializers.ChoiceField(
        choices=["player", "substitute"],
        default="player",
        required=False
    )
    
    def validate_invited_user_id(self, value):
        """Validate invited user exists (profile will be created if needed)."""
        try:
            User.objects.get(id=value)
            # Note: UserProfile will be created automatically if needed via get_or_create in views
        except User.DoesNotExist:
            raise serializers.ValidationError(f"User with ID {value} does not exist")
        return value


class RespondInviteSerializer(serializers.Serializer):
    """Serializer for POST /api/teams/invites/{id}/respond/."""
    action = serializers.ChoiceField(
        choices=["accept", "decline"],
        required=True
    )


# ════════════════════════════════════════════════════════════════════
# Captain Transfer Serializer
# ════════════════════════════════════════════════════════════════════

class TransferCaptainSerializer(serializers.Serializer):
    """Serializer for POST /api/teams/{id}/transfer-captain/."""
    new_captain_id = serializers.IntegerField(required=True)
    
    def validate_new_captain_id(self, value):
        """Validate new captain user exists."""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(f"User with ID {value} does not exist")
        return value
