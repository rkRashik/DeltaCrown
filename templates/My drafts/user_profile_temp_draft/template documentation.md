# **📘 DeltaCrown User Profile – Technical Documentation**

---

## **1\. Executive Summary**

The **Aurora Zenith** profile is designed to be more than a static information page; it is a dynamic **"Command Center"** for esports athletes.

The design philosophy moves away from traditional "social media" layouts into a **"High-Tech HUD" (Heads-Up Display)** aesthetic. It utilizes "Deep Space" dark modes, neon aurora gradients, and holographic glassmorphism to create a premium, immersive experience that appeals to the modern gaming demographic while maintaining the elegance required for high-net-worth investors or recruiters.

---

## **2\. Design System Specifications**

This template operates on a strict visual framework defined in the Tailwind configuration.

### **2.1 Color Palette (The "Aurora" Theme)**

* **Background (`z-bg`):** `#030014` (Deep Space Black) \- The canvas.  
* **Primary Accent (`z-cyan`):** `#00F0FF` (Electric Cyan) \- Used for primary actions, verified badges, and tech accents.  
* **Secondary Accent (`z-purple`):** `#7B2CBF` (Royal Purple) \- Used for "Rare" items and creative elements.  
* **Economy/Premium (`z-gold`):** `#FFD60A` (Trophy Gold) \- Strictly reserved for money (DeltaCoins), wins, and premium status.  
* **Live Status (`z-pink/z-green`):** Used to indicate real-time activity.

### **2.2 Typography**

* **Headings:** *Space Grotesk* – A sci-fi inspired sans-serif that conveys a futuristic, "esports tournament" vibe.  
* **UI/Body:** *Inter* – A clean, highly readable font for stats, bios, and buttons.

### **2.3 Visual Physics**

* **Glassmorphism:** Elements mimic frosted glass (`backdrop-blur-xl`) with prismatic borders that glow on hover.  
* **Micro-Interactions:** Elements do not just "sit" there; they float (`animate-float`), pulse (`animate-pulse-slow`), or glow when interacted with.

---

## **3\. Component Analysis: The Hero Section**

*Location: Top of the page (Header).*

The Hero Section is the user's digital business card. It is the first thing a visitor sees and must instantly communicate **Status, Skill, and Identity**.

### **3.1 The "Living" Background**

* **Description:** A layered composition featuring a high-quality game wallpaper overlaid with `gradient-to-t` (bottom fade) and `gradient-to-r` (side fade).  
* **Visual Tech:** A "Mesh Gradient" (`bg-mesh-dark`) sits on top to create the moving "Aurora" effect behind the text.  
* **Behavioral Logic:**  
  * **Owner:** Sees a floating **"Change Cover"** button in the top-right corner to upload a new banner.  
  * **Spectator/Friend:** Sees only the image and effects.

### **3.2 The Holographic Avatar**

* **Description:** The profile picture is framed by a spinning RGB ring (`.holo-ring`) and a static inner glow.  
* **Visual Tech:** CSS `conic-gradient` animation rotates a color wheel behind the image to create a "breathing" neon rim.  
* **Behavioral Logic:**  
  * **Owner:** Hovering over the avatar reveals a **"Camera Icon"** and **"UPDATE"** overlay to upload a new photo.  
  * **Spectator:** Hovering triggers a slight zoom/scale effect but no edit options.  
  * **Verified User:** If `user.is_verified_pro` is true, the "Verified Pro" badge appears floating below the chin.

### **3.3 The Identity Block (Name & Bio)**

* **Description:** Contains the Display Name, Gamertag, Level Badge, and Bio.  
* **Visual Tech:** The name uses `tracking-tighter` for a cinematic movie-poster look. The Gamertag is highlighted with a gradient text clip.  
* **Behavioral Logic:**  
  * **Owner:** A small "Pen/Edit" icon appears next to the name and bio on hover, allowing quick inline editing.  
  * **Spectator:** Can click the **"Copy UID"** button to copy the user's ID for game invites.

### **3.4 The "Stats HUD" (Followers/Following)**

