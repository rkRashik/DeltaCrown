# Signing-key rotation runbook (OL-02B)

**Status: code foundation only. No production key has been rotated and nothing here authorizes it.** The mechanism is covered by synthetic-key tests; it has not been rehearsed against production-like data. Every irreversible step needs the owner's explicit approval (see "Owner decisions"). Never paste a key, token or ciphertext into chat, tickets, commits or logs.

## Why this exists
Render builds report `security.W009`: the configured `DJANGO_SECRET_KEY` fails Django's strength check. That is a remediation requirement, not evidence of compromise. Before this change a rotation would also have broken stored OAuth tokens, because their encryption key was derived from `SECRET_KEY`.

## What the code now provides
| Setting (env var) | Purpose | Default |
|---|---|---|
| `FIELD_ENCRYPTION_KEY` | Primary Fernet key; the only key used to encrypt OAuth tokens | unset: derived from `SECRET_KEY` (old behavior, unchanged) |
| `FIELD_ENCRYPTION_LEGACY_SECRET_KEYS` | JSON array of previous `DJANGO_SECRET_KEY` values; **decrypt-only** (the old derived key is recomputed internally) | empty |
| `FIELD_ENCRYPTION_LEGACY_KEYS` | JSON array of previous Fernet keys; decrypt-only (for a later encryption-key rotation) | empty |
| `DJANGO_SECRET_KEY_FALLBACKS` | JSON array of previous signing keys passed to Django's `SECRET_KEY_FALLBACKS` | empty |

Format: a JSON array of non-empty strings, for example `["previous-value"]` (not comma separated: keys may contain commas). Inside the JSON string, escape `"` and `\` if the old key contains them (build the value in your secret manager or with `json.dumps`, never by typing it into a shared terminal history); a wrong value fails `manage.py check` with a message that does not show it. At most 5 entries; malformed values stop startup/`manage.py check` with a message that never contains the value.

Chosen design: new strong primary key plus a decrypt-only legacy secret, rather than pinning the key derived from the old weak secret. Pinning would keep all future writes protected by a key derived from the weak secret and would require handling a derived key; the chosen design keeps the old secret only for reading, and the maintenance command lets you retire it.

Safety behavior (tested): only configured keys are tried; ciphertext that cannot be decrypted reads as an empty value (so integrations ask the user to reconnect) and is **written back unchanged** on save: never returned as a token, never re-encrypted (no double encryption), recoverable after a rollback; legacy plaintext rows still work and are encrypted on next save; error and log text contain no key or token.

## What depends on `SECRET_KEY` (inventory at this code revision)
| Item | Mechanism | Covered by `DJANGO_SECRET_KEY_FALLBACKS`? | Impact if rotated |
|---|---|---|---|
| Browser sessions | Django session auth hash | Yes | Without fallback: everyone is logged out |
| Password-reset links | Django token generator | Yes | Without fallback: outstanding links fail |
| Published editor-image URLs | `signing.dumps(salt="published-editor-image")`, **stored inside published content, no expiry** | Yes | Without fallback: existing images 404. **The fallback cannot be removed until these URLs are re-signed**; no re-signing tool exists yet (follow-up) |
| Mobile/API/WebSocket JWT (SimpleJWT) | `SIGNING_KEY = SECRET_KEY`, no fallback support | **No** | All access (60 min) and refresh (7 day) tokens stop validating; clients must sign in again. Intentionally unchanged |
| OAuth tokens (`GameOAuthConnection.access_token/refresh_token`) | Fernet, key derived from `SECRET_KEY` unless `FIELD_ENCRYPTION_KEY` set | Not applicable: handled by the field-encryption settings above | Without the legacy setting: unreadable (preserved, but users must reconnect) |
| Ticket "secret code" on the registration success page | `salted_hmac('vip-pass-secret', ...)` | No | Displayed code changes for the same registration; no verification code was found in the repository |
| Password hashes, wallet PIN/OTP hashes | Own salts | n/a | None |

Encrypted-data inventory: only the two OAuth token columns above use `EncryptedTextField`. Get status counts (no values) with `python manage.py reencrypt_oauth_tokens` (dry run).

## Preconditions (before any production change)
1. Owner-approved window; a current database backup/restore point exists and its restore has been rehearsed.
2. The current `DJANGO_SECRET_KEY` value is stored in the owner's secret manager (it is needed as the legacy value). **If it cannot be retrieved, stop**: do not rotate. Existing tokens could then only be recovered by users reconnecting; run the dry run first to count affected rows.
3. Confirm in the Render dashboard that `FIELD_ENCRYPTION_KEY` is currently **unset** (presence only; never display values). If it is set, tell the engineer before continuing: the plan changes.
4. Generate the new values offline, store them only in the secret manager: a new signing key (for example `python -c "import secrets; print(secrets.token_urlsafe(64))"`) and a new Fernet key (`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
5. Rehearse the whole sequence on a disposable/staging database with synthetic OAuth rows and sessions.

