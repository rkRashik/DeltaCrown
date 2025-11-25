"""
Registration UX Enhancement Service

Auto-save drafts, progress tracking, validation feedback.
Improves user experience during registration.
"""
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
from django.core.cache import cache
from django.utils import timezone
from apps.tournaments.models import FormResponse, TournamentRegistrationForm


class RegistrationDraftService:
    """
    Service for auto-saving registration drafts.
    
    Features:
    - Auto-save to cache every N seconds
    - Periodic persistence to database
    - Draft recovery
    - Progress tracking
    """
    
    CACHE_PREFIX = 'registration_draft'
    CACHE_TTL = 3600  # 1 hour
    
    @staticmethod
    def get_cache_key(user_id: int, form_id: int) -> str:
        """Generate cache key for draft"""
        return f"{RegistrationDraftService.CACHE_PREFIX}:{user_id}:{form_id}"
    
    @staticmethod
    def save_draft(
        user_id: int,
        tournament_form_id: int,
        form_data: Dict,
        persist_to_db: bool = False,
    ) -> Dict:
        """
        Save registration draft to cache (and optionally DB).
        
        Returns draft info including progress percentage.
        """
        cache_key = RegistrationDraftService.get_cache_key(user_id, tournament_form_id)
        
        # Calculate progress
        tournament_form = TournamentRegistrationForm.objects.get(id=tournament_form_id)
        progress = RegistrationProgressService.calculate_progress(
            tournament_form,
            form_data
        )
        
        # Prepare draft data
        draft_data = {
            'form_data': form_data,
            'progress': progress,
            'saved_at': datetime.now().isoformat(),
        }
        
        # Save to cache
        cache.set(cache_key, draft_data, RegistrationDraftService.CACHE_TTL)
        
        # Optionally persist to database
        if persist_to_db:
            response, created = FormResponse.objects.get_or_create(
                tournament_form_id=tournament_form_id,
                user_id=user_id,
                status='draft',
                defaults={'response_data': form_data}
            )
            
            if not created:
                response.response_data = form_data
                response.save()
        
        return draft_data
    
    @staticmethod
    def get_draft(user_id: int, tournament_form_id: int) -> Optional[Dict]:
        """Retrieve draft from cache or DB"""
        cache_key = RegistrationDraftService.get_cache_key(user_id, tournament_form_id)
        
        # Try cache first
        draft = cache.get(cache_key)
        if draft:
            return draft
        
        # Fall back to database
        try:
            response = FormResponse.objects.get(
                tournament_form_id=tournament_form_id,
                user_id=user_id,
                status='draft'
            )
            
            tournament_form = TournamentRegistrationForm.objects.get(id=tournament_form_id)
            progress = RegistrationProgressService.calculate_progress(
                tournament_form,
                response.response_data
            )
            
            draft_data = {
                'form_data': response.response_data,
                'progress': progress,
                'saved_at': response.updated_at.isoformat(),
            }
            
            # Restore to cache
            cache.set(cache_key, draft_data, RegistrationDraftService.CACHE_TTL)
            
            return draft_data
            
        except FormResponse.DoesNotExist:
            return None
    
    @staticmethod
    def clear_draft(user_id: int, tournament_form_id: int):
        """Clear draft from cache (call after successful submission)"""
        cache_key = RegistrationDraftService.get_cache_key(user_id, tournament_form_id)
        cache.delete(cache_key)


class RegistrationProgressService:
    """
    Calculate registration completion progress.
    
    Tracks which fields are filled and calculates percentage.
    """
    
    @staticmethod
    def calculate_progress(
        tournament_form: TournamentRegistrationForm,
        form_data: Dict,
    ) -> Dict:
        """
        Calculate registration progress.
        
        Returns:
            {
                'percentage': 75,
                'completed_fields': 15,
                'total_fields': 20,
                'required_completed': 8,
                'required_total': 10,
                'sections': [...]
            }
        """
        form_schema = tournament_form.template.form_schema
        
        total_fields = 0
        completed_fields = 0
        required_total = 0
        required_completed = 0
        sections_progress = []
        
        for section in form_schema.get('sections', []):
            section_total = 0
            section_completed = 0
            section_required_total = 0
            section_required_completed = 0
            
            for field in section.get('fields', []):
                # Skip non-data fields
                if field.get('type') in ['section_header', 'divider']:
                    continue
                
                field_id = field.get('id')
                is_required = field.get('required', False)
                
                total_fields += 1
                section_total += 1
                
                if is_required:
                    required_total += 1
                    section_required_total += 1
                
                # Check if field is filled
                value = form_data.get(field_id)
                is_filled = False
                
                if value is not None:
                    if isinstance(value, str):
                        is_filled = len(value.strip()) > 0
                    elif isinstance(value, list):
                        is_filled = len(value) > 0
                    elif isinstance(value, dict):
                        is_filled = bool(value)
                    else:
                        is_filled = True
                
                if is_filled:
                    completed_fields += 1
                    section_completed += 1
                    
                    if is_required:
                        required_completed += 1
                        section_required_completed += 1
            
            # Calculate section percentage
            section_percentage = (
                int((section_completed / section_total) * 100)
                if section_total > 0 else 0
            )
            
            sections_progress.append({
                'title': section.get('title', 'Untitled Section'),
                'percentage': section_percentage,
                'completed': section_completed,
                'total': section_total,
                'required_completed': section_required_completed,
                'required_total': section_required_total,
            })
        
        # Calculate overall percentage
        overall_percentage = (
            int((completed_fields / total_fields) * 100)
            if total_fields > 0 else 0
        )
        
        return {
            'percentage': overall_percentage,
            'completed_fields': completed_fields,
            'total_fields': total_fields,
            'required_completed': required_completed,
            'required_total': required_total,
            'sections': sections_progress,
            'is_ready_to_submit': required_completed == required_total,
        }
    
    @staticmethod
    def get_next_incomplete_section(
        tournament_form: TournamentRegistrationForm,
        form_data: Dict,
    ) -> Optional[str]:
        """
        Find the first incomplete section.
        
        Returns section title or None if all complete.
        """
        progress = RegistrationProgressService.calculate_progress(
            tournament_form,
            form_data
        )
        
        for section in progress['sections']:
            if section['percentage'] < 100:
                return section['title']
        
        return None


