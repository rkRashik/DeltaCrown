# apps/tournaments/admin/base.py
from __future__ import annotations

import importlib
from django.contrib import admin

# Import submodules (not symbols) so we don't crash if some names are missing.
# Each submodule uses @admin.register on its ModelAdmins.
_modules = {}
for modname in (".tournaments", ".registrations", ".matches", ".exports", ".hooks"):
    try:
        _modules[modname] = importlib.import_module(modname, __package__)
    except Exception:
        _modules[modname] = None

tournaments_mod = _modules.get(".tournaments")
registrations_mod = _modules.get(".registrations")
matches_mod = _modules.get(".matches")
exports_mod = _modules.get(".exports")
hooks_mod = _modules.get(".hooks")

# Pull classes/actions if they exist
TournamentAdmin = getattr(tournaments_mod, "TournamentAdmin", None)
action_generate_bracket = getattr(tournaments_mod, "action_generate_bracket", None)
action_lock_bracket = getattr(tournaments_mod, "action_lock_bracket", None)

action_auto_schedule = getattr(matches_mod, "action_auto_schedule", None)
action_clear_schedule = getattr(matches_mod, "action_clear_schedule", None)

RegistrationAdmin = getattr(registrations_mod, "RegistrationAdmin", None)
action_verify_payment = getattr(registrations_mod, "action_verify_payment", None)
action_reject_payment = getattr(registrations_mod, "action_reject_payment", None)
action_mark_pending = getattr(registrations_mod, "action_mark_pending", None)

export_tournaments_csv = getattr(exports_mod, "export_tournaments_csv", None)
export_disputes_csv = getattr(exports_mod, "export_disputes_csv", None)
export_matches_csv = getattr(exports_mod, "export_matches_csv", None)

attach_match_export_action = getattr(hooks_mod, "attach_match_export_action", None)
attach_dispute_export_action = getattr(hooks_mod, "attach_dispute_export_action", None)

# Attach any actions that exist to the TournamentAdmin (idempotent)
if TournamentAdmin:
    existing = (getattr(TournamentAdmin, "actions", []) or [])
    to_add = [
        a for a in (
            action_generate_bracket,
            action_lock_bracket,
            action_auto_schedule,
            action_clear_schedule,
        ) if callable(a)
    ]
    # dedupe while preserving existing
    seen = set(existing)
    for a in to_add:
        if a not in seen:
            existing.append(a)
            seen.add(a)
    TournamentAdmin.actions = existing  # type: ignore[attr-defined]

# Set helpful labels on CSV actions if present
if export_tournaments_csv:
    export_tournaments_csv.short_description = "Export selected tournaments to CSV"  # type: ignore[attr-defined]
if export_disputes_csv:
    export_disputes_csv.short_description = "Export selected disputes to CSV"  # type: ignore[attr-defined]
if export_matches_csv:
    export_matches_csv.short_description = "Export selected matches to CSV"  # type: ignore[attr-defined]

# Attach CSV export hooks if present
if attach_match_export_action:
    attach_match_export_action(admin.site)  # type: ignore[misc]
if attach_dispute_export_action:
    attach_dispute_export_action(admin.site)  # type: ignore[misc]
