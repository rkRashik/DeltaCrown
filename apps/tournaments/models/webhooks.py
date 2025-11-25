"""
Form Webhooks System

Webhook notifications for form events (submissions, approvals, payments).
Allows external systems to integrate with DeltaCrown tournaments.
"""
import json
import hmac
import hashlib
import requests
from typing import Dict, Optional, List
from datetime import datetime
from django.db import models
from django.utils import timezone
from apps.tournaments.models import TournamentRegistrationForm, FormResponse


class FormWebhook(models.Model):
    """
    Webhook configuration for tournament form events.
    
    Sends HTTP POST requests to external URLs when form events occur.
    """
    
    EVENT_CHOICES = [
        ('response.created', 'Response Created (Draft)'),
        ('response.submitted', 'Response Submitted'),
        ('response.approved', 'Response Approved'),
        ('response.rejected', 'Response Rejected'),
        ('payment.received', 'Payment Received'),
        ('payment.verified', 'Payment Verified'),
        ('form.opened', 'Form Opened'),
        ('form.closed', 'Form Closed'),
    ]
    
    tournament_form = models.ForeignKey(
        TournamentRegistrationForm,
        on_delete=models.CASCADE,
        related_name='webhooks'
    )
    
    url = models.URLField(
        help_text='External URL to send webhook POST requests'
    )
    
    secret = models.CharField(
        max_length=255,
        help_text='Secret key for HMAC signature verification',
        blank=True
    )
    
    events = models.JSONField(
        default=list,
        help_text='List of events to trigger this webhook'
    )
    
    is_active = models.BooleanField(default=True)
    
    custom_headers = models.JSONField(
        default=dict,
        blank=True,
        help_text='Custom HTTP headers to send with requests'
    )
    
    retry_count = models.IntegerField(
        default=3,
        help_text='Number of retry attempts for failed deliveries'
    )
    
    timeout = models.IntegerField(
        default=10,
        help_text='Request timeout in seconds'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tournaments_form_webhook'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Webhook: {self.url} ({len(self.events)} events)"
    
    def generate_signature(self, payload: str) -> str:
        """Generate HMAC signature for webhook payload"""
        if not self.secret:
            return ''
        
        return hmac.new(
            self.secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    def send(self, event: str, data: Dict) -> 'WebhookDelivery':
        """
        Send webhook with event data.
        
        Creates a WebhookDelivery record for tracking.
        """
        # Prepare payload
        payload = {
            'event': event,
            'timestamp': datetime.now().isoformat(),
            'data': data,
        }
        
        payload_json = json.dumps(payload)
        
        # Generate signature
        signature = self.generate_signature(payload_json)
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DeltaCrown-Webhooks/1.0',
            'X-Webhook-Event': event,
            'X-Webhook-Signature': signature,
        }
        
        # Add custom headers
        if self.custom_headers:
            headers.update(self.custom_headers)
        
        # Create delivery record
        delivery = WebhookDelivery.objects.create(
            webhook=self,
            event=event,
            payload=payload,
            status='pending'
        )
        
        # Send request
        attempt = 1
        while attempt <= self.retry_count:
            try:
                response = requests.post(
                    self.url,
                    data=payload_json,
                    headers=headers,
                    timeout=self.timeout
                )
                
                # Update delivery record
                delivery.status = 'success' if response.status_code < 400 else 'failed'
                delivery.status_code = response.status_code
                delivery.response_body = response.text[:1000]  # Truncate
                delivery.attempts = attempt
                delivery.delivered_at = timezone.now()
                delivery.save()
                
                if delivery.status == 'success':
                    break
                
            except requests.exceptions.RequestException as e:
                delivery.status = 'failed'
                delivery.error_message = str(e)[:500]
                delivery.attempts = attempt
                delivery.save()
            
            attempt += 1
        
        return delivery


class WebhookDelivery(models.Model):
    """
    Track individual webhook delivery attempts.
    
    Provides audit trail and debugging information.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ]
    
    webhook = models.ForeignKey(
        FormWebhook,
        on_delete=models.CASCADE,
        related_name='deliveries'
    )
    
    event = models.CharField(max_length=50)
    
    payload = models.JSONField()
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    status_code = models.IntegerField(null=True, blank=True)
    
    response_body = models.TextField(blank=True)
    
    error_message = models.TextField(blank=True)
    
    attempts = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    delivered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'tournaments_webhook_delivery'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event} - {self.status} ({self.created_at})"


class WebhookService:
    """
    Service for triggering webhooks based on form events.
    """
    
    @staticmethod
    def trigger_event(
        tournament_form: TournamentRegistrationForm,
        event: str,
        response: Optional[FormResponse] = None,
        extra_data: Optional[Dict] = None,
    ):
        """
        Trigger webhook for a specific event.
        
        Finds all active webhooks listening for this event and sends them.
        """
        # Get active webhooks for this event
        webhooks = FormWebhook.objects.filter(
            tournament_form=tournament_form,
            is_active=True,
            events__contains=event
        )
        
        # Prepare event data
        data = {
            'tournament': {
                'id': tournament_form.tournament.id,
                'name': tournament_form.tournament.name,
                'slug': tournament_form.tournament.slug,
            },
            'form': {
                'id': tournament_form.id,
                'template_name': tournament_form.template.name,
            }
        }
        
        # Add response data if provided
        if response:
            data['response'] = {
                'id': response.id,
                'status': response.status,
                'user': response.user.username if response.user else None,
                'team': response.team.name if response.team else None,
                'submitted_at': response.submitted_at.isoformat() if response.submitted_at else None,
                'has_paid': response.has_paid,
                'payment_verified': response.payment_verified,
                'payment_amount': float(response.payment_amount) if response.payment_amount else None,
                'form_data': response.response_data,
            }
        
        # Add extra data
        if extra_data:
            data.update(extra_data)
        
        # Send to all webhooks
        deliveries = []
        for webhook in webhooks:
            delivery = webhook.send(event, data)
            deliveries.append(delivery)
        
        return deliveries
    
    @staticmethod
    def on_response_created(response: FormResponse):
        """Trigger when a new response is created (draft)"""
        return WebhookService.trigger_event(
            response.tournament_form,
            'response.created',
            response=response
        )
    
    @staticmethod
    def on_response_submitted(response: FormResponse):
        """Trigger when a response is submitted"""
        return WebhookService.trigger_event(
            response.tournament_form,
            'response.submitted',
            response=response
        )
    
    @staticmethod
    def on_response_approved(response: FormResponse):
        """Trigger when a response is approved"""
        return WebhookService.trigger_event(
            response.tournament_form,
            'response.approved',
            response=response
        )
    
    @staticmethod
    def on_response_rejected(response: FormResponse, reason: str = None):
        """Trigger when a response is rejected"""
        extra_data = {}
        if reason:
            extra_data['rejection_reason'] = reason
        
        return WebhookService.trigger_event(
            response.tournament_form,
            'response.rejected',
            response=response,
            extra_data=extra_data
        )
    
    @staticmethod
    def on_payment_received(response: FormResponse):
        """Trigger when payment is received (marked as paid)"""
        return WebhookService.trigger_event(
            response.tournament_form,
            'payment.received',
            response=response
        )
    
    @staticmethod
    def on_payment_verified(response: FormResponse):
        """Trigger when payment is verified by organizer"""
        return WebhookService.trigger_event(
            response.tournament_form,
            'payment.verified',
            response=response
        )
    
    @staticmethod
    def on_form_opened(tournament_form: TournamentRegistrationForm):
        """Trigger when registration form is opened"""
        return WebhookService.trigger_event(
            tournament_form,
            'form.opened'
        )
    
    @staticmethod
    def on_form_closed(tournament_form: TournamentRegistrationForm):
        """Trigger when registration form is closed"""
        return WebhookService.trigger_event(
            tournament_form,
            'form.closed'
        )
