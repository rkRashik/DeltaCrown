"""Custom authentication backends for DeltaCrown."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    """
    Authenticate using either username or email address.
    This allows users to log in with either their username or email.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        UserModel = get_user_model()
        
        try:
            # Try to find user by username or email (case-insensitive)
            user = UserModel.objects.get(
                Q(username__iexact=username) | Q(email__iexact=username)
            )
        except UserModel.DoesNotExist:
            # Run the default password hasher once to reduce timing
            # difference between existing and non-existing users
            UserModel().set_password(password)
            return None
        except UserModel.MultipleObjectsReturned:
            # If multiple users are returned, try to get by username first
            user = UserModel.objects.filter(username__iexact=username).first()
            if not user:
                return None

        # Check password and verify user is active
        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None
