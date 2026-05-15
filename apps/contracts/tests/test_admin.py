from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite

from apps.contracts.admin import ContractEnrollmentAdmin
from apps.contracts.models import ContractEnrollment


def _admin_instance(monkeypatch):
    admin_instance = ContractEnrollmentAdmin(ContractEnrollment, AdminSite())
    monkeypatch.setattr(admin_instance, "message_user", lambda *args, **kwargs: None)
    return admin_instance


def _request():
    return SimpleNamespace(user=SimpleNamespace(username="staff", pk=1))


def _enrollment():
    return SimpleNamespace(pk="enr-1", reference_code="MS-GEN-TEST")


def test_mission_enrollment_admin_protects_lifecycle_and_escrow_fields():
    admin_instance = ContractEnrollmentAdmin(ContractEnrollment, AdminSite())

    action_names = [getattr(action, "__name__", action) for action in admin_instance.actions]
    assert "complete_selected_missions" in action_names
    assert "fail_selected_missions" in action_names
    assert "void_refund_selected_missions" in action_names
    assert "expire_overdue_missions" in action_names

    for field in [
        "status",
        "deadline_at",
        "escrow_lock_txn",
        "reward_payout_txn",
        "closure_reason",
        "closure_note",
        "resolved_at",
    ]:
        assert field in admin_instance.readonly_fields


def test_mission_admin_complete_calls_service(monkeypatch):
    admin_instance = _admin_instance(monkeypatch)
    calls = []
    monkeypatch.setattr(
        "apps.contracts.admin.ContractService.admin_complete",
        lambda **kwargs: calls.append(kwargs),
    )

    admin_instance.complete_selected_missions(_request(), [_enrollment()])

    assert calls[0]["enrollment_id"] == "enr-1"
    assert calls[0]["actor"].username == "staff"


def test_mission_admin_fail_calls_service(monkeypatch):
    admin_instance = _admin_instance(monkeypatch)
    calls = []
    monkeypatch.setattr(
        "apps.contracts.admin.ContractService.admin_fail",
        lambda **kwargs: calls.append(kwargs),
    )

    admin_instance.fail_selected_missions(_request(), [_enrollment()])

    assert calls[0]["enrollment_id"] == "enr-1"
    assert calls[0]["actor"].username == "staff"


def test_mission_admin_void_refund_calls_service(monkeypatch):
    admin_instance = _admin_instance(monkeypatch)
    calls = []
    monkeypatch.setattr(
        "apps.contracts.admin.ContractService.admin_void_refund",
        lambda **kwargs: calls.append(kwargs),
    )

    admin_instance.void_refund_selected_missions(_request(), [_enrollment()])

    assert calls[0]["enrollment_id"] == "enr-1"
    assert calls[0]["actor"].username == "staff"
