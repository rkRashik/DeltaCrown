# apps/economy/views/withdrawal.py
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q

from ..models import DeltaCrownWallet, WithdrawalRequest, DeltaCrownTransaction
from ..forms import WithdrawalRequestForm, PaymentMethodForm, PINSetupForm


@login_required
def withdrawal_request_view(request):
    """
    Create new withdrawal request.
    
    Flow:
    1. Verify wallet exists and has balance
    2. Verify payment method configured
    3. Verify PIN set up
    4. Display form with balance info
    5. On submit: validate PIN, create request, lock pending balance
    """
    profile = request.user.profile
    wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
    
    # Check if PIN is set up
    if not wallet.has_pin():
        messages.warning(request, 'Please set up your PIN before requesting a withdrawal.')
        return redirect('economy:pin_setup')
    
    # Check if payment method configured
    if not wallet.has_payment_method():
        messages.warning(request, 'Please add a payment method before requesting a withdrawal.')
        return redirect('economy:payment_methods')
    
    # Check available balance
    if wallet.available_balance <= 0:
        messages.error(request, 'Insufficient balance for withdrawal.')
        return redirect('economy:wallet_dashboard')
    
    if request.method == 'POST':
        form = WithdrawalRequestForm(request.POST, wallet=wallet)
        if form.is_valid():
            withdrawal = form.save()
            messages.success(
                request,
                f'Withdrawal request submitted! Amount: {withdrawal.amount} DC via {withdrawal.get_payment_method_display()}. '
                'Your request will be reviewed by our team.'
            )
            return redirect('economy:withdrawal_status', pk=withdrawal.pk)
    else:
        form = WithdrawalRequestForm(wallet=wallet)
    
    # Get recent withdrawals
    recent_withdrawals = wallet.withdrawal_requests.all()[:5]
    
    context = {
        'wallet': wallet,
        'form': form,
        'recent_withdrawals': recent_withdrawals,
    }
    return render(request, 'economy/withdrawal_request.html', context)


@login_required
def withdrawal_status_view(request, pk):
    """
    View status of specific withdrawal request.
    Allows cancellation if status is pending.
    """
    profile = request.user.profile
    withdrawal = get_object_or_404(
        WithdrawalRequest,
        pk=pk,
        wallet__profile=profile
    )
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'cancel' and withdrawal.can_cancel:
            try:
                withdrawal.cancel()
                messages.success(request, 'Withdrawal request cancelled successfully.')
            except ValueError as e:
                messages.error(request, str(e))
        
        return redirect('economy:withdrawal_status', pk=pk)
    
    context = {
        'withdrawal': withdrawal,
    }
    return render(request, 'economy/withdrawal_status.html', context)


@login_required
def withdrawal_history_view(request):
    """
    List all withdrawal requests for current user.
    With filtering by status and pagination.
    """
    profile = request.user.profile
    wallet = get_object_or_404(DeltaCrownWallet, profile=profile)
    
    # Get status filter
    status_filter = request.GET.get('status', '')
    
    withdrawals = wallet.withdrawal_requests.all()
    
    if status_filter:
        withdrawals = withdrawals.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(withdrawals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Calculate totals
    total_requested = sum(w.amount for w in withdrawals)
    total_completed = sum(w.amount for w in withdrawals.filter(status='completed'))
    total_pending = sum(w.amount for w in withdrawals.filter(status='pending'))
    
    context = {
        'wallet': wallet,
        'page_obj': page_obj,
        'status_filter': status_filter,
        'total_requested': total_requested,
        'total_completed': total_completed,
        'total_pending': total_pending,
        'status_choices': WithdrawalRequest.Status.choices,
    }
    return render(request, 'economy/withdrawal_history.html', context)


@login_required
def payment_methods_view(request):
    """
    Manage payment methods (bKash, Nagad, Rocket, Bank).
    """
    profile = request.user.profile
    wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
    
    if request.method == 'POST':
        form = PaymentMethodForm(request.POST, instance=wallet)
        if form.is_valid():
            form.save()
            messages.success(request, 'Payment methods updated successfully.')
            return redirect('economy:payment_methods')
    else:
        form = PaymentMethodForm(instance=wallet)
    
    context = {
        'wallet': wallet,
        'form': form,
    }
    return render(request, 'economy/payment_methods.html', context)


@login_required
def pin_setup_view(request):
    """
    Set up or change 4-digit PIN.
    """
    profile = request.user.profile
    wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
    
    if request.method == 'POST':
        form = PINSetupForm(request.POST)
        if form.is_valid():
            pin = form.cleaned_data['pin']
            wallet.set_pin(pin)
            messages.success(request, 'PIN set up successfully. You can now request withdrawals.')
            return redirect('economy:wallet_dashboard')
    else:
        form = PINSetupForm()
    
    context = {
        'wallet': wallet,
        'form': form,
        'has_pin': wallet.has_pin(),
    }
    return render(request, 'economy/pin_setup.html', context)


@login_required
def wallet_dashboard_view(request):
    """
    Wallet dashboard showing balance, transactions, and withdrawal options.
    """
    profile = request.user.profile
    wallet, created = DeltaCrownWallet.objects.get_or_create(profile=profile)
    
    # Get recent transactions
    recent_transactions = DeltaCrownTransaction.objects.filter(
        wallet=wallet
    ).order_by('-created_at')[:10]
    
    # Get pending withdrawals
    pending_withdrawals = wallet.withdrawal_requests.filter(
        status=WithdrawalRequest.Status.PENDING
    )
    
    # Calculate stats
    total_earned = DeltaCrownTransaction.objects.filter(
        wallet=wallet,
        amount__gt=0
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    total_withdrawn = wallet.withdrawal_requests.filter(
        status=WithdrawalRequest.Status.COMPLETED
    ).aggregate(total=models.Sum('amount'))['total'] or 0
    
    context = {
        'wallet': wallet,
        'recent_transactions': recent_transactions,
        'pending_withdrawals': pending_withdrawals,
        'total_earned': total_earned,
        'total_withdrawn': total_withdrawn,
        'has_pin': wallet.has_pin(),
        'has_payment_method': wallet.has_payment_method(),
    }
    return render(request, 'economy/wallet_dashboard.html', context)
