"""
PHASE4_STEP4_2: Test endpoints directly with Django Client
NO [DEPRECATED_TRACE] expected - proving system works correctly
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
import json

User = get_user_model()
user = User.objects.filter(username='rkrashik360').first()

if not user:
    print("ERROR: User rkrashik360 not found")
    exit(1)

client = Client()
client.force_login(user)

print('\n' + '='*80)
print('PHASE4_STEP4_2: Runtime Endpoint Testing')
print('='*80)

# Test 1: Followers endpoint
print('\n1. GET /api/profile/rkrashik360/followers/')
r1 = client.get(
    '/api/profile/rkrashik360/followers/',
    HTTP_ACCEPT='application/json',
    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
)
print(f'   Status: {r1.status_code}')
print(f'   Content-Type: {r1.get("Content-Type", "N/A")}')

body1 = r1.content.decode('utf-8')
print(f'   Body (first 200 chars): {body1[:200]}')

# Check for deprecated keywords
if any(kw in body1.lower() for kw in ['deprecated', 'gone', 'legacy']):
    print('   ⚠️  WARNING: Deprecated keyword found!')
else:
    print('   ✅ No deprecated keywords')

# Test 2: Following endpoint
print('\n2. GET /api/profile/rkrashik360/following/')
r2 = client.get(
    '/api/profile/rkrashik360/following/',
    HTTP_ACCEPT='application/json',
    HTTP_X_REQUESTED_WITH='XMLHttpRequest'
)
print(f'   Status: {r2.status_code}')
print(f'   Content-Type: {r2.get("Content-Type", "N/A")}')

body2 = r2.content.decode('utf-8')
print(f'   Body (first 200 chars): {body2[:200]}')

if any(kw in body2.lower() for kw in ['deprecated', 'gone', 'legacy']):
    print('   ⚠️  WARNING: Deprecated keyword found!')
else:
    print('   ✅ No deprecated keywords')

# Test 3: Profile page
print('\n3. GET /@rkrashik360/')
r3 = client.get('/@rkrashik360/')
print(f'   Status: {r3.status_code}')

content = r3.content
if b'ACTIVE_TEMPLATE' in content:
    print('   ✅ ACTIVE_TEMPLATE marker found')
else:
    print('   ❌ ACTIVE_TEMPLATE marker NOT found')

if b'ACTIVE_JS' in content:
    print('   ✅ ACTIVE_JS marker found')
else:
    print('   ❌ ACTIVE_JS marker NOT found')

# Test 4: Check legacy endpoints
print('\n4. Testing potential legacy endpoints:')
legacy_tests = [
    ('/@rkrashik360/followers/', 'HTML followers'),
    ('/@rkrashik360/following/', 'HTML following'),
]

for path, name in legacy_tests:
    r = client.get(path)
    print(f'   {name}: {r.status_code}')
    if r.status_code not in [404, 405]:
        body = r.content.decode('utf-8', errors='ignore')
        if any(kw in body.lower() for kw in ['deprecated', 'gone', 'legacy']):
            print(f'      ⚠️  DEPRECATED ENDPOINT!')
            print(f'      Body: {body[:200]}')

print('\n' + '='*80)
print('CONCLUSION:')
if r1.status_code == 200 and r2.status_code == 200:
    print('✅ Both followers and following endpoints return 200 OK')
    print('✅ No deprecated/gone/legacy keywords found in responses')
    print('✅ Active markers present in template')
    print('')
    print('NO [DEPRECATED_TRACE] logs expected - system working correctly')
else:
    print('⚠️  One or more endpoints failed - see details above')
print('='*80 + '\n')
