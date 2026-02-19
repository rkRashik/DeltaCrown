# DeltaCrown Seeding Plan — Updated for Current Architecture

**Last Updated:** February 18, 2026
**Objective:** Seed production-quality demo data for the Bangladesh/South Asia esports region.
**Architecture:** Django 5.2, PostgreSQL, `organizations.Team` (vNext), `user_profile.GameProfile` (Game Passport)

---

## Architecture Notes (What Changed from Original Plan)

| Original Concept | Current Model | Notes |
|---|---|---|
| `riot_id` / `pubg_id` on User | `GameProfile` (Game Passport) model | One `GameProfile` per user per game — `apps/user_profile/models_main.py` |
| `teams.Team` (legacy) | `organizations.Team` (vNext) | New model with `game_id` IntegerField. Legacy still exists for GroupStanding FK compat. |
| Team `captain` field | `TeamMembership.is_tournament_captain` | Captaincy is per-membership, not per-team |
| Team `role` on membership | `TeamMembership.role` choices: `OWNER, MANAGER, COACH, PLAYER, SUBSTITUTE, ANALYST, SCOUT` | |
| `roster_slot` on membership | `STARTER, SUBSTITUTE, COACH, ANALYST` | Separate from role |
| Game model in tournaments | `games.Game` with `GameRosterConfig`, `GameTournamentConfig` | Full game config hierarchy |
| Direct FK to Team | `Registration.team_id` (IntegerField) | Cross-app decoupled |
| Organization | `organizations.Organization` | Teams can belong to an org or be independent |
| `GroupStanding.team_id` | FK to `teams_team` (legacy table) | Must use `LegacyTeam` + `legacy_write_bypass` for group standings |

---

## Part 1: Users & Teams

### 1. Platform Rules

- A user can have **one GameProfile per game** (enforced by `unique_together = ['user', 'game']`)
- A user can be in **one team per game** (enforced by `one_active_independent_team_per_game_per_user` constraint)
- A team is tied to a **single game** via `game_id`
- One `is_tournament_captain` per team (enforced by DB constraint)
- Membership roles: `OWNER` (creator), `PLAYER`, `SUBSTITUTE`, `COACH`, `MANAGER`, `ANALYST`
- Roster slots: `STARTER`, `SUBSTITUTE`, `COACH`, `ANALYST`

### 2. User Profiles (100 Users)

**Region:** Bangladesh (Gen-Z Gamers, Age 16-25)
**Password for all seeded users:** `DeltaCrown2025!`

#### Type A: The Grinders (40 Users — user_001 to user_040)

Competitive players. English/Anime display names. Verified.

