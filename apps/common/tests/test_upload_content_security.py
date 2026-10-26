"""Provider-independent upload prerequisites for the storage migration."""

from io import BytesIO
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from PIL import Image

from apps.common.validators import (
    validate_document_upload,
    validate_image_upload,
    validate_payment_proof_upload,
)


class UploadContentSecurityTests(SimpleTestCase):
    def test_spoofed_unknown_content_cannot_bypass_allowlists_without_libmagic(self):
        # Unknown bytes and unrelated RIFF containers must not inherit a browser MIME claim.
        for validator in [
            validate_document_upload,
            validate_image_upload,
            validate_payment_proof_upload,
        ]:
            for content in [b"unrecognized bounded content", b"RIFF1234WAVE1234", b""]:
                with self.subTest(validator=validator.__name__, content=content):
                    upload = SimpleUploadedFile("spoof.png", content, content_type="image/png")
                    with patch.dict("sys.modules", {"magic": None}):
                        with self.assertRaises(ValidationError):
                            validator(upload)
                    self.assertEqual(upload.tell(), 0)

    def test_recognized_images_respect_existing_format_allowlists(self):
        for image_format in ["PNG", "JPEG", "WEBP"]:
            output = BytesIO()
            Image.new("RGB", (8, 8)).save(output, format=image_format)
            for validator in [
                validate_document_upload,
                validate_image_upload,
                validate_payment_proof_upload,
            ]:
                upload = SimpleUploadedFile(
                    "fixture.bin", output.getvalue(), content_type="application/octet-stream"
                )
                # Existing configured document policy permits PDF/JPEG/PNG,
                # while image/proof policies also permit WebP.
                if validator is validate_document_upload and image_format == "WEBP":
                    with self.assertRaises(ValidationError):
                        validator(upload)
                else:
                    validator(upload)
                self.assertEqual(upload.tell(), 0)

    def test_pdf_content_is_only_accepted_by_document_validator(self):
        upload = SimpleUploadedFile(
            "rules.pdf", b"%PDF-1.4\nlocal fixture", content_type="text/plain"
        )
        validate_document_upload(upload)
        with self.assertRaises(ValidationError):
            validate_image_upload(upload)
