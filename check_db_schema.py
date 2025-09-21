#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
sys.path.append(os.path.dirname(__file__))
django.setup()

from django.db import connection

def check_table():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT column_name, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name='tournaments_paymentverification' 
            ORDER BY ordinal_position
        """)
        rows = cursor.fetchall()
        print('PaymentVerification table columns:')
        for row in rows:
            print(f'  {row[0]}: nullable={row[1]}, default={row[2]}')

if __name__ == '__main__':
    check_table()