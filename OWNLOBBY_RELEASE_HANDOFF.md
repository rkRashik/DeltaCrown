# OwnLobby release handoff

## Decision

**No-Go for production deployment/cutover; local corrections are an isolated staging candidate.** Phase 3 dependency updates are implemented, but the Twisted HTTP parser finding, Linux/runtime validation and the infrastructure gates below remain required. Nothing was pushed, deployed, purchased or changed in DNS, production providers, mail or payment settings.

## Phase 3 dependency handoff (2026-10-26)

Implementation commit: **`e7d648e2c3cd294fc3895ad0feb846fe7770e049`** (`fix: remediate OwnLobby production dependency advisories`), on `feature/ownlobby-dependency-security`. Recorded by a documentation-only follow-up; implementation history is unchanged. Working tree was clean after that commit; no push/deploy.

- **Changed:** compatible security upgrades in both requirements files; Docker production now uses the same runtime source as Render. Maintained pypdf replaces unsupported PyPDF2; PDF preview's undefined reader references are fixed. No schema/business/financial/provider changes. All 69 approved asset hashes remain identical.
- **Fixed:** 191 of 197 underlying baseline advisories. Raw entries decreased 308 to 6; affected packages 29 to 1. Clean runtime install and pip check pass. Full matrix/inventory are committed under branding/; see [dependency report](OWNLOBBY_DEPENDENCY_SECURITY.md).
- **Remaining security blocker:** Twisted 26.4.0 HTTP bare CR/LF parser advisory GHSA-q7qq-6mhp-9rc4; only a prerelease fix is currently listed. A bounded local transport test confirms parser acceptance; actual Render proxy behavior is unverified. Five unused-protocol Twisted findings remain installed and documented. Dependency gate is **not resolved**.
- **Compatibility evidence:** final focused 211 pass/one Cairo skip; workflow 60 pass/one existing skip. Expanded mocked OAuth/offline storage: 38 pass/seven failures/eight skips, with identical outcomes in the original environment. No observed passing-test regression. Linux/Python 3.12 execution and native Cairo remain unverified; wheel availability alone is not parity.
- **Visual evidence:** 12 guest viewport checks pass; mobile homepage has two disclosed accessibility findings, mobile login none. Static collection/build succeeds; unchanged dormant optional template failure remains. See [commands and limits](OWNLOBBY_DEPENDENCY_VALIDATION.md).
- **Owner next steps:** arrange review and completion of the stable Twisted fix/backport and isolated Linux 3.12/Cairo validation; investigate baseline OAuth failures. Then complete storage/recovery, staging, mail/providers and existing approval gates below. No dashboard action is needed merely to review these local dependency changes. No new variables or credentials are required.
- **Do not change yet:** production dependencies, Render runtime/service names, DNS, secrets, callbacks, sender, canonical origin, redirects or remote branches. Do not deploy this intermediate security candidate.
- **Rollback point:** Phase 2 `00fa31d942386ca0e9d42fbd553d4ff7eb81cc83`; empty safety checkpoint `c797aeab7917cf258884954bdbad2ea3cea6078f`; task branch `feature/ownlobby-dependency-security`. Restore dependency artifacts by rebuilding a separate clean environment at the reviewed commit; do not mutate production or rewrite history. Reverting this local change would also restore known vulnerabilities, so it is not a recommended production release.

The Phase 2 validation table below remains historical except for its updated dependency row; current Phase 3 evidence is summarized above. The existing manual environment-variable table and domain migration sequence remain unchanged. No production-sensitive variable was introduced by Phase 3.

## Git and rollback point

Started from clean `feature/ownlobby-rebrand` at `ece37c2fa5fc9f81305375684d2c8e606c9e2c88`. Readiness checkpoint: `c525ffb7be6ebca1c17d3bdd07e6650b6d738ffb`. Task branch: `feature/ownlobby-production-readiness`.

Implementation commit: **`8dff4da78162a986ca5e1c8d93d8a4a15f6c774d`** — `fix: harden OwnLobby release readiness and technical SEO`. This SHA is recorded by a documentation-only follow-up; the implementation history is not rewritten.

## Changed and fixed

