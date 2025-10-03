# apps/tournaments/admin/userprefs.py
"""
DEPRECATED: User preferences should be managed via API/frontend, not Django admin.

This file previously registered UI preference models (CalendarFeedToken, SavedMatchFilter, 
PinnedTournament) in Django admin. These models are user-facing preferences and should not 
clutter the administrative interface.

If you need to manage these models administratively, uncomment the code below.
"""

from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered

# Commented out - UI preferences should not be in admin
# from ..models.userprefs import CalendarFeedToken, SavedMatchFilter, PinnedTournament
#
# class SavedMatchFilterAdmin(admin.ModelAdmin):
#     list_display = ("user", "name", "is_default", "game", "state", "tournament_id", "start_date", "end_date", "updated_at")
#     list_filter = ("is_default", "game", "state")
#     search_fields = ("user__username", "name")
#
# for model, admin_cls in [
#     (CalendarFeedToken, admin.ModelAdmin),
#     (SavedMatchFilter, SavedMatchFilterAdmin),
#     (PinnedTournament, admin.ModelAdmin),
# ]:
#     try:
#         admin.site.register(model, admin_cls)
#     except AlreadyRegistered:
#         pass
