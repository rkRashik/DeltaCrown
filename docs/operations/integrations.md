# Integrations

Purpose: how OwnLobby talks to external services (database, Redis, email, OAuth providers, media storage, Discord) and what is verified versus assumed. **"Unverified" means the repository cannot prove the production configuration**; check the Render dashboard or the provider console. Related: [deployment](deployment.md), [security](security.md), [environment reference](../reference/environment.md).

## Supabase PostgreSQL

* `DATABASES` is built from `DATABASE_URL` in `deltacrown/settings.py` with `sslmode=require`. Django connects directly to PostgreSQL (the owner's setup uses the Supabase pooler, normally the transaction pooler on port 6543); there is no Supabase client library, RLS identity mapping or Data API use. The Supabase Data API was disabled by the owner on 2026-10-29 as containment and must stay off (OL-01 in `Documents/Development/BACKLOG.md`). Storage APIs are a separate surface.
* Pooler-aware connection tuning: `DB_CONN_MAX_AGE_*`, `DB_CONN_HEALTH_CHECKS`, `DB_DISABLE_SERVER_SIDE_CURSORS`. Use the session pooler (port 5432) with the Supabase CA certificate for `pg_dump`; the transaction pooler is not suitable for dumps.
* Never use the production database for development or tests ([setup](../getting-started/setup.md#2-create-the-local-databases)).

## Redis

`REDIS_URL` provides database 0 (Django cache, key prefix `dc`), 1/2 (Celery) and 3 (Channels layer). Without it the cache is in-process memory and, in development, the channel layer is in-memory (single process only, no cross-instance coordination). In production the channel layer is Redis (`channels_redis`). Whether production has `REDIS_URL` set, and its behaviour under load, are unverified.

## Email

Selection happens in `deltacrown/settings.py` ("Email" block), first match wins:

1. `RESEND_API_KEY` set and `DEBUG` off: Resend SMTP (`smtp.resend.com`, port 2587, STARTTLS, user `resend`, password = the API key).
2. `DEBUG` on (and `USE_SMTP_EMAIL_IN_DEBUG` not `1`): console backend, mail is printed.
3. `DeltaCrownEmailAppPassword` set: Gmail SMTP (`smtp.gmail.com:587`, user `EMAIL_HOST_USER`, default `deltacrownhq@gmail.com`).
4. Otherwise: console backend (nothing is delivered, also in production).

`DEFAULT_FROM_EMAIL` defaults to `noreply@deltacrown.xyz` and is overridden by the environment variable of the same name; `normalize_from_email` (`apps/accounts/emails.py`) formats it with the brand name. The sender domain must be verified at the provider (Resend rejects unverified domains). Which backend and sender production uses is **unverified here**; confirm with a real OTP email after a deploy. Contact addresses: `BRAND_SUPPORT_EMAIL` (code default `support@ownlobby.com`, which the registrar forwards; forwarding is not an authenticated sending identity). Add provider SPF/DKIM exactly as issued and avoid two SPF records on one hostname.

## OAuth and game identity providers

| Provider | Purpose | Callback (route) |
|---|---|---|
| Google | Sign-in | `account/google/callback/`. Redirect URI = `SITE_URL` + path (`_build_google_redirect_uri` in `apps/accounts/views.py`; localhost and tunnel hosts use the request host). Scopes `openid email profile`, `access_type=offline`, `prompt=consent`. The state value is stored in the session, checked and consumed before the token exchange |
| Discord | Account linking | `account/discord/callback/` |
| Riot RSO | Game identity | `api/oauth/riot/callback/` (and `profile/api/oauth/...` alias); `RIOT_REDIRECT_URI`, `RIOT_OAUTH_SCOPES` |
| Epic | Game identity | `api/oauth/epic/callback/` |
| Steam OpenID | Game identity | `api/oauth/steam/callback/` |

Data model: `ProviderAccount(provider, provider_account_id)` is the unique external identity and `GameOAuthConnection` links a game profile to it (`apps/user_profile/models/oauth.py`); tokens are stored encrypted (`FIELD_ENCRYPTION_KEY`, `reencrypt_oauth_tokens`). Existing callback paths and client identities must not change; when adding a new domain register the new callback next to the old one. Google sign-in keeps the validated `next` parameter. Whether the Google client, Riot RSO approval and the other provider applications are correctly configured in production is **unverified here**; a live Google redirect reaching `accounts.google.com` shows the client id exists, not that the redirect URI is authorised.

## Media storage

The mode and flags below are **code defaults**. The values actually set in production (mode, `*_VERIFIED` flags, `OWNLOBBY_PUBLIC_DERIVATIVES`, `OWNLOBBY_PUBLIC_CDN`) are unverified in this repository; read the Render environment before assuming a mode.

`OWNLOBBY_MEDIA_MODE` selects the backend (`apps/common/media/configuration.py`, called from `deltacrown/settings.py`):

| Mode | Behaviour |
|---|---|
| `legacy` (code default) | Existing storage (local files / Cloudinary default). Blocked by the release gate when persistent media is required |
| `local` | Local filesystem roots (development and QA) |
| `s3` | S3-compatible private storage |
| `hybrid` | Cloudinary CDN only for explicitly public organization logo/banner/badge; everything else (profiles, team artwork, draft tournaments, KYC, payments, disputes, certificates) in private S3-compatible storage (Supabase Storage S3 endpoint) with record-authorized delivery, no raw private URLs and no public fallback |

Rules for the non-legacy modes (`legacy` keeps public and confidential uploads on the same default backend, with no separate private delivery, which is why the release gate blocks it for persistent media): confidential files are served only through record-authorized Django routes; public/private buckets are distinct; Supabase S3 keys bypass RLS across all buckets (keep server-only); unbound rich-text uploads are rejected in hybrid mode. There are 53 upload fields plus editor content (inventory in `branding/media-storage-inventory.json`). Verification flags (`MEDIA_STORAGE_VERIFIED`, `MEDIA_RESTORE_VERIFIED`, `MEDIA_LEGACY_PRIVACY_VERIFIED`) are owner attestations: never set them to silence a build check. Switching modes needs a verified copy of existing objects first; no deletion is part of any mode change. See the runbooks for derivatives, CDN delivery and origin throttling:

* [Public image derivatives](../runbooks/public-image-derivatives.md): resized WebP variants (128/320/640/960/1280 px, never upscaled) next to originals, behind `OWNLOBBY_PUBLIC_DERIVATIVES` (off by default).
* [Public CDN delivery](../runbooks/public-cdn-delivery.md): Cloudinary delivery of reviewed public artwork (off by default).
* [Media origin governor](../runbooks/media-origin-governor.md): admission control for media origin reads so image bursts cannot starve the 512 MB service.
* [Signing-key rotation](../runbooks/signing-key-rotation.md): `DJANGO_SECRET_KEY` rotation foundation (no key has been rotated).

## Certificates and S3

Tournament certificates are generated as PDFs (CairoSVG/ReportLab) and can be stored in S3 (`AWS_STORAGE_BUCKET_NAME`, `AWS_S3_REGION_NAME`, keys from environment); S3 tests are opt-in (`S3_TESTS=1`).

## Discord

Webhooks (`DiscordWebhookLog`) post tournament events; the optional Discord bot is enabled with `ENABLE_DISCORD_BOT` and is off by default.
