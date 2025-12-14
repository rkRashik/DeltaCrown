# DeltaCrown Homepage Rebuild Blueprint

**Created:** December 14, 2025  
**Purpose:** Step-by-step plan to rebuild homepage into a modern 2025 esports landing page

---

## Current State Inventory

### Homepage Routing
- **Current View:** `apps/siteui/views.py::home()` (Line 15)
- **URL:** `apps/siteui/urls.py` → `path("", home, name="homepage")`
- **Active Template:** `templates/home_cyberpunk.html` (368 lines)
- **Alternative Templates:** `templates/home_modern.html` (714 lines, unused)

### Assets & Dependencies
**CSS Files:**
- `static/css/homepage-cyberpunk.css` (active)
- `static/css/homepage-improvements.css` (active)
- `static/css/game-cards-premium.css` (active)
- `static/css/game-cards-v3.css` (active)
- `static/css/homepage-modern.css` (unused)
- `static/css/homepage-premium.css` (unused)

**JavaScript:**
- `static/js/homepage-cyberpunk.js` (particle canvas, counters, animations)

**Fonts:**
- Rajdhani (400, 500, 600, 700)
- Space Mono (400, 700)

**Hero Background:**
- Cyberpunk particle canvas (`#particle-canvas`)
- Multi-layer overlay system (hero-overlay, hero-grid)
- **MUST PRESERVE AND REUSE**

### Current Content Structure
1. **Hero Section:** Badge, title ("DOMINATE THE ARENA"), description, 2 CTAs, 4 live stats
2. **Games Section:** 6 game cards (hardcoded in view)
3. **Features Section:** "Why DeltaCrown?" (templated from `homepage.features`)
4. **Footer:** (inherited from base.html)

### Current Data Flow
```python
# apps/siteui/views.py::home()
context = {
    "featured_tournament": None,  # Legacy system disabled
    "community_stats": {
        "players": compute_stats().get("players", 0),
        "prizes_bdt": compute_stats().get("prize_bdt", 0),
        "payout_accuracy": 98
    },
    "spotlight": get_spotlight(3),
    "timeline": get_timeline(6),
    "games_strip": [...]  # Hardcoded 6 games
}
```

---

## Platform Story & Messaging (from README.md + EXECUTIVE_SUMMARY.md)

### Core Vision
> "From the Delta to the Crown — Where Champions Rise"

### Mission
Transform esports from a scattered hobby into a respected profession through:
- Unified competition infrastructure
- Long-term player/team identity
- Economic participation (DeltaCoin)
- Career progression pathways

### Key Differentiators
1. **Complete Ecosystem** (not fragmented tools)
2. **Local Payment Support** (bKash, Nagad, Rocket, Bank)
3. **11 Supported Games** (mobile + PC)
4. **Professional Structure** (teams, coaches, sponsors)
5. **Digital Economy** (DeltaCoin rewards system)
6. **Emerging Markets Focus** (Bangladesh-first, global vision)

### Ecosystem Pillars (EXECUTIVE_SUMMARY.md Section 5)
1. **Tournaments** — Competitive engine
2. **Teams** — Professional organizations
3. **Players** — Career progression
4. **Economy** — DeltaCoin + payments
5. **Community** — Content + engagement
6. **Analytics** — Rankings + performance
7. **Coaching** — Talent development
8. **Commerce** — Merchandise + sponsorships

---

## Proposed Homepage Architecture

### Phase 1: Content Foundation (Admin-Editable Layout)
Build new template with editable content system, reuse existing hero background

### Phase 2: Dynamic Data Wiring (Future)
Connect tournaments/teams/games from database dynamically

---

## Section-by-Section Blueprint

### 1. HERO SECTION
**Purpose:** Immediate impact, clear value proposition, drive CTAs

**Visual:**
- **PRESERVE:** Cyberpunk particle canvas background
- **PRESERVE:** Multi-layer overlay system (hero-overlay, hero-grid)
- **UPDATE:** Hero content structure for 2025

