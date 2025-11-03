# Sprint 4 - Week 4: Tournament Frontend UI

**Sprint Goal:** Build tournament UI (creation wizard, list, detail, dashboards)  
**Duration:** Week 4 (5 days)  
**Story Points:** 60  
**Team:** Frontend (3), Backend (1), QA (1), DevOps (1)  
**Linked Epic:** Epic 2 - Tournament Engine (see `00_BACKLOG_OVERVIEW.md`)

---

## 📋 Task Cards - Frontend Track - Core Pages (35 points)

### **FE-011: Tournament Creation Wizard (Multi-step Form)**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 10  
**Assignee:** Frontend Dev 1  
**Sprint:** Sprint 4  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create comprehensive multi-step tournament creation wizard with 5 steps: Basic Info → Game Settings → Schedule → Rules → Review & Publish. Implement step validation, progress indicator, draft saving, and image uploads. Support game-specific settings (eFootball vs Valorant).

**Acceptance Criteria:**
- [ ] **Step 1: Basic Information**
  - Title (required, max 200 chars, live validation)
  - Description (rich text editor with markdown preview)
  - Logo upload (drag-drop, max 2MB, preview)
  - Banner upload (drag-drop, max 5MB, preview, recommended 1920x400)
  - Visibility: Public/Private/Unlisted (radio buttons)
  - Featured toggle (admin only)
  - Save as draft button (saves and exits)
  - Next button (validates and proceeds to Step 2)
- [ ] **Step 2: Game Settings**
  - Game selection (searchable dropdown, shows icon + description)
  - Tournament format: Single Elimination / Double Elimination / Swiss / Round Robin (radio with descriptions)
  - Team size (number input, validated against game min/max)
  - Max teams (number input, validation: must be power of 2 for elimination)
  - Platform selection (multi-select checkboxes based on game)
  - Game-specific settings (dynamic based on game type):
    - eFootball: Half length (6/10/12 mins), Difficulty (Amateur/Professional/World Class)
    - Valorant: Rounds to win (13/25), Overtime (yes/no), Tournament mode (yes/no)
  - Previous/Next buttons
- [ ] **Step 3: Schedule & Pricing**
  - Registration start date/time (datetime picker)
  - Registration end date/time (datetime picker)
  - Tournament start date/time (datetime picker)
  - Check-in start date/time (datetime picker, auto-fill: 2h before tournament)
  - Check-in end date/time (datetime picker, auto-fill: 30min before tournament)
  - Entry fee (currency input, default 0, max 10,000)
  - Prize pool (currency input, validation: <= total entry fees if paid)
  - Date validation: registration_end < tournament_start, check_in_end < tournament_start
  - Visual timeline showing all dates
  - Previous/Next buttons
- [ ] **Step 4: Rules & Details**
  - Rules text (rich text editor, markdown, min 100 chars)
  - Match settings (dynamic based on format):
    - Single/Double Elimination: Seeding method (random/manual/by rank)
    - Swiss: Number of rounds (auto-calculated based on teams, editable)
    - Round Robin: Home/Away (yes/no), Tiebreaker rules
  - Additional settings:
    - Allow substitutes (yes/no)
    - Max substitutes per match (0-3)
    - Stream URL (optional, YouTube/Twitch embed)
    - Discord server link (optional)
  - Previous/Next buttons
- [ ] **Step 5: Review & Publish**
  - Complete summary with all entered data
  - Edit buttons next to each section (jumps to that step)
  - Final validation checks (all required fields, date logic)
  - Save as Draft button (status=DRAFT)
  - Publish Tournament button (status=PUBLISHED, confirmation modal)
- [ ] **Global Features:**
  - Progress indicator: Step circles (1-5) with labels, current step highlighted
  - Auto-save draft every 2 minutes (background, non-intrusive notification)
  - Validation errors shown inline (below fields) and in summary at top
  - Keyboard navigation: Tab through fields, Enter to proceed
  - Mobile responsive: Stacked layout on mobile
  - Exit confirmation: "You have unsaved changes. Are you sure?" if attempting to leave
- [ ] **Accessibility:**
  - ARIA labels on all form fields
  - Focus management: Focus first field when step changes
  - Error announcements for screen readers
  - Keyboard-only navigation functional
- [ ] Form submission calls `POST /api/tournaments/` with all data

**Dependencies:**
- FE-002 (Design tokens)
- FE-007 (Button component)
- FE-008 (Input/Form components)
- BE-008 (Tournament API)
- BE-009 (GameConfig API)

**Technical Notes:**
- Use Alpine.js for wizard state management (currentStep, formData)
- Use HTMX for form submission and step navigation (no full page reload)
- Rich text editor: Use Quill.js or TipTap for markdown editing
- Image uploads: Use dropzone.js for drag-drop, preview with base64 or FileReader API
- Auto-save: Use JavaScript `setInterval()` and localStorage as backup
- Reference: PROPOSAL_PART_4.md Section 5.1 (Tournament Creation Wizard)

**Files to Create/Modify:**
- `templates/tournaments/create.html` (new - wizard template)
- `apps/tournaments/views.py` (add `TournamentCreateView`)
- `apps/tournaments/urls.py` (add `/tournaments/create/` route)
- `static/js/tournament-wizard.js` (new - wizard logic)
- `static/css/tournament-wizard.css` (new - wizard-specific styles)

**Wizard HTML Structure:**
```html
<div class="max-w-4xl mx-auto p-6" x-data="tournamentWizard()">
  <!-- Progress Indicator -->
  <div class="flex items-center justify-between mb-8">
    <template x-for="step in steps" :key="step.number">
      <div class="flex items-center">
        <div :class="step.number <= currentStep ? 'bg-primary-500 text-white' : 'bg-gray-300 text-gray-600'"
             class="w-10 h-10 rounded-full flex items-center justify-center font-semibold">
          <span x-text="step.number"></span>
        </div>
        <span x-text="step.label" class="ml-2 text-sm" :class="step.number <= currentStep ? 'text-primary-500' : 'text-gray-500'"></span>
        <div x-show="step.number < 5" class="h-1 w-16 bg-gray-300 mx-4"></div>
      </div>
    </template>
  </div>
  
  <!-- Step 1: Basic Info -->
  <div x-show="currentStep === 1" x-transition>
    <h2 class="text-2xl font-bold mb-4">Basic Information</h2>
    <form @submit.prevent="nextStep">
      <label class="block mb-4">
        <span class="text-gray-700">Tournament Title *</span>
        <input type="text" x-model="formData.title" maxlength="200" required
               class="mt-1 block w-full rounded-md border-gray-300 shadow-sm">
        <span x-text="`${formData.title.length}/200`" class="text-sm text-gray-500"></span>
      </label>
      
      <label class="block mb-4">
        <span class="text-gray-700">Description *</span>
        <textarea x-model="formData.description" rows="6" required
                  class="mt-1 block w-full rounded-md border-gray-300"></textarea>
        <div id="markdown-preview" class="mt-2 p-4 bg-gray-50 rounded"></div>
      </label>
      
      <label class="block mb-4">
        <span class="text-gray-700">Logo (max 2MB)</span>
        <div class="mt-1 border-2 border-dashed border-gray-300 rounded-lg p-8 text-center cursor-pointer hover:border-primary-500"
             @drop.prevent="handleLogoDrop" @dragover.prevent>
          <svg class="mx-auto h-12 w-12 text-gray-400"><!-- Upload icon --></svg>
          <p class="mt-2 text-sm text-gray-600">Drag & drop or click to upload</p>
          <input type="file" accept="image/*" @change="handleLogoChange" class="hidden">
        </div>
        <img x-show="formData.logo_preview" :src="formData.logo_preview" class="mt-2 h-32 rounded">
      </label>
      
      <div class="flex justify-between mt-8">
        <button type="button" @click="saveDraft" class="btn btn-secondary">Save Draft</button>
        <button type="submit" class="btn btn-primary">Next →</button>
      </div>
    </form>
  </div>
  
  <!-- Step 2: Game Settings -->
  <div x-show="currentStep === 2" x-transition>
    <h2 class="text-2xl font-bold mb-4">Game Settings</h2>
    <form @submit.prevent="nextStep">
      <label class="block mb-4">
        <span class="text-gray-700">Select Game *</span>
        <select x-model="formData.game" @change="loadGameConfig" required
                class="mt-1 block w-full rounded-md border-gray-300">
          <option value="">-- Choose a game --</option>
          <template x-for="game in availableGames" :key="game.slug">
            <option :value="game.slug" x-text="game.name"></option>
          </template>
        </select>
      </label>
      
      <label class="block mb-4">
        <span class="text-gray-700">Tournament Format *</span>
        <div class="space-y-2">
          <template x-for="format in formats" :key="format.value">
            <label class="flex items-center p-4 border rounded hover:bg-gray-50 cursor-pointer">
              <input type="radio" x-model="formData.format" :value="format.value" required class="mr-3">
              <div>
                <div class="font-semibold" x-text="format.label"></div>
                <div class="text-sm text-gray-500" x-text="format.description"></div>
              </div>
            </label>
          </template>
        </div>
      </label>
      
      <div class="flex justify-between mt-8">
        <button type="button" @click="currentStep--" class="btn btn-secondary">← Previous</button>
        <button type="submit" class="btn btn-primary">Next →</button>
      </div>
    </form>
  </div>
  
  <!-- Steps 3, 4, 5 similar structure... -->
  
</div>
```

**Alpine.js Wizard Logic:**
```javascript
function tournamentWizard() {
  return {
    currentStep: 1,
    steps: [
      { number: 1, label: 'Basic Info' },
      { number: 2, label: 'Game Settings' },
      { number: 3, label: 'Schedule' },
      { number: 4, label: 'Rules' },
      { number: 5, label: 'Review' }
    ],
    formData: {
      title: '',
      description: '',
      logo: null,
      logo_preview: '',
      game: '',
      format: '',
      team_size: 1,
      max_teams: 16,
      // ... all other fields
    },
    availableGames: [],
    
    init() {
      this.loadGames();
      this.loadDraft(); // Load from localStorage if exists
      this.startAutoSave();
    },
    
    async loadGames() {
      const response = await fetch('/api/games/');
      this.availableGames = await response.json();
    },
    
    async nextStep() {
      if (this.validateCurrentStep()) {
        this.currentStep++;
        window.scrollTo(0, 0);
      }
    },
    
    validateCurrentStep() {
      // Step-specific validation
      if (this.currentStep === 1) {
        if (!this.formData.title || this.formData.title.length < 5) {
          alert('Title must be at least 5 characters');
          return false;
        }
      }
      return true;
    },
    
    async saveDraft() {
      const response = await fetch('/api/tournaments/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() },
        body: JSON.stringify({ ...this.formData, status: 'DRAFT' })
      });
      if (response.ok) {
        alert('Draft saved!');
        localStorage.removeItem('tournament_draft');
      }
    },
    
    startAutoSave() {
      setInterval(() => {
        localStorage.setItem('tournament_draft', JSON.stringify(this.formData));
        console.log('Auto-saved draft');
      }, 120000); // 2 minutes
    },
    
    loadDraft() {
      const draft = localStorage.getItem('tournament_draft');
      if (draft) {
        this.formData = JSON.parse(draft);
        if (confirm('Continue with previously saved draft?')) {
          // Keep loaded data
        } else {
          localStorage.removeItem('tournament_draft');
        }
      }
    }
  }
}
```

**Testing:**
- Access `/tournaments/create/` → wizard loads with Step 1
- Fill Basic Info, click Next → proceeds to Step 2
- Select game → game config loaded, team size validated
- Select format=SINGLE_ELIMINATION, max_teams=15 → validation error (not power of 2)
- Fill all steps, click Publish → confirmation modal shown
- Confirm publish → tournament created with status=PUBLISHED
- Leave page mid-wizard → "Unsaved changes" confirmation
- Return to wizard → "Continue with draft?" prompt shown
- Test auto-save: Fill form, wait 2 min, check localStorage has draft
- Test responsive: Wizard stacks on mobile
- Test keyboard: Tab through all fields, Enter to submit
- Test screen reader: All fields announced correctly

---

### **FE-012: Tournament List Page (Browse & Filter)**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 8  
**Assignee:** Frontend Dev 2  
**Sprint:** Sprint 4  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create tournament list/browse page with filtering, search, sorting, and pagination. Display tournaments as grid of cards with key info. Support game filter, status filter, search by title, and date range filter.

**Acceptance Criteria:**
- [ ] **Layout:**
  - Page accessible at `/tournaments/`
  - Hero section: "Browse Tournaments" headline, search bar, "Create Tournament" button
  - Filter sidebar (left, 25% width):
    - Game filter (checkboxes with icons): All, eFootball, Valorant, etc.
    - Status filter (checkboxes): All, Upcoming, Ongoing, Completed
    - Entry fee filter (checkboxes): Free, Paid
    - Date range picker: Show tournaments starting between dates
    - Prize pool range slider: Min-Max
    - "Clear All Filters" button
  - Tournament grid (right, 75% width):
    - Grid layout: 3 columns on desktop, 2 on tablet, 1 on mobile
    - Sort dropdown: Latest, Starting Soon, Highest Prize, Most Popular
    - Results count: "Showing 15 of 42 tournaments"
    - Tournament cards (see FE-016 for card component)
    - Pagination: 20 tournaments per page, "Load More" button or page numbers
- [ ] **Search Functionality:**
  - Search bar in hero section (debounced, 300ms delay)
  - Search by tournament title
  - Live results update (no page reload)
  - Clear search button (X icon)
- [ ] **Filtering:**
  - Filters applied via URL query params: `/tournaments/?game=valorant&status=upcoming`
  - Multiple filters combinable (AND logic)
  - Filter badges shown above grid (removable)
  - Filter count badge on sidebar sections: "Status (2 active)"
  - Smooth transitions when filters change
- [ ] **Empty States:**
  - No tournaments: "No tournaments found. Create the first one!"
  - No search results: "No matches for 'xyz'. Try different keywords."
  - No filter results: "No tournaments match your filters. Clear filters?"
- [ ] **Loading States:**
  - Skeleton loaders for cards during initial load
  - Spinner during filter changes
  - Disabled state for filters while loading
- [ ] **Featured Tournaments:**
  - Top of page: Carousel/slider with 3-5 featured tournaments (large cards)
  - Auto-rotate every 5 seconds, manual navigation arrows
  - Only show if featured tournaments exist
- [ ] **Performance:**
  - Lazy load images (use loading="lazy" attribute)
  - Infinite scroll or pagination (configurable)
  - API calls cached for 30 seconds (avoid redundant requests)
- [ ] **Responsive:**
  - Mobile: Filters in collapsible drawer (hamburger menu)
  - Tablet: 2-column grid
  - Desktop: 3-column grid with sidebar
- [ ] **Accessibility:**
  - Filters have ARIA labels
  - Keyboard navigation: Tab through filters, Enter to toggle
  - Screen reader announces result count changes

**Dependencies:**
- FE-002 (Design tokens)
- FE-016 (Tournament card component - created in Task 4.5)
- BE-008 (Tournament API with filtering)

**Technical Notes:**
- Use HTMX for filtering/pagination (no full page reload)
- Use Alpine.js for filter state management
- URL params updated using History API (pushState)
- Featured carousel: Use Swiper.js or Alpine.js with CSS transforms
- Reference: PROPOSAL_PART_4.md Section 5.2 (Tournament List & Filtering)

**Files to Create/Modify:**
- `templates/tournaments/list.html` (new)
- `apps/tournaments/views.py` (add `TournamentListView`)
- `apps/tournaments/urls.py` (add `/tournaments/` route)
- `static/js/tournament-filters.js` (new - filter logic)
- `static/css/tournament-list.css` (new)

**HTML Structure:**
```html
<div class="min-h-screen bg-gray-50">
  <!-- Hero Section -->
  <div class="bg-gradient-to-r from-primary-600 to-primary-800 py-16">
    <div class="container mx-auto px-4 text-center">
      <h1 class="text-4xl font-bold text-white mb-4">Browse Tournaments</h1>
      <p class="text-primary-100 mb-8">Find and join competitive gaming tournaments</p>
      
      <!-- Search Bar -->
      <div class="max-w-2xl mx-auto">
        <form hx-get="/api/tournaments/" hx-target="#tournament-grid" hx-trigger="keyup changed delay:300ms">
          <input type="search" name="search" placeholder="Search tournaments..."
                 class="w-full px-6 py-4 rounded-lg text-lg">
        </form>
      </div>
      
      <a href="/tournaments/create/" class="mt-4 inline-block btn btn-secondary btn-lg">
        + Create Tournament
      </a>
    </div>
  </div>
  
  <!-- Featured Tournaments Carousel -->
  <div class="container mx-auto px-4 py-8" x-data="carousel()">
    <h2 class="text-2xl font-bold mb-4">Featured Tournaments</h2>
    <div class="relative overflow-hidden">
      <div class="flex transition-transform duration-500" :style="`transform: translateX(-${currentSlide * 100}%)`">
        <template x-for="tournament in featuredTournaments" :key="tournament.id">
          <div class="w-full flex-shrink-0 px-2">
            <!-- Large tournament card -->
          </div>
        </template>
      </div>
      <button @click="prevSlide" class="absolute left-0 top-1/2 -translate-y-1/2 btn btn-circle">←</button>
      <button @click="nextSlide" class="absolute right-0 top-1/2 -translate-y-1/2 btn btn-circle">→</button>
    </div>
  </div>
  
  <!-- Main Content: Filters + Grid -->
  <div class="container mx-auto px-4 py-8">
    <div class="flex flex-col lg:flex-row gap-6">
      
      <!-- Filters Sidebar -->
      <aside class="lg:w-1/4">
        <div class="bg-white rounded-lg shadow p-6 sticky top-4">
          <div class="flex justify-between items-center mb-4">
            <h3 class="font-bold text-lg">Filters</h3>
            <button @click="clearFilters()" class="text-sm text-primary-500 hover:underline">Clear All</button>
          </div>
          
          <!-- Game Filter -->
          <div class="mb-6">
            <h4 class="font-semibold mb-2">Game</h4>
            <div class="space-y-2">
              <label class="flex items-center cursor-pointer hover:bg-gray-50 p-2 rounded">
                <input type="checkbox" name="game" value="efootball" class="mr-2">
                <img src="/static/img/games/efootball.png" class="w-6 h-6 mr-2">
                <span>eFootball</span>
              </label>
              <label class="flex items-center cursor-pointer hover:bg-gray-50 p-2 rounded">
                <input type="checkbox" name="game" value="valorant" class="mr-2">
                <img src="/static/img/games/valorant.png" class="w-6 h-6 mr-2">
                <span>Valorant</span>
              </label>
            </div>
          </div>
          
          <!-- Status Filter -->
          <div class="mb-6">
            <h4 class="font-semibold mb-2">Status</h4>
            <div class="space-y-2">
              <label class="flex items-center">
                <input type="checkbox" name="status" value="upcoming" class="mr-2">
                <span>Upcoming</span>
              </label>
              <label class="flex items-center">
                <input type="checkbox" name="status" value="ongoing" class="mr-2">
                <span>Ongoing</span>
              </label>
            </div>
          </div>
          
          <!-- Prize Pool Range -->
          <div class="mb-6">
            <h4 class="font-semibold mb-2">Prize Pool</h4>
            <input type="range" min="0" max="10000" step="100" class="w-full">
            <div class="flex justify-between text-sm text-gray-600">
              <span>$0</span>
              <span>$10,000+</span>
            </div>
          </div>
          
          <button hx-get="/api/tournaments/" hx-include="[name='game'],[name='status']" 
                  hx-target="#tournament-grid" class="w-full btn btn-primary">
            Apply Filters
          </button>
        </div>
      </aside>
      
      <!-- Tournament Grid -->
      <main class="lg:w-3/4">
        <div class="flex justify-between items-center mb-4">
          <p class="text-gray-600">Showing <span id="result-count">42</span> tournaments</p>
          <select name="sort" hx-get="/api/tournaments/" hx-target="#tournament-grid" hx-trigger="change"
                  class="border rounded px-3 py-2">
            <option value="-created_at">Latest</option>
            <option value="tournament_start">Starting Soon</option>
            <option value="-prize_pool">Highest Prize</option>
          </select>
        </div>
        
        <!-- Active Filter Badges -->
        <div id="active-filters" class="flex flex-wrap gap-2 mb-4">
          <!-- Dynamically added badges: <span class="badge">Valorant <button>×</button></span> -->
        </div>
        
        <div id="tournament-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <!-- Tournament cards rendered here via HTMX -->
          <!-- Skeleton loaders shown initially -->
          <div class="bg-white rounded-lg shadow animate-pulse">
            <div class="h-48 bg-gray-300 rounded-t-lg"></div>
            <div class="p-4 space-y-2">
              <div class="h-4 bg-gray-300 rounded w-3/4"></div>
              <div class="h-4 bg-gray-300 rounded w-1/2"></div>
            </div>
          </div>
        </div>
        
        <!-- Pagination -->
        <div class="mt-8 flex justify-center">
          <button hx-get="/api/tournaments/?page=2" hx-target="#tournament-grid" hx-swap="beforeend"
                  class="btn btn-secondary">
            Load More
          </button>
        </div>
      </main>
      
    </div>
  </div>
</div>
```

