# **📘 DeltaCrown Career Page Design Doc \- Part 1**

**Category:** Tactical Shooters & MOBA (Rank \+ Role Focus)

## **1\. Visual Architecture (The Master Layout)**

Every game page uses the exact same HTML structure (Wide Mode), but the data inside the "Slots" changes dynamically.

### **The "Identity Card" (Top Header)**

* **Slot A (Main Title):** The primary identifier (e.g., Riot ID).  
* **Slot B (Subtitle/Context):** Server, Region, or Platform.  
* **Slot C (Stats):** Matches Played (Not "Hours" \- derived from Tournament App).  
* **Slot D (Ranking):** The main Rank Name \+ Icon.

### **The "Attributes Sidebar" (Left Column)**

* A vertical list of 3-4 key properties specific to that game (e.g., Role, Peak Rank).

### **The "Stats Engine" (Center Grid)**

* **Shooter UI:** 4-Grid (K/D, Win Rate, Tournaments, Winnings).  
* **Tactician UI:** Hex/Bar Stats (GPM, KDA, Hero Pool).

---

## **2\. Game Specifications (Shooters & MOBA)**

### **🔫 Game: VALORANT**

* **Engine:** Shooter UI  
* **Visual Theme:** Red (\#ff4655)  
* **Data Source:** \[Screenshot: image\_54c1f8.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **Riot ID** | core\_identity.riot\_id | e.g., "Siuu\#2025" |
| **Context Badge** | **Region** | core\_identity.region | e.g., "Asia Pacific" |
| **Stat Line** | Matches Played | *(Calculated)* | Count from Tournament App |
| **Rank Display** | **Current Rank** | competitive\_info.current\_rank | e.g., "Platinum 1" |
| **Attribute 1** | Main Role | competitive\_info.main\_role | e.g., "Initiator" |
| **Attribute 2** | Peak Rank | optional\_fields.peak\_rank | e.g., "Diamond 1" |
| **Privacy Rule** | **NONE** | Riot IDs are public. Display full ID. |  |

---

### **🔫 Game: COUNTER-STRIKE 2 (CS2)**

* **Engine:** Shooter UI  
* **Visual Theme:** Yellow/Orange (\#eab308)  
* **Data Source:** \[Screenshot: image\_54c5a1.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **In-Game Name** | core\_identity.in\_game\_name | e.g., "s1mple" |
| **Context Badge** | **Region** | core\_identity.primary\_region | e.g., "EU West" |
| **Stat Line** | Matches Played | *(Calculated)* | Count from Tournament App |
| **Rank Display** | **Rating** | optional\_fields.premier\_rating | e.g., "15,000" (If null, use Rank) |
| **Attribute 1** | Main Role | competitive\_info.main\_role | e.g., "AWPer" |
| **Attribute 2** | Steam Link | *(Derived)* | Link icon to Steam Profile (Optional) |
| **Privacy Rule** | **HIDE ID** | **Hide Steam ID64**. Do not display it on the profile card. |  |

---

### **🔫 Game: CALL OF DUTY: MOBILE**

* **Engine:** Shooter UI  
* **Visual Theme:** Green/Military (\#10b981)  
* **Data Source:** \[Screenshot: image\_54c1ba.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **In-Game Name** | core\_identity.in\_game\_name | e.g., "PlayerName" |
| **Context Badge** | **Region** | core\_identity.region | e.g., "Global" |
| **Stat Line** | Matches Played | *(Calculated)* |  |
| **Rank Display** | **Rank** | competitive\_info.mp\_rank | Show MP Rank by default (e.g. Legendary) |
| **Attribute 1** | Main Mode | optional\_fields.main\_mode | e.g., "Hardpoint" |
| **Attribute 2** | BR Rank | competitive\_info.br\_rank | Optional secondary stat |
| **Privacy Rule** | **HIDE ID** | **Hide COD Mobile UID**. This is a private login identifier. |  |

---

### **🧙‍♂️ Game: DOTA 2**

* **Engine:** Tactician UI (Uses the Hex/Bar layout for stats)  
* **Visual Theme:** Red/Dark Stone (\#b91c1c)  
* **Data Source:** \[Screenshot: image\_54c562.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **In-Game Name** | core\_identity.in\_game\_name | e.g., "Dendi" |
| **Context Badge** | **Server** | core\_identity.primary\_server | e.g., "SEA" |
| **Stat Line** | Matches Played | *(Calculated)* |  |
| **Rank Display** | **MMR Rank** | competitive\_info.current\_rank | e.g., "Divine 5" |
| **Attribute 1** | Role | competitive\_info.main\_role | e.g., "Pos 1 (Carry)" |
| **Attribute 2** | Steam Link | *(Derived)* |  |
| **Privacy Rule** | **HIDE ID** | **Hide Steam ID64**. Display IGN only. |  |

---

### **🧙‍♂️ Game: MOBILE LEGENDS (MLBB)**

* **Engine:** Tactician UI  
* **Visual Theme:** Purple/Pink (\#db2777)  
* **Data Source:** \[Screenshot: image\_54c4e5.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **In-Game Name** | core\_identity.in\_game\_name | e.g., "Lemon" |
| **Context Badge** | **Region** | core\_identity.server\_region | e.g., "Indonesia" |
| **Stat Line** | Matches Played | *(Calculated)* |  |
| **Rank Display** | **Rank** | competitive\_info.current\_rank | e.g., "Mythical Glory" |
| **Attribute 1** | Main Role | competitive\_info.main\_role | e.g., "Roamer" |
| **Attribute 2** | Server ID | *Hidden* | Do not show Server ID on public profile |
| **Privacy Rule** | **HIDE ID** | **Hide Account ID & Server ID**. These are used for account recovery/hacking. |  |

# **📘 DeltaCrown Career Page Design Doc \- Part 2**

**Category:** Battle Royale (Rank \+ Mode Focus)

## **1\. Visual Architecture (Modifications)**

* **Layout Engine:** Shooter UI (Reused because K/D and Wins are still the primary metrics).  
* **Key Difference:** The "Attributes Sidebar" highlights the **Character ID** prominently, as player names in mobile BRs often contain special characters or are hard to search.

---

## **🪂 Game Specifications (Battle Royale)**

### **🪂 Game: PUBG MOBILE**

* **Engine:** Shooter UI  
* **Visual Theme:** Orange/Camo (\#f97316)  
* **Data Source:** \[Screenshot: image\_54c53d.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **In-Game Name** | core\_identity.in\_game\_name | e.g., "PlayerName" |
| **Context Badge** | **Server** | core\_identity.server | e.g., "Asia", "North America" |
| **Stat Line** | Matches Played | *(Calculated)* | Count from Tournament App |
| **Rank Display** | **Current Rank** | competitive\_info.current\_rank | e.g., "Conqueror" |
| **Attribute 1** | Main Mode | optional\_fields.main\_mode | e.g., "Squad TPP" (Crucial for BRs) |
| **Attribute 2** | Character ID | core\_identity.character\_id | **Display this.** Public ID required for search. |
| **Attribute 3** | Server | core\_identity.server | Repeated for clarity in sidebar |
| **Privacy Rule** | **NONE** | Character ID is public data used for friending/invites. |  |

---

### **🔥 Game: FREE FIRE**

* **Engine:** Shooter UI  
* **Visual Theme:** Red/Fire (\#ef4444)  
* **Data Source:** \[Screenshot: image\_54c900.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **In-Game Name** | core\_identity.in\_game\_name | e.g., "Kelly\_FF" |
| **Context Badge** | **Server** | core\_identity.server | e.g., "BD Server" |
| **Stat Line** | Matches Played | *(Calculated)* |  |
| **Rank Display** | **Current Rank** | competitive\_info.current\_rank | e.g., "Grandmaster" |
| **Attribute 1** | Player ID | core\_identity.player\_id | **Display this.** Primary search identifier. |
| **Attribute 2** | Server | core\_identity.server |  |
| **Attribute 3** | Rank | competitive\_info.current\_rank |  |
| **Privacy Rule** | **NONE** | Player ID is public. |  |

# **📘 DeltaCrown Career Page Design Doc \- Part 3**

**Category:** Sports & Simulation (Division \+ Platform Focus)

## **1\. Visual Architecture (The Athlete Engine)**

* **Layout Engine:** Athlete UI (Replaces the standard grid with a **"Pitch/Field" Visualization**).  
* **Visual Focus:** Highlighting "Goals", "Assists", and "Form" (Win/Loss streak).  
* **Key Context:** The **Platform** (PS5, PC, Mobile) is a critical identity field here because cross-play isn't always universal.

---

## **⚽ Game Specifications (Sports & Sim)**

### **⚽ Game: eFOOTBALL 2026**

* **Engine:** Athlete UI  
* **Visual Theme:** Blue/Yellow Pitch (\#3b82f6)  
* **Data Source:** \[Screenshot: image\_54c21b.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **Username** | optional\_fields.username | Use "Username" preference first, fallback to generic name. |
| **Context Badge** | **Platform** | core\_identity.platform | e.g., "Mobile (iOS/Android)", "PlayStation 5" |
| **Stat Line** | Matches Played | *(Calculated)* |  |
| **Rank Display** | **Division** | competitive\_info.division | e.g., "Division 1" |
| **Attribute 1** | Team Name | optional\_fields.team\_name | e.g., "SIUU" (User's custom squad name) |
| **Attribute 2** | Platform | core\_identity.platform |  |
| **Attribute 3** | Division | competitive\_info.division |  |
| **Privacy Rule** | **STRICT PRIVACY** | **HIDE** Konami ID & User ID. These are sensitive login/recovery fields. |  |

---

### **⚽ Game: EA SPORTS FC 26**

* **Engine:** Athlete UI  
* **Visual Theme:** Dark Green/Lime (\#10b981)  
* **Data Source:** \[Screenshot: image\_54c17b.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **In-Game Name** | core\_identity.in\_game\_name | e.g., "Siuu" (The Persona Name) |
| **Context Badge** | **Platform** | core\_identity.platform | e.g., "PC (Origin/Steam)" |
| **Stat Line** | Matches Played | *(Calculated)* |  |
| **Rank Display** | **Division** | competitive\_info.division | e.g., "Elite Division" |
| **Attribute 1** | Main Mode | optional\_fields.main\_mode | e.g., "Ultimate Team" (FUT) |
| **Attribute 2** | Platform | core\_identity.platform |  |
| **Attribute 3** | Division | competitive\_info.division |  |
| **Privacy Rule** | **HIDE ID** | **Hide EA ID**. It is used for account recovery. Display IGN only. |  |

---

### **🏎️ Game: ROCKET LEAGUE**

* **Engine:** Athlete UI (Modified for "Aerials/Saves" instead of just Goals)  
* **Visual Theme:** Neon Blue/Orange (\#06b6d4)  
* **Data Source:** \[Screenshot: image\_54c5df.png\]

| Layout Slot | Field Name (Frontend Label) | Data Source (Backend Field) | Note |
| :---- | :---- | :---- | :---- |
| **Identity (Big Text)** | **In-Game Name** | core\_identity.in\_game\_name | e.g., "PlayerName" |
| **Context Badge** | **Platform** | core\_identity.platform | e.g., "Steam", "Epic Games" |
| **Stat Line** | Matches Played | *(Calculated)* |  |
| **Rank Display** | **Highest Rank** | competitive\_info.highest\_rank | e.g., "Supersonic Legend" |
| **Attribute 1** | Main Mode | optional\_fields.main\_mode | e.g., "Standard 3v3" |
| **Attribute 2** | Platform | core\_identity.platform |  |
| **Attribute 3** | Rank | competitive\_info.highest\_rank |  |
| **Privacy Rule** | **HIDE ID** | **Hide Epic Games ID**. Use In-Game Name for display. |  |

You now have the complete map for all 11 games.

* **Part 1:** Valorant, CS2, CoD:M, Dota 2, MLBB (Role/Rank focus).  
* **Part 2:** PUBG M, Free Fire (ID/Mode focus).  
* **Part 3:** eFootball, FC 26, Rocket League (Platform/Division focus).

**Action:** Use these three parts to populate the `GAME_DISPLAY_CONFIG` dictionary in the backend. Do not deviate from these field mappings as they correspond to the exact data collected during user onboarding.

