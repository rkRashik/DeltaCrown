"""
Admin interfaces for Bracket and BracketNode models.

⚠️ LEGACY: This Django admin customization is DEPRECATED as of Phase 7, Epic 7.6.
The new Organizer Console (Phase 7, Epics 7.1-7.6) provides a superior UX for:
- Bracket management (generate, finalize, visualize)
- BracketNode inspection and manual adjustments
- Bracket progression tracking

This file is retained ONLY for:
1. Emergency administrative access (super admin use only)
2. Backward compatibility during Phase 7 transition
3. Data inspection/debugging (not end-user workflows)

SCHEDULED FOR REMOVAL: Phase 8+
REPLACEMENT: Organizer Console Bracket Management UI

Provides Tournament Organizer interfaces for:
- Bracket management (generate, finalize, visualize)
- BracketNode inspection and manual adjustments
- Bracket progression tracking

Source: Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md
"""

from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from django.contrib import messages
from apps.tournaments.models import Bracket, BracketNode


class BracketNodeInline(TabularInline):
    """
    Inline display of bracket nodes (limited to first round for preview).
    """
    model = BracketNode
    extra = 0
    can_delete = False
    max_num = 8  # Show max 8 nodes in inline
    
    fields = [
        'round_number',
        'match_number_in_round',
        'participant1_display',
        'participant2_display',
        'winner_display',
        'is_bye',
        'bracket_type'
    ]
    
    readonly_fields = [
        'round_number',
        'match_number_in_round',
        'participant1_display',
        'participant2_display',
        'winner_display',
        'is_bye',
        'bracket_type'
    ]
    
    def participant1_display(self, obj):
        """Display participant 1 with ID"""
        if obj.participant1_id:
            return f"{obj.participant1_name} ({obj.participant1_id})"
        return "—"
    participant1_display.short_description = "Participant 1"
    
    def participant2_display(self, obj):
        """Display participant 2 with ID"""
        if obj.participant2_id:
            return f"{obj.participant2_name} ({obj.participant2_id})"
        return "—"
    participant2_display.short_description = "Participant 2"
    
    def winner_display(self, obj):
        """Display winner with styling"""
        if obj.winner_id:
            winner_name = obj.get_winner_name()
            return format_html(
                '<strong style="color: green;">🏆 {}</strong>',
                winner_name
            )
        return "—"
    winner_display.short_description = "Winner"
    
    def get_queryset(self, request):
        """Limit to first round nodes only"""
        qs = super().get_queryset(request)
        # Don't slice queryset - causes "Cannot filter after slice" error
        # Django admin may apply additional filters after this
        return qs.filter(round_number=1).order_by('position')


