# OwnLobby production domain migration

Status: preparation only. No DNS, production deployment, external provider, mail-account or payment configuration was changed. The purchased domain does not make the application ready for cutover.

## Configuration delivered

`OWNLOBBY_DOMAIN_ENABLED=0` is the default. Setting it to `1` adds `ownlobby.com` and `www.ownlobby.com` to Django hosts and HTTPS CSRF origins. Existing old-domain entries remain accepted. Explicit `CSRF_TRUSTED_ORIGINS` entries are additive. Keep existing environment host entries when adding new ones.

`SITE_URL` controls canonical, social-image, notification and generated absolute URLs. Its production default remains `https://deltacrown.xyz`. Brand identity can therefore ship before changing the canonical origin. `branding/environment.example` contains non-secret examples, not a replacement for the production environment.

CORS retains its existing exact-origin environment configuration. The ASGI `AllowedHostsOriginValidator` uses `ALLOWED_HOSTS`; `WS_ALLOWED_ORIGINS` alone does not govern the entire WebSocket stack. Test the actual deployed proxy and ASGI service together. Do not introduce wildcard credentialed origins.

`DEFAULT_FROM_EMAIL`, `BRAND_SUPPORT_EMAIL` and the three `BRAND_*_URL` social settings support a later verified transition. The current sender, support address, social destinations and all credential aliases remain defaults. Existing SMTP aliases, integration IDs and secrets must continue to work.

## Before scheduling cutover

- Resolve or explicitly accept the existing release issues in `OWNLOBBY_VALIDATION.md`; verify staging with a realistic, access-controlled data set. Back up production data through the existing approved process. This rebrand has no database migration.
- Inventory hosting, CDN/object storage, reverse proxy, registrar, certificate automation, Django Sites (`SITE_ID`), analytics/search properties and OAuth/Discord application ownership. Record current configuration securely without copying secrets into Git or QA reports.
- Confirm the new domain's ownership and intended apex/www behavior. Obtain exact DNS targets from the hosting provider; do not invent IP addresses. Lower TTL in advance through an approved DNS change.
- Provision and verify TLS for both new hostnames before making either canonical. Keep old-domain certificates and routing valid throughout transition and rollback.
- Register both old and new callback origins with providers where supported. Preserve provider client IDs, bot IDs, tokens, scopes and existing linked-account identifiers.
- Verify the actual callbacks: Google `/account/google/callback/`; Discord `/account/discord/callback/`; Riot `/api/oauth/riot/callback/`; Epic `/api/oauth/epic/callback/`; Steam `/api/oauth/steam/callback/`. Riot also has explicit `RIOT_REDIRECT_URI`; inspect each enabled provider's existing callback settings before changing them. Include Discord bot links, webhooks, app links and any embedded allowlists in this review.
- Verify a new mail sender and mailbox first. Complete the mail provider's SPF, DKIM and DMARC requirements without removing records still used by the old sender. Confirm support delivery, bounce handling and password-reset delivery. Keep the old sender until this succeeds.
- Inventory custom-domain static/media URLs, CORS at storage/CDN, CSP, fonts, embeds, newsletter destinations and stored CMS/site-settings content. Rebranding source templates does not rewrite stored legal text, old tournament records or externally managed pages.

## Approved deployment order

1. Deploy and validate the reviewed application on staging using its own database, mail sink and provider test setup. Build with `npm ci` followed by `npm run build`. Run the existing release checks and production static processing; investigate the existing design-token warning rather than assuming exit code zero proves a clean pipeline.
2. After separate deployment approval, release the branding while retaining the old canonical `SITE_URL`, sender and enabled old host. Leave new-domain support disabled until routing and TLS are ready.
3. Add the new hosting/CDN routing and approved DNS records. Enable new-domain hosts/CSRF additively; add exact CORS origins wherever genuinely needed. Keep old routing, callback URLs and sender working. Validate HTTPS, forwarded-host/proto behavior and WebSocket upgrade handling on both domains.
4. Exercise login/logout, OAuth linking, CSRF-protected saves, reset/verification email links, real-time updates, tournament registration, Team HQ and wallet display in staging and then approved production smoke checks. Do not execute financial transactions merely to test branding.
5. Change canonical `SITE_URL` to `https://ownlobby.com` only after those checks pass. Update the existing Django Sites record through the approved operational process if Sites/allauth uses it. Confirm canonical tags, sitemap/robots, OG images, certificate links, notifications and email links use the new origin. Inspect authenticated responses for `private, no-store` and purge only public CDN caches.
6. Switch verified sender/support/social settings separately when their external setup is ready. Preserve historical transactions, already-sent messages and generated documents.
7. After an agreed observation period, approve old-domain redirects for public safe GET/HEAD pages, preserving paths and query strings. Do not blindly redirect POSTs, OAuth callbacks, API clients, webhook targets or WebSockets. Drain active sessions/matches and migrate external clients deliberately. Keep the old domain registered, TLS valid and an operational rollback route.

## Cookies and sessions

Cookies cannot be shared across the unrelated `.xyz` and `.com` registrable domains. Expect a fresh login on the new domain. Preserve secure, HttpOnly, SameSite and CSRF protections; do not weaken cookies to make migration appear seamless. Inspect any explicitly configured session/CSRF cookie domain and provider state-cookie behavior. Keep old-domain sessions working during the transition window.

## Rollback

Restore the previously approved application release and canonical/environment values using the established deployment system. Remove or bypass new redirect rules, restore old callback routing if changed, and retain old-domain DNS/TLS and the verified sender. Keep database data and wallet history intact; this change requires no reverse schema migration. Leave new DNS/provider entries in a safe additive state while investigating rather than rotating credentials or deleting accounts. Verify login, CSRF, old-domain links and WebSocket origins after rollback.

## Owner actions

Approve the deployment and cutover window separately; supply access or arrange changes with the registrar/host, OAuth and Discord application owners, and mail provider; confirm final support/social destinations and legal brand usage. No external configuration action is required to review this local implementation.