- Fixed JSON-LD script escaping; draft tournament read access; private WebSocket event recipients; inconsistent origin parsing; double-counted connection gauges; a missed async dispute broadcast; and a PostgreSQL profile-cache locking error. Wallet/ledger amounts, IDs, APIs and schema remain unchanged.
- Corrected settings/WebSocket fixture and assertion defects while retaining actual CSRF, JWT and Origin rejection. Fixed four reachable broken templates and the 30,000-point Crown caption. Newsletter UI/backend no longer pretend to subscribe anyone.
- Implemented controlled canonical/query handling, sensitive-route noindex headers, paginated public/privacy-aware sitemaps, accurate event mode/status metadata, origin-safe verification/reset links and a disabled public redirect feature.
- Made the Render build use locked frontend dependencies and both build outputs, propagate static-processing errors, avoid build-time migrations and use the actual secret/debug names plus existing external database binding. Added a deploy-time persistent-media gate.
- Preserved all 69 approved assets, branding, homepage personalization, settings behavior, existing account/provider identities and old-domain compatibility. No Django model or migration file changed.

## Validation

| Category | Result |
| --- | --- |
| Focused Django suite | **197 passed**, including repaired settings tests and new SEO/privacy, mail, origin, media-gate and wallet-sync regressions. |
| Workflow suite | **60 passed, 1 skipped**, including WebSocket security/broadcasts and inactive-user denial, tournament registration, Game Passport, CP pipeline and email sender normalization. The existing CP pipeline case cannot create a Match without a tournament FK and skips; it is not counted as passing. |
| System checks | Local QA check has no errors; expected filesystem-media warning. A separate production-mode local check deliberately blocks with `siteui.E001`. No live configuration check was performed. |
| Templates | **353 compile; 1 existing dormant optional crispy integration fails** because its dependency is not installed. No active reference was found. Four reachable failures are fixed; no new compile regression. |
| Assets/static/build | 69 approved copies verified; locked `npm ci --include=dev` and combined build pass; production-style collectstatic passes without error suppression; critical hashed entries resolve. |
| Domain/security | Three production-mode old/additive/new-canonical configurations pass; three unsafe canonical origins rejected; secure cookies retained. Trusted old/new WS origins accepted, untrusted/missing origins and invalid/expired tokens denied. |
| Frontend syntax | Ten relevant standalone/build entry points pass `node --check`; affected inline behavior is exercised in browser QA. Shell scripts pass `bash -n`; Render YAML parses. |
| Dependency audit | **Phase 3: 308 raw entries / 197 underlying advisories reduced to six in Twisted; 191 fixed.** Clean production install/pip check and both requirement resolutions pass. Public HTTP advisory plus Linux/runtime validation keep gate open. Existing four moderate npm findings remain separate. |
| Browser | 24 page/viewport checks at 360/768/1440 pixels return 200 without overflow or page JavaScript errors. Old/new Host requests use the selected canonical sitemap. Six sitemap XML endpoints return 200. |
| Accessibility | Homepage/login/teams desktop and settings/wallet mobile scans pass. Tournament scans pass at 360/768/1440 after scoped semantic/name/contrast fixes. Desktop section and mobile share keyboard activation pass. Scope is not an accessibility certification. |
| Not tested live | Render Linux/Python 3.12 execution, true staging, remote Supabase/Upstash/worker load, provider callbacks, SMTP deliverability/bounces, production upload ACLs/persistence, backup restoration, real financial transactions, full device/browser matrix, load/Core Web Vitals. |

Evidence is retained locally under ignored `Artifacts/readiness/`, including logs, redacted configuration findings and screenshots. Synthetic users/sessions are not committed. The prior reports describe an earlier checkpoint; this report supersedes their unresolved test/static/template findings.

## Release blockers and owner actions, in order

**Security prerequisite (updated):** complete the remaining Twisted HTTP parser remediation and Linux/Python 3.12/native-runtime validation described in the Phase 3 handoff. Investigate the seven reproduced baseline OAuth failures. Most dependency advisories are now fixed; the combined release is still blocked. No residual-risk acceptance occurred.

