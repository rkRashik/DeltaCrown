# apps/tournaments/admin/__init__.py
"""
Admin package loader for tournaments.

Keep this file idempotent:
- Import modules (not symbols) so we don't couple to their internal names.
- Import order ensures TournamentAdmin is registered first.
"""

# 1) Main registrar: defines & registers TournamentAdmin (with its actions as methods)
from . import tournaments as _tournaments  # noqa: F401

# 2) Optional/related admin modules — load best-effort, never break startup
for _mod in (
    "components",            # inlines/filters (if you have them)
    "registrations",         # Registration admin (optional in some trees)
    "matches",               # Match admin (optional)
    "disputes",              # MatchDispute admin (optional)
    "exports",               # CSV export helpers (optional)
    "payment_verification",  # PaymentVerification admin (optional)
    "hooks",                 # any extra hook wiring you keep
    "base",                  # safe extensions; must be last
):
    try:
        __import__(f"{__package__}.{_mod}", fromlist=["*"])
    except Exception:
        # Never block admin import because of optional modules
        pass

# (Optional) Re-expose TournamentAdmin for convenience, but NOT the actions.
try:
    from .tournaments import TournamentAdmin  # noqa: F401
except Exception:
    pass
