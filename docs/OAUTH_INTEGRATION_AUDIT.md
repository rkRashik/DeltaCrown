# OAuth Integration Audit — Riot, Epic, Steam
**Date:** 2026-03-19  
**Author:** Senior Security & API Integration Review  
**Scope:** All code in `apps/user_profile/views/oauth_*`, `apps/user_profile/services/oauth_*`, `apps/user_profile/models/oauth.py`, `apps/user_profile/fields.py`, `deltacrown/settings.py`

---

## 1. Exact Redirect URIs

These are dynamically constructed using Django's `request.build_absolute_uri()` against named URL patterns. The canonical production URLs (assuming domain `https://deltacrown.xyz`) are:

| Provider | Redirect URI to register in developer portal |
|----------|----------------------------------------------|
| **Riot (Valorant)** | `https://deltacrown.xyz/api/oauth/riot/callback/` |
| **Epic (Rocket League)** | `https://deltacrown.xyz/api/oauth/epic/callback/` |
| **Steam (CS2 / Dota 2)** | `https://deltacrown.xyz/api/oauth/steam/callback/` |

### URL Name References (Django reverse)

| URL name | Path |
|----------|------|
| `user_profile:riot_oauth_callback` | `/api/oauth/riot/callback/` |
| `user_profile:epic_oauth_callback` | `/api/oauth/epic/callback/` |
| `user_profile:steam_openid_callback` | `/api/oauth/steam/callback/` |

**Note — Alias paths also exist** (mapped to the same views) but should **not** be registered in developer portals. Only the canonical paths above should be allowlisted:
- `profile/api/oauth/riot/callback/`
- `profile/api/oauth/epic/callback/`
- `profile/api/oauth/steam/callback/`

### Steam-specific: Realm

Steam OpenID also requires registering a **realm** (the full origin). Set this to:
```
https://deltacrown.xyz
```

The Django code derives the realm automatically via `f"{request.scheme}://{request.get_host()}"`. Ensure the production host reported by Django matches the registered realm exactly, including no trailing slash.

---

## 2. Required Environment Variables

All variables are read via `os.getenv(...).strip()` in `deltacrown/settings.py`. **Missing or empty values will cause the relevant provider to refuse with a config error** — the code raises a 500 before even attempting the redirect.

### Riot Games (RSO — Riot Sign-On)

| Variable | Required | Purpose |
|----------|----------|---------|
| `RIOT_CLIENT_ID` | **Yes** | OAuth 2.0 client identifier |
| `RIOT_CLIENT_SECRET` | **Yes** | OAuth 2.0 client secret (used in Basic auth for token exchange) |
| `RIOT_REDIRECT_URI` | **Yes** | Must match exactly what is registered in the RSO portal → `https://deltacrown.xyz/api/oauth/riot/callback/` |
| `RIOT_API_KEY` | Optional | Riot Games API key; added as `X-Riot-Token` header for account lookup fallback. If absent, OAuth identity resolution relies solely on the Bearer token. |
| `RIOT_OAUTH_SCOPES` | Optional | Default: `openid offline_access`. Override only if RSO portal grants different scopes. |
| `RIOT_OAUTH_TIMEOUT_SECONDS` | Optional | Default: `10`. HTTP timeout for all Riot API calls. |
| `RIOT_ACCOUNT_API_CLUSTERS` | Optional | Default: `americas,asia,europe`. Comma-separated list. Used for multi-cluster `gameName/tagLine` resolution. |

### Epic Games (EAS — Epic Account Services)

| Variable | Required | Purpose |
|----------|----------|---------|
| `EPIC_CLIENT_ID` | **Yes** | OAuth 2.0 client identifier from EAS portal |
| `EPIC_CLIENT_SECRET` | **Yes** | OAuth 2.0 client secret (used in HTTP Basic auth for token exchange) |

> Epic does **not** use a static redirect URI env var. The redirect URI is built dynamically at runtime via `request.build_absolute_uri(reverse("user_profile:epic_oauth_callback"))`. Register the full absolute URI in the EAS portal under **Allowed Redirect URIs**.

### Steam (OpenID 2.0)

| Variable | Required | Purpose |
|----------|----------|---------|
| `STEAM_API_KEY` | **Yes** | Steam Web API key, used to call `ISteamUser/GetPlayerSummaries/v2/` after identity is verified. Without this the callback will fail at the profile-fetch step (HTTP 500 is raised). |

