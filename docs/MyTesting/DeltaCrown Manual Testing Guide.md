# DeltaCrown — Manual Testing Guide

*A walkthrough for testing the DeltaCrown esports platform, written for anyone — no technical experience required.*

---

## Before You Begin

**What is this?**  
DeltaCrown is an esports tournament platform — think of it as a website where gamers create teams, join tournaments, and compete against each other. This guide walks you through every part of the site to make sure everything works properly.

**What you'll need:**
- A web browser (Chrome, Firefox, or Edge)
- The website running at: **http://127.0.0.1:8000** (your local test server)
- The admin panel at: **http://127.0.0.1:8000/admin/**
- About 45–60 minutes

**What's already set up:**  
The database has been pre-loaded ("seeded") with sample data so you have something to test with. You'll find 100 test users, 24 teams, 3 organizations, and 19 tournaments already created — covering various games like Valorant, CS2, League of Legends, Dota 2, Apex Legends, Rocket League, Overwatch 2, and FC 25.

---

## Quick Reference — Test Accounts

Every test account uses the same password: **`DeltaCrown2025!`**

| Who | Username | Role | Good For Testing |
|-----|----------|------|------------------|
| Omar (Caster) | `dc_omar` | Tournament organizer | Creating & managing tournaments |
| Nabil (Org CEO) | `dc_nabil` | Organization CEO | Managing Titan Esports org & teams |
| Tanvir (Pro) | `dc_tanvir` | Team captain | Leading Crimson Syndicate (Valorant) |
| Sakib (IGL) | `dc_sakib` | Team captain | Leading Velocity X BD (Valorant) |
| Rifat (Pro) | `dc_rifat` | Team captain | Leading Old School BD (CS2) |
| Sumon (Multi-game) | `dc_sumon` | Player + Org CEO | Crown Dynasty org, plays Val/CS2/LoL |
| FC Master | `dc_fc_master` | Solo player | FC 25 solo tournament testing |
| Bot Slayer | `dc_bot_slayer` | Casual player | Casual user experience |
| Jamal (Caster) | `dc_jamal` | Non-player staff | User with no games linked |

### Starting the Test Server

Open a terminal in the project folder and run:

```
python manage.py runserver
```

This uses the main `deltacrown.settings` which reads the production database URL from the `.env` file.

The site will be available at http://127.0.0.1:8000

---

## Part 1 — The Home Page (First Impressions)

**Goal:** Make sure the front door of the website looks right and works.

1. Open your browser and go to **http://127.0.0.1:8000**
2. You should see the DeltaCrown homepage with:
   - A navigation bar at the top
   - Featured tournaments or highlights
   - Links to browse tournaments, teams, and community

**Check these things:**
- [ ] Does the page load without any errors?
- [ ] Do all the navigation links at the top work?
- [ ] Does the "Tournaments" link take you to the tournament listing?
- [ ] Does the "Teams" link take you to the team directory?
- [ ] Does "About" page load? → http://127.0.0.1:8000/about/
- [ ] Does "Community" page load? → http://127.0.0.1:8000/community/

---

## Part 2 — Signing In

**Goal:** Log into the platform as different users.

### Test A: Log in as a Tournament Organizer

1. Go to **http://127.0.0.1:8000/account/login/**
2. Enter username: **dc_omar**
3. Enter password: **DeltaCrown2025!**
4. Click "Sign In"

**Check:**
- [ ] Did you land on the homepage or dashboard after login?
- [ ] Does the navigation bar show you're logged in (your name or avatar)?
- [ ] Can you see a dashboard link?

### Test B: Log out and log in as a Player

1. Click "Logout" or go to **http://127.0.0.1:8000/account/logout/**
2. Now log in as **dc_tanvir** (password: `DeltaCrown2025!`)
3. This is a pro Valorant player who captains Crimson Syndicate

**Check:**
- [ ] Did login work for a different user?
- [ ] Can you navigate to your profile?

### Test C: Sign Up (New Account)

1. Log out first
2. Go to **http://127.0.0.1:8000/account/signup/**
3. Create a new account with any username, email, and password
4. Check if the signup process completes

