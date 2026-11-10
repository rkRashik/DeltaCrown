# Security

## Authentication and sessions

* Django sessions (database-backed) and CSRF on all browser forms; JWT (`api/token/`) for API and WebSocket clients. Backends: `EmailOrUsernameBackend` plus optional allauth (legacy `accounts/` routes redirect to `account/`).
* Login: rate limited (10 attempts/60 s/IP); `next` is honoured only for same-host targets (`LoginView.get_redirect_url`); external, protocol-relative and `javascript:` targets are ignored. Error messages are generic.
* Signup uses email OTP; the user is created only after verification. Password reset returns the same response whether or not the account exists, tokens are single use, requests are rate limited (5/60 s/IP). Signed-in password change at `account/password_change/`.
* Accounts scheduled for deletion are blocked by middleware. Existing account, role and privacy boundaries must not be weakened by UI work.

## Permissions

Organizer, staff, team-role and owner checks live in services and views (tournament organizers/staff, TOC permissions, team roles, `match_authority`). Private profiles hide content from non-followers; draft and pending tournaments are visible only to organizers/staff. Hiding links in templates is not authorization: every endpoint enforces its own check.

## Browser protections

`CSPMiddleware` issues a per-request nonce (`request.csp_nonce`); inline scripts and styles must carry it, and full responses containing a nonce must never be cached. HSTS, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy: same-origin`, secure cookies and `SearchIndexingMiddleware` noindex on sensitive routes are applied in production. A bot-probe middleware fast-fails scanner paths. Dev/QA pages (`/ui/`, `/test-game-assets/`, `/favicon-test/`) are staff or DEBUG only (`apps.common.dev_only`).

## Wallet and coins

* Ledger of immutable transactions, soft-deleted request records, staff approval for top-ups, withdrawals and prize claims in the Django admin; no automatic payout.
* Wallet PIN: stored hashed with Django hashers. Current master: 4-digit PIN setup in the API and an HTML PIN page that did not save. **Open PR #77** (reviewed, mergeable, no migrations) adds one 6-digit policy with a weak-PIN list, legacy 4-digit PINs still verify, an existing PIN is never replaced without verifying it, a stale setup OTP cannot overwrite a PIN, and a shared lockout (5 failures, 15 minutes) under a row lock.
* Residual gap even after #77: the lockout in `withdraw_request` and `pin_verify` reads then updates the counters without a row lock, so concurrent wrong guesses can exceed five per window (attacker needs a signed-in session). Until it is fixed, staff must verify each withdrawal request (owner, payment method, amount). No forced rotation of legacy 4-digit PINs and no self-service forgotten-PIN recovery exist.

## Dependencies and supply chain

* Twisted 26.4.0 is installed from a committed, hash-pinned local wheel `26.4.0+ownlobby.1` (`vendor/twisted/`, provenance in `vendor/twisted/provenance.json`, rebuilt by `scripts/build_twisted_backport.py`). It backports the upstream fix (commit `1616f702`, advisory GHSA-q7qq-6mhp-9rc4) that rejects bare CR/LF in HTTP header values; no startup monkeypatch. Remove it when an acceptable stable upstream release exists. Both requirements files install the same wheel; Render and Docker verify its hash.
* The dependency auditor (`scripts/` + pip-audit) exits non-zero deliberately for six base-version findings (five in unused Twisted protocols); a scanner skip is not clearance. Other packages are pinned but not fully hash-locked.
* Secrets: none in Git. `.gitleaks.toml`, GitGuardian on PRs and a CI denylist guard the repository; tests generate throwaway credentials at runtime instead of literals. `.env` files stay local; never paste credentials into issues, PRs or chat.

## Data protection and incident notes

* **OL-01:** Supabase Data API disabled by the owner (2026-10-29); keep it off until RLS/privilege hardening is reviewed. Do not publish endpoint or table inventories or reproduction steps.
* Private media (KYC, payment proofs, dispute evidence, certificates, private profile artwork) is served only by record-authorized routes; see [integrations.md](integrations.md#media-storage).
* Production changes (migrations, secrets rotation, provider settings, storage switches, deploys) need explicit owner approval and a rollback target; see [deployment.md](deployment.md).
