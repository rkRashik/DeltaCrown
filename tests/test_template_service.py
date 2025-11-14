"""
Tournament Template Service Tests

Tests for TemplateService business logic.

Source: BACKEND_ONLY_BACKLOG.md, Module 2.3
Target: ≥80% coverage, 15+ tests
"""

import pytest
from decimal import Decimal
from django.core.exceptions import ValidationError, PermissionDenied
from apps.tournaments.models import TournamentTemplate, Game
from apps.tournaments.services.template_service import TemplateService


@pytest.mark.django_db
class TestCreateTemplate:
    """Tests for TemplateService.create_template()"""
    
    def test_create_private_template_success(self, user, game_valorant):
        """Test creating a private template (happy path)."""
        template = TemplateService.create_template(
            name="5v5 Valorant Tournament",
            created_by=user,
            game_id=game_valorant.id,
            template_config={
                "format": "single_elimination",
                "max_participants": 16,
                "has_entry_fee": True,
                "entry_fee_amount": "500.00"
            },
            description="Standard 5v5 Valorant tournament",
            visibility=TournamentTemplate.PRIVATE,
        )
        
        assert template.id is not None
        assert template.name == "5v5 Valorant Tournament"
        assert template.created_by == user
        assert template.game == game_valorant
        assert template.visibility == TournamentTemplate.PRIVATE
        assert template.is_active is True
        assert template.usage_count == 0
        assert template.template_config["format"] == "single_elimination"
    
    def test_create_global_template_requires_staff(self, user, game_valorant):
        """Test that non-staff cannot create GLOBAL templates."""
        with pytest.raises(PermissionDenied) as exc_info:
            TemplateService.create_template(
                name="Global Template",
                created_by=user,
                game_id=game_valorant.id,
                visibility=TournamentTemplate.GLOBAL,
            )
        
        assert "Only staff can create GLOBAL templates" in str(exc_info.value)
    
    def test_create_global_template_staff_success(self, staff_user, game_valorant):
        """Test that staff can create GLOBAL templates."""
        template = TemplateService.create_template(
            name="Global Template",
            created_by=staff_user,
            game_id=game_valorant.id,
            visibility=TournamentTemplate.GLOBAL,
        )
        
        assert template.visibility == TournamentTemplate.GLOBAL
        assert template.created_by == staff_user
    
    def test_create_org_template_requires_org_id(self, user, game_valorant):
        """Test that ORG visibility requires organization_id."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateService.create_template(
                name="Org Template",
                created_by=user,
                game_id=game_valorant.id,
                visibility=TournamentTemplate.ORG,
                organization_id=None,
            )
        
        assert "ORG visibility requires organization_id" in str(exc_info.value)
    
    def test_create_org_template_success(self, user, game_valorant):
        """Test creating ORG template with organization_id."""
        template = TemplateService.create_template(
            name="Org Template",
            created_by=user,
            game_id=game_valorant.id,
            visibility=TournamentTemplate.ORG,
            organization_id=123,
        )
        
        assert template.visibility == TournamentTemplate.ORG
        assert template.organization_id == 123
    
    def test_create_template_invalid_game_id(self, user):
        """Test that invalid game_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateService.create_template(
                name="Invalid Game Template",
                created_by=user,
                game_id=99999,  # Non-existent game
            )
        
        assert "does not exist" in str(exc_info.value)
    
    def test_create_template_invalid_format(self, user, game_valorant):
        """Test that invalid tournament format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateService.create_template(
                name="Invalid Format Template",
                created_by=user,
                game_id=game_valorant.id,
                template_config={"format": "invalid_format"},
            )
        
        assert "Invalid format" in str(exc_info.value)
    
    def test_create_template_multi_game(self, user):
        """Test creating multi-game template (no game_id)."""
        template = TemplateService.create_template(
            name="Multi-Game Template",
            created_by=user,
            game_id=None,  # Multi-game
            template_config={"format": "round_robin"},
        )
        
        assert template.game is None
        assert template.name == "Multi-Game Template"


@pytest.mark.django_db
class TestUpdateTemplate:
    """Tests for TemplateService.update_template()"""
    
    def test_update_template_success(self, user, template_private):
        """Test updating template (owner)."""
        updated = TemplateService.update_template(
            template_id=template_private.id,
            user=user,
            name="Updated Template Name",
            description="Updated description",
        )
        
        assert updated.name == "Updated Template Name"
        assert updated.description == "Updated description"
    
    def test_update_template_staff_can_modify(self, staff_user, template_private):
        """Test that staff can modify any template."""
        updated = TemplateService.update_template(
            template_id=template_private.id,
            user=staff_user,
            name="Staff Updated",
        )
        
        assert updated.name == "Staff Updated"
    
    def test_update_template_non_owner_denied(self, other_user, template_private):
        """Test that non-owner cannot modify template."""
        with pytest.raises(PermissionDenied):
            TemplateService.update_template(
                template_id=template_private.id,
                user=other_user,
                name="Hacked",
            )
    
    def test_update_inactive_template_denied(self, user, template_inactive):
        """Test that inactive templates cannot be modified unless activating."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateService.update_template(
                template_id=template_inactive.id,
                user=user,
                name="Try to update inactive",
            )
        
        assert "Cannot modify inactive template" in str(exc_info.value)
    
    def test_update_inactive_template_can_activate(self, user, template_inactive):
        """Test that inactive templates can be activated."""
        updated = TemplateService.update_template(
            template_id=template_inactive.id,
            user=user,
            is_active=True,
        )
        
        assert updated.is_active is True
    
    def test_update_template_config(self, user, template_private):
        """Test updating template_config."""
        new_config = {"format": "double_elimination", "max_participants": 32}
        updated = TemplateService.update_template(
            template_id=template_private.id,
            user=user,
            template_config=new_config,
        )
        
        assert updated.template_config == new_config
    
    def test_update_visibility_to_global_requires_staff(self, user, template_private):
        """Test that only staff can change visibility to GLOBAL."""
        with pytest.raises(PermissionDenied):
            TemplateService.update_template(
                template_id=template_private.id,
                user=user,
                visibility=TournamentTemplate.GLOBAL,
            )


