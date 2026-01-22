"""
PHASE4_STEP4_2: Simulate browser clicking Followers/Following
Tests the actual endpoints with browser-like headers to trigger middleware logging
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_followers_following_browser():
    """Simulate browser requests to followers/following endpoints"""
    
    # Create session to handle cookies
    session = requests.Session()
    
    print("\n" + "="*80)
    print("PHASE4_STEP4_2: Browser Simulation Test")
    print("="*80)
    
    # Test 1: Visit profile page first (get CSRF token)
    print("\n1. Loading profile page...")
    profile_response = session.get(f"{BASE_URL}/@userA/")
    print(f"   Status: {profile_response.status_code}")
    
    # Extract CSRF token from cookies
    csrf_token = session.cookies.get('csrftoken', '')
    
    # Test 2: Click Followers (AJAX request)
    print("\n2. Clicking Followers (AJAX)...")
    followers_response = session.get(
        f"{BASE_URL}/api/profile/userA/followers/",
        headers={
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f"{BASE_URL}/@userA/",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        }
    )
    print(f"   Status: {followers_response.status_code}")
    print(f"   Content-Type: {followers_response.headers.get('Content-Type')}")
    
    if followers_response.status_code == 200:
        try:
            data = followers_response.json()
            print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            
            # Check for deprecated keywords
            body_str = json.dumps(data).lower()
            if any(keyword in body_str for keyword in ['deprecated', 'gone', 'legacy']):
                print("   ⚠️  WARNING: Response contains deprecation keywords!")
            else:
                print("   ✅ No deprecation keywords found")
        except Exception as e:
            print(f"   ❌ Error parsing JSON: {e}")
            print(f"   Body: {followers_response.text[:200]}")
    else:
        print(f"   Body: {followers_response.text[:200]}")
    
    # Test 3: Click Following (AJAX request)
    print("\n3. Clicking Following (AJAX)...")
    following_response = session.get(
        f"{BASE_URL}/api/profile/userA/following/",
        headers={
            'Accept': 'application/json',
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': f"{BASE_URL}/@userA/",
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
        }
    )
    print(f"   Status: {following_response.status_code}")
    print(f"   Content-Type: {following_response.headers.get('Content-Type')}")
    
    if following_response.status_code == 200:
        try:
            data = following_response.json()
            print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            
            # Check for deprecated keywords
            body_str = json.dumps(data).lower()
            if any(keyword in body_str for keyword in ['deprecated', 'gone', 'legacy']):
                print("   ⚠️  WARNING: Response contains deprecation keywords!")
            else:
                print("   ✅ No deprecation keywords found")
        except Exception as e:
            print(f"   ❌ Error parsing JSON: {e}")
            print(f"   Body: {following_response.text[:200]}")
    else:
        print(f"   Body: {following_response.text[:200]}")
    
    # Test 4: Try potential legacy endpoints (if they exist)
    print("\n4. Testing potential legacy endpoints...")
    legacy_paths = [
        "/@userA/followers/",
        "/@userA/following/",
        "/profile/userA/followers/",
        "/profile/userA/following/",
    ]
    
    for path in legacy_paths:
        response = session.get(f"{BASE_URL}{path}")
        print(f"   {path}: {response.status_code}")
        if response.status_code not in [404, 405]:
            print(f"      Content-Type: {response.headers.get('Content-Type')}")
            if 'json' in response.headers.get('Content-Type', ''):
                try:
                    data = response.json()
                    if 'deprecated' in json.dumps(data).lower():
                        print(f"      ⚠️  DEPRECATED ENDPOINT FOUND!")
                        print(f"      Body: {json.dumps(data)}")
                except:
                    pass
    
    print("\n" + "="*80)
    print("Check server terminal for [DEPRECATED_TRACE] logs")
    print("="*80 + "\n")


if __name__ == '__main__':
    try:
        test_followers_following_browser()
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Server not running at http://127.0.0.1:8000")
        print("Start server with: python manage.py runserver 8000")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
