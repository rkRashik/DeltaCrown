# DeltaCrown GamePassport Audit

## Phase 9.1 UI Completion Report (Supervisor Submission)

Date: 2026-03-15
Owner: Player Hub Frontend QA/UX Pass
Status: Completed (UI implementation delivered)

### 1. Scope Requested

1. Match Active Roster card visual style to approved demo screenshot.
2. Reduce unused horizontal whitespace and better utilize viewport width.
3. Keep manual-game editing/update flow and lock-state disconnect behavior intact.
4. Ensure modal behavior remains stable with current frosted UI stack.

### 2. Delivered UI Changes

1. Active Roster heading and hierarchy aligned with demo style.
2. Connected game cards redesigned to compact esports layout:
  - Source badge in top-right (`API Synced` / `Manual`).
  - Strong game-title + identity hierarchy.
  - Compact metadata chips (rank/role/region/etc).
  - Footer lock state text (`Identity Locked` / `Roster Ready`) and action row.
3. Disconnect control now reflects lock state visually with premium disabled treatment.
4. Container width expanded from narrow center column to wide responsive layout (`max-w-[1700px]` + reduced side padding) to utilize left/right space.
5. Grid tuning updated for denser desktop occupancy while preserving mobile responsiveness.

### 3. Functional Integrity Preserved

1. Manual game Edit flow remains connected to update endpoint (`/profile/api/game-passports/update/`).
2. Direct-connect OAuth routes remain unchanged for API-synced games.
3. OTP disconnect modal flow remains intact.
4. Schema label formatting and human-readable field names remain active.

### 4. Files Updated

1. templates/user_profile/profile/settings/partials/_game_passports.html
2. static/user_profile/js/oauth_linked_accounts.js

### 5. QA Verification Snapshot

1. No diagnostics errors in modified JS/template files.
2. Card rendering pipeline validated after refactor (`renderConnectedGames`, `renderAddGames`).
3. Modal initialization path still executes on tab activation with existing controller lifecycle.

### 6. Notes for Final Acceptance

1. Visual output now follows the provided screenshot language for Active Roster cards and spacing utilization.
2. If brand team requests pixel-level parity (exact chip thickness/typography scale), this can be done as a final micro-tuning pass without backend changes.

### 7. Visual Refinement Pass (2026-03-15, Iteration 2)

1. Active Roster cards were further rebuilt for tighter screenshot parity:
  - accent-tinted card framing,
  - top-right source chips,
  - fixed two-column metadata chip grid on desktop,
  - lock-state footer with premium disabled disconnect styling.
2. Layout utilization was widened again (`max-w-[1700px]` container + tuned grids) to eliminate side dead space.
3. No frontend diagnostics errors after this pass.

Date: 2026-03-14
Scope: Current implemented state only (no feature proposals/code changes).

---

## 1) Model Structure & Integrity

### 1.1 Primary model currently used for GamePassport

The active GamePassport model is `GameProfile` in `apps/user_profile/models_main.py`.

Key evidence:
- `class GameProfile(models.Model)` in `apps/user_profile/models_main.py:1630`
- `GameProfile` re-exported as canonical model in `apps/user_profile/models/__init__.py:56`
- CRUD endpoints operate on `GameProfile` in `apps/user_profile/views/game_passports_api.py:162`, `apps/user_profile/views/game_passports_api.py:243`, `apps/user_profile/views/game_passports_api.py:637`, `apps/user_profile/views/game_passports_api.py:823`

### 1.2 Exact `GameProfile` fields (current schema)

From `apps/user_profile/models_main.py:1630` onward:

Identity/ownership:
- `user` (ForeignKey to AUTH_USER_MODEL, `on_delete=CASCADE`) - `apps/user_profile/models_main.py:1670`
- `game` (ForeignKey to `games.Game`, `on_delete=PROTECT`) - `apps/user_profile/models_main.py:1675`
- `game_display_name` (CharField, editable=False)
- `ign` (CharField, nullable, indexed)
- `discriminator` (CharField, nullable, indexed)
- `platform` (CharField, nullable, indexed)
- `in_game_name` (CharField)
- `identity_key` (CharField, indexed)

