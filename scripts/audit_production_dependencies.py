"""Audit a clean runtime AND its upstream base versions without suppressions.

Local distribution labels must never make vulnerable upstream code disappear
from advisory matching. pip-audit must be installed in the calling environment.
"""

import argparse
from importlib.metadata import distributions
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-packages", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "vendor/twisted/provenance.json").read_text())
    packages = {}
    for item in distributions(path=[str(args.site_packages)]):
        name = item.metadata["Name"]
        value = item.version
        if name.lower() == "twisted":
            if value != manifest["version"]:
                raise ValueError("Runtime does not contain the reviewed Twisted distribution")
            value = manifest["base_version"]
        packages[name] = value
    if not any(name.lower() == "twisted" for name in packages):
        raise ValueError("Clean runtime Twisted distribution not found")
    requirements = args.output_dir / "upstream-base-requirements.txt"
    requirements.write_text(
        "\n".join(name + "==" + value for name, value in sorted(packages.items())) + "\n"
    )
    actual = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "--path",
            str(args.site_packages),
            "--format",
            "json",
            "--output",
            str(args.output_dir / "installed.json"),
        ]
    )
    upstream = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "-r",
            str(requirements),
            "--no-deps",
            "--disable-pip",
            "--format",
            "json",
            "--output",
            str(args.output_dir / "upstream-base.json"),
        ]
    )
    base_result = json.loads((args.output_dir / "upstream-base.json").read_text())
    if len(base_result["dependencies"]) != len(packages) or any(
        "skip_reason" in item for item in base_result["dependencies"]
    ):
        raise ValueError("Upstream-base audit did not cover every installed distribution")
    # Every installed distribution is explicitly included in the base manifest.
    # A nonzero result remains visible even when one advisory has a tested backport.
    return max(actual.returncode, upstream.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
