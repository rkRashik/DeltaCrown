# DeltaCrown Tournament Seeding — Complete Model Reference

> Generated: 2026-03-06  
> Purpose: All Django models, fields, relationships, and choices needed to seed a complete tournament.

---

## Table of Contents

1. [accounts.User](#1-accountsuser)
2. [user_profile.UserProfile](#2-user_profileuserprofile)
3. [user_profile.GameProfile (Game Passport)](#3-user_profilegameprofile-game-passport)
4. [games.Game](#4-gamesgame)
5. [games.GameRosterConfig](#5-gamesgamerosterconfig)
6. [games.GameTournamentConfig](#6-gamesgametournamentconfig)
7. [games.GamePlayerIdentityConfig](#7-gamesgameplayeridentityconfig)
8. [games.GameRole](#8-gamesgamerole)
9. [organizations.Organization](#9-organizationsorganization)
10. [teams.Team (Legacy)](#10-teamsteam-legacy)
11. [teams.TeamMembership (Legacy)](#11-teamsteammembership-legacy)
12. [tournaments.Tournament](#12-tournamentstournament)
13. [tournaments.Registration](#13-tournamentsregistration)
14. [tournaments.Payment](#14-tournamentspayment)
15. [tournaments.TournamentPaymentMethod](#15-tournamentstournamentpaymentmethod)
16. [tournaments.Bracket](#16-tournamentsbracket)
17. [tournaments.BracketNode](#17-tournamentsbracketnode)
18. [tournaments.Match](#18-tournamentsmatch)
19. [tournaments.Group & GroupStanding](#19-tournamentsgroup--groupstanding)
20. [tournaments.TournamentAnnouncement](#20-tournamentsannouncementtournamentannouncement)
21. [tournaments.TournamentStaff (Legacy) & StaffRole](#21-tournamentstournamentstaff-legacy--staffrole)
22. [tournaments.TournamentStaffAssignment (Phase 7)](#22-tournamentstournamentstaffassignment-phase-7)
23. [tournaments.Certificate](#23-tournamentscertificate)
24. [tournaments.PrizeTransaction](#24-tournamentsprizetransaction)
25. [economy.CoinPolicy](#25-economycoinpolicy)
26. [Existing Seed Scripts](#26-existing-seed-scripts)
27. [Valorant-Specific Config Values](#27-valorant-specific-config-values)

---

## 1. accounts.User

**Path:** `apps/accounts/models.py` → `apps.accounts.models.User`  
**Extends:** `AbstractUser`  
**DB Table:** default (`accounts_user`)

### Fields
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `username` | CharField(150) | Yes | Unique |
| `email` | EmailField | Yes | **Unique** (overridden from AbstractUser) |
| `password` | CharField(128) | Yes | Inherited |
| `first_name` | CharField(150) | No | Inherited |
| `last_name` | CharField(150) | No | Inherited |
| `is_active` | BooleanField | — | Default `True` |
| `is_staff` | BooleanField | — | Default `False` |
| `is_superuser` | BooleanField | — | Default `False` |
| `is_verified` | BooleanField | — | Default `False` |
| `email_verified_at` | DateTimeField | No | Null/blank OK |

### Key Methods
- `mark_email_verified()` — sets `is_verified=True`, `email_verified_at=now()`
- `__str__` — returns `"username (DC-YY-NNNNNN)"` if profile exists

### Seeding Pattern
```python
from apps.accounts.models import User
user, _ = User.objects.get_or_create(
    username='seed_player_01',
    defaults={
        'email': 'player01@seed.deltacrown.local',
        'first_name': 'Player',
        'last_name': 'One',
        'is_active': True,
        'is_verified': True,
    }
)
```

---

## 2. user_profile.UserProfile

**Path:** `apps/user_profile/models_main.py` → `apps.user_profile.models_main.UserProfile`  
**DB Table:** default (`user_profile_userprofile`)

### Key Fields
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `user` | **OneToOneField(User)** | Yes | `related_name='profile'` |
| `uuid` | UUIDField | Auto | `default=uuid4`, unique, editable=False |
| `public_id` | CharField(15) | Auto | `DC-YY-NNNNNN` format, unique |
| `display_name` | CharField(80) | Yes | — |
| `slug` | SlugField(64) | No | Unique, blank OK |
| `avatar` | ImageField | No | `upload_to='user_avatars/{user_id}/'` |
| `banner` | ImageField | No | `upload_to='user_banners/{user_id}/'` |
| `bio` | TextField | No | Blank OK |
| `country` | CountryField | No | ISO country code |
| `region` | CharField(2) | — | Default `'BD'`. Choices: `BD, SA, AS, EU, NA` |
| `city` | CharField(100) | No | — |
| `gender` | CharField(20) | No | `male, female, other, prefer_not_to_say` |
| `phone` | CharField(20) | No | International format |
| `real_full_name` | CharField(200) | No | For KYC/certificates |
| `kyc_status` | CharField(20) | — | Default `'unverified'`. Choices: `unverified, pending, verified, rejected` |

### Signal / Auto-creation
UserProfile is likely auto-created via a signal on User creation. If not, create manually:
```python
from apps.user_profile.models_main import UserProfile
profile, _ = UserProfile.objects.get_or_create(
    user=user,
    defaults={
        'display_name': user.username,
        'region': 'BD',
        'country': 'BD',
    }
)
```

---

## 3. user_profile.GameProfile (Game Passport)

**Path:** `apps/user_profile/models_main.py` → `apps.user_profile.models_main.GameProfile`  
**DB Table:** default (`user_profile_gameprofile`)

### Key Fields
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `user` | **FK(User)** | Yes | `related_name='game_profiles'` |
| `game` | **FK(games.Game)** | Yes | `related_name='passports'`, on_delete=PROTECT |
| `game_display_name` | CharField(100) | Auto | editable=False |
| `ign` | CharField(64) | No | In-game name (e.g., `Player123`) |
| `discriminator` | CharField(32) | No | Tag (e.g., `#NA1`) |
| `platform` | CharField(32) | No | e.g., `PC`, `PS5` |
| `in_game_name` | CharField(100) | Yes | Display name (computed: `ign+discriminator`) |
| `identity_key` | CharField(100) | Yes | Normalized for uniqueness |
| `rank_name` | CharField(50) | No | e.g., `Diamond 2` |
| `rank_tier` | IntegerField | — | Default 0 |
| `matches_played` | IntegerField | — | Default 0 |
| `win_rate` | IntegerField | — | Default 0 (0-100) |
| `visibility` | CharField | — | `PUBLIC, PROTECTED, PRIVATE` |
| `status` | CharField | — | `ACTIVE, SUSPENDED` |

### Seeding Pattern (Valorant Riot ID)
```python
from apps.user_profile.models_main import GameProfile
gp, _ = GameProfile.objects.get_or_create(
    user=user,
    game=valorant_game,
    defaults={
        'game_display_name': 'VALORANT',
        'ign': 'PlayerName',
        'discriminator': '#TAG',
        'in_game_name': 'PlayerName#TAG',
        'identity_key': 'playername#tag',
        'rank_name': 'Diamond 2',
    }
)
```

---

## 4. games.Game

**Path:** `apps/games/models/game.py` → `apps.games.models.Game`  
**DB Table:** `games_game`

### Key Fields
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | CharField(100) | Yes | Unique (`'VALORANT'`) |
| `display_name` | CharField(150) | Yes | (`'VALORANT'`) |
| `slug` | SlugField | Yes | Unique. **Valorant = `'valorant'`** |
| `short_code` | CharField(10) | Yes | Unique (`'VAL'`) |
| `category` | CharField(50) | Yes | `FPS, MOBA, BR, SPORTS, FIGHTING, STRATEGY, CCG, OTHER` |
| `game_type` | CharField(50) | — | Default `'TEAM_VS_TEAM'`. Choices: `TEAM_VS_TEAM, 1V1, BATTLE_ROYALE, FREE_FOR_ALL` |
| `platforms` | JSONField | — | e.g., `['PC']` |
| `has_servers` | BooleanField | — | Default False |
| `has_rank_system` | BooleanField | — | Default False |
| `available_ranks` | JSONField | — | `[{'value': 'iron', 'label': 'Iron'}, ...]` |
| `primary_color` | CharField(7) | — | Hex, default `'#7c3aed'` |
| `secondary_color` | CharField(7) | — | Hex, default `'#1e1b4b'` |
| `is_active` | BooleanField | — | Default True |
| `is_featured` | BooleanField | — | Default False |
| `is_passport_supported` | BooleanField | — | Default False |
| `game_id_label` | CharField(50) | No | e.g., `'Riot ID'` |
| `game_id_placeholder` | CharField(100) | No | e.g., `'Username#TAG'` |
| `description` | TextField | No | — |
| `developer` | CharField(100) | No | — |
| `publisher` | CharField(100) | No | — |

### `__str__`
Returns `display_name`

### Seeding
Use `init_default_games` management command, or:
```python
game, _ = Game.objects.get_or_create(
    slug='valorant',
    defaults={
        'name': 'VALORANT',
        'display_name': 'VALORANT',
        'short_code': 'VAL',
        'category': 'FPS',
        'game_type': 'TEAM_VS_TEAM',
        'platforms': ['PC'],
        'has_rank_system': True,
        'primary_color': '#ff4655',
        'secondary_color': '#0f1923',
        'is_active': True,
    }
)
```

---

## 5. games.GameRosterConfig

**Path:** `apps/games/models/roster_config.py`  
**DB Table:** `games_roster_config`

### Fields
| Field | Type | Notes |
|-------|------|-------|
| `game` | **OneToOneField(Game)** | `related_name='roster_config'` |
| `min_team_size` | IntegerField | Default 1 |
| `max_team_size` | IntegerField | Default 5 |
| `min_substitutes` | IntegerField | Default 0 |
| `max_substitutes` | IntegerField | Default 2 |
| `min_roster_size` | IntegerField | Default 1 |
| `max_roster_size` | IntegerField | Default 10 |
| `allow_coaches` | BooleanField | Default True |
| `max_coaches` | IntegerField | Default 2 |
| `allow_analysts` | BooleanField | Default True |
| `max_analysts` | IntegerField | Default 1 |
| `allow_managers` | BooleanField | Default True |
| `max_managers` | IntegerField | Default 2 |
| `has_roles` | BooleanField | Default False |
| `has_regions` | BooleanField | Default False |

### Valorant Values
```python
GameRosterConfig.objects.get_or_create(
    game=valorant,
    defaults={
        'min_team_size': 5, 'max_team_size': 5,
        'min_substitutes': 0, 'max_substitutes': 2,
        'min_roster_size': 5, 'max_roster_size': 7,
    }
)
```

---

## 6. games.GameTournamentConfig

**Path:** `apps/games/models/tournament_config.py`  
**DB Table:** `games_tournament_config`

### Key Fields
| Field | Type | Notes |
|-------|------|-------|
| `game` | **OneToOneField(Game)** | `related_name='tournament_config'` |
| `available_match_formats` | JSONField | e.g., `['BO1', 'BO3', 'BO5']` |
| `default_match_format` | CharField(20) | Choices: `BO1, BO3, BO5, BO7, SINGLE, SERIES` |
| `default_scoring_type` | CharField(20) | Choices: `WIN_LOSS, POINTS, ROUNDS, KILLS, PLACEMENT, GOALS, CUSTOM` |
| `scoring_rules` | JSONField | — |
| `default_tiebreakers` | JSONField | — |
| `supports_single_elimination` | BooleanField | Default True |
| `supports_double_elimination` | BooleanField | Default True |
| `supports_round_robin` | BooleanField | Default True |
| `supports_swiss` | BooleanField | Default False |
| `supports_group_stage` | BooleanField | Default True |
| `default_match_duration_minutes` | IntegerField | Default 60 |
| `allow_draws` | BooleanField | Default False |
| `overtime_enabled` | BooleanField | Default True |
| `min_team_size` | IntegerField | Default 1 |
| `max_team_size` | IntegerField | Default 5 |

### Valorant Values
```python
GameTournamentConfig.objects.get_or_create(
    game=valorant,
    defaults={
        'available_match_formats': ['BO1', 'BO3', 'BO5'],
        'default_match_format': 'BO3',
        'default_scoring_type': 'ROUNDS',
        'scoring_rules': {'win_points': 3, 'draw_points': 0, 'loss_points': 0},
        'default_tiebreakers': ['head_to_head', 'round_diff', 'rounds_won'],
        'supports_swiss': True,
        'allow_draws': False,
        'overtime_enabled': True,
        'min_team_size': 5,
        'max_team_size': 7,
    }
)
```

---

## 7. games.GamePlayerIdentityConfig

**Path:** `apps/games/models/player_identity.py`  
**DB Table:** `games_player_identity_config`

### Fields
| Field | Type | Notes |
|-------|------|-------|
| `game` | **FK(Game)** | `related_name='identity_configs'` |
| `field_name` | CharField(50) | e.g., `'riot_id'` |
| `display_name` | CharField(100) | e.g., `'Riot ID'` |
| `field_type` | CharField(20) | `TEXT, NUMBER, EMAIL, URL` |
| `is_required` | BooleanField | Default True |
| `is_immutable` | BooleanField | Default False |
| `validation_regex` | CharField(500) | — |
| `validation_error_message` | CharField(200) | — |
| `placeholder` | CharField(200) | e.g., `'PlayerName#1234'` |
| `help_text` | TextField | — |
| `order` | IntegerField | Default 0 |

**Unique Together:** `(game, field_name)`

### Valorant
```python
GamePlayerIdentityConfig.objects.get_or_create(
    game=valorant,
    field_name='riot_id',
    defaults={
        'display_name': 'Riot ID',
        'field_type': 'TEXT',
        'is_required': True,
        'placeholder': 'PlayerName#TAG',
        'validation_regex': r'^.+#.+$',
        'validation_error_message': 'Must be in format Name#Tag',
    }
)
```

---

## 8. games.GameRole

**Path:** `apps/games/models/role.py`  
**DB Table:** `games_role`

### Fields
| Field | Type | Notes |
|-------|------|-------|
| `game` | **FK(Game)** | `related_name='roles'` |
| `role_name` | CharField(50) | e.g., `'Duelist'` |
| `role_code` | CharField(20) | e.g., `'DUE'` |
| `description` | TextField | — |
| `icon` | CharField(50) | Emoji or icon ID |
| `color` | CharField(7) | Hex color |
| `order` | IntegerField | Default 0 |
| `is_competitive` | BooleanField | Default True |
| `is_active` | BooleanField | Default True |

**Unique Together:** `(game, role_name)`

### Valorant Roles
- Duelist (DUE, 🎯, #ff4655)
- Initiator (INI, ⚡, #00bfa5)
- Controller (CTRL, 🌫️, #7c3aed)
- Sentinel (SEN, 🛡️, #2196f3)

---

## 9. organizations.Organization

**Path:** `apps/organizations/models/organization.py`  
**DB Table:** `organizations_organization`

### Key Fields
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `uuid` | UUIDField | Auto | — |
| `public_id` | CharField(20) | Auto | `ORG_XXXXXXXXXX` format |
| `name` | CharField(100) | Yes | Unique |
| `slug` | SlugField(100) | Auto | Unique, auto from name |
| `ceo` | **FK(User)** | Yes | `related_name='owned_organizations'`, on_delete=PROTECT |
| `is_verified` | BooleanField | — | Default False |
| `logo` | ImageField | No | — |
| `banner` | ImageField | No | — |
| `description` | TextField | No | — |
| `website` | URLField | No | — |
| `enforce_brand` | BooleanField | — | Default False |

### `__str__`
Returns `"OrgName ✓"` if verified

---

## 10. teams.Team (Legacy)

**Path:** `apps/teams/models/_legacy.py` → also re-exported from `apps/teams/models/team.py`  
**Import:** `from apps.organizations.models import Team` (as used in seed_demo_tournaments)  
**DB Table:** `teams_team`

> **Note:** Phase 5 has write enforcement. In seed scripts, Team is imported from `apps.organizations.models` OR directly if legacy writes are allowed.

### Key Fields
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | CharField(100) | Yes | Unique |
| `tag` | CharField(10) | Yes | Unique, abbreviation |
| `description` | TextField(500) | No | — |
| `logo` | ImageField | No | `upload_to='team_logos/{id}/'` |
| `game` | CharField(50) | No | **Game slug** (e.g., `'valorant'`) — NOT a FK |
| `slug` | SlugField(64) | No | Unique per game |
| `region` | CharField(48) | No | — |
| `is_active` | BooleanField | — | Default True |
| `is_public` | BooleanField | — | Default True |
| `is_verified` | BooleanField | — | Default False |
| `total_points` | PositiveIntegerField | — | Default 0 |
| `tagline` | CharField(200) | No | — |
| `is_recruiting` | BooleanField | — | Default False |
| `allow_join_requests` | BooleanField | — | Default True |

### Properties
- `captain` — determined by OWNER role in TeamMembership
- `members_count` — count of ACTIVE memberships
- `max_roster_size` — from GameRosterConfig

### `__str__`
Returns `"TeamName (TAG)"`

### Seeding Pattern
```python
from apps.organizations.models import Team  # or apps.teams.models
team, _ = Team.objects.get_or_create(
    slug='my-team-slug',
    defaults={
        'name': 'My Team',
        'tag': 'MT',
        'game': 'valorant',
        'region': 'BD',
        'is_active': True,
        'is_public': True,
    }
)
```

---

## 11. teams.TeamMembership (Legacy)

**Path:** `apps/teams/models/_legacy.py` → re-exported from `apps/teams/models/membership.py`  
**DB Table:** `teams_teammembership`

### Role Choices (`TeamMembership.Role`)
**Ownership/Management:**
- `OWNER` — Team Owner
- `GENERAL_MANAGER`
- `TEAM_MANAGER`

**Coaching:**
- `HEAD_COACH`, `ASSISTANT_COACH`, `PERFORMANCE_COACH`

**Analysis:**
- `ANALYST`, `STRATEGIST`, `DATA_ANALYST`

**Players:**
- `PLAYER` — Default
- `SUBSTITUTE`

**Content:**
- `CONTENT_CREATOR`, `SOCIAL_MEDIA_MANAGER`, `COMMUNITY_MANAGER`

**Legacy (Deprecated):**
- `MANAGER`, `COACH`, `CAPTAIN`, `SUB`

### Status Choices (`TeamMembership.Status`)
- `ACTIVE`, `PENDING`, `REMOVED`

### RosterSlot Choices
- `STARTER`, `SUBSTITUTE`, `COACH`, `ANALYST`

### Key Fields
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `team` | **FK(Team)** | Yes | `related_name='memberships'` |
| `profile` | **FK(UserProfile)** | Yes | `related_name='team_memberships'` |
| `role` | CharField(30) | — | Default `'PLAYER'` |
| `status` | CharField(16) | — | Default `'ACTIVE'` |
| `roster_slot` | CharField(16) | No | `STARTER, SUBSTITUTE, COACH, ANALYST` |
| `is_captain` | BooleanField | — | Default False |
| `player_role` | CharField(50) | No | In-game role (e.g., `'Duelist'`) |
| `joined_at` | DateTimeField | — | Default `timezone.now` |
| `can_register_tournaments` | BooleanField | — | Default False |
| `can_invite_members` | BooleanField | — | Default False |
| ... (many granular permission booleans) |

### Seeding Pattern
```python
from apps.teams.models import TeamMembership
membership, _ = TeamMembership.objects.get_or_create(
    team=team,
    profile=user_profile,
    defaults={
        'role': TeamMembership.Role.OWNER,  # or 'PLAYER'
        'status': TeamMembership.Status.ACTIVE,
        'roster_slot': 'STARTER',
        'is_captain': True,
        'player_role': 'Duelist',
    }
)
```

---

## 12. tournaments.Tournament

**Path:** `apps/tournaments/models/tournament.py`  
**DB Table:** default (`tournaments_tournament`)  
**Inherits:** `SoftDeleteModel, TimestampedModel`

### STATUS_CHOICES
| Value | Label |
|-------|-------|
| `draft` | Draft |
| `pending_approval` | Pending Approval |
| `published` | Published |
| `registration_open` | Registration Open |
| `registration_closed` | Registration Closed |
| `live` | Live |
| `completed` | Completed |
| `cancelled` | Cancelled |
| `archived` | Archived |

### FORMAT_CHOICES
| Value | Constant | Label |
|-------|----------|-------|
| `single_elimination` | `SINGLE_ELIM` | Single Elimination |
| `double_elimination` | `DOUBLE_ELIM` | Double Elimination |
| `round_robin` | `ROUND_ROBIN` | Round Robin |
| `swiss` | `SWISS` | Swiss |
| `group_playoff` | `GROUP_PLAYOFF` | Group Stage + Playoff |

### PARTICIPATION_TYPE_CHOICES
| Value | Label |
|-------|-------|
| `team` | Team |
| `solo` | Solo/Individual |

### PLATFORM_CHOICES
`pc, mobile, ps5, xbox, switch`

### MODE_CHOICES
`online, lan, hybrid`

### PAYMENT_METHOD_CHOICES
`deltacoin, bkash, nagad, rocket, bank_transfer`

### REFUND_POLICY_CHOICES
`no_refund, refund_until_checkin, refund_until_bracket, full_refund, custom`

### Key Fields (ALL)
| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| `name` | CharField(200) | Yes | — | — |
| `slug` | SlugField(250) | Auto | — | Unique, auto-generated |
| `description` | TextField | Yes | — | — |
| `organizer` | **FK(accounts.User)** | Yes | — | on_delete=PROTECT |
| `is_official` | BooleanField | — | False | — |
| `is_featured` | BooleanField | — | False | — |
| `game` | **FK(games.Game)** | Yes | — | on_delete=PROTECT |
| `format` | CharField(50) | — | `'single_elimination'` | — |
| `participation_type` | CharField(20) | — | `'team'` | — |
| `platform` | CharField(20) | — | `'pc'` | — |
| `mode` | CharField(10) | — | `'online'` | — |
| `venue_name` | CharField(200) | No | `''` | For LAN |
| `venue_address` | TextField | No | `''` | — |
| `venue_city` | CharField(100) | No | `''` | — |
| `max_participants` | PositiveIntegerField | — | 16 | Min 2, Max 256 |
| `min_participants` | PositiveIntegerField | — | 2 | Min 2 |
| `registration_start` | DateTimeField | **Yes** | — | — |
| `registration_end` | DateTimeField | **Yes** | — | — |
| `tournament_start` | DateTimeField | **Yes** | — | — |
| `tournament_end` | DateTimeField | No | — | — |
| `timezone_name` | CharField(64) | — | `'Asia/Dhaka'` | IANA tz |
| `prize_pool` | DecimalField(10,2) | — | 0.00 | — |
| `prize_currency` | CharField(10) | — | `'BDT'` | — |
| `prize_deltacoin` | PositiveIntegerField | — | 0 | — |
| `prize_distribution` | JSONField | — | `{}` | `{"1": "50%", "2": "30%"}` |
| `has_entry_fee` | BooleanField | — | False | — |
| `entry_fee_amount` | DecimalField(10,2) | — | 0.00 | — |
| `entry_fee_currency` | CharField(10) | — | `'BDT'` | — |
| `entry_fee_deltacoin` | PositiveIntegerField | — | 0 | — |
| `payment_deadline_hours` | PositiveIntegerField | — | 48 | — |
| `payment_methods` | ArrayField(CharField) | — | `[]` | PostgreSQL only |
| `refund_policy` | CharField(30) | — | `'no_refund'` | — |
| `banner_image` | ImageField | No | — | — |
| `thumbnail_image` | ImageField | No | — | — |
| `rules_text` | TextField | No | — | — |
| `terms_and_conditions` | TextField | No | — | — |
| `require_terms_acceptance` | BooleanField | — | True | — |
| `status` | CharField(30) | — | `'draft'` | — |
| `cancellation_reason` | TextField | No | `''` | — |
| `published_at` | DateTimeField | No | — | — |
| `total_registrations` | PositiveIntegerField | — | 0 | Denormalized |
| `total_matches` | PositiveIntegerField | — | 0 | Denormalized |
| `completed_matches` | PositiveIntegerField | — | 0 | Denormalized |
| `config` | JSONField | — | `{}` | Advanced config |
| `enable_check_in` | BooleanField | — | True | — |
| `check_in_minutes_before` | PositiveIntegerField | — | 15 | — |
| `enable_certificates` | BooleanField | — | True | — |
| `enable_challenges` | BooleanField | — | False | — |
| `enable_fan_voting` | BooleanField | — | False | — |
| `max_guest_teams` | PositiveIntegerField | — | 0 | — |
| `allow_display_name_override` | BooleanField | — | False | — |
| `social_discord` | URLField | No | `''` | — |
| `contact_email` | EmailField | No | `''` | — |
| `contact_phone` | CharField(20) | No | `''` | — |
| `stream_youtube_url` | URLField | No | — | — |
| `stream_twitch_url` | URLField | No | — | — |
| `meta_description` | TextField | No | — | — |
| `meta_keywords` | ArrayField(CharField) | — | `[]` | — |
| `registration_form_overrides` | JSONField | — | `{}` | — |

### `__str__`
Returns `"Tournament Name (Game Name)"`

### Slug Behavior
Auto-generated from name via `slugify()` with uniqueness counter.

### Seeding Pattern
```python
from apps.tournaments.models import Tournament
from datetime import timedelta
from decimal import Decimal

tournament = Tournament.objects.create(
    name='VALORANT Championship S1',
    game=game,
    organizer=organizer_user,
    format=Tournament.SINGLE_ELIM,
    participation_type=Tournament.TEAM,
    platform=Tournament.PC,
    mode=Tournament.ONLINE,
    status=Tournament.REGISTRATION_OPEN,
    max_participants=16,
    min_participants=4,
    registration_start=timezone.now() - timedelta(days=7),
    registration_end=timezone.now() + timedelta(days=7),
    tournament_start=timezone.now() + timedelta(days=14),
    has_entry_fee=True,
    entry_fee_amount=Decimal('200.00'),
    entry_fee_currency='BDT',
    prize_pool=Decimal('10000.00'),
    prize_currency='BDT',
    payment_methods=['bkash', 'nagad'],
    description='Official Valorant Championship Season 1',
)
```

---

## 13. tournaments.Registration

**Path:** `apps/tournaments/models/registration.py`  
**DB Table:** `tournaments_registration`  
**Inherits:** `SoftDeleteModel, TimestampedModel`

### STATUS_CHOICES
| Value | Label |
|-------|-------|
| `draft` | Draft |
| `submitted` | Submitted |
| `pending` | Pending |
| `auto_approved` | Auto Approved |
| `needs_review` | Needs Review |
| `payment_submitted` | Payment Submitted |
| `confirmed` | Confirmed |
| `rejected` | Rejected |
| `cancelled` | Cancelled |
| `waitlisted` | Waitlisted |
| `no_show` | No Show |

### Key Fields
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `tournament` | **FK(Tournament)** | Yes | `related_name='registrations'`, CASCADE |
| `user` | **FK(accounts.User)** | No* | `related_name='tournament_registrations'` |
| `team_id` | IntegerField | No* | Team ID (avoids circular FK) |
| `registration_data` | JSONField | — | Default `{}` |
| `status` | CharField(20) | — | Default `'pending'` |
| `registration_number` | CharField(30) | Auto | Unique, `DC-YY-NNNN` format |
| `slot_number` | IntegerField | No | Bracket position (1-based) |
| `seed` | IntegerField | No | Lower = higher seed |
| `checked_in` | BooleanField | — | Default False |
| `checked_in_at` | DateTimeField | No | — |
| `lineup_snapshot` | JSONField | — | `[{user_id, username, game_id, role}]` |
| `is_guest_team` | BooleanField | — | Default False |
| `completion_percentage` | DecimalField(5,2) | — | Default 0.00 |
| `current_step` | PositiveIntegerField | — | Default 1 |

> **XOR Constraint:** Either `user` OR `team_id` must be set, not both.  
> **Unique Together:** `(tournament, user)` — one registration per user per tournament.

### Seeding Pattern
```python
reg = Registration.objects.create(
    tournament=tournament,
    team_id=team.id,       # For team tournaments
    # OR user=user,        # For solo tournaments
    status=Registration.CONFIRMED,
    slot_number=1,
    checked_in=True,
    checked_in_at=timezone.now(),
)
```

---

## 14. tournaments.Payment

**Path:** `apps/tournaments/models/registration.py`  
**DB Table:** `tournaments_payment`

### PAYMENT_METHOD_CHOICES
`bkash, nagad, rocket, bank, deltacoin`

### STATUS_CHOICES
`pending, submitted, verified, rejected, refunded, waived, expired`

### Key Fields
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `registration` | **OneToOneField(Registration)** | Yes | `related_name='payment'` |
| `payment_method` | CharField(20) | Yes | — |
| `amount` | DecimalField(10,2) | Yes | Must be > 0 |
| `transaction_id` | CharField(200) | No | — |
| `payment_proof` | FileField | No | `upload_to='payment_proofs/%Y/%m/'` |
| `status` | CharField(20) | — | Default `'pending'` |
| `admin_notes` | TextField | No | — |
| `verified_by` | FK(User) | No | — |
| `verified_at` | DateTimeField | No | — |
| `waived` | BooleanField | — | Default False |
| `proof_image` | ImageField | No | — |
| `payer_account_number` | CharField(32) | No | — |
| `amount_bdt` | PositiveIntegerField | No | — |
| `idempotency_key` | CharField(255) | No | Unique |

### Seeding Pattern (for paid tournaments)
```python
from apps.tournaments.models.registration import Payment
payment = Payment.objects.create(
    registration=registration,
    payment_method='bkash',
    amount=Decimal('200.00'),
    transaction_id='TXN123456',
    status=Payment.VERIFIED,
    verified_by=organizer_user,
    verified_at=timezone.now(),
)
```

---

## 15. tournaments.TournamentPaymentMethod

**Path:** `apps/tournaments/models/payment_config.py`  
**DB Table:** default

### Key Fields
| Field | Type | Notes |
|-------|------|-------|
| `tournament` | **FK(Tournament)** | `related_name='payment_configurations'` |
| `method` | CharField(20) | `deltacoin, bkash, nagad, rocket, bank_transfer` |
| `is_enabled` | BooleanField | Default True |
| `display_order` | PositiveIntegerField | Default 0 |
| `bkash_account_number` | CharField(20) | — |
| `bkash_account_type` | CharField(20) | `personal, merchant, agent` |
| `bkash_account_name` | CharField(100) | — |
| `bkash_instructions` | TextField | — |
| (similar fields for nagad, rocket, bank) |

### Seeding Pattern
```python
from apps.tournaments.models.payment_config import TournamentPaymentMethod
TournamentPaymentMethod.objects.create(
    tournament=tournament,
    method='bkash',
    is_enabled=True,
    bkash_account_number='01712345678',
    bkash_account_type='personal',
    bkash_account_name='DeltaCrown',
    bkash_instructions='Send to 01712345678 via bKash. Use tournament ID as reference.',
)
```

---

## 16. tournaments.Bracket

**Path:** `apps/tournaments/models/bracket.py`  
**DB Table:** `tournament_engine_bracket_bracket`  
**Inherits:** `TimestampedModel`

### FORMAT_CHOICES
| Value | Label |
|-------|-------|
| `single-elimination` | Single Elimination |
| `double-elimination` | Double Elimination |
| `round-robin` | Round Robin |
| `swiss` | Swiss System |
| `group-stage` | Group Stage |

### SEEDING_METHOD_CHOICES
`slot-order, random, ranked, manual`

### Fields
| Field | Type | Notes |
|-------|------|-------|
| `tournament` | **OneToOneField(Tournament)** | `related_name='bracket'` |
| `format` | CharField(50) | Default `'single-elimination'` |
| `total_rounds` | PositiveIntegerField | Default 0 |
| `total_matches` | PositiveIntegerField | Default 0 |
| `bracket_structure` | JSONField | Tree structure metadata |
| `seeding_method` | CharField(30) | Default `'slot-order'` |
| `is_finalized` | BooleanField | Default False |

---

## 17. tournaments.BracketNode

**Path:** `apps/tournaments/models/bracket.py`  
**DB Table:** `tournament_engine_bracket_bracketnode`

### Fields
| Field | Type | Notes |
|-------|------|-------|
| `bracket` | **FK(Bracket)** | `related_name='nodes'` |
| `position` | PositiveIntegerField | Unique per bracket |
| `round_number` | PositiveIntegerField | 1-indexed |
| `match_number_in_round` | PositiveIntegerField | 1-indexed |
| `match` | OneToOneField(Match) | nullable |
| `participant1_id` | IntegerField | nullable |
| `participant1_name` | CharField(100) | cached |
| `participant2_id` | IntegerField | nullable |
| `participant2_name` | CharField(100) | cached |
| `winner_id` | IntegerField | nullable |
| `parent_node` | FK(self) | nullable — winner advances here |
| `parent_slot` | PositiveSmallIntegerField | 1 or 2 |
| `child1_node` | FK(self) | nullable |
| `child2_node` | FK(self) | nullable |
| `is_bye` | BooleanField | Default False |
| `bracket_type` | CharField(50) | `main, losers, third-place, group-N` |

---

## 18. tournaments.Match

**Path:** `apps/tournaments/models/match.py`  
**DB Table:** `tournament_engine_match_match`  
**Inherits:** `SoftDeleteModel, TimestampedModel`

### STATE_CHOICES
| Value | Label |
|-------|-------|
| `scheduled` | Scheduled |
| `check_in` | Check-in Open |
| `ready` | Ready to Start |
| `live` | Live/In Progress |
| `pending_result` | Pending Result |
| `completed` | Completed |
| `disputed` | Disputed |
| `forfeit` | Forfeit |
| `cancelled` | Cancelled |

### Key Fields
| Field | Type | Notes |
|-------|------|-------|
| `tournament` | **FK(Tournament)** | `related_name='matches'` |
| `bracket` | **FK(Bracket)** | nullable, `related_name='matches'` |
| `round_number` | PositiveIntegerField | Min 1 |
| `match_number` | PositiveIntegerField | Min 1 |
| `participant1_id` | PositiveIntegerField | nullable |
| `participant1_name` | CharField(100) | denormalized |
| `participant2_id` | PositiveIntegerField | nullable |
| `participant2_name` | CharField(100) | denormalized |
| `state` | CharField(20) | Default `'scheduled'` |
| `participant1_score` | PositiveIntegerField | Default 0 |
| `participant2_score` | PositiveIntegerField | Default 0 |
| `winner_id` | PositiveIntegerField | nullable |
| `loser_id` | PositiveIntegerField | nullable |
| `lobby_info` | JSONField | Default `{}` |
| `stream_url` | URLField | — |
| `scheduled_time` | DateTimeField | nullable |
| `check_in_deadline` | DateTimeField | nullable |
| `participant1_checked_in` | BooleanField | Default False |
| `participant2_checked_in` | BooleanField | Default False |
| `started_at` | DateTimeField | nullable |
| `completed_at` | DateTimeField | nullable |
| `best_of` | PositiveSmallIntegerField | Default 1. Choices: `1, 3, 5` |
| `game_scores` | JSONField | `[{"game": N, "p1": X, "p2": Y, "winner_slot": 1|2}]` |

### `__str__`
Returns `"Round X, Match Y: Team1 vs Team2"`

### Seeding Pattern
```python
match = Match.objects.create(
    tournament=tournament,
    bracket=bracket,
    round_number=1,
    match_number=1,
    participant1_id=team1.id,
    participant1_name=team1.name,
    participant2_id=team2.id,
    participant2_name=team2.name,
    state=Match.SCHEDULED,
    scheduled_time=timezone.now() + timedelta(hours=2),
    best_of=3,
)
```

---

## 19. tournaments.Group & GroupStanding

**Path:** `apps/tournaments/models/group.py`  
**DB Table:** `tournament_groups` / `tournament_group_standings`

### Group Fields
| Field | Type | Notes |
|-------|------|-------|
| `tournament` | **FK(Tournament)** | `related_name='groups'` |
| `name` | CharField(100) | e.g., `'Group A'` |
| `display_order` | PositiveIntegerField | Default 0 |
| `max_participants` | PositiveIntegerField | Min 2 |
| `advancement_count` | PositiveIntegerField | Default 2 |
| `config` | JSONField | `{points_system, tiebreaker_rules, match_format}` |
| `is_finalized` | BooleanField | Default False |
| `draw_seed` | CharField(64) | — |

### GroupStanding Key Fields
| Field | Type | Notes |
|-------|------|-------|
| `group` | **FK(Group)** | `related_name='standings'` |
| `user` | FK(User) | nullable (XOR with team_id) |
| `team_id` | IntegerField | nullable |
| `rank` | PositiveIntegerField | Default 0 |
| `matches_played` | PositiveIntegerField | Default 0 |
| `matches_won` | PositiveIntegerField | Default 0 |
| `points` | ... | Universal standings |

---

## 20. tournaments.TournamentAnnouncement

**Path:** `apps/tournaments/models/announcement.py`  
**DB Table:** `tournament_announcements`

### Fields
| Field | Type | Notes |
|-------|------|-------|
| `tournament` | **FK(Tournament)** | `related_name='announcements'` |
| `title` | CharField(200) | Required |
| `message` | TextField | Required |
| `created_by` | FK(User) | nullable, SET_NULL |
| `is_pinned` | BooleanField | Default False |
| `is_important` | BooleanField | Default False |
| `created_at` | DateTimeField | auto |
| `updated_at` | DateTimeField | auto |

---

## 21. tournaments.TournamentStaff (Legacy) & StaffRole

**Path:** `apps/tournaments/models/staff.py` (LEGACY — use staffing.py instead)

### TournamentStaffRole Fields (Legacy)
| Field | Type |
|-------|------|
| `name` | CharField(50) unique |
| `slug` | SlugField(60) unique |
| `description` | TextField |
| `can_review_participants` | BooleanField |
| `can_verify_payments` | BooleanField |
| `can_manage_brackets` | BooleanField |
| `can_manage_matches` | BooleanField |
| `can_enter_scores` | BooleanField |
| `can_handle_disputes` | BooleanField |
| `can_send_notifications` | BooleanField |
| `can_modify_tournament` | BooleanField |
| `can_view_pii` | BooleanField |
| `is_system_role` | BooleanField |

### TournamentStaff Fields (Legacy)
- `tournament` — FK(Tournament)
- `user` — FK(User)
- `role` — FK(TournamentStaffRole)

---

## 22. tournaments.TournamentStaffAssignment (Phase 7)

**Path:** `apps/tournaments/models/staffing.py`  
**DB Table:** `tournament_staff_assignments`

### StaffRole Fields
| Field | Type | Notes |
|-------|------|-------|
| `name` | CharField(100) | Unique |
| `code` | CharField(50) | Unique, e.g., `'referee'`, `'admin'` |
| `description` | TextField | — |
| `capabilities` | JSONField | `{'can_schedule': true, ...}` |
| `is_referee_role` | BooleanField | Default False |

### TournamentStaffAssignment Fields
| Field | Type | Notes |
|-------|------|-------|
| `tournament` | FK(Tournament) | `related_name='epic73_staff_assignments'` |
| `user` | FK(User) | — |
| `role` | FK(StaffRole) | — |
| `is_active` | BooleanField | Default True |
| `assigned_by` | FK(User) | nullable |
| `notes` | TextField | — |

**Unique Together:** `(tournament, user, role)`

---

## 23. tournaments.Certificate

**Path:** `apps/tournaments/models/certificate.py`  
**DB Table:** `tournament_engine_certificate_certificate`

### CERTIFICATE_TYPE_CHOICES
`winner, runner_up, third_place, participant`

### Key Fields
| Field | Type | Notes |
|-------|------|-------|
| `tournament` | **FK(Tournament)** | `related_name='certificates'` |
| `participant` | **FK(Registration)** | `related_name='certificates'` |
| `certificate_type` | CharField(20) | — |
| `placement` | CharField(20) | e.g., `'1st'` |
| `file_pdf` | FileField | nullable |
| `file_image` | ImageField | nullable |
| `verification_code` | UUIDField | auto, unique |
| `certificate_hash` | CharField(64) | SHA-256 |
| `download_count` | PositiveIntegerField | Default 0 |
| `revoked_at` | DateTimeField | nullable |

---

## 24. tournaments.PrizeTransaction

**Path:** `apps/tournaments/models/prize.py`  
**DB Table:** `tournament_engine_prize_prizetransaction`

### Fields
| Field | Type | Notes |
|-------|------|-------|
| `tournament` | FK(Tournament) | — |
| `participant` | FK(Registration) | — |
| `placement` | CharField(20) | `1st, 2nd, 3rd, participation` |
| `amount` | DecimalField(10,2) | >= 0 |
| `coin_transaction_id` | IntegerField | nullable, ref to economy |
| `processed_by` | FK(User) | nullable |
| `status` | CharField(20) | `pending, completed, failed, refunded` |

---

## 25. economy.CoinPolicy

**Path:** `apps/economy/models.py` (~line 409)  
**DB Table:** default

### Fields
| Field | Type | Notes |
|-------|------|-------|
| `tournament_id` | IntegerField | Unique, nullable |
| `enabled` | BooleanField | Default True |
| `participation` | PositiveIntegerField | Default 5 |
| `top4` | PositiveIntegerField | Default 25 |
| `runner_up` | PositiveIntegerField | Default 50 |
| `winner` | PositiveIntegerField | Default 100 |

### Seeding Pattern
```python
from apps.economy.models import CoinPolicy
CoinPolicy.objects.get_or_create(
    tournament_id=tournament.id,
    defaults={
        'enabled': True,
        'participation': 5,
        'top4': 25,
        'runner_up': 50,
        'winner': 100,
    }
)
```

---

## 26. Existing Seed Scripts

### Management Commands (Reference)

| Command | What it does |
|---------|-------------|
| `seed_demo_tournaments` | Creates 24 demo teams + 4 tournaments (GROUP_PLAYOFF, COMPLETED, LIVE, REG_OPEN). **Best reference for seeding pattern.** |
| `seed_uradhura_ucl` | 32-player group stage tournament with full registration/payment flow. Uses `RegistrationService`. |
| `seed_demo_environment` | Form builder demo with registrations, ratings, webhooks. |
| `seed_registration_data` | Seeds FormResponse data for form builder testing. |
| `init_default_games` | **Creates all 9 games** with related configs (roster, tournament, identities, roles). Idempotent. |
| `seed_org` | Seeds organizations (in organizations app). |
| `seed_game_passport_schemas` | Seeds game passport JSON schemas. |

### Import Patterns from Existing Scripts
```python
# Tournament + related models
from apps.tournaments.models import Tournament, Registration, Match, Group, GroupStanding, Game, Bracket, BracketNode
from apps.tournaments.models.payment_config import TournamentPaymentMethod
from apps.tournaments.models.registration import Payment

# Teams (imported from organizations)
from apps.organizations.models import Team
# OR from apps.teams.models import Team

# Users
from apps.accounts.models import User
# OR from django.contrib.auth import get_user_model; User = get_user_model()

# Economy
from apps.economy.models import CoinPolicy

# Game configs
from apps.games.models import Game, GameRosterConfig, GameTournamentConfig, GamePlayerIdentityConfig, GameRole
```

---

## 27. Valorant-Specific Config Values

### Game
- `slug`: `'valorant'`
- `name`: `'VALORANT'`
- `display_name`: `'VALORANT'`
- `short_code`: `'VAL'`
- `category`: `'FPS'`
- `game_type`: `'TEAM_VS_TEAM'`
- `platforms`: `['PC']`
- `primary_color`: `'#ff4655'`
- `secondary_color`: `'#0f1923'`

### Roster Config
- **5v5** — `min_team_size=5, max_team_size=5`
- `min_substitutes=0, max_substitutes=2`
- `min_roster_size=5, max_roster_size=7`

### Tournament Config
- `default_match_format`: `'BO3'`
- `default_scoring_type`: `'ROUNDS'`
- `available_match_formats`: `['BO1', 'BO3', 'BO5']`
- `allow_draws`: `False`
- `overtime_enabled`: `True`

### Player Identity
- Field: `riot_id`
- Label: `'Riot ID'`
- Placeholder: `'PlayerName#TAG'`
- Regex: `^.+#.+$`

### Roles
| Name | Code | Icon | Color |
|------|------|------|-------|
| Duelist | DUE | 🎯 | #ff4655 |
| Initiator | INI | ⚡ | #00bfa5 |
| Controller | CTRL | 🌫️ | #7c3aed |
| Sentinel | SEN | 🛡️ | #2196f3 |

---

## Entity Relationship Summary (Seeding Order)

```
1. User (accounts.User)
2. UserProfile (auto or manual, OneToOne with User)
3. Game + GameRosterConfig + GameTournamentConfig + GamePlayerIdentityConfig + GameRole
4. GameProfile (user + game → Riot ID)
5. Organization (optional, if teams belong to an org)
6. Team (game=slug, not FK)
7. TeamMembership (team + profile + role)
8. Tournament (game FK, organizer FK)
9. TournamentPaymentMethod (tournament FK)
10. CoinPolicy (tournament_id IntegerField)
11. Registration (tournament + team_id or user)
12. Payment (registration OneToOne)
13. Bracket (tournament OneToOne)
14. BracketNode (bracket FK, linked list)
15. Match (tournament FK, bracket FK)
16. Group + GroupStanding (for group_playoff)
17. TournamentAnnouncement (tournament FK)
18. StaffRole + TournamentStaffAssignment (tournament + user + role)
19. Certificate (tournament + registration, post-completion)
20. PrizeTransaction (tournament + registration, post-completion)
```
