"""
Example unit tests for the User model.

This file demonstrates best practices for testing Django models.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from datetime import date, timedelta

from tests.factories import UserFactory, PlayerFactory, OrganizerFactory, AdminUserFactory

User = get_user_model()


@pytest.mark.unit
@pytest.mark.models
class TestUserModel:
    """Test suite for User model."""
    
    def test_create_user(self, db):
        """Test creating a basic user."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.check_password("TestPass123!")
        assert user.is_active is True
        assert user.is_staff is False
        assert user.is_superuser is False
    
    def test_create_superuser(self, db):
        """Test creating a superuser."""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminPass123!"
        )
        
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.role == "ADMIN"
    
    def test_user_str_representation(self, user):
        """Test User __str__ method."""
        assert str(user) == user.username
    
    def test_user_full_name_property(self):
        """Test full_name property."""
        user = UserFactory(first_name="John", last_name="Doe")
        assert user.full_name == "John Doe"
    
    def test_user_full_name_empty(self):
        """Test full_name when no first/last name."""
        user = UserFactory(first_name="", last_name="")
        assert user.full_name == user.username
    
    def test_user_age_property(self):
        """Test age calculation."""
        birth_date = date.today() - timedelta(days=365 * 25)  # 25 years ago
        user = UserFactory(date_of_birth=birth_date)
        assert user.age == 25
    
    def test_user_age_none_when_no_birthdate(self, user):
        """Test age is None when no date_of_birth."""
        user.date_of_birth = None
        user.save()
        assert user.age is None
    
    def test_role_choices(self):
        """Test different user roles."""
        player = PlayerFactory()
        organizer = OrganizerFactory()
        admin = AdminUserFactory()
        
        assert player.role == "PLAYER"
        assert organizer.role == "ORGANIZER"
        assert admin.role == "ADMIN"
    
    def test_is_player_property(self):
        """Test is_player property."""
        player = PlayerFactory()
        organizer = OrganizerFactory()
        
        assert player.is_player is True
        assert organizer.is_player is False
    
    def test_is_organizer_property(self):
        """Test is_organizer property."""
        player = PlayerFactory()
        organizer = OrganizerFactory()
        
        assert player.is_organizer is False
        assert organizer.is_organizer is True
    
    def test_is_admin_role_property(self):
        """Test is_admin_role property."""
        player = PlayerFactory()
        admin = AdminUserFactory()
        
        assert player.is_admin_role is False
        assert admin.is_admin_role is True
    
    def test_mark_email_verified(self, user):
        """Test marking email as verified."""
        assert user.is_verified is False
        assert user.email_verified_at is None
        
        user.mark_email_verified()
        
        assert user.is_verified is True
        assert user.email_verified_at is not None
    
    def test_email_uniqueness(self, user):
        """Test that email must be unique."""
        with pytest.raises(Exception):  # IntegrityError
            User.objects.create_user(
                username="another_user",
                email=user.email,  # Duplicate email
                password="TestPass123!"
            )
    
    def test_username_uniqueness(self, user):
        """Test that username must be unique."""
        with pytest.raises(Exception):  # IntegrityError
            User.objects.create_user(
                username=user.username,  # Duplicate username
                email="different@example.com",
                password="TestPass123!"
            )
    
    def test_uuid_field_auto_generated(self, user):
        """Test that UUID is automatically generated."""
        assert user.uuid is not None
        assert str(user.uuid) != ""
    
    def test_uuid_uniqueness(self):
        """Test that UUIDs are unique."""
        user1 = UserFactory()
        user2 = UserFactory()
        assert user1.uuid != user2.uuid


@pytest.mark.unit
@pytest.mark.models
class TestUserManager:
    """Test suite for User manager."""
    
    def test_create_user_with_email(self, db):
        """Test creating user with email."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!"
        )
        assert user.email == "test@example.com"
    
    def test_create_user_without_username_raises_error(self, db):
        """Test that creating user without username raises error."""
        with pytest.raises(ValueError, match="The Username field must be set"):
            User.objects.create_user(
                username="",
                email="test@example.com",
                password="TestPass123!"
            )
    
    def test_create_superuser(self, db):
        """Test creating superuser through manager."""
        admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="AdminPass123!"
        )
        
        assert admin.is_staff is True
        assert admin.is_superuser is True


@pytest.mark.unit
@pytest.mark.models
class TestUserQuerySets:
    """Test custom querysets and filters."""
    
    def test_filter_by_role(self):
        """Test filtering users by role."""
        PlayerFactory.create_batch(3)
        OrganizerFactory.create_batch(2)
        AdminUserFactory()
        
        players = User.objects.filter(role="PLAYER")
        organizers = User.objects.filter(role="ORGANIZER")
        admins = User.objects.filter(role="ADMIN")
        
        assert players.count() == 3
        assert organizers.count() == 2
        assert admins.count() == 1
    
    def test_filter_verified_users(self):
        """Test filtering verified users."""
        UserFactory.create_batch(3, is_verified=False)
        UserFactory.create_batch(2, is_verified=True)
        
        verified = User.objects.filter(is_verified=True)
        unverified = User.objects.filter(is_verified=False)
        
        assert verified.count() == 2
        assert unverified.count() == 3


@pytest.mark.unit
@pytest.mark.models  
class TestUserValidation:
    """Test model validation."""
    
    def test_bio_max_length(self):
        """Test bio field max length validation."""
        long_bio = "x" * 501  # Exceeds 500 char limit
        user = UserFactory.build(bio=long_bio)
        
        with pytest.raises(ValidationError):
            user.full_clean()
    
    def test_phone_number_optional(self):
        """Test phone number is optional."""
        user = UserFactory(phone_number=None)
        assert user.phone_number is None
    
    def test_date_of_birth_optional(self):
        """Test date of birth is optional."""
        user = UserFactory(date_of_birth=None)
        assert user.date_of_birth is None
