"""
Rebuild public_profile.html with clean include statements only.
Removes all inline tab content and replaces with {% include %} statements.
"""

# Read the current file
with open(r"g:\My Projects\WORK\DeltaCrown\templates\user_profile\profile\public_profile.html", 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find key markers
header_end = None
footer_start = None

for i, line in enumerate(lines):
    if '<!-- MAIN CONTENT AREA -->' in line:
        header_end = i + 2  # Include the <section> tag
    if '<!-- RIGHT SIDEBAR -->' in line:
        footer_start = i
        break

print(f"Header ends at line {header_end}")
print(f"Footer starts at line {footer_start}")

# Build the clean middle section with just includes
clean_middle = """        {# === OVERVIEW TAB === #}
        {% include 'user_profile/profile/_overview.html' %}

        {# === POSTS TAB === #}
        {% include 'user_profile/profile/tabs/_posts.html' %}

        {# === LOADOUTS TAB === #}
        {% include 'user_profile/profile/tabs/_loadouts.html' %}

        {# === BOUNTIES TAB === #}
        {% include 'user_profile/profile/tabs/_bounties.html' %}

        {# === MEDIA TAB === #}
        {% include 'user_profile/profile/tabs/_media.html' %}

        {# === CAREER TAB === #}
        {% include 'user_profile/profile/tabs/_career.html' %}

        {# === GAME IDS TAB === #}
        {% include 'user_profile/profile/tabs/_game_ids.html' %}

        {# === STATS TAB === #}
        {% include 'user_profile/profile/tabs/_stats.html' %}

        {# === HIGHLIGHTS TAB === #}
        {% include 'user_profile/profile/tabs/_highlights.html' %}

        {# === WALLET TAB === #}
        {% include 'user_profile/profile/tabs/_wallet.html' %}

        {# === INVENTORY TAB === #}
        {% include 'user_profile/profile/tabs/_inventory.html' %}
    </section>

"""

# Assemble the final file
final_content = ''.join(lines[:header_end]) + clean_middle + ''.join(lines[footer_start:])

# Write it back
with open(r"g:\My Projects\WORK\DeltaCrown\templates\user_profile\profile\public_profile.html", 'w', encoding='utf-8') as f:
    f.write(final_content)

# Count lines
final_lines = final_content.count('\n')
print(f"\n✅ Rebuild complete!")
print(f"Original: {len(lines)} lines")
print(f"Final: {final_lines} lines")
print(f"Reduction: {len(lines) - final_lines} lines removed")
