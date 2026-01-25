"""
Diagnostic script to test feature flags.
Run with: python manage.py shell < apps/organizations/test_flags.py
"""

from django.conf import settings
from apps.organizations.context_processors import vnext_feature_flags
from django.http import HttpRequest

print("\n" + "="*60)
print("  VNEXT FEATURE FLAGS DIAGNOSTIC")
print("="*60 + "\n")

print("1. Django Settings Values:")
print(f"   DEBUG = {settings.DEBUG}")
print(f"   TEAM_VNEXT_ADAPTER_ENABLED = {settings.TEAM_VNEXT_ADAPTER_ENABLED}")
print(f"   TEAM_VNEXT_FORCE_LEGACY = {settings.TEAM_VNEXT_FORCE_LEGACY}")
print(f"   TEAM_VNEXT_ROUTING_MODE = {settings.TEAM_VNEXT_ROUTING_MODE}")

print("\n2. Context Processor Output:")
ctx = vnext_feature_flags(HttpRequest())
for key, value in ctx.items():
    print(f"   {key} = {value}")

print("\n3. Template Condition Check:")
adapter_enabled = ctx['TEAM_VNEXT_ADAPTER_ENABLED']
force_legacy = ctx['TEAM_VNEXT_FORCE_LEGACY']
routing_mode = ctx['TEAM_VNEXT_ROUTING_MODE']

condition = adapter_enabled and not force_legacy and routing_mode != 'legacy_only'
print(f"   Condition: {adapter_enabled} AND NOT {force_legacy} AND '{routing_mode}' != 'legacy_only'")
print(f"   Result: {condition}")

if condition:
    print("\n✅ BUTTON SHOULD BE VISIBLE")
else:
    print("\n❌ BUTTON WILL BE HIDDEN")
    if not adapter_enabled:
        print("   Reason: ADAPTER_ENABLED is False")
    if force_legacy:
        print("   Reason: FORCE_LEGACY is True")
    if routing_mode == 'legacy_only':
        print("   Reason: ROUTING_MODE is 'legacy_only'")

print("\n4. Environment Variables:")
import os
print(f"   TEAM_VNEXT_ADAPTER_ENABLED = {os.getenv('TEAM_VNEXT_ADAPTER_ENABLED', 'not set')}")
print(f"   TEAM_VNEXT_FORCE_LEGACY = {os.getenv('TEAM_VNEXT_FORCE_LEGACY', 'not set')}")
print(f"   TEAM_VNEXT_ROUTING_MODE = {os.getenv('TEAM_VNEXT_ROUTING_MODE', 'not set')}")

print("\n" + "="*60 + "\n")
