/**
 * JSON Widget Helpers — powers all 4 admin widget types.
 * Each set of functions: sync (DOM → JSON textarea), addRow, presets.
 */

/* ═══════════════════════════════════════════════
   PRIZE DISTRIBUTION
   ═══════════════════════════════════════════════ */

function prizeSync(textareaId) {
    const table = document.getElementById(textareaId + '_table');
    const textarea = document.getElementById(textareaId);
    if (!table || !textarea) return;
    const data = {};
    table.querySelectorAll('tbody tr').forEach(row => {
        const place = row.querySelector('.jw-prize-placement')?.value?.trim();
        const amount = row.querySelector('.jw-prize-amount')?.value?.trim();
        if (place) data[place] = amount ? Number(amount) : 0;
    });
    textarea.value = JSON.stringify(data, null, 2);
}

function prizeAddRow(textareaId) {
    const table = document.getElementById(textareaId + '_table');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    const nextPlace = tbody.querySelectorAll('tr').length + 1;
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><input type="text" value="${nextPlace}" class="jw-input jw-prize-placement" placeholder="e.g. ${nextPlace}"></td>
        <td><input type="number" value="" class="jw-input jw-prize-amount" placeholder="e.g. 500"></td>
        <td><button type="button" class="jw-btn-remove" onclick="this.closest('tr').remove();prizeSync('${textareaId}')">✕</button></td>
    `;
    tbody.appendChild(tr);
    // Attach change listeners
    tr.querySelectorAll('input').forEach(inp => inp.addEventListener('input', () => prizeSync(textareaId)));
}

function prizePreset(textareaId, count) {
    const table = document.getElementById(textareaId + '_table');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    const presets = count === 4
        ? { 1: 1000, 2: 500, 3: 250, 4: 125 }
        : { 1: 500, 2: 250, 3: 125 };
    for (const [place, amount] of Object.entries(presets)) {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" value="${place}" class="jw-input jw-prize-placement"></td>
            <td><input type="number" value="${amount}" class="jw-input jw-prize-amount"></td>
            <td><button type="button" class="jw-btn-remove" onclick="this.closest('tr').remove();prizeSync('${textareaId}')">✕</button></td>
        `;
        tbody.appendChild(tr);
        tr.querySelectorAll('input').forEach(inp => inp.addEventListener('input', () => prizeSync(textareaId)));
    }
    prizeSync(textareaId);
}

/* ═══════════════════════════════════════════════
   COORDINATOR ROLES
   ═══════════════════════════════════════════════ */

function rolesSync(textareaId) {
    const table = document.getElementById(textareaId + '_table');
    const textarea = document.getElementById(textareaId);
    if (!table || !textarea) return;
    const data = [];
    table.querySelectorAll('tbody tr').forEach(row => {
        const key = row.querySelector('.jw-role-key')?.value?.trim();
        const label = row.querySelector('.jw-role-label')?.value?.trim();
        const desc = row.querySelector('.jw-role-desc')?.value?.trim();
        if (key || label) data.push({ key: key || '', label: label || '', description: desc || '' });
    });
    textarea.value = JSON.stringify(data, null, 2);
}

