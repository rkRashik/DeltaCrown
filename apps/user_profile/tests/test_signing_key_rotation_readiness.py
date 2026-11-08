"""OL-02B: signing-key / field-encryption rotation readiness, with synthetic keys only.

These tests prove the code foundation. They say nothing about the real production configuration.
"""
import logging

import jwt
import pytest
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core import signing
from django.core.exceptions import ImproperlyConfigured
from django.db.models import TextField
from django.db.models.functions import Cast
from django.test import Client, override_settings
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.exceptions import TokenBackendError

from deltacrown.key_config import parse_key_list
from apps.user_profile import checks
from apps.user_profile.fields import (
    EncryptedTextField,
    UndecryptableToken,
    classify_stored_value,
    derive_key_from_secret,
)
from apps.user_profile.models.oauth import GameOAuthConnection

OLD_SECRET = "synthetic-old-signing-key-for-tests-0123456789-abcdefghijklmnop"
NEW_SECRET = "synthetic-new-signing-key-for-tests-9876543210-zyxwvutsrqponmlk"
PRIMARY = Fernet.generate_key().decode()  # synthetic primary field-encryption key
TOKEN = "synthetic-provider-token-value"
field = EncryptedTextField()

BEFORE = dict(SECRET_KEY=OLD_SECRET, FIELD_ENCRYPTION_KEY=None, FIELD_ENCRYPTION_LEGACY_SECRET_KEYS=[], FIELD_ENCRYPTION_LEGACY_KEYS=[])
AFTER = dict(SECRET_KEY=NEW_SECRET, FIELD_ENCRYPTION_KEY=PRIMARY, FIELD_ENCRYPTION_LEGACY_SECRET_KEYS=[OLD_SECRET], FIELD_ENCRYPTION_LEGACY_KEYS=[])


def legacy_ciphertext(value=TOKEN, secret=OLD_SECRET):
    """What production rows look like today: Fernet under the key derived from the old SECRET_KEY."""
    return Fernet(derive_key_from_secret(secret)).encrypt(value.encode()).decode()


def read(stored):
    return field.from_db_value(stored, None, None)


def raw_column(pk, column):
    """The stored (still encrypted) column value, bypassing the field's decryption."""
    return GameOAuthConnection.objects.annotate(r=Cast(column, TextField())).values_list("r", flat=True).get(pk=pk)


# ---------------------------------------------------------------- field encryption
@override_settings(**AFTER)
def test_legacy_ciphertext_stays_readable_after_rotation():
    assert read(legacy_ciphertext()) == TOKEN


@override_settings(**AFTER)
def test_new_ciphertext_uses_only_the_primary_key():
    stored = field.get_prep_value(TOKEN)
    assert Fernet(PRIMARY.encode()).decrypt(stored.encode()).decode() == TOKEN
    for unrelated in (derive_key_from_secret(OLD_SECRET), derive_key_from_secret(NEW_SECRET)):
        with pytest.raises(Exception):
            Fernet(unrelated).decrypt(stored.encode())


@override_settings(**BEFORE)
def test_default_configuration_is_unchanged_and_backward_compatible():
    stored = field.get_prep_value(TOKEN)
    assert Fernet(derive_key_from_secret(OLD_SECRET)).decrypt(stored.encode()).decode() == TOKEN
    assert read(stored) == TOKEN and read("legacy plaintext") == "legacy plaintext"
    assert read(None) is None and read("") == ""


@override_settings(SECRET_KEY=NEW_SECRET, FIELD_ENCRYPTION_KEY=None, FIELD_ENCRYPTION_LEGACY_SECRET_KEYS=[], FIELD_ENCRYPTION_LEGACY_KEYS=[])
def test_blind_rotation_is_not_silent_and_never_returns_or_re_encrypts_ciphertext(caplog):
    stored = legacy_ciphertext()
    with caplog.at_level(logging.WARNING):
        value = read(stored)
    assert isinstance(value, UndecryptableToken) and value == "" and not value
    assert stored not in repr(value) and stored not in caplog.text and TOKEN not in caplog.text
    # saving the model value writes the original bytes back: no double encryption, nothing lost
    assert field.get_prep_value(value) == stored


@override_settings(**AFTER)
def test_repeated_saves_never_nest_or_corrupt_values():
    stored = legacy_ciphertext()
    for _ in range(5):
        value = read(stored)
        assert value == TOKEN
        stored = field.get_prep_value(value)
    assert Fernet(PRIMARY.encode()).decrypt(stored.encode()).decode() == TOKEN  # single layer, primary key
    assert read(stored) == TOKEN


