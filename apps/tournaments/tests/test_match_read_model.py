"""
Canonical MatchReadModel — unit tests.

These verify the read model's decision rules without hitting a real DB:
  * BracketNode.match FK → source='bracket_node', stage='knockout'
  * BracketNode exists at coord but match_id null → source='inferred_legacy'
  * No node → falls back to format-based classifier
  * Round label uses BracketNode.round_number over Match.round_number

To stay hermetic, we patch the Django ORM calls inside `MatchReadModel._load`
with pure-Python stubs. Integration tests that exercise the real ORM live
in the DB-backed suite (needs Postgres).
"""

from types import SimpleNamespace as SN

import pytest


class _FakeMatch(SN):
    pass


def _fake_match(**kwargs):
    defaults = {
        'id': 1, 'is_deleted': False, 'round_number': 1, 'match_number': 1,
        'bracket_id': None, 'state': 'completed',
        'participant1_id': 10, 'participant1_name': 'Team A',
        'participant2_id': 20, 'participant2_name': 'Team B',
        'participant1_score': 2, 'participant2_score': 1,
        'winner_id': 10, 'loser_id': 20,
        'scheduled_time': None, 'started_at': None, 'completed_at': None,
        'best_of': 1,
    }
    defaults.update(kwargs)
    return _FakeMatch(**defaults)


def _fake_node(**kwargs):
    defaults = {
        'id': 100, 'bracket_id': 500, 'match_id': None,
        'round_number': 1, 'match_number_in_round': 1,
        'bracket_type': 'main', 'is_bye': False,
        'participant1_id': 10, 'participant1_name': 'Team A',
        'participant2_id': 20, 'participant2_name': 'Team B',
        'winner_id': 10,
    }
    defaults.update(kwargs)
    return SN(**defaults)


@pytest.fixture
def patched_read_model(monkeypatch):
    """Patch MatchReadModel._load to use in-memory fake ORM state."""
    from apps.tournaments.services import match_read_model as mrm

    def _make(*, format='single_elimination', matches=None, nodes=None,
             total_rounds=3, bracket_id=500):
        from types import SimpleNamespace
        matches = matches or []
        nodes = nodes or []
        tournament = SimpleNamespace(
            pk=1, id=1, format=format, is_deleted=False,
        )
        bracket = SimpleNamespace(id=bracket_id, tournament=tournament,
                                   total_rounds=total_rounds)

        class _MatchQS(list):
            def order_by(self, *a): return self
            def filter(self, **kw): return self
            def values_list(self, *a, **kw): return [m.round_number for m in self]

        class _MatchMgr:
            @staticmethod
            def filter(**kw):
                return _MatchQS(matches)

        class _BracketMgr:
            @staticmethod
            def filter(**kw):
                class _BQS(list):
                    def first(self): return self[0] if self else None
                return _BQS([bracket])

        class _NodeMgr:
            @staticmethod
            def filter(**kw):
                return nodes

        # Patch Match + Bracket + BracketNode lookups used by read model.
        monkeypatch.setattr(mrm, 'Match', SimpleNamespace(objects=_MatchMgr))
        # round_naming.tournament_total_rounds relies on Bracket + Match;
        # patch it with a fixed return so tests stay DB-free.
        monkeypatch.setattr(mrm, '_total_rounds',
                            lambda t, bracket=None: total_rounds)

        # Patch the Bracket/BracketNode import inside _load.
        import sys, types as _types
        brackets_models_fake = _types.ModuleType('apps.brackets.models')
        brackets_models_fake.Bracket = SimpleNamespace(objects=_BracketMgr)
        brackets_models_fake.BracketNode = SimpleNamespace(objects=_NodeMgr)
        monkeypatch.setitem(sys.modules, 'apps.brackets.models',
                            brackets_models_fake)

        return mrm.MatchReadModel.for_tournament(tournament)

    return _make


