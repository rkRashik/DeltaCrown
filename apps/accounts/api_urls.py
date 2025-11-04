"""
DeltaCrown - Authentication API URLs
====================================
API endpoints for JWT authentication and user management.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenVerifyView

from .api_views import (
    RegisterView,
    LoginView,
    LogoutView,
    UserProfileView,
    ChangePasswordView,
    RefreshTokenView,
    UserListView,
)

app_name = 'auth_api'

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    
    # Token Management
    path('token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # User Profile
    path('me/', UserProfileView.as_view(), name='user_profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # User Management (Admin/Organizer)
    path('users/', UserListView.as_view(), name='user_list'),
]
