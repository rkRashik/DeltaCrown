"""Static design-section content for the redesigned homepage body.

These sections (why / ecosystem / daily-ops / crown-points ladder / teams copy /
trust / organizer ops rows / pathways) are FINAL, static brand content per the
DeltaCrown Homepage handoff (§3 "Real data needed: None"). They carry the exact
approved copy and the design's inline SVG icon set, kept out of the template so
home.html stays readable. Pure dict construction — cheap, no DB, no cache.

The icon strings are trusted, hand-authored SVG markup (rendered with `|safe`),
never user input.
"""
from __future__ import annotations

from typing import Any, Dict, List

# Triad tokens (match colors_and_type.css / home.css)
_AZ = "var(--az4)"
_VI = "var(--vi4)"
_GO = "var(--go4)"
_SUC = "var(--suc)"
_SOFT = "var(--soft)"

# Inner SVG path markup, keyed by name (verified against the design's icon map).
_ICONS: Dict[str, str] = {
    "trophy": '<path d="M7 4h10v3a5 5 0 0 1-10 0V4Z"/><path d="M9 14v3h6v-3M8 21h8M12 12v2"/>',
    "team": '<circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><circle cx="17" cy="9" r="2"/><path d="M19 19c0-2-1.4-3.4-3-3.8"/>',
    "bolt": '<path d="M13 2 4 14h7l-1 8 9-12h-7l1-8Z"/>',
    "flag": '<path d="M5 21V4M5 4h11l-2 4 2 4H5"/>',
    "target": '<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 1v3M12 20v3M1 12h3M20 12h3"/>',
    "drop": '<path d="M12 3v10M8 9l4 4 4-4M5 20h14"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8.5 12.5 11 15l5-5.5"/>',
    "shield": '<path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z"/><path d="M9.5 12l1.8 1.8L15 10"/>',
    "scale": '<path d="M12 4v16M7 8h10M5 8l-2.5 6h5L5 8ZM19 8l-2.5 6h5L19 8Z"/>',
    "coin": '<circle cx="12" cy="12" r="8"/><path d="M12 8v8M9.5 9.5h3.2a1.8 1.8 0 0 1 0 3.6H9.5"/>',
    "roster": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 13h8M8 16h5"/>',
    "swords": '<path d="M14.5 4H20v5.5L9 20.5 3.5 15 14.5 4Z"/><path d="M16 16l4 4M4 4l4 4"/>',
    "cal": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 9h18M8 3v4M16 3v4"/>',
    "door": '<path d="M14 3H6v18h8M14 3l4 2v14l-4 2M14 3v18M11 12h.01"/>',
    "gavel": '<path d="M9 11l5-5 4 4-5 5-4-4ZM7 13l4 4M4 21h8"/>',
    "crown": '<path d="M3 17l2-9 4 5 3-7 3 7 4-5 2 9Z"/><path d="M3 20h18"/>',
    "store": '<path d="M4 9h16l-1-4H5L4 9Z"/><path d="M4 9v10h16V9M4 9a2.4 2.4 0 0 0 4 0 2.4 2.4 0 0 0 4 0 2.4 2.4 0 0 0 4 0 2.4 2.4 0 0 0 4 0"/>',
    "idcard": '<rect x="3" y="5" width="18" height="14" rx="2"/><circle cx="8.5" cy="11" r="2.2"/><path d="M14 10h4M14 14h4M5 16c.6-1.4 2-2 3.5-2s2.9.6 3.5 2"/>',
    "users": '<circle cx="8" cy="9" r="3"/><path d="M2 20c0-3.5 2.7-5.5 6-5.5s6 2 6 5.5"/><circle cx="17" cy="8" r="2.5"/><path d="M16 14.5c3 .3 5 2.3 5 5.5"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    "handshake": '<path d="M3 12l4-4 4 3 3-2 4 4"/><path d="M11 11l2 2a1.6 1.6 0 0 0 2.3-2.3"/><path d="M21 13l-4 4-3-2"/><path d="M3 12v3M21 13v-3"/>',
    "whistle": '<circle cx="9" cy="13" r="5"/><path d="M14 11l7-3-1 4-6 1M9 8V5h3"/>',
}


