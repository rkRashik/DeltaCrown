"""
Extract JavaScript from public_profile.html to external profile.js file.
Keeps Django template variables in a small inline script.
"""

# Read the current file
with open(r"g:\My Projects\WORK\DeltaCrown\templates\user_profile\profile\public_profile.html", 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find script boundaries
script_start = None
script_end = None

for i, line in enumerate(lines):
    if line.strip() == '<script>':
        script_start = i
    if line.strip() == '</script>':
        script_end = i
        break

print(f"Script starts at line {script_start + 1}")
print(f"Script ends at line {script_end + 1}")
print(f"JavaScript is {script_end - script_start - 1} lines")

# Extract the JavaScript content (without <script> tags)
js_content = ''.join(lines[script_start + 1:script_end])

# Identify Django template variables (lines containing {{ or {%)}
django_vars_lines = []
pure_js_lines = []

for line in lines[script_start + 1:script_end]:
    # Check if line contains Django template syntax
    if '{{' in line or '{%' in line or 'json_script' in line:
        django_vars_lines.append(line)
    else:
        pure_js_lines.append(line)

print(f"\nDjango template lines: {len(django_vars_lines)}")
print(f"Pure JavaScript lines: {len(pure_js_lines)}")

# Save pure JavaScript to external file
js_file_path = r"g:\My Projects\WORK\DeltaCrown\static\user_profile\profile.js"
with open(js_file_path, 'w', encoding='utf-8') as f:
    f.write('// DeltaCrown Profile JavaScript\n')
    f.write('// Auto-extracted from public_profile.html\n\n')
    f.write(''.join(pure_js_lines))

print(f"\n✅ Extracted {len(pure_js_lines)} lines of JavaScript to profile.js")

# Build replacement script block (inline Django vars + external JS reference)
new_script_block = [
    '{{ hardware_gear|json_script:"hardwareData" }}\n',
    '{{ game_configs|json_script:"gameConfigsData" }}\n',
    '\n',
    '<script>\n',
    '// Django template variables\n'
]

# Add Django variable declarations
for line in django_vars_lines:
    if 'const ' in line or 'let ' in line or 'var ' in line:
        new_script_block.append(line)

new_script_block.append('</script>\n')
new_script_block.append('\n')
new_script_block.append('<script src="{% static \'user_profile/profile.js\' %}"></script>\n')

# Rebuild the HTML file
new_content = (
    ''.join(lines[:script_start - 2]) +  # Everything before json_script tags
    ''.join(new_script_block) +
    '{% endblock %}\n'
)

# Write back
with open(r"g:\My Projects\WORK\DeltaCrown\templates\user_profile\profile\public_profile.html", 'w', encoding='utf-8') as f:
    f.write(new_content)

# Count final lines
final_lines = new_content.count('\n') + 1
original_lines = len(lines)

print(f"\n✅ Template rebuild complete!")
print(f"Original template: {original_lines} lines")
print(f"Final template: {final_lines} lines")
print(f"Reduction: {original_lines - final_lines} lines removed")
print(f"\n📁 JavaScript saved to: {js_file_path}")
