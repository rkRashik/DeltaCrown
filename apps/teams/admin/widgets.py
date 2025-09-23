# apps/teams/admin/widgets.py
"""
Custom admin widgets for team management.
"""
from django import forms
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class TeamPointsCalculatorWidget(forms.NumberInput):
    """
    Custom widget for team points calculation with Add/Minus buttons.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'team-points-input',
            'placeholder': 'Enter points to add/subtract',
            'step': '1'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        # Get the base input field
        input_html = super().render(name, value, attrs, renderer)
        
        # Create the calculator interface
        widget_html = format_html('''
            <div class="team-points-calculator" data-field-name="{}">
                <div class="points-input-group">
                    {}
                    <div class="calculator-buttons">
                        <button type="button" class="btn-add-points" data-action="add" title="Add Points">
                            +
                        </button>
                        <button type="button" class="btn-subtract-points" data-action="subtract" title="Subtract Points">
                            -
                        </button>
                    </div>
                </div>
                <div class="points-preview">
                    <span class="current-total">Current Total: <span class="total-value">0</span> points</span>
                    <span class="calculation-preview" style="display: none;"></span>
                </div>
            </div>
        ''', name, input_html)
        
        return mark_safe(widget_html)
    
    class Media:
        css = {
            'all': ('admin/css/team_points_widget.css',)
        }
        js = ('admin/js/team_points_widget.js',)


class ReadOnlyPointsWidget(forms.TextInput):
    """
    Read-only widget for displaying total points.
    """
    
    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'readonly-points-display',
            'readonly': True
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        input_html = super().render(name, value, attrs, renderer)
        
        widget_html = format_html('''
            <div class="readonly-points-widget">
                {}
                <div class="points-info">
                    <span class="trophy-icon">🏆</span>
                    <span class="points-label">Total Ranking Points</span>
                </div>
            </div>
        ''', input_html)
        
        return mark_safe(widget_html)