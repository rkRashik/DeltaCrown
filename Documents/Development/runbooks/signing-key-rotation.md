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
| Published editor-image URLs | `signing.dumps(salt="published-editor-image")`, stored inside authored text (`Tournament.description`/`rules_text` are the only admin rich-text fields; others only if pasted), **no expiry**; route `/files/editor/<token>/` | Yes | Without fallback: existing images 404. The fallback is retired only after `resign_editor_image_urls` reports `legacy: 0` and no unexplained `invalid` (Steps 5-7) |
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

## Deployment sequence
Eight steps, in this order; each environment change restarts Render, so do not merge steps. Every step needs the owner's explicit approval, a verified restore point, and a "stop" decision if any check below fails. Production currently runs an older release than master: Step 1 is therefore a real deploy and must be verified before anything else.

**Step 1: deploy the compatibility code, change no keys.** Behavior is identical to today (the primary field key is still derived from `SECRET_KEY`; no fallback is configured). The build log shows `user_profile.W001` (expected). Verify health and login. Run the read-only reports and record the counts as the baseline: `reencrypt_oauth_tokens` (dry run), `resign_editor_image_urls` (dry run) and `resign_editor_image_urls --discover` (see "Running discovery safely" below). Doing this first means an instance still on the previous release during a deploy overlap never meets new-key data.

**Step 2: verify OAuth encryption configuration and recovery prerequisites** (see Preconditions): `FIELD_ENCRYPTION_KEY` confirmed unset (presence only), the current `DJANGO_SECRET_KEY` is retrievable from the secret manager (if not: stop; the only recovery for OAuth tokens is users reconnecting), a restore point exists, and `reencrypt_oauth_tokens` shows `undecryptable: 0`.

**Step 3: separate the field-encryption key.** Set `FIELD_ENCRYPTION_KEY` (new Fernet key) and `FIELD_ENCRYPTION_LEGACY_SECRET_KEYS` (`["<current DJANGO_SECRET_KEY>"]`); leave `DJANGO_SECRET_KEY` unchanged. Verify: health OK; dry run shows `legacy` rows and `undecryptable: 0`; one OAuth feature works for an owner-controlled test account. Rows are re-encrypted lazily on save. Optional, with approval: `python manage.py reencrypt_oauth_tokens --apply` (rewrites only `legacy`/`plaintext` rows; undecryptable rows are never modified); run the dry run before and after.

**Step 4: rotate the Django signing key with a temporary fallback.** Set `DJANGO_SECRET_KEY` (new) and `DJANGO_SECRET_KEY_FALLBACKS` (`["<old key>"]`). Sessions, reset links and existing editor-image URLs keep working through the fallback; OAuth tokens are unaffected (Step 3); **all JWTs are invalidated** (see Step 8). The next build log should no longer show `security.W009`; `user_profile.W002` stays as a reminder while the fallback exists.

**Step 5: re-sign stored editor-image URLs** (never automatic; not run by deploys, migrations or startup).
1. `python manage.py resign_editor_image_urls` (dry run, read-only; prints counts only). `current`: already signed with the new key. `legacy`: verifies only through the fallback and will be migrated. `invalid`: verifies with no configured key (tampered, other salt, not an editor image, or signed with a key that is not in the fallback list); **never modified**. `missing`: verifies but the image no longer exists; **never modified**. Add `--field app_label.Model.field` for any extra text field that `--discover` reported (the default targets are `Tournament.description` and `Tournament.rules_text`).
2. With approval and a fresh restore point: `python manage.py resign_editor_image_urls --apply`. Each record changes in its own transaction, is rechecked under a row lock, and only the token part of an exact root-relative `/files/editor/<token>/` URL is replaced; all other text and HTML is kept byte for byte. A failing record is rolled back and left unchanged, and the command exits non-zero with the failure count. Re-running is safe: the second run reports `legacy: 0` and `records re-signed: 0`.
3. Re-run `--discover` and require its last line to start with `discover: COMPLETE:` (see below); any other verdict means the inventory is not trustworthy yet.
4. Investigate every `invalid` and `missing` count before Step 7: those URLs stop working once the fallback is removed (a missing image is already broken today).

The command writes with `QuerySet.update()` on the single text column: no model `save()` hooks, signals or `updated_at` changes run.

