"""Repository safety checks use only disposable local files; no Django or DB."""

from pathlib import Path
import json
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.ops import check_repo_hygiene as hygiene
from scripts import check_documentation as documentation

ROOT = Path(__file__).resolve().parents[1]


class RepositoryToolTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "Artifacts/repository-cleanup/test-scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        if not scratch.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError("Disposable repository fixtures must stay inside this workspace")
        self.workspace = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.workspace.cleanup)
        self.root = Path(self.workspace.name)
        subprocess.run(["git", "init", "--quiet", str(self.root)], check=True, capture_output=True)
        (self.root / "config").mkdir()
        (self.root / "config/repository-policy.json").write_text(
            json.dumps(
                {"allowed_root_files": ["README.md", "OWNLOBBY_SECURITY_CLOSURE.md", ".gitignore"]}
            )
        )
        (self.root / ".gitignore").write_text(".env\ndb.sqlite3\nDocuments/\n")
        (self.root / "README.md").write_text("# Project\n")
        (self.root / "OWNLOBBY_SECURITY_CLOSURE.md").write_text("# Evidence\n")

    def test_reviewed_reports_and_ignored_owner_files_are_preserved(self):
        (self.root / "Documents").mkdir()
        owner_file = self.root / "Documents/owner-notes.md"
        owner_file.write_text("unique owner notes")
        (self.root / ".env").write_text("SYNTHETIC_TEST_ONLY=1")
        (self.root / "db.sqlite3").write_bytes(b"synthetic fixture")
        with patch.object(hygiene, "PROJECT_ROOT", self.root):
            self.assertEqual(hygiene.check_root_hygiene(), [])
        self.assertEqual(owner_file.read_text(), "unique owner notes")

    def test_unreviewed_root_file_is_reported_without_deletion(self):
        notes = self.root / "new-notes.md"
        notes.write_text("preserve this")
        with patch.object(hygiene, "PROJECT_ROOT", self.root):
            result = hygiene.check_root_hygiene()
        self.assertEqual([item["file"] for item in result], ["new-notes.md"])
        self.assertTrue(notes.exists())

    def test_force_tracked_environment_is_not_hidden_by_ignore(self):
        (self.root / ".env").write_text("SYNTHETIC_TEST_ONLY=1")
        subprocess.run(
            ["git", "-C", str(self.root), "add", "--force", ".env"], check=True, capture_output=True
        )
        with patch.object(hygiene, "PROJECT_ROOT", self.root):
            result = hygiene.check_root_hygiene()
        self.assertEqual(result[0]["file"], ".env")
        self.assertIn("Sensitive", result[0]["reason"])

    def test_documentation_distinguishes_clone_links_and_owner_workspace(self):
        (self.root / "owner.md").write_text("private local notes")
        (self.root / "guide.md").write_text(
            "[ok](README.md) [owner](owner.md) [bad](missing.md) [web](https://example.com/)\n```\n[example](not-a-real-file.md)\n```\n"
        )
        rows = documentation.link_results(self.root, "guide.md", {"guide.md", "README.md"})
        self.assertEqual([row["status"] for row in rows], ["exists", "workspace-only", "missing"])

    def test_documentation_checks_fragments(self):
        (self.root / "guide.md").write_text("[ok](README.md#project) [bad](README.md#missing)")
        rows = documentation.link_results(self.root, "guide.md", {"guide.md", "README.md"})
        self.assertEqual([row["status"] for row in rows], ["exists", "missing-anchor"])

    def test_legacy_manual_probe_import_never_contacts_provider(self):
        with patch(
            "requests.get", side_effect=AssertionError("Live providers are forbidden")
        ) as request:
            namespace = runpy.run_path(
                str(ROOT / "riot_test.py"), run_name="repository_cleanup_import_check"
            )
        request.assert_not_called()
        self.assertTrue(callable(namespace["main"]))
