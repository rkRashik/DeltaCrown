"""
Script to complete Phase 3.5 Modular Modularization of public_profile.html
Systematically replaces inline tab content with includes.
"""

import re

# Read the file
file_path = r"g:\My Projects\WORK\DeltaCrown\templates\user_profile\profile\public_profile.html"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define tab replacements (tab_id -> include_path)
tab_replacements = [
    # Posts - already has include added, need to remove inline content
    {
        'start_marker': r'        {# === POSTS TAB === #}\n        {% include \'user_profile/profile/tabs/_posts\.html\' %}',
        'end_marker': r'        </div>\n\n        <!-- LOADOUT TAB',
        'replacement': '        {# === POSTS TAB === #}\n        {% include \'user_profile/profile/tabs/_posts.html\' %}\n\n        <!-- LOADOUT TAB'
    },
    # Loadouts
    {
        'start_marker': r'        <!-- LOADOUT TAB - UP-PHASE-2C2 -->\n        <div id="tab-loadout"',
        'end_marker': r'        </div>\n\n        <!-- BOUNTIES TAB',
        'replacement': '        {# === LOADOUTS TAB === #}\n        {% include \'user_profile/profile/tabs/_loadouts.html\' %}\n\n        <!-- BOUNTIES TAB'
    },
    # Bounties
    {
        'start_marker': r'        <!-- BOUNTIES TAB - UP-PHASE-2C2 -->\n        <div id="tab-bounties"',
        'end_marker': r'        </div>\n\n        <!-- MEDIA TAB',
        'replacement': '        {# === BOUNTIES TAB === #}\n        {% include \'user_profile/profile/tabs/_bounties.html\' %}\n\n        <!-- MEDIA TAB'
    },
    # Media
    {
        'start_marker': r'        <!-- MEDIA TAB -->\n        <div id="tab-media"',
        'end_marker': r'        </div>\n\n        <!-- CAREER TAB',
        'replacement': '        {# === MEDIA TAB === #}\n        {% include \'user_profile/profile/tabs/_media.html\' %}\n\n        <!-- CAREER TAB'
    },
    # Career
    {
        'start_marker': r'        <!-- CAREER TAB -->\n        <div id="tab-career"',
        'end_marker': r'        </div>\n        \n        <!-- GAME IDs TAB',
        'replacement': '        {# === CAREER TAB === #}\n        {% include \'user_profile/profile/tabs/_career.html\' %}\n        \n        <!-- GAME IDs TAB'
    },
    # Game IDs
    {
        'start_marker': r'        <!-- GAME IDs TAB -->\n        <div id="tab-game-ids"',
        'end_marker': r'        </div>\n\n        <!-- STATS TAB',
        'replacement': '        {# === GAME IDS TAB === #}\n        {% include \'user_profile/profile/tabs/_game_ids.html\' %}\n\n        <!-- STATS TAB'
    },
    # Stats
    {
        'start_marker': r'        <!-- STATS TAB -->\n        <div id="tab-stats"',
        'end_marker': r'        </div>\n\n        <!-- HIGHLIGHTS TAB',
        'replacement': '        {# === STATS TAB === #}\n        {% include \'user_profile/profile/tabs/_stats.html\' %}\n\n        <!-- HIGHLIGHTS TAB'
    },
    # Highlights
    {
        'start_marker': r'        <!-- HIGHLIGHTS TAB -->\n        <div id="tab-highlights"',
        'end_marker': r'        </div>\n\n        <!-- WALLET TAB',
        'replacement': '        {# === HIGHLIGHTS TAB === #}\n        {% include \'user_profile/profile/tabs/_highlights.html\' %}\n\n        <!-- WALLET TAB'
    },
    # Wallet
    {
        'start_marker': r'        <!-- WALLET TAB \(Owner Only\) -->\n        <div id="tab-wallet"',
        'end_marker': r'        </div>\n        {% endif %}\n\n        <!-- INVENTORY TAB',
        'replacement': '        {# === WALLET TAB === #}\n        {% include \'user_profile/profile/tabs/_wallet.html\' %}\n\n        <!-- INVENTORY TAB'
    },
    # Inventory
    {
        'start_marker': r'        <!-- INVENTORY TAB - UP-PHASE-2C2 -->\n        <div id="tab-inventory"',
        'end_marker': r'        </div>\n    </section>',
        'replacement': '        {# === INVENTORY TAB === #}\n        {% include \'user_profile/profile/tabs/_inventory.html\' %}\n    </section>'
    },
]

print("Starting Phase 3.5 Tab Replacement...")
print(f"Original file size: {len(content)} characters")

# Apply each replacement
for i, replacement in enumerate(tab_replacements, 1):
    pattern = replacement['start_marker'] + r'.*?' + replacement['end_marker']
    matches = re.findall(pattern, content, re.DOTALL)
    if matches:
        content = re.sub(pattern, replacement['replacement'], content, flags=re.DOTALL, count=1)
        print(f"✓ Replacement {i} applied")
    else:
        print(f"✗ Replacement {i} NOT FOUND - pattern may need adjustment")

print(f"Final file size: {len(content)} characters")
print(f"Reduction: {len(content)} characters")

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ Phase 3.5 Modularization Complete!")
print("Run: Get-Content public_profile.html | Measure-Object -Line")