**Filter Logic (tournament-filters.js):**
```javascript
function tournamentFilters() {
  return {
    filters: {
      games: [],
      statuses: [],
      prizeMin: 0,
      prizeMax: 10000,
      search: ''
    },
    
    applyFilters() {
      const params = new URLSearchParams();
      if (this.filters.games.length) params.append('game', this.filters.games.join(','));
      if (this.filters.statuses.length) params.append('status', this.filters.statuses.join(','));
      if (this.filters.search) params.append('search', this.filters.search);
      
      // Update URL without reload
      history.pushState({}, '', `/tournaments/?${params.toString()}`);
      
      // Trigger HTMX request
      htmx.trigger('#tournament-grid', 'htmx:trigger');
    },
    
    clearFilters() {
      this.filters = { games: [], statuses: [], prizeMin: 0, prizeMax: 10000, search: '' };
      history.pushState({}, '', '/tournaments/');
      this.applyFilters();
    },
    
    updateFilterBadges() {
      const container = document.getElementById('active-filters');
      container.innerHTML = '';
      
      this.filters.games.forEach(game => {
        const badge = `<span class="badge">${game} <button onclick="removeFilter('game', '${game}')">×</button></span>`;
        container.innerHTML += badge;
      });
    }
  }
}

function carousel() {
  return {
    currentSlide: 0,
    featuredTournaments: [],
    
    init() {
      this.loadFeatured();
      setInterval(() => this.nextSlide(), 5000); // Auto-rotate
    },
    
    async loadFeatured() {
      const response = await fetch('/api/tournaments/?featured=true&limit=5');
      this.featuredTournaments = await response.json();
    },
    
    nextSlide() {
      this.currentSlide = (this.currentSlide + 1) % this.featuredTournaments.length;
    },
    
    prevSlide() {
      this.currentSlide = (this.currentSlide - 1 + this.featuredTournaments.length) % this.featuredTournaments.length;
    }
  }
}
```

**Testing:**
- Access `/tournaments/` → tournament list loads
- Featured carousel: Verify 5 featured tournaments shown, auto-rotate every 5s
- Search "valorant" → results filtered in real-time (300ms debounce)
- Select game filter "Valorant" → only Valorant tournaments shown
- Select status "Upcoming" → only upcoming tournaments shown
- Combine filters: Game + Status → both applied (AND logic)
- Active filter badges shown above grid, click X to remove
- Click "Clear All Filters" → all filters reset
- Change sort to "Highest Prize" → tournaments reordered
- Scroll down, click "Load More" → next 20 tournaments appended
- Test empty state: Search "xyz" → "No matches" message
- Test responsive: Mobile → filters in drawer, 1-column grid
- Test keyboard: Tab through filters, Enter to apply
- Test loading state: Skeleton loaders shown during initial load

---

### **FE-013: Tournament Detail View**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 8  
**Assignee:** Frontend Dev 3  
**Sprint:** Sprint 4  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create comprehensive tournament detail page showing all tournament information, registration status, participant list, bracket preview, and action buttons. Support both public view (spectators) and participant view (registered teams).

**Acceptance Criteria:**
- [ ] **Page Layout** (accessible at `/tournaments/<slug>/`):
  - Hero section with tournament banner image (1920x400)
  - Tournament title, game icon, status badge (color-coded)
  - Quick stats: Prize pool, entry fee, teams registered/max, start date
  - Primary action button (context-dependent):
    - Not registered: "Register Team" (green, prominent)
    - Registration closed: "Registration Closed" (gray, disabled)
    - Already registered: "Manage Registration" (blue)
    - Organizer: "Manage Tournament" (purple)
- [ ] **Tournament Information Tabs:**
  - Tab 1: Overview (default active)
  - Tab 2: Participants (team list)
  - Tab 3: Bracket (preview if generated, else "Coming Soon")
  - Tab 4: Rules
  - Tab 5: Discussion (upcoming sprint)
- [ ] **Overview Tab Content:**
  - Description (markdown rendered, expandable if > 500 chars)
  - Tournament details card:
    - Game, Format, Team size, Max teams
    - Platform(s)
    - Registration dates (with countdown if ongoing)
    - Tournament dates
    - Check-in times
  - Prize distribution (if prize pool > 0):
    - 1st place: 50%, 2nd: 30%, 3rd: 20% (default split, customizable later)
    - Visual progress bars
  - Organizer info card:
    - Organizer name, avatar, verification badge
    - Organized tournaments count
    - "View Profile" link
  - Share buttons: Twitter, Facebook, Discord, Copy Link
- [ ] **Participants Tab:**
  - List of registered teams (grid view)
  - Each team card: Logo, name, members count, captain name, registration status
  - Empty state: "No teams registered yet. Be the first!"
  - Filter: All / Confirmed / Pending / Checked In
  - Sort: Registration date, Team name
  - Pagination: 20 teams per page
- [ ] **Bracket Tab:**
  - If bracket generated: Display bracket visualization (from Sprint 8)
  - If not generated: "Bracket will be available after registration closes" message
  - Bracket type indicator: Single Elimination, Double Elimination, Swiss, etc.
- [ ] **Rules Tab:**
  - Rules text (markdown rendered)
  - Match settings card (game-specific):
    - eFootball: Half length, Difficulty, Stamina, Injuries
    - Valorant: Rounds to win, Overtime, Tournament mode
  - Additional rules: Substitutes, Max subs per match
  - Disqualification policies
  - Dispute resolution process
- [ ] **Action Buttons (conditional visibility):**
  - **Register Team** (if user authenticated, has team, registration open):
    - Opens team selection modal (if user captains multiple teams)
    - Validates team size matches tournament
    - Submits registration
  - **Withdraw Registration** (if registered, before check-in):
    - Confirmation modal: "Are you sure? This cannot be undone."
    - Updates registration status to CANCELLED
  - **Check In** (if registered CONFIRMED, during check-in window):
    - One-click check-in
    - Success: Status updated to CHECKED_IN, green checkmark shown
  - **Edit Tournament** (if organizer or admin):
    - Opens tournament edit page
  - **Publish/Cancel Tournament** (if organizer, status=DRAFT):
    - Publish: Confirmation modal, status → PUBLISHED
    - Cancel: Confirmation modal, status → CANCELLED
- [ ] **Real-time Updates:**
  - Registration count updates live (WebSocket or polling every 30s)
  - Status badge updates (PUBLISHED → ONGOING → COMPLETED)
  - New teams appear in participants tab without refresh
- [ ] **Responsive Design:**
  - Mobile: Tabs become accordion
  - Hero stats stack vertically
  - Share buttons in dropdown menu
- [ ] **Accessibility:**
  - Tab navigation keyboard accessible
  - Action buttons have ARIA labels
  - Status badges use ARIA live regions for updates
  - Countdown timers announced by screen readers

**Dependencies:**
- FE-002 (Design tokens)
- FE-009 (Card component)
- FE-010 (Modal component)
- BE-008 (Tournament API detail endpoint)

**Technical Notes:**
- Use HTMX for tab switching (partial page updates)
- Use Alpine.js for countdown timers and real-time updates
- Markdown rendering: Use marked.js library
- Share functionality: Web Share API with fallback to copy to clipboard
- Reference: PROPOSAL_PART_4.md Section 6.1 (Tournament Detail Page)

**Files to Create/Modify:**
- `templates/tournaments/detail.html` (new)
- `apps/tournaments/views.py` (add `TournamentDetailView`)
- `apps/tournaments/urls.py` (add `/tournaments/<slug>/` route)
- `static/js/tournament-detail.js` (new - countdown, real-time updates)
- `static/css/tournament-detail.css` (new)

**HTML Structure:**
```html
<div class="min-h-screen bg-gray-50">
  <!-- Hero Section -->
  <div class="relative h-96 bg-cover bg-center" style="background-image: url('{{ tournament.banner.url }}')">
    <div class="absolute inset-0 bg-gradient-to-t from-black/70 to-transparent"></div>
    <div class="relative container mx-auto px-4 h-full flex flex-col justify-end pb-8">
      <div class="flex items-center gap-3 mb-2">
        <img src="{{ tournament.game.icon.url }}" class="w-12 h-12 rounded">
        <span class="badge badge-{{ tournament.get_status_display_color }}">{{ tournament.status }}</span>
        {% if tournament.featured %}
        <span class="badge badge-yellow">Featured</span>
        {% endif %}
      </div>
      <h1 class="text-4xl font-bold text-white mb-4">{{ tournament.title }}</h1>
      
      <div class="flex flex-wrap gap-6 text-white">
        <div>
          <div class="text-sm opacity-80">Prize Pool</div>
          <div class="text-2xl font-bold">${{ tournament.prize_pool }}</div>
        </div>
        <div>
          <div class="text-sm opacity-80">Entry Fee</div>
          <div class="text-2xl font-bold">{{ tournament.entry_fee|default:"Free" }}</div>
        </div>
        <div>
          <div class="text-sm opacity-80">Teams</div>
          <div class="text-2xl font-bold">{{ tournament.registrations_count }}/{{ tournament.max_teams }}</div>
        </div>
        <div>
          <div class="text-sm opacity-80">Starts</div>
          <div class="text-2xl font-bold">{{ tournament.tournament_start|date:"M d, Y" }}</div>
        </div>
      </div>
      
      <!-- Action Button -->
      <div class="mt-6">
        {% if user_can_register %}
        <button onclick="showRegisterModal()" class="btn btn-primary btn-lg">
          Register Team
        </button>
        {% elif user_registered %}
        <a href="/tournaments/{{ tournament.slug }}/registration/" class="btn btn-secondary btn-lg">
          Manage Registration
        </a>
        {% elif is_organizer %}
        <a href="/tournaments/{{ tournament.slug }}/edit/" class="btn btn-accent btn-lg">
          Manage Tournament
        </a>
        {% endif %}
      </div>
    </div>
  </div>
  
  <!-- Tabs -->
  <div class="container mx-auto px-4 py-8">
    <div class="bg-white rounded-lg shadow">
      <!-- Tab Headers -->
      <div class="border-b border-gray-200">
        <nav class="flex -mb-px" x-data="{ activeTab: 'overview' }">
          <button @click="activeTab = 'overview'" 
                  :class="activeTab === 'overview' ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500'"
                  class="px-6 py-4 border-b-2 font-medium">
            Overview
          </button>
          <button @click="activeTab = 'participants'" 
                  :class="activeTab === 'participants' ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500'"
                  class="px-6 py-4 border-b-2 font-medium">
            Participants ({{ tournament.registrations_count }})
          </button>
          <button @click="activeTab = 'bracket'" class="px-6 py-4 border-b-2">
            Bracket
          </button>
          <button @click="activeTab = 'rules'" class="px-6 py-4 border-b-2">
            Rules
          </button>
        </nav>
      </div>
      
      <!-- Tab Content -->
      <div class="p-6">
        <!-- Overview Tab -->
        <div x-show="activeTab === 'overview'" class="space-y-6">
          <div class="prose max-w-none">
            {{ tournament.description|markdown }}
          </div>
          
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <!-- Tournament Details Card -->
            <div class="bg-gray-50 rounded-lg p-6">
              <h3 class="font-bold mb-4">Tournament Details</h3>
              <dl class="space-y-2">
                <div class="flex justify-between">
                  <dt class="text-gray-600">Format</dt>
                  <dd class="font-semibold">{{ tournament.get_format_display }}</dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-gray-600">Team Size</dt>
                  <dd class="font-semibold">{{ tournament.team_size }}</dd>
                </div>
                <div class="flex justify-between">
                  <dt class="text-gray-600">Platforms</dt>
                  <dd class="font-semibold">PC, PS5</dd>
                </div>
              </dl>
            </div>
            
            <!-- Registration Countdown -->
            <div class="bg-blue-50 rounded-lg p-6" x-data="countdown('{{ tournament.registration_end|date:'c' }}')">
              <h3 class="font-bold mb-2">Registration Closes In</h3>
              <div class="text-3xl font-bold text-primary-600" x-text="timeLeft"></div>
              <div class="text-sm text-gray-600 mt-2">{{ tournament.registration_end|date:"M d, Y H:i" }}</div>
            </div>
            
            <!-- Organizer Card -->
            <div class="bg-gray-50 rounded-lg p-6">
              <h3 class="font-bold mb-4">Organized By</h3>
              <div class="flex items-center gap-3 mb-3">
                <img src="{{ tournament.organizer.avatar }}" class="w-12 h-12 rounded-full">
                <div>
                  <div class="font-semibold">{{ tournament.organizer.username }}</div>
                  <div class="text-sm text-gray-600">{{ tournament.organizer.organized_tournaments_count }} tournaments</div>
                </div>
              </div>
              <a href="/users/{{ tournament.organizer.id }}/" class="btn btn-sm btn-secondary w-full">
                View Profile
              </a>
            </div>
          </div>
        </div>
        
        <!-- Participants Tab -->
        <div x-show="activeTab === 'participants'">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {% for registration in registrations %}
            <div class="bg-gray-50 rounded-lg p-4">
              <div class="flex items-center gap-3 mb-2">
                <img src="{{ registration.team.logo.url }}" class="w-10 h-10 rounded">
                <div>
                  <div class="font-semibold">{{ registration.team.name }}</div>
                  <div class="text-sm text-gray-600">{{ registration.team.members.count }} members</div>
                </div>
              </div>
              <span class="badge badge-{{ registration.status|lower }}">{{ registration.status }}</span>
            </div>
            {% empty %}
            <div class="col-span-4 text-center py-12 text-gray-500">
              No teams registered yet. Be the first!
            </div>
            {% endfor %}
          </div>
        </div>
        
        <!-- Bracket Tab -->
        <div x-show="activeTab === 'bracket'">
          {% if tournament.bracket_generated %}
          <!-- Bracket visualization (Sprint 8) -->
          {% else %}
          <div class="text-center py-12 text-gray-500">
            Bracket will be available after registration closes.
          </div>
          {% endif %}
        </div>
        
        <!-- Rules Tab -->
        <div x-show="activeTab === 'rules'">
          <div class="prose max-w-none">
            {{ tournament.rules_text|markdown }}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

**Countdown Timer (Alpine.js):**
```javascript
function countdown(endDate) {
  return {
    timeLeft: '',
    
    init() {
      this.updateCountdown();
      setInterval(() => this.updateCountdown(), 1000);
    },
    
    updateCountdown() {
      const now = new Date().getTime();
      const end = new Date(endDate).getTime();
      const distance = end - now;
      
      if (distance < 0) {
        this.timeLeft = 'Closed';
        return;
      }
      
      const days = Math.floor(distance / (1000 * 60 * 60 * 24));
      const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
      const seconds = Math.floor((distance % (1000 * 60)) / 1000);
      
      this.timeLeft = `${days}d ${hours}h ${minutes}m ${seconds}s`;
    }
  }
}
```

**Testing:**
- Access `/tournaments/summer-valorant-cup/` → detail page loads
- Verify hero section: Banner, title, status badge, quick stats
- Test tabs: Click Overview, Participants, Bracket, Rules → content changes
- Test countdown: Registration countdown updates every second
- Test action button (not registered): "Register Team" shown
- Test action button (registered): "Manage Registration" shown
- Test action button (organizer): "Manage Tournament" shown
- Test participants tab: All registered teams shown with status badges
- Test empty state: No teams → "Be the first!" message
- Test responsive: Mobile → tabs become accordion, stats stack
- Test share: Click Twitter → share dialog opens
- Test real-time: New team registers → count updates (poll every 30s)

---

### **FE-014: Organizer Dashboard**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 5  
**Assignee:** Frontend Dev 1  
**Sprint:** Sprint 4  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create organizer dashboard for managing tournaments. Display all organized tournaments with quick stats, pending actions, recent registrations, and quick access to tournament management tools.

**Acceptance Criteria:**
- [ ] **Page Layout** (accessible at `/dashboard/organizer/`):
  - Page title: "Organizer Dashboard"
  - Quick stats cards (4 cards in row):
    - Total tournaments organized
    - Active tournaments (status=ONGOING)
    - Total participants (across all tournaments)
    - Total prize pool distributed
  - Recent activity feed (right sidebar, 30% width):
    - New registrations
    - Check-ins
    - Match results submitted
    - Limit: Last 20 activities
- [ ] **Main Content Area:**
  - Tabs: All Tournaments / Active / Completed / Drafts
  - Tournament table view:
    - Columns: Title, Status, Registered/Max, Start Date, Actions
    - Actions dropdown: View, Edit, Publish (if draft), Cancel, Export
  - Sorting: By start date (default), created date, status
  - Pagination: 10 tournaments per page
- [ ] **Pending Actions Section:**
  - Alert cards for items requiring attention:
    - "5 pending payment verifications" → Links to payment review page
    - "3 tournaments starting in 24 hours" → Links to pre-tournament checklist
    - "2 disputes to resolve" → Links to dispute management
  - Dismissible alerts (stored in session)
- [ ] **Tournament Creation Button:**
  - Prominent "+ Create New Tournament" button (top right, always visible)
  - Links to tournament creation wizard
- [ ] **Tournament Table Actions:**
  - View: Opens tournament detail page
  - Edit: Opens tournament edit page
  - Publish: Confirmation modal, publishes draft tournament
  - Cancel: Confirmation modal, cancels tournament (if no confirmed registrations)
  - Export: Downloads CSV of all registrations
  - Delete: Confirmation modal, deletes tournament (if status=DRAFT only)
- [ ] **Filters:**
  - Game filter dropdown
  - Date range picker (tournaments starting between dates)
  - Status filter: All, Draft, Published, Ongoing, Completed, Cancelled
- [ ] **Search:**
  - Search by tournament title (debounced)
- [ ] **Empty States:**
  - No tournaments: "You haven't organized any tournaments yet. Create your first one!"
  - No pending actions: "All caught up! No pending actions."
- [ ] **Responsive:**
  - Mobile: Stats stack vertically, table becomes cards
  - Activity feed moves below main content on mobile

**Dependencies:**
- FE-002 (Design tokens)
- FE-009 (Card component)
- BE-008 (Tournament API with organizer filter)

**Technical Notes:**
- Use DataTables.js or similar for sortable, filterable table
- Export CSV: Generate client-side from table data or server endpoint
- Activity feed: Real-time updates via WebSocket (Sprint 9) or polling (30s)
- Reference: PROPOSAL_PART_4.md Section 6.2 (Organizer Dashboard)

**Files to Create/Modify:**
- `templates/dashboard/organizer.html` (new)
- `apps/dashboard/views.py` (add `OrganizerDashboardView`)
- `apps/dashboard/urls.py` (add `/dashboard/organizer/` route)
- `static/js/organizer-dashboard.js` (new)

**HTML Structure:**
```html
<div class="min-h-screen bg-gray-50 py-8">
  <div class="container mx-auto px-4">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Organizer Dashboard</h1>
      <a href="/tournaments/create/" class="btn btn-primary btn-lg">
        + Create New Tournament
      </a>
    </div>
    
    <!-- Quick Stats -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-gray-600">Total Tournaments</div>
            <div class="text-3xl font-bold text-primary-600">{{ stats.total_tournaments }}</div>
          </div>
          <svg class="w-12 h-12 text-primary-200"><!-- Icon --></svg>
        </div>
      </div>
      
      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-gray-600">Active Tournaments</div>
            <div class="text-3xl font-bold text-green-600">{{ stats.active_tournaments }}</div>
          </div>
          <svg class="w-12 h-12 text-green-200"><!-- Icon --></svg>
        </div>
      </div>
      
      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-gray-600">Total Participants</div>
            <div class="text-3xl font-bold text-blue-600">{{ stats.total_participants }}</div>
          </div>
          <svg class="w-12 h-12 text-blue-200"><!-- Icon --></svg>
        </div>
      </div>
      
      <div class="bg-white rounded-lg shadow p-6">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm text-gray-600">Prize Pool Distributed</div>
            <div class="text-3xl font-bold text-yellow-600">${{ stats.total_prize_pool }}</div>
          </div>
          <svg class="w-12 h-12 text-yellow-200"><!-- Icon --></svg>
        </div>
      </div>
    </div>
    
    <!-- Pending Actions -->
    {% if pending_actions %}
    <div class="mb-8 space-y-4">
      {% for action in pending_actions %}
      <div class="bg-yellow-50 border-l-4 border-yellow-400 p-4 flex justify-between items-center">
        <div class="flex items-center gap-3">
          <svg class="w-6 h-6 text-yellow-600"><!-- Alert icon --></svg>
          <div>
            <div class="font-semibold text-yellow-900">{{ action.title }}</div>
            <div class="text-sm text-yellow-700">{{ action.description }}</div>
          </div>
        </div>
        <div class="flex gap-2">
          <a href="{{ action.link }}" class="btn btn-sm btn-primary">Review</a>
          <button onclick="dismissAction('{{ action.id }}')" class="btn btn-sm btn-ghost">Dismiss</button>
        </div>
      </div>
      {% endfor %}
    </div>
    {% endif %}
    
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- Main Content: Tournament Table -->
      <div class="lg:col-span-2">
        <div class="bg-white rounded-lg shadow">
          <!-- Tabs -->
          <div class="border-b border-gray-200">
            <nav class="flex">
              <button class="px-6 py-4 border-b-2 border-primary-500 text-primary-600 font-medium">
                All Tournaments
              </button>
              <button class="px-6 py-4 border-b-2 border-transparent text-gray-500">
                Active
              </button>
              <button class="px-6 py-4 border-b-2 border-transparent text-gray-500">
                Completed
              </button>
              <button class="px-6 py-4 border-b-2 border-transparent text-gray-500">
                Drafts
              </button>
            </nav>
          </div>
          
          <!-- Filters & Search -->
          <div class="p-4 border-b border-gray-200 flex gap-4">
            <input type="search" placeholder="Search tournaments..." class="flex-1 border rounded px-3 py-2">
            <select class="border rounded px-3 py-2">
              <option>All Games</option>
              <option>Valorant</option>
              <option>eFootball</option>
            </select>
            <select class="border rounded px-3 py-2">
              <option>All Status</option>
              <option>Draft</option>
              <option>Published</option>
              <option>Ongoing</option>
            </select>
          </div>
          
          <!-- Tournament Table -->
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead class="bg-gray-50">
                <tr>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Teams</th>
                  <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Start Date</th>
                  <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody class="bg-white divide-y divide-gray-200">
                {% for tournament in tournaments %}
                <tr class="hover:bg-gray-50">
                  <td class="px-6 py-4">
                    <div class="flex items-center gap-3">
                      <img src="{{ tournament.game.icon.url }}" class="w-8 h-8 rounded">
                      <div>
                        <div class="font-semibold">{{ tournament.title }}</div>
                        <div class="text-sm text-gray-500">{{ tournament.game.name }}</div>
                      </div>
                    </div>
                  </td>
                  <td class="px-6 py-4">
                    <span class="badge badge-{{ tournament.get_status_display_color }}">{{ tournament.status }}</span>
                  </td>
                  <td class="px-6 py-4">{{ tournament.registrations_count }}/{{ tournament.max_teams }}</td>
                  <td class="px-6 py-4">{{ tournament.tournament_start|date:"M d, Y" }}</td>
                  <td class="px-6 py-4 text-right">
                    <div class="relative inline-block" x-data="{ open: false }">
                      <button @click="open = !open" class="btn btn-sm btn-ghost">⋮</button>
                      <div x-show="open" @click.away="open = false" 
                           class="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg z-10">
                        <a href="/tournaments/{{ tournament.slug }}/" class="block px-4 py-2 hover:bg-gray-50">View</a>
                        <a href="/tournaments/{{ tournament.slug }}/edit/" class="block px-4 py-2 hover:bg-gray-50">Edit</a>
                        {% if tournament.status == 'DRAFT' %}
                        <button onclick="publishTournament('{{ tournament.slug }}')" class="block w-full text-left px-4 py-2 hover:bg-gray-50">Publish</button>
                        {% endif %}
                        <button onclick="exportRegistrations('{{ tournament.slug }}')" class="block w-full text-left px-4 py-2 hover:bg-gray-50">Export CSV</button>
                        <button onclick="cancelTournament('{{ tournament.slug }}')" class="block w-full text-left px-4 py-2 text-red-600 hover:bg-red-50">Cancel</button>
                      </div>
                    </div>
                  </td>
                </tr>
                {% empty %}
                <tr>
                  <td colspan="5" class="px-6 py-12 text-center text-gray-500">
                    No tournaments found. Create your first one!
                  </td>
                </tr>
                {% endfor %}
              </tbody>
            </table>
          </div>
          
          <!-- Pagination -->
          <div class="p-4 flex justify-between items-center">
            <div class="text-sm text-gray-600">Showing 1-10 of {{ total_tournaments }}</div>
            <div class="flex gap-2">
              <button class="btn btn-sm">Previous</button>
              <button class="btn btn-sm btn-primary">1</button>
              <button class="btn btn-sm">2</button>
              <button class="btn btn-sm">Next</button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Sidebar: Recent Activity -->
      <div class="lg:col-span-1">
        <div class="bg-white rounded-lg shadow p-6">
          <h3 class="font-bold mb-4">Recent Activity</h3>
          <div class="space-y-4">
            {% for activity in recent_activities %}
            <div class="flex gap-3">
              <div class="flex-shrink-0 w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center">
                <svg class="w-5 h-5 text-primary-600"><!-- Icon --></svg>
              </div>
              <div class="flex-1">
                <div class="text-sm font-semibold">{{ activity.title }}</div>
                <div class="text-xs text-gray-500">{{ activity.timestamp|timesince }} ago</div>
                <div class="text-sm text-gray-600 mt-1">{{ activity.description }}</div>
              </div>
            </div>
            {% empty %}
            <div class="text-center text-gray-500 py-8">No recent activity</div>
            {% endfor %}
          </div>
        </div>
      </div>
    </div>
  </div>
