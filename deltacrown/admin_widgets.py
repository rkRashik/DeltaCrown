"""
Custom admin widgets for user-friendly editing of JSON fields.

Replaces raw JSON textareas with interactive HTML tables
that organizers can easily edit without knowing JSON syntax.
"""

import json
from django import forms
from django.utils.html import format_html, escapejs, escape


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
                    '<tr>'
                    '<td><input type="text" value="{}" class="jw-input jw-prize-placement" placeholder="e.g. 1"></td>'
                    '<td><input type="number" value="{}" class="jw-input jw-prize-amount" placeholder="e.g. 500"></td>'
                    '<td><button type="button" class="jw-btn-remove" data-widget-action="remove-row" data-sync-fn="prizeSync" data-target-id="{}">✕</button></td>'
                    '</tr>'
                ).format(escape(str(placement)), escape(str(amount)), escapejs(textarea_id))

        html = format_html('''
        <div class="jw-widget jw-prize-widget" data-target="{}">
            <div class="jw-header">
                <span class="jw-title">💰 Prize Distribution</span>
                <div class="jw-actions">
                    <button type="button" class="jw-btn" data-widget-action="prize-preset" data-target-id="{}" data-count="3">Preset: Top 3</button>
                    <button type="button" class="jw-btn" data-widget-action="prize-preset" data-target-id="{}" data-count="4">Preset: Top 4</button>
                    <button type="button" class="jw-btn jw-btn-add" data-widget-action="prize-add-row" data-target-id="{}">+ Add Place</button>
                </div>
            </div>
            <table class="jw-table" id="{}_table">
                <thead>
                    <tr><th>Placement</th><th>Prize Amount (৳)</th><th></th></tr>
                </thead>
                <tbody>{}</tbody>
            </table>
            <textarea name="{}" id="{}" class="jw-hidden-textarea" style="display:none;">{}</textarea>
        </div>
        ''', textarea_id, textarea_id, textarea_id, textarea_id, textarea_id,
             format_html(rows_html), name, textarea_id, json_str)
        return html


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
                key = escape(str(item.get('key', '')))
                label = escape(str(item.get('label', '')))
                desc = escape(str(item.get('description', '')))
                rows_html += (
                    '<tr>'
                    '<td><input type="text" value="{}" class="jw-input jw-role-key" placeholder="captain_igl"></td>'
                    '<td><input type="text" value="{}" class="jw-input jw-role-label" placeholder="Captain / IGL"></td>'
                    '<td><input type="text" value="{}" class="jw-input jw-role-desc" placeholder="Team leader"></td>'
                    '<td><button type="button" class="jw-btn-remove" data-widget-action="remove-row" data-sync-fn="rolesSync" data-target-id="{}">✕</button></td>'
                    '</tr>'
                ).format(key, label, desc, escapejs(textarea_id))

        html = format_html('''
        <div class="jw-widget jw-roles-widget" data-target="{}">
            <div class="jw-header">
                <span class="jw-title">🎖️ Coordinator Roles</span>
                <div class="jw-actions">
                    <button type="button" class="jw-btn" data-widget-action="roles-preset-defaults" data-target-id="{}">Load Defaults</button>
                    <button type="button" class="jw-btn jw-btn-add" data-widget-action="roles-add-row" data-target-id="{}">+ Add Role</button>
                </div>
            </div>
            <table class="jw-table" id="{}_table">
                <thead>
                    <tr><th>Key (internal)</th><th>Label (shown)</th><th>Description</th><th></th></tr>
                </thead>
                <tbody>{}</tbody>
            </table>
            <textarea name="{}" id="{}" class="jw-hidden-textarea" style="display:none;">{}</textarea>
        </div>
        ''', textarea_id, textarea_id, textarea_id, textarea_id,
             format_html(rows_html), name, textarea_id, json_str)
        return html


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
                key = escape(str(ch.get('key', '')))
                label = escape(str(ch.get('label', '')))
                placeholder = escape(str(ch.get('placeholder', '')))
                required = 'checked' if ch.get('required') else ''
                ch_type = ch.get('type', 'text')
                rows_html += (
                    '<tr>'
                    '<td><input type="text" value="{key}" class="jw-input jw-ch-key" placeholder="discord"></td>'
                    '<td><input type="text" value="{label}" class="jw-input jw-ch-label" placeholder="Discord Tag"></td>'
                    '<td><input type="text" value="{placeholder}" class="jw-input jw-ch-placeholder" placeholder="user#1234"></td>'
                    '<td><select class="jw-input jw-ch-type">'
                    '<option value="text" {sel_text}>Text</option>'
                    '<option value="url" {sel_url}>URL</option>'
                    '<option value="tel" {sel_tel}>Phone</option>'
                    '</select></td>'
                    '<td class="jw-center"><input type="checkbox" class="jw-ch-required" {required}></td>'
                    '<td><button type="button" class="jw-btn-remove" data-widget-action="remove-row" data-sync-fn="channelsSync" data-target-id="{tid}">✕</button></td>'
                    '</tr>'
                ).format(
                    key=key, label=label, placeholder=placeholder, required=required,
                    sel_text='selected' if ch_type == 'text' else '',
                    sel_url='selected' if ch_type == 'url' else '',
                    sel_tel='selected' if ch_type == 'tel' else '',
                    tid=escapejs(textarea_id),
                )

        html = format_html('''
        <div class="jw-widget jw-channels-widget" data-target="{}">
            <div class="jw-header">
                <span class="jw-title">📡 Communication Channels</span>
                <div class="jw-actions">
                    <button type="button" class="jw-btn" data-widget-action="channels-preset-defaults" data-target-id="{}">Load Defaults</button>
                    <button type="button" class="jw-btn jw-btn-add" data-widget-action="channels-add-row" data-target-id="{}">+ Add Channel</button>
                </div>
            </div>
            <table class="jw-table" id="{}_table">
                <thead>
                    <tr><th>Key</th><th>Label</th><th>Placeholder</th><th>Type</th><th>Required</th><th></th></tr>
                </thead>
                <tbody>{}</tbody>
            </table>
            <textarea name="{}" id="{}" class="jw-hidden-textarea" style="display:none;">{}</textarea>
        </div>
        ''', textarea_id, textarea_id, textarea_id, textarea_id,
             format_html(rows_html), name, textarea_id, json_str)
        return html


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
                fname = escape(str(fld.get('field_name', '')))
                label = escape(str(fld.get('label', '')))
                ftype = fld.get('type', 'text')
                required = 'checked' if fld.get('required') else ''
                rows_html += (
                    '<tr>'
                    '<td><input type="text" value="{fname}" class="jw-input jw-mcf-name" placeholder="national_id"></td>'
                    '<td><input type="text" value="{label}" class="jw-input jw-mcf-label" placeholder="National ID"></td>'
                    '<td><select class="jw-input jw-mcf-type">'
                    '<option value="text" {sel_text}>Text</option>'
                    '<option value="number" {sel_number}>Number</option>'
                    '<option value="email" {sel_email}>Email</option>'
                    '<option value="url" {sel_url}>URL</option>'
                    '<option value="date" {sel_date}>Date</option>'
                    '</select></td>'
                    '<td class="jw-center"><input type="checkbox" class="jw-mcf-required" {required}></td>'
                    '<td><button type="button" class="jw-btn-remove" data-widget-action="remove-row" data-sync-fn="mcfSync" data-target-id="{tid}">✕</button></td>'
                    '</tr>'
                ).format(
                    fname=fname, label=label, required=required,
                    sel_text='selected' if ftype == 'text' else '',
                    sel_number='selected' if ftype == 'number' else '',
                    sel_email='selected' if ftype == 'email' else '',
                    sel_url='selected' if ftype == 'url' else '',
                    sel_date='selected' if ftype == 'date' else '',
                    tid=escapejs(textarea_id),
                )

        html = format_html('''
        <div class="jw-widget jw-mcf-widget" data-target="{}">
            <div class="jw-header">
                <span class="jw-title">📝 Custom Member Fields</span>
                <div class="jw-actions">
                    <button type="button" class="jw-btn jw-btn-add" data-widget-action="mcf-add-row" data-target-id="{}">+ Add Field</button>
                </div>
            </div>
            <table class="jw-table" id="{}_table">
                <thead>
                    <tr><th>Field Name</th><th>Label</th><th>Type</th><th>Required</th><th></th></tr>
                </thead>
                <tbody>{}</tbody>
            </table>
            <textarea name="{}" id="{}" class="jw-hidden-textarea" style="display:none;">{}</textarea>
        </div>
        ''', textarea_id, textarea_id, textarea_id,
             format_html(rows_html), name, textarea_id, json_str)
        return html
