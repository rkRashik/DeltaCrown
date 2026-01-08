import django
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.contrib import admin
from apps.user_profile.models_main import UserProfile

ma = admin.site._registry[UserProfile]
print('✅ Registered fieldsets for UserProfile admin:')
for fs in ma.fieldsets:
    print(f'  📁 {fs[0]}')
    if fs[1].get('fields'):
        for field in fs[1]['fields']:
            print(f'     - {field}')
