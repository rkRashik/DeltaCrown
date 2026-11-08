"""OL-05: public tournament list images must not all load eagerly (template-source check, no database)."""
import re
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[3] / "templates" / "tournaments" / "list.html"


def test_every_list_image_is_lazy_and_decoded_asynchronously():
    tags = re.findall(r"<img\b[^>]*>", TEMPLATE.read_text(encoding="utf-8"), re.S)
    assert len(tags) >= 4
    for tag in tags:
        assert 'loading="lazy"' in tag and 'decoding="async"' in tag, tag[:120]


def test_fixed_size_icons_reserve_their_space():
    html = TEMPLATE.read_text(encoding="utf-8")
    assert 'alt="{{ game.name }}" width="24" height="24"' in html
    assert 'class="w-9 h-9 rounded object-cover border border-white/10" width="36" height="36"' in html