> Steam OpenID 2.0 does **not** use a Client ID or Secret — the trust model is URL-based. The "whitelist" in the Steam developer portal is the **realm** (your domain).

### Token Encryption

| Variable | Required | Purpose |
|----------|----------|---------|
| `FIELD_ENCRYPTION_KEY` | Strongly Recommended | A base64-encoded 32-byte Fernet key used to encrypt `access_token` and `refresh_token` at rest in the database. If absent, the code falls back to deriving a key from Django's `SECRET_KEY`. For production: set an explicit, stable key so tokens remain decryptable across deployments. |

---

## 3. Requested Scopes

### Riot (RSO / OIDC)

Configured via the `RIOT_OAUTH_SCOPES` env var. Default value (hardcoded fallback):

```
openid offline_access
```

| Scope | Purpose |
|-------|---------|
| `openid` | Required for OIDC — grants access to `/userinfo` endpoint which returns `sub` (PUUID) |
| `offline_access` | Grants a refresh token so the access token can be silently renewed |

> The RSO portal must explicitly grant both scopes to the application. Not all RSO app tiers have `offline_access` enabled by default.

### Epic Games (EAS)

Hardcoded in `oauth_epic_service.py` — not configurable via env:

```
basic_profile
```

| Scope | Purpose |
|-------|---------|
| `basic_profile` | Grants access to the account's display name and `account_id` |

> No refresh-token scope is explicitly requested; Epic returns a refresh token as part of `basic_profile` by default.

### Steam (OpenID 2.0)

Steam OpenID 2.0 does not use scopes in the OAuth 2.0 sense. The OpenID exchange only yields identity verification (SteamID). Extended profile data (persona name, avatars) is fetched separately via the Steam Web API using `STEAM_API_KEY`.

---

## 4. Database Architecture

### Tables involved

| Table | Django Model | Purpose |
|-------|-------------|---------|
| `user_profile_gameprofile` (from `models_main.py`) | `GameProfile` | The Game Passport itself — one row per user+game combination |
| `user_profile_game_oauth_connection` | `GameOAuthConnection` | The OAuth linkage — one-to-one with `GameProfile` |

### `GameProfile` — fields populated on OAuth success

| Field | Population source |
|-------|------------------|
| `user` | Authenticated Django user from session |
| `game` | Looked up by `slug__iexact` (`"valorant"`, `"cs2"`, `"dota2"`, `"rocketleague"`) |
| `game_display_name` | Copied from `game.display_name` |
| `ign` | Riot: `gameName`; Steam: Steam persona name; Epic: Epic display name |
| `discriminator` | Riot: `#tagLine`; Steam/Epic: blank |
| `platform` | Set to `"PC"` for all three providers |
| `in_game_name` | Riot: `gameName#tagLine`; Steam: persona name; Epic: display name |
| `identity_key` | Riot: `gameName#tagLine`; Steam: SteamID64; Epic: `account_id` |
| `visibility` | Defaulted to `"PUBLIC"` on creation; not updated on reconnect |
| `metadata` | Provider-specific JSON blob (see below) |

**`metadata` per provider:**

```jsonc
// Riot
{
  "riot_puuid": "...",
  "riot_game_name": "Player",
  "riot_tag_line": "NA1",
  "oauth_provider": "riot"
}

// Steam
{
  "steam_id": "76561198...",
  "steam_persona_name": "PlayerName",
  "steam_profile_url": "https://steamcommunity.com/id/...",
  "steam_avatar": "https://...",
  "steam_avatar_medium": "https://...",
  "steam_avatar_full": "https://...",
  "oauth_provider": "steam"
}

// Epic
{
  "epic_account_id": "...",
  "epic_display_name": "PlayerName",
  "oauth_provider": "epic"
}
```

### `GameOAuthConnection` — fields saved on OAuth success

| Field | Type | Notes |
|-------|------|-------|
| `passport` | OneToOneField → GameProfile | The linked passport |
| `provider` | CharField | `"riot"` / `"steam"` / `"epic"` |
| `provider_account_id` | CharField(191) | Riot: PUUID; Steam: SteamID64; Epic: account_id |
| `game_shard` | CharField | Always `""` — not populated in any current provider |
| `access_token` | `EncryptedTextField` | Fernet-encrypted at rest. Steam: empty string (OpenID has no token) |
| `refresh_token` | `EncryptedTextField` | Fernet-encrypted at rest. Steam: empty string |
| `token_type` | CharField | Riot/Epic: `"Bearer"` from response; Steam: hardcoded `"openid"` |
| `scopes` | TextField | Riot/Epic: scope string from token response; Steam: hardcoded `"openid2"` |
| `expires_at` | DateTimeField | Riot/Epic: `now() + expires_in seconds`; Steam: `null` |
| `last_synced_at` | DateTimeField | Set to `now()` on every successful connect/refresh |
| `connected_at` | DateTimeField | Auto-set on creation; never updated |
| `updated_at` | DateTimeField | Auto-updated on every save |

