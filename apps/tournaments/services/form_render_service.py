"""
Dynamic Form Rendering Service

Sprint 1-2: Form Rendering Engine
Created: November 25, 2025

Handles dynamic form generation, validation, conditional logic, and response storage.
"""

from typing import Dict, List, Any, Optional, Tuple
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.tournaments.models import (
    TournamentRegistrationForm,
    FormResponse,
    Tournament,
)
from apps.tournaments.services.form_validator import FormValidator, FormFieldValidator


class FormRenderService:
    """
    Main service for rendering dynamic forms and processing responses.
    
    Responsibilities:
    - Generate HTML from form schema
    - Validate submissions
    - Handle conditional logic
    - Save/update responses
    - Track analytics
    """
    
    def __init__(self, tournament: Tournament):
        """
        Initialize service for a specific tournament.
        
        Args:
            tournament: Tournament instance
        """
        self.tournament = tournament
        
        # Get or create registration form
        self.form_config, created = TournamentRegistrationForm.objects.get_or_create(
            tournament=tournament,
            defaults={'form_schema': self._get_default_schema()}
        )
        
        self.schema = self.form_config.form_schema
        self.validator = FormValidator(self.schema)
    
    def _get_default_schema(self) -> Dict[str, Any]:
        """Get default form schema if none exists"""
        return {
            'version': '2.0',
            'form_id': f'{self.tournament.slug}_registration',
            'form_name': f'{self.tournament.name} Registration',
            'settings': {
                'theme': 'dark',
                'primary_color': '#FF4655',
                'show_section_numbers': True,
            },
            'sections': []
        }
    
    # ==================== RENDERING ====================
    
    def render_form(self, step: int = 1, response_data: Optional[Dict] = None) -> str:
        """
        Render form HTML for a specific step.
        
        Args:
            step: Current step number (1-indexed)
            response_data: Existing response data for pre-filling
        
        Returns:
            Rendered HTML string
        """
        response_data = response_data or {}
        
        # Get sections for this step
        sections = self._get_sections_for_step(step)
        
        # Filter fields based on conditional logic
        visible_sections = []
        for section in sections:
            visible_fields = []
            for field in section.get('fields', []):
                if not self._is_field_hidden(field['id'], response_data):
                    visible_fields.append(field)
            
            if visible_fields:
                section_copy = section.copy()
                section_copy['fields'] = visible_fields
                visible_sections.append(section_copy)
        
        # Render each field
        rendered_fields = []
        for section in visible_sections:
            section_fields = []
            for field in section['fields']:
                field_html = self._render_field(field, response_data.get(field['id']))
                section_fields.append({
                    'field': field,
                    'html': field_html
                })
            
            rendered_fields.append({
                'section': section,
                'fields': section_fields
            })
        
        # Calculate progress
        total_steps = self._get_total_steps()
        progress_percent = (step / total_steps) * 100 if self.form_config.enable_progress_bar else None
        
        # Render complete form
        context = {
            'tournament': self.tournament,
            'form_config': self.form_config,
            'sections': rendered_fields,
            'current_step': step,
            'total_steps': total_steps,
            'progress_percent': progress_percent,
            'is_final_step': step == total_steps,
        }
        
        return render_to_string('tournaments/form_builder/form_step.html', context)
    
    def _render_field(self, field_config: Dict[str, Any], value: Any = None) -> str:
        """
        Render individual field HTML.
        
        Args:
            field_config: Field configuration
            value: Current field value
        
        Returns:
            Rendered field HTML
        """
        field_type = field_config.get('type', 'text')
        template_name = f'tournaments/form_builder/fields/{field_type}.html'
        
        context = {
            'field': field_config,
            'value': value or field_config.get('default_value'),
            'errors': [],  # Will be populated during validation
        }
        
        try:
            return render_to_string(template_name, context)
        except Exception:
            # Fallback to text field if template doesn't exist
            return render_to_string('tournaments/form_builder/fields/text.html', context)
    
    def _get_sections_for_step(self, step: int) -> List[Dict]:
        """Get sections for a specific step"""
        if not self.form_config.enable_multi_step:
            return self.schema.get('sections', [])
        
        # Distribute sections across steps
        all_sections = self.schema.get('sections', [])
        sections_per_step = max(1, len(all_sections) // self._get_total_steps())
        
        start_idx = (step - 1) * sections_per_step
        end_idx = start_idx + sections_per_step if step < self._get_total_steps() else len(all_sections)
        
        return all_sections[start_idx:end_idx]
    
    def _get_total_steps(self) -> int:
        """Calculate total number of steps"""
        if not self.form_config.enable_multi_step:
            return 1
        
        # For now, use 3 steps by default (can be configured later)
        total_sections = len(self.schema.get('sections', []))
        return min(3, total_sections) if total_sections > 0 else 1
    
    def _is_field_hidden(self, field_id: str, response_data: Dict[str, Any]) -> bool:
        """Check if field should be hidden based on conditional logic"""
        conditional_rules = self.schema.get('conditional_rules', {})
        field_rules = conditional_rules.get(field_id, {})
        
        if not field_rules:
            return False
        
        # Use validator's conditional logic
        return self.validator._is_field_hidden(field_id, response_data)
    
    # ==================== VALIDATION ====================
    
    def validate_step(self, step: int, response_data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
        """
        Validate data for a specific step.
        
        Args:
            step: Step number
            response_data: User responses
        
        Returns:
            Tuple of (is_valid, errors_dict)
        """
        errors = {}
        
        # Get fields for this step
        sections = self._get_sections_for_step(step)
        
        for section in sections:
            for field in section.get('fields', []):
                field_id = field.get('id')
                
                # Skip hidden fields
                if self._is_field_hidden(field_id, response_data):
                    continue
                
                # Validate field
                validator = FormFieldValidator(field)
                value = response_data.get(field_id)
                is_valid, error_msg = validator.validate(value)
                
                if not is_valid:
                    errors[field_id] = error_msg
        
        return len(errors) == 0, errors
    
    def validate_complete_form(self, response_data: Dict[str, Any]) -> Tuple[bool, Dict[str, str]]:
        """
        Validate complete form submission.
        
        Args:
            response_data: Complete form responses
        
        Returns:
            Tuple of (is_valid, errors_dict)
        """
        return self.validator.validate_submission(response_data)
    
    # ==================== RESPONSE MANAGEMENT ====================
    
    @transaction.atomic
    def save_response(
        self,
        user,
        response_data: Dict[str, Any],
        status: str = 'submitted',
        team=None,
        **metadata
    ) -> FormResponse:
        """
        Save form response to database.
        
        Args:
            user: User submitting the form
            response_data: Form responses
            status: Response status (draft, submitted, etc.)
            team: Team (for team tournaments)
            **metadata: Additional metadata (IP, user agent, etc.)
        
        Returns:
            FormResponse instance
        """
        # Get or create response
        response, created = FormResponse.objects.get_or_create(
            tournament=self.tournament,
            user=user,
            defaults={
                'registration_form': self.form_config,
                'response_data': response_data,
                'status': status,
                'team': team,
            }
        )
        
        # Update if exists
        if not created:
            response.response_data = response_data
            response.status = status
            response.updated_at = timezone.now()
        
        # Add metadata
        if metadata.get('ip_address'):
            response.ip_address = metadata['ip_address']
        if metadata.get('user_agent'):
            response.user_agent = metadata['user_agent']
        if metadata.get('submission_duration'):
            response.submission_duration = metadata['submission_duration']
        
        # Mark as submitted if status is submitted
        if status == 'submitted' and not response.submitted_at:
            response.submitted_at = timezone.now()
            
            # Increment completion analytics
            self.form_config.increment_completions()
        
        response.save()
        
        return response
    
    def save_draft(self, user, response_data: Dict[str, Any]) -> FormResponse:
        """
        Save draft response.
        
        Args:
            user: User
            response_data: Partial form responses
        
        Returns:
            FormResponse instance
        """
        return self.save_response(user, response_data, status='draft')
    
    def get_response(self, user) -> Optional[FormResponse]:
        """
        Get existing response for user.
        
        Args:
            user: User
        
        Returns:
            FormResponse or None
        """
        try:
            return FormResponse.objects.get(
                tournament=self.tournament,
                user=user
            )
        except FormResponse.DoesNotExist:
            return None
    
    # ==================== ANALYTICS ====================
    
    def track_view(self):
        """Track form view"""
        self.form_config.increment_views()
    
    def track_start(self):
        """Track form start (user interacted)"""
        self.form_config.increment_starts()
    
    def get_analytics(self) -> Dict[str, Any]:
        """
        Get form analytics.
        
        Returns:
            Dict with analytics data
        """
        return {
            'total_views': self.form_config.total_views,
            'total_starts': self.form_config.total_starts,
            'total_completions': self.form_config.total_completions,
            'completion_rate': self.form_config.completion_rate,
            'abandonment_rate': self.form_config.abandonment_rate,
        }
    
    # ==================== SCHEMA UTILITIES ====================
    
    def get_all_fields(self) -> List[Dict[str, Any]]:
        """Get all fields from schema"""
        fields = []
        for section in self.schema.get('sections', []):
            fields.extend(section.get('fields', []))
        return fields
    
    def get_field_by_id(self, field_id: str) -> Optional[Dict[str, Any]]:
        """Get field configuration by ID"""
        for field in self.get_all_fields():
            if field.get('id') == field_id:
                return field
        return None
    
    def get_required_fields(self) -> List[str]:
        """Get list of required field IDs"""
        return [
            field['id']
            for field in self.get_all_fields()
            if field.get('required', False) and field.get('enabled', True)
        ]
    
    def update_schema(self, new_schema: Dict[str, Any]):
        """
        Update form schema.
        
        Args:
            new_schema: New schema configuration
        """
        self.form_config.form_schema = new_schema
        self.form_config.save(update_fields=['form_schema', 'updated_at'])
        
        # Reload
        self.schema = new_schema
        self.validator = FormValidator(new_schema)


class FormTemplateService:
    """Service for managing form templates"""
    
    @staticmethod
    def create_from_template(tournament: Tournament, template_slug: str) -> TournamentRegistrationForm:
        """
        Create tournament form from template.
        
        Args:
            tournament: Tournament instance
            template_slug: Template slug
        
        Returns:
            TournamentRegistrationForm instance
        """
        from apps.tournaments.models import RegistrationFormTemplate
        
        try:
            template = RegistrationFormTemplate.objects.get(slug=template_slug)
        except RegistrationFormTemplate.DoesNotExist:
            raise ValueError(f"Template '{template_slug}' not found")
        
        # Create form from template
        form = TournamentRegistrationForm.objects.create(
            tournament=tournament,
            based_on_template=template,
            form_schema=template.form_schema.copy(),
        )
        
        # Increment template usage
        template.increment_usage()
        
        return form
    
    @staticmethod
    def get_recommended_templates(tournament: Tournament) -> List:
        """
        Get recommended templates for tournament.
        
        Args:
            tournament: Tournament instance
        
        Returns:
            List of RegistrationFormTemplate instances
        """
        from apps.tournaments.models import RegistrationFormTemplate
        
        # Filter by game and participation type
        templates = RegistrationFormTemplate.objects.filter(
            is_active=True,
            participation_type=tournament.participation_type
        )
        
        if tournament.game:
            # Prioritize game-specific templates
            templates = templates.filter(
                Q(game=tournament.game) | Q(game__isnull=True)
            ).order_by(
                '-game',  # Game-specific first
                '-is_featured',
                '-usage_count'
            )
        else:
            templates = templates.filter(
                game__isnull=True
            ).order_by('-is_featured', '-usage_count')
        
        return list(templates[:10])  # Top 10


# Utility function for quick access
def get_form_service(tournament: Tournament) -> FormRenderService:
    """
    Get FormRenderService instance for tournament.
    
    Args:
        tournament: Tournament instance
    
    Returns:
        FormRenderService instance
    """
    return FormRenderService(tournament)
