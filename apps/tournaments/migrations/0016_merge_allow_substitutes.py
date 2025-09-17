# Generated manually to merge parallel migrations introducing allow_substitutes.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tournaments", "0014_add_allow_substitutes"),
        ("tournaments", "0015_add_allow_substitutes_to_settings"),
    ]

    operations = []