## Staged procedure
Each environment change causes a Render restart. Do the stages in this order; do not merge them.

**Stage 1: ship the code, change no configuration.** Behavior is identical to today (the primary key is still derived from `SECRET_KEY`). The build log shows `user_profile.W001` (expected). Verify health/login normal and `reencrypt_oauth_tokens` (dry run) reports no `undecryptable` rows. Doing this first means any instance still running the previous release during a deploy overlap is never confronted with new-key data.

**Stage 2: separate the field key.** Set `FIELD_ENCRYPTION_KEY` (new Fernet key) and `FIELD_ENCRYPTION_LEGACY_SECRET_KEYS` (`["<current DJANGO_SECRET_KEY>"]`). Leave `DJANGO_SECRET_KEY` unchanged. Verify: health OK; dry run shows `legacy` rows and `undecryptable: 0`; one OAuth-dependent feature works for an owner-controlled test account. Rows are re-encrypted lazily on save.

**Stage 3 (optional, approval needed): re-encrypt now.** `python manage.py reencrypt_oauth_tokens --apply` rewrites only `legacy` and `plaintext` rows; undecryptable rows are never modified. Run the dry run before and after (counts only).

**Stage 4: rotate the signing key.** Set `DJANGO_SECRET_KEY` (new) and `DJANGO_SECRET_KEY_FALLBACKS` (`["<old key>"]`). Impact: sessions and reset links survive via the fallback; **all JWTs are invalidated** (mobile/WebSocket users sign in again; plan communication); OAuth tokens are unaffected because they no longer depend on the signing key. The next build log should no longer show `security.W009`.

**Stage 5: retire the compatibility values.**
* `FIELD_ENCRYPTION_LEGACY_SECRET_KEYS`: remove when the dry run reports `legacy: 0` (after Stage 3 or enough natural saves).
* `DJANGO_SECRET_KEY_FALLBACKS`: remove only when (a) the session lifetime has elapsed, (b) reset-link validity has elapsed, and (c) the editor-image URLs signed under the old key have been re-signed or confirmed unused. Condition (c) is currently **unresolved**; plan a follow-up task. Until then keep the fallback (the build keeps printing `user_profile.W002` as a reminder).
After each removal, restart and re-verify.

## Rollback
| Situation | Action | Limits |
|---|---|---|
| Problem after Stage 4 | Restore the previous `DJANGO_SECRET_KEY`; keep `FIELD_ENCRYPTION_KEY` | OAuth tokens remain readable (field key is independent). JWTs issued meanwhile become invalid again |
| Problem after Stage 2 | Unset both new field variables only if no token was written under the new key; otherwise keep `FIELD_ENCRYPTION_KEY` and set the previous key as a legacy value | Rows written under the new key are unreadable to configurations without it, but are **preserved** and never overwritten by this code |
| Roll back the code release after Stage 2 | Not lossless | The previous release cannot read new-key rows and could re-encrypt them; avoid by completing Stage 1 first and rolling back configuration, not code |

Triggers: elevated 5xx after restart, OAuth reconnect failures above normal, `undecryptable` count greater than zero, or unexpected mass sign-outs.

## Verifying success without revealing credentials
* Build log: no `security.W009`; `user_profile.W001` gone after Stage 2; `W002`/`W003` present only while compatibility values are configured.
* `reencrypt_oauth_tokens` counts: `undecryptable: 0` at every stage.
* Boolean checks only: login works, an owner-controlled OAuth connection refreshes, a pre-rotation password-reset link and a known editor image still load (Stage 4).

## Owner decisions required
1. Approve the maintenance window and the stages (Stage 3 and Stage 4 separately).
2. Provide/confirm retrieval of the current key (without sharing it in chat) and that `FIELD_ENCRYPTION_KEY` is unset.
3. Accept JWT invalidation (all mobile/WebSocket sessions re-authenticate).
4. Decide how to handle the editor-image URLs (keep the fallback indefinitely, or approve a re-signing follow-up).
5. If the old key is unrecoverable: approve a reconnect-based migration instead.

## Not covered
No production value was read, generated or installed. Multi-instance deploy overlap, Render restart timing and real provider reconnects were reasoned about, not exercised. This document is not a certification that production is secure.