1. **Storage and recovery:** confirm the actual production storage backend. Prove public media durability and confidential evidence/KYC authorization with restore and restart tests. Do not simply add public Cloudinary storage for private documents. Choose/approve any storage costs and migration plan before moving uploads. Back up Supabase and media; demonstrate a restore in isolation.
2. **Live configuration/staging:** compare actual Render dashboard commands, plan, auto-deploy, environment groups, secret/debug names, Supabase URL and existing worker/Upstash/cron setup with the reviewed files. Establish an isolated staging environment or approve its costs, then run the platform-parity and functional checks. Keep the existing secret values, service/database identities and working monitor targets.
3. **Mail and identity:** verify the current SMTP sender and delivery, then authenticate the future OwnLobby domain with the selected mail provider. Confirm forwarding/mailboxes, SPF/DKIM/DMARC, bounces and recipient tests. Confirm `@ownlobbygg` URLs and public support destination; the desired professional addresses are not yet verified. Do not substitute them prematurely.
4. **Separate release approval:** approve the exact commit, push/deployment window and rollback owner. Deploy old-domain-compatible code first only after the preceding gates pass. No schema migration is required.
5. **Manual domains/providers:** follow `OWNLOBBY_DOMAIN_MIGRATION.md` for Render custom domains, reverified DNS targets, Namecheap conflicting-record removal, ownership/TLS, both-origin acceptance and callback preregistration. No dashboard operation has been completed by this task.
6. **Canonical/SEO/redirect approval:** after real functional checks, change the canonical origin, relevant Sites/provider settings and worker environment; submit sitemaps and inspect Search Console. Enable redirects only after a separate observed approval. Keep old callbacks/POST/API/WS/session handling working.

## Manual environment-variable table

These are dashboard changes for an approved release, **not values written to the live environment**. Web and relevant workers need consistent link/branding settings. Changes generally need a restart/redeploy; preserve existing secret values and record previous settings securely outside Git.

