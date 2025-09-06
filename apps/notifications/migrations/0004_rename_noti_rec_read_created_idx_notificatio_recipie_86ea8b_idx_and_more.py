# Safe index fixer for Postgres: create target indexes if they don't exist; no-op otherwise.
from django.db import migrations

SQL_ENSURE_INDEXES = r"""
DO $$ BEGIN
  -- Index 1: (recipient_id, is_read, created_at)
  IF NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = ANY (current_schemas(false))
      AND indexname IN (
        'noti_rec_read_created_idx',
        'notifications_notification_recipient_id_is_read_created_at_idx'
      )
  ) THEN
    CREATE INDEX notifications_notification_recipient_id_is_read_created_at_idx
      ON notifications_notification (recipient_id, is_read, created_at);
  END IF;

  -- Index 2: (recipient_id, type, tournament_id, match_id)
  IF NOT EXISTS (
    SELECT 1
    FROM pg_indexes
    WHERE schemaname = ANY (current_schemas(false))
      AND indexname IN (
        'noti_rec_type_tour_match_idx',
        'notifications_notification_recipient_id_type_tournament_id_match_id_idx'
      )
  ) THEN
    CREATE INDEX notifications_notification_recipient_id_type_tournament_id_match_id_idx
      ON notifications_notification (recipient_id, type, tournament_id, match_id);
  END IF;
END $$;
"""

SQL_REVERSE = r"""
-- Drop only the canonical names; ignore if already gone.
DROP INDEX IF EXISTS notifications_notification_recipient_id_is_read_created_at_idx;
DROP INDEX IF EXISTS notifications_notification_recipient_id_type_tournament_id_match_id_idx;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("notifications", "0003_add_event_field"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL_ENSURE_INDEXES, reverse_sql=SQL_REVERSE),
    ]
