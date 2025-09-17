from __future__ import annotations

from typing import Dict, Iterable, Tuple

# (app_label, model_name, actions)
PermissionSpec = Tuple[str, str, Tuple[str, ...]]
StaffGroupMap = Dict[str, Iterable[PermissionSpec]]

STAFF_GROUP_DEFINITIONS: StaffGroupMap = {
    "Valorant Organizer": (
        ("tournaments", "tournament", ("view", "change", "add")),
        ("tournaments", "tournamentsettings", ("view", "change")),
        ("tournaments", "registration", ("view", "change")),
        ("tournaments", "match", ("view", "change")),
        ("tournaments", "paymentverification", ("view", "change")),
        ("game_valorant", "valorantconfig", ("view", "change")),
        ("teams", "team", ("view", "change")),
        ("teams", "teammembership", ("view", "change")),
    ),
    "eFootball Organizer": (
        ("tournaments", "tournament", ("view", "change", "add")),
        ("tournaments", "tournamentsettings", ("view", "change")),
        ("tournaments", "registration", ("view", "change")),
        ("tournaments", "match", ("view", "change")),
        ("tournaments", "paymentverification", ("view", "change")),
        ("game_efootball", "efootballconfig", ("view", "change")),
        ("teams", "team", ("view", "change")),
        ("teams", "teammembership", ("view", "change")),
    ),
    "Team Moderator": (
        ("teams", "team", ("view", "change")),
        ("teams", "teammembership", ("view", "change")),
        ("teams", "teaminvite", ("view", "change", "add")),
    ),
    "Support Staff": (
        ("tournaments", "tournament", ("view",)),
        ("tournaments", "tournamentsettings", ("view",)),
        ("tournaments", "registration", ("view", "change")),
        ("tournaments", "paymentverification", ("view", "change")),
        ("tournaments", "match", ("view",)),
    ),
}

STAFF_GROUP_NAMES = frozenset(STAFF_GROUP_DEFINITIONS.keys())

LEGACY_GROUP_NAMES = frozenset(
    {
        "Platform Admin",
    }
)
