# **📜 Proposal: The DeltaCrown "Command Center" Architecture**

**Part 1: The Philosophy & The Registration Engine**

## **I. The Concept: "The Digital War Room"**

**Imagine a physical sports stadium. There are two distinct worlds existing simultaneously.**

**First, there is the Lobby (The Player’s View). This is the locker room. It is where athletes gather, check their gear, look at the schedule, feel the nerves, and wait for the signal to march onto the field. It is a place of anticipation and preparation. Access to this room is granted immediately upon registration—players don't need to hunt for it; it lives right in their personal dashboard.**

**Second, high above the stands, is the Command Center (The Organizer’s View). This is the control tower. Here, the directors see everything. They don't just watch; they control the rules, the gates, and the flow of money. They are the "Gods" of the arena.**

**Our proposal completely separates these two views. We are not just building a "page" for the organizer; we are building a living workspace—an "Always-On" dashboard that empowers one person to manage 30 teams with the efficiency of a full staff.**

## **II. The Backstory: Why We Need This**

**In the current landscape, organizing a tournament is a fragmented process. Organizers wrestle with inflexible forms, chaotic payment tracking via WhatsApp, and confused players asking, "Am I registered?"**

**DeltaCrown’s mission is to professionalize this ecosystem. However, we face specific realities:**

1. **No Direct Game APIs: We rely on human verification for results.**  
2. **Diverse Payments: We must support bKash, Nagad, Rocket, and Banks with varying proof requirements.**  
3. **Storage Costs: Mandatory screenshots for every user are expensive and time-consuming; text-based Transaction IDs are faster and more cost-effective.**

**Therefore, the Command Center must be a "Force Multiplier." It must provide the organizer with granular control over how they verify data, allowing them to toggle the strictness (Screenshots vs. IDs) based on their needs, while keeping the user informed via smart notifications.**

## **III. The Idea: Phase 1 — The Registration Engine**

**The Command Center is active the moment the tournament is created. It acts as the engine room for the entire Registration Period.**

### **A. The Organizer’s Command Center (State: REG\_OPEN)**

**In this phase, the organizer serves as a Gatekeeper. Their dashboard focuses on Configuration, Verification, and Support.**

**1\. "Hot Editing" & Payment Configuration (The Control Panel)**

**Organizers need flexibility even after a tournament goes live. The "Settings" tab allows "Hot Edits" to critical logistics:**

* **Payment Methods: The organizer can toggle active gateways. They can enable "bKash" and "Nagad" while keeping "Bank Transfer" off. They can update the destination wallet number instantly (e.g., "Send to 017..." changed to "018...").**  
* **Proof Customization (Granular Control): To optimize verification speed and storage costs, the organizer configures *what* the user must submit:**  
  * **Transaction ID (TrxID): *Mandatory / Optional*. (Best for quick text search).**  
  * **Sender Mobile Number: *Mandatory / Optional*.**  
  * **Screenshot Proof: *Mandatory / Optional / Disabled*. (Disabled \= saves server storage; useful for smaller/trusted events).**  
* **Dynamic Rule Updates: If a rule is unclear, the organizer uploads a revised PDF or updates the description without taking the tournament offline.**

**2\. The Live "Incoming" Stream (Verification Deck)**

**Instead of a static list, the Organizer sees a "Kanban Board" of teams:**

* **The "One-Glance" Card: Clicking a pending team (e.g., "Dhaka Defenders") opens a detailed modal:**  
  * **Roster Check: Shows all 5 player IDs. System auto-flags regex errors (e.g., "Invalid Riot ID format").**  
  * **Financial Proof: Displays the user's input (TrxID: 8H7...) next to the Organizer's expected fee. If "Screenshot" was enabled, the image loads here.**  
  * **Action Buttons: Large "APPROVE" (Green) or "REQUEST FIX" (Yellow).**  
* **The "Request Fix" Workflow: If the TrxID is valid but the Roster is incomplete, the Organizer clicks "Request Fix" \-\> selects "Roster Issue." The team is *not* rejected; they are pushed back to the user with a specific "Fix It" task.**

**3\. Support & Inquiry Hub**

**A dedicated "Help Desk" section within the Command Center.**

* **Pre-Tournament Tickets: Teams can submit inquiries ("Payment sent but not updated," "Can we change roster?").**  
* **Direct Context: When an Organizer opens a ticket, they see the team's registration status side by side, allowing them to resolve the issue instantly.**

### **B. The User’s Experience (Lobby & Navigation)**