**Content (Admin-Editable):**
```
hero_badge_text: "Bangladesh's #1 Esports Platform" (or custom)
hero_title: "From the Delta to the Crown"
hero_subtitle: "Where Champions Rise"
hero_description: "Building a world where geography does not define destiny—where a gamer in Bangladesh has the same trusted path to global glory as a pro on the main stage."

primary_cta_text: "Join Tournament"
primary_cta_url: "/tournaments/"
primary_cta_icon: "🏆"

secondary_cta_text: "Explore Teams"
secondary_cta_url: "/teams/"
secondary_cta_icon: "👥"

hero_highlights: [
    {"label": "Active Players", "value": "12,500+", "icon": "👥", "source": "DB_COUNT"},
    {"label": "Prize Pool", "value": "৳5,00,000+", "icon": "💰", "source": "STATIC"},
    {"label": "Tournaments", "value": "150+", "icon": "🏆", "source": "DB_COUNT"},
    {"label": "Games Supported", "value": "11", "icon": "🎮", "source": "STATIC"}
]
```

**Data Needs:**
- `User.objects.count()` → "Active Players"
- `Tournament.objects.count()` → "Tournaments"
- Static values for prize pool (until payment tracking implemented)

**Implementation:** Admin-editable via `HomePageContent` model

---

### 2. PROBLEM/OPPORTUNITY SECTION
**Purpose:** Position the platform, explain "why DeltaCrown exists"

**Content (Admin-Editable):**
```
section_title: "The Esports Gap"
section_subtitle: "Most platforms solve one problem. DeltaCrown solves the entire esports lifecycle."

comparison_table: [
    {"traditional": "One-time tournaments", "deltacrown": "Persistent competitive history"},
    {"traditional": "Temporary teams", "deltacrown": "Professional organizations"},
    {"traditional": "No career progression", "deltacrown": "Player & team legacy"},
    {"traditional": "Fragmented tools", "deltacrown": "Unified ecosystem"},
    {"traditional": "No local payment support", "deltacrown": "Global + local payments"}
]
```

**Visual:** 
- Glass card with gradient border
- Side-by-side comparison table (responsive stacking on mobile)
- Subtle animation on scroll

**Implementation:** Admin-editable via JSON field

---

### 3. ECOSYSTEM PILLARS SECTION
**Purpose:** Explain the 8 interconnected domains

**Content (Admin-Editable):**
```
section_title: "Complete Esports Ecosystem"
section_description: "Eight interconnected domains, one unified platform"

pillars: [
    {
        "icon": "🏆",
        "title": "Tournaments",
        "description": "Smart registration, automated brackets, verified results",
        "link": "/tournaments/"
    },
    {
        "icon": "👥",
        "title": "Teams",
        "description": "Professional structures with coaches, managers, sponsors",
        "link": "/teams/"
    },
    {
        "icon": "🎯",
        "title": "Players",
        "description": "Career progression, stats tracking, achievement system",
        "link": "/players/"
    },
    {
        "icon": "💰",
        "title": "Economy",
        "description": "DeltaCoin rewards, local payments, prize distribution",
        "link": "/economy/"
    },
    {
        "icon": "🌐",
        "title": "Community",
        "description": "Content, highlights, strategy guides, esports news",
        "link": "/community/"
    },
    {
        "icon": "📊",
        "title": "Rankings",
        "description": "Real-time leaderboards, performance analytics",
        "link": "/leaderboards/"
    },
    {
        "icon": "🧠",
        "title": "Coaching",
        "description": "Mentorship, training systems, skill development",
        "link": "/coaching/"
    },
    {
        "icon": "🛒",
        "title": "Commerce",
        "description": "Team merch, gaming gear, digital products",
        "link": "/shop/"
    }
]
```

**Visual:**
- 4x2 grid (desktop), 2x4 (tablet), 1x8 (mobile)
- Glass cards with icon, title, short description
- Hover effects with glow
- Optional: SVG diagram showing interconnections

**Implementation:** Admin-editable JSON field

---

### 4. GAMES SECTION
**Purpose:** Showcase 11 supported games, demonstrate multi-title capability

