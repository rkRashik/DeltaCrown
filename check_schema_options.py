import django
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.user_profile.models import GamePassportSchema

print("\n=== GamePassportSchema Dropdown Options ===\n")

schemas = GamePassportSchema.objects.all().select_related('game')
print(f"Total schemas: {schemas.count()}\n")

for schema in schemas:
    region_count = len(schema.region_choices) if schema.region_choices else 0
    rank_count = len(schema.rank_choices) if schema.rank_choices else 0
    role_count = len(schema.role_choices) if schema.role_choices else 0
    platform_count = len(schema.platform_choices) if schema.platform_choices else 0
    server_count = len(schema.server_choices) if schema.server_choices else 0
    mode_count = len(schema.mode_choices) if schema.mode_choices else 0
    
    print(f"{schema.game.display_name}:")
    print(f"   Regions: {region_count}")
    print(f"   Ranks: {rank_count}")
    print(f"   Roles: {role_count}")
    print(f"   Platforms: {platform_count}")
    print(f"   Servers: {server_count}")
    print(f"   Modes: {mode_count}")
    
    if rank_count > 0:
        print(f"   Sample ranks: {schema.rank_choices[:5]}")
    
    print()