| # | Username | Display Name | Bio | City | Games |
|---|---|---|---|---|---|
| 1 | `dc_shadow_strike` | Shadow.Strike | Radiant peak. DM for scrims. | Dhaka | Valorant, CS2 |
| 2 | `dc_kryptek` | Kryptek_BD | IGL for Team Eclipse. | Dhaka | Valorant |
| 3 | `dc_vortex` | V0rtex | Duelist main. Grinding for national. | Dhaka | Valorant |
| 4 | `dc_aimgod_rafi` | AimGod_Rafi | Global Elite since 2019. | Dhaka | CS2 |
| 5 | `dc_zeus` | Z3US | Support god. | Dhaka | Valorant, LoL |
| 6 | `dc_hypernova` | Hyper.Nova | Entry fragger. | Chittagong | Valorant |
| 7 | `dc_glitch` | Glitch.FPS | Stream at twitch.tv/glitch | Dhaka | CS2 |
| 8 | `dc_spectre` | Spectre_BD | Sentinel main. | Dhaka | Valorant |
| 9 | `dc_phoenix_rise` | PhoenixRise | Flash and entry. | Sylhet | Valorant |
| 10 | `dc_apex_hunter` | Apex.Hunter | Diamond IV. | Dhaka | Apex Legends |
| 11 | `dc_frag_master` | FragMaster | FPS veteran. 10K hours. | Dhaka | CS2, Valorant |
| 12 | `dc_blade_runner` | BladeRunner | Flex player. | Rajshahi | Valorant |
| 13 | `dc_nova_blast` | NovaBlast | High KD ratio. | Dhaka | Apex Legends |
| 14 | `dc_cyber_wolf` | CyberWolf | IGL. Clean comms. | Dhaka | CS2 |
| 15 | `dc_rapid_fire` | RapidFire | AWP specialist. | Chittagong | CS2 |
| 16 | `dc_storm_break` | StormBreak | Controller main. | Dhaka | Valorant |
| 17 | `dc_neon_rush` | NeonRush | Aggressive entry. | Dhaka | Valorant |
| 18 | `dc_dark_matter` | DarkMatter | Rifler. B-site anchor. | Dhaka | CS2 |
| 19 | `dc_iron_sight` | IronSight | Sniper specialist. | Sylhet | CS2 |
| 20 | `dc_quantum` | Quantum.bd | Flex. | Dhaka | Valorant, Apex Legends |
| 21 | `dc_fury` | Fury_BD | Berserker playstyle. | Dhaka | LoL |
| 22 | `dc_mystic_soul` | MysticSoul | Support main. | Khulna | LoL |
| 23 | `dc_thunder` | Thunder.GG | ADC main. | Dhaka | LoL |
| 24 | `dc_echo_wave` | EchoWave | Mid laner. | Dhaka | LoL |
| 25 | `dc_celestial` | Celestial | Jungle main. | Dhaka | LoL, Dota 2 |
| 26 | `dc_venom` | Venom_BD | Offlaner. | Chittagong | Dota 2 |
| 27 | `dc_phantom` | Phantom_X | Pos 1 carry. | Dhaka | Dota 2 |
| 28 | `dc_reaper` | Reaper.BD | Pos 5 support. | Dhaka | Dota 2 |
| 29 | `dc_omega` | Omega.GG | Mid player. | Dhaka | Dota 2 |
| 30 | `dc_nitro` | Nitro.Speed | Grand Champ. | Dhaka | Rocket League |
| 31 | `dc_apex_pred` | ApexPredator | Pred rank. | Dhaka | Apex Legends |
| 32 | `dc_sniper_king` | SniperKing | Marksman. | Comilla | Apex Legends |
| 33 | `dc_turbo` | Turbo.RL | Aerial specialist. | Dhaka | Rocket League |
| 34 | `dc_stellar` | Stellar_BD | Consistent performer. | Dhaka | Rocket League |
| 35 | `dc_fc_master` | FC_Master | Division 1. | Dhaka | FC 25 |
| 36 | `dc_goal_king` | GoalKing | 90% win rate. | Dhaka | FC 25 |
| 37 | `dc_striker` | Striker.BD | Attacking playstyle. | Chittagong | FC 25 |
| 38 | `dc_dribble` | Dribble_Pro | Skill moves expert. | Dhaka | FC 25 |
| 39 | `dc_ow_mercy` | MercyMain | Support player. | Dhaka | Overwatch 2 |
| 40 | `dc_ow_genji` | Genji.Blade | DPS flex. | Dhaka | Overwatch 2 |

#### Type B: The Casuals (40 Users — user_041 to user_080)

Fun, casual-competitive. "Banglish" names. These are the heart of the BD gaming scene.

| # | Username | Display Name | Bio | City | Games |
|---|---|---|---|---|---|
| 41 | `dc_mama_lag` | Mama_Lag_Kore | Lag er moddhe clutch. | Chittagong | Valorant |
| 42 | `dc_bhai_op` | Bhai_OP | Study kom game beshi. | Dhaka | Valorant |
| 43 | `dc_kushtia_sniper` | Kushtia_Sniper | Playing from village. Ping 200. | Kushtia | CS2 |
| 44 | `dc_net_nai` | Net_Nai | Broadband ar pera khabo na. | Rajshahi | CS2 |
| 45 | `dc_bot_slayer` | Bot_Slayer | Actually Iron 1. | Dhaka | Valorant |
| 46 | `dc_dhaka_king` | Dhaka_King | Dhanmondi er pride. | Dhaka | Valorant |
| 47 | `dc_noob_hunter` | Noob_Hunter | Ping high but spirits high. | Sylhet | CS2 |
| 48 | `dc_lag_lord` | Lag_Lord | WiFi r shathe juddhho. | Barisal | Valorant |
| 49 | `dc_bhai_clutch` | Bhai_Clutch | 1v5 everyday. | Dhaka | CS2 |
| 50 | `dc_exam_kaal` | Exam_Kaal | Poriksha ase but one more game. | Dhaka | Valorant |
| 51 | `dc_taka_nai` | Taka_Nai | Free tournament only. | Chittagong | Valorant |
| 52 | `dc_net_slow` | Net_SlowBD | Buffering champion. | Mymensingh | CS2 |
| 53 | `dc_chai_break` | Chai_Break | AFK for cha. | Dhaka | Valorant |
| 54 | `dc_study_later` | StudyLater | One more round then study. | Dhaka | LoL |
| 55 | `dc_bronze_pride` | Bronze_Pride | Bronze is a lifestyle. | Dhaka | LoL |
| 56 | `dc_carry_pls` | Carry_Pls | Need carry from Iron. | Chittagong | Valorant |
| 57 | `dc_afk_alert` | AFK_Alert | Mom called. BRB. | Dhaka | CS2 |
| 58 | `dc_toxic_heal` | Toxic_Healer | Support but toxic. | Dhaka | LoL |
| 59 | `dc_dhaka_bot` | Dhaka_Bot | Playing for fun. No tilt. | Dhaka | Valorant |
| 60 | `dc_sylhet_snipe` | Sylhet_Snipe | Sniper from the hills. | Sylhet | CS2 |
| 61 | `dc_rocket_noob` | Rocket_Noob | What a save! | Dhaka | Rocket League |
| 62 | `dc_goal_miss` | GoalMiss | Always hit the post. | Dhaka | FC 25 |
| 63 | `dc_offside_king` | Offside_King | Timing is hard. | Dhaka | FC 25 |
| 64 | `dc_tank_main` | TankMain | Reinhardt one trick. | Dhaka | Overwatch 2 |
| 65 | `dc_heal_pls` | Heal_Pls | DPS queued as support. | Chittagong | Overwatch 2 |
| 66 | `dc_mid_or_feed` | MidOrFeed | Classic. | Dhaka | Dota 2 |
| 67 | `dc_pudge_hook` | PudgeHook | Hook accuracy 30%. | Dhaka | Dota 2 |
| 68 | `dc_int_master` | IntMaster | Die 15 times carry 1v9. | Dhaka | LoL |
| 69 | `dc_apex_noob` | Apex_Noob | Drop Skull Town. Die. Repeat. | Dhaka | Apex Legends |
| 70 | `dc_pathfinder` | PathFinder_BD | Grapple god. | Chittagong | Apex Legends |
| 71 | `dc_val_casual` | Val_Casual | Unrated only. | Dhaka | Valorant |
| 72 | `dc_cs_silver` | CS_Silver | Silver Elite Master. Peaked. | Dhaka | CS2 |
| 73 | `dc_rl_bronze` | RL_Bronze | Car go brr. | Dhaka | Rocket League |
| 74 | `dc_fc_draw` | FC_Draw | Every game 1-1. | Rajshahi | FC 25 |
| 75 | `dc_dota_sup` | Dota_Sup | Ward duty. | Dhaka | Dota 2 |
| 76 | `dc_apex_loot` | Apex_Loot | Loot goblin. Never fights. | Dhaka | Apex Legends |
| 77 | `dc_val_iron` | Val_Iron | Iron 1 and proud. | Dhaka | Valorant |
| 78 | `dc_cs_rush` | CS_RushB | Rush B no stop. | Dhaka | CS2 |
| 79 | `dc_ow_potato` | OW_Potato | Aim like a potato. | Dhaka | Overwatch 2 |
| 80 | `dc_rl_flip` | RL_Flip | Front flip goal. | Dhaka | Rocket League |