**Check:**
- [ ] Does the signup form appear?
- [ ] Can you create a new account successfully?

---

## Part 3 — User Profiles

**Goal:** Verify that player profiles display correctly.

### View Your Own Profile

1. Log in as **dc_tanvir** (password: `DeltaCrown2025!`)
2. Go to **http://127.0.0.1:8000/@dc_tanvir/**

**Check:**
- [ ] Does the profile page load?
- [ ] Can you see the display name "Tanvir.Gaming"?
- [ ] Is the bio shown: "Pro player for Crimson Syndicate"?
- [ ] Are game passports (linked games) visible?
- [ ] Does the activity tab work? → http://127.0.0.1:8000/@dc_tanvir/activity/

### View Another Player's Profile

1. Go to **http://127.0.0.1:8000/@dc_mama_lag/**
2. This is "Mama_Lag_Kore" — a casual player from Chittagong

**Check:**
- [ ] Does the profile load for a different user?
- [ ] Is their bio and city shown correctly?

### Edit Your Profile

1. Log in as **dc_tanvir**
2. Go to **http://127.0.0.1:8000/me/edit/**

**Check:**
- [ ] Does the edit page load?
- [ ] Can you change the bio and save?
- [ ] Does the change appear on the profile?

### Profile Settings & Privacy

- Settings: **http://127.0.0.1:8000/me/settings/**
- Privacy: **http://127.0.0.1:8000/me/privacy/**

**Check:**
- [ ] Do both pages load?

---

## Part 4 — Browsing Tournaments

**Goal:** Make sure visitors can find and view tournaments.

### Tournament List

1. Go to **http://127.0.0.1:8000/tournaments/**

**Check:**
- [ ] Does the page show a list of tournaments?
- [ ] Can you see tournaments with different statuses (live, completed, open)?
- [ ] Is there a "Browse" page too? → http://127.0.0.1:8000/tournaments/browse/

### View a Completed Tournament

1. Click on **"DeltaCrown Valorant Invitationals: Season 1"** or go to:
   **http://127.0.0.1:8000/tournaments/valorant-invitational-s1/**

**Check:**
- [ ] Does the tournament detail page load?
- [ ] Can you see the tournament name, game (Valorant), and status (Completed)?
- [ ] Is the prize pool shown (৳50,000)?
- [ ] Can you view the bracket? → http://127.0.0.1:8000/tournaments/valorant-invitational-s1/bracket/
- [ ] Can you view results? → http://127.0.0.1:8000/tournaments/valorant-invitational-s1/results/

### View a Live Tournament

1. Go to **http://127.0.0.1:8000/tournaments/radiant-rising-s2/**

**Check:**
- [ ] Does it show as "Live"?
- [ ] Can you see registered teams and ongoing matches?
- [ ] Does the bracket page show match results and upcoming matches?

### View an Open Registration Tournament

1. Go to **http://127.0.0.1:8000/tournaments/valorant-scrims-44/**

**Check:**
- [ ] Does it show as "Registration Open"?
- [ ] Can you see how many slots are filled vs. total?
- [ ] Is there a "Register" button visible?

---

## Part 5 — Registering for a Tournament

**Goal:** Test the tournament registration process.

### Team Registration

1. Log in as **dc_bot_slayer** (password: `DeltaCrown2025!`)
   - This player is on the "Headhunterz" Valorant team
2. Go to **http://127.0.0.1:8000/tournaments/valorant-scrims-44/**
3. Look for a "Register" or "Register Team" button
4. Try to register your team

**Check:**
- [ ] Can you see the registration option?
- [ ] Does the registration form or wizard load?
- [ ] Does it show which team you can register?

### Solo Registration

1. Log in as **dc_fc_master** (password: `DeltaCrown2025!`)
2. Go to **http://127.0.0.1:8000/tournaments/fc25-solo-championship/**
3. This is a solo tournament — try to register as an individual player

**Check:**
- [ ] Does solo registration work differently from team registration?
- [ ] Can you register without selecting a team?

### Registration with Entry Fee

