# apps/tournaments/migrations/0003_paymentverification_add_payer_txid.py
from django.db import migrations, models


POSTGRES_SQL = r"""
ALTER TABLE "tournaments_paymentverification"
    ADD COLUMN IF NOT EXISTS "payer_account_number" varchar(32) DEFAULT '' NOT NULL,
    ADD COLUMN IF NOT EXISTS "transaction_id" varchar(64) DEFAULT '' NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'pv_payer_account_idx') THEN
        CREATE INDEX pv_payer_account_idx
            ON "tournaments_paymentverification" ("payer_account_number");
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = 'pv_transaction_id_idx') THEN
        CREATE INDEX pv_transaction_id_idx
            ON "tournaments_paymentverification" ("transaction_id");
    END IF;
END$$;
"""

SQLITE_SQL = [
    'ALTER TABLE "tournaments_paymentverification" ADD COLUMN IF NOT EXISTS "payer_account_number" varchar(32) DEFAULT \'\' NOT NULL;',
    'ALTER TABLE "tournaments_paymentverification" ADD COLUMN IF NOT EXISTS "transaction_id" varchar(64) DEFAULT \'\' NOT NULL;',
    'CREATE INDEX IF NOT EXISTS "pv_payer_account_idx" ON "tournaments_paymentverification" ("payer_account_number");',
    'CREATE INDEX IF NOT EXISTS "pv_transaction_id_idx" ON "tournaments_paymentverification" ("transaction_id");',
]


def forwards(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        if schema_editor.connection.vendor == "postgresql":
            c.execute(POSTGRES_SQL)
        else:
            for stmt in SQLITE_SQL:
                c.execute(stmt)


def backwards(apps, schema_editor):
    # Non-destructive; we keep columns/indexes.
    pass


class Migration(migrations.Migration):
    # depend on the immediately previous migration to avoid cycles
    dependencies = [
        ("tournaments", "0002_sync_ts_audit_columns"),
    ]

    operations = [
        # Apply DB changes safely (no-op if they already exist)
        migrations.RunPython(forwards, backwards),

        # Update Django state ONLY (no DB ops duplicated)
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="paymentverification",
                    name="payer_account_number",
                    field=models.CharField(max_length=32, blank=True, default=""),
                ),
                migrations.AddField(
                    model_name="paymentverification",
                    name="transaction_id",
                    field=models.CharField(max_length=64, blank=True, default=""),
                ),
                migrations.AddIndex(
                    model_name="paymentverification",
                    index=models.Index(fields=["payer_account_number"], name="pv_payer_account_idx"),
                ),
                migrations.AddIndex(
                    model_name="paymentverification",
                    index=models.Index(fields=["transaction_id"], name="pv_transaction_id_idx"),
                ),
            ]
        ),
    ]
