import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.corelib.models.idempotency import IdempotencyKey
from apps.tournaments.forms_registration import SoloRegistrationForm

User = get_user_model()


@pytest.mark.django_db
def test_autofill_and_idempotency(client):
    u = User.objects.create_user(username="rashik", password="x", first_name="Redwanul", last_name="Rashik")
    client.login(username="rashik", password="x")

    # GET: form should get an idempotency token + autofill display_name
    request = client.get("/").wsgi_request  # dummy request object
    request.user = u
    form = SoloRegistrationForm(request=request)  # no POST -> initial render
    assert form.fields["__idem"].initial  # token seeded
    # display_name pre-filled from get_full_name() fallback
    assert form.initial.get("display_name", "").startswith("Redwanul")

    # POST: submit once -> ok; second submit with same token -> ValidationError
    data = {"display_name": "Rashik", "contact_phone": "", "discord_tag": "", "ign": "", "__idem": form.fields["__idem"].initial}
    form2 = SoloRegistrationForm(data=data, request=request)
    assert form2.is_valid()
    # mark token as used (clean() stores it). The second clean() with same data should fail.
    form3 = SoloRegistrationForm(data=data, request=request)
    assert not form3.is_valid()
    assert any("Duplicate submission" in str(e) for e in sum(form3.errors.values(), []))
