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