**Content (Phase 1: Static/Admin; Phase 2: Dynamic from Game model):**
```
section_title: "11 Games, One Platform"
section_description: "From mobile to PC, tactical shooters to sports—game-agnostic by design"

games: [
    {
        "slug": "call-of-duty-mobile",
        "name": "Call of Duty®: Mobile",
        "tagline": "Tactical FPS",
        "platforms": ["Mobile"],
        "color": "#FF6B00",
        "logo": "img/game_cards/cod_mobile.jpg",
        "banner": "img/game_cards/cod_mobile_banner.jpg"
    },
    // ... 10 more games
]
```

**Data Needs:**
- **Phase 1:** Hardcoded or admin JSON
- **Phase 2:** Query `Game.objects.filter(is_active=True)` from `apps/games/models/game.py`

**Visual:**
- Horizontal scrollable carousel (desktop)
- 2-column grid (mobile)
- Game cards with logo overlay on banner image
- Platform badges (PC, Mobile, Console)

**Implementation:** Admin JSON initially, migrate to Game FK list in Phase 2

---

### 5. FEATURED TOURNAMENTS SECTION (Dynamic)
**Purpose:** Show live/upcoming tournaments, drive registrations

**Content:**
```
section_title: "Active Tournaments"
section_description: "Join verified competitions with real prizes"

# Dynamic query:
tournaments = Tournament.objects.filter(
    status__in=['REGISTRATION', 'ONGOING']
).order_by('-prize_pool_bdt')[:3]
```

**Data Needs:**
- Tournament.name, prize_pool_bdt, start_date, game, registration_deadline
- Team/player count (if available)

**Visual:**
- 3-card horizontal layout (desktop)
- Stacked cards (mobile)
- Live badges for ongoing tournaments
- "Registration Open" badges for upcoming
- CTA: "View All Tournaments"

**Implementation:** Phase 2 (dynamic from DB), Phase 1 can show placeholder cards

---

### 6. FEATURED TEAMS SECTION (Dynamic)
**Purpose:** Showcase top-ranked teams, encourage team creation

**Content:**
```
section_title: "Top Teams"
section_description: "Professional organizations competing for glory"

# Dynamic query:
teams = Team.objects.filter(
    is_active=True
).order_by('-elo_rating')[:6]
```

**Data Needs:**
- Team.name, logo, game, elo_rating, member_count

**Visual:**
- 3x2 grid (desktop), 2x3 (tablet), 1x6 (mobile)
- Team cards with logo, name, game, rank badge
- Hover: Show member count, recent wins

**Implementation:** Phase 2 (dynamic), Phase 1 can show static examples

---

### 7. LOCAL PAYMENTS SECTION
**Purpose:** Highlight Bangladesh-first infrastructure, trust signal

**Content (Admin-Editable):**
```
section_title: "Local Payment Partners"
section_description: "Bangladesh-first infrastructure—we support the payment methods you already trust"

payment_methods: [
    {
        "name": "bKash",
        "icon": "💳",
        "color": "#E2136E",
        "description": "Mobile money leader"
    },
    {
        "name": "Nagad",
        "icon": "📱",
        "color": "#EE4023",
        "description": "Fast & reliable"
    },
    {
        "name": "Rocket",
        "icon": "⚡",
        "color": "#8142C6",
        "description": "Dutch-Bangla Bank"
    },
    {
        "name": "Bank Transfer",
        "icon": "🏦",
        "color": "#10B981",
        "description": "Traditional & secure"
    }
]

trust_message: "No credit cards required. No barriers to entry. Built for South Asian markets."
```

**Visual:**
- 4-column grid with colored icons
- Glass cards with brand colors
- Trust badge/shield icon
- Optional: "Coming Soon" badges for Stripe/PayPal (global expansion)

**Implementation:** Admin-editable JSON field

---

### 8. DELTACOIN ECONOMY SECTION
**Purpose:** Explain reward system, drive participation

**Content (Admin-Editable):**
```
section_title: "DeltaCoin Economy"
section_description: "Earn by competing. Spend on upgrades. Build your legacy."

cycle_diagram_svg: "..." (inline SVG or separate file)

earn_methods: [
    "Participating in tournaments",
    "Winning matches",
    "Achieving milestones",
    "Engaging with community"
]

spend_options: [
    "Store purchases",
    "Premium subscriptions",
    "Platform services",
    "Team merchandise"
]
```