#### Type C: The Pros & Influencers (20 Users — user_081 to user_100)

Professional/content creator profiles. Clean branding.

| # | Username | Display Name | Bio | City | Games |
|---|---|---|---|---|---|
| 81 | `dc_tanvir` | Tanvir.Gaming | Pro player for Crimson Syndicate | Dhaka | Valorant |
| 82 | `dc_sakib` | Sakib_Plays | IGL. Team captain. | Dhaka | Valorant |
| 83 | `dc_rifat` | Rifat.Official | CS2 professional. 8K hours. | Dhaka | CS2 |
| 84 | `dc_nabil` | Nabil_Esports | Org owner. Titan Esports CEO. | Dhaka | Valorant, CS2 |
| 85 | `dc_arif` | Arif.Pro | Competitive Dota 2. | Dhaka | Dota 2 |
| 86 | `dc_farhan` | Farhan.GG | LoL streamer. 50K followers. | Dhaka | LoL |
| 87 | `dc_siam` | Siam.Live | Content creator. | Chittagong | Valorant |
| 88 | `dc_rashed` | Rashed.TTV | Twitch partner. | Dhaka | CS2 |
| 89 | `dc_karim` | Karim.Coach | Ex-pro. Now coaching. | Dhaka | Valorant, CS2 |
| 90 | `dc_jamal` | Jamal.Caster | Tournament caster & analyst. | Dhaka | — |
| 91 | `dc_hasan` | Hasan.FC | FC25 content creator. | Dhaka | FC 25 |
| 92 | `dc_imran` | Imran.RL | Rocket League streamer. | Dhaka | Rocket League |
| 93 | `dc_zahid` | Zahid.OW | Top 500 Overwatch. | Dhaka | Overwatch 2 |
| 94 | `dc_mamun` | Mamun.Apex | Apex predator. Content. | Dhaka | Apex Legends |
| 95 | `dc_robin` | Robin.Dota | Dota 2 Immortal. | Chittagong | Dota 2 |
| 96 | `dc_sumon` | Sumon.Pro | Multi-game competitor. | Dhaka | Valorant, CS2, LoL |
| 97 | `dc_jubayer` | Jubayer.GG | Rising talent. | Dhaka | Valorant |
| 98 | `dc_mahfuz` | Mahfuz.Coach | Strategic analyst. | Dhaka | CS2, Dota 2 |
| 99 | `dc_shafiq` | Shafiq.Org | Org operations. | Dhaka | CS2 |
| 100 | `dc_omar` | Omar.Cast | Commentator. Tournament host. | Dhaka | — |

