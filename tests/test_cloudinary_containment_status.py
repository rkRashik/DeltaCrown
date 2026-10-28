"""Offline regression tests: status never mutates provider assets."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import ownlobby_cloudinary_containment as script


class CloudinaryStatusTests(unittest.TestCase):
    def test_asset_identity(self):
        source = {"asset_id": "id", "public_id": "x", "resource_type": "image",
                  "version": 7, "verified_bytes": 123}
        info = dict(source, bytes=123, type="authenticated")
        self.assertTrue(script.asset_matches(info, source, "authenticated"))
        self.assertFalse(script.asset_matches(info, source, "upload"))

    def test_apply_and_status_exclusive(self):
        with patch("sys.argv", ["tool", "--apply", "--status"]):
            with self.assertRaises(SystemExit):
                script.main()

    def test_status_is_read_only_and_counts_sources(self):
        source = lambda i: {"asset_id": "id"+str(i), "public_id": "item"+str(i),
                            "resource_type": "image", "version": 1, "verified_bytes": 100}
        inventory = {"items": [
            {"classification": "copy_private_supabase", "sources": [source(i)]}
            for i in range(111)] + [
            {"classification": "keep_cloudinary", "sources": [source(i)]}
            for i in range(111, 113)]}
        def lookup(public_id, resource_type, type):
            i = int(public_id.removeprefix("item"))
            if type == ("authenticated" if i < 7 else "upload"):
                return dict(source(i), bytes=100, type=type)
            raise script.cloudinary.api.NotFound("missing")
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "inventory.json"
            p.write_text(json.dumps(inventory), encoding="utf8")
            with patch.object(script, "INVENTORY", p), \
                 patch("sys.argv", ["tool", "--status"]), \
                 patch.object(script, "dotenv_values", return_value={
                     "CLOUDINARY_URL": "cloudinary://key:secret@example"}), \
                 patch.object(script.cloudinary, "config"), \
                 patch.object(script.cloudinary.api, "resource", side_effect=lookup), \
                 patch.object(script.cloudinary.uploader, "rename") as rename, \
                 patch.object(script.time, "sleep"), \
                 patch("builtins.print") as output:
                script.main()
                rename.assert_not_called()
                messages = [" ".join(map(str, call.args)) for call in output.call_args_list]
                self.assertIn("PUBLIC_EXCLUSIONS_VERIFIED: 2", messages)
                self.assertIn("STILL_PUBLIC: 104", messages)
                self.assertIn("AUTHENTICATED: 7", messages)
                self.assertIn("STATUS_PASS: no changes made", messages)

    def test_public_exclusion_change_fails_closed(self):
        source = lambda i: {"asset_id": "id"+str(i), "public_id": "item"+str(i),
                            "resource_type": "image", "version": 1, "verified_bytes": 100}
        inventory = {"items": [
            {"classification": "copy_private_supabase", "sources": [source(i)]}
            for i in range(111)] + [
            {"classification": "keep_cloudinary", "sources": [source(i)]}
            for i in range(111, 113)]}
        def lookup(public_id, resource_type, type):
            i = int(public_id.removeprefix("item"))
            if type != "upload":
                raise script.cloudinary.api.NotFound("missing")
            data = dict(source(i), bytes=100, type=type)
            if i == 112:
                data["asset_id"] = "unexpected-change"
            return data
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "inventory.json"
            p.write_text(json.dumps(inventory), encoding="utf8")
            with patch.object(script, "INVENTORY", p), \
                 patch("sys.argv", ["tool", "--status"]), \
                 patch.object(script, "dotenv_values", return_value={
                     "CLOUDINARY_URL": "cloudinary://key:secret@example"}), \
                 patch.object(script.cloudinary, "config"), \
                 patch.object(script.cloudinary.api, "resource", side_effect=lookup), \
                 patch.object(script.cloudinary.uploader, "rename") as rename, \
                 patch.object(script.time, "sleep"), \
                 patch("builtins.print"):
                with self.assertRaises(SystemExit):
                    script.main()
                rename.assert_not_called()
