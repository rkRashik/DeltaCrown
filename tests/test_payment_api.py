"""
Module 3.2: Payment Processing API Tests

Comprehensive tests for payment proof submission, verification, rejection, and refund endpoints.

Source Documents:
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md (Payment Flow)
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md (Testing Strategy)
- Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md (Testing Standards)
"""

import io
from decimal import Decimal
from PIL import Image
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from apps.tournaments.models.tournament import Tournament
from apps.tournaments.models.registration import Registration, Payment

User = get_user_model()


class PaymentAPITestCase(TestCase):
    """Test payment API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.player = User.objects.create_user(
            username='player1',
            email='player@test.com',
            password='testpass123'
        )
        
        self.organizer = User.objects.create_user(
            username='organizer1',
            email='organizer@test.com',
            password='testpass123'
        )
        
        self.admin = User.objects.create_user(
            username='admin1',
            email='admin@test.com',
            password='testpass123',
            is_staff=True
        )
        
        self.other_player = User.objects.create_user(
            username='player2',
            email='player2@test.com',
            password='testpass123'
        )
        
        # Create tournament (minimal fields only)
        from apps.games.models.game import Game
        game = Game.objects.create(
            name='Valorant',
            slug='valorant',
            default_team_size=5,
            default_result_type=Game.MAP_SCORE
        )
        
        self.tournament = Tournament.objects.create(
            name='Test Tournament',
            slug='test-tournament',
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
            entry_fee_amount=Decimal('500.00'),
            prize_pool=Decimal('5000.00'),
            entry_fee_deltacoin=100,
        )
        self.tournament.payment_methods = ['bkash', 'nagad', 'deltacoin']
        self.tournament.save()
        
        # Create registration
        self.registration = Registration.objects.create(
            tournament=self.tournament,
            user=self.player,
            status=Registration.PENDING
        )
        
        # Create payment
        self.payment = Payment.objects.create(
            registration=self.registration,
            payment_method='bkash',
            amount=Decimal('500.00'),
            status=Payment.PENDING
        )
        
        # API client
        self.client = APIClient()
    
    def create_test_image(self, filename='test.jpg', size=(100, 100)):
        """Create a test image file"""
        image = Image.new('RGB', size, color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        return SimpleUploadedFile(
            filename,
            image_io.read(),
            content_type='image/jpeg'
        )
    
    def create_test_pdf(self, filename='test.pdf'):
        """Create a test PDF file"""
        pdf_content = b'%PDF-1.4\n%Test PDF\n%%EOF'
        return SimpleUploadedFile(
            filename,
            pdf_content,
            content_type='application/pdf'
        )
    
    def test_submit_payment_proof_success_image(self):
        """Test successful payment proof submission with image"""
        self.client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        
        image_file = self.create_test_image()
        data = {
            'payment_proof': image_file,
            'reference_number': 'BKS12345678',
            'notes': 'Paid via bKash mobile app'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('payment', response.data)
        
        # Verify payment was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.SUBMITTED)
        self.assertEqual(self.payment.reference_number, 'BKS12345678')
        self.assertIsNotNone(self.payment.payment_proof)
        self.assertEqual(self.payment.file_type, 'IMAGE')
    
    def test_submit_payment_proof_success_pdf(self):
        """Test successful payment proof submission with PDF"""
        self.client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        
        pdf_file = self.create_test_pdf()
        data = {
            'payment_proof': pdf_file,
            'reference_number': 'NGD98765432',
            'notes': 'Bank transfer receipt'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify payment was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.SUBMITTED)
        self.assertEqual(self.payment.file_type, 'PDF')
    
    def test_submit_payment_proof_oversized_file(self):
        """Test rejection of oversized file (>5MB)"""
        self.client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        
        # Create 6MB file
        large_content = b'x' * (6 * 1024 * 1024)
        large_file = SimpleUploadedFile('large.jpg', large_content, content_type='image/jpeg')
        
        data = {
            'payment_proof': large_file,
            'reference_number': 'TEST123'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('payment_proof', response.data)
    
    def test_submit_payment_proof_invalid_file_type(self):
        """Test rejection of invalid file type"""
        self.client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        
        # Create invalid file type
        txt_file = SimpleUploadedFile('test.txt', b'test content', content_type='text/plain')
        
        data = {
            'payment_proof': txt_file,
            'reference_number': 'TEST123'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('payment_proof', response.data)
    
    def test_submit_payment_proof_unauthenticated(self):
        """Test unauthenticated user cannot submit proof"""
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        
        image_file = self.create_test_image()
        data = {
            'payment_proof': image_file,
            'reference_number': 'TEST123'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_submit_payment_proof_wrong_user(self):
        """Test user cannot submit proof for another user's registration"""
        self.client.force_authenticate(user=self.other_player)
        
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        
        image_file = self.create_test_image()
        data = {
            'payment_proof': image_file,
            'reference_number': 'TEST123'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_submit_payment_proof_organizer_can_submit(self):
        """Test organizer can submit proof on behalf of participant"""
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        
        image_file = self.create_test_image()
        data = {
            'payment_proof': image_file,
            'reference_number': 'ORG123'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_submit_payment_proof_resubmit_after_rejection(self):
        """Test can resubmit after rejection"""
        # Set payment to rejected
        self.payment.status = Payment.REJECTED
        self.payment.rejection_reason = 'Invalid transaction ID'
        self.payment.save()
        
        self.client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        
        image_file = self.create_test_image()
        data = {
            'payment_proof': image_file,
            'reference_number': 'CORRECTED123'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify status changed back to submitted
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.SUBMITTED)
    
    def test_submit_payment_proof_cannot_resubmit_verified(self):
        """Test cannot resubmit after verification"""
        # Set payment to verified
        self.payment.status = Payment.VERIFIED
        self.payment.verified_by = self.organizer
        self.payment.verified_at = timezone.now()
        self.payment.save()
        
        self.client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        
        image_file = self.create_test_image()
        data = {
            'payment_proof': image_file,
            'reference_number': 'TEST123'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
    
    def test_verify_payment_success(self):
        """Test successful payment verification by organizer"""
        # Submit payment first
        self.payment.status = Payment.SUBMITTED
        self.payment.save()
        
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/verify/'
        data = {
            'notes': 'Verified via bKash app'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify payment was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.VERIFIED)
        self.assertEqual(self.payment.verified_by, self.organizer)
        self.assertIsNotNone(self.payment.verified_at)
        
        # Verify registration status updated
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.CONFIRMED)
    
    def test_verify_payment_admin_can_verify(self):
        """Test admin (staff user) can verify payment for any tournament"""
        # Create a separate tournament/registration/payment where admin is organizer
        # This tests that staff users can access payments via is_staff check
        admin_tournament = Tournament.objects.create(
            name='Admin Organized Tournament',
            slug='admin-tournament',
            description='Admin Test',
            game=self.tournament.game,
            organizer=self.admin,
            format=Tournament.SINGLE_ELIM,
            participation_type=Tournament.SOLO,
            max_participants=8,
            min_participants=2,
            registration_start=timezone.now(),
            registration_end=timezone.now() + timezone.timedelta(days=7),
            tournament_start=timezone.now() + timezone.timedelta(days=14),
            tournament_end=timezone.now() + timezone.timedelta(days=15),
            status=Tournament.REGISTRATION_OPEN,
            has_entry_fee=True,
            entry_fee_amount=Decimal('300.00')
        )
        admin_tournament.payment_methods = ['bkash']
        admin_tournament.save()
        
        admin_registration = Registration.objects.create(
            tournament=admin_tournament,
            user=self.other_player,
            status=Registration.PENDING
        )
        
        admin_payment = Payment.objects.create(
            registration=admin_registration,
            payment_method='bkash',
            amount=Decimal('300.00'),
            status=Payment.SUBMITTED
        )
        
        self.client.force_authenticate(user=self.admin)
        
        url = f'/api/tournaments/payments/{admin_payment.id}/verify/'
        data = {}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_verify_payment_player_cannot_verify(self):
        """Test player cannot verify their own payment"""
        self.payment.status = Payment.SUBMITTED
        self.payment.save()
        
        self.client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/{self.payment.id}/verify/'
        data = {}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_verify_payment_wrong_status(self):
        """Test cannot verify payment with wrong status"""
        # Payment is PENDING
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/verify/'
        data = {}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
    
    def test_reject_payment_success(self):
        """Test successful payment rejection by organizer"""
        # Submit payment first
        self.payment.status = Payment.SUBMITTED
        self.payment.save()
        
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/reject/'
        data = {
            'admin_notes': 'Transaction ID does not match our records'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify payment was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.REJECTED)
        self.assertEqual(self.payment.admin_notes, 'Transaction ID does not match our records')
        self.assertIsNotNone(self.payment.verified_at)
        
        # Verify registration status reverted to PENDING
        self.registration.refresh_from_db()
        self.assertEqual(self.registration.status, Registration.PENDING)
    
    def test_reject_payment_missing_reason(self):
        """Test rejection requires reason"""
        self.payment.status = Payment.SUBMITTED
        self.payment.save()
        
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/reject/'
        data = {}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('admin_notes', response.data)
    
    def test_reject_payment_player_cannot_reject(self):
        """Test player cannot reject payments"""
        self.payment.status = Payment.SUBMITTED
        self.payment.save()
        
        self.client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/{self.payment.id}/reject/'
        data = {
            'admin_notes': 'Test reason'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_refund_payment_success(self):
        """Test successful payment refund"""
        # Verify payment first
        self.payment.status = Payment.VERIFIED
        self.payment.verified_by = self.organizer
        self.payment.verified_at = timezone.now()
        self.payment.save()
        
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/refund/'
        data = {
            'admin_notes': 'Tournament cancelled',
            'refund_method': 'same'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify payment was updated
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.REFUNDED)
    
    def test_refund_payment_wrong_status(self):
        """Test cannot refund non-verified payment"""
        # Payment is PENDING
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/refund/'
        data = {
            'admin_notes': 'Test reason',
            'refund_method': 'same'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', response.data)
    
    def test_refund_payment_missing_required_fields(self):
        """Test refund requires reason and refund_method"""
        self.payment.status = Payment.VERIFIED
        self.payment.verified_at = timezone.now()  # Required by check constraint
        self.payment.verified_by = self.organizer
        self.payment.save()
        
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/refund/'
        data = {}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('admin_notes', response.data)
        self.assertIn('refund_method', response.data)
    
    def test_get_payment_status_success(self):
        """Test payment status retrieval"""
        self.client.force_authenticate(user=self.player)
        
        url = f'/api/tournaments/payments/{self.payment.id}/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.payment.id)
        self.assertEqual(response.data['status'], Payment.PENDING)
        self.assertIn('status_display', response.data)
        self.assertIn('payment_method_display', response.data)
    
    def test_get_payment_status_organizer_can_view(self):
        """Test organizer can view payment status"""
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_get_payment_status_other_player_cannot_view(self):
        """Test other player cannot view payment status"""
        self.client.force_authenticate(user=self.other_player)
        
        url = f'/api/tournaments/payments/{self.payment.id}/'
        
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_payment_workflow_complete(self):
        """Test complete payment workflow: submit → verify"""
        # Step 1: Submit payment proof
        self.client.force_authenticate(user=self.player)
        
        submit_url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        image_file = self.create_test_image()
        submit_data = {
            'payment_proof': image_file,
            'reference_number': 'WORKFLOW123'
        }
        
        submit_response = self.client.post(submit_url, submit_data, format='multipart')
        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)
        
        # Step 2: Verify payment
        self.client.force_authenticate(user=self.organizer)
        
        verify_url = f'/api/tournaments/payments/{self.payment.id}/verify/'
        verify_data = {
            'notes': 'Payment confirmed'
        }
        
        verify_response = self.client.post(verify_url, verify_data, format='json')
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        
        # Verify final state
        self.payment.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.VERIFIED)
        self.assertEqual(self.registration.status, Registration.CONFIRMED)
    
    def test_payment_workflow_reject_and_resubmit(self):
        """Test payment workflow: submit → reject → resubmit → verify"""
        # Step 1: Submit payment proof
        self.client.force_authenticate(user=self.player)
        
        submit_url = f'/api/tournaments/payments/registrations/{self.registration.id}/submit-proof/'
        image_file1 = self.create_test_image(filename='first_attempt.jpg')
        submit_data1 = {
            'payment_proof': image_file1,
            'reference_number': 'WRONG123'
        }
        
        submit_response1 = self.client.post(submit_url, submit_data1, format='multipart')
        self.assertEqual(submit_response1.status_code, status.HTTP_200_OK)
        
        # Step 2: Reject payment
        self.client.force_authenticate(user=self.organizer)
        
        reject_url = f'/api/tournaments/payments/{self.payment.id}/reject/'
        reject_data = {
            'admin_notes': 'Invalid transaction ID - Please resubmit with correct ID'
        }
        
        reject_response = self.client.post(reject_url, reject_data, format='json')
        self.assertEqual(reject_response.status_code, status.HTTP_200_OK)
        
        # Step 3: Resubmit with corrected proof
        self.client.force_authenticate(user=self.player)
        
        image_file2 = self.create_test_image(filename='corrected_attempt.jpg')
        submit_data2 = {
            'payment_proof': image_file2,
            'reference_number': 'CORRECT123'
        }
        
        submit_response2 = self.client.post(submit_url, submit_data2, format='multipart')
        self.assertEqual(submit_response2.status_code, status.HTTP_200_OK)
        
        # Step 4: Verify payment
        self.client.force_authenticate(user=self.organizer)
        
        verify_url = f'/api/tournaments/payments/{self.payment.id}/verify/'
        verify_data = {
            'admin_notes': 'Corrected payment confirmed'
        }
        
        verify_response = self.client.post(verify_url, verify_data, format='json')
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)
        
        # Verify final state
        self.payment.refresh_from_db()
        self.registration.refresh_from_db()
        self.assertEqual(self.payment.status, Payment.VERIFIED)
        self.assertEqual(self.registration.status, Registration.CONFIRMED)
        self.assertEqual(self.payment.reference_number, 'CORRECT123')


class PaymentAPIDeltaCoinTestCase(TestCase):
    """Test payment API for DeltaCoin payments (no proof required)"""
    
    def setUp(self):
        """Set up test data"""
        self.player = User.objects.create_user(
            username='dcplayer',
            email='dcplayer@test.com',
            password='testpass123'
        )
        
        self.organizer = User.objects.create_user(
            username='dcorganizer',
            email='dcorganizer@test.com',
            password='testpass123'
        )
        
        # Create game
        from apps.games.models.game import Game
        game = Game.objects.create(
            name='Valorant DC',
            slug='valorant-dc',
            default_team_size=5,
            default_result_type=Game.MAP_SCORE
        )
        
        self.tournament = Tournament.objects.create(
            name='Test Tournament DeltaCoin',
            slug='test-tournament-deltacoin',
            description='Test Description DeltaCoin',
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
            entry_fee_amount=Decimal('0.00'),
            entry_fee_deltacoin=100,
        )
        self.tournament.payment_methods = ['deltacoin']
        self.tournament.save()
        
        self.registration = Registration.objects.create(
            tournament=self.tournament,
            user=self.player,
            status=Registration.PENDING
        )
        
        self.payment = Payment.objects.create(
            registration=self.registration,
            payment_method='deltacoin',
            amount=Decimal('100.00'),  # DeltaCoin amount (entry_fee_deltacoin)
            status=Payment.VERIFIED,  # DeltaCoin payments are auto-verified
            verified_at=timezone.now(),  # Required by check constraint
            verified_by=self.organizer
        )
        
        self.client = APIClient()
    
    def test_cannot_submit_proof_for_deltacoin(self):
        """Test cannot submit proof for DeltaCoin payment"""
        self.client.force_authenticate(user=self.player)
        
        # Create a separate registration for this test (self.registration already has a payment)
        from django.contrib.auth import get_user_model
        from apps.tournaments.models.registration import Registration as Reg
        User = get_user_model()
        test_player = User.objects.create_user(
            username='dcplayer2',
            email='dcplayer2@test.com',
            password='testpass123'
        )
        
        dc_registration = Reg.objects.create(
            tournament=self.tournament,
            user=test_player,
            status=Reg.PENDING
        )
        
        # Create pending DeltaCoin payment for new registration
        dc_payment = Payment.objects.create(
            registration=dc_registration,
            payment_method='deltacoin',
            amount=Decimal('100.00'),  # DeltaCoin amount (entry_fee_deltacoin)
            status=Payment.PENDING
        )
        
        # Authenticate as the player who owns this registration
        self.client.force_authenticate(user=test_player)
        
        url = f'/api/tournaments/payments/registrations/{dc_registration.id}/submit-proof/'
        
        # Try to submit proof
        from PIL import Image
        import io
        image = Image.new('RGB', (100, 100), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        image_file = SimpleUploadedFile('test.jpg', image_io.read(), content_type='image/jpeg')
        
        data = {
            'payment_proof': image_file,
            'reference_number': 'DC123'
        }
        
        response = self.client.post(url, data, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('payment_method', response.data)


class PaymentPermissionTestCase(TestCase):
    """Test permission boundaries for payment API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.player1 = User.objects.create_user(
            username='player1',
            email='player1@test.com',
            password='testpass123'
        )
        
        self.player2 = User.objects.create_user(
            username='player2',
            email='player2@test.com',
            password='testpass123'
        )
        
        self.organizer = User.objects.create_user(
            username='permorganizer',
            email='permorganizer@test.com',
            password='testpass123'
        )
        
        # Create game
        from apps.games.models.game import Game
        game = Game.objects.create(
            name='Valorant Perm',
            slug='valorant-perm',
            default_team_size=5,
            default_result_type=Game.MAP_SCORE
        )
        
        self.tournament = Tournament.objects.create(
            name='Permission Test Tournament',
            slug='perm-test-tournament',
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
        self.tournament.payment_methods = ['bkash']
        self.tournament.save()
        
        # Player1's registration and payment
        self.registration1 = Registration.objects.create(
            tournament=self.tournament,
            user=self.player1,
            status=Registration.PENDING
        )
        
        self.payment1 = Payment.objects.create(
            registration=self.registration1,
            payment_method='bkash',
            amount=Decimal('500.00'),
            status=Payment.SUBMITTED
        )
        
        # Player2's registration and payment
        self.registration2 = Registration.objects.create(
            tournament=self.tournament,
            user=self.player2,
            status=Registration.PENDING
        )
        
        self.payment2 = Payment.objects.create(
            registration=self.registration2,
            payment_method='bkash',
            amount=Decimal('500.00'),
            status=Payment.SUBMITTED
        )
        
        self.client = APIClient()
    
    def test_player_cannot_retrieve_other_players_payment(self):
        """Test player cannot view another player's payment details"""
        self.client.force_authenticate(user=self.player2)
        
        # Try to access player1's payment
        url = f'/api/tournaments/payments/{self.payment1.id}/'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_player_cannot_verify_payment(self):
        """Test regular player cannot verify any payment"""
        self.client.force_authenticate(user=self.player1)
        
        url = f'/api/tournaments/payments/{self.payment1.id}/verify/'
        data = {'admin_notes': 'Trying to verify own payment'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
    
    def test_player_cannot_reject_payment(self):
        """Test regular player cannot reject any payment"""
        self.client.force_authenticate(user=self.player1)
        
        url = f'/api/tournaments/payments/{self.payment1.id}/reject/'
        data = {'admin_notes': 'Trying to reject own payment'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
    
    def test_player_cannot_refund_payment(self):
        """Test regular player cannot refund any payment"""
        # Set payment to verified
        self.payment1.status = Payment.VERIFIED
        self.payment1.verified_at = timezone.now()
        self.payment1.verified_by = self.organizer
        self.payment1.save()
        
        self.client.force_authenticate(user=self.player1)
        
        url = f'/api/tournaments/payments/{self.payment1.id}/refund/'
        data = {
            'admin_notes': 'Trying to refund own payment',
            'refund_method': 'same'
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.data)
    
    def test_organizer_can_access_all_tournament_payments(self):
        """Test organizer can access all payments for their tournament"""
        self.client.force_authenticate(user=self.organizer)
        
        # Access player1's payment
        url1 = f'/api/tournaments/payments/{self.payment1.id}/'
        response1 = self.client.get(url1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        
        # Access player2's payment
        url2 = f'/api/tournaments/payments/{self.payment2.id}/'
        response2 = self.client.get(url2)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
    
    def test_organizer_can_verify_payments(self):
        """Test organizer can verify payments for their tournament"""
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment1.id}/verify/'
        data = {'admin_notes': 'Organizer verification'}
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.payment1.refresh_from_db()
        self.assertEqual(self.payment1.status, Payment.VERIFIED)


class PaymentValidationTestCase(TestCase):
    """Test validation edge cases for payment API endpoints"""
    
    def setUp(self):
        """Set up test data"""
        self.player = User.objects.create_user(
            username='valplayer',
            email='valplayer@test.com',
            password='testpass123'
        )
        
        self.organizer = User.objects.create_user(
            username='valorganizer',
            email='valorganizer@test.com',
            password='testpass123'
        )
        
        # Create game
        from apps.games.models.game import Game
        game = Game.objects.create(
            name='Valorant Val',
            slug='valorant-val',
            default_team_size=5,
            default_result_type=Game.MAP_SCORE
        )
        
        self.tournament = Tournament.objects.create(
            name='Validation Test Tournament',
            slug='val-test-tournament',
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
        self.tournament.payment_methods = ['bkash']
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
            status=Payment.VERIFIED,
            verified_at=timezone.now(),
            verified_by=self.organizer
        )
        
        self.client = APIClient()
    
    def test_refund_missing_refund_method_returns_400(self):
        """Test refund without refund_method returns 400 with specific error"""
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/refund/'
        data = {
            'admin_notes': 'Tournament cancelled'
            # Missing refund_method
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('refund_method', response.data)
        self.assertEqual(response.data['refund_method'][0], 'This field is required.')
    
    def test_refund_missing_admin_notes_returns_400(self):
        """Test refund without admin_notes returns 400 with specific error"""
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/refund/'
        data = {
            'refund_method': 'same'
            # Missing admin_notes
        }
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('admin_notes', response.data)
        self.assertEqual(response.data['admin_notes'][0], 'This field is required.')
    
    def test_reject_missing_admin_notes_returns_400(self):
        """Test reject without admin_notes returns 400 with specific error"""
        self.payment.status = Payment.SUBMITTED
        self.payment.verified_at = None
        self.payment.verified_by = None
        self.payment.save()
        
        self.client.force_authenticate(user=self.organizer)
        
        url = f'/api/tournaments/payments/{self.payment.id}/reject/'
        data = {}  # Missing admin_notes
        
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('admin_notes', response.data)
        self.assertEqual(response.data['admin_notes'][0], 'This field is required.')
