"""Tests for email or username login functionality."""
import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.backends import EmailOrUsernameBackend

User = get_user_model()


@pytest.fixture
def verified_user():
    """Create a verified user for testing login."""
    user = User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="TestPass123!",
        is_active=True,
        is_verified=True,
    )
    return user


@pytest.mark.django_db
def test_login_with_username(client, verified_user):
    """Test that users can login with their username."""
    url = reverse("account:login")
    data = {
        "username": "testuser",
        "password": "TestPass123!",
    }
    resp = client.post(url, data, follow=True)
    assert resp.status_code == 200
    
    # Check that user is authenticated
    assert resp.wsgi_request.user.is_authenticated
    assert resp.wsgi_request.user.username == "testuser"


@pytest.mark.django_db
def test_login_with_email(client, verified_user):
    """Test that users can login with their email address."""
    url = reverse("account:login")
    data = {
        "username": "test@example.com",  # Field name is 'username' but we're using email
        "password": "TestPass123!",
    }
    resp = client.post(url, data, follow=True)
    assert resp.status_code == 200
    
    # Check that user is authenticated
    assert resp.wsgi_request.user.is_authenticated
    assert resp.wsgi_request.user.email == "test@example.com"


@pytest.mark.django_db
def test_login_with_email_case_insensitive(client, verified_user):
    """Test that email login is case-insensitive."""
    url = reverse("account:login")
    data = {
        "username": "TEST@EXAMPLE.COM",  # Uppercase email
        "password": "TestPass123!",
    }
    resp = client.post(url, data, follow=True)
    assert resp.status_code == 200
    
    # Check that user is authenticated
    assert resp.wsgi_request.user.is_authenticated
    assert resp.wsgi_request.user.email == "test@example.com"


@pytest.mark.django_db
def test_login_with_username_case_insensitive(client, verified_user):
    """Test that username login is case-insensitive."""
    url = reverse("account:login")
    data = {
        "username": "TESTUSER",  # Uppercase username
        "password": "TestPass123!",
    }
    resp = client.post(url, data, follow=True)
    assert resp.status_code == 200
    
    # Check that user is authenticated
    assert resp.wsgi_request.user.is_authenticated
    assert resp.wsgi_request.user.username == "testuser"


@pytest.mark.django_db
def test_login_with_wrong_password(client, verified_user):
    """Test that login fails with incorrect password."""
    url = reverse("account:login")
    data = {
        "username": "testuser",
        "password": "WrongPassword123!",
    }
    resp = client.post(url, data)
    assert resp.status_code == 200  # Returns to login page
    
    # Check that user is NOT authenticated
    assert not resp.wsgi_request.user.is_authenticated
    assert "Please enter a correct" in resp.content.decode()


@pytest.mark.django_db
def test_login_with_nonexistent_user(client):
    """Test that login fails with non-existent user."""
    url = reverse("account:login")
    data = {
        "username": "nonexistent@example.com",
        "password": "SomePassword123!",
    }
    resp = client.post(url, data)
    assert resp.status_code == 200  # Returns to login page
    
    # Check that user is NOT authenticated
    assert not resp.wsgi_request.user.is_authenticated


@pytest.mark.django_db
def test_backend_authenticate_with_username(verified_user):
    """Test the backend directly with username."""
    backend = EmailOrUsernameBackend()
    user = backend.authenticate(
        request=None,
        username="testuser",
        password="TestPass123!"
    )
    assert user is not None
    assert user.username == "testuser"


@pytest.mark.django_db
def test_backend_authenticate_with_email(verified_user):
    """Test the backend directly with email."""
    backend = EmailOrUsernameBackend()
    user = backend.authenticate(
        request=None,
        username="test@example.com",
        password="TestPass123!"
    )
    assert user is not None
    assert user.email == "test@example.com"


@pytest.mark.django_db
def test_backend_authenticate_fails_with_wrong_password(verified_user):
    """Test the backend returns None with wrong password."""
    backend = EmailOrUsernameBackend()
    user = backend.authenticate(
        request=None,
        username="testuser",
        password="WrongPassword"
    )
    assert user is None


@pytest.mark.django_db
def test_backend_authenticate_fails_with_inactive_user():
    """Test the backend returns None for inactive users."""
    inactive_user = User.objects.create_user(
        username="inactive",
        email="inactive@example.com",
        password="TestPass123!",
        is_active=False,
    )
    backend = EmailOrUsernameBackend()
    user = backend.authenticate(
        request=None,
        username="inactive",
        password="TestPass123!"
    )
    assert user is None


@pytest.mark.django_db
def test_login_page_shows_correct_label(client):
    """Test that the login page shows 'Username or Email' label."""
    url = reverse("account:login")
    resp = client.get(url)
    assert resp.status_code == 200
    content = resp.content.decode()
    
    # Check for the updated label
    assert "Username or Email" in content
    # Check for the updated placeholder
    assert "Enter your username or email" in content
