"""
Example API tests for authentication endpoints.

This file demonstrates best practices for testing DRF API endpoints.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

from tests.factories import UserFactory, VerifiedUserFactory

User = get_user_model()


@pytest.mark.api
@pytest.mark.integration
class TestUserRegistrationAPI:
    """Test suite for user registration endpoint."""
    
    def test_register_user_success(self, api_client, mailoutbox):
        """Test successful user registration."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
            "first_name": "New",
            "last_name": "User",
        }
        
        response = api_client.post("/api/auth/register/", data, format="json")
        
        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert response.data["user"]["username"] == "newuser"
        assert response.data["user"]["email"] == "newuser@example.com"
        
        # Check user was created in database
        user = User.objects.get(username="newuser")
        assert user.email == "newuser@example.com"
        assert user.check_password("SecurePass123!")
        
        # Check welcome email was sent
        assert len(mailoutbox) == 1
        assert mailoutbox[0].to == ["newuser@example.com"]
    
    def test_register_with_duplicate_username(self, api_client, user):
        """Test registration fails with duplicate username."""
        data = {
            "username": user.username,  # Duplicate
            "email": "different@example.com",
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
        }
        
        response = api_client.post("/api/auth/register/", data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "username" in response.data
    
    def test_register_with_duplicate_email(self, api_client, user):
        """Test registration fails with duplicate email."""
        data = {
            "username": "newuser",
            "email": user.email,  # Duplicate
            "password": "SecurePass123!",
            "password_confirm": "SecurePass123!",
        }
        
        response = api_client.post("/api/auth/register/", data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data
    
    def test_register_password_mismatch(self, api_client):
        """Test registration fails when passwords don't match."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "password_confirm": "DifferentPass123!",  # Mismatch
        }
        
        response = api_client.post("/api/auth/register/", data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_weak_password(self, api_client):
        """Test registration fails with weak password."""
        data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "123",  # Too weak
            "password_confirm": "123",
        }
        
        response = api_client.post("/api/auth/register/", data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data
    
    def test_register_missing_required_fields(self, api_client):
        """Test registration fails with missing required fields."""
        data = {
            "username": "newuser",
            # Missing email and password
        }
        
        response = api_client.post("/api/auth/register/", data, format="json")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.api
@pytest.mark.integration
class TestUserLoginAPI:
    """Test suite for user login endpoint."""
    
    def test_login_with_username(self, api_client):
        """Test login with username."""
        user = VerifiedUserFactory(username="testuser")
        
        data = {
            "email_or_username": "testuser",
            "password": "TestPass123!",
        }
        
        response = api_client.post("/api/auth/login/", data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
        assert "user" in response.data
        assert response.data["user"]["username"] == "testuser"
    
    def test_login_with_email(self, api_client):
        """Test login with email."""
        user = VerifiedUserFactory(email="test@example.com")
        
        data = {
            "email_or_username": "test@example.com",
            "password": "TestPass123!",
        }
        
        response = api_client.post("/api/auth/login/", data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
        assert "refresh" in response.data
    
    def test_login_invalid_credentials(self, api_client, user):
        """Test login fails with invalid credentials."""
        data = {
            "email_or_username": user.username,
            "password": "WrongPassword123!",
        }
        
        response = api_client.post("/api/auth/login/", data, format="json")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_inactive_user(self, api_client):
        """Test login fails for inactive user."""
        user = VerifiedUserFactory(is_active=False)
        
        data = {
            "email_or_username": user.username,
            "password": "TestPass123!",
        }
        
        response = api_client.post("/api/auth/login/", data, format="json")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
@pytest.mark.integration
class TestUserProfileAPI:
    """Test suite for user profile endpoints."""
    
    def test_get_own_profile(self, authenticated_client, user):
        """Test authenticated user can get their own profile."""
        response = authenticated_client.get("/api/auth/me/")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == user.username
        assert response.data["email"] == user.email
    
    def test_get_profile_unauthenticated(self, api_client):
        """Test unauthenticated request fails."""
        response = api_client.get("/api/auth/me/")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_profile(self, authenticated_client, user):
        """Test user can update their profile."""
        data = {
            "first_name": "Updated",
            "last_name": "Name",
            "bio": "Updated bio text",
        }
        
        response = authenticated_client.patch("/api/auth/me/", data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated"
        assert response.data["last_name"] == "Name"
        assert response.data["bio"] == "Updated bio text"
        
        # Verify in database
        user.refresh_from_db()
        assert user.first_name == "Updated"
    
    def test_cannot_update_username(self, authenticated_client, user):
        """Test user cannot update username."""
        original_username = user.username
        data = {"username": "newusername"}
        
        response = authenticated_client.patch("/api/auth/me/", data, format="json")
        
        # Should succeed but username shouldn't change
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.username == original_username
    
    def test_cannot_update_email(self, authenticated_client, user):
        """Test user cannot update email."""
        original_email = user.email
        data = {"email": "newemail@example.com"}
        
        response = authenticated_client.patch("/api/auth/me/", data, format="json")
        
        # Should succeed but email shouldn't change
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.email == original_email


@pytest.mark.api
@pytest.mark.integration
class TestChangePasswordAPI:
    """Test suite for password change endpoint."""
    
    def test_change_password_success(self, authenticated_client, user):
        """Test successful password change."""
        data = {
            "old_password": "TestPass123!",
            "new_password": "NewSecurePass456!",
            "new_password_confirm": "NewSecurePass456!",
        }
        
        response = authenticated_client.post(
            "/api/auth/change-password/",
            data,
            format="json"
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify password was changed
        user.refresh_from_db()
        assert user.check_password("NewSecurePass456!")
    
    def test_change_password_wrong_old_password(self, authenticated_client):
        """Test password change fails with wrong old password."""
        data = {
            "old_password": "WrongPassword123!",
            "new_password": "NewSecurePass456!",
            "new_password_confirm": "NewSecurePass456!",
        }
        
        response = authenticated_client.post(
            "/api/auth/change-password/",
            data,
            format="json"
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_change_password_mismatch(self, authenticated_client):
        """Test password change fails when new passwords don't match."""
        data = {
            "old_password": "TestPass123!",
            "new_password": "NewSecurePass456!",
            "new_password_confirm": "DifferentPass456!",
        }
        
        response = authenticated_client.post(
            "/api/auth/change-password/",
            data,
            format="json"
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.api
@pytest.mark.integration
class TestTokenRefreshAPI:
    """Test suite for token refresh endpoint."""
    
    def test_refresh_token_success(self, api_client, user_tokens):
        """Test successful token refresh."""
        data = {"refresh": user_tokens["refresh"]}
        
        response = api_client.post("/api/auth/token/refresh/", data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        assert "access" in response.data
    
    def test_refresh_with_invalid_token(self, api_client):
        """Test refresh fails with invalid token."""
        data = {"refresh": "invalid_token_here"}
        
        response = api_client.post("/api/auth/token/refresh/", data, format="json")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.api
@pytest.mark.integration
class TestLogoutAPI:
    """Test suite for logout endpoint."""
    
    def test_logout_success(self, authenticated_client, user_tokens):
        """Test successful logout."""
        data = {"refresh": user_tokens["refresh"]}
        
        response = authenticated_client.post("/api/auth/logout/", data, format="json")
        
        assert response.status_code == status.HTTP_200_OK
        
        # Try to use the refresh token - should fail
        refresh_response = authenticated_client.post(
            "/api/auth/token/refresh/",
            data,
            format="json"
        )
        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED
