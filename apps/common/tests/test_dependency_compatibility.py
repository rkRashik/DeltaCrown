"""Bounded security-upgrade regressions; all identities and files are synthetic."""
from decimal import Decimal
from io import BytesIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
from PIL import Image, ImageOps, UnidentifiedImageError
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.contrib.sessions.backends.db import SessionStore
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse


FIXTURE = json.loads((Path(__file__).parent / "fixtures/dependency_legacy.json").read_text(encoding="utf-8"))
TEST_KEY = "local-dependency-compatibility-key-not-for-production"


@override_settings(SECRET_KEY=TEST_KEY, FIELD_ENCRYPTION_KEY=None)
class LegacyAuthenticationCompatibilityTests(SimpleTestCase):
    def test_existing_encrypted_field_can_still_be_read(self):
        from apps.user_profile.fields import EncryptedTextField
        field = EncryptedTextField()
        self.assertEqual(field.from_db_value(FIXTURE["encrypted_provider_token"], None, None), "qa-provider-token")
        self.assertEqual(field.from_db_value("legacy plaintext", None, None), "legacy plaintext")

    def test_existing_hs256_access_token_remains_valid(self):
        payload = jwt.decode(FIXTURE["access_token"], TEST_KEY, algorithms=["HS256"])
        self.assertEqual(payload["user_id"], "42")
        self.assertEqual(payload["token_type"], "access")

    def test_wrong_signature_and_algorithm_remain_rejected(self):
        with self.assertRaises(jwt.InvalidSignatureError):
            jwt.decode(FIXTURE["access_token"], "another-test-key-that-is-not-the-signing-key", algorithms=["HS256"])
        with self.assertRaises(jwt.InvalidAlgorithmError):
            jwt.decode(FIXTURE["access_token"], TEST_KEY, algorithms=["HS384"])

    def test_malformed_claim_raises_a_token_error(self):
        token = jwt.encode({"exp": []}, TEST_KEY, algorithm="HS256")
        with self.assertRaises(jwt.InvalidTokenError):
            jwt.decode(token, TEST_KEY, algorithms=["HS256"])

    @override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.PBKDF2PasswordHasher"])
    def test_existing_session_and_password_hash_remain_valid(self):
        self.assertEqual(SessionStore().decode(FIXTURE["session"])["_auth_user_id"], "42")
        self.assertTrue(check_password("local-qa-password", FIXTURE["password_hash"]))
        self.assertFalse(check_password("wrong-password", FIXTURE["password_hash"]))


