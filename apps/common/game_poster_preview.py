"""Small, already-checked-in game posters for browsing surfaces only.

These are public-intended static *previews*, not copies from private media.
An exact saved origin name check preserves any future staff artwork edits:
when a card changes, its record-governed URL is used instead.
"""
from django.templatetags.static import static


_CARD_PREVIEWS = {
    "valorant": ("media/games/cards/Valorant_c4snne", "img/games/posters/valorant.jpg"),
    "cs2": ("media/games/cards/CS2_rx62o0", "img/games/posters/cs2.jpg"),
    "dota2": ("media/games/cards/dota_2_animated_i94zyq", "img/games/posters/dota2.jpg"),
    "ea-fc": ("media/games/cards/fc-27-1nv56_ciqgqr", "img/games/fc27-key-art.jpg"),
    "efootball": ("media/games/cards/efootball_5_iowa2o", "img/games/posters/efootball.jpg"),
    "pubgm": ("media/games/cards/pubg_ne8ryt", "img/games/posters/pubg.jpg"),
    "mlbb": ("media/games/cards/mlbb_osudev", "img/games/posters/mlbb.jpg"),
    "freefire": ("media/games/cards/FreeFire_egrxu4", "img/games/posters/freefire.jpg"),
    "codm": ("media/games/cards/call_of_duty_dpacmn", "img/games/posters/codm.jpg"),
    "rocketleague": ("media/games/cards/Rocket_league_egp56r", "img/games/posters/rocketleague.jpg"),
    "r6siege": ("media/games/cards/Rainbow_Six_Siege_zf6qnw", "img/games/posters/r6.jpg"),
}


def fast_game_card(game):
    """Return a compact hashed static preview or the original protected URL."""
    field = getattr(game, "card_image", None)
    if not field:
        return ""
    item = _CARD_PREVIEWS.get((getattr(game, "slug", "") or "").lower())
    if item and getattr(field, "name", None) == item[0]:
        return static(item[1])
    return field.url