**1\. Smart Navigation (The "Compass")**

**Users should never get lost.**

* **Public Detail Page: The main CTA button is dynamic.**  
  * ***Visitor:*** **"Register Now"**  
  * ***Registered (Pending):*** **"Check Status" (Links to Lobby)**  
  * ***Registered (Approved):*** **"Enter Lobby"**  
* **User Dashboard (/dashboard/): A "My Active Tournaments" card appears immediately after registration submission. Clicking it bypasses the Detail Page and drops them directly into the Tournament Lobby.**

**2\. The Lobby "Waiting Room" (State: REG\_OPEN)**

**Upon registering, the user enters the Lobby. Since the bracket isn't ready, this view manages expectations.**

* **Status Tracker: A visual stepper: Submitted \-\> In Review \-\> Approved.**  
* **Correction Mode: If the Organizer requests a correction (e.g., "TrxID invalid"), the Lobby transforms into a "Correction Form" that highlights exactly what needs to be fixed.**  
* **Support Channel: A "Contact Organizer" button allows the user to open a support ticket directly from the Lobby if their verification is stuck.**

---

## **IV. Notification Strategy (The Nervous System)**

**To keep users engaged and reduce anxiety, we will implement a trigger-based notification system (Push \+ In-App \+ Email).**

| Trigger Event | Audience | Notification Content (Short) | Timing |
| :---- | :---- | :---- | :---- |
| **Registration Submitted** | **User (Captain)** | **"Registration received\! We are verifying your details."** | **Instant** |
| **Payment Config Change** | **Pending Users** | **"Update: Organizer changed payment instructions. Check details."** | **Instant (If relevant)** |
| **Request Fix** | **User (Captain)** | **"⚠️ Action Required: Please fix your Transaction ID to proceed."** | **Instant** |
| **Approved/Verified** | **All Team Members** | **"✅ You're in\! Dhaka Defenders is officially registered."** | **Instant** |
| **Registration Deadline** | **"Saved" Users** | **"⏳ 2 Hours Left\! Registration closes soon."** | **\-2 Hours** |
| **New Support Reply** | **User** | **"Organizer replied to your inquiry."** | **Instant** |

---

## **V. Optional "High-Impact" Features (Must-Haves?)**

**These features are not strictly necessary for the MVP, but they would significantly elevate the platform's professional feel (Marked with ⭐ for High Impact).**

1. **⭐ Waitlist Logic:**  
   * ***Concept:*** **If 30/30 slots are full, allow teams to register for a "Waitlist."**  
   * ***Feature:*** **If a confirmed team is disqualified or fails payment, the Organizer can "Promote" a waitlisted team with one click.**  
2. **Audit Logs:**  
   * ***Concept:*** **For Organizers with multiple staff (Admins/Mods).**  
   * ***Feature:*** **Record who approved a team. "Admin X approved Dhaka Defenders at 14:00." Essential for preventing corruption/favoritism.**

---

**End of Part 1\.**

**Part 2: The Transparency Engine & The Flexible War Room**

*(Continuing from where Part 1 ended: Registration has just closed.)*

## **I. The Backstory: The "Black Box" Problem**

In traditional esports platforms, the period between "Registration Closed" and "Tournament Start" is a black box. Players register, wait in the dark, and suddenly wake up to find themselves in a "Group of Death" with the strongest teams. Naturally, they suspect corruption or favoritism.

Furthermore, rigid platforms fail because real life is messy. Teams often need to reschedule matches due to power outages or religious observances, such as prayer times. Organizers often prefer receiving screenshots on Discord rather than forcing users to log in to a website.

DeltaCrown will solve this by introducing **Transparency** (via Live Draws) and **Extreme Flexibility** (via Discord/WhatsApp integrations and Manual Overrides).

---

## **II. The Idea: Phase 2 — The Processing Phase (Transparency Mode)**

The "Command Center" now shifts from verifying users to **building the Stage**. This phase is all about proving fairness.

### **A. The Organizer’s View (The "Architect" Mode)**

**1\. The "Live Draw" Studio (Corruption Killer)**

* **The Problem:** Users complain, "Why did you put us in Group A against the pro team? It's rigged\!"  
* **The Solution:** An optional **"Live Draw Mode"** toggle.  
  * **Manual/Private Seeding:** The classic drag-and-drop method for quick setup.  
  * **Live Broadcast Seeding:** The Organizer sets a time (e.g., "Draw starts at 8:00 PM").  
    * *The Interface:* The Organizer clicks "Draw Next Team." The system randomly picks a team and animates them into a Group slot.  
    * *Streaming:* The Organizer can screen-share this view to Discord/Facebook, turning the administrative task into a content event.