* **Description:** A glass panel displaying Followers, Following, and Enrolled Teams count.  
* **Purpose:** Social proof. High numbers indicate a popular or skilled player.  
* **Behavioral Logic:**  
  * **All Users:** Clicking "Followers" opens a modal list of users.  
  * **Social Icons:** Links to Discord/Twitter/YouTube.  
  * **Owner:** Sees a **"+" (Plus)** button at the end of the social row to add new social links.

### **3.5 The Action Dock (Buttons)**

*Location: Bottom Right of Hero.*

This is the primary interaction point for visitors. The buttons change dynamically based on who is viewing.

#### **Scenario A: The Spectator (Public View)**

* **Primary Button:** **"FOLLOW"** (Cyan Border). Adds the user to their feed.  
* **Secondary Button:** **"MESSAGE"** (if DM is open) or "GIFT" (Send DeltaCoins).  
* **Tertiary Button:** **"..."** (Report/Block).

#### **Scenario B: The Recruiter (Team Manager)**

* **Primary Button:** **"SCOUT PLAYER"** (White/Gold).  
  * *Function:* Adds the player to a "Shortlist" and opens a contract negotiation modal.  
* **Secondary Button:** **"VIEW STATS"**.

#### **Scenario C: The Owner (You)**

* **Primary Button:** **"EDIT PROFILE"**.  
* **Secondary Button:** **"SHARE PROFILE"** (Generates a link).  
* **Hidden:** "Follow" and "Scout" buttons are hidden.

---

## **4\. Component Analysis: Navigation Strip (Sticky Tabs)**

*Location: Below Hero, sticks to top on scroll.*

* **Description:** A horizontal scrolling menu (`overflow-x-auto`) that acts as the controller for the dynamic content below.  
* **Visual Tech:** Active tabs have a glowing neon underline (`box-shadow: 0 0 10px #00F0FF`).  
* **Logic:**  
  * **"Economy/Wallet" Tab:** This tab is highlighted in **Gold** (`text-z-gold`) to separate financial data from social data.  
  * **Mobile Behavior:** On mobile devices, this turns into a swipeable strip.  
  * **Notification Badges:** If there are new posts, a small badge (e.g., "12") appears next to the "Posts" tab.

## **5\. Component Analysis: Left Sidebar (Identity & Specs)**

*Location: Left Column (Desktop) / Top of Stack (Mobile).*

This column serves as the user's permanent record—data that rarely changes but is crucial for verification.

### **5.1 Personal Info Module (.z-card)**

* **Description:** A glass panel displaying Real Name, Nationality, Location, and Join Date.  
* **Privacy Logic:**  
  * **Public View:** Shows only what the user has set to "Public" (e.g., just Nationality).  
  * **Friend View:** Shows Location and Real Name.  
  * **Owner View:** Shows everything \+ an **"Edit Pen"** icon. Includes a "Visibility" toggle badge at the top right.

### **5.2 Game Passports (Linked IDs)**

* **Description:** A list of connected game accounts (Valorant, PUBG, CS2).  
* **Visual Tech:** Uses a "Slot Machine" style layout. The "Main" game is highlighted with a border-l-z-cyan accent.  
* **Behavior:**  
  * **Spectator:** Can view Ranks (e.g., "Immortal 3") and copy the ID.  
  * **Owner:** Sees a **"+ Link New ID"** button at the bottom to connect more games via OAuth or manual entry.

### **5.3 Gear Setup (Loadout)**

* **Description:** A list of hardware peripherals (Mouse, Keyboard, Headset) used by the player.  
* **Commercial Logic:** This section is designed for **Affiliate Marketing**.  
  * **Spectator:** Clicking an item (e.g., "Logitech G Pro") redirects to the **DeltaCrown Store** product page.  
  * **Owner:** Can edit the list to match their current setup.

---

## **6\. Component Analysis: Center Command (Dynamic Tabs)**

*Location: Center Column (Desktop) / Middle of Stack (Mobile).*

This is the interactive heart of the profile. Content changes based on the selected tab in the Navigation Strip.

### **6.1 Tab: Overview (Default)**

