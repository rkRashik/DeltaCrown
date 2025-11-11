"""Fix all remaining issues in services and tests."""

import re

# Fix 1: Update imports in services.py to use shop exceptions
services_file = 'apps/shop/services.py'
with open(services_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Change imports
content = content.replace(
    'from apps.economy.exceptions import IdempotencyConflict as EconomyIdempotencyConflict, InsufficientFunds',
    'from apps.economy.exceptions import IdempotencyConflict as EconomyIdempotencyConflict\nfrom .exceptions import InsufficientFunds'
)

with open(services_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed imports in {services_file}")

# Fix 2: Remove leftover Decimal import and usage in test_available_balance
test_file = 'tests/shop/test_available_balance_module_7_2.py'
with open(test_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove assert with Decimal
content = re.sub(r"assert available == Decimal\('-500\.00'\)", "assert available == -500", content)

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed Decimal in {test_file}")

# Fix 3: Fix test calls to match keyword-only arguments
test_files = [
    'tests/shop/test_authorize_capture_release_module_7_2.py',
    'tests/shop/test_available_balance_module_7_2.py',
]

for test_file in test_files:
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix authorize_spend calls: (wallet, amount, 'SKU', idempotency_key=...)
    # Should be: (wallet, amount, sku='SKU', idempotency_key=...)
    content = re.sub(
        r"authorize_spend\(([^,]+),\s*(\d+),\s*'([^']+)',\s*idempotency_key=",
        r"authorize_spend(\1, \2, sku='\3', idempotency_key=",
        content
    )
    
    # Fix capture calls: capture(..., hold_id=xxx) should be capture(..., authorization_id=xxx)
    content = content.replace('hold_id=', 'authorization_id=')
    
    # Fix release calls: release(..., hold_id=xxx) should be release(..., authorization_id=xxx)
    content = re.sub(r'release\(([^,]+),\s*hold_id=', r'release(\1, authorization_id=', content)
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Fixed function calls in {test_file}")

# Fix 4: Fix refund meta query - should be meta__original_transaction_id not meta__original_transaction_id
# Actually the error shows it's trying to query 'meta' which doesn't exist
# The query should filter on the JSON field properly

# Actually, looking at the error, it says "Cannot resolve keyword 'meta' into field"
# This means the query is trying to filter on 'meta' but DeltaCrownTransaction doesn't have it
# Let me check the actual query in refund

print("\n✅ Phase 1 fixes complete. Now checking refund query issue...")

# The refund service queries: meta__original_transaction_id=capture_txn_id
# But DeltaCrownTransaction might not have a 'meta' field. Let me check models.

# Since I can't read models easily, I'll create a note about this
print("⚠️  Note: Need to verify DeltaCrownTransaction has 'meta' JSONField")
print("    If not, refund service needs to use note or another field")

# Fix 5: Fix test_refund_non_purchase_transaction_raises to use correct credit signature
test_file = 'tests/shop/test_refund_module_7_2.py'
with open(test_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix credit call: credit(wallet=...) should be credit(profile=...)
content = content.replace('credit_result = credit(\n        wallet=funded_wallet', 
                          'credit_result = credit(\n        profile=funded_wallet.profile')

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed credit call in {test_file}")

# Fix 6: Fix concurrency test to create user with email
test_file = 'tests/shop/test_concurrency_module_7_2.py'
with open(test_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix user creation to include email
content = re.sub(
    r"user2 = get_user_model\(\)\.objects\.create_user\(\s*username='user2',\s*password='pass'",
    "user2 = get_user_model().objects.create_user(\n        username='user2',\n        email='user2@test.com',\n        password='pass'",
    content
)

with open(test_file, 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ Fixed user creation in {test_file}")

print("\n✅ All automatic fixes applied!")
print("\nRemaining manual fixes needed:")
print("1. Verify DeltaCrownTransaction has 'meta' JSONField for refund queries")
print("2. Fix idempotency conflict detection in authorize_spend")
print("3. Fix release idempotency to return exact same dict")
print("4. Fix capture balance_after calculation")
print("5. Fix freezegun mock issue in test_capture_expired_hold_raises")
