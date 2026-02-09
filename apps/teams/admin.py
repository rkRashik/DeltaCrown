"""
FROZEN STUB — minimal admin registration for legacy Team model.
Required because other admin classes (e.g. UserProfileAdmin) reference Team
via autocomplete_fields.
"""

from django.contrib import admin
from .models import Team


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    search_fields = ['name', 'tag', 'slug']
    list_display = ['name', 'tag', 'slug']
    readonly_fields = ['name', 'tag', 'slug']