* **Pinned Highlight:** A large, cinematic video player for the user's "Best Play." Auto-plays on hover (muted).  
* **Bounty Card:** A high-contrast, red-accented card showing an active challenge.  
  * *Action:* "ACCEPT CONTRACT" button triggers a matchmaking logic or DM.  
* **Skill Matrix:** A list of endorsements.  
  * *Logic:* Only verified teammates (people who have played in the same team roster) can endorse a skill to prevent spam.

### **6.2 Tab: Wallet (Economy Dashboard)**

* **Aesthetic:** "Fintech Dark Mode." Uses Gold (z-gold) text and graphs.  
* **Key Metrics:**  
  * **Total Balance:** Large, distinct font.  
  * **Conversion:** Approximate Real-World Currency value (e.g., ≈ 50,420 BDT).  
* **Transaction Ledger:** A list of recent inflows (Tournament Wins) and outflows (Store Purchases).  
* **Privacy:**  
  * **Owner:** Full access to Deposit/Withdraw.  
  * **Public:** This tab is **Hidden** or shows only "Total Career Earnings" without current balance.

### **6.3 Tab: Career (Timeline)**

* **Visuals:** A vertical line connects past and present teams.  
* **Current Team:** Highlighted with a glowing border and "Active" badge.  
* **Data Points:** Shows Role (IGL/Entry), Duration (Jan 2025 \- Present), and Team Logo.

### **6.4 Tab: Stats (Combat Data)**

* **Layout:** A grid of boxy, high-contrast metrics (K/D, Win Rate, Headshot %).  
* **Monetization:** A "Lock Icon" blocks advanced analytics (Heatmaps, Round-win %), prompting the user to upgrade to **DeltaCrown Premium**.

### **6.5 Tab: Inventory (Vault)**

* **Purpose:** Showcases virtual assets owned by the user (Avatar Frames, Profile Themes, Badges).  
* **Equipped Logic:** The currently active item has an "EQUIPPED" tag.  
* **Rarity Colors:**  
  * Common: Gray/White  
  * Rare: Purple (text-z-purple)  
  * Legendary: Gold (text-z-gold)

---

## **7\. Component Analysis: Right Sidebar (Status & Assets)**

*Location: Right Column (Desktop) / Bottom of Stack (Mobile).*

### **7.1 Live Tournament Widget**

* **Visual Tech:** Uses a gradient-to-b background that simulates a "scanning" radar.  
* **Function:** If the user is currently playing in a tournament, this widget appears.  
* **Action:** "WATCH STREAM" button links directly to the Twitch/YouTube broadcast.

### **7.2 Affiliations (Team List)**

* **Description:** A quick list of teams the user is enrolled in.  
* **Difference from Career:** "Career" is a history; "Affiliations" is current status.  
* **Action:** Clicking a team navigates to the **Team Profile Page**.

### **7.3 Trophy Cabinet**

* **Visuals:** A grid of square slots displaying earned tournament medals.  
* **Interaction:** Hovering over a trophy reveals a tooltip with details (e.g., "Season 1 Winner \- Winter Cup").

---

## **8\. Technical Implementation Guide**

### **8.1 Responsiveness Strategy**

The layout uses a **Mobile-First** approach via Tailwind classes:

* grid-cols-1: Default (Mobile). Stacked vertically.  
* lg:grid-cols-12: Desktop. Splits into 3-9-3 or 3-6-3 ratios.  
* overflow-x-auto: Applied to the Navigation Strip to allow swiping tabs on mobile screens without breaking layout.

### **8.2 JavaScript Logic (switchTab)**

The template includes a Vanilla JS function to handle tab switching without page reloads.

**How it works:**

