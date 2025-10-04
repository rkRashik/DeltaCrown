# Tournament Detail Page V7 - Quick Visual Reference

## 🎨 Page Structure Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         HERO SECTION                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              [Full-width Banner Image]                    │  │
│  │                 [Gradient Overlay]                        │  │
│  │                                                            │  │
│  │        [Game Badge]    🎮 EFOOTBALL                       │  │
│  │                                                            │  │
│  │           TOURNAMENT NAME (H1)                            │  │
│  │         Short description text                            │  │
│  │                                                            │  │
│  │    ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐                   │  │
│  │    │Prize│  │Start│  │Teams│  │Format│  [Quick Stats]   │  │
│  │    │Pool │  │Date │  │12/32│  │SE   │                   │  │
│  │    └─────┘  └─────┘  └─────┘  └─────┘                   │  │
│  │                                                            │  │
│  │        [●  Registration Open ]  [Status Badge]            │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    CTA SECTION (Sticky)                         │
│  ┌────────────┐  ┌────────────┐  ┌──────┐  ┌──────┐          │
│  │ Register   │  │  Pay Entry │  │Share │  │Follow│          │
│  │    Now     │  │    Fee     │  │      │  │      │          │
│  └────────────┘  └────────────┘  └──────┘  └──────┘          │
│                                                                 │
│  ⏰ Registration closes in 2d 14h 30m                          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  TAB NAVIGATION (Sticky)                        │
│  [Overview] [Rules] [Prizes] [Schedule] [Brackets] ...         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      MAIN CONTENT AREA                          │
│  ┌─────────────────────────────┐  ┌────────────────────────┐  │
│  │      MAIN COLUMN            │  │     SIDEBAR           │  │
│  │  ┌───────────────────────┐  │  │  ┌─────────────────┐ │  │
│  │  │  About Tournament     │  │  │  │  Registration   │ │  │
│  │  │  Description text...  │  │  │  │  Progress       │ │  │
│  │  └───────────────────────┘  │  │  │  32/64 Teams    │ │  │
│  │                              │  │  │  [Progress Bar] │ │  │
│  │  ┌─────┐ ┌─────┐ ┌─────┐   │  │  └─────────────────┘ │  │
│  │  │Info │ │Info │ │Info │   │  │                        │  │
│  │  │Card │ │Card │ │Card │   │  │  ┌─────────────────┐ │  │
│  │  └─────┘ └─────┘ └─────┘   │  │  │ Important Dates │ │  │
│  │                              │  │  │  • Reg Start    │ │  │
│  │  ┌───────────────────────┐  │  │  │  • Reg End      │ │  │
│  │  │  Eligibility          │  │  │  │  • Tournament   │ │  │
│  │  │  Requirements         │  │  │  │    Start        │ │  │
│  │  └───────────────────────┘  │  │  └─────────────────┘ │  │
│  │                              │  │                        │  │
│  └──────────────────────────────┘  │  ┌─────────────────┐ │  │
│                                     │  │   Organizer     │ │  │
│                                     │  │  [Avatar]       │ │  │
│                                     │  │  Name           │ │  │
│                                     │  │  [Contact Btn]  │ │  │
│                                     │  └─────────────────┘ │  │
│                                     │                        │  │
│                                     │  ┌─────────────────┐ │  │
│                                     │  │ Quick Actions   │ │  │
│                                     │  │  • Report Issue │ │  │
│                                     │  │  • Download     │ │  │
│                                     │  └─────────────────┘ │  │
│                                     └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📊 Component Breakdown

### 1. Hero Section
```
Full-width background
↓
Dark gradient overlay (85-95% opacity)
↓
Centered content:
  - Game badge (icon + name)
  - Tournament title (H1, 3rem)
  - Subtitle (1.125rem)
  - 4-stat grid (auto-fit, 200px min)
  - Status badge (animated dot)
```

**Key Features:**
- Responsive background (cover, center)
- Gradient ensures text readability
- Stats cards have hover effects
- Status badge pulses for "Live"

---