Rank/stats/profile:
- `rank_name`, `rank_image`, `rank_points`, `rank_tier`, `peak_rank`
- `matches_played`, `win_rate`, `kd_ratio`, `hours_played`
- `main_role`

Passport behavior:
- `visibility` (`PUBLIC|PROTECTED|PRIVATE`)
- `is_lft`
- `region` (indexed)
- `is_pinned`, `pinned_order`, `sort_order`
- `locked_until`
- `status` (`ACTIVE|SUSPENDED`)
- `metadata` (JSONField)

Verification:
- `is_verified` (deprecated compatibility flag)
- `verification_status` (`PENDING|VERIFIED|FLAGGED`, indexed)
- `verification_notes`
- `verified_at`
- `verified_by` (ForeignKey to AUTH_USER_MODEL, `on_delete=SET_NULL`) - `apps/user_profile/models_main.py:1870`

Timestamps:
- `created_at`, `updated_at`

Constraints/indexes:
- `unique_together = [['user', 'game']]` - `apps/user_profile/models_main.py:1884`
- `UniqueConstraint(fields=['game', 'identity_key'], name='unique_game_identity')` - `apps/user_profile/models_main.py:1895`
- Additional indexes include `['user','game']` and `['game','identity_key']` - `apps/user_profile/models_main.py:1889`

### 1.3 Are all 11 games stored in one nullable-column model or relational structure?

Current implementation is relational, not per-game nullable columns.

What exists now:
- One `GameProfile` row per `(user, game)` pair (`unique_together`) - `apps/user_profile/models_main.py:1884`
- `game` is a ForeignKey to `games.Game` - `apps/user_profile/models_main.py:1675`
- Per-game field rules are stored in separate schema/config models:
  - `GamePassportSchema` (`OneToOne` to game) in `apps/user_profile/models/game_passport_schema.py:30`
  - `GamePlayerIdentityConfig` (`ForeignKey` to game) in `apps/games/models/player_identity.py:14`

There is also a deprecated legacy JSON field on `UserProfile`:
- `UserProfile.game_profiles` marked deprecated in `apps/user_profile/models_main.py:293`

### 1.4 Connection to base User model

- `GameProfile.user` -> `ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)` in `apps/user_profile/models_main.py:1670`
- This is **not** OneToOne; a user can have multiple passports (one per game).

---

## 2) Relational Dependencies (Danger Zones)

## 2.1 Direct model dependencies on `GameProfile` (true DB links)

### A) `GameProfileAlias`
- Field: `game_profile = models.ForeignKey(GameProfile, on_delete=models.CASCADE)`
- File: `apps/user_profile/models_main.py:1974`
- Effect: Deleting a passport cascades and deletes alias history for that passport.

### B) `GamePassportDeleteOTP`
- Field: `passport = models.ForeignKey('user_profile.GameProfile', on_delete=models.CASCADE)`
- File: `apps/user_profile/models/delete_otp.py:24`
- Effect: Deleting a passport cascades OTP rows tied to that passport.

## 2.2 Models storing passport references without FK integrity (stale-reference risk)

These do not cascade from passport delete, but can become stale:

### A) `ProfileShowcase`
- Field: `featured_passport_id = models.IntegerField(...)`
- File: `apps/user_profile/models/showcase.py:49`
- Risk: Passport deletion leaves stale integer reference.

### B) `ProfileAboutItem`
- Generic source linkage:
  - `source_model` (CharField), `source_id` (PositiveIntegerField)
- File: `apps/user_profile/models/about.py:87`, `apps/user_profile/models/about.py:93`
- Risk: If item points to `GameProfile`, no FK protection.

### C) `UserAuditEvent`
- Generic object reference fields: `object_type`, `object_id`
- File: `apps/user_profile/models/audit.py:99`, `apps/user_profile/models/audit.py:104`
- Risk: Audit rows can reference deleted passports by ID (expected for append-only logs).

