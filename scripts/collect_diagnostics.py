#!/usr/bin/env python3
"""
DeltaCrown: collect diagnostics for CI/test DB/migration issues.

Creates ./dc_diagnostics.zip with:
- pytest output (verbose + quick)
- manage.py showmigrations, migrate --plan, check, check --deploy
- apps/*/migrations tree listing
- settings snippets (sanitized), pytest.ini, requirements.txt
- DB engine/name from settings_test_pg (sanitized)
"""

import os, sys, subprocess, json, zipfile, io, textwrap, pathlib, re, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "dc_diagnostics.zip"

def run(cmd, cwd=ROOT):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, shell=True)
        return p.returncode, p.stdout, p.stderr
    except Exception as e:
        return 1, "", f"EXC: {e}"

def read(path):
    try:
        return pathlib.Path(path).read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"<<error reading {path}: {e}>>"

def write_to_zip(z, arcname, content):
    z.writestr(arcname, content if isinstance(content, (str, bytes)) else str(content))

def main():
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as z:
        # 0) Environment info
        pyver = sys.version
        rc, pip_freeze, _ = run("pip freeze")
        z.writestr(f"env/python_version.txt", pyver)
        z.writestr(f"env/pip_freeze.txt", pip_freeze)

        # 1) Config files (sanitized)
        for rel in ["pytest.ini", "requirements.txt", "deltacrown/settings.py", "deltacrown/settings_test_pg.py"]:
            p = ROOT / rel
            if p.exists():
                txt = read(p)
                # sanitize DATABASE_URL/passwords (best-effort)
                txt = re.sub(r"(?i)(password|SECRET_KEY)\s*=\s*.+", r"\1 = '***REDACTED***'", txt)
                txt = re.sub(r"postgres://[^\\s'\"]+", "postgres://***REDACTED***", txt)
                write_to_zip(z, f"config/{rel.replace(os.sep,'/')}", txt)

        # 2) INSTALLED_APPS + DATABASES via Django
        cmds = [
            ("django_settings_dump.json",
             "python manage.py shell -c \"import json,django,os; "
             "from django.conf import settings; "
             "print(json.dumps({'INSTALLED_APPS':list(settings.INSTALLED_APPS),"
             "'DATABASES':{k:{kk:('***' if kk in ['PASSWORD','USER'] else vv) "
             "for kk,vv in v.items()} for k,v in settings.DATABASES.items()},"
             "'TIME_ZONE':settings.TIME_ZONE}, indent=2))\""),
            ("manage_check.txt", "python manage.py check"),
            ("manage_check_deploy.txt", "python manage.py check --deploy || exit 0"),
            ("showmigrations_all.txt", "python manage.py showmigrations"),
            ("migrate_plan.txt", "python manage.py migrate --plan || exit 0"),
        ]
        for name, cmd in cmds:
            rc, out, err = run(cmd)
            write_to_zip(z, f"manage/{name}", out + ("\nSTDERR:\n"+err if err else ""))

        # 3) Migrations tree listing for each app
        apps = ["apps.user_profile", "apps.teams", "apps.tournaments",
                "apps.game_efootball", "apps.game_valorant", "apps.notifications"]
        for a in apps:
            path = ROOT / a.replace(".", os.sep) / "migrations"
            buf = io.StringIO()
            buf.write(f"# {a} migrations\n")
            if path.exists():
                for p in sorted(path.glob("*.py")):
                    buf.write(p.name + "\n")
            else:
                buf.write("<<no migrations dir>>\n")
            write_to_zip(z, f"migrations/{a}.txt", buf.getvalue())

        # 4) Pytest runs (verbose + quick), test settings
        pytest_cmds = [
            ("pytest_full.txt", "pytest -vv -rA --maxfail=1 --ds=deltacrown.settings_test_pg --create-db"),
            ("pytest_quick.txt", "pytest -q --ds=deltacrown.settings_test_pg --create-db"),
        ]
        for name, cmd in pytest_cmds:
            rc, out, err = run(cmd)
            write_to_zip(z, f"pytest/{name}", out + ("\nSTDERR:\n"+err if err else ""))

        # 5) Optional: lastfail (won’t hurt if no cache)
        rc, out, err = run("pytest --lf -vv --ds=deltacrown.settings_test_pg --reuse-db")
        write_to_zip(z, "pytest/pytest_lastfail.txt", out + ("\nSTDERR:\n"+err if err else ""))

        # 6) Useful project files
        for rel in [
            "apps/user_profile/models.py",
            "apps/user_profile/signals.py",
            "apps/tournaments/models.py",
            "apps/tournaments/tests/test_registration.py",
            "apps/tournaments/tests/test_brackets.py",
        ]:
            p = ROOT / rel
            if p.exists():
                write_to_zip(z, f"project/{rel.replace(os.sep,'/')}", read(p))

    print(f"Wrote {OUT}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
