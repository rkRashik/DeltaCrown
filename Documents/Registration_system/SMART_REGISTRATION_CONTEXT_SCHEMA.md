# SmartRegistrationView — Template Context Schema

> **Source:** `apps/tournaments/views/smart_registration.py` → `_build_context()`
> **Generated:** 2025-06-23 — Post Cross-App Sync Audit
> **Status:** All field references audited and corrected against live models.

---

## Top-Level Context Dictionary

```python
context = {
    # ── Tournament & Game Theme ────────────────────────────────────────
    "tournament":             Tournament,           # Full ORM instance (select_related('game'))
    "game_spec":              GameSpec | None,       # apps.games.services.game_service.get_game() dataclass
    "game_color":             str,                   # CSS hex, e.g. "#06b6d4" (fallback: "#06b6d4")
    "game_color_rgb":         str,                   # CSS RGB vals, e.g. "6, 182, 212"

    # ── Registration Type ──────────────────────────────────────────────
    "registration_type":      str,                   # "team" | "solo"

    # ── Auto-Fill Fields (flat dict) ───────────────────────────────────
    "fields":                 dict,                  # See §FIELDS_DICT below

    # ── Readiness Metrics ──────────────────────────────────────────────
    "readiness":              int,                   # 0-100 percentage
    "filled_count":           int,                   # number of display_keys with values
    "missing_count":          int,                   # number of display_keys without values
    "total_fields":           int,                   # len(display_keys) = 9

    # ── SVG Readiness Ring ─────────────────────────────────────────────
    "circumference":          float,                 # 2πr where r=34 → ≈213.63
    "dash_offset":            float,                 # circumference × (1 – readiness/100)

    # ── Section Completeness ───────────────────────────────────────────
    "identity_complete":      bool,                  # all of full_name, display_name, email filled
    "game_complete":          bool,                  # game_id field has a value
    "sections_complete":      int,                   # count of completed sections
    "sections_total":         int,                   # total sections (varies: 5-7)
    "sections_needing_input": int,                   # sections_total - sections_complete

    # ── Team Data (only when registration_type == "team") ─────────────
    "team":                   Team | None,           # apps.organizations.models.Team
    "roster_members":         QuerySet,              # TeamMembership QS, select_related('user'), max 12
    "user_teams":             list[Team],            # all teams user can register (multi-select)

    # ── Economy / Payment ──────────────────────────────────────────────
    "deltacoin_can_afford":   bool,                  # True if balance ≥ entry_fee_amount
    "deltacoin_balance":      int,                   # user's DeltaCoin balance

    # ── Game-ID Dynamic Label ──────────────────────────────────────────
    "game_id_label":          str,                   # "Riot ID" | "Steam ID" | "Game ID"
    "game_id_placeholder":    str,                   # "Name#TAG" | "Steam profile URL" | "Your in-game name/ID"

    # ── Custom Questions ───────────────────────────────────────────────
    "custom_questions":       list[RegistrationQuestion],  # See §CUSTOM_QUESTIONS below

    # ── Refund Policy ──────────────────────────────────────────────────
    "refund_policy":          str,                   # raw value from Tournament.refund_policy
    "refund_policy_display":  str,                   # human-readable label
    "refund_policy_text":     str,                   # freeform policy text (may be blank)

    # ── Guest Team Context ─────────────────────────────────────────────
    "is_guest_team":          bool,                  # True if guest team mode is active
    "allows_guest_teams":     bool,                  # True if tournament.max_guest_teams > 0
    "guest_slots_remaining":  int,                   # max_guest_teams - current_guest_count
    "max_guest_teams":        int,                   # tournament.max_guest_teams (0 if disabled)

    # ── Waitlist Context ───────────────────────────────────────────────
    "is_waitlist":            bool,                  # True if eligibility status == 'full_waitlist'
    "waitlist_count":         int,                   # number of currently waitlisted registrations

    # ── Display Name Override ──────────────────────────────────────────
    "allow_display_name_override": bool,             # tournament-level flag
}
```

---

## §FIELDS_DICT — `context["fields"]`

Each key maps to a dict with `{ value, locked, source }`.

