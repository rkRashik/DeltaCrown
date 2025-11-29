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
        
        # If schema is empty (newly created or existing), generate from configuration
        if not self.form_config.form_schema.get('sections'):
            self.form_config.form_schema = self._generate_schema_from_configuration()
            self.form_config.save(update_fields=['form_schema'])
        
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
    
    def _generate_schema_from_configuration(self) -> Dict[str, Any]:
        """
        Generate form schema from TournamentFormConfiguration.
        
        Creates a proper form schema with sections and fields based on
        the tournament's form configuration settings.
        """
        from apps.tournaments.models.form_configuration import TournamentFormConfiguration
        
        # Get form configuration
        form_config = TournamentFormConfiguration.get_or_create_for_tournament(self.tournament)
        
        sections = []
        
        if self.tournament.participation_type == 'solo':
            sections = self._generate_solo_registration_schema(form_config)
        elif self.tournament.participation_type == 'team':
            sections = self._generate_team_registration_schema(form_config)
        else:
            # Default/fallback
            sections = self._generate_solo_registration_schema(form_config)
        
        return {
            'version': '2.0',
            'form_id': f'{self.tournament.slug}_registration',
            'form_name': f'{self.tournament.name} Registration',
            'settings': {
                'theme': 'dark',
                'primary_color': '#FF4655',
                'show_section_numbers': True,
            },
            'sections': sections
        }
    
    def _generate_solo_registration_schema(self, form_config) -> List[Dict]:
        """Generate form sections for solo registration"""
        sections = []
        
        # Section 1: Player Information
        player_fields = [
            {
                'id': 'player_name',
                'type': 'text',
                'label': 'Full Name',
                'required': True,
                'placeholder': 'Enter your full name',
                'help_text': 'Your real name as it appears on official documents'
            }
        ]
        
        # Add optional fields based on configuration
        if form_config.enable_age_field:
            player_fields.append({
                'id': 'age',
                'type': 'number',
                'label': 'Age',
                'required': False,
                'min': 13,
                'max': 100,
                'help_text': 'You must be 13+ to participate'
            })
        
        if form_config.enable_country_field:
            player_fields.append({
                'id': 'country',
                'type': 'select',
                'label': 'Country',
                'required': False,
                'options': [
                    {'value': 'BD', 'label': 'Bangladesh'},
                    {'value': 'IN', 'label': 'India'},
                    {'value': 'PK', 'label': 'Pakistan'},
                    {'value': 'LK', 'label': 'Sri Lanka'},
                    {'value': 'NP', 'label': 'Nepal'},
                    {'value': 'US', 'label': 'United States'},
                    {'value': 'GB', 'label': 'United Kingdom'},
                    {'value': 'CA', 'label': 'Canada'},
                    {'value': 'AU', 'label': 'Australia'},
                    {'value': 'other', 'label': 'Other'}
                ]
            })
        
        sections.append({
            'id': 'player_info',
            'title': 'Player Information',
            'description': 'Basic information about you',
            'fields': player_fields
        })
        
        # Section 2: Game Details
        game_fields = []
        
        if form_config.enable_platform_field:
            game_fields.append({
                'id': 'platform',
                'type': 'select',
                'label': 'Platform/Server',
                'required': False,
                'options': [
                    {'value': 'pc', 'label': 'PC'},
                    {'value': 'mobile', 'label': 'Mobile'},
                    {'value': 'ps5', 'label': 'PlayStation 5'},
                    {'value': 'xbox', 'label': 'Xbox Series X/S'}
                ]
            })
        
        if form_config.enable_rank_field:
            game_fields.append({
                'id': 'rank',
                'type': 'text',
                'label': 'Current Rank',
                'required': False,
                'placeholder': 'e.g., Gold III, Immortal 2'
            })
        
        if game_fields:
            sections.append({
                'id': 'game_details',
                'title': 'Game Details',
                'description': 'Your gaming information',
                'fields': game_fields
            })
        
        # Section 3: Contact Information
        contact_fields = []
        
        if form_config.enable_phone_field:
            contact_fields.append({
                'id': 'phone',
                'type': 'tel',
                'label': 'Phone/WhatsApp',
                'required': False,
                'placeholder': '+880 1XX XXX XXXX'
            })
        
        if form_config.enable_discord_field:
            contact_fields.append({
                'id': 'discord',
                'type': 'text',
                'label': 'Discord Username',
                'required': False,
                'placeholder': 'username#1234'
            })
        
        if form_config.enable_preferred_contact_field:
            contact_fields.append({
                'id': 'preferred_contact',
                'type': 'select',
                'label': 'Preferred Contact Method',
                'required': False,
                'options': [
                    {'value': 'whatsapp', 'label': 'WhatsApp'},
                    {'value': 'discord', 'label': 'Discord'},
                    {'value': 'email', 'label': 'Email'}
                ]
            })
        
        if contact_fields:
            sections.append({
                'id': 'contact_info',
                'title': 'Contact Information',
                'description': 'How we can reach you during the tournament',
                'fields': contact_fields
            })
        
        # Section 4: Payment (if tournament has entry fee)
        if self.tournament.has_entry_fee and self.tournament.entry_fee_amount > 0:
            payment_fields = []
            
            if form_config.enable_payment_mobile_number_field:
                payment_fields.append({
                    'id': 'payment_mobile',
                    'type': 'tel',
                    'label': 'Payment Mobile Number',
                    'required': True,
                    'placeholder': '+880 1XX XXX XXXX',
                    'help_text': 'Mobile number used for payment'
                })
            
            if form_config.enable_payment_screenshot_field:
                payment_fields.append({
                    'id': 'payment_screenshot',
                    'type': 'file',
                    'label': 'Payment Screenshot',
                    'required': True,
                    'accept': 'image/*',
                    'help_text': 'Upload a screenshot of your payment'
                })
            
            if form_config.enable_payment_notes_field:
                payment_fields.append({
                    'id': 'payment_notes',
                    'type': 'textarea',
                    'label': 'Payment Notes',
                    'required': False,
                    'placeholder': 'Any additional payment information'
                })
            
            if payment_fields:
                sections.append({
                    'id': 'payment',
                    'title': 'Payment Information',
                    'description': f'Entry fee: {self.tournament.entry_fee_amount} {self.tournament.entry_fee_currency}',
                    'fields': payment_fields
                })
        
        return sections
    
    def _generate_team_registration_schema(self, form_config) -> List[Dict]:
        """Generate form sections for team registration"""
        # For now, return basic team schema
        # This would be expanded with team-specific fields
        sections = [
            {
                'id': 'team_info',
                'title': 'Team Information',
                'description': 'Information about your team',
                'fields': [
                    {
                        'id': 'team_name',
                        'type': 'text',
                        'label': 'Team Name',
                        'required': True,
                        'placeholder': 'Enter your team name'
                    }
                ]
            }
        ]
        
        return sections
    
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