1. Go to **http://127.0.0.1:8000/tournaments/cs2-comp-league-spring/**
2. This tournament has a ৳500 entry fee
3. Try to register

**Check:**
- [ ] Does the entry fee amount show during registration?
- [ ] Is the payment process clear?

---

## Part 6 — Teams & Organizations

**Goal:** Verify team browsing, creation, and management.

### Browse Teams

1. Go to **http://127.0.0.1:8000/teams/**

**Check:**
- [ ] Does the team directory load?
- [ ] Can you see team names, tags, and games?
- [ ] Are teams from different games shown?

### View a Team's Page

1. Click on **Crimson Syndicate** or go to:
   **http://127.0.0.1:8000/teams/crimson-syndicate/**

**Check:**
- [ ] Does the team detail page load?
- [ ] Can you see the team name "Crimson Syndicate" and tag "CRS"?
- [ ] Is the game (Valorant) shown?
- [ ] Can you see the roster (Tanvir + members)?

### Manage Your Team

1. Log in as **dc_tanvir** (password: `DeltaCrown2025!`) — captain of Crimson Syndicate
2. Go to **http://127.0.0.1:8000/teams/crimson-syndicate/manage/**

**Check:**
- [ ] Does the management page load?
- [ ] Can you see team settings and roster controls?
- [ ] Are member roles visible (Owner, Player, Substitute)?

### Create a New Team

1. Log in as any user
2. Go to **http://127.0.0.1:8000/teams/create/**

**Check:**
- [ ] Does the team creation form load?
- [ ] Can you fill in a team name, tag, and select a game?
- [ ] Does the team get created successfully?

### Browse Organizations

1. Go to **http://127.0.0.1:8000/orgs/**

**Check:**
- [ ] Can you see the three test organizations: Titan Esports, Eclipse Gaming, Crown Dynasty?

### View an Organization

1. Go to **http://127.0.0.1:8000/orgs/titan-esports/**

**Check:**
- [ ] Does the organization detail page load?
- [ ] Can you see the CEO (Nabil) and org description?
- [ ] Can you see the org's teams (Dhaka Leviathans, Titan Valorant, Fury Esports)?

### Organization Management

1. Log in as **dc_nabil** (password: `DeltaCrown2025!`) — CEO of Titan Esports
2. Go to **http://127.0.0.1:8000/orgs/titan-esports/hub/**

**Check:**
- [ ] Does the org hub load?
- [ ] Can you manage org-level settings?

---

## Part 7 — The Organizer Console (Creating Tournaments)

**Goal:** Test tournament creation and management from the organizer's perspective.

### Access the Organizer Dashboard

1. Log in as **dc_omar** (password: `DeltaCrown2025!`)
2. Go to **http://127.0.0.1:8000/tournaments/organizer/**

**Check:**
- [ ] Does the organizer dashboard load?
- [ ] Can you see your existing tournaments?

### Create a New Tournament

1. Go to **http://127.0.0.1:8000/tournaments/organizer/create/**
2. Fill in the form:
   - **Name:** "Test Tournament Alpha"
   - **Game:** Select any game (e.g., VALORANT)
   - **Format:** Single Elimination
   - **Participation Type:** Team
   - **Platform:** PC
   - **Mode:** Online
   - **Max Participants:** 8
   - **Min Participants:** 4
   - **Registration Start:** Today's date
   - **Registration End:** A week from now
   - **Tournament Start:** Two weeks from now
   - **Prize Pool:** 5000
   - **Description:** "A test tournament for manual testing"
3. Toggle some options: Featured, Check-in, Certificates
4. Click Create / Submit

**Check:**
- [ ] Does the form load with all the fields?
- [ ] Are there dropdowns for Game, Format, Platform, Mode, Participation Type?
- [ ] Do the toggle switches work (Featured, Check-in, Certificates, Live Updates)?
- [ ] Does the tournament get created successfully?
- [ ] Are you redirected to the tournament's organizer page?

### Manage an Existing Tournament

1. Go to **http://127.0.0.1:8000/tournaments/organizer/radiant-rising-s2/**

