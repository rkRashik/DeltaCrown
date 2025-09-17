from django.db import migrations


GROUP_DEFINITIONS = {
    "Valorant Organizer": (
        ("tournaments", "tournament", ("view", "change", "add")),
        ("tournaments", "tournamentsettings", ("view", "change")),
        ("tournaments", "registration", ("view", "change")),
        ("tournaments", "match", ("view", "change")),
        ("tournaments", "paymentverification", ("view", "change")),
        ("game_valorant", "valorantconfig", ("view", "change")),
        ("teams", "team", ("view", "change")),
        ("teams", "teammembership", ("view", "change")),
    ),
    "eFootball Organizer": (
        ("tournaments", "tournament", ("view", "change", "add")),
        ("tournaments", "tournamentsettings", ("view", "change")),
        ("tournaments", "registration", ("view", "change")),
        ("tournaments", "match", ("view", "change")),
        ("tournaments", "paymentverification", ("view", "change")),
        ("game_efootball", "efootballconfig", ("view", "change")),
        ("teams", "team", ("view", "change")),
        ("teams", "teammembership", ("view", "change")),
    ),
    "Team Moderator": (
        ("teams", "team", ("view", "change")),
        ("teams", "teammembership", ("view", "change")),
        ("teams", "teaminvite", ("view", "change", "add")),
    ),
    "Support Staff": (
        ("tournaments", "tournament", ("view",)),
        ("tournaments", "tournamentsettings", ("view",)),
        ("tournaments", "registration", ("view", "change")),
        ("tournaments", "paymentverification", ("view", "change")),
        ("tournaments", "match", ("view",)),
    ),
}

RENAMED_GROUPS = {
    "Efootball Organizer": "eFootball Organizer",
    "Team Manager": "Team Moderator",
    "Tournament Staff": "Support Staff",
}

LEGACY_GROUPS = {"Platform Admin"}


def _perms(permission_model, content_type_model, app_label, model_name, actions):
    try:
        ct = content_type_model.objects.get(app_label=app_label, model=model_name)
    except content_type_model.DoesNotExist:
        return []
    codenames = [f"{action}_{model_name}" for action in actions]
    return list(permission_model.objects.filter(content_type=ct, codename__in=codenames))


def apply_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")

    # Rename legacy groups to their new titles when possible to preserve membership.
    for old, new in RENAMED_GROUPS.items():
        try:
            group = Group.objects.get(name=old)
        except Group.DoesNotExist:
            continue
        Group.objects.filter(name=new).exclude(pk=group.pk).delete()
        group.name = new
        group.save(update_fields=["name"])

    # Remove groups we no longer keep.
    Group.objects.filter(name__in=LEGACY_GROUPS).delete()

    # Create/update scoped staff groups with the desired permissions.
    for name, specs in GROUP_DEFINITIONS.items():
        group, _ = Group.objects.get_or_create(name=name)
        perms = []
        for app_label, model_name, actions in specs:
            perms.extend(_perms(Permission, ContentType, app_label, model_name, actions))
        group.permissions.set(perms)


def teardown_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GROUP_DEFINITIONS.keys()).delete()
    # Best-effort recreation of legacy names for reversibility.
    for old in RENAMED_GROUPS.keys():
        Group.objects.get_or_create(name=old)
    for name in LEGACY_GROUPS:
        Group.objects.get_or_create(name=name)


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_create_default_groups"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(apply_groups, teardown_groups),
    ]