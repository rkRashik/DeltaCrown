#!/usr/bin/env python
"""Fix literal `n sequences in test file."""

with open('tests/test_winner_determination_module_5_1.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace literal backtick-n with actual newlines
content = content.replace('`n        ', '\n        ')
content = content.replace('`n', '\n')

with open('tests/test_winner_determination_module_5_1.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed backtick sequences")
