# apps/economy/migrations/0004_coins_polish.py
from django.db import migrations, models
from django.conf import settings

# Raw SQL: only add columns / indexes if missing.
POSTGRES_SQL = r"""
-- Add columns idempotently (NO rename, no FK here)
ALTER TABLE "economy_deltacrowntransaction"
    ADD COLUMN IF NOT EXISTS "note" varchar(255) DEFAULT '' NOT NULL,
    ADD COLUMN IF NOT EXISTS "idempotency_key" varchar(64),
    ADD COLUMN IF NOT EXISTS "created_by_id" integer;

-- Unique index for idempotency_key (nullable)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'eco_tx_idempotency_key_uq') THEN
        CREATE UNIQUE INDEX eco_tx_idempotency_key_uq
            ON "economy_deltacrowntransaction" ("idempotency_key");
    END IF;
END$$;

-- Other indexes
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'eco_tx_reason_created_idx') THEN
        CREATE INDEX eco_tx_reason_created_idx
            ON "economy_deltacrowntransaction" ("reason", "created_at");
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'eco_tx_tournament_created_idx') THEN
        CREATE INDEX eco_tx_tournament_created_idx
            ON "economy_deltacrowntransaction" ("tournament_id", "created_at");
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'eco_tx_registration_idx') THEN
        CREATE INDEX eco_tx_registration_idx
            ON "economy_deltacrowntransaction" ("registration_id");
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'eco_tx_wallet_idx') THEN
        CREATE INDEX eco_tx_wallet_idx
            ON "economy_deltacrowntransaction" ("wallet_id");
    END IF;
END$$;
"""

SQLITE_SQL = [
    'ALTER TABLE "economy_deltacrowntransaction" ADD COLUMN IF NOT EXISTS "note" varchar(255) DEFAULT \'\' NOT NULL;',
    'ALTER TABLE "economy_deltacrowntransaction" ADD COLUMN IF NOT EXISTS "idempotency_key" varchar(64);',
    'ALTER TABLE "economy_deltacrowntransaction" ADD COLUMN IF NOT EXISTS "created_by_id" integer;',
    'CREATE UNIQUE INDEX IF NOT EXISTS "eco_tx_idempotency_key_uq" ON "economy_deltacrowntransaction" ("idempotency_key");',
    'CREATE INDEX IF NOT EXISTS "eco_tx_reason_created_idx" ON "economy_deltacrowntransaction" ("reason", "created_at");',
    'CREATE INDEX IF NOT EXISTS "eco_tx_tournament_created_idx" ON "economy_deltacrowntransaction" ("tournament_id", "created_at");',
    'CREATE INDEX IF NOT EXISTS "eco_tx_registration_idx" ON "economy_deltacrowntransaction" ("registration_id");',
    'CREATE INDEX IF NOT EXISTS "eco_tx_wallet_idx" ON "economy_deltacrowntransaction" ("wallet_id");',
]

def forwards(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        if schema_editor.connection.vendor == "postgresql":
            c.execute(POSTGRES_SQL)
        else:
            for stmt in SQLITE_SQL:
                c.execute(stmt)

def backwards(apps, schema_editor):
    # Non-destructive; keep columns/indexes.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("economy", "0003_remove_deltacrowntransaction_uq_participation_once_per_registration"),
        # Do NOT depend on auth here; we aren't creating the FK at the DB level in this migration.
    ]

    operations = [
        # 1) Apply DB changes safely (IF NOT EXISTS everywhere)
        migrations.RunPython(forwards, backwards),

        # 2) Update ONLY Django's state so ORM knows these fields exist,
        #    without running DB 'ALTER TABLE ADD COLUMN' again.
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="deltacrowntransaction",
                    name="note",
                    field=models.CharField(max_length=255, blank=True, default=""),
                ),
                migrations.AddField(
                    model_name="deltacrowntransaction",
                    name="idempotency_key",
                    field=models.CharField(max_length=64, null=True, blank=True, unique=True),
                ),
                migrations.AddField(
                    model_name="deltacrowntransaction",
                    name="created_by",
                    field=models.ForeignKey(
                        to=settings.AUTH_USER_MODEL,
                        on_delete=models.deletion.SET_NULL,
                        null=True,
                        blank=True,
                        related_name="coin_transactions_created",
                    ),
                ),
                migrations.AddIndex(
                    model_name="deltacrowntransaction",
                    index=models.Index(fields=["reason", "created_at"], name="eco_tx_reason_created_idx"),
                ),
                migrations.AddIndex(
                    model_name="deltacrowntransaction",
                    index=models.Index(fields=["tournament", "created_at"], name="eco_tx_tournament_created_idx"),
                ),
                migrations.AddIndex(
                    model_name="deltacrowntransaction",
                    index=models.Index(fields=["registration"], name="eco_tx_registration_idx"),
                ),
                migrations.AddIndex(
                    model_name="deltacrowntransaction",
                    index=models.Index(fields=["wallet"], name="eco_tx_wallet_idx"),
                ),
            ]
        ),
    ]
