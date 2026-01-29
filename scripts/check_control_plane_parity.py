#!/usr/bin/env python3
"""
Strict 100% parity check for Control Plane template.
Compares raw body content with Django content block.
"""

import re
from pathlib import Path


def extract_body_content(html_content):
    """Extract content between <body> and </body> tags."""
    body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL)
    if body_match:
        return body_match.group(1)
    return ""


def extract_django_content_block(template_content):
    """Extract content from {% block content %} and {% block extra_js %} combined."""
    # Extract content block
    content_match = re.search(
        r'{%\s*block\s+content\s*%}(.*?){%\s*endblock\s*%}',
        template_content,
        re.DOTALL
    )
    content = content_match.group(1) if content_match else ""
    
    # Extract extra_js block (scripts were moved here per Django best practices)
    js_match = re.search(
        r'{%\s*block\s+extra_js\s*%}(.*?){%\s*endblock\s*%}',
        template_content,
        re.DOTALL
    )
    js_content = js_match.group(1) if js_match else ""
    
    # Combine them to match the original body structure
    # In raw: body had main content + scripts at end
    # In Django: content block has main + extra_js block has scripts
    # Don't add newline - both blocks preserve exact spacing from raw
    if content and js_content:
        return content + js_content
    elif content:
        return content
    else:
        return js_content


def normalize_whitespace(content):
    """Normalize whitespace for strict comparison."""
    # Convert CRLF to LF
    content = content.replace('\r\n', '\n')
    
    # Split into lines and strip trailing whitespace
    lines = [line.rstrip() for line in content.split('\n')]
    
    # Remove leading blank lines
    while lines and not lines[0]:
        lines.pop(0)
    
    # Remove trailing blank lines
    while lines and not lines[-1]:
        lines.pop()
    
    return lines


def compare_content(raw_lines, django_lines):
    """Compare two sets of lines with strict 100% match requirement."""
    if raw_lines == django_lines:
        print("✅ MATCH — 100% PARITY VERIFIED")
        print(f"   Lines: {len(raw_lines)}")
        return True
    
    print("❌ MISMATCH — PARITY FAILED")
    print(f"   Raw body lines: {len(raw_lines)}")
    print(f"   Django content lines: {len(django_lines)}")
    print(f"   Line difference: {abs(len(raw_lines) - len(django_lines))}")
    
    # Count total differences
    diff_count = 0
    max_len = max(len(raw_lines), len(django_lines))
    for i in range(max_len):
        raw_line = raw_lines[i] if i < len(raw_lines) else None
        django_line = django_lines[i] if i < len(django_lines) else None
        if raw_line != django_line:
            diff_count += 1
    
    print(f"   Total differing lines: {diff_count}")
    
    # Show first 20-line diff window
    print("\n📍 First difference window (max 20 lines):")
    shown_lines = 0
    found_first = False
    
    for i in range(min(len(raw_lines), len(django_lines))):
        if raw_lines[i] != django_lines[i]:
            if not found_first:
                # Show 3 lines of context before first diff
                start = max(0, i - 3)
                for j in range(start, i):
                    print(f"     {j+1:4d} ✓ {raw_lines[j][:80]}")
                    shown_lines += 1
                found_first = True
            
            # Show the differing lines
            print(f"   ❌ {i+1:4d} RAW:    {raw_lines[i][:80]}")
            print(f"          DJANGO: {django_lines[i][:80]}")
            shown_lines += 2
            
            if shown_lines >= 20:
                print("   ... (showing first 20 lines only)")
                break
    
    # Handle length mismatch
    if len(raw_lines) != len(django_lines):
        shorter = min(len(raw_lines), len(django_lines))
        print(f"\n⚠️  Length mismatch after line {shorter}")
        if len(raw_lines) > len(django_lines):
            print(f"   Raw has {len(raw_lines) - len(django_lines)} extra lines")
            for i in range(shorter, min(shorter + 5, len(raw_lines))):
                print(f"   +RAW {i+1:4d}: {raw_lines[i][:80]}")
        else:
            print(f"   Django has {len(django_lines) - len(raw_lines)} extra lines")
            for i in range(shorter, min(shorter + 5, len(django_lines))):
                print(f"   +DJANGO {i+1:4d}: {django_lines[i][:80]}")
    
    return False


def main():
    """Run the parity check."""
    workspace_root = Path(__file__).parent.parent
    raw_path = workspace_root / "templates" / "My drafts" / "Org_create" / "Organization_Control_Plane.html"
    django_path = workspace_root / "templates" / "organizations" / "org" / "org_control_plane.html"
    
    print("🔍 Control Plane Template Parity Check")
    print(f"   Raw: {raw_path.name}")
    print(f"   Django: {django_path.name}")
    print()
    
    if not raw_path.exists():
        print(f"❌ Raw template not found: {raw_path}")
        return False
    
    if not django_path.exists():
        print(f"❌ Django template not found: {django_path}")
        return False
    
    # Read files
    raw_content = raw_path.read_text(encoding='utf-8')
    django_content = django_path.read_text(encoding='utf-8')
    
    # Extract body and content block
    raw_body = extract_body_content(raw_content)
    django_block = extract_django_content_block(django_content)
    
    if not raw_body:
        print("❌ Could not extract <body> from raw template")
        return False
    
    if not django_block:
        print("❌ Could not extract {% block content %} from Django template")
        return False
    
    # Normalize and compare
    raw_lines = normalize_whitespace(raw_body)
    django_lines = normalize_whitespace(django_block)
    
    return compare_content(raw_lines, django_lines)


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
