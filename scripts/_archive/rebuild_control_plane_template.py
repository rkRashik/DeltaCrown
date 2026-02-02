#!/usr/bin/env python3
"""
Rebuild Django template from raw with 100% body parity.
Automatically extracts and splits content properly.
"""

import re
from pathlib import Path


def rebuild_django_template():
    """Rebuild Django template from raw with exact body parity."""
    workspace_root = Path(__file__).parent.parent
    raw_path = workspace_root / "templates" / "My drafts" / "Org_create" / "Organization_Control_Plane.html"
    django_path = workspace_root / "templates" / "organizations" / "org" / "org_control_plane.html"
    
    print("🔧 Rebuilding Django template for 100% parity...")
    print(f"   Source: {raw_path.name}")
    print(f"   Target: {django_path.name}")
    
    # Read raw template
    raw_content = raw_path.read_text(encoding='utf-8')
    
    # Extract head (everything between <head> and </head>)
    head_match = re.search(r'<head>(.*?)</head>', raw_content, re.DOTALL)
    if not head_match:
        print("❌ Could not find <head> in raw template")
        return False
    head_content = head_match.group(1)
    
    # Extract body (everything between <body> and </body>)
    body_match = re.search(r'<body[^>]*>(.*?)</body>', raw_content, re.DOTALL)
    if not body_match:
        print("❌ Could not find <body> in raw template")
        return False
    body_content = body_match.group(1)
    
    # Split head into styles (everything in <style> tags)
    style_pattern = r'(<style>.*?</style>)'
    styles = re.findall(style_pattern, head_content, re.DOTALL)
    style_block = '\n'.join(styles) if styles else ""
    
    # Split body: content up to </main>, scripts after </main>
    main_end_pos = body_content.rfind('</main>')
    if main_end_pos < 0:
        print("❌ Could not find </main> in body")
        return False
    
    # Content block: everything up to and including </main>
    content_block = body_content[:main_end_pos + 7]  # +7 for "</main>"
    
    # Scripts block: everything after </main>
    scripts_block = body_content[main_end_pos + 7:]
    
    print(f"\n📊 Extracted:")
    print(f"   Styles: {len(style_block)} chars")
    print(f"   Content: {len(content_block)} chars")
    print(f"   Scripts: {len(scripts_block)} chars")
    
    # Build Django template (preserve exact whitespace from raw body)
    django_content = "{% extends \"base.html\" %}\n"
    django_content += "{% load static %}\n"
    django_content += "\n"
    django_content += "{% block extra_css %}\n"
    if style_block:
        django_content += style_block + "\n"
    django_content += "{% endblock %}\n"
    django_content += "\n"
    django_content += "{% block content %}\n"
    django_content += content_block  # Already has trailing newline
    django_content += "{% endblock %}\n"
    django_content += "\n"
    django_content += "{% block extra_js %}"
    # Scripts block starts with newlines from raw - don't add extra
    django_content += scripts_block  # Already has leading/trailing newlines
    django_content += "{% endblock %}\n"
    django_path.write_text(django_content, encoding='utf-8')
    
    print(f"\n✅ Rebuilt Django template")
    print(f"   Total size: {len(django_content)} chars")
    print(f"   Saved to: {django_path}")
    
    return True


if __name__ == "__main__":
    import sys
    success = rebuild_django_template()
    sys.exit(0 if success else 1)
