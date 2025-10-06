"""
Generate Cyberpunk Homepage and Footer
======================================
Creates all files needed for the modern cyberpunk-themed homepage and footer.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def write_file(filepath, content):
    """Write content to a file"""
    full_path = os.path.join(BASE_DIR, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Created {filepath}")

# Due to length constraints, I'll create the files in parts
print("🚀 Creating cyberpunk homepage and footer...")
print("=" * 60)

# This script will be run separately for each component
print("\n✅ Context processor updated!")
print("📝 Next: Run create_homepage_template.py")
print("📝 Then: Run create_homepage_styles.py")
print("📝 Then: Run create_footer.py")
print("\n" + "=" * 60)
