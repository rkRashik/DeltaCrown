# Generated manually for Phase 19: ELO rating + tier rebrand

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organizations", "0042_phase18_activity_antiabuse_fields"),
    ]

    operations = [
        # 1. Add elo_rating field (internal, default 1200)
        migrations.AddField(
            model_name="teamranking",
            name="elo_rating",
            field=models.IntegerField(
                default=1200,
                help_text="Internal ELO rating (K=32). Drives CP scaling, not shown to users.",
            ),
        ),
        # 2. Update tier default from UNRANKED to ROOKIE
        migrations.AlterField(
            model_name="teamranking",
            name="tier",
            field=models.CharField(
                choices=[
                    ("ROOKIE", "Rookie"),
                    ("CHALLENGER", "Challenger"),
                    ("ELITE", "Elite"),
                    ("MASTER", "Master"),
                    ("LEGEND", "Legend"),
                    ("THE_CROWN", "The Crown"),
                ],
                db_index=True,
                default="ROOKIE",
                help_text="Tier based on current CP thresholds",
                max_length=20,
            ),
        ),
        # 3. Migrate existing tier values to new names
        migrations.RunSQL(
            sql="""
                UPDATE organizations_ranking SET tier = CASE
                    WHEN tier = 'UNRANKED' THEN 'ROOKIE'
                    WHEN tier = 'BRONZE' THEN 'ROOKIE'
                    WHEN tier = 'SILVER' THEN 'CHALLENGER'
                    WHEN tier = 'GOLD' THEN 'ELITE'
                    WHEN tier = 'PLATINUM' THEN 'MASTER'
                    WHEN tier = 'DIAMOND' THEN 'LEGEND'
                    WHEN tier = 'ASCENDANT' THEN 'LEGEND'
                    WHEN tier = 'CROWN' THEN 'THE_CROWN'
                    ELSE tier
                END
                WHERE tier IN ('UNRANKED', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'DIAMOND', 'ASCENDANT', 'CROWN');
            """,
            reverse_sql="""
                UPDATE organizations_ranking SET tier = CASE
                    WHEN tier = 'ROOKIE' THEN 'UNRANKED'
                    WHEN tier = 'CHALLENGER' THEN 'SILVER'
                    WHEN tier = 'ELITE' THEN 'GOLD'
                    WHEN tier = 'MASTER' THEN 'PLATINUM'
                    WHEN tier = 'LEGEND' THEN 'DIAMOND'
                    WHEN tier = 'THE_CROWN' THEN 'CROWN'
                    ELSE tier
                END
                WHERE tier IN ('ROOKIE', 'CHALLENGER', 'ELITE', 'MASTER', 'LEGEND', 'THE_CROWN');
            """,
        ),
    ]
