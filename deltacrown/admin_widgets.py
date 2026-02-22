"""
Custom admin widgets for user-friendly editing of JSON fields.

Replaces raw JSON textareas with interactive HTML tables
that organizers can easily edit without knowing JSON syntax.
"""

import json
from django import forms
from django.utils.safestring import mark_safe


class PrizeDistributionWidget(forms.Textarea):
    """
    Renders prize_distribution JSON as editable placement→amount table.
    Stores underlying data as JSON in a hidden textarea.
    """

    class Media:
        js = ('admin/js/json_widgets.js',)
        css = {'all': ('admin/css/json_widgets.css',)}

    def render(self, name, value, attrs=None, renderer=None):
        # Parse existing JSON
        data = {}
        if value:
            try:
                data = json.loads(value) if isinstance(value, str) else value
            except (json.JSONDecodeError, TypeError):
                data = {}

        textarea_id = attrs.get('id', f'id_{name}') if attrs else f'id_{name}'
        json_str = json.dumps(data, indent=2) if data else '{}'

        rows_html = ''
        if data and isinstance(data, dict):
            for placement, amount in data.items():
                rows_html += (
                    f'<tr>'
                    f'<td><input type="text" value="{placement}" class="jw-input jw-prize-placement" placeholder="e.g. 1"></td>'
                    f'<td><input type="number" value="{amount}" class="jw-input jw-prize-amount" placeholder="e.g. 500"></td>'
                    f'<td><button type="button" class="jw-btn-remove" onclick="this.closest(\'tr\').remove();prizeSync(\'{textarea_id}\')">✕</button></td>'
                    f'</tr>'
                )

        html = f'''
        <div class="jw-widget jw-prize-widget" data-target="{textarea_id}">
            <div class="jw-header">
                <span class="jw-title">💰 Prize Distribution</span>
                <div class="jw-actions">
                    <button type="button" class="jw-btn" onclick="prizePreset('{textarea_id}', 3)">Preset: Top 3</button>
                    <button type="button" class="jw-btn" onclick="prizePreset('{textarea_id}', 4)">Preset: Top 4</button>
                    <button type="button" class="jw-btn jw-btn-add" onclick="prizeAddRow('{textarea_id}')">+ Add Place</button>
                </div>
            </div>
            <table class="jw-table" id="{textarea_id}_table">
                <thead>
                    <tr><th>Placement</th><th>Prize Amount (৳)</th><th></th></tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
            <textarea name="{name}" id="{textarea_id}" class="jw-hidden-textarea" style="display:none;">{json_str}</textarea>
        </div>
        '''
        return mark_safe(html)


class CoordinatorRolesWidget(forms.Textarea):
    """
    Renders coordinator_role_choices JSON as an editable table of
    key / label / description rows.
    """

    class Media:
        js = ('admin/js/json_widgets.js',)
        css = {'all': ('admin/css/json_widgets.css',)}

    def render(self, name, value, attrs=None, renderer=None):
        data = []
        if value:
            try:
                data = json.loads(value) if isinstance(value, str) else value
            except (json.JSONDecodeError, TypeError):
                data = []

        textarea_id = attrs.get('id', f'id_{name}') if attrs else f'id_{name}'
        json_str = json.dumps(data, indent=2) if data else '[]'

        rows_html = ''
        if data and isinstance(data, list):
            for item in data:
                key = item.get('key', '')
                label = item.get('label', '')
                desc = item.get('description', '')
                rows_html += (
                    f'<tr>'
                    f'<td><input type="text" value="{key}" class="jw-input jw-role-key" placeholder="captain_igl"></td>'
                    f'<td><input type="text" value="{label}" class="jw-input jw-role-label" placeholder="Captain / IGL"></td>'
                    f'<td><input type="text" value="{desc}" class="jw-input jw-role-desc" placeholder="Team leader"></td>'
                    f'<td><button type="button" class="jw-btn-remove" onclick="this.closest(\'tr\').remove();rolesSync(\'{textarea_id}\')">✕</button></td>'
                    f'</tr>'
                )

        html = f'''
        <div class="jw-widget jw-roles-widget" data-target="{textarea_id}">
            <div class="jw-header">
                <span class="jw-title">🎖️ Coordinator Roles</span>
                <div class="jw-actions">
                    <button type="button" class="jw-btn" onclick="rolesPresetDefaults('{textarea_id}')">Load Defaults</button>
                    <button type="button" class="jw-btn jw-btn-add" onclick="rolesAddRow('{textarea_id}')">+ Add Role</button>
                </div>
            </div>
            <table class="jw-table" id="{textarea_id}_table">
                <thead>
                    <tr><th>Key (internal)</th><th>Label (shown)</th><th>Description</th><th></th></tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
            <textarea name="{name}" id="{textarea_id}" class="jw-hidden-textarea" style="display:none;">{json_str}</textarea>
        </div>
        '''
        return mark_safe(html)


