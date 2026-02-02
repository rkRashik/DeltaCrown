#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Deterministic .env loading - must happen before settings import
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)

# Fail-fast: Refuse to start if DATABASE_URL or DATABASE_URL_DEV is missing
# DATABASE_URL_DEV takes precedence (for fresh development databases)
if not os.getenv("DATABASE_URL_DEV") and not os.getenv("DATABASE_URL"):
    print("\n" + "="*70)
    print("ERROR: Neither DATABASE_URL_DEV nor DATABASE_URL is set!")
    print("="*70)
    print("\nTo prevent accidental use of localhost database,")
    print("DeltaCrown requires a database URL to be explicitly set.")
    print("\nFor a fresh development database:")
    print("  DATABASE_URL_DEV=postgresql://user:pass@host:port/dbname")
    print("\nFor production-like database:")
    print("  DATABASE_URL=postgresql://user:pass@host:port/dbname")
    print("\nCreate a .env file in the project root or set as environment variable.")
    print("="*70 + "\n")
    sys.exit(1)


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
