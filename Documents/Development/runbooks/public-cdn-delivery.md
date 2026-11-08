# Public Cloudinary CDN delivery: rollout handoff (OL-08)

**Status: code only, switched off. No provider call, upload or activation has happened.** Every step below that touches production needs the owner's explicit approval first.

## What it is
Verified copies of a *strictly approved* set of public artwork on Cloudinary, delivered as responsive `c_limit,w_N,f_auto,q_auto` URLs (widths 128/320/640/960/1280 only). Everything else keeps the authorized Django route (with OL-07 derivatives). The stored original and its database reference are never replaced; a new table `common.PublishedMedia` (additive migration `0002`) maps *record + field + original version* to an immutable Cloudinary id.

## Exactly what may be published (initial set)
`games.game` icon / logo / banner / card_image, `ecommerce.brand` logo, `ecommerce.category` image.
Reason: a CDN copy cannot be revoked by a database flag, so only artwork whose disclosure is acceptable even after deactivation qualifies. **Excluded, stays on the authorized route:** shop products and product images, team and profile art, tournaments and sponsors (draft/visibility), community media, all KYC/evidence/payment/certificate fields. The legacy sensitive Cloudinary assets (the earlier 111) are never read, copied or transformed: the command only reads the fields above from the governed storage, uploads to the new `ownlobby-public/v1/` namespace with `overwrite=False`, and cannot name an existing id. Org brand art that is *already* on Cloudinary (hybrid) is not re-uploaded; it keeps the optional `OWNLOBBY_CLOUDINARY_TRANSFORMS` URL resize.

## Prerequisites
- Cloudinary configured on the host (`CLOUDINARY_URL`, or cloud name/key/secret); values are never printed. Upload and delivery need an account that allows `image/upload` delivery and on-the-fly transformations.
- Quota: storage ≈ one WebP master (≤1280 px, typically tens to a few hundred KB) per image; each *distinct* width requested first time is one transformation, so at most 5 per image. Bandwidth is the main ongoing cost driver. Check the plan's transformation/bandwidth allowance before step 3.
- Media mode `local`, `s3` or `hybrid` (production hybrid/legacy compatibility: `legacy` is unsupported, templates keep their URLs).

## Sequence (approval gate before steps 3, 5, 6)
1. Deploy with `OWNLOBBY_PUBLIC_CDN` unset (no behavior change) and run migrations (one new empty table).
2. Dry run (no provider contact): `python manage.py publish_public_media` → counts and ready mappings per model.
3. **Approval:** one small batch: `python manage.py publish_public_media --apply --model games.game --max-images 5 --max-pixels 8000000 --max-seconds 120` (`--max-images` is a hard cap on images; a game can hold up to four eligible fields, so `--limit` alone is not an image count; the lower `--max-pixels` keeps memory small next to the running web process on a 512 MB instance; larger sources are `skipped`). Output is counts only: `uploaded / already_present / unsupported / skipped / failed`. Repeat with `--after-pk <cursor>` until `complete`; then `ecommerce.category`, `ecommerce.brand`.
4. Verify: every `uploaded` is checked before the row is written (public id, `type=upload`, public access, version/size present). Spot-check one URL from the Django shell: `from apps.common.media import cdn; cdn.url(game.icon, "card")` once the flag is on, or open it in a browser.
5. **Approval:** set `OWNLOBBY_PUBLIC_CDN=1`, restart. Pages emit CDN URLs only for published, currently active, unchanged originals; all others keep their route. Images carry an `onerror` fallback to the original URL.
6. Measure for several days against the same pages: total image bytes, LCP (RUM or Lighthouse), 4xx/5xx for `res.cloudinary.com` image requests, Cloudinary bandwidth/transformation graphs.

## Future uploads, replacement, removal
- New or replaced approved artwork gets a new original name → new version → no CDN URL until `publish_public_media --apply` runs again (run it periodically, e.g. a Render cron job or by hand). Nothing blocks the upload or a page request. Until then the authorized route serves it.
- Deactivated or deleted records stop emitting the CDN URL immediately (checked per render), but the already-public Cloudinary file stays reachable by its URL until deleted from Cloudinary. Remove it manually in Cloudinary if disclosure is a problem. Originals are never deleted automatically.

## Stop conditions (the command exits non-zero and does nothing further)
Provider rate limit, refused credentials, an asset returned with unexpected id/visibility, the original changing during upload, or three consecutive failures. Cost anomaly: unset `OWNLOBBY_PUBLIC_CDN` (URLs revert at once) and stop running the command. Privacy anomaly: same, then delete the asset in Cloudinary and mark its `PublishedMedia` row `revoked`.

## Rollback
Unset `OWNLOBBY_PUBLIC_CDN` and restart: templates return to derivative/authorized URLs immediately. Rows and Cloudinary assets are inert.

## Not covered
Static CSS/JS (belong in the static pipeline), unreferenced oversized originals under `static/img/game_cards/LOGOS/` (~100 MB, not used by any template), Cloudinary authenticated/signed delivery for dynamic-visibility media (not enabled: needs plan support, expiry and revocation design), `legacy` mode.

## First production release (code-only) and rollback
Production ran `e15a8999`; the release carries exactly one new migration (`common.0002`: one new empty table, no change to existing tables, about 4 s; rehearsed forward, backward and forward again on a scratch database that had been migrated at `e15a8999`). Render builds do **not** migrate and boot does not migrate, and with the flags off nothing queries the new table, so the order below is safe.
1. **Approval A:** manual deploy of the merge commit (auto-deploy stays off). Existing media-mode, signing-key and storage settings unchanged; the three flags unset.
2. Smoke (read-only): `/healthz/`, `/`, `/tournaments/`, a game icon via `/files/...` (200, `private, max-age=900`), a protected file as its owner and as a stranger (stranger refused), login/logout.
3. **Approval A2:** `python manage.py migrate common` on production (additive; rollback `migrate common 0001`).
4. Read-only inventory: `python manage.py generate_image_derivatives` and `python manage.py publish_public_media` (both dry runs). Check Cloudinary plan/usage: `python manage.py shell -c "import cloudinary.api as a; u=a.usage(); print({k: u.get(k) for k in ('plan','transformations','bandwidth','storage')})"` (usage metadata only, no secret).
5. **Approval B:** the five-image batch above; verify (step 4 of the sequence); **Approval C:** `OWNLOBBY_PUBLIC_CDN=1`; measure before/after on `/`, `/tournaments/`, one game page on desktop and mobile (image bytes, LCP, TTFB, 4xx/5xx). `OWNLOBBY_PUBLIC_DERIVATIVES` (backfill first) and `OWNLOBBY_CLOUDINARY_TRANSFORMS` are separate later approvals.
**Rollback:** flags: unset and restart (instant, files inert). Code: redeploy `e15a8999` from the Render dashboard (the extra table is ignored by old code; no data change). Schema (only if wanted): `migrate common 0001` drops only `common_publishedmedia`. Databases, originals, secret keys and protected media are never touched by any step.
