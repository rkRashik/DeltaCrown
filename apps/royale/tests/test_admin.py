from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite

from apps.royale.admin import RoyaleEntryAdmin, RoyaleLobbyAdmin
from apps.royale.models import RoyaleEntry, RoyaleLobby


def _admin_instance(monkeypatch):
    admin_instance = RoyaleLobbyAdmin(RoyaleLobby, AdminSite())
    monkeypatch.setattr(admin_instance, "message_user", lambda *args, **kwargs: None)
    return admin_instance


def _request():
    return SimpleNamespace(user=SimpleNamespace(username="staff", pk=1))


def _lobby():
    return SimpleNamespace(pk="lob-1", reference_code="DZ-GEN-TEST")


def test_dropzone_lobby_admin_protects_lifecycle_and_escrow_fields():
    admin_instance = RoyaleLobbyAdmin(RoyaleLobby, AdminSite())

    action_names = [getattr(action, "__name__", action) for action in admin_instance.actions]
    assert "record_scores_from_entries" in action_names
    assert "settle_selected_lobbies" in action_names
    assert "cancel_refund_selected_lobbies" in action_names
    assert "mark_selected_lobbies_live" in action_names
    assert "close_selected_reservations" in action_names

    for field in [
        "status",
        "closure_reason",
        "closure_note",
        "reserved_slots_display",
        "settlement_state",
    ]:
        assert field in admin_instance.readonly_fields


def test_dropzone_entry_admin_protects_sensitive_fields_but_allows_score_input():
    admin_instance = RoyaleEntryAdmin(RoyaleEntry, AdminSite())

    for field in [
        "status",
        "escrow_lock_txn",
        "payout_txn",
        "closure_reason",
        "closure_note",
        "resolved_at",
    ]:
        assert field in admin_instance.readonly_fields
    assert "placement" not in admin_instance.readonly_fields
    assert "kills" not in admin_instance.readonly_fields


def test_dropzone_admin_settle_calls_service(monkeypatch):
    admin_instance = _admin_instance(monkeypatch)
    calls = []
    monkeypatch.setattr(
        "apps.royale.admin.RoyaleService.admin_settle_lobby",
        lambda **kwargs: calls.append(kwargs),
    )

    admin_instance.settle_selected_lobbies(_request(), [_lobby()])

    assert calls[0]["lobby_id"] == "lob-1"
    assert calls[0]["actor"].username == "staff"


def test_dropzone_admin_cancel_refund_calls_service(monkeypatch):
    admin_instance = _admin_instance(monkeypatch)
    calls = []
    monkeypatch.setattr(
        "apps.royale.admin.RoyaleService.admin_cancel_lobby",
        lambda **kwargs: calls.append(kwargs),
    )

    admin_instance.cancel_refund_selected_lobbies(_request(), [_lobby()])

    assert calls[0]["lobby_id"] == "lob-1"
    assert calls[0]["actor"].username == "staff"


def test_dropzone_admin_record_scores_calls_service(monkeypatch):
    admin_instance = _admin_instance(monkeypatch)
    calls = []
    monkeypatch.setattr(
        "apps.royale.admin.RoyaleService.admin_record_scores_from_entries",
        lambda **kwargs: calls.append(kwargs),
    )

    admin_instance.record_scores_from_entries(_request(), [_lobby()])

    assert calls[0]["lobby_id"] == "lob-1"
    assert calls[0]["actor"].username == "staff"
