"""
DeltaCrown - Authentication API Serializers
===========================================
Serializers for user registration, login, and profile management.
"""
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model - used for profile display.
    """
    age = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id',
            'uuid',
            'username',
            'email',
            'first_name',
            'last_name',
            'full_name',
            'role',
            'phone_number',
            'date_of_birth',
            'age',
            'country',
            'avatar',
            'bio',
            'is_verified',
            'email_verified_at',
            'date_joined',
            'last_login',
        ]
        read_only_fields = [
            'id',
            'uuid',
            'email',
            'is_verified',
            'email_verified_at',
            'date_joined',
            'last_login',
        ]


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    Validates email uniqueness, password strength, and creates new user.
    """
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = [
            'username',
            'email',
            'password',
            'password_confirm',
            'first_name',
            'last_name',
            'phone_number',
            'country',
            'role',
        ]
        extra_kwargs = {
            'first_name': {'required': False},
            'last_name': {'required': False},
            'phone_number': {'required': False},
            'country': {'required': False},
            'role': {'required': False},
        }
    
    def validate(self, attrs):
        """Validate password confirmation matches."""
        if attrs.get('password') != attrs.get('password_confirm'):
            raise ValidationError({"password_confirm": "Passwords do not match."})
        return attrs
    
    def validate_email(self, value):
        """Ensure email is unique."""
        if User.objects.filter(email__iexact=value).exists():
            raise ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_username(self, value):
        """Ensure username is unique and valid."""
        if User.objects.filter(username__iexact=value).exists():
            raise ValidationError("A user with this username already exists.")
        return value
    
    def create(self, validated_data):
        """Create new user with validated data."""
        # Remove password_confirm as it's not a model field
        validated_data.pop('password_confirm', None)
        
        # Extract password
        password = validated_data.pop('password')
        
        # Create user (inactive until email verified)
        user = User.objects.create_user(
            password=password,
            is_active=False,  # Will be activated after email verification
            **validated_data
        )
        
        return user


class LoginSerializer(TokenObtainPairSerializer):
    """
    Custom JWT token serializer that supports email or username login.
    Returns access token, refresh token, and user data.
    """
    username_field = 'email_or_username'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Replace username field with email_or_username
        self.fields['email_or_username'] = serializers.CharField()
        self.fields.pop('username', None)
    
    @classmethod
    def get_token(cls, user):
        """Customize token claims."""
        token = super().get_token(user)
        
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        token['is_verified'] = user.is_verified
        
        return token
    
    def validate(self, attrs):
        """Validate credentials and return tokens with user data."""
        email_or_username = attrs.get('email_or_username')
        password = attrs.get('password')
        
        # Try to authenticate
        user = None
        
        # Try email first
        if '@' in email_or_username:
            try:
                user_obj = User.objects.get(email__iexact=email_or_username)
                user = authenticate(
                    request=self.context.get('request'),
                    username=user_obj.username,
                    password=password
                )
            except User.DoesNotExist:
                pass
        else:
            # Try username
            user = authenticate(
                request=self.context.get('request'),
                username=email_or_username,
                password=password
            )
        
        if not user:
            raise ValidationError(
                {'detail': 'Invalid credentials. Please check your email/username and password.'}
            )
        
        if not user.is_active:
            raise ValidationError(
                {'detail': 'Account is inactive. Please verify your email or contact support.'}
            )
        
        # Get tokens
        refresh = self.get_token(user)
        
        data = {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserSerializer(user).data
        }
        
        return data


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating user profile.
    Email and username cannot be changed.
    """
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'phone_number',
            'date_of_birth',
            'country',
            'avatar',
            'bio',
        ]
    
    def validate_bio(self, value):
        """Ensure bio doesn't exceed max length."""
        if value and len(value) > 500:
            raise ValidationError("Bio cannot exceed 500 characters.")
        return value
    
    def validate_date_of_birth(self, value):
        """Ensure date of birth is in the past."""
        from django.utils import timezone
        if value and value >= timezone.now().date():
            raise ValidationError("Date of birth must be in the past.")
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer for changing user password.
    """
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate_old_password(self, value):
        """Verify old password is correct."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise ValidationError("Old password is incorrect.")
        return value
    
    def validate(self, attrs):
        """Ensure new passwords match."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise ValidationError({"new_password_confirm": "New passwords do not match."})
        return attrs
    
    def save(self, **kwargs):
        """Update user password."""
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LogoutSerializer(serializers.Serializer):
    """
    Serializer for logout - blacklists the refresh token.
    """
    refresh = serializers.CharField(required=True)
    
    def validate(self, attrs):
        """Validate and blacklist refresh token."""
        self.token = attrs['refresh']
        return attrs
    
    def save(self, **kwargs):
        """Blacklist the refresh token."""
        try:
            token = RefreshToken(self.token)
            token.blacklist()
        except Exception as e:
            raise ValidationError({'detail': 'Invalid or expired token.'})
