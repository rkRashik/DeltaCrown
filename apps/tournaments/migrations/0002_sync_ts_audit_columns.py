from django.db import migrations

SQL = r"""
DO $$
BEGIN
  -- Add created_at if it's missing
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = current_schema()
       AND table_name = 'tournaments_tournamentsettings'
       AND column_name = 'created_at'
  ) THEN
    ALTER TABLE tournaments_tournamentsettings
      ADD COLUMN created_at timestamp with time zone DEFAULT now() NOT NULL;
  END IF;

  -- Add updated_at if it's missing
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
     WHERE table_schema = current_schema()
       AND table_name = 'tournaments_tournamentsettings'
       AND column_name = 'updated_at'
  ) THEN
    ALTER TABLE tournaments_tournamentsettings
      ADD COLUMN updated_at timestamp with time zone DEFAULT now() NOT NULL;
  END IF;
END $$;
"""

class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(SQL, reverse_sql=migrations.RunSQL.noop),
    ]
