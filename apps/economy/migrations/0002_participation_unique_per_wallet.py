from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ("economy", "0001_initial"),
    ]

    operations = [
        # Safely drop any old constraint if it ever existed (on any table name),
        # so applying this migration is idempotent across machines.
        migrations.RunSQL(
            sql="""
DO $$
BEGIN
    IF to_regclass('public.economy_deltacrowntransaction') IS NOT NULL THEN
        EXECUTE 'ALTER TABLE public.economy_deltacrowntransaction
                 DROP CONSTRAINT IF EXISTS uq_participation_once_per_registration';
    END IF;
    IF to_regclass('public.ecommerce_deltacrowntransaction') IS NOT NULL THEN
        EXECUTE 'ALTER TABLE public.ecommerce_deltacrowntransaction
                 DROP CONSTRAINT IF EXISTS uq_participation_once_per_registration';
    END IF;
END $$;
""",
            reverse_sql="-- no-op",
        ),
        migrations.AddConstraint(
            model_name="deltacrowntransaction",
            constraint=models.UniqueConstraint(
                fields=("registration", "wallet", "reason"),
                condition=models.Q(("reason", "participation")),
                name="uq_participation_once_per_registration_wallet",
            ),
        ),
    ]
