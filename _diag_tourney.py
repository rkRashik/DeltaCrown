import os, django
os.environ['DJANGO_SETTINGS_MODULE'] = 'deltacrown.settings'
django.setup()

from apps.tournaments.models.tournament import Tournament

# Check the tournament
t = Tournament.objects.filter(slug='uradhura-ucl-s1').first()
if t:
    print("Found: {} (id={})".format(t.name, t.id))
    print("  status={}  is_published={}  visibility={}".format(
        t.status, getattr(t, 'is_published', 'N/A'), getattr(t, 'visibility', 'N/A')))
    print("  game={}  game_slug={}".format(
        getattr(t.game, 'display_name', None) if t.game else None,
        getattr(t.game, 'slug', None) if t.game else None))
    print("  format={}  participation_type={}".format(t.format, getattr(t, 'participation_type', 'N/A')))
    print("  is_deleted={}".format(getattr(t, 'is_deleted', 'N/A')))
    print("  created={}".format(t.created_at if hasattr(t, 'created_at') else 'N/A'))
    # Check all boolean flags
    for field in t._meta.get_fields():
        if hasattr(field, 'get_internal_type') and field.get_internal_type() == 'BooleanField':
            print("  {}: {}".format(field.name, getattr(t, field.name, None)))
else:
    print("NOT FOUND: uradhura-ucl-s1")
    # Try partial match
    for t in Tournament.objects.filter(slug__icontains='ucl'):
        print("  Similar: slug={} title={} status={}".format(t.slug, t.title, t.status))
