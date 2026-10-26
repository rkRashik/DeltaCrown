# OwnLobby final engineering handoff

Date: 2026-10-26. Branch: `feature/ownlobby-durable-media`. Starting HEAD: `9e5e453b9deb4c0baa983da78b946cd27f9f1a2c`. **Local storage code is a staging-validation candidate; production remains No-Go.** Nothing was pushed, merged, deployed, purchased, migrated in production or changed in provider dashboards/DNS. This is the primary current handoff; earlier reports retain historical evidence.

## A. Completed locally

- Integrated all **53 concrete upload fields** (55 including proxy aliases) through governed FileField/ImageField runtime classes. Built-in Django migration deconstruction, field names, upload paths and existing stored keys are preserved. No migration, account identity, financial calculation or ledger change.
- Separate `public_media` and `private_media` storage aliases support local filesystem or existing django-storages/boto3 S3-compatible backends. **Both origins must remain private**, including the public-artwork bucket. No raw backend URLs are returned. Public artwork is delivered only when its record is visible; private downloads check the actual user/record on every request using session/JWT authentication.
- KYC requires owner or explicit model-permission reviewer access; unrelated organizers cannot read it. Payments, evidence, teams, private profiles/followers, community attachments, drafts and certificates have category-specific rules. Unknown fields fail closed. Team and user participant ID namespaces are distinguished in new and existing evidence download checks.
- `.url` remains the template/serializer interface but returns a stable application route. Delivery uses no-store/noindex/nosniff/no-referrer headers, safe content disposition and sandbox policy. **Private downloads use an application proxy, not bearer presigned URLs**: possession of a URL grants no private access, and permissions are rechecked each request. No signed private URL lifetime needs configuring.
- Validation runs on direct field saves, including admin/service uploads: existing validators, signature/extension checks, byte limits, bounded decoded pixels/frames, real image decoding, PDF parsing and rejection of encrypted/oversized/active-root PDFs. Supported gallery MP4/WebM and private opaque replay attachments are handled separately. This is not antivirus, complete PDF sanitization or video transcoding.
- Removed necessary local `.path` dependencies, prevented implicit development production-media fallback, and preserved old profile files when replacement/removal occurs. Reference changes withdraw their application routes; retention-aware object retirement is intentionally separate from deleting references.
- Staff CKEditor uploads remain deliberate **public-image publication** through a separate signed application route, never confidential evidence. These public image links are persistent publication identifiers, not expiring private access grants. Do not upload confidential draft/evidence material through this editor; record-bound attachments use the governed fields.
- Added read-only `export_media_references` and offline `scripts/media_transfer.py`: classification, SHA-256 manifests, disjoint-root checks, exclusive writes, idempotent verification and local restore testing. No source deletion, database rewrite or cloud transfer is performed.
- Persistent-media checks remain. Additional checks reject legacy/local production media, incomplete/insecure S3 configuration, shared buckets, unverified persistence/recovery and unclassified fields (`siteui.E002`–`E006`). Verification flags default false; setting them is an owner attestation after real proof, not a test bypass.

## Actual validation evidence

Reused the completed interrupted-run logs rather than repeating suites. Windows/Python 3.13.15; guarded loopback PostgreSQL `ownlobby_test`; synthetic files and mocked providers only. Evidence stays ignored under `Artifacts/final-engineering/`.

| Category | Actual result |
|---|---|
| Final combined core/media suite, governed storage enabled | **242 passed, 1 existing Cairo skip** (243 run); includes **23 new media/security/migration regressions** |
| OAuth/identity/Google redirect suites | **47 passed**, 2 existing migration deprecation warnings |
| Registration, teams/competitive pipeline, Game Passport, email, WebSocket authorization, offline certificate storage | **88 passed, 9 existing skips**, 2 migration warnings |
| Frontend build | Passed JSX and Tailwind; existing Browserslist freshness notice; reused installed packages, not a fresh npm install |
| Brand/templates/hashed static collection | Passed: all 69 approved assets identical, 353 templates compiled, one unchanged optional-crispy template failure, settings contracts preserved, zero new failures |
| Governed-media system check | Passed without errors; existing filesystem-media warning remains. Export command discovery passed. Twisted backport hash verification passed |
| S3 adapter/configuration | Tested through actual django-storages adapter with an in-memory transport; private parameters, read/write/delete, failure propagation and bounded SDK retry configuration checked; no live S3 test |
| Migration/restore | Synthetic local checksum copy/restore, idempotency, traversal rejection and no-overwrite tests passed; no production migration or actual backup restoration |
| Compatibility | All 53 field classes/deconstruction contracts tested; no schema migration; application defaults retain `legacy` behavior until approved backfill |
| Linux/Python 3.12/native Cairo | **Unverified**: Docker absent; one focused WSL check reported it is not installed. No host infrastructure installed or discovery repeated |