@admin.register(Bracket)
class BracketAdmin(ModelAdmin):
    """
    Admin interface for Bracket model.
    
    Features:
    - Bracket generation and regeneration
    - Finalization control
    - Bracket visualization link
    - Seeding method management
    """
    
    list_display = [
        'tournament_link',
        'format_badge',
        'seeding_method',
        'total_rounds',
        'total_matches',
        'progress_bar',
        'is_finalized_badge',
        'generated_at'
    ]
    
    list_filter = [
        'format',
        'seeding_method',
        'is_finalized',
        ('tournament', admin.RelatedOnlyFieldListFilter),
        'generated_at'
    ]
    
    search_fields = [
        'tournament__name',
        'tournament__slug'
    ]
    
    readonly_fields = [
        'tournament',
        'total_rounds',
        'total_matches',
        'bracket_structure',
        'generated_at',
        'updated_at',
        'created_at',
        'nodes_summary',
        'visualization_link'
    ]
    
    fields = [
        'tournament',
        'format',
        'seeding_method',
        'is_finalized',
        'total_rounds',
        'total_matches',
        'generated_at',
        'updated_at',
        'nodes_summary',
        'visualization_link',
        'bracket_structure'
    ]
    
    inlines = [BracketNodeInline]
    
    actions = [
        'regenerate_bracket',
        'finalize_bracket',
        'unfinalize_bracket'
    ]
    
    def tournament_link(self, obj):
        """Link to tournament admin page"""
        url = reverse('admin:tournaments_tournament_change', args=[obj.tournament.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.tournament.name
        )
    tournament_link.short_description = "Tournament"
    tournament_link.admin_order_field = 'tournament__name'
    
    @display(
        description='Format',
        ordering='format',
        label={
            'single-elimination': 'success',
            'double-elimination': 'warning',
            'round-robin': 'info',
            'swiss': 'primary',
            'group-stage': 'danger',
        },
    )
    def format_badge(self, obj):
        """Display bracket format with Unfold color badge."""
        return obj.format

    @display(description='Finalized', ordering='is_finalized', boolean=True)
    def is_finalized_badge(self, obj):
        """Display finalized status."""
        return obj.is_finalized
    
    def progress_bar(self, obj):
        """Show bracket completion progress"""
        # Count completed nodes
        total_nodes = BracketNode.objects.filter(bracket=obj).count()
        if total_nodes == 0:
            return "—"
        
        completed_nodes = BracketNode.objects.filter(
            bracket=obj,
            winner_id__isnull=False
        ).count()
        
        percentage = (completed_nodes / total_nodes) * 100 if total_nodes > 0 else 0
        
        # Color based on percentage
        if percentage == 100:
            color = '#4CAF50'  # Green
        elif percentage >= 50:
            color = '#FF9800'  # Orange
        else:
            color = '#2196F3'  # Blue
        
        return format_html(
            '<div style="width: 100px; background-color: #f0f0f0; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; color: white; line-height: 20px;">'
            '{}%'
            '</div></div>',
            percentage,
            color,
            int(percentage)
        )
    progress_bar.short_description = "Progress"
    
    def nodes_summary(self, obj):
        """Summary of bracket nodes by round"""
        if not obj.id:
            return "—"
        
        nodes = BracketNode.objects.filter(bracket=obj).values('round_number').annotate(
            total=Count('id'),
            completed=Count('id', filter=Q(winner_id__isnull=False))
        ).order_by('round_number')
        
        html = '<table style="width: 100%; border-collapse: collapse;">'
        html += '<tr style="background-color: #f5f5f5;"><th>Round</th><th>Total Matches</th><th>Completed</th></tr>'
        
        for node in nodes:
            round_name = obj.get_round_name(node['round_number'])
            html += f'<tr><td>{round_name}</td><td>{node["total"]}</td><td>{node["completed"]}</td></tr>'
        
        html += '</table>'
        return format_html(html)
    nodes_summary.short_description = "Bracket Nodes Summary"
    
    def visualization_link(self, obj):
        """Link to bracket visualization (future implementation)"""
        if not obj.id:
            return "—"
        
        # TODO: Create actual visualization view
        return format_html(
            '<a href="#" onclick="alert(\'Bracket visualization coming in Phase 2\'); return false;" '
            'style="background-color: #2196F3; color: white; padding: 5px 15px; border-radius: 3px; text-decoration: none;">'
            '📊 View Bracket Tree'
            '</a>'
        )
    visualization_link.short_description = "Visualization"
    
    def regenerate_bracket(self, request, queryset):
        """Action to regenerate selected brackets"""
        finalized_count = queryset.filter(is_finalized=True).count()
        
        if finalized_count > 0:
            self.message_user(
                request,
                f"{finalized_count} bracket(s) skipped because they are finalized. "
                "Unfinalize them first to regenerate.",
                level=messages.WARNING
            )
        
        regenerated_count = 0
        for bracket in queryset.filter(is_finalized=False):
            try:
                from apps.tournaments.services.bracket_service import BracketService
                BracketService.recalculate_bracket(
                    tournament_id=bracket.tournament_id,
                    force=True
                )
                regenerated_count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to regenerate bracket for {bracket.tournament.name}: {e}",
                    level=messages.ERROR
                )
        
        if regenerated_count > 0:
            self.message_user(
                request,
                f"Successfully regenerated {regenerated_count} bracket(s).",
                level=messages.SUCCESS
            )
    regenerate_bracket.short_description = "Regenerate selected brackets (force)"
    
    def finalize_bracket(self, request, queryset):
        """Action to finalize selected brackets"""
        count = 0
        for bracket in queryset.filter(is_finalized=False):
            try:
                from apps.tournaments.services.bracket_service import BracketService
                BracketService.finalize_bracket(bracket.id)
                count += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Failed to finalize bracket for {bracket.tournament.name}: {e}",
                    level=messages.ERROR
                )
        
        if count > 0:
            self.message_user(
                request,
                f"Successfully finalized {count} bracket(s).",
                level=messages.SUCCESS
            )
    finalize_bracket.short_description = "Finalize selected brackets (lock)"
    
    def unfinalize_bracket(self, request, queryset):
        """Action to unfinalize selected brackets"""
        count = queryset.filter(is_finalized=True).update(is_finalized=False)
        
        if count > 0:
            self.message_user(
                request,
                f"Successfully unfinalized {count} bracket(s). They can now be regenerated.",
                level=messages.SUCCESS
            )
    unfinalize_bracket.short_description = "Unfinalize selected brackets (unlock)"


