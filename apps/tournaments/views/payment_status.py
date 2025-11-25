"""
Payment Status Views - Track registration payment verification status

7 Payment States:
1. PENDING - Payment not yet submitted (clock icon)
2. SUBMITTED - Payment proof uploaded, awaiting verification (hourglass)
3. VERIFIED - Payment approved by organizer (green check)
4. REJECTED - Payment rejected, needs resubmission (red X)
5. REFUNDED - Payment refunded (blue return arrow)
6. WAIVED - Fee waived by organizer (gold star)
7. RESUBMISSION - Resubmitted after rejection (orange reload)

Features:
- Visual status indicators with icons and colors
- Timeline view of payment history
- Rejection reason display
- Resubmission prompt with instructions
- Download payment proof
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, Http404
from django.utils import timezone

from apps.tournaments.models import Registration, Payment, Tournament


class RegistrationStatusView(LoginRequiredMixin, View):
    """
    Display registration and payment status for a participant.
    
    Shows:
    - Registration details
    - Payment status with visual indicators
    - Payment timeline/history
    - Actions available (resubmit, download proof)
    """
    
    def get(self, request, slug, registration_id):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = get_object_or_404(
            Registration, 
            id=registration_id,
            tournament=tournament
        )
        
        # Security: Only registration owner or organizers can view
        is_owner = (
            registration.user == request.user or 
            (registration.team and registration.team.captain == request.user)
        )
        is_organizer = tournament.organizers.filter(id=request.user.id).exists()
        
        if not (is_owner or is_organizer):
            messages.error(request, 'You do not have permission to view this registration.')
            return redirect('tournaments:detail', slug=slug)
        
        # Get payment records (ordered by submission time, most recent first)
        payments = registration.payments.all().order_by('-submitted_at')
        current_payment = payments.first() if payments.exists() else None
        
        # Determine registration status
        status_info = self._get_status_info(registration, current_payment)
        
        context = {
            'tournament': tournament,
            'registration': registration,
            'current_payment': current_payment,
            'payment_history': payments,
            'status_info': status_info,
            'is_organizer': is_organizer,
        }
        
        return render(request, 'tournaments/registration/status.html', context)
    
    def _get_status_info(self, registration, payment):
        """
        Get status information with icon, color, and message.
        
        Returns dict with:
        - status: registration status
        - icon: emoji icon
        - color: Tailwind color class
        - title: Status title
        - message: Status description
        - action: Action available (if any)
        """
        
        if not payment:
            # No payment submitted yet
            return {
                'status': Registration.PENDING,
                'icon': '🕐',
                'color': 'gray',
                'title': 'Payment Pending',
                'message': 'Waiting for payment submission.',
                'action': 'submit_payment',
            }
        
        # Check payment status
        if payment.status == Payment.PENDING:
            return {
                'status': payment.status,
                'icon': '🕐',
                'color': 'gray',
                'title': 'Payment Pending',
                'message': 'Payment proof not yet submitted.',
                'action': 'submit_payment',
            }
        
        elif payment.status == Payment.SUBMITTED:
            return {
                'status': payment.status,
                'icon': '⏳',
                'color': 'yellow',
                'title': 'Payment Submitted',
                'message': 'Payment proof submitted. Verification in progress (1-2 hours).',
                'action': None,
            }
        
        elif payment.status == Payment.VERIFIED:
            return {
                'status': payment.status,
                'icon': '✅',
                'color': 'green',
                'title': 'Payment Verified',
                'message': 'Your payment has been verified. Registration confirmed!',
                'action': None,
            }
        
        elif payment.status == Payment.REJECTED:
            return {
                'status': payment.status,
                'icon': '❌',
                'color': 'red',
                'title': 'Payment Rejected',
                'message': payment.admin_notes or 'Payment was rejected. Please resubmit with correct information.',
                'action': 'resubmit_payment',
            }
        
        elif payment.status == Payment.REFUNDED:
            return {
                'status': payment.status,
                'icon': '↩️',
                'color': 'blue',
                'title': 'Payment Refunded',
                'message': 'Payment has been refunded to your account.',
                'action': None,
            }
        
        elif payment.status == Payment.WAIVED:
            return {
                'status': payment.status,
                'icon': '⭐',
                'color': 'yellow',
                'title': 'Fee Waived',
                'message': payment.waive_reason or 'Entry fee waived by organizer.',
                'action': None,
            }
        
        else:
            return {
                'status': 'unknown',
                'icon': '❓',
                'color': 'gray',
                'title': 'Unknown Status',
                'message': 'Contact organizers for status update.',
                'action': None,
            }


class PaymentResubmitView(LoginRequiredMixin, View):
    """
    Allow participants to resubmit payment after rejection.
    """
    
    def get(self, request, slug, registration_id):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = get_object_or_404(
            Registration,
            id=registration_id,
            tournament=tournament
        )
        
        # Security check
        is_owner = (
            registration.user == request.user or 
            (registration.team and registration.team.captain == request.user)
        )
        
        if not is_owner:
            messages.error(request, 'You do not have permission to resubmit payment.')
            return redirect('tournaments:detail', slug=slug)
        
        # Get rejected payment
        rejected_payment = registration.payments.filter(
            status=Payment.REJECTED
        ).order_by('-submitted_at').first()
        
        if not rejected_payment:
            messages.error(request, 'No rejected payment found.')
            return redirect('tournaments:registration_status', slug=slug, registration_id=registration_id)
        
        context = {
            'tournament': tournament,
            'registration': registration,
            'rejected_payment': rejected_payment,
            'entry_fee': tournament.entry_fee_amount,
            'currency': tournament.entry_fee_currency or 'BDT',
        }
        
        return render(request, 'tournaments/registration/resubmit_payment.html', context)
    
    def post(self, request, slug, registration_id):
        tournament = get_object_or_404(Tournament, slug=slug)
        registration = get_object_or_404(
            Registration,
            id=registration_id,
            tournament=tournament
        )
        
        # Security check
        is_owner = (
            registration.user == request.user or 
            (registration.team and registration.team.captain == request.user)
        )
        
        if not is_owner:
            messages.error(request, 'You do not have permission to resubmit payment.')
            return redirect('tournaments:detail', slug=slug)
        
        # Get payment data
        payment_method = request.POST.get('payment_method')
        transaction_id = request.POST.get('transaction_id', '')
        payment_proof = request.FILES.get('payment_proof')
        payment_notes = request.POST.get('payment_notes', '')
        
        # Validate
        if not payment_method:
            messages.error(request, 'Payment method is required.')
            return redirect('tournaments:payment_resubmit', slug=slug, registration_id=registration_id)
        
        if payment_method in ['bkash', 'nagad', 'rocket'] and not transaction_id:
            messages.error(request, 'Transaction ID is required.')
            return redirect('tournaments:payment_resubmit', slug=slug, registration_id=registration_id)
        
        if not payment_proof:
            messages.error(request, 'Payment proof is required.')
            return redirect('tournaments:payment_resubmit', slug=slug, registration_id=registration_id)
        
        # Create new payment (resubmission)
        from apps.tournaments.services.registration_service import RegistrationService
        
        try:
            # Get previous rejected payment to increment resubmission count
            previous_payment = registration.payments.filter(
                status=Payment.REJECTED
            ).order_by('-submitted_at').first()
            
            resubmission_count = previous_payment.resubmission_count + 1 if previous_payment else 1
            
            payment = RegistrationService.submit_payment(
                registration_id=registration.id,
                payment_method=payment_method,
                amount=tournament.entry_fee_amount,
                transaction_id=transaction_id,
                payment_proof=payment_proof
            )
            
            # Update resubmission count
            payment.resubmission_count = resubmission_count
            payment.save(update_fields=['resubmission_count'])
            
            # Update registration status
            registration.status = Registration.PAYMENT_SUBMITTED
            registration.save(update_fields=['status'])
            
            messages.success(request, 'Payment resubmitted successfully! Verification in progress.')
            return redirect('tournaments:registration_status', slug=slug, registration_id=registration_id)
            
        except Exception as e:
            messages.error(request, f'Error submitting payment: {str(e)}')
            return redirect('tournaments:payment_resubmit', slug=slug, registration_id=registration_id)


class DownloadPaymentProofView(LoginRequiredMixin, View):
    """
    Download payment proof file.
    """
    
    def get(self, request, slug, payment_id):
        tournament = get_object_or_404(Tournament, slug=slug)
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Security check
        registration = payment.registration
        is_owner = (
            registration.user == request.user or 
            (registration.team and registration.team.captain == request.user)
        )
        is_organizer = tournament.organizers.filter(id=request.user.id).exists()
        
        if not (is_owner or is_organizer):
            raise Http404("Payment proof not found")
        
        # Check if file exists
        if not payment.payment_proof:
            raise Http404("Payment proof not found")
        
        # Return file
        try:
            response = HttpResponse(payment.payment_proof.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{payment.payment_proof.name}"'
            return response
        except Exception:
            raise Http404("Error downloading payment proof")
