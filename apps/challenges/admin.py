from django.contrib import admin

from .models import Challenge


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'team', 'challenge_type', 'status', 'prize_amount', 'created_at')
    list_filter = ('status', 'challenge_type')
    search_fields = ('title', 'team__name')
    raw_id_fields = ('team', 'opponent_team', 'created_by', 'target_player')