class MediaDocumentCompatibilityTests(SimpleTestCase):
    def image_bytes(self, format):
        output = BytesIO()
        Image.new("RGB", (64, 64), (226, 183, 97)).save(output, format=format)
        return output.getvalue()

    def test_supported_upload_formats_validate_and_transform(self):
        from apps.common.validators import validate_image_upload
        for format, mime in [("PNG", "image/png"), ("JPEG", "image/jpeg"), ("WEBP", "image/webp")]:
            with self.subTest(format=format):
                upload = SimpleUploadedFile("qa."+format.lower(), self.image_bytes(format), content_type=mime)
                validate_image_upload(upload)
                with Image.open(upload) as image:
                    result = ImageOps.exif_transpose(image).convert("RGB")
                    result.thumbnail((32, 32), Image.Resampling.LANCZOS)
                    output = BytesIO()
                    result.save(output, format="PNG")
                with Image.open(BytesIO(output.getvalue())) as decoded:
                    self.assertEqual(decoded.size, (32, 32))

    def test_small_malformed_image_is_rejected(self):
        with self.assertRaises(UnidentifiedImageError):
            Image.open(BytesIO(b"not an image"))

    def test_svg_rendering_and_entity_rejection(self):
        try:
            import cairosvg
        except OSError as exc:
            self.skipTest("Cairo native runtime unavailable on this host: " + str(exc).splitlines()[0])
        from defusedxml.common import EntitiesForbidden
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="#E2B761"/></svg>'
        with Image.open(BytesIO(cairosvg.svg2png(bytestring=svg))) as image:
            self.assertEqual(image.convert("RGB").getpixel((1, 1)), (226, 183, 97))
        entity = b'<!DOCTYPE svg [<!ENTITY qa "bounded-test">]><svg xmlns="http://www.w3.org/2000/svg"><text>&qa;</text></svg>'
        with self.assertRaises(EntitiesForbidden):
            cairosvg.svg2png(bytestring=entity)

    def test_pdf_reader_and_rules_importer_use_maintained_package(self):
        from reportlab.pdfgen.canvas import Canvas
        from apps.tournaments.utils.rules_importer import _load_pdf_reader_class, import_rules_from_pdf, preview_pdf_text
        reader_class = _load_pdf_reader_class()
        self.assertEqual(reader_class.__module__.split(".")[0], "pypdf")
        output = BytesIO()
        canvas = Canvas(output)
        canvas.drawString(40, 800, "OwnLobby local QA tournament rules")
        canvas.save()
        self.assertIn("OwnLobby", reader_class(BytesIO(output.getvalue())).pages[0].extract_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "rules.pdf"
            path.write_bytes(output.getvalue())
            tournament = SimpleNamespace(id=1, rules_pdf=SimpleNamespace(path=str(path), name="rules.pdf"), rules_text="", save=Mock())
            self.assertIn("OwnLobby", import_rules_from_pdf(tournament))
            tournament.save.assert_called_once_with(update_fields=["rules_text"])
            self.assertIn("OwnLobby", preview_pdf_text(tournament))

    def test_bounded_invalid_pdf_is_rejected(self):
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
        with self.assertRaises(PdfReadError):
            PdfReader(BytesIO(b"%PDF-1.4\ninvalid bounded fixture\n%%EOF"))


class BackgroundSerializationCompatibilityTests(SimpleTestCase):
    def test_redis_channel_layer_serialization_round_trip(self):
        from channels_redis.core import RedisChannelLayer
        # Serialization only: no connection to any Redis server is made.
        layer = RedisChannelLayer(hosts=[("127.0.0.1", 6399)])
        message = {"type": "score_updated", "data": {"match_id": 7, "score": 2}}
        self.assertEqual(layer.deserialize(layer.serialize(message)), message)

    def test_celery_json_retains_decimal_and_identifiers(self):
        from kombu.serialization import dumps, loads
        message = {"amount": Decimal("125.25"), "currency": "DeltaCoin", "tournament_id": 7}
        content_type, encoding, body = dumps(message, serializer="json")
        self.assertEqual(loads(body, content_type, encoding, accept={content_type}), message)

    def test_memory_broker_delivers_json(self):
        from kombu import Connection, Exchange, Queue
        queue = Queue("dependency-qa", Exchange("dependency-qa"), routing_key="qa")
        received = []
        with Connection("memory://") as connection:
            with connection.Consumer(queue, callbacks=[lambda body, message: (received.append(body), message.ack())], accept=["json"]):
                connection.Producer(serializer="json").publish({"tournament_id": 7}, exchange=queue.exchange, routing_key="qa", declare=[queue])
                connection.drain_events(timeout=2)
        self.assertEqual(received, [{"tournament_id": 7}])


class UploadEndpointCompatibilityTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("dependency_upload_qa", "dependency-upload@example.com", "local-qa-password")
        self.client.force_login(self.user)

    def test_invalid_upload_is_rejected_by_the_existing_endpoint(self):
        upload = SimpleUploadedFile("bad.png", b"not an image", content_type="image/png")
        response = self.client.post(reverse("user_profile:upload_media"), {"media_type": "avatar", "file": upload})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])

    def test_upload_endpoint_still_requires_authentication(self):
        self.client.logout()
        response = self.client.post(reverse("user_profile:upload_media"), {})
        self.assertEqual(response.status_code, 302)
