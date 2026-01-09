#!/usr/bin/env python3
"""
Phase 3.8.3 Add Defensive Guards
Adds null checks where DOM elements are accessed without guards
"""

import re
from pathlib import Path

def add_defensive_guards(file_path):
    """Add null checks for DOM element access"""
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    changes = []
    
    # Pattern 1: safeGetById().property without null check
    # Find: const x = safeGetById('id'); x.innerHTML = ...
    # Need to add: if (!x) return;
    
    # Pattern 2: safeGetById('x').innerHTML = ... (direct access)
    # Convert to: const x = safeGetById('x'); if (x) x.innerHTML = ...
    
    # This is complex - let's do targeted replacements
    
    # Fix 1: loadAvailableGames - add null check for select
    old_load_games = '''            availableGames = data.games;
            const select = safeGetById('passportGameSelect');
            select.innerHTML = '<option value="">Select a game...</option>';'''
    
    new_load_games = '''            availableGames = data.games;
            const select = safeGetById('passportGameSelect');
            if (!select) return;
            select.innerHTML = '<option value="">Select a game...</option>';'''
    
    if old_load_games in content:
        content = content.replace(old_load_games, new_load_games)
        changes.append("✅ Added null check in loadAvailableGames()")
    
    # Fix 2: loadGamePassports - add null check for container
    old_load_passports = '''        const container = safeGetById('passportsList');
        
        if (!data.success || !data.passports || data.passports.length === 0) {
            container.innerHTML = '<div class="text-center text-gray-500 py-8">No game IDs yet. Add one above!</div>';'''
    
    new_load_passports = '''        const container = safeGetById('passportsList');
        if (!container) return;
        
        if (!data.success || !data.passports || data.passports.length === 0) {
            container.innerHTML = '<div class="text-center text-gray-500 py-8">No game IDs yet. Add one above!</div>';'''
    
    if old_load_passports in content:
        content = content.replace(old_load_passports, new_load_passports)
        changes.append("✅ Added null check in loadGamePassports()")
    
    # Fix 3: closeGamePassportsModal - add defensive check
    old_close_passports = '''    const modal = safeGetById('gamePassportsModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
        safeGetById('addPassportForm').reset();
    }'''
    
    new_close_passports = '''    const modal = safeGetById('gamePassportsModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
        const form = safeGetById('addPassportForm');
        if (form) form.reset();
    }'''
    
    if old_close_passports in content:
        content = content.replace(old_close_passports, new_close_passports)
        changes.append("✅ Added null check for addPassportForm.reset()")
    
    # Fix 4: closeEditHighlightsModal
    old_close_highlights = '''function closeEditHighlightsModal() {
    const modal = safeGetById('editHighlightsModal');
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}'''
    
    new_close_highlights = '''function closeEditHighlightsModal() {
    const modal = safeGetById('editHighlightsModal');
    if (!modal) return;
    modal.classList.add('hidden');
    document.body.style.overflow = '';
}'''
    
    if old_close_highlights in content:
        content = content.replace(old_close_highlights, new_close_highlights)
        changes.append("✅ Added null check in closeEditHighlightsModal()")
    
    # Fix 5: openEditHighlightsModal
    old_open_highlights = '''    if (!requireOwner('openEditHighlightsModal')) return;
    
    const modal = safeGetById('editHighlightsModal');
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';'''
    
    new_open_highlights = '''    if (!requireOwner('openEditHighlightsModal')) return;
    
    const modal = safeGetById('editHighlightsModal');
    if (!modal) return;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';'''
    
    if old_open_highlights in content:
        content = content.replace(old_open_highlights, new_open_highlights)
        changes.append("✅ Added null check in openEditHighlightsModal()")
    
    # Write changes
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ File updated: {file_path}")
        print("\nChanges made:")
        for change in changes:
            print(f"  {change}")
        return True
    else:
        print("⚠️  No additional defensive guards needed")
        return False

if __name__ == '__main__':
    profile_js = Path('g:/My Projects/WORK/DeltaCrown/static/user_profile/profile.js')
    
    if not profile_js.exists():
        print(f"❌ File not found: {profile_js}")
        exit(1)
    
    print(f"🔧 Adding defensive guards in: {profile_js}\n")
    add_defensive_guards(profile_js)
    print("\n✅ Defensive guards complete!")
