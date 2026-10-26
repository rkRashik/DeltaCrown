# OwnLobby OAuth reliability - Phase 4

Audit: 2026-10-26. **All seven previously failing cases now pass with documented dispositions. Final selected OAuth/ownership/security suite: 47 passed.** Providers are mocked; no live identity, token, provider application, callback allowlist or linked production account was used/changed. Linux and live staging provider validation remain required.

## Seven-case root-cause matrix

| Original failing node | Verified root cause | Correction and retained contract |
|---|---|---|
| apps/user_profile/tests/test_oauth_api.py::test_riot_callback_success_creates_passport_and_oauth_connection | _get_riot_state assumed JSON, but auto-mode correctly redirects browser requests (302). Later assertions also used pre-migration passport/provider-ID fields. | Test explicitly requests response_mode=json/callback_mode=json; checks GameProfile plus authoritative game_profile/ProviderAccount relationships, stable PUUID and encrypted tokens. Browser redirect behavior remains unchanged. |
| ...::test_riot_callback_invalid_code_returns_structured_error | Same outdated initiation expectation prevented reaching the API error contract. | Explicit JSON initiation now reaches invalid-code callback and asserts 400/error code/no persisted connection; provider POST mocked. No security check bypass. |
| ...::test_steam_callback_success_creates_cs2_passport_and_oauth_connection | requests.get mock returned a player-summary payload for GetOwnedGames too, so ownership set was empty and service correctly skipped passports. Legacy relationship/ID assertions also stale. | URL-specific fixtures return real-shaped summaries and owned app IDs 730/570. Asserts both distinct HTTP lookups, CS2 passport, verified account anchor and stable Steam ID. No unconditional passport creation or ownership bypass. |
| ...::test_steam_same_id_can_link_cs2_and_dota2_for_same_user | Two-item side-effect list omitted each ownership call, producing empty/wrong payloads/StopIteration. Test used nullable legacy passport column instead of game_profile and provider anchor. | URL-specific mock handles every requested endpoint; asserts two game passports/two connections sharing the same external account. Existing model identities and multi-game behavior retained. |
| ...::test_steam_callback_redirect_mode_returns_to_settings_passports_tab | Incomplete ownership fixture legitimately produced warning. **Real application defect:** successful return was indented beneath an earlier unconditional warning return; owned-game success fell through to JSON instead of redirect. oauth_game expectation also belonged to obsolete single-game linking. | Corrected success return indentation, retained warning behavior when no games found. Test checks 302/settings/passports/provider/connected and two actual connections. No invented single-game query field; current flow links all supported owned games. Removed 169 lines of unreachable stale single-game code below the unconditional JSON return, including undefined old symbols; active routes/workflows unchanged. |
| ...::test_epic_callback_success_creates_rocketleague_passport_and_oauth_connection | Correct service persisted game_profile/provider_account; test queried the nullable deprecated passport relation and compared internal FK to external identity. | Test uses authoritative relationships and asserts the real external Epic account ID/access/refresh tokens. No persistence/schema rewrite. |
| tests/accounts/test_google_oauth.py::test_google_oauth_creates_user_and_logs_in | Expected old /account/profile/ redirect, whereas current implementation intentionally defaults to siteui:homepage. | Assert exact named homepage and the actual authenticated session user. Existing Google identity-linking suite remains intact and passes. |

The five abbreviated rows above refer to the full test_oauth_api.py node IDs recorded in OWNLOBBY_DEPENDENCY_VALIDATION.md. Phase 3 reproduced the same seven failures with original/upgraded dependencies. Phase 4 did not relabel all failures as harmless: the Steam redirect was a real defect and additional security bugs were corrected below.

## Additional security/reliability corrections

### Google

GoogleLoginStart previously saved unchecked next URLs into the session; callback redirected to them. Now same-request-host safe URL checks apply both at initiation and callback, respecting HTTPS. New flow clears stale destinations, a matched state is consumed before provider exchange (including failed exchange), missing code is rejected, and email_verified must be a real boolean True before verified-email account linking. Existing safe local next destinations, homepage fallback, GoogleIdentity IDs, verified-email policy, inactive/deletion rejection and session login are preserved.

Regressions cover external/protocol-relative/backslash/javascript targets, safe local settings return, old unsafe stored next, failed exchange and replay. Existing tests still cover existing sub reuse, verified/unverified email linking, ambiguity, inactive accounts and scheduled deletion. No PKCE/client-ID/key migration or live consent flow was introduced.

### Steam signed assertions

Beyond server-side check_authentication, the old verifier did not bind an assertion to the expected return_to or require signed identity fields, and had no local nonce age/replay guard. It also accepted a substring containing is_valid:true instead of an exact response line.

Initiation now caches its exact return_to with the state. Callback verifies namespace, id_res mode, fixed Steam endpoint, identity/claimed-ID agreement, return_to equality, required signed fields and signature/association presence. Provider verification still goes to the fixed HTTPS Steam endpoint. A correctly formatted nonce must be within the selected 600-second window (matching state TTL, with 30-second forward clock tolerance); only verified assertions can enter the atomic replay cache. An exact is_valid:true line is required. Existing in-flight state format has a canonical return_to fallback; IDs, URLs and callback response keys are preserved.

