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
    """Check that trace.yml is properly populated.
    
    Returns tuple: (errors, warnings)
    - errors: modules with status='complete' and empty implements (FAIL)
    - warnings: modules with status='planned'/'in_progress' and empty implements (WARN)
    """
    if not os.path.exists(TRACE_PATH):
        print(f"Error: {TRACE_PATH} not found")
        return (["trace.yml missing"], [])
    
    try:
        with open(TRACE_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except Exception as e:
        print(f"Error reading trace.yml: {e}")
        return (["trace.yml invalid"], [])
    
    errors = []
    warnings = []
    
    for phase, modules in (data or {}).items():
        if not isinstance(modules, dict):
            continue
        for m, payload in (modules or {}).items():
            if not payload or not payload.get("implements"):
                module_key = f"{phase}:{m}"
                status = payload.get("status") if payload else None
                
                # Fail only if status is explicitly 'complete' with empty implements
                if status == "complete":
                    errors.append(module_key)
                # Warn if planned/in_progress (acceptable during development)
                elif status in ["planned", "in_progress"]:
                    warnings.append(module_key)
                # No status or unknown status = treat as placeholder (warn only)
                else:
                    warnings.append(module_key)
    
    return (errors, warnings)


def main():
    """Run all checks."""
    missing_headers = check_headers()
    trace_errors, trace_warnings = check_trace()
    
    fail = False
    
    if missing_headers:
        print("Files missing implementation header:")
        for p in missing_headers:
            print(" -", os.path.relpath(p, ROOT))
        fail = True
    
    if trace_errors:
        print("\n[ERROR] Complete modules with empty 'implements':")
        for k in trace_errors:
            print(" -", k)
        print("\nComplete modules MUST have planning document references.")
        fail = True
    
    if trace_warnings:
        print("\n[WARNING] Planned/in-progress modules with empty 'implements':")
        for k in trace_warnings:
            print(" -", k)
        print("(This is acceptable during development; fill before marking complete)")
    
    if fail:
        print("\n[FAIL] Traceability checks failed")
        sys.exit(1)
    else:
        print("\n[PASS] Traceability checks passed")
        if trace_warnings:
            print("       (with warnings for planned modules)")


if __name__ == "__main__":
    main()
