# apps/tournaments/admin/tournaments_extras.py
from django.contrib import admin
from django.apps import apps

def _has_field(Model, name: str) -> bool:
    try:
        return any(f.name == name for f in Model._meta.get_fields())
    except Exception:
        return False

def _augment_tournament_admin():
    Tournament = apps.get_model('tournaments', 'Tournament')
    if Tournament not in admin.site._registry:
        return
    adm = admin.site._registry[Tournament]

    # Only proceed if the model actually has the field
    if not _has_field(Tournament, 'groups_published'):
        return

    # Add to list_display if not present
    ld = list(getattr(adm, 'list_display', []) or [])
    if 'groups_published' not in ld:
        ld.append('groups_published')
        adm.list_display = tuple(ld)

    # Add to list_filter if sensible
    lf = list(getattr(adm, 'list_filter', []) or [])
    if 'groups_published' not in lf:
        lf.append('groups_published')
        adm.list_filter = tuple(lf)

    # Add to fieldsets or fields
    if hasattr(adm, 'fieldsets') and adm.fieldsets:
        fs = list(adm.fieldsets)
        first = list(fs[0][1].get('fields', ()))
        if 'groups_published' not in first:
            first.append('groups_published')
            fs[0] = (fs[0][0], {**fs[0][1], 'fields': tuple(first)})
        adm.fieldsets = tuple(fs)
    else:
        fields = list(getattr(adm, 'fields', []) or [])
        if 'groups_published' not in fields:
            fields.append('groups_published')
            adm.fields = tuple(fields)

try:
    _augment_tournament_admin()
except Exception:
    # Keep admin robust even if anything is slightly different in your project
    pass
