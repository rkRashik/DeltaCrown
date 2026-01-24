# **🛡️ DeltaCrown Team Management Master Plan**

## **1\. The Core Philosophy**

**"Managers Manage, Players Play."**

* **Old System:** Everyone needed a Game ID.  
* **New System:**  
  * **Management Roles (Owner, Manager, Coach, Analyst):** Do **NOT** need a Game Passport. They run the business.  
  * **Combat Roles (Player, Substitute, IGL):** **MUST** have a valid Game Passport (Game ID) to occupy a slot.

---

## **2\. The Team Dashboard (The Command Center)**

When a Manager opens their team page, they see the **Dashboard Hub** (not just a public profile).

### **Layout of the Hub**

1. **Status Bar (Top):**  
   * **Team Health:** "Ready for Tournament" (Green) or "Incomplete Roster" (Red).  
   * **Wallet Balance:** "BDT 5,000" (or "Managed by Org").  
   * **Next Match:** Countdown timer.  
2. **Quick Actions:**  
   * \+ Invite Member  
   * Edit Team Identity  
   * Tournament Ops (Link to TOC).

---

## **3\. Roster Management (The "Gatekeeper" Logic)**

This is the most critical part of the system. We separate the "Human" from the "Game ID".

### **A. The Invitation Flow**

**Scenario:** The Manager wants to add a new member.

1. **Manager Action:** Clicks \+ Invite Member.  
2. **Input:** Enters Email or Username (e.g., "ShooterX").  
3. **Role Selection (Crucial Step):**  
   * The Manager **MUST** select the intended role for this invite:  
   * \[ \] Player (Combat Role)  
   * \[ \] Coach / Staff (Non-Combat Role)  
4. **System Logic:**  
   * **If Role \= Coach/Staff:** Invite sent immediately. No checks.  
   * **If Role \= Player:** System checks User's profile *silently*.  
     * *If User has Valorant ID:* Invite sent.  
     * *If User has NO Valorant ID:* Warning to Manager: *"ShooterX does not have a Valorant ID. They will be prompted to add one before accepting."*

### **B. The Acceptance Flow (User Side)**

1. **User Notification:** "Protocol V invited you to join as a **Player**."  
2. **User Action:** Clicks "Accept".  
3. **The Gatekeeper Check:**  
   * **Case A (Has Passport):** Success\! Added to roster.  
   * **Case B (No Passport):**  
     * **Popup:** *"To join as a Player, you must link your Valorant Riot ID."*  
     * **Form:** \[ Enter Riot ID \] \-\> \[ Verify \] \-\> \[ Join Team \].  
   * *Result:* We capture the Game ID *at the moment of need*.

---

## **4\. Roles & Permissions Matrix**

We define exactly who can do what.

| Feature | 👑 Owner / CEO | 👔 Manager | 🧢 Coach | 🔫 Player |
| :---- | :---- | :---- | :---- | :---- |
| **Edit Team Name/Logo** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Delete Team** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Invite/Kick Members** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Register for Tournament** | ✅ Yes | ✅ Yes | ❌ No | ❌ No |
| **Manage Wallet (Withdraw)** | ✅ Yes | ❌ No | ❌ No | ❌ No |
| **Edit TOC (Roster Setup)** | ✅ Yes | ✅ Yes | ✅ Yes | ❌ No |
| **View Scrim Schedule** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Game Passport Required?** | ❌ **NO** | ❌ **NO** | ❌ **NO** | ✅ **YES** |

---

## **5\. Financial Management (The Wallet)**

This differs based on whether the team is **Independent** or **Organization-Owned**.

### **Scenario A: Independent Team**

* **Wallet Access:** Only the **Owner** (Creator) can withdraw.  
* **Income Source:** Tournament Winnings.  
* **Withdrawal:**  
  * Owner clicks "Withdraw".  
  * Selects Method: Bkash / Nagad / Bank.  
  * *Security:* OTP sent to Owner's phone/email.

### **Scenario B: Organization Team (e.g., Protocol V)**

* **Wallet Access:** Locked for the Team Manager.  
* **Income Source:** Winnings go to **Org Master Wallet**.  
* **The "Budget" Feature:**  
  * The Org CEO can allocate a **"Petty Cash"** budget to the Team Manager (e.g., 5,000 BDT for scrim fees).  
  * The Manager *can* spend this specific budget but cannot touch the prize money.

---

## **6\. Advanced Features**

### **A. The "Bench" System (Substitutes)**

* **Active Roster:** Limited to 5 Slots (for 5v5 games).  
* **The Bench:** Unlimited slots.  
* **Action:** Drag-and-drop a player from "Active" to "Bench".  
* *Why:* Keeps the main roster clean for tournament registrations while allowing a large community of subs.

### **B. Activity Log (The "Black Box")**

* **Purpose:** Security and dispute resolution.  
* **Logs:**  
  * *"Manager X kicked Player Y"* (Timestamped).  
  * *"Owner changed Team Name to 'Delta Force'"*.  
  * *"Wallet withdrawal of 500 BDT to 017..."*.  
* *Benefit:* If a Manager goes rogue, the Owner can see exactly what happened and revert changes.

### **C. Transfer Market Status**

* **Setting:** A toggle in the dashboard: \[ \] Open for Offers.  
* **Effect:** If ON, other Organizations can send "Acquisition Requests" (Buyout offers) to the Team Owner.  
* **If OFF:** The team is listed as "Locked / Not for Sale".

---

## **7\. Developer Implementation Checklist**

1. **Update TeamMember Model:**  
   * Add field: role (Choices: OWNER, MANAGER, COACH, PLAYER, SUB).  
   * Add field: is\_active (Boolean).  
2. **Invite Logic:**  
   * Create TeamInvite model with target\_role field.  
   * Implement "Passport Check" middleware on the "Accept Invite" endpoint.  
3. **Permissions Decorators:**  
   * Create @requires\_manager and @requires\_owner decorators for your Django views to secure the API.  
4. **Audit Log:**  
   * Implement a simple TeamActivityLog model to record key actions.

This plan ensures your team management is secure, professional, and flexible enough for both friends and corporations.

