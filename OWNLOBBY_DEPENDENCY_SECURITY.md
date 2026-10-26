# OwnLobby dependency security remediation

Assessment date: 2026-10-26. **Substantial remediation implemented; dependency release gate remains open. Overall production release: No-Go.** No remote changes, deployment, migrations, secret rotation or financial operations occurred.

## Before and after

| Measure | Baseline | Updated |
|---|---:|---:|
| Production declared pins | 128 | 132 (one conditional on Python >=3.13) |
| Resolved Windows production packages | 130 | 132 |
| Raw scanner advisory entries | 308 | 6 |
| Affected packages reported | 29 | 1 (Twisted) |
| Underlying package/advisory clusters, deduplicated by ID/aliases | 197 | 6 |
| Underlying baseline advisories no longer affecting selected versions | 0 | 191 |

Counts describe advisory metadata, not independently exploitable application defects. Baseline pinned and full resolved scans both reproduced 308 entries. Final full resolved and clean installed scans both report six. The installed scan includes pip (133 distributions); runtime graph has 132. All 197 baseline canonical records were retrieved; none is marked withdrawn. No ignore flags, vulnerability suppressions or removal of necessary functionality was used. Baseline raw data stays available in `branding/production-dependency-audit.json`.

The per-advisory [remediation matrix](branding/dependency-remediation-matrix.json) records aliases, affected/fixed ranges, severity, package exposure, actual import paths, final version, status and references. It distinguishes six installed residual vulnerabilities from application reachability. No waiver of exploitability was required for the 191 fixed findings. Advisory prerequisites vary: installed vulnerable code alone does not establish an exploitable route. Disputed status is not consistently machine-readable; none was dismissed on that basis. Alias deduplication handles repeated PYSEC/CVE/GHSA entries rather than counting them as independent exploits.

## Authoritative dependencies and graph

`requirements-prod.txt` is authoritative for Render (`render_build.sh`) and now for Docker's production stage. `requirements.txt` retains the broader development/test inventory, aligned runtime pins and its existing unrelated tools. Docker development additionally installs that file. `pyproject.toml` configures tools only. No production lock/constraints file or GitHub Actions workflow existed. The requirements were already a mixture of direct dependencies and explicitly pinned transitives, rather than a minimal list of imports.

[Resolved inventory](branding/production-dependency-inventory.json) includes versions, Python requirements, dependency edges and source imports where found. No direct import does not mean unused: Twisted, Autobahn, pyOpenSSL, service-identity, pyasn1 and serialization libraries are required through Daphne/Channels or TLS. Core Django RedisCache uses redis directly. Existing optional match polling imports django_redis (dev-only) and catches failures with fail-open provider throttling; enabling/relying on that polling limiter needs separate correction because the configured Django RedisCache is not django-redis. No task contract was changed here.

New Autobahn transitives cbor2 6.1.5 and ujson 6.0.0 are pinned, as are previously resolved typing-inspection 0.4.4 and Python >=3.13-only audioop-lts 0.2.2. txaio, service-identity and yarl changed to satisfy the upgraded transport/crypto/network graph. Production and development full resolution succeed. Runtime pins are exact, but this is not a hash-locked, built Linux wheelhouse: verify Linux source-build provenance and generate platform-specific artifact hashes before claiming hermetic supply-chain reproduction. Development-only packages were not broadly upgraded or security-cleared by this runtime task.

## Versions and controlled groups

| Package | Previous | Selected |
|---|---|---|
| django | 5.2.8 | 5.2.18 |
| daphne | 4.2.1 | 4.2.3 |
| msgpack | 1.1.2 | 1.2.1 |
| djangorestframework | 3.16.1 | 3.18.3 |
| pyjwt | 2.10.1 | 2.15.1 |
| django-allauth | 65.13.0 | 65.14.1 |
| cryptography | 46.0.3 | 50.0.2 |
| pyopenssl | 25.3.0 | 26.4.0 |
| pynacl | 1.5.0 | 1.6.2 |
| certifi | 2025.10.5 | 2026.10.23 |
| urllib3 | 2.5.0 | 2.8.0 |
| pillow | 12.0.0 | 13.0.0 |
| python-dotenv | 1.2.1 | 1.2.4 |
| bleach | 6.3.0 | 6.4.0 |
| soupsieve | 2.8.1 | 2.9 |
| requests | 2.32.5 | 2.34.2 |
| idna | 3.11 | 3.15 |
| cairosvg | 2.8.2 | 2.9.1 |
| lxml | 6.0.2 | 6.1.3 |
| pypdf2 | 3.0.1 | pypdf 6.21.2 (replacement) |
| aiohttp | 3.13.3 | 3.14.5 |
| multidict | 6.7.1 | 6.9.1 |
| yarl | 1.22.0 | 1.25.1 |
| marshmallow | 4.1.0 | 4.1.2 |
| pygments | 2.19.2 | 2.20.0 |
| setuptools | 80.9.0 | 84.1.0 |
| sqlparse | 0.5.3 | 0.6.0 |
| twisted | 25.5.0 | 26.4.0 |
| autobahn | 25.10.2 | 26.7.1 |
| txaio | 25.9.2 | 25.12.2 |
| service-identity | 24.2.0 | 26.1.0 |
| pyasn1 | 0.6.1 | 0.6.4 |

