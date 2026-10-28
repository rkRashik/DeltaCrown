from deltacrown.branding import BRAND, brand_copy
# Central content layer injected as SITE (Part 1 contract)
SITE_CONTENT = {
    "brand": {
        "tagline": BRAND["tagline"],
        "subtext": "Bangladesh-born, globally-driven esports.",
    },
    "hero": {
        "discord_url": BRAND["social"]["discord"],
        "fallback_cta_url": "/tournaments/",
        "cta_labels": {
            "open": "Enter {name}",
            "ongoing": "Watch Live Now",
            "closed": "See All Events",
        },
    },
    # Optional: countdown target for next showcase tournament (ISO8601, local or Z)
    "next_event_iso": None,

    "timeline": [],
    "stats": {
        "players": 0,
        "prize_bdt": 0,
        "payout_accuracy_pct": None,
    },
    "spotlight": None,
    "social": BRAND["social"],
    "final_cta": {
        "events_url": "/tournaments/",
        "discord_url": BRAND["social"]["discord"],
    },
    "signals": [],
}
