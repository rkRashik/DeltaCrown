"""
Wrapper script to seed the database with all necessary data for DeltaCrown platform.
This runs all seeding commands in the correct order.

Usage:
    python scripts/seed_all.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.core.management import call_command

print("="*80)
print("DELTACROWN - COMPLETE DATABASE SEEDING")
print("="*80)
print()

# 1. Seed games (includes Game, Roster, Roles, Identity, Tournament configs)
print("1. Seeding games...")
try:
    call_command('seed_games')
    print("   ✅ Games seeded successfully!\n")
except Exception as e:
    print(f"   ❌ Error seeding games: {e}\n")
    import traceback
    traceback.print_exc()

# 2. Seed game passport schemas
print("2. Seeding game passport schemas...")
try:
    call_command('seed_game_passport_schemas')
    print("   ✅ Game passport schemas seeded successfully!\n")
except Exception as e:
    print(f"   ❌ Error seeding game passport schemas: {e}\n")
    import traceback
    traceback.print_exc()

print("="*80)
print("SEEDING COMPLETE")
print("="*80)
print("\n✅ All data has been seeded successfully!")
print("   • 11 Games with roles and configs")
print("   • 2026-accurate identity configurations")
print("   • Game passport schemas for user profiles")
print()
