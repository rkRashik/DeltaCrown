from django.contrib import admin
from .models import EfootballConfig

@admin.register(EfootballConfig)
class EfootballConfigAdmin(admin.ModelAdmin):
    list_display = ("tournament", "format_type", "match_duration_min", "team_strength_cap")
    search_fields = ("tournament__name",)