Group 1: Django/DRF/allauth/sqlparse. Group 2: Daphne/Twisted/Autobahn/txaio. Group 3: JWT/crypto/TLS/network with coupled dependencies. Group 4: Pillow/CairoSVG/lxml and pypdf replacement. Group 5: remaining affected utilities. Each group was installed into isolated QA and pip-checked; focused tests ran after groups 1, 2, 3/4 and the complete final group. Raw group-3/group-4 failures remain in evidence and their disposition is documented below. Group 5 was covered by the final complete suite rather than an artificial separate micro-test suite.

Django remains on supported 5.2 security maintenance, not 6.x. Exact 5.2.18 was verified against vendor release notes. Daphne 4.2.3 includes the frame/message limits and header hardening from 4.2.2. Pillow 13 and cryptography 50 cross major versions because cumulative security fixes require them; inspected application APIs remain supported. pyOpenSSL 26.4 pairs with cryptography 50; removed legacy OpenSSL APIs are not directly imported by OwnLobby. Existing Fernet fields, PBKDF2 hashes, signed sessions and HS256 tokens are verified using golden synthetic artifacts produced with the old installed libraries. No key/session rotation occurred.

PyPDF2 3.0.1 is unsupported; scanner fix metadata mentioning 3.9.0 must not be interpreted as an available PyPDF2 release. Replaced it with maintained pypdf 6.21.2. The sole application reader loader now uses pypdf explicitly; PDF preview's pre-existing undefined PdfReader/PYPDF2_AVAILABLE names are corrected. ReportLab 4.4.4 remains, with real PDF generation/extraction/import/preview coverage. HTML escaping, rules_text persistence, file authorization and model identities remain unchanged. Existing rules import still requires storage .path; remote-storage compatibility remains a storage workstream, not a newly solved capability.

Render declares Python 3.12.10; Docker declares python:3.12-slim. Selected runtime packages permit Python 3.12; Pillow requires >=3.11. Actual execution here is Windows Python 3.13.15. Linux/3.12 runtime remains unverified. 129 Linux CPython 3.12 manylinux wheels downloaded successfully using glibc 2.28/2014 tags. Cloudinary 1.40.0 and pycairo 1.28.0 require source builds; Python 3.13 audioop-lts is excluded on 3.12. Docker already declares Cairo/compiler headers, but this is not evidence of successful Render native builds. The initial manylinux2014-only wheel check failed because newer Pillow wheels require a newer manylinux tag; the corrected target succeeds. Do not downgrade security fixes to retain an obsolete wheel tag.

License metadata for the replacements/core upgrades remains permissive (pypdf BSD-3-Clause, Pillow MIT-CMU, cryptography Apache-2.0 OR BSD-3-Clause, setuptools MIT; Django BSD-3-Clause). Full metadata is in the inventory where published; missing expressions are not assertions of no license. No legal review or complete bundled-native-library license audit is claimed.

## Remaining findings: Twisted 26.4.0

All six remain visible in both final audits. Latest stable Twisted verified from PyPI was 26.4.0; 26.10.0rc1 is a prerelease. No prerelease, project monkeypatch or unreviewed dependency fork was silently introduced.

