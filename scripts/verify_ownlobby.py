"""Local rebrand verification; requires the strictly isolated brand QA settings.

Example: python scripts/verify_ownlobby.py
Set DATABASE_URL_TEST to a local disposable database named ownlobby_test first.
Reports are written only under ignored Artifacts/ownlobby/.
"""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deltacrown.settings_brand_qa")
if os.environ["DJANGO_SETTINGS_MODULE"] != "deltacrown.settings_brand_qa":
    raise SystemExit("Use deltacrown.settings_brand_qa; production settings are forbidden for this check.")

BASELINE = "8270018c536df41dcd869c3f4412c3c62a1d685b"


def original(path):
    result = subprocess.run(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, capture_output=True)
    return result.stdout.decode("utf-8-sig") if result.returncode == 0 else None


def run(*, collect_static=False):
    import django
    django.setup()
    from django.conf import settings
    from django.contrib.staticfiles import finders
    from django.template import engines

    report = {"baseline": BASELINE, "new_failures": []}
    provenance = json.loads((ROOT / "branding/approved-assets.json").read_text(encoding="utf-8"))
    bad_assets = []
    for row in provenance["files"]:
        path = ROOT / row["path"]
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            bad_assets.append(row["path"])
    report["approved_asset_copies"] = {"checked": len(provenance["files"]), "mismatches": bad_assets}
    report["new_failures"] += [f"Approved asset changed: {name}" for name in bad_assets]
    paths = [value for value in settings.BRAND.values() if isinstance(value, str) and value.startswith("ownlobby/")]
    missing = [name for name in paths if not finders.find(name)]
    report["brand_paths"] = {"checked": len(paths), "missing": missing}
    report["new_failures"] += [f"Missing brand asset: {name}" for name in missing]

    engine = engines["django"].engine
    compiled, existing = 0, []
    for path in (ROOT / "templates").rglob("*.html"):
        if "My drafts" in path.parts:
            continue
        name = path.relative_to(ROOT).as_posix()
        try:
            engine.from_string(path.read_text(encoding="utf-8-sig"))
            compiled += 1
        except Exception as error:
            before = original(name)
            try:
                if before is None:
                    raise RuntimeError("No checkpoint version")
                engine.from_string(before)
            except Exception:
                existing.append({"path": name, "error": str(error)})
            else:
                report["new_failures"].append(f"Template regression: {name}: {error}")
    report["templates"] = {"compiled": compiled, "existing_failures": existing}

    changed = subprocess.check_output(["git", "diff", "--name-only", BASELINE], cwd=ROOT, text=True).splitlines()
    changed += subprocess.check_output(["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    changed = sorted(set(changed))
    syntax_errors = []
    url_changes = []
    url_pattern = r"{%\s*url\b.*?%}"
    for name in changed:
        path = ROOT / name
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8-sig", errors="replace") if path.suffix in {".py", ".html"} else ""
        if path.suffix == ".py":
            try:
                ast.parse(source)
            except SyntaxError as error:
                syntax_errors.append({"path": name, "error": str(error)})
        if path.suffix == ".html":
            before = original(name)
            # Capturing a reversed URL with "as name" preserves its route and
            # arguments (reset mail now passes that path to the public-origin tag).
            def routes(text):
                return [re.sub(r"\s+as\s+\w+\s*%}", " %}", tag) for tag in re.findall(url_pattern, text, re.S)]
            if before is not None and routes(before) != routes(source):
                url_changes.append(name)
    report["python_syntax_errors"] = syntax_errors
    report["template_url_tag_changes"] = url_changes
    report["new_failures"] += [f"Python syntax: {row['path']}" for row in syntax_errors]
    report["new_failures"] += [f"Template URL contract changed: {name}" for name in url_changes]

    name = "templates/user_profile/profile/settings_control_deck.html"
    before, after = original(name), (ROOT / name).read_text(encoding="utf-8")
    patterns = {
        "ids": r'\bid=["\']([^"\']+)["\']',
        "field_names": r'\bname=["\']([^"\']+)["\']',
        "tab_values": r'name=["\']settings_tab["\'][^>]*value=["\']([^"\']+)',
        "csrf_tags": r"{%\s*csrf_token\s*%}",
        "url_tags": url_pattern,
    }
    contracts = {key: re.findall(pattern, before, re.S) == re.findall(pattern, after, re.S) for key, pattern in patterns.items()}
    # These are the only authorized changes inside existing settings scripts.
    for old, new in [
        ("new Notification('DeltaCrown - New Request'", "new Notification('OwnLobby - New Request'"),
        ("new Notification('DeltaCrown - Request Update'", "new Notification('OwnLobby - Request Update'"),
        ("role in the DeltaCrown server.", "role in the OwnLobby server."),
        ("icon: '/static/img/logo.png'", "icon: '{% static brand.apple_icon %}'"),
    ]:
        before = before.replace(old, new)
    scripts = r"<script\b[^>]*>.*?</script\s*>"
    contracts["inline_script_behavior"] = re.findall(scripts, before, re.S) == re.findall(scripts, after, re.S)
    for name in ["apps/user_profile/urls.py", "static/user_profile/js/oauth_linked_accounts.js", "templates/user_profile/profile/settings/partials/_game_passports.html"]:
        contracts[name] = original(name) == (ROOT / name).read_text(encoding="utf-8-sig")
    report["settings_contracts"] = contracts
    report["new_failures"] += [f"Settings contract changed: {key}" for key, ok in contracts.items() if not ok]
    migrations = [name for name in changed if "migrations" in Path(name).parts]
    report["modified_migrations"] = migrations
    report["new_failures"] += [f"Unexpected migration: {name}" for name in migrations]
    if collect_static:
        from django.core.management import call_command
        from django.test import override_settings
        output = ROOT / "Artifacts/readiness/collected-static"
        with override_settings(STATIC_ROOT=output, STORAGES={**settings.STORAGES, "staticfiles": {"BACKEND": "deltacrown.storage.RobustStaticFilesStorage"}}):
            call_command("collectstatic", interactive=False, verbosity=0)
            manifest = json.loads((output / "staticfiles.json").read_text(encoding="utf-8"))["paths"]
            critical = [settings.BRAND["logo_dark"], settings.BRAND["logo_light"], "ownlobby/brand.css", "ownlobby/manifest.webmanifest", "community/build/app.js", "dist/tailwind.css", "css/design-tokens.css"]
            unresolved = [name for name in critical if name not in manifest or not (output / manifest[name]).is_file()]
            report["production_static_collection"] = {"critical_checked": len(critical), "unresolved": unresolved}
            report["new_failures"] += [f"Unresolved hashed asset: {name}" for name in unresolved]
    target = ROOT / "Artifacts/ownlobby/final-verification.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"approved_assets": len(provenance["files"]), "templates_compiled": compiled,
                      "existing_template_failures": len(existing), "settings_contracts_preserved": all(contracts.values()),
                      "new_failures": report["new_failures"]}, indent=2))
    return bool(report["new_failures"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect-static", action="store_true", help="Also run production static storage into ignored local QA output.")
    raise SystemExit(run(collect_static=parser.parse_args().collect_static))
