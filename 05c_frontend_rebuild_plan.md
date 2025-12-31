# Frontend Rebuild Plan – User Profile Aurora Zenith
**Date:** December 31, 2025  
**Role:** Frontend + Django Template Engineer  
**Type:** NO CODE Planning Document  
**Purpose:** Plan complete rebuild of user profile page aligned to Aurora Zenith design system

---

## A. FILE CHANGES PLAN

### A.1 New Primary Template

**Target File:** `templates/user_profile/profile/public_v5_aurora.html`

**Source:** `templates/My drafts/user_profile_temp_draft/user_profile.html`

**Rationale:**
- Clean slate using Aurora Zenith design system
- Self-contained with inline Tailwind config + custom CSS
- Mobile-first responsive layout
- Tab-based navigation (Overview, Highlights, Bounties, Endorsements, Loadout, Wallet, Career, Stats)

**Action:**
- Copy draft template to `public_v5_aurora.html` (NOT delete draft, keep as reference)
- Convert to Django template syntax (`{{ profile.user.username }}` instead of hardcoded "VIPER")
- Strip mock data, inject context variables from backend contract

---

### A.2 Archive Existing Templates (DO NOT DELETE)

**Current Primary:** `templates/user_profile/profile/public_v4.html` (Dragon Fire design)

**Archived To:** `templates/user_profile/profile/archive_2025_12_31/`

**Files to Archive:**
- `public_v4.html` (current profile page)
- `profile.html` (legacy profile)
- `settings_v4.html` (settings page, keep active for now)
- `privacy.html` (privacy settings, keep active)
- `activity.html` (activity feed, keep active)

**Files to Keep Active:**
- `settings_v4.html` (not replaced in this rebuild)
- `privacy.html` (privacy controls)
- `activity.html` (user activity feed)
- `followers_modal.html` / `following_modal.html` (reusable modals)

**Rationale:**
- Never delete working code during migration
- Old templates may be referenced by cached URLs or external links
- Rollback safety if Aurora Zenith causes issues

---

### A.3 Component Partials Breakdown

**New Directory:** `templates/user_profile/profile/partials_aurora/`

**Partials to Create:**

#### Hero Section
- `_hero_background.html` - Cover photo, gradient overlays, "Change Cover" button (owner only)
- `_hero_avatar.html` - Holographic ring, avatar, camera icon overlay (owner only), verified badge
- `_hero_identity.html` - Name, gamertag, level badge, bio, edit pen (owner only)
- `_hero_stats_hud.html` - Followers, Following, Teams count + social icons
- `_hero_action_dock.html` - Follow/Message/Scout buttons (public) OR Edit Profile (owner)

#### Navigation
- `_tab_navigation.html` - Sticky tabs bar with badge notifications (posts_count, bounties_count)

#### Left Sidebar
- `_sidebar_personal_info.html` - Real name, join date, location (privacy-filtered)
- `_sidebar_game_passports.html` - Linked game IDs (Valorant, CS2, PUBG) with ranks
- `_sidebar_gear_setup.html` - Hardware loadout (mouse, keyboard, headset, monitor)

#### Center Command (Tab Content)
- `_tab_overview.html` - Pinned clip + active bounty + endorsement summary
- `_tab_wallet.html` - Balance, transactions, deposit/withdraw (OWNER ONLY)
- `_tab_career.html` - Team history timeline
- `_tab_stats.html` - Combat data (K/D, Win Rate, Headshot %)
- `_tab_inventory.html` - Unlocked cosmetics (frames, banners, badges)
- `_tab_highlights.html` - Video gallery (YouTube/Twitch embeds)
- `_tab_bounties.html` - Created, accepted, completed bounty lists
- `_tab_endorsements.html` - Skill breakdown (Aim, Shotcalling, Clutch, etc.)
- `_tab_loadout.html` - Full hardware + game configs (Valorant sens, CS2 crosshair)
- `_tab_posts.html` - **PLACEHOLDER** ("Coming Soon" message, apps/community missing)

#### Right Sidebar
- `_sidebar_live_status.html` - Live tournament banner + stream embed (Twitch/YouTube)
- `_sidebar_affiliations.html` - Current teams with logos
- `_sidebar_trophy_cabinet.html` - Tournament wins

#### Shared Components
- `_bounty_card.html` - Reusable bounty display (title, stake, requirements, countdown)
- `_endorsement_skill_meter.html` - Skill name + progress bar + count
- `_highlight_video_embed.html` - Iframe sandbox with platform validation (YouTube/Twitch/Medal)
- `_cosmetic_item.html` - Frame/banner/badge with rarity glow
- `_hardware_item.html` - Product name, specs, affiliate link
- `_transaction_row.html` - Wallet transaction (amount, reason, timestamp)

**Naming Convention:**
- Prefix: `_` (indicates partial)
- Suffix: `.html`
- Naming: `_section_component_name.html` (e.g., `_hero_avatar.html`, `_tab_bounties.html`)

---

### A.4 Existing Components to Reuse