The workflow skips are eight intentionally disabled live-S3 tests and one existing competitive-pipeline fixture limitation. The Cairo skip and dormant optional-crispy template failure are pre-existing. No passing-suite regression was observed; full-project/browser/live-provider/live Redis/Celery/cloud tests were not rerun. Twisted/dependency inputs and all approved brand files are unchanged. The pinned backport is still required; no unrelated dependency upgrade or new vulnerability-clearance claim.

## B. Requires actual staging/cloud validation

1. Run the reviewed code on Linux/Python 3.12 with native Cairo and shipped fonts; execute SVG/PNG/PDF/certificate rendering and relevant imports/tests. The saved Windows results are not Linux parity.
2. Verify two **distinct private origins** with synthetic S3 files: successful writes/reads/deletes, anonymous raw GET/HEAD denial, cross-user denial, unavailable storage behavior and web/worker restart persistence. Do not enable a public bucket endpoint, public ACL, custom-domain bypass, or private-read fallback.
3. Approve and execute a protected legacy-media inventory/backfill. Existing public Cloudinary/filesystem URLs, editor HTML/JSON references, external URLFields and orphaned objects need separate discovery. A FileField export alone does not cover them. Old confidential public URLs/caches must be contained before cutover; code cannot revoke an existing external public URL.
4. Restore independent database metadata and object backups into isolated targets, compare every referenced key/checksum/permission, and measure agreed recovery objectives. Mocked storage and synthetic local restore are not proof of durability or production recoverability.
5. Verify real Redis/channel-layer/Celery workers, SMTP verification/reset mail and approved OAuth sandbox callbacks on staging. Existing identity/client IDs, secrets, sender and old domain remain intact.

The code is ready for these controlled staging checks, not for an unqualified staging or production deployment. Remaining provider ACLs, backfill coverage, editor-publication policy and restore evidence require explicit acceptance. Do not hide a gate by disabling `REQUIRE_PERSISTENT_MEDIA` or setting verification flags without proof.

## Configuration and existing-file safety

All changes below require a later approved restart/redeploy on web and workers. Do not enter secrets into Git, reports or chat.

| Variable | Safe/current behavior | Approved target |
|---|---|---|
| `OWNLOBBY_MEDIA_MODE` | `legacy` default; existing data still readable; not production-approved | `local` for reviewed split local data; `s3` after staging/backfill |
| `MEDIA_PUBLIC_BUCKET`, `MEDIA_PRIVATE_BUCKET` | Unset | Two distinct private-origin buckets |
| `MEDIA_PUBLIC_ENDPOINT_URL`, `MEDIA_PRIVATE_ENDPOINT_URL` | Unset | Provider-issued HTTPS S3 endpoints; not public delivery domains |
| `MEDIA_PUBLIC_REGION`, `MEDIA_PRIVATE_REGION` | `auto` | Provider-issued region; use `auto` only where supported |
| `MEDIA_PUBLIC_ACCESS_KEY_ID`, `MEDIA_PUBLIC_SECRET_ACCESS_KEY` | Blank/unset | Least-privilege public-artwork bucket credentials, kept secret |
| `MEDIA_PRIVATE_ACCESS_KEY_ID`, `MEDIA_PRIVATE_SECRET_ACCESS_KEY` | Blank/unset | Separate least-privilege confidential bucket credentials |
| `MEDIA_STORAGE_VERIFIED`, `MEDIA_RESTORE_VERIFIED` | `0` | `1` only after recorded real persistence/privacy and restore proof |
| `REQUIRE_PERSISTENT_MEDIA` | Existing Render default `1` | Keep `1`; do not bypass |

