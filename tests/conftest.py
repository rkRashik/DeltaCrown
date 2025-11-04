"""
Pytest configuration and fixtures for DeltaCrown test suite.

This file provides shared fixtures, configuration, and utilities
for all test modules.
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

User = get_user_model()


# =====================================================
# Django Database Configuration
# =====================================================

@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Custom database setup for test session.
    Loads initial data and creates necessary database objects.
    """
    with django_db_blocker.unblock():
        # Run migrations
        call_command("migrate", "--no-input")
        
        # Load fixtures if needed
        # call_command("loaddata", "initial_data.json")


@pytest.fixture(scope="function")
def db_with_data(db):
    """
    Fixture that provides a database with initial test data.
    """
    # Add any common test data here
    pass


# =====================================================
# User Fixtures
# =====================================================

@pytest.fixture
def user_data():
    """
    Returns valid user registration data.
    """
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "TestPass123!",
        "first_name": "Test",
        "last_name": "User",
        "role": "PLAYER",
    }


@pytest.fixture
def user(db):
    """
    Creates and returns a regular user (PLAYER).
    """
    return User.objects.create_user(
        username="player1",
        email="player1@example.com",
        password="TestPass123!",
        first_name="Player",
        last_name="One",
        role="PLAYER",
        is_active=True,
    )


@pytest.fixture
def verified_user(db):
    """
    Creates and returns a verified user.
    """
    user = User.objects.create_user(
        username="verified_player",
        email="verified@example.com",
        password="TestPass123!",
        role="PLAYER",
        is_active=True,
    )
    user.mark_email_verified()
    return user


@pytest.fixture
def organizer(db):
    """
    Creates and returns an organizer user.
    """
    return User.objects.create_user(
        username="organizer1",
        email="organizer1@example.com",
        password="TestPass123!",
        first_name="Organizer",
        last_name="One",
        role="ORGANIZER",
        is_active=True,
    )


@pytest.fixture
def admin_user(db):
    """
    Creates and returns an admin user.
    """
    return User.objects.create_user(
        username="admin1",
        email="admin1@example.com",
        password="TestPass123!",
        first_name="Admin",
        last_name="User",
        role="ADMIN",
        is_staff=True,
        is_superuser=True,
        is_active=True,
    )


@pytest.fixture
def multiple_users(db):
    """
    Creates and returns multiple users with different roles.
    """
    users = {
        "player1": User.objects.create_user(
            username="player1",
            email="player1@example.com",
            password="TestPass123!",
            role="PLAYER",
        ),
        "player2": User.objects.create_user(
            username="player2",
            email="player2@example.com",
            password="TestPass123!",
            role="PLAYER",
        ),
        "organizer": User.objects.create_user(
            username="organizer1",
            email="organizer1@example.com",
            password="TestPass123!",
            role="ORGANIZER",
        ),
        "admin": User.objects.create_user(
            username="admin1",
            email="admin1@example.com",
            password="TestPass123!",
            role="ADMIN",
            is_staff=True,
        ),
    }
    return users


# =====================================================
# API Client Fixtures
# =====================================================

@pytest.fixture
def api_client():
    """
    Returns an unauthenticated DRF API client.
    """
    return APIClient()


@pytest.fixture
def authenticated_client(user):
    """
    Returns an API client authenticated as a regular user.
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def organizer_client(organizer):
    """
    Returns an API client authenticated as an organizer.
    """
    client = APIClient()
    client.force_authenticate(user=organizer)
    return client


@pytest.fixture
def admin_client(admin_user):
    """
    Returns an API client authenticated as an admin.
    """
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


# =====================================================
# JWT Token Fixtures
# =====================================================

@pytest.fixture
def user_tokens(user):
    """
    Returns JWT tokens for a user.
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
    }


@pytest.fixture
def auth_headers(user_tokens):
    """
    Returns authentication headers with JWT token.
    """
    return {
        "HTTP_AUTHORIZATION": f"Bearer {user_tokens['access']}"
    }


# =====================================================
# Email Testing Fixtures
# =====================================================

@pytest.fixture
def mailoutbox(settings):
    """
    Provides access to Django's mail outbox for testing emails.
    """
    from django.core import mail
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    return mail.outbox


# =====================================================
# File Upload Fixtures
# =====================================================

@pytest.fixture
def sample_image():
    """
    Creates a sample image file for testing uploads.
    """
    from io import BytesIO
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    # Create a simple image
    image = Image.new("RGB", (100, 100), color="red")
    image_io = BytesIO()
    image.save(image_io, format="JPEG")
    image_io.seek(0)
    
    return SimpleUploadedFile(
        name="test_image.jpg",
        content=image_io.read(),
        content_type="image/jpeg"
    )


# =====================================================
# Cache Fixtures
# =====================================================

@pytest.fixture
def clear_cache():
    """
    Clears the cache before and after tests.
    """
    from django.core.cache import cache
    cache.clear()
    yield
    cache.clear()


# =====================================================
# Settings Override Fixtures
# =====================================================

@pytest.fixture
def disable_throttling(settings):
    """
    Disables DRF throttling for tests.
    """
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = []
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}


# =====================================================
# Pytest Configuration Hooks
# =====================================================

def pytest_configure(config):
    """
    Configure pytest with custom markers and settings.
    """
    config.addinivalue_line(
        "markers",
        "unit: Mark test as a unit test"
    )
    config.addinivalue_line(
        "markers",
        "integration: Mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "slow: Mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "api: Mark test as an API test"
    )
    config.addinivalue_line(
        "markers",
        "models: Mark test as a model test"
    )
    config.addinivalue_line(
        "markers",
        "views: Mark test as a view test"
    )
    config.addinivalue_line(
        "markers",
        "serializers: Mark test as a serializer test"
    )


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Give all tests access to the database by default.
    """
    pass


# =====================================================
# Test Utilities
# =====================================================

@pytest.fixture
def assert_valid_response():
    """
    Utility to assert API response validity.
    """
    def _assert_valid_response(response, status_code=200, has_data=True):
        assert response.status_code == status_code, \
            f"Expected {status_code}, got {response.status_code}: {response.data}"
        
        if has_data and status_code < 400:
            assert response.data is not None, "Response should contain data"
        
        return response.data
    
    return _assert_valid_response


@pytest.fixture
def create_test_user():
    """
    Factory fixture to create test users with custom attributes.
    """
    def _create_user(**kwargs):
        defaults = {
            "username": f"testuser_{User.objects.count()}",
            "email": f"testuser{User.objects.count()}@example.com",
            "password": "TestPass123!",
            "role": "PLAYER",
            "is_active": True,
        }
        defaults.update(kwargs)
        
        password = defaults.pop("password")
        user = User.objects.create_user(**defaults)
        user.set_password(password)
        user.save()
        
        return user
    
    return _create_user
