"""
Form Analytics Service

Comprehensive analytics for registration forms including conversion funnels,
abandonment analysis, field-level metrics, and time-based insights.
"""
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField, FloatField
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta
from typing import Dict, List, Optional
from apps.tournaments.models import FormResponse, TournamentRegistrationForm


class FormAnalyticsService:
    """
    Comprehensive analytics service for registration forms.
    
    Provides insights into:
    - Conversion funnels
    - Abandonment analysis
    - Field-level completion rates
    - Time-based metrics
    - User journey analysis
    """
    
    def __init__(self, tournament_form_id: int):
        self.tournament_form = TournamentRegistrationForm.objects.select_related(
            'template', 'tournament'
        ).get(id=tournament_form_id)
        self.form_schema = self.tournament_form.template.form_schema
    
    def get_overview_metrics(self) -> Dict:
        """
        Get high-level overview metrics for the form.
        
        Returns:
            Dict with key performance indicators
        """
        responses = FormResponse.objects.filter(
            tournament_form=self.tournament_form
        )
        
        total_views = self.tournament_form.view_count
        total_starts = self.tournament_form.start_count
        total_submissions = responses.filter(status='submitted').count()
        total_drafts = responses.filter(status='draft').count()
        total_approved = responses.filter(status='approved').count()
        total_rejected = responses.filter(status='rejected').count()
        
        # Calculate rates
        start_rate = (total_starts / total_views * 100) if total_views > 0 else 0
        completion_rate = (total_submissions / total_starts * 100) if total_starts > 0 else 0
        approval_rate = (total_approved / total_submissions * 100) if total_submissions > 0 else 0
        abandonment_rate = 100 - completion_rate if total_starts > 0 else 0
        
        # Calculate average completion time
        avg_completion_time = responses.filter(
            status='submitted',
            submitted_at__isnull=False
        ).annotate(
            completion_duration=ExpressionWrapper(
                F('submitted_at') - F('created_at'),
                output_field=DurationField()
            )
        ).aggregate(
            avg_duration=Avg('completion_duration')
        )['avg_duration']
        
        # Convert timedelta to minutes
        avg_minutes = None
        if avg_completion_time:
            avg_minutes = round(avg_completion_time.total_seconds() / 60, 2)
        
        return {
            'total_views': total_views,
            'total_starts': total_starts,
            'total_submissions': total_submissions,
            'total_drafts': total_drafts,
            'total_approved': total_approved,
            'total_rejected': total_rejected,
            'start_rate': round(start_rate, 2),
            'completion_rate': round(completion_rate, 2),
            'abandonment_rate': round(abandonment_rate, 2),
            'approval_rate': round(approval_rate, 2),
            'avg_completion_time_minutes': avg_minutes,
        }
    
    def get_conversion_funnel(self) -> List[Dict]:
        """
        Get conversion funnel data showing drop-off at each stage.
        
        Returns:
            List of funnel stages with counts and conversion rates
        """
        metrics = self.get_overview_metrics()
        
        total_views = metrics['total_views']
        total_starts = metrics['total_starts']
        total_submissions = metrics['total_submissions']
        total_approved = metrics['total_approved']
        
        funnel = [
            {
                'stage': 'Views',
                'count': total_views,
                'percentage': 100.0,
                'drop_off': 0,
                'description': 'Users who viewed the registration page'
            },
            {
                'stage': 'Starts',
                'count': total_starts,
                'percentage': round((total_starts / total_views * 100) if total_views > 0 else 0, 2),
                'drop_off': total_views - total_starts,
                'description': 'Users who started filling the form'
            },
            {
                'stage': 'Submissions',
                'count': total_submissions,
                'percentage': round((total_submissions / total_views * 100) if total_views > 0 else 0, 2),
                'drop_off': total_starts - total_submissions,
                'description': 'Users who submitted the form'
            },
            {
                'stage': 'Approved',
                'count': total_approved,
                'percentage': round((total_approved / total_views * 100) if total_views > 0 else 0, 2),
                'drop_off': total_submissions - total_approved,
                'description': 'Registrations that were approved'
            },
        ]
        
        return funnel
    
    def get_field_analytics(self) -> List[Dict]:
        """
        Get field-level analytics showing completion rates and errors.
        
        Returns:
            List of fields with their analytics
        """
        responses = FormResponse.objects.filter(
            tournament_form=self.tournament_form,
            status__in=['submitted', 'approved']
        )
        
        total_responses = responses.count()
        if total_responses == 0:
            return []
        
        field_analytics = []
        
        # Extract all fields from form schema
        for section in self.form_schema.get('sections', []):
            for field in section.get('fields', []):
                field_id = field.get('id')
                field_name = field.get('label', field_id)
                field_type = field.get('type')
                is_required = field.get('required', False)
                
                # Count how many responses have this field filled
                filled_count = 0
                for response in responses:
                    value = response.response_data.get(field_id)
                    if value is not None and value != '' and value != []:
                        filled_count += 1
                
                completion_rate = (filled_count / total_responses * 100)
                
                field_analytics.append({
                    'field_id': field_id,
                    'field_name': field_name,
                    'field_type': field_type,
                    'is_required': is_required,
                    'filled_count': filled_count,
                    'completion_rate': round(completion_rate, 2),
                    'missing_count': total_responses - filled_count,
                })
        
        # Sort by completion rate (lowest first to identify problem fields)
        field_analytics.sort(key=lambda x: x['completion_rate'])
        
        return field_analytics
    
    def get_time_series_data(self, days: int = 30, interval: str = 'day') -> List[Dict]:
        """
        Get time-series data for submissions over time.
        
        Args:
            days: Number of days to analyze
            interval: 'day' or 'hour'
        
        Returns:
            List of time buckets with submission counts
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        responses = FormResponse.objects.filter(
            tournament_form=self.tournament_form,
            created_at__gte=cutoff_date
        )
        
        if interval == 'hour':
            trunc_func = TruncHour
        else:
            trunc_func = TruncDate
        
        time_series = responses.annotate(
            time_bucket=trunc_func('created_at')
        ).values('time_bucket').annotate(
            total_count=Count('id'),
            draft_count=Count(Case(When(status='draft', then=1))),
            submitted_count=Count(Case(When(status='submitted', then=1))),
            approved_count=Count(Case(When(status='approved', then=1))),
        ).order_by('time_bucket')
        
        return list(time_series)
    
    def get_abandonment_analysis(self) -> Dict:
        """
        Analyze where users are abandoning the form.
        
        Returns:
            Analysis of abandonment patterns
        """
        draft_responses = FormResponse.objects.filter(
            tournament_form=self.tournament_form,
            status='draft'
        )
        
        total_drafts = draft_responses.count()
        if total_drafts == 0:
            return {
                'total_abandoned': 0,
                'abandonment_points': [],
                'most_common_exit_field': None,
            }
        
        # Analyze which fields were last filled before abandonment
        field_abandonment = {}
        
        for draft in draft_responses:
            response_data = draft.response_data
            
            # Find the last filled field
            last_field = None
            for section in self.form_schema.get('sections', []):
                for field in section.get('fields', []):
                    field_id = field.get('id')
                    if response_data.get(field_id):
                        last_field = {
                            'id': field_id,
                            'label': field.get('label', field_id)
                        }
            
            if last_field:
                field_id = last_field['id']
                if field_id not in field_abandonment:
                    field_abandonment[field_id] = {
                        'field_label': last_field['label'],
                        'count': 0
                    }
                field_abandonment[field_id]['count'] += 1
        
        # Sort by count
        abandonment_points = sorted(
            [
                {
                    'field_id': k,
                    'field_label': v['field_label'],
                    'abandonment_count': v['count'],
                    'percentage': round((v['count'] / total_drafts * 100), 2)
                }
                for k, v in field_abandonment.items()
            ],
            key=lambda x: x['abandonment_count'],
            reverse=True
        )
        
        most_common_exit = abandonment_points[0] if abandonment_points else None
        
        return {
            'total_abandoned': total_drafts,
            'abandonment_points': abandonment_points,
            'most_common_exit_field': most_common_exit,
        }
    
    def get_step_analytics(self) -> List[Dict]:
        """
        Get analytics for multi-step forms showing drop-off per step.
        
        Returns:
            List of steps with completion metrics
        """
        if not self.tournament_form.is_multi_step:
            return []
        
        total_steps = len(self.form_schema.get('sections', []))
        
        responses = FormResponse.objects.filter(
            tournament_form=self.tournament_form
        )
        
        step_analytics = []
        
        for step_num in range(1, total_steps + 1):
            # Count responses that reached this step
            reached_count = 0
            completed_count = 0
            
            for response in responses:
                # Check if response has fields from this step filled
                section = self.form_schema['sections'][step_num - 1]
                section_fields = [f['id'] for f in section.get('fields', [])]
                
                has_any_field = any(
                    response.response_data.get(field_id)
                    for field_id in section_fields
                )
                
                if has_any_field:
                    reached_count += 1
                
                # Check if all required fields are filled
                required_fields = [
                    f['id'] for f in section.get('fields', [])
                    if f.get('required', False)
                ]
                
                all_required_filled = all(
                    response.response_data.get(field_id)
                    for field_id in required_fields
                )
                
                if all_required_filled:
                    completed_count += 1
            
            step_analytics.append({
                'step_number': step_num,
                'step_name': self.form_schema['sections'][step_num - 1].get('title', f'Step {step_num}'),
                'reached_count': reached_count,
                'completed_count': completed_count,
                'drop_off_count': reached_count - completed_count,
                'completion_rate': round((completed_count / reached_count * 100) if reached_count > 0 else 0, 2),
            })
        
        return step_analytics
    
    def get_device_analytics(self) -> Dict:
        """
        Get analytics by device type (desktop vs mobile).
        
        Note: Requires user_agent tracking in FormResponse metadata
        
        Returns:
            Breakdown by device type
        """
        responses = FormResponse.objects.filter(
            tournament_form=self.tournament_form
        )
        
        device_breakdown = {
            'desktop': 0,
            'mobile': 0,
            'tablet': 0,
            'unknown': 0,
        }
        
        for response in responses:
            device_type = response.metadata.get('device_type', 'unknown')
            if device_type in device_breakdown:
                device_breakdown[device_type] += 1
            else:
                device_breakdown['unknown'] += 1
        
        total = sum(device_breakdown.values())
        
        return {
            'breakdown': device_breakdown,
            'percentages': {
                device: round((count / total * 100) if total > 0 else 0, 2)
                for device, count in device_breakdown.items()
            }
        }
    
    def export_analytics_report(self) -> Dict:
        """
        Generate comprehensive analytics report for export.
        
        Returns:
            Complete analytics data bundle
        """
        return {
            'tournament': {
                'id': self.tournament_form.tournament.id,
                'name': self.tournament_form.tournament.name,
                'slug': self.tournament_form.tournament.slug,
            },
            'template': {
                'id': self.tournament_form.template.id,
                'name': self.tournament_form.template.name,
            },
            'generated_at': timezone.now().isoformat(),
            'overview': self.get_overview_metrics(),
            'conversion_funnel': self.get_conversion_funnel(),
            'field_analytics': self.get_field_analytics(),
            'abandonment_analysis': self.get_abandonment_analysis(),
            'step_analytics': self.get_step_analytics(),
            'time_series': self.get_time_series_data(days=30),
            'device_analytics': self.get_device_analytics(),
        }
