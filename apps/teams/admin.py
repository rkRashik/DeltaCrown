"""
FROZEN STUB — minimal admin registration for legacy Team model.
Required because other admin classes (e.g. UserProfileAdmin) reference Team
via autocomplete_fields.
"""

from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Team


@admin.register(Team)
class TeamAdmin(ModelAdmin):
    search_fields = ['name', 'tag', 'slug']
    list_display = ['name', 'tag', 'slug']
    readonly_fields = ['name', 'tag', 'slug']
