"""
Team DTOs.

Data Transfer Objects for team-related data.
"""

from dataclasses import dataclass
from typing import List, Optional

from .base import DTOBase


@dataclass
class TeamDTO(DTOBase):
    """
    DTO for team data.

    Represents a team without coupling to the Django Team ORM model.
    Used by TeamAdapter to return team information to TournamentOps orchestration layer.

    Attributes:
        id: Team primary key.
        name: Team display name.
        captain_id: User ID of the team captain.
        captain_name: Display name of the captain.
        member_ids: List of user IDs for all team members.
        member_names: List of display names for all team members.
        game: Game slug (e.g., "valorant", "csgo") that this team is registered for.
        is_verified: Whether the team has been verified/approved.
        logo_url: Optional URL to the team's logo image.
    """

    id: int
    name: str
    captain_id: int
    captain_name: str
    member_ids: List[int]
    member_names: List[str]
    game: str  # game slug, not model
    is_verified: bool
    logo_url: Optional[str]

    @classmethod
    def from_model(cls, model: any) -> "TeamDTO":
        """
        Create TeamDTO from a team model.

        Handles:
        - organizations.Team ORM instances (primary path — queries memberships)
        - Plain dicts (test/serialization path)
        - Simple attribute objects (test fakes with direct fields)

        Args:
            model: Team model instance or dict.

        Returns:
            TeamDTO instance.
        """
        # Dict passthrough
        if isinstance(model, dict):
            return cls(
                id=model.get("id", 0),
                name=model.get("name", ""),
                captain_id=model.get("captain_id", 0),
                captain_name=model.get("captain_name", ""),
                member_ids=model.get("member_ids", []),
                member_names=model.get("member_names", []),
                game=model.get("game", ""),
                is_verified=model.get("is_verified", False),
                logo_url=model.get("logo_url"),
            )

        # Resolve game slug — Team.game property returns slug string,
        # test fakes may have game=FakeGameModel(slug="...")
        game_slug = ""
        game_value = getattr(model, "game", None)
        if game_value is not None:
            if isinstance(game_value, str):
                game_slug = game_value
            elif hasattr(game_value, "slug"):
                game_slug = game_value.slug
            else:
                game_slug = str(game_value)

        # Check if this is a real ORM Team (has vnext_memberships manager)
        has_memberships_manager = hasattr(model, 'vnext_memberships')

        if has_memberships_manager:
            # ── ORM path: organizations.Team ──
            # Captain: OWNER membership → created_by fallback
            captain_id = 0
            captain_name = ""
            try:
                owner = model.vnext_memberships.filter(
                    role='OWNER', status='ACTIVE'
                ).select_related('user').first()
                if owner:
                    captain_id = owner.user_id
                    profile = getattr(owner.user, 'profile', None)
                    captain_name = (
                        getattr(profile, 'display_name', '') if profile
                        else owner.user.username
                    )
            except Exception:
                pass
            if not captain_id and getattr(model, 'created_by_id', None):
                captain_id = model.created_by_id
                captain_name = (
                    getattr(model.created_by, 'username', '')
                    if model.created_by else ''
                )

            # Members: all active memberships
            member_ids: List[int] = []
            member_names: List[str] = []
            try:
                memberships = model.vnext_memberships.filter(
                    status='ACTIVE'
                ).select_related('user')
                for m in memberships:
                    member_ids.append(m.user_id)
                    profile = getattr(m.user, 'profile', None)
                    name = (
                        getattr(profile, 'display_name', m.user.username)
                        if profile else m.user.username
                    )
                    member_names.append(name)
            except Exception:
                pass

            # Is verified: team status == ACTIVE
            is_verified = getattr(model, 'status', '') == 'ACTIVE'

            # Logo URL
            logo_url = None
            if hasattr(model, 'get_effective_logo_url'):
                logo_url = model.get_effective_logo_url()
            elif hasattr(model, 'logo') and model.logo:
                try:
                    logo_url = model.logo.url
                except Exception:
                    pass
        else:
            # ── Simple attribute path: test fakes / plain objects ──
            captain_id = getattr(model, "captain_id", 0)
            captain_name = getattr(model, "captain_name", "")
            member_ids = getattr(model, "member_ids", [])
            member_names = getattr(model, "member_names", [])
            is_verified = getattr(model, "is_verified", False)
            logo_url = getattr(model, "logo_url", None)

        return cls(
            id=getattr(model, "id", 0),
            name=getattr(model, "name", ""),
            captain_id=captain_id,
            captain_name=captain_name,
            member_ids=member_ids,
            member_names=member_names,
            game=game_slug,
            is_verified=is_verified,
            logo_url=logo_url,
        )

    def validate(self) -> List[str]:
        """
        Validate team data.

        Ensures:
        - name is not empty
        - captain_id is present in member_ids
        - member_ids and member_names have same length
        - game is not empty

        Returns:
            List of validation error messages (empty if valid).
        """
        errors = []

        if not self.name:
            errors.append("name cannot be empty")

        if not self.game:
            errors.append("game cannot be empty")

        if self.captain_id not in self.member_ids:
            errors.append("captain_id must be in member_ids")

        if len(self.member_ids) != len(self.member_names):
            errors.append("member_ids and member_names must have same length")

        return errors
