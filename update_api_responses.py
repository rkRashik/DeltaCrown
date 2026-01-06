"""
Script to update game_passports_api.py to use standardized error responses (Phase 9A-13 Section C).
"""
import re

file_path = r"g:\My Projects\WORK\DeltaCrown\apps\user_profile\views\game_passports_api.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern replacements for common error formats
replacements = [
    # VALIDATION_ERROR with field_errors
    (
        r"return JsonResponse\(\{\s*'success': False,\s*'error': 'VALIDATION_ERROR',\s*'message': ([^,]+),\s*'field_errors': ([^\}]+)\s*\}, status=400\)",
        r"return validation_error_response(\2, message=\1)"
    ),
    # NOT_FOUND errors
    (
        r"return JsonResponse\(\{\s*'success': False,\s*'error': 'NOT_FOUND',\s*'message': 'Game not found'\s*\}, status=404\)",
        r"return not_found_error_response('game')"
    ),
    (
        r"return JsonResponse\(\{\s*'success': False,\s*'error': 'NOT_FOUND',\s*'message': 'Passport not found'\s*\}, status=404\)",
        r"return not_found_error_response('passport')"
    ),
    # DUPLICATE_GAME_PASSPORT
    (
        r"return JsonResponse\(\{\s*'success': False,\s*'error': 'DUPLICATE_GAME_PASSPORT',\s*'message': ([^,]+),\s*'existing_passport_id': ([^\}]+)\s*\}, status=409\)",
        r"return duplicate_error_response('game passport', existing_id=\2)"
    ),
    # Simple VALIDATION_ERROR
    (
        r"return JsonResponse\(\{\s*'success': False,\s*'error': 'VALIDATION_ERROR',\s*'message': 'Invalid JSON in request body'\s*\}, status=400\)",
        r"return error_response('VALIDATION_ERROR', 'Invalid JSON in request body')"
    ),
    # SERVER_ERROR with traceback
    (
        r"return JsonResponse\(\{\s*'success': False,\s*'error': 'SERVER_ERROR',.*?status=500\)",
        r"return error_response('SERVER_ERROR', 'An unexpected error occurred', exception=e)",
        re.DOTALL
    ),
]

# Apply replacements
for pattern, replacement, *flags in replacements:
    flag = flags[0] if flags else 0
    content = re.sub(pattern, replacement, content, flags=flag)

# Handle success responses for create/update (keep detailed payload format)
# Just update the outer structure

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Updated game_passports_api.py with standardized error responses")
