"""Quick fix script for participant card rendering in hub-engine.js"""
import sys

path = r"g:\My Projects\WORK\DeltaCrown\static\tournaments\js\hub-engine.js"

with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Find the target line (line 1222, 0-indexed 1221)
found = False
for i, line in enumerate(lines):
    if "const tag = p.detail_url ? 'a' : 'div';" in line and i > 1200:
        # Insert the unverifiedClass line after this
        lines.insert(i + 1, "      const unverifiedClass = (p.verified === false) ? ' opacity-80 border-dashed' : '';\n")
        found = True
        break

if not found:
    print("ERROR: Could not find target line")
    sys.exit(1)

# Now find the border${youBorder} and add ${unverifiedClass}
for i, line in enumerate(lines):
    if 'border${youBorder} hover:border-white/20' in line and i > 1200:
        lines[i] = line.replace('border${youBorder} hover', 'border${youBorder}${unverifiedClass} hover')
        found = True
        break

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print("OK - patched successfully")
