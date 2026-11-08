"""OL-05: public tournament list images must not all load eagerly (template-source check, no database)."""
import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[3] / "templates" / "tournaments" / "list.html"


def test_offscreen_list_images_are_lazy_and_the_first_row_of_cards_stays_eager():
    tags = re.findall(r"<img[^>]*>", TEMPLATE.read_text(encoding="utf-8"), re.S)
    assert len(tags) >= 4
    card_banners = [tag for tag in tags if "t.banner_image" in tag]
    assert len(card_banners) == 1
    # first two cards (the first row of the two-column grid) load immediately: never lazy-load likely LCP imagery
    assert 'loading="{% if forloop.counter <= 2 %}eager{% else %}lazy{% endif %}"' in card_banners[0]
    for tag in tags:
        assert 'decoding="async"' in tag, tag[:120]
        if tag is not card_banners[0]:
            assert 'loading="lazy"' in tag, tag[:120]  # filter icons, per-card game icons, winners sidebar


def test_fixed_size_icons_reserve_their_space():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'alt="{{ game.name }}" width="24" height="24"' in html
    assert 'class="w-9 h-9 rounded object-cover border border-white/10" width="36" height="36"' in html
