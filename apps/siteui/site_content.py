# Central content layer injected as SITE (Part 1 contract)
SITE_CONTENT = {
    "brand": {
        "tagline": "From the Delta to the Crown — Where Champions Rise",
        "subtext": "Bangladesh-born, globally-driven esports.",
    },
    "hero": {
        "discord_url": "https://discord.gg/your-invite",
        "fallback_cta_url": "/tournaments/",
        "cta_labels": {
            "open": "Enter {name}",
            "ongoing": "Watch Live Now",
            "closed": "See All Events",
        },
    },
    # Optional: countdown target for next showcase tournament (ISO8601, local or Z)
    "next_event_iso": "2025-12-01T18:00:00+06:00",

    "timeline": [
        {"date": "2023", "title": "First Community Cup", "desc": "Kicked off with 64 players."},
        {"date": "2024", "title": "Regional Expansion", "desc": "Valorant & eFootball circuits."},
        {"date": "2025", "title": "DeltaCrown Series", "desc": "Bigger stages, bigger prizes."},
    ],
    "stats": {
        "players": 5000,
        "prize_bdt": 2000000,
        "payout_accuracy_pct": 98,
    },
    "spotlight": None,
    "social": {
        "facebook": "https://facebook.com/DeltaCrown",
        "youtube": "https://youtube.com/@DeltaCrown",
        "discord": "https://discord.gg/your-invite",
    },
    "final_cta": {
        "events_url": "/tournaments/",
        "discord_url": "https://discord.gg/your-invite",
    },
    "signals": [],
}
