# apps/tournaments/admin/userprefs.py
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

from ..models.userprefs import CalendarFeedToken, SavedMatchFilter, PinnedTournament

class SavedMatchFilterAdmin(admin.ModelAdmin):
    list_display = ("user", "name", "is_default", "game", "state", "tournament_id", "start_date", "end_date", "updated_at")
    list_filter = ("is_default", "game", "state")
    search_fields = ("user__username", "name")

for model, admin_cls in [
    (CalendarFeedToken, admin.ModelAdmin),
    (SavedMatchFilter, SavedMatchFilterAdmin),
    (PinnedTournament, admin.ModelAdmin),
]:
    try:
        admin.site.register(model, admin_cls)
    except AlreadyRegistered:
        pass
