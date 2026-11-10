# Integrations

## Supabase PostgreSQL

* Django connects directly to PostgreSQL through the Supabase pooler (`DATABASE_URL`, transaction pooler port 6543, `sslmode=require`); there is no Supabase client library, RLS identity mapping or Data API use. The Supabase **Data API was disabled by the owner on 2026-10-29** as containment and must stay off; Storage APIs are a separate surface. Provider-side verification and permanent privilege hardening are tracked as OL-01 in `Documents/Development/BACKLOG.md`.
* Use the session pooler (port 5432) with certificate verification for `pg_dump` backups; the Supabase CA certificate must be supplied locally.
* Connection reuse is controlled by `DB_CONN_MAX_AGE*` variables. Never use the production database for development or tests.

## Redis

`REDIS_URL` configures the Django cache (key prefix `dc`) and the Channels layer (`channels_redis`). Without it, local-memory cache and in-memory channel layer are used (single process only, no cross-instance coordination). Redis is not required for tests. Degraded-Redis behaviour under production load is not measured.

## Email

Production selects Resend SMTP (`smtp.resend.com`, STARTTLS 2587, user `resend`, password `RESEND_API_KEY`) when the key is present and `DEBUG` is off; otherwise optional Gmail SMTP (`EMAIL_HOST_USER`, `DeltaCrownEmailAppPassword`); local default is the console backend. The sender is `noreply@deltacrown.xyz` and its domain must be verified at Resend (unverified domains are rejected with 550). Transactional mail: signup OTP, password reset, notifications. Support mail: `BRAND_SUPPORT_EMAIL` (default `support@ownlobby.com`, forwarded by the registrar; forwarding is not an authenticated sending identity). Add provider SPF/DKIM exactly as issued and avoid two SPF records on one hostname.

## OAuth and game identity providers

| Provider | Purpose | Callback |
|---|---|---|
| Google | Sign-in | `/account/google/callback/` (redirect URI is built from `SITE_URL`; scopes `openid email profile`) |
| Discord | Account linking | `/account/discord/callback/` |
| Riot RSO | Game identity | `/api/oauth/riot/callback/` (`RIOT_REDIRECT_URI`; an API key alone is not RSO approval) |
| Epic | Game identity | `/api/oauth/epic/callback/` |
| Steam OpenID | Game identity | `/api/oauth/steam/callback/` |

Contracts: `ProviderAccount(provider, provider_account_id)` is the unique external-identity anchor; `GameOAuthConnection` links a game profile to a provider account. Signed state and nonce checks protect callbacks; Steam assertions are verified; provider ownership races are guarded. Existing callback paths, client identities and encryption keys must not change; `/profile/api/oauth` aliases remain. Google/Discord sign-in must keep the `next` parameter safe (same-host only). Add new-domain callbacks next to the old ones; do not remove old ones until traffic has moved.

## Media storage

`OWNLOBBY_MEDIA_MODE` selects the backend (`apps/common/media/configuration.py`, called from `deltacrown/settings.py`):

| Mode | Behaviour |
|---|---|
| `legacy` (default) | Existing storage (local files / Cloudinary default). Blocked by the release gate when persistent media is required |
| `local` | Local filesystem roots (development and QA) |
| `s3` | S3-compatible private storage |
| `hybrid` | Cloudinary CDN only for explicitly public organization logo/banner/badge; everything else (profiles, team artwork, draft tournaments, KYC, payments, disputes, certificates) in private S3-compatible storage (Supabase Storage S3 endpoint) with record-authorized delivery, no raw private URLs and no public fallback |

Rules that hold in every mode: confidential files are served only through record-authorized Django routes; public/private buckets are distinct; Supabase S3 keys bypass RLS across all buckets (keep server-only); unbound rich-text uploads are rejected in hybrid mode. There are 53 upload fields plus editor content (inventory in `branding/media-storage-inventory.json`). Verification flags (`MEDIA_STORAGE_VERIFIED`, `MEDIA_RESTORE_VERIFIED`, `MEDIA_LEGACY_PRIVACY_VERIFIED`) are owner attestations: never set them to silence a build check. Switching modes needs a verified copy of existing objects first; no deletion is part of any mode change. See the runbooks for derivatives, CDN delivery and origin throttling:

* [Public image derivatives](runbooks/public-image-derivatives.md): resized WebP variants (128/320/640/960/1280 px, never upscaled) next to originals, behind `OWNLOBBY_PUBLIC_DERIVATIVES` (off by default).
* [Public CDN delivery](runbooks/public-cdn-delivery.md): Cloudinary delivery of reviewed public artwork (off by default).
* [Media origin governor](runbooks/media-origin-governor.md): admission control for media origin reads so image bursts cannot starve the 512 MB service.
* [Signing-key rotation](runbooks/signing-key-rotation.md): `DJANGO_SECRET_KEY` rotation foundation (no key has been rotated).

## Certificates and S3

Tournament certificates are generated as PDFs (CairoSVG/ReportLab) and can be stored in S3 (`AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, keys from environment); S3 tests are opt-in (`S3_TESTS=1`).

## Discord

Webhooks (`DiscordWebhookLog`) post tournament events; the optional Discord bot is enabled with `ENABLE_DISCORD_BOT` and is off by default.
