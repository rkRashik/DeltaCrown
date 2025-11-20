"""
Quick test to verify the new hero template structure
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.template import Template, Context
from apps.tournaments.models import Tournament

# Get a test tournament
tournament = Tournament.objects.filter(status__in=['published', 'registration_open', 'live']).first()

if not tournament:
    print("❌ No tournaments found for testing")
    exit(1)

print(f"✅ Testing with tournament: {tournament.name}")
print(f"   Status: {tournament.status}")
print(f"   Game: {tournament.game.name if tournament.game else 'None'}")

# Read the hero template
template_path = 'templates/tournaments/detailPages/partials/detail/hero.html'
with open(template_path, 'r', encoding='utf-8') as f:
    template_content = f.read()

# Check for new structure elements
checks = {
    'td-hero-banner': 'Full-width banner container',
    'td-hero-banner-frame': 'Banner frame',
    'td-hero-action': 'Action strip container',
    'td-hero-action-left': 'Identity zone',
    'td-hero-action-center': 'Info zone',
    'td-hero-action-right': 'CTA zone',
    'action-title': 'Tournament title',
    'action-cta-button': 'CTA button',
    'info-countdown': 'Countdown display',
    'info-entry-fee': 'Entry fee display',
    'info-prize-pool': 'Prize pool display',
}

print("\n📋 Structure Verification:")
for class_name, description in checks.items():
    if class_name in template_content:
        print(f"   ✅ {description} ({class_name})")
    else:
        print(f"   ❌ {description} ({class_name})")

# Check CSS file
css_path = 'static/tournaments/detailPages/css/detail.css'
with open(css_path, 'r', encoding='utf-8') as f:
    css_content = f.read()

css_checks = {
    '.td-hero-banner': 'Banner styles',
    '.td-hero-action': 'Action strip styles',
    'aspect-ratio: 21 / 9': 'Cinematic aspect ratio',
    'grid-template-columns: minmax(0, 1.8fr) minmax(0, 2fr) minmax(0, 1.4fr)': '3-column grid',
    '@keyframes heroFadeIn': 'Hero fade animation',
    '@keyframes actionStripSlideUp': 'Action strip animation',
}

print("\n🎨 CSS Verification:")
for selector, description in css_checks.items():
    if selector in css_content:
        print(f"   ✅ {description}")
    else:
        print(f"   ❌ {description}")

print("\n✨ Hero redesign verification complete!")
print(f"\n💡 Test the hero live at: /tournaments/{tournament.slug}/")
