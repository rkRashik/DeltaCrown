import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
def test_create_staff_user_directly():
    """Test creating staff user with different methods"""
    
    # Method 1: create_user with is_staff
    user1 = User.objects.create_user(
        username="staff1",
        email="staff1@test.com",
        password="pass123",
        is_staff=True
    )
    print(f"Method 1 (create_user with is_staff): is_staff={user1.is_staff}")
    
    # Method 2: create then set is_staff
    user2 = User.objects.create_user(
        username="staff2",
        email="staff2@test.com",
        password="pass123"
    )
    user2.is_staff = True
    user2.save()
    user2.refresh_from_db()
    print(f"Method 2 (create then set): is_staff={user2.is_staff}")
    
    # Method 3: create with User.objects.create
    user3 = User.objects.create(
        username="staff3",
        email="staff3@test.com",
        is_staff=True
    )
    user3.set_password("pass123")
    user3.save()
    user3.refresh_from_db()
    print(f"Method 3 (create with set_password): is_staff={user3.is_staff}")
    
    assert user2.is_staff is True, "Method 2 should work"
    assert user3.is_staff is True, "Method 3 should work"
