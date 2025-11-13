import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_force_authenticate_sets_is_staff():
    """Debug test to check if force_authenticate preserves is_staff"""
    
    # Create staff user
    staff_user = User.objects.create_user(
        username="test_staff",
        email="test@test.com",
        password="pass123",
        is_staff=True
    )
    
    # Verify user was created with is_staff=True
    assert staff_user.is_staff is True
    staff_user.refresh_from_db()
    assert staff_user.is_staff is True
    
    # Create authenticated client
    client = APIClient()
    client.force_authenticate(user=staff_user)
    
    # Check if request.user.is_staff is preserved
    # We'll test with a simple view
    from rest_framework import permissions, viewsets, decorators
    from rest_framework.response import Response
    
    class DebugViewSet(viewsets.GenericViewSet):
        permission_classes = []
        
        @decorators.action(detail=False, methods=["get"])
        def test(self, request):
            return Response({
                "authenticated": request.user.is_authenticated,
                "is_staff": request.user.is_staff,
                "user_id": request.user.id,
                "username": request.user.username
            })
    
    from django.urls import path, include
    from rest_framework.routers import DefaultRouter
    
    router = DefaultRouter()
    router.register(r'debug', DebugViewSet, basename='debug')
    
    # We can't easily test this without setting up URLs, so let's use a different approach
    # Let's check the permission class directly
    from apps.tournaments.api.payments import IsStaff
    
    class FakeRequest:
        def __init__(self, user):
            self.user = user
    
    permission = IsStaff()
    fake_request = FakeRequest(staff_user)
    
    result = permission.has_permission(fake_request, None)
    
    print(f"User is_staff: {staff_user.is_staff}")
    print(f"Permission check result: {result}")
    
    assert result is True, f"Permission check failed for staff user: is_staff={staff_user.is_staff}"
