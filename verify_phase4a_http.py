"""
Phase 4A: HTTP-based verification (no Django test client dependency)
"""
import requests
import json

BASE_URL = 'http://localhost:8000'

print("\n" + "="*70)
print("PHASE 4A: HTTP RUNTIME VERIFICATION")
print("="*70 + "\n")

# Test 1: Games API
print("[TEST 1] Games API")
print("-" * 70)
try:
    response = requests.get(f'{BASE_URL}/api/games/')
    print(f"GET /api/games/ → Status {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Returned {len(data)} games")
        if len(data) > 0:
            print(f"  First game: {data[0]['name']}")
    else:
        print(f"❌ Failed: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Profile Pages
print("\n[TEST 2] Profile Page Access")
print("-" * 70)

# Test existing user if possible
try:
    # Try to access a profile
    response = requests.get(f'{BASE_URL}/me/', allow_redirects=False)
    print(f"GET /me/ → Status {response.status_code}")
    
    if response.status_code == 302:
        print("✅ Redirect (expected for unauthenticated user)")
    elif response.status_code == 200:
        print("✅ Page loaded")
    else:
        print(f"❌ Unexpected status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Settings Page
print("\n[TEST 3] Settings Page")
print("-" * 70)
try:
    response = requests.get(f'{BASE_URL}/me/settings/', allow_redirects=False)
    print(f"GET /me/settings/ → Status {response.status_code}")
    
    if response.status_code in [302, 200]:
        print("✅ Settings endpoint exists")
    else:
        print(f"❌ Failed: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 4: Passport Creation Endpoint
print("\n[TEST 4] Passport Creation Endpoint")
print("-" * 70)
try:
    response = requests.post(f'{BASE_URL}/api/passports/create/', 
                            json={'game_id': 1, 'ign': 'test'},
                            allow_redirects=False)
    print(f"POST /api/passports/create/ → Status {response.status_code}")
    
    if response.status_code == 401 or response.status_code == 403:
        print("✅ Endpoint exists (requires auth)")
    elif response.status_code == 200:
        print("✅ Endpoint works")
    elif response.status_code == 400:
        print("✅ Endpoint exists (validation error expected)")
    elif response.status_code == 404:
        print("❌ Endpoint NOT FOUND")
    else:
        print(f"⚠️  Unexpected status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 5: Follow Endpoints
print("\n[TEST 5] Follow System Endpoints")
print("-" * 70)
try:
    response = requests.post(f'{BASE_URL}/actions/follow/testuser/', allow_redirects=False)
    print(f"POST /actions/follow/testuser/ → Status {response.status_code}")
    
    if response.status_code in [401, 403]:
        print("✅ Endpoint exists (requires auth)")
    elif response.status_code == 404:
        print("❌ Endpoint NOT FOUND")
    else:
        print(f"⚠️  Status: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "="*70)
print("HTTP VERIFICATION COMPLETE")
print("="*70)
print("\n⚠️  Note: Most endpoints require authentication")
print("Next: Fix any 404s, then test authenticated flows")
