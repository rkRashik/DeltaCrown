#!/usr/bin/env python3
"""
Remove unused CSS files and consolidate team stylesheets.
"""

import os
import shutil
from pathlib import Path

# List of CSS files that appear to be unused based on template analysis
UNUSED_CSS_FILES = [
    'static/siteui/css/teams-list-professional.css',
    'static/siteui/css/teams-rankings-modern.css', 
    'static/siteui/css/teams-list.css',
    'static/siteui/css/teams-list-enhanced.css',
    'static/siteui/css/teams-list-esports.css',
    'static/siteui/css/teams-list-modern-new.css',
    # Keep teams-list-modern.css as it's used by ranking_list.html
    # Keep teams-list-two-column.css as it's actively used
]

def remove_unused_css():
    """Remove unused CSS files."""
    project_root = Path(__file__).parent
    removed_files = []
    
    for css_file in UNUSED_CSS_FILES:
        file_path = project_root / css_file
        if file_path.exists():
            print(f"Removing unused CSS file: {css_file}")
            file_path.unlink()
            removed_files.append(css_file)
        else:
            print(f"File not found (already removed?): {css_file}")
    
    return removed_files

def backup_important_files():
    """Create backups of important files before cleanup."""
    project_root = Path(__file__).parent
    backup_dir = project_root / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    important_files = [
        'static/siteui/css/teams-list-two-column.css',
        'apps/teams/views/public.py',
        'apps/teams/urls.py',
    ]
    
    for file_path in important_files:
        source = project_root / file_path
        if source.exists():
            backup_path = backup_dir / f"{source.name}.backup"
            shutil.copy2(source, backup_path)
            print(f"Backed up: {file_path} -> {backup_path}")

def main():
    print("DeltaCrown CSS Cleanup")
    print("=" * 30)
    
    # Create backups first
    backup_important_files()
    
    # Remove unused CSS files
    removed = remove_unused_css()
    
    print(f"\n✅ Cleanup complete!")
    print(f"   Removed {len(removed)} unused CSS files")
    print(f"   Kept active stylesheets: teams-list-two-column.css, teams-list-modern.css")

if __name__ == "__main__":
    main()