1. **Input:** Receives tabId (string, e.g., 'wallet').  
2. **Reset:** Selects all elements with class .tab-content and hides them (display: none).  
3. **Activate:** Selects the target ID (\#tab-wallet) and sets display: block \+ adds .active class for CSS fade-in animation.  
4. **Styling:** Loops through all buttons, removes the white/glow styling, and applies it only to the clicked button.

### **8.3 Backend Data Requirements**

To fully power this template, your Django Backend needs to provide the following Context Variables:

| Variable | Description |
| :---- | :---- |
| profile | The UserProfile object (Avatar, Bio, Level). |
| wallet | The DeltaCoin wallet model (Balance, Transactions). |
| active\_teams | Queryset of teams where membership.status \= 'active'. |
| career\_history | Queryset of past team memberships. |
| posts | User's community posts. |
| game\_ids | Linked GamePassport objects. |
| is\_owner | Boolean (request.user \== profile.user). |

---

## **9\. Customization & Extensions**

### **How to Change the Color Theme?**

1. Open the \<script\> tag containing tailwind.config.  
2. Modify the colors object:  
   * Change 'z-cyan' to \#FF4D00 for a **Orange/Fire Theme**.  
   * Change 'z-bg' to \#000000 for a **Pitch Black OLED Theme**.

### **How to Add a "Premium" Gold Border?**

Add a conditional class to the z-card or avatar:

HTML  
\<div class="z-card ... {% if user.is\_premium %}border-z-gold shadow-neon-gold{% endi

This is **Part 3 of the Comprehensive Project Documentation**.

This final section covers the **Backend Integration Blueprint**. It provides the specific Django Models, View Logic, and Database Schema required to power the "Aurora Zenith" frontend features (like Bounties, Endorsements, and the Economy system) defined in the previous parts.

---

## **10\. Backend Data Schema (Django Models)**

To fully support the features in the Aurora Zenith UI, your `models.py` should include the following structures.

### **10.1 Core Profile Extensions**

The `UserProfile` model needs specific fields to support the customization and visual flair.

Python  
class UserProfile(models.Model):  
    user \= models.OneToOneField(User, on\_delete=models.CASCADE)  
    \# Identity  
    gamertag \= models.CharField(max\_length=50)  
    bio \= models.TextField(max\_length=500, blank=True)  
    nationality \= models.CharField(max\_length=50, default="Bangladesh")  
    location \= models.CharField(max\_length=100, blank=True)  
      
    \# Visual Assets  
    avatar \= models.ImageField(upload\_to='avatars/')  
    cover\_photo \= models.ImageField(upload\_to='covers/', default='defaults/cover.jpg')  
    equipped\_frame \= models.CharField(max\_length=50, default='default') \# e.g. 'dragon\_fire'  
      
    \# Status & Stats  
    is\_verified\_pro \= models.BooleanField(default=False)  
    reputation\_score \= models.IntegerField(default=100) \# 0-100  
    level \= models.IntegerField(default=1)  
      
    \# Privacy Settings (JSON Field for flexibility)  
    privacy\_settings \= models.JSONField(default=dict)   
    \# Example: {'real\_name': 'friends', 'inventory': 'public'}

    def get\_completion\_percent(self):  
        \# Logic to calculate profile completion for the "Setup" wizard  
        pass

### **10.2 The "Game Passport" System**

To support the "Linked IDs" slot machine in the sidebar.

Python  
class GamePassport(models.Model):  
    user \= models.ForeignKey(UserProfile, related\_name='game\_passports', on\_delete=models.CASCADE)  
    game\_name \= models.CharField(max\_length=50) \# 'Valorant', 'PUBG'  
    in\_game\_id \= models.CharField(max\_length=100)  
    rank\_tier \= models.CharField(max\_length=50) \# 'Immortal 3'  
    is\_main \= models.BooleanField(default=False) \# Highlights with Cyan border

### **10.3 The "Bounty" System**

To support the high-contrast Bounty Card in the Overview tab.

Python  
class Bounty(models.Model):  
    creator \= models.ForeignKey(User, on\_delete=models.CASCADE)  
    title \= models.CharField(max\_length=100) \# "1v1 Aim Duel"  
    game \= models.CharField(max\_length=50)  
    reward\_amount \= models.IntegerField() \# In DeltaCoins  
    status \= models.CharField(choices=\['OPEN', 'IN\_PROGRESS', 'COMPLETED'\], default='OPEN')  
    requirements \= models.TextField() \# "First to 100k, Gridshot"

### **10.4 Skill Endorsements**

To support the LinkedIn-style skill voting in the Overview tab.

Python  
class SkillEndorsement(models.Model):  
    receiver \= models.ForeignKey(User, related\_name='received\_endorsements', on\_delete=models.CASCADE)  
    endorser \= models.ForeignKey(User, related\_name='given\_endorsements', on\_delete=models.CASCADE)  
    skill\_name \= models.CharField(max\_length=50) \# 'Shotcalling', 'Aim'  
      
    class Meta:  
        unique\_together \= ('receiver', 'endorser', 'skill\_name')

---

## **11\. View Logic & Context Data**

In your `views.py`, the `profile_detail` view must calculate the "View Mode" (Owner vs. Spectator) and fetch the relevant data chunks.

Python  
def profile\_detail(request, username):  
    \# 1\. Fetch User  
    target\_user \= get\_object\_or\_404(User, username=username)  
    profile \= target\_user.profile  
      
    \# 2\. Determine View Mode  
    is\_owner \= (request.user \== target\_user)  
    is\_friend \= (request.user in profile.friends.all())  
      
    \# 3\. Fetch Dynamic Data  
    active\_teams \= target\_user.teammembership\_set.filter(status='active')  
    game\_passports \= profile.game\_passports.all()  
    gear\_setup \= profile.gear.all()  
      
    \# 4\. Economy (Owner Only Security)  
    wallet\_data \= None  
    if is\_owner:  
        wallet\_data \= target\_user.wallet \# Full access  
    else:  
        wallet\_data \= {'net\_worth': target\_user.wallet.calculate\_net\_worth()} \# Public limited data  
          
    \# 5\. Render Template  
    context \= {  
        'profile': profile,  
        'is\_owner': is\_owner,  
        'view\_mode': 'owner' if is\_owner else ('friend' if is\_friend else 'public'),  
        'active\_teams': active\_teams,  
        'game\_ids': game\_passports,  
        'wallet': wallet\_data,  
        'bounty': Bounty.objects.filter(creator=target\_user, status='OPEN').first(),  
        'endorsements': SkillEndorsement.objects.filter(receiver=target\_user).values('skill\_name').annotate(count=Count('id')),  
    }  
    return render(request, 'user\_profile/profile\_detail.html', context)

---

## **12\. Future Scalability & Roadmap**

This template is designed with specific "hooks" for future features that are visualized in the UI but require complex backend logic.

### **12.1 Real-Time WebSocket Integration**

* **UI Element:** The "LIVE STATUS" sidebar widget.  
* **Implementation Plan:**  
  1. Integrate **Django Channels** (Redis).  
  2. When a match starts, the Tournament Server sends a signal to the User Channel.  
  3. The frontend listens for `socket.on('match_start')` and unhides the "Live Widget" automatically without a page refresh.

### **12.2 Advanced Analytics (The Locked Tab)**

* **UI Element:** The "Advanced Analytics Locked" button in the Stats tab.  
* **Implementation Plan:**  
  1. Create a `PremiumSubscription` model.  
  2. If `user.has_premium`, replace the static "Lock Icon" with interactive **Chart.js** or **ApexCharts** visualizations (Heatmaps, Aim Accuracy Graphs).

### **12.3 The "CrownStore" Connection**

* **UI Element:** Gear Setup and Inventory items.  
* **Implementation Plan:**  
  1. Link `UserGear` items to `StoreProduct` models.  
  2. Add an affiliate tracking ID to the "View in Store" button.  
  3. If a spectator buys a mouse from a Pro Player's profile, the player earns a small DeltaCoin commission.

---

## **13\. Final Project Handover Checklist**

Before deploying this template to production, ensure the following:

* \[ \] **Assets:** Verify that `hero-pattern` and default avatar images are stored in your S3/Static Media bucket, not hotlinked from Unsplash (for faster load times).  
* \[ \] **Mobile QA:** Test the "Sticky Tabs" on an actual iPhone/Android device to ensure the horizontal scroll feels smooth.  
* \[ \] **Empty States:** Create logic for users with *no* teams, *no* bio, or *no* transactions (e.g., show a "Setup your profile to see stats" empty state card).  
* \[ \] **SEO:** Populate the `<meta name="description">` tag dynamically with the user's bio for better Google indexing of pro player profiles.

