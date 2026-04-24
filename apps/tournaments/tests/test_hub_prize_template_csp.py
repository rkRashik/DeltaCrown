"""
Hub Prizes template CSP guards.

Make sure the Hub Prizes tab partial doesn't reintroduce a raw inline
`<script>` block. The renderer logic must live in
`static/tournaments/js/hub-prize-engine.js` so the strict CSP doesn't
refuse it.

These tests don't need the database — they just read the template file.
"""

import os

import pytest


HUB_PRIZES_PARTIAL = os.path.join(
    'templates', 'tournaments', 'hub', '_tab_prizes.html',
)
STATIC_HUB_PRIZE_JS = os.path.join(
    'static', 'tournaments', 'js', 'hub-prize-engine.js',
)
HUB_BASE_TEMPLATE = os.path.join(
    'templates', 'tournaments', 'hub', 'hub.html',
)


def _read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


class TestHubPrizesPartialIsCSPSafe:
    def test_no_inline_script_block(self):
        body = _read(HUB_PRIZES_PARTIAL)
        # Allow `<script src=...>` but never a raw inline `<script>` body.
        # We catch both `<script>` and `<script ` (no src attribute follows).
        # Accept `<script src=...>` though by requiring `src=` between
        # `<script` and `>`.
        import re
        # Find every <script ... > tag start.
        opens = re.findall(r'<script(\s[^>]*)?>', body, flags=re.IGNORECASE)
        for tag in opens:
            attrs = (tag or '').strip()
            assert 'src=' in attrs.lower(), (
                'Hub Prizes partial must not contain inline <script> blocks; '
                'CSP will refuse them. Move logic to a static .js file.'
            )

    def test_root_element_present(self):
        body = _read(HUB_PRIZES_PARTIAL)
        assert 'id="hub-prize-engine"' in body
        assert 'data-prize-overview-url=' in body

    def test_renderer_static_file_exists(self):
        assert os.path.exists(STATIC_HUB_PRIZE_JS), (
            'hub-prize-engine.js must exist as a static file'
        )
        body = _read(STATIC_HUB_PRIZE_JS)
        assert 'hub-prize-engine' in body
        assert 'fetch(' in body

    def test_hub_html_includes_prize_engine_static(self):
        body = _read(HUB_BASE_TEMPLATE)
        assert 'hub-prize-engine.js' in body, (
            'hub.html must load the static hub-prize-engine.js'
        )
