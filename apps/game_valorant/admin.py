from django.contrib import admin
from .models import ValorantConfig

@admin.register(ValorantConfig)
class ValorantConfigAdmin(admin.ModelAdmin):
    list_display = ("tournament", "best_of", "rounds_per_match")
    search_fields = ("tournament__name",)
