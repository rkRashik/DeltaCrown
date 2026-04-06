"""
Add soft-delete columns to BracketNode table.

The 0001_initial migration moved the Bracket / BracketNode models from the
tournaments app to the brackets app using SeparateDatabaseAndState with
empty database_operations.  The model *state* already contains the
is_deleted / deleted_at / deleted_by columns (via SoftDeleteModel), but the
underlying ``tournament_engine_bracket_bracketnode`` table was never
altered.  This migration adds the three columns to the database only.
"""

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("brackets", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunSQL(
                    sql=[
                        'ALTER TABLE "tournament_engine_bracket_bracketnode" ADD COLUMN "is_deleted" boolean NOT NULL DEFAULT false;',
                        'CREATE INDEX "idx_bracketnode_is_deleted" ON "tournament_engine_bracket_bracketnode" ("is_deleted");',
                        'ALTER TABLE "tournament_engine_bracket_bracketnode" ADD COLUMN "deleted_at" timestamp with time zone NULL;',
                        'ALTER TABLE "tournament_engine_bracket_bracketnode" ADD COLUMN "deleted_by_id" integer NULL REFERENCES "accounts_user" ("id") DEFERRABLE INITIALLY DEFERRED;',
                        'CREATE INDEX "idx_bracketnode_deleted_by" ON "tournament_engine_bracket_bracketnode" ("deleted_by_id");',
                    ],
                    reverse_sql=[
                        'DROP INDEX IF EXISTS "idx_bracketnode_deleted_by";',
                        'DROP INDEX IF EXISTS "idx_bracketnode_is_deleted";',
                        'ALTER TABLE "tournament_engine_bracket_bracketnode" DROP COLUMN IF EXISTS "deleted_by_id";',
                        'ALTER TABLE "tournament_engine_bracket_bracketnode" DROP COLUMN IF EXISTS "deleted_at";',
                        'ALTER TABLE "tournament_engine_bracket_bracketnode" DROP COLUMN IF EXISTS "is_deleted";',
                    ],
                ),
            ],
        ),
    ]