| Key               | `value` type | `locked` | `source`         | Description |
|--------------------|-------------|----------|------------------|-------------|
| `full_name`        | `str`       | `bool`   | `"profile"`       | `user.get_full_name()` or `profile.real_full_name`. Locked if non-empty. |
| `display_name`     | `str`       | `bool`   | `"username"` or `"editable"` | `user.username`. Locked unless `allow_display_name_override`. |
| `email`            | `str`       | `True`   | `"account"`       | `user.email`. Always locked. |
| `phone`            | `str`       | `False`  | `"profile"`       | From `autofill_data['phone']` → `profile.phone`, else `profile.phone`. |
| `discord`          | `str`       | `False`  | `"profile"`       | From `autofill_data['discord']` → `SocialLink(platform='discord').handle`. Fallback: `profile.discord_id` / `profile.discord` (defensive getattr). |
| `country`          | `str`       | `False`  | `"profile"`       | From `autofill_data['country']` → `profile.country`. |
| `game_id`          | `str`       | `bool`   | `"game_passport"` | `autofill_data['player_id'].value` (format: `IGN#TAG`) or `autofill_data['ign'].value`. Locked if sourced from passport. |
| `platform_server`  | `str`       | `False`  | `"game_passport"` | `autofill_data['platform']` or `autofill_data['server']`. |
| `rank`             | `str`       | `bool`   | `"game_passport"` | `autofill_data['rank'].value` → `GameProfile.rank_name`. Locked if from passport. |
| `preferred_contact`| `str`       | `False`  | `"default"`       | `"discord"` if discord has value, else `"email"`. |

**Display keys** (used for readiness calculation):
```python
['full_name', 'display_name', 'email', 'phone', 'discord', 'country',
 'game_id', 'platform_server', 'rank']
```

---

## §AUTOFILL_DATA — Internal `RegistrationAutoFillService.get_autofill_data()` Structure

Each value is an `AutoFillField` dataclass:

```python
@dataclass
class AutoFillField:
    field_name: str              # key name
    value: Any                   # the auto-filled value
    source: str                  # 'profile' | 'team' | 'game_passport' | 'social_link' | 'previous_payment' | 'manual'
    confidence: str              # 'high' | 'medium' | 'low'
    needs_verification: bool     # default False
    missing: bool                # default False — True if data unavailable
    update_url: Optional[str]    # e.g. '/profile/edit/', '/settings/#game-passports'
```

### Player autofill keys (solo/both):

| Key               | Source                 | Value                                      |
|---------------------|----------------------|---------------------------------------------|
| `player_name`      | `profile`            | `"{first} {last}"` or `get_full_name()` or `""` |
| `email`            | `profile`            | `user.email`                                |
| `phone`            | `profile`            | `profile.phone` or `""` (missing)           |
| `age`              | `profile`            | `int` from `date_of_birth` or `""` (missing)|
| `country`          | `profile`            | `profile.country` or `""` (missing)         |
| `discord`          | `social_link`        | `SocialLink(platform='discord').handle` or `""` |
| `ign`              | `game_passport`      | `GameProfile.ign` or `""` (missing)         |
| `player_id`        | `game_passport`      | `"{ign}#{discriminator}"` or `"{ign}"`      |
| `rank`             | `game_passport`      | `GameProfile.rank_name` or absent           |
| `platform`         | `game_passport`      | `GameProfile.platform` or absent            |
| `region`           | `game_passport`      | `GameProfile.region` or absent              |

### Team autofill keys (when `team` is not None):

| Key               | Source    | Value                                              |
|--------------------|----------|-----------------------------------------------------|
| `team_name`        | `team`   | `team.name`                                         |
| `team_logo`        | `team`   | `team.logo.url` or `""` (missing)                   |
| `team_region`      | `team`   | `team.region` or absent                             |
| `captain_name`     | `team`   | OWNER membership `user.get_full_name()` or username |
| `captain_email`    | `team`   | OWNER membership `user.email`                       |
| `captain_phone`    | `team`   | OWNER membership `user.profile.phone` or absent     |
| `roster`           | `team`   | `list[dict]` — see §ROSTER_DATA below               |