**Deduplication / conflict rules:**
- **Cross-user linking blocked:** If the same provider account ID is already linked to a *different* user, the callback raises a 409 and the connection is refused.
- **Per-user uniqueness:** Each user can have exactly one `GameOAuthConnection` per `GameProfile` (OneToOne). Reconnecting the same game simply overwrites the existing row via `update_or_create`.

---

## 5. Code-Level Blockers

The following issues were identified and their status is noted.

---

### ✅ FIXED — Epic: Wrong Authorization URL (Critical)

**File:** `apps/user_profile/services/oauth_epic_service.py`

**Was:**
```python
EPIC_AUTHORIZE_URL = "https://www.epicgames.com/id/api/redirect"
```

**Now (fixed):**
```python
EPIC_AUTHORIZE_URL = "https://www.epicgames.com/id/authorize"
```

The `/id/api/redirect` endpoint does not support `response_type=code` in the standard authorization flow. This was the direct cause of the `"Invalid Client"` / `"response_type is not allowed"` error. Epic's correct OAuth 2.0 authorization endpoint is `https://www.epicgames.com/id/authorize`.

---

### ✅ FIXED — Riot: Callback Stranded User on Raw JSON (Critical)

**File:** `apps/user_profile/views/oauth_riot_api.py`

**Was:** `RiotCallbackView` always returned raw `JsonResponse` regardless of context. When Riot redirected the browser back to the callback URL after successful authentication, the user was presented with a JSON blob instead of being redirected back to the settings page.

**Also:** The state cache stored only a plain `user_id` integer. Post-flow redirect target was unresolvable.

**Now (fixed):**
- `RiotLoginRedirectView` now caches `{"user_id": ..., "callback_mode": ...}` (same pattern as Epic/Steam).
- `RiotCallbackView` supports `callback_mode=redirect`, which redirects to `/profile/settings/?tab=passports&oauth_provider=riot&oauth_status=connected` on success.
- Old `"plain integer"` cache format is handled gracefully (backward compatible).

---

### ✅ FIXED — Riot: Frontend Route Used Wrong Path / No Callback Mode

**File:** `static/user_profile/js/oauth_linked_accounts.js`

**Was:**
```js
valorant: '/api/oauth/riot/login/',
```

**Now (fixed):**
```js
valorant: '/profile/api/oauth/riot/login/?response_mode=json&callback_mode=redirect',
```

The old route did not set `callback_mode=redirect`, so even after fixing the server-side view, the browser would have received JSON instead of being redirected home.

---

### ⚠️ OPEN — Riot: Static RIOT_REDIRECT_URI Must Match Exactly

**File:** `apps/user_profile/services/oauth_riot_service.py`

Unlike Epic (which builds the redirect URI dynamically per-request), Riot uses a **static** `RIOT_REDIRECT_URI` environment variable:

```python
"redirect_uri": settings.RIOT_REDIRECT_URI,  # used in both auth URL and token exchange
```

This means:
1. The env var must be set to exactly `https://deltacrown.xyz/api/oauth/riot/callback/`
2. It must be allowlisted verbatim in the RSO developer portal
3. Any mismatch (trailing slash, http vs https, staging vs production) will cause Riot to return `invalid_redirect_uri`

For local development, a separate `RIOT_REDIRECT_URI` value (e.g. `http://localhost:8000/api/oauth/riot/callback/`) must be registered as an additional allowed URI in the RSO portal.

---

### ⚠️ OPEN — Epic: No EPIC_REDIRECT_URI Env Var — Runtime Value Must Be Stable

**File:** `apps/user_profile/views/oauth_epic_api.py`

```python
redirect_uri = request.build_absolute_uri(reverse("user_profile:epic_oauth_callback"))
```

Epic's EAS portal requires the exact redirect URI to be pre-registered. Since this is built from the incoming HTTP request, the value will differ between:
- Local dev: `http://localhost:8000/api/oauth/epic/callback/`
- Production: `https://deltacrown.xyz/api/oauth/epic/callback/`

