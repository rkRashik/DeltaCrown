"""Test frontend API response"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.user_profile.views.dynamic_content_api import get_available_games
from django.http import HttpRequest
import json

req = HttpRequest()
req.method = 'GET'
resp = get_available_games(req)
data = json.loads(resp.content)

valorant = [g for g in data['games'] if g['slug'] == 'valorant'][0]

print(f"\n✅ VALORANT API Response:")
print(f"   Total fields: {len(valorant['identity_fields'])}")
print(f"\n📋 Field Details:")

for field in valorant['identity_fields']:
    options_count = len(field.get('options', []))
    print(f"   • {field['key']}: required={field.get('required')}, options={options_count}")
    if options_count > 0:
        print(f"     First 2 options: {field['options'][:2]}")
