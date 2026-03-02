"""Wrapper to run seeder - writes all output to seeder_log.txt."""
import os, sys, traceback

# Redirect both stdout and stderr to a file directly from Python
# Use line buffering (buffering=1) to ensure output is written immediately
log_file = open('seeder_log.txt', 'w', encoding='utf-8', errors='replace', buffering=1)
sys.stdout = log_file
sys.stderr = log_file

print("=== WRAPPER STARTED ===", flush=True)

# Load DATABASE_URL from .env
with open('.env') as f:
    for line in f:
        if line.startswith('DATABASE_URL='):
            os.environ['DATABASE_URL'] = line.strip().split('=', 1)[1]
            break

os.environ['DJANGO_SETTINGS_MODULE'] = 'deltacrown.settings'

import django
django.setup()

import logging
logging.disable(logging.CRITICAL)  # Suppress ALL logs AFTER setup

from django.core.management import call_command

print("=== CALLING SEEDER ===", flush=True)

try:
    call_command('seed_uradhura_ucl', '--purge', '--with-results', verbosity=1)
    print("\n=== SEEDER COMPLETED SUCCESSFULLY ===", flush=True)
except BaseException as exc:
    print(f"\n=== SEEDER FAILED ===", flush=True)
    print(f"Exception type: {type(exc).__name__}", flush=True)
    print(f"Exception: {exc}", flush=True)
    traceback.print_exc(file=log_file)
    log_file.flush()
finally:
    print("=== WRAPPER DONE ===", flush=True)
    log_file.flush()
    log_file.close()