@override_settings(**AFTER)
def test_plaintext_rows_are_read_and_encrypted_on_save():
    assert read("legacy plaintext") == "legacy plaintext"
    assert classify_stored_value(field.get_prep_value("legacy plaintext")) == "primary"


@override_settings(**AFTER)
def test_status_classification_is_value_free():
    assert classify_stored_value(None) == classify_stored_value("") == "empty"
    assert classify_stored_value(field.get_prep_value(TOKEN)) == "primary"
    assert classify_stored_value(legacy_ciphertext()) == "legacy"
    assert classify_stored_value("legacy plaintext") == "plaintext"
    assert classify_stored_value(legacy_ciphertext(secret="synthetic-unknown-key-0123456789-abcdefghijklmnopqrstuv")) == "undecryptable"


def test_rollback_restores_access_without_data_loss():
    with override_settings(**AFTER):
        stored = field.get_prep_value(TOKEN)  # written by the rotated configuration
    with override_settings(**BEFORE):  # rolled back to the old signing key and no pinned key
        value = read(stored)
        assert isinstance(value, UndecryptableToken)
        assert field.get_prep_value(value) == stored  # untouched even if the row is saved
    with override_settings(**{**AFTER, "SECRET_KEY": OLD_SECRET}):  # only the signing key rolled back
        assert read(stored) == TOKEN  # field encryption is independent of SECRET_KEY


@pytest.mark.parametrize("overrides", [
    {"FIELD_ENCRYPTION_KEY": "not-a-fernet-key-SENTINEL-VALUE"},
    {"FIELD_ENCRYPTION_LEGACY_KEYS": ["short-SENTINEL-VALUE"]},
    {"FIELD_ENCRYPTION_LEGACY_SECRET_KEYS": "a-string-not-a-list-SENTINEL-VALUE"},
    {"FIELD_ENCRYPTION_LEGACY_SECRET_KEYS": ["", "x"]},
])
def test_malformed_configuration_fails_safely_without_echoing_values(overrides):
    with override_settings(**{**AFTER, **overrides}):
        with pytest.raises(ImproperlyConfigured) as caught:
            field.get_prep_value(TOKEN)
        assert "SENTINEL-VALUE" not in str(caught.value)
        found = checks.field_encryption_configuration(None)
        assert [m.id for m in found] == ["user_profile.E001"] and "SENTINEL-VALUE" not in found[0].msg


@override_settings(**AFTER)
def test_checks_report_legacy_and_fallback_state_in_deploy_mode():
    with override_settings(SECRET_KEY_FALLBACKS=[OLD_SECRET]):
        ids = {m.id for m in checks.field_encryption_key_is_separate(None)}
    assert ids == {"user_profile.W002", "user_profile.W003"}
    with override_settings(FIELD_ENCRYPTION_KEY=None, FIELD_ENCRYPTION_LEGACY_SECRET_KEYS=[], SECRET_KEY_FALLBACKS=[]):
        assert [m.id for m in checks.field_encryption_key_is_separate(None)] == ["user_profile.W001"]


# ---------------------------------------------------------------- key list parsing
def test_key_lists_are_empty_by_default_and_validated():
    from django.conf import settings
    assert settings.SECRET_KEY_FALLBACKS == [] and settings.FIELD_ENCRYPTION_LEGACY_SECRET_KEYS == []
    assert parse_key_list(None, "X") == parse_key_list("  ", "X") == []
    assert parse_key_list('["a-key", "a-key", "b-key"]', "X") == ["a-key", "b-key"]
    assert parse_key_list('["current", "old"]', "X", current="current") == ["old"]
    for bad in ("SENTINEL-key", '{"k": 1}', '["SENTINEL-ok", 5]', '[""]', '["a","b","c","d","e","f"]'):
        with pytest.raises(ImproperlyConfigured) as caught:
            parse_key_list(bad, "X")
        assert "SENTINEL" not in str(caught.value)