| Advisory | Vendor severity | Applicability and release decision |
|---|---|---|
| GHSA-q7qq-6mhp-9rc4 / CVE-2026-115877 | Moderate | **P1 blocker.** HTTPChannel accepts bare CR/LF header values; a proxy interpreting them differently can enable request smuggling. OwnLobby's public Daphne stack uses this parser. Bounded loopback checks return two HTTP 200 responses for each malformed-header/pipelining case. This confirms parser acceptance, not a proven exploit through Render. No evidence that Render rejects it; do not assume edge mitigation. Fixed-version metadata lists 26.10.0rc1 only. |
| GHSA-cwm5-jh59-mwxr / CVE-2026-115778 | High | P2 installed residual; requires exposed conch Telnet/manhole. No such service/import/configuration exists in application deployment. RC-only fix. |
| GHSA-2qrf-pqgx-qh9v / CVE-2026-115774 | Moderate | P2 installed residual; authenticated IMAP SEARCH. No IMAP service. RC-only fix. |
| GHSA-3476-c5c2-fr73 / CVE-2026-115775 | High | P2 installed residual; domish/XMPP streaming XML. No such service/import. RC-only fix. |
| GHSA-53xc-49m8-p798 / CVE-2026-115776 | High | P2 installed residual; Twisted IRC server. No such service. Discord uses a different stack. RC-only fix. |
| GHSA-8pqf-f4m5-798g / CVE-2026-106454 | Moderate | P2 installed residual; authenticated IMAP LIST/LSUB regex parsing. No IMAP service. No fixed version listed. |

The five unused-protocol findings are not removed or globally suppressed: enabling a Twisted auxiliary protocol would change applicability. No residual risk is accepted on the owner's behalf. Before release, obtain a stable upstream HTTP fix and retest; if unavailable, undertake a separately reviewed minimal upstream parser backport with byte-level malformed-header, pipelining, lifecycle and proxy tests. A normal Django middleware fix runs after transport parsing and is insufficient. Do not enable production redirects or proxy assumptions as a substitute. The current stable update is retained as a reviewable intermediate result, not declared safe to deploy.

## Validation and preservation

See [validation](OWNLOBBY_DEPENDENCY_VALIDATION.md) for commands and counts. Baseline 197 focused tests pass; final 212 run, 211 pass and one Cairo-host skip. Workflow set 60 pass/one existing skip. Expanded mocked OAuth/offline storage: seven failures, 38 passes, eight skips on BOTH original and upgraded libraries; exact failing node IDs agree. No observed previously passing regression in compared suites. Those failures still require functional investigation before release, not false-green fixture edits.

69 approved assets are byte-identical; 353 templates compile with one unchanged dormant optional integration failure; production hashed static collection succeeds. Frontend build succeeds. Public browser checks cover 12 page/viewports with no overflow or JS errors; mobile homepage accessibility reports two remaining violations, login none. No UI redesign, schema migration, business-logic/payment calculation change, provider call or database identifier change was introduced.

## Maintenance and release gates

- **P1 open:** stable Twisted HTTP parser remediation and Linux/Python 3.12/native Cairo validation.
- **P1 existing:** seven verified baseline OAuth failures require triage, and real provider callbacks/session linking still require isolated staging tests.
- **P1 existing:** durable public/private media, backup restoration, actual Render/Upstash/worker parity, authenticated mail delivery and separately approved cutover remain required. Keep all previous domain/SEO approval gates.
- **P2:** five unexposed Twisted protocol advisories, optional polling limiter dependency/backend mismatch, development-only dependency drift/advisories, four existing moderate npm build advisories, mobile homepage accessibility findings. No owner acceptance is implied.
- Schedule automated advisory scans of clean resolved Linux runtime environments, vendor maintenance reviews and exact-pin updates with this regression suite. Do not treat a future zero scanner result as security certification.

## Primary security references

- [Django 5.2.18](https://docs.djangoproject.com/en/6.0/releases/5.2.18/)
- [Daphne changelog](https://github.com/django/daphne/blob/main/CHANGELOG.txt)
- [Pillow 13](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html)
- [cryptography changelog](https://cryptography.io/en/latest/changelog/), [pyOpenSSL changelog](https://www.pyopenssl.org/en/latest/changelog.html), [PyJWT changelog](https://pyjwt.readthedocs.io/en/stable/changelog.html)
- [Twisted releases](https://github.com/twisted/twisted/releases), [HTTP advisory](https://github.com/twisted/twisted/security/advisories/GHSA-q7qq-6mhp-9rc4)
- Per-advisory vendor/OSV references and affected/fixed ranges: committed matrix. Current exact release metadata: PyPI JSON for each selected package, retained in ignored evidence.
