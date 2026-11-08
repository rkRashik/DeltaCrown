# Public image derivatives: rollout handoff (OL-07 / OL-07B)

**Status: code only, switched off. Nothing here has been run against production.** Every step below that changes production needs the owner's explicit approval.

## What it does
Resized WebP variants (icon 128, thumb 320, card 640, large 960, hero 1280 px; never upscaled) are stored next to each original, in the same storage, and used through `srcset` by the templates. Originals, URLs and database rows are never changed. Delivery stays on the authorized Django route; a missing derivative falls back to the original.

## Flags (all default off)
| Env var | Effect | Approval |
|---|---|---|
| `OWNLOBBY_PUBLIC_DERIVATIVES=1` | Templates emit derivative URLs; new uploads generate derivatives | Render env change + restart |
| `OWNLOBBY_CLOUDINARY_TRANSFORMS=1` | Hybrid mode only: org logo/banner/badge on the CDN are resized by Cloudinary URL transformations (no files are created by us) | Render env change; **counts toward Cloudinary transformation credits** |

Rollback: unset the flag. Templates return to original URLs immediately; derivative files stay inert.

## Fields
| Class | Fields | Cache (never `public`) |
|---|---|---|
| Eligible, stable | `games.game` icon/logo/banner/card_image; `ecommerce` brand.logo, category.image, product.featured_image/hover_image, productimage.image; `organizations.organization` logo/banner/badge (non-hybrid modes) | private, 15 min, ETag |
| Eligible, revalidate every time | `organizations.team` logo/banner; `tournaments.tournament` banner_image/thumbnail_image; `tournaments.tournamentsponsor` logo/banner_image; `user_profile.userprofile` avatar/banner | private, no-cache, ETag |
| Excluded | every KYC/evidence/payment/certificate field, `teammembership.roster_image`, `communitypostmedia` file/thumbnail (privacy/approval dependent), `matchmedia`, `gameprofile.rank_image`, arena thumbnails, `gamemappool.image`, `inventoryitem.icon`, `registrationformtemplate.thumbnail` (no template integration yet) | n/a |

Eligibility, authorization and caching are separate: the derivative route re-runs `policy.can_download` on the record (same as the original route), so a private profile, draft tournament, inactive game/product or hidden team gets 404 for the derivative exactly as for the original, with or without an ETag.

## Media-mode support
| Mode | Result |
|---|---|
| `legacy` | Not supported (direct storage URLs). Templates keep original URLs |
| `local`, `s3` | Supported for every eligible field |
| `hybrid` | Supported for fields served through the Django route (games, tournaments, sponsors, teams, profiles, shop). **Org logo/banner/badge are published on Cloudinary: no derivative files; optional URL transformations via `OWNLOBBY_CLOUDINARY_TRANSFORMS`** |

## Backfill (explicit, bounded, resumable; one model per run)
Run off-peak, after Step 1 below. Dry run first: `python manage.py generate_image_derivatives` (counts only). Then, per model, repeat until it prints `complete`:
`python manage.py generate_image_derivatives --apply --model <model> --limit 20 --max-seconds 120 [--after-pk <cursor>]`
Suggested order (most visible first): `games.game`, `tournaments.tournament`, `ecommerce.product`, `ecommerce.category`, `ecommerce.brand`, `organizations.team`, `tournaments.tournamentsponsor`, `user_profile.userprofile`, `organizations.organization` (non-hybrid only).
Output is status counts only (`generated/exists/missing/unsupported/too_large/error`). `too_large` (above 12 MiB / 24 MP) and `unsupported` (animated/malformed) keep the original. It writes **only new files into the existing media storage**.

## Sequence
1. Deploy with flags off (no behavior change).
2. Approval: bounded backfill, model by model (writes ~5 small files per image to the existing storage).
3. Verify: open the target pages with the flag still off, then check a sample derivative URL `/files/derived/...` returns `200 image/webp` (or a 302 to the original if not generated).
4. Approval: set `OWNLOBBY_PUBLIC_DERIVATIVES=1`, restart. New uploads also get derivatives (inline for sources up to 6 MiB / 4 MP; larger ones wait for the backfill).
5. Measure for a few days against the same pages before the change: total image bytes per page, LCP (field/RUM or Lighthouse), 4xx/5xx and 302-to-original counts for `/files/derived/`. A high 302 rate means the backfill is incomplete.
6. Optional, separate approval: `OWNLOBBY_CLOUDINARY_TRANSFORMS=1` (hybrid).

## Costs and limits
- Storage: about five small WebP files per image (typically a few hundred KB in total for multi-MB originals).
- CPU: roughly 0.3-0.8 s per image on a development machine; Render Free is slower and is **not measured**. Upload-time generation is capped (6 MiB / 4 MP) and never fails an upload; the backfill is serial, one image at a time.
- Bandwidth/origin: far fewer bytes, but every image still goes through Django (auth + storage read). A CDN/edge cache would remove that, but needs a purgeable cache and an owner decision; shared (`public`) caching is deliberately **not** enabled.
- Not covered: homepage artwork (static files), dashboard/team-hub/manage pages that build `logo_url` strings in views, replaced-image garbage collection.