@pytest.mark.django_db
class TestGetTemplate:
    """Tests for TemplateService.get_template()"""
    
    def test_get_template_success(self, user, template_private):
        """Test retrieving template by ID."""
        template = TemplateService.get_template(template_private.id, user)
        
        assert template.id == template_private.id
        assert template.name == template_private.name
    
    def test_get_template_not_found(self, user):
        """Test that non-existent template raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateService.get_template(99999, user)
        
        assert "does not exist" in str(exc_info.value)
    
    def test_get_private_template_owner_allowed(self, user, template_private):
        """Test that owner can view private template."""
        template = TemplateService.get_template(template_private.id, user)
        assert template.id == template_private.id
    
    def test_get_private_template_non_owner_denied(self, other_user, template_private):
        """Test that non-owner cannot view private template."""
        with pytest.raises(PermissionDenied):
            TemplateService.get_template(template_private.id, other_user)
    
    def test_get_global_template_anyone_allowed(self, user, template_global):
        """Test that anyone can view global template."""
        template = TemplateService.get_template(template_global.id, user)
        assert template.visibility == TournamentTemplate.GLOBAL


@pytest.mark.django_db
class TestListTemplates:
    """Tests for TemplateService.list_templates()"""
    
    def test_list_templates_default(self, user, template_private, template_global):
        """Test listing templates (default filters)."""
        templates = TemplateService.list_templates(user=user)
        
        # Should see own private + global templates
        template_ids = [t.id for t in templates]
        assert template_private.id in template_ids
        assert template_global.id in template_ids
    
    def test_list_templates_filter_by_game(self, user, game_valorant, template_private):
        """Test filtering by game_id."""
        templates = TemplateService.list_templates(
            user=user,
            game_id=game_valorant.id
        )
        
        assert all(t.game_id == game_valorant.id for t in templates if t.game_id)
    
    def test_list_templates_filter_by_visibility(self, user, template_private, template_global):
        """Test filtering by visibility."""
        templates = TemplateService.list_templates(
            user=user,
            visibility=TournamentTemplate.GLOBAL
        )
        
        assert all(t.visibility == TournamentTemplate.GLOBAL for t in templates)
        assert template_global.id in [t.id for t in templates]
    
    def test_list_templates_filter_by_creator(self, user, other_user, template_private):
        """Test filtering by created_by_id."""
        templates = TemplateService.list_templates(
            user=user,
            created_by_id=user.id
        )
        
        assert all(t.created_by_id == user.id for t in templates)
        assert template_private.id in [t.id for t in templates]
    
    def test_list_templates_anonymous_sees_global_only(self, template_private, template_global):
        """Test that anonymous users only see GLOBAL templates."""
        templates = TemplateService.list_templates(user=None)
        
        template_ids = [t.id for t in templates]
        assert template_global.id in template_ids
        assert template_private.id not in template_ids
    
    def test_list_templates_staff_sees_all(self, staff_user, template_private, template_global):
        """Test that staff can see all templates."""
        templates = TemplateService.list_templates(user=staff_user)
        
        # Staff should see everything
        assert len(templates) >= 2


@pytest.mark.django_db
class TestApplyTemplate:
    """Tests for TemplateService.apply_template()"""
    
    def test_apply_template_success(self, user, template_with_config):
        """Test applying template (happy path)."""
        merged = TemplateService.apply_template(
            template_id=template_with_config.id,
            user=user,
            tournament_payload={"name": "Summer Championship 2025"}
        )
        
        # Should have template config + override
        assert merged["format"] == "single_elimination"
        assert merged["max_participants"] == 16
        assert merged["name"] == "Summer Championship 2025"
        
        # Check usage count incremented
        template_with_config.refresh_from_db()
        assert template_with_config.usage_count == 1
        assert template_with_config.last_used_at is not None
    
    def test_apply_template_payload_overrides_template(self, user, template_with_config):
        """Test that tournament_payload overrides template values."""
        merged = TemplateService.apply_template(
            template_id=template_with_config.id,
            user=user,
            tournament_payload={"max_participants": 32}  # Override template's 16
        )
        
        assert merged["max_participants"] == 32  # Overridden
        assert merged["format"] == "single_elimination"  # From template
    
    def test_apply_template_inactive_denied(self, user, template_inactive):
        """Test that inactive templates cannot be applied."""
        with pytest.raises(ValidationError) as exc_info:
            TemplateService.apply_template(
                template_id=template_inactive.id,
                user=user,
            )
        
        assert "Cannot apply inactive template" in str(exc_info.value)
    
    def test_apply_template_adds_game_id(self, user, game_valorant):
        """Test that game_id is added from template if not in payload."""
        template = TemplateService.create_template(
            name="With Game",
            created_by=user,
            game_id=game_valorant.id,
            template_config={"format": "swiss"},
        )
        
        merged = TemplateService.apply_template(
            template_id=template.id,
            user=user,
        )
        
        assert merged["game_id"] == game_valorant.id
    
    def test_apply_template_permission_check(self, other_user, template_private):
        """Test that permission check is enforced."""
        with pytest.raises(PermissionDenied):
            TemplateService.apply_template(
                template_id=template_private.id,
                user=other_user,
            )


@pytest.mark.django_db
class TestDeleteTemplate:
    """Tests for TemplateService.delete_template()"""
    
    def test_delete_template_success(self, user, template_private):
        """Test soft deleting template."""
        TemplateService.delete_template(template_private.id, user)
        
        # Verify soft delete
        template_private.refresh_from_db()
        assert template_private.is_deleted is True
        assert template_private.deleted_at is not None
        assert template_private.deleted_by == user
    
    def test_delete_template_non_owner_denied(self, other_user, template_private):
        """Test that non-owner cannot delete template."""
        with pytest.raises(PermissionDenied):
            TemplateService.delete_template(template_private.id, other_user)
    
    def test_delete_template_staff_allowed(self, staff_user, template_private):
        """Test that staff can delete any template."""
        TemplateService.delete_template(template_private.id, staff_user)
        
        template_private.refresh_from_db()
        assert template_private.is_deleted is True


@pytest.mark.django_db
class TestValidateTemplateConfig:
    """Tests for TemplateService._validate_template_config()"""
    
    def test_validate_valid_config(self, game_valorant):
        """Test that valid config passes validation."""
        config = {
            "format": "single_elimination",
            "participation_type": "team",
            "max_participants": 16,
        }
        
        # Should not raise
        TemplateService._validate_template_config(config, game_valorant)
    
    def test_validate_invalid_format(self):
        """Test that invalid format raises ValidationError."""
        config = {"format": "invalid_format"}
        
        with pytest.raises(ValidationError) as exc_info:
            TemplateService._validate_template_config(config)
        
        assert "Invalid format" in str(exc_info.value)
    
    def test_validate_invalid_participation_type(self):
        """Test that invalid participation_type raises ValidationError."""
        config = {"participation_type": "invalid_type"}
        
        with pytest.raises(ValidationError):
            TemplateService._validate_template_config(config)
    
    def test_validate_numeric_fields(self):
        """Test validation of numeric fields."""
        valid_config = {
            "max_participants": 16,
            "entry_fee_amount": "500.00",
        }
        
        # Should not raise
        TemplateService._validate_template_config(valid_config)
        
        # Invalid numeric
        invalid_config = {"max_participants": "not_a_number"}
        with pytest.raises(ValidationError):
            TemplateService._validate_template_config(invalid_config)
