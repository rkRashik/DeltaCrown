# apps/tournaments/admin/attendance.py
from django.contrib import admin
from django.contrib.admin.sites import AlreadyRegistered
from ..models.attendance import MatchAttendance

class MatchAttendanceAdmin(admin.ModelAdmin):
    list_display = ("match", "user", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("match__id", "user__username", "user__email")

try:
    admin.site.register(MatchAttendance, MatchAttendanceAdmin)
except AlreadyRegistered:
    pass
