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
        import re
        # Strip Django comments ({# ... #} and {% comment %}...{% endcomment %})
        # so the test can't be tripped by references to "<script>" in docs.
        stripped = re.sub(r'\{#.*?#\}', '', body, flags=re.DOTALL)
        stripped = re.sub(
            r'\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}',
            '',
            stripped,
            flags=re.DOTALL | re.IGNORECASE,
        )
        opens = re.findall(r'<script(\s[^>]*)?>', stripped, flags=re.IGNORECASE)
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

    def test_renderer_uses_es5_compatible_syntax(self):
        """
        The project's CSP doesn't transpile. Optional chaining (`?.`) and
        nullish coalescing (`??`) crash older browsers AND Esprima ES5 parser.
        Keep the file ES5-safe.
        """
        body = _read(STATIC_HUB_PRIZE_JS)
        import re
        # Strip string literals so '?.' inside a quoted string doesn't trip the test.
        no_strings = re.sub(r"'([^'\\]|\\.)*'", "''", body)
        no_strings = re.sub(r'"([^"\\]|\\.)*"', '""', no_strings)
        assert '?.' not in no_strings, 'optional chaining (?.) is not ES5-safe'
        assert '??' not in no_strings, 'nullish coalescing (??) is not ES5-safe'

    def test_renderer_parses_as_es5_script(self):
        """
        Final guard: the JS must parse with esprima's ES5 strict parser.
        Catches multi-line ternary mistakes that produce 'Unexpected token ?'.
        """
        try:
            import esprima
        except ImportError:
            pytest.skip('esprima not installed')
        body = _read(STATIC_HUB_PRIZE_JS)
        try:
            esprima.parseScript(body, tolerant=False)
        except esprima.Error as e:
            pytest.fail(f'hub-prize-engine.js failed ES5 parse: {e}')

    def test_hub_html_includes_prize_engine_static(self):
        body = _read(HUB_BASE_TEMPLATE)
        assert 'hub-prize-engine.js' in body, (
            'hub.html must load the static hub-prize-engine.js'
        )
