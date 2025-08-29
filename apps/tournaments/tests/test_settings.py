# apps/tournaments/tests/test_settings.py
import pytest
from datetime import timedelta
from django.utils import timezone
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model


def _create_tournament(**overrides):
    """
    Create a Tournament instance while adapting to your actual field names.
    Sets a consistent timeline:
      reg_open_at = now
      reg_close_at = now + 1h
      start_at = reg_close_at + 1h
      end_at = start_at + 2h
    """
    from apps.tournaments.models import Tournament

    field_names = {f.name for f in Tournament._meta.get_fields()}
    data = {}

    # Name/slug
    now = timezone.now()
    ts = str(now.timestamp()).replace(".", "")
    data["name"] = overrides.get("name", f"DC Open {ts}")
    if "slug" in field_names:
        data["slug"] = overrides.get("slug", f"dc-open-{ts}")

    # Timeline
    reg_open = overrides.get("reg_open_at", now)
    reg_close = overrides.get("reg_close_at", reg_open + timedelta(hours=1))
    start = overrides.get("start_at", reg_close + timedelta(hours=1))
    end = overrides.get("end_at", start + timedelta(hours=2))

    if "reg_open_at" in field_names:
        data["reg_open_at"] = reg_open
    if "reg_close_at" in field_names:
        data["reg_close_at"] = reg_close

    if "start_at" in field_names:
        data["start_at"] = start
    elif "start_date" in field_names:
        data["start_date"] = start

    if "end_at" in field_names:
        data["end_at"] = end
    elif "end_date" in field_names:
        data["end_date"] = end

    # Slots
    if "slot_size" in field_names:
        data["slot_size"] = overrides.get("slot_size", 8)

    # Status
    if "status" in field_names:
        data["status"] = overrides.get("status", "draft")

    # Monetary: entry fee
    for fee_field in ("entry_fee_bdt", "entry_fee", "fee"):
        if fee_field in field_names:
            data[fee_field] = overrides.get(fee_field, 0)
            break

    # Monetary: prize pool
    for pool_field in ("prize_pool_bdt", "prize_pool", "pool"):
        if pool_field in field_names:
            data[pool_field] = overrides.get(pool_field, 0)
            break

    # Optional created_by FK
    if "created_by" in field_names:
        User = get_user_model()
        creator = overrides.get("created_by")
        if creator is None:
            creator = User.objects.create_user(username=f"creator_{ts}")
        data["created_by"] = creator

    return Tournament.objects.create(**data)


@pytest.mark.django_db
def test_settings_autocreated_on_tournament_create():
    from apps.tournaments.models import TournamentSettings
    t = _create_tournament(name="DC Open (auto settings)")
    assert TournamentSettings.objects.filter(tournament=t).exists(), "TournamentSettings was not auto-created"


@pytest.mark.django_db
def test_settings_defaults_and_file_upload():
    from apps.tournaments.models import TournamentSettings
    t = _create_tournament(name="DC Masters (defaults)")
    s = t.settings  # auto-created by signal

    # Defaults (assert only if the field exists)
    if hasattr(s, "bracket_visibility"):
        assert s.bracket_visibility == "public"
    if hasattr(s, "check_in_open_mins"):
        assert s.check_in_open_mins == 60
    if hasattr(s, "check_in_close_mins"):
        assert s.check_in_close_mins == 15

    # Upload a small PDF
    if hasattr(s, "rules_pdf"):
        pdf = SimpleUploadedFile("rules.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        s.rules_pdf = pdf
        s.save()
        assert s.rules_pdf.name.endswith(".pdf")
