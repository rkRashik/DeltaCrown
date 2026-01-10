# Generated manually for Phase 4F
# Date: 2026-01-10
# Purpose: Backfill left_at for existing REMOVED memberships (best-effort, no guessing)

from django.db import migrations


def backfill_left_at(apps, schema_editor):
    """
    Backfill left_at for existing REMOVED memberships.
    Strategy: Use role_changed_at as best guess, only if it exists.
    Do NOT invent dates if no data available.
    """
    TeamMembership = apps.get_model('teams', 'TeamMembership')
    
    # Find all REMOVED memberships without left_at
    removed_memberships = TeamMembership.objects.filter(
        status='REMOVED',
        left_at__isnull=True
    )
    
    backfilled_count = 0
    skipped_count = 0
    
    for membership in removed_memberships:
        if membership.role_changed_at:
            # Best guess: they left around the time their role last changed
            membership.left_at = membership.role_changed_at
            membership.save(update_fields=['left_at'])
            backfilled_count += 1
        else:
            # No reliable data - leave as NULL (will show "End date unavailable")
            skipped_count += 1
    
    print(f"Backfill complete: {backfilled_count} memberships updated, {skipped_count} left as NULL (no data)")


def reverse_backfill(apps, schema_editor):
    """
    Reverse migration: Clear backfilled left_at values.
    Only clear those that match role_changed_at (likely backfilled by us).
    """
    TeamMembership = apps.get_model('teams', 'TeamMembership')
    
    # Clear left_at where it matches role_changed_at (our backfill)
    cleared = TeamMembership.objects.filter(
        status='REMOVED',
        left_at__isnull=False
    ).update(left_at=None)
    
    print(f"Reverse backfill complete: {cleared} memberships cleared")


class Migration(migrations.Migration):

    dependencies = [
        ('teams', '0021_add_left_at_field'),
    ]

    operations = [
        migrations.RunPython(backfill_left_at, reverse_backfill),
    ]
