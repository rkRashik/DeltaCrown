As I want a **"hassle-free, completely clean project. I have two option.** 

**❌ Option 1: Delete Everything (The Trap)**

* **The Reality: This is NOT hassle-free. It is "Maximum Hassle."**  
* **What will happen: You delete the folder. You run the server. It crashes. You fix one error in `tournaments`. It crashes again in `user_profile`. You fix that. It crashes in `notifications`. You will spend 2 weeks just fighting error messages before you write a single line of new code.**  
* **Verdict: Do not do this unless you plan to delete `tournaments`, `economy`, and `user_profile` apps as well.**

**✅ Option 2: Parallel Build (The "Strangler Fig" Pattern)**

* **The Reality: This is the only professional way to handle a "gigantic" platform refactor.**  
* **Why it's cleaner: You build `apps/organizations` in a vacuum. It is 100% clean, modern code with no legacy baggage. You verify it works perfectly.**  
* **The Switch: Once the new app is ready, you change the connections (imports) one by one.**  
* **Verdict: Choose Option 2\. It keeps the platform running while you build the perfect future.**


**I prefer option 2\.** 

**To make Option 2 work "cleanly," we need to add 3 Specific Plans to your roadmap right now.**

#### **1\. The "Data Migration" Strategy Plan**

* **The Problem: You have existing teams (e.g., "Protocol V") owned by users. You are moving to a world where "Syntax" (Organization) owns "Protocol V".**  
* **The Plan Need: We need a script that:**  
  1. **Takes every existing Independent Team.**  
  2. **Creates a "Hidden" Organization for them (so the data fits the new model).**  
  3. **Moves the roster to the new table.**  
  4. **Updates the Tournament Registration `team_id` to point to the new ID.**

#### **2\. The "URL Redirect" Plan (The 50+ Hardcoded Links)**

* **The Problem: The audit found 50+ places linking to `/teams/team-slug/`. If you delete the old app, all email notifications and profile links will 404\.**  
* **The Plan Need: We need a Routing Shim.**  
  * ***New Logic:*** **When a user visits `/teams/protocol-v/`, the system checks: "Is this a legacy team? Redirect to old view. Is it a new Org team? Redirect to `/orgs/syntax/teams/protocol-v/`."**

#### **3\. The "Service Layer" Abstraction**

* **The Problem: The audit shows `tournaments` is importing `Team` directly. This creates tight coupling.**  
* **The Plan Need: Before we finish the new app, we should write a `TeamService` interface.**  
  * ***Goal:*** **The Tournament app should ask `TeamService.get_team(id)`, and it shouldn't care if the data comes from the old app or the new `organizations` app.**

**We have the "Functional Plan" (Features), but we lack the "Bridge Plan" (The Compatibility Layer).**

**If we build the new app without planning exactly how the Tournament App will "talk" to it (without knowing it's a new app), we will create a mess.**

### **The Final Missing Piece: The "Unified Service Layer" Protocol**

**We need to design a "TeamInterface". This is a set of standard functions that the rest of your platform (Tournaments, Economy) will call.**

**Why we need this: Currently, your Tournament app probably does this: `from apps.teams.models import Team` (Direct Database Access). This is bad because if you change the database, the Tournament app breaks.**

**The New Plan: The Tournament app should do this: `TeamService.get_team_status(team_id)` (Asking a "Manager").**

---

### **Action: Add this "Service Layer Plan" to our roadmap**

**I propose we define these 5 Standard Methods before we start coding. This ensures that no matter how complex the new "Organization" logic is, the Tournament app stays happy.**

1. **`get_team_wallet(team_id)`**  
   * ***Old Logic:*** **Returns `team.owner.wallet`.**  
   * ***New Logic:*** **Returns `team.organization.master_wallet` (if Org) OR `team.owner.wallet` (if Independent).**  
   * ***Benefit:*** **The Economy app doesn't need to know *who* owns the wallet. It just asks "Where do I send the money?" and the Service tells it.**  
2. **`validate_roster(team_id, tournament_id)`**  
   * ***Old Logic:*** **Checks if 5 players exist.**  
   * ***New Logic:*** **Checks if "Active Lineup" exists AND passes the new "Passport Check".**  
   * ***Benefit:*** **Centralizes all your complex rules (1v1, 5v5, Org Passports) in one place.**  
3. **`get_team_identity(team_id)`**  
   * ***Old Logic:*** **Returns `name`, `logo`.**  
   * ***New Logic:*** **Checks "Brand Inheritance." Returns `org.logo` (if enforced) OR `team.logo` (if custom).**  
   * ***Benefit:*** **Tournaments always display the correct logo without writing `if/else` logic in every template.**  
4. **`get_authorized_managers(team_id)`**  
   * ***Old Logic:*** **Returns `[owner]`.**  
   * ***New Logic:*** **Returns `[org_ceo, team_manager, team_coach]`.**  
   * ***Benefit:*** **Solves the permission matrix. Any user in this list can edit the Tournament settings.**  
5. **`create_temporary_team(name, logo, game_id)`**  
   * ***New Function:*** **Handles the "Guest Team" creation for the Tournament app instantly.**

