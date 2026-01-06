"""
Management command to fix eFootball schema by removing incorrect fields.

Phase 9A-16: Remove owner_id and ign from eFootball, keep only:
- konami_id
- efootball_id
- username
- platform
- division
- team_name (optional)
"""

from django.core.management.base import BaseCommand
from apps.games.models import Game, GamePlayerIdentityConfig


class Command(BaseCommand):
    help = 'Fix eFootball schema by removing owner_id and ign fields'

    def handle(self, *args, **options):
        self.stdout.write('\n[PHASE 9A-16] Fixing eFootball schema...\n')
        
        try:
            game = Game.objects.get(slug='efootball')
        except Game.DoesNotExist:
            self.stdout.write(self.style.ERROR('[ERROR] eFootball game not found'))
            return
        
        # Delete incorrect fields
        deleted_owner_id = GamePlayerIdentityConfig.objects.filter(
            game=game,
            field_name='owner_id'
        ).delete()
        
        deleted_ign = GamePlayerIdentityConfig.objects.filter(
            game=game,
            field_name='ign'
        ).delete()
        
        deleted_team_name = GamePlayerIdentityConfig.objects.filter(
            game=game,
            field_name='team_name'
        ).delete()
        
        if deleted_owner_id[0] > 0:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Deleted owner_id field'))
        else:
            self.stdout.write('  ℹ️  owner_id field not found (already clean)')
        
        if deleted_ign[0] > 0:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Deleted ign field'))
        else:
            self.stdout.write('  ℹ️  ign field not found (already clean)')
        
        if deleted_team_name[0] > 0:
            self.stdout.write(self.style.SUCCESS(f'  ✅ Deleted team_name field'))
        else:
            self.stdout.write('  ℹ️  team_name field not found (already clean)')
        
        # Show remaining fields
        remaining_fields = GamePlayerIdentityConfig.objects.filter(
            game=game
        ).values_list('field_name', flat=True).order_by('order')
        
        self.stdout.write(f'\n✅ Remaining eFootball fields: {list(remaining_fields)}')
        self.stdout.write(self.style.SUCCESS('\n[SUCCESS] eFootball schema cleaned!'))
        self.stdout.write('\n💡 Now run: python manage.py seed_identity_configs_2026 --game efootball --force\n')