@admin.register(BracketNode)
class BracketNodeAdmin(ModelAdmin):
    """
    Admin interface for BracketNode model.
    
    Features:
    - Node navigation and inspection
    - Manual participant adjustments
    - Winner tracking
    - Parent/child relationship visualization
    """
    
    list_display = [
        'position',
        'bracket_link',
        'round_info',
        'match_info',
        'participant1_display',
        'vs',
        'participant2_display',
        'winner_badge',
        'parent_link',
        'bracket_type_badge'
    ]
    
    list_filter = [
        ('bracket', admin.RelatedOnlyFieldListFilter),
        'round_number',
        'bracket_type',
        'is_bye',
        ('winner_id', admin.EmptyFieldListFilter)
    ]
    
    search_fields = [
        'bracket__tournament__name',
        'participant1_name',
        'participant2_name',
        'participant1_id',
        'participant2_id'
    ]
    
    readonly_fields = [
        'bracket',
        'position',
        'round_number',
        'match_number_in_round',
        'parent_node',
        'parent_slot',
        'child1_node',
        'child2_node',
        'match',
        'winner_id',
        'navigation_tree'
    ]
    
    fields = [
        'bracket',
        'position',
        'round_number',
        'match_number_in_round',
        'bracket_type',
        'participant1_id',
        'participant1_name',
        'participant2_id',
        'participant2_name',
        'winner_id',
        'is_bye',
        'match',
        'parent_node',
        'parent_slot',
        'child1_node',
        'child2_node',
        'navigation_tree'
    ]
    
    def bracket_link(self, obj):
        """Link to bracket admin page"""
        url = reverse('admin:tournaments_bracket_change', args=[obj.bracket.id])
        return format_html(
            '<a href="{}">{}</a>',
            url,
            obj.bracket.tournament.name
        )
    bracket_link.short_description = "Bracket"
    bracket_link.admin_order_field = 'bracket__tournament__name'
    
    def round_info(self, obj):
        """Display round number with name"""
        round_name = obj.bracket.get_round_name(obj.round_number)
        return f"R{obj.round_number}: {round_name}"
    round_info.short_description = "Round"
    round_info.admin_order_field = 'round_number'
    
    def match_info(self, obj):
        """Display match number in round"""
        return f"Match {obj.match_number_in_round}"
    match_info.short_description = "Match"
    match_info.admin_order_field = 'match_number_in_round'
    
    def participant1_display(self, obj):
        """Display participant 1"""
        if obj.participant1_id:
            return f"{obj.participant1_name}"
        return format_html('<em style="color: #999;">TBD</em>')
    participant1_display.short_description = "Participant 1"
    
    def vs(self, obj):
        """VS separator"""
        return "vs"
    vs.short_description = ""
    
    def participant2_display(self, obj):
        """Display participant 2"""
        if obj.participant2_id:
            return f"{obj.participant2_name}"
        return format_html('<em style="color: #999;">TBD</em>')
    participant2_display.short_description = "Participant 2"
    
    def winner_badge(self, obj):
        """Display winner with trophy icon"""
        if obj.winner_id:
            winner_name = obj.get_winner_name()
            return format_html(
                '<strong style="color: green;">🏆 {}</strong>',
                winner_name
            )
        elif obj.is_bye:
            return format_html('<em style="color: #999;">BYE</em>')
        return "—"
    winner_badge.short_description = "Winner"
    
    def parent_link(self, obj):
        """Link to parent node"""
        if obj.parent_node:
            url = reverse('admin:tournaments_bracketnode_change', args=[obj.parent_node.id])
            return format_html(
                '<a href="{}">Position {}</a>',
                url,
                obj.parent_node.position
            )
        return "—"
    parent_link.short_description = "Advances To"
    
    def bracket_type_badge(self, obj):
        """Display bracket type with color"""
        if not obj.bracket_type:
            return format_html(
                '<span style="background-color: #757575; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">—</span>'
            )
        
        type_colors = {
            'main': '#4CAF50',
            'losers': '#FF9800',
            'third-place': '#2196F3'
        }
        
        bracket_type = obj.bracket_type
        color = type_colors.get(bracket_type, '#757575')
        
        # bracket_type is CharField - format display name from value
        display_name = bracket_type.replace('-', ' ').replace('_', ' ').title()
        
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color, display_name
        )
    bracket_type_badge.short_description = "Type"
    bracket_type_badge.admin_order_field = 'bracket_type'
    
    def navigation_tree(self, obj):
        """Display navigation tree (parent/children)"""
        if not obj.id:
            return "—"
        
        html = '<div style="font-family: monospace; line-height: 1.8;">'
        
        # Show children (previous round)
        if obj.child1_node or obj.child2_node:
            html += '<strong>Children (feeds from):</strong><br>'
            if obj.child1_node:
                url = reverse('admin:tournaments_bracketnode_change', args=[obj.child1_node.id])
                html += f'  ├─ Child 1: <a href="{url}">Position {obj.child1_node.position}</a><br>'
            if obj.child2_node:
                url = reverse('admin:tournaments_bracketnode_change', args=[obj.child2_node.id])
                html += f'  └─ Child 2: <a href="{url}">Position {obj.child2_node.position}</a><br>'
            html += '<br>'
        
        # Show current node
        html += '<strong>Current Node:</strong><br>'
        html += f'  Position {obj.position} (Round {obj.round_number}, Match {obj.match_number_in_round})<br><br>'
        
        # Show parent (next round)
        if obj.parent_node:
            html += '<strong>Parent (advances to):</strong><br>'
            url = reverse('admin:tournaments_bracketnode_change', args=[obj.parent_node.id])
            html += f'  └─ <a href="{url}">Position {obj.parent_node.position}</a> (Slot {obj.parent_slot})<br>'
        
        html += '</div>'
        return format_html(html)
    navigation_tree.short_description = "Navigation Tree"
