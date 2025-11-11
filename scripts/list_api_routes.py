"""
Quick script to list API routes for Module 6.3 audit.
"""
import django
import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver


def collect_patterns(resolver, prefix=''):
    """Recursively collect all URL patterns."""
    patterns = []
    for pattern in resolver.url_patterns:
        if isinstance(pattern, URLResolver):
            patterns.extend(collect_patterns(pattern, prefix + str(pattern.pattern)))
        else:
            patterns.append(prefix + str(pattern.pattern))
    return patterns


def main():
    resolver = get_resolver()
    all_patterns = collect_patterns(resolver)
    
    # Filter for API tournament routes
    keywords = ['api/tournaments', 'bracket', 'match', 'result', 'analytics', 'certificate', 'payout']
    
    print("=" * 80)
    print("API TOURNAMENT ROUTES AUDIT - Module 6.3")
    print("=" * 80)
    
    relevant = [p for p in all_patterns if any(k in p for k in keywords)]
    
    for pattern in sorted(relevant):
        print(pattern)
    
    print("\n" + "=" * 80)
    print(f"Total routes found: {len(relevant)}")
    print("=" * 80)


if __name__ == '__main__':
    main()
