"""Add all missing social URL columns"""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')
django.setup()

from django.db import connection

missing_columns = [
    "twitter_url varchar(200) DEFAULT ''",
    "instagram_url varchar(200) DEFAULT ''",
    "youtube_url varchar(200) DEFAULT ''",
    "twitch_url varchar(200) DEFAULT ''"
]

with connection.cursor() as cursor:
    for col_def in missing_columns:
        col_name = col_def.split()[0]
        cursor.execute(f"""
            ALTER TABLE organizations_team 
            ADD COLUMN IF NOT EXISTS {col_def}
        """)
        print(f"✓ Added {col_name}")
    
    print("\n✓ All social URL columns added")
