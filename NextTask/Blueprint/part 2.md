
### **Part 2 (Revised): Game-Specific Field & Roster Specifications**

This document serves as the technical blueprint for the dynamic fields within the tournament registration form. It is built upon the "form-first, organizer-driven" philosophy from Part 1 and incorporates the specific requirements from your developer instruction guide.

#### **General Roster & Player Field Information**

For **Team-Based Games**, the fields detailed below are to be presented for **each player** the captain adds to the roster in Step 2. The system should enforce the minimum number of starters and allow up to the maximum number of substitutes as specified for each game.

For **Solo Games**, these fields will appear in the single-step registration form.

---

### **A. Team-Based Games**

#### **1. VALORANT**
* **Team Size:** 5 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `riotId` | Riot ID | Text Input | `Example: PlayerName#TAG` | Must contain a single `#` character. Min length: 5 (e.g., `a#a`). |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer can set as Required/Optional). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* Duelist
* Controller
* Initiator
* Sentinel
* IGL (In-Game Leader)

---

#### **2. CS2 (Counter-Strike 2)**
* **Team Size:** 5 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `steamId` | Steam ID | Text Input | `e.g., STEAM_0:1:123456 or 7656119...` | Must contain numbers and start with `STEAM_` or `765`. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Note on `steamId`:** It's helpful to add a small link below this field: "How to find your Steam ID?" which links to a simple guide.

**Player Role Dropdown Options (`playerRole`):**
* IGL (In-Game Leader)
* Entry Fragger
* AWPer
* Lurker
* Support

---

#### **3. Dota 2**
* **Team Size:** 5 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `steamId` | Steam ID | Text Input | `e.g., STEAM_0:1:123456 or 7656119...` | Must contain numbers and start with `STEAM_` or `765`. |
| `dotaFriendId` | Dota 2 Friend ID | Text Input | `Find this in your Dota 2 profile` | Must be numbers only. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Position | Dropdown | `Select a position` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* Hard Carry (Pos 1)
* Midlaner (Pos 2)
* Offlaner (Pos 3)
* Soft Support (Pos 4)
* Hard Support (Pos 5)

---

#### **4. Mobile Legends: Bang Bang (MLBB)**
* **Team Size:** 5 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `inGameName` | In-Game Name | Text Input | `The exact name shown in MLBB` | Must not be empty. |
| `mlbbUserId` | MLBB User ID | Text Input | `Example: 12345678 (1234)` | Must be numbers only. Can accept format `ID(Zone)`. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* Gold Laner
* EXP Laner
* Mid Laner
* Jungler
* Roamer

---

#### **5. PUBG (PC/Mobile)**
* **Team Size:** 4 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `characterName` | PUBG Character Name | Text Input | `The exact name shown in PUBG` | Must not be empty. |
| `pubgId` | PUBG ID | Text Input | `Example: 5123456789` | Must be numbers only (for Mobile) or alphanumeric. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* IGL / Shot Caller
* Assaulter / Fragger
* Support
* Sniper / Scout

---

#### **6. Free Fire**
* **Team Size:** 4 Starters + 2 Substitutes

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `inGameName` | In-Game Name | Text Input | `The exact name shown in Free Fire` | Must not be empty. |
| `freeFireUid` | Free Fire UID | Text Input | `Example: 1234567890` | Must be numbers only. |
| `discordId` | Discord ID | Text Input | `Example: username` | No special validation needed. (Organizer sets as Optional by default). |
| `playerRole` | Player Role | Dropdown | `Select a role` | N/A |

**Player Role Dropdown Options (`playerRole`):**
* Rusher
* Flanker
* Support
* Shot Caller (IGL)

---

### **B. Solo / Individual Entry Games**

#### **7. eFootball**
* **Format:** Can be Solo (1v1) or Team (2v2 with 1 sub). The form should adapt.

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `efootballUsername` | eFootball Username | Text Input | `Your username in the game` | Must not be empty. |
| `efootballUserId`| eFootball User ID | Text Input | `Example: 123456789` | Must be numbers only. |

---

#### **8. FC 26 (EA Sports FC)**
* **Format:** Can be Solo (1v1) or Team (1v1 with 1 sub for co-op formats).

| Field Name | Field Label | Field Type | Helper Text / Placeholder | Format Validation Rule (Client-Side) |
| :--- | :--- | :--- | :--- | :--- |
| `displayName` | Player Display Name | Text Input | `Enter player's name` | Must not be empty. |
| `platform` | Platform | Dropdown | `Select your gaming platform` | Must select one option. |
| `platformId` | EA ID / PSN ID / Gamertag | Text Input | `Enter your ID for the selected platform` | No special format validation. |
| `fc26Username` | FC 26 Username | Text Input | `Your username in FC 26` | Must not be empty. |

**Platform Dropdown Options (`platform`):**
* PC (EA App)
* PlayStation
* Xbox

**Note on `platformId`:** The label for this field should dynamically change based on the `platform` selection (e.g., if "PlayStation" is chosen, the label becomes "PSN ID").

---