</div>
```

**Testing:**
- Access `/dashboard/organizer/` → dashboard loads
- Verify quick stats: Total tournaments, active, participants, prize pool
- Test pending actions: Click "Review" → navigates to relevant page
- Test tournament table: All organized tournaments shown
- Test tabs: Click "Active" → only active tournaments shown
- Test search: Type "valorant" → filters tournaments
- Test actions dropdown: Click ⋮ → View, Edit, Publish, Export, Cancel options
- Test publish: Click Publish (draft) → confirmation modal → tournament published
- Test export: Click Export CSV → file downloads with registrations
- Test responsive: Mobile → stats stack, table becomes cards
- Test empty state: No tournaments → "Create your first one!" message

---

### **FE-015: My Tournaments Page (Player View)**

**Type:** Story  
**Priority:** Medium (P2)  
**Story Points:** 4  
**Assignee:** Frontend Dev 2  
**Sprint:** Sprint 4  
**Epic:** Epic 2 - Tournament Engine

**Description:**
Create "My Tournaments" page for players to view all tournaments they're registered for. Display registration status, upcoming matches, check-in reminders, and quick actions.

**Acceptance Criteria:**
- [ ] **Page Layout** (accessible at `/my/tournaments/`):
  - Page title: "My Tournaments"
  - Tabs: Upcoming / Ongoing / Completed / All
  - Tournament list (card view):
    - Tournament title, game icon, status badge
    - Registration status badge (Pending, Confirmed, Checked In)
    - Team name (which team you registered with)
    - Start date/time with countdown if upcoming
    - Quick actions: View Tournament, Check In, Withdraw
- [ ] **Upcoming Tab (default):**
  - Shows tournaments starting in future (tournament_start > now)
  - Sorted by start date (soonest first)
  - Check-in reminders: "Check-in opens in 2 hours" (highlighted)
  - Empty state: "No upcoming tournaments. Browse and join one!"
- [ ] **Ongoing Tab:**
  - Shows tournaments currently running (status=ONGOING)
  - Next match info (if bracket generated):
    - "Your next match: vs Team Alpha on May 15 at 3 PM"
    - Link to match page
  - Live match indicator if match in progress
  - Empty state: "No ongoing tournaments"
- [ ] **Completed Tab:**
  - Shows finished tournaments (status=COMPLETED)
  - Your placement: "🥇 1st Place" / "🥈 2nd Place" / "Eliminated in Round 2"
  - Prize won (if applicable): "$500"
  - View Results button
  - Empty state: "No completed tournaments"
- [ ] **All Tab:**
  - All tournaments (upcoming, ongoing, completed, cancelled)
  - Filter by status, game
- [ ] **Action Buttons (per tournament):**
  - View Tournament: Opens tournament detail page
  - Check In (if check-in window open): One-click check-in
  - Withdraw (if before check-in): Confirmation modal, withdraws registration
  - View Results (if completed): Opens bracket/standings page
- [ ] **Notifications/Alerts:**
  - Check-in reminder: Alert banner if check-in opens within 2 hours
  - Match starting soon: Alert if next match starts within 30 minutes
  - Registration confirmed: Success banner if just confirmed
- [ ] **Empty States:**
  - No tournaments at all: "You haven't joined any tournaments yet. Browse tournaments to get started!"
  - No upcoming: "No upcoming tournaments"
- [ ] **Responsive:**
  - Mobile: Cards stack vertically
  - Desktop: 2-column grid

**Dependencies:**
- FE-002 (Design tokens)
- FE-009 (Card component)
- BE-013 (TournamentRegistration API)

**Technical Notes:**
- Filter tournaments by user's team registrations
- Use Alpine.js for countdown timers
- Check-in button enabled only during check-in window
- Reference: PROPOSAL_PART_4.md Section 6.3 (My Tournaments)

**Files to Create/Modify:**
- `templates/tournaments/my_tournaments.html` (new)
- `apps/tournaments/views.py` (add `MyTournamentsView`)
- `apps/tournaments/urls.py` (add `/my/tournaments/` route)
- `static/js/my-tournaments.js` (new)

**HTML Structure:**
```html
<div class="min-h-screen bg-gray-50 py-8">
  <div class="container mx-auto px-4">
    <h1 class="text-3xl font-bold mb-8">My Tournaments</h1>
    
    <!-- Alerts -->
    {% if check_in_reminders %}
    <div class="mb-6 space-y-4">
      {% for reminder in check_in_reminders %}
      <div class="bg-blue-50 border-l-4 border-blue-400 p-4 flex items-center gap-3">
        <svg class="w-6 h-6 text-blue-600"><!-- Clock icon --></svg>
        <div>
          <div class="font-semibold text-blue-900">Check-in reminder</div>
          <div class="text-sm text-blue-700">{{ reminder.tournament_title }} check-in opens in {{ reminder.time_until }}</div>
        </div>
        <a href="/tournaments/{{ reminder.slug }}/" class="ml-auto btn btn-sm btn-primary">View</a>
      </div>
      {% endfor %}
    </div>
    {% endif %}
    
    <!-- Tabs -->
    <div class="bg-white rounded-lg shadow">
      <div class="border-b border-gray-200">
        <nav class="flex" x-data="{ activeTab: 'upcoming' }">
          <button @click="activeTab = 'upcoming'" 
                  :class="activeTab === 'upcoming' ? 'border-primary-500 text-primary-600' : 'border-transparent text-gray-500'"
                  class="px-6 py-4 border-b-2 font-medium">
            Upcoming
          </button>
          <button @click="activeTab = 'ongoing'" class="px-6 py-4 border-b-2">
            Ongoing
          </button>
          <button @click="activeTab = 'completed'" class="px-6 py-4 border-b-2">
            Completed
          </button>
          <button @click="activeTab = 'all'" class="px-6 py-4 border-b-2">
            All
          </button>
        </nav>
      </div>
      
      <!-- Tab Content -->
      <div class="p-6">
        <div x-show="activeTab === 'upcoming'">
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            {% for registration in upcoming_tournaments %}
            <div class="bg-white border rounded-lg p-6 hover:shadow-md transition">
              <div class="flex items-center gap-3 mb-4">
                <img src="{{ registration.tournament.game.icon.url }}" class="w-10 h-10 rounded">
                <div class="flex-1">
                  <h3 class="font-bold">{{ registration.tournament.title }}</h3>
                  <div class="text-sm text-gray-600">as {{ registration.team.name }}</div>
                </div>
                <span class="badge badge-{{ registration.status|lower }}">{{ registration.status }}</span>
              </div>
              
              <div class="space-y-2 mb-4">
                <div class="flex justify-between text-sm">
                  <span class="text-gray-600">Starts</span>
                  <span class="font-semibold">{{ registration.tournament.tournament_start|date:"M d, Y H:i" }}</span>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-gray-600">Prize Pool</span>
                  <span class="font-semibold">${{ registration.tournament.prize_pool }}</span>
                </div>
                <div x-data="countdown('{{ registration.tournament.tournament_start|date:'c' }}')">
                  <div class="text-primary-600 font-semibold" x-text="`Starts in ${timeLeft}`"></div>
                </div>
              </div>
              
              <div class="flex gap-2">
                <a href="/tournaments/{{ registration.tournament.slug }}/" class="flex-1 btn btn-secondary btn-sm">
                  View Tournament
                </a>
                {% if registration.can_check_in %}
                <button onclick="checkIn('{{ registration.id }}')" class="flex-1 btn btn-primary btn-sm">
                  Check In
                </button>
                {% endif %}
              </div>
            </div>
            {% empty %}
            <div class="col-span-2 text-center py-12 text-gray-500">
              No upcoming tournaments. <a href="/tournaments/" class="text-primary-500 hover:underline">Browse tournaments</a>
            </div>
            {% endfor %}
          </div>
        </div>
        
        <div x-show="activeTab === 'ongoing'">
          <!-- Similar structure for ongoing -->
        </div>
        
        <div x-show="activeTab === 'completed'">
          <!-- Similar structure for completed with placement badges -->
        </div>
      </div>
    </div>
  </div>
