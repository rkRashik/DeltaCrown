"""
Data Transfer Objects for Smart Registration (Phase 5).

These DTOs facilitate data transfer between tournament_ops service layer
and the tournaments domain without creating ORM dependencies.

Source: Documents/Modify_TournamentApp/Workplan/SMART_REG_AND_RULES_PART_3.md
"""

from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime


@dataclass
class RegistrationQuestionDTO:
    """
    DTO for RegistrationQuestion model.
    
    Represents a dynamic registration question with validation config.
    """
    id: int
    slug: str
    text: str
    type: str  # text, select, boolean, number, etc.
    scope: str  # team or player
    is_required: bool
    order: int
    config: dict = field(default_factory=dict)
    help_text: str = ''
    show_if: dict = field(default_factory=dict)
    is_built_in: bool = False
    tournament_id: Optional[int] = None
    game_id: Optional[int] = None
    
    @classmethod
    def from_model(cls, question):
        """
        Convert RegistrationQuestion model to DTO.
        
        Args:
            question: tournaments.models.RegistrationQuestion instance
        
        Returns:
            RegistrationQuestionDTO
        """
        return cls(
            id=question.id,
            slug=question.slug,
            text=question.text,
            type=question.type,
            scope=question.scope,
            is_required=question.is_required,
            order=question.order,
            config=question.config,
            help_text=question.help_text,
            show_if=question.show_if,
            is_built_in=question.is_built_in,
            tournament_id=question.tournament_id,
            game_id=question.game_id,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'slug': self.slug,
            'text': self.text,
            'type': self.type,
            'scope': self.scope,
            'is_required': self.is_required,
            'order': self.order,
            'config': self.config,
            'help_text': self.help_text,
            'show_if': self.show_if,
            'is_built_in': self.is_built_in,
            'tournament_id': self.tournament_id,
            'game_id': self.game_id,
        }
    
    def validate_answer(self, answer_value: Any) -> tuple[bool, list[str]]:
        """
        Validate answer value against question config.
        
        Returns:
            (is_valid, error_messages)
        """
        errors = []
        
        # Required check
        if self.is_required and (answer_value is None or answer_value == ''):
            errors.append(f'{self.text} is required')
            return (False, errors)
        
        # Skip validation if no answer provided (and not required)
        if answer_value is None or answer_value == '':
            return (True, [])
        
        # Type-specific validation
        if self.type == 'number':
            if not isinstance(answer_value, (int, float)):
                errors.append(f'{self.text} must be a number')
            else:
                # Min/max validation
                if 'min' in self.config and answer_value < self.config['min']:
                    errors.append(f'{self.text} must be at least {self.config["min"]}')
                if 'max' in self.config and answer_value > self.config['max']:
                    errors.append(f'{self.text} must be at most {self.config["max"]}')
        
        elif self.type == 'select':
            if 'options' in self.config:
                valid_options = self.config['options']
                if answer_value not in valid_options:
                    errors.append(f'{self.text} must be one of: {", ".join(valid_options)}')
        
        elif self.type == 'multi_select':
            if not isinstance(answer_value, list):
                errors.append(f'{self.text} must be a list')
            elif 'options' in self.config:
                valid_options = self.config['options']
                for val in answer_value:
                    if val not in valid_options:
                        errors.append(f'Invalid option: {val}')
        
        elif self.type == 'boolean':
            if not isinstance(answer_value, bool):
                errors.append(f'{self.text} must be true or false')
        
        return (len(errors) == 0, errors)


