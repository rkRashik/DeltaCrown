"""
Factory Boy factories for creating test data.

Factories provide a convenient way to create model instances
with default or custom attributes for testing.
"""

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory
from faker import Faker

fake = Faker()
User = get_user_model()


class UserFactory(DjangoModelFactory):
    """
    Factory for creating User instances.
    
    Usage:
        # Create a user with default values
        user = UserFactory()
        
        # Create a user with custom values
        user = UserFactory(username="custom_user", email="custom@example.com")
        
        # Create multiple users
        users = UserFactory.create_batch(5)
        
        # Create a user without saving to database
        user = UserFactory.build()
    """
    
    class Meta:
        model = User
        django_get_or_create = ("username",)
    
    # Basic fields
    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    
    # Authentication
    password = factory.PostGenerationMethodCall("set_password", "TestPass123!")
    is_active = True
    is_staff = False
    is_superuser = False
    
    # Custom fields
    role = "PLAYER"
    phone_number = factory.Faker("phone_number")
    date_of_birth = factory.Faker("date_of_birth", minimum_age=18, maximum_age=50)
    country = factory.Faker("country")
    bio = factory.Faker("text", max_nb_chars=200)
    
    # Verification
    is_verified = False
    email_verified_at = None


class VerifiedUserFactory(UserFactory):
    """
    Factory for creating verified users.
    
    Usage:
        verified_user = VerifiedUserFactory()
    """
    
    is_verified = True
    email_verified_at = factory.Faker("date_time_this_year")


class PlayerFactory(UserFactory):
    """
    Factory for creating player users.
    
    Usage:
        player = PlayerFactory()
    """
    
    role = "PLAYER"


class OrganizerFactory(UserFactory):
    """
    Factory for creating organizer users.
    
    Usage:
        organizer = OrganizerFactory()
    """
    
    role = "ORGANIZER"
    is_verified = True
    email_verified_at = factory.Faker("date_time_this_year")


class AdminUserFactory(UserFactory):
    """
    Factory for creating admin users.
    
    Usage:
        admin = AdminUserFactory()
    """
    
    role = "ADMIN"
    is_staff = True
    is_superuser = True
    is_verified = True
    email_verified_at = factory.Faker("date_time_this_year")


class SuperUserFactory(UserFactory):
    """
    Factory for creating superuser instances.
    
    Usage:
        superuser = SuperUserFactory()
    """
    
    is_staff = True
    is_superuser = True
    role = "ADMIN"


# =====================================================
# Future Factories (Placeholders)
# =====================================================

# Uncomment and implement as needed when models are created

# class TournamentFactory(DjangoModelFactory):
#     """Factory for creating Tournament instances."""
#     
#     class Meta:
#         model = "tournaments.Tournament"
#     
#     name = factory.Faker("sentence", nb_words=4)
#     description = factory.Faker("paragraph")
#     organizer = factory.SubFactory(OrganizerFactory)
#     start_date = factory.Faker("future_datetime", end_date="+30d")
#     end_date = factory.LazyAttribute(
#         lambda obj: fake.future_datetime(end_date="+60d")
#     )
#     max_teams = factory.Faker("random_int", min=8, max=64)
#     entry_fee = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)


# class TeamFactory(DjangoModelFactory):
#     """Factory for creating Team instances."""
#     
#     class Meta:
#         model = "teams.Team"
#     
#     name = factory.Faker("company")
#     captain = factory.SubFactory(PlayerFactory)
#     description = factory.Faker("paragraph")


# class MatchFactory(DjangoModelFactory):
#     """Factory for creating Match instances."""
#     
#     class Meta:
#         model = "tournaments.Match"
#     
#     tournament = factory.SubFactory(TournamentFactory)
#     team1 = factory.SubFactory(TeamFactory)
#     team2 = factory.SubFactory(TeamFactory)
#     scheduled_time = factory.Faker("future_datetime")
