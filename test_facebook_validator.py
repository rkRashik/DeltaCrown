#!/usr/bin/env python
"""Quick test of Facebook video URL validation."""

from apps.user_profile.services.url_validator import validate_highlight_url

# Test cases
test_urls = [
    "https://www.facebook.com/share/v/17b9XarFZY/",
    "https://www.facebook.com/watch/?v=1234567890",
    "https://www.facebook.com/username/videos/1234567890",
    "https://www.facebook.com/reel/1234567890",
    "https://fb.watch/abc123xyz",
    "https://www.facebook.com/profile/page",  # Should fail - not video
]

print("Testing Facebook video URL validation:\n")

for url in test_urls:
    result = validate_highlight_url(url)
    status = "✅ VALID" if result['valid'] else "❌ INVALID"
    print(f"{status}: {url}")
    
    if result['valid']:
        print(f"  Platform: {result['platform']}")
        print(f"  Video ID: {result['video_id']}")
        print(f"  Embed URL: {result['embed_url'][:80]}...")
    else:
        print(f"  Error: {result['error']}")
    print()