### 3. Game Passport Setup (GameProfile per User)

Each user gets one `GameProfile` entry per game they play. This is the "Game Passport" — their in-game identity on DeltaCrown.

**Model:** `apps/user_profile/models_main.py → GameProfile`
**Fields:** `user` FK, `game` FK, `ign` (in-game name), `discriminator` (tag/code), `platform`, `rank_name`, `rank_points`, `peak_rank`, `matches_played`, `win_rate`, `kd_ratio`, `main_role`, `verification_status`

| Game | IGN Format | Discriminator | Platform | Rank Example |
|---|---|---|---|---|
| Valorant | Riot Name | Tagline (`#BD01`) | `pc` | Radiant / Diamond / Iron |
| CS2 | Steam Name | Steam Friend Code | `pc` | Global Elite / Silver |
| League of Legends | Summoner Name | Riot Tag | `pc` | Challenger / Gold |
| Dota 2 | Steam Name | Friend ID | `pc` | Immortal / Archon |
| Apex Legends | EA ID | — | `pc` | Predator / Diamond |
| Overwatch 2 | BattleTag | Discriminator | `pc` | Top 500 / Gold |
| Rocket League | Epic/Steam Name | — | `pc` | Grand Champion / Silver |
| FC 25 | EA Sports ID | — | `pc` | Division 1 / Division 5 |
| Fortnite | Epic Name | — | `pc` | Champion League / Open |

### 4. Organizations (3 Esports Orgs)

**Model:** `apps/organizations/models.py → Organization`

| Name | Slug | CEO User | Teams Under Org | Description |
|---|---|---|---|---|
| Titan Esports | `titan-esports` | `dc_nabil` | Dhaka Leviathans (Val), Titan Valorant (Val), Fury Esports (LoL) | Bangladesh's premier esports organization. Est. 2023. |
| Eclipse Gaming | `eclipse-gaming` | `dc_shafiq` | Dust2 Demons (CS2), Ancient Defense (Dota 2) | Rising competitive org. Focus on tactical FPS and MOBA. |
| Crown Dynasty | `crown-dynasty` | `dc_sumon` | AimBot Activated (Val) | Content + competition. Streaming-focused brand. |

### 5. Teams (40 Teams Total)

**Model:** `apps/organizations/models.py → Team` (vNext)
**Membership Model:** `apps/organizations/models.py → TeamMembership`

#### Valorant Teams (12)

| # | Team Name | Tag | Tier | Org | Roster |
|---|---|---|---|---|---|
| 1 | Crimson Syndicate | CRS | T1 | — | `dc_tanvir` (OWNER/Capt), `dc_vortex` (PLAYER/STARTER), `dc_spectre` (PLAYER/STARTER), `dc_blade_runner` (PLAYER/STARTER), `dc_frag_master` (PLAYER/STARTER), `dc_shadow_strike` (SUBSTITUTE), `dc_quantum` (SUBSTITUTE), `dc_karim` (COACH) |
| 2 | Velocity X BD | VXB | T1 | — | `dc_sakib` (OWNER/Capt), `dc_hypernova` (PLAYER/STARTER), `dc_kryptek` (PLAYER/STARTER), `dc_zeus` (PLAYER/STARTER), `dc_phoenix_rise` (PLAYER/STARTER), `dc_neon_rush` (SUBSTITUTE), `dc_storm_break` (SUBSTITUTE), `dc_karim` role conflict—skip |
| 3 | Dhaka Leviathans | DLV | T1 | Titan | `dc_nabil` (OWNER), `dc_storm_break` (PLAYER/Capt/STARTER), `dc_neon_rush` (PLAYER/STARTER), `dc_mama_lag` (PLAYER/STARTER), `dc_bhai_op` (PLAYER/STARTER), `dc_dhaka_king` (SUBSTITUTE) |
| 4 | Titan Valorant | TVL | T1 | Titan | `dc_jubayer` (OWNER/Capt), `dc_siam` (PLAYER/STARTER), `dc_val_casual` (PLAYER/STARTER), `dc_lag_lord` (PLAYER/STARTER), `dc_chai_break` (PLAYER/STARTER), `dc_taka_nai` (SUBSTITUTE) |
| 5 | Headhunterz | HHZ | T2 | — | `dc_exam_kaal` (OWNER/Capt), `dc_bot_slayer` (PLAYER/STARTER), `dc_dhaka_bot` (PLAYER/STARTER), `dc_carry_pls` (PLAYER/STARTER), `dc_val_iron` (PLAYER/STARTER) |
| 6 | AimBot Activated | ABA | T2 | Crown | `dc_sumon` (OWNER/Capt), `dc_noob_hunter` (PLAYER/STARTER—plays CS2 too but Val team here... needs adjustment) |

