#!/usr/bin/env python3
"""
Phase 3.8 Hardening Script for profile.js
Systematically replaces unsafe patterns with safe versions
"""
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
PROFILE_JS = PROJECT_ROOT / "static" / "user_profile" / "profile.js"

def count_unsafe_patterns():
    """Count remaining unsafe patterns"""
    content = PROFILE_JS.read_text(encoding='utf-8')
    
    # Count raw fetch (excluding safeFetch definition)
    fetch_matches = re.findall(r'(?<!safe)fetch\(', content)
    # Exclude the one inside safeFetch itself
    raw_fetches = len([m for m in re.finditer(r'\bfetch\(', content)])
    safe_fetches = len([m for m in re.finditer(r'safeFetch\(', content)])
    actual_raw = raw_fetches - 1  # Subtract the one inside safeFetch implementation
    
    # Count document.getElementById (excluding safeGetById implementation)
    getelementbyid = len(re.findall(r'document\.getElementById\(', content))
    safe_getbyid = len(re.findall(r'safeGetById\(', content))
    
    # Count querySelector
    queryselector = len(re.findall(r'\.querySelector\(', content))
    safe_query = len(re.findall(r'safeQuery\(', content))
    
    print("=" * 60)
    print("Phase 3.8 Hardening Audit")
    print("=" * 60)
    print(f"Raw fetch() calls: {actual_raw}")
    print(f"Safe safeFetch() calls: {safe_fetches}")
    print(f"Raw document.getElementById(): {getelementbyid}")
    print(f"Safe safeGetById(): {safe_getbyid}")
    print(f"Raw querySelector(): {queryselector}")
    print(f"Safe safeQuery(): {safe_query}")
    print("=" * 60)
    
    return {
        'raw_fetch': actual_raw,
        'safe_fetch': safe_fetches,
        'raw_getelementbyid': getelementbyid,
        'safe_getbyid': safe_getbyid,
        'raw_queryselector': queryselector,
        'safe_query': safe_query
    }

if __name__ == "__main__":
    stats = count_unsafe_patterns()
    
    if stats['raw_fetch'] > 0:
        print(f"\n⚠️  WARNING: {stats['raw_fetch']} raw fetch() calls need conversion to safeFetch()")
    else:
        print("\n✅ All fetch() calls are using safeFetch()")
    
    if stats['raw_getelementbyid'] > 1:  # Allow 1 for safeGetById implementation
        print(f"⚠️  WARNING: {stats['raw_getelementbyid']} document.getElementById() calls need conversion to safeGetById()")
    else:
        print("✅ All getElementById() calls are using safeGetById()")
