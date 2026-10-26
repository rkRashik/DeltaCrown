# Temporary Twisted upstream security backport

This is an explicitly maintained downstream package, not a new official Twisted release.

- Stable base: Twisted 26.4.0 from the exact PyPI URL/SHA256 in provenance.json.
- Patch: official commit 1616f702d36eda8990a5a5b22ad70fab140a7eb1, referenced by GHSA-q7qq-6mhp-9rc4. Only the functional HTTP header hunk is applied; the broader 26.10 release candidate is not adopted.
- Distribution: 26.4.0+ownlobby.1 (PEP 440). Upstream internal __version__ remains its base version; no runtime monkeypatch.
- Runtime source changes: twisted/web/http.py only. METADATA version, dist-info directory and RECORD are regenerated. All other source/license/test fixture content is unchanged. Six private-key fixtures inside the upstream test package are deliberately public upstream test keys, not OwnLobby credentials.
- Integrity: input wheel, immutable official patch, original/patched HTTP module and final wheel hashes are pinned. Original license remains inside the wheel.

From repository root:

```
python scripts/build_twisted_backport.py
python scripts/build_twisted_backport.py --rebuild
pip install -r requirements-prod.txt
python -m unittest apps.common.tests.test_http_transport_security
python scripts/check_http_transport.py
```

Default verifies offline integrity. --rebuild downloads verified upstream inputs and compares exact bytes. Render/Docker verify the artifact before installing. Both requirement files use the same exact local wheel path. The committed binary avoids network patch application during deployment. Full hash locking of all unrelated dependencies is not claimed. Build toolchain is recorded in the manifest; other compression toolchains require a reviewed reproducibility comparison.

Always audit installed metadata AND upstream base versions from an environment with pip-audit:

```
python scripts/audit_production_dependencies.py --site-packages <clean-runtime-site-packages> --output-dir <ignored-audit-output>
```

The installed scan cannot audit a local version not found on PyPI; its skip is preserved, never counted as clearance. The mandatory base scan audits all 133 installed distributions and returns nonzero for six findings. Only the HTTP advisory has this backport; five unused-protocol findings remain. Byte/network checks and 238 upstream HTTP tests pass locally; Linux runtime remains unverified. This is not approval to deploy.

Removal: once an acceptable stable fix exists, update both dependency sources, remove local-wheel build verification/copy integration and the base-version special case, update provenance/fingerprint tests, and repeat audits/parser/OAuth/Channels/TLS/Linux validation. Preserve this commit as provenance. Do not silently delete fingerprint tests or substitute an untested prerelease. Rollback to unpatched 26.4.0 reopens the HTTP blocker.

.gitattributes preserves exact wheel/patch bytes on Windows and Linux. The upstream unified diff contains required blank context lines with a single space; only that artifact exempts blank-at-EOL whitespace checks. No application source or advisory check is suppressed.