**Keep From Current System:**
- `templates/user_profile/followers_modal.html` (follower list modal)
- `templates/user_profile/following_modal.html` (following list modal)
- `templates/user_profile/components/_passport_modal.html` (game passport linking flow)

**Adapt/Restyle:**
- Re-skin modals to match Aurora Zenith glassmorphism (backdrop-blur, neon borders)
- Keep existing modal logic (Alpine.js/vanilla JS event dispatching)

---

## B. TEMPLATE ARCHITECTURE

### B.1 Main Template Structure

```
public_v5_aurora.html
├── <head>
│   ├── Meta tags
│   ├── Tailwind CDN config (Aurora color palette, animations)
│   ├── Font imports (Space Grotesk, Inter)
│   ├── Font Awesome icons
│   └── <style> block (glassmorphism, holographic effects, scrollbar)
├── <body>
│   ├── Navbar (global navigation, reusable from base.html or inline)
│   ├── HERO SECTION
│   │   ├── {% include 'user_profile/profile/partials_aurora/_hero_background.html' %}
│   │   ├── {% include 'user_profile/profile/partials_aurora/_hero_avatar.html' %}
│   │   ├── {% include 'user_profile/profile/partials_aurora/_hero_identity.html' %}
│   │   ├── {% include 'user_profile/profile/partials_aurora/_hero_stats_hud.html' %}
│   │   └── {% include 'user_profile/profile/partials_aurora/_hero_action_dock.html' %}
│   ├── TAB NAVIGATION
│   │   └── {% include 'user_profile/profile/partials_aurora/_tab_navigation.html' %}
│   ├── MAIN CONTAINER (3-column grid)
│   │   ├── LEFT SIDEBAR
│   │   │   ├── {% include 'user_profile/profile/partials_aurora/_sidebar_personal_info.html' %}
│   │   │   ├── {% include 'user_profile/profile/partials_aurora/_sidebar_game_passports.html' %}
│   │   │   └── {% include 'user_profile/profile/partials_aurora/_sidebar_gear_setup.html' %}
│   │   ├── CENTER COMMAND (tab-switched content)
│   │   │   ├── <div id="tab-overview" class="tab-content active">
│   │   │   │   └── {% include 'user_profile/profile/partials_aurora/_tab_overview.html' %}
│   │   │   ├── <div id="tab-wallet" class="tab-content hidden">
│   │   │   │   └── {% if is_owner %}{% include '.../_tab_wallet.html' %}{% endif %}
│   │   │   ├── <div id="tab-career"> ... </div>
│   │   │   ├── <div id="tab-stats"> ... </div>
│   │   │   ├── <div id="tab-inventory"> ... </div>
│   │   │   ├── <div id="tab-highlights"> ... </div>
│   │   │   ├── <div id="tab-bounties"> ... </div>
│   │   │   ├── <div id="tab-endorsements"> ... </div>
│   │   │   ├── <div id="tab-loadout"> ... </div>
│   │   │   └── <div id="tab-posts"> <!-- PLACEHOLDER --> </div>
│   │   └── RIGHT SIDEBAR
│   │       ├── {% include 'user_profile/profile/partials_aurora/_sidebar_live_status.html' %}
│   │       ├── {% include 'user_profile/profile/partials_aurora/_sidebar_affiliations.html' %}
│   │       └── {% include 'user_profile/profile/partials_aurora/_sidebar_trophy_cabinet.html' %}
│   ├── MODALS
│   │   ├── {% include 'user_profile/followers_modal.html' %} (reused)
│   │   ├── {% include 'user_profile/following_modal.html' %} (reused)
│   │   └── <!-- Future: bounty creation modal, clip upload modal, etc. -->
│   └── <script> block (tab switching logic, edit mode toggles)
```

---

### B.2 Partial Design Principles

#### Encapsulation
- Each partial responsible for ONE UI section
- Self-contained styling (no cross-partial dependencies)
- Context variables passed via parent template

#### Reusability
- `_bounty_card.html` used in Overview tab AND Bounties tab
- `_endorsement_skill_meter.html` used in Overview AND Endorsements tab
- `_highlight_video_embed.html` used for pinned clip AND highlights gallery

#### Conditional Rendering
```django
{% if profile.pinned_clip %}
    {% include 'user_profile/profile/partials_aurora/_highlight_video_embed.html' with clip=profile.pinned_clip %}
{% else %}
    <div class="z-card text-center py-12">
        <p class="text-gray-400">No pinned highlight yet.</p>
        {% if is_owner %}
            <button class="mt-4 px-4 py-2 bg-z-purple rounded-lg">Upload First Clip</button>
        {% endif %}
    </div>
{% endif %}
```

#### Privacy Filtering
```django
<!-- Wallet tab ONLY if owner -->
{% if is_owner %}
    <button class="z-tab-btn" onclick="switchTab('wallet')">
        <i class="fa-solid fa-wallet"></i> Wallet
        <span class="text-z-gold">{{ wallet.cached_balance|intcomma }}</span>
    </button>
{% endif %}
```

---

### B.3 JavaScript Architecture

