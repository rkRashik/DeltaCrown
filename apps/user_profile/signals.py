from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_profile(sender, instance, created, **_):
    defaults = {"display_name": instance.username or instance.email}
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults=defaults)
    else:
        UserProfile.objects.get_or_create(user=instance, defaults=defaults)
