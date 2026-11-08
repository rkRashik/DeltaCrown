# Media origin governor and ASGI liveness (OL-10)

Incident, 8 Nov (Render Free, 512 MiB): `/healthz/` timed out, instance restarted, Supabase "Connection pool is full", governed media requests took 2.5-24 s, memory 200 -> 363 MiB after a media burst. CPU was **not** saturated (0.07 of a 0.15 limit): the stalls were waiting on object-store reads with no concurrency bound.

## What changed (code only, no env/flag/data change)
- `deltacrown/fast_health.py`: `GET/HEAD /healthz/` is answered in the event loop before middleware, threads or the DB. Liveness only.
- `apps/common/media/origin.py`: one process-wide budget of `MEDIA_ORIGIN_CONCURRENCY` (default 3) private-origin reads. A request waits up to `MEDIA_ORIGIN_WAIT_SECONDS` (default 8, at most 24 waiters), otherwise a fast `503` + `Retry-After: 2`. Chunk reads use their own pool and 256 KiB chunks. The lease is released on close, on error and when a response abandoned by a disconnected client is garbage collected.
- boto client: `max_pool_connections=8` (> budget), `read_timeout=15`, 2 attempts.
- `/files/...` for public-intended artwork (all `derivatives.POLICY` fields except user-profile media) now carries an `ETag` and honours `If-None-Match` **after** authorization: unchanged images cost a 304 with no origin read. Stable art: `private, max-age=900`; visibility-dependent art (tournaments, teams, sponsors): `private, no-cache`. Everything else stays `private, no-store`.

## Not changed / still needed for small images
Originals of 2-8 MB are still what a first view downloads. The real fix is activating derivatives / the public CDN, which needs the owner to run the bounded commands with production credentials (never from CI):
1. `generate_image_derivatives --apply --model <m> --limit 20` per model (private storage writes only), then set `OWNLOBBY_PUBLIC_DERIVATIVES=1`.
2. `publish_public_media` (see `public-cdn-delivery.md`), then `OWNLOBBY_PUBLIC_CDN=1`.

## Verify after deploy
`/healthz/` stays ~1 ms under media load; Render logs show no "Connection pool is full"; `/files/games.game/icon/<pk>/` with `If-None-Match` returns 304; `request_mem route=governed_media` elapsed stays in the low seconds; RSS stays well under 400 MiB.

Rollback: redeploy the previous commit. No schema or data change is involved.

## How to run the production management commands (no new infrastructure)
Render Free has no shell, but the owner's machine already has a gitignored `.env` (read automatically by `deltacrown/settings.py`) holding the production database and storage credentials. Nothing is copied, committed or pasted anywhere. From the repo root, per command, set only non-secret process variables:

```
set OWNLOBBY_MEDIA_MODE=hybrid          (the .env says legacy; production runs hybrid)
set DISABLE_INPROCESS_MATCH_REMINDER=1  (REQUIRED: otherwise the settings start the match-reminder scheduler in this local process, against the production database)
.venv\Scripts\python.exe manage.py generate_image_derivatives            (dry run: counts only)
.venv\Scripts\python.exe manage.py publish_public_media                  (dry run: counts only)
```
Memory is not a Render concern: the work runs on the owner's machine; Render only serves the finished small files.

Dry run on 8 Nov 2026 (production): games 14 records / 44 images (11 games have files, none above 12 MiB, largest 8.7 MiB), tournaments 13, teams 4, profiles 56, organizations are CDN-published (not applicable), 0 Cloudinary mappings yet.

Suggested first batch (needs approval): `generate_image_derivatives --apply --model games.game --limit 20 --max-seconds 120` (11 games x 4 fields, ~220 small WebP files into the existing private storage, originals untouched), then tournaments, teams, profiles. Only afterwards: `OWNLOBBY_PUBLIC_DERIVATIVES=1` on Render.