**Tab Switching Logic:**
```javascript
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.add('hidden');
    });
    
    // Remove active state from all buttons
    document.querySelectorAll('.z-tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById('tab-' + tabName).classList.remove('hidden');
    
    // Mark button as active
    document.querySelector('[data-tab="' + tabName + '"]').classList.add('active');
    
    // Update URL hash (for shareable links)
    window.location.hash = tabName;
}

// On page load, check hash and switch to that tab
window.addEventListener('DOMContentLoaded', () => {
    const hash = window.location.hash.substring(1); // Remove #
    if (hash) {
        switchTab(hash);
    }
});
```

**Edit Mode Triggers:**
```javascript
// Show edit icons on hover (owner only)
// CSS handles this via .group:hover .edit-trigger { opacity: 1; }

// Edit bio inline
function editBio() {
    const bioText = document.getElementById('bio-text');
    const bioForm = document.getElementById('bio-form');
    bioText.classList.add('hidden');
    bioForm.classList.remove('hidden');
}

// Save bio via AJAX
async function saveBio() {
    const bioInput = document.getElementById('bio-input').value;
    const response = await fetch('/profile/update-bio/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ bio: bioInput })
    });
    if (response.ok) {
        location.reload(); // Refresh to show updated bio
    }
}
```

---

## C. RENDERING STRATEGY (Progressive Enhancement)

### C.1 Phase 1: Render What Exists Now

**Goal:** Page loads with basic profile data (existing models)

**Sections to Render:**
- ✅ Hero (avatar, bio, level, followers/following) - **Existing:** UserProfile, Follow system
- ✅ Navigation (tabs, no badges yet) - **Exists:** Render all tabs
- ✅ Left Sidebar (personal info, join date, location) - **Existing:** UserProfile
- ✅ Game Passports (linked IDs + ranks) - **Existing:** GamePassport
- ✅ Career Tab (team history) - **Existing:** TeamMembership
- ✅ Wallet Tab (balance, transactions) - **Existing:** DeltaCrownWallet (owner-only)
- ✅ Right Sidebar (current teams) - **Existing:** TeamMembership

**Sections to Show Placeholders:**
- ❌ Pinned Clip (Overview) - Show empty state: "Upload your first highlight"
- ❌ Bounties (Overview) - Show placeholder: "No active bounties"
- ❌ Endorsements (Overview) - Show placeholder: "Endorsements coming soon"
- ❌ Gear Setup (Left Sidebar) - Show placeholder: "Set up your loadout"
- ❌ Live Status (Right Sidebar) - Show placeholder: "Not in a tournament"
- ❌ Highlights Tab - Empty gallery
- ❌ Bounties Tab - "Feature launching soon"
- ❌ Endorsements Tab - "Feature launching soon"
- ❌ Loadout Tab - "Feature launching soon"
- ❌ Inventory Tab - "Showcase system coming soon"
- ❌ Posts Tab - "Community feed in development"

**Placeholder Template Example:**
```django
<!-- _tab_bounties.html -->
{% if bounties_exist %}
    <!-- Render bounty list -->
    {% for bounty in user_bounties.created %}
        {% include 'user_profile/profile/partials_aurora/_bounty_card.html' with bounty=bounty %}
    {% endfor %}
{% else %}
    <div class="z-card text-center py-16">
        <i class="fa-solid fa-trophy text-6xl text-z-purple mb-4 opacity-20"></i>
        <h3 class="text-xl font-bold text-white mb-2">Bounty System Launching Soon</h3>
        <p class="text-gray-400 mb-4">Challenge rivals, set stakes, prove your skill.</p>
        {% if is_owner %}
            <button class="px-6 py-2 bg-z-purple/20 text-z-purple border border-z-purple/30 rounded-lg cursor-not-allowed">
                Coming in Phase 2
            </button>
        {% endif %}
    </div>
{% endif %}
```

---

### C.2 Phase 2: Add New Features (Progressive Rollout)

**Milestone 1: Highlights System**
- Backend: Create `HighlightClip` model, URL validation service
- Frontend: Show video embeds in Overview + Highlights tab
- Partials: `_highlight_video_embed.html` (iframe sandbox, CSP)
- Safety: Whitelist YouTube/Twitch/Medal domains, sandbox attributes

**Milestone 2: Bounties**
- Backend: Create `Bounty`, `BountyAcceptance` models, escrow services
- Frontend: Render bounty cards in Overview + Bounties tab
- Partials: `_bounty_card.html`, `_tab_bounties.html`
- Safety: Never show wallet balance to non-owners