**Running discovery safely.** `--discover` runs one `COUNT(*) ... LIKE '%/files/editor/%'` per text/char column of every model, which is a full scan of each table (no index can serve it). It issues only SELECT/SHOW statements and a transaction-local `statement_timeout`, and never writes. To keep the load low on a large database: run it off-peak, preferably against a restored copy or read replica; keep the default per-field limit (`--statement-timeout-ms`, default 5000) or lower it; and slice the work with `--discover-model app_label.Model` (repeatable), one large table at a time.
How to read the verdict (last line; failures are also listed as `FAILED <model.field>: timeout|error`, categories only):
* `discover: COMPLETE: ... 0 failed`: every text/char field of every model was scanned. This is the only verdict that may be used as evidence for retiring the fallback, together with the dry run.
* `discover: INCOMPLETE: ...` (the command also exits non-zero): at least one field could not be scanned. It is **not** an inventory. Retry (off-peak, or with a higher limit) before relying on any count.
* `discover: PARTIAL SCOPE ...`: you restricted the models. Useful for load control, never a substitute for a complete run.
Only text and character columns are inspected (not JSON or other serialized content), and soft-deleted rows are included by every mode of this command, so a later restore does not bring back old-key URLs.

**Step 6: confirm signed URLs work without the old key, in an isolated/staging check, before touching production.** Restore the post-Step-5 backup into a disposable database, run with the new `DJANGO_SECRET_KEY` and **no** `DJANGO_SECRET_KEY_FALLBACKS`, open a sample of pages containing editor images (boolean check: the image loads) and run the dry run: it must report `legacy: 0` and an `invalid` count equal to the investigated value. Synthetic-key unit tests do not replace this check.

**Step 7: retire the compatibility values** (restart and re-verify after each).
* `FIELD_ENCRYPTION_LEGACY_SECRET_KEYS`: remove when the OAuth dry run reports `legacy: 0`.
* `DJANGO_SECRET_KEY_FALLBACKS`: remove only when all hold: (a) Step 6 passed; (b) the dry run reports `legacy: 0` and no unexplained `invalid`, and an unrestricted `--discover` ended `COMPLETE` with 0 failed; (c) the session lifetime and password-reset validity have elapsed since Step 4; (d) Step 5 was re-run immediately before removal, so content saved in the meantime from a stale draft carrying an old-key URL is covered.

**Step 8: JWT re-authentication and rollback limits.** Every access (60 min) and refresh (7 day) token issued before Step 4 stops validating (SimpleJWT has no fallback support here); mobile and WebSocket clients must sign in again. Plan the communication before Step 4. Rollback is not symmetric: see the table below.

## Rollback
| Situation | Action | Limits |
|---|---|---|
| Problem after Step 4 | Restore the previous `DJANGO_SECRET_KEY`; keep `FIELD_ENCRYPTION_KEY` | OAuth tokens remain readable (field key is independent). JWTs issued meanwhile become invalid again |
| Problem after Step 3 | Unset both new field variables only if no token was written under the new key; otherwise keep `FIELD_ENCRYPTION_KEY` and set the previous key as a legacy value | Rows written under the new key are unreadable to configurations without it, but are **preserved** and never overwritten by this code |
| Problem after Step 5 (re-signed URLs) | Restore the pre-Step-5 backup, or leave the data and keep **both** keys configured | Re-signed URLs are signed with the new key. Reverting `DJANGO_SECRET_KEY` to the old key without adding the new key to `DJANGO_SECRET_KEY_FALLBACKS` makes every re-signed URL invalid; the same applies to sessions created after Step 4 |
| Roll back the code release after Step 3 | Not lossless | The previous release cannot read new-key rows and could re-encrypt them; avoid by completing Step 1 first and rolling back configuration, not code |

Triggers: elevated 5xx after restart, OAuth reconnect failures above normal, `undecryptable` count greater than zero, or unexpected mass sign-outs.

## Verifying success without revealing credentials
* Build log: no `security.W009`; `user_profile.W001` gone after Step 3; `W002`/`W003` present only while compatibility values are configured.
* `reencrypt_oauth_tokens` counts: `undecryptable: 0` at every step; `resign_editor_image_urls` prints counts only (never URLs or ids).
* Boolean checks only: login works, an owner-controlled OAuth connection refreshes, a pre-rotation password-reset link and a known editor image still load (Step 4, and again after Step 5).

## Owner decisions required
1. Approve the maintenance window and the stages (Steps 3, 4 and 5 separately).
2. Provide/confirm retrieval of the current key (without sharing it in chat) and that `FIELD_ENCRYPTION_KEY` is unset.
3. Accept JWT invalidation (all mobile/WebSocket sessions re-authenticate).
4. Approve running `resign_editor_image_urls --apply` (Step 5) and decide what to do with any `invalid`/`missing` URLs it reports.
5. If the old key is unrecoverable: approve a reconnect-based migration instead.

## Not covered
No production value was read, generated or installed. Multi-instance deploy overlap, Render restart timing and real provider reconnects were reasoned about, not exercised. This document is not a certification that production is secure.