> **Note:** Each user can only be on ONE Valorant team. The seed script must enforce this constraint. Users who play multiple games (e.g., `dc_shadow_strike` plays Valorant + CS2) can be on one Val team and one CS2 team. But never two Val teams.

**Simplified Valorant Rosters (constraint-safe):**

| # | Team | Tag | Owner (Capt) | Starters | Subs |
|---|---|---|---|---|---|
| 1 | Crimson Syndicate | CRS | `dc_tanvir` | `dc_vortex`, `dc_spectre`, `dc_blade_runner`, `dc_frag_master` | `dc_shadow_strike`, `dc_quantum` |
| 2 | Velocity X BD | VXB | `dc_sakib` | `dc_hypernova`, `dc_kryptek`, `dc_zeus`, `dc_phoenix_rise` | — |
| 3 | Dhaka Leviathans | DLV | `dc_nabil` | `dc_storm_break`, `dc_neon_rush`, `dc_bhai_op`, `dc_dhaka_king` | `dc_mama_lag` |
| 4 | Titan Valorant | TVL | `dc_jubayer` | `dc_siam`, `dc_val_casual`, `dc_lag_lord`, `dc_chai_break` | `dc_taka_nai` |
| 5 | Headhunterz | HHZ | `dc_exam_kaal` | `dc_bot_slayer`, `dc_dhaka_bot`, `dc_carry_pls`, `dc_val_iron` | — |
| 6 | AimBot Activated | ABA | `dc_sumon` | `dc_net_nai`... |

> **Seed script will auto-assign remaining casual users** to fill out Val teams 6-12 from the pool of Valorant-tagged casuals not yet assigned.

#### CS2 Teams (8)

| # | Team | Tag | Owner (Capt) | Starters | Subs |
|---|---|---|---|---|---|
| 1 | Old School BD | OSB | `dc_rifat` | `dc_aimgod_rafi`, `dc_cyber_wolf`, `dc_glitch`, `dc_rapid_fire` | `dc_shadow_strike` |
| 2 | Dust2 Demons | D2D | `dc_shafiq` | `dc_dark_matter`, `dc_iron_sight`, `dc_rashed`, `dc_mahfuz` | — |
| 3 | Mirage Kings | MRG | `dc_kushtia_sniper` | `dc_net_nai`, `dc_noob_hunter`, `dc_bhai_clutch`, `dc_afk_alert` | — |
| 4 | Global Elites | GEL | `dc_cs_silver` | `dc_net_slow`, `dc_sylhet_snipe`, `dc_cs_rush`, `dc_frag_master` (if not in dual constraint) | — |
| 5-8 | *(4 more community CS2 teams)* | | *(auto-fill from pool)* | | |

#### League of Legends Teams (6)

| # | Team | Tag | Owner (Capt) | Starters |
|---|---|---|---|---|
| 1 | Fury Esports | FRY | `dc_fury` | `dc_farhan`, `dc_thunder`, `dc_echo_wave`, `dc_celestial` |
| 2 | Mystic Legion | MYL | `dc_mystic_soul` | `dc_study_later`, `dc_bronze_pride`, `dc_toxic_heal`, `dc_int_master` |
| 3 | Echo Rift | ECR | `dc_zeus` | *(auto-fill from LoL pool)* |
| 4-6 | *(3 more LoL teams)* | | *(auto-fill)* | |

#### Dota 2 Teams (5)

| # | Team | Tag | Owner (Capt) | Starters |
|---|---|---|---|---|
| 1 | Ancient Defense | ACD | `dc_arif` | `dc_phantom`, `dc_reaper`, `dc_omega`, `dc_robin` |
| 2 | Roshan Raiders | RSR | `dc_venom` | `dc_celestial`, `dc_mid_or_feed`, `dc_pudge_hook`, `dc_dota_sup` |
| 3-5 | *(3 more Dota teams)* | | *(auto-fill)* | |

#### Apex Legends Teams (3 — trios)

| # | Team | Tag | Owner (Capt) | Members |
|---|---|---|---|---|
| 1 | Apex Predators BD | APB | `dc_mamun` | `dc_apex_pred`, `dc_apex_hunter` |
| 2 | Zone Survivors | ZNS | `dc_sniper_king` | `dc_pathfinder`, `dc_nova_blast` |
| 3 | Loot Goblins | LTG | `dc_apex_loot` | `dc_apex_noob` |

#### Rocket League Teams (3 — 3v3)

| # | Team | Tag | Owner (Capt) | Members |
|---|---|---|---|---|
| 1 | Nitro Speed | NTS | `dc_nitro` | `dc_turbo`, `dc_stellar` |
| 2 | Flip Reset FC | FRF | `dc_imran` | `dc_rl_bronze`, `dc_rl_flip` |
| 3 | Car Go Brr | CGB | `dc_rocket_noob` | *(1-2 auto-fill)* |

#### Overwatch 2 Teams (3 — 5v5)