# ---------------------------------------------------------------- Django signing vs JWT
def test_django_signed_payloads_follow_the_configured_fallback_policy():
    with override_settings(SECRET_KEY=OLD_SECRET, SECRET_KEY_FALLBACKS=[]):
        token = signing.dumps("editor/abc.png", salt="published-editor-image")
    with override_settings(SECRET_KEY=NEW_SECRET, SECRET_KEY_FALLBACKS=[]):
        with pytest.raises(signing.BadSignature):
            signing.loads(token, salt="published-editor-image")
    with override_settings(SECRET_KEY=NEW_SECRET, SECRET_KEY_FALLBACKS=[OLD_SECRET]):
        assert signing.loads(token, salt="published-editor-image") == "editor/abc.png"
        assert signing.loads(signing.dumps("x", salt="s"), salt="s") == "x"  # new signatures use the new key
        with pytest.raises(signing.BadSignature):
            signing.loads(signing.dumps("x", salt="s") + "tamper", salt="s")


@pytest.mark.parametrize("fallbacks", [[], [OLD_SECRET]])
def test_jwt_is_not_covered_by_django_fallbacks_and_needs_reauthentication(fallbacks):
    claims = {"user_id": "42", "token_type": "access", "exp": 4102444800, "iat": 1700000000, "jti": "synthetic"}
    old_token = TokenBackend("HS256", OLD_SECRET).encode(claims)
    with override_settings(SECRET_KEY=NEW_SECRET, SECRET_KEY_FALLBACKS=fallbacks):
        with pytest.raises(TokenBackendError):
            TokenBackend("HS256", NEW_SECRET).decode(old_token)
        fresh = TokenBackend("HS256", NEW_SECRET).encode(claims)
        assert TokenBackend("HS256", NEW_SECRET).decode(fresh)["user_id"] == "42"
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(old_token, NEW_SECRET, algorithms=["HS256"])


def test_simplejwt_signing_key_still_follows_secret_key():
    from django.conf import settings
    assert settings.SIMPLE_JWT["SIGNING_KEY"] == settings.SECRET_KEY  # unchanged on purpose


# ---------------------------------------------------------------- database-backed behavior
@pytest.mark.django_db
def test_oauth_connection_round_trip_across_rotation_and_repeated_saves():
    with override_settings(**BEFORE):
        conn = GameOAuthConnection.objects.create(provider="riot", access_token=TOKEN, refresh_token="synthetic-refresh")
        legacy_access = raw_column(conn.pk, "access_token")
    with override_settings(**AFTER):
        assert classify_stored_value(legacy_access) == "legacy"
        loaded = GameOAuthConnection.objects.get(pk=conn.pk)
        assert (loaded.access_token, loaded.refresh_token) == (TOKEN, "synthetic-refresh")
        for _ in range(3):  # repeated saves re-encrypt once under the primary key and then stay stable
            loaded.save()
            loaded = GameOAuthConnection.objects.get(pk=conn.pk)
            assert loaded.access_token == TOKEN
        stored = raw_column(conn.pk, "access_token")
        assert classify_stored_value(stored) == "primary"
        assert Fernet(PRIMARY.encode()).decrypt(stored.encode()).decode() == TOKEN


@pytest.mark.django_db
def test_unreadable_row_is_preserved_by_unrelated_saves():
    with override_settings(**AFTER):
        conn = GameOAuthConnection.objects.create(provider="riot", access_token=TOKEN)
        stored = raw_column(conn.pk, "access_token")
    with override_settings(**BEFORE):  # a rolled-back or misconfigured instance
        loaded = GameOAuthConnection.objects.get(pk=conn.pk)
        assert loaded.access_token == "" and not loaded.access_token
        loaded.scopes = "read"
        loaded.save()
        assert raw_column(conn.pk, "access_token") == stored
    with override_settings(**AFTER):
        assert GameOAuthConnection.objects.get(pk=conn.pk).access_token == TOKEN


@pytest.mark.django_db
def test_sessions_follow_the_signing_key_policy():
    user = get_user_model().objects.create_user(username="rot-user", email="rot@example.test", password="synthetic-pass-123")
    with override_settings(SECRET_KEY=OLD_SECRET, SECRET_KEY_FALLBACKS=[]):
        client = Client()
        client.force_login(user)
        assert client.get("/tournaments/my/", secure=True).status_code == 200
        session_id = client.cookies["sessionid"].value

    def status(**overrides):
        with override_settings(**overrides):
            fresh = Client()
            fresh.cookies["sessionid"] = session_id
            return fresh.get("/tournaments/my/", secure=True).status_code

    assert status(SECRET_KEY=NEW_SECRET, SECRET_KEY_FALLBACKS=[]) == 302  # logged out: rotation without fallback
    assert status(SECRET_KEY=NEW_SECRET, SECRET_KEY_FALLBACKS=[OLD_SECRET]) == 200  # preserved by the fallback
