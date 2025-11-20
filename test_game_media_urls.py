"""
Test script to verify game media URL resolution
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.common.game_registry import get_all_games

print("=" * 80)
print("GAME MEDIA URL ANALYSIS")
print("=" * 80)

games = get_all_games()

for game in games[:3]:  # Test first 3 games
    print(f"\n🎮 {game.display_name} ({game.slug})")
    print(f"   Database ID: {game.database_id}")
    print(f"   Active: {game.is_active}")
    
    # Analyze icon
    if game.icon:
        is_url = game.icon.startswith('/') or '://' in game.icon
        icon_type = "Full URL (DB)" if is_url else "Static Path (ASSETS)"
        print(f"   ✅ Icon: {icon_type}")
        print(f"      Value: {game.icon}")
    else:
        print(f"   ❌ Icon: Missing")
    
    # Analyze banner
    if game.banner:
        is_url = game.banner.startswith('/') or '://' in game.banner
        banner_type = "Full URL (DB)" if is_url else "Static Path (ASSETS)"
        print(f"   ✅ Banner: {banner_type}")
        print(f"      Value: {game.banner}")
    else:
        print(f"   ❌ Banner: Missing")
    
    # Analyze logo
    if game.logo:
        is_url = game.logo.startswith('/') or '://' in game.logo
        logo_type = "Full URL (DB)" if is_url else "Static Path (ASSETS)"
        print(f"   ✅ Logo: {logo_type}")
        print(f"      Value: {game.logo}")
    else:
        print(f"   ❌ Logo: Missing")

print("\n" + "=" * 80)
print("TEMPLATE LOGIC EXPLANATION")
print("=" * 80)

print("""
The hero template now uses smart URL detection:

1. If game_spec.banner starts with "/" or contains "://":
   → It's a full URL from the database ImageField
   → Use directly: <img src="{{ game_spec.banner }}">

2. If game_spec.banner is a relative path (no "/" or "://"):
   → It's a static path from GAME_ASSETS
   → Wrap in static tag: <img src="{% static game_spec.banner %}">

3. If game_spec.banner is empty:
   → Fall back to tournament.banner_image (if exists)
   → Or show fallback with game icon + initials

This ensures compatibility with BOTH:
- Database-uploaded images (e.g., /media/game_banners/efootball.jpg)
- Static asset paths (e.g., img/game_banners/valorant_banner.jpg)
""")

print("\n" + "=" * 80)
print("HOW TO UPLOAD IMAGES IN DJANGO ADMIN")
print("=" * 80)

print("""
To add real banner/icon images for a game:

1. Go to Django Admin: /admin/tournaments/game/
2. Click on a game (e.g., "eFootball")
3. In the edit form, you'll see these fields:
   - Icon: Upload a small square image (e.g., 128x128px)
   - Banner: Upload a wide banner (e.g., 1920x810px for 21:9 ratio)
   - Logo: Upload a logo with transparency (optional)
   - Card Image: Upload a card image (optional)

4. Upload the images and save
5. The GameSpec will now have FULL URLS like:
   - icon: "/media/game_icons/efootball_icon.png"
   - banner: "/media/game_banners/efootball_banner.jpg"

6. The hero template will detect these are full URLs and use them directly

IMPORTANT: Media files must be served correctly:
- In development: Django serves MEDIA_URL automatically
- In production: Nginx/Cloudflare must serve MEDIA_ROOT
""")

print("\n✅ Test complete! Check the output above to verify URL resolution.\n")
