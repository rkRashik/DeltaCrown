# OwnLobby production domain migration

Status (2026-10-26): **No-Go pending the operational gates in OWNLOBBY_PRODUCTION_READINESS.md.** Local preparation is implemented and tested. No DNS, deployment, provider, mailbox or payment configuration changed.

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

## Verified configuration details from the readiness audit

- Code reads `DJANGO_DEBUG` and `DJANGO_SECRET_KEY`; the previous blueprint's `DEBUG` and generated `SECRET_KEY` names did not match. The local blueprint now uses the real names and preserves the existing dashboard-managed secret instead of generating a replacement. Confirm the live values; **do not rotate the key**. Field encryption can derive from it.
- The current `DATABASE_URL` is an external Supabase dependency. The local blueprint no longer declares an unrelated Render database binding. Preserve all current pooler/direct fallback URLs and database credentials. No schema migration is introduced.
- `start.sh` and `bin/start_render.sh` start Daphne with proxy-header handling; they do not start Celery, Beat, Discord or migrations. Confirm the separate worker, queues and Upstash limits in the dashboard. Keep the existing Render service name and hostname.
- Production defaults retain secure/HttpOnly/Lax session and CSRF cookies, HTTPS redirection, forwarded-proto handling and existing HSTS policy. Forwarded Host is not enabled. The broad default `.onrender.com` host was narrowed to `deltacrown.onrender.com`; review and remove any broad dashboard override separately after identifying legitimate hosts. Do not blindly copy the new local blueprint over a live environment.
- `WS_ALLOWED_ORIGINS` was assigned twice with inconsistent types. It is now parsed once; consumers accept both legacy strings and lists. The outer ASGI host-origin validator still applies to all WebSockets. Explicit restrictions must list both old/new required origins during transition, not `*`.
- Password-reset/verification links now use `SITE_URL`, while actual provider callback behavior differs: Google/Discord use the configured canonical base (with existing local/tunnel exceptions); Riot uses explicit `RIOT_REDIRECT_URI`; Epic/Steam derive their callback/realm from the request origin. Register and test the exact provider-specific behavior.
- Public redirect code is prepared under `PUBLIC_DOMAIN_REDIRECTS_ENABLED=0`. It requires the new apex canonical origin and only redirects approved successful anonymous HTML GET/HEAD responses. New-www login/signup/reset entry pages also move to apex before form submission. Callback, POST, API, private, authenticated, error and WebSocket traffic is excluded; the service hostname remains operational. Direct OAuth initiation must use the apex; do not advertise www API/OAuth links.

## Exact manual Render and Namecheap procedure

These are instructions for the owner after approval, not actions executed by this task. Record a secure before/after configuration export and named rollback owner. A local branch/commit cannot verify an authenticated dashboard.