**Milestone 3: Endorsements**
- Backend: Create `SkillEndorsement` model, post-match triggers
- Frontend: Skill meter in Overview + detailed breakdown in Endorsements tab
- Partials: `_endorsement_skill_meter.html`, `_tab_endorsements.html`
- Safety: Anonymous endorsers (don't expose who endorsed whom publicly)

**Milestone 4: Loadout + Showcase**
- Backend: Create `HardwareProduct`, `UserHardware`, `ProfileFrame`, `ProfileBanner` models
- Frontend: Gear list in Left Sidebar, full loadout in Loadout tab, cosmetics in Inventory tab
- Partials: `_sidebar_gear_setup.html`, `_tab_loadout.html`, `_tab_inventory.html`, `_cosmetic_item.html`
- Safety: Validate affiliate URLs (prevent open redirect), re-encode images (prevent XSS)

---

### C.3 Graceful Degradation (Avoid Breaking)

**Strategy:** Check if context variable exists before rendering

**Example Pattern:**
```django
<!-- _tab_overview.html -->
<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    
    <!-- Pinned Clip Section -->
    <div class="z-card p-6">
        <h3 class="text-xl font-bold text-white mb-4">Pinned Highlight</h3>
        {% if profile.pinned_clip %}
            {% include 'user_profile/profile/partials_aurora/_highlight_video_embed.html' with clip=profile.pinned_clip %}
        {% else %}
            <div class="aspect-video bg-black/30 rounded-lg flex items-center justify-center">
                <div class="text-center">
                    <i class="fa-solid fa-video text-4xl text-gray-600 mb-2"></i>
                    <p class="text-gray-500">No pinned clip yet</p>
                </div>
            </div>
        {% endif %}
    </div>
    
    <!-- Active Bounty Section -->
    <div class="z-card p-6">
        <h3 class="text-xl font-bold text-white mb-4">Active Bounty</h3>
        {% if active_bounty %}
            {% include 'user_profile/profile/partials_aurora/_bounty_card.html' with bounty=active_bounty %}
        {% elif 'Bounty' in dir(apps.get_model) %}  <!-- Check if Bounty model exists -->
            <p class="text-gray-400">No active bounties</p>
            {% if is_owner %}
                <button class="mt-4 px-4 py-2 bg-z-purple rounded-lg">Create Bounty</button>
            {% endif %}
        {% else %}
            <!-- Model doesn't exist yet, show placeholder -->
            <div class="text-center py-8">
                <i class="fa-solid fa-trophy text-3xl text-gray-700 mb-2"></i>
                <p class="text-gray-500 text-sm">Bounty system launching soon</p>
            </div>
        {% endif %}
    </div>
    
</div>
```

**Backend Preparation:**
```python
# apps/user_profile/views/fe_v2.py

def profile_view_v5(request, username):
    profile = get_object_or_404(UserProfile, user__username=username)
    is_owner = request.user == profile.user
    
    context = {
        'profile': profile,
        'is_owner': is_owner,
        'view_mode': 'owner' if is_owner else 'public',
        # ... existing data ...
    }
    
    # Progressive: Only query if model exists
    try:
        from apps.economy.models import Bounty
        context['active_bounty'] = Bounty.objects.filter(creator=profile.user, status='OPEN').first()
    except ImportError:
        context['active_bounty'] = None  # Model doesn't exist yet
    
    try:
        from apps.user_profile.models import HighlightClip
        context['highlight_clips'] = HighlightClip.objects.filter(user=profile.user).order_by('position')[:20]
    except ImportError:
        context['highlight_clips'] = []
    
    return render(request, 'user_profile/profile/public_v5_aurora.html', context)
```

---

## D. UI SAFETY RULES

### D.1 Wallet Content Security

**Rule:** Wallet balance, transactions, deposit/withdraw NEVER rendered unless `is_owner=True`

**Implementation:**
```django
<!-- _tab_wallet.html -->
{% if not is_owner %}
    <div class="z-card text-center py-16">
        <i class="fa-solid fa-lock text-6xl text-gray-700 mb-4"></i>
        <h3 class="text-xl font-bold text-white mb-2">Wallet is Private</h3>
        <p class="text-gray-400">Only the profile owner can view wallet details.</p>
    </div>
{% else %}
    <!-- Render wallet content -->
    <div class="z-card p-6">
        <div class="flex items-center justify-between mb-6">
            <h3 class="text-2xl font-bold text-white">DeltaCrown Wallet</h3>
            <div class="text-right">
                <p class="text-xs text-gray-400 uppercase">Balance</p>
                <p class="text-3xl font-bold text-gradient-gold">{{ wallet.cached_balance|intcomma }}</p>
                <p class="text-xs text-gray-500">≈ {{ wallet.cached_balance|multiply:bdt_conversion_rate|intcomma }} BDT</p>
            </div>
        </div>
        <!-- Transaction ledger -->
        {% for tx in wallet_transactions %}
            {% include 'user_profile/profile/partials_aurora/_transaction_row.html' with transaction=tx %}
        {% endfor %}
    </div>
{% endif %}
```

**Tab Navigation Visibility:**
```django
<!-- _tab_navigation.html -->
{% if is_owner %}
    <button class="z-tab-btn" data-tab="wallet" onclick="switchTab('wallet')">
        <i class="fa-solid fa-wallet"></i> Wallet
        <span class="text-z-gold ml-2">{{ wallet.cached_balance|intcomma }}</span>
    </button>
{% endif %}
```

---

### D.2 Video/Stream Embed Safety

**Rule:** All video embeds MUST use sanitized `embed_url` + iframe sandbox attributes + CSP

**Implementation:**
```django
<!-- _highlight_video_embed.html -->
{% if clip.platform == 'youtube' %}
    <iframe 
        src="https://www.youtube.com/embed/{{ clip.video_id }}" 
        class="w-full aspect-video rounded-lg"
        sandbox="allow-scripts allow-same-origin"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowfullscreen
        loading="lazy"
        title="{{ clip.title|escape }}"
    ></iframe>
{% elif clip.platform == 'twitch' %}
    <iframe 
        src="https://clips.twitch.tv/embed?clip={{ clip.video_id }}&parent=deltacrown.com" 
        class="w-full aspect-video rounded-lg"
        sandbox="allow-scripts allow-same-origin"
        allowfullscreen
        loading="lazy"
        title="{{ clip.title|escape }}"
    ></iframe>
{% elif clip.platform == 'medal' %}
    <iframe 
        src="https://medal.tv/clip/{{ clip.video_id }}?embed=true" 
        class="w-full aspect-video rounded-lg"
        sandbox="allow-scripts allow-same-origin"
        allowfullscreen
        loading="lazy"
        title="{{ clip.title|escape }}"
    ></iframe>
{% else %}
    <div class="aspect-video bg-red-900/20 rounded-lg flex items-center justify-center">
        <p class="text-red-400">Unsupported video platform</p>
    </div>
{% endif %}
```

**CSP Header (Django Settings):**
```python
# settings.py
CSP_FRAME_SRC = [
    'https://www.youtube.com',
    'https://clips.twitch.tv',
    'https://medal.tv',
]
```

**Backend Validation:**
```python
# apps/user_profile/services/highlight_validator.py

ALLOWED_DOMAINS = {
    'youtube': ['youtube.com', 'youtu.be'],
    'twitch': ['clips.twitch.tv'],
    'medal': ['medal.tv'],
}

def validate_highlight_url(url):
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Check whitelist
    for platform, allowed_domains in ALLOWED_DOMAINS.items():
        if any(domain.endswith(d) for d in allowed_domains):
            return {
                'valid': True,
                'platform': platform,
                'video_id': extract_video_id(url, platform),
            }
    
    return {'valid': False, 'error': 'Unsupported domain'}
```

---

### D.3 XSS Prevention

**Rule:** All user-generated text MUST be escaped (Django autoescapes by default)

**Django Template Escaping:**
```django
<!-- SAFE: Django autoescape enabled -->
<h2 class="text-2xl font-bold">{{ profile.user.username }}</h2>
<p class="text-gray-400">{{ profile.bio }}</p>

<!-- UNSAFE: Manual HTML (NEVER do this) -->
<div>{{ profile.bio|safe }}</div>  <!-- ❌ DON'T USE |safe unless you control the content -->
```

**URL Escaping:**
```django
<!-- Social links (user-provided URLs) -->
{% for link in social_links %}
    <a href="{{ link.url|urlencode }}" target="_blank" rel="noopener noreferrer">
        <i class="fa-brands fa-{{ link.platform }}"></i>
    </a>
{% endfor %}
```

**Image URLs (Affiliate Links):**
```django
<!-- Hardware affiliate links -->
<a href="{{ product.affiliate_url|urlencode }}" 
   target="_blank" 
   rel="noopener noreferrer nofollow"  <!-- Prevent SEO manipulation -->
   class="text-z-cyan hover:underline">
    Buy on Store
</a>
```

---

### D.4 Privacy Cascading

**Rule:** Respect `view_mode` for all sensitive data

**Personal Info Filtering:**
```django
<!-- _sidebar_personal_info.html -->
<div class="z-card p-6">
    <h3 class="text-lg font-bold text-white mb-4">Personal Info</h3>
    
    <!-- Real Name (owner/friend only) -->
    {% if view_mode in 'owner,friend' and profile.real_name %}
        <div class="mb-3">
            <p class="text-xs text-gray-500 uppercase">Real Name</p>
            <p class="text-white font-semibold">{{ profile.real_name }}</p>
        </div>
    {% endif %}
    
    <!-- Location (owner/friend only) -->
    {% if view_mode in 'owner,friend' and profile.location %}
        <div class="mb-3">
            <p class="text-xs text-gray-500 uppercase">Location</p>
            <p class="text-white font-semibold">{{ profile.location }}</p>
        </div>
    {% endif %}
    
    <!-- Nationality (public) -->
    {% if profile.nationality %}
        <div class="mb-3">
            <p class="text-xs text-gray-500 uppercase">Nationality</p>
            <p class="text-white font-semibold">{{ profile.nationality }}</p>
        </div>
    {% endif %}
    
    <!-- Join Date (public) -->
    <div class="mb-3">
        <p class="text-xs text-gray-500 uppercase">Member Since</p>
        <p class="text-white font-semibold">{{ profile.joined_at|date:"F Y" }}</p>
    </div>
</div>
```

**Backend View Mode Logic:**
```python
def determine_view_mode(request, profile):
    if request.user == profile.user:
        return 'owner'
    elif request.user in profile.friends.all():  # If friend system exists
        return 'friend'
    else:
        return 'public'
```

---

### D.5 CSRF Protection

**Rule:** All POST requests (bio edit, bounty create, clip upload) MUST include CSRF token

**Form Example:**
```django
<!-- Edit bio form -->
<form method="POST" action="{% url 'profile:update-bio' %}" class="mt-4">
    {% csrf_token %}
    <textarea name="bio" class="w-full bg-black/30 border border-white/10 rounded-lg p-3 text-white" rows="4">{{ profile.bio }}</textarea>
    <button type="submit" class="mt-2 px-4 py-2 bg-z-cyan text-black rounded-lg font-bold">Save</button>
</form>
```

**AJAX Example:**
```javascript
async function updateBio() {
    const bioText = document.getElementById('bio-input').value;
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    const response = await fetch('/profile/update-bio/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify({ bio: bioText })
    });
    
    if (response.ok) {
        location.reload();
    }
}
```

---

## E. MILESTONES

### MILESTONE 1: Page Loads with Hero + Basic Tabs
**Target Date:** Week 1 (Jan 2-8, 2026)

**Goal:** Replace `public_v4.html` with `public_v5_aurora.html` as primary profile page

**Tasks:**
1. Copy `user_profile.html` draft to `templates/user_profile/profile/public_v5_aurora.html`
2. Convert all hardcoded mock data to Django template variables
3. Create `partials_aurora/` directory
4. Extract Hero components into partials (_hero_background, _hero_avatar, _hero_identity, _hero_stats_hud, _hero_action_dock)
5. Extract tab navigation into `_tab_navigation.html`
6. Render existing tabs with real data (Career, Wallet)
7. Add placeholders for non-existent features (Bounties, Highlights, Endorsements, Loadout, Inventory)
8. Update `apps/user_profile/views/fe_v2.py` to render new template
9. Update URL routing to point to new view
10. Archive `public_v4.html` to `archive_2025_12_31/`

**Success Criteria:**
- ✅ Profile page loads without errors
- ✅ Hero section displays avatar, bio, followers/following
- ✅ Tabs are clickable and switch content
- ✅ Career tab shows team history
- ✅ Wallet tab shows balance (owner only)
- ✅ Non-existent features show "Coming Soon" placeholders

**Rollback Plan:**
- Keep `public_v4.html` active via URL toggle: `/@username/?v=4` loads old version
- Nginx A/B testing: 50% traffic to v5, 50% to v4 for first 48 hours

---

### MILESTONE 2: Adds Highlights Embed
**Target Date:** Week 2-3 (Jan 9-22, 2026)

**Goal:** Render video embeds in Overview tab + Highlights tab

**Backend Tasks:**
1. Create `HighlightClip` model (video_id, platform, title, thumbnail_url, embed_url, position)
2. Add `UserProfile.pinned_clip` ForeignKey
3. Create URL validation service (whitelist YouTube/Twitch/Medal)
4. Create admin interface for `HighlightClip`
5. Add upload form view (owner only)

**Frontend Tasks:**
1. Create `_highlight_video_embed.html` partial (iframe sandbox, platform detection)
2. Update `_tab_overview.html` to render pinned clip
3. Create `_tab_highlights.html` (grid gallery, add/reorder/pin controls)
4. Add "Pin Clip" button to highlight cards (owner only)
5. Style empty state ("Upload your first clip")

**Success Criteria:**
- ✅ Owner can upload YouTube/Twitch/Medal.tv URLs
- ✅ Video embeds render in Overview tab (pinned clip)
- ✅ Highlights tab shows gallery of all clips
- ✅ Iframe sandbox attributes present (CSP enforced)
- ✅ Invalid URLs rejected (domain whitelist)

**Security Checklist:**
- ✅ URL validation (HTTPS only, whitelisted domains)
- ✅ Iframe sandbox attributes (`allow-scripts allow-same-origin` only)
- ✅ CSP frame-src directive (YouTube/Twitch/Medal only)
- ✅ Twitch parent parameter hardcoded (`parent=deltacrown.com`)
- ✅ Title/description XSS escaped

---

### MILESTONE 3: Adds Bounties + Endorsements
**Target Date:** Week 4-7 (Jan 23 - Feb 19, 2026)

**Goal:** Render bounty cards + endorsement skill meters

**Backend Tasks (Bounties):**
1. Create `Bounty`, `BountyAcceptance`, `BountyProof`, `BountyDispute` models
2. Create escrow services (lock funds in pending_balance)
3. Create bounty lifecycle services (create, accept, submit, complete, expire, dispute)
4. Add Celery task for auto-expiry (runs every 15 min)
5. Create bounty admin interface

**Backend Tasks (Endorsements):**
1. Create `SkillEndorsement`, `EndorsementOpportunity` models
2. Create post-match signal listener (create opportunities 24h window)
3. Create endorsement aggregation service (skill breakdown)
4. Add endorsement form view (teammates only, post-match)

**Frontend Tasks (Bounties):**
1. Create `_bounty_card.html` partial (title, stake, requirements, countdown, accept button)
2. Update `_tab_overview.html` to show active bounty
3. Create `_tab_bounties.html` (created, accepted, completed lists)
4. Add "Create Bounty" form modal (owner only)
5. Add "Accept Bounty" button (public)

**Frontend Tasks (Endorsements):**
1. Create `_endorsement_skill_meter.html` partial (skill name, progress bar, count)
2. Update `_tab_overview.html` to show top 3 skills
3. Create `_tab_endorsements.html` (full skill breakdown, recent matches)
4. Add endorsement form (post-match modal)

**Success Criteria:**
- ✅ Owner can create bounty (stake locked in escrow)
- ✅ Public can accept bounty
- ✅ Bounty card displays in Overview tab
- ✅ Bounties tab shows created/accepted/completed lists
- ✅ Teammates can endorse post-match
- ✅ Overview tab shows top 3 endorsed skills
- ✅ Endorsements tab shows full skill breakdown

**Security Checklist (Bounties):**
- ✅ Escrow locking (SELECT FOR UPDATE, idempotency keys)
- ✅ Expiry race condition handled (status check before refund)
- ✅ Platform fee calculation (5%, stored in settings)
- ✅ Dispute window (24 hours post-completion)

**Security Checklist (Endorsements):**
- ✅ Post-match only (opportunitywindow 24h)
- ✅ Unique constraint (match_id, endorser, receiver)
- ✅ Captain verification (Match.participant check)
- ✅ Anonymous display (don't expose endorser publicly)

---

### MILESTONE 4: Adds Loadout + Showcase
**Target Date:** Week 8-11 (Feb 20 - Mar 19, 2026)

**Goal:** Render hardware loadout + unlocked cosmetics

**Backend Tasks (Loadout):**
1. Create `HardwareProduct` model (200+ catalog, scraped or manual)
2. Create `UserHardware` model (5 categories: MOUSE, KEYBOARD, HEADSET, MONITOR, MOUSEPAD)
3. Create `GameConfig` model (JSON settings per game)
4. Create hardware selection form (owner only)
5. Create game config editor (owner only)

**Backend Tasks (Showcase):**
1. Create `ProfileFrame`, `ProfileBanner` models (cosmetics catalog)
2. Create `UnlockedCosmetic` model (user inventory)
3. Add `UserProfile.equipped_frame`, `UserProfile.equipped_banner` FKs
4. Create unlock service (badge achievement triggers)
5. Create equip/unequip endpoints

**Frontend Tasks (Loadout):**
1. Create `_hardware_item.html` partial (product name, specs, affiliate link)
2. Update `_sidebar_gear_setup.html` to show hardware list
3. Create `_tab_loadout.html` (full hardware + game configs)
4. Add hardware selection dropdown (owner only)
5. Add game config editor (sensitivity, DPI, crosshair)

**Frontend Tasks (Showcase):**
1. Create `_cosmetic_item.html` partial (frame/banner/badge, rarity glow)
2. Update Hero avatar to display equipped frame (holographic ring overlay)
3. Update Hero background to use equipped banner
4. Create `_tab_inventory.html` (unlocked cosmetics grid, equip/unequip buttons)
5. Add rarity colors (COMMON gray, RARE blue, EPIC purple, LEGENDARY gold)

**Success Criteria:**
- ✅ Owner can select hardware from catalog
- ✅ Left sidebar shows gear setup (mouse, keyboard, etc.)
- ✅ Loadout tab shows full hardware + game configs
- ✅ Public can click affiliate links (opens in new tab)
- ✅ Equipped frame displays on avatar
- ✅ Equipped banner displays on hero background
- ✅ Inventory tab shows unlocked cosmetics (owner sees all, public sees equipped only)

**Security Checklist (Loadout):**
- ✅ Affiliate URL validation (prevent open redirect)
- ✅ Game config JSON sanitization (no script injection)
- ✅ Rate limits (10 updates/hour)

**Security Checklist (Showcase):**
- ✅ Server-side unlock validation (can't equip without badge)
- ✅ Image re-encoding (prevent XSS via SVG)
- ✅ CSP headers (img-src whitelist)

---

## F. DEPLOYMENT CHECKLIST

### Pre-Launch
- [ ] Archive `public_v4.html` to `archive_2025_12_31/`
- [ ] Copy `user_profile.html` draft to `public_v5_aurora.html`
- [ ] Convert all mock data to Django variables
- [ ] Create `partials_aurora/` directory with 25+ partials
- [ ] Update `apps/user_profile/views/fe_v2.py` to render new template
- [ ] Add URL routing: `path('@<username>/', profile_view_v5, name='profile-v5')`
- [ ] Test responsive layout (mobile, tablet, desktop)
- [ ] Test tab switching (JavaScript logic)
- [ ] Test wallet privacy (owner-only rendering)
- [ ] Test video embeds (iframe sandbox, CSP)
- [ ] Test XSS escape (bio, username, social links)
- [ ] Test CSRF protection (all forms)

### Post-Launch Monitoring
- [ ] Check error logs for template rendering failures
- [ ] Monitor page load times (target < 1.5s)
- [ ] Verify CSP violations (none should occur)
- [ ] Track user engagement (tab switches, video plays)
- [ ] A/B test vs. `public_v4.html` (bounce rate, session duration)
- [ ] Collect user feedback (Discord, feedback form)

### Rollback Triggers
- [ ] Template rendering errors > 5%
- [ ] Page load time > 3s
- [ ] Bounce rate increase > 20%
- [ ] CSP violations detected
- [ ] User complaints > 10 in first 24h

**Rollback Command:**
```python
# Temporarily revert to public_v4.html
# apps/user_profile/views/fe_v2.py
def profile_view(request, username):
    # ... existing logic ...
    return render(request, 'user_profile/profile/public_v4.html', context)  # Fallback
```

---

## G. MIGRATION NOTES

### Template File Mapping

| Old Template | New Template | Status |
|--------------|--------------|--------|
| `public_v4.html` | `public_v5_aurora.html` | **REPLACE** (archive old) |
| `components/_identity_card.html` | `partials_aurora/_sidebar_personal_info.html` | **REDESIGN** |
| `components/_game_passport.html` | `partials_aurora/_sidebar_game_passports.html` | **REDESIGN** |
| `components/_wallet_card.html` | `partials_aurora/_tab_wallet.html` | **REDESIGN** |
| `components/_team_card.html` | `partials_aurora/_tab_career.html` | **REDESIGN** |
| `followers_modal.html` | **KEEP AS IS** (reusable) | **RESTYLE** (Aurora theme) |
| `following_modal.html` | **KEEP AS IS** (reusable) | **RESTYLE** (Aurora theme) |

### Context Variable Changes

| Old Context Key | New Context Key | Notes |
|-----------------|-----------------|-------|
| `profile_user` | `profile.user` | Nested access |
| `is_own_profile` | `is_owner` | Renamed for clarity |
| `social_media_links` | `social_links` | Shortened |
| N/A | `view_mode` | **NEW** (privacy levels) |
| N/A | `tab_badges` | **NEW** (notification counts) |
| N/A | `active_bounty` | **NEW** (Phase 2) |
| N/A | `endorsement_summary` | **NEW** (Phase 3) |
| N/A | `highlight_clips` | **NEW** (Phase 2) |

### CSS Framework Change

| Old Stack | New Stack | Migration Notes |
|-----------|-----------|----------------|
| Custom CSS (`design-tokens.css`) | Tailwind CDN + inline config | **Inline Tailwind config** (Aurora palette, animations) in `<head>` |
| Dragon Fire theme (blues/purples) | Aurora Zenith theme (cyan/purple/gold) | **Color palette shift** (update all color classes) |
| `glass-panel` class | `z-card` class | **Rename** glassmorphism panels |
| Font Awesome 5.x | Font Awesome 6.x | **Upgrade** icon classes |

---

## H. POSTS TAB PLACEHOLDER (Community App Missing)

**Problem:** `apps/community/` does not exist, so Posts tab cannot render user-generated content

**Solution:** Show "Coming Soon" placeholder

**Implementation:**
```django
<!-- _tab_posts.html -->
<div class="z-card text-center py-20">
    <i class="fa-solid fa-rocket text-7xl text-z-purple mb-6 opacity-20"></i>
    <h3 class="text-2xl font-bold text-white mb-3">Community Feed Coming Soon</h3>
    <p class="text-gray-400 max-w-md mx-auto mb-6">
        Share highlights, host discussions, and connect with teammates. 
        We're building a vibrant community space.
    </p>
    <div class="flex items-center justify-center gap-3">
        <span class="px-4 py-2 bg-z-purple/20 text-z-purple border border-z-purple/30 rounded-lg text-sm font-semibold">
            Launching in Phase 3
        </span>
    </div>
</div>
```

**Alternative (if Posts tab hidden):**
```django
<!-- _tab_navigation.html -->
{% comment %}
<button class="z-tab-btn" data-tab="posts" onclick="switchTab('posts')">
    <i class="fa-solid fa-newspaper"></i> Posts
    {% if tab_badges.posts_count > 0 %}
        <span class="badge">{{ tab_badges.posts_count }}</span>
    {% endif %}
</button>
{% endcomment %}
<!-- Posts tab hidden until apps/community implemented -->
```

**Recommendation:** **Option 1** (Hide Posts tab) until `apps/community/` exists. Show in Phase 3 only.

---

**END OF REBUILD PLAN**

**Status:** ✅ Ready for Implementation  
**Next Steps:**
1. Execute Milestone 1 (Week 1: Page loads with hero + basic tabs)
2. Test with existing data (UserProfile, TeamMembership, DeltaCrownWallet)
3. Add placeholders for Phase 2/3 features (Bounties, Highlights, Endorsements, Loadout, Inventory, Posts)
4. Monitor errors, page load times, user feedback
5. Rollout Phase 2 (Highlights) after M1 stabilizes
