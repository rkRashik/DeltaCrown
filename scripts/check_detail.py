"""Quick script to inspect tournament detail page + team hub rendering."""
import requests
import re

# === TOURNAMENT DETAIL PAGE ===
print("=" * 60)
print("TOURNAMENT DETAIL PAGE")
print("=" * 60)
r = requests.get('http://127.0.0.1:8000/tournaments/efootball-the-genesis-cup/')
print(f"Status: {r.status_code}")

# Check image paths — should be /media/ not /static/ for game assets
imgs = re.findall(r'<img[^>]+src="([^"]+)"', r.text)
print("\n=== Images ===")
for img in imgs:
    flag = " [WRONG: should be /media/]" if "/static/games/" in img else ""
    print(f"  {img}{flag}")

# Check for game asset paths
print("\n=== Game asset paths ===")
for m in re.findall(r'/(?:static|media)/games/[^\s"<>]+', r.text):
    flag = " [OK]" if "/media/" in m else " [WRONG]"
    print(f"  {m}{flag}")

# === TEAM HUB PAGE ===
print("\n" + "=" * 60)
print("TEAM HUB PAGE - TOURNAMENT ARENA")
print("=" * 60)
r2 = requests.get('http://127.0.0.1:8000/teams/vnext/')
print(f"Status: {r2.status_code}")

# Check for raw HTML tags in tournament description
arena_match = re.search(r'Tournament Arena.*?(?=<!-- GLOBAL STANDINGS|$)', r2.text, re.DOTALL)
if arena_match:
    section = arena_match.group(0)
    
    # Check for raw <p>, <strong> tags in visible text
    raw_html = re.findall(r'<p class="text-gray-300[^>]*>([^<]*<(?:p|strong|/p|/strong)[^<]*)</p>', section)
    if raw_html:
        print("\n[BAD] Raw HTML in description:")
        for h in raw_html:
            print(f"  {h[:100]}")
    else:
        print("\n[OK] No raw HTML tags in description")
    
    # Check for game images
    card_imgs = re.findall(r'<img[^>]+src="([^"]+)"', section)
    if card_imgs:
        print(f"\n[OK] Tournament card images: {card_imgs}")
    else:
        print("\n[CHECK] No images in tournament card section")
    
    # Check CTA buttons
    ctas = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]+(?:<[^>]+>[^<]*)*)</a>', section)
    print(f"\n=== CTA Links ===")
    for href, text in ctas[:5]:
        clean_text = re.sub(r'<[^>]+>', '', text).strip()
        print(f"  [{clean_text}] -> {href}")
else:
    print("\nCouldn't find Tournament Arena section")

print("\nDone.")
