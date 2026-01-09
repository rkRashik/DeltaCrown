#!/usr/bin/env python3
"""
Syntax checker for profile.js
Runs Node.js parse check if available, otherwise does pattern-based validation
"""
import subprocess
import sys
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent.parent
PROFILE_JS = PROJECT_ROOT / "static" / "user_profile" / "profile.js"

def check_with_node():
    """Try to check syntax using Node.js"""
    try:
        result = subprocess.run(
            ['node', '--check', str(PROFILE_JS)],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✅ Node.js parse check: PASSED")
            return True
        else:
            print("❌ Node.js parse check: FAILED")
            print(result.stderr)
            return False
    except FileNotFoundError:
        print("⚠️  Node.js not found, falling back to pattern check")
        return None
    except subprocess.TimeoutExpired:
        print("❌ Node.js check timed out")
        return False

def check_orphaned_patterns():
    """Check for common orphaned object literal patterns"""
    print("\n🔍 Scanning for orphaned object literals...")
    
    content = PROFILE_JS.read_text(encoding='utf-8')
    lines = content.splitlines()
    
    issues = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Check for lines starting with object properties at wrong indentation
        if stripped.startswith(('method:', 'headers:', 'body:', 'credentials:')):
            # Check if previous line might be missing fetch(
            if i > 1:
                prev_line = lines[i-2].strip()
                if not prev_line.endswith('({') and not 'fetch(' in prev_line:
                    issues.append((i, line))
    
    if issues:
        print(f"❌ Found {len(issues)} potential orphaned object literals:")
        for line_num, line_content in issues:
            print(f"  Line {line_num}: {line_content.strip()[:60]}")
        return False
    else:
        print("✅ No orphaned object literal patterns detected")
        return True

def main():
    print(f"Checking: {PROFILE_JS}")
    print("=" * 60)
    
    if not PROFILE_JS.exists():
        print(f"❌ File not found: {PROFILE_JS}")
        sys.exit(1)
    
    # Try Node.js first
    node_result = check_with_node()
    
    # If Node.js not available, do pattern check
    if node_result is None:
        pattern_result = check_orphaned_patterns()
        sys.exit(0 if pattern_result else 1)
    else:
        sys.exit(0 if node_result else 1)

if __name__ == "__main__":
    main()