**Check:**
- [ ] Can you see tournament details, registrations, and matches?
- [ ] Can you navigate between tabs (overview, registrations, bracket, etc.)?

---

## Part 8 — Match Viewing

**Goal:** Verify match pages work correctly.

### View Tournament Matches

1. Go to **http://127.0.0.1:8000/tournaments/radiant-rising-s2/bracket/**

**Check:**
- [ ] Does the bracket view show matches?
- [ ] Can you see completed match scores?
- [ ] Are upcoming matches shown as "Scheduled"?

### View Group Standings

1. Go to **http://127.0.0.1:8000/tournaments/valorant-invitational-s1/groups/standings/**

**Check:**
- [ ] Does the standings page load?

---

## Part 9 — Dashboard & My Tournaments

**Goal:** Check the player dashboard and personal tournament views.

### Player Dashboard

1. Log in as **dc_tanvir** (password: `DeltaCrown2025!`)
2. Go to **http://127.0.0.1:8000/dashboard/**

**Check:**
- [ ] Does the dashboard load?
- [ ] Can you see your upcoming matches or registered tournaments?

### My Tournaments

1. Go to **http://127.0.0.1:8000/tournaments/my/**

**Check:**
- [ ] Does the page show tournaments you're registered in?
- [ ] Can you distinguish between active and completed tournaments?

### My Registrations

1. Go to **http://127.0.0.1:8000/tournaments/my/registrations/**

**Check:**
- [ ] Can you see all your tournament registrations?

---

## Part 10 — Search

**Goal:** Test the search functionality.

1. Go to **http://127.0.0.1:8000/search/**

**Check:**
- [ ] Does the search page load?
- [ ] Try searching for "Valorant" — do tournament results appear?
- [ ] Try searching for "Crimson" — does the team show up?
- [ ] Try searching for a username like "dc_tanvir"

---

## Part 11 — Spectator View

**Goal:** Test the public spectator pages.

1. Go to **http://127.0.0.1:8000/spectator/**

**Check:**
- [ ] Does the spectator tournament list load?
- [ ] Can you view tournament details from spectator view?
- [ ] Can you view match details?

---

## Part 12 — The Admin Panel

**Goal:** Verify the Django admin panel works correctly for platform administrators.

### Log In to Admin

1. First, create a superuser if you haven't:
   ```
   python manage.py createsuperuser
   ```
   Or log in with an existing admin account.

2. Go to **http://127.0.0.1:8000/admin/**

**Check:**
- [ ] Does the admin panel load with the Unfold theme?
- [ ] Can you see all registered models (Tournaments, Teams, Users, etc.)?

### Check Tournament Admin

1. Click on "Tournaments" in the admin sidebar
2. You should see all 19 tournaments listed

**Check:**
- [ ] Can you see tournament list with names, games, statuses?
- [ ] Click on "DeltaCrown Valorant Invitationals: Season 1" — does the edit form load?
- [ ] Can you see all fields (name, slug, game, format, dates, prizes)?
- [ ] Can you modify and save changes?

### Check Team Admin

1. Click on "Teams" in the admin sidebar

**Check:**
- [ ] Can you see all 24 teams?
- [ ] Click on any team — does the detail view load?
- [ ] Can you see memberships?

### Check User Admin

1. Click on "Users" in the admin sidebar

**Check:**
- [ ] Can you see all 100+ users?
- [ ] Can you filter by username (search "dc_tanvir")?
- [ ] Click on a user — can you view their details?

### Check Registration Admin

1. Click on "Registrations" in the admin sidebar

**Check:**
- [ ] Can you see all registrations?
- [ ] Are different statuses visible (confirmed, payment_submitted)?

### Check Match Admin

1. Click on "Matches" in the admin sidebar

**Check:**
- [ ] Can you see all 78+ matches?
- [ ] Are match states shown correctly (completed, scheduled, live)?
- [ ] Click on a match — can you view participants, scores, and winner?

---

## Part 13 — Edge Cases & Error Handling

**Goal:** Test how the site handles unusual situations.

### Non-existent Pages

1. Go to **http://127.0.0.1:8000/tournaments/this-does-not-exist/**

