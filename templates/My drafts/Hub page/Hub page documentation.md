# **📘 DeltaCrown Command Hub – Technical Implementation Guide**

**Tech Stack:** HTML5, Tailwind CSS (v3.4), Vanilla JS

**Author:** Frontend Architecture Team

---

## **1\. Overview & Architecture**

This template is a single-page, high-density dashboard designed for the "Team & Organization" module of DeltaCrown. It serves as the central hub for users to find teams, view rankings, and manage their esports careers.

### **Core Design Philosophy: "Liquid Cyberpunk"**

* **Visual Language:** Dark mode (\#020204) with high-contrast neon accents (Electric Blue, Violet, Gold).  
* **UI Pattern:** Glassmorphism (blurs, semi-transparent panels) \+ Bento Grids.  
* **Responsiveness:** Mobile-first approach, scaling up to 8K via max-w-\[1920px\].

### **File Structure (Recommended for Django)**

Plaintext  
templates/  
└── teams/  
    ├── hub.html              \# The main file provided here  
    ├── components/  
    │   ├── navbar.html       \# Extract the \<nav\> block here  
    │   ├── hero\_carousel.html \# Extract the hero section  
    │   ├── game\_grid.html    \# The 11-game selector  
    │   ├── team\_card.html    \# Loopable card template  
    │   └── ranking\_row.html  \# Loopable table row  
    └── partials/  
        └── scout\_radar.html  \# The sidebar widget

---

## **2\. CSS Architecture & Customization**

The template uses **Tailwind CSS via CDN** for rapid prototyping, but for production, you should migrate the configuration to your tailwind.config.js.

### **Custom Colors (The Delta Palette)**

These colors are hardcoded in the \<script\> config block at the top of the file. You must add them to your build process to ensure consistency across the platform.

| Class Name | Hex Code | Usage |
| :---- | :---- | :---- |
| bg-delta-base | \#020204 | Main page background (Deep Void) |
| bg-delta-panel | \#0b1121 | Cards & Panels background |
| text-delta-electric | \#00E5FF | Primary Action / Cyan Accents |
| text-delta-violet | \#6C00FF | Secondary Branding / Gradients |
| text-delta-gold | \#FFD700 | Premium/Rank \#1 Highlights |
| text-delta-danger | \#FF0055 | "Live" indicators, Alerts |

### **Custom Fonts**

* **Headings:** Unbounded (Google Fonts) – Used for "Cyber" feel.  
* **UI Text:** Plus Jakarta Sans – Clean, readable at small sizes.  
* **Numbers:** Teko – Condensed, high-impact for stats.

---

## **3\. Component Breakdown & Backend Integration**

This section details every major component in the template, what data it displays, and **what your backend developer needs to wire up.**

### **A. Navigation Bar (\<nav\>)**

* **Current State:** Static HTML using the requested "Default Primary Navbar" layout.  
* **Backend Logic Needed:**  
  * **User Auth Check:** Toggle between "Login/Register" buttons and the "Profile/Notification" view based on request.user.is\_authenticated.  
  * **Profile Data:** Inject {{ user.username }} and {{ user.avatar\_url }} into the profile section.  
  * **Notifications:** The red dot (bg-delta-danger) should only appear if user.notifications.unread\_count \> 0.

### **B. Live Ticker (Marquee)**

* **HTML Location:** div.relative.w-full.bg-delta-surface (Below Navbar).  
* **Current State:** Hardcoded match results (Protocol V vs Null Boyz).  
* **Backend Logic Needed:**  
  * **API Endpoint:** Create an endpoint /api/matches/live-ticker/ that returns the latest 5 finished matches or ongoing live scores.  
  * **HTMX/AJAX:** Use JS to fetch this JSON and dynamically replace the \<span\> content inside the marquee.

### **C. Hero Section: Dynamic Carousel**

* **HTML Location:** \<header\> \-\> Right Column \-\> \#heroCarousel.  
* **Logic:**  
  * **Slide 1 (Empire Spotlight):** This currently shows "SYNTAX". You need a backend query to fetch the **\#1 Ranked Organization** of the week and populate:  
    * Org Name  
    * Total Valuation (calculated field)  
    * Trophy Count  
  * **Slide 2 (User Status):**  
    * **If User is Org Owner:** Show "Empire Status" (My Org Stats).  
    * **If User is Free Agent:** Show "Free Agent" (as currently designed).  
    * **If User is Anonymous:** Show a generic "Join the Revolution" CTA.  
  * **Slide 3 (Live Tournament):** Fetch the currently active "Tier S" tournament. If none, hide this slide or show "Upcoming Events".

### **D. Game Selector (Tactical Grid)**

* **HTML Location:** Section with ID game-nav.  
* **Current State:** 12 Static Buttons (All Systems \+ 11 Games).  
* **Missing Plan Feature:** The template shows generic icons. **Action Item:** Replace the \<img\> src attributes with your actual uploaded game assets (e.g., {% static 'games/valorant\_icon.png' %}).  
* **Interaction:**  
  * The JS currently just toggles visual classes.  
  * **Backend:** Clicking a game (e.g., "Valorant") should trigger an HTMX request or a full page reload to ?game=valorant to filter the **Featured Units** and **Leaderboard** below.

---

## **4\. Main Content: Grid & List Views**

This is the core data display. The template separates "Featured Units" (Grid) and "Global Leaderboard" (List), but includes a toggle to switch view modes if preferred.

### **E. Advanced Search Bar**

* **HTML Location:** section \> div.bg-white/5 (rounded bar with inputs).  
* **Current State:** Visual only.  
* **Backend Logic Needed:**  
  * **Filters:** The "Region" and "Platform" dropdowns need to populate their \<option\> tags from your GameConfiguration or Region models in Django.  
  * **Input:** The text input needs to hook into a search API (e.g., /search/teams/?q=...).

### **F. Featured Units (Grid View)**

* **HTML Location:** \#teamGridView.  
* **Data Binding:**  
  * **Banner Image:** team.banner\_image.url (fallback to default game banner if empty).  
  * **Badge (Top Right):** Logic required. If team.rank \< 10 show "TOP 1%", if team.is\_recruiting show "RECRUITING".  
  * **Logo:** team.logo.url.  
  * **Stats:** team.current\_cp (CP), team.win\_rate (Win %), team.streak (Streak).  
  * **Action:** The "View Profile" button should link to {% url 'team\_detail' team.slug %}.

### **G. Global Leaderboard (Table View)**

* **HTML Location:** \#leaderboardView.  
* **Data Binding:**  
  * **Rank:** Loop counter {{ forloop.counter }}.  
  * **Trend:** Compare current\_rank vs previous\_rank.  
    * If Up: Green Arrow (fa-caret-up).  
    * If Down: Red Arrow (fa-caret-down).  
    * If Same: Dash (fa-minus).  
  * **Form:** The 5 dots represent the last 5 matches.  
    * Green Dot: bg-delta-success (Win).  
    * Red/Transparent Dot: bg-delta-danger or opacity-50 (Loss).

---

## **5\. Smart Sidebar (The "Missing" Logic)**

The template includes a "Scout Radar" and "Scrim Finder" in the right column. These were design concepts that need backend logic now.

### **H. Scout Radar Widget**

* **Concept:** Shows trending Free Agents looking for a team.  
* **Backend Query:** User.objects.filter(is\_looking\_for\_team=True).order\_by('-rank\_score')\[:3\].  
* **Action:** Clicking the "+" button should trigger an "Invite to Team" modal (if the viewer is a Captain/Manager).

### **I. Scrim Finder Widget**

* **Concept:** Live feed of teams looking for practice matches.  
* **Backend Query:** ScrimRequest.objects.filter(status='OPEN', game=current\_game)\[:5\].  
* **Data:** Show Time (e.g., "20:00" or "NOW") and Map/Server info.

---

## **6\. JavaScript Logic Explanation**

The embedded \<script\> block at the bottom handles the client-side interactivity.

### **1\. Hero Carousel (updateCarousel)**

* **Function:** Rotates the 3 slides every 5 seconds.  
* **Customization:** You can change the interval 5000 to 8000 for a slower pace.  
* **Note:** If you want to fetch this data dynamically, replace the hardcoded HTML slides with a loop from your database, and the JS will still work as long as the class .carousel-slide is preserved.

### **2\. View Toggle (toggleView)**

* **Function:** The template currently *hides* the List view by default.  
* **Logic:**  
  * view \=== 'grid': Shows \#teamGridView, hides \#leaderboardView.  
  * view \=== 'list': Hides \#teamGridView, shows \#leaderboardView.  
* **Dev Note:** Ensure both containers (div) exist in the DOM even if empty, or this script will throw an error.

### **3\. Load More (loadMore)**

* **Function:** Simulates an AJAX call.  
* **Production Implementation:**  
  * Replace setTimeout with a real fetch() call to your pagination API (e.g., ?page=2).  
  * Append the new HTML returned by the server to the \#teamGridView container.  
  * If next\_page is null, hide the button.

---

## **7\. Migration Checklist for Developer**

1. **Split the File:** Do not keep this as one giant HTML file. Break it into base.html (head/scripts) and hub.html (content).  
2. **Asset Replacement:** The template uses unsplash.com images. Replace these with:  
   * {% static 'images/games/valorant.jpg' %}  
   * {{ team.banner.url }}  
3. **Color Config:** Add the colors.delta object to your project's tailwind.config.js to ensure these custom colors work on other pages too.  
4. **Mobile Check:** The "Game Selector" uses overflow-x-auto. Ensure your mobile testing verifies that users can swipe left/right to see all 11 games.

This template is **feature-complete** regarding the frontend. The backend simply needs to fill the "slots" with real database values.

# **📘 DeltaCrown Command Hub – Technical Implementation Guide (Part 2\)**

**Focus:** Backend Data Schema, API Definitions, and "Shadow Feature" Logic.

---

## **8\. Recommended Database Schema (Django Models)**

To support the specific UI elements in this template, your backend developer needs to extend the `teams`, `tournaments`, and `users` apps.

### **A. The "Live Ticker" Model (`matches` app)**

The marquee at the top requires a lightweight model to fetch live scores quickly.

Python  
\# apps/matches/models.py  
class MatchTicker(models.Model):  
    game \= models.CharField(choices=GAME\_CHOICES) \# Valorant, CS2, etc.  
    team\_a \= models.ForeignKey('teams.Team', related\_name='team\_a\_matches')  
    team\_b \= models.ForeignKey('teams.Team', related\_name='team\_b\_matches')  
    score\_a \= models.IntegerField(default=0)  
    score\_b \= models.IntegerField(default=0)  
    status \= models.CharField(choices=\['LIVE', 'FINISHED', 'UPCOMING'\])  
    is\_hot \= models.BooleanField(default=False) \# If True, shows "LIVE" pulse icon  
      
    \# For the "Transfer" or "Market" news in the ticker  
    news\_text \= models.CharField(max\_length=255, blank=True)   
    \# e.g., "Player 'S1mple' joined Cloud9 Blue"

### **B. The "Scout Radar" Model (`players` app)**

This powers the sidebar widget looking for free agents.

Python  
\# apps/players/models.py  
class PlayerProfile(models.Model):  
    user \= models.OneToOneField(User, on\_delete=models.CASCADE)  
    is\_lft \= models.BooleanField(default=False) \# "Looking For Team"  
    primary\_game \= models.CharField(max\_length=50)  
    rank\_tier \= models.CharField(max\_length=50) \# e.g., "Diamond 3", "Global Elite"  
    role \= models.CharField(max\_length=50) \# e.g., "Duelist", "AWPer"  
      
    \# Algorithm Score for "Trending"  
    scout\_score \= models.IntegerField(default=0) 

### **C. The "Scrim Finder" Model (`scrims` app)**

This powers the "Scrim Finder" widget in the sidebar.

Python  
\# apps/scrims/models.py  
class ScrimRequest(models.Model):  
    team \= models.ForeignKey('teams.Team', on\_delete=models.CASCADE)  
    game \= models.CharField(max\_length=50)  
    scheduled\_time \= models.DateTimeField() \# or Null for "NOW"  
    server\_region \= models.CharField(max\_length=50) \# e.g., "Mumbai", "Frankfurt"  
    tier\_requirement \= models.CharField(max\_length=50) \# e.g., "High Tier"  
    is\_active \= models.BooleanField(default=True)

---

## **9\. API Definitions (JSON Responses)**

Your frontend `loadMore()` and `search` functions need specific JSON structures to render the cards dynamically.

### **A. Search & Filter API**

**Endpoint:** `GET /api/teams/search/?game=valorant&region=na&q=syntax`

**Response Structure:**

JSON  
{  
  "results": \[  
    {  
      "id": 101,  
      "name": "Protocol V",  
      "slug": "protocol-v",  
      "logo\_url": "/media/teams/logos/proto\_v.png",  
      "banner\_url": "/media/teams/banners/proto\_v\_bg.jpg",  
      "game": "Valorant",  
      "rank\_label": "Diamond I",  
      "rank\_tier": "diamond", // Used for CSS coloring  
      "stats": {  
        "cp": 14500,  
        "win\_rate": 72,  
        "streak": "5W"  
      },  
      "tags": \["TOP 1%"\] // Renders the top-right badge  
    }  
  \],  
  "pagination": {  
    "has\_next": true,  
    "next\_page": 2  
  }  
}

### **B. Live Ticker API**

**Endpoint:** `GET /api/system/ticker/`

**Response Structure:**

JSON  
\[  
  {  
    "type": "match",  
    "game": "VALORANT",  
    "team\_a": "Protocol V",  
    "score\_a": 13,  
    "team\_b": "Null Boyz",  
    "score\_b": 11,  
    "status": "FINISHED" // Renders "WIN" or "LIVE"  
  },  
  {  
    "type": "transfer",  
    "text": "Player 'S1mple' joined Cloud9 Blue"  
  }  
\]

---

## **10\. "Shadow Features" Implementation Guide**

These are features included in the template to make it "Premium" that were not explicitly detailed in your original plan. Here is how to implement them without breaking your scope.

### **Feature 1: The "Empire Spotlight" (Hero Carousel Slide 1\)**

* **What it is:** A spotlight on the \#1 Organization.  
* **How to implement:**  
  * Don't manually curate this. Write a scheduled task (Cron job or Celery) that runs every Monday at 00:00.  
  * It calculates `Sum(CP of all teams in Org)`.  
  * The Org with the highest total is flagged `is_spotlight=True`.  
  * The frontend simply queries `Organization.objects.get(is_spotlight=True)`.

### **Feature 2: "Scout Radar" (Sidebar Widget)**

* **What it is:** A feed of individual players looking for teams.  
* **How to implement:**  
  * In your **User Settings**, add a toggle: "Looking for Team".  
  * Add fields for "Role" (e.g., Duelist) and "Current Rank".  
  * The Sidebar simply lists the 3 most recent users who toggled this on for the currently selected game filter.

### **Feature 3: "Scrim Finder" (Sidebar Widget)**

* **What it is:** A "Looking for Group" (LFG) system for whole teams.  
* **How to implement:**  
  * Create a simple form on the Dashboard: "Post Scrim Request".  
  * Fields: Game, Time, Server.  
  * The Sidebar lists these requests.  
  * *MVP Shortcut:* If you don't want to build a full scrim system yet, you can fake this data with "Upcoming Tournament Matches" instead.

---

## **11\. Performance & Optimization Strategy**

Since this is a "High Density" interface with many images and gradients, performance is key.

1. **Image Optimization (Cloudinary/AWS S3):**  
   * The `Banner` images in the grid are large. Ensure your backend resizes them to `w=400` (width 400px) when uploading. Do not serve 4K banners in a tiny grid card.  
   * Use `.webp` format for all game assets.  
2. **Lazy Loading:**  
   * The template uses standard `<img>`. For the grid, add `loading="lazy"` to all image tags inside the loop.  
   * Example: `<img src="..." loading="lazy" class="...">`  
3. **CSS Purging:**  
   * Since we are using extensive Tailwind classes, ensure your production build pipeline runs `PurgeCSS` to remove unused styles, or the CSS file will be huge.  
4. **Glassmorphism Performance:**  
   * Backdrop filters (`backdrop-blur`) can be CPU intensive on cheap mobile phones.  
   * **Tip:** In your CSS, wrap the blur effects in a `@media` query to disable them on low-power devices if scrolling feels laggy.

---

## **12\. Final Handover Note to Developer**

"This template relies heavily on the `game` attribute. Almost every query—from the Leaderboard to the Scrim Finder—should listen to the active Game Filter selected in the horizontal scroll bar. Ensure the frontend passes `?game=slug` in every HTMX/AJAX request to keep the context relevant."

