from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0019_alter_tournamentsettings_automatic_scheduling_enabled"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE tournaments_tournamentsettings ALTER COLUMN check_in_open_mins DROP NOT NULL",
            reverse_sql=(
                "UPDATE tournaments_tournamentsettings SET check_in_open_mins = 60 "
                "WHERE check_in_open_mins IS NULL;"
                "ALTER TABLE tournaments_tournamentsettings ALTER COLUMN check_in_open_mins SET NOT NULL"
            ),
        ),
        migrations.RunSQL(
            sql="ALTER TABLE tournaments_tournamentsettings ALTER COLUMN check_in_close_mins DROP NOT NULL",
            reverse_sql=(
                "UPDATE tournaments_tournamentsettings SET check_in_close_mins = 15 "
                "WHERE check_in_close_mins IS NULL;"
                "ALTER TABLE tournaments_tournamentsettings ALTER COLUMN check_in_close_mins SET NOT NULL"
            ),
        ),
    ]