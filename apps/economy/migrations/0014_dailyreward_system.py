"""
Daily Reward system:
  - DailyRewardConfig   (singleton schedule)
  - DailyRewardMilestone
  - DailyRewardClaim    (immutable log)
  - DailyLoginStreak.total_xp_earned  (new field)

Seeds one active DailyRewardConfig and 6 milestone rows.
"""
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


_DEFAULT_SCHEDULE = [
    {"day": "Thu", "xp": 25,  "dc": 0},
    {"day": "Fri", "xp": 30,  "dc": 0},
    {"day": "Sat", "xp": 40,  "dc": 2},
    {"day": "Sun", "xp": 50,  "dc": 0},
    {"day": "Mon", "xp": 60,  "dc": 3},
    {"day": "Tue", "xp": 75,  "dc": 0},
    {"day": "Wed", "xp": 100, "dc": 10},
]

_DEFAULT_MILESTONES = [
    (7,   100,  10,  "1-Week Warrior"),
    (14,  200,  20,  "Fortnight Grinder"),
    (30,  500,  50,  "Monthly Legend"),
    (60,  1000, 100, "Two-Month Elite"),
    (100, 2000, 200, "Century Crown"),
    (365, 5000, 500, "Eternal Champion"),
]


def seed_config_and_milestones(apps, schema_editor):
    DailyRewardConfig = apps.get_model("economy", "DailyRewardConfig")
    DailyRewardMilestone = apps.get_model("economy", "DailyRewardMilestone")

    if not DailyRewardConfig.objects.filter(is_active=True).exists():
        DailyRewardConfig.objects.create(
            name="Default",
            is_active=True,
            week_schedule=_DEFAULT_SCHEDULE,
        )

    for days, xp, dc, label in _DEFAULT_MILESTONES:
        DailyRewardMilestone.objects.get_or_create(
            streak_days=days,
            defaults={"bonus_xp": xp, "bonus_dc": dc, "label": label, "is_active": True},
        )


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0013_dailyloginstreak"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── 1. New field on existing DailyLoginStreak ────────────────────
        migrations.AddField(
            model_name="dailyloginstreak",
            name="total_xp_earned",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Lifetime XP earned via daily reward.",
            ),
        ),

        # ── 2. DailyRewardConfig ─────────────────────────────────────────
        migrations.CreateModel(
            name="DailyRewardConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, default="Default")),
                ("is_active", models.BooleanField(default=True, db_index=True)),
                ("week_schedule", models.JSONField(
                    default=list,
                    help_text="7-element list [{day,xp,dc}] — Thu=0 through Wed=6.",
                )),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "Daily Reward Config", "verbose_name_plural": "Daily Reward Configs"},
        ),

        # ── 3. DailyRewardMilestone ──────────────────────────────────────
        migrations.CreateModel(
            name="DailyRewardMilestone",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("streak_days", models.PositiveIntegerField(unique=True, db_index=True)),
                ("bonus_xp", models.PositiveIntegerField(default=0)),
                ("bonus_dc", models.PositiveIntegerField(default=0)),
                ("label", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Daily Reward Milestone",
                "verbose_name_plural": "Daily Reward Milestones",
                "ordering": ["streak_days"],
            },
        ),

        # ── 4. DailyRewardClaim ──────────────────────────────────────────
        migrations.CreateModel(
            name="DailyRewardClaim",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="daily_reward_claims",
                    to=settings.AUTH_USER_MODEL,
                    db_index=True,
                )),
                ("claimed_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("platform_date", models.DateField(db_index=True)),
                ("streak_day", models.PositiveIntegerField()),
                ("day_index", models.SmallIntegerField()),
                ("base_xp", models.PositiveIntegerField(default=0)),
                ("base_dc", models.PositiveIntegerField(default=0)),
                ("milestone_bonus_xp", models.PositiveIntegerField(default=0)),
                ("milestone_bonus_dc", models.PositiveIntegerField(default=0)),
                ("total_xp", models.PositiveIntegerField()),
                ("total_dc", models.PositiveIntegerField()),
                ("milestone", models.ForeignKey(
                    null=True, blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to="economy.dailyrewardmilestone",
                )),
                ("config", models.ForeignKey(
                    null=True, blank=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to="economy.dailyrewardconfig",
                )),
            ],
            options={
                "verbose_name": "Daily Reward Claim",
                "verbose_name_plural": "Daily Reward Claims",
                "ordering": ["-claimed_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="dailyrewardclaim",
            constraint=models.UniqueConstraint(
                fields=["user", "platform_date"],
                name="unique_daily_claim_per_user_per_day",
            ),
        ),

        # ── 5. Seed default config + milestones ──────────────────────────
        migrations.RunPython(seed_config_and_milestones, migrations.RunPython.noop),
    ]
