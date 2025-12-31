import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.user_profile.services.url_validator import validate_highlight_url

test_urls = [
    'https://www.facebook.com/share/v/17b9XarFZY/',
    'https://www.facebook.com/watch/?v=1234567890',
    'https://fb.watch/abc123xyz',
    'https://www.facebook.com/profile/page',
]

print('Testing Facebook video URL validation:')
print()
for url in test_urls:
    result = validate_highlight_url(url)
    if result['valid']:
        print(f'✅ VALID: {url}')
        print(f'   Video ID: {result["video_id"]}')
        print(f'   Embed: {result["embed_url"][:70]}...')
    else:
        print(f'❌ INVALID: {url}')
        print(f'   Error: {result["error"]}')
    print()