These are relying-party controls informed by [OpenID 2.0 verification](https://openid.net/specs/openid-authentication-2_0.html#verification); the chosen age/skew limits are OwnLobby policy, not a claim that the spec prescribes those numbers. Test fixtures now have signed fields/return_to/current synthetic nonce as a real provider assertion would. Provider verification is mocked, never skipped. Tests reject mismatched return_to/identity, missing signature/signed fields, stale nonce, foreign-user state and reuse of consumed state.

### Provider ownership race

Riot/Steam/Epic previously checked whether an identity belonged to someone else, then used update_or_create with user in defaults. Two concurrent requests could both pass the initial check and the unique-key retry could update the first owner's row to the second user. This was an application race, not an outdated test.

A small shared claim_provider_account helper now uses the existing unique identity key, get_or_create, a row lock and an ownership recheck before metadata updates. Existing owner can resync; ownership is never updated from another user's request. Provider services retain their existing *_ACCOUNT_ALREADY_LINKED/409 error contract. No new column, model/table identifier or migration. Three real PostgreSQL two-thread races (one per provider) each produce one winner/one denied contender, one stable anchor; resync preserves PK/external ID. The existing one-Steam/multiple-game association still works.

### Discord and account/session boundaries

Existing Discord link start requires authentication and caches a user-bound CSRF state; callback consumes it and verifies the current session user before exchanging a code. Two new negative tests verify missing/foreign state never contacts the provider. This is not a full successful Discord sandbox/live integration test. Existing bot/client identities and callback builder remain unchanged. Game linking still requires an authenticated account; OAuth is not a route for transferring another user's provider identity.

## Current identity contracts

ProviderAccount(provider, provider_account_id) is the unique cross-game external identity anchor. GameOAuthConnection.game_profile and provider_account are authoritative. Its nullable passport field remains for legacy migration compatibility. A connection's provider_account_id is the internal FK; its provider_account.provider_account_id is the external provider ID. Tests now distinguish them instead of changing schema or rewriting stored identities. Any pre-existing JSON response ambiguity between an internal FK and external ID requires a separately reviewed API compatibility decision; no response-key migration was silently introduced here.

No provider callback path, client identity, Google/Discord linked user ID, account password or encryption key changed. Existing primary routes and /profile/api/oauth aliases remain available. Google/Discord use existing canonical callback logic, Riot explicit RIOT_REDIRECT_URI, Epic/Steam their existing callback builders. Cutover preregistration remains in OWNLOBBY_DOMAIN_MIGRATION.md. Valid cross-domain sessions still cannot be shared across .xyz/.com; no cookie weakening.

## Executed validation

Guarded settings_brand_qa, loopback PostgreSQL 18 on 55432/ownlobby_test, memory cache/mail/broker, synthetic values. Exact final selected command:

```powershell
$env:DATABASE_URL='postgresql://ownlobby_qa@127.0.0.1:55432/ownlobby_unused'
$env:DATABASE_URL_TEST='postgresql://ownlobby_qa@127.0.0.1:55432/ownlobby_test'
$env:COMPETITION_APP_ENABLED='1'
$env:S3_TESTS='0'
$env:AWS_EC2_METADATA_DISABLED='true'
Artifacts/dependencies/qa/Scripts/python.exe -m pytest apps/user_profile/tests/test_oauth_api.py apps/user_profile/tests/test_provider_account_ownership.py tests/accounts/test_google_oauth.py tests/accounts/test_google_oauth_linking.py tests/accounts/test_google_oauth_redirect_security.py --reuse-db --ds=deltacrown.settings_brand_qa --tb=short --show-capture=no
```

Result: **47 pass**, two existing migration deprecation warnings. Intermediate outcomes are retained: 17 pass after original seven-case corrections; 36 after state/redirect/assertion hardening; 40 after concurrency tests; 42 with Discord negative cases; 43 after the valid timestamp-only nonce boundary regression; final 47 includes verified nonce replay, invalid verification-line and malformed boolean-claim regressions. One intermediate endpoint-name assertion in the newly corrected Steam mock used the wrong URL segment and was fixed; it was not an application regression.

The final independent workflow suite has 88 pass/nine existing skips (including Game Passport, registration, WebSocket auth/private events and offline certificate storage). Focused Django suite has 219 pass/one native-Cairo skip, including encrypted fields, old session/JWT/password compatibility, media rejection, financial invariants, settings and SEO. No passing-test regression observed in selected coverage. Full project suite, live providers, Redis network concurrency, all browser auth journeys and Linux execution are not certified by these results.

## Remaining provider/release gates

- On approved isolated Linux staging, exercise successful provider consent, existing account linking/resync, owned/private Steam library behavior, cancellation/timeouts and session expiry using sandbox/test identities. Verify clock synchronization and shared Redis cache semantics across processes. Local mocked signatures do not prove provider configuration.
- Preserve callback aliases, scopes, approved applications, credentials and linked IDs; add both canonical origins later through the separately approved migration procedure. No provider dashboard action is needed in this phase.
- Live mail/provider readiness, storage privacy and restoration, Linux native rendering and deployment approval still block production. Seven baseline failures themselves are no longer open; do not keep reporting them as unresolved after this correction.