class TestCanonicalRoundAndStage:

    def test_bracket_node_fk_drives_stage(self, patched_read_model):
        m = _fake_match(id=1, round_number=1, match_number=1, bracket_id=None)
        n = _fake_node(match_id=1, round_number=3)  # node says round 3
        rm = patched_read_model(matches=[m], nodes=[n])
        view = rm.by_id(1)
        assert view is not None
        assert view['stage'] == 'knockout'
        assert view['source'] == 'bracket_node'
        # Canonical round_number comes from the node.
        assert view['round_number'] == 3
        assert view['raw_round_number'] == 1

    def test_inferred_legacy_link_when_match_id_missing(self, patched_read_model):
        # BracketNode exists at coord (2, 1) but match.bracket_id is null and
        # node.match_id is null — should still infer knockout.
        m = _fake_match(id=1, round_number=2, match_number=1, bracket_id=None)
        n = _fake_node(match_id=None, round_number=2, match_number_in_round=1)
        rm = patched_read_model(matches=[m], nodes=[n])
        view = rm.by_id(1)
        assert view['stage'] == 'knockout'
        assert view['source'] == 'inferred_legacy'

    def test_pure_knockout_without_node_still_knockout(self, patched_read_model):
        m = _fake_match(id=1, round_number=2, bracket_id=None)
        rm = patched_read_model(matches=[m], nodes=[])
        view = rm.by_id(1)
        assert view['stage'] == 'knockout'
        assert view['source'] == 'match'

    def test_round_robin_always_group(self, patched_read_model):
        m = _fake_match(id=1, round_number=2, bracket_id=None)
        rm = patched_read_model(format='round_robin', matches=[m])
        view = rm.by_id(1)
        assert view['stage'] == 'group_stage'

    def test_group_playoff_with_node_is_knockout(self, patched_read_model):
        m = _fake_match(id=1, round_number=1, bracket_id=None)
        n = _fake_node(match_id=1, round_number=1)
        rm = patched_read_model(format='group_playoff', matches=[m], nodes=[n])
        assert rm.by_id(1)['stage'] == 'knockout'

    def test_group_playoff_without_node_is_group(self, patched_read_model):
        m = _fake_match(id=1, round_number=1, bracket_id=None)
        rm = patched_read_model(format='group_playoff', matches=[m])
        assert rm.by_id(1)['stage'] == 'group_stage'


class TestRoundOptions:

    def test_8_team_single_elim_emits_canonical_labels(self, patched_read_model):
        ms = [
            _fake_match(id=1, round_number=1, match_number=1),
            _fake_match(id=2, round_number=1, match_number=2),
            _fake_match(id=3, round_number=1, match_number=3),
            _fake_match(id=4, round_number=1, match_number=4),
            _fake_match(id=5, round_number=2, match_number=1),
            _fake_match(id=6, round_number=2, match_number=2),
            _fake_match(id=7, round_number=3, match_number=1),
        ]
        rm = patched_read_model(total_rounds=3, matches=ms, nodes=[])
        labels = [o['label'] for o in rm.round_options()]
        assert labels == ['Quarterfinal', 'Semifinal', 'Final']
        assert all(o['stage'] == 'knockout' for o in rm.round_options())


class TestFilterBehavior:

    def test_filter_by_canonical_round_number(self, patched_read_model):
        # Match.round_number=1 but node.round_number=3. Filtering by round=3
        # must return the match (bracket tree is authoritative).
        m = _fake_match(id=1, round_number=1, bracket_id=None)
        n = _fake_node(match_id=1, round_number=3)
        rm = patched_read_model(matches=[m], nodes=[n], total_rounds=3)
        assert [v['match_id'] for v in rm.filter(round_number=3)] == [1]


