"""
DeltaCrown - Authentication API Views
=====================================
REST API endpoints for user authentication using JWT tokens.
"""
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
)

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """
    User Registration Endpoint
    
    POST /api/auth/register/
    
    Creates a new user account. User will be inactive until email is verified.
    
    Request Body:
    {
        "username": "player1",
        "email": "player@example.com",
        "password": "SecurePass123!",
        "password_confirm": "SecurePass123!",
        "first_name": "John",
        "last_name": "Doe",
        "phone_number": "+8801234567890",
        "country": "Bangladesh",
        "role": "PLAYER"  // Optional: PLAYER, ORGANIZER
    }
    
    Response (201 Created):
    {
        "message": "Registration successful. Please check your email to verify your account.",
        "user": {
            "id": 1,
            "uuid": "...",
            "username": "player1",
            "email": "player@example.com",
            ...
        }
    }
    """
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Send welcome email (async in production with Celery)
        self._send_welcome_email(user)
        
        return Response(
            {
                'message': 'Registration successful. Please check your email to verify your account.',
                'user': UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )
    
    def _send_welcome_email(self, user):
        """Send welcome email to new user."""
        try:
            subject = 'Welcome to DeltaCrown Tournament Engine!'
            message = f"""
            Hello {user.username},
            
            Welcome to DeltaCrown Tournament Engine!
            
            Your account has been created successfully. Please verify your email address to activate your account.
            
            Account Details:
            - Username: {user.username}
            - Email: {user.email}
            - Role: {user.get_role_display()}
            
            If you didn't create this account, please ignore this email.
            
            Best regards,
            DeltaCrown Team
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=True,
            )
        except Exception as e:
            # Log error but don't fail registration
            print(f"Failed to send welcome email: {e}")


class LoginView(TokenObtainPairView):
    """
    User Login Endpoint
    
    POST /api/auth/login/
    
    Authenticate user with email or username and return JWT tokens.
    
    Request Body:
    {
        "email_or_username": "player1",  // or "player@example.com"
        "password": "SecurePass123!"
    }
    
    Response (200 OK):
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
        "user": {
            "id": 1,
            "username": "player1",
            "email": "player@example.com",
            "role": "PLAYER",
            ...
        }
    }
    """
    serializer_class = LoginSerializer
    permission_classes = [AllowAny]


class LogoutView(APIView):
    """
    User Logout Endpoint
    
    POST /api/auth/logout/
    
    Blacklist the refresh token to prevent reuse.
    
    Request Body:
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    
    Response (200 OK):
    {
        "message": "Logout successful"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {'message': 'Logout successful'},
            status=status.HTTP_200_OK
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """
    User Profile Endpoint
    
    GET /api/auth/me/
    Retrieve authenticated user's profile.
    
    Response (200 OK):
    {
        "id": 1,
        "uuid": "...",
        "username": "player1",
        "email": "player@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "full_name": "John Doe",
        "role": "PLAYER",
        "phone_number": "+8801234567890",
        "date_of_birth": "1995-01-15",
        "age": 30,
        "country": "Bangladesh",
        "avatar": "/media/avatars/...",
        "bio": "Professional esports player",
        "is_verified": true,
        "date_joined": "2025-11-04T10:00:00Z",
        "last_login": "2025-11-04T12:00:00Z"
    }
    
    PATCH /api/auth/me/
    Update authenticated user's profile (partial update).
    
    Request Body:
    {
        "first_name": "John",
        "last_name": "Smith",
        "phone_number": "+8801234567890",
        "country": "Bangladesh",
        "bio": "Updated bio"
    }
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        """Return the authenticated user."""
        return self.request.user
    
    def get_serializer_class(self):
        """Use different serializer for updates."""
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserSerializer
    
    def update(self, request, *args, **kwargs):
        """Update user profile."""
        partial = kwargs.pop('partial', True)  # Always allow partial updates
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        # Return full user data
        return Response(
            UserSerializer(instance).data,
            status=status.HTTP_200_OK
        )


class ChangePasswordView(APIView):
    """
    Change Password Endpoint
    
    POST /api/auth/change-password/
    
    Change authenticated user's password.
    
    Request Body:
    {
        "old_password": "OldPass123!",
        "new_password": "NewPass123!",
        "new_password_confirm": "NewPass123!"
    }
    
    Response (200 OK):
    {
        "message": "Password changed successfully"
    }
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            {'message': 'Password changed successfully'},
            status=status.HTTP_200_OK
        )


class RefreshTokenView(TokenRefreshView):
    """
    Token Refresh Endpoint
    
    POST /api/auth/token/refresh/
    
    Get a new access token using a valid refresh token.
    
    Request Body:
    {
        "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    
    Response (200 OK):
    {
        "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
    """
    pass  # Uses default TokenRefreshView behavior


class UserListView(generics.ListAPIView):
    """
    User List Endpoint (Admin/Organizer only)
    
    GET /api/auth/users/
    
    List all users (paginated).
    
    Query Parameters:
    - role: Filter by role (PLAYER, ORGANIZER, ADMIN)
    - is_verified: Filter by verification status (true/false)
    - search: Search by username, email, name
    
    Response (200 OK):
    {
        "count": 100,
        "next": "http://api.example.com/auth/users/?page=2",
        "previous": null,
        "results": [
            {
                "id": 1,
                "username": "player1",
                ...
            }
        ]
    }
    """
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter users based on permissions and query params."""
        user = self.request.user
        queryset = User.objects.all()
        
        # Only admin and organizers can see all users
        if not (user.is_staff or user.is_organizer):
            # Regular users can only see verified users
            queryset = queryset.filter(is_verified=True)
        
        # Apply filters
        role = self.request.query_params.get('role')
        if role:
            queryset = queryset.filter(role=role)
        
        is_verified = self.request.query_params.get('is_verified')
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified.lower() == 'true')
        
        # Search
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                username__icontains=search
            ) | queryset.filter(
                email__icontains=search
            ) | queryset.filter(
                first_name__icontains=search
            ) | queryset.filter(
                last_name__icontains=search
            )
        
        return queryset.order_by('-date_joined')