| # | Team | Tag | Owner (Capt) | Members |
|---|---|---|---|---|
| 1 | Payload Pushers | PLP | `dc_zahid` | `dc_ow_mercy`, `dc_ow_genji`, `dc_tank_main`, `dc_heal_pls` |
| 2-3 | *(2 more OW2 teams)* | | *(auto-fill)* | |

#### FC 25 — Solo Game

FC 25 tournaments use `participation_type='solo'`. No teams needed.
Solo players: `dc_fc_master`, `dc_goal_king`, `dc_striker`, `dc_dribble`, `dc_hasan`, `dc_goal_miss`, `dc_offside_king`, `dc_fc_draw`

---

## Part 2: Tournament Scenarios (15 Tournaments)

### Completed Tournaments (5)

#### T1: DeltaCrown Valorant Invitationals — Season 1

| Field | Value |
|---|---|
| **Name** | `DeltaCrown Valorant Invitationals: Season 1` |
| **Slug** | `valorant-invitational-s1` |
| **Game** | Valorant |
| **Format** | `group_playoff` (Groups → Double Elimination Playoffs) |
| **Status** | `completed` |
| **Participation** | `team` |
| **Platform** | `pc` |
| **Mode** | `online` |
| **Teams** | 12 Valorant teams |
| **Max Participants** | 12 |
| **Prize Pool** | 50000 (BDT) |
| **Entry Fee** | 0 (Invitational) |
| **Dates** | Sept 12 – Oct 5, 2025 (past) |
| **Stage 1** | 3 Groups of 4 — Round Robin within groups. Top 2 advance. |
| **Stage 2** | 6-team Single Elimination Playoff |
| **Winner** | Crimson Syndicate |
| **Runner-up** | Velocity X BD |
| **Grand Final** | Crimson Syndicate 3-1 Velocity X BD |
| **Description** | The flagship Valorant tournament of Bangladesh. Top 12 teams invited to battle for the crown. |

#### T2: CS2 Masters — BD Edition

| Field | Value |
|---|---|
| **Name** | `CS2 Masters: Bangladesh Edition` |
| **Slug** | `cs2-masters-bd` |
| **Game** | CS2 |
| **Format** | `single_elimination` |
| **Status** | `completed` |
| **Participation** | `team` |
| **Platform** | `pc` |
| **Teams** | 8 CS2 teams |
| **Max Participants** | 8 |
| **Prize Pool** | 30000 (BDT) |
| **Entry Fee** | 200 |
| **Winner** | Old School BD |
| **Dates** | Oct 15 – Nov 2, 2025 |

#### T3: LoL Rift Clash — Season 1

| Field | Value |
|---|---|
| **Name** | `League of Legends Rift Clash: Season 1` |
| **Slug** | `lol-rift-clash-s1` |
| **Game** | League of Legends |
| **Format** | `single_elimination` |
| **Status** | `completed` |
| **Participation** | `team` |
| **Teams** | 6 LoL teams |
| **Max Participants** | 8 |
| **Prize Pool** | 20000 (BDT) |
| **Entry Fee** | 0 |
| **Winner** | Fury Esports |
| **Dates** | Nov 10 – Nov 24, 2025 |

#### T4: Rocket League Nitro Cup

| Field | Value |
|---|---|
| **Name** | `Rocket League Nitro Cup` |
| **Slug** | `rl-nitro-cup` |
| **Game** | Rocket League |
| **Format** | `round_robin` |
| **Status** | `completed` |
| **Participation** | `team` |
| **Teams** | 3 RL teams |
| **Max Participants** | 4 |
| **Prize Pool** | 10000 (BDT) |
| **Entry Fee** | 0 |
| **Winner** | Nitro Speed |
| **Dates** | Dec 1 – Dec 15, 2025 |

#### T5: FC 25 Weekend League #1 (Solo)

| Field | Value |
|---|---|
| **Name** | `FC 25 Weekend League #1` |
| **Slug** | `fc25-weekend-league-1` |
| **Game** | FC 25 |
| **Format** | `single_elimination` |
| **Participation** | `solo` |
| **Status** | `completed` |
| **Players** | 8 solo users |
| **Max Participants** | 8 |
| **Prize Pool** | 5000 (BDT) |
| **Entry Fee** | 0 |
| **Winner** | dc_fc_master |
| **Dates** | Jan 10 – Jan 12, 2026 |

### Live Tournaments (5) — In Progress

#### T6: Radiant Rising — Season 2 (Valorant)

| Field | Value |
|---|---|
| **Name** | `Radiant Rising: Season 2` |
| **Slug** | `radiant-rising-s2` |
| **Game** | Valorant |
| **Format** | `double_elimination` |
| **Status** | `live` |
| **Participation** | `team` |
| **Teams** | 8 Valorant teams |
| **Max Participants** | 8 |
| **Prize Pool** | 40000 (BDT) |
| **Entry Fee** | 500 |
| **Dates** | Feb 1 – ongoing |
| **Current State** | WB R1 completed (4 matches). WB R2 in progress: 1 match completed, 1 scheduled. LB R1: 2 matches scheduled. |
| **Test Case** | Double elim bracket advancement — WB losers move to LB. Verify bracket_structure JSON. |

