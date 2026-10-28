"""Offline tests for post-containment CDN variant audit; no real provider calls."""
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts import ownlobby_cdn_original_audit as audit


class CloudinaryVariantTests(unittest.TestCase):
    def create_rows(self):
        private = [{"asset_id": "secret-" + str(i)} for i in range(111)]
        public = [{"asset_id": "art-" + str(i)} for i in range(2)]
        rows = [
            {"asset_id": item["asset_id"], "classification": "private",
             "url": "https://res.cloudinary.com/example/image/upload/v12345/private" +
                    str(index) + ".jpg"}
            for index, item in enumerate(private)
        ]
        rows.extend([
            {"asset_id": item["asset_id"], "classification": "public",
             "url": "https://res.cloudinary.com/example/image/upload/v12345/art" +
                    str(index) + ".jpg"}
            for index, item in enumerate(public)
        ])
        return private, public, rows

    def run_audit(self, response=(404, 404)):
        private, public, rows = self.create_rows()
        seen = []

        def sample(url):
            seen.append(url)
            return response

        out = io.StringIO()
        with patch.object(audit, "configure_cloudinary", return_value="example"), \
             patch.object(audit, "approved_inventory", return_value=(private, public)), \
             patch.object(audit, "latest_media_backup", return_value=(None, b"x" * 32)), \
             patch.object(audit, "BASELINE_FILE", "test"), \
             patch.object(audit, "decrypt_from", return_value=json.dumps(rows).encode()), \
             patch.object(audit, "sample_http", side_effect=sample), \
             patch.object(audit, "Path") as ignored_path, \
             redirect_stdout(out):
            # Patch only the local immutable-manifest existence check.
            ignored_path.return_value.exists.return_value = True
            with patch.object(audit, "latest_media_backup",
                              return_value=(ignored_path.return_value, b"x" * 32)):
                audit.verify_variants()
        return seen, out.getvalue()

    def test_denies_111_versionless_and_111_transforms(self):
        seen, output = self.run_audit()
        self.assertEqual(len(seen), 222)
        self.assertTrue(any("/image/upload/private0.jpg" in u for u in seen))
        self.assertTrue(any("/image/upload/c_scale,w_1/v12345/private0.jpg" in u
                            for u in seen))
        self.assertNotIn("art0.jpg", "\n".join(seen))
        self.assertIn("CDN_VARIANT_DENIAL_PASS", output)

    def test_reachable_variant_fails(self):
        with self.assertRaises(ValueError):
            self.run_audit(response=(200, 200))
