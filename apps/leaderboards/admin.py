from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from unfold.admin import ModelAdmin
from apps.leaderboards.models import Season, LeaderboardEntry, LeaderboardSnapshot


@admin.register(Season)
class SeasonAdmin(ModelAdmin):
    list_display = ('season_id', 'name', 'status_badge', 'start_date', 'end_date', 'time_remaining', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('season_id', 'name')
    ordering = ('-start_date',)
    readonly_fields = ('created_at', 'updated_at', 'time_remaining', 'progress_bar')
    fieldsets = (
        (None, {
            'fields': ('season_id', 'name', 'is_active'),
        }),
        ('Schedule', {
            'fields': ('start_date', 'end_date', 'time_remaining', 'progress_bar'),
        }),
        ('Configuration', {
            'fields': ('decay_rules_json',),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        now = timezone.now()
        if obj.is_active and obj.start_date <= now <= obj.end_date:
            return format_html('<span style="background:#10B981;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">Live</span>')
        elif now > obj.end_date:
            return format_html('<span style="background:#6B7280;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">Ended</span>')
        elif now < obj.start_date:
            return format_html('<span style="background:#3B82F6;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">Upcoming</span>')
        else:
            return format_html('<span style="background:#F59E0B;color:#fff;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;">Inactive</span>')
    status_badge.short_description = 'Status'

    def time_remaining(self, obj):
        now = timezone.now()
        if now > obj.end_date:
            return 'Season ended'
        if now < obj.start_date:
            delta = obj.start_date - now
            return f'Starts in {delta.days}d {delta.seconds // 3600}h'
        delta = obj.end_date - now
        total = (obj.end_date - obj.start_date).total_seconds()
        elapsed = (now - obj.start_date).total_seconds()
        pct = min(100, int(elapsed / total * 100)) if total > 0 else 0
        return f'{delta.days}d {delta.seconds // 3600}h remaining ({pct}% complete)'
    time_remaining.short_description = 'Time'

    def progress_bar(self, obj):
        now = timezone.now()
        if now > obj.end_date:
            pct = 100
        elif now < obj.start_date:
            pct = 0
        else:
            total = (obj.end_date - obj.start_date).total_seconds()
            elapsed = (now - obj.start_date).total_seconds()
            pct = min(100, int(elapsed / total * 100)) if total > 0 else 0
        color = '#10B981' if pct < 80 else '#F59E0B' if pct < 95 else '#EF4444'
        return format_html(
            '<div style="width:200px;height:8px;background:#1f2937;border-radius:4px;overflow:hidden;">'
            '<div style="width:{}%;height:100%;background:{};border-radius:4px;"></div></div>'
            '<span style="font-size:11px;color:#9CA3AF;">{}%</span>',
            pct, color, pct
        )
    progress_bar.short_description = 'Progress'

    def save_model(self, request, obj, form, change):
        if obj.is_active:
            Season.objects.exclude(pk=obj.pk).update(is_active=False)
        super().save_model(request, obj, form, change)


@admin.register(LeaderboardEntry)
class LeaderboardEntryAdmin(ModelAdmin):
    list_display = ('leaderboard_type', 'rank', 'points', 'player', 'team', 'is_active')
    list_filter = ('leaderboard_type', 'is_active')
    search_fields = ('player__username', 'team__name')
    ordering = ('leaderboard_type', 'rank')
    raw_id_fields = ('player', 'team', 'tournament')


@admin.register(LeaderboardSnapshot)
class LeaderboardSnapshotAdmin(ModelAdmin):
    list_display = ('date', 'leaderboard_type', 'team', 'rank', 'points')
    list_filter = ('leaderboard_type', 'date')
    search_fields = ('team__name',)
    ordering = ('-date', 'rank')
    raw_id_fields = ('player', 'team')
    date_hierarchy = 'date'
