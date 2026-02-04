#!/usr/bin/env python
"""
Test template rendering with feature flags
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.template import Template, Context, loader
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from apps.organizations.context_processors import vnext_feature_flags

# Create fake request
factory = RequestFactory()
request = factory.get('/teams/')
request.user = AnonymousUser()

# Get context processor data
flags = vnext_feature_flags(request)

print("="*60)
print("  TEMPLATE RENDERING TEST")
print("="*60)
print()

print("1. Context Processor Flags:")
for key, value in flags.items():
    print(f"   {key} = {value}")
print()

# Load the actual template
template = loader.get_template('teams/list.html')

# Create minimal context for testing just the nav section
context = {
    **flags,
    'user': request.user,
    'teams': [],
    'teams_paginated': [],
    'filter_form': None,
}

print("2. Rendering template snippet...")
# Create a simple test template with the same logic
test_template_str = """
{% if TEAM_VNEXT_ADAPTER_ENABLED and not TEAM_VNEXT_FORCE_LEGACY and TEAM_VNEXT_ROUTING_MODE != 'legacy_only' %}
<a href="/teams/create/" class="navbar-btn secondary">
    <span>Team & Org BETA</span>
</a>
{% else %}
NO BUTTON - Condition failed
{% endif %}
"""

test_template = Template(test_template_str)
result = test_template.render(Context(context))

print("   Result:")
print(result)
print()

print("3. Checking actual template file...")
with open('templates/teams/list.html', 'r', encoding='utf-8') as f:
    content = f.read()
    if 'Team & Org' in content:
        print("   ✅ 'Team & Org' text FOUND in template file")
        # Find the line
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            if 'Team & Org' in line:
                print(f"   Line {i}: {line.strip()}")
    else:
        print("   ❌ 'Team & Org' text NOT FOUND in template file")
print()

print("4. Template condition breakdown:")
print(f"   TEAM_VNEXT_ADAPTER_ENABLED = {flags['TEAM_VNEXT_ADAPTER_ENABLED']}")
print(f"   TEAM_VNEXT_FORCE_LEGACY = {flags['TEAM_VNEXT_FORCE_LEGACY']}")
print(f"   TEAM_VNEXT_ROUTING_MODE = '{flags['TEAM_VNEXT_ROUTING_MODE']}'")
print()
print(f"   Condition: {flags['TEAM_VNEXT_ADAPTER_ENABLED']} AND NOT {flags['TEAM_VNEXT_FORCE_LEGACY']} AND '{flags['TEAM_VNEXT_ROUTING_MODE']}' != 'legacy_only'")

condition = (
    flags['TEAM_VNEXT_ADAPTER_ENABLED'] and 
    not flags['TEAM_VNEXT_FORCE_LEGACY'] and 
    flags['TEAM_VNEXT_ROUTING_MODE'] != 'legacy_only'
)
print(f"   Result: {condition}")
print(f"   Button visibility: {'✅ SHOULD BE VISIBLE' if condition else '❌ HIDDEN'}")
print()

print("="*60)
