"""Verify CTA buttons and description text."""
import requests
import re

r = requests.get('http://127.0.0.1:8000/teams/vnext/')
section = re.search(r'Tournament Arena.*?GLOBAL STANDINGS', r.text, re.DOTALL)
if section:
    s = section.group(0)
    
    # Find CTA area
    cta_area = re.search(r'class="flex gap-2 mt-4"(.*?)</div>\s*</div>', s, re.DOTALL)
    if cta_area:
        print('=== CTA HTML ===')
        print(cta_area.group(0)[:600])
    
    # Description text
    desc = re.search(r'text-gray-300 text-sm[^>]*>(.*?)</p>', s, re.DOTALL)
    if desc:
        print('\n=== Description ===')
        print(desc.group(1).strip()[:300])
    
    # Check for <strong> or <p> tags showing as text
    if '<strong>' in s or '&lt;strong&gt;' in s:
        print('\n[BAD] Found raw HTML tags')
    else:
        print('\n[OK] No raw HTML tags visible')
    
    # Check Register button
    reg = re.search(r'Register Now', s)
    if reg:
        print('[OK] "Register Now" CTA found')
    
    # Check image
    img = re.search(r'<img[^>]+src="([^"]+)"', s)
    if img:
        print(f'[OK] Card image: {img.group(1)}')
