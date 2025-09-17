
from django.db import migrations


def _perms(permission_model, content_type_model, app_label, model_name, actions):
    try:
        ct = content_type_model.objects.get(app_label=app_label, model=model_name)
    except content_type_model.DoesNotExist:
        return []
    codenames = [f"{action}_{model_name}" for action in actions]
    return list(permission_model.objects.filter(content_type=ct, codename__in=codenames))


def create_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    groups = {
        'Platform Admin': 'ALL',
        'Tournament Staff': [
            ('tournaments', 'tournament', ('view', 'change', 'add')),
            ('tournaments', 'registration', ('view', 'change', 'add')),
            ('tournaments', 'match', ('view', 'change')),
            ('tournaments', 'paymentverification', ('view', 'change')),
        ],
        'Valorant Organizer': [
            ('tournaments', 'tournament', ('view', 'change')),
            ('tournaments', 'registration', ('view', 'change')),
            ('game_valorant', 'valorantconfig', ('view', 'change')),
            ('teams', 'team', ('view', 'change')),
        ],
        'Efootball Organizer': [
            ('tournaments', 'tournament', ('view', 'change')),
            ('tournaments', 'registration', ('view', 'change')),
            ('game_efootball', 'efootballconfig', ('view', 'change')),
            ('teams', 'team', ('view', 'change')),
        ],
        'Team Manager': [
            ('teams', 'team', ('view', 'change')),
            ('teams', 'teammembership', ('view', 'change')),
        ],
    }

    all_perms = list(Permission.objects.all())

    for name, rules in groups.items():
        group, _ = Group.objects.get_or_create(name=name)
        if rules == 'ALL':
            group.permissions.set(all_perms)
            continue
        perms = []
        for app_label, model_name, actions in rules:
            perms.extend(_perms(Permission, ContentType, app_label, model_name, actions))
        group.permissions.set(perms)


def remove_groups(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=[
        'Platform Admin',
        'Tournament Staff',
        'Valorant Organizer',
        'Efootball Organizer',
        'Team Manager',
    ]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_pendingsignup_alter_emailotp_user_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_groups, remove_groups),
    ]

