#!/usr/bin/env python
"""Comprehensive audit of @rkrashik Career Tab data"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from apps.accounts.models import User
from apps.user_profile.models import GameProfile, UserProfile
from apps.teams.models import Team, TeamMembership
from apps.tournaments.models import Registration

print("="*80)
print("CAREER TAB DATA AUDIT FOR @rkrashik")
print("="*80)

try:
    user = User.objects.get(username='testuser_phase9a7')
    print(f"\n✓ User found: {user.username} (ID: {user.id})")
except User.DoesNotExist:
    print("\n✗ User 'rkrashik' NOT FOUND")
    exit(1)

# Get UserProfile
try:
    profile = user.profile
    print(f"✓ UserProfile found (ID: {profile.id})")
    
    # Check primary_game field
    if hasattr(profile, 'primary_game'):
        print(f"  Primary Game Field: {profile.primary_game}")
    else:
        print(f"  Primary Game Field: NOT FOUND (DB column missing)")
except Exception as e:
    print(f"✗ UserProfile error: {e}")
    profile = None

print("\n" + "="*80)
print("A) LINKED PASSPORTS (GameProfile)")
print("="*80)

passports = GameProfile.objects.filter(user=user).select_related('game')
print(f"\nFound {passports.count()} GameProfile(s):\n")

for idx, gp in enumerate(passports, 1):
    print(f"{idx}. Game: {gp.game.slug} ({gp.game.display_name})")
    print(f"   In-Game Name: {gp.in_game_name}")
    print(f"   IGN: {getattr(gp, 'ign', 'N/A')}")
    print(f"   Discriminator: {getattr(gp, 'discriminator', 'N/A')}")
    print(f"   Region: {getattr(gp, 'region', 'N/A')}")
    print(f"   Platform: {getattr(gp, 'platform', 'N/A')}")
    print(f"   Identity Key: {getattr(gp, 'identity_key', 'N/A')}")
    
    # Metadata keys
    metadata = getattr(gp, 'metadata', {})
    if metadata:
        print(f"   Metadata Keys: {list(metadata.keys())}")
    else:
        print(f"   Metadata Keys: (empty)")
    
    # Rank info
    print(f"   Rank Name: {gp.rank_name or 'N/A'}")
    print(f"   Rank Tier: {gp.rank_tier}")
    print(f"   Rank Points: {getattr(gp, 'rank_points', 'N/A')}")
    print(f"   Peak Rank: {getattr(gp, 'peak_rank', 'N/A')}")
    
    # Rank image
    if hasattr(gp, 'rank_image') and gp.rank_image:
        print(f"   Rank Image: EXISTS → {gp.rank_image.url}")
    else:
        print(f"   Rank Image: NOT SET")
    
    # Game logo/icon/banner
    print(f"   Game Logo: {gp.game.logo.url if gp.game.logo else 'NOT SET'}")
    print(f"   Game Icon: {gp.game.icon.url if gp.game.icon else 'NOT SET'}")
    print(f"   Game Banner: {gp.game.banner.url if gp.game.banner else 'NOT SET'}")
    print()

print("\n" + "="*80)
print("B) PRIMARY GAME ORDERING")
print("="*80)

if hasattr(profile, 'primary_game') and profile.primary_game:
    print(f"\nUserProfile.primary_game = {profile.primary_game}")
else:
    print("\nPrimary game field missing or null.")
    print("Fallback ordering: is_pinned DESC, pinned_order ASC, created_at DESC")
    
    pinned = GameProfile.objects.filter(user=user, is_pinned=True).order_by('pinned_order')
    if pinned.exists():
        print(f"  → First pinned game: {pinned.first().game.slug}")
    else:
        print(f"  → No pinned games. Ordering by created_at DESC")
        if passports.exists():
            print(f"  → First game: {passports.order_by('-created_at').first().game.slug}")

print("\n" + "="*80)
print("C) TEAM MEMBERSHIPS")
print("="*80)

if profile:
    memberships = TeamMembership.objects.filter(profile=profile).select_related('team')
    print(f"\nFound {memberships.count()} TeamMembership(s):\n")
    
    for idx, tm in enumerate(memberships, 1):
        print(f"{idx}. Team: {tm.team.name} (slug: {tm.team.slug})")
        print(f"   Team Game: {getattr(tm.team, 'game', 'NO GAME FIELD')}")
        print(f"   Role: {tm.role} ({tm.get_role_display() if hasattr(tm, 'get_role_display') else 'N/A'})")
        print(f"   Joined: {tm.joined_at}")
        print(f"   Left: {tm.left_at or 'ACTIVE'}")
        print(f"   Status: {tm.status}")
        
        if hasattr(tm.team, 'logo') and tm.team.logo:
            print(f"   Team Logo: EXISTS → {tm.team.logo.url}")
        else:
            print(f"   Team Logo: NOT SET")
        print()
else:
    print("\nCannot query memberships (no profile)")

print("\n" + "="*80)
print("D) TOURNAMENT PARTICIPATION (Registration)")
print("="*80)

registrations = Registration.objects.filter(user=user).select_related('tournament')
print(f"\nFound {registrations.count()} Registration(s):\n")

for idx, reg in enumerate(registrations[:10], 1):  # Limit to 10
    print(f"{idx}. Tournament: {reg.tournament.title if hasattr(reg.tournament, 'title') else reg.tournament.name}")
    print(f"   Slug: {reg.tournament.slug}")
    print(f"   Game: {reg.tournament.game.slug if hasattr(reg.tournament, 'game') else 'NO GAME FK'}")
    print(f"   Status: {reg.status}")
    
    # Placement fields
    placement_fields = ['placement', 'final_placement', 'final_standing', 'position']
    for field in placement_fields:
        if hasattr(reg, field):
            val = getattr(reg, field, None)
            if val:
                print(f"   {field}: {val}")
    
    # Prize fields
    prize_fields = ['prize_won', 'prize_amount', 'prize_pool']
    for field in prize_fields:
        if hasattr(reg, field):
            val = getattr(reg, field, None)
            if val:
                print(f"   {field}: {val}")
    
    # Attributes
    if hasattr(reg.tournament, 'attributes') and reg.tournament.attributes:
        print(f"   Tournament Attributes Keys: {list(reg.tournament.attributes.keys())}")
    
    print()

print("\n" + "="*80)
print("AUDIT COMPLETE")
print("="*80)
