#!/usr/bin/env python
import os, sys, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings_test')
django.setup()
from django.db import connection

print('='*70)
print('GAME PASSPORT TEST SCHEMA SETUP')
print('='*70)
print('\n[1/1] Recreating test_schema (clean slate)...')
with connection.cursor() as cursor:
    cursor.execute('DROP SCHEMA IF EXISTS test_schema CASCADE')
    cursor.execute('CREATE SCHEMA test_schema')
print(' test_schema recreated\n' + '='*70)
print('TEST SCHEMA COMPLETE - Run pytest to apply migrations')
print('='*70)