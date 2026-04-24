"""
Prize Config Service unit tests — normalisation logic.

The pure normalisation paths (`_normalize_for_write`, `_normalize_for_read`)
need no DB. Persistence and the public_payload merge are exercised in
integration tests that require a database.
"""

from apps.tournaments.services.prize_config_service import (
    PrizeConfigService,
    _ordinal,
)


class TestOrdinal:
    def test_basic(self):
        assert _ordinal(1) == '1st'
        assert _ordinal(2) == '2nd'
        assert _ordinal(3) == '3rd'
        assert _ordinal(4) == '4th'

    def test_teens(self):
        assert _ordinal(11) == '11th'
        assert _ordinal(12) == '12th'
        assert _ordinal(13) == '13th'

    def test_higher(self):
        assert _ordinal(21) == '21st'
        assert _ordinal(102) == '102nd'


class TestNormaliseForWrite:
    def test_clamps_percent_and_strips_negatives(self):
        out = PrizeConfigService._normalize_for_write({
            'currency': 'usd',
            'fiat_pool': '5000',
            'coin_pool': -100,
            'placements': [
                {'rank': 1, 'title': 'Champion', 'percent': 200, 'fiat': -10, 'coins': 'abc'},
                {'rank': 2, 'title': '', 'percent': 30, 'fiat': 1500, 'coins': 300},
            ],
            'special_awards': [],
        })
        assert out['currency'] == 'USD'
        assert out['fiat_pool'] == 5000
        assert out['coin_pool'] == 0
        assert out['placements'][0]['percent'] == 100
        assert out['placements'][0]['fiat'] == 0
        assert out['placements'][0]['coins'] == 0
        # Empty title falls back to ordinal.
        assert out['placements'][1]['title'] == '2nd'

    def test_dedupes_ranks_and_sorts(self):
        out = PrizeConfigService._normalize_for_write({
            'placements': [
                {'rank': 3, 'title': 'C', 'percent': 10},
                {'rank': 1, 'title': 'A', 'percent': 50},
                {'rank': 1, 'title': 'Dup', 'percent': 20},  # dropped
                {'rank': 2, 'title': 'B', 'percent': 30},
            ],
        })
        ranks = [p['rank'] for p in out['placements']]
        titles = [p['title'] for p in out['placements']]
        assert ranks == [1, 2, 3]
        assert titles == ['A', 'B', 'C']  # 'Dup' filtered

    def test_skips_invalid_ranks(self):
        out = PrizeConfigService._normalize_for_write({
            'placements': [
                {'rank': 0, 'title': 'Zero'},
                {'rank': -2, 'title': 'Neg'},
                {'rank': 'x', 'title': 'NaN'},
                {'rank': 1, 'title': 'Valid'},
            ],
        })
        assert len(out['placements']) == 1
        assert out['placements'][0]['title'] == 'Valid'

    def test_special_awards_default_type(self):
        out = PrizeConfigService._normalize_for_write({
            'placements': [],
            'special_awards': [
                {'title': 'MVP', 'type': 'weird'},
                {'title': '', 'type': 'cash'},  # empty title dropped
                {'title': 'Hardware', 'type': 'hardware', 'reward_text': 'Mouse'},
            ],
        })
        assert len(out['special_awards']) == 2
        # Invalid type → 'cash' default.
        assert out['special_awards'][0]['type'] == 'cash'
        assert out['special_awards'][0]['id']  # auto-slugged
        assert out['special_awards'][1]['type'] == 'hardware'
        assert out['special_awards'][1]['reward_text'] == 'Mouse'

    def test_certificates_enabled_defaults_true(self):
        out = PrizeConfigService._normalize_for_write({})
        assert out['certificates_enabled'] is True
        out2 = PrizeConfigService._normalize_for_write({'certificates_enabled': False})
        assert out2['certificates_enabled'] is False
