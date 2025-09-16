"""Signal handlers for user profile creation."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **kwargs):
    """Ensure every user always has an associated profile."""

    defaults = {"display_name": getattr(instance, "username", "") or instance.get_full_name()}
    UserProfile.objects.get_or_create(user=instance, defaults=defaults)