### 2. CTA Section (Sticky)
```
Background: bg-secondary (#1e293b)
Border: 1px bottom
Position: sticky, top: 0
Z-index: 200

Layout:
┌──────────────────────────────────────────┐
│ [Primary CTA]  [Secondary CTAs...]  ⏰  │
└──────────────────────────────────────────┘
     ↑              ↑                ↑
   Main         Pay/Share/      Timer
  Action        Follow
```

**Button States:**
- **Guest:** "Login to Register" (primary)
- **Registered:** "Go to Dashboard" (primary)
- **Not Registered:** "Register Now" (primary)
- **Running:** "Watch Live" (primary)

---

### 3. Tab Navigation (Sticky)
```
8 Tabs:
┌────────┬─────┬──────┬─────────┬─────────┬──────────┬──────┬────┐
│Overview│Rules│Prizes│Schedule │Brackets │Participants│Media│FAQ │
└────────┴─────┴──────┴─────────┴─────────┴──────────┴──────┴────┘
   ↑ Active (border-bottom: primary color)
```

**Features:**
- Horizontal scroll on mobile
- URL hash updates (#overview, #rules, etc.)
- Smooth scroll to section
- Browser back/forward support

---

### 4. Content Layout

#### Desktop (> 1024px)
```
┌────────────────┬───────────┐
│                │           │
│   Main         │  Sidebar  │
│   (flex: 1)    │  (350px)  │
│                │           │
└────────────────┴───────────┘
      ↑ gap: 2rem
```

#### Mobile (< 1024px)
```
┌───────────────┐
│   Sidebar     │
│   (order: -1) │
├───────────────┤
│               │
│   Main        │
│   Content     │
│               │
└───────────────┘
```

---

## 🎯 Interactive Elements

### 1. Tab Switching
```javascript
Click Tab → 
  Remove .active from all tabs/panels → 
  Add .active to selected → 
  Update URL hash → 
  Smooth scroll to section
```

### 2. Share Modal
```
Click Share Button →
  Open modal (#shareModal) →
  User clicks platform:
    - Facebook → window.open(shareUrl)
    - Twitter → window.open(tweetUrl)
    - Discord → copyToClipboard()
    - WhatsApp → window.open(waUrl)
  OR
  Click Copy Link →
    copyToClipboard() →
    Show "Copied!" feedback →
    Toast notification
```

### 3. FAQ Accordion
```
Click Question →
  Close all other FAQs →
  Toggle current FAQ:
    - Add .active class
    - Expand answer (max-height transition)
    - Rotate icon
```

### 4. Registration Timer
```
setInterval(1000ms) →
  Calculate time remaining →
  Format (days/hours/minutes/seconds) →
  Update DOM →
  If expired:
    Show "Registration Closed"
    Stop interval
```

---

## 🎨 Design System Quick Reference

### Spacing Scale
```
xs:  0.25rem (4px)
sm:  0.5rem  (8px)
md:  1rem    (16px)
lg:  1.5rem  (24px)
xl:  2rem    (32px)
2xl: 3rem    (48px)
```

### Typography Scale
```
Hero Title:    3rem (48px), weight: 900
Card Title:    1.5rem (24px), weight: 700
Section Title: 1.25rem (20px), weight: 700
Body:          1rem (16px), weight: 400
Small:         0.875rem (14px)
Tiny:          0.75rem (12px)
```

### Border Radius
```
sm:  0.375rem (6px)
md:  0.5rem   (8px)
lg:  0.75rem  (12px)
xl:  1rem     (16px)
full: 9999px  (pill shape)
```

### Shadows
```
sm: 0 1px 2px rgba(0,0,0,0.3)
md: 0 4px 6px rgba(0,0,0,0.4)
lg: 0 10px 15px rgba(0,0,0,0.5)
xl: 0 20px 25px rgba(0,0,0,0.6)
```

---

## 📱 Responsive Breakpoints

### Desktop Large (1400px+)
- Two-column layout
- All features visible
- Hover effects active
- Sticky CTA & tabs

### Desktop (1024px - 1400px)
- Two-column layout
- Slightly narrower sidebar (300px)
- Same functionality

### Tablet (768px - 1024px)
- Single column
- Sidebar above content
- Stats grid 2 columns
- Simplified CTA layout

### Mobile (480px - 768px)
- Single column
- Stats vertical stack
- Full-width buttons
- Scrollable tabs

### Small Mobile (< 480px)
- Compressed hero
- Smaller typography
- Vertical CTAs
- Simplified cards

---

## 🎨 Color Usage Guide

### Primary Color (#6366f1)
- **Use for:**
  - Primary CTA buttons
  - Active tab indicators
  - Links
  - Icons
  - Progress bars
  - Badges

### Accent Color (#f59e0b)
- **Use for:**
  - Pay Entry button
  - Prize amounts
  - Warning notices
  - Timer elements
  - Free entry badges

### Status Colors
```
Live:      #10b981 (Green)
Open:      #3b82f6 (Blue)
Closed:    #6b7280 (Gray)
Completed: #8b5cf6 (Purple)
```

### Background Layers
```
Layer 1 (Body):      #0f172a (darkest)
Layer 2 (Cards):     #1e293b
Layer 3 (Hover):     #334155
Layer 4 (Active):    #475569 (lightest)
```

---

## 🔧 CSS Class Patterns

### Card Structure
```html
<div class="content-card">
  <h2 class="card-title">
    <svg>...</svg>
    Title Text
  </h2>
  <div class="card-body">
    <!-- Content -->
  </div>
</div>
```

### Button Variants
```html
<!-- Primary -->
<button class="btn-cta btn-primary">Text</button>

<!-- Accent -->
<button class="btn-cta btn-accent">Text</button>

<!-- Secondary -->
<button class="btn-cta btn-secondary">Text</button>

<!-- Outline -->
<button class="btn-cta btn-outline">Text</button>
```

### Stat Cards
```html
<div class="stat-item">
  <svg class="stat-icon">...</svg>
  <div class="stat-content">
    <span class="stat-value">12/32</span>
    <span class="stat-label">Teams</span>
  </div>
</div>
```

---

## 📐 Layout Measurements

### Hero Section
- Min Height: 500px (desktop), 400px (mobile)
- Padding: 3rem 2rem
- Title: 3rem → 2.5rem → 2rem (responsive)

### CTA Section
- Height: ~77px (auto with padding)
- Padding: 1.5rem 2rem
- Sticky top: 0

### Tab Navigation
- Height: ~60px
- Padding: 1.5rem 2rem (per tab)
- Sticky top: 77px (below CTA)

### Content Container
- Max Width: 1400px
- Padding: 0 2rem
- Gap: 2rem

### Sidebar
- Width: 350px (desktop)
- Gap between cards: 1.5rem

---

## 🎬 Animation Timing

### Standard Transitions
```css
Fast:   150ms cubic-bezier(0.4, 0, 0.2, 1)
Base:   250ms cubic-bezier(0.4, 0, 0.2, 1)
Slow:   350ms cubic-bezier(0.4, 0, 0.2, 1)
```

### Special Effects
- **Fade In:** 250ms opacity + translateY
- **Slide In:** 300ms transform
- **Pulse:** 2s infinite (status badge)
- **Shimmer:** 2s infinite (progress bar)

---

## 🚀 Quick Deploy Checklist

```
[ ] Static files collected
[ ] Browser cache cleared
[ ] Template loads without errors
[ ] All data displays correctly
[ ] Tabs switch properly
[ ] Share buttons work
[ ] Timer counts down
[ ] FAQ accordion works
[ ] Mobile view works
[ ] All links functional
[ ] No console errors
[ ] Performance acceptable
```

---

## 📞 Quick Troubleshooting

### Page not loading
1. Check server is running: `python manage.py runserver 8002`
2. Check URL: `http://localhost:8002/tournaments/t/slug/`
3. Check terminal for errors

### Styles not applying
1. Run: `python manage.py collectstatic --noinput`
2. Hard refresh: Ctrl+Shift+R (Chrome)
3. Check CSS file loaded in DevTools Network tab

### JavaScript not working
1. Check browser console for errors
2. Verify script tag in template
3. Check file path: `/static/js/tournaments-v7-detail.js`

### Data not showing
1. Check tournament has related models (schedule, finance, etc.)
2. Check template variable names match context
3. Add defensive checks: `{% if tournament.finance %}`

---

**Quick Reference Version:** 7.0.0  
**Last Updated:** October 5, 2025  
**Print this for easy reference during development!**
