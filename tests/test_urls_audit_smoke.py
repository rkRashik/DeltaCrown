import io
import pytest
from django.core.management import call_command

pytestmark = pytest.mark.django_db

def test_urls_audit_runs_and_prints(client):
    out = io.StringIO()
    err = io.StringIO()
    # We don't assert "all good" because projects vary; we just assert the command runs
    call_command("urls_audit", stdout=out, stderr=err)
    text = out.getvalue()
    assert "URL reverse audit" in text
    assert "Template render audit" in text
