"""
Bulk Response Operations Service

Bulk actions for managing multiple form responses at once.
Includes approval, rejection, deletion, and email notifications.
"""
from typing import List, Dict
from django.db.models import QuerySet
from django.core.mail import send_mass_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from apps.tournaments.models import FormResponse, TournamentRegistrationForm


class BulkResponseService:
    """
    Service for performing bulk operations on form responses.
    
    Supports:
    - Bulk approve/reject
    - Bulk delete
    - Bulk email notifications
    - Bulk payment verification
    - Bulk status updates
    """
    
    def __init__(self, tournament_form: TournamentRegistrationForm):
        self.tournament_form = tournament_form
        self.tournament = tournament_form.tournament
    
    def bulk_approve(
        self,
        response_ids: List[int],
        send_email: bool = True,
        custom_message: str = None,
    ) -> Dict:
        """
        Approve multiple responses at once.
        
        Returns:
            Dict with 'approved' count and 'failed' list
        """
        responses = FormResponse.objects.filter(
            id__in=response_ids,
            tournament_form=self.tournament_form,
            status__in=['submitted', 'draft']
        )
        
        approved_count = 0
        failed = []
        email_messages = []
        
        for response in responses:
            try:
                response.status = 'approved'
                response.save()
                approved_count += 1
                
                # Prepare email if needed
                if send_email and response.user and response.user.email:
                    subject = f"Registration Approved - {self.tournament.name}"
                    
                    context = {
                        'tournament': self.tournament,
                        'response': response,
                        'custom_message': custom_message,
                    }
                    
                    html_message = render_to_string(
                        'tournaments/emails/registration_approved.html',
                        context
                    )
                    plain_message = strip_tags(html_message)
                    
                    email_messages.append((
                        subject,
                        plain_message,
                        'noreply@deltacrown.com',
                        [response.user.email]
                    ))
                
            except Exception as e:
                failed.append({
                    'id': response.id,
                    'error': str(e)
                })
        
        # Send bulk emails
        if email_messages:
            send_mass_mail(email_messages, fail_silently=True)
        
        return {
            'approved': approved_count,
            'failed': failed,
            'emails_sent': len(email_messages),
        }
    
    def bulk_reject(
        self,
        response_ids: List[int],
        reason: str = None,
        send_email: bool = True,
    ) -> Dict:
        """
        Reject multiple responses at once.
        
        Returns:
            Dict with 'rejected' count and 'failed' list
        """
        responses = FormResponse.objects.filter(
            id__in=response_ids,
            tournament_form=self.tournament_form,
            status__in=['submitted', 'draft', 'approved']
        )
        
        rejected_count = 0
        failed = []
        email_messages = []
        
        for response in responses:
            try:
                response.status = 'rejected'
                
                # Store rejection reason in metadata
                if reason:
                    if not response.metadata:
                        response.metadata = {}
                    response.metadata['rejection_reason'] = reason
                
                response.save()
                rejected_count += 1
                
                # Prepare email if needed
                if send_email and response.user and response.user.email:
                    subject = f"Registration Update - {self.tournament.name}"
                    
                    context = {
                        'tournament': self.tournament,
                        'response': response,
                        'reason': reason,
                    }
                    
                    html_message = render_to_string(
                        'tournaments/emails/registration_rejected.html',
                        context
                    )
                    plain_message = strip_tags(html_message)
                    
                    email_messages.append((
                        subject,
                        plain_message,
                        'noreply@deltacrown.com',
                        [response.user.email]
                    ))
                
            except Exception as e:
                failed.append({
                    'id': response.id,
                    'error': str(e)
                })
        
        # Send bulk emails
        if email_messages:
            send_mass_mail(email_messages, fail_silently=True)
        
        return {
            'rejected': rejected_count,
            'failed': failed,
            'emails_sent': len(email_messages),
        }
    
    def bulk_delete(self, response_ids: List[int]) -> Dict:
        """
        Delete multiple responses at once.
        
        Only deletes drafts to prevent data loss.
        """
        responses = FormResponse.objects.filter(
            id__in=response_ids,
            tournament_form=self.tournament_form,
            status='draft'
        )
        
        count = responses.count()
        responses.delete()
        
        return {
            'deleted': count,
        }
    
    def bulk_verify_payment(
        self,
        response_ids: List[int],
        verified: bool = True,
        send_email: bool = True,
    ) -> Dict:
        """
        Verify or unverify payment for multiple responses.
        """
        responses = FormResponse.objects.filter(
            id__in=response_ids,
            tournament_form=self.tournament_form,
            has_paid=True
        )
        
        verified_count = 0
        failed = []
        email_messages = []
        
        for response in responses:
            try:
                response.payment_verified = verified
                response.save()
                verified_count += 1
                
                # Prepare email if needed
                if send_email and verified and response.user and response.user.email:
                    subject = f"Payment Verified - {self.tournament.name}"
                    
                    context = {
                        'tournament': self.tournament,
                        'response': response,
                    }
                    
                    html_message = render_to_string(
                        'tournaments/emails/payment_verified.html',
                        context
                    )
                    plain_message = strip_tags(html_message)
                    
                    email_messages.append((
                        subject,
                        plain_message,
                        'noreply@deltacrown.com',
                        [response.user.email]
                    ))
                
            except Exception as e:
                failed.append({
                    'id': response.id,
                    'error': str(e)
                })
        
        # Send bulk emails
        if email_messages:
            send_mass_mail(email_messages, fail_silently=True)
        
        return {
            'verified': verified_count,
            'failed': failed,
            'emails_sent': len(email_messages),
        }
    
    def send_bulk_notification(
        self,
        response_ids: List[int],
        subject: str,
        message: str,
        status_filter: List[str] = None,
    ) -> Dict:
        """
        Send custom email notification to multiple participants.
        """
        queryset = FormResponse.objects.filter(
            id__in=response_ids,
            tournament_form=self.tournament_form,
            user__email__isnull=False
        )
        
        if status_filter:
            queryset = queryset.filter(status__in=status_filter)
        
        email_messages = []
        
        for response in queryset:
            if response.user and response.user.email:
                context = {
                    'tournament': self.tournament,
                    'response': response,
                    'custom_message': message,
                    'user': response.user,
                }
                
                html_message = render_to_string(
                    'tournaments/emails/custom_notification.html',
                    context
                )
                plain_message = strip_tags(html_message)
                
                email_messages.append((
                    subject,
                    plain_message,
                    'noreply@deltacrown.com',
                    [response.user.email]
                ))
        
        # Send emails
        if email_messages:
            send_mass_mail(email_messages, fail_silently=True)
        
        return {
            'emails_sent': len(email_messages),
        }
    
    def get_bulk_action_preview(
        self,
        response_ids: List[int],
        action: str,
    ) -> Dict:
        """
        Preview the impact of a bulk action before executing.
        
        Returns affected count and details.
        """
        base_queryset = FormResponse.objects.filter(
            id__in=response_ids,
            tournament_form=self.tournament_form
        )
        
        preview = {
            'total_selected': len(response_ids),
            'will_be_affected': 0,
            'will_be_skipped': 0,
            'status_breakdown': {},
            'warnings': [],
        }
        
        if action == 'approve':
            eligible = base_queryset.filter(status__in=['submitted', 'draft'])
            preview['will_be_affected'] = eligible.count()
            preview['will_be_skipped'] = base_queryset.count() - eligible.count()
            
            if preview['will_be_skipped'] > 0:
                preview['warnings'].append(
                    f"{preview['will_be_skipped']} responses cannot be approved (already approved or rejected)"
                )
        
        elif action == 'reject':
            eligible = base_queryset.filter(status__in=['submitted', 'draft', 'approved'])
            preview['will_be_affected'] = eligible.count()
            preview['will_be_skipped'] = base_queryset.count() - eligible.count()
        
        elif action == 'delete':
            eligible = base_queryset.filter(status='draft')
            preview['will_be_affected'] = eligible.count()
            preview['will_be_skipped'] = base_queryset.count() - eligible.count()
            
            if preview['will_be_skipped'] > 0:
                preview['warnings'].append(
                    f"{preview['will_be_skipped']} responses cannot be deleted (only drafts can be deleted)"
                )
        
        elif action == 'verify_payment':
            eligible = base_queryset.filter(has_paid=True)
            preview['will_be_affected'] = eligible.count()
            preview['will_be_skipped'] = base_queryset.count() - eligible.count()
            
            if preview['will_be_skipped'] > 0:
                preview['warnings'].append(
                    f"{preview['will_be_skipped']} responses cannot be verified (payment not marked as paid)"
                )
        
        # Status breakdown
        for response in base_queryset:
            status = response.get_status_display()
            preview['status_breakdown'][status] = preview['status_breakdown'].get(status, 0) + 1
        
        return preview