#### T7: Ancient Defense Cup (Dota 2)

| Field | Value |
|---|---|
| **Name** | `Ancient Defense Cup` |
| **Slug** | `ancient-defense-cup` |
| **Game** | Dota 2 |
| **Format** | `double_elimination` |
| **Status** | `live` |
| **Participation** | `team` |
| **Teams** | 5 Dota 2 teams (padded with BYEs to 8) |
| **Max Participants** | 8 |
| **Prize Pool** | 25000 (BDT) |
| **Entry Fee** | 0 |
| **Dates** | Feb 5 – ongoing |
| **Current State** | WB R1 done (3 matches + 1 BYE). LB R1 in progress. |
| **Test Case** | BYE advancement. Teams that lost in WB correctly appear in LB. |

#### T8: Apex Legends Survival Series

| Field | Value |
|---|---|
| **Name** | `Apex Legends Survival Series` |
| **Slug** | `apex-survival-series` |
| **Game** | Apex Legends |
| **Format** | `round_robin` |
| **Status** | `live` |
| **Participation** | `team` |
| **Teams** | 3 Apex trios |
| **Max Participants** | 4 |
| **Prize Pool** | 15000 (BDT) |
| **Dates** | Feb 8 – ongoing |
| **Current State** | 2 of 3 round-robin matches played. 1 remaining. |

#### T9: Overwatch 2 Payload Push

| Field | Value |
|---|---|
| **Name** | `Overwatch 2 Payload Push` |
| **Slug** | `ow2-payload-push` |
| **Game** | Overwatch 2 |
| **Format** | `single_elimination` |
| **Status** | `live` |
| **Participation** | `team` |
| **Teams** | 3 OW2 teams (padded with BYE to 4) |
| **Max Participants** | 4 |
| **Prize Pool** | 12000 (BDT) |
| **Dates** | Feb 10 – ongoing |
| **Current State** | Semi-final done. Grand Final scheduled. |

#### T10: Nitro Speed Cup — Season 2 (Rocket League)

| Field | Value |
|---|---|
| **Name** | `Nitro Speed Cup: Season 2` |
| **Slug** | `nitro-speed-cup-s2` |
| **Game** | Rocket League |
| **Format** | `round_robin` |
| **Status** | `live` |
| **Participation** | `team` |
| **Teams** | 3 RL teams |
| **Max Participants** | 4 |
| **Prize Pool** | 8000 (BDT) |
| **Dates** | Feb 12 – ongoing |
| **Current State** | All 3 matches completed. Standings finalized. Waiting for organizer to close. |
| **Test Case** | Tournament with all matches done but still `live` — organizer must transition to `completed`. |

### Open Registration Tournaments (5) — Accepting Signups

#### T11: Community Scrims #44 — Friday Night (Valorant)

| Field | Value |
|---|---|
| **Name** | `Community Scrims #44 (Friday Night)` |
| **Slug** | `valorant-scrims-44` |
| **Game** | Valorant |
| **Format** | `single_elimination` |
| **Status** | `registration_open` |
| **Participation** | `team` |
| **Max Teams** | 16 |
| **Registered** | 8 of 16 (8 slots left) |
| **Entry Fee** | 0 (Free) |
| **Reg Deadline** | 3 days from now |
| **Test** | Register a new team. Try duplicate registration. See slot counter update. |

#### T12: CS2 Competitive League — Spring 2026

| Field | Value |
|---|---|
| **Name** | `CS2 Competitive League: Spring 2026` |
| **Slug** | `cs2-comp-league-spring` |
| **Game** | CS2 |
| **Format** | `group_playoff` |
| **Status** | `registration_open` |
| **Participation** | `team` |
| **Max Teams** | 8 |
| **Registered** | 6 of 8 (2 slots remaining — "Almost Full!") |
| **Entry Fee** | 500 (BDT) |
| **Reg Deadline** | 5 days from now |
| **Test** | Last 2 slots urgency UI. Payment pending flow. Reject registration. |

#### T13: FC 25 Solo Championship

| Field | Value |
|---|---|
| **Name** | `FC 25 Solo Championship` |
| **Slug** | `fc25-solo-championship` |
| **Game** | FC 25 |
| **Format** | `single_elimination` |
| **Participation** | `solo` |
| **Status** | `registration_open` |
| **Max Players** | 16 |
| **Registered** | 0 of 16 (empty — "Be the first to register!") |
| **Entry Fee** | 50 (BDT) |
| **Reg Deadline** | 7 days from now |
| **Test** | Solo registration flow (no team). Empty state UI. First registration. |

