"""
Debug migration execution to find what's creating duplicate tables.
"""
import sys
import logging
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.backends.postgresql import schema

# Monkey-patch schema editor to log all SQL
original_execute = schema.DatabaseSchemaEditor.execute

def logged_execute(self, sql, params=()):
    import traceback
    print(f"\n{'='*80}")
    print(f"SQL: {sql[:200]}...")
    print(f"Params: {params}")
    print("Call stack:")
    for line in traceback.format_stack()[:-1]:
        if '/django/' in line or '/apps/' in line:
            print(line.strip())
    print('='*80)
    return original_execute(self, sql, params)

schema.DatabaseSchemaEditor.execute = logged_execute


class Command(BaseCommand):
    help = 'Run migrations with detailed SQL logging'

    def handle(self, *args, **options):
        from django.core.management import call_command
        call_command('migrate', verbosity=2)