**Visual:**
- Circular flow diagram (SVG animation)
- "Earn" → "Spend" → "Improve" → "Compete" cycle
- Icon-based card layout for earn/spend lists

**Implementation:** Admin-editable + SVG asset

---

### 9. COMMUNITY & CONTENT SECTION
**Purpose:** Show platform is more than competition

**Content (Dynamic):**
```
section_title: "Join the Community"
section_description: "Strategy guides, match highlights, esports news—all in one home"

# Dynamic query:
spotlight = get_spotlight(3)  # Recent blog posts
timeline = get_timeline(4)    # Recent community activity
```

**Data Needs:**
- Blog post titles, thumbnails, authors
- Community activity feed

**Visual:**
- 2-column layout: Blog highlights (left), Activity feed (right)
- CTA: "Explore Community"

**Implementation:** Already exists in current view, needs styling update

---

### 10. ROADMAP / VISION SECTION
**Purpose:** Show platform growth, build anticipation

**Content (Admin-Editable):**
```
section_title: "The Vision Ahead"
section_description: "Evolving toward global scale while staying rooted in emerging markets"

roadmap_items: [
    {
        "status": "COMPLETED",
        "title": "Full Tournament Lifecycle",
        "description": "Brackets, registration, results, disputes"
    },
    {
        "status": "COMPLETED",
        "title": "Team & Player Systems",
        "description": "Professional structures, ranking, analytics"
    },
    {
        "status": "IN_PROGRESS",
        "title": "Payment Integration",
        "description": "Local payment methods + prize distribution"
    },
    {
        "status": "PLANNED",
        "title": "Mobile Apps",
        "description": "iOS & Android native apps"
    },
    {
        "status": "PLANNED",
        "title": "Sponsor Marketplace",
        "description": "Connect brands with teams"
    },
    {
        "status": "PLANNED",
        "title": "Streaming Integrations",
        "description": "YouTube, Twitch, Facebook Gaming"
    }
]
```

**Visual:**
- Timeline view with progress indicators
- Status badges: ✅ Completed, 🔄 In Progress, 📅 Planned
- Horizontal scrollable on mobile

**Implementation:** Admin-editable JSON field

---

### 11. FINAL CTA SECTION
**Purpose:** Convert visitors to users

**Content (Admin-Editable):**
```
cta_title: "Ready to Compete?"
cta_description: "Join thousands of gamers building their esports careers on DeltaCrown"

primary_cta_text: "Create Account"
primary_cta_url: "/account/register/"

secondary_cta_text: "Explore Platform"
secondary_cta_url: "/about/"
```

**Visual:**
- Full-width gradient background
- Large centered CTAs
- Optional: Counter animation (players joined today)

**Implementation:** Admin-editable fields

---

### 12. FOOTER
**Purpose:** Navigation, trust signals, legal

**Content:**
- Links: About, Contact, Support, Terms, Privacy, Careers
- Social media: Discord, Twitter, Facebook, YouTube
- Contact: deltacrownhq@gmail.com
- Copyright & founding year

**Implementation:** Keep existing footer from base.html, ensure links updated

---

## HomePageContent Model Design

