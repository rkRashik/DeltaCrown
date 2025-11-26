# apps/economy/urls.py
from django.urls import path
from .views.wallet import wallet_view
from .views import withdrawal

app_name = "economy"

urlpatterns = [
    path("wallet/", wallet_view, name="wallet"),
    
    # Wallet Dashboard
    path('wallet/dashboard/', withdrawal.wallet_dashboard_view, name='wallet_dashboard'),
    
    # Withdrawal
    path('withdrawal/request/', withdrawal.withdrawal_request_view, name='withdrawal_request'),
    path('withdrawal/<int:pk>/', withdrawal.withdrawal_status_view, name='withdrawal_status'),
    path('withdrawal/history/', withdrawal.withdrawal_history_view, name='withdrawal_history'),
    
    # Payment Methods
    path('payment-methods/', withdrawal.payment_methods_view, name='payment_methods'),
    
    # PIN
    path('pin/setup/', withdrawal.pin_setup_view, name='pin_setup'),
]
