from django.db import migrations


def forward(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    mapping = {
        "REG_CONFIRMED": "reg_confirmed",
        "BRACKET_READY": "bracket_ready",
        "MATCH_SCHEDULED": "match_scheduled",
        "RESULT_VERIFIED": "result_verified",
        "PAYMENT_VERIFIED": "payment_verified",
        "CHECKIN_OPEN": "checkin_open",
    }
    for old, new in mapping.items():
        Notification.objects.filter(type=old).update(type=new)


def backward(apps, schema_editor):
    Notification = apps.get_model("notifications", "Notification")
    mapping = {
        "reg_confirmed": "REG_CONFIRMED",
        "bracket_ready": "BRACKET_READY",
        "match_scheduled": "MATCH_SCHEDULED",
        "result_verified": "RESULT_VERIFIED",
        "payment_verified": "PAYMENT_VERIFIED",
        "checkin_open": "CHECKIN_OPEN",
    }
    for old, new in mapping.items():
        Notification.objects.filter(type=old).update(type=new)


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