```python
# apps/siteui/models.py

from django.db import models
from django.core.validators import URLValidator

class HomePageContent(models.Model):
    """
    Single-row model for homepage content management.
    Enforces singleton pattern in admin.
    """
    
    # Hero Section
    hero_badge_text = models.CharField(max_length=100, default="Bangladesh's #1 Esports Platform")
    hero_title = models.CharField(max_length=200, default="From the Delta to the Crown")
    hero_subtitle = models.CharField(max_length=200, default="Where Champions Rise")
    hero_description = models.TextField(default="Building a world where geography does not define destiny...")
    
    primary_cta_text = models.CharField(max_length=50, default="Join Tournament")
    primary_cta_url = models.CharField(max_length=200, default="/tournaments/")
    
    secondary_cta_text = models.CharField(max_length=50, default="Explore Teams")
    secondary_cta_url = models.CharField(max_length=200, default="/teams/")
    
    # Stats/Highlights (JSON)
    hero_highlights = models.JSONField(default=list, blank=True, help_text="Array of {label, value, icon, source}")
    
    # Problem Section
    problem_section_enabled = models.BooleanField(default=True)
    problem_title = models.CharField(max_length=200, default="The Esports Gap")
    problem_subtitle = models.TextField(default="Most platforms solve one problem...")
    comparison_table = models.JSONField(default=list, blank=True)
    
    # Ecosystem Pillars
    pillars_section_enabled = models.BooleanField(default=True)
    ecosystem_pillars = models.JSONField(default=list, blank=True, help_text="Array of {icon, title, description, link}")
    
    # Games Section
    games_section_enabled = models.BooleanField(default=True)
    games_data = models.JSONField(default=list, blank=True, help_text="Phase 1: JSON array. Phase 2: Migrate to Game FK")
    
    # Payments Section
    payments_section_enabled = models.BooleanField(default=True)
    payment_methods = models.JSONField(default=list, blank=True)
    payments_trust_message = models.TextField(default="No credit cards required...")
    
    # DeltaCoin Section
    deltacoin_section_enabled = models.BooleanField(default=True)
    deltacoin_description = models.TextField(default="Earn by competing. Spend on upgrades...")
    deltacoin_earn_methods = models.JSONField(default=list, blank=True)
    deltacoin_spend_options = models.JSONField(default=list, blank=True)
    
    # Roadmap Section
    roadmap_section_enabled = models.BooleanField(default=True)
    roadmap_items = models.JSONField(default=list, blank=True)
    
    # Final CTA
    final_cta_title = models.CharField(max_length=200, default="Ready to Compete?")
    final_cta_description = models.TextField(default="Join thousands of gamers...")
    final_cta_primary_text = models.CharField(max_length=50, default="Create Account")
    final_cta_primary_url = models.CharField(max_length=200, default="/account/register/")
    
    # Meta
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Homepage Content"
        verbose_name_plural = "Homepage Content"
    
    def __str__(self):
        return f"Homepage Content (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        # Enforce singleton: Delete all other instances
        if not self.pk and HomePageContent.objects.exists():
            HomePageContent.objects.all().delete()
        return super().save(*args, **kwargs)
```

---

## Context Provider

```python
# apps/siteui/homepage_context.py

from typing import Dict, Any
from django.contrib.auth import get_user_model
from .models import HomePageContent

User = get_user_model()

def get_homepage_context() -> Dict[str, Any]:
    """
    Returns safe homepage context with DB content + dynamic stats.
    Falls back to defaults if HomePageContent doesn't exist.
    """
    # Get or create singleton content
    try:
        content = HomePageContent.objects.first()
        if not content:
            content = HomePageContent.objects.create()  # Creates with defaults
    except Exception:
        # If DB error, return safe defaults
        return _get_default_context()
    
    # Compute live stats
    stats = {
        "players_count": _safe_count(User.objects),
        "tournaments_count": _safe_count_model('tournaments', 'Tournament'),
        "teams_count": _safe_count_model('teams', 'Team'),
        "games_count": 11,  # Static for now
    }
    
    # Merge content + stats
    context = {
        "homepage_content": content,
        "live_stats": stats,
        "hero": {
            "badge_text": content.hero_badge_text,
            "title": content.hero_title,
            "subtitle": content.hero_subtitle,
            "description": content.hero_description,
            "primary_cta": {
                "text": content.primary_cta_text,
                "url": content.primary_cta_url,
            },
            "secondary_cta": {
                "text": content.secondary_cta_text,
                "url": content.secondary_cta_url,
            },
            "highlights": _merge_highlights(content.hero_highlights, stats),
        },
        "sections_enabled": {
            "problem": content.problem_section_enabled,
            "pillars": content.pillars_section_enabled,
            "games": content.games_section_enabled,
            "payments": content.payments_section_enabled,
            "deltacoin": content.deltacoin_section_enabled,
            "roadmap": content.roadmap_section_enabled,
        }
    }
    
    return context

def _safe_count(queryset):
    try:
        return queryset.count()
    except Exception:
        return 0

def _safe_count_model(app_label, model_name):
    try:
        from django.apps import apps
        Model = apps.get_model(app_label, model_name)
        return Model.objects.count()
    except Exception:
        return 0

def _merge_highlights(highlights_json, stats):
    """Replace 'DB_COUNT' source values with live stats."""
    for highlight in highlights_json:
        if highlight.get("source") == "DB_COUNT":
            if highlight["label"] == "Active Players":
                highlight["value"] = f"{stats['players_count']:,}+"
            elif highlight["label"] == "Tournaments":
                highlight["value"] = f"{stats['tournaments_count']:,}+"
            # ... other mappings
    return highlights_json

def _get_default_context():
    """Fallback if DB unavailable."""
    return {
        "hero": {
            "badge_text": "Bangladesh's #1 Esports Platform",
            "title": "From the Delta to the Crown",
            "subtitle": "Where Champions Rise",
            "description": "Building a world where geography does not define destiny...",
            "primary_cta": {"text": "Join Tournament", "url": "/tournaments/"},
            "secondary_cta": {"text": "Explore Teams", "url": "/teams/"},
            "highlights": [
                {"label": "Active Players", "value": "12,500+", "icon": "👥"},
                {"label": "Prize Pool", "value": "৳5,00,000+", "icon": "💰"},
                {"label": "Tournaments", "value": "150+", "icon": "🏆"},
                {"label": "Games", "value": "11", "icon": "🎮"},
            ],
        },
        "live_stats": {"players_count": 0, "tournaments_count": 0},
        "sections_enabled": {
            "problem": True,
            "pillars": True,
            "games": True,
            "payments": True,
            "deltacoin": True,
            "roadmap": True,
        },
    }
```