class FieldValidationService:
    """
    Real-time field validation with user-friendly feedback.
    
    Provides instant validation as user fills out form.
    """
    
    @staticmethod
    def validate_field(
        field_config: Dict,
        value: any,
    ) -> Dict:
        """
        Validate a single field value.
        
        Returns:
            {
                'valid': True/False,
                'errors': [...],
                'warnings': [...],
                'suggestions': [...]
            }
        """
        field_type = field_config.get('type')
        is_required = field_config.get('required', False)
        validation = field_config.get('validation', {})
        
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': [],
        }
        
        # Check required
        if is_required:
            if value is None or (isinstance(value, str) and len(value.strip()) == 0):
                result['valid'] = False
                result['errors'].append(f"{field_config.get('label', 'This field')} is required")
                return result
        
        # Skip validation if empty and not required
        if value is None or (isinstance(value, str) and len(value.strip()) == 0):
            return result
        
        # Type-specific validation
        if field_type == 'email':
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, value):
                result['valid'] = False
                result['errors'].append('Please enter a valid email address')
        
        elif field_type == 'number':
            try:
                num_value = float(value)
                
                if 'min' in validation and num_value < validation['min']:
                    result['valid'] = False
                    result['errors'].append(f"Value must be at least {validation['min']}")
                
                if 'max' in validation and num_value > validation['max']:
                    result['valid'] = False
                    result['errors'].append(f"Value must be at most {validation['max']}")
                
            except (ValueError, TypeError):
                result['valid'] = False
                result['errors'].append('Please enter a valid number')
        
        elif field_type == 'tel':
            # Basic phone validation
            import re
            phone_pattern = r'^[\d\s\-\+\(\)]+$'
            if not re.match(phone_pattern, value):
                result['valid'] = False
                result['errors'].append('Please enter a valid phone number')
            elif len(value.replace(' ', '').replace('-', '')) < 10:
                result['warnings'].append('Phone number seems short')
        
        elif field_type in ['text', 'textarea']:
            if 'min_length' in validation and len(value) < validation['min_length']:
                result['valid'] = False
                result['errors'].append(f"Must be at least {validation['min_length']} characters")
            
            if 'max_length' in validation and len(value) > validation['max_length']:
                result['valid'] = False
                result['errors'].append(f"Must be at most {validation['max_length']} characters")
            
            if 'pattern' in validation:
                import re
                if not re.match(validation['pattern'], value):
                    result['valid'] = False
                    result['errors'].append(validation.get('pattern_message', 'Invalid format'))
        
        elif field_type == 'url':
            import re
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            if not re.match(url_pattern, value):
                result['valid'] = False
                result['errors'].append('Please enter a valid URL starting with http:// or https://')
        
        elif field_type == 'date':
            try:
                from datetime import datetime
                date_value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                
                if 'min_date' in validation:
                    min_date = datetime.fromisoformat(validation['min_date'])
                    if date_value < min_date:
                        result['valid'] = False
                        result['errors'].append(f"Date must be after {min_date.strftime('%Y-%m-%d')}")
                
                if 'max_date' in validation:
                    max_date = datetime.fromisoformat(validation['max_date'])
                    if date_value > max_date:
                        result['valid'] = False
                        result['errors'].append(f"Date must be before {max_date.strftime('%Y-%m-%d')}")
                
            except (ValueError, TypeError):
                result['valid'] = False
                result['errors'].append('Please enter a valid date')
        
        return result
