import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings")
django.setup()

from apps.teams.models import TeamMembership

# Get first membership
m = TeamMembership.objects.first()

print("TeamMembership Fields:")
for field in TeamMembership._meta.fields:
    print(f"  - {field.name}: {field.get_internal_type()}, null={field.null}, blank={field.blank}, default={field.default}")
    
print(f"\n Has role_metadata: {hasattr(m, 'role_metadata')}")

if m and hasattr(m, 'role_metadata'):
    print(f" role_metadata value: {m.role_metadata}")