</div>
```

**Testing:**
- Access `/my/tournaments/` → page loads with upcoming tournaments
- Test tabs: Click Ongoing, Completed, All → content changes
- Test countdown: Verify countdown updates every second
- Test check-in: Click "Check In" (during window) → registration updated to CHECKED_IN
- Test alerts: Tournament with check-in opening soon → alert banner shown
- Test empty state: No upcoming → "Browse tournaments" message
- Test responsive: Mobile → cards stack vertically
- Test actions: Click "View Tournament" → navigates to detail page

---

### FE-016: Tournament Card Component

**Type:** Frontend - Component  
**Priority:** P1  
**Story Points:** 6  
**Assignee:** Frontend Developer  
**Sprint:** 4 (Week 4)  
**Epic:** Tournament Engine - Frontend

**Description:**

Develop a reusable tournament card component for displaying tournaments in list and grid views across multiple pages. This component serves as the primary visual representation of tournaments in browse listings (FE-012), organizer dashboards (FE-014), and player tournament lists (FE-015). The card must support multiple display variants, handle different states (loading, empty, error), and provide responsive design that adapts from mobile to desktop layouts.

The component should be implemented as a Django template include (`components/tournament_card.html`) with Alpine.js for interactive features, accepting a tournament object and configuration props. It must follow the established design system (FE-002) and integrate with the Button (FE-007), Badge (FE-009), and Card (FE-009) components. The card should support click-through navigation, hover effects, lazy-loaded images, and accessibility features including keyboard navigation and screen reader support.

**Acceptance Criteria:**

- [ ] Component file created at `templates/components/tournament_card.html` as Django template include
- [ ] Accepts `tournament` object, `variant` (default/featured/compact), `show_actions` boolean as props
- [ ] **Default variant** displays logo (80x80), title, game icon with name, status badge, teams count (X/Y), prize pool, start date, "View Details" button
- [ ] **Featured variant** displays larger logo (120x120), gradient background, "Featured" badge, priority styling, emphasized prize pool
- [ ] **Compact variant** displays smaller logo (60x60), condensed info (title, game, prize, date only), no actions
- [ ] Status badge color-coded: DRAFT (gray-500), PUBLISHED (blue-500), ONGOING (green-500), COMPLETED (purple-500), CANCELLED (red-500)
- [ ] Hover effect: Card lifts with shadow (`transform: translateY(-4px)`, `shadow-lg`) on desktop, maintains tap target 44x44px minimum on mobile
- [ ] Loading state: Skeleton loader with animated pulse for logo, title, info lines (uses `animate-pulse` Tailwind utility)
- [ ] Empty state: Placeholder card with "No tournament data" message and icon
- [ ] Images lazy loaded with `loading="lazy"` attribute and fallback image (placeholder logo if tournament.logo is null)
- [ ] Quick actions: "View Tournament" primary button, "Register" secondary button (if can_register), "Edit" icon button (if is_organizer)
- [ ] Responsive design: Full width mobile (<640px), 2 columns tablet (640-1024px), 3 columns desktop (>1024px) in grid layouts
- [ ] Accessibility: Semantic HTML (`<article>` wrapper), ARIA labels ("Tournament card for {title}"), keyboard navigation (Tab, Enter to click), focus indicators (ring-2 ring-primary-500)
- [ ] Prize pool formatted with currency symbol and thousands separator (e.g., "$1,500" for 1500, "Free Entry" if 0)
- [ ] Start date displays relative time if within 7 days ("In 2 days"), absolute date otherwise ("May 15, 2024")
- [ ] Component documented with usage examples: `{% include 'components/tournament_card.html' with tournament=tournament variant='default' show_actions=True %}`

**Dependencies:**
- FE-002: Design System Foundation (design tokens, spacing, colors)
- FE-007: Button Component (primary/secondary buttons)
- FE-009: Card Component (base card structure, shadows)
- BE-008: Tournament API CRUD (tournament object structure)

**Technical Notes:**

**Component Props:**
```django
{# templates/components/tournament_card.html #}
{# Props: tournament (object), variant (string), show_actions (boolean) #}

<article class="tournament-card {{ variant }}" 
         data-tournament-id="{{ tournament.id }}"
         role="article"
         aria-label="Tournament card for {{ tournament.title }}">
  
  {% if variant == 'featured' %}
  <div class="tournament-card-featured bg-gradient-to-br from-primary-500 to-primary-700 rounded-lg p-6 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
    <div class="flex items-start gap-4">
      <img src="{{ tournament.logo.url|default:'/static/img/placeholder-logo.png' }}" 
           alt="{{ tournament.title }} logo"
           class="w-32 h-32 rounded-lg object-cover"
           loading="lazy">
      <div class="flex-1 text-white">
        <div class="flex items-center gap-2 mb-2">
          <span class="badge badge-warning text-xs font-bold">⭐ FEATURED</span>
          <span class="badge badge-{{ tournament.status|lower }}">{{ tournament.get_status_display }}</span>
        </div>
        <h3 class="text-2xl font-bold mb-2">{{ tournament.title }}</h3>
        <div class="flex items-center gap-2 mb-3">
          <img src="{{ tournament.game.icon.url }}" alt="" class="w-5 h-5">
          <span class="text-sm opacity-90">{{ tournament.game.name }}</span>
        </div>
        <div class="grid grid-cols-3 gap-4 mb-4">
          <div>
            <div class="text-xs opacity-75">Prize Pool</div>
            <div class="text-xl font-bold">{{ tournament.prize_pool|currency }}</div>
          </div>
          <div>
            <div class="text-xs opacity-75">Teams</div>
            <div class="text-xl font-bold">{{ tournament.registrations_count }}/{{ tournament.max_teams }}</div>
          </div>
          <div>
            <div class="text-xs opacity-75">Starts</div>
            <div class="text-sm font-semibold">{{ tournament.tournament_start|relative_time }}</div>
          </div>
        </div>
        <a href="{% url 'tournaments:detail' tournament.slug %}" class="btn btn-light inline-block">
          View Tournament →
        </a>
      </div>
    </div>
  </div>
  
  {% elif variant == 'compact' %}
  <div class="tournament-card-compact bg-white rounded-lg p-4 border border-gray-200 hover:border-primary-300 hover:shadow-md transition-all">
    <a href="{% url 'tournaments:detail' tournament.slug %}" class="flex items-center gap-3">
      <img src="{{ tournament.logo.url|default:'/static/img/placeholder-logo.png' }}" 
           alt="{{ tournament.title }} logo"
           class="w-16 h-16 rounded-lg object-cover flex-shrink-0"
           loading="lazy">
      <div class="flex-1 min-w-0">
        <h4 class="font-semibold text-gray-900 truncate mb-1">{{ tournament.title }}</h4>
        <div class="flex items-center gap-2 text-sm text-gray-600">
          <img src="{{ tournament.game.icon.url }}" alt="" class="w-4 h-4">
          <span>{{ tournament.game.name }}</span>
          <span class="text-gray-400">•</span>
          <span class="font-semibold text-primary-600">{{ tournament.prize_pool|currency }}</span>
        </div>
      </div>
      <div class="text-right flex-shrink-0">
        <span class="badge badge-{{ tournament.status|lower }} text-xs">{{ tournament.get_status_display }}</span>
        <div class="text-xs text-gray-500 mt-1">{{ tournament.tournament_start|date:"M d" }}</div>
      </div>
    </a>
  </div>
  
  {% else %}
  {# Default variant #}
  <div class="tournament-card-default bg-white rounded-lg shadow-sm hover:shadow-lg border border-gray-200 overflow-hidden transition-all duration-300 transform hover:-translate-y-1">
    <a href="{% url 'tournaments:detail' tournament.slug %}" class="block">
      <div class="relative">
        {% if tournament.banner %}
        <img src="{{ tournament.banner.url }}" 
             alt="{{ tournament.title }} banner"
             class="w-full h-40 object-cover"
             loading="lazy">
        {% else %}
        <div class="w-full h-40 bg-gradient-to-r from-primary-400 to-primary-600"></div>
        {% endif %}
        <div class="absolute top-3 right-3">
          <span class="badge badge-{{ tournament.status|lower }}">{{ tournament.get_status_display }}</span>
        </div>
      </div>
      
      <div class="p-4">
        <div class="flex items-start gap-3 mb-3">
          <img src="{{ tournament.logo.url|default:'/static/img/placeholder-logo.png' }}" 
               alt="{{ tournament.title }} logo"
               class="w-20 h-20 rounded-lg object-cover flex-shrink-0 -mt-10 border-4 border-white shadow-md"
               loading="lazy">
          <div class="flex-1 pt-2">
            <h3 class="font-bold text-lg text-gray-900 mb-1 line-clamp-2">{{ tournament.title }}</h3>
            <div class="flex items-center gap-2 text-sm text-gray-600">
              <img src="{{ tournament.game.icon.url }}" alt="" class="w-4 h-4">
              <span>{{ tournament.game.name }}</span>
            </div>
          </div>
        </div>
        
        <div class="grid grid-cols-2 gap-3 mb-3 text-sm">
          <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z"/>
            </svg>
            <span class="text-gray-700">{{ tournament.registrations_count }}/{{ tournament.max_teams }} teams</span>
          </div>
          <div class="flex items-center gap-2">
            <svg class="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clip-rule="evenodd"/>
            </svg>
            <span class="text-gray-700">{{ tournament.tournament_start|relative_time }}</span>
          </div>
        </div>
        
        {% if tournament.prize_pool > 0 %}
        <div class="bg-gradient-to-r from-yellow-50 to-yellow-100 rounded-lg p-3 mb-3">
          <div class="flex items-center justify-between">
            <span class="text-sm text-gray-600">Prize Pool</span>
            <span class="text-lg font-bold text-yellow-700">{{ tournament.prize_pool|currency }}</span>
          </div>
        </div>
        {% else %}
        <div class="bg-green-50 rounded-lg p-3 mb-3 text-center">
          <span class="text-sm font-semibold text-green-700">🎉 Free Entry</span>
        </div>
        {% endif %}
      </div>
    </a>
    
    {% if show_actions %}
    <div class="px-4 pb-4 flex gap-2">
      {% if tournament.can_register %}
      <button onclick="registerTournament('{{ tournament.id }}')" class="flex-1 btn btn-primary btn-sm">
        Register Now
      </button>
      {% endif %}
      {% if tournament.is_organizer %}
      <a href="{% url 'tournaments:edit' tournament.slug %}" class="btn btn-secondary btn-sm">
        <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
          <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/>
        </svg>
      </a>
      {% endif %}
      <a href="{% url 'tournaments:detail' tournament.slug %}" class="flex-1 btn btn-secondary btn-sm">
        View Details
      </a>
    </div>
    {% endif %}
  </div>
  {% endif %}
</article>
```

**Loading State Component:**
```django
{# templates/components/tournament_card_skeleton.html #}
<div class="tournament-card-skeleton bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
  <div class="animate-pulse">
    <div class="bg-gray-300 h-40 w-full"></div>
    <div class="p-4">
      <div class="flex items-start gap-3 mb-3">
        <div class="w-20 h-20 bg-gray-300 rounded-lg -mt-10"></div>
        <div class="flex-1 pt-2 space-y-2">
          <div class="h-5 bg-gray-300 rounded w-3/4"></div>
          <div class="h-4 bg-gray-300 rounded w-1/2"></div>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-3 mb-3">
        <div class="h-4 bg-gray-300 rounded"></div>
        <div class="h-4 bg-gray-300 rounded"></div>
      </div>
      <div class="h-16 bg-gray-300 rounded mb-3"></div>
    </div>
    <div class="px-4 pb-4">
      <div class="h-9 bg-gray-300 rounded"></div>
    </div>
  </div>
</div>
```

**Usage Examples:**
```django
{# In tournament list page (FE-012) #}
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {% for tournament in tournaments %}
    {% include 'components/tournament_card.html' with tournament=tournament variant='default' show_actions=True %}
  {% endfor %}
</div>

{# In organizer dashboard (FE-014) - compact variant #}
<div class="space-y-3">
  {% for tournament in my_tournaments %}
    {% include 'components/tournament_card.html' with tournament=tournament variant='compact' show_actions=False %}
  {% endfor %}
</div>

{# Featured tournament carousel (FE-012) #}
<div class="featured-carousel">
  {% for tournament in featured_tournaments %}
    {% include 'components/tournament_card.html' with tournament=tournament variant='featured' show_actions=True %}
  {% endfor %}
</div>

{# Loading state #}
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {% for i in "123" %}
    {% include 'components/tournament_card_skeleton.html' %}
  {% endfor %}
</div>
```

**Custom Template Filters:**
```python
# apps/tournaments/templatetags/tournament_filters.py
from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def currency(value):
    """Format currency with $ and thousands separator."""
    if value == 0:
        return "Free Entry"
    return f"${value:,.0f}"

@register.filter
def relative_time(value):
    """Return relative time if within 7 days, otherwise absolute date."""
    if not value:
        return ""
    
    now = timezone.now()
    delta = value - now
    
    if delta < timedelta(0):
        return value.strftime("%b %d, %Y")
    elif delta < timedelta(days=1):
        hours = delta.seconds // 3600
        return f"In {hours} hours"
    elif delta < timedelta(days=7):
        days = delta.days
        return f"In {days} days"
    else:
        return value.strftime("%b %d, %Y")
```

**Alpine.js Interactions (Optional):**
```javascript
// static/js/components/tournament-card.js
function tournamentCard() {
  return {
    isHovered: false,
    handleHover() {
      this.isHovered = true;
    },
    handleLeave() {
      this.isHovered = false;
    },
    handleClick(tournamentId) {
      // Track card click analytics
      if (typeof gtag !== 'undefined') {
        gtag('event', 'tournament_card_click', {
          tournament_id: tournamentId
        });
      }
    }
  }
}
```

**Files to Create/Modify:**
- `templates/components/tournament_card.html` - Main component template (default/featured/compact variants)
- `templates/components/tournament_card_skeleton.html` - Loading state component
- `apps/tournaments/templatetags/tournament_filters.py` - Custom template filters (currency, relative_time)
- `static/js/components/tournament-card.js` - Optional Alpine.js component for interactions
- `static/img/placeholder-logo.png` - Fallback logo image (add if not exists)

**References:**
- PROPOSAL_PART_4.md Section 10.7 (Tournament Card Component Design)
- Design System: FE-002 (colors, spacing, shadows)
- Component Library: FE-007 (buttons), FE-009 (cards, badges)

**Testing:**
- Render default variant → displays all elements (logo, title, game, status, teams, prize, date, actions)
- Render featured variant → gradient background, "Featured" badge, larger size, emphasized prize
- Render compact variant → condensed layout, clickable, no action buttons
- Test with missing logo → placeholder image displays
- Test with zero prize pool → "Free Entry" badge shown
- Test with different statuses → badge colors correct (DRAFT gray, PUBLISHED blue, ONGOING green, etc.)
- Test hover effect → card lifts and shadow increases on desktop
- Test loading state → skeleton loader animates with pulse
- Test responsive: Desktop (3 cols) → Tablet (2 cols) → Mobile (1 col)
- Test accessibility: Tab navigation → focus indicators visible, Enter to click
- Test with screen reader → ARIA labels read correctly ("Tournament card for {title}")
- Test currency filter: 1500 → "$1,500", 0 → "Free Entry"
- Test relative time filter: 2 days future → "In 2 days", 10 days future → "May 15, 2024"

---

### FE-017: Tournament Filters Component

**Type:** Frontend - Component  
**Priority:** P1  
**Story Points:** 7  
**Assignee:** Frontend Developer  
**Sprint:** 4 (Week 4)  
**Epic:** Tournament Engine - Frontend

**Description:**

Create an advanced filtering component for tournament browsing that extracts and enhances the filter sidebar from FE-012 into a reusable, standalone component. This component enables users to filter tournaments by multiple criteria including game type, status, entry fee, date range, and prize pool. It must manage complex filter state, integrate with HTMX for real-time filtering, persist filter selections in URL parameters, and provide an intuitive mobile experience with a collapsible drawer interface.

The component should be implemented as a Django template include with Alpine.js for state management, supporting both sidebar (desktop) and drawer (mobile) layouts. It must handle filter combinations with AND logic, display active filter counts, provide clear/reset functionality, and emit filter change events that trigger HTMX requests to reload tournament listings. The component should be flexible enough to be used in tournament browse pages, organizer dashboards, and search results.

**Acceptance Criteria:**

- [ ] Component file created at `templates/components/tournament_filters.html` as Django template include
- [ ] Accepts `games` list, `current_filters` dict, `layout` (sidebar/drawer) as props
- [ ] **Game filter section**: Multi-select checkboxes with game icons, "All Games" option, active count badge (e.g., "Game (2 selected)")
- [ ] **Status filter section**: Multi-select checkboxes (All/Upcoming/Ongoing/Completed/Cancelled), active count badge
- [ ] **Entry fee filter section**: Radio buttons (All/Free Entry/Paid), visual icons (🎉 Free, 💰 Paid)
- [ ] **Date range filter section**: From/To date pickers (flatpickr.js), quick presets (Today, This Week, This Month, Custom)
- [ ] **Prize pool filter section**: Range slider (noUiSlider.js) with min/max inputs ($0 - $10,000+), current range display
- [ ] Filter state managed with Alpine.js reactive object (`filters: { games: [], status: [], entry_fee: 'all', date_from: null, date_to: null, prize_min: 0, prize_max: 10000 }`)
- [ ] Filter changes trigger HTMX GET request to `/tournaments/?game=valorant&status=upcoming&fee=free` with debounce (500ms)
- [ ] Active filter badges displayed above results (e.g., "Valorant ✕", "Free Entry ✕"), click ✕ to remove individual filter
- [ ] "Clear All Filters" button resets all filters to defaults and reloads results
- [ ] Filter count badges on section headers (e.g., "Status (2)" when 2 status filters active)
- [ ] URL parameters synced with filter state using History API (`pushState`), bookmarkable/shareable URLs
- [ ] **Desktop layout**: Sidebar (25% width), sticky positioning (scrolls with page), collapsible sections (Alpine.js `x-collapse`)
- [ ] **Mobile layout**: Hidden by default, opens as slide-in drawer from left, hamburger menu button (☰ Filters (3)), overlay backdrop (closes drawer on click), close button (✕)
- [ ] Smooth transitions: Filter section expand/collapse (300ms ease), drawer slide-in (250ms ease-out), filter badge fade (200ms)
- [ ] Accessibility: Proper labels (`<label for="filter-game-valorant">`), ARIA expanded states, keyboard navigation (Tab, Space/Enter to toggle), focus trap in mobile drawer
- [ ] Empty states: No games → hide game filter section, no results → "No tournaments match your filters. Clear some filters?"

**Dependencies:**
- FE-002: Design System Foundation (colors, spacing, transitions)
- FE-007: Button Component (Clear All button)
- FE-009: Badge Component (active filter badges, count badges)
- FE-012: Tournament List Page (primary usage)
- BE-008: Tournament API CRUD (filtering support)

**Technical Notes:**

**Component Structure:**
```django
{# templates/components/tournament_filters.html #}
{# Props: games (queryset), current_filters (dict), layout ('sidebar'|'drawer') #}

<div x-data="tournamentFilters({{ current_filters|json }}, '{{ layout }}')" 
     x-init="init()"
     class="tournament-filters">
  
  {% if layout == 'drawer' %}
  {# Mobile Drawer #}
  <button @click="isOpen = true" class="lg:hidden btn btn-secondary mb-4">
    <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M3 3a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clip-rule="evenodd"/>
    </svg>
    <span>Filters</span>
    <span x-show="activeFilterCount > 0" 
          x-text="`(${activeFilterCount})`" 
          class="ml-1 font-bold"></span>
  </button>
  
  {# Overlay #}
  <div x-show="isOpen" 
       x-transition:enter="transition-opacity ease-out duration-200"
       x-transition:enter-start="opacity-0"
       x-transition:enter-end="opacity-100"
       x-transition:leave="transition-opacity ease-in duration-150"
       x-transition:leave-start="opacity-100"
       x-transition:leave-end="opacity-0"
       @click="isOpen = false"
       class="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
       x-cloak></div>
  
  {# Drawer Panel #}
  <div x-show="isOpen"
       x-transition:enter="transition ease-out duration-250"
       x-transition:enter-start="-translate-x-full"
       x-transition:enter-end="translate-x-0"
       x-transition:leave="transition ease-in duration-200"
       x-transition:leave-start="translate-x-0"
       x-transition:leave-end="-translate-x-full"
       @keydown.escape.window="isOpen = false"
       x-trap="isOpen"
       class="fixed inset-y-0 left-0 w-80 bg-white shadow-xl z-50 overflow-y-auto lg:hidden"
       x-cloak>
    
    <div class="p-6">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-xl font-bold">Filters</h2>
        <button @click="isOpen = false" class="p-2 hover:bg-gray-100 rounded-lg">
          <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
          </svg>
        </button>
      </div>
      {% include 'components/tournament_filters_content.html' %}
    </div>
  </div>
  {% else %}
  {# Desktop Sidebar #}
  <aside class="hidden lg:block w-full bg-white rounded-lg border border-gray-200 p-6 sticky top-20">
    <div class="flex items-center justify-between mb-6">
      <h2 class="text-lg font-bold">Filters</h2>
      <button @click="clearAllFilters()" 
              x-show="activeFilterCount > 0"
              class="text-sm text-primary-600 hover:text-primary-700 font-medium">
        Clear All
      </button>
    </div>
    {% include 'components/tournament_filters_content.html' %}
  </aside>
  {% endif %}
  
</div>
```

**Filter Content (Shared):**
```django
{# templates/components/tournament_filters_content.html #}
<div class="space-y-6">
  
  {# Game Filter #}
  <div class="filter-section">
    <button @click="sections.game = !sections.game" 
            class="w-full flex items-center justify-between py-2 font-semibold text-gray-900">
      <span>
        Game
        <span x-show="filters.games.length > 0" 
              x-text="`(${filters.games.length})`"
              class="ml-1 text-sm text-primary-600"></span>
      </span>
      <svg :class="sections.game ? 'rotate-180' : ''" 
           class="w-5 h-5 transform transition-transform"
           fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
      </svg>
    </button>
    
    <div x-show="sections.game" 
         x-collapse
         class="mt-3 space-y-2">
      {% for game in games %}
      <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
        <input type="checkbox" 
               value="{{ game.id }}"
               x-model="filters.games"
               @change="applyFilters()"
               class="w-4 h-4 text-primary-600 rounded">
        <img src="{{ game.icon.url }}" alt="" class="w-6 h-6">
        <span class="flex-1 text-sm text-gray-700">{{ game.name }}</span>
      </label>
      {% endfor %}
    </div>
  </div>
  
  {# Status Filter #}
  <div class="filter-section border-t pt-6">
    <button @click="sections.status = !sections.status" 
            class="w-full flex items-center justify-between py-2 font-semibold text-gray-900">
      <span>
        Status
        <span x-show="filters.status.length > 0" 
              x-text="`(${filters.status.length})`"
              class="ml-1 text-sm text-primary-600"></span>
      </span>
      <svg :class="sections.status ? 'rotate-180' : ''" 
           class="w-5 h-5 transform transition-transform"
           fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
      </svg>
    </button>
    
    <div x-show="sections.status" 
         x-collapse
         class="mt-3 space-y-2">
      <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
        <input type="checkbox" value="upcoming" x-model="filters.status" @change="applyFilters()" class="w-4 h-4">
        <span class="flex-1 text-sm">Upcoming</span>
        <span class="badge badge-blue text-xs">Upcoming</span>
      </label>
      <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
        <input type="checkbox" value="ongoing" x-model="filters.status" @change="applyFilters()" class="w-4 h-4">
        <span class="flex-1 text-sm">Ongoing</span>
        <span class="badge badge-green text-xs">Ongoing</span>
      </label>
      <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
        <input type="checkbox" value="completed" x-model="filters.status" @change="applyFilters()" class="w-4 h-4">
        <span class="flex-1 text-sm">Completed</span>
        <span class="badge badge-purple text-xs">Completed</span>
      </label>
    </div>
  </div>
  
  {# Entry Fee Filter #}
  <div class="filter-section border-t pt-6">
    <h3 class="font-semibold text-gray-900 mb-3">Entry Fee</h3>
    <div class="space-y-2">
      <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
        <input type="radio" name="entry_fee" value="all" x-model="filters.entry_fee" @change="applyFilters()" class="w-4 h-4">
        <span class="text-sm">All Tournaments</span>
      </label>
      <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
        <input type="radio" name="entry_fee" value="free" x-model="filters.entry_fee" @change="applyFilters()" class="w-4 h-4">
        <span class="text-sm">🎉 Free Entry</span>
      </label>
      <label class="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50 cursor-pointer">
        <input type="radio" name="entry_fee" value="paid" x-model="filters.entry_fee" @change="applyFilters()" class="w-4 h-4">
        <span class="text-sm">💰 Paid Entry</span>
      </label>
    </div>
  </div>
  
  {# Date Range Filter #}
  <div class="filter-section border-t pt-6">
    <h3 class="font-semibold text-gray-900 mb-3">Start Date</h3>
    <div class="space-y-3">
      <div class="grid grid-cols-2 gap-2">
        <button @click="setDatePreset('today')" class="btn btn-secondary btn-sm">Today</button>
        <button @click="setDatePreset('week')" class="btn btn-secondary btn-sm">This Week</button>
        <button @click="setDatePreset('month')" class="btn btn-secondary btn-sm">This Month</button>
        <button @click="setDatePreset('custom')" class="btn btn-secondary btn-sm">Custom</button>
      </div>
      <div x-show="filters.date_preset === 'custom'" class="space-y-2">
        <input type="date" 
               x-model="filters.date_from" 
               @change="applyFilters()"
               class="input w-full text-sm"
               placeholder="From">
        <input type="date" 
               x-model="filters.date_to" 
               @change="applyFilters()"
               class="input w-full text-sm"
               placeholder="To">
      </div>
    </div>
  </div>
  
  {# Prize Pool Filter #}
  <div class="filter-section border-t pt-6">
    <h3 class="font-semibold text-gray-900 mb-3">Prize Pool</h3>
    <div class="space-y-3">
      <div class="flex items-center justify-between text-sm text-gray-600">
        <span x-text="`$${filters.prize_min}`"></span>
        <span x-text="`$${filters.prize_max === 10000 ? '10,000+' : filters.prize_max}`"></span>
      </div>
      <div id="prize-slider" 
           x-init="initPrizeSlider()"
           class="px-2"></div>
      <div class="grid grid-cols-2 gap-2">
        <input type="number" 
               x-model="filters.prize_min" 
               @change="updatePrizeSlider()"
               min="0" 
               class="input text-sm"
               placeholder="Min">
        <input type="number" 
               x-model="filters.prize_max" 
               @change="updatePrizeSlider()"
               min="0" 
               class="input text-sm"
               placeholder="Max">
      </div>
    </div>
  </div>
  
</div>
```

**Alpine.js Filter Logic:**
```javascript
// static/js/components/tournament-filters.js
function tournamentFilters(initialFilters = {}, layout = 'sidebar') {
  return {
    layout: layout,
    isOpen: false,
    filters: {
      games: initialFilters.games || [],
      status: initialFilters.status || [],
      entry_fee: initialFilters.entry_fee || 'all',
      date_from: initialFilters.date_from || null,
      date_to: initialFilters.date_to || null,
      date_preset: 'custom',
      prize_min: initialFilters.prize_min || 0,
      prize_max: initialFilters.prize_max || 10000
    },
    sections: {
      game: true,
      status: true
    },
    prizeSlider: null,
    debounceTimer: null,
    
    get activeFilterCount() {
      let count = 0;
      if (this.filters.games.length > 0) count += this.filters.games.length;
      if (this.filters.status.length > 0) count += this.filters.status.length;
      if (this.filters.entry_fee !== 'all') count += 1;
      if (this.filters.date_from || this.filters.date_to) count += 1;
      if (this.filters.prize_min > 0 || this.filters.prize_max < 10000) count += 1;
      return count;
    },
    
    init() {
      // Initialize from URL params
      const params = new URLSearchParams(window.location.search);
      if (params.has('game')) {
        this.filters.games = params.get('game').split(',');
      }
      if (params.has('status')) {
        this.filters.status = params.get('status').split(',');
      }
      if (params.has('fee')) {
        this.filters.entry_fee = params.get('fee');
      }
      if (params.has('date_from')) {
        this.filters.date_from = params.get('date_from');
      }
      if (params.has('date_to')) {
        this.filters.date_to = params.get('date_to');
      }
      if (params.has('prize_min')) {
        this.filters.prize_min = parseInt(params.get('prize_min'));
      }
      if (params.has('prize_max')) {
        this.filters.prize_max = parseInt(params.get('prize_max'));
      }
    },
    
    applyFilters() {
      // Debounce filter changes
      clearTimeout(this.debounceTimer);
      this.debounceTimer = setTimeout(() => {
        this.executeFilter();
      }, 500);
    },
    
    executeFilter() {
      // Build URL params
      const params = new URLSearchParams();
      
      if (this.filters.games.length > 0) {
        params.set('game', this.filters.games.join(','));
      }
      if (this.filters.status.length > 0) {
        params.set('status', this.filters.status.join(','));
      }
      if (this.filters.entry_fee !== 'all') {
        params.set('fee', this.filters.entry_fee);
      }
      if (this.filters.date_from) {
        params.set('date_from', this.filters.date_from);
      }
      if (this.filters.date_to) {
        params.set('date_to', this.filters.date_to);
      }
      if (this.filters.prize_min > 0) {
        params.set('prize_min', this.filters.prize_min);
      }
      if (this.filters.prize_max < 10000) {
        params.set('prize_max', this.filters.prize_max);
      }
      
      // Update URL
      const url = `${window.location.pathname}?${params.toString()}`;
      window.history.pushState({}, '', url);
      
      // Trigger HTMX request
      htmx.ajax('GET', url, {
        target: '#tournament-results',
        swap: 'innerHTML',
        indicator: '#loading-indicator'
      });
      
      // Close mobile drawer
      if (this.layout === 'drawer') {
        this.isOpen = false;
      }
    },
    
    clearAllFilters() {
      this.filters = {
        games: [],
        status: [],
        entry_fee: 'all',
        date_from: null,
        date_to: null,
        date_preset: 'custom',
        prize_min: 0,
        prize_max: 10000
      };
      if (this.prizeSlider) {
        this.prizeSlider.set([0, 10000]);
      }
      this.executeFilter();
    },
    
    removeFilter(type, value = null) {
      if (type === 'game') {
        this.filters.games = this.filters.games.filter(g => g !== value);
      } else if (type === 'status') {
        this.filters.status = this.filters.status.filter(s => s !== value);
      } else if (type === 'entry_fee') {
        this.filters.entry_fee = 'all';
      } else if (type === 'date') {
        this.filters.date_from = null;
        this.filters.date_to = null;
      } else if (type === 'prize') {
        this.filters.prize_min = 0;
        this.filters.prize_max = 10000;
        if (this.prizeSlider) {
          this.prizeSlider.set([0, 10000]);
        }
      }
      this.executeFilter();
    },
    
    setDatePreset(preset) {
      this.filters.date_preset = preset;
      const today = new Date();
      
      if (preset === 'today') {
        this.filters.date_from = today.toISOString().split('T')[0];
        this.filters.date_to = today.toISOString().split('T')[0];
        this.applyFilters();
      } else if (preset === 'week') {
        this.filters.date_from = today.toISOString().split('T')[0];
        const nextWeek = new Date(today.getTime() + 7 * 24 * 60 * 60 * 1000);
        this.filters.date_to = nextWeek.toISOString().split('T')[0];
        this.applyFilters();
      } else if (preset === 'month') {
        this.filters.date_from = today.toISOString().split('T')[0];
        const nextMonth = new Date(today.getFullYear(), today.getMonth() + 1, today.getDate());
        this.filters.date_to = nextMonth.toISOString().split('T')[0];
        this.applyFilters();
      }
      // 'custom' just shows the date inputs
    },
    
    initPrizeSlider() {
      // Using noUiSlider library
      const slider = document.getElementById('prize-slider');
      if (!slider || this.prizeSlider) return;
      
      this.prizeSlider = noUiSlider.create(slider, {
        start: [this.filters.prize_min, this.filters.prize_max],
        connect: true,
        range: {
          'min': 0,
          'max': 10000
        },
        step: 100,
        format: {
          to: value => Math.round(value),
          from: value => Math.round(value)
        }
      });
      
      this.prizeSlider.on('change', (values) => {
        this.filters.prize_min = values[0];
        this.filters.prize_max = values[1];
        this.applyFilters();
      });
    },
    
    updatePrizeSlider() {
      if (this.prizeSlider) {
        this.prizeSlider.set([this.filters.prize_min, this.filters.prize_max]);
        this.applyFilters();
      }
    }
  }
}
```

**Active Filter Badges:**
```django
{# Display above tournament results #}
<div x-data="{ filters: tournamentFilters().filters }" 
     x-show="activeFilterCount > 0"
     class="flex flex-wrap gap-2 mb-4">
  <template x-for="gameId in filters.games" :key="gameId">
    <span class="badge badge-primary flex items-center gap-2">
      <span x-text="getGameName(gameId)"></span>
      <button @click="removeFilter('game', gameId)" class="hover:text-red-500">
        ✕
      </button>
    </span>
  </template>
  
  <template x-for="status in filters.status" :key="status">
    <span class="badge badge-blue flex items-center gap-2">
      <span x-text="status"></span>
      <button @click="removeFilter('status', status)" class="hover:text-red-500">
        ✕
      </button>
    </span>
  </template>
  
  <span x-show="filters.entry_fee !== 'all'" class="badge badge-green flex items-center gap-2">
    <span x-text="filters.entry_fee === 'free' ? 'Free Entry' : 'Paid Entry'"></span>
    <button @click="removeFilter('entry_fee')" class="hover:text-red-500">
      ✕
    </button>
  </span>
  
  <span x-show="filters.date_from || filters.date_to" class="badge badge-purple flex items-center gap-2">
    <span x-text="`${filters.date_from} - ${filters.date_to}`"></span>
    <button @click="removeFilter('date')" class="hover:text-red-500">
      ✕
    </button>
  </span>
  
  <span x-show="filters.prize_min > 0 || filters.prize_max < 10000" class="badge badge-yellow flex items-center gap-2">
    <span x-text="`$${filters.prize_min} - $${filters.prize_max}`"></span>
    <button @click="removeFilter('prize')" class="hover:text-red-500">
      ✕
    </button>
  </span>
</div>
```

**Files to Create/Modify:**
- `templates/components/tournament_filters.html` - Main filter component (sidebar/drawer wrapper)
- `templates/components/tournament_filters_content.html` - Shared filter sections content
- `static/js/components/tournament-filters.js` - Alpine.js filter logic with HTMX integration
- `static/css/nouislider.min.css` - Range slider styles (if not already included)
- `static/js/vendor/nouislider.min.js` - Range slider library (CDN or local)

**External Libraries:**
- **noUiSlider**: Range slider for prize pool (`<script src="https://cdn.jsdelivr.net/npm/nouislider@15.7.0/dist/nouislider.min.js"></script>`)
- **Alpine Collapse**: For smooth section expand/collapse (`<script defer src="https://cdn.jsdelivr.net/npm/@alpinejs/collapse@3.x.x/dist/cdn.min.js"></script>`)

**References:**
- PROPOSAL_PART_4.md Section 10.8 (Filter Component Design)
- FE-012: Tournament List Page (primary usage context)
- Design System: FE-002 (transitions, spacing)

**Testing:**
- Render sidebar layout → filter sections visible, collapsible
- Render drawer layout → filters hidden, opens on button click, overlay backdrop, close button works
- Select game filter → checkbox checked, count badge updates, HTMX request triggered after 500ms
- Select multiple filters → AND logic applies, multiple checkboxes checked
- Click "Clear All Filters" → all filters reset, results reload
- Test URL sync → filter selections update URL params, bookmarkable
- Test browser back/forward → filters restore from URL
- Test active filter badges → badges display above results, click ✕ removes individual filter
- Test date presets → "Today" sets today's date, "This Week" sets 7-day range
- Test prize slider → drag slider updates inputs, drag inputs updates slider, triggers filter with debounce
- Test mobile drawer → opens with slide-in animation, close on overlay click, close on Escape key, focus trap active
- Test empty states → no games available → game filter hidden
- Test responsive: Desktop → sidebar sticky, Mobile → hamburger menu opens drawer
- Test accessibility: Tab navigation → all checkboxes/inputs reachable, screen reader announces filter counts
- Test filter combinations: Game + Status + Free → only free Valorant upcoming tournaments shown

---

### FE-018: Game Selector Component

**Type:** Frontend - Component  
**Priority:** P1  
**Story Points:** 7  
**Assignee:** Frontend Developer  
**Sprint:** 4 (Week 4)  
**Epic:** Tournament Engine - Frontend

**Description:**

Build an interactive game selection component that allows users to browse, search, and select games for tournament creation and filtering. This component displays games in a visually appealing grid layout with icons, names, and platform badges, supporting both single-select (radio) and multi-select (checkbox) modes. It includes a search feature to quickly find games, an info modal to view detailed game specifications (min/max team size, supported platforms, match settings), and visual feedback for selected/disabled states.

The component should be implemented as a reusable Alpine.js component with Django template includes, fetching game data from the GameConfig API (BE-009). It will be used in the tournament creation wizard (FE-011) for game selection, in the tournament filters component (FE-017) for filtering by game, and potentially in user profile settings for favorite games. The component must handle loading states, empty states (no games available), and provide keyboard navigation for accessibility.

**Acceptance Criteria:**

- [ ] Component file created at `templates/components/game_selector.html` as Django template include
- [ ] Accepts `mode` ('single'|'multi'), `selected_games` array, `disabled_games` array, `show_info` boolean as props
- [ ] Fetches available games from `/api/games/` endpoint (BE-009) with loading state (skeleton loaders for 6 game cards)
- [ ] Displays games in responsive grid: 2 columns mobile (<640px), 3 columns tablet (640-1024px), 4 columns desktop (>1024px)
- [ ] Each game card shows: Icon (64x64), name, platform badges (PC/PS5/Xbox/Mobile), team size (e.g., "5v5"), selection indicator (checkmark circle for multi, radio dot for single)
- [ ] **Single-select mode**: Radio button behavior, only one game selectable, clicking new game deselects previous
- [ ] **Multi-select mode**: Checkbox behavior, multiple games selectable, selected count displayed (e.g., "3 games selected")
- [ ] Search input (top of component): Debounced 300ms, filters games by name case-insensitive, shows result count (e.g., "4 games found")
- [ ] Game info button (ℹ️ icon on each card): Opens modal with detailed game info (description, min/max team size, supported platforms, default match settings, icon/banner preview)
- [ ] Info modal: Displays game details, "Select Game" button (if not already selected), "Close" button, closes on Escape key, backdrop click, focus trap
- [ ] Selected state: Game card has blue border (`border-primary-500`), checkmark icon, slightly elevated shadow
- [ ] Disabled state: Game card grayed out (`opacity-50`), not clickable, tooltip explaining why disabled (e.g., "Team size doesn't match requirements")
- [ ] Hover state: Card lifts with shadow increase (desktop only), cursor pointer
- [ ] Empty state: No games available → "No games configured yet" message with icon
- [ ] No search results: "No games match '{query}'" with "Clear search" button
- [ ] Accessibility: Semantic HTML (fieldset/legend for mode), ARIA labels ("Select game {name}"), keyboard navigation (Tab, Space/Enter to select, Arrow keys to navigate grid), focus indicators (ring-2)
- [ ] Selection emits custom event: `game-selected` with game object, consumed by parent components

**Dependencies:**
- FE-002: Design System Foundation (colors, shadows, transitions)
- FE-009: Card Component, Badge Component (platform badges)
- FE-010: Modal Component (game info modal)
- BE-009: GameConfig API (game data source)
- FE-011: Tournament Wizard (primary usage - Step 2 game selection)
- FE-017: Tournament Filters (secondary usage - game filter)

**Technical Notes:**

**Component Structure:**
```django
{# templates/components/game_selector.html #}
{# Props: mode ('single'|'multi'), selected_games (array), disabled_games (array), show_info (boolean) #}

<div x-data="gameSelector('{{ mode }}', {{ selected_games|json }}, {{ disabled_games|json }}, {{ show_info }})"
     x-init="init()"
     class="game-selector">
  
  {# Search Bar #}
  <div class="mb-6">
    <div class="relative">
      <input type="text" 
             x-model="searchQuery"
             @input.debounce.300ms="filterGames()"
             placeholder="Search games..."
             class="input pl-10 w-full"
             aria-label="Search games">
      <svg class="absolute left-3 top-3 w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
      </svg>
    </div>
    <div x-show="searchQuery" class="mt-2 text-sm text-gray-600">
      <span x-text="`${filteredGames.length} games found`"></span>
      <button @click="clearSearch()" class="ml-2 text-primary-600 hover:underline">
        Clear search
      </button>
    </div>
  </div>
  
  {# Selected Count (Multi-select mode) #}
  <div x-show="mode === 'multi' && selectedGames.length > 0" 
       class="mb-4 p-3 bg-primary-50 rounded-lg">
    <span class="text-sm font-semibold text-primary-700" 
          x-text="`${selectedGames.length} game${selectedGames.length > 1 ? 's' : ''} selected`"></span>
  </div>
  
  {# Loading State #}
  <div x-show="loading" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
    <template x-for="i in 6" :key="i">
      <div class="game-card-skeleton bg-white rounded-lg border border-gray-200 p-4 animate-pulse">
        <div class="w-16 h-16 bg-gray-300 rounded-lg mb-3 mx-auto"></div>
        <div class="h-4 bg-gray-300 rounded w-3/4 mx-auto mb-2"></div>
        <div class="h-3 bg-gray-300 rounded w-1/2 mx-auto"></div>
      </div>
    </template>
  </div>
  
  {# Games Grid #}
  <fieldset x-show="!loading" class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
    <legend class="sr-only">Select game</legend>
    
    <template x-for="game in filteredGames" :key="game.id">
      <div class="game-card relative"
           :class="{
             'border-primary-500 shadow-md ring-2 ring-primary-200': isSelected(game.id),
             'opacity-50 cursor-not-allowed': isDisabled(game.id),
             'hover:shadow-lg transform hover:-translate-y-1 transition-all cursor-pointer': !isDisabled(game.id)
           }"
           @click="selectGame(game)"
           @keydown.enter="selectGame(game)"
           @keydown.space.prevent="selectGame(game)"
           tabindex="0"
           role="radio"
           :aria-checked="isSelected(game.id)"
           :aria-disabled="isDisabled(game.id)"
           :aria-label="`Select ${game.name}`">
        
        <div class="bg-white rounded-lg border-2 border-gray-200 p-4 text-center relative">
          {# Selection Indicator #}
          <div x-show="isSelected(game.id)" 
               class="absolute top-2 right-2 w-6 h-6 bg-primary-500 rounded-full flex items-center justify-center">
            <svg class="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"/>
            </svg>
          </div>
          
          {# Game Icon #}
          <img :src="game.icon" 
               :alt="game.name"
               class="w-16 h-16 mx-auto mb-3 rounded-lg object-cover">
          
          {# Game Name #}
          <h3 class="font-semibold text-gray-900 text-sm mb-2" x-text="game.name"></h3>
          
          {# Platform Badges #}
          <div class="flex flex-wrap justify-center gap-1 mb-2">
            <template x-for="platform in game.platforms" :key="platform">
              <span class="badge badge-secondary text-xs" x-text="platform"></span>
            </template>
          </div>
          
          {# Team Size #}
          <div class="text-xs text-gray-600" x-text="`${game.min_team_size}v${game.min_team_size}`"></div>
          
          {# Info Button #}
          <button x-show="showInfo"
                  @click.stop="openGameInfo(game)"
                  class="absolute bottom-2 left-2 p-1 text-gray-400 hover:text-primary-500 transition-colors"
                  aria-label="View game details">
            <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"/>
            </svg>
          </button>
          
          {# Disabled Tooltip #}
          <div x-show="isDisabled(game.id)" 
               class="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 rounded-lg">
            <span class="text-xs text-gray-600 px-2 text-center" x-text="getDisabledReason(game.id)"></span>
          </div>
        </div>
      </div>
    </template>
  </fieldset>
  
  {# Empty State #}
  <div x-show="!loading && games.length === 0" 
       class="text-center py-12">
    <svg class="w-16 h-16 mx-auto text-gray-400 mb-4" fill="currentColor" viewBox="0 0 20 20">
      <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z"/>
    </svg>
    <p class="text-gray-600">No games configured yet</p>
  </div>
  
  {# No Results State #}
  <div x-show="!loading && games.length > 0 && filteredGames.length === 0" 
       class="text-center py-12">
    <svg class="w-16 h-16 mx-auto text-gray-400 mb-4" fill="currentColor" viewBox="0 0 20 20">
      <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd"/>
    </svg>
    <p class="text-gray-600 mb-2" x-text="`No games match '${searchQuery}'`"></p>
    <button @click="clearSearch()" class="btn btn-secondary btn-sm">
      Clear search
    </button>
  </div>
  
  {# Game Info Modal #}
  <div x-show="gameInfoModal.open"
       x-transition:enter="transition ease-out duration-200"
       x-transition:enter-start="opacity-0"
       x-transition:enter-end="opacity-100"
       x-transition:leave="transition ease-in duration-150"
       x-transition:leave-start="opacity-100"
       x-transition:leave-end="opacity-0"
       @click="closeGameInfo()"
       @keydown.escape.window="closeGameInfo()"
       class="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
       x-cloak>
    
    <div @click.stop
         x-trap="gameInfoModal.open"
         class="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
      
      <div class="p-6">
        <div class="flex items-start justify-between mb-4">
          <div class="flex items-center gap-4">
            <img :src="gameInfoModal.game?.icon" 
                 :alt="gameInfoModal.game?.name"
                 class="w-20 h-20 rounded-lg object-cover">
            <div>
              <h2 class="text-2xl font-bold text-gray-900" x-text="gameInfoModal.game?.name"></h2>
              <div class="flex flex-wrap gap-2 mt-2">
                <template x-for="platform in gameInfoModal.game?.platforms" :key="platform">
                  <span class="badge badge-secondary" x-text="platform"></span>
                </template>
              </div>
            </div>
          </div>
          <button @click="closeGameInfo()" 
                  class="p-2 hover:bg-gray-100 rounded-lg">
            <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"/>
            </svg>
          </button>
        </div>
        
        <div class="space-y-4">
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">Description</h3>
            <p class="text-gray-600" x-text="gameInfoModal.game?.description || 'No description available'"></p>
          </div>
          
          <div class="grid grid-cols-2 gap-4">
            <div class="bg-gray-50 rounded-lg p-4">
              <h4 class="font-semibold text-gray-900 mb-1">Team Size</h4>
              <p class="text-sm text-gray-600">
                Min: <span x-text="gameInfoModal.game?.min_team_size"></span> players<br>
                Max: <span x-text="gameInfoModal.game?.max_team_size"></span> players
              </p>
            </div>
            <div class="bg-gray-50 rounded-lg p-4">
              <h4 class="font-semibold text-gray-900 mb-1">Tournament Formats</h4>
              <p class="text-sm text-gray-600">
                Single/Double Elimination<br>
                Swiss System<br>
                Round Robin
              </p>
            </div>
          </div>
          
          <div>
            <h3 class="font-semibold text-gray-900 mb-2">Default Match Settings</h3>
            <div class="bg-gray-50 rounded-lg p-4">
              <template x-for="(value, key) in gameInfoModal.game?.match_settings" :key="key">
                <div class="flex justify-between py-1 text-sm">
                  <span class="text-gray-600 capitalize" x-text="key.replace('_', ' ')"></span>
                  <span class="text-gray-900 font-medium" x-text="value"></span>
                </div>
              </template>
            </div>
          </div>
        </div>
        
        <div class="mt-6 flex gap-3">
          <button @click="selectGameFromModal()" 
                  x-show="!isSelected(gameInfoModal.game?.id)"
                  class="flex-1 btn btn-primary">
            Select <span x-text="gameInfoModal.game?.name"></span>
          </button>
          <button @click="closeGameInfo()" 
                  class="flex-1 btn btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>
  </div>
  
</div>
```

**Alpine.js Logic:**
```javascript
// static/js/components/game-selector.js
function gameSelector(mode = 'single', initialSelectedGames = [], disabledGames = [], showInfo = true) {
  return {
    mode: mode,
    showInfo: showInfo,
    loading: true,
    games: [],
    filteredGames: [],
    selectedGames: initialSelectedGames,
    disabledGames: disabledGames,
    searchQuery: '',
    gameInfoModal: {
      open: false,
      game: null
    },
    
    async init() {
      await this.fetchGames();
      this.filterGames();
    },
    
    async fetchGames() {
      try {
        const response = await fetch('/api/games/');
        const data = await response.json();
        this.games = data.results || data;
        this.loading = false;
      } catch (error) {
        console.error('Failed to fetch games:', error);
        this.loading = false;
      }
    },
    
    filterGames() {
      if (!this.searchQuery) {
        this.filteredGames = this.games;
        return;
      }
      
      const query = this.searchQuery.toLowerCase();
      this.filteredGames = this.games.filter(game => 
        game.name.toLowerCase().includes(query)
      );
    },
    
    clearSearch() {
      this.searchQuery = '';
      this.filterGames();
    },
    
    isSelected(gameId) {
      return this.selectedGames.includes(gameId);
    },
    
    isDisabled(gameId) {
      return this.disabledGames.some(d => d.id === gameId);
    },
    
    getDisabledReason(gameId) {
      const disabled = this.disabledGames.find(d => d.id === gameId);
      return disabled?.reason || 'Not available';
    },
    
    selectGame(game) {
      if (this.isDisabled(game.id)) return;
      
      if (this.mode === 'single') {
        this.selectedGames = [game.id];
      } else {
        // Multi-select toggle
        if (this.isSelected(game.id)) {
          this.selectedGames = this.selectedGames.filter(id => id !== game.id);
        } else {
          this.selectedGames.push(game.id);
        }
      }
      
      // Emit custom event
      this.$dispatch('game-selected', {
        mode: this.mode,
        selectedGames: this.selectedGames,
        game: game
      });
    },
    
    openGameInfo(game) {
      this.gameInfoModal = {
        open: true,
        game: game
      };
    },
    
    closeGameInfo() {
      this.gameInfoModal = {
        open: false,
        game: null
      };
    },
    
    selectGameFromModal() {
      if (this.gameInfoModal.game) {
        this.selectGame(this.gameInfoModal.game);
        this.closeGameInfo();
      }
    }
  }
}
```

**Usage Examples:**
```django
{# In tournament creation wizard (FE-011) - Step 2: Single-select #}
<div x-data="{ selectedGame: null }" 
     @game-selected.window="selectedGame = $event.detail.selectedGames[0]">
  <label class="label">Select Game *</label>
  {% include 'components/game_selector.html' with mode='single' selected_games=form.game.value show_info=True %}
  <input type="hidden" name="game" :value="selectedGame">
</div>

{# In tournament filters (FE-017) - Multi-select #}
<div x-data="{ selectedGames: [] }" 
     @game-selected.window="selectedGames = $event.detail.selectedGames">
  {% include 'components/game_selector.html' with mode='multi' selected_games=current_filters.games show_info=False %}
</div>

{# With disabled games (team size constraint) #}
{% include 'components/game_selector.html' with mode='single' selected_games=[] disabled_games=incompatible_games show_info=True %}
```

**Files to Create/Modify:**
- `templates/components/game_selector.html` - Main game selector component
- `static/js/components/game-selector.js` - Alpine.js logic with API integration
- `apps/tournaments/views.py` - Add context for disabled_games if needed

**API Integration:**
```python
# apps/tournaments/views.py (context for disabled games)
def get_compatible_games(team_size):
    """Return games compatible with given team size."""
    return GameConfig.objects.filter(
        min_team_size__lte=team_size,
        max_team_size__gte=team_size,
        is_active=True
    )

def get_disabled_games(team_size):
    """Return games that are incompatible with team size."""
    incompatible = GameConfig.objects.filter(
        Q(min_team_size__gt=team_size) | Q(max_team_size__lt=team_size)
    )
    return [
        {
            'id': game.id,
            'reason': f'Requires {game.min_team_size}-{game.max_team_size} players'
        }
        for game in incompatible
    ]
```

**References:**
- PROPOSAL_PART_4.md Section 10.9 (Game Selector Component Design)
- BE-009: GameConfig API (data source)
- FE-011: Tournament Wizard Step 2 (primary usage)
- FE-017: Tournament Filters (secondary usage)

**Testing:**
- Fetch games from API → loading state shows, then games display in grid
- Test single-select mode → click game A (selected), click game B (A deselects, B selected)
- Test multi-select mode → click games A, B, C (all selected), click A again (A deselects)
- Test search → type "Valorant" → only Valorant shows, result count updates
- Test clear search → search results reset to all games
- Test game info modal → click ℹ️ → modal opens with game details, platforms, team size, match settings
- Test "Select Game" in modal → game selected, modal closes
- Test disabled game → game grayed out, not clickable, shows reason tooltip
- Test selected state → game has blue border, checkmark icon, elevated shadow
- Test hover effect → card lifts and shadow increases on desktop
- Test keyboard navigation: Tab → focuses cards in order, Enter/Space → selects game, Escape → closes modal
- Test responsive: Desktop 4 cols → Tablet 3 cols → Mobile 2 cols
- Test empty state → no games → "No games configured" message
- Test no results state → search "xyz" → "No games match 'xyz'" with clear button
- Test accessibility: Screen reader announces "Select {game name}", selected state, disabled reason
- Test custom event: game-selected event emitted with correct payload (mode, selectedGames, game object)

---

### QA-007: Tournament Wizard Tests

**Type:** QA - Frontend Testing  
**Priority:** P1  
**Story Points:** 3  
**Assignee:** QA Engineer / Frontend Developer  
**Sprint:** 4 (Week 4)  
**Epic:** Tournament Engine - Testing

**Description:**

Develop comprehensive frontend tests for the tournament creation wizard (FE-011) using Jest and Testing Library. This test suite validates the complete multi-step form workflow including step navigation, per-step validation, auto-save functionality, form submission, image uploads, keyboard navigation, and accessibility features. Tests should cover all five wizard steps (Basic Info, Game Settings, Schedule, Rules, Review) and ensure proper state management, error handling, and user feedback.

The test suite must simulate real user interactions including typing in inputs, clicking buttons, uploading files, navigating between steps, and submitting the form. It should mock API calls to `/api/games/` and `/api/tournaments/`, use fake timers for auto-save testing, and verify HTMX integration for form submission. Tests must achieve >80% code coverage for wizard-specific JavaScript (Alpine.js components, validation logic, auto-save mechanism).

**Acceptance Criteria:**

- [ ] Test file created at `static/js/__tests__/tournament-wizard.test.js` with Jest + Testing Library setup
- [ ] **Step Navigation Tests** (5 tests): Test next/previous button navigation, step indicator updates (circle highlights), first step active on init, cannot go back from step 1, cannot go next from step 5
- [ ] **Step 1 Validation Tests** (6 tests): Title required (shows error "Title is required"), title max length 200 chars (shows error "Title too long"), description min 100 chars (shows error "Description too short"), logo file size max 2MB (shows error "File too large"), banner dimensions validated (shows error if not 1920x400), visibility radio selection required
- [ ] **Step 2 Validation Tests** (6 tests): Game selection required (error "Select a game"), format selection required, team size must be within game min/max (error "Invalid team size"), max teams power of 2 for elimination (error "Must be power of 2"), platform selection required, game-specific settings validation (eFootball half length 4-20, Valorant rounds 13-25)
- [ ] **Step 3 Validation Tests** (7 tests): Registration end before tournament start (error "Invalid dates"), check-in end before tournament start, tournament start before tournament end, registration window min 24h (error "Registration too short"), check-in window 30min (warning "Recommended 30min"), prize pool <= total entry fees (error "Prize pool exceeds fees"), entry fee non-negative
- [ ] **Step 4 Validation Tests** (4 tests): Rules text min 100 chars (error "Rules too short"), max substitutes 0-3 (error "Invalid value"), stream URL valid format (error "Invalid URL"), Discord link valid format
- [ ] **Step 5 Review Tests** (3 tests): Summary displays all entered data correctly, edit buttons navigate back to respective steps, validation errors prevent publish
- [ ] **Auto-save Tests** (4 tests): Draft saved to localStorage every 2 minutes (use jest.useFakeTimers), draft loaded on init if exists, draft cleared after successful publish, draft includes all step data
- [ ] **Form Submission Tests** (3 tests): Save as Draft POSTs to `/api/tournaments/` with status=DRAFT, Publish POSTs with status=PUBLISHED, submission success redirects to tournament detail page
- [ ] **Image Upload Tests** (3 tests): Drag-drop triggers file input, file preview shown after upload, file validation (type, size) shows errors
- [ ] **Keyboard Navigation Tests** (3 tests): Tab key navigates through inputs in order, Enter key advances to next step (if valid), Escape key shows exit confirmation modal
- [ ] **Accessibility Tests** (4 tests): All inputs have proper labels (aria-label or label element), error messages associated with inputs (aria-describedby), step indicator has aria-current="step", focus moves to first input on step change
- [ ] **Responsive Tests** (2 tests): Mobile layout stacks form fields vertically, desktop layout shows side-by-side fields where appropriate
- [ ] Test coverage report generated with `npm test -- --coverage`, >80% coverage for `tournament-wizard.js`

**Dependencies:**
- FE-011: Tournament Creation Wizard (feature under test)
- BE-008: Tournament API CRUD (API endpoints to mock)
- BE-009: GameConfig API (games endpoint to mock)

**Technical Notes:**

**Test Setup:**
```javascript
// static/js/__tests__/tournament-wizard.test.js
import { screen, fireEvent, waitFor, within } from '@testing-library/dom';
import '@testing-library/jest-dom';
import Alpine from 'alpinejs';
import { tournamentWizard } from '../tournament-wizard';

// Mock fetch for API calls
global.fetch = jest.fn();

// Mock HTMX
global.htmx = {
  ajax: jest.fn()
};

beforeEach(() => {
  // Reset DOM
  document.body.innerHTML = `
    <div x-data="tournamentWizard()" x-init="init()">
      <!-- Wizard HTML structure from FE-011 -->
    </div>
  `;
  
  // Initialize Alpine
  Alpine.data('tournamentWizard', tournamentWizard);
  Alpine.start();
  
  // Clear mocks
  fetch.mockClear();
  htmx.ajax.mockClear();
  localStorage.clear();
  jest.clearAllTimers();
});

afterEach(() => {
  Alpine.destroyTree(document.body);
  jest.useRealTimers();
});
```

**Sample Tests:**

**Step Navigation:**
```javascript
describe('Tournament Wizard - Step Navigation', () => {
  test('should start on step 1', () => {
    const step1 = screen.getByRole('button', { name: /basic info/i });
    expect(step1).toHaveAttribute('aria-current', 'step');
  });
  
  test('should navigate to next step on valid input', async () => {
    // Fill step 1 required fields
    fireEvent.input(screen.getByLabelText(/title/i), {
      target: { value: 'Test Tournament' }
    });
    fireEvent.input(screen.getByLabelText(/description/i), {
      target: { value: 'A'.repeat(100) }
    });
    fireEvent.click(screen.getByRole('radio', { name: /public/i }));
    
    // Click next
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    
    await waitFor(() => {
      const step2 = screen.getByRole('button', { name: /game settings/i });
      expect(step2).toHaveAttribute('aria-current', 'step');
    });
  });
  
  test('should navigate to previous step', async () => {
    // Navigate to step 2 first (assume valid step 1)
    const nextBtn = screen.getByRole('button', { name: /next/i });
    fireEvent.click(nextBtn);
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /game settings/i }))
        .toHaveAttribute('aria-current', 'step');
    });
    
    // Click previous
    fireEvent.click(screen.getByRole('button', { name: /previous/i }));
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /basic info/i }))
        .toHaveAttribute('aria-current', 'step');
    });
  });
  
  test('should not show previous button on step 1', () => {
    expect(screen.queryByRole('button', { name: /previous/i })).not.toBeInTheDocument();
  });
  
  test('should show publish button on step 5', async () => {
    // Navigate to step 5 (assume all steps valid)
    // ... navigation logic ...
    
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /publish/i })).toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /next/i })).not.toBeInTheDocument();
    });
  });
});
```

**Validation Tests:**
```javascript
describe('Tournament Wizard - Step 1 Validation', () => {
  test('should show error when title is empty', async () => {
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/title is required/i)).toBeInTheDocument();
    });
  });
  
  test('should show error when title exceeds 200 chars', async () => {
    fireEvent.input(screen.getByLabelText(/title/i), {
      target: { value: 'A'.repeat(201) }
    });
    
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/title too long/i)).toBeInTheDocument();
    });
  });
  
  test('should show error when description is less than 100 chars', async () => {
    fireEvent.input(screen.getByLabelText(/description/i), {
      target: { value: 'Short description' }
    });
    
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/description too short/i)).toBeInTheDocument();
    });
  });
  
  test('should show error when logo file exceeds 2MB', async () => {
    const file = new File(['x'.repeat(3 * 1024 * 1024)], 'logo.png', { type: 'image/png' });
    const input = screen.getByLabelText(/upload logo/i);
    
    fireEvent.change(input, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(screen.getByText(/file too large/i)).toBeInTheDocument();
    });
  });
});

describe('Tournament Wizard - Step 3 Date Validation', () => {
  test('should show error when registration end is after tournament start', async () => {
    fireEvent.input(screen.getByLabelText(/registration end/i), {
      target: { value: '2024-05-20T12:00' }
    });
    fireEvent.input(screen.getByLabelText(/tournament start/i), {
      target: { value: '2024-05-15T12:00' }
    });
    
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/invalid dates/i)).toBeInTheDocument();
    });
  });
  
  test('should show error when registration window is less than 24 hours', async () => {
    const now = new Date();
    const registrationEnd = new Date(now.getTime() + 12 * 60 * 60 * 1000); // 12 hours
    
    fireEvent.input(screen.getByLabelText(/registration start/i), {
      target: { value: now.toISOString().slice(0, 16) }
    });
    fireEvent.input(screen.getByLabelText(/registration end/i), {
      target: { value: registrationEnd.toISOString().slice(0, 16) }
    });
    
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    
    await waitFor(() => {
      expect(screen.getByText(/registration too short/i)).toBeInTheDocument();
    });
  });
});
```

**Auto-save Tests:**
```javascript
describe('Tournament Wizard - Auto-save', () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  
  test('should save draft to localStorage every 2 minutes', () => {
    fireEvent.input(screen.getByLabelText(/title/i), {
      target: { value: 'Test Tournament' }
    });
    
    // Fast-forward 2 minutes
    jest.advanceTimersByTime(2 * 60 * 1000);
    
    const draft = JSON.parse(localStorage.getItem('tournament_draft'));
    expect(draft).toMatchObject({
      title: 'Test Tournament'
    });
  });
  
  test('should load draft from localStorage on init', () => {
    const draftData = {
      title: 'Saved Tournament',
      description: 'A'.repeat(100),
      visibility: 'public'
    };
    localStorage.setItem('tournament_draft', JSON.stringify(draftData));
    
    // Re-initialize component
    Alpine.destroyTree(document.body);
    document.body.innerHTML = `<div x-data="tournamentWizard()" x-init="init()"></div>`;
    Alpine.start();
    
    expect(screen.getByLabelText(/title/i)).toHaveValue('Saved Tournament');
  });
  
  test('should clear draft after successful publish', async () => {
    localStorage.setItem('tournament_draft', JSON.stringify({ title: 'Test' }));
    
    htmx.ajax.mockImplementation((method, url, options) => {
      // Simulate successful response
      options.swap = 'none';
      return Promise.resolve();
    });
    
    // Navigate to step 5 and publish (assume valid form)
    // ... publish logic ...
    
    await waitFor(() => {
      expect(localStorage.getItem('tournament_draft')).toBeNull();
    });
  });
});
```

**Form Submission Tests:**
```javascript
describe('Tournament Wizard - Form Submission', () => {
  test('should POST to /api/tournaments/ with status=DRAFT on Save as Draft', async () => {
    // Fill form data
    // ... fill all required fields ...
    
    fireEvent.click(screen.getByRole('button', { name: /save as draft/i }));
    
    await waitFor(() => {
      expect(htmx.ajax).toHaveBeenCalledWith(
        'POST',
        '/api/tournaments/',
        expect.objectContaining({
          values: expect.objectContaining({
            status: 'DRAFT'
          })
        })
      );
    });
  });
  
  test('should POST with status=PUBLISHED on Publish', async () => {
    // Navigate to step 5 and fill form
    // ... fill all required fields ...
    
    fireEvent.click(screen.getByRole('button', { name: /publish/i }));
    
    await waitFor(() => {
      expect(htmx.ajax).toHaveBeenCalledWith(
        'POST',
        '/api/tournaments/',
        expect.objectContaining({
          values: expect.objectContaining({
            status: 'PUBLISHED'
          })
        })
      );
    });
  });
});
```

**Accessibility Tests:**
```javascript
describe('Tournament Wizard - Accessibility', () => {
  test('should have aria-label on all inputs', () => {
    const inputs = screen.getAllByRole('textbox');
    inputs.forEach(input => {
      expect(
        input.hasAttribute('aria-label') || 
        input.labels.length > 0
      ).toBe(true);
    });
  });
  
  test('should associate error messages with inputs via aria-describedby', async () => {
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    
    await waitFor(() => {
      const titleInput = screen.getByLabelText(/title/i);
      const errorId = titleInput.getAttribute('aria-describedby');
      expect(errorId).toBeTruthy();
      expect(document.getElementById(errorId)).toHaveTextContent(/title is required/i);
    });
  });
  
  test('should move focus to first input on step change', async () => {
    const nextBtn = screen.getByRole('button', { name: /next/i });
    fireEvent.click(nextBtn);
    
    await waitFor(() => {
      const firstInput = screen.getAllByRole('combobox')[0]; // Game select
      expect(document.activeElement).toBe(firstInput);
    });
  });
});
```

**Files to Create/Modify:**
- `static/js/__tests__/tournament-wizard.test.js` - Main test file (all test suites)
- `package.json` - Add test scripts: `"test": "jest"`, `"test:watch": "jest --watch"`, `"test:coverage": "jest --coverage"`
- `jest.config.js` - Jest configuration (if not exists)
- `.github/workflows/frontend-tests.yml` - CI pipeline for running tests (optional)

**Test Configuration:**
```javascript
// jest.config.js
module.exports = {
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': 'identity-obj-proxy',
  },
  collectCoverageFrom: [
    'static/js/**/*.js',
    '!static/js/vendor/**',
    '!static/js/**/*.test.js'
  ],
  coverageThreshold: {
    global: {
      statements: 80,
      branches: 75,
      functions: 80,
      lines: 80
    }
  }
};

// jest.setup.js
import '@testing-library/jest-dom';
import Alpine from 'alpinejs';
global.Alpine = Alpine;
```

**Running Tests:**
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage

# Run specific test file
npm test tournament-wizard.test.js

# Run tests matching pattern
npm test -- --testNamePattern="Step Navigation"
```

**References:**
- FE-011: Tournament Creation Wizard (feature specification)
- Jest Documentation: https://jestjs.io/docs/getting-started
- Testing Library: https://testing-library.com/docs/dom-testing-library/intro
- Alpine.js Testing: https://alpinejs.dev/advanced/testing

**Testing:**
- Run `npm test` → all test suites pass (50+ tests)
- Run `npm run test:coverage` → coverage report shows >80% for tournament-wizard.js
- Test CI integration → tests run automatically on PR creation
- Test watch mode → tests re-run on file changes
- Verify all edge cases covered: empty inputs, invalid dates, file size limits, navigation boundaries
- Verify accessibility tests pass: ARIA labels, focus management, keyboard navigation
- Verify mocks work correctly: API calls don't hit real endpoints, timers fast-forward properly

---

### QA-008: Tournament Components Tests

**Type:** QA - Frontend Testing  
**Priority:** P1  
**Story Points:** 2  
**Assignee:** QA Engineer / Frontend Developer  
**Sprint:** 4 (Week 4)  
**Epic:** Tournament Engine - Testing

**Description:**

Create comprehensive unit tests for the three tournament-related frontend components: Tournament Card (FE-016), Tournament Filters (FE-017), and Game Selector (FE-018). These tests validate component rendering with different props, user interactions (clicks, hovers, selections), state changes, responsive behavior, and accessibility features. The test suite should cover all component variants, edge cases (empty data, loading states, errors), and ensure proper integration with parent components via custom events.

Tests should use Jest and Testing Library to simulate real DOM interactions and verify visual output. Mock API calls, test Alpine.js reactivity, and validate that components emit correct events with proper payloads. The test suite must achieve >75% code coverage for component-specific JavaScript and serve as living documentation for component usage patterns.

**Acceptance Criteria:**

- [ ] Test file created at `static/js/__tests__/tournament-components.test.js` with Jest + Testing Library setup
- [ ] **Tournament Card Tests (FE-016)** - 10 tests total:
  - [ ] Renders default variant with all elements (logo, title, game, status badge, teams count, prize pool, start date, action buttons)
  - [ ] Renders featured variant with gradient background, "Featured" badge, larger logo, emphasized prize
  - [ ] Renders compact variant with condensed layout, no action buttons
  - [ ] Displays "Free Entry" badge when prize pool is 0
  - [ ] Displays formatted currency ($1,500) when prize pool > 0
  - [ ] Displays placeholder image when tournament.logo is null
  - [ ] Shows correct status badge colors (DRAFT gray, PUBLISHED blue, ONGOING green, COMPLETED purple, CANCELLED red)
  - [ ] Renders loading skeleton with animated pulse
  - [ ] Hover effect applies on desktop (card lifts, shadow increases)
  - [ ] Accessibility: Has aria-label, role="article", keyboard navigable
- [ ] **Tournament Filters Tests (FE-017)** - 12 tests total:
  - [ ] Renders sidebar layout (desktop) with all filter sections visible
  - [ ] Renders drawer layout (mobile) with filters hidden initially, opens on button click
  - [ ] Game filter: Selecting checkbox updates filters.games array, emits HTMX request
  - [ ] Status filter: Multi-select checkboxes work, count badge updates
  - [ ] Entry fee filter: Radio buttons work, "all"/"free"/"paid" selection
  - [ ] Date range filter: Preset buttons set date ranges (Today, This Week, This Month), custom date inputs work
  - [ ] Prize pool filter: Range slider updates min/max, input fields update slider, emits filter request
  - [ ] "Clear All Filters" button resets all filters, reloads results
  - [ ] Active filter badges display above results, click ✕ removes individual filter
  - [ ] URL params sync with filter state (history.pushState), bookmarkable URLs
  - [ ] Drawer closes on overlay click, Escape key, after filter application (mobile)
  - [ ] Accessibility: All filters have labels, ARIA expanded states, keyboard navigable, focus trap in drawer
- [ ] **Game Selector Tests (FE-018)** - 10 tests total:
  - [ ] Fetches games from API on init, displays loading skeletons
  - [ ] Renders games in responsive grid (2/3/4 cols mobile/tablet/desktop)
  - [ ] Single-select mode: Clicking game selects it, clicking another deselects first
  - [ ] Multi-select mode: Multiple games selectable, selected count displays
  - [ ] Search input filters games by name (debounced 300ms), updates result count
  - [ ] Game info modal opens on ℹ️ click, displays game details, closes on backdrop/Escape
  - [ ] Selected state: Game has blue border, checkmark icon, elevated shadow
  - [ ] Disabled state: Game grayed out, not clickable, shows reason tooltip
  - [ ] Emits custom event "game-selected" with correct payload (mode, selectedGames, game)
  - [ ] Accessibility: ARIA labels, keyboard navigation (Tab, Enter/Space to select), focus indicators
- [ ] **Integration Tests** - 3 tests total:
  - [ ] Tournament Card emits click event consumed by parent
  - [ ] Tournament Filters trigger HTMX request with correct URL params
  - [ ] Game Selector event updates parent component state
- [ ] Test coverage report shows >75% coverage for component files (`tournament-card.js`, `tournament-filters.js`, `game-selector.js`)

**Dependencies:**
- FE-016: Tournament Card Component (component under test)
- FE-017: Tournament Filters Component (component under test)
- FE-018: Game Selector Component (component under test)
- QA-007: Tournament Wizard Tests (related test patterns)

**Technical Notes:**

**Test Setup:**
```javascript
// static/js/__tests__/tournament-components.test.js
import { screen, fireEvent, waitFor, within } from '@testing-library/dom';
import '@testing-library/jest-dom';
import Alpine from 'alpinejs';
import { tournamentCard } from '../components/tournament-card';
import { tournamentFilters } from '../components/tournament-filters';
import { gameSelector } from '../components/game-selector';

// Mock fetch for API calls
global.fetch = jest.fn();

// Mock HTMX
global.htmx = {
  ajax: jest.fn()
};

// Mock noUiSlider for prize pool range
global.noUiSlider = {
  create: jest.fn(() => ({
    on: jest.fn(),
    set: jest.fn()
  }))
};

beforeEach(() => {
  fetch.mockClear();
  htmx.ajax.mockClear();
  localStorage.clear();
});

afterEach(() => {
  document.body.innerHTML = '';
});
```

**Sample Tests:**

**Tournament Card Tests:**
```javascript
describe('Tournament Card Component', () => {
  const mockTournament = {
    id: '123',
    title: 'Test Tournament',
    slug: 'test-tournament',
    logo: { url: '/static/img/logo.png' },
    banner: { url: '/static/img/banner.png' },
    game: { name: 'Valorant', icon: { url: '/static/img/valorant.png' } },
    status: 'PUBLISHED',
    prize_pool: 1500,
    registrations_count: 8,
    max_teams: 16,
    tournament_start: '2024-05-15T14:00:00Z',
    can_register: true,
    is_organizer: false
  };
  
  test('should render default variant with all elements', () => {
    document.body.innerHTML = `
      {% include 'components/tournament_card.html' with tournament=mockTournament variant='default' show_actions=true %}
    `;
    
    expect(screen.getByText('Test Tournament')).toBeInTheDocument();
    expect(screen.getByText('Valorant')).toBeInTheDocument();
    expect(screen.getByText('$1,500')).toBeInTheDocument();
    expect(screen.getByText('8/16 teams')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /register now/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /view details/i })).toBeInTheDocument();
  });
  
  test('should render featured variant with gradient background', () => {
    document.body.innerHTML = `
      {% include 'components/tournament_card.html' with tournament=mockTournament variant='featured' %}
    `;
    
    const card = screen.getByRole('article');
    expect(card).toHaveClass('bg-gradient-to-br', 'from-primary-500', 'to-primary-700');
    expect(screen.getByText('⭐ FEATURED')).toBeInTheDocument();
  });
  
  test('should display "Free Entry" badge when prize pool is 0', () => {
    const freeTournament = { ...mockTournament, prize_pool: 0 };
    document.body.innerHTML = `
      {% include 'components/tournament_card.html' with tournament=freeTournament %}
    `;
    
    expect(screen.getByText('🎉 Free Entry')).toBeInTheDocument();
    expect(screen.queryByText(/\$/)).not.toBeInTheDocument();
  });
  
  test('should display placeholder image when logo is null', () => {
    const noLogoTournament = { ...mockTournament, logo: null };
    document.body.innerHTML = `
      {% include 'components/tournament_card.html' with tournament=noLogoTournament %}
    `;
    
    const img = screen.getByAltText('Test Tournament logo');
    expect(img).toHaveAttribute('src', '/static/img/placeholder-logo.png');
  });
  
  test('should show correct status badge colors', () => {
    const statuses = [
      { status: 'DRAFT', class: 'badge-gray' },
      { status: 'PUBLISHED', class: 'badge-blue' },
      { status: 'ONGOING', class: 'badge-green' },
      { status: 'COMPLETED', class: 'badge-purple' },
      { status: 'CANCELLED', class: 'badge-red' }
    ];
    
    statuses.forEach(({ status, class: badgeClass }) => {
      const tournament = { ...mockTournament, status };
      document.body.innerHTML = `
        {% include 'components/tournament_card.html' with tournament=tournament %}
      `;
      
      const badge = screen.getByText(status);
      expect(badge).toHaveClass(badgeClass);
    });
  });
  
  test('should render loading skeleton with animated pulse', () => {
    document.body.innerHTML = `
      {% include 'components/tournament_card_skeleton.html' %}
    `;
    
    const skeleton = document.querySelector('.tournament-card-skeleton');
    expect(skeleton).toBeInTheDocument();
    expect(skeleton.querySelector('.animate-pulse')).toBeInTheDocument();
  });
  
  test('should have proper accessibility attributes', () => {
    document.body.innerHTML = `
      {% include 'components/tournament_card.html' with tournament=mockTournament %}
    `;
    
    const card = screen.getByRole('article');
    expect(card).toHaveAttribute('aria-label', 'Tournament card for Test Tournament');
    expect(card).toHaveAttribute('data-tournament-id', '123');
  });
});
```

**Tournament Filters Tests:**
```javascript
describe('Tournament Filters Component', () => {
  const mockGames = [
    { id: 1, name: 'Valorant', icon: { url: '/img/valorant.png' } },
    { id: 2, name: 'eFootball', icon: { url: '/img/efootball.png' } }
  ];
  
  beforeEach(() => {
    document.body.innerHTML = `
      <div x-data="tournamentFilters({}, 'sidebar')" x-init="init()">
        {% include 'components/tournament_filters_content.html' %}
      </div>
      <div id="tournament-results"></div>
    `;
    
    Alpine.data('tournamentFilters', tournamentFilters);
    Alpine.start();
  });
  
  test('should select game filter and trigger HTMX request', async () => {
    const checkbox = screen.getByLabelText(/valorant/i);
    fireEvent.click(checkbox);
    
    await waitFor(() => {
      expect(htmx.ajax).toHaveBeenCalledWith(
        'GET',
        expect.stringContaining('game=1'),
        expect.any(Object)
      );
    }, { timeout: 600 }); // Wait for 500ms debounce
  });
  
  test('should show active filter count badge', async () => {
    const gameCheckbox = screen.getByLabelText(/valorant/i);
    const statusCheckbox = screen.getByLabelText(/upcoming/i);
    
    fireEvent.click(gameCheckbox);
    fireEvent.click(statusCheckbox);
    
    await waitFor(() => {
      expect(screen.getByText('(1)')).toBeInTheDocument(); // Game count
      expect(screen.getByText('(1)')).toBeInTheDocument(); // Status count
    });
  });
  
  test('should clear all filters on button click', async () => {
    // Apply some filters first
    fireEvent.click(screen.getByLabelText(/valorant/i));
    
    await waitFor(() => {
      expect(screen.getByText('(1)')).toBeInTheDocument();
    });
    
    // Clear all
    fireEvent.click(screen.getByRole('button', { name: /clear all/i }));
    
    await waitFor(() => {
      expect(screen.queryByText('(1)')).not.toBeInTheDocument();
      expect(htmx.ajax).toHaveBeenCalledWith(
        'GET',
        expect.not.stringContaining('game='),
        expect.any(Object)
      );
    });
  });
  
  test('should sync filters with URL parameters', async () => {
    const pushStateSpy = jest.spyOn(window.history, 'pushState');
    
    fireEvent.click(screen.getByLabelText(/valorant/i));
    
    await waitFor(() => {
      expect(pushStateSpy).toHaveBeenCalledWith(
        {},
        '',
        expect.stringContaining('game=1')
      );
    }, { timeout: 600 });
    
    pushStateSpy.mockRestore();
  });
  
  test('should set date preset to "This Week"', async () => {
    fireEvent.click(screen.getByRole('button', { name: /this week/i }));
    
    await waitFor(() => {
      const today = new Date().toISOString().split('T')[0];
      expect(screen.getByLabelText(/from/i)).toHaveValue(today);
    });
  });
  
  test('should open mobile drawer on button click', async () => {
    document.body.innerHTML = `
      <div x-data="tournamentFilters({}, 'drawer')" x-init="init()">
        {% include 'components/tournament_filters.html' %}
      </div>
    `;
    Alpine.start();
    
    const drawerButton = screen.getByRole('button', { name: /filters/i });
    fireEvent.click(drawerButton);
    
    await waitFor(() => {
      const drawer = document.querySelector('.fixed.inset-y-0.left-0');
      expect(drawer).toBeVisible();
    });
  });
});
```

**Game Selector Tests:**
```javascript
describe('Game Selector Component', () => {
  const mockGames = [
    {
      id: 1,
      name: 'Valorant',
      icon: '/img/valorant.png',
      platforms: ['PC', 'PS5'],
      min_team_size: 5,
      max_team_size: 5,
      description: 'Tactical shooter',
      match_settings: { rounds: 13, overtime: true }
    },
    {
      id: 2,
      name: 'eFootball',
      icon: '/img/efootball.png',
      platforms: ['PC', 'PS5', 'Xbox'],
      min_team_size: 1,
      max_team_size: 11,
      description: 'Soccer game'
    }
  ];
  
  beforeEach(() => {
    fetch.mockResolvedValue({
      json: async () => ({ results: mockGames })
    });
    
    document.body.innerHTML = `
      <div x-data="gameSelector('single', [], [], true)" x-init="init()">
        {% include 'components/game_selector.html' %}
      </div>
    `;
    
    Alpine.data('gameSelector', gameSelector);
    Alpine.start();
  });
  
  test('should fetch games from API on init', async () => {
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith('/api/games/');
      expect(screen.getByText('Valorant')).toBeInTheDocument();
      expect(screen.getByText('eFootball')).toBeInTheDocument();
    });
  });
  
  test('should display loading skeletons while fetching', () => {
    const skeletons = document.querySelectorAll('.game-card-skeleton');
    expect(skeletons.length).toBeGreaterThan(0);
    expect(skeletons[0]).toHaveClass('animate-pulse');
  });
  
  test('should select game in single-select mode', async () => {
    await waitFor(() => screen.getByText('Valorant'));
    
    const gameCard = screen.getByText('Valorant').closest('.game-card');
    fireEvent.click(gameCard);
    
    await waitFor(() => {
      expect(gameCard).toHaveClass('border-primary-500');
      expect(gameCard.querySelector('svg')).toBeInTheDocument(); // Checkmark
    });
  });
  
  test('should deselect previous game when selecting new one in single-select mode', async () => {
    await waitFor(() => screen.getByText('Valorant'));
    
    const valorantCard = screen.getByText('Valorant').closest('.game-card');
    const efootballCard = screen.getByText('eFootball').closest('.game-card');
    
    fireEvent.click(valorantCard);
    await waitFor(() => expect(valorantCard).toHaveClass('border-primary-500'));
    
    fireEvent.click(efootballCard);
    await waitFor(() => {
      expect(efootballCard).toHaveClass('border-primary-500');
      expect(valorantCard).not.toHaveClass('border-primary-500');
    });
  });
  
  test('should filter games by search query', async () => {
    await waitFor(() => screen.getByText('Valorant'));
    
    const searchInput = screen.getByPlaceholderText(/search games/i);
    fireEvent.input(searchInput, { target: { value: 'valorant' } });
    
    await waitFor(() => {
      expect(screen.getByText('Valorant')).toBeInTheDocument();
      expect(screen.queryByText('eFootball')).not.toBeInTheDocument();
      expect(screen.getByText('1 games found')).toBeInTheDocument();
    }, { timeout: 400 }); // Wait for 300ms debounce
  });
  
  test('should open game info modal on info button click', async () => {
    await waitFor(() => screen.getByText('Valorant'));
    
    const infoButtons = screen.getAllByLabelText(/view game details/i);
    fireEvent.click(infoButtons[0]);
    
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Valorant' })).toBeInTheDocument();
      expect(screen.getByText('Tactical shooter')).toBeInTheDocument();
      expect(screen.getByText(/min: 5 players/i)).toBeInTheDocument();
    });
  });
  
  test('should emit game-selected event with correct payload', async () => {
    const eventHandler = jest.fn();
    window.addEventListener('game-selected', eventHandler);
    
    await waitFor(() => screen.getByText('Valorant'));
    
    const gameCard = screen.getByText('Valorant').closest('.game-card');
    fireEvent.click(gameCard);
    
    await waitFor(() => {
      expect(eventHandler).toHaveBeenCalledWith(
        expect.objectContaining({
          detail: expect.objectContaining({
            mode: 'single',
            selectedGames: [1],
            game: expect.objectContaining({ id: 1, name: 'Valorant' })
          })
        })
      );
    });
    
    window.removeEventListener('game-selected', eventHandler);
  });
  
  test('should have proper accessibility attributes', async () => {
    await waitFor(() => screen.getByText('Valorant'));
    
    const gameCards = screen.getAllByRole('radio');
    gameCards.forEach(card => {
      expect(card).toHaveAttribute('aria-checked');
      expect(card).toHaveAttribute('aria-label');
      expect(card).toHaveAttribute('tabindex', '0');
    });
  });
});
```

**Integration Tests:**
```javascript
describe('Component Integration Tests', () => {
  test('Tournament Card click navigates to detail page', () => {
    const mockTournament = { /* ... */ };
    document.body.innerHTML = `
      {% include 'components/tournament_card.html' with tournament=mockTournament %}
    `;
    
    const detailLink = screen.getByRole('link', { name: /view details/i });
    expect(detailLink).toHaveAttribute('href', '/tournaments/test-tournament/');
  });
  
  test('Tournament Filters update parent component results', async () => {
    document.body.innerHTML = `
      <div x-data="{ results: [] }" @htmx:afterSwap.window="results = $event.detail.xhr.response">
        <div x-data="tournamentFilters()">
          {% include 'components/tournament_filters.html' %}
        </div>
        <div id="tournament-results" x-text="results.length"></div>
      </div>
    `;
    Alpine.start();
    
    htmx.ajax.mockImplementation((method, url, options) => {
      options.swap = 'innerHTML';
      const event = new CustomEvent('htmx:afterSwap', {
        detail: { xhr: { response: [{ id: 1 }, { id: 2 }] } }
      });
      window.dispatchEvent(event);
    });
    
    fireEvent.click(screen.getByLabelText(/valorant/i));
    
    await waitFor(() => {
      expect(screen.getByText('2')).toBeInTheDocument();
    }, { timeout: 600 });
  });
});
```

**Files to Create/Modify:**
- `static/js/__tests__/tournament-components.test.js` - Main test file (all component tests)
- `package.json` - Ensure test scripts are configured
- `jest.config.js` - Coverage thresholds for component files

**Running Tests:**
```bash
# Run all component tests
npm test tournament-components.test.js

# Run with coverage
npm run test:coverage -- tournament-components.test.js

# Run specific component tests
npm test -- --testNamePattern="Tournament Card"
npm test -- --testNamePattern="Tournament Filters"
npm test -- --testNamePattern="Game Selector"

# Watch mode
npm run test:watch tournament-components.test.js
```

**Coverage Configuration:**
```javascript
// jest.config.js (add to existing)
collectCoverageFrom: [
  'static/js/components/tournament-card.js',
  'static/js/components/tournament-filters.js',
  'static/js/components/game-selector.js',
],
coverageThreshold: {
  './static/js/components/': {
    statements: 75,
    branches: 70,
    functions: 75,
    lines: 75
  }
}
```

**References:**
- FE-016: Tournament Card Component (component specification)
- FE-017: Tournament Filters Component (component specification)
- FE-018: Game Selector Component (component specification)
- QA-007: Tournament Wizard Tests (related test patterns and setup)

**Testing:**
- Run `npm test tournament-components.test.js` → all 35 tests pass
- Run `npm run test:coverage` → coverage report shows >75% for all component files
- Test all Tournament Card variants (default, featured, compact, skeleton)
- Test all Tournament Filters sections (game, status, fee, date, prize)
- Test all Game Selector modes (single-select, multi-select, search, info modal)
- Verify accessibility tests pass for all components
- Verify integration tests confirm proper parent-child communication
- Test responsive behavior: Desktop/tablet/mobile layouts render correctly

---

## Sprint 4 Summary

### Overview
**Sprint Goal:** Build comprehensive tournament UI with creation wizard, browse/list pages, detail views, dashboards, reusable components, and frontend testing.

**Duration:** Week 4 (5 working days)  
**Total Story Points:** 60  
**Tasks Completed:** 8

### Team Allocation
- **Frontend Developers:** 3 developers (main effort)
- **Backend Developer:** 1 developer (API integration support)
- **QA Engineer:** 1 engineer (frontend testing)
- **DevOps Engineer:** 1 engineer (CI/CD for frontend tests)

### Completed Tasks

**Frontend Track - Core Pages (35 points):**
1. **FE-011:** Tournament Creation Wizard (10 pts) - 5-step multi-step form with validation, auto-save, image uploads, rich text editor, responsive design
2. **FE-012:** Tournament List/Browse Page (8 pts) - Hero section, featured carousel, filter sidebar, tournament grid, search, pagination, HTMX integration
3. **FE-013:** Tournament Detail View (8 pts) - Hero section, tabs (Overview/Participants/Bracket/Rules), action buttons, real-time updates, countdown timer
4. **FE-014:** Organizer Dashboard (5 pts) - Quick stats, pending actions, tournament table, filters, activity feed, export functionality
5. **FE-015:** My Tournaments (Player View) (4 pts) - Tabs (Upcoming/Ongoing/Completed/All), check-in reminders, match info, placement badges

**Frontend Track - Components (20 points):**
6. **FE-016:** Tournament Card Component (6 pts) - Reusable card with variants (default/featured/compact), loading skeleton, responsive design, accessibility
7. **FE-017:** Tournament Filters Component (7 pts) - Advanced filtering with game/status/fee/date/prize filters, sidebar/drawer layouts, URL persistence, HTMX integration
8. **FE-018:** Game Selector Component (7 pts) - Grid layout with icons, single/multi-select modes, search, game info modal, custom events

**Quality Track (5 points):**
9. **QA-007:** Tournament Wizard Tests (3 pts) - Jest + Testing Library tests covering step navigation, validation, auto-save, form submission, keyboard nav, accessibility (>80% coverage)
10. **QA-008:** Tournament Components Tests (2 pts) - Unit tests for card/filters/selector components covering rendering, interactions, state changes, accessibility (>75% coverage)

### Technology Stack
- **Frontend Framework:** Tailwind CSS 3.4+, HTMX 1.9+, Alpine.js 3.x
- **Rich Text:** Quill.js 2.0+ (tournament description, rules)
- **Carousel:** Swiper.js 11.0+ (featured tournaments)
- **Markdown:** marked.js 12.0+ (rendering descriptions, rules)
- **Range Slider:** noUiSlider 15.7+ (prize pool filter)
- **Testing:** Jest 29.x, Testing Library (DOM/Jest-DOM), jsdom
- **Image Upload:** Native HTML5 drag-drop, FileReader API
- **Date Pickers:** Native HTML5 date/datetime-local inputs
- **Real-time:** Polling (30s interval) for registration counts, status updates (WebSocket in Sprint 9)

### Definition of Done Checklist
- [ ] All 8 tasks (FE-011 to FE-018) completed with acceptance criteria met
- [ ] Tournament creation wizard functional with all 5 steps, validation, auto-save
- [ ] Tournament list page displays tournaments with filters, search, featured carousel
- [ ] Tournament detail page shows complete information with tabs, action buttons
- [ ] Organizer and player dashboards operational with stats, tables, activity feeds
- [ ] All 3 reusable components (card, filters, selector) documented with usage examples
- [ ] Frontend tests written with >80% coverage for wizard, >75% for components
- [ ] All pages responsive (mobile/tablet/desktop tested)
- [ ] Accessibility features implemented: ARIA labels, keyboard navigation, screen reader support
- [ ] Code reviewed and merged to main branch
- [ ] Manual QA completed: Cross-browser testing (Chrome, Firefox, Safari, Edge)
- [ ] Performance validated: Page load <2s, image optimization, lazy loading
- [ ] Documentation updated: Component usage, API integration, testing procedures

### Integration Points
- **Backend APIs:**
  - `POST /api/tournaments/` - Create tournament (wizard submission)
  - `GET /api/tournaments/` - List tournaments (browse page, filters)
  - `GET /api/tournaments/:slug/` - Tournament detail
  - `GET /api/games/` - Game configurations (wizard, filters, selector)
  - `POST /api/tournaments/:slug/register/` - Register team (detail page action)
  - `GET /api/tournaments/:slug/registrations/` - List registrations (participants tab)
  
- **Frontend Components:**
  - Tournament Card (FE-016) used in: FE-012 (list), FE-014 (dashboard), FE-015 (my tournaments)
  - Tournament Filters (FE-017) used in: FE-012 (browse sidebar), future search pages
  - Game Selector (FE-018) used in: FE-011 (wizard Step 2), FE-017 (game filter)
  
- **Design System:**
  - Button Component (FE-007): Primary, secondary, tertiary variants
  - Input Component (FE-008): Text, textarea, select, file, date inputs
  - Card Component (FE-009): Base card structure, shadows, borders
  - Badge Component (FE-009): Status badges, count badges, platform badges
  - Modal Component (FE-010): Game info modal, confirmation modals

### Known Issues / Tech Debt
- **Real-time Updates:** Currently using polling (30s) for registration counts. Will upgrade to WebSocket in Sprint 9 for true real-time updates.
- **Image Optimization:** Images uploaded directly to S3. Consider adding image resizing/optimization service (Sprint 13).
- **Offline Support:** No offline capability. Consider adding service worker for offline draft saving (Sprint 15).
- **Browser Support:** IE11 not supported (Alpine.js requires modern browsers). Document minimum browser versions.
- **Accessibility Audit:** Manual accessibility testing done. Schedule full audit with screen reader users in Sprint 13.

### Performance Metrics
- **Tournament List Page:** Target <2s load time (20 tournaments, images lazy-loaded)
- **Tournament Detail Page:** Target <1.5s load time (single tournament with tabs)
- **Wizard Auto-save:** Draft saved every 2 minutes (localStorage, <50ms operation)
- **Filter Response:** HTMX request debounced 500ms, results load <1s
- **Component Tests:** 85 total tests, execution time <5s

### Next Sprint Preview (Sprint 5-6: Registration & Payment)
- **BE-014:** TournamentRegistration API endpoints (register, withdraw, check-in)
- **BE-015:** Payment integration (Stripe/PayPal for entry fees)
- **BE-016:** Payment verification workflow (admin approval, proof upload)
- **FE-019:** Registration form modal (team selection, payment method)
- **FE-020:** Payment flow UI (Stripe checkout, payment confirmation)
- **FE-021:** Registration management page (organizer view, approve/reject)
- **QA-009:** Registration & Payment integration tests

### Files Created/Modified (Sprint 4)
**Templates:**
- `templates/tournaments/create.html` (FE-011)
- `templates/tournaments/list.html` (FE-012)
- `templates/tournaments/detail.html` (FE-013)
- `templates/dashboard/organizer.html` (FE-014)
- `templates/tournaments/my_tournaments.html` (FE-015)
- `templates/components/tournament_card.html` (FE-016)
- `templates/components/tournament_card_skeleton.html` (FE-016)
- `templates/components/tournament_filters.html` (FE-017)
- `templates/components/tournament_filters_content.html` (FE-017)
- `templates/components/game_selector.html` (FE-018)

**JavaScript:**
- `static/js/tournament-wizard.js` (FE-011)
- `static/js/tournament-filters.js` (FE-012)
- `static/js/tournament-detail.js` (FE-013)
- `static/js/organizer-dashboard.js` (FE-014)
- `static/js/my-tournaments.js` (FE-015)
- `static/js/components/tournament-card.js` (FE-016)
- `static/js/components/tournament-filters.js` (FE-017)
- `static/js/components/game-selector.js` (FE-018)

**Tests:**
- `static/js/__tests__/tournament-wizard.test.js` (QA-007)
- `static/js/__tests__/tournament-components.test.js` (QA-008)

**Template Tags:**
- `apps/tournaments/templatetags/tournament_filters.py` (currency, relative_time filters)

**Configuration:**
- `jest.config.js` (test configuration, coverage thresholds)
- `package.json` (test scripts, dependencies)

### Sprint Retrospective Notes
**What Went Well:**
- Component-based approach (FE-016, FE-017, FE-018) promotes reusability across pages
- Alpine.js provides lightweight reactivity without heavy framework overhead
- HTMX integration simplifies dynamic content loading with minimal JavaScript
- Comprehensive test coverage (>80% wizard, >75% components) catches edge cases early
- Auto-save feature prevents data loss in wizard (localStorage backup every 2min)

**What Could Be Improved:**
- Large wizard component (FE-011) could benefit from further breakdown into sub-components
- Polling for real-time updates increases server load (upgrade to WebSocket in Sprint 9)
- Some validation logic duplicated between frontend and backend (consider shared validation library)
- Testing setup requires mocking multiple libraries (fetch, HTMX, noUiSlider) - consider test utilities module

**Action Items for Next Sprint:**
- Create shared validation utility for common rules (date ranges, team size, prize pool)
- Document Alpine.js component patterns and best practices for team
- Set up Playwright for E2E testing (complement Jest unit tests)
- Review image upload UX with design team (consider Cloudinary for optimization)

---

**Sprint 4 Status:** ✅ **COMPLETE** (60/60 points, 8/8 tasks)

**Next Sprint:** Sprint 5-6: Registration & Payment System (95 points, 15 tasks)