class TestCanonicalParticipants:
    """The big-fix test set — node-first participant resolution."""

    def test_node_participant_overrides_tba_match(self, patched_read_model):
        # The bracket tree knows the real semifinal teams; the Match row is TBA.
        m = _fake_match(
            id=1, round_number=2, match_number=1, bracket_id=None,
            participant1_id=None, participant1_name='',
            participant2_id=None, participant2_name='TBA',
            winner_id=None,
        )
        n = _fake_node(
            match_id=1, round_number=2, match_number_in_round=1,
            participant1_id=10, participant1_name='Tower_Tareq',
            participant2_id=20, participant2_name='rkrashik',
            winner_id=20,
        )
        rm = patched_read_model(matches=[m], nodes=[n])
        v = rm.by_id(1)
        # Canonical participants come from the node.
        assert v['participant1_id'] == 10
        assert v['participant1_name'] == 'Tower_Tareq'
        assert v['participant2_id'] == 20
        assert v['participant2_name'] == 'rkrashik'
        assert v['winner_id'] == 20
        assert v['winner_side'] == 2
        assert v['winner_name'] == 'rkrashik'
        # Raw fields preserved for repair tooling.
        assert v['raw_participant1_name'] == ''
        assert v['raw_participant2_name'] == 'TBA'

    def test_match_participant_used_when_node_slot_empty(self, patched_read_model):
        # Node slot is genuinely TBD — Match has the participant. Match wins.
        m = _fake_match(
            id=1, round_number=1, match_number=1, bracket_id=None,
            participant1_id=10, participant1_name='Team A',
            participant2_id=20, participant2_name='Team B',
        )
        n = _fake_node(
            match_id=1, round_number=1, match_number_in_round=1,
            participant1_id=None, participant1_name='',
            participant2_id=None, participant2_name='',
            winner_id=None,
        )
        rm = patched_read_model(matches=[m], nodes=[n])
        v = rm.by_id(1)
        assert v['participant1_id'] == 10
        assert v['participant1_name'] == 'Team A'
        assert v['participant2_id'] == 20
        assert v['participant2_name'] == 'Team B'

    def test_winner_id_falls_back_to_match_when_node_empty(self, patched_read_model):
        m = _fake_match(
            id=1, round_number=1, bracket_id=None,
            participant1_id=10, participant1_name='Team A',
            participant2_id=20, participant2_name='Team B',
            winner_id=10,
        )
        n = _fake_node(match_id=1, round_number=1, winner_id=None)
        rm = patched_read_model(matches=[m], nodes=[n])
        assert rm.by_id(1)['winner_id'] == 10

    def test_node_winner_overrides_match_when_match_winner_missing(self, patched_read_model):
        m = _fake_match(
            id=1, round_number=1, bracket_id=None,
            participant1_id=10, participant1_name='Team A',
            participant2_id=20, participant2_name='Team B',
            winner_id=None,
        )
        n = _fake_node(match_id=1, round_number=1, winner_id=20)
        rm = patched_read_model(matches=[m], nodes=[n])
        v = rm.by_id(1)
        assert v['winner_id'] == 20
        assert v['winner_side'] == 2
        assert v['winner_name'] == 'Team B'

    def test_efootball_genesis_cup_shape(self, patched_read_model):
        # End-to-end shape mirroring the real legacy bug. Final match exists
        # in DB with TBA participants but bracket node has the real teams.
        sf1 = _fake_match(id=2, round_number=2, match_number=1, bracket_id=None,
                          participant1_id=None, participant1_name='', participant2_id=None,
                          participant2_name='', winner_id=None)
        sf2 = _fake_match(id=3, round_number=2, match_number=2, bracket_id=None,
                          participant1_id=None, participant1_name='', participant2_id=None,
                          participant2_name='', winner_id=None)
        final_m = _fake_match(id=4, round_number=3, match_number=1, bracket_id=None,
                              participant1_id=None, participant1_name='',
                              participant2_id=None, participant2_name='',
                              winner_id=None,
                              participant1_score=1, participant2_score=2)
        sf1_node = _fake_node(id=12, match_id=2, round_number=2, match_number_in_round=1,
                              participant1_id=11, participant1_name='Pistol_Pappu',
                              participant2_id=22, participant2_name='rkrashik',
                              winner_id=22)
        sf2_node = _fake_node(id=13, match_id=3, round_number=2, match_number_in_round=2,
                              participant1_id=33, participant1_name='Tower_Tareq',
                              participant2_id=44, participant2_name='Other',
                              winner_id=33)
        final_node = _fake_node(id=14, match_id=4, round_number=3, match_number_in_round=1,
                                participant1_id=33, participant1_name='Tower_Tareq',
                                participant2_id=22, participant2_name='rkrashik',
                                winner_id=22)
        rm = patched_read_model(
            total_rounds=3,
            matches=[sf1, sf2, final_m],
            nodes=[sf1_node, sf2_node, final_node],
        )
        final_view = rm.by_id(4)
        assert final_view['participant1_name'] == 'Tower_Tareq'
        assert final_view['participant2_name'] == 'rkrashik'
        assert final_view['winner_id'] == 22
        assert final_view['winner_name'] == 'rkrashik'
        assert final_view['round_label'] == 'Final'
        assert final_view['stage'] == 'knockout'
        assert rm.filter(round_number=1) == []  # raw round_number gone


