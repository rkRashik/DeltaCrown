# apps/tournaments/admin/__init__.py

# 1) Main registrar: defines & registers TournamentAdmin (with its actions as methods)
from . import tournaments as _tournaments  # noqa: F401

# 2) Game configuration admin (dynamic registration forms)
from . import game_configs as _game_configs  # noqa: F401

# 3) Optional/related admin modules — load best-effort, never break startup
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



from .tournaments import TournamentAdmin
from .matches import MatchAdmin
from .brackets import BracketAdmin

try:
    from .payments import *      # noqa: F401,F403
except Exception:
    pass
try:
    from .payments_extras import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .brackets import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .tournaments_extras import *  # noqa: F401,F403
except Exception:
    pass

# UI preferences removed from admin - managed via frontend/API
# from .userprefs import *  # noqa

from .attendance import *  # noqa