#### T14: LoL Rift Clash — Season 2

| Field | Value |
|---|---|
| **Name** | `LoL Rift Clash: Season 2` |
| **Slug** | `lol-rift-clash-s2` |
| **Game** | League of Legends |
| **Format** | `round_robin` |
| **Status** | `registration_open` |
| **Participation** | `team` |
| **Max Teams** | 6 |
| **Registered** | 3 confirmed, 2 pending payment |
| **Entry Fee** | 300 (BDT) |
| **Reg Deadline** | 10 days from now |
| **Test** | Payment verification flow. Pending→Confirmed. Admin approve/reject. Mixed status registrations. |

#### T15: Dota 2 Guardian Cup

| Field | Value |
|---|---|
| **Name** | `Dota 2 Guardian Cup` |
| **Slug** | `dota2-guardian-cup` |
| **Game** | Dota 2 |
| **Format** | `swiss` |
| **Status** | `registration_open` |
| **Participation** | `team` |
| **Max Teams** | 8 |
| **Registered** | 4 of 8 |
| **Entry Fee** | 0 (Free) |
| **Reg Deadline** | 14 days from now |
| **Test** | Swiss format registration. Half-full state. |

---

## Part 3: Seeding Execution Order

```
Step 1: Initialize games          → python manage.py init_default_games
Step 2: Create users + profiles   → 100 users with UserProfile (display_name, bio, country='BD')
Step 3: Create game passports     → GameProfile entries for each user's games
Step 4: Create organizations      → 3 orgs
Step 5: Create teams              → 40 teams (organizations.Team vNext) under orgs or independent
Step 6: Assign team memberships   → TeamMembership with correct roles + roster slots + captain flags
Step 7: Create legacy team stubs  → LegacyTeam entries for GroupStanding FK compatibility
Step 8: Completed tournaments     → T1-T5 with full match history, brackets, group standings
Step 9: Live tournaments          → T6-T10 with partial match data, active brackets
Step 10: Open tournaments         → T11-T15 with registrations in various states
```

### Key Implementation Notes

1. **UserActivity FK** — Django signal creates UserActivity on user creation. If it fails, wrap in try/except. Use `SET CONSTRAINTS ALL IMMEDIATE` if deferred.
2. **LegacyTeam** — Required only for `GroupStanding.team_id` FK. Use `legacy_write_bypass` context manager from `apps/teams/models/_legacy.py`.
3. **Registration.team_id** — Plain IntegerField. Set to `organizations.Team.id`, not legacy team ID.
4. **Match.participant_id** — PositiveIntegerField. For team tournaments, this is the `organizations.Team.id`. For solo, it's `User.id`.
5. **Bracket.bracket_structure** — JSON blob. For completed tournaments, must have all match results. For live, partial.
6. **Dates** — All completed tournament dates should be in the past. Live tournament dates span current date. Open registration dates should have `registration_end` in the future.

### Verification Checklist

After seeding, verify:

- [ ] 100 users exist with `is_verified=True`
- [ ] Each user has a `UserProfile` with `display_name`, `bio`, `country='BD'`
- [ ] Each user has `GameProfile` entries for their declared games
- [ ] 3 organizations with correct CEOs
- [ ] 40 teams with correct `game_id`, `organization` (or null), `status='active'`
- [ ] Each team has correct `TeamMembership` entries (roles, roster_slots)
- [ ] Each team has exactly 1 `is_tournament_captain=True` membership
- [ ] No user appears twice on the same game's teams
- [ ] T1-T5: `status='completed'`, all matches have results, dates in past
- [ ] T6-T10: `status='live'`, partial match data, brackets partially filled
- [ ] T11-T15: `status='registration_open'`, correct registration counts
- [ ] Admin panel shows all data correctly
- [ ] Tournament list page shows tournaments grouped by status

---

## Testing Accounts Quick Reference

| Role | Username | Password | Purpose |
|---|---|---|---|
| **Admin/Superuser** | `admin` | *(created via `createsuperuser`)* | Full admin access |
| **Organizer** | `dc_omar` | `DeltaCrown2025!` | Creates & manages tournaments |
| **Pro Player** | `dc_tanvir` | `DeltaCrown2025!` | Captain of Crimson Syndicate |
| **Casual Player** | `dc_mama_lag` | `DeltaCrown2025!` | Team owner, casual gamer |
| **Content Creator** | `dc_farhan` | `DeltaCrown2025!` | LoL streamer, team player |
| **Org CEO** | `dc_nabil` | `DeltaCrown2025!` | Titan Esports CEO |
| **Solo Player** | `dc_fc_master` | `DeltaCrown2025!` | FC 25 solo competitor |
| **Coach** | `dc_karim` | `DeltaCrown2025!` | Non-playing coach role |
| **New User** | *(register fresh)* | *(any)* | Test registration flow |
