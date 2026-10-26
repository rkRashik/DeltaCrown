# OwnLobby security closure - Phase 4

Date: 2026-10-26. **HTTP fix implemented and validated locally; Linux/runtime and production storage/recovery gates remain open. Production cutover: No-Go.** No push, merge, deployment, DNS, provider or production data change.

## Upstream decision and maintainable backport

Current [official advisory](https://github.com/twisted/twisted/security/advisories/GHSA-q7qq-6mhp-9rc4) lists <=26.4.0 affected and 26.10.0rc1 patched. [Official releases](https://github.com/twisted/twisted/releases) and PyPI metadata still identify 26.4.0 as the latest stable. The RC includes broader changes and other protocol fixes. It was not silently installed or treated as production supported.

Selected a narrow, explicitly documented backport to stable 26.4.0 using the exact functional hunk in official commit [1616f702d36eda8990a5a5b22ad70fab140a7eb1](https://github.com/twisted/twisted/commit/1616f702d36eda8990a5a5b22ad70fab140a7eb1), referenced by the advisory. It rejects bare CR/LF alongside NUL in HTTP header values before request dispatch and disconnects. The later upstream optimization commit 022b6f7feb5980166c71f54e2c0d8f4f21ff6e1a was reviewed; the simpler original security hunk is sufficient and is the one retained. No speculative parser rewrite.

- Package: **Twisted 26.4.0+ownlobby.1**, committed under vendor/twisted; a documented downstream build, not an official vendor release.
- Output SHA256: `439da47560b0fd5d3ecbe5b027c54bd44864870cdcc2b81b016dee8f705ea8e6`.
- Provenance: vendor/twisted/provenance.json pins PyPI URL/hash, immutable patch URL/commit/hash, original/patched parser hashes and build toolchain. Original license/test package content remains intact; its public test keys are not production credentials.
- Only runtime source change is twisted/web/http.py. Distribution metadata/local label and RECORD are regenerated. No site-packages editing, startup monkeypatch, dependency ignore or global scanner suppression.
- Both requirements files install the same exact wheel. Render build and Docker verify its hash before installation; Docker copies only the necessary vendored package/build verifier into the dependency stage. Default verification is offline. Rebuild downloads hash-verified upstream inputs and matched the committed wheel byte-for-byte twice locally.
- Full hash locking of all other packages and Linux rebuild/runtime proof remain outside the evidence obtained here. Follow vendor/twisted/README.md to reproduce and eventually remove the temporary package when an acceptable stable release exists.

## Audits without false clearance

A local package version absent from PyPI is **skipped** by the normal installed scan. Its report says no findings but is not proof that Twisted is clear. This skip is preserved in branding/security-runtime-dependency-audit.json.

scripts/audit_production_dependencies.py therefore audits all 133 installed distributions (132 runtime + pip) again with Twisted normalized to its 26.4.0 upstream base. It fails if any base distribution is skipped or coverage is incomplete. That scan still reports **six** advisories and deliberately exits nonzero. No ignore IDs are used. The HTTP item is addressed by the verified backport; five other affected protocol implementations remain installed. The current inventory is branding/security-runtime-dependency-inventory.json; Phase 3 inventories/matrix remain historical evidence.

| Advisory | Base finding | Phase 4 disposition |
|---|---|---|
| GHSA-q7qq-6mhp-9rc4 / CVE-2026-115877 | Moderate, HTTP header framing | Exact upstream fix packaged, source hash verified, malformed headers close with one 400; Windows unit/network/upstream tests pass. Linux verification still required. |
| GHSA-cwm5-jh59-mwxr / CVE-2026-115778 | High, conch Telnet | Installed affected code; no such service/import in OwnLobby entry points. Not fixed by this patch. |
| GHSA-2qrf-pqgx-qh9v / CVE-2026-115774 | Moderate, IMAP SEARCH | Installed affected code; no IMAP service. Not fixed. |
| GHSA-3476-c5c2-fr73 / CVE-2026-115775 | High, domish/XMPP XML | Installed affected code; no words/XMPP service. Not fixed. |
| GHSA-53xc-49m8-p798 / CVE-2026-115776 | High, IRC buffer | Installed affected code; no Twisted IRC service. Discord uses discord.py/aiohttp. Not fixed. |
| GHSA-8pqf-f4m5-798g / CVE-2026-106454 | Moderate, IMAP LIST regex | Installed affected code; no IMAP service. No stable fixed version listed. |

Checked start.sh, bin/start_render.sh, render.yaml, ASGI routing and application imports: declared serving remains Daphne HTTP/WebSocket only. No twistd mail/words/manhole service is configured. Live dashboard/auxiliary-process configuration was not queried; reassess before enabling any new Twisted protocol. Five residuals stay visible and no owner risk acceptance is implied.

## Executed parser/transport validation

| Check | Result |
|---|---|
| Five committed byte-level tests | Pass: upstream malformed CR/LF/NUL cases, valid headers/pipelining, malformed pipelining without dispatch, network-chunk boundary and exact installed parser hash/version |
| Upstream twisted.web.test.test_http | 243 run: **238 successes, five skips** (optional HTTP/2 and unsupported HTTP/0.9 cases); initial collection lacked PyHamcrest, installed PyHamcrest 2.1.0 into QA only and reran successfully |
| Real clean-runtime Daphne loopback | Normal HTTP 200; both bare CR/LF vectors now one 400 and connection close, instead of Phase 3's two 200 responses. No second request dispatch. WS 101 upgrade and bounded frame rejection; subsequent HTTP remains 200. |
| Other malformed header observation | Vertical tab is rejected by Daphne with 400 but a following normal pipelined request is still processed. This upstream behavior was not generalized into a claim that every invalid byte closes the connection; the backport covers the reviewed CR/LF/NUL framing issue. |
| Actual application WS/auth | Workflow suite **88 pass/nine existing skips**, including authorized/untrusted/missing Origins, token/user rejection, private recipients and broadcasts; synthetic transport harness alone does not test authentication |
| TLS | Clean runtime HTTPS 200 over TLS 1.3 with a temporary locally trusted test certificate; cryptography/pyOpenSSL/Twisted interoperate |
| Dependencies | New clean prod install, prod/dev resolution and pip check pass; normal Django imports pass |

No Render host or production request-smuggling probe was used. Actual edge behavior is unverified and is not the mitigation. HTTP/2 is not enabled in the tested runtime. Tiny bounded fixtures, loopback services and disposable database only.

## Additional targeted corrections

See OWNLOBBY_OAUTH_RELIABILITY.md: all seven original failures resolved with documented causes; real Steam redirect defect, unsafe Google next URL, missing Steam signed-assertion binding/replay guards and concurrent identity reassignment are corrected. **47 OAuth/ownership/security tests pass**, including three real PostgreSQL two-user races.

See OWNLOBBY_MEDIA_ARCHITECTURE.md: 55 registered/53 concrete file fields audited; shared MIME sniffing now rejects unknown/spoofed content and unrelated RIFF; rules PDF importer/preview use storage.open; Docker excludes local environment/credential directories. These are prerequisites, not a completed private-storage system.

Final focused set **219 pass/one Cairo skip**. Brand verifier: 69 assets byte-identical, 353 compiled templates and one unchanged dormant optional crispy failure, settings contracts preserved, no new failures. Frontend and actual hashed static collection pass. No model/migration, financial calculation, API route, account identity or approved artwork was changed. No previously passing regression was observed in selected suites.

## Release and rollback

The reviewed HTTP issue has local code-level closure under the pinned verified package. Security/runtime release closure is **conditional on Linux/Python 3.12 validation**. Native Cairo still fails on this Windows host; no Linux runtime was available. Media/privacy/recovery, explicit validation on all upload paths, real provider callback/staging/mail/worker checks and the separate domain approvals still prevent production release.

Rollback uses reviewed Git commits and a clean environment rebuild, not manual library replacement. Rolling back the wheel to plain 26.4.0 reopens the HTTP vulnerability; treat it as containment only, not a safe production baseline. Reverting identity protections or MIME checks also restores known defects. No reverse schema migration is needed. Preserve keys, linked IDs, stored data and old-domain behavior.

## Git custody

Phase 4 implementation: `03bb5281d9dc269a1a9d78de78e1dbd576beae76`. This exact SHA is recorded by the documentation-only handoff follow-up. No push commands were executed.

Started clean on feature/ownlobby-dependency-security at a7f3e3c0063db8487b98a0baf84a42f39067c1c8. All three prior implementation commits are ancestors. New local branch: feature/ownlobby-security-runtime. Existing Phase 3 branch/history remain unchanged.

Origin is configured as https://github.com/rkRashik/DeltaCrown.git. Cached origin/master is 903103708b1c85dec86a6d098019ea03f39b3790; this is not a new remote verification. No fetch/push/merge/PR/deploy command executed. Latest owner instruction explicitly postpones all pushes, so neither Phase 3 nor Phase 4 was pushed and no remote feature URL is claimed. Live Render-linked branch/auto-deploy status remains unverified; local autoDeploy:false does not establish dashboard safety. Check it during the later coordinated release, not by an unsolicited dashboard request now.

Focused tracked-tree credential review covered 3,202 pre-change tracked files: 22 database-pattern candidates were redaction patterns or reviewed placeholders/local examples; five .sql candidates were schema/index/RLS scripts without data payloads. No live credential identified by this limited scan. New fixture strings are synthetic. Ignored .env/media/Artifacts are treated as private/local, not uploaded; artifacts include synthetic sessions, disposable DB and ephemeral test TLS keys. Six public upstream test-key fixtures remain inside the vendor wheel. This is not a full historical secret-scan certification; repeat history and staged-content review before the later push. No value was printed or rotated.

## Reproducible command/evidence index

All commands ran from repository root. Local runtime is Artifacts/security-runtime/runtime; QA overlays upgraded packages/test tools in Artifacts/dependencies/qa; audit tooling is Artifacts/readiness/dependency-audit-venv. See OWNLOBBY_DEPENDENCY_VALIDATION.md for guarded local DB setup and the original core test list; never reuse a production DATABASE_URL.

```powershell
.venv/Scripts/python.exe -m venv Artifacts/security-runtime/runtime
Artifacts/security-runtime/runtime/Scripts/python.exe -m pip install --no-cache-dir -r requirements-prod.txt --report Artifacts/security-runtime/clean-install.json
Artifacts/security-runtime/runtime/Scripts/python.exe -m pip check
Artifacts/security-runtime/runtime/Scripts/python.exe -m pip install --dry-run --ignore-installed --no-cache-dir -r requirements.txt --report Artifacts/security-runtime/dev-resolved.json
Artifacts/security-runtime/runtime/Scripts/python.exe scripts/build_twisted_backport.py --rebuild
Artifacts/security-runtime/runtime/Scripts/python.exe -m unittest apps.common.tests.test_http_transport_security -q
Artifacts/security-runtime/runtime/Scripts/python.exe scripts/check_http_transport.py
Artifacts/readiness/dependency-audit-venv/Scripts/python.exe scripts/audit_production_dependencies.py --site-packages Artifacts/security-runtime/runtime/Lib/site-packages --output-dir Artifacts/security-runtime/audit
# Audit exits nonzero for six unsuppressed base-version findings.
Artifacts/dependencies/qa/Scripts/python.exe -m pip install --no-cache-dir PyHamcrest==2.1.0
Artifacts/dependencies/qa/Scripts/python.exe -m twisted.trial --temp-directory=Artifacts/security-runtime/trial-http twisted.web.test.test_http
# With guarded local DB env and COMPETITION_APP_ENABLED=1:
Artifacts/dependencies/qa/Scripts/python.exe manage.py test apps.common.tests.test_release_readiness apps.siteui.tests.test_ownlobby_branding apps.siteui.tests.test_homepage_hero apps.siteui.tests.test_homepage_presentation apps.economy.tests.test_escrow_cached_balance apps.organizations.tests.test_membership apps.organizations.tests.test_leaderboard_service apps.user_profile.tests.test_settings_control_deck_smoke apps.user_profile.tests.test_settings_endpoints_smoke apps.common.tests.test_dependency_compatibility apps.common.tests.test_http_transport_security apps.common.tests.test_upload_content_security --settings=deltacrown.settings_brand_qa --keepdb --noinput
Artifacts/dependencies/qa/Scripts/python.exe -m pytest tests/integration/test_websocket_realtime.py apps/accounts/tests/test_email_sender.py apps/organizations/tests/test_cp_pipeline_e2e.py apps/user_profile/tests/test_game_passport_service_schema.py tests/tournaments/test_phase2_registration.py tests/certificates/test_s3_storage_core.py --ds=deltacrown.settings_brand_qa --tb=short --show-capture=no
# Exact 47-test OAuth command is in OWNLOBBY_OAUTH_RELIABILITY.md.
Artifacts/security-runtime/runtime/Scripts/python.exe manage.py check --deploy --settings=deltacrown.settings_brand_qa
Artifacts/security-runtime/runtime/Scripts/python.exe scripts/check_native_rendering.py
Artifacts/dependencies/qa/Scripts/python.exe scripts/verify_ownlobby.py --collect-static
npm run build
# Git Bash syntax check also executed for render_build.sh/start.sh/bin/start_render.sh/bin/start_worker.sh.
```

Workflow S3_TESTS was verified disabled; final auth/core commands explicitly set S3_TESTS=0 and AWS_EC2_METADATA_DISABLED=true. Do not enable the eight live-S3 cases to repeat local evidence. The custom synthetic production-mode check and temporary TLS harness are retained under Artifacts/security-runtime; they use no production endpoints. Local TLS result is tls-smoke.json; transport result is transport-smoke.json. Phase 3's ignored transport harness was initially reused, overwriting its ignored transport-smoke.json with Phase 4 observations. The committed Phase 3 reports/audit inventory are preserved as baseline evidence. Authoritative Phase 4 transport output now lives separately under security-runtime.

Relevant logs: core-tests-final.log (219/one skip), workflow-tests.log (88/nine skips), oauth-final.log (47 pass), upstream-http-tests.log (238/five skips), http-unit-final.log, clean-install.json, pip-check.log, dev-resolved.json, audit/, brand-static.log, frontend-build.log, production-mode-check.log, native-rendering.log. Intermediate core upload test incorrectly assumed configured document policy allowed WebP; corrected test now asserts that existing rejection rather than weakening the allowlist. No unexecuted Linux/browser/live-provider test is counted as passed.
