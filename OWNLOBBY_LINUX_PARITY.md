# OwnLobby Linux/Python 3.12 parity

Date: 2026-10-26. **Linux runtime parity NOT established.** No Linux test or native Cairo skip is counted as a pass. This remains a release gate.

## Actual environment and serious availability checks

Executed on Windows x64, Python 3.13.15. Get-Command found only wsl.exe/ssh.exe/py.exe among Linux execution candidates; no Docker, Podman, QEMU or uv runtime. Checked standard Docker Desktop, VirtualBox, VMware and QEMU locations; no usable executable found. wsl --list --verbose reports WSL not installed; Windows feature inventory reports VirtualMachinePlatform and Microsoft-Windows-Subsystem-Linux disabled (InstallState 2). py -0p lists only Python 3.13. An SSH client alone is not an approved Linux environment; no target/credentials were assumed or used.

No virtualization feature, host package manager or paid infrastructure was installed. No dashboard visit is required for independent local work. A future approved existing Linux runner/container environment is needed; this report does not ask the owner to provision it during Phase 4.

## Work completed, with boundaries

| Category | Executed evidence | Linux status |
|---|---|---|
| Clean runtime | Fresh Artifacts/security-runtime/runtime venv, production requirements only; 132 runtime distributions, plus pip; install report and pip check pass | Windows only |
| Framework/imports | Clean-runtime Django checks execute; focused compatibility/SEO/domain/wallet/settings suite 219 pass/one Cairo skip | Windows only |
| HTTP/ASGI/Channels | Verified wheel, five parser tests, 238 upstream HTTP passes/five skips, bounded real Daphne HTTP/WS tests; workflow 88 pass/nine existing skips | Windows only |
| PostgreSQL | psycopg2 imports and loopback PostgreSQL 18 tests, including concurrent provider identity claims | Windows only; Supabase production not connected |
| Redis/Celery | Imports, Redis channel-layer serialization and Kombu memory broker tests pass in focused suite | Real Redis/broker network/worker behavior not tested; Upstash untouched |
| TLS | Clean-runtime verified local TLS 1.3 handshake and HTTPS 200 | Windows only |
| Image/PDF | JPEG/PNG/WebP and document rules import/preview pass; PDF generation/extraction uses ReportLab/pypdf | Windows only |
| Native rendering | scripts/check_native_rendering.py executed and **fails** in cairocffi shared-library loading; libcairo unavailable to that loader | No successful CairoSVG/pycairo/cairocffi/svglib/rlPyCairo end-to-end result; Linux not run |
| Assets/build | npm build passes; real hashed static collection succeeds; 69 asset hashes match, 353 templates compile with one historical optional crispy failure | Windows only |
| Wheel availability | Phase 3 downloaded 129 Linux cp312 manylinux wheels; Cloudinary and pycairo require source builds. Twisted backport wheel is pure Python | Packaging information, NOT runtime parity; not repeated as new proof |

The native smoke script performs actual SVG-to-PNG/PDF, pycairo and cairocffi surfaces, svglib-to-ReportLab PDF/raster via rlPyCairo and certificate text extraction. Missing libraries cause a failure, not a skip. An initial script syntax typo was corrected before the actual runtime attempt; the final observed failure is the missing native library. No synthetic success output is generated.

## Deploy-check interpretation

manage.py check --deploy with guarded settings_brand_qa reported **385 warnings, no errors**: 379 DRF schema-generation warnings (356 W002/23 W001), five deliberately insecure local-test security settings and the filesystem-media warning. This is not a production configuration pass.

A separate ignored production_check_settings module applies the reviewed production security policy, a strong explicitly synthetic key, loopback DB/memory services and REQUIRE_PERSISTENT_MEDIA=True. Its deploy check **fails as expected with siteui.E001**, plus siteui.W001 and the same 379 schema warnings; the five test-policy security warnings disappear. Thus the persistent-media gate is still active. No warning or check was suppressed. DRF schema warning baseline counts were not compared against a prior checkout and need separate triage; runtime API regression tests still pass. Neither command validates the live Render environment.

## Reproduce the Linux release gate later

The checked-in production Docker base is python:3.12-slim; Render declares Python 3.12.10. Record actual immutable image/OS/Python and OpenSSL/Cairo versions on an approved runner rather than assuming the floating Docker tag matches Render. Use a clean build context: .dockerignore now excludes .env variants, credential directories and Artifacts/media.

Inside an approved disposable Linux container/runner only, install the existing project's required native build/runtime dependencies: compiler/pkg-config, PostgreSQL driver headers as needed, Cairo development/runtime, libffi/freetype/font libraries and libmagic; verify which wheels avoid compilation. Existing Dockerfile already includes several Cairo/compiler headers; successful native linkage remains unproven. Include the shipped fonts for certificate rendering. Do not copy host/production credentials or change host-level infrastructure to run this checklist.

Use a disposable PostgreSQL database named ownlobby_test reachable at loopback inside that environment; settings_brand_qa rejects remote hosts. Use memory mail/cache/Channels/broker for baseline tests and separate local disposable Redis for network/worker integration. Do not substitute Supabase/Upstash or real OAuth credentials. Have test provider values in the runner, no .env from this workspace.

```bash
python3.12 -m venv /tmp/ownlobby-runtime
/tmp/ownlobby-runtime/bin/python scripts/build_twisted_backport.py
/tmp/ownlobby-runtime/bin/pip install --no-cache-dir -r requirements-prod.txt
/tmp/ownlobby-runtime/bin/pip check
/tmp/ownlobby-runtime/bin/python scripts/check_native_rendering.py
/tmp/ownlobby-runtime/bin/python scripts/check_http_transport.py
# Set DATABASE_URL_TEST=postgresql://<disposable-user>@127.0.0.1:<port>/ownlobby_test
# and a distinct local DATABASE_URL; no production credentials.
/tmp/ownlobby-runtime/bin/python manage.py check --deploy --settings=deltacrown.settings_brand_qa
```

Install compatible test tooling in a separate QA environment and rerun the exact focused/OAuth/workflow/upstream HTTP commands recorded in OWNLOBBY_SECURITY_CLOSURE.md / OWNLOBBY_OAUTH_RELIABILITY.md and Phase 3 validation. Run the dual installed/base audit from separate pip-audit tooling. Repeat locked npm ci/build, scripts/verify_ownlobby.py --collect-static, template validation and all 69 hashes. Test certificate rendering, PostgreSQL transactions, Redis channel layer, Celery task execution, both domain configurations, private origins/recipients and local TLS. Preserve expected media gate failures until Phase 5; do not silence them to obtain a green deploy check.

Save command exits, installed inventory, OS/Python/native library versions and logs. Only actual Linux execution can close this gate. The local backport is a prepared candidate for isolated Linux validation; a validated staging deployment cannot yet be certified. Production cutover remains No-Go for the additional media/recovery/provider gates.