### Payment autofill keys:

| Key               | Source                | Value                                    |
|--------------------|-----------------------|-------------------------------------------|
| `payment_mobile`   | `profile` or `previous_payment` | `profile.phone` or last `Payment.mobile_number` |

---

## §ROSTER_DATA — `autofill_data["roster"].value`

```python
[
    {
        "username": str,          # member.user.username
        "name":     str,          # member.user.get_full_name() or username
        "role":     str,          # TeamMembership.role: "OWNER" | "MANAGER" | "PLAYER" | "COACH" | "SUBSTITUTE"
        "ign":      str | None,   # GamePassportService.get_passport(user, game.slug).ign
    },
    ...
]
```

---

## §ROSTER_MEMBERS — `context["roster_members"]`

Direct QuerySet (not from autofill). Used for team roster display in the template.

```python
TeamMembership.objects.filter(
    team=team,
    status=TeamMembership.Status.ACTIVE,  # "ACTIVE"
).select_related('user').order_by('role', '-joined_at')[:12]
```

Each `TeamMembership` instance provides:
- `.user` → `User` (select_related)
- `.user.username` → `str`
- `.user.get_full_name()` → `str`
- `.role` → `str` ("OWNER", "MANAGER", "PLAYER", "COACH", "SUBSTITUTE")
- `.display_name` → `str | None`
- `.joined_at` → `datetime`
- `.is_tournament_captain` → `bool`

---

## §CUSTOM_QUESTIONS — `context["custom_questions"]`

```python
list[RegistrationQuestion]
```

Each `RegistrationQuestion` instance:

| Field            | Type       | Description |
|------------------|------------|-------------|
| `.id`            | `int`      | PK — used for form field name: `custom_q_{id}` |
| `.slug`          | `str`      | Machine key, e.g. `"rank"`, `"region"`, `"discord_username"` |
| `.text`          | `str`      | Label shown to user |
| `.help_text`     | `str`      | Additional help (may be blank) |
| `.type`          | `str`      | `"text"` \| `"select"` \| `"multi_select"` \| `"boolean"` \| `"number"` \| `"file"` \| `"date"` |
| `.scope`         | `str`      | `"team"` \| `"player"` — team-level questions excluded for solo tournaments |
| `.is_required`   | `bool`     | Must be answered |
| `.config`        | `dict`     | `{options: ["opt1", "opt2"], min: 0, max: 100, regex: "pattern"}` |
| `.order`         | `int`      | Sort order |
| `.is_active`     | `bool`     | Always `True` in queryset (filtered) |

---

## §USER_TEAMS — `context["user_teams"]`

List of `Team` instances from `apps.organizations.models.Team` that the current user has authority to register.

Authority is granted by ANY of:
1. `TeamMembership.role` is `OWNER` or `MANAGER`
2. `TeamMembership.is_tournament_captain` is `True`
3. Granular `register_tournaments` permission in `TeamMembership` JSON overrides
4. `team.created_by == user`
5. User is `Organization.ceo` for the team's org
6. User has `OrganizationMembership.role` of `CEO` or `MANAGER` in the team's org

Each `Team` provides:
- `.id` → `int`
- `.name` → `str`
- `.slug` → `str`
- `.tag` → `str`
- `.logo` → `ImageField`
- `.region` → `str`
- `.status` → `str`
- `.game_id` → `int`
- `.organization_id` → `int | None`

---

## §TOURNAMENT — Key Fields Used in Template

| Field                        | Type       | Notes |
|------------------------------|------------|-------|
| `.id`                        | `int`      | PK |
| `.name`                      | `str`      | Tournament title |
| `.slug`                      | `str`      | URL slug |
| `.game`                      | `Game`     | FK (select_related) |
| `.game.name`                 | `str`      | Game display name |
| `.game.slug`                 | `str`      | Game slug for theming |
| `.participation_type`        | `str`      | `"solo"` \| `"team"` |
| `.has_entry_fee`             | `bool`     | Whether payment is required |
| `.entry_fee_amount`          | `Decimal`  | Fee in DeltaCoin or currency |
| `.max_participants`          | `int`      | Slot cap |
| `.max_guest_teams`           | `int`      | Guest team cap (0 = disabled) |
| `.refund_policy`             | `str`      | Raw policy code |
| `.refund_policy_text`        | `str`      | Freeform policy text |
| `.get_refund_policy_display()` | `str`   | Human-readable label |
| `.allow_display_name_override` | `bool`  | Let users change display_name |
| `.start_date` / `.end_date`  | `datetime` | Tournament schedule |
| `.registration_start_date` / `.registration_end_date` | `datetime` | Reg window |

