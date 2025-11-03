import pytest
from django.apps import apps
from django.db import models
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

pytestmark = pytest.mark.django_db

def _admin_request(admin_client):
    rf = RequestFactory()
    req = rf.get("/admin/")
    req.session = admin_client.session
    setattr(req, "_messages", FallbackStorage(req))
    return req

def get_admin_for(model_label):
    from django.contrib import admin
    Model = apps.get_model("tournaments", model_label)
    return admin.site._registry[Model]

def create_minimal_tournament():
    Tournament = apps.get_model("tournaments", "Tournament")
    for kwargs in (
        {"name": "Cup", "slug": "cup", "game": "valorant"},
        {"name": "Cup", "slug": "cup"},
        {"name": "Cup"},
    ):
        try:
            return Tournament.objects.create(**kwargs)
        except Exception:
            continue
    raise RuntimeError("Unable to create Tournament")

def _ensure_user_and_profile(username="payer", email="payer@example.test"):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user(username=username, password="pw123", email=email)
    p = None
    try:
        Profile = apps.get_model("user_profile", "UserProfile")
        p, _ = Profile.objects.get_or_create(user=u, defaults={"display_name": username})
    except LookupError:
        p = None
    return u, p

def _find_fk_field(model, target_label_lower_set):
    for f in model._meta.get_fields():
        if isinstance(f, models.ForeignKey):
            rel = getattr(f.remote_field, "model", None)
            if rel and getattr(rel._meta, "label_lower", "") in target_label_lower_set:
                return f.name
    return None

def create_registration(email="payer@example.test", pending=True):
    Registration = apps.get_model("tournaments", "Registration")
    t = create_minimal_tournament()
    user, profile = _ensure_user_and_profile(email=email)

    reg_kwargs = {}
    # tournament FK if exists
    t_field = _find_fk_field(Registration, {"tournaments.tournament"})
    if t_field:
        reg_kwargs[t_field] = t

    # profile/user FK if exists
    prof_field = _find_fk_field(Registration, {"user_profile.userprofile"})
    user_field = _find_fk_field(Registration, {"auth.user"})
    if prof_field and profile:
        reg_kwargs[prof_field] = profile
    elif user_field:
        reg_kwargs[user_field] = user

    # team FK if exists
    team_field = _find_fk_field(Registration, {"teams.team"})
    if team_field:
        Team = apps.get_model("teams", "Team")
        cap_field = _find_fk_field(Team, {"user_profile.userprofile"})
        team_kwargs = {"name": "PayTeam", "tag": "PAY", "slug": "payteam", "game": "valorant"}
        if cap_field and profile:
            team_kwargs[cap_field] = profile
        team = Team.objects.create(**team_kwargs)
        reg_kwargs[team_field] = team

    reg = Registration.objects.create(**reg_kwargs)

    # set pending-like state if available
    for attr in ("payment_state", "status", "state"):
        if hasattr(reg, attr):
            setattr(reg, attr, "PENDING_PAYMENT" if pending else "PAID")
            reg.save(update_fields=[attr])
            break
    return reg

def test_send_payment_reminders_sends_email(admin_client, monkeypatch):
    # Import the action and patch inside its module
    import apps.tournaments.admin.payments as payments_admin

    # Always return an email during tests
    monkeypatch.setattr(payments_admin, "_find_email_from_registration",
                        lambda reg: "payer@example.test", raising=True)

    # Count calls to send_mail IN THE MODULE (payments.py) because it imported the symbol directly
    sent = {"count": 0}
    def fake_send_mail(*args, **kwargs):
        sent["count"] += 1
        return 1
    monkeypatch.setattr(payments_admin, "send_mail", fake_send_mail, raising=True)

    from apps.tournaments.admin.payments import action_send_payment_reminders
    req = _admin_request(admin_client)
    reg = create_registration(pending=True)
    admin_obj = get_admin_for("Registration")
    qs = apps.get_model("tournaments", "Registration").objects.filter(id=reg.id)

    action_send_payment_reminders(admin_obj, req, qs)
    assert sent["count"] == 1

def test_verify_selected_marks_verified(admin_client):
    req = _admin_request(admin_client)
    reg = create_registration(pending=True)
    PV = apps.get_model("tournaments", "PaymentVerification")
    pv = PV.objects.filter(registration=reg).first()
    if not pv:
        pv_kwargs = {"registration": reg, "transaction_id": "TX999"}
        for attr in ("state", "status"):
            if hasattr(PV, attr):
                pv_kwargs[attr] = "PENDING"
                break
        pv = PV.objects.create(**pv_kwargs)
    else:
        for attr in ("state", "status"):
            if hasattr(pv, attr):
                setattr(pv, attr, "PENDING")
        pv.save()
    from django.contrib import admin
    Model = apps.get_model("tournaments", "PaymentVerification")
    admin_obj = admin.site._registry[Model]
    action = None
    for act in (admin_obj.actions or []):
        if getattr(act, "__name__", "") == "action_verify_selected":
            action = act
            break
    assert action, "Verify action not found on PaymentVerification admin"
    qs = PV.objects.filter(id=pv.id)
    action(admin_obj, req, qs)
    pv.refresh_from_db()
    state = getattr(pv, "state", getattr(pv, "status", ""))
    assert state == "VERIFIED"
