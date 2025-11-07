"""
Traceability verification script.

Ensures all code files have proper implementation headers and trace.yml is populated.
"""
import os
import sys
import re
import yaml

ROOT = os.path.dirname(os.path.dirname(__file__))

TRACE_PATH = os.path.join(ROOT, "Documents", "ExecutionPlan", "trace.yml")
MAP_PATH = os.path.join(ROOT, "Documents", "ExecutionPlan", "MAP.md")

REQUIRED_HEADER = re.compile(
    r"Implements:\s*- Documents/ExecutionPlan/00_MASTER_EXECUTION_PLAN", re.I
)


def iter_repo_files():
    """Iterate over all Python, HTML, JS, and TS files in the repository."""
    exclude_dirs = {".git", "venv", "node_modules", "staticfiles", "__pycache__"}
    
    for base, dirs, files in os.walk(ROOT):
        # Remove excluded directories from traversal
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for f in files:
            p = os.path.join(base, f)
            if p.endswith((".py", ".html", ".js", ".ts")):
                # Skip migration files and test fixtures
                if "/migrations/" in p or "/fixtures/" in p:
                    continue
                yield p


def check_headers():
    """Check that implementation files have proper headers."""
    missing = []
    
    # Only check files in apps/ directory for now (actual implementation)
    apps_path = os.path.join(ROOT, "apps")
    if not os.path.exists(apps_path):
        return []  # No apps yet
    
    for p in iter_repo_files():
        # Only check files in apps directory
        if not p.startswith(apps_path):
            continue
        
        try:
            with open(p, "r", encoding="utf-8", errors="ignore") as fh:
                head = fh.read(2000)
                if not REQUIRED_HEADER.search(head):
                    missing.append(p)
        except Exception as e:
            print(f"Warning: Could not read {p}: {e}")
    
    return missing


def check_trace():
    """Check that trace.yml is properly populated."""
    if not os.path.exists(TRACE_PATH):
        print(f"Error: {TRACE_PATH} not found")
        return ["trace.yml missing"]
    
    try:
        with open(TRACE_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as e:
        print(f"Error reading trace.yml: {e}")
        return ["trace.yml invalid"]
    
    empty = []
    for phase, modules in (data or {}).items():
        if not isinstance(modules, dict):
            continue
        for m, payload in (modules or {}).items():
            if not payload or not payload.get("implements"):
                empty.append(f"{phase}:{m}")
    
    return empty


def main():
    """Run all checks."""
    missing_headers = check_headers()
    empty_trace = check_trace()
    
    fail = False
    
    if missing_headers:
        print("Files missing implementation header:")
        for p in missing_headers:
            print(" -", os.path.relpath(p, ROOT))
        fail = True
    
    if empty_trace:
        print("\nTrace entries with empty 'implements':")
        for k in empty_trace:
            print(" -", k)
        print("\nFill 'Documents/Planning/...' anchors for each module before merging.")
        # Not fatal during initial setup
        # Uncomment to enforce later:
        # fail = True
    
    if fail:
        print("\n❌ Traceability checks failed")
        sys.exit(1)
    else:
        print("✅ Traceability checks passed")


if __name__ == "__main__":
    main()
