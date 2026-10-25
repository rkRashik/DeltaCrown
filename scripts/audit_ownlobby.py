"""Classify remaining legacy references without reading secrets or application data.

Run from the repository root. The detailed source inventory is written under
branding/; private runtime logs, uploads, archives and dependencies are excluded.
"""
import ast
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import tokenize
import io

ROOT = Path(__file__).resolve().parents[1]
LEGACY = re.compile(r"deltacrown|deltacoin|crown[ _-]?(?:points?|rank|store)", re.I)
PUBLIC = re.compile(r"\b(?:DeltaCrown|DELTACROWN|DeltaCoins?|Crown Points?|Crown Rank|Crown ?Store)\b")
SUFFIXES = {".py", ".html", ".txt", ".js", ".jsx", ".css", ".svg", ".json", ".md", ".yml", ".yaml", ".toml", ".webmanifest", ".sh", ".ps1"}


def comment_lines(source, suffix):
    result = set()
    if suffix == ".py":
        try:
            for token in tokenize.generate_tokens(io.StringIO(source).readline):
                if token.type == tokenize.COMMENT:
                    result.add(token.start[0])
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    result.update(range(node.lineno, node.end_lineno + 1))
        except (SyntaxError, tokenize.TokenError):
            pass
    else:
        pattern = r"<!--.*?-->|/\*.*?\*/|{\%\s*comment\s*\%}.*?{\%\s*endcomment\s*\%}|{#.*?#}"
        for match in re.finditer(pattern, source, re.S):
            start = source.count("\n", 0, match.start()) + 1
            result.update(range(start, start + match.group().count("\n") + 1))
        for number, line in enumerate(source.splitlines(), 1):
            if line.lstrip().startswith(("//", "#", "*")):
                result.add(number)
    return result


def classify(path, line, number, comments):
    parts = set(path.parts)
    text = line.strip()
    if number in comments:
        return "intentionally_preserved", "Historical implementation comment or documentation string."
    if parts & {"migrations", "migrations_new", "tests", "docs", "Documents", "reports", "backup_unused", "My drafts", "management"} or path.name.startswith("test_"):
        return "intentionally_preserved", "Migration, test contract, archive or historical project record."
    if path.parts[0] in {"scripts", "tools", "ci", ".github", ".agents", ".codex"} or path.name == "manage.py":
        return "intentionally_preserved", "Engineering tool, detector pattern, setup utility or technical entrypoint."
    if path.suffix == ".md" or path.name == "schema.yml":
        return "intentionally_preserved", "Technical documentation, migration report or generated schema snapshot."
    if path.as_posix().startswith(("static/img/deltaCrown_logos/", "static/siteui/svg/")) or "-old" in path.name:
        return "intentionally_preserved", "Unused legacy artwork/source retained for cached clients and history; active slots use approved assets."
    if re.search(r"(?:https?://|@)[^\s\"'<>]*deltacrown|DeltaCrownEmail|DeltaCrown_OAUTH|RIOT_API_USER_AGENT", text, re.I):
        return "requires_later_migration", "Legacy origin, mailbox, external handle, environment alias or provider identity; controlled owner cutover required."
    if "models" in parts or path.name in {"models.py", "models_main.py"}:
        return "intentionally_preserved", "Persisted model metadata, currency codes or schema identity; no model/migration rewrite."
    if "Joined DeltaCrown in the first month" in text:
        return "intentionally_preserved", "Historical early-adopter achievement describes the platform at the time of joining."
    if "PRODID:" in text or "User-Agent" in text:
        return "intentionally_preserved", "Existing calendar producer or external client identity; integration identifiers remain stable."
    if re.search(r'"currency"\s*:\s*"DeltaCoin"', text):
        return "intentionally_preserved", "Existing API currency value; the public presentation layer displays Coins."
    if "refuses to start" in text:
        return "intentionally_preserved", "Technical startup diagnostic for the unchanged Django project package."
    if "new CrownStore(" in text:
        return "intentionally_preserved", "Existing JavaScript constructor identifier; display name is Store."
    if "dcLog(" in text or "logger." in text or "console." in text:
        return "intentionally_preserved", "Developer diagnostic text, not a product brand slot."
    if PUBLIC.search(text):
        # Names containing additional identifier characters are intentionally
        # excluded by PUBLIC's word boundaries (DeltaCrownWallet, etc.).
        if re.search(r"(?:static|src=|href=).*?(?:deltaCrown_logos|logo-deltacrown)", text, re.I):
            return "unexpected", "Active source appears to reference legacy artwork; inspect before committing."
        if path.suffix in {".html", ".jsx"}:
            return "unexpected", "Potential authored UI copy; inspect its runtime context."
        if path.suffix in {".js", ".py"} and not re.search(r"(?:import |class |def |\bname\s*=|\bdescription\s*=|\bverbose_name|\bhelp_text|__all__|__version__)", text):
            return "unexpected", "Potential authored display string; inspect before classifying."
    return "intentionally_preserved", "Django package/app/model/API/DOM/storage identifier, import, code or compatibility asset path."


def main():
    names = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=ROOT, text=True).splitlines()
    references = []
    for name in names:
        path = Path(name)
        if path.suffix not in SUFFIXES or name.startswith(("branding/", "static/community/build/")):
            continue
        if path.name.startswith(".env") or set(path.parts) & {"Artifacts", "media", "staticfiles", "node_modules", ".git", ".venv"}:
            continue
        source = (ROOT / path).read_text(encoding="utf-8-sig", errors="replace")
        comments = comment_lines(source, path.suffix)
        for number, line in enumerate(source.splitlines(), 1):
            if not LEGACY.search(line):
                continue
            category, reason = classify(path, line, number, comments)
            references.append({"path": path.as_posix(), "line": number, "classification": category, "reason": reason})
    target = ROOT / "branding"
    target.mkdir(exist_ok=True)
    counts = Counter(row["classification"] for row in references)
    (target / "legacy-references.json").write_text(json.dumps({"scope": "Tracked and non-ignored source; dependencies, secrets, runtime artifacts and duplicate generated community bundles excluded.", "counts": counts, "references": references}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(counts, indent=2))
    for row in references:
        if row["classification"] == "unexpected":
            print(f"REVIEW {row['path']}:{row['line']}")


if __name__ == "__main__":
    main()