---

## Django Admin Configuration

```python
# apps/siteui/admin.py

from django.contrib import admin
from .models import HomePageContent
from django.utils.html import format_html

@admin.register(HomePageContent)
class HomePageContentAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Hero Section', {
            'fields': (
                'hero_badge_text',
                'hero_title',
                'hero_subtitle',
                'hero_description',
                'primary_cta_text',
                'primary_cta_url',
                'secondary_cta_text',
                'secondary_cta_url',
                'hero_highlights',
            ),
            'description': 'Main banner content and CTAs'
        }),
        ('Problem/Opportunity Section', {
            'fields': (
                'problem_section_enabled',
                'problem_title',
                'problem_subtitle',
                'comparison_table',
            ),
            'classes': ('collapse',)
        }),
        ('Ecosystem Pillars', {
            'fields': (
                'pillars_section_enabled',
                'ecosystem_pillars',
            ),
            'classes': ('collapse',)
        }),
        ('Games Section', {
            'fields': (
                'games_section_enabled',
                'games_data',
            ),
            'classes': ('collapse',),
            'description': 'Phase 1: JSON array. Phase 2: Migrate to Game FK'
        }),
        ('Local Payments', {
            'fields': (
                'payments_section_enabled',
                'payment_methods',
                'payments_trust_message',
            ),
            'classes': ('collapse',)
        }),
        ('DeltaCoin Economy', {
            'fields': (
                'deltacoin_section_enabled',
                'deltacoin_description',
                'deltacoin_earn_methods',
                'deltacoin_spend_options',
            ),
            'classes': ('collapse',)
        }),
        ('Roadmap', {
            'fields': (
                'roadmap_section_enabled',
                'roadmap_items',
            ),
            'classes': ('collapse',)
        }),
        ('Final CTA', {
            'fields': (
                'final_cta_title',
                'final_cta_description',
                'final_cta_primary_text',
                'final_cta_primary_url',
            ),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('updated_at', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ('updated_at', 'updated_by')
    
    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
    
    def has_add_permission(self, request):
        # Only allow adding if no instance exists
        return not HomePageContent.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion
        return False
```

---

## Implementation Plan: Phase 1 vs Phase 2

### Phase 1: Content Foundation (Weeks 1-2)
**Goal:** Build new template with admin-editable content, preserve hero background