1. **Before deployment:** confirm restorable Supabase backups and separately recoverable media, exact current Render build/start commands, service plan, environment groups, auto-deploy setting, active worker, Redis quotas and cron-job.org targets. Resolve durable/private media and verify SMTP on staging. No staging service is assumed to exist. Options are local disposable QA (completed), an isolated temporary environment, or separately approved paid staging compute/storage; do not clone production credentials or real private data into it.
2. **Staging:** build from the reviewed lockfile using `npm ci --include=dev`, `npm run build`, production Python dependencies, fail-visible `collectstatic` and `check --deploy`. `render_build.sh` now follows that sequence and deliberately does not migrate. No migration is required for this work. Verify production Python 3.12 on Linux; local execution used Python 3.13 on Windows, so this remains a platform-parity gate.
3. **Old-domain-compatible application release:** after separate push/deploy approval, deploy the reviewed commit with old `SITE_URL`, sender and callbacks, new-domain support/redirects disabled, and durable media confirmed. Observe health, errors, registration, settings, ranking and wallet read behavior. Keep the prior release available for rollback.
4. **Render domains:** inspect the existing `deltacrown` service Settings → Custom Domains. Determine whether the earlier Add Domain workflow actually saved either new domain. Add/verify both `ownlobby.com` and `www.ownlobby.com` only when approved. Review Render's paired-www behavior: domain addition can also configure redirects. Do not accept a blanket routing change before callback/API/session handling is approved.
5. **Reverify targets:** compare the current dashboard with the supplied root `A @ → 216.24.57.1` and `CNAME www → deltacrown.onrender.com`. [Render's current Namecheap instructions](https://render.com/docs/configure-namecheap-dns) support this record pattern and apex target. Use the actual service hostname shown at execution time; do not replace it with an invented OwnLobby service hostname.
6. **Namecheap:** Domain List → Manage → Advanced DNS. After approval remove only the conflicting `@` URL Redirect Record to `http://www.ownlobby.com/`; add the reverified apex A record and www CNAME. Review conflicting A/AAAA/ALIAS/CNAME/redirect records for those two hosts. Preserve unrelated TXT/MX/SPF, forwarding and verification records. Do not reset the zone or change nameservers. [Namecheap's conflict guidance](https://www.namecheap.com/support/knowledgebase/article/9837/46/how-to-connect-a-domain-to-a-server-or-hosting/).
7. **Routing/TLS:** verify DNS independently, Render ownership status and certificates for both hostnames. Existing old-domain and www certificates remain valid. Do not request a new HSTS preload or expand policy during cutover. Test edge forwarded-proto behavior, secure cookies, CSRF and WebSocket upgrade/Origin rejection. Keep `SITE_URL` old while new-origin smoke checks run with additive hosts.
8. **Provider preregistration:** register new callback URLs alongside old ones before changing canonical auth behavior. Verify state/session handling and link an existing test identity on staging. Keep the same client IDs/secrets, bot app/guild IDs and linked account records. Do not register callbacks at www unless the provider flow has explicitly been tested there.
9. **Functional acceptance:** verify login/logout and expected reauthentication across registrable domains; settings and team saves with valid CSRF; tournament registration/check-in and relevant match rooms; authorized/unauthorized WebSocket origins and private events; uploads and restart persistence; real verification/reset mail through the selected provider. Financial smoke checks must be read-only or approved sandbox flows, never live money movements.
10. **Canonical switch:** after acceptance and approval, set `SITE_URL=https://ownlobby.com` on web and relevant workers, set explicit Riot redirect URI if that integration is approved, restart/redeploy as required, refresh public caches, and update the existing Django Sites record to the new domain/name if allauth/Sites uses it. Do not create a replacement Site ID blindly. Verify robots, sitemap XML, page canonicals, mail links and provider callbacks immediately.
11. **SEO/monitoring:** verify Search Console properties, submit the new sitemap, inspect redirects/canonicals and watch 404/5xx, rejected origins, mail errors, database connections, Upstash commands and worker queue depth. Update monitoring labels/health targets only after the new endpoint is proven; retain the working service-host health check as a fallback.
12. **Final redirects:** after observation, explicitly approve `PUBLIC_DOMAIN_REDIRECTS_ENABLED=1` and test a path/query matrix before enabling it. Test new-www public and auth-entry pages; old-domain public pages; old logged-in sessions; and excluded callbacks/API/POST/WS. Run Change of Address only after eligible verified properties and functioning public redirects are confirmed. Keep old ownership, DNS, TLS and integration routes through the migration window.

## Provider callback matrix

All routes below were reversed in local regression tests. Credentials present locally do not prove the same live applications are enabled.

| Provider | New callback / behavior | Manual prerequisite |
| --- | --- | --- |
| Google | `https://ownlobby.com/account/google/callback/` | Add exact authorized redirect; inspect consent/authorized domain settings; preserve old callback. Both standard and legacy client-env aliases remain supported. |
| Discord account linking | `https://ownlobby.com/account/discord/callback/` | Add exact OAuth redirect in the existing application. Preserve app/bot IDs, token, guild setup, scopes and webhook targets. |
| Riot RSO | `https://ownlobby.com/api/oauth/riot/callback/` | Confirm RSO approval/application allowlist; update `RIOT_REDIRECT_URI` only after provider setup. A Riot API key alone is not RSO approval. |
| Epic | `https://ownlobby.com/api/oauth/epic/callback/` | Verify existing product/client callback policy; callback is derived from request origin. Do not change deployment/sandbox/client identity. |
| Steam OpenID | `https://ownlobby.com/api/oauth/steam/callback/`; realm new apex | Verify return_to/realm and any API-domain registration. Preserve Steam IDs; API enrichment key and OpenID login have different requirements. |

## Email transition and contacts

Local source selects Resend SMTP (`smtp.resend.com`, STARTTLS port 2587) when a Resend key is present in production; optional legacy Gmail SMTP otherwise requires its existing password alias. Local audit uses console mail, not a working production SMTP configuration. The configured sender address remains `noreply@deltacrown.xyz`; independent verification in the actual provider is an owner gate, not an inference from its spelling.

`ownlobbyhq@gmail.com` is the owner-supplied existing administrative inbox. `hello@`, `support@` and `noreply@ownlobby.com` are **desired, unverified** addresses and were not substituted for functioning destinations. Existing public support/social destinations remain controlled by `BRAND_SUPPORT_EMAIL` and `BRAND_*_URL`; inventory old references and confirm each actual OwnLobby account before updating them. `@ownlobbygg` identifies the intended social identity but does not prove ownership of every platform URL.

Incoming Namecheap forwarding can deliver aliases to the administrative inbox; it does not provide authenticated transactional SMTP sending or automatically establish an independent mailbox. Retain its existing required SPF/forwarding records. Add provider-specific SPF/DKIM records exactly as issued; avoid competing SPF policies on one hostname, and keep existing senders authorized. Establish DMARC reporting and alignment, then tighten policy after delivery is verified. Configure bounce/complaint handling and test reset/OTP mail at multiple recipient providers before switching `DEFAULT_FROM_EMAIL`. Replies/support handling and incoming forwarding need separate tests. [Namecheap forwarding](https://www.namecheap.com/support/knowledgebase/article.aspx/308/2214/how-to-set-up-free-email-forwarding/), [Resend SMTP](https://www.resend.com/changelog/smtp-service).

## Safe infrastructure renaming later

Treat cosmetic names as a separate approved change after domain stability. For GitHub, inventory remotes, actions, deploy hooks, app permissions, branch protection, badges and package URLs before rename; verify redirects and explicitly update clients. For Render, a display-name/service-slug change can affect the onrender hostname, custom-domain CNAME target, hooks, monitors and callbacks: preserve the hostname through initial cutover. Supabase project display-name changes must preserve project ref, database host/password, pooler, storage URLs and API keys. Monitoring labels can change after checking target URLs, incident routing and scheduled secrets. Do not rename Django apps/tables, reconstruct services or rotate credentials for branding.

## Rollback additions

Prefer an environment/routing rollback while retaining the security corrections. A code rollback to the earlier checkpoint reintroduces the JSON-LD and tournament visibility defects identified in the readiness report; assess containment and restore those fixes rather than treating an older artifact as automatically safe.

First disable `PUBLIC_DOMAIN_REDIRECTS_ENABLED`; restore the last approved `SITE_URL` and Riot/provider origin settings, redeploy the prior approved artifact if needed, and confirm old auth/CSRF/WS behavior. Keep additive new host/callback entries while diagnosing unless they introduce a verified risk. Restore Namecheap's saved records only under explicit rollback authority and avoid deleting mail/verification TXT records. DNS caches may retain both routes, so both origins need safe handling. This release has no schema migration: do not restore a stale database backup over new user transactions merely to undo code. Storage backfill or ACL changes require their own rollback plan. Record incident times, lossless data checks, mail/queue status and owner approval before resuming cutover.
