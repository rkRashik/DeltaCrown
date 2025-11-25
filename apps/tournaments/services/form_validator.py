"""
Dynamic Form Field Validators

Sprint 1: Validation Service
Created: November 25, 2025

Provides validation for all 15+ field types supported by the form builder.
"""

import re
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple
from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError


class FieldValidationError(Exception):
    """Custom exception for field validation errors"""
    def __init__(self, field_id: str, message: str):
        self.field_id = field_id
        self.message = message
        super().__init__(f"Field '{field_id}': {message}")


class FormFieldValidator:
    """
    Validates form field values based on field type and configuration.
    
    Supports 15+ field types with comprehensive validation rules.
    """
    
    # Phone number patterns for different regions
    PHONE_PATTERNS = {
        'BD': r'^(\+880|880|0)?1[3-9]\d{8}$',  # Bangladesh
        'IN': r'^(\+91|91|0)?[6-9]\d{9}$',      # India
        'INTL': r'^\+?[1-9]\d{1,14}$',          # International E.164
    }
    
    # URL pattern
    URL_PATTERN = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$'
    
    def __init__(self, field_config: Dict[str, Any]):
        """
        Initialize validator with field configuration.
        
        Args:
            field_config: Field definition from form schema
        """
        self.field_config = field_config
        self.field_id = field_config.get('id', 'unknown')
        self.field_type = field_config.get('type', 'text')
        self.required = field_config.get('required', False)
        self.enabled = field_config.get('enabled', True)
        self.validation = field_config.get('validation', {})
    
    def validate(self, value: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate field value.
        
        Args:
            value: The value to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Skip validation if field is disabled
        if not self.enabled:
            return True, None
        
        # Check required
        if self.required and self._is_empty(value):
            return False, f"{self.field_config.get('label', 'This field')} is required"
        
        # Skip type validation if empty and not required
        if self._is_empty(value) and not self.required:
            return True, None
        
        # Delegate to type-specific validator
        validator_method = getattr(self, f'_validate_{self.field_type}', self._validate_text)
        
        try:
            return validator_method(value)
        except FieldValidationError as e:
            return False, e.message
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def _is_empty(self, value: Any) -> bool:
        """Check if value is empty"""
        if value is None:
            return True
        if isinstance(value, str) and value.strip() == '':
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False
    
    # ==================== TEXT VALIDATORS ====================
    
    def _validate_text(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate text field"""
        if not isinstance(value, str):
            return False, "Must be text"
        
        value = value.strip()
        
        # Min length
        min_length = self.validation.get('min_length')
        if min_length and len(value) < min_length:
            return False, f"Must be at least {min_length} characters"
        
        # Max length
        max_length = self.validation.get('max_length')
        if max_length and len(value) > max_length:
            return False, f"Must not exceed {max_length} characters"
        
        # Pattern matching
        pattern = self.validation.get('pattern')
        if pattern:
            if not re.match(pattern, value):
                custom_error = self.validation.get('pattern_error', 'Invalid format')
                return False, custom_error
        
        return True, None
    
    def _validate_textarea(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate textarea (same as text but typically longer)"""
        return self._validate_text(value)
    
    def _validate_email(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate email address"""
        if not isinstance(value, str):
            return False, "Must be text"
        
        value = value.strip().lower()
        
        try:
            django_validate_email(value)
        except DjangoValidationError:
            return False, "Invalid email address"
        
        # Check domain whitelist/blacklist
        domain = value.split('@')[1] if '@' in value else ''
        
        allowed_domains = self.validation.get('allowed_domains', [])
        if allowed_domains and domain not in allowed_domains:
            return False, f"Email must be from: {', '.join(allowed_domains)}"
        
        blocked_domains = self.validation.get('blocked_domains', [])
        if blocked_domains and domain in blocked_domains:
            return False, "This email domain is not allowed"
        
        return True, None
    
    def _validate_phone(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate phone number"""
        if not isinstance(value, str):
            return False, "Must be text"
        
        value = value.strip()
        
        # Get region (default to Bangladesh)
        region = self.validation.get('region', 'BD')
        pattern = self.PHONE_PATTERNS.get(region, self.PHONE_PATTERNS['INTL'])
        
        if not re.match(pattern, value):
            return False, "Invalid phone number format"
        
        return True, None
    
    def _validate_url(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate URL"""
        if not isinstance(value, str):
            return False, "Must be text"
        
        value = value.strip()
        
        if not re.match(self.URL_PATTERN, value):
            return False, "Invalid URL format (must start with http:// or https://)"
        
        return True, None
    
    # ==================== NUMBER VALIDATORS ====================
    
    def _validate_number(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate numeric field"""
        # Try to convert to number
        try:
            if isinstance(value, str):
                value = value.strip()
                if '.' in value:
                    num_value = float(value)
                else:
                    num_value = int(value)
            elif isinstance(value, (int, float, Decimal)):
                num_value = float(value)
            else:
                return False, "Must be a number"
        except (ValueError, InvalidOperation):
            return False, "Must be a valid number"
        
        # Min value
        min_value = self.validation.get('min_value')
        if min_value is not None and num_value < min_value:
            return False, f"Must be at least {min_value}"
        
        # Max value
        max_value = self.validation.get('max_value')
        if max_value is not None and num_value > max_value:
            return False, f"Must not exceed {max_value}"
        
        # Integer only
        if self.validation.get('integer_only', False) and not isinstance(num_value, int):
            if num_value != int(num_value):
                return False, "Must be a whole number"
        
        return True, None
    
    def _validate_rating(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate rating (1-5 stars typically)"""
        try:
            rating = int(value)
        except (ValueError, TypeError):
            return False, "Invalid rating"
        
        max_rating = self.validation.get('max_rating', 5)
        if not (1 <= rating <= max_rating):
            return False, f"Rating must be between 1 and {max_rating}"
        
        return True, None
    
    # ==================== DATE/TIME VALIDATORS ====================
    
    def _validate_date(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate date field"""
        # Parse date
        if isinstance(value, str):
            try:
                date_obj = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                return False, "Invalid date format (use YYYY-MM-DD)"
        elif isinstance(value, date):
            date_obj = value
        else:
            return False, "Invalid date"
        
        # Min date
        min_date_str = self.validation.get('min_date')
        if min_date_str:
            min_date = datetime.strptime(min_date_str, '%Y-%m-%d').date()
            if date_obj < min_date:
                return False, f"Date must be on or after {min_date_str}"
        
        # Max date
        max_date_str = self.validation.get('max_date')
        if max_date_str:
            max_date = datetime.strptime(max_date_str, '%Y-%m-%d').date()
            if date_obj > max_date:
                return False, f"Date must be on or before {max_date_str}"
        
        return True, None
    
    def _validate_datetime(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate datetime field"""
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                return False, "Invalid datetime format"
        
        return True, None
    
    # ==================== CHOICE VALIDATORS ====================
    
    def _validate_dropdown(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate dropdown selection"""
        options = self.field_config.get('options', [])
        
        if not options:
            return True, None  # No validation if no options defined
        
        # Extract option values
        valid_values = []
        for option in options:
            if isinstance(option, dict):
                valid_values.append(option.get('value', option.get('label')))
            else:
                valid_values.append(str(option))
        
        if value not in valid_values:
            return False, "Invalid selection"
        
        return True, None
    
    def _validate_radio(self, value: str) -> Tuple[bool, Optional[str]]:
        """Validate radio button (same as dropdown)"""
        return self._validate_dropdown(value)
    
    def _validate_checkbox(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate checkbox (single or multiple)"""
        # Single checkbox (boolean)
        if isinstance(value, bool):
            return True, None
        
        # Multiple checkboxes (list of values)
        if isinstance(value, list):
            options = self.field_config.get('options', [])
            if not options:
                return True, None
            
            valid_values = [
                opt.get('value', opt.get('label')) if isinstance(opt, dict) else str(opt)
                for opt in options
            ]
            
            for v in value:
                if v not in valid_values:
                    return False, f"Invalid selection: {v}"
            
            # Check min/max selections
            min_selections = self.validation.get('min_selections')
            if min_selections and len(value) < min_selections:
                return False, f"Select at least {min_selections} options"
            
            max_selections = self.validation.get('max_selections')
            if max_selections and len(value) > max_selections:
                return False, f"Select at most {max_selections} options"
            
            return True, None
        
        return False, "Invalid checkbox value"
    
    def _validate_multiselect(self, value: List) -> Tuple[bool, Optional[str]]:
        """Validate multi-select field"""
        if not isinstance(value, list):
            return False, "Must be a list"
        
        return self._validate_checkbox(value)
    
    # ==================== FILE VALIDATORS ====================
    
    def _validate_file(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate file upload"""
        # In production, value would be a Django UploadedFile
        # For now, validate file metadata
        
        if isinstance(value, dict):
            # Validate file size
            max_size = self.validation.get('max_size_mb', 10) * 1024 * 1024  # Convert to bytes
            file_size = value.get('size', 0)
            
            if file_size > max_size:
                max_size_mb = max_size / (1024 * 1024)
                return False, f"File size must not exceed {max_size_mb}MB"
            
            # Validate file type
            allowed_types = self.validation.get('allowed_types', [])
            if allowed_types:
                file_ext = value.get('name', '').split('.')[-1].lower()
                if file_ext not in allowed_types:
                    return False, f"Allowed file types: {', '.join(allowed_types)}"
        
        return True, None
    
    # ==================== SPECIAL VALIDATORS ====================
    
    def _validate_agreement(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Validate agreement/terms acceptance"""
        if not value or value != True:
            return False, "You must accept the terms"
        
        return True, None
    
    def _validate_section_header(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Section headers don't need validation"""
        return True, None
    
    def _validate_divider(self, value: Any) -> Tuple[bool, Optional[str]]:
        """Dividers don't need validation"""
        return True, None


class FormValidator:
    """
    Validates complete form submissions.
    
    Handles field-level validation, conditional logic, and cross-field validation.
    """
    
    def __init__(self, form_schema: Dict[str, Any]):
        """
        Initialize form validator.
        
        Args:
            form_schema: Complete form configuration
        """
        self.form_schema = form_schema
        self.sections = form_schema.get('sections', [])
        self.conditional_rules = form_schema.get('conditional_rules', {})
    
    def validate_submission(self, response_data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
        """
        Validate complete form submission.
        
        Args:
            response_data: User's form responses {field_id: value}
        
        Returns:
            Tuple of (is_valid, errors_dict)
            errors_dict maps field_id to error message
        """
        errors = {}
        
        # Validate each field
        for section in self.sections:
            for field in section.get('fields', []):
                field_id = field.get('id')
                
                # Skip if field is hidden by conditional logic
                if self._is_field_hidden(field_id, response_data):
                    continue
                
                # Get field value
                value = response_data.get(field_id)
                
                # Validate
                validator = FormFieldValidator(field)
                is_valid, error_message = validator.validate(value)
                
                if not is_valid:
                    errors[field_id] = error_message
        
        # Cross-field validation
        cross_field_errors = self._validate_cross_fields(response_data)
        errors.update(cross_field_errors)
        
        return len(errors) == 0, errors
    
    def _is_field_hidden(self, field_id: str, response_data: Dict[str, Any]) -> bool:
        """
        Check if field is hidden by conditional logic.
        
        Args:
            field_id: Field to check
            response_data: Current form responses
        
        Returns:
            True if field is hidden, False otherwise
        """
        # Get conditional rules for this field
        field_rules = self.conditional_rules.get(field_id, {})
        
        if not field_rules:
            return False  # No rules = always visible
        
        show_if = field_rules.get('show_if', [])
        hide_if = field_rules.get('hide_if', [])
        
        # Evaluate show_if conditions
        if show_if:
            if not self._evaluate_conditions(show_if, response_data):
                return True  # Conditions not met, hide field
        
        # Evaluate hide_if conditions
        if hide_if:
            if self._evaluate_conditions(hide_if, response_data):
                return True  # Conditions met, hide field
        
        return False
    
    def _evaluate_conditions(self, conditions: List[Dict], response_data: Dict[str, Any]) -> bool:
        """
        Evaluate conditional logic rules.
        
        Args:
            conditions: List of condition rules
            response_data: Current form responses
        
        Returns:
            True if conditions are met
        """
        if not conditions:
            return True
        
        # Get logic operator (AND/OR)
        logic = conditions[0].get('logic', 'AND') if len(conditions) > 1 else 'AND'
        
        results = []
        for condition in conditions:
            field_id = condition.get('field')
            operator = condition.get('operator', 'equals')
            expected_value = condition.get('value')
            
            actual_value = response_data.get(field_id)
            
            # Evaluate based on operator
            if operator == 'equals':
                results.append(actual_value == expected_value)
            elif operator == 'not_equals':
                results.append(actual_value != expected_value)
            elif operator == 'contains':
                results.append(expected_value in str(actual_value))
            elif operator == 'greater_than':
                results.append(float(actual_value) > float(expected_value))
            elif operator == 'less_than':
                results.append(float(actual_value) < float(expected_value))
            elif operator == 'is_empty':
                results.append(not actual_value)
            elif operator == 'is_not_empty':
                results.append(bool(actual_value))
        
        # Apply logic
        if logic == 'AND':
            return all(results)
        else:  # OR
            return any(results)
    
    def _validate_cross_fields(self, response_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Validate relationships between multiple fields.
        
        Args:
            response_data: Form responses
        
        Returns:
            Dict of field_id -> error_message
        """
        errors = {}
        
        # Example: Password confirmation
        if 'password' in response_data and 'password_confirm' in response_data:
            if response_data['password'] != response_data['password_confirm']:
                errors['password_confirm'] = "Passwords do not match"
        
        # Example: Date range validation
        if 'start_date' in response_data and 'end_date' in response_data:
            start = response_data['start_date']
            end = response_data['end_date']
            
            if start and end:
                try:
                    start_date = datetime.strptime(start, '%Y-%m-%d').date()
                    end_date = datetime.strptime(end, '%Y-%m-%d').date()
                    
                    if end_date < start_date:
                        errors['end_date'] = "End date must be after start date"
                except ValueError:
                    pass  # Already handled by field validation
        
        return errors
    
    def get_visible_fields(self, response_data: Dict[str, Any]) -> List[str]:
        """
        Get list of visible field IDs based on conditional logic.
        
        Args:
            response_data: Current form responses
        
        Returns:
            List of visible field IDs
        """
        visible_fields = []
        
        for section in self.sections:
            for field in section.get('fields', []):
                field_id = field.get('id')
                
                if not self._is_field_hidden(field_id, response_data):
                    visible_fields.append(field_id)
        
        return visible_fields
