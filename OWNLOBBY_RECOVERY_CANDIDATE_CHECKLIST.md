# OwnLobby media-compatible recovery candidate — staged, not certified

## Baseline and scope
- This branch was forked from the latest `feature/ownlobby-free-hosting` release and retains the same governed hybrid media implementation.
- It is a **candidate**, not a proven live rollback. Do not deploy old DeltaCrown SHA after source containment.
- The release and recovery code have not been exercised together against live Render.
- Cloudinary: latest operator read-only evidence shows 111 sensitive sources of type `upload`, 0 authenticated, 0 mismatched. Two deliberately public artwork exclusions exist in the inventory.
- Supabase private media objects were copied and content verified, but an actual full production canary and live restoration proof are still required.

## Read-only checks added on this candidate
The `--status` command verifies **both** the 111 restricted Cloudinary assets and the two excluded public artworks. It aborts on:
- any changed asset identity/version/bytes or missing/duplicated delivery state;
- absent or altered approved public exclusions;
- any provider read errors.
It does not call `rename` or `destroy`. Run it before and after coordinated cutover to reconcile partial state without publishing identifying URLs.

## Verified Supabase live metadata (2026-10-28, read-only)

The connected production Supabase project `DeltaCrown` (region `ap-south-1`)
was queried directly. This replaces the older *source-only* bucket assumptions:

- `ownlobby-private-media`: `public=false`, exactly **125** object rows,
  **125 unique object names**, **109,908,333 total metadata bytes**.
- All 125 object metadata size fields are present and greater than zero.
- `ownlobby-public-media`: private, zero objects; `screenshots`: private,
  zero objects.
- Storage `objects` and `buckets` have PostgreSQL RLS enabled, with zero
  policies; direct anon/authenticated row access is default-denied by RLS,
  although SQL table grants alone still exist. S3 access-key authorization is
  separate and may bypass RLS. These are not equivalent to anonymous HTTP
  denial tests on Cloudinary.
- Latest storage record update in this inspection was 2026-10-27 UTC.
- No writes, ACL changes, service settings changes or secret reads occurred.

The read-only private-origin probe now **requires exactly 125 objects with
exactly 109,908,333 summed HEAD ContentLength bytes**. Any new uploads or
divergent sizes intentionally stop rehearsal for inventory reconciliation.
This check still cannot prove per-object checksum, backup restoration or
application authorization. Leave all three `MEDIA_*_VERIFIED` flags false
until their separately specified acceptance tests really pass.

## Live private-origin readiness canary (no production writes)
The standalone `scripts/private_media_probe.py` checks the approved existing
`ownlobby-private-media` bucket using the existing server-only S3 credentials.
It lists the private origin, confirms at least 125 migrated object entries,
HEAD-checks every listed object, and performs five one-byte authenticated
Range reads. It writes nothing and never displays object keys, URLs or credentials.

From the project root, with the approved private S3 `MEDIA_PRIVATE_*` values
in local `.env` or environment, run:

```powershell
.\.venv\Scripts\python.exe scripts\private_media_probe.py
```

Successful output begins `PRIVATE_ORIGIN_READ_ONLY_PASS`. Failure prints
only a generic exception type and exits nonzero. The offline regression suite
is `python -m unittest tests.test_private_media_probe`.

**Evidence boundary:** This verifies read-only S3 connectivity and object
presence, not content checksums against the confidential migration manifest,
not an independent restore, not a live Render deployment, not anonymous
Cloudinary URL invalidation and not record-level authorization. Do not set
`MEDIA_STORAGE_VERIFIED`, `MEDIA_RESTORE_VERIFIED` or
`MEDIA_LEGACY_PRIVACY_VERIFIED` solely from this output.

## Operator-confirmed private-origin canary (2026-10-28)

The operator refreshed the OwnLobby release branch and ran the read-only
`python scripts/private_media_probe.py` against the configured Supabase origin.
Observed sanitized result:

```text
PRIVATE_ORIGIN_READ_ONLY_PASS
OBJECTS_HEAD_VERIFIED: 125
SIGNED_READS: 5
NOT VERIFIED: backup restoration, anonymous URL denial, record authorization
```

This verifies live authenticated S3 read ability, HEAD visibility for every
audited object and exact size/count checks. It did not mutate any object.
It is **not** an app authorization canary or an independent restore. The
Cloudinary 111-asset containment and anonymous URL checks remain outstanding.

## Acceptance criteria — no shortcuts
1. Local Django privacy, hybrid storage, launcher, worker and recovery tests pass on this exact branch with disposable QA configuration.
2. Run read-only status preflight again immediately before cutover: 111 upload, 0 authenticated, two exclusions verified, zero mismatch.
3. Confirm all **11 legacy /media paths** and representative original/versioned/transformed/embedded sensitive CDN URLs are denied to anonymous GET and HEAD **after** invalidation propagates. Metadata status alone is not proof of denial.
4. Positive canary: authorized owner/organizer accesses representative S3 private media; anonymous/non-owner denied before storage I/O; public organization artwork remains accessible.
5. Validate a real independent backup restore and post-restart persistence. The three `MEDIA_*_VERIFIED` flags require evidence; never set merely to bypass `check --deploy`.
6. Verify login/CSRF, tournament registration, brackets, notifications and WebSockets; broker/worker must be measured against the 512 MiB container limit and audited for queue backlog.
7. Prove a separate recovery deployment can come up with sources remaining private. If that cannot be demonstrated, do not mutate the 111 sources.
8. No production database rollback, Cloudinary return to public, deletion, or queue purge as recovery strategy.

## Safe local regression command
```powershell
git fetch origin release/ownlobby-hybrid-recovery-candidate-20261028
git switch release/ownlobby-hybrid-recovery-candidate-20261028
git pull --ff-only origin release/ownlobby-hybrid-recovery-candidate-20261028
.\.venv\Scripts\python.exe -m unittest tests.test_cloudinary_containment_status -v
.\.venv\Scripts\python.exe manage.py test apps.common.tests.test_hybrid_media apps.common.tests.test_media_profile_privacy --settings=deltacrown.settings_media_qa --noinput
```

### Staged-only decision
**NO-GO for live provider mutation today based only on this checklist.** Need actual restoration/canary evidence and CDN access denial checks. These cannot be inferred from unit tests.
