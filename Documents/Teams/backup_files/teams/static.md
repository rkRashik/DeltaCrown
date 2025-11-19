# 📄 **FILE 6/8**

# **apps/teams/static.md**

### (*Complete documentation of all static assets: JS, CSS, images, pipelines, dependencies, and how each file connects to templates in the Teams App.*)

This document explains:

✔ Every JS file (function-by-function)
✔ Every CSS file (purpose + where it's used)
✔ All image assets (logos, game cards, icons)
✔ Static pipeline behavior (static vs staticfiles)
✔ Known static bugs
✔ How to work safely with static files in this project
✔ What Copilot MUST follow when modifying static files

---

# 🟩 **1. Static Assets Overview**

Static directory structure:

```
/static/
    /teams/
        /css/
        /js/
        /img/
        /components/
        /themes/
    /img/
        /game_cards/
```

Production uses **ManifestStaticFilesStorage**, meaning:

* Filenames become content-hashed (e.g., `team-create-esports.2fd8aa.css`)
* Staticfiles folder is used in production
* Development uses `/static/` directly

---

# 🟦 **2. JavaScript Files (Full Inventory)**

## 🔹 **2.1 Team Creation Scripts**

### **team-create-esports.js**

**Used by:**
`team_create_esports.html` (main create wizard)

**Controls:**
✔ Multi-step wizard navigation
✔ Validation (name/tag availability)
✔ Game selection logic
✔ Game ID field insertion
✔ Resume creation (session data restore)
✔ Step animations
✔ Scroll-to-error behavior
✔ Success summary slide

**Key global functions:**

* `showStep(stepIndex)`
* `jumpToErrorStep()`
* `TeamCreateEsports.init()`

---

### **team-create-enhanced.js**

**Used by:**
`team_create.html`

**Controls:**
✔ Real-time validation using AJAX
✔ Game ID pop-up loader
✔ Role preference
✔ Region selection
✔ Dynamic Game → Region mapping
✔ Styling animation triggers

**Key logged output:**
✔ `[TeamCreateEnhanced] Script loaded`
✔ `[TeamCreateEnhanced] Initialized successfully`

---

## 🔹 **2.2 Team List Scripts**

### **team-list-premium.js**

**Used by:** `list.html`

**Controls:**

* Premium grid layout
* Filtering buttons
* Game chips
* Team card hover animations
* Event listeners for "Join"
* Global `quickJoin()` reference (MUST be defined globally)

**Known issue (important):**

```
quickJoin is not defined
```

Copilot MUST fix by adding:

```
window.quickJoin = function (slug) { ... }
```

---

### **team-list-vlr-style.js**

**Used by:** list grid alternative

**Controls:**

* Valorant-style UI
* Game category classifier
* Rebuilds list dynamically
* Stores teams in JS memory
* Reads card DOM attributes

---

## 🔹 **2.3 Team Detail Scripts**

### **team-leave-modern.js**

**Used by:** `_team_hub.html` → Leave team

**Controls:**

* Leave modal open/close
* Dark glassy modal animation
* AJAX submission of leave request
* Toast notifications

**Critical requirement:**
Server must **return JSON**, not redirect.

---

### **team-dashboard.js**

(Used by: `dashboard_modern.html`)

**Controls:**

* Recent activity polling
* Pending items
* Card animations
* Statistics widgets

---

### **team-join.js**

**Used by:** Join modal or join button

Controls:

* Open join modal
* Validate join requirements
* Submit join request

---

### **team-uploads.js**

Used by: team settings/manage pages
Controls:

* Live preview for logos/banners
* File size/type validation

---

### **team-roster-order.js**

Used by: roster drag+drop
Controls:

* Drag sorting
* AJAX save order

---

## 🔹 **2.4 Discussion Scripts**

### discussion.js

Used by: discussion board
Controls:

* Markdown preview
* Expand/collapse posts
* Reaction interactions

---

## 🔹 **2.5 Chat Scripts**

### team-chat.js

Used by: team_chat.html
Controls:

* WebSocket connection
* Typing indicator
* Message rendering
* Scroll locking
* Message reactions

---

# 🟦 **3. CSS Files (Full Inventory)**

### **team-create-esports.css**

Formal esports styling for create wizard.
Includes neon borders, animated step transitions.

### **team-create.css**

Basic version of create wizard styling.

---

### **team-list.css**

Styles for team cards grid layout.

### **team-list-vlr.css**

Valorant aesthetic (red/cyan contrast with CAPS headings).

---

### **team-detail-new.css**

Controls:

* Hero banner
* Tab bar
* Team hub
* Esports glassy effects

---

### **tabs.css / tabs-enhanced.css**

Tab variants.

---

### **dashboard.css / dashboard_modern.css**

Controls:

* Dashboard cards
* Activity feed
* Metrics grid

---

### **roster-esports.css / roster-eclipse.css**

Two designs for the roster section.

---

### **player-modal-eclipse.css**

Modal for player role assignment.

---

### **overview-enhanced.css**

Style for team overview widgets.

---

### **responsive.css**

Breakpoints for mobile/tablet.

---

# 🟦 **4. Image Assets (Full Inventory)**

## Game card images (used in Step 2)

Located in:

```
static/img/game_cards/
```

Files required:

```
CallOfDutyMobile.jpg
CS2.jpg
Dota2.jpg
efootball.jpeg
FC26.jpg
FreeFire.jpeg
MobileLegend.jpg
PUBG.jpeg
Valorant.jpg
```

Copilot must ensure:

* Paths are correct
* Templates reference them through `{% static %}`
* All capital letters are respected

---

# 🟥 5. Known Static Bugs (MUST FIX)

### **BUG 1: quickJoin is not defined**

Occurs on `/teams/`
Root cause: JS file not attaching to window.
Fix: `window.quickJoin = ...`

---

### **BUG 2: 404 default_game_logo.jpg**

Reason: Path wrong or asset missing.

---

### **BUG 3: Game card images not loading**

Cause:

* Wrong filename case
* Missing assets
* Missing `{% static %}`
* JS/HTML pointing to old paths

---

### **BUG 4: Static pipeline mismatch**

Copilot must ensure:

* All assets exist in `/static/`
* No reference to `/staticfiles/`
* Use `{% static %}` everywhere
* If images stored incorrectly, move them

---

### **BUG 5: Create wizard errors invisible**

Some error messages are not styled.
Copilot must implement:

* Scroll-to-first-error
* Error badge per field
* Highlight step navigation

---

### **BUG 6: team-leave-modern.js expects JSON but server returns redirect**

Must convert `/leave/` view to JSON-compatible.

---

# 🟦 **6. Static Pipeline Guidelines**

### Development:

* Django serves `/static/` directly
* No hashing

### Production:

* `collectstatic` generates `/staticfiles/`
* Inlined hashed filenames
* Must run:

```
python manage.py collectstatic --clear
```

---

# 🟩 **7. How Copilot Must Modify Static Files (Rules)**

1. Never touch hashed files inside `/staticfiles/`
2. Modify source files only in `/static/teams/...`
3. Always reference assets via `{% static %}`
4. JS functions that must be global → attach to `window.*`
5. Large components must stay consistent with esports theme
6. Never break existing animations
7. Use minimal invasive edits unless rewriting a full component

---


---

# UPDATED: Modern Team Create Static Files

Added November 19, 2025

## New Static Files

### team-create-modern.css
**Path:** static/teams/css/team-create-modern.css
**Size:** 1,400+ lines
**Purpose:** Premium glassmorphism styling for 4-step wizard

**Key Features:**
- CSS Variables for theming (colors, backgrounds, borders)
- Progress bar with pulse and checkPop animations
- Game cards grid with hover/selected states
- Region selector cards
- File upload zones with drag-drop styling
- Live preview card (sticky sidebar)
- Terms box with scrollable content + custom checkbox
- Validation feedback states (checking, valid, invalid)
- Alert boxes (error, info)
- Button styles (primary, secondary, success)
- Loading overlay with spinner
- Responsive breakpoints (@media max-width: 768px)

**Design System:**
- Dark theme: #0a0e1a background
- Glassmorphism: backdrop-filter blur(20px)
- Primary colors: cyan (#00d9ff), purple (#8b5cf6), pink (#ff006e), gold (#ffbe0b)
- Card BG: rgba(15, 20, 35, 0.85)
- Borders: rgba(255, 255, 255, 0.1)

### team-create-modern.js
**Path:** static/teams/js/team-create-modern.js
**Size:** ~900 lines
**Purpose:** Complete wizard logic with AJAX

**Class:** TeamCreateModern
**Methods:**
- setupStepNavigation() - prev/next buttons
- goToStep(n) - update progress bar, show/hide steps
- validateCurrentStep() - per-step validation logic
- validateTeamName(name) - AJAX uniqueness check
- validateTeamTag(tag) - AJAX uniqueness check
- setupGameCards() - render game grid from config
- selectGame(code) - handle game selection
- checkExistingTeam(code) - one-team-per-game AJAX
- loadGameRegions(code) - dynamic region loading
- selectRegion(code, name) - region selection
- setupFileUploads() - drag-drop + click handlers
- handleFileUpload(file, preview, type) - FileReader preview
- updatePreview(field, value) - live preview updates
- populateSummary() - fill Step 4 summary card
- setupTermsCheckbox() - validation binding
- validateStep4() - terms acceptance check
- setupFormSubmission() - AJAX submit with loading
- showToast(message, type) - notifications

**AJAX Endpoints Used:**
- GET /teams/api/validate-name/?name={name}
- GET /teams/api/validate-tag/?tag={tag}
- GET /teams/api/check-existing-team/?game={code}
- GET /teams/api/game-regions/{code}/
- POST /teams/create/ (form submission)

**Config:** window.TEAM_CREATE_CONFIG passed from Django

## Game Card Images
**Path:** static/img/game_cards/
**Files (verified exist):**
- Valorant.jpg
- CS2.jpg
- Dota2.jpg
- MobileLegend.jpg
- PUBG.jpeg
- FreeFire.jpeg
- CallOfDutyMobile.jpg
- efootball.jpeg
- FC26.jpg

## Backup Files
- team-create-esports.css.backup (old version)
- team-create-esports.js.backup (old version)
- team-create-modern.js.v3backup (replaced 5-step version)

See TEAM_APP_FUNCTIONAL_SPEC.md Section 14 for complete documentation.
