"""
Registration Withdrawal Views

Allows users to withdraw/cancel their tournament registrations
with refund eligibility calculation.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from apps.tournaments.models import Registration, Tournament
from apps.tournaments.services.registration_service import RegistrationService
from django.core.exceptions import ValidationError


@login_required
@require_http_methods(["GET", "POST"])
def withdraw_registration_view(request, slug: str):
    """
    Allow user to withdraw their tournament registration.
    Shows refund policy and eligibility before confirming.
    """
    tournament = get_object_or_404(Tournament, slug=slug)
    
    # Get user's registration
    registration = get_object_or_404(
        Registration,
        tournament=tournament,
        user=request.user,
        is_deleted=False
    )
    
    # Check if already cancelled
    if registration.status in [Registration.CANCELLED, Registration.REJECTED]:
        messages.warning(request, "This registration has already been cancelled.")
        return redirect('tournaments:detail', slug=tournament.slug)
    
    # Check if can withdraw
    can_withdraw, reason = RegistrationService.can_withdraw(registration)
    
    if request.method == 'POST':
        if not can_withdraw:
            messages.error(request, reason)
            return redirect('tournaments:detail', slug=tournament.slug)
        
        # Get withdrawal reason from user
        withdrawal_reason = request.POST.get('reason', '')
        
        try:
            # Withdraw registration
            result = RegistrationService.withdraw_registration(
                registration=registration,
                reason=withdrawal_reason
            )
            
            # Show success message with refund info
            if result['refund_eligible']:
                messages.success(
                    request,
                    f"Registration withdrawn successfully. You are eligible for a {result['refund_percentage']}% "
                    f"refund (৳{result['refund_amount']:.2f}). Refund will be processed within 7-10 business days."
                )
            else:
                messages.success(
                    request,
                    "Registration withdrawn successfully. Unfortunately, you are not eligible for a refund "
                    "due to the withdrawal timing policy."
                )
            
            if result['roster_unlocked']:
                messages.info(request, "Your team roster has been unlocked.")
            
            return redirect('tournaments:detail', slug=tournament.slug)
            
        except ValidationError as e:
            messages.error(request, str(e))
            return redirect('tournaments:detail', slug=tournament.slug)
    
    # GET request - show withdrawal confirmation page
    # Calculate refund info for display
    refund_info = _calculate_refund_preview(tournament, registration)
    
    context = {
        'tournament': tournament,
        'registration': registration,
        'can_withdraw': can_withdraw,
        'withdrawal_blocked_reason': reason if not can_withdraw else None,
        'refund_info': refund_info,
    }
    
    return render(request, 'tournaments/registration/withdraw.html', context)


def _calculate_refund_preview(tournament: Tournament, registration: Registration) -> dict:
    """Calculate refund information for preview"""
    from decimal import Decimal
    from django.utils import timezone
    
    refund_info = {
        'eligible': False,
        'amount': Decimal('0.00'),
        'percentage': 0,
        'policy': []
    }
    
    if not tournament.has_entry_fee or registration.status != Registration.CONFIRMED:
        return refund_info
    
    if not tournament.tournament_start:
        return refund_info
    
    time_until_start = tournament.tournament_start - timezone.now()
    hours_until = time_until_start.total_seconds() / 3600
    
    # Build refund policy display
    refund_info['policy'] = [
        {'label': 'More than 7 days before', 'percentage': 100, 'active': hours_until > 168},
        {'label': '3-7 days before', 'percentage': 50, 'active': 72 < hours_until <= 168},
        {'label': '1-3 days before', 'percentage': 25, 'active': 24 < hours_until <= 72},
        {'label': 'Less than 24 hours', 'percentage': 0, 'active': hours_until <= 24},
    ]
    
    # Calculate actual refund
    if hours_until > 168:
        refund_info['eligible'] = True
        refund_info['amount'] = tournament.entry_fee_amount
        refund_info['percentage'] = 100
    elif hours_until > 72:
        refund_info['eligible'] = True
        refund_info['amount'] = tournament.entry_fee_amount * Decimal('0.50')
        refund_info['percentage'] = 50
    elif hours_until > 24:
        refund_info['eligible'] = True
        refund_info['amount'] = tournament.entry_fee_amount * Decimal('0.25')
        refund_info['percentage'] = 25
    
    return refund_info