**Steps:**
1. **Create model + admin** (Day 1)
   - Add `HomePageContent` model to `apps/siteui/models.py`
   - Configure Django admin with fieldsets
   - Run migrations
   - Populate default data via admin

2. **Build context provider** (Day 1)
   - Create `apps/siteui/homepage_context.py`
   - Add `get_homepage_context()` function
   - Test with/without DB data

3. **Create `home_v2.html` template** (Days 2-5)
   - Start from scratch (don't copy home_cyberpunk.html)
   - **PRESERVE:** Particle canvas background + overlay system
   - Use Tailwind CSS (no new CSS files if possible)
   - Build sections 1-11 in order
   - Ensure responsive (mobile-first)
   - Accessibility: focus states, reduced motion, ARIA labels

4. **Update view with feature flag** (Day 6)
   ```python
   def home(request):
       template = "home_v2.html" if request.GET.get('v') == '2' else "home_cyberpunk.html"
       context = get_homepage_context() if template == "home_v2.html" else _old_context()
       return render(request, template, context)
   ```

5. **Manual QA** (Day 7)
   - Test on Chrome, Firefox, Safari
   - Test mobile (iOS, Android)
   - Verify admin editing works
   - Check performance (Lighthouse)
   - Accessibility audit (aXe, WAVE)

**Deliverables:**
- ✅ `HomePageContent` model + migrations
- ✅ Django admin configuration
- ✅ `homepage_context.py` helper
- ✅ `templates/home_v2.html`
- ✅ Feature flag in view (`?v=2`)
- ✅ QA checklist (see below)

---

### Phase 2: Dynamic Data Wiring (Weeks 3-4)
**Goal:** Replace static/JSON data with dynamic DB queries

**Steps:**
1. **Featured Tournaments Section**
   - Query `Tournament.objects.filter(status__in=['REGISTRATION', 'ONGOING'])`
   - Add template logic for "no tournaments" state
   - Test with/without data

2. **Featured Teams Section**
   - Query `Team.objects.order_by('-elo_rating')[:6]`
   - Add team cards with logos, stats
   - Link to team detail pages

3. **Games Migration**
   - Migrate `games_data` JSON → `Game` ForeignKey ManyToMany
   - Update admin to use Game selector
   - Update template to loop dynamic games

4. **Community/Content**
   - Already exists (`spotlight`, `timeline`)
   - Update styling to match v2 design

5. **Analytics Integration** (Optional)
   - Track CTA clicks
   - Monitor section engagement
   - A/B test different hero copy

**Deliverables:**
- ✅ Dynamic tournament cards
- ✅ Dynamic team cards
- ✅ Games FK migration
- ✅ Updated admin UI
- ✅ Analytics setup (if desired)

---

## Design Requirements (2025 Esports Vibe)

### Visual Style
- **Dark gradients:** Black → Gray-900 → Black
- **Glass panels:** `backdrop-filter: blur(16px)`, `bg-opacity: 0.1`
- **Neon accents:** Cyan (#06b6d4), Purple (#8b5cf6), Gold (#facc15)
- **Typography:** Inter/Space Grotesk (or Rajdhani/Space Mono if preferred)
- **Shadows:** Multi-layer, colored glows
- **Animations:** Subtle, purposeful (scroll reveals, hover states, counter animations)

### Responsive Breakpoints
- Mobile: < 768px
- Tablet: 768px - 1024px
- Desktop: > 1024px

### Accessibility
- Focus states: 4px solid ring with offset
- Reduced motion: `@media (prefers-reduced-motion: reduce)`
- ARIA labels on interactive elements
- Contrast ratio: WCAG AA minimum (4.5:1 for text)

### Performance
- Lazy load images below fold
- Minimize layout shift (CLS < 0.1)
- First Contentful Paint < 1.5s
- Time to Interactive < 3.5s

---

## QA Checklist

### Visual Testing
- [ ] Hero section renders correctly on all screen sizes
- [ ] Particle canvas animates smoothly (60 FPS)
- [ ] All sections aligned and centered properly
- [ ] Glass cards have correct blur + opacity
- [ ] Text is readable (contrast check)
- [ ] CTAs are prominent and clickable
- [ ] Images load correctly (no broken assets)
- [ ] Icons display properly (emoji or SVG)

### Functional Testing
- [ ] All CTAs link to correct URLs
- [ ] Feature flag (`?v=2`) switches templates correctly
- [ ] Admin can edit all homepage fields
- [ ] JSON fields validate properly in admin
- [ ] Live stats update from DB (players, tournaments)
- [ ] "No data" states handled gracefully
- [ ] Section toggles work (enable/disable via admin)

### Responsive Testing
- [ ] Mobile: Single column layout, no horizontal scroll
- [ ] Tablet: 2-column grids, readable text sizes
- [ ] Desktop: Full-width sections, optimal spacing
- [ ] Hero CTAs stack on mobile
- [ ] Cards reflow properly at breakpoints

### Accessibility Testing
- [ ] Keyboard navigation works (Tab, Enter, Esc)
- [ ] Focus states visible on all interactive elements
- [ ] Screen reader announces content correctly
- [ ] ARIA labels present on icons/buttons
- [ ] Reduced motion respected (no forced animations)
- [ ] Color contrast passes WCAG AA

### Performance Testing
- [ ] Lighthouse score > 90 (Performance)
- [ ] Images optimized (WebP, lazy loading)
- [ ] No layout shift (CLS < 0.1)
- [ ] JavaScript bundle < 100KB
- [ ] First Contentful Paint < 1.5s

### Cross-Browser Testing
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Chrome (iOS/Android)
- [ ] Mobile Safari (iOS)

---

## Migration Strategy: Safe Switch-Over

### Current State
- Live site uses `home_cyberpunk.html`
- No disruption to users

### Phase 1 Testing
- Access v2 via `/?v=2` query parameter
- Test internally before public release
- Gather feedback from team/beta users

### Phase 1 Launch
- Option A: Hard switch (replace `home_cyberpunk.html` → `home_v2.html`)
- Option B: Gradual rollout (% of users see v2 randomly)
- Option C: User preference (let logged-in users choose)

**Recommended:** Option A after thorough QA (1-2 weeks of `?v=2` testing)

### Rollback Plan
- Keep `home_cyberpunk.html` intact
- If issues arise, revert view to render old template
- Fix issues in v2, re-test, re-deploy

---

## File Structure

```
apps/siteui/
  models.py                  # Add HomePageContent model
  admin.py                   # Add admin configuration
  homepage_context.py        # NEW: Context provider
  views.py                   # Update home() view with feature flag

templates/
  home_v2.html               # NEW: Phase 1 template
  home_cyberpunk.html        # PRESERVE: Current template (rollback)
  home_modern.html           # PRESERVE: Unused alternative

static/
  css/
    homepage-cyberpunk.css   # PRESERVE: Current CSS
    home_v2.css              # NEW (optional): Phase 1 styles (prefer Tailwind)
  js/
    homepage-cyberpunk.js    # PRESERVE: Current JS (particle canvas)
    home_v2.js               # NEW (optional): Phase 1 interactions

migrations/
  00XX_create_homepage_content.py  # NEW: Model migration
```

---

## Next Steps

1. **Review this blueprint** — Confirm section order, content strategy, technical approach
2. **Create Django model** — Add `HomePageContent` to `apps/siteui/models.py`
3. **Build context provider** — Implement `homepage_context.py`
4. **Start template** — Create `templates/home_v2.html` with hero section
5. **Iterate section-by-section** — Build, test, refine each section
6. **QA and polish** — Run full checklist before launch

---

## Notes & Considerations

### Why Not Delete Old Templates?
- Rollback safety
- Reference for copy/assets
- May want to offer multiple homepage styles in future

### Why Singleton Model?
- Homepage is single-instance content
- Prevents confusion (multiple homepage configs)
- Easier to manage via admin

### Why JSON Fields?
- Flexibility for Phase 1 (rapid iteration)
- Easy to migrate to proper FKs in Phase 2
- Admin can edit without code changes

### Why Feature Flag?
- Test in production without affecting users
- Gradual rollout capability
- Easy A/B testing setup

---

**End of Blueprint**
