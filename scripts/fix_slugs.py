#!/usr/bin/env python
"""Fix empty slugs in UserProfile"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.user_profile.models import UserProfile
from django.utils.text import slugify

profiles_with_empty_slug = UserProfile.objects.filter(slug='')
fixed_count = 0
used_slugs = set(UserProfile.objects.exclude(slug='').values_list('slug', flat=True))

for profile in profiles_with_empty_slug:
    base_slug = slugify(profile.display_name) or f'user-{profile.id}'
    slug = base_slug
    counter = 1
    
    while slug in used_slugs:
        slug = f'{base_slug}-{counter}'
        counter += 1
    
    profile.slug = slug
    used_slugs.add(slug)
    profile.save(update_fields=['slug'])
    fixed_count += 1

print(f'✅ Fixed {fixed_count} empty slugs')