2\. Waitlist & Roster Finalization

Before the draw, the Organizer performs the final cleanup.

* **Waitlist Logic:** If "Team Alpha" is disqualified, the system prompts: *"Promote 'Team Beta' (Waitlist \#1)?"* This ensures the bracket is full before generation.

### **B. The User’s Experience (Lobby Transition)**

* **The "Draw" Event:** Instead of a static "Processing" screen, the Lobby displays a countdown: *"Group Draw begins in 02:30:00."*  
* **Real-Time Updates:** If the Organizer is using "Live Draw Mode," users watching the Lobby page see the brackets fill up in real-time without needing to refresh.

#### **Phase 2.5 — The "Check-In" Window (The Safety Net)**

**A. The Concept: The "Attendance Call."** Once the bracket is published, we cannot simply assume everyone will show up. If "Team Alpha" registered two weeks ago but forgot to play today, their opponent will be stuck waiting in an empty lobby. The Check-In phase serves as a mandatory safety net, filtering out "ghost" teams before the first match begins.

**B. The User’s Experience (The "Ready" Button)**

* **The Countdown:** 60 minutes before the tournament starts, a massive **"CHECK-IN NOW"** button activates in the Lobby.  
* **The Action:** The Captain clicks it. The status changes from "Registered" to **"✅ Checked In & Ready."**  
* **The Cutoff:** The button locks and disappears exactly 15 minutes before the start time.

**C. The Organizer’s Command Center (The "Attendance Grid")** The Organizer sees a dedicated **"Check-In Monitor"** panel:

1. **Live Status:** A real-time grid of all 30 teams.  
   * **Green:** Checked In.  
   * **Grey:** Pending.  
2. **The "No-Show" Protocol:**  
   * At the cutoff time (e.g., \-15 mins to start), the system highlights the teams that are still Grey.  
   * **Auto-Action:** The Organizer clicks **"Finalize Attendance."**  
   * **Smart Logic:** The system *automatically* disqualifies teams that fail to show up. It then auto-fills the empty slots by promoting teams from the **Waitlist** or assigning "Walkover" wins to their opponents.  
3. **Manual Override:** If a team member calls on WhatsApp and says, "My internet is slow, mark me present\!", the Organizer can manually force-check them in from this panel.

---

## **III. The Idea: Phase 3 — The Live Event (Flexibility & Comms)**

The tournament is LIVE. The Command Center becomes a **Monitoring Grid**. We now introduce the flexible "Hybrid Communication" model.

### **A. The "Hybrid" Communication Hub**

We recognize that Discord/WhatsApp are faster than any web chat. We shouldn't fight them; we should integrate them.

1\. Organizer Setup (External Links)

In the Command Center settings, the Organizer can input:

* **Official Discord Server:** (e.g., "Join for Voice Channels & Support").  
* **WhatsApp Group:** (e.g., "Captains Only Group").  
* **Effect:** These appear as prominent, specialized buttons in the User's Lobby: *"Join Discord for Voice"* or *"Chat with Admin on WhatsApp."*

**2\. The "Manual Result" Workflow (The Flexibility Factor)**

* **Scenario:** A user sends the win screenshot to the Organizer via WhatsApp instead of the website.  
* **Old Way:** The Organizer tells the user, "Go upload it on the site." (User gets annoyed).  
* **DeltaCrown Way:** The Organizer opens the Command Center, finds the match, and uses the **"Admin Override"** input.  
  * *Action:* Organizer enters the score and uploads the screenshot *on behalf of the user*.  
  * *Result:* The match updates instantly. The system logs: *"Result uploaded by Admin (Source: External)."*

***3\. Broadcast & Stream Integration***

* ***The Feature:** A dedicated input field in the Command Center for "Live Stream URL" (YouTube/Twitch/Facebook).*  
* ***The Effect:** When the Organizer pastes a link (e.g., `youtube.com/live/...`), it instantly embeds the video player at the top of the **User’s Lobby** and the **Public Detail Page**.*  
* ***Value:** This centralizes the audience. Players don't have to leave the platform to watch the official cast or the "Live Draw".*

### **B. The User’s Match Room (Flexibility & Control)**

**1\. Reschedule Requests (The "Life Happens" Button)**

