import re

# Read the file
with open(r"g:\My Projects\WORK\DeltaCrown\apps\user_profile\tests\test_phase_9a12_passport_integration.py", 'r', encoding='utf-8') as f:
    content = f.read()

# Replace function calls with GamePassportService method calls
replacements = [
    (r'\bget_passport_for_game\(', 'GamePassportService.get_passport('),
    (r'\bvalidate_passport_for_team_action\(', 'GamePassportService.validate_passport_for_team_action('),
    (r'\bbuild_team_identity_payload\(', 'GamePassportService.build_identity_payload('),
    (r'\bvalidate_roster_passports\(', 'GamePassportService.validate_roster_passports('),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Write back
with open(r"g:\My Projects\WORK\DeltaCrown\apps\user_profile\tests\test_phase_9a12_passport_integration.py", 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated test file with GamePassportService method calls")