### D) Tournament/roster snapshots
- `Registration.registration_data` JSON (game IDs and identity payloads)
- `Registration.lineup_snapshot` JSON with `game_id` values
- File: `apps/tournaments/models/registration.py:85`, `apps/tournaments/models/registration.py:181`
- Risk: Snapshot values can be stale after passport changes/deletion; no FK cascade.

### E) Free-agent cache field
- `FreeAgentRegistration.game_id` stores in-game ID text
- File: `apps/tournaments/models/free_agent.py:96`
- Risk: Not FK to passport; can diverge from current passport.

## 2.3 Runtime dependencies (service/view coupling, not DB FK)

Used by team/tournament flows to read passport data at action time:
- `GamePassportService.get_passport(...)` usage in:
  - `apps/tournaments/views/smart_registration.py:743`
  - `apps/tournaments/views/hub.py:169`, `apps/tournaments/views/hub.py:214`
  - `apps/tournaments/services/registration_autofill.py:224`, `apps/tournaments/services/registration_autofill.py:414`
- Direct `GameProfile` queries for team context:
  - `apps/organizations/views/team.py:213`
  - `apps/organizations/services/team_detail_context.py:383`
- Tournament verification service uses GameProfile lookup for duplicate/missing game IDs:
  - `apps/tournaments/services/registration_verification.py:28` and around `apps/tournaments/services/registration_verification.py:50`

## 2.4 on_delete behavior and history safety question

Question: "If a user disconnects a Game ID, will it cascade and accidentally delete tournament history?"

Short answer: **No direct cascade from GameProfile to tournament history models is present in current schema.**

Why:
- No tournament model has FK/OneToOne/M2M directly to `GameProfile` in model definitions.
- Tournament identity values are persisted as JSON/snapshot fields (`registration_data`, `lineup_snapshot`) or text fields, not FK references.

What does cascade when passport is deleted:
- `GameProfileAlias` rows (expected)
- `GamePassportDeleteOTP` rows (expected)

What does not cascade-delete:
- Tournament registration/history records
- Team membership records
- Match history/stat history models in tournaments

However, stale-reference behavior can occur in integer/generic references and snapshots (listed above).

---

## 3) Validation & Security

## 3.1 DB-level uniqueness/integrity controls

On `GameProfile`:
- Per-user-per-game uniqueness: `unique_together(user, game)` - `apps/user_profile/models_main.py:1884`
- Global per-game identity uniqueness: `unique_game_identity` on `(game, identity_key)` - `apps/user_profile/models_main.py:1895`

On game identity config:
- `GamePlayerIdentityConfig` uniqueness `(game, field_name)` - `apps/games/models/player_identity.py:82`

## 3.2 Validation layers currently in use

### A) Schema-driven structured validator
- `GamePassportSchemaValidator.validate_structured(...)`
- File: `apps/user_profile/validators/schema_validator.py:49`
- Enforces:
  - Required fields per game schema
  - Normalization (`identity_key` generation)
  - Region/role validity against schema choices
  - Uniqueness pre-check against `GameProfile`

### B) Payload validator used by API create/update flow
- `validate_passport_payload(...)` and helper checks
- File: `apps/user_profile/services/passport_validator.py:216`
- Includes:
  - required field checks via `GamePlayerIdentityConfig`
  - regex checks via `validation_regex`
  - select-choice checks against `GamePassportSchema`
  - immutable-field checks on update
  - visibility and pinned-count validators

### C) API-level lock/verification guards
- `check_passport_locked(...)` blocks edits/deletes if:
  - `verification_status == VERIFIED`
  - or `locked_until` in future
- File: `apps/user_profile/views/game_passports_api.py:124`

### D) Deletion-specific security flow (OTP path)
- Request OTP + resend cooldown + policy checks in `request_delete_otp`
- Confirm OTP + re-check + 90-day cooldown + delete in `confirm_delete`
- File: `apps/user_profile/views/game_passports_delete.py:27`, `apps/user_profile/views/game_passports_delete.py:177`

