"""
Organizer — Payment Management Actions (FE-T-023).

Extracted from organizer.py during Phase 3 restructure.
Handles payment verification, refunds, CSV export, and payment history.
"""
import json
import csv
from decimal import Decimal

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils import timezone

from apps.tournaments.models import Tournament, Registration, Payment
from apps.tournaments.services.staff_permission_checker import StaffPermissionChecker
from apps.tournaments.services.payment_service import PaymentService


@login_required
@require_POST
def verify_payment(request, slug, payment_id):
    """Verify a payment."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_approve_payments():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    payment = get_object_or_404(Payment, id=payment_id, registration__tournament=tournament)
    PaymentService.verify_payment(payment, request.user)

    messages.success(request, f"Payment verified for {payment.registration.user.username}.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def reject_payment(request, slug, payment_id):
    """Reject a payment."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_approve_payments():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    payment = get_object_or_404(Payment, id=payment_id, registration__tournament=tournament)
    PaymentService.reject_payment(payment, request.user)

    messages.warning(request, f"Payment rejected for {payment.registration.user.username}.")
    return JsonResponse({'success': True})


@login_required
@require_POST
def bulk_verify_payments(request, slug):
    """FE-T-023: Bulk verify multiple payments."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_approve_payments():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    try:
        data = json.loads(request.body)
        payment_ids = data.get('payment_ids', [])

        if not payment_ids:
            return JsonResponse({'success': False, 'error': 'No payments selected'}, status=400)

        updated = PaymentService.organizer_bulk_verify(
            payment_ids,
            tournament,
            request.user
        )

        messages.success(request, f"Successfully verified {updated} payment(s).")
        return JsonResponse({'success': True, 'count': updated})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def process_refund(request, slug, payment_id):
    """FE-T-023: Process refund for a payment."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.can_approve_payments():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    payment = get_object_or_404(Payment, id=payment_id, registration__tournament=tournament)

    try:
        data = json.loads(request.body)
        refund_amount = Decimal(str(data.get('amount', 0)))
        reason = data.get('reason', '').strip()
        refund_method = data.get('refund_method', 'manual')

        try:
            PaymentService.organizer_process_refund(
                payment,
                refund_amount,
                reason,
                refund_method,
                request.user.username
            )
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)

        messages.success(request, f"Refund of ${refund_amount} processed successfully.")
        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def export_payments_csv(request, slug):
    """FE-T-023: Export payment report as CSV."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.has_any(['approve_payments', 'view_all']):
        messages.error(request, "You don't have permission to export payments.")
        return redirect('tournaments:organizer_hub', slug=slug, tab='payments')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{tournament.slug}_payments_{timezone.now().strftime("%Y%m%d")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Username', 'Amount', 'Method', 'Status',
        'Submitted At', 'Verified At', 'Verified By'
    ])

    payments = Payment.objects.filter(
        registration__tournament=tournament
    ).select_related('registration__user', 'verified_by').order_by('-submitted_at')

    for payment in payments:
        writer.writerow([
            payment.id,
            payment.registration.user.username if payment.registration.user else 'N/A',
            f'${payment.amount}' if hasattr(payment, 'amount') else 'N/A',
            payment.payment_method if hasattr(payment, 'payment_method') else 'N/A',
            payment.get_status_display() if hasattr(payment, 'get_status_display') else payment.status,
            payment.submitted_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(payment, 'submitted_at') and payment.submitted_at else 'N/A',
            payment.verified_at.strftime('%Y-%m-%d %H:%M:%S') if hasattr(payment, 'verified_at') and payment.verified_at else 'N/A',
            payment.verified_by.username if hasattr(payment, 'verified_by') and payment.verified_by else 'N/A',
        ])

    return response


@login_required
def payment_history(request, slug, registration_id):
    """FE-T-023: View payment history for a registration."""
    tournament = get_object_or_404(Tournament, slug=slug)
    checker = StaffPermissionChecker(tournament, request.user)

    if not checker.has_any(['approve_payments', 'view_all']):
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)

    registration = get_object_or_404(Registration, id=registration_id, tournament=tournament)

    payments = Payment.objects.filter(
        registration=registration
    ).select_related('verified_by').order_by('-submitted_at')

    payment_data = []
    for payment in payments:
        payment_data.append({
            'id': payment.id,
            'amount': str(payment.amount) if hasattr(payment, 'amount') else '0',
            'method': payment.payment_method if hasattr(payment, 'payment_method') else 'N/A',
            'status': payment.status,
            'submitted_at': payment.submitted_at.isoformat() if hasattr(payment, 'submitted_at') and payment.submitted_at else None,
            'verified_at': payment.verified_at.isoformat() if hasattr(payment, 'verified_at') and payment.verified_at else None,
            'verified_by': payment.verified_by.username if hasattr(payment, 'verified_by') and payment.verified_by else None,
        })

    return JsonResponse({
        'success': True,
        'participant': registration.user.username if registration.user else f'Team {registration.team_id}',
        'payments': payment_data
    })
