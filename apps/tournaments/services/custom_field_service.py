"""
Custom Field Service

Module: 2.2 - Game Configurations & Custom Fields (Backend Only)
Source Documents:
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md (CustomField Model)
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md (Service Layer Standards)

Architecture Decisions:
- ADR-001: Service Layer Pattern - All business logic in services
- ADR-004: PostgreSQL Features - Uses JSONB for field_config and field_value
- ADR-010: Audit Logging - Track custom field changes

Description:
Manages custom fields for tournaments, providing validation, CRUD operations,
and constraint enforcement. Custom fields allow organizers to add dynamic
fields (Discord server, special requirements, etc.) with type-safe validation.

Supported field types:
- text: Free-form text (with optional regex validation)
- number: Numeric values (with min/max constraints)
- media: File uploads
- toggle: Boolean yes/no
- date: Date values
- url: URL with validation
- dropdown: Predefined options

Example custom field:
{
    "field_name": "Discord Server",
    "field_key": "discord-server",
    "field_type": "url",
    "is_required": true,
    "help_text": "Tournament Discord server link",
    "field_config": {
        "pattern": "^https://discord\\.gg/[a-zA-Z0-9]+$"
    }
}
"""

import re
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date, datetime
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils.text import slugify

from apps.tournaments.models.tournament import CustomField, Tournament


