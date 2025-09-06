from django.db import migrations

class Migration(migrations.Migration):

    # Adjust numbers if your local sequence differs
    dependencies = [
        ("tournaments", "0004_remove_paymentverification_pv_payer_account_idx_and_more"),
        ("tournaments", "0005_groups_published"),
    ]

    operations = [
        # No-op merge: just reconciles the graph so future migrations apply linearly.
    ]
