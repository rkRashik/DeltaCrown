# Game Competitive Systems Research Report - 2025
## Comprehensive Analysis for Tournament Registration System

**Date:** December 27, 2025  
**Purpose:** Determine actual competitive requirements for game passport/tournament registration system

---

## 1. VALORANT

### Identity System
- **Primary ID:** Riot ID (Username#Tag format, e.g., "Player#NA1")
- **Account System:** Riot Games Account (unified across Riot titles)
- **Verification:** Riot ID is unique globally and displayed in-game

### Rank/Division System (2024-2025)
**Competitive Ranks** (in ascending order):
1. **Iron** (I, II, III)
2. **Bronze** (I, II, III)
3. **Silver** (I, II, III)
4. **Gold** (I, II, III)
5. **Platinum** (I, II, III)
6. **Diamond** (I, II, III)
7. **Ascendant** (I, II, III)
8. **Immortal** (I, II, III)
9. **Radiant** (Top 500 per region)

**Total:** 27 ranks with RR (Ranked Rating) points system

### Server/Region System
**Regional Servers** (affects matchmaking and rank):
- North America (NA)
- Europe (EU)
- Asia Pacific (APAC) - includes multiple sub-regions
- Latin America (LATAM)
- Brazil (BR)
- Korea (KR)

**Important:** Ranks are region-specific. Players have separate ranks per region.

### Platform
- **PC Only** (Windows)

### What Matters for Competitive Tournaments
**Required Information:**
1. **Riot ID** (Username#Tag)
2. **Region** (where they play competitive)
3. **Current Rank** (with tier, e.g., "Diamond II")
4. **Peak Rank** (for season qualification often)
5. **Act/Episode** (VALORANT uses Episodes and Acts for seasons)

**Verification Method:**
- Riot API available for rank verification
- In-game profile screenshots with Riot ID visible
- Tracker sites: tracker.gg/valorant

---

## 2. Counter-Strike 2 (CS2)

### Identity System
- **Primary ID:** Steam ID (64-bit SteamID64 or Steam Profile URL)
- **Account System:** Steam Account
- **Display Name:** Steam username (can be changed freely)

### Rank/Division System (2024-2025)
**CS2 Premier Mode** (Primary competitive system):
- **CS Rating System** (numerical rating, similar to Elo)
- **Rating Range:** 0-35,000+ (approximate)
- **Color-coded tiers** based on rating ranges (no fixed "ranks" like CS:GO)

**Legacy Competitive Mode** (still exists):
1. Silver (I-IV, Elite, Elite Master)
2. Gold Nova (I-IV, Master)
3. Master Guardian (I, II, Elite, Distinguished Master Guardian)
4. Legendary Eagle (Master)
5. Supreme Master First Class
6. Global Elite

**Note:** Premier mode with CS Rating is now the primary competitive system used for tournaments.

### Server/Region System
- **Global Matchmaking** - No hard region locks
- Players can select preferred server regions
- Ping-based matchmaking prioritizes nearby servers
- No separate ranks per region

**Server Regions:**
- North America (East, West, Central)
- Europe (West, East, North)
- Asia (Southeast Asia, East Asia)
- South America
- Australia
- Africa (limited)
- Middle East

### Platform
- **PC** (Windows, Linux, macOS via Steam)

### What Matters for Competitive Tournaments
**Required Information:**
1. **Steam ID64** or **Steam Profile URL**
2. **CS Rating** (Premier mode rating)
3. **Region/Server preference** (for ping considerations)
4. **Faceit Level** (many tournaments use third-party platforms)
5. **Hours played** (anti-smurf measure)

**Verification Method:**
- Steam API for account verification
- Third-party platforms: Faceit, ESEA (common for competitive)
- Demo files/match history

---

## 3. Dota 2

### Identity System
- **Primary ID:** Steam ID (64-bit SteamID64)
- **Account System:** Steam Account
- **In-game ID:** Friend ID (visible in Dota 2 client)

### Rank/Division System (2024-2025)
**Medal System with MMR (Matchmaking Rating):**

**Medals** (each has 5 stars):
1. **Herald** (~0-770 MMR)
2. **Guardian** (~770-1540 MMR)
3. **Crusader** (~1540-2310 MMR)
4. **Archon** (~2310-3080 MMR)
5. **Legend** (~3080-3850 MMR)
6. **Ancient** (~3850-4620 MMR)
7. **Divine** (~4620-5420+ MMR)
8. **Immortal** (5420+ MMR with leaderboard ranking)

**Separate MMR for:**
- Core MMR
- Support MMR

### Server/Region System
**Regional Servers** (player selects preferences):
- US West
- US East
- Europe West
- Europe East
- Southeast Asia
- China (Perfect World servers - separate ecosystem)
- South America
- Australia
- India
- South Africa
- Japan
- Korea
- Dubai

**Important:** MMR is global but regional leaderboards exist for Immortal players.

### Platform
- **PC** (Windows, Linux, macOS via Steam)

### What Matters for Competitive Tournaments
**Required Information:**
1. **Steam ID** or **Friend ID**
2. **MMR** (numerical rating)
3. **Medal/Rank** (e.g., "Divine 3")
4. **Server Region** (primary region for ping)
5. **Role preference** (Core/Support MMR)
6. **Behavior Score** (some tournaments check this)

**Verification Method:**
- Dota 2 API (public profile required)
- OpenDota, Dotabuff, Stratz (stat tracking sites)
- In-game profile with visible MMR

---

## 4. EA SPORTS FC 26 (formerly FIFA)

### Identity System
- **Primary ID:** EA Account (EA ID)
- **Platform Account:** Also need PlayStation Network, Xbox Live, or Steam ID
- **Display Name:** EA account username

### Rank/Division System (2024-2025)
**FUT Champions and Division Rivals:**

**FUT Champions:**
- Qualification through Division Rivals
- Skill Rating (SR) based system
- Weekly competitive event with rewards tiers

**Division Rivals Divisions:**
1. Division 10 (lowest)
2. Division 9
3. Division 8
4. Division 7
5. Division 6
6. Division 5
7. Division 4
8. Division 3
9. Division 2
10. Division 1
11. **Elite Division** (highest)

**Skill Rating (SR)** determines division placement

### Server/Region System
**Regional Tournament Structure:**
- Africa
- Asia North
- Asia South  
- Europe East
- Europe West
- Latin America North
- Latin America South
- Middle East
- North America
- Oceania

**Note:** Online matchmaking is region-based but not strictly locked.

### Platform
- **PlayStation 5**
- **PlayStation 4**
- **Xbox Series X|S**
- **Xbox One**
- **PC** (Steam, EA App)
- **Nintendo Switch** (limited version)

**Cross-platform:** Limited cross-play between console generations

### What Matters for Competitive Tournaments
**Required Information:**
1. **EA Account ID**
2. **Platform** (PS5, Xbox, PC)
3. **FUT Division** and **Skill Rating**
4. **Regional Qualifier** (which region they compete in)
5. **FUT Champions Rank** (if applicable)
6. **Console/PC specific ID** (PSN ID, Xbox Gamertag, Steam)

**Verification Method:**
- EA account verification
- FUT Champions/Division Rivals records
- FC Pro official tournament platform

---

## 5. eFootball 2026 (formerly PES)

### Identity System
- **Primary ID:** Konami ID
- **Platform Account:** Also need PlayStation Network, Xbox Live, or Steam ID
- **Display Name:** In-game username linked to Konami account

### Rank/Division System (2024-2025)
**Division System in eFootball:**

**Divisions:**
1. Division 10 (lowest)
2. Division 9
3. Division 8
4. Division 7
5. Division 6
6. Division 5
7. Division 4
8. Division 3
9. Division 2
10. Division 1
11. **eFootball Champion Badge** (top tier)

**Rating System:** Numerical rating that determines division

### Server/Region System
- **Global matchmaking** with regional preferences
- No hard region locks
- Cross-platform play between all platforms

**Platform Regions:**
- Generally matched by ping/connection quality
- FIFAe World Cup uses regional qualifiers

### Platform
- **PlayStation 5**
- **PlayStation 4**
- **Xbox Series X|S**
- **Xbox One**
- **PC** (Windows, Steam)
- **iOS**
- **Android**

**Cross-platform:** Full cross-platform play across all devices

### What Matters for Competitive Tournaments
**Required Information:**
1. **Konami ID**
2. **Platform** (Console/PC/Mobile)
3. **Division** and **Rating**
4. **Platform-specific ID** (PSN, Xbox, Steam)
5. **Region** (for tournament organization)

**Verification Method:**
- Konami account verification
- In-game division/rating visible
- FIFAe World Cup official platform (yes, FIFA branded event for eFootball)

---

## 6. PUBG MOBILE

### Identity System
- **Primary ID:** PUBG Mobile ID (numeric, e.g., "512345678")
- **Account System:** Linked to social media (Facebook, Twitter) or phone number
- **Display Name:** In-game name (can be changed with rename cards)

### Rank/Division System (2024-2025)
**Tier System** (separate for each mode - TPP/FPP, Solo/Duo/Squad):

**Classic Mode Ranks:**
1. **Bronze** (V, IV, III, II, I)
2. **Silver** (V, IV, III, II, I)
3. **Gold** (V, IV, III, II, I)
4. **Platinum** (V, IV, III, II, I)
5. **Diamond** (V, IV, III, II, I)
6. **Crown** (V, IV, III, II, I)
7. **Ace** (with star system and points)
8. **Ace Master** (4200+ points)
9. **Ace Dominator** (4400+ points)
10. **Conqueror** (Top 500 per server per mode)

**Important:** Each tier has divisions (V to I), and points determine progression.

### Server/Region System
**Regional Servers** (player must choose at account creation):
- North America
- Europe  
- Asia
- South America
- Middle East
- KRJP (Korea/Japan)

**Important:** Server selection affects ranking leaderboards. Conqueror is top 500 per server.

### Platform
- **iOS** (iPhone, iPad)
- **Android**

### What Matters for Competitive Tournaments
**Required Information:**
1. **PUBG Mobile ID** (numeric ID)
2. **In-game Name**
3. **Server/Region**
4. **Tier and Division** (e.g., "Ace Dominator")
5. **Rank Points**
6. **Mode** (TPP/FPP, Solo/Duo/Squad)
7. **Linked Account** (for verification - Facebook, Twitter, etc.)

**Verification Method:**
- In-game ID search
- Screenshot verification with ID visible
- Third-party tracking (limited compared to PC games)
- PMCO/PMGC official tournament platform

---

## 7. Mobile Legends: Bang Bang (MLBB)

### Identity System
- **Primary ID:** MLBB ID + Server ID (e.g., "12345678 [1234]")
- **Account System:** Moonton Account
- **Display Name:** In-game name (can be changed with rename cards)

### Rank/Division System (2024-2025)
**Ranked Mode Tiers:**

1. **Warrior** (III, II, I)
2. **Elite** (III, II, I)
3. **Master** (IV, III, II, I)
4. **Grandmaster** (V, IV, III, II, I)
5. **Epic** (V, IV, III, II, I)
6. **Legend** (V, IV, III, II, I)
7. **Mythic** (with star system)
8. **Mythic Honor** (based on points)
9. **Mythic Glory** (based on points)
10. **Mythic Immortal** (Top 50 per server)

**Points System:** Above Mythic, players earn points instead of stars.

### Server/Region System
**Server Selection** (affects rankings and matchmaking):

Multiple servers per region, including:
- Various numbered servers (e.g., Server 2001, 2002, etc.)
- Servers are region-specific but not named by region
- Players in same region can be on different servers

**Regional Tournament Structure:**
- Southeast Asia (strongest region - Philippines, Indonesia, Malaysia, Singapore)
- North America
- Latin America
- Europe
- Middle East
- India
- Other regions

**Important:** Server number matters for leaderboards and rankings.

### Platform
- **iOS** (iPhone, iPad)
- **Android**

### What Matters for Competitive Tournaments
**Required Information:**
1. **MLBB ID** (numeric)
2. **Server ID** (numeric)
3. **In-game Name**
4. **Rank Tier** (e.g., "Mythic Glory")
5. **Rank Points** (if Mythic+)
6. **Server Ranking** (if high rank)
7. **Moonton Account** (for verification)
8. **Region/Country**

**Verification Method:**
- In-game ID lookup with server
- Profile screenshot with ID and rank visible
- MPL (Mobile Legends Professional League) official platform
- M-series World Championship platform

---

## 8. Free Fire

### Identity System
- **Primary ID:** Free Fire ID (numeric, e.g., "123456789")
- **Account System:** Garena Account (or Google/Facebook login)
- **Display Name:** In-game name (can be changed)

### Rank/Division System (2024-2025)
**BR Ranked Mode:**

1. **Bronze** (III, II, I)
2. **Silver** (III, II, I)
3. **Gold** (III, II, I)
4. **Platinum** (III, II, I)
5. **Diamond** (III, II, I)
6. **Heroic**
7. **Grandmaster**

**Ranked Points:** Determines progression through tiers.

**Clash Squad Ranked Mode:**
- Similar tier system but separate from BR ranked

### Server/Region System
**Regional Servers:**
- Brazil
- LATAM (Latin America)
- North America
- Europe
- Middle East
- India
- Southeast Asia
- Indonesia

**Important:** Free Fire has strong regional divisions, especially for tournaments.

### Platform
- **iOS** (iPhone, iPad)
- **Android**

### What Matters for Competitive Tournaments
**Required Information:**
1. **Free Fire ID** (numeric)
2. **In-game Name**
3. **Server/Region**
4. **Rank Tier** (BR or Clash Squad)
5. **Ranked Points**
6. **Garena Account** or linked social account
7. **Region** (critical for regional tournaments)

**Verification Method:**
- In-game profile verification
- Screenshot with ID and rank
- FFWS (Free Fire World Series) official platform
- Regional league platforms

**Note:** Free Fire has particularly strong esports presence in Brazil, LATAM, and Southeast Asia.

---

## 9. Call of Duty: Mobile (CODM)

### Identity System
- **Primary ID:** Call of Duty (Activision) ID
- **Account System:** Activision Account
- **Display Name:** Username (can include special characters)
- **UID:** Unique numeric ID in-game

### Rank/Division System (2024-2025)
**Multiplayer Ranked:**

1. **Rookie** (V, IV, III, II, I)
2. **Veteran** (V, IV, III, II, I)
3. **Elite** (V, IV, III, II, I)
4. **Pro** (V, IV, III, II, I)
5. **Master** (V, IV, III, II, I)
6. **Grandmaster** (V, IV, III, II, I)
7. **Legendary** (with points, e.g., 6500+)

**Battle Royale Ranked:**
- Same tier system as Multiplayer but separate rankings

**Important:** Multiplayer and BR have separate rank progressions.

### Server/Region System
**Server Regions:**
- North America
- South America
- Europe
- Asia
- Middle East
- Other

**Regional matchmaking** but not as strictly separated as some games.

### Platform
- **iOS** (iPhone, iPad)
- **Android**
- **Controller support** available on mobile

### What Matters for Competitive Tournaments
**Required Information:**
1. **Activision ID** (Username with numbers)
2. **UID** (numeric ID visible in-game)
3. **Rank Mode** (MP or BR)
4. **Rank Tier** (e.g., "Legendary 7500")
5. **Server/Region**
6. **Device** (iOS/Android - some tournaments device-specific)
7. **Linked Account** (Activision account)

**Verification Method:**
- Activision account verification
- In-game UID lookup
- Screenshot with rank and UID
- COD Mobile World Championship official platform
- Regional tournament organizers

---

## 10. Rocket League

### Identity System
- **Primary ID:** Epic Games Account ID
- **Platform Account:** Can link PlayStation Network, Xbox Live, Steam, Nintendo Switch
- **Display Name:** Epic Games display name
- **Legacy:** Some players still use Steam ID if account predates Epic acquisition

### Rank/Division System (2024-2025)
**Competitive Playlists** (separate ranks for each mode):

**Ranks** (with 4 divisions each, I-IV):
1. **Bronze** (I, II, III)
2. **Silver** (I, II, III)
3. **Gold** (I, II, III)
4. **Platinum** (I, II, III)
5. **Diamond** (I, II, III)
6. **Champion** (I, II, III)
7. **Grand Champion** (I, II, III)
8. **Supersonic Legend** (no divisions)

**MMR System:** Hidden MMR determines rank, with visible rank as representation.

**Competitive Playlists:**
- 1v1 (Duel)
- 2v2 (Doubles)
- 3v3 (Standard)
- Extra modes (separate rankings)

### Server/Region System
**Server Regions** (player can select preferred regions):
- US-East
- US-West
- Europe
- Asia (Southeast Asia, East)
- Oceania
- South America
- Middle East
- South Africa

**Important:** No region-locked rankings; matchmaking considers ping.

### Platform
- **PC** (Epic Games Store, Steam)
- **PlayStation 5**
- **PlayStation 4**
- **Xbox Series X|S**
- **Xbox One**
- **Nintendo Switch**

**Cross-platform:** Full cross-platform play and parties across all platforms.

### What Matters for Competitive Tournaments
**Required Information:**
1. **Epic Games Account ID** (or Steam ID for legacy)
2. **Current Rank** (with division, e.g., "Champion II")
3. **Playlist** (1v1, 2v2, or 3v3)
4. **Peak Rank** (highest achieved)
5. **Platform** (which platform they primarily play on)
6. **Server Region** (preferred region for ping)
7. **Tracker Network profile** (common for verification)

**Verification Method:**
- Epic Games account
- Rocket League Tracker (tracker.gg/rocket-league)
- In-game profile with Epic ID
- RLCS (Rocket League Championship Series) official platform

---

## 11. Tom Clancy's Rainbow Six Siege (R6)

### Identity System
- **Primary ID:** Ubisoft Connect Username
- **Account System:** Ubisoft Connect (formerly Uplay)
- **Platform-Specific:** Also have platform usernames (PSN, Xbox, Steam)

### Rank/Division System (2024-2025)
**Ranked 2.0 System:**

**Ranks** (each with 5 divisions, V-I):
1. **Copper** (V, IV, III, II, I)
2. **Bronze** (V, IV, III, II, I)
3. **Silver** (V, IV, III, II, I)
4. **Gold** (V, IV, III, II, I)
5. **Platinum** (V, IV, III, II, I)
6. **Emerald** (V, IV, III, II, I)
7. **Diamond** (V, IV, III, II, I)
8. **Champion** (no divisions, top players)

**Rank Points (RP):** Numerical system with minimum/maximum RP per rank.

**Separate Ranks:**
- Ranked 2.0 (current standard)
- Standard (legacy, less used)

### Server/Region System
**Data Centers** (affects matchmaking):

**Regions:**
- North America (Central, East, West)
- South America (Brazil, South)
- Europe (West, North, North Central, Central)
- Asia (East, Southeast, South, Japan)
- Australia

**Important:** Players can select data center preference but ranked is primarily matched by region.

### Platform
- **PC** (Ubisoft Connect, Steam)
- **PlayStation 5**
- **PlayStation 4**
- **Xbox Series X|S**
- **Xbox One**

**Cross-play:** Available between consoles; PC separate pool

### What Matters for Competitive Tournaments
**Required Information:**
1. **Ubisoft Connect Username**
2. **Platform** (PC, PlayStation, Xbox)
3. **Rank** (with division, e.g., "Platinum III")
4. **RP (Rank Points)**
5. **Data Center/Region**
6. **Platform-specific username** (if different from Ubisoft)
7. **K/D and Win Rate** (often requested)

**Verification Method:**
- Ubisoft Connect profile
- R6 Tracker (r6.tracker.network)
- In-game profile screenshot
- Official R6 esports platform
- SiegeGG, Faceit (for competitive leagues)

---

## Summary Table: Critical Tournament Registration Fields by Game

| Game | Primary Identity | Rank System Type | Regional? | Platforms | Key Verification |
|------|-----------------|------------------|-----------|-----------|------------------|
| VALORANT | Riot ID (Name#Tag) | 9 Ranks (27 tiers) + RR | Yes (region-specific) | PC | Riot ID, Region, Rank+Tier |
| CS2 | Steam ID64 | CS Rating (numerical) | No (global) | PC | Steam ID, CS Rating |
| Dota 2 | Steam ID | MMR + Medals (8 ranks) | Global MMR, regional leaderboards | PC | Steam ID, MMR, Medal |
| EA FC 26 | EA Account + Platform ID | Skill Rating + Divisions | Regional tournaments | Multi-platform | EA ID, Platform, Division, SR |
| eFootball 2026 | Konami ID + Platform ID | 11 Divisions + Rating | Global, regional events | Multi-platform + Mobile | Konami ID, Platform, Division |
| PUBG Mobile | PUBG Mobile ID (numeric) | 10 Tiers (5 divisions each) | Yes (server-specific) | Mobile (iOS/Android) | PUBG ID, Server, Rank+Points |
| MLBB | MLBB ID + Server | 10 Tiers + Points | Yes (server-specific) | Mobile (iOS/Android) | MLBB ID, Server, Rank+Points |
| Free Fire | FF ID (numeric) | 7 Tiers (3 divisions each) | Yes (regional servers) | Mobile (iOS/Android) | FF ID, Region, Rank |
| COD Mobile | Activision ID + UID | 7 Tiers (5 divisions each) | Regional matching | Mobile (iOS/Android) | Activision ID, UID, Rank |
| Rocket League | Epic Games ID | 8 Ranks (4 divisions each) | No (global + ping) | Multi-platform | Epic ID, Rank+Division, Playlist |
| R6 Siege | Ubisoft Username | 8 Ranks (5 divisions each) | Data center selection | Multi-platform | Ubisoft ID, Platform, Rank+RP |

---

## Recommended Universal Tournament Registration Fields

Based on this research, a tournament registration system should collect:

### Universal Fields (All Games)
1. **Game Title** (dropdown selection)
2. **Primary Account ID** (game-specific format validation)
3. **In-Game Display Name**
4. **Current Rank/Rating** (game-specific options)
5. **Peak Rank/Rating** (optional but valuable)

### Game-Specific Conditional Fields

#### For Regional Games (VALORANT, PUBG Mobile, MLBB, Free Fire)
6. **Server/Region** (required)
7. **Server ID** (for mobile games with numbered servers)

#### For Multi-Platform Games (FC, eFootball, Rocket League, R6)
8. **Platform** (PC, PlayStation, Xbox, Mobile, Switch)
9. **Platform-Specific ID** (Steam ID, PSN ID, Xbox Gamertag)

#### For Games with Mode-Specific Ranks (CODM, Rocket League)
10. **Game Mode/Playlist** (specify which ranked mode)

### Verification Fields
11. **Tracker Network Profile URL** (if applicable)
12. **Screenshot Upload** (showing ID + rank)
13. **Public Profile Toggle** (must be enabled for verification)

### Additional Competitive Context
14. **Team/Organization** (if representing one)
15. **Previous Tournament Experience** (optional)
16. **Preferred Role** (for team games like Dota 2, MLBB)

---

## API Availability for Verification

### Games with Public APIs
- ✅ **VALORANT**: Riot Games API (requires API key)
- ✅ **CS2**: Steam Web API
- ✅ **Dota 2**: Steam Web API, OpenDota API
- ✅ **Rocket League**: Epic Games API (limited)
- ⚠️ **R6 Siege**: Ubisoft Connect API (restricted)
- ⚠️ **EA FC 26**: Limited official API
- ⚠️ **Mobile Games**: Generally no public APIs

### Third-Party Verification Services
- **Tracker Network** (tracker.gg): Covers VALORANT, CS2, R6, Rocket League
- **OpenDota/Dotabuff**: Dota 2 statistics
- **Mobile Game Trackers**: Limited availability, rely on screenshots

---

## Competitive Scene Context (2025)

### Tier 1 Esports (Largest prize pools, viewership, infrastructure)
1. **Dota 2** - The International
2. **CS2** - Major Championships
3. **VALORANT** - VCT (VALORANT Champions Tour)
4. **Mobile Legends** - M-series World Championship (Southeast Asia dominant)
5. **League of Legends** - Not in list but relevant context

### Tier 2 Esports (Established competitive scenes)
6. **Rocket League** - RLCS
7. **Rainbow Six Siege** - Six Invitational
8. **EA FC 26** - FC Pro, eChampions League
9. **PUBG Mobile** - PMGC (Global Championship)
10. **Free Fire** - FFWS (World Series)

### Growing/Regional Esports
11. **COD Mobile** - World Championship
12. **eFootball** - FIFAe World Cup (ironic naming)

---

## Platform-Specific Considerations

### PC Games
- Generally more established verification systems
- Public APIs often available
- Third-party platforms (Faceit, ESEA) common for CS2
- Steam integration provides additional verification layer

### Console Games
- Platform accounts (PSN, Xbox Live) required
- Cross-platform games need both platform and game account
- More difficult to verify without screenshots
- Some games have console-exclusive tournaments

### Mobile Games
- Verification primarily through screenshots
- Server/region critical for ranking context
- Regional strength varies significantly (e.g., MLBB strongest in SEA)
- Device specifications sometimes matter for tournaments
- Account binding (Facebook, Google, etc.) important for recovery

---

## Recommendations for Implementation

### Priority 1: Essential Data
- Primary account identifier (validated format per game)
- Current rank/rating (with proper tier/division if applicable)
- Region/server (for games where it matters)
- Platform (for multi-platform games)

### Priority 2: Verification Data
- Screenshot of profile (automated upload)
- Tracker profile URL (where available)
- Secondary identifier (email, Discord, phone)

### Priority 3: Tournament Context
- Team information
- Role preference (for team games)
- Previous tournament results
- Availability/timezone

### Data Validation Rules by Game

**VALORANT:**
- Format: Username#TAG (no spaces in username, TAG is 4-5 characters)
- Rank: Must specify tier (e.g., "Diamond II" not just "Diamond")
- Region: Required - affects rank validity

**CS2:**
- Steam ID format validation (SteamID64 is 17 digits)
- CS Rating: Integer between 0-35000
- Region: Optional (global ranks)

**Dota 2:**
- Steam ID format validation
- MMR: Integer (typically 0-12000+)
- Medal: Herald through Immortal with star count

**PUBG Mobile:**
- ID: 9-10 digit number
- Server: Must select from valid server list
- Tier + Division + Points

**MLBB:**
- ID: 10-11 digit number
- Server: 4-digit server number required
- Rank points if Mythic+

**Mobile Games General:**
- Platform: iOS or Android
- Screenshot required (no public APIs)

---

## Conclusion

For a tournament registration system to properly verify player skill levels across these 11 games, the system must:

1. **Adapt to game-specific ID formats** - No universal player ID exists
2. **Understand regional variations** - Some games have region-locked ranks, others don't
3. **Support platform diversity** - Multi-platform games need platform-specific data
4. **Implement verification workflows** - Mix of API verification (where available) and screenshot verification (mobile games)
5. **Account for mode-specific rankings** - Some games have multiple ranked modes
6. **Provide clear dropdown options** - Rank selection must match each game's current system

The most critical fields are:
- **Game-specific primary ID** (format varies)
- **Current rank with full specification** (tier, division, points as applicable)
- **Region/server** (where it affects ranking)
- **Platform** (for multi-platform games)
- **Verification method** (screenshot, profile URL, or API)

Mobile games (PUBG Mobile, MLBB, Free Fire, COD Mobile) require the most manual verification due to lack of public APIs, while PC games (VALORANT, CS2, Dota 2, Rocket League) can leverage existing APIs for automated verification.

---

**Research Sources:**
- Official game websites and documentation
- Liquipedia esports wikis
- Tracker Network sites (tracker.gg, r6.tracker.network, etc.)
- Esports tournament platforms (RLCS, VCT, etc.)
- Game update notes and patch notes from 2024-2025
- Community wikis and competitive scene documentation

**Note:** Rank systems can change with major updates. This report reflects systems as of late 2024/early 2025. Recommend periodic updates to maintain accuracy.
