"""Public identity only. Technical app, ledger and route names stay stable."""
import json
import os
from pathlib import Path

TOKENS = json.loads((Path(__file__).resolve().parent.parent / "static/ownlobby/brand-tokens.json").read_text(encoding="utf-8"))
BRAND = {
    "name": TOKENS["brand"],
    "short_name": TOKENS["brand"],
    "tagline": "Your Lobby. Your Next Level.",
    "domain": TOKENS["domain"],
    "description": "OwnLobby connects competitive gaming communities through tournaments, teams, Game Passport, rankings, and competitive operations.",
    "logo_dark": "ownlobby/logos/primary-horizontal-dark.svg",
    "logo_light": "ownlobby/logos/primary-horizontal-light.svg",
    "symbol_dark": "ownlobby/logos/symbol-dark.svg",
    "symbol_light": "ownlobby/logos/symbol-light.svg",
    "email_logo": "ownlobby/logos/primary-horizontal-dark.png",
    "favicon": "ownlobby/icons/favicon.ico",
    "favicon_svg": "ownlobby/icons/favicon.svg",
    "apple_icon": "ownlobby/icons/icon-180.png",
    "manifest": "ownlobby/manifest.webmanifest",
    "social_image": "ownlobby/social/og-preview-1200x630.png",
    "colors": TOKENS["colors"],
    "theme_color": TOKENS["colors"]["deep"],
    "fonts": {"body": 'Inter, ui-sans-serif, system-ui, sans-serif', "display": 'Inter, ui-sans-serif, system-ui, sans-serif', "mono": 'JetBrains Mono, ui-monospace, monospace'},
    "features": {"coins": "Coins", "ranking_points": "Ranking Points", "ranking_points_short": "RP", "team_rank": "Team Rank", "competitive_hub": "Competitive Hub", "store": "Store", "passport": "Game Passport", "team_hq": "Team HQ", "showdown": "Showdown", "missions": "Missions", "bounty": "Bounty", "dropzone": "Dropzone", "match_rooms": "Match Rooms"},
    # Existing verified destinations stay in service until the owner updates them.
    "social": {"facebook": os.getenv("BRAND_FACEBOOK_URL", "https://www.facebook.com/DeltaCrownGG"), "youtube": os.getenv("BRAND_YOUTUBE_URL", "https://www.youtube.com/@DeltaCrownGG"), "discord": os.getenv("BRAND_DISCORD_URL", "https://discord.gg/UaHRC8Cd")},
    "support_email": os.getenv("BRAND_SUPPORT_EMAIL", "support@deltacrown.xyz"),
}


def brand_copy(value):
    """Resolve identity placeholders in authored copy, never stored user content."""
    for key, text in {"brand": BRAND["name"], **BRAND["features"]}.items():
        value = value.replace("[[" + key + "]]", text)
    return value
