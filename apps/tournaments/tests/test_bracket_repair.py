"""
BracketRepairService — pure-Python unit tests.

Focus on the logic that decides whether to backfill participant slots, since
that's the most dangerous behaviour. We use in-memory shims for ORM lookups
so the test stays hermetic. Integration tests against a real Postgres live
in the DB-backed suite (skipped here when the local DB is unavailable).
"""

from types import SimpleNamespace

import pytest


class _FakeMatch:
    """Mutable Match shim that records save() calls."""

    def __init__(self, **kwargs):
        defaults = {
            'id': 1, 'is_deleted': False,
            'participant1_id': None, 'participant1_name': '',
            'participant2_id': None, 'participant2_name': '',
            'bracket_id': None,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)
        self.save_calls = []

    def save(self, *, update_fields=None, **kw):
        self.save_calls.append({'update_fields': list(update_fields or [])})


class _FakeNode:
    def __init__(self, **kwargs):
        defaults = {
            'id': 100, 'bracket_id': 500, 'match_id': None,
            'round_number': 1, 'match_number_in_round': 1,
            'bracket_type': 'main', 'is_bye': False,
            'participant1_id': None, 'participant1_name': '',
            'participant2_id': None, 'participant2_name': '',
            'winner_id': None,
            'match': None,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


def _make_repair_env(monkeypatch, *, matches, nodes):
    """Patch the imports the service does at runtime."""
    from apps.tournaments.services import bracket_repair_service as brs
    from contextlib import contextmanager

    # Replace transaction.atomic with a no-op so the service doesn't try to
    # open a DB connection just to wrap our in-memory save() calls.
    @contextmanager
    def _fake_atomic(*a, **kw):
        yield
    monkeypatch.setattr(brs.transaction, 'atomic', _fake_atomic)

    bracket = SimpleNamespace(id=500, tournament=None)

    class _MatchObjects:
        @staticmethod
        def filter(**kw):
            # Used for orphan-bracket-FK backfill — return an empty result so
            # phase 2 doesn't block phase 3 tests.
            class _QS:
                def __init__(self, items): self._items = items
                def update(self, **vals): return 0
                def count(self): return len(self._items)
            return _QS([])

    class _BracketObjects:
        @staticmethod
        def filter(**kw):
            class _BQS:
                def first(self):
                    return bracket
            return _BQS()

    class _LinkedQS(list):
        def values_list(self, *a, **kw):
            # Phase 2 path
            return [n.match_id for n in self]
        def select_related(self, *a):
            # Phase 3 path
            return self

    class _BracketNodeObjects:
        @staticmethod
        def filter(**kw):
            # Phase 1: nodes with match__isnull=True
            if kw.get('match__isnull') is True:
                return [n for n in nodes if n.match_id is None]
            # Phase 2 + Phase 3: nodes with linked match.
            return _LinkedQS([n for n in nodes if n.match_id is not None])

    # Patch the imports inside brs.repair.
    import sys, types as _types
    fake_match_mod = _types.ModuleType('apps.tournaments.models.match')
    fake_match_mod.Match = SimpleNamespace(objects=_MatchObjects)
    monkeypatch.setitem(sys.modules,
                        'apps.tournaments.models.match', fake_match_mod)

    fake_brackets = _types.ModuleType('apps.brackets.models')
    fake_brackets.Bracket = SimpleNamespace(objects=_BracketObjects)
    fake_brackets.BracketNode = SimpleNamespace(objects=_BracketNodeObjects)
    monkeypatch.setitem(sys.modules, 'apps.brackets.models', fake_brackets)

    fake_tournament_mod = _types.ModuleType('apps.tournaments.models.tournament')
    class _TournamentClass:
        pass
    fake_tournament_mod.Tournament = _TournamentClass
    monkeypatch.setitem(sys.modules,
                        'apps.tournaments.models.tournament',
                        fake_tournament_mod)

    return brs, bracket


def _tournament(pk=1):
    return SimpleNamespace(pk=pk)


class TestParticipantBackfill:

    def test_dry_run_reports_without_writing(self, monkeypatch):
        m = _FakeMatch(id=1, participant1_id=None, participant1_name='',
                        participant2_id=None, participant2_name='')
        n = _FakeNode(match_id=1, match=m,
                       participant1_id=99, participant1_name='Tower_Tareq',
                       participant2_id=100, participant2_name='rkrashik')
        brs, _ = _make_repair_env(monkeypatch, matches=[m], nodes=[n])
        report = brs.BracketRepairService.repair(_tournament(), dry_run=True)
        assert report.participant_slots_backfilled == 2
        assert report.dry_run is True
        # No writes happened.
        assert m.save_calls == []
        assert m.participant1_id is None  # unchanged

    def test_default_backfills_empty_slots(self, monkeypatch):
        m = _FakeMatch(id=1)
        n = _FakeNode(match_id=1, match=m,
                       participant1_id=99, participant1_name='Tower_Tareq',
                       participant2_id=100, participant2_name='rkrashik')
        brs, _ = _make_repair_env(monkeypatch, matches=[m], nodes=[n])
        report = brs.BracketRepairService.repair(_tournament())
        assert report.participant_slots_backfilled == 2
        assert m.participant1_id == 99
        assert m.participant1_name == 'Tower_Tareq'
        assert m.participant2_id == 100
        assert m.participant2_name == 'rkrashik'
        assert m.save_calls  # one save with update_fields set

    def test_default_does_not_overwrite_non_empty(self, monkeypatch):
        m = _FakeMatch(id=1, participant1_id=7, participant1_name='Existing',
                        participant2_id=None, participant2_name='')
        n = _FakeNode(match_id=1, match=m,
                       participant1_id=99, participant1_name='Override',
                       participant2_id=100, participant2_name='Filler')
        brs, _ = _make_repair_env(monkeypatch, matches=[m], nodes=[n])
        report = brs.BracketRepairService.repair(_tournament())
        # Slot 1: NOT overwritten (match had data).
        assert m.participant1_id == 7
        assert m.participant1_name == 'Existing'
        # Slot 2: backfilled.
        assert m.participant2_id == 100
        assert m.participant2_name == 'Filler'
        assert report.participant_slots_backfilled == 1
        assert report.skipped_non_empty_participants == 1

    def test_force_participants_overrides_non_empty(self, monkeypatch):
        m = _FakeMatch(id=1, participant1_id=7, participant1_name='Wrong',
                        participant2_id=8, participant2_name='AlsoWrong')
        n = _FakeNode(match_id=1, match=m,
                       participant1_id=99, participant1_name='Authoritative',
                       participant2_id=100, participant2_name='Truth')
        brs, _ = _make_repair_env(monkeypatch, matches=[m], nodes=[n])
        report = brs.BracketRepairService.repair(
            _tournament(), force_participants=True,
        )
        assert m.participant1_id == 99
        assert m.participant1_name == 'Authoritative'
        assert m.participant2_id == 100
        assert m.participant2_name == 'Truth'
        assert report.participant_slots_backfilled == 2
        assert report.skipped_non_empty_participants == 0

    def test_node_with_empty_slot_does_nothing(self, monkeypatch):
        m = _FakeMatch(id=1)
        n = _FakeNode(match_id=1, match=m,
                       participant1_id=None, participant1_name='',
                       participant2_id=None, participant2_name='')
        brs, _ = _make_repair_env(monkeypatch, matches=[m], nodes=[n])
        report = brs.BracketRepairService.repair(_tournament())
        assert report.participant_slots_backfilled == 0
        assert m.save_calls == []


class TestWinnerBackfill:

    def test_winner_backfilled_when_match_has_no_winner(self, monkeypatch):
        m = _FakeMatch(id=1, participant1_id=10, participant1_name='A',
                        participant2_id=20, participant2_name='B',
                        winner_id=None)
        n = _FakeNode(match_id=1, match=m,
                       participant1_id=10, participant1_name='A',
                       participant2_id=20, participant2_name='B',
                       winner_id=20)
        brs, _ = _make_repair_env(monkeypatch, matches=[m], nodes=[n])
        report = brs.BracketRepairService.repair(_tournament())
        assert report.winners_backfilled == 1
        assert m.winner_id == 20

    def test_winner_skipped_when_not_in_participants(self, monkeypatch):
        # Node says winner=99, but neither participant ID matches → orphan
        # winner. Repair must NOT write it.
        m = _FakeMatch(id=1, participant1_id=10, participant1_name='A',
                        participant2_id=20, participant2_name='B',
                        winner_id=None)
        n = _FakeNode(match_id=1, match=m,
                       participant1_id=10, participant1_name='A',
                       participant2_id=20, participant2_name='B',
                       winner_id=99)
        brs, _ = _make_repair_env(monkeypatch, matches=[m], nodes=[n])
        report = brs.BracketRepairService.repair(_tournament())
        assert report.winners_backfilled == 0
        assert m.winner_id is None

    def test_winner_not_overwritten_when_match_has_winner(self, monkeypatch):
        m = _FakeMatch(id=1, participant1_id=10, participant1_name='A',
                        participant2_id=20, participant2_name='B',
                        winner_id=10)
        n = _FakeNode(match_id=1, match=m,
                       participant1_id=10, participant1_name='A',
                       participant2_id=20, participant2_name='B',
                       winner_id=20)
        brs, _ = _make_repair_env(monkeypatch, matches=[m], nodes=[n])
        report = brs.BracketRepairService.repair(_tournament())
        # Repair only fills empty winner_id; existing values are preserved.
        assert report.winners_backfilled == 0
        assert m.winner_id == 10

    def test_dry_run_proposed_changes_includes_winner(self, monkeypatch):
        m = _FakeMatch(id=1, participant1_id=None, participant1_name='',
                        participant2_id=None, participant2_name='',
                        winner_id=None)
        n = _FakeNode(match_id=1, match=m,
                       participant1_id=10, participant1_name='A',
                       participant2_id=20, participant2_name='B',
                       winner_id=20)
        brs, _ = _make_repair_env(monkeypatch, matches=[m], nodes=[n])
        report = brs.BracketRepairService.repair(_tournament(), dry_run=True)
        # Both slots + winner proposed; nothing written.
        assert report.dry_run is True
        assert report.participant_slots_backfilled == 2
        assert report.winners_backfilled == 1
        assert m.save_calls == []
        assert report.proposed_changes
        change_strs = ' '.join(report.proposed_changes[0]['changes'])
        assert 'participant1_id' in change_strs
        assert 'winner_id' in change_strs
