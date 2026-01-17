# **📘 Documentation: Adaptive Career Engine (v5.0)**

**Component:** User Profile "Career" Tab **Design System:** Aurora Zenith (Wide Mode) **Purpose:** To display a player's complete competitive history across 10+ different game titles using adaptive layouts.

---

## **1\. UX Architecture: "Wide Mode"**

Unlike the other tabs (Overview, Inventory), the Career tab **breaks the grid**.

* **Behavior:** When the user clicks "Career", the **Right Sidebar** (Bounties/Live Feed) is hidden.  
* **Result:** The Center Column expands from `col-span-6` to `col-span-9`.  
* **Why:** Competitive stats (graphs, timelines, heatmaps) require horizontal space to be readable. This creates a "Pro Dashboard" feel similar to Tracker.gg or Dotabuff.

---

## **2\. Component Breakdown**

### **2.1 The Game Selector Bar (Sticky Nav)**

**Location:** Top of the Career Tab (Sticky). **Visual:** A horizontal scrollable glass bar containing 10 game buttons.

* **Elements:**  
  * **Shooter Block:** Valorant, CS2, CoD, PUBG, FreeFire.  
  * **Sports Block:** eFootball, FC 26, Rocket League.  
  * **MOBA Block:** MLBB, Dota 2\.  
* **Behavior:**  
  * **Clicking a Game:** Triggers the `setGame(gameKey, layoutType)` function.  
  * **Action 1:** Updates the "Passport Card" with that game's specific Rank, IGN, and Background Image.  
  * **Action 2:** Swaps the **"Layout Engine"** below (e.g., switches from *Shooter UI* to *Athlete UI*).

### **2.2 The "Official Passport" Card**

**Location:** Prominent header below the selector. **Purpose:** The player's "License" to compete in that specific game.

* **Dynamic Elements (Updates via JS):**  
  * **Background Image:** Changes to a game-specific wallpaper (e.g., Dust 2 for CS2, Bind for Valorant).  
  * **Game Icon:** The 64px logo on the left (e.g., Valorant "V").  
  * **IGN (In-Game Name):** Displays the unique ID for that game (e.g., `Viper#NA1` vs `ViperCS`).  
  * **Rank Badge:** Displays the current competitive tier (e.g., "Radiant" or "Global Elite").  
* **Static Elements:**  
  * **"Verified" Badge:** Indicates the account is linked and owned by the user.  
  * **"Current Affiliation" (Side Card):** Shows the team the player is currently signed to *for that specific game*.

---

## **3\. The 3 Adaptive UI Engines**

This is the core intelligence of the page. Instead of one generic layout, the page loads a different "Engine" based on the game genre.

### **🚗 Engine A: The Shooter UI (Tactical)**

**Used For:** Valorant, CS2, CoD, PUBG, FreeFire. **Philosophy:** Precision, Kills, and Survival.

* **Stat Grid (4 Cards):**  
  1. **K/D Ratio:** Kill/Death ratio (The \#1 stat for shooters).  
  2. **Win Rate:** Percentage of matches won.  
  3. **Tournaments:** Total events played.  
  4. **Winnings:** Total cash prize earned in this game.  
* **Role Card:** Shows the player's tactical role (e.g., "Entry Fragger" or "Sniper").  
* **Affiliation History:** A list of past teams specifically for this shooter.

### **⚽ Engine B: The Athlete UI (Sports/Sim)**

**Used For:** eFootball, FC 26, Rocket League. **Philosophy:** Match Ratings, Goals, and Form.

* **The "Pitch" Visual:** A green field background visualization.  
  1. **Primary Stat:** **Goals Scored** (Big text).  
  2. **Secondary Stat:** **Assists** (Big text).  
* **Metric Trio:**  
  1. **Win Rate:** Match success %.  
  2. **Clean Sheets:** Games with 0 goals conceded.  
  3. **Form:** A visual "Last 3 Games" dot indicator (Green/Green/Red).  
* **Player Card (FUT Style):** A vertical card showing their position (e.g., "ST" \- Striker) and style (e.g., "Finisher").

### **🧙‍♂️ Engine C: The Tactician UI (MOBA)**

**Used For:** Dota 2, MLBB. **Philosophy:** Economy, Roles, and Objectives.

* **Hero Pool:** Circular avatars of the user's top 3 played heroes (e.g., Juggernaut, Pudge).  
* **Hex Stats:** Two large vertical cards emphasizing:  
  1. **GPM:** Gold Per Minute (Economy stat).  
  2. **KDA:** (Kills \+ Assists) / Deaths (Teamfight contribution).

---

## **4\. The Universal Tournament Log**

**Location:** Bottom of the tab (Full Width). **Purpose:** A unified history of every tournament played in the selected game.

* **Columns:**  
  1. **Tournament:** Name \+ Date (e.g., "DeltaCrown Winter Major").  
  2. **Result:** A badge showing placement (e.g., 🥇 1st Place, 🥉 3rd Place, or "Defeat").  
  3. **Prize:** Cash amount won (or "-").  
* **Behavior:** This table filters its rows based on the selected game ID.

---

## **5\. Developer Implementation Notes**

### **Data Structure (`gameConfig`)**

The JavaScript uses a dictionary object to store the "Identity" data for each game. You must populate this from your backend (Django Context).

JavaScript  
const gameConfig \= {  
    'valorant': {  
        name: 'VALORANT',       // Display Name  
        type: 'shooter',        // Which Layout Engine to use?  
        icon: 'fa-v',           // FontAwesome Class  
        color: 'text-\[\#ff4655\]',// Brand Color  
        ign: 'Viper\#NA1',       // User's IGN  
        rank: 'Radiant'         // User's Rank  
    },  
    // ... other games  
};

### **Switching Logic**

When `switchView('career')` is called:

1. **CSS Class Swap:** The `#center-column` removes `lg:col-span-6` and adds `lg:col-span-9`.  
2. **Sidebar Hiding:** The `#right-sidebar` gets `hidden` class.  
3. **Game Init:** It automatically calls `setGame('valorant')` to load the default view.

### **Manual Data Collection Strategy**

Since you do not have game APIs, the "Stats" in the UI Engines are explicitly designed to be **manually updatable**:

* **"K/D Ratio"** is calculated from Tournament Data (Total Kills / Total Deaths in *your* database).  
* **"Win Rate"** is calculated from Match Results in *your* database.  
* **"Rank"** is a dropdown field the user sets in their profile (Verified by admin).

This design ensures the profile looks professional and "data-rich" even without a live connection to Riot or Valve servers.

