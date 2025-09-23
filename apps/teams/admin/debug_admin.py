# Temporary simple team admin for debugging
from django.contrib import admin
from ..models import Team

@admin.register(Team)
class SimpleTeamAdmin(admin.ModelAdmin):
    """Simple admin to test if the issue is with our complex configuration"""
    list_display = ('name', 'tag', 'game')
    fields = ('name', 'tag', 'game', 'description', 'total_points', 'manual_points')
    readonly_fields = ('total_points',)
    
    def get_model_perms(self, request):
        """Make sure this admin is accessible"""
        return {
            'add': True,
            'change': True,
            'delete': True,
            'view': True,
        }