# Generated manually for Phase 2 - Task 6.1
# Convert legacy CAPTAIN role to OWNER or MANAGER

from django.db import migrations


def convert_captain_to_owner(apps, schema_editor):
    """
    Phase 2 Task 6.1: Convert CAPTAIN roles to OWNER or MANAGER.
    
    Logic:
    - If team has no OWNER: convert CAPTAIN → OWNER
    - If team has OWNER: convert CAPTAIN → MANAGER and set is_captain=True
    """
    TeamMembership = apps.get_model('teams', 'TeamMembership')
    
    # Find all CAPTAIN memberships
    captain_memberships = TeamMembership.objects.filter(role='CAPTAIN', status='ACTIVE')
    
    converted_count = 0
    for membership in captain_memberships:
        team = membership.team
        
        # Check if team already has an OWNER
        has_owner = TeamMembership.objects.filter(
            team=team,
            role='OWNER',
            status='ACTIVE'
        ).exists()
        
        if has_owner:
            # Convert to MANAGER with captain designation
            membership.role = 'MANAGER'
            membership.is_captain = True
            membership.save(update_fields=['role', 'is_captain'])
            converted_count += 1
            print(f"  Converted CAPTAIN to MANAGER (captain designation) for team {team.name}")
        else:
            # Convert to OWNER
            membership.role = 'OWNER'
            membership.save(update_fields=['role'])
            converted_count += 1
            print(f"  Converted CAPTAIN to OWNER for team {team.name}")
    
    print(f"✅ Converted {converted_count} CAPTAIN roles")


def reverse_migration(apps, schema_editor):
    """Reverse: convert OWNER/MANAGER back to CAPTAIN (for rollback)"""
    TeamMembership = apps.get_model('teams', 'TeamMembership')
    
    # Convert OWNER back to CAPTAIN
    owners = TeamMembership.objects.filter(role='OWNER', status='ACTIVE')
    owner_count = owners.count()
    owners.update(role='CAPTAIN')
    
    # Convert MANAGER with is_captain=True back to CAPTAIN
    captain_managers = TeamMembership.objects.filter(
        role='MANAGER',
        is_captain=True,
        status='ACTIVE'
    )
    manager_count = captain_managers.count()
    captain_managers.update(role='CAPTAIN', is_captain=False)
    
    print(f"⏪ Reversed {owner_count} OWNERs and {manager_count} captain MANAGERs to CAPTAIN")


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0010_add_phase1_performance_indexes'),
    ]

    operations = [
        migrations.RunPython(convert_captain_to_owner, reverse_migration),
    ]
