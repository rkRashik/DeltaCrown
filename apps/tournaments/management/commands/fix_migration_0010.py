"""
Fix migration 0010 - Drop incomplete tables and reset migration
"""
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Fix migration 0010 by dropping incomplete tables'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.stdout.write("Dropping incomplete form builder tables...")
            
            cursor.execute("DROP TABLE IF EXISTS tournaments_form_response CASCADE")
            self.stdout.write(self.style.SUCCESS("✓ Dropped tournaments_form_response"))
            
            cursor.execute("DROP TABLE IF EXISTS tournaments_registration_form CASCADE")
            self.stdout.write(self.style.SUCCESS("✓ Dropped tournaments_registration_form"))
            
            cursor.execute("DROP TABLE IF EXISTS tournaments_registration_form_template CASCADE")
            self.stdout.write(self.style.SUCCESS("✓ Dropped tournaments_registration_form_template"))
            
            cursor.execute("DELETE FROM django_migrations WHERE app = 'tournaments' AND name = '0010_create_form_builder_models'")
            self.stdout.write(self.style.SUCCESS("✓ Reset migration 0010"))
            
        self.stdout.write(self.style.SUCCESS("\n✅ Ready to run: python manage.py migrate tournaments"))