Checks include:
- Block verified passport deletion
- Block within identity lock window
- Block if user has active team membership for that game
- Block if user has active registration in ongoing tournament

## 3.3 Unique-claim protection (same Riot/Steam identity claimed by 2 users?)

Yes, protected at multiple levels:
- DB hard constraint: `(game, identity_key)` unique
- Pre-checks in validators and create endpoints
- IntegrityError handling maps uniqueness collision to explicit conflict response in create API
  - `apps/user_profile/views/game_passports_api.py:518` onward

## 3.4 Serializer status (requested scope includes serializers)

There are currently **no dedicated GamePassport/GameProfile serializer classes** in `apps/user_profile`.
- No serializer module under `apps/user_profile` (`apps/user_profile/**/*serial*.py` not present)
- Passport endpoints manually parse JSON + return dict responses in views:
  - `apps/user_profile/views/game_passports_api.py`
  - `apps/user_profile/views/passport_api.py`
  - `apps/user_profile/views/passport_create.py`

Validation is handled by service/validator modules instead of DRF serializers.

---

## 4) Readiness for OAuth Integration

## 4.1 Current schema support for OAuth token/account linkage

Current `GameProfile` schema does **not** include explicit OAuth linkage/token fields such as:
- provider type
- provider user id
- access token
- refresh token
- token expiry
- scope list
- token status/revocation timestamps

No equivalent token/link model is present in user_profile models currently.

## 4.2 Existing related hints

- `GamePassportSchema.requires_verification` exists as a boolean config (`apps/user_profile/models/game_passport_schema.py:164`) but does not implement provider token storage.
- Audit service explicitly treats oauth/access/refresh tokens as forbidden snapshot fields:
  - `FORBIDDEN_FIELDS` includes `oauth_token`, `access_token`, `refresh_token`
  - `apps/user_profile/services/audit.py:51`

## 4.3 Readiness verdict

Verdict: **Partially ready for identity status workflows, not ready for first-class OAuth credential management.**

What is ready:
- Per-game account model (`GameProfile`) and uniqueness model (`identity_key`)
- Verification status lifecycle (`PENDING/VERIFIED/FLAGGED`)
- Dynamic per-game schema/config (`GamePassportSchema`, `GamePlayerIdentityConfig`)

What is missing for OAuth hybrid target:
- Explicit provider account linkage fields/model
- Secure token storage + rotation metadata
- Expiry/refresh tracking fields
- Provider-specific external user identifiers separated from display identity

---

## Additional Observations (Current-State Only)

1. Multiple overlapping passport endpoints exist (legacy + newer APIs), with different validation/deletion behavior:
- Newer CRUD/identity APIs: `apps/user_profile/views/game_passports_api.py`
- OTP deletion flow: `apps/user_profile/views/game_passports_delete.py`
- Legacy/frontend endpoints still active: `apps/user_profile/views/passport_api.py`, `apps/user_profile/views/passport_create.py`
- URL wiring shows both route sets active in `apps/user_profile/urls.py:314` through `apps/user_profile/urls.py:343`.

2. Deletion behavior is not fully uniform across endpoints:
- OTP delete path applies team/tournament/cooldown checks.
- Other delete paths may bypass parts of that policy depending on endpoint used.

3. Legacy `UserProfile.game_profiles` JSON remains in model but marked deprecated; active writes are intended for `GameProfile` table.

---

## Bottom-line answer to the system-upgrade planning question

- DeltaCrown is already on a relational passport model (`GameProfile`) keyed by `(user, game)`, not a one-row-per-user 11-column nullable design.
- The schema enforces strong uniqueness for per-game identity (`identity_key`) and supports per-game dynamic validation.
- Tournament/team history is not FK-cascaded from passport rows, so deleting a passport does not directly erase tournament history.
- OAuth-specific account/token storage is not yet represented in the current database schema.