@dataclass
class RegistrationRuleDTO:
    """
    DTO for RegistrationRule model.
    
    Represents an auto-approval/rejection rule.
    """
    id: int
    tournament_id: int
    name: str
    rule_type: str  # auto_approve, auto_reject, flag_for_review
    condition: dict
    priority: int
    is_active: bool
    reason_template: str = ''
    
    @classmethod
    def from_model(cls, rule):
        """
        Convert RegistrationRule model to DTO.
        
        Args:
            rule: tournaments.models.RegistrationRule instance
        
        Returns:
            RegistrationRuleDTO
        """
        return cls(
            id=rule.id,
            tournament_id=rule.tournament_id,
            name=rule.name,
            rule_type=rule.rule_type,
            condition=rule.condition,
            priority=rule.priority,
            is_active=rule.is_active,
            reason_template=rule.reason_template,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'tournament_id': self.tournament_id,
            'name': self.name,
            'rule_type': self.rule_type,
            'condition': self.condition,
            'priority': self.priority,
            'is_active': self.is_active,
            'reason_template': self.reason_template,
        }
    
    def evaluate(self, registration_data: dict, answers: dict) -> bool:
        """
        Evaluate if condition matches registration data + answers.
        
        Args:
            registration_data: {user_id, team_id, email_verified, ...}
            answers: {question_slug: answer_value, ...}
        
        Returns:
            True if condition matches, False otherwise
        """
        # Combine data sources
        data = {**registration_data, **answers}
        
        # Evaluate each condition key
        for key, expected in self.condition.items():
            actual = data.get(key)
            
            # Handle different comparison types
            if isinstance(expected, dict):
                # Advanced operators: {"in": [...], "gte": 18, ...}
                for op, op_value in expected.items():
                    if op == 'in':
                        if actual not in op_value:
                            return False
                    elif op == 'gte':
                        if actual is None or actual < op_value:
                            return False
                    elif op == 'lte':
                        if actual is None or actual > op_value:
                            return False
                    elif op == 'eq':
                        if actual != op_value:
                            return False
                    else:
                        # Unknown operator
                        return False
            else:
                # Simple equality
                if actual != expected:
                    return False
        
        return True


@dataclass
class RegistrationDraftDTO:
    """
    DTO for RegistrationDraft model.
    
    Represents a draft registration (multi-session persistence).
    """
    id: int
    uuid: str
    registration_number: str
    user_id: int
    tournament_id: int
    team_id: Optional[int]
    form_data: dict
    auto_filled_fields: list
    locked_fields: list
    current_step: str
    completion_percentage: int
    submitted: bool
    registration_id: Optional[int]
    created_at: datetime
    last_saved_at: datetime
    expires_at: datetime
    
    @classmethod
    def from_model(cls, draft):
        """
        Convert RegistrationDraft model to DTO.
        
        Args:
            draft: tournaments.models.RegistrationDraft instance
        
        Returns:
            RegistrationDraftDTO
        """
        return cls(
            id=draft.id,
            uuid=str(draft.uuid),
            registration_number=draft.registration_number,
            user_id=draft.user_id,
            tournament_id=draft.tournament_id,
            team_id=draft.team_id,
            form_data=draft.form_data,
            auto_filled_fields=draft.auto_filled_fields,
            locked_fields=draft.locked_fields,
            current_step=draft.current_step,
            completion_percentage=draft.completion_percentage,
            submitted=draft.submitted,
            registration_id=draft.registration_id,
            created_at=draft.created_at,
            last_saved_at=draft.last_saved_at,
            expires_at=draft.expires_at,
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'uuid': self.uuid,
            'registration_number': self.registration_number,
            'user_id': self.user_id,
            'tournament_id': self.tournament_id,
            'team_id': self.team_id,
            'form_data': self.form_data,
            'auto_filled_fields': self.auto_filled_fields,
            'locked_fields': self.locked_fields,
            'current_step': self.current_step,
            'completion_percentage': self.completion_percentage,
            'submitted': self.submitted,
            'registration_id': self.registration_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_saved_at': self.last_saved_at.isoformat() if self.last_saved_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
        }
    
    def is_expired(self) -> bool:
        """Check if draft has expired."""
        from django.utils import timezone
        return timezone.now() > self.expires_at