def _svg(name: str, color: str = "currentColor", size: int = 20) -> str:
    """Return the inline SVG markup for an icon at *size* / *color* (stroke 1.7)."""
    paths = _ICONS.get(name, "")
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
        f'stroke="{color}" stroke-width="1.7" stroke-linecap="round" '
        f'stroke-linejoin="round">{paths}</svg>'
    )


def get_homepage_sections() -> Dict[str, Any]:
    """Return the static body-section content consumed by templates/home.html."""
    return {
        # §2 — Why DeltaCrown (old way uses an inline ✕ in the template)
        "why_old": [
            {"title": "Scattered group chats",
             "desc": "Brackets buried in Discord DMs, screenshots passed around as proof."},
            {"title": "Pay-later, ghost-later",
             "desc": "Prize money promised on stream — paid halfway, if at all."},
            {"title": "Score arguments",
             "desc": "No referee, no log. Whoever argues loudest takes the win."},
            {"title": "Results that vanish",
             "desc": "Wins disappear into chat history. Nothing counts, nothing carries."},
        ],
        "why_new": [
            {"title": "Verified match rooms", "color": _AZ, "icon": _svg("grid", _AZ, 15),
             "desc": "One page per match — live score, evidence, chat and dispute, all logged."},
            {"title": "Escrow-backed payouts", "color": _GO, "icon": _svg("coin", _GO, 15),
             "desc": "The pot is locked at registration and released only on a verified result."},
            {"title": "Proof & dispute review", "color": _VI, "icon": _svg("shield", _VI, 15),
             "desc": "Contested results route to a review queue and are settled on the record."},
            {"title": "A record that counts", "color": _SUC, "icon": _svg("check", _SUC, 15),
             "desc": "Every verified match feeds Crown Points and a history that travels with you."},
        ],
        # §4 — Ecosystem (8 connected pillars)
        "ecosystem_pillars": [
            {"name": "Tournaments", "color": _AZ, "tint": "var(--tAz)", "bd": "rgba(10,132,255,.3)",
             "icon": _svg("trophy", _AZ, 19),
             "blurb": "Verified brackets across 11 titles — single elim to battle royale leagues."},
            {"name": "Teams & Team HQ", "color": _VI, "tint": "var(--tVi)", "bd": "rgba(104,73,229,.3)",
             "icon": _svg("users", _VI, 19),
             "blurb": "Roster, scrims, tryouts and a shared competitive record."},
            {"name": "Game Passport", "color": _AZ, "tint": "var(--tAz)", "bd": "rgba(10,132,255,.3)",
             "icon": _svg("idcard", _AZ, 19),
             "blurb": "Your verified identity and linked game IDs — one profile, every title."},
            {"name": "Match Rooms", "color": _AZ, "tint": "var(--tAz)", "bd": "rgba(10,132,255,.3)",
             "icon": _svg("grid", _AZ, 19),
             "blurb": "Live score, evidence and dispute — one operated page per match."},
            {"name": "Competitive Hub", "color": _VI, "tint": "var(--tVi)", "bd": "rgba(104,73,229,.3)",
             "icon": _svg("bolt", _VI, 19),
             "blurb": "Showdown, Missions, Bounty and Dropzone — reward play every day."},
            {"name": "Crown Points", "color": _GO, "tint": "var(--tGo)", "bd": "rgba(207,167,90,.3)",
             "icon": _svg("crown", _GO, 19),
             "blurb": "A cross-game rank — opponent-scaled, anti-farm, seasonally reset."},
            {"name": "DeltaCoin", "color": _GO, "tint": "var(--tGo)", "bd": "rgba(207,167,90,.3)",
             "icon": _svg("coin", _GO, 19),
             "blurb": "Reward utility earned through verified competition across the platform."},
            {"name": "Crown Store", "color": _VI, "tint": "var(--tVi)", "bd": "rgba(104,73,229,.3)",
             "icon": _svg("store", _VI, 19),
             "blurb": "Spend earned rewards on cosmetics, perks and event entries."},
        ],
        # §5 — Daily Ops (4 always-on modes)
        "daily_modes": [
            {"name": "Showdown", "url": "/dashboard/showdown/", "meta": "Earns CP + DC",
             "color": _AZ, "tint": "var(--tAz)", "bd": "rgba(10,132,255,.3)", "icon": _svg("bolt", _AZ),
             "desc": "Reward matches for Crown Points and DeltaCoin — queue, play, get verified."},
            {"name": "Missions", "url": "/dashboard/missions/", "meta": "Resets daily",
             "color": _VI, "tint": "var(--tVi)", "bd": "rgba(104,73,229,.3)", "icon": _svg("flag", _VI),
             "desc": "Daily and weekly objectives that keep your progression moving between events."},
            {"name": "Bounty", "url": "/dashboard/bounty/", "meta": "Community-posted",
             "color": _GO, "tint": "var(--tGo)", "bd": "rgba(207,167,90,.3)", "icon": _svg("target", _GO),
             "desc": "Open challenges posted by players and teams — claim one and prove it."},
            {"name": "Dropzone", "url": "/dashboard/dropzone/", "meta": "Always open",
             "color": _AZ, "tint": "var(--tAz)", "bd": "rgba(10,132,255,.3)", "icon": _svg("drop", _AZ),
             "desc": "Drop-in lobbies for fast, low-stakes competitive play any time of day."},
        ],
        # §6 — Crown Points ladder (Rookie → The Crown)
        "crown_tiers": [
            {"name": "Rookie", "cp": "0 CP", "dot": "#3a4256", "glow": "transparent",
             "row": "var(--s1)", "rb": "var(--hair)", "tx": "var(--mut)"},
            {"name": "Challenger", "cp": "100 CP", "dot": "#0A84FF", "glow": "rgba(10,132,255,.5)",
             "row": "var(--s1)", "rb": "var(--hair)", "tx": "var(--fg)"},
            {"name": "Elite", "cp": "500 CP", "dot": "#3FA3FF", "glow": "rgba(63,163,255,.5)",
             "row": "var(--s1)", "rb": "var(--hair)", "tx": "var(--fg)"},
            {"name": "Master", "cp": "2,000 CP", "dot": "#6849E5", "glow": "rgba(104,73,229,.55)",
             "row": "var(--s1)", "rb": "var(--hair)", "tx": "var(--fg)"},
            {"name": "Legend", "cp": "8,000 CP", "dot": "#8470EE", "glow": "rgba(132,112,238,.55)",
             "row": "var(--s1)", "rb": "var(--hair)", "tx": "var(--fg)"},
            {"name": "The Crown", "cp": "30,000 CP+", "dot": "#E2C588", "glow": "rgba(226,197,136,.7)",
             "row": "linear-gradient(90deg,rgba(207,167,90,.14),rgba(104,73,229,.06))",
             "rb": "rgba(207,167,90,.35)", "tx": "var(--go4)"},
        ],
        # §7 — Teams: illustrative roster (role labels only — no fabricated identities)
        "team_roles": [
            {"code": "IG", "role": "IGL", "bg": "linear-gradient(140deg,#7C5CFF,#0A84FF)"},
            {"code": "DU", "role": "Duelist", "bg": "linear-gradient(140deg,#0A84FF,#3FA3FF)"},
            {"code": "SE", "role": "Sentinel", "bg": "linear-gradient(140deg,#6849E5,#8470EE)"},
            {"code": "FX", "role": "Flex", "bg": "linear-gradient(140deg,#3FA3FF,#6849E5)"},
            {"code": "IN", "role": "Init", "bg": "linear-gradient(140deg,#8470EE,#0A84FF)"},
        ],
        "team_features": [
            {"title": "Roster & Team HQ —", "icon": _svg("roster", _VI, 17),
             "desc": "manage members, roles and invites in one workspace."},
            {"title": "Scrims & tryouts —", "icon": _svg("swords", _VI, 17),
             "desc": "schedule practice and recruit through open tryouts."},
            {"title": "Shared record —", "icon": _svg("trophy", _VI, 17),
             "desc": "rank, wins and Crown Points travel with the crest."},
        ],
        # §8 — Trust: 5-step proof flow + 4 trust cards
        "trust_flow": [
            {"no": "01", "name": "Register & escrow lock", "tint": "var(--tGo)", "icon": _svg("coin", _GO, 13)},
            {"no": "02", "name": "Play in match room", "tint": "var(--tAz)", "icon": _svg("grid", _AZ, 13)},
            {"no": "03", "name": "Submit result + proof", "tint": "var(--tVi)", "icon": _svg("idcard", _VI, 13)},
            {"no": "04", "name": "Review if disputed", "tint": "var(--tAz)", "icon": _svg("shield", _AZ, 13)},
            {"no": "05", "name": "Verified payout + CP", "tint": "var(--tSu)", "icon": _svg("check", _SUC, 13)},
        ],
        "trust_cards": [
            {"title": "Verified results", "color": _SUC, "icon": _svg("check", _SUC, 20),
             "desc": "Scores are submitted in-platform and confirmed by both sides — no he-said screenshots."},
            {"title": "Dispute-aware rooms", "color": _AZ, "icon": _svg("shield", _AZ, 20),
             "desc": "Every match room captures evidence, so disputes are reviewed on facts, not vibes."},
            {"title": "Escrow-backed payouts", "color": _GO, "icon": _svg("coin", _GO, 20),
             "desc": "Prize money is held in escrow and released on verified results. Clean, every time."},
            {"title": "Fair competition", "color": _VI, "icon": _svg("scale", _VI, 20),
             "desc": "Seeding, check-in and roster locks keep brackets honest from first round to final."},
        ],
        # §9 — Organizer: capability rows below the ops console
        "ops_rows": [
            {"title": "Check-in & seeding —", "desc": "automated, on schedule.", "tag": "Auto",
             "color": _AZ, "icon": _svg("cal", _AZ, 17)},
            {"title": "Live match rooms —", "desc": "ready states & result submit.", "tag": "Live",
             "color": _SUC, "icon": _svg("door", _SUC, 17)},
            {"title": "Disputes & payouts —", "desc": "review queue to escrow release.", "tag": "Queue",
             "color": _GO, "icon": _svg("gavel", _GO, 17)},
        ],
        # §10 — Pathways: four audience entry points
        "pathways": [
            {"name": "Players", "cta": "Create account", "url": "/account/signup/", "accent": _AZ,
             "tint": "var(--tAz)", "bd": "rgba(10,132,255,.32)", "icon": _svg("bolt", _AZ, 20),
             "line": "Compete solo or with a squad, climb the ladder, and build a record that counts."},
            {"name": "Teams & Orgs", "cta": "Create a team", "url": "/teams/create/", "accent": _VI,
             "tint": "var(--tVi)", "bd": "rgba(104,73,229,.32)", "icon": _svg("users", _VI, 20),
             "line": "Build a roster, run Team HQ, and grow a brand that carries its own history."},
            {"name": "Organizers", "cta": "Run an event", "url": "/dashboard/", "accent": _AZ,
             "tint": "var(--tAz)", "bd": "rgba(10,132,255,.32)", "icon": _svg("whistle", _AZ, 20),
             "line": "Run verified events end to end — check-in, match rooms, disputes, payouts."},
            {"name": "Sponsors", "cta": "Partner with us", "url": "/about/", "accent": _GO,
             "tint": "var(--tGo)", "bd": "rgba(207,167,90,.32)", "icon": _svg("handshake", _GO, 20),
             "line": "Back the next wave of talent with verified performance data, not guesswork."},
        ],
    }
