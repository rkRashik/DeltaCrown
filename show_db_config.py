import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.conf import settings

print(f"Database: {settings.DATABASES['default']}")