Local split storage places public-category bytes in `MEDIA_ROOT` and confidential bytes in `.private-media/`; neither is automatically backfilled. Both are excluded from source/build custody as appropriate. In governed mode Django no longer directly serves `/media/`; `.url` resolves to authorized application delivery. Do not switch modes on existing data until files have been copied and verified. Never point tests at Supabase production.

Offline procedure, run only against an approved isolated/restored source (commands are **not** authorization to read production):

```powershell
# Supply only the approved isolated database/settings first.
python manage.py export_media_references --output Artifacts/media-references.json
python scripts/media_transfer.py --references Artifacts/media-references.json --source-root <approved-local-source> --manifest Artifacts/media-plan.json
# Optional verified local copy; all three roots must be disjoint:
python scripts/media_transfer.py --references Artifacts/media-references.json --source-root <approved-local-source> --destination-public <public-staging-root> --destination-private <private-staging-root> --manifest Artifacts/media-copy.json --copy
```

Use fresh output filenames; manifests are confidential and must not be committed. Mixed public/private references to one key stop for manual review. Export includes soft-deleted references for retention. For an approved provider transfer, use a scoped, non-deleting copy tool; compare downloaded SHA-256 and length against this manifest (multipart ETags are not equivalent). Preserve exact keys and all DB references. Separately inventory editor/JSON/orphan objects; retain encrypted source backups and reconcile uploads made during the copy window. No automated cloud migration was executed or claimed.

## Focused Linux reproduction

On an **already approved isolated Linux/Python 3.12 runner** with local disposable PostgreSQL, Cairo development/runtime, compiler/pkg-config, libffi/freetype and Node/npm available; never mount this workspace's `.env` or private media:

```bash
python3.12 -m venv /tmp/ownlobby-media-qa
source /tmp/ownlobby-media-qa/bin/activate
python scripts/build_twisted_backport.py
pip install -r requirements.txt
pip check
export DATABASE_URL='postgresql://ownlobby_qa@127.0.0.1:55432/ownlobby_unused'
export DATABASE_URL_DEV="$DATABASE_URL"
export DATABASE_URL_TEST='postgresql://ownlobby_qa@127.0.0.1:55432/ownlobby_test'
export S3_TESTS=0 AWS_EC2_METADATA_DISABLED=true SENTRY_DSN='' COMPETITION_APP_ENABLED=1
mkdir -p Artifacts/final-engineering
python scripts/check_native_rendering.py
python manage.py check --settings=deltacrown.settings_media_qa
python manage.py test apps.common.tests.test_governed_media apps.common.tests.test_dependency_compatibility apps.common.tests.test_http_transport_security --settings=deltacrown.settings_media_qa --keepdb --noinput
npm ci --include=dev && npm run build
python scripts/verify_ownlobby.py --collect-static
```

Use the preserved full OAuth/workflow commands from existing release reports if platform-specific results require investigation. A production-mode `check --deploy` must still fail until genuine storage/recovery proof is supplied; local QA security warnings are not production clearance. No Docker/WSL installation or cloud runner was provisioned here.

## C. Owner approval, infrastructure and release order

