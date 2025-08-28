from django.contrib import admin
from .models import Tournament, Registration

@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name","status","start_at","entry_fee_bdt")
    list_filter  = ("status",)
    search_fields = ("name","slug")

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("tournament","user","team","payment_status","status","created_at")
    list_filter  = ("payment_status","status","tournament")
    search_fields = ("payment_reference",)
