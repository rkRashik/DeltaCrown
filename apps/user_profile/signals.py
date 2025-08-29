from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import UserProfile


@receiver(post_save, sender=User)
def create_profile_on_user_create(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance, defaults={"display_name": instance.username})
    else:
        # make sure we never lose the profile (e.g., users imported without profile)
        UserProfile.objects.get_or_create(user=instance)