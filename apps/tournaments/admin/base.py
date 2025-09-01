# apps/tournaments/admin/base.py
from django.contrib import admin

# Import concrete admin classes and actions from submodules
from .tournaments import (
    TournamentAdmin,
    action_generate_bracket,
    action_lock_bracket,
)
from .registrations import (
    RegistrationAdmin,
    action_verify_payment,
    action_reject_payment,
)
from .matches import (
    MatchAdmin,
    action_auto_schedule,
    action_clear_schedule,
)

# CSV export actions
from .exports import (
    export_tournaments_csv,
    export_disputes_csv,
    export_matches_csv,
)

# Hooks that attach CSV exports to existing admins (or register minimal ones)
from .hooks import (
    attach_match_export_action,
    attach_dispute_export_action,
)

# Ensure TournamentAdmin exposes bracket + scheduling actions (idempotent)
TournamentAdmin.actions = list(set((getattr(TournamentAdmin, "actions", []) or []) + [
    action_generate_bracket,
    action_lock_bracket,
    action_auto_schedule,
    action_clear_schedule,
]))

# Helpful labels for CSV actions (as seen in the actions dropdown)
export_tournaments_csv.short_description = "Export selected tournaments to CSV"
export_disputes_csv.short_description = "Export selected disputes to CSV"  # type: ignore[attr-defined]
export_matches_csv.short_description = "Export selected matches to CSV"  # type: ignore[attr-defined]

# Attach CSV export actions to existing admins (or register minimal ones)
attach_match_export_action(admin.site)
attach_dispute_export_action(admin.site)
