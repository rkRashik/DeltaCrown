# apps/economy/urls.py
from django.urls import path
from .views.wallet import wallet_view, wallet_transactions_view
from .views import withdrawal
from . import inventory_api

# UP-PHASE7.1: Economy request API (top-up and withdrawal requests)
from .views.request_views import topup_request, withdraw_request, get_wallet_requests

# UP-PHASE7.2: Wallet PIN security API
from .views.pin_views import pin_setup, pin_verify

# UP-PHASE7.7: OTP verification for PIN security
from .views.otp_views import otp_request, otp_verify_and_set_pin

app_name = "economy"

urlpatterns = [
    # UP-PHASE7.7: Old wallet page redirects to Settings
    path("wallet/", wallet_view, name="wallet"),
    
    # Wallet Dashboard
    path('wallet/dashboard/', withdrawal.wallet_dashboard_view, name='wallet_dashboard'),
    # Backwards compatibility / short links used in templates
    path('deposit/', wallet_transactions_view, name='deposit'),
    path('withdraw/', withdrawal.withdrawal_request_view, name='withdraw'),
    path('transactions/', wallet_transactions_view, name='transaction_history'),
    
    # Withdrawal
    path('withdrawal/request/', withdrawal.withdrawal_request_view, name='withdrawal_request'),
    path('withdrawal/<int:pk>/', withdrawal.withdrawal_status_view, name='withdrawal_status'),
    path('withdrawal/history/', withdrawal.withdrawal_history_view, name='withdrawal_history'),
    
    # Payment Methods
    path('payment-methods/', withdrawal.payment_methods_view, name='payment_methods'),
    
    # PIN
    path('pin/setup/', withdrawal.pin_setup_view, name='pin_setup'),
    
    # ========== Phase 3A: Inventory System ==========
    # Inventory viewing
    path('me/inventory/', inventory_api.my_inventory_view, name='my_inventory'),
    path('profiles/<str:username>/inventory/', inventory_api.user_inventory_view, name='user_inventory'),
    
    # Phase 4A: Inventory Requests Inbox
    path('me/inventory/requests/', inventory_api.my_requests_view, name='my_requests'),
    
    # Gifting
    path('me/inventory/gift/', inventory_api.gift_item_view, name='gift_item'),
    
    # Trading
    path('me/inventory/trade/request/', inventory_api.trade_request_view, name='trade_request'),
    path('me/inventory/trade/respond/', inventory_api.trade_respond_view, name='trade_respond'),
    
    # UP-PHASE7.1: Economy Request APIs (top-up and withdrawal with admin approval)
    path('api/topup/request/', topup_request, name='topup_request'),
    path('api/withdraw/request/', withdraw_request, name='withdraw_request'),
    path('api/wallet/requests/', get_wallet_requests, name='wallet_requests'),  # NEW: Get user's requests
    
    # UP-PHASE7.2: Wallet PIN Security APIs
    path('api/wallet/pin/setup/', pin_setup, name='pin_setup'),
    path('api/wallet/pin/verify/', pin_verify, name='pin_verify'),
    
    # UP-PHASE7.7: OTP Security for PIN Setup/Change
    path('api/wallet/pin/otp/request/', otp_request, name='pin_otp_request'),
    path('api/wallet/pin/otp/verify/', otp_verify_and_set_pin, name='pin_otp_verify'),
]

