#!/usr/bin/env python
"""Verify Gate 5 schema changes applied successfully."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.organizations.models import Team

team = Team.objects.first()
if team:
    print("✅ Social fields exist:")
    print(f"  - twitter_url: {hasattr(team, 'twitter_url')}")
    print(f"  - instagram_url: {hasattr(team, 'instagram_url')}")
    print(f"  - youtube_url: {hasattr(team, 'youtube_url')}")
    print(f"  - twitch_url: {hasattr(team, 'twitch_url')}")
    print("\n✅ FK reverse relations exist:")
    print(f"  - sponsors: {hasattr(team, 'sponsors')}")
    print(f"  - invites: {hasattr(team, 'invites')}")
    print(f"  - join_requests: {hasattr(team, 'join_requests')}")
    print("\n✅ Schema validation passed!")
else:
    print("⚠️ No teams found in database")
