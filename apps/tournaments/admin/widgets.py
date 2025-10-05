# apps/tournaments/admin/widgets.py

from django import forms
from django.utils.safestring import mark_safe
import json

class PrizeDistributionWidget(forms.Widget):
    template_name = 'admin/widgets/prize_distribution_widget.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        
        # Decode JSON string to a Python dict for the template
        if isinstance(value, str) and value:
            try:
                prizes = json.loads(value)
            except json.JSONDecodeError:
                prizes = {}
        elif isinstance(value, dict):
            prizes = value
        else:
            prizes = {}
            
        # Ensure prizes is a dictionary of lists/tuples for easier iteration
        context['widget']['prizes'] = sorted(prizes.items(), key=lambda item: int(item[0])) if prizes else []
        return context

    def render(self, name, value, attrs=None, renderer=None):
        context = self.get_context(name, value, attrs)
        
        html = f"""
        <div id="prize-distribution-widget" data-field-name="{name}">
            <div id="prize-entries">
        """
        
        prizes = context['widget']['prizes']
        if prizes:
            for rank, amount in prizes:
                html += f"""
                <div class="prize-entry">
                    <input type="number" class="prize-rank" value="{rank}" placeholder="Rank">
                    <input type="number" class="prize-amount" value="{amount}" placeholder="Amount">
                    <button type="button" class="remove-prize-entry button">-</button>
                </div>
                """
        else:
             html += """
                <div class="prize-entry">
                    <input type="number" class="prize-rank" placeholder="Rank (e.g., 1)">
                    <input type="number" class="prize-amount" placeholder="Amount (e.g., 10000)">
                    <button type="button" class="remove-prize-entry button">-</button>
                </div>
            """

        html += """
            </div>
            <button type="button" id="add-prize-entry" class="button">Add Prize Rank</button>
            <input type="hidden" name="{name}" value='{value}'>
        </div>
        """.format(name=name, value=value or '{}')

        return mark_safe(html)

    class Media:
        css = {
            'all': ('admin/css/prize_distribution_widget.css',)
        }
        js = ('admin/js/prize_distribution_widget.js',)
