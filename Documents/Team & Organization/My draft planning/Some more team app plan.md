# **Some more team app plan topics**

## **1\. The Transfer Ecosystem (Movement Logic)**

**We need a system that manages how players move between teams without breaking tournament integrity.**

### **A. Player Status Types**

**Every user has a "Competitive Status" visible on their profile:**

1. **Free Agent: Not currently on any roster for that game. Eligible to join immediately.**  
2. **Contracted (Active): Currently on a roster. Cannot join another team unless released.**  
3. **Restricted: Banned or Suspended. Cannot join any team.**

### **B. The "Leave & Join" Process**

#### **Scenario 1: Voluntary Departure (Resignation)**

* **Action: Player clicks "Leave Team" in their dashboard.**  
* **The Check: Is the team currently in an "Active Tournament" (Roster Locked)?**  
  * ***Yes:*** **Action Blocked. Error: *"You cannot leave while the team is in an active tournament run."***  
  * ***No:*** **Action Allowed.**  
* **Result: Player becomes "Free Agent". Team Manager gets a notification.**

#### **Scenario 2: The "Kick" (Release)**

* **Action: Manager clicks "Remove from Roster".**  
* **The Check: Roster Lock check (same as above).**  
* **Result: Player is removed. Notification sent: *"You have been released from Protocol V."***

#### **Scenario 3: The "Transfer" (Poaching)**

* ***Context:*** **Protocol V wants a player who is currently in Null Boyz.**  
* **Action: Protocol V Manager sends "Transfer Offer".**  
* **Flow:**  
  * **Notification: Goes to the Current Player.**  
  * **Decision: Player views offer.**  
  * **Acceptance: If Player clicks "Accept":**  
    * **They are auto-removed from Null Boyz.**  
    * **They are auto-added to Protocol V.**  
  * ***Note:*** **In the MVP, we assume "At-Will Employment" (players can leave anytime if not Roster Locked). In the future, you can add "Manager Approval Required" for contracts.**

---

## **2\. The "Solo-Squad" Architecture (1v1 Games)**

**How do we represent 1v1 games (eFootball, FC24, Street Fighter) where a single person plays, but represents a Team/Organization?**

**The Solution: "The Stable" Model.**

### **A. Concept: The "Roster of Solos"**

**Even though the game is 1v1, the Organization still creates a Team Entity.**

* **Example: SYNTAX creates a team called "Syntax FC" (Game: eFootball).**  
* **The Roster: Instead of 5 starters, the roster contains 3 individual players (e.g., Player A, Player B, Player C).**  
* **The Logic: These 3 players do not play *together*. They play *parallel* matches, but they all wear the "Syntax FC" jersey.**

### **B. Display Changes (UI)**

**In the Team Profile for a 1v1 Game, the layout changes:**

* **5v5 Game (Valorant): Shows "Active Lineup" (IGL, Duelist, Smoke...).**  
* **1v1 Game (eFootball): Shows "Athletes List".**  
  * ***Card Style:*** **"Player Name | Rank | Win Rate".**  
  * ***Visual:*** **Like a Tennis or MMA Gym roster. "Here are the 4 fighters representing Syntax."**

### **C. Tournament Registration for Solos**

**When registering for an eFootball Tournament (1v1):**

1. **Manager Action: Selects "Syntax FC".**  
2. **The Question: The system asks: *"Which athlete is entering this slot?"***  
3. **Selection: Manager selects "Player A".**  
4. **Result:**  
   * **Bracket Name: "Syntax FC (Player A)" or just "Player A \[SYN\]".**  
   * **Ranking Points (CP): Earned by Syntax FC (The Team).**

---

## **3\. The "Free Agent" Market (LFT/LFP)**

**This is the discovery engine. It keeps users engaged when they don't have a team.**

### **A. For Players: "Open to Work"**

* **Profile Setting: A toggle switch `[ ] Looking for Team`.**  
* **Inputs:**  
  * **Role: (e.g., Duelist / Striker / Solo).**  
  * **Region: (e.g., Dhaka).**  
  * **Language: (e.g., Bangla/English).**  
* **Visibility: The player now appears in the public "Scouting Grounds" list.**

### **B. For Teams: "Recruitment Post"**

* **Manager Action: Create a "Help Wanted" ad.**  
  * ***Headline:*** **"Looking for Aggressive Duelist for Tier B Tournament."**  
  * ***Requirements:*** **"Must be Diamond 3+, available weekends."**  
* **Application: Free Agents can click "Apply". The Manager sees a list of applicants and can invite them with one click.**

---

## **4\. Technical Implementation Plan**

### **Database Schema Updates**

**1\. `TransferHistory` Model**

* **Tracks every movement for security and history.**