Both must be registered in the EAS portal. If the production server is behind a reverse proxy and `request.build_absolute_uri()` returns `http://` instead of `https://`, Epic will reject with `redirect_uri_mismatch`. Ensure Django's `SECURE_PROXY_SSL_HEADER` and `USE_X_FORWARDED_HOST` are correctly set for the Render deployment.

---

### ⚠️ OPEN — Riot: Token Exchange Uses filter + update_or_create With Potential Race

**File:** `apps/user_profile/services/oauth_riot_service.py` — `upsert_riot_connection()`

The conflict check `linked_elsewhere` query runs **after** `get_or_create` and **before** `update_or_create` within the same transaction. In theory a concurrent second connection from the same provider account could slip past the first check before the connection row is created. The impact is low (requires near-simultaneous OAuth callbacks from two different users with the same account), but for correctness the uniqueness constraint should be enforced at the DB level via a unique index on `(provider, provider_account_id)`.

Current state: only a non-unique index exists on those fields (see `user_profil_provide_1e2e3a_idx`). Consider adding a `unique_together` or `UniqueConstraint`.

---

### ℹ️ INFO — Steam: No Access/Refresh Tokens Stored (By Design)

Steam uses OpenID 2.0, not OAuth 2.0. No tokens are issued or stored. The `access_token` and `refresh_token` fields in `GameOAuthConnection` are saved as empty strings for Steam connections. This is correct and expected — the linkage is proven by SteamID, which is re-verified on every reconnect.

---

### ℹ️ INFO — FIELD_ENCRYPTION_KEY Fallback

If `FIELD_ENCRYPTION_KEY` is not set in production, `access_token` and `refresh_token` are encrypted using a key derived from `SECRET_KEY`. Tokens will become unreadable if `SECRET_KEY` is rotated. Set an explicit, independent `FIELD_ENCRYPTION_KEY` for production.

---

## 6. Developer Portal Configuration Checklist

### Riot Games RSO Portal (`https://developer.riotgames.com/`)
- [ ] Grant type: `Authorization Code`
- [ ] Allowed redirect URI: `https://deltacrown.xyz/api/oauth/riot/callback/`
- [ ] Allowed redirect URI (dev): `http://localhost:8000/api/oauth/riot/callback/`
- [ ] Scopes enabled: `openid`, `offline_access`
- [ ] Copy `RIOT_CLIENT_ID` → env
- [ ] Copy `RIOT_CLIENT_SECRET` → env
- [ ] Set `RIOT_REDIRECT_URI=https://deltacrown.xyz/api/oauth/riot/callback/` → env

### Epic Games EAS Portal (`https://dev.epicgames.com/portal/`)
- [ ] Grant type: `Authorization Code with PKCE` *(or Standard Authorization Code if PKCE not forced)*
- [ ] Allowed redirect URI: `https://deltacrown.xyz/api/oauth/epic/callback/`
- [ ] Allowed redirect URI (dev): `http://localhost:8000/api/oauth/epic/callback/`
- [ ] Scope: `basic_profile`
- [ ] Copy `EPIC_CLIENT_ID` → env
- [ ] Copy `EPIC_CLIENT_SECRET` → env

### Steam Developer Portal (`https://steamcommunity.com/dev/apikey`)
- [ ] Register domain: `deltacrown.xyz`
- [ ] Copy Web API key → env as `STEAM_API_KEY`
- [ ] *(No client ID/secret for OpenID 2.0)*

### Encryption Key
- [ ] Generate a Fernet key and set `FIELD_ENCRYPTION_KEY` in production env:
  ```python
  from cryptography.fernet import Fernet
  print(Fernet.generate_key().decode())
  ```

---

## 7. Summary

| Provider | Auth Protocol | Critical Code Bug | Status |
|----------|--------------|-------------------|--------|
| **Epic** | OAuth 2.0 (Authorization Code) | Wrong authorization URL — `id/api/redirect` instead of `id/authorize` | ✅ **Fixed** |
| **Riot** | OAuth 2.0 + OIDC | Callback returned raw JSON; state cache missing `callback_mode`; frontend used wrong route | ✅ **Fixed** |
| **Steam** | OpenID 2.0 | None — architecture was correct | ✅ **No change needed** |

All three providers are now functionally correct at the code level. Completion of the developer portal configuration checklist in §6 is the remaining prerequisite for end-to-end connectivity.