**Check:**
- [ ] Do you get a proper 404 page (not an ugly error)?

### Non-existent Profile

1. Go to **http://127.0.0.1:8000/@nonexistent_user/**

**Check:**
- [ ] Does it show a 404 or "user not found" message?

### Accessing Organizer Pages Without Permission

1. Log in as **dc_bot_slayer** (a regular player)
2. Try to go to **http://127.0.0.1:8000/tournaments/organizer/radiant-rising-s2/**

**Check:**
- [ ] Are you blocked from managing someone else's tournament?
- [ ] Do you get a permission error or redirect?

### Empty Tournament (No Registrations)

1. Go to **http://127.0.0.1:8000/tournaments/fc25-solo-championship/**

**Check:**
- [ ] Does the tournament page handle having zero registrations gracefully?
- [ ] Does it show "No participants yet" or something similar?

---

## Part 14 — Static Pages & Policies

**Goal:** Verify informational pages load.

- [ ] Privacy Policy: http://127.0.0.1:8000/privacy/
- [ ] Terms of Service: http://127.0.0.1:8000/terms/
- [ ] Cookie Policy: http://127.0.0.1:8000/cookies/
- [ ] Game Passport Rules: http://127.0.0.1:8000/game-passport-rules/

---

## Summary Checklist

| Section | What to Test | Status |
|---------|-------------|--------|
| 1. Homepage | Page loads, navigation works | ☐ |
| 2. Sign In | Login/logout/signup flows | ☐ |
| 3. Profiles | View, edit, privacy settings | ☐ |
| 4. Browse Tournaments | List, detail pages for all statuses | ☐ |
| 5. Registration | Team, solo, paid tournament registration | ☐ |
| 6. Teams & Orgs | Browse, view, create, manage teams/orgs | ☐ |
| 7. Organizer Console | Create tournament, manage existing | ☐ |
| 8. Matches | Bracket view, match details | ☐ |
| 9. Dashboard | Player dashboard, my tournaments | ☐ |
| 10. Search | Search for tournaments, teams, players | ☐ |
| 11. Spectator | Public spectator views | ☐ |
| 12. Admin Panel | Full admin CRUD for all models | ☐ |
| 13. Edge Cases | 404s, permissions, empty states | ☐ |
| 14. Static Pages | Privacy, terms, cookies | ☐ |

---

## Seeded Data At a Glance

**19 Tournaments across 8 games:**
- 6 Completed (Valorant, CS2, LoL, Rocket League, FC 25)
- 7 Live (Valorant, Dota 2, Apex Legends, Overwatch 2, Rocket League)
- 6 Open Registration (Valorant, CS2, FC 25, LoL, Dota 2)

**24 Teams:**
- 6 Valorant teams (Crimson Syndicate, Velocity X BD, Dhaka Leviathans, Titan Valorant, Headhunterz, AimBot Activated)
- 4 CS2 teams (Old School BD, Dust2 Demons, Mirage Kings, Global Elites)
- 3 LoL teams (Fury Esports, Mystic Legion, Echo Rift)
- 3 Dota 2 teams (Ancient Defense, Roshan Raiders, Ward Vision)
- 3 Apex teams (Apex Predators BD, Zone Survivors, Loot Goblins)
- 3 Rocket League teams (Nitro Speed, Flip Reset FC, Car Go Brr)
- 1 Overwatch 2 team (Payload Pushers, Point Capture)
- FC 25 is solo — no teams

**3 Organizations:**
- Titan Esports (CEO: dc_nabil) — owns Dhaka Leviathans, Titan Valorant, Fury Esports
- Eclipse Gaming (CEO: dc_shafiq) — owns Dust2 Demons, Ancient Defense
- Crown Dynasty (CEO: dc_sumon) — owns AimBot Activated

**100 Users (all password: `DeltaCrown2025!`):**
- 40 "Grinders" (dc_shadow_strike through dc_ow_genji) — competitive players
- 40 "Casuals" (dc_mama_lag through dc_rl_flip) — fun/relaxed players
- 20 "Pros" (dc_tanvir through dc_omar) — pro players, org owners, casters