---

## §GAME_SPEC — `context["game_spec"]`

Dataclass from `apps.games.services.game_service`. May be `None`.

| Attribute           | Type   | Example |
|----------------------|--------|---------|
| `.slug`              | `str`  | `"valorant"` |
| `.name`              | `str`  | `"VALORANT"` |
| `.primary_color`     | `str`  | `"#ff4655"` |
| `.primary_color_rgb` | `str`  | `"255, 70, 85"` |
| *(other game metadata)* | — | — |

---

## §SECTION_FLAGS — Progressive Disclosure Logic

The sections evaluated for the summary bar:

| Section     | Condition for `True`                 | Always present? |
|-------------|--------------------------------------|-----------------|
| `identity`  | `full_name + display_name + email` all filled | Yes |
| `game`      | `game_id` has a value                | Yes |
| `team`      | `team is not None`                   | Only if `is_team` |
| `contact`   | Always `True` (has defaults)         | Yes |
| `details`   | Always `True` (read-only info)       | Yes |
| `payment`   | Always `False` (needs user action)   | Only if `has_entry_fee` |
| `terms`     | Always `False` (needs checkboxes)    | Yes |

---

## §POST_DATA — Form Submission Field Names

These are the `name` attributes the template must use in `<form>` inputs:

| Field Name                  | Context Key            | Notes |
|-----------------------------|------------------------|-------|
| `full_name`                 | `fields.full_name`     | |
| `display_name`              | `fields.display_name`  | |
| `email`                     | `fields.email`         | |
| `phone`                     | `fields.phone`         | |
| `discord`                   | `fields.discord`       | |
| `country`                   | `fields.country`       | |
| `game_id`                   | `fields.game_id`       | Required |
| `platform_server`           | `fields.platform_server` | |
| `rank`                      | `fields.rank`          | |
| `preferred_contact`         | `fields.preferred_contact` | `"discord"` \| `"email"` |
| `team_id`                   | `team.id`              | Required for team tournaments (hidden or select) |
| `payment_method`            | —                      | `"deltacoin"` \| `"bkash"` \| `"nagad"` \| `"rocket"` |
| `transaction_id`            | —                      | Required for mobile payment methods |
| `payment_proof`             | —                      | File input, max 5MB |
| `registration_type`         | —                      | `"guest_team"` for guest submissions |
| `guest_team_name`           | —                      | Guest team name |
| `guest_team_tag`            | —                      | Guest team tag |
| `guest_team_justification`  | —                      | Why this guest team |
| `member_game_id_{N}`        | —                      | Guest member game IDs (0-indexed) |
| `member_display_name_{N}`   | —                      | Guest member names (0-indexed, max 20) |
| `custom_q_{question.id}`    | —                      | One per RegistrationQuestion |

---

## §INELIGIBLE_CONTEXT — `_render_ineligible()` Context

Separate template: `tournaments/registration/smart_ineligible.html`

```python
{
    "tournament":    Tournament,
    "game_color":    str,           # hex
    "game_color_rgb": str,         # RGB values
    "reasons":       list[str],    # e.g. ["Registration is closed"]
    "suggestions":   list[str],    # actionable hints
}
```

---

## §SUCCESS_CONTEXT — `SmartRegistrationSuccessView` Context

Template: `tournaments/registration/smart_success.html`

```python
{
    "tournament":    Tournament,
    "registration":  Registration,   # the created Registration instance
    "team":          Team | None,    # registration.team
    "game_color":    str,
    "game_color_rgb": str,
}
```