class CustomFieldService:
    """
    Service for managing custom tournament fields.
    
    Provides CRUD operations, validation, and constraint enforcement
    for tournament custom fields.
    """
    
    @staticmethod
    @transaction.atomic
    def create_field(
        tournament_id: int,
        user,
        field_data: Dict[str, Any]
    ) -> CustomField:
        """
        Create a custom field for a tournament.
        
        Args:
            tournament_id: ID of the tournament
            user: User creating the field (organizer or staff)
            field_data: Field definition data
        
        Returns:
            CustomField: Created field instance
        
        Raises:
            Tournament.DoesNotExist: If tournament not found
            ValidationError: If field_data is invalid
            PermissionError: If user lacks permission
        
        Example:
            >>> field = CustomFieldService.create_field(
            ...     tournament_id=1,
            ...     user=organizer,
            ...     field_data={
            ...         'field_name': 'Discord Server',
            ...         'field_type': 'url',
            ...         'is_required': True,
            ...         'help_text': 'Tournament Discord link'
            ...     }
            ... )
        """
        tournament = Tournament.objects.get(id=tournament_id)
        
        # Permission check: organizer or staff only
        if tournament.organizer != user and not user.is_staff:
            raise PermissionError("Only the organizer or staff can add custom fields")
        
        # Status check: DRAFT only
        if tournament.status != Tournament.DRAFT:
            raise ValidationError(
                f"Cannot add custom fields to tournament with status '{tournament.status}'. "
                "Only DRAFT tournaments can be edited."
            )
        
        # Validate required fields
        required_fields = ['field_name', 'field_type']
        missing_fields = [f for f in required_fields if f not in field_data]
        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate field_type
        valid_field_types = ['text', 'number', 'media', 'toggle', 'date', 'url', 'dropdown']
        if field_data['field_type'] not in valid_field_types:
            raise ValidationError(
                f"Invalid field_type: {field_data['field_type']}. "
                f"Must be one of: {', '.join(valid_field_types)}"
            )
        
        # Generate field_key if not provided
        field_key = field_data.get('field_key')
        if not field_key:
            field_key = slugify(field_data['field_name'])
        
        # Check for duplicate field_key
        if CustomField.objects.filter(tournament=tournament, field_key=field_key).exists():
            raise ValidationError(f"A field with key '{field_key}' already exists for this tournament")
        
        # Validate field_config based on field_type
        field_config = field_data.get('field_config', {})
        CustomFieldService._validate_field_config(field_data['field_type'], field_config)
        
        # Create custom field
        custom_field = CustomField(
            tournament=tournament,
            field_name=field_data['field_name'],
            field_key=field_key,
            field_type=field_data['field_type'],
            field_config=field_config,
            is_required=field_data.get('is_required', False),
            help_text=field_data.get('help_text', ''),
            order=field_data.get('order', 0),
        )
        
        custom_field.full_clean()
        custom_field.save()
        
        return custom_field
    
    @staticmethod
    @transaction.atomic
    def update_field(
        field_id: int,
        user,
        update_data: Dict[str, Any]
    ) -> CustomField:
        """
        Update a custom field.
        
        Args:
            field_id: ID of the custom field
            user: User updating the field (organizer or staff)
            update_data: Partial update data
        
        Returns:
            CustomField: Updated field instance
        
        Raises:
            CustomField.DoesNotExist: If field not found
            ValidationError: If update_data is invalid
            PermissionError: If user lacks permission
        
        Example:
            >>> field = CustomFieldService.update_field(
            ...     field_id=1,
            ...     user=organizer,
            ...     update_data={
            ...         'is_required': False,
            ...         'help_text': 'Optional Discord link'
            ...     }
            ... )
        """
        custom_field = CustomField.objects.select_related('tournament').get(id=field_id)
        tournament = custom_field.tournament
        
        # Permission check: organizer or staff only
        if tournament.organizer != user and not user.is_staff:
            raise PermissionError("Only the organizer or staff can update custom fields")
        
        # Status check: DRAFT only
        if tournament.status != Tournament.DRAFT:
            raise ValidationError(
                f"Cannot update custom fields for tournament with status '{tournament.status}'. "
                "Only DRAFT tournaments can be edited."
            )
        
        # Apply updates
        updatable_fields = ['field_name', 'field_type', 'field_config', 'is_required', 'help_text', 'order']
        for field in updatable_fields:
            if field in update_data:
                setattr(custom_field, field, update_data[field])
        
        # Validate field_config if field_type changed
        if 'field_type' in update_data or 'field_config' in update_data:
            CustomFieldService._validate_field_config(
                custom_field.field_type,
                custom_field.field_config
            )
        
        custom_field.full_clean()
        custom_field.save()
        
        return custom_field
    
    @staticmethod
    @transaction.atomic
    def delete_field(field_id: int, user) -> None:
        """
        Delete a custom field.
        
        Args:
            field_id: ID of the custom field
            user: User deleting the field (organizer or staff)
        
        Raises:
            CustomField.DoesNotExist: If field not found
            PermissionError: If user lacks permission
            ValidationError: If tournament status doesn't allow deletion
        
        Example:
            >>> CustomFieldService.delete_field(field_id=1, user=organizer)
        """
        custom_field = CustomField.objects.select_related('tournament').get(id=field_id)
        tournament = custom_field.tournament
        
        # Permission check: organizer or staff only
        if tournament.organizer != user and not user.is_staff:
            raise PermissionError("Only the organizer or staff can delete custom fields")
        
        # Status check: DRAFT only
        if tournament.status != Tournament.DRAFT:
            raise ValidationError(
                f"Cannot delete custom fields for tournament with status '{tournament.status}'. "
                "Only DRAFT tournaments can be edited."
            )
        
        custom_field.delete()
    
    @staticmethod
    def validate_field_value(
        field: CustomField,
        value: Any
    ) -> Any:
        """
        Validate a value against custom field constraints.
        
        Args:
            field: CustomField instance with type and config
            value: Value to validate
        
        Returns:
            Any: Validated/coerced value
        
        Raises:
            ValidationError: If value is invalid
        
        Example:
            >>> field = CustomField.objects.get(field_key='discord-server')
            >>> validated = CustomFieldService.validate_field_value(field, 'https://discord.gg/abc123')
        """
        # Check required constraint
        if field.is_required and (value is None or value == ''):
            raise ValidationError(f"Field '{field.field_name}' is required")
        
        # If value is None/empty and not required, allow it
        if value is None or value == '':
            return value
        
        # Type-specific validation
        if field.field_type == 'text':
            return CustomFieldService._validate_text(value, field.field_config)
        elif field.field_type == 'number':
            return CustomFieldService._validate_number(value, field.field_config)
        elif field.field_type == 'toggle':
            return CustomFieldService._validate_toggle(value)
        elif field.field_type == 'date':
            return CustomFieldService._validate_date(value)
        elif field.field_type == 'url':
            return CustomFieldService._validate_url(value, field.field_config)
        elif field.field_type == 'dropdown':
            return CustomFieldService._validate_dropdown(value, field.field_config)
        elif field.field_type == 'media':
            # Media validation would check file type, size, etc.
            # For now, just ensure it's a valid file path or upload
            return value
        else:
            raise ValidationError(f"Unknown field type: {field.field_type}")
    
    @staticmethod
    def _validate_field_config(field_type: str, field_config: Dict[str, Any]) -> None:
        """
        Validate field_config based on field_type.
        
        Args:
            field_type: Type of field
            field_config: Configuration dictionary
        
        Raises:
            ValidationError: If config is invalid for field_type
        """
        if field_type == 'text':
            if 'min_length' in field_config and not isinstance(field_config['min_length'], int):
                raise ValidationError("text field_config.min_length must be an integer")
            if 'max_length' in field_config and not isinstance(field_config['max_length'], int):
                raise ValidationError("text field_config.max_length must be an integer")
            if 'pattern' in field_config and not isinstance(field_config['pattern'], str):
                raise ValidationError("text field_config.pattern must be a string")
        
        elif field_type == 'number':
            if 'min_value' in field_config and not isinstance(field_config['min_value'], (int, float)):
                raise ValidationError("number field_config.min_value must be a number")
            if 'max_value' in field_config and not isinstance(field_config['max_value'], (int, float)):
                raise ValidationError("number field_config.max_value must be a number")
        
        elif field_type == 'dropdown':
            if 'options' not in field_config:
                raise ValidationError("dropdown field_config must include 'options' list")
            if not isinstance(field_config['options'], list) or not field_config['options']:
                raise ValidationError("dropdown field_config.options must be a non-empty list")
        
        elif field_type == 'url':
            if 'pattern' in field_config and not isinstance(field_config['pattern'], str):
                raise ValidationError("url field_config.pattern must be a string")
    
    @staticmethod
    def _validate_text(value: Any, config: Dict[str, Any]) -> str:
        """Validate text field value."""
        if not isinstance(value, str):
            raise ValidationError("Text field value must be a string")
        
        if 'min_length' in config and len(value) < config['min_length']:
            raise ValidationError(f"Text must be at least {config['min_length']} characters")
        if 'max_length' in config and len(value) > config['max_length']:
            raise ValidationError(f"Text must be at most {config['max_length']} characters")
        if 'pattern' in config:
            if not re.match(config['pattern'], value):
                raise ValidationError(f"Text does not match required pattern")
        
        return value
    
    @staticmethod
    def _validate_number(value: Any, config: Dict[str, Any]) -> float:
        """Validate number field value."""
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            raise ValidationError("Number field value must be a valid number")
        
        if 'min_value' in config and num_value < config['min_value']:
            raise ValidationError(f"Number must be at least {config['min_value']}")
        if 'max_value' in config and num_value > config['max_value']:
            raise ValidationError(f"Number must be at most {config['max_value']}")
        
        return num_value
    
    @staticmethod
    def _validate_toggle(value: Any) -> bool:
        """Validate toggle field value."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ['true', '1', 'yes']:
                return True
            if value.lower() in ['false', '0', 'no']:
                return False
        raise ValidationError("Toggle field value must be a boolean")
    
    @staticmethod
    def _validate_date(value: Any) -> str:
        """Validate date field value."""
        if isinstance(value, date):
            return value.isoformat()
        if isinstance(value, str):
            try:
                # Try parsing ISO format
                datetime.fromisoformat(value.replace('Z', '+00:00'))
                return value
            except ValueError:
                raise ValidationError("Date field value must be in ISO format (YYYY-MM-DD)")
        raise ValidationError("Date field value must be a date or ISO format string")
    
    @staticmethod
    def _validate_url(value: Any, config: Dict[str, Any]) -> str:
        """Validate URL field value."""
        if not isinstance(value, str):
            raise ValidationError("URL field value must be a string")
        
        # Django URL validator
        validator = URLValidator()
        try:
            validator(value)
        except ValidationError:
            raise ValidationError("Invalid URL format")
        
        # Check pattern if specified
        if 'pattern' in config:
            if not re.match(config['pattern'], value):
                raise ValidationError("URL does not match required pattern")
        
        return value
    
    @staticmethod
    def _validate_dropdown(value: Any, config: Dict[str, Any]) -> str:
        """Validate dropdown field value."""
        if not isinstance(value, str):
            raise ValidationError("Dropdown field value must be a string")
        
        options = config.get('options', [])
        if value not in options:
            raise ValidationError(f"Value must be one of: {', '.join(options)}")
        
        return value
