#!/usr/bin/env python3
"""Fix Decimal usage in test files - convert to int."""
import re

test_files = [
    'tests/shop/test_authorize_capture_release_module_7_2.py',
    'tests/shop/test_refund_module_7_2.py',
    'tests/shop/test_available_balance_module_7_2.py',
    'tests/shop/test_concurrency_module_7_2.py',
    'tests/shop/conftest.py',
]

for filepath in test_files:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove Decimal imports
    content = content.replace('from decimal import Decimal\n', '')
    
    # Replace Decimal('NNN.NN') with just the integer value
    content = re.sub(r"Decimal\('(\d+)\.00'\)", r'\1', content)
    content = re.sub(r"Decimal\('(\d+)\.0'\)", r'\1', content)
    content = re.sub(r"Decimal\('(\d+)'\)", r'\1', content)
    content = re.sub(r'Decimal\("(\d+)\.00"\)', r'\1', content)
    content = re.sub(r'Decimal\("(\d+)"\)', r'\1', content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'Fixed: {filepath}')

print('\nAll files fixed!')