| Variable | Purpose | Current/default behavior | Required value / safe placeholder | When | Restart/redeploy | Security considerations |
| --- | --- | --- | --- | --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | Runtime settings | `deltacrown.settings` in blueprint | Keep `deltacrown.settings` | All production phases | Yes | Never use QA settings in production. |
| `DJANGO_DEBUG` | Actual debug switch | Code reads this, not `DEBUG` | `0` | Staging/production | Yes | Do not expose debug pages. Audit stale `DEBUG` separately. |
| `DJANGO_SECRET_KEY` | Actual Django signing key | Existing secret / legacy blueprint mismatch | **Existing secret unchanged** | Verify before deployment | Yes if setting mapping corrected | Do not rotate; sessions/signatures and derived field encryption depend on it. |
| `DATABASE_URL` | Existing Supabase database | Existing external connection | **Existing dashboard secret unchanged** | Verify before deployment | Yes | Never replace with a newly created Render DB; never use it in tests. |
| `SUPABASE_DIRECT_DATABASE_URL` and pooler controls | Existing fallback behavior | Existing settings | Preserve current reviewed values | Verify operationally | Yes | Credentials remain private; no connectivity experiment against production. |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | Cache/Channels/tasks | Existing Upstash routing and overrides | Existing reviewed URLs | Verify before deployment | Yes, including worker | Preserve TLS, credentials, DB/queue routing and resource limits; never print URLs. |
| `OWNLOBBY_DOMAIN_ENABLED` | Add new host/CSRF support | `0` by default | `0`, then `1` | After routing preparation/approval | Yes | Additive; does not itself change DNS or canonical origin. |
| `SITE_URL` | Canonical and generated link origin | Production default old domain; local `.env` uses LAN origin | `https://deltacrown.xyz`, later `https://ownlobby.com` | New canonical only after acceptance | Yes, web/workers | HTTPS origin only, no path, credentials or query. |
| `ALLOWED_HOSTS` | Exact HTTP/outer WS hosts | Built-in old/new gated hosts plus exact Render hostname; env additive | Retain actual required hosts, add exact new hosts as needed | Transition | Yes | No `*` or broad unrelated Render tenant wildcard. |
| `CSRF_TRUSTED_ORIGINS` | Extra HTTPS POST origins | Existing old entries; flag adds new entries | Exact old/new HTTPS origins if explicitly needed | Transition | Yes | No wildcard credentialed-origin shortcut. |
| `CORS_ALLOWED_ORIGINS` | Browser cross-origin API clients | Empty in production unless configured | Existing exact clients; add new HTTPS origins only where needed | Before cross-origin clients move | Yes | Same-origin Django pages need no extra CORS permission. Preserve credentials policy. |
| `WS_ALLOWED_ORIGINS` | Additional consumer allowlist | Parsed list; empty leaves outer host validation active | Include every required old/new exact HTTPS origin if nonempty | Before new-origin WS testing | Yes | Example: old apex/www and new apex/www; never `*`. Outer ASGI validator remains active. |
| `PUBLIC_DOMAIN_REDIRECTS_ENABLED` | Prepared public redirects | `0` | Keep `0`; later `1` only after approval | Final migration stage | Yes | Excludes integrations/private traffic. New-www auth-entry GET pages move before forms; callback/start links must use tested origins. |
| `REQUIRE_PERSISTENT_MEDIA` | Block ephemeral-media releases | Defaults `1` when `RENDER` is present, otherwise `0` | `1` in approved production environment | Before deployment | Yes | Resolve storage; do not bypass `siteui.E001`. |
| `CLOUDINARY_URL` or reviewed storage configuration | Durable media backend | Absent locally; live unknown | Provider-issued secret, **after storage/privacy decision** | Before upload/persistence acceptance | Yes | Public images and private KYC/payment evidence need appropriate separate access policies. No purchase/backfill authorized here. |
| `DEFAULT_FROM_EMAIL` | Transactional sender | Existing old-domain address remains | Keep verified sender; later `OwnLobby <noreply@ownlobby.com>` | Only after authentication/delivery checks | Yes, web/workers | Desired address is not proof of sender ownership. Display-name changes alone do not verify a domain. |
| `RESEND_API_KEY` / existing Gmail credential aliases | Outgoing mail authentication | Production Resend path or optional legacy SMTP; local console | Existing provider secret, not a report value | Verify before auth-mail acceptance | Yes | Forwarding does not supply SMTP; no credential rotation. |
| `BRAND_SUPPORT_EMAIL` | Public support destination | Existing old-domain default | Verified working destination; later `support@ownlobby.com` | After receiving/support tests | Yes | Owner-provided admin inbox exists; approve its public use separately if desired. |
| `BRAND_FACEBOOK_URL`, `BRAND_YOUTUBE_URL`, `BRAND_DISCORD_URL` | Public account destinations | Existing accounts/invite remain defaults | Verified actual OwnLobby URLs | After account ownership confirmation | Yes | Do not invent URLs from a shared handle or replace Discord integration IDs. |
| `RIOT_REDIRECT_URI` | Explicit RSO callback | Existing value, if RSO configured | Later `https://ownlobby.com/api/oauth/riot/callback/` | After provider preregistration | Yes | Preserve client credentials and RSO approval; API-key presence alone is insufficient. |
| Google/Discord/Epic/Steam client/key variables | Existing provider identities | Existing standard/legacy aliases | **Existing values unchanged** | Verify allowlists manually | Yes if an env URL changes | Add callbacks in existing applications; do not create replacement identities. |
| `SITE_ID` | Existing Django Sites record | Existing ID, default `1` | Preserve ID; update its domain/name through approved admin process | Canonical switch, if used | Cache/process refresh | Do not create/delete Sites blindly; keep allauth/provider associations intact. |
| `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` | Existing HTTPS policy | Production redirect and one-year HSTS defaults | Keep reviewed production policy | Verify staging/cutover | Yes | Do not weaken cookies/CSRF or request new preload to solve routing problems. |

## Do not change yet

Do not push, merge, deploy, change DNS/routing, enable redirects, rotate secrets, change live callbacks/mail, move private files, execute financial transactions or rename infrastructure without the relevant approval. Keep the old domain and TLS working. Keep `THE_CROWN`, internal Django/database identifiers, Render hostname, Supabase project ref and account IDs stable. Infrastructure display-name cleanup is a later separate checklist, not a domain prerequisite.

Detailed root causes: `OWNLOBBY_PRODUCTION_READINESS.md`. SEO policy and Search Console work: `OWNLOBBY_TECHNICAL_SEO.md`. Ordered dashboard actions and rollback: `OWNLOBBY_DOMAIN_MIGRATION.md`.
