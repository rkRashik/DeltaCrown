"""Synthetic-only media privacy, remote backend and migration regressions."""

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from datetime import timedelta

from PIL import Image
from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import FileField, ImageField
from django.test import TransactionTestCase, SimpleTestCase, override_settings
from django.utils import timezone

from apps.common.media.fields import MediaFileField, MediaImageField
from apps.common.media.policy import match_participant, storage_alias, can_download
from apps.common.media.storage import ProtectedS3Storage
from apps.common.media.configuration import configure
from scripts.media_transfer import make_plan, copy_verified, checksum


def image(name="synthetic.png"):
    output = BytesIO()
    Image.new("RGB", (64, 64), "white").save(output, "PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


class MediaPrivacyTests(TransactionTestCase):
    def setUp(self):
        self.temp = TemporaryDirectory(dir=Path("Artifacts/final-engineering"))
        self.addCleanup(self.temp.cleanup)
        config = {
            k: v
            for k, v in __import__("django.conf", fromlist=["settings"]).settings.STORAGES.items()
        }
        for category in ("public", "private"):
            config[category + "_media"] = {
                "BACKEND": "apps.common.media.storage.ProtectedFileSystemStorage",
                "OPTIONS": {"location": str(Path(self.temp.name) / category)},
            }
        config["default"] = config["private_media"]
        self.override = override_settings(OWNLOBBY_MEDIA_MODE="local", STORAGES=config)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.owner = get_user_model().objects.create_user(
            "media-owner", "owner@example.invalid", "synthetic-pass"
        )
        self.other = get_user_model().objects.create_user(
            "media-other", "other@example.invalid", "synthetic-pass"
        )
        VerificationRecord = apps.get_model("user_profile.VerificationRecord")
        self.record, _ = VerificationRecord.objects.get_or_create(user_profile=self.owner.profile)
        self.record.id_document_front.save("synthetic.png", image(), save=True)
        self.blob = self.record.id_document_front

    def test_private_url_authorizes_each_request_not_bearer_possession(self):
        url = self.blob.url
        self.assertTrue(url.startswith("/files/user_profile.verificationrecord/"))
        for user in (None, self.other):
            self.client.logout()
            if user:
                self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), image().read())
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        response.close()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_hybrid_preserves_private_record_authorization(self):
        with override_settings(OWNLOBBY_MEDIA_MODE="hybrid"):
            self.test_private_url_authorizes_each_request_not_bearer_possession()
            self.test_no_raw_url_or_public_bucket_copy_for_evidence()
            self.test_staff_without_model_permission_cannot_read_kyc()

    def test_hybrid_profile_privacy_uses_private_origin(self):
        with override_settings(OWNLOBBY_MEDIA_MODE="hybrid"):
            # Reload fields created under the local-mode fixture, as at process startup.
            self.owner = get_user_model().objects.get(pk=self.owner.pk)
            self.test_private_profile_asset_requires_owner_or_approved_follower()
            self.assertTrue(storages["private_media"].exists(self.owner.profile.avatar.name))
            self.assertFalse(storages["public_media"].exists(self.owner.profile.avatar.name))

    def test_staff_without_model_permission_cannot_read_kyc(self):
        from apps.accounts.roles import STAFF_GROUP_NAMES

        group, _ = Group.objects.get_or_create(name=sorted(STAFF_GROUP_NAMES)[0])
        self.other.groups.add(group)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.blob.url).status_code, 404)
        permission = Permission.objects.get(
            content_type__app_label="user_profile", codename="view_verificationrecord"
        )
        self.other.user_permissions.add(permission)
        response = self.client.get(self.blob.url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_no_raw_url_or_public_bucket_copy_for_evidence(self):
        with self.assertRaises(ValueError):
            self.blob.storage.url(self.blob.name)
        self.assertFalse(storages["public_media"].exists(self.blob.name))
        self.assertEqual(self.client.get("/media/" + self.blob.name).status_code, 404)

    def test_storage_failure_is_retryable_without_fallback(self):
        self.client.force_login(self.owner)
        with patch(
            "apps.common.media.storage.ProtectedFileSystemStorage._open",
            side_effect=OSError("synthetic unavailable"),
        ):
            response = self.client.get(self.blob.url)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response["Retry-After"], "30")
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_direct_save_rejects_spoof_and_keeps_original(self):
        old = self.blob.name
        with self.assertRaises(ValidationError):
            self.blob.save("fake.png", ContentFile(b"<html>not an image</html>"), save=False)
        self.assertTrue(storages["private_media"].exists(old))
        self.assertEqual(self.blob.name, old)

    def test_decode_and_extension_validation(self):
        for name, content in [
            ("fake.jpg", image().read()),
            ("fake.png", b"\x89PNG\r\n\x1a\ntruncated"),
        ]:
            with self.subTest(name=name), self.assertRaises(ValidationError):
                self.blob.save(name, ContentFile(content), save=False)

    def test_valid_public_image_read_then_withdraw_and_delete(self):
        from apps.games.models import Game

        game = Game.objects.create(
            name="Synthetic Media",
            slug="synthetic-media",
            short_code="SMED",
            display_name="Synthetic",
            category="FPS",
            game_type="TEAM_VS_TEAM",
            is_active=True,
            icon=image(),
        )
        key = game.icon.name
        self.assertTrue(storages["public_media"].exists(key))
        response = self.client.get(game.icon.url)
        self.assertEqual(response.status_code, 200)
        response.close()
        game.is_active = False
        game.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(game.icon.url).status_code, 404)
        game.icon.delete(save=False)
        self.assertFalse(storages["public_media"].exists(key))

    def test_unknown_fields_and_invalid_ids_fail_closed(self):
        self.assertEqual(
            self.client.get("/files/user_profile.verificationrecord/no_such_field/1/").status_code,
            404,
        )
        self.assertEqual(
            self.client.get(
                "/files/user_profile.verificationrecord/id_document_front/invalid/"
            ).status_code,
            404,
        )

    def test_draft_rules_only_owner_and_valid_pdf_workflow(self):
        from apps.tournaments.models import Tournament
        from apps.games.models import Game
        from reportlab.pdfgen import canvas

        game = Game.objects.create(
            name="Rules",
            slug="rules",
            short_code="RULE",
            display_name="Rules",
            category="FPS",
            game_type="TEAM_VS_TEAM",
        )
        now = timezone.now()
        tournament = Tournament.objects.create(
            name="Synthetic Draft",
            slug="synthetic-draft",
            description="Synthetic",
            organizer=self.owner,
            game=game,
            max_participants=16,
            registration_start=now,
            registration_end=now + timedelta(days=1),
            tournament_start=now + timedelta(days=2),
            status="draft",
        )
        output = BytesIO()
        pdf = canvas.Canvas(output)
        pdf.drawString(20, 20, "Synthetic rules")
        pdf.save()
        tournament.rules_pdf.save("rules.pdf", ContentFile(output.getvalue()), save=True)
        self.assertEqual(storage_alias(tournament._meta.get_field("rules_pdf")), "private_media")
        self.assertEqual(self.client.get(tournament.rules_pdf.url).status_code, 404)
        self.client.force_login(self.owner)
        response = self.client.get(tournament.rules_pdf.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response["Content-Disposition"])
        response.close()
        tournament.status = "published"
        tournament.save(update_fields=["status"])
        self.client.logout()
        response = self.client.get(tournament.rules_pdf.url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_editor_only_publishes_valid_images_no_private_origin_urls(self):
        from apps.common.media.editor import EditorStorage

        editor = EditorStorage()
        key = editor.save("synthetic.png", image())
        self.assertTrue(key.startswith("editor/"))
        response = self.client.get(editor.url(key))
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(
            self.client.get(editor.url(key).rstrip("/") + "tampered/").status_code, 404
        )
        with self.assertRaises(ValidationError):
            editor.save("bad.svg", ContentFile(b"<svg/>", name="bad.svg"))

    def test_certificate_generated_contentfile_without_name(self):
        Certificate = apps.get_model("user_profile.Certificate")
        certificate = Certificate(user=self.owner)
        certificate.image.save("certificate.png", ContentFile(image().read()), save=False)
        self.assertTrue(storages["private_media"].exists(certificate.image.name))

    def test_profile_replacement_failure_preserves_previous_bytes_and_reference(self):
        profile = self.owner.profile
        profile.avatar.save("old.png", image(), save=True)
        original = profile.avatar.name
        self.client.force_login(self.owner)
        with patch.object(type(profile), "save", side_effect=RuntimeError("synthetic DB failure")):
            response = self.client.post(
                "/me/settings/media/", {"media_type": "avatar", "file": image()}
            )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"], "Failed to save file")
        self.assertTrue(storages["public_media"].exists(original))
        profile.refresh_from_db()
        self.assertEqual(profile.avatar.name, original)

    def test_private_profile_asset_requires_owner_or_approved_follower(self):
        profile = self.owner.profile
        profile.avatar.save("avatar.png", image(), save=True)
        privacy = profile.privacy_settings
        privacy.is_private_account = True
        privacy.save(update_fields=["is_private_account"])
        self.assertEqual(self.client.get(profile.avatar.url).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(profile.avatar.url).status_code, 404)
        apps.get_model("user_profile.Follow").objects.create(
            follower=self.other, following=self.owner
        )
        response = self.client.get(profile.avatar.url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_all_53_fields_have_explicit_runtime_classes_and_stable_migration_types(self):
        import json

        rows = json.loads(Path("branding/media-storage-inventory.json").read_text())["fields"]
        seen = set()
        for row in rows:
            key = (row["concrete_model"], row["field"])
            if key in seen:
                continue
            seen.add(key)
            field = apps.get_model(key[0])._meta.get_field(key[1])
            self.assertIsInstance(field, (MediaFileField, MediaImageField))
            _, path, args, kwargs = field.deconstruct()
            self.assertIn(path, {"django.db.models.FileField", "django.db.models.ImageField"})
            builtin = ImageField if isinstance(field, ImageField) else FileField
            self.assertEqual(builtin(*args, **kwargs).deconstruct()[1:], (path, args, kwargs))
        self.assertEqual(len(seen), 53)


class RemoteAndMigrationTests(SimpleTestCase):
    def test_real_s3_adapter_uses_private_parameters_and_no_public_or_signed_urls(self):
        storage = ProtectedS3Storage(
            bucket_name="synthetic-bucket", access_key="synthetic", secret_key="synthetic"
        )
        data = {}
        params = {}

        class Object:
            content_encoding = None

            def __init__(self, name):
                self.name = name

            @property
            def content_length(self):
                return len(data[self.name])

            def load(self, **kwargs):
                pass

            def upload_fileobj(self, body, ExtraArgs, Config):
                data[self.name] = body.read()
                params.update(ExtraArgs)

            def download_fileobj(self, body, **kwargs):
                body.write(data[self.name])

            def delete(self):
                data.pop(self.name, None)

        storage._bucket = SimpleNamespace(Object=Object)
        with patch.object(storage, "exists", side_effect=lambda name: name in data):
            key = storage.save("synthetic/image.png", ContentFile(image().read()))
        with storage.open(key, "rb") as stream:
            self.assertEqual(stream.read(), image().read())
        self.assertNotIn("ACL", params)
        self.assertEqual(params["CacheControl"], "private, no-store")
        with self.assertRaises(ValueError):
            storage.url(key)
        storage.delete(key)
        self.assertNotIn(key, data)

    def test_sdk_retries_are_bounded_and_never_change_to_public_fallback(self):
        with patch.dict("os.environ", {"OWNLOBBY_MEDIA_MODE": "s3"}):
            config = {}
            self.assertEqual(configure(config, Path("."), Path("media")), "s3")
        for alias in ("public_media", "private_media"):
            options = config[alias]["OPTIONS"]
            retries = options["client_config"].retries
            self.assertEqual(retries, {"mode": "standard", "total_max_attempts": 3})
            self.assertTrue(options["querystring_auth"])
            self.assertIsNone(options["custom_domain"])

    def test_participant_identity_namespaces_do_not_cross(self):
        user = SimpleNamespace(is_authenticated=True, pk=7)
        match = SimpleNamespace(
            participant1_id=7,
            participant2_id=9,
            tournament=SimpleNamespace(participation_type="team"),
        )
        with patch("apps.common.media.policy.apps.get_model") as registry:
            registry.return_value.objects.filter.return_value.exists.return_value = False
            self.assertFalse(match_participant(user, match))
        match.tournament.participation_type = "solo"
        self.assertTrue(match_participant(user, match))
        match.tournament.participation_type = "unknown"
        self.assertFalse(match_participant(user, match))

    def test_kyc_never_granted_by_unrelated_organizer_or_model_id(self):
        obj = SimpleNamespace(
            _meta=SimpleNamespace(
                concrete_model=SimpleNamespace(
                    _meta=SimpleNamespace(label_lower="tournaments.kycsubmission")
                ),
                app_label="tournaments",
                model_name="kycsubmission",
            ),
            user_id=2,
        )
        user = SimpleNamespace(
            pk=1, is_authenticated=True, is_active=True, is_superuser=False, is_staff=False
        )
        self.assertFalse(can_download(user, obj, "document_front"))

    def test_deploy_gate_stays_closed_for_unverified_s3(self):
        from apps.siteui.checks import governed_media_release_check

        with override_settings(
            DEBUG=False,
            REQUIRE_PERSISTENT_MEDIA=True,
            OWNLOBBY_MEDIA_MODE="s3",
            MEDIA_STORAGE_VERIFIED=False,
            MEDIA_RESTORE_VERIFIED=False,
        ):
            ids = {error.id for error in governed_media_release_check(None)}
            self.assertIn("siteui.E005", ids)
        with override_settings(
            DEBUG=False, REQUIRE_PERSISTENT_MEDIA=True, OWNLOBBY_MEDIA_MODE="legacy"
        ):
            self.assertEqual(governed_media_release_check(None)[0].id, "siteui.E002")

    def test_checksum_copy_restore_is_idempotent_and_never_overwrites(self):
        with TemporaryDirectory(dir="Artifacts/final-engineering") as work:
            root = Path(work)
            source = root / "source"
            source.mkdir()
            (source / "synthetic.png").write_bytes(image().read())
            refs = [{"key": "synthetic.png", "alias": "private_media"}]
            plan = make_plan(refs, source)
            dest = {"public_media": root / "public", "private_media": root / "private"}
            self.assertEqual(copy_verified(plan, source, dest), ["copied-verified"])
            self.assertEqual(copy_verified(plan, source, dest), ["already-verified"])
            self.assertEqual(
                checksum(source / "synthetic.png"), checksum(root / "private/synthetic.png")
            )
            restored = {
                "public_media": root / "restore-public",
                "private_media": root / "restore-private",
            }
            self.assertEqual(copy_verified(plan, root / "private", restored), ["copied-verified"])
            (root / "private/synthetic.png").write_bytes(b"different existing data")
            with self.assertRaises(ValueError):
                copy_verified(plan, source, dest)
            self.assertEqual(
                (root / "private/synthetic.png").read_bytes(), b"different existing data"
            )

    def test_active_pdf_and_bounded_pixel_limit_rejected(self):
        from apps.common.media.validation import validate_upload
        from pypdf import PdfWriter

        field = apps.get_model("tournaments.Tournament")._meta.get_field("rules_pdf")
        output = BytesIO()
        pdf = PdfWriter()
        pdf.add_blank_page(width=50, height=50)
        pdf.add_js('app.alert("synthetic");')
        pdf.write(output)
        with self.assertRaises(ValidationError):
            validate_upload(ContentFile(output.getvalue(), name="synthetic.pdf"), field, None)
        field = apps.get_model("user_profile.UserProfile")._meta.get_field("avatar")
        mock_image = Mock(width=50_000, height=50_000, n_frames=1)
        with patch("apps.common.media.validation.Image.open") as opened:
            opened.return_value.__enter__.return_value = mock_image
            with self.assertRaises(ValidationError):
                validate_upload(image(), field, None)

    def test_s3_write_failure_propagates_without_local_fallback(self):
        storage = ProtectedS3Storage(
            bucket_name="synthetic-bucket", access_key="synthetic", secret_key="synthetic"
        )
        obj = Mock()
        obj.upload_fileobj.side_effect = OSError("synthetic write failure")
        storage._bucket = SimpleNamespace(Object=lambda name: obj)
        with patch.object(storage, "exists", return_value=False), self.assertRaises(OSError):
            storage.save("synthetic.png", ContentFile(image().read()))
        self.assertEqual(obj.upload_fileobj.call_count, 1)

    def test_path_traversal_and_mixed_confidentiality_require_review(self):
        for key in ("../sensitive", "/absolute", "foo\\bar"):
            with self.assertRaises(ValueError):
                make_plan([{"key": key, "alias": "private_media"}], ".")
        with self.assertRaises(ValueError):
            make_plan(
                [
                    {"key": "same", "alias": "public_media"},
                    {"key": "same", "alias": "private_media"},
                ],
                ".",
            )