function rolesAddRow(textareaId) {
    const table = document.getElementById(textareaId + '_table');
    if (!table) return;
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><input type="text" value="" class="jw-input jw-role-key" placeholder="role_key"></td>
        <td><input type="text" value="" class="jw-input jw-role-label" placeholder="Role Label"></td>
        <td><input type="text" value="" class="jw-input jw-role-desc" placeholder="Description"></td>
        <td><button type="button" class="jw-btn-remove" onclick="this.closest('tr').remove();rolesSync('${textareaId}')">✕</button></td>
    `;
    table.querySelector('tbody').appendChild(tr);
    tr.querySelectorAll('input').forEach(inp => inp.addEventListener('input', () => rolesSync(textareaId)));
}

function rolesPresetDefaults(textareaId) {
    const defaults = [
        { key: 'captain_igl', label: 'Captain / IGL', description: 'In-game leader and team captain' },
        { key: 'manager', label: 'Team Manager', description: 'Handles team logistics and communication' },
        { key: 'coach', label: 'Coach', description: 'Team coach / analyst' },
        { key: 'representative', label: 'Representative', description: 'Team representative for the tournament' },
    ];
    const table = document.getElementById(textareaId + '_table');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    defaults.forEach(role => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" value="${role.key}" class="jw-input jw-role-key"></td>
            <td><input type="text" value="${role.label}" class="jw-input jw-role-label"></td>
            <td><input type="text" value="${role.description}" class="jw-input jw-role-desc"></td>
            <td><button type="button" class="jw-btn-remove" onclick="this.closest('tr').remove();rolesSync('${textareaId}')">✕</button></td>
        `;
        tbody.appendChild(tr);
        tr.querySelectorAll('input').forEach(inp => inp.addEventListener('input', () => rolesSync(textareaId)));
    });
    rolesSync(textareaId);
}

/* ═══════════════════════════════════════════════
   COMMUNICATION CHANNELS
   ═══════════════════════════════════════════════ */

function channelsSync(textareaId) {
    const table = document.getElementById(textareaId + '_table');
    const textarea = document.getElementById(textareaId);
    if (!table || !textarea) return;
    const data = [];
    table.querySelectorAll('tbody tr').forEach(row => {
        const key = row.querySelector('.jw-ch-key')?.value?.trim();
        const label = row.querySelector('.jw-ch-label')?.value?.trim();
        const placeholder = row.querySelector('.jw-ch-placeholder')?.value?.trim();
        const type = row.querySelector('.jw-ch-type')?.value || 'text';
        const required = row.querySelector('.jw-ch-required')?.checked || false;
        if (key || label) data.push({ key: key || '', label: label || '', placeholder: placeholder || '', type, required });
    });
    textarea.value = JSON.stringify(data, null, 2);
}

function channelsAddRow(textareaId) {
    const table = document.getElementById(textareaId + '_table');
    if (!table) return;
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><input type="text" value="" class="jw-input jw-ch-key" placeholder="channel_key"></td>
        <td><input type="text" value="" class="jw-input jw-ch-label" placeholder="Channel Name"></td>
        <td><input type="text" value="" class="jw-input jw-ch-placeholder" placeholder="placeholder"></td>
        <td><select class="jw-input jw-ch-type"><option value="text">Text</option><option value="url">URL</option><option value="tel">Phone</option></select></td>
        <td class="jw-center"><input type="checkbox" class="jw-ch-required"></td>
        <td><button type="button" class="jw-btn-remove" onclick="this.closest('tr').remove();channelsSync('${textareaId}')">✕</button></td>
    `;
    table.querySelector('tbody').appendChild(tr);
    tr.querySelectorAll('input, select').forEach(inp => inp.addEventListener('input', () => channelsSync(textareaId)));
    tr.querySelector('.jw-ch-required')?.addEventListener('change', () => channelsSync(textareaId));
}

function channelsPresetDefaults(textareaId) {
    const defaults = [
        { key: 'discord', label: 'Discord', placeholder: 'username#1234', type: 'text', required: true },
        { key: 'whatsapp', label: 'WhatsApp', placeholder: '+880XXXXXXXXXX', type: 'tel', required: false },
    ];
    const table = document.getElementById(textareaId + '_table');
    if (!table) return;
    const tbody = table.querySelector('tbody');
    tbody.innerHTML = '';
    defaults.forEach(ch => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" value="${ch.key}" class="jw-input jw-ch-key"></td>
            <td><input type="text" value="${ch.label}" class="jw-input jw-ch-label"></td>
            <td><input type="text" value="${ch.placeholder}" class="jw-input jw-ch-placeholder"></td>
            <td><select class="jw-input jw-ch-type">
                <option value="text" ${ch.type === 'text' ? 'selected' : ''}>Text</option>
                <option value="url" ${ch.type === 'url' ? 'selected' : ''}>URL</option>
                <option value="tel" ${ch.type === 'tel' ? 'selected' : ''}>Phone</option>
            </select></td>
            <td class="jw-center"><input type="checkbox" class="jw-ch-required" ${ch.required ? 'checked' : ''}></td>
            <td><button type="button" class="jw-btn-remove" onclick="this.closest('tr').remove();channelsSync('${textareaId}')">✕</button></td>
        `;
        tbody.appendChild(tr);
        tr.querySelectorAll('input, select').forEach(inp => inp.addEventListener('input', () => channelsSync(textareaId)));
        tr.querySelector('.jw-ch-required')?.addEventListener('change', () => channelsSync(textareaId));
    });
    channelsSync(textareaId);
}

