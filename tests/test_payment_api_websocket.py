"""
Module 3.2: Payment Processing WebSocket Tests

Tests for WebSocket event broadcasting in payment workflows.

Source Documents:
- Documents/Planning/PART_2.3_REALTIME_SECURITY.md (WebSocket Channels)
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (Real-time Notifications)
"""

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from unittest.mock import patch, MagicMock, call
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.registration import Registration, Payment
from apps.tournaments.services.registration_service import RegistrationService

User = get_user_model()


class PaymentWebSocketTestCase(TestCase):
    """Test WebSocket event broadcasting for payment operations"""
    
    def setUp(self):
        """Set up test data"""
        self.player = User.objects.create_user(
            username='wsplayer',
            email='wsplayer@test.com',
            password='testpass123'
        )
        
        self.organizer = User.objects.create_user(
            username='wsorganizer',
            email='wsorganizer@test.com',
            password='testpass123'
        )
        
        # Create game
        from apps.games.models.game import Game
        game = Game.objects.create(
            name='Valorant WS',
            slug='valorant-ws',
            default_team_size=5,
            default_result_type=Game.MAP_SCORE
        )
        
        self.tournament = Tournament.objects.create(
            name='WebSocket Test Tournament',
            slug='ws-test-tournament',
            description='Test Description',
            game=game,
            organizer=self.organizer,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.SOLO,
            max_participants=16,
            min_participants=2,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timezone.timedelta(days=7),
            tournament_start=timezone.now() + timezone.timedelta(days=14),
            tournament_end=timezone.now() + timezone.timedelta(days=15),
            status=Tournament.REGISTRATION_OPEN,
            has_entry_fee=True,
            entry_fee_amount=Decimal('500.00')
        )
        self.tournament.payment_methods = ['bkash', 'nagad']
        self.tournament.save()
        
        self.registration = Registration.objects.create(
            tournament=self.tournament,
            user=self.player,
            status=Registration.PENDING
        )
        
        self.payment = Payment.objects.create(
            registration=self.registration,
            payment_method='bkash',
            amount=Decimal('500.00'),
            status=Payment.PENDING
        )
    
    @patch('channels.layers.get_channel_layer')
    def test_payment_proof_submitted_websocket_event(self, mock_get_channel_layer):
        """Test payment_proof_submitted WebSocket event is broadcast"""
        # Mock channel layer
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer
        
        # Submit proof via service
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        import io
        
        image = Image.new('RGB', (100, 100), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        proof_file = SimpleUploadedFile('proof.jpg', image_io.read(), content_type='image/jpeg')
        
        # Use API endpoint to trigger broadcast
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        data = {
            'payment_proof': proof_file,
            'reference_number': 'TEST123'
        }
        
        response = client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify WebSocket broadcast was called
        mock_channel_layer.group_send.assert_called_once()
        call_args = mock_channel_layer.group_send.call_args
        
        # Check tournament channel
        self.assertEqual(call_args[0][0], f'tournament_{self.tournament.id}')
        
        # Check event payload
        event = call_args[0][1]
        self.assertEqual(event['type'], 'payment.proof_submitted')
        self.assertEqual(event['payment_id'], self.payment.id)
        self.assertEqual(event['registration_id'], self.registration.id)
        self.assertEqual(event['tournament_id'], self.tournament.id)
        self.assertIn('timestamp', event)
    
    @patch('channels.layers.get_channel_layer')
    def test_payment_verified_websocket_event(self, mock_get_channel_layer):
        """Test payment_verified WebSocket event is broadcast"""
        # Mock channel layer
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer
        
        # Set payment to submitted
        self.payment.status = Payment.SUBMITTED
        self.payment.save()
        
        # Verify via API
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/verify/'
        data = {'admin_notes': 'Payment verified'}
        
        response = client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify WebSocket broadcast
        mock_channel_layer.group_send.assert_called_once()
        call_args = mock_channel_layer.group_send.call_args
        
        event = call_args[0][1]
        self.assertEqual(event['type'], 'payment.verified')
        self.assertEqual(event['payment_id'], self.payment.id)
        self.assertIn('verified_by', event)
        self.assertEqual(event['verified_by'], self.organizer.username)
    
    @patch('channels.layers.get_channel_layer')
    def test_payment_rejected_websocket_event(self, mock_get_channel_layer):
        """Test payment_rejected WebSocket event is broadcast"""
        # Mock channel layer
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer
        
        # Set payment to submitted
        self.payment.status = Payment.SUBMITTED
        self.payment.save()
        
        # Reject via API
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/reject/'
        data = {'admin_notes': 'Invalid proof'}
        
        response = client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify WebSocket broadcast
        mock_channel_layer.group_send.assert_called_once()
        call_args = mock_channel_layer.group_send.call_args
        
        event = call_args[0][1]
        self.assertEqual(event['type'], 'payment.rejected')
        self.assertEqual(event['payment_id'], self.payment.id)
        self.assertIn('reason', event)
        self.assertEqual(event['reason'], 'Invalid proof')
    
    @patch('channels.layers.get_channel_layer')
    def test_payment_refunded_websocket_event(self, mock_get_channel_layer):
        """Test payment_refunded WebSocket event is broadcast"""
        # Mock channel layer
        mock_channel_layer = MagicMock()
        mock_get_channel_layer.return_value = mock_channel_layer
        
        # Set payment to verified
        self.payment.status = Payment.VERIFIED
        self.payment.verified_at = timezone.now()
        self.payment.verified_by = self.organizer
        self.payment.save()
        
        # Refund via API
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/refund/'
        data = {
            'admin_notes': 'Tournament cancelled',
            'refund_method': 'same'
        }
        
        response = client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, 200)
        
        # Verify WebSocket broadcast
        mock_channel_layer.group_send.assert_called_once()
        call_args = mock_channel_layer.group_send.call_args
        
        event = call_args[0][1]
        self.assertEqual(event['type'], 'payment.refunded')
        self.assertEqual(event['payment_id'], self.payment.id)
        self.assertIn('reason', event)
        self.assertEqual(event['reason'], 'Tournament cancelled')
