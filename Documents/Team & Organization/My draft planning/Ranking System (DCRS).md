# **👑 DeltaCrown Ranking System (DCRS) Master Plan**

## **1\. Core Philosophy**

Rankings on DeltaCrown are not just vanity metrics; they are **currency**.

* **For Teams:** High rank \= Saves money (Free entry) \+ Fame (Direct Invites).  
* **For Organizers:** High rank \= Reliable, high-quality participants.  
* **For Fans:** High rank \= The teams to watch.

**The Metric:** **Crown Points (CP)**.

(Distinct from "Skill Rating/MMR". MMR is for matchmaking; CP is for Legacy/Rankings).

---

## **2\. The Point System: Calculating "Crown Points" (CP)**

Points are awarded based on the **Prestige** of the tournament and the **Performance** of the team.

### **A. Tournament Tiers (The Multipliers)**

We classify every tournament on the platform into Tiers.

| Tier | Criteria | Example | Multiplier |
| :---- | :---- | :---- | :---- |
| **Tier S (Crown)** | Official DeltaCrown Majors, \>50k BDT Prize, LAN Finals. | *Delta Winter Championship* | **100x** |
| **Tier A (Elite)** | Verified Org tournaments, \>10k BDT Prize. | *GamerHub Monthly Cup* | **50x** |
| **Tier B (Challenger)** | Community cups, Weekly events. | *Weekend Skirmish* | **20x** |
| **Tier C (Grassroots)** | Daily scrims, small user-hosted events. | *Daily Scrim \#45* | **5x** |

### **B. Placement Points (The Base)**

* **1st Place:** 100 Points  
* **2nd Place:** 75 Points  
* **Top 4:** 50 Points  
* **Top 8:** 25 Points  
* **Participation:** 5 Points (Must play at least 1 match)

**Formula:** Base Points x Tier Multiplier \= **Total CP**

* *Example:* **Protocol V** wins a **Tier A** Cup.  
* Calculation: 100 (1st) x 50 (Tier A) \= **5,000 CP**.

---

## **3\. The "Direct Invite" Ecosystem (The Royalty Pass) 🚀**

This is the "Killer Feature" that makes teams addicted to your platform. We replace the traditional "pay-to-play" model with a "play-to-earn-access" model.

### **How it Works:**

1. **The Privilege:** Teams in the **Top 5% (Diamond Tier or above)** of their region/game are eligible for "Direct Invites."  
2. **The Benefit:**  
   * **Skip Qualifiers:** While other teams fight through 6 rounds of "Open Qualifiers," Invited Teams go straight to the Main Event / Group Stage.  
   * **Fee Waiver:** Invited teams pay **$0 Entry Fee**.  
3. **The Organizer Incentive:** Why would an organizer allow this?  
   * Because having "Protocol V" (Rank \#1) in their tournament brings **viewers** and **prestige**.  
   * DeltaCrown can subsidize the fee or give the Organizer "Platform Credits" for hosting top teams.

**User Journey (The Grind):**

* *New Team:* Pays entry fees, plays Open Qualifiers.  
* *Mid-Tier Team:* Grinds Tier B/C tournaments to earn CP.  
* *Top-Tier Team:* Gets an email: *"You have been Directly Invited to the Winter Major. Accept Invitation?"* (No fee, straight to main stage).

---

## **4\. The Visual Hierarchy: Tiers & Badges**

Gamers need status symbols. These badges appear on Team Profiles and Tournament Lobbies.

| Tier | CP Range | Badge Visual | Perk |
| :---- | :---- | :---- | :---- |
| **Unranked** | 0 \- 50 | Grey Circle | None |
| **Bronze** | 50 \- 500 | Rusty Shield | \- |
| **Silver** | 501 \- 1,500 | Polished Metal | \- |
| **Gold** | 1,501 \- 5,000 | Shining Gold | Verified Team Application |
| **Platinum** | 5,001 \- 15,000 | Teal Gem | Scrim Priority |
| **Diamond** | 15,001 \- 40,000 | Blue Refractive | **Direct Invites (Tier B)** |
| **Ascendant** | 40,001 \- 80,000 | Red/Crimson | **Direct Invites (Tier A)** |
| **CROWN** | Top 1% (Regional) | **Animated Purple Crown** | **Direct Invites (Tier S) \+ Homepage Feature** |

*   
  **Decay Rule:** To prevent "camping" the \#1 spot, teams lose **5% of their CP** every week if they are inactive. You must play to stay King.

---

## **5\. The "Organization Power Ranking"**

For Organizations like **SYNTAX**, we aggregate the success of all their squads.

### **The Metric: "Empire Score"**

Calculated by summing the CP of the Organization's **Top 3 Performing Teams** (weighted).

* *Why:* Incentivizes Orgs to maintain high quality across multiple games (e.g., a good Valorant team AND a good eFootball team).

**Visual:**

* **Leaderboard:** "Top Esports Organizations in Bangladesh"  
* **Profile Flair:** Organizations with high Empire Scores get a **Golden Border** on their profile page and better rates for sponsor integration.

---

## **6\. Seasonal Resets (The Loop)**

Esports operates in Seasons. Points cannot last forever.

* **Season Duration:** 4 Months (Winter, Summer, Autumn).  
* **The Soft Reset:** At the end of a season:  
  * Teams lose 50% of their CP.  
  * This "squishes" the leaderboard, allowing new teams to catch up while preserving the hierarchy.  
* **Hall of Fame:** The \#1 Team of the season gets permanently listed in the "History" tab (e.g., "Season 1 Champion: Protocol V").

---

## **7\. Modern "Hype" Features**

To make the ranking page exciting:

1. **"Giant Slayer" Bonus ⚔️**  
   * If a Silver Team beats a Diamond Team in a tournament match:  
   * Silver Team gets **\+500 Bonus CP**.  
   * Diamond Team loses **\-200 CP**.  
   * *Effect:* Creates viral moments and storylines.  
2. **"Hot Streak" 🔥**  
   * Win 3 official matches in a row? Get a 🔥 icon next to the team name.  
   * Earn **1.2x CP multiplier** while on a streak.  
3. **Regional Leaderboards**  
   * "Top 10 in Dhaka"  
   * "Top 10 in Chittagong"  
   * Allows casual teams to feel famous in their local city even if they aren't \#1 globally.

---

## **8\. Technical Implementation (Data Model)**

**TeamRanking Model:**

Python  
class TeamRanking(models.Model):  
    team \= models.OneToOneField(Team, related\_name='ranking')  
    current\_cp \= models.IntegerField(default=0)  
    season\_cp \= models.IntegerField(default=0)  \# Resets every season  
    tier \= models.CharField(choices=TIERS, default='UNRANKED')  
      
    \# Trend Tracking  
    rank\_change\_24h \= models.IntegerField(default=0) \# e.g., \+2 (Moved up 2 spots)  
    is\_hot\_streak \= models.BooleanField(default=False)  
      
    def update\_cp(self, points):  
        self.current\_cp \+= points  
        self.recalculate\_tier()

**OrganizationRanking Model:**

Python  
class OrganizationRanking(models.Model):  
    organization \= models.OneToOneField(Organization, related\_name='ranking')  
    empire\_score \= models.IntegerField(default=0)  
    global\_rank \= models.IntegerField()

### **Summary of Benefits**

1. **Direct Invite System:** Now a core progression mechanic. High rank \= Real value ($$$ savings).  
2. **Organization Value:** Organizations are ranked on their total "Empire Score," encouraging them to expand into more games.  
3. **Engagement:** Decay and Hot Streaks force teams to play regularly, not just sit on a high rank.

