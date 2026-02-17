"""Batch convert all admin files to use unfold base classes."""
import re
import os

files = [
    'apps/moderation/admin.py',
    'apps/shop/admin.py',
    'apps/challenges/admin.py',
    'apps/teams/admin.py',
    'apps/support/admin.py',
    'apps/siteui/admin.py',
    'apps/common/events/admin.py',
    'apps/tournaments/admin_certificate.py',
    'apps/tournaments/admin_match.py',
    'apps/tournaments/admin_prize.py',
    'apps/tournaments/admin_result.py',
    'apps/economy/admin.py',
    'apps/tournaments/admin_bracket.py',
    'apps/tournaments/admin_staff.py',
    'apps/tournaments/admin_registration.py',
    'apps/user_profile/admin.py',
    'apps/organizations/admin.py',
    'apps/ecommerce/admin.py',
    'apps/games/admin.py',
    'apps/tournaments/admin.py',
    'apps/competition/admin.py',
]

base_dir = r'G:\My Projects\WORK\DeltaCrown'

for fpath in files:
    full_path = os.path.join(base_dir, fpath)
    if not os.path.exists(full_path):
        print(f'SKIP: {fpath}')
        continue
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()

    has_tab = 'admin.TabularInline' in content
    has_stk = 'admin.StackedInline' in content

    imports = ['ModelAdmin']
    if has_tab:
        imports.append('TabularInline')
    if has_stk:
        imports.append('StackedInline')

    unfold_line = 'from unfold.admin import ' + ', '.join(imports)

    if 'from unfold.admin' not in content:
        content = re.sub(
            r'(from django\.contrib import admin(?:, messages)?)\n',
            r'\1\n' + unfold_line + '\n',
            content, count=1
        )

    content = content.replace('(admin.ModelAdmin)', '(ModelAdmin)')
    content = content.replace('(admin.TabularInline)', '(TabularInline)')
    content = content.replace('(admin.StackedInline)', '(StackedInline)')

    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'OK: {fpath}')

print('\nDone.')
