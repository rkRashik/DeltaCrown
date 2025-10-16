from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission

class Command(BaseCommand):
    help = 'Grant all permissions to all superusers'

    def handle(self, *args, **options):
        User = get_user_model()
        superusers = User.objects.filter(is_superuser=True)
        if not superusers:
            self.stderr.write(self.style.ERROR('No superusers found'))
            return

        all_perms = Permission.objects.all()
        for user in superusers:
            user.user_permissions.set(all_perms)
            user.is_staff = True
            user.save()
            self.stdout.write(self.style.SUCCESS(f'All permissions granted to superuser: {user.username}'))

        self.stdout.write(self.style.SUCCESS(f'Granted permissions to {superusers.count()} superuser(s)'))
