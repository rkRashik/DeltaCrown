#!/usr/bin/env python3
"""
Phase 3.8.3 DOM Safety Conversion Script
Converts all raw DOM queries to safe wrappers
"""

import re
import sys
from pathlib import Path

def convert_dom_queries(file_path):
    """Convert all raw DOM queries to safe wrappers"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    conversions = []
    
    # Pattern 1: document.getElementById('id') -> safeGetById('id')
    # BUT skip the one inside the safeGetById function definition
    pattern1 = r'(\s+)return document\.getElementById\(id\);'
    if re.search(pattern1, content):
        print("⚠️  Skipping conversion inside safeGetById definition")
    
    # Convert all other getElementById calls
    pattern_getbyid = r'document\.getElementById\('
    matches = list(re.finditer(pattern_getbyid, content))
    
    # Filter out the one inside the function definition
    filtered_matches = []
    for match in matches:
        start = match.start()
        # Check if this is inside the safeGetById function
        before_text = content[max(0, start-100):start]
        if 'function safeGetById' not in before_text and 'return document.getElementById(id)' not in content[start:start+50]:
            filtered_matches.append(match)
    
    print(f"Found {len(filtered_matches)} document.getElementById() calls to convert")
    content = re.sub(r'(?<!function safeGetById\(id\) \{\n    try \{\n        return )document\.getElementById\(', 'safeGetById(', content)
    
    # More precise: only replace if NOT inside the safeGetById function definition line
    # Let's use a different approach - replace all then fix the definition
    content_lines = content.split('\n')
    fixed_lines = []
    in_safegetbyid_function = False
    
    for i, line in enumerate(content_lines):
        if 'function safeGetById(id)' in line:
            in_safegetbyid_function = True
        elif in_safegetbyid_function and 'return' in line and 'safeGetById(' in line and 'safeGetById(id)' in line:
            # Fix the definition line back
            line = line.replace('return safeGetById(id);', 'return document.getElementById(id);')
            in_safegetbyid_function = False
        elif in_safegetbyid_function and '}' in line and line.strip() == '}':
            in_safegetbyid_function = False
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    conversions.append(f"✅ Converted document.getElementById() -> safeGetById()")
    
    # Pattern 2: document.querySelector(...) -> safeQuery(...)
    # BUT skip the one inside safeQuery function definition
    pattern_queryselector = r'document\.querySelector\('
    matches_qs = list(re.finditer(pattern_queryselector, content))
    
    # Filter out the one inside function definition
    filtered_qs = []
    for match in matches_qs:
        start = match.start()
        before_text = content[max(0, start-100):start]
        if 'function safeQuery' not in before_text:
            filtered_qs.append(match)
    
    print(f"Found {len(filtered_qs)} document.querySelector() calls to convert")
    
    # Convert document.querySelector to safeQuery
    content_lines = content.split('\n')
    fixed_lines = []
    in_safequery_function = False
    
    for i, line in enumerate(content_lines):
        if 'function safeQuery' in line:
            in_safequery_function = True
        elif in_safequery_function and 'return' in line and 'scope.querySelector(' in line:
            # Don't modify this line
            in_safequery_function = False
        elif in_safequery_function and '}' in line and line.strip() == '}':
            in_safequery_function = False
        elif not in_safequery_function:
            # Convert document.querySelector to safeQuery
            line = line.replace('document.querySelector(', 'safeQuery(')
        
        fixed_lines.append(line)
    
    content = '\n'.join(fixed_lines)
    conversions.append(f"✅ Converted document.querySelector() -> safeQuery()")
    
    # Pattern 3: e.target.querySelector(...) -> safeQueryIn(e.target, ...)
    # This one is trickier - need to capture the element reference
    pattern_element_qs = r'(\w+)\.querySelector\('
    
    def replace_element_queryselector(match):
        element = match.group(1)
        # Skip if it's 'scope' (inside safeQuery definition)
        if element == 'scope':
            return match.group(0)
        # Skip if it's 'document'
        if element == 'document':
            return match.group(0)
        return f'safeQueryIn({element}, '
    
    # Find all element.querySelector patterns
    matches_elem = list(re.finditer(pattern_element_qs, content))
    elem_qs_count = len([m for m in matches_elem if m.group(1) not in ['scope', 'document']])
    print(f"Found {elem_qs_count} element.querySelector() calls to convert")
    
    content = re.sub(pattern_element_qs, replace_element_queryselector, content)
    conversions.append(f"✅ Converted element.querySelector() -> safeQueryIn(element, ...)")
    
    # Write back
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"\n✅ File updated: {file_path}")
        print(f"\nConversions made:")
        for conv in conversions:
            print(f"  {conv}")
        return True
    else:
        print("⚠️  No changes needed")
        return False

if __name__ == '__main__':
    profile_js = Path('g:/My Projects/WORK/DeltaCrown/static/user_profile/profile.js')
    
    if not profile_js.exists():
        print(f"❌ File not found: {profile_js}")
        sys.exit(1)
    
    print(f"🔧 Converting DOM queries in: {profile_js}\n")
    convert_dom_queries(profile_js)
    print("\n✅ DOM query conversion complete!")