class TestParticipantCanonicalization:
    """Node-first participant slots — TBA Match must not override real node data."""

    def test_node_participant_overrides_tba_match(self, patched_read_model):
        # Match has TBA participants but BracketNode knows the real teams.
        m = _fake_match(
            id=1, round_number=2, bracket_id=None,
            participant1_id=None, participant1_name='',
            participant2_id=None, participant2_name='',
            participant1_score=2, participant2_score=1,
            winner_id=None,
        )
        n = _fake_node(
            match_id=1, round_number=2,
            participant1_id=99, participant1_name='Tower_Tareq',
            participant2_id=100, participant2_name='rkrashik',
            winner_id=100,
        )
        rm = patched_read_model(matches=[m], nodes=[n], total_rounds=3)
        view = rm.by_id(1)
        assert view['participant1_id'] == 99
        assert view['participant1_name'] == 'Tower_Tareq'
        assert view['participant2_id'] == 100
        assert view['participant2_name'] == 'rkrashik'
        # Raw fields preserved.
        assert view['raw_participant1_id'] is None
        assert view['raw_participant1_name'] == ''
        # Winner flows from node when match.winner_id is null.
        assert view['winner_id'] == 100
        assert view['winner_side'] == 2
        assert view['winner_name'] == 'rkrashik'
        # Scores still come from Match row.
        assert view['participant1_score'] == 2
        assert view['participant2_score'] == 1

    def test_node_empty_slot_falls_back_to_match(self, patched_read_model):
        # Node has slot 1 filled, slot 2 TBD; match has slot 2 filled.
        m = _fake_match(
            id=1, round_number=1,
            participant1_id=None, participant1_name='',
            participant2_id=42, participant2_name='Wildcard',
        )
        n = _fake_node(
            match_id=1, round_number=1,
            participant1_id=99, participant1_name='Champion',
            participant2_id=None, participant2_name='',
        )
        rm = patched_read_model(matches=[m], nodes=[n])
        view = rm.by_id(1)
        # Slot 1 from node.
        assert view['participant1_id'] == 99
        assert view['participant1_name'] == 'Champion'
        # Slot 2 from match (node was empty there).
        assert view['participant2_id'] == 42
        assert view['participant2_name'] == 'Wildcard'

    def test_no_node_uses_raw_match_fields(self, patched_read_model):
        m = _fake_match(id=1, round_number=2, participant1_name='Solo Match Team')
        rm = patched_read_model(matches=[m], nodes=[])
        view = rm.by_id(1)
        assert view['participant1_name'] == 'Solo Match Team'
        assert view['source'] == 'match'

    def test_winner_id_from_node_overrides_match_winner(self, patched_read_model):
        m = _fake_match(
            id=1, round_number=1,
            participant1_id=10, participant2_id=20,
            winner_id=10,  # match says 10 wins
        )
        n = _fake_node(
            match_id=1, round_number=1,
            participant1_id=10, participant2_id=20,
            winner_id=20,  # node says 20 wins (e.g. dispute resolved at node)
        )
        rm = patched_read_model(matches=[m], nodes=[n])
        view = rm.by_id(1)
        assert view['winner_id'] == 20
        assert view['winner_side'] == 2