**Python**

**class TransferLog(models.Model):**

    **player \= ForeignKey(User)**

    **from\_team \= ForeignKey(Team, null=True)**

    **to\_team \= ForeignKey(Team, null=True)**

    **transfer\_type \= ChoiceField(JOIN, LEAVE, KICK, TRANSFER)**

    **timestamp \= DateTimeField()**

**2\. `GameConfiguration` Update**

* **We need to tell the system which games are 1v1 and which are Team.**

**Python**

**class GameConfig(models.Model):**

    **name \= "eFootball"**

    **format \= ChoiceField(TEAM\_VS\_TEAM, 1V1\_SOLO, BATTLE\_ROYALE)**

    **roster\_size\_limit \= IntegerField(default=10)** 

    **\# For 1v1 games, roster limit is just how many athletes an Org can hold (e.g., 10).**

    **\# For 5v5 games, limit might be 7 (5 main \+ 2 sub).**

### **UX/UI Updates**

**1\. The "Solo" Team Page**

* **If `GameConfig.format == 1V1_SOLO`:**  
  * **Hide "Roles" (IGL, Support).**  
  * **Show "Individual Stats" per player (Goals Scored, Matches Won).**

**2\. The Player Profile**

* **Add a "Career History" tab.**  
  * ***2025:*** **Joined Null Boyz.**  
  * ***2026:*** **Transferred to Protocol V.**  
  * ***2026:*** **Won Winter Major.**

---

## **5\. Summary of Rules for Users**

1. **Transfers: You can leave a team anytime *unless* the team is locked in an active tournament.**  
2. **Solo Representation: If you play a 1v1 game (eFootball) for an Organization, you share the Organization's Ranking Points. Your wins contribute to the Org's "Empire Score."**  
3. **Free Agency: Mark yourself as "Looking for Team" to be scouted by Managers.**

**This plan ensures that Single-Player games feel just as professional and organized as big Team games, giving Syntax (and other orgs) a reason to sign eFootball stars.**

#### **1\. The "1v1 vs. Squad" Conflict (eFootball/Tekken)**

***The Scenario:*** **"Syntax FC" (eFootball Team) has 3 players: A, B, and C. *The Tournament:* It is a 1v1 Solo Tournament. *The Question:* Do we only allow 1 player? Or all 3?**

**The Smart Solution: "The Entrant Slot System" We treat the Organization like a Formula 1 Constructor. They can send multiple cars (players) to the race.**

* **Logic:**  
  * **The Tournament Organizer (TO) sets a rule: "Max Entries Per Org."**  
  * ***Scenario A (Strict):*** **TO sets Limit \= 1\. The Manager must pick their best player.**  
  * ***Scenario B (Open):*** **TO sets Limit \= Unlimited. The Manager can register Player A, Player B, and Player C.**  
* **Bracket Display:**  
  * **They appear as: "Syntax FC (Player A)", "Syntax FC (Player B)".**  
  * ***Constraint:*** **If they face each other in the bracket, it's a "Team Kill."**  
* **Points Calculation (The "Empire" Boost):**  
  * **If Player A wins (100 pts) and Player B comes 3rd (50 pts):**  
  * **Syntax FC (Team) earns 150 CP total.**  
  * **This incentivizes Orgs to sign *many* good solo players, not just one.**

#### **2\. Cross-Game Player Freedom**

***The Question:*** **Can I be in "Cloud9" for Valorant and "Fnatic" for eFootball?**

**The Solution: "Per-Game Contracts"**

* **Yes, absolutely.**  
* **The Check: When a User tries to join a team, the system runs this query:**  
  * **`Does User have an active Team for [Game_ID]?`**  
* **Example:**  
  * **Joining eFootball Team? System checks `My_eFootball_Teams`. Result: 0\. ALLOWED.**  
  * **Joining Valorant Team? System checks `My_Valorant_Teams`. Result: 1 (Already in Cloud9). BLOCKED.**

#### **3\. The "Ad-Hoc / Temporary" Team (Tournament App)**

***The Idea:*** **Creating a team *during* registration for outsiders.**

**The Plan:**

* **"Quick-Gen" Feature: In the Tournament Registration form, add a button: "Create Temporary Squad".**  
* **Data: User enters Name & Logo only. No dashboard, no wallet setup yet.**  
* **Status: The Team is created with a flag `is_temporary = True`.**  
* **Post-Tournament Upsell: After the tournament ends, send a notification:**  
  * ***"You placed 5th\! Want to make 'Dhaka Strikers' permanent? Click here to claim this team."***  
  * **If they click Yes \-\> Full Team setup.**  
  * **If No \-\> Team stays archived as "Guest Team" in history.**

