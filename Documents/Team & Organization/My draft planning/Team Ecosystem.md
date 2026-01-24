# **Organization & Team Ecosystem**

## **1\. The Core Strategy Pivot**

We are shifting from a strict "1 User \= 1 Team" model to a professional "Esports Ecosystem" model.

* **Old Way:** Strict Game Passport requirement. 1 User \= 1 Team.  
* **New Way:** **Frictionless Creation.** Organizations (Empires) own Teams (Squads).  
* **Key Policy:** **No Game Passport required for Owners/Managers.** Passports are only for Players in active roster slots.

---

## **2\. The Hierarchy (Architecture)**

We introduce a tiered structure to mimic real-world esports.

### **Tier 1: The Organization (The Brand)**

* **Example:** `SYNTAX`  
* **Role:** The parent company. Holds finances, verification, and brand identity.  
* **Owner:** CEO (User).  
* **Permissions:** Can create teams, delete teams, manage master wallet, assign Managers.

### **Tier 2: The Teams (The Squads)**

* **Example:** `Protocol V` (Valorant Division)  
* **Role:** The unit competing in tournaments.  
* **Owner:** The **Organization** (SYNTAX).  
* **Manager:** An employee appointed by the Org (or the CEO themselves).  
* **Identity:** Unique logo & name (Sub-brand strategy).

### **Tier 3: The Independent Team (The Casuals)**

* **Example:** `Dhaka Killers` (Friends playing for fun)  
* **Role:** Standalone team.  
* **Owner:** The Creator (User).  
* **Permissions:** Absolute control.

---

## **3\. The "Fast-Track" Team Creation Flow (UX)**

*Goal: Maximum speed. Minimize friction. Get the team LIVE in under 30 seconds.*

### **Step 1: The Identity (Mandatory)**

* **Input 1: Team Name** (e.g., "Protocol V")  
* **Input 2: Game Selection** (Grid View: Valorant, eFootball, etc.)  
* **Input 3: Organization Link** (The "Fork in the Road")  
  * **Toggle:** `Link to an Organization? [OFF / ON]` (Default: OFF)  
  * **If OFF:** Creates **Independent Team**.  
  * **If ON:** Dropdown appears showing User's owned Orgs (e.g., SYNTAX).  
* **Logic Check (Backend):**  
  * *Independent:* Does User already own a team for this game? \-\> **Block**.  
  * *Org:* Does Org already have a team for this game? \-\> **Warn** (Suggest adding "Academy" suffix).

### **Step 2: The Base (Mandatory \- Smart Default)**

* **Input:** **Region/Country Base** (Identity, not Server).  
* **Smart Default:** Auto-detect User's IP (e.g., "Bangladesh") and pre-fill the dropdown.  
* **User Action:** Click "Next" (90% of cases) or change manually.

### **Step 3: The Setup (Skippable)**

* **Visuals:**  
  * **Logo/Banner:** Upload Box OR **"Skip for Later"** button.  
  * *Default:* If skipped, system generates a placeholder initials logo (e.g., "PV").  
* **Manager Assignment:**  
  * **Radio A:** "I will manage this team" (Default).  
  * **Radio B:** "Assign a Manager" (Input Email).  
* **Org Branding (Only if Org linked in Step 1):**  
  * **Checkbox:** `[ ] Use Organization Logo instead of custom logo?` (Default: Unchecked).

### **Step 4: The Launch (Post-Creation State)**

* **Action:** User clicks **"Create Team"**.  
* **Redirect:** Directly to **Team Dashboard**.  
* **Empty State Handling:**  
  * Show a **"Completion Bar"** at top: *"Profile Strength: 30%"*.  
  * **Primary CTA:** *"Your Roster is Empty. Start Scouting\!"*

---

## **4\. The Tournament Operations Center (TOC)**

*The "Mission Control" for getting a team tournament-ready.*

This is a dedicated tab in the Team Dashboard. It replaces the need for filling repetitive forms during tournament registration.

### **Module A: Roster Snapshot (Active Lineup)**

* **Action:** Manager drags & drops 5 players from the member list into "Active Lineup".  
* **Validation:** System checks if these 5 users have valid Game Passports.  
  * *Visual:* Valid players \= Green Light. Invalid \= Red Warning.  
* **Benefit:** One-click tournament registration uses this preset roster.

### **Module B: Logistics & Settings**

* **Preferred Server:** (e.g., Singapore/Mumbai). Used for TOC/Matchmaking data, not identity.  
* **Emergency Contact:** Pre-filled Discord ID/Phone for Tournament Admins.  
* **Payout Preference:**  
  * *Org Team:* Auto-set to Org Master Wallet.  
  * *Independent:* User Wallet.

---

## **5\. Features for Organizations**

### **A. Master Wallet & Smart Contracts**

* **Feature:** Automated Revenue Split.  
* **Action:** CEO sets contract rules (e.g., "80% to Players, 20% to Org").  
* **Result:** Tournament payouts are automatically divided by the system.

### **B. Brand Inheritance (The "Powered By" Badge)**

* **Visual:** Independent Team has no badge. Org Team displays a small **"Verified Org Badge"** (e.g., SYNTAX Logo) next to their team name/header.  
* **Benefit:** Team keeps unique identity (Protocol V logo) while gaining Org credibility.

### **C. The Trophy Room**

* **Feature:** Aggregate Achievements.  
* **Display:** Organization Profile shows total trophy count from ALL sub-teams (Valorant \+ eFootball \+ etc.).

### **D. Global Sponsor Slots**

* **Feature:** One-click sponsor management.  
* **Action:** Upload Sponsor Logo in Org Settings.  
* **Result:** Logo appears in the footer of **every** team page owned by the Org.

---

## **6\. Strategic Rules & Logic (Q\&A Summary)**

* **Can an Org have 2 teams for 1 game?**  
  * **YES.** (e.g., Main \+ Academy). System warns but allows.  
* **Can a User own 2 Independent teams for 1 game?**  
  * **NO.** Blocked to prevent spam.  
* **Region vs. Server?**  
  * **Region:** Team Identity (e.g., "Bangladesh") \-\> Set during Creation.  
  * **Server:** Game Setting (e.g., "Singapore") \-\> Set in TOC.  
* **How does an Org acquire an existing team?**  
  * **"Acquisition Protocol":** Org sends request \-\> Team Owner accepts \-\> Ownership transfers to Org \-\> Owner becomes Manager.