* **The Feature:** A "Request Reschedule" button inside the Match Room.  
* **Workflow:**  
  1. **Team A** proposes: *"Can we play at 9:30 PM instead of 9:00 PM?"*  
  2. **Team B** receives the request.  
  3. **If Team B Accepts:** The system updates the match time automatically (or flags it for Admin Approval, based on settings).  
  4. **If Team B Declines:** The original time stands.  
* *Note:* Organizers can disable this feature for strict tournaments.

**2\. Submission Rules & Deadlines**

* **The Timer:** A countdown appears after the scheduled end time: *"Result Submission Deadline: 15:00 minutes."*  
* **The Rule:** If no result is submitted by the deadline, the match is flagged **RED** in the Organizer’s dashboard for immediate attention.

### **C. The Organizer’s Live Dashboard (The "Grid")**

1\. The Match Matrix (Enhanced)

The Organizer sees a bird's-eye view of all matches with status indicators:

* **Blue:** Scheduled / In Progress.  
* **Orange:** Reschedule Requested (Needs Admin approval).  
* **Green:** Completed & Verified.  
* **Red:** **Dispute / Deadline Missed.**

**2\. Dispute Resolution & Support**

* **Context-Aware Support:** When a user clicks "Help" in the lobby, they can choose *"Issue with Match \#12"* or *"General Inquiry."*  
* **The Dispute Room:** If a dispute is filed, it creates a dedicated channel in the Command Center. The Organizer can:  
  * Chat with both captains.  
  * View evidence.  
  * **Finalize Result:** Force a win for one side to keep the tournament moving.

---

## **IV. The Idea: Phase 4 — Completion & Payouts**

* **The "Podium" View:** The Lobby creates a celebratory moment for the winners.  
* **KYC Trigger:** For big prizes, the system halts the payout until Identity Verification is complete.  
* **Payout Disbursement:** Once verified, the Organizer clicks "Disburse," and the system handles the wallet transfers or records the manual bank transfer details.

---

## **V. High-Impact "Must-Haves" Summary**

These are the distinguishing features that make DeltaCrown a "Modern Platform" (Marked ⭐).

1. **⭐ Live Draw System:**  
   * *Value:* Eliminates "corruption" claims. Makes the seeding process transparent and entertaining.  
2. **⭐ "Admin Override" for Results:**  
   * *Value:* Allows the Organizer to accept results via WhatsApp/Discord and input them manually, removing friction for users.  
3. **⭐ Match Rescheduling System:**  
   * *Value:* Reduces forfeits by allowing teams to agree on slight time shifts (e.g., for prayer or technical issues).  
4. **⭐ Waitlist Logic:**  
   * *Value:* Ensures 100% participation capacity by auto-promoting teams when spots open up.

---

## **VI. Notification Strategy (Comprehensive)**

| Trigger Event | Audience | Notification Content (Short) | Timing |
| :---- | :---- | :---- | :---- |
| **Draw Scheduled** | All Users | "🎲 Live Group Draw starts in 30 mins\!" | \-30 Mins |
| **Reschedule Requested** | Opponent Captain | "📅 Opponent requested time change to 9:30 PM. Accept?" | Instant |
| **Reschedule Approved** | Both Teams | "✅ Match rescheduled to 9:30 PM." | Instant |
| **Deadline Warning** | Active Match Captains | "⏳ Match ended? Submit results within 10 mins." | Post-Match |
| **Admin Override** | Both Teams | "👨‍⚖️ Admin manually updated match result. Check lobby." | Instant |
| **Dispute Filed** | Organizer | "🚨 Dispute in Match \#4. Action required." | Instant |
| **Prize Unlocked** | Winner | "🏆 Congrats\! Complete KYC to claim your prize." | Post-Event |
| **Check-In Open** | All Captains | "🔔 Check-in is OPEN\! Confirm attendance now." | \-60 Mins |
| **Check-In Warning** | Pending Teams | "⚠️ 15 Mins left to Check-in or be DQ'd." | \-15 Mins |
| **Waitlist Promo** | Waitlisted Team | "🎉 Spot Open\! You are now in the Main Bracket." | Instant |

---

Summary:

This updated Part 2 focuses on trust and flexibility. By introducing the Live Draw, we address the trust/corruption issues. By adding Discord/WhatsApp integration, as well as rescheduling, we acknowledge the reality of grassroots esports—that flexibility is key. The Command Center is no longer just a verification tool; it is a broadcast studio, a communication hub, and a referee desk all in one.

