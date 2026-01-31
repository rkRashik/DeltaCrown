import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.conf import settings

db_config = settings.DATABASES['default']
print(f"Database Name: {db_config['NAME']}")
print(f"Database Host: {db_config.get('HOST', 'localhost')}")
print(f"Database Port: {db_config.get('PORT', '5432')}")
print(f"Database User: {db_config.get('USER', 'N/A')}")