/* ═══════════════════════════════════════════════
   MEMBER CUSTOM FIELDS
   ═══════════════════════════════════════════════ */

function mcfSync(textareaId) {
    const table = document.getElementById(textareaId + '_table');
    const textarea = document.getElementById(textareaId);
    if (!table || !textarea) return;
    const data = [];
    table.querySelectorAll('tbody tr').forEach(row => {
        const name = row.querySelector('.jw-mcf-name')?.value?.trim();
        const label = row.querySelector('.jw-mcf-label')?.value?.trim();
        const type = row.querySelector('.jw-mcf-type')?.value || 'text';
        const required = row.querySelector('.jw-mcf-required')?.checked || false;
        if (name || label) data.push({ field_name: name || '', label: label || '', type, required });
    });
    textarea.value = JSON.stringify(data, null, 2);
}

function mcfAddRow(textareaId) {
    const table = document.getElementById(textareaId + '_table');
    if (!table) return;
    const tr = document.createElement('tr');
    tr.innerHTML = `
        <td><input type="text" value="" class="jw-input jw-mcf-name" placeholder="field_name"></td>
        <td><input type="text" value="" class="jw-input jw-mcf-label" placeholder="Display Label"></td>
        <td><select class="jw-input jw-mcf-type">
            <option value="text">Text</option><option value="number">Number</option>
            <option value="email">Email</option><option value="url">URL</option><option value="date">Date</option>
        </select></td>
        <td class="jw-center"><input type="checkbox" class="jw-mcf-required"></td>
        <td><button type="button" class="jw-btn-remove" onclick="this.closest('tr').remove();mcfSync('${textareaId}')">✕</button></td>
    `;
    table.querySelector('tbody').appendChild(tr);
    tr.querySelectorAll('input, select').forEach(inp => inp.addEventListener('input', () => mcfSync(textareaId)));
    tr.querySelector('.jw-mcf-required')?.addEventListener('change', () => mcfSync(textareaId));
}

/* ═══════════════════════════════════════════════
   AUTO-INIT: attach change listeners to existing rows
   ═══════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    // For each widget type, attach input listeners on existing rows
    document.querySelectorAll('.jw-prize-widget').forEach(widget => {
        const tid = widget.dataset.target;
        widget.querySelectorAll('tbody input').forEach(inp => inp.addEventListener('input', () => prizeSync(tid)));
    });
    document.querySelectorAll('.jw-roles-widget').forEach(widget => {
        const tid = widget.dataset.target;
        widget.querySelectorAll('tbody input').forEach(inp => inp.addEventListener('input', () => rolesSync(tid)));
    });
    document.querySelectorAll('.jw-channels-widget').forEach(widget => {
        const tid = widget.dataset.target;
        widget.querySelectorAll('tbody input, tbody select').forEach(inp => inp.addEventListener('input', () => channelsSync(tid)));
        widget.querySelectorAll('.jw-ch-required').forEach(cb => cb.addEventListener('change', () => channelsSync(tid)));
    });
    document.querySelectorAll('.jw-mcf-widget').forEach(widget => {
        const tid = widget.dataset.target;
        widget.querySelectorAll('tbody input, tbody select').forEach(inp => inp.addEventListener('input', () => mcfSync(tid)));
        widget.querySelectorAll('.jw-mcf-required').forEach(cb => cb.addEventListener('change', () => mcfSync(tid)));
    });
});