Recommended architecture: existing Render Daphne web plus separate Celery worker, existing Supabase PostgreSQL and Upstash Redis, two private S3-compatible media origins, an independent encrypted backup destination, existing verified transactional mail provider, and Namecheap DNS after approved cutover. R2 Standard is a reasonable portable option; no provider is selected or purchased. [django-storages configuration](https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html), [R2 private-origin guidance](https://developers.cloudflare.com/r2/buckets/public-buckets/) and [current pricing](https://developers.cloudflare.com/r2/pricing/) were checked during the implementation. R2 lists 10 GB-month Standard storage, 1M Class A/10M Class B monthly free allowance; overage storage $0.015/GB-month plus operations, with free direct Internet egress. This is not an account entitlement or full hosting bill; backup storage and web proxy bandwidth/compute also count.

Initial planning estimates, **not measured capacity or a purchased plan**: one web process with about 1 GB RAM preferred for bounded image/PDF work; a separate 512 MB–1 GB worker with conservative concurrency; budget approximately 5–10 DB connections per process and verify the actual Supabase pool limits. Storage capacity should include live objects plus at least one independent full backup generation and growth. The no-store application proxy favors privacy over CDN performance; measure Bangladesh latency, download concurrency, memory, temporary-disk usage and costs before choosing the smallest plan. Existing free service allowances are not a reliability guarantee.

Ordered owner-approved sequence:

1. Approve an isolated Linux/staging environment, storage provider/budget, editor-publication policy, retention/hold policy and recovery targets. No dashboard visit is needed merely to review this code.
2. **Storage/Supabase:** verify current source ACLs; independently back up DB metadata and media; create approved isolated storage/least-privilege credentials; validate canaries and restore. Audit legacy exposure and transfer/checksum coverage before switching production reads.
3. **Render/GitHub:** review live linked branch/auto-deploy first, then authorize the coordinated feature push and staging deploy. Keep the service hostname unchanged. Run Linux/native tests, exact locked build, private-origin and worker/restart tests. Supply approved storage settings only after proof; do not turn flags on to get a green build.
4. **Upstash:** verify existing limits/TLS and isolated worker/channel-layer behavior; preserve existing credentials, queues and live workers until approved transition.
5. **Email/OAuth:** authenticate the intended sender with provider-issued SPF/DKIM/DMARC and test mail. Add/test new callbacks alongside old ones using existing application identities. Do not change production sender/callbacks prematurely.
6. Approve the reconciled media copy and legacy URL containment, then deploy old-domain-compatible code/settings; validate registration, private files, team permissions, wallet reads, WebSockets and recovery. No financial smoke transaction is required.
7. **Render/Namecheap:** follow the existing [domain runbook](OWNLOBBY_DOMAIN_MIGRATION.md): reverify actual targets/TLS, replace only conflicting apex/www records after approval, preserve mail TXT/MX/SPF, then test both domains. Keep old origin/canonical behavior until acceptance.
8. Approve canonical/provider switch and only later controlled public redirects/Search Console migration. Monitor errors, private 403/404 behavior, costs and queues. Keep old-domain ownership and rollback artifacts.

Rollback: restore reviewed application/settings and reconcile both object stores using manifests, without deleting new uploads or rolling back user/financial data. **Do not restore public confidential URLs or roll back to unprotected legacy serving.** If storage fails, retain private origins and return safe failure/maintenance responses while repairing/reconciling; no public fallback. Restore from verified independent backups only through a separately approved recovery. Keep the Twisted backport and OAuth protections throughout.

## D. Safe to defer

Infrastructure display-name changes, optional CDN derivatives, cosmetic work, broad cleanup and automatic orphan retirement can wait. Malware scanning/transcoding and metadata-removal enhancements are not supplied here: do not describe uploaded originals as sanitized or safe to execute. Approve supported document/video handling and reviewer procedures for launch; never use the public rich-text editor for confidential drafts. Retention deletions need their own reference/hold checks and approval.

## Git custody and exact next action

Implementation commit: **`8075d266fefe2d24932ec2ea8b87403c852b99af`**, `feat: add governed durable media and private file delivery`. The commit-reference follow-up changes only this handoff. All earlier commits remain ancestors; final working-tree status is checked after the follow-up and reported to the owner.

All 26 protected Documents files pass pre/post name/size/hash comparison. AST comparison confirms the 23 model sources differ only in governed upload classes/imports; financial and other model definitions are unchanged. Changed Python syntax and `git diff --check` pass. A focused credential-pattern review of changed/new files found no matches; this is not a full historical secret-scan certification. No private upload or protected document is added. No remote operation is authorized.

**Next owner action:** approve the isolated Linux/staging validation and two-private-origin storage/backup budget and policy. Then perform one coordinated GitHub/infrastructure step after deployment-link safety is verified. Do not share credentials in chat or change DNS yet.