class CommunicationChannelsWidget(forms.Textarea):
    """
    Renders communication_channels JSON as an editable table with
    key, label, placeholder, required, and type columns.
    """

    class Media:
        js = ('admin/js/json_widgets.js',)
        css = {'all': ('admin/css/json_widgets.css',)}

    def render(self, name, value, attrs=None, renderer=None):
        data = []
        if value:
            try:
                data = json.loads(value) if isinstance(value, str) else value
            except (json.JSONDecodeError, TypeError):
                data = []

        textarea_id = attrs.get('id', f'id_{name}') if attrs else f'id_{name}'
        json_str = json.dumps(data, indent=2) if data else '[]'

        rows_html = ''
        if data and isinstance(data, list):
            for ch in data:
                key = ch.get('key', '')
                label = ch.get('label', '')
                placeholder = ch.get('placeholder', '')
                required = 'checked' if ch.get('required') else ''
                ch_type = ch.get('type', 'text')
                rows_html += (
                    f'<tr>'
                    f'<td><input type="text" value="{key}" class="jw-input jw-ch-key" placeholder="discord"></td>'
                    f'<td><input type="text" value="{label}" class="jw-input jw-ch-label" placeholder="Discord Tag"></td>'
                    f'<td><input type="text" value="{placeholder}" class="jw-input jw-ch-placeholder" placeholder="user#1234"></td>'
                    f'<td><select class="jw-input jw-ch-type">'
                    f'<option value="text" {"selected" if ch_type == "text" else ""}>Text</option>'
                    f'<option value="url" {"selected" if ch_type == "url" else ""}>URL</option>'
                    f'<option value="tel" {"selected" if ch_type == "tel" else ""}>Phone</option>'
                    f'</select></td>'
                    f'<td class="jw-center"><input type="checkbox" class="jw-ch-required" {required}></td>'
                    f'<td><button type="button" class="jw-btn-remove" onclick="this.closest(\'tr\').remove();channelsSync(\'{textarea_id}\')">✕</button></td>'
                    f'</tr>'
                )

        html = f'''
        <div class="jw-widget jw-channels-widget" data-target="{textarea_id}">
            <div class="jw-header">
                <span class="jw-title">📡 Communication Channels</span>
                <div class="jw-actions">
                    <button type="button" class="jw-btn" onclick="channelsPresetDefaults('{textarea_id}')">Load Defaults</button>
                    <button type="button" class="jw-btn jw-btn-add" onclick="channelsAddRow('{textarea_id}')">+ Add Channel</button>
                </div>
            </div>
            <table class="jw-table" id="{textarea_id}_table">
                <thead>
                    <tr><th>Key</th><th>Label</th><th>Placeholder</th><th>Type</th><th>Required</th><th></th></tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
            <textarea name="{name}" id="{textarea_id}" class="jw-hidden-textarea" style="display:none;">{json_str}</textarea>
        </div>
        '''
        return mark_safe(html)


class MemberCustomFieldsWidget(forms.Textarea):
    """
    Renders member_custom_fields JSON as an editable table of
    field_name, label, type, required rows.
    """

    class Media:
        js = ('admin/js/json_widgets.js',)
        css = {'all': ('admin/css/json_widgets.css',)}

    def render(self, name, value, attrs=None, renderer=None):
        data = []
        if value:
            try:
                data = json.loads(value) if isinstance(value, str) else value
            except (json.JSONDecodeError, TypeError):
                data = []

        textarea_id = attrs.get('id', f'id_{name}') if attrs else f'id_{name}'
        json_str = json.dumps(data, indent=2) if data else '[]'

        rows_html = ''
        if data and isinstance(data, list):
            for fld in data:
                fname = fld.get('field_name', '')
                label = fld.get('label', '')
                ftype = fld.get('type', 'text')
                required = 'checked' if fld.get('required') else ''
                rows_html += (
                    f'<tr>'
                    f'<td><input type="text" value="{fname}" class="jw-input jw-mcf-name" placeholder="national_id"></td>'
                    f'<td><input type="text" value="{label}" class="jw-input jw-mcf-label" placeholder="National ID"></td>'
                    f'<td><select class="jw-input jw-mcf-type">'
                    f'<option value="text" {"selected" if ftype == "text" else ""}>Text</option>'
                    f'<option value="number" {"selected" if ftype == "number" else ""}>Number</option>'
                    f'<option value="email" {"selected" if ftype == "email" else ""}>Email</option>'
                    f'<option value="url" {"selected" if ftype == "url" else ""}>URL</option>'
                    f'<option value="date" {"selected" if ftype == "date" else ""}>Date</option>'
                    f'</select></td>'
                    f'<td class="jw-center"><input type="checkbox" class="jw-mcf-required" {required}></td>'
                    f'<td><button type="button" class="jw-btn-remove" onclick="this.closest(\'tr\').remove();mcfSync(\'{textarea_id}\')">✕</button></td>'
                    f'</tr>'
                )

        html = f'''
        <div class="jw-widget jw-mcf-widget" data-target="{textarea_id}">
            <div class="jw-header">
                <span class="jw-title">📝 Custom Member Fields</span>
                <div class="jw-actions">
                    <button type="button" class="jw-btn jw-btn-add" onclick="mcfAddRow('{textarea_id}')">+ Add Field</button>
                </div>
            </div>
            <table class="jw-table" id="{textarea_id}_table">
                <thead>
                    <tr><th>Field Name</th><th>Label</th><th>Type</th><th>Required</th><th></th></tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
            <textarea name="{name}" id="{textarea_id}" class="jw-hidden-textarea" style="display:none;">{json_str}</textarea>
        </div>
        '''
        return mark_safe(html)
