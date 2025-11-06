# Part 4: UI/UX Design Specifications

**DeltaCrown Tournament Engine**  
**Version:** 1.0  
**Date:** November 3, 2025  
**Author:** Design & Development Team

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Design Philosophy](#2-design-philosophy)
3. [Design System Foundation](#3-design-system-foundation)
4. [Component Library](#4-component-library)
5. [Tournament Management Screens](#5-tournament-management-screens)
6. [Registration & Payment Flow](#6-registration--payment-flow)
7. [Bracket & Match Screens](#7-bracket--match-screens)
8. [Player Experience Screens](#8-player-experience-screens)
9. [Spectator & Community Screens](#9-spectator--community-screens)
10. [Mobile Design Patterns](#10-mobile-design-patterns)
11. [Accessibility Guidelines](#11-accessibility-guidelines)
12. [Animation & Interaction Patterns](#12-animation--interaction-patterns)

---

## 1. Introduction

This document provides comprehensive UI/UX design specifications for the DeltaCrown Tournament Engine. It serves as the bridge between the technical architecture (Part 2) and the visual implementation, ensuring a consistent, accessible, and engaging user experience.

### Document Purpose

- **For Designers:** Design system, component specifications, screen layouts
- **For Frontend Developers:** Implementation guidelines, component structure, responsive behavior
- **For Stakeholders:** Visual representation of features and user flows
- **For QA:** Testing criteria for UI consistency and accessibility

### Design Goals

1. **Bangladesh-First:** Optimized for local context (mobile-first, data-efficient, BDT currency)
2. **Gaming Aesthetic:** Modern, energetic design that resonates with esports culture
3. **Performance:** Fast loading, smooth animations, efficient asset usage
4. **Accessibility:** WCAG 2.1 AA compliant, keyboard navigable, screen reader friendly
5. **Scalability:** Component-based system that grows with platform needs

### Target Devices & Browsers

**Primary Devices (80% traffic):**
- Mobile: 360x640 to 428x926 (iOS/Android)
- Tablet: 768x1024 to 1024x1366 (iPad, Android tablets)
- Desktop: 1366x768 to 1920x1080

**Browser Support:**
- Chrome 90+ (primary)
- Firefox 88+
- Safari 14+ (iOS/macOS)
- Edge 90+

---

## 2. Design Philosophy

### Core Principles

**1. Clarity Over Complexity**
- Information hierarchy guides user attention
- Single primary action per screen
- Progressive disclosure for advanced features
- Clear visual feedback for all interactions

**2. Speed & Efficiency**
- Minimize clicks to core actions
- Smart defaults reduce form fields
- Keyboard shortcuts for power users
- Optimistic UI updates

**3. Trust & Transparency**
- Clear payment verification process
- Real-time tournament status updates
- Transparent dispute resolution
- Organizer accountability (profiles, ratings)

**4. Community & Excitement**
- Live match updates create urgency
- Social features encourage engagement
- Achievements and badges gamify participation
- Sponsor visibility enhances professionalism

### Design Language

**Tone & Voice:**
- **Professional yet Energetic:** Serious about competition, exciting about esports
- **Inclusive & Welcoming:** Accessible to casual and hardcore gamers
- **Local & Global:** Bangladesh-first but internationally competitive

**Visual Style:**
- **Dark Mode Primary:** Reduces eye strain, aligns with gaming culture
- **Neon Accents:** High-contrast highlights for CTAs and status indicators
- **Clean Typography:** Legible at all sizes, professional hierarchy
- **Purposeful Animation:** Enhances understanding, never decorative only

### Tournament State Machine

**Purpose:** Visual alignment between backend state enums and UI transitions to guide animations, modal behavior, and conditional component rendering.

**State Flow Diagram:**

```
┌──────────┐
│  DRAFT   │ (Organizer only, hidden from public)
└────┬─────┘
     │ Publish Action
     ▼
┌──────────┐
│PUBLISHED │ (Public view, registration locked)
└────┬─────┘
     │ Open Registration Action
     ▼
┌───────────────┐
│ REGISTRATION  │ (Accept sign-ups, payment submissions)
│     OPEN      │ ← Most UI interactions happen here
└───────┬───────┘
        │ Auto-transition at start_time
        ▼
┌──────────┐
│ ONGOING  │ (Brackets locked, match results, live HUD)
└────┬─────┘
     │ Manual completion or auto after final match
     ▼
┌──────────┐
│COMPLETED │ (Winners declared, certificates issued)
└────┬─────┘
     │ Auto-transition after 90 days (configurable)
     ▼
┌──────────┐
│ ARCHIVED │ (Read-only, search excluded by default)
└──────────┘

  ┌──────────┐
  │CANCELLED │ (Can transition from any state)
  └──────────┘
```

**State-Specific UI Behaviors:**

| State | Public Visibility | Registration CTA | Bracket View | Match Submission | Certificate Access |
|-------|-------------------|------------------|--------------|------------------|--------------------|
| **Draft** | ❌ Organizer only | ❌ Hidden | ❌ Hidden | ❌ Disabled | ❌ Not issued |
| **Published** | ✅ Public view | 🔒 "Registration Opens [Date]" | 👁️ Preview (empty) | ❌ Disabled | ❌ Not issued |
| **Registration Open** | ✅ Public view | ✅ "Register Now" (primary) | 👁️ Preview (filling) | ❌ Disabled | ❌ Not issued |
| **Ongoing** | ✅ Public view | 🔒 "Registration Closed" | ✅ Live bracket | ✅ Enabled | ⏳ Pending completion |
| **Completed** | ✅ Public view | 🔒 "Tournament Ended" | ✅ Final standings | 🔒 Read-only | ✅ Issued to winners |
| **Archived** | 🔍 Search only | 🔒 "Archived" | ✅ Historical view | 🔒 Read-only | ✅ Still accessible |
| **Cancelled** | ⚠️ Public (with notice) | 🔒 "Cancelled" | ❌ Hidden | ❌ Disabled | ❌ Not issued |

**Transition Animations:**

1. **Published → Registration Open:**
   - Confetti animation on tournament page
   - "Register Now" button pulses (3 times)
   - Toast notification to followers: "Registration is now open!"
   - Email/SMS to interested users

2. **Registration Open → Ongoing:**
   - Countdown timer reaches 00:00:00
   - Auto-redirect participants to bracket view
   - Banner change: "🔴 LIVE" badge appears
   - Disable registration forms (fade out + disable)

3. **Ongoing → Completed:**
   - Final match result triggers completion modal
   - Winners podium animation (1st, 2nd, 3rd place)
   - Certificate generation background task
   - "View Certificate" CTA for winners

4. **Completed → Archived:**
   - No user-facing animation (background transition)
   - Search results exclude by default (can opt-in with filter)
   - Historical badge on tournament card

5. **Any State → Cancelled:**
   - Red banner: "⚠️ This tournament has been cancelled"
   - Refund notice (if entry fees collected)
   - Contact organizer CTA
   - Dim tournament card (grayscale filter)

**Backend Enum Alignment:**

Ensure these states match your Django model `TournamentStatus` choices:

```python
class TournamentStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    PUBLISHED = 'PUBLISHED', 'Published'
    REGISTRATION_OPEN = 'REGISTRATION_OPEN', 'Registration Open'
    ONGOING = 'ONGOING', 'Ongoing'
    COMPLETED = 'COMPLETED', 'Completed'
    ARCHIVED = 'ARCHIVED', 'Archived'
    CANCELLED = 'CANCELLED', 'Cancelled'
```

**Conditional Rendering Examples:**

```html
<!-- Show registration CTA only if state allows -->
{% if tournament.status == 'REGISTRATION_OPEN' %}
    <button class="btn-primary" data-analytics-id="dc-btn-register">
        Register Now
    </button>
{% elif tournament.status == 'PUBLISHED' %}
    <button class="btn-secondary" disabled>
        Registration Opens {{ tournament.registration_opens_at|date:"M d, g:i A" }}
    </button>
{% elif tournament.status == 'ONGOING' %}
    <span class="badge badge-live">🔴 LIVE</span>
{% endif %}

<!-- Bracket visibility -->
{% if tournament.status in ['ONGOING', 'COMPLETED', 'ARCHIVED'] %}
    <a href="{% url 'tournament_bracket' tournament.slug %}" 
       data-analytics-id="dc-link-bracket">
        View Bracket
    </a>
{% endif %}
```

**State Transition Validation:**

- Draft → Published: Requires all mandatory fields (date, format, teams)
- Published → Registration Open: Requires start_time set
- Registration Open → Ongoing: Auto-trigger at start_time (cron job)
- Ongoing → Completed: Requires all matches resolved OR manual override
- Any → Cancelled: Requires cancellation reason (logged in admin)

---

## 3. Design System Foundation

### 3.1 Color Palette

**Primary Colors (Dark Theme):**

```css
/* Background Layers */
--bg-primary: #0A0E1A;      /* Main background (deep navy) */
--bg-secondary: #151928;    /* Card backgrounds */
--bg-tertiary: #1F2937;     /* Elevated elements (modals, dropdowns) */
--bg-hover: #2D3748;        /* Hover states */

/* Brand Colors */
--brand-primary: #3B82F6;   /* DeltaCrown Blue (primary CTAs) */
--brand-secondary: #8B5CF6; /* Purple (secondary actions) */
--brand-accent: #F59E0B;    /* Amber (highlights, warnings) */

/* Semantic Colors */
--success: #10B981;         /* Green (confirmed, completed) */
--warning: #F59E0B;         /* Amber (pending, attention needed) */
--error: #EF4444;           /* Red (errors, disputes) */
--info: #3B82F6;            /* Blue (information, neutral) */

/* Neon Accents (Gaming Aesthetic) */
--neon-cyan: #06B6D4;       /* Live indicators */
--neon-magenta: #EC4899;    /* Featured tournaments */
--neon-lime: #84CC16;       /* Online status, check-in */

/* Text Colors */
--text-primary: #F9FAFB;    /* Primary text (white) */
--text-secondary: #9CA3AF;  /* Secondary text (gray) */
--text-tertiary: #6B7280;   /* Tertiary text (muted) */
--text-disabled: #4B5563;   /* Disabled text */

/* Borders & Dividers */
--border-primary: #374151;  /* Primary borders */
--border-secondary: #1F2937;/* Subtle dividers */
--border-accent: #3B82F6;   /* Highlighted borders */
```

**Light Theme (Optional):**

```css
/* Background Layers (Light) */
--bg-primary-light: #FFFFFF;
--bg-secondary-light: #F3F4F6;
--bg-tertiary-light: #E5E7EB;

/* Text Colors (Light) */
--text-primary-light: #111827;
--text-secondary-light: #4B5563;
--text-tertiary-light: #6B7280;
```

**Color Usage Guidelines:**

| Color | Use Case | Example |
|-------|----------|---------|
| `--brand-primary` | Primary CTAs, active states | "Register Now", active nav links |
| `--brand-secondary` | Secondary actions, badges | "View Details", achievement badges |
| `--brand-accent` | Highlights, featured items | Featured tournaments, new notifications |
| `--success` | Confirmations, completed states | Payment verified, match completed |
| `--warning` | Pending actions, attention | Payment pending, check-in required |
| `--error` | Errors, disputes, rejections | Payment rejected, dispute filed |
| `--neon-cyan` | Live/real-time indicators | Live match badge, streaming indicator |

**Alert & Message Color Tokens** (for consistent error/success/warning messaging):

| State | Text Color | Background | Border | Use Case |
|-------|-----------|------------|--------|----------|
| **Success** | `--success` (#10B981) | `#ECFDF5` (green-50) | `#10B981` | Payment approved, registration confirmed |
| **Warning** | `--warning` (#F59E0B) | `#FFFBEB` (amber-50) | `#F59E0B` | Payment pending, deadline approaching |
| **Error** | `--error` (#EF4444) | `#FEF2F2` (red-50) | `#EF4444` | Payment rejected, validation failed |
| **Info** | `--info` (#3B82F6) | `#EFF6FF` (blue-50) | `#3B82F6` | Helpful tips, neutral information |

**Alert Component CSS:**

```css
/* Base Alert Styles */
.alert {
    padding: 1rem;
    border-radius: 0.5rem;
    border-left: 4px solid;
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
}

/* Success Alert */
.alert-success {
    background-color: #ECFDF5;
    border-color: var(--success);
    color: #065F46; /* green-800 for readability */
}

/* Warning Alert */
.alert-warning {
    background-color: #FFFBEB;
    border-color: var(--warning);
    color: #92400E; /* amber-800 */
}

/* Error Alert */
.alert-error {
    background-color: #FEF2F2;
    border-color: var(--error);
    color: #991B1B; /* red-800 */
}

/* Info Alert */
.alert-info {
    background-color: #EFF6FF;
    border-color: var(--info);
    color: #1E40AF; /* blue-800 */
}
```

---

### 3.2 Typography

**Font Stack:**

```css
/* Primary Font (UI) */
--font-primary: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* Secondary Font (Headings) */
--font-heading: 'Outfit', 'Inter', sans-serif;

/* Monospace Font (Codes, IDs) */
--font-mono: 'Fira Code', 'Courier New', monospace;

/* Bengali Support */
--font-bengali: 'Noto Sans Bengali', sans-serif;
```

**Type Scale:**

```css
/* Font Sizes */
--text-xs: 0.75rem;    /* 12px - Captions, meta info */
--text-sm: 0.875rem;   /* 14px - Body small, labels */
--text-base: 1rem;     /* 16px - Body text */
--text-lg: 1.125rem;   /* 18px - Emphasized text */
--text-xl: 1.25rem;    /* 20px - Subheadings */
--text-2xl: 1.5rem;    /* 24px - Section headings */
--text-3xl: 1.875rem;  /* 30px - Page headings */
--text-4xl: 2.25rem;   /* 36px - Hero text */
--text-5xl: 3rem;      /* 48px - Display text */

/* Font Weights */
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
--font-black: 900;

/* Line Heights */
--leading-tight: 1.25;   /* Headings */
--leading-normal: 1.5;   /* Body text */
--leading-relaxed: 1.75; /* Long-form content */
```

**Typography Hierarchy:**

```html
<!-- H1 - Page Title -->
<h1 class="text-4xl font-bold text-primary leading-tight">
    DeltaCrown Valorant Cup 2025
</h1>

<!-- H2 - Section Heading -->
<h2 class="text-3xl font-semibold text-primary leading-tight">
    Tournament Details
</h2>

<!-- H3 - Subsection Heading -->
<h3 class="text-2xl font-semibold text-primary">
    Registration Information
</h3>

<!-- H4 - Card Heading -->
<h4 class="text-xl font-medium text-primary">
    Participant List
</h4>

<!-- Body Text -->
<p class="text-base text-secondary leading-normal">
    This tournament follows FACEIT anti-cheat rules...
</p>

<!-- Small Text / Caption -->
<span class="text-sm text-tertiary">
    Created on November 3, 2025
</span>

<!-- Meta / Micro Text -->
<span class="text-xs text-tertiary uppercase tracking-wide">
    VALORANT • 5V5 • SINGLE ELIMINATION
</span>
```

---

### 3.3 Spacing System

**Spacing Scale (Tailwind-based):**

```css
--space-0: 0;          /* 0px */
--space-1: 0.25rem;    /* 4px */
--space-2: 0.5rem;     /* 8px */
--space-3: 0.75rem;    /* 12px */
--space-4: 1rem;       /* 16px */
--space-5: 1.25rem;    /* 20px */
--space-6: 1.5rem;     /* 24px */
--space-8: 2rem;       /* 32px */
--space-10: 2.5rem;    /* 40px */
--space-12: 3rem;      /* 48px */
--space-16: 4rem;      /* 64px */
--space-20: 5rem;      /* 80px */
--space-24: 6rem;      /* 96px */
```

**Spacing Guidelines:**

| Element | Spacing | Example |
|---------|---------|---------|
| Component padding (small) | `space-4` (16px) | Button padding, input fields |
| Component padding (medium) | `space-6` (24px) | Card padding, modal padding |
| Component padding (large) | `space-8` (32px) | Section padding, hero padding |
| Element gap (tight) | `space-2` (8px) | Icon + text, form field gap |
| Element gap (normal) | `space-4` (16px) | Button group, list items |
| Element gap (loose) | `space-6` (24px) | Card grid, section dividers |
| Section spacing | `space-12` (48px) | Between major sections |
| Page margins (mobile) | `space-4` (16px) | Left/right container padding |
| Page margins (desktop) | `space-8` (32px) | Left/right container padding |

---

### 3.4 Border Radius

```css
--radius-none: 0;
--radius-sm: 0.25rem;   /* 4px - Small elements */
--radius-base: 0.5rem;  /* 8px - Buttons, inputs */
--radius-lg: 0.75rem;   /* 12px - Cards */
--radius-xl: 1rem;      /* 16px - Modals, large cards */
--radius-2xl: 1.5rem;   /* 24px - Hero sections */
--radius-full: 9999px;  /* Circular elements */
```

---

### 3.5 Shadows & Elevation

```css
/* Shadow Levels */
--shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.3);
--shadow-base: 0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px 0 rgba(0, 0, 0, 0.3);
--shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3);
--shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3);
--shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3);
--shadow-2xl: 0 25px 50px -12px rgba(0, 0, 0, 0.6);

/* Glow Effects (Gaming Aesthetic) */
--glow-primary: 0 0 20px rgba(59, 130, 246, 0.5);    /* Blue glow */
--glow-success: 0 0 20px rgba(16, 185, 129, 0.5);    /* Green glow */
--glow-warning: 0 0 20px rgba(245, 158, 11, 0.5);    /* Amber glow */
--glow-live: 0 0 30px rgba(6, 182, 212, 0.7);        /* Cyan glow for live */
```

**Elevation Hierarchy:**

| Level | Shadow | Use Case |
|-------|--------|----------|
| 0 | None | Flat elements, text |
| 1 | `shadow-sm` | Subtle cards, list items |
| 2 | `shadow-base` | Default cards, inputs |
| 3 | `shadow-md` | Elevated cards, dropdowns |
| 4 | `shadow-lg` | Modals, popovers |
| 5 | `shadow-xl` | Mega menus, full overlays |
| Special | `glow-*` | Live indicators, CTAs, featured items |

---

### 3.6 Animation Timing

```css
/* Duration */
--duration-fast: 150ms;      /* Instant feedback (hover, focus) */
--duration-base: 250ms;      /* Standard transitions */
--duration-slow: 350ms;      /* Complex animations */
--duration-slower: 500ms;    /* Page transitions, modals */

/* Easing Functions */
--ease-in: cubic-bezier(0.4, 0, 1, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);

/* Standard Transition */
--transition-base: all var(--duration-base) var(--ease-out);
```

---

### 3.7 Responsive Breakpoints

```css
/* Mobile First Approach */
--screen-sm: 640px;   /* Small devices (landscape phones) */
--screen-md: 768px;   /* Medium devices (tablets) */
--screen-lg: 1024px;  /* Large devices (laptops) */
--screen-xl: 1280px;  /* Extra large (desktops) */
--screen-2xl: 1536px; /* 2X large (large desktops) */
```

**Breakpoint Usage:**

```css
/* Mobile (default) */
.container {
    padding: var(--space-4);
}

/* Tablet and up */
@media (min-width: 768px) {
    .container {
        padding: var(--space-8);
        max-width: 720px;
        margin: 0 auto;
    }
}

/* Desktop and up */
@media (min-width: 1024px) {
    .container {
        max-width: 960px;
    }
}
```

---

### 3.8 Grid System

**12-Column Grid:**

```css
.grid-container {
    display: grid;
    grid-template-columns: repeat(12, 1fr);
    gap: var(--space-6);
}

/* Column Spans */
.col-span-1 { grid-column: span 1; }
.col-span-2 { grid-column: span 2; }
.col-span-3 { grid-column: span 3; }
.col-span-4 { grid-column: span 4; }
.col-span-6 { grid-column: span 6; }
.col-span-8 { grid-column: span 8; }
.col-span-12 { grid-column: span 12; }
```

**Common Layouts:**

```html
<!-- Two-column layout (sidebar + content) -->
<div class="grid grid-cols-12 gap-6">
    <aside class="col-span-12 lg:col-span-3"><!-- Sidebar --></aside>
    <main class="col-span-12 lg:col-span-9"><!-- Content --></main>
</div>

<!-- Three-column card grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    <div class="card"><!-- Card 1 --></div>
    <div class="card"><!-- Card 2 --></div>
    <div class="card"><!-- Card 3 --></div>
</div>

<!-- Four-column stats -->
<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
    <div class="stat"><!-- Stat 1 --></div>
    <div class="stat"><!-- Stat 2 --></div>
    <div class="stat"><!-- Stat 3 --></div>
    <div class="stat"><!-- Stat 4 --></div>
</div>
```

---

### 3.9 Iconography

**Icon Library:** Heroicons (by Tailwind Labs)

**Icon Sizes:**

```css
--icon-xs: 16px;   /* Inline with text */
--icon-sm: 20px;   /* Small icons, badges */
--icon-base: 24px; /* Default icon size */
--icon-lg: 32px;   /* Large icons, features */
--icon-xl: 48px;   /* Hero icons, empty states */
```

**Icon Usage Guidelines:**
- Always include text labels for accessibility
- Use outline style for inactive/secondary actions
- Use solid style for active/primary actions
- Maintain consistent stroke width (2px default)
- Color should match adjacent text color

**Common Icons:**

| Context | Icon | Heroicon Name |
|---------|------|---------------|
| Tournament | 🏆 | `TrophyIcon` |
| Registration | ✅ | `CheckCircleIcon` |
| Payment | 💳 | `CreditCardIcon` |
| Match | ⚔️ | `FireIcon` |
| Live | 🔴 | `SignalIcon` |
| Teams | 👥 | `UsersIcon` |
| Schedule | 📅 | `CalendarIcon` |
| Settings | ⚙️ | `CogIcon` |
| Notifications | 🔔 | `BellIcon` |
| Chat | 💬 | `ChatBubbleIcon` |

---

## 4. Component Library

### 4.1 Buttons

**Button Variants:**

```html
<!-- Primary Button (Main CTAs) -->
<button class="btn btn-primary">
    <span class="btn-icon">
        <svg><!-- Icon --></svg>
    </span>
    <span class="btn-text">Register Now</span>
</button>

<!-- Secondary Button -->
<button class="btn btn-secondary">
    View Details
</button>

<!-- Ghost Button (Subtle Actions) -->
<button class="btn btn-ghost">
    Cancel
</button>

<!-- Danger Button (Destructive Actions) -->
<button class="btn btn-danger">
    Delete Tournament
</button>

<!-- Disabled Button -->
<button class="btn btn-primary" disabled>
    Registration Closed
</button>

<!-- Loading Button -->
<button class="btn btn-primary btn-loading">
    <span class="spinner"></span>
    Processing...
</button>
```

**Button Styles:**

```css
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    padding: var(--space-3) var(--space-6);
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    line-height: 1;
    border-radius: var(--radius-base);
    border: 2px solid transparent;
    cursor: pointer;
    transition: var(--transition-base);
    white-space: nowrap;
}

/* Primary Button */
.btn-primary {
    background: var(--brand-primary);
    color: var(--text-primary);
    box-shadow: var(--glow-primary);
}

.btn-primary:hover {
    background: #2563EB;
    transform: translateY(-1px);
    box-shadow: var(--shadow-md), var(--glow-primary);
}

.btn-primary:active {
    transform: translateY(0);
}

/* Secondary Button */
.btn-secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    border-color: var(--border-primary);
}

.btn-secondary:hover {
    background: var(--bg-hover);
    border-color: var(--brand-primary);
}

/* Ghost Button */
.btn-ghost {
    background: transparent;
    color: var(--text-secondary);
}

.btn-ghost:hover {
    background: var(--bg-tertiary);
    color: var(--text-primary);
}

/* Danger Button */
.btn-danger {
    background: var(--error);
    color: var(--text-primary);
}

.btn-danger:hover {
    background: #DC2626;
}

/* Disabled State */
.btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    pointer-events: none;
}

/* Loading State */
.btn-loading {
    pointer-events: none;
}

.btn-loading .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}
```

**Button Sizes:**

```html
<!-- Small -->
<button class="btn btn-primary btn-sm">Small</button>

<!-- Base (default) -->
<button class="btn btn-primary">Base</button>

<!-- Large -->
<button class="btn btn-primary btn-lg">Large</button>
```

```css
.btn-sm {
    padding: var(--space-2) var(--space-4);
    font-size: var(--text-sm);
}

.btn-lg {
    padding: var(--space-4) var(--space-8);
    font-size: var(--text-lg);
}
```

---

### 4.2 Card Components

**Tournament Card:**

```html
<article class="card card-tournament">
    <!-- Card Header with Image -->
    <div class="card-image">
        <img src="tournament-banner.jpg" alt="Valorant Cup 2025">
        <div class="card-badge card-badge-live">
            <span class="badge-dot"></span>
            LIVE
        </div>
    </div>
    
    <!-- Card Body -->
    <div class="card-body">
        <div class="card-meta">
            <span class="badge badge-game">VALORANT</span>
            <span class="card-date">
                <svg class="icon-sm"><!-- Calendar icon --></svg>
                Dec 15, 2025
            </span>
        </div>
        
        <h3 class="card-title">DeltaCrown Valorant Cup 2025</h3>
        
        <div class="card-stats">
            <div class="stat">
                <span class="stat-value">32</span>
                <span class="stat-label">Teams</span>
            </div>
            <div class="stat">
                <span class="stat-value">৳50,000</span>
                <span class="stat-label">Prize Pool</span>
            </div>
            <div class="stat">
                <span class="stat-value">16/32</span>
                <span class="stat-label">Registered</span>
            </div>
        </div>
        
        <div class="card-footer">
            <button class="btn btn-primary btn-sm">Register Now</button>
            <button class="btn btn-ghost btn-sm">View Details</button>
        </div>
    </div>
</article>
```

**Card Styles:**

```css
.card {
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--border-secondary);
    transition: var(--transition-base);
}

.card:hover {
    border-color: var(--border-accent);
    box-shadow: var(--shadow-lg);
    transform: translateY(-4px);
}

.card-image {
    position: relative;
    aspect-ratio: 16/9;
    overflow: hidden;
}

.card-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: var(--transition-base);
}

.card:hover .card-image img {
    transform: scale(1.05);
}

.card-badge {
    position: absolute;
    top: var(--space-3);
    right: var(--space-3);
    padding: var(--space-2) var(--space-3);
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(8px);
    border-radius: var(--radius-base);
    font-size: var(--text-xs);
    font-weight: var(--font-bold);
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: var(--space-2);
}

.card-badge-live {
    background: rgba(6, 182, 212, 0.2);
    color: var(--neon-cyan);
    border: 1px solid var(--neon-cyan);
    box-shadow: var(--glow-live);
}

.badge-dot {
    width: 8px;
    height: 8px;
    background: var(--neon-cyan);
    border-radius: 50%;
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}

.card-body {
    padding: var(--space-6);
}

.card-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--space-4);
}

.card-date {
    display: flex;
    align-items: center;
    gap: var(--space-1);
    color: var(--text-secondary);
    font-size: var(--text-sm);
}

.card-title {
    font-size: var(--text-xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-4);
    line-height: var(--leading-tight);
}

.card-stats {
    display: flex;
    gap: var(--space-6);
    padding: var(--space-4) 0;
    margin-bottom: var(--space-4);
    border-top: 1px solid var(--border-secondary);
    border-bottom: 1px solid var(--border-secondary);
}

.stat {
    display: flex;
    flex-direction: column;
    gap: var(--space-1);
}

.stat-value {
    font-size: var(--text-lg);
    font-weight: var(--font-bold);
    color: var(--brand-primary);
}

.stat-label {
    font-size: var(--text-xs);
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.card-footer {
    display: flex;
    gap: var(--space-3);
}
```

**Match Card:**

```html
<article class="card card-match">
    <div class="match-header">
        <span class="match-round">SEMIFINALS</span>
        <span class="match-status match-status-live">LIVE</span>
    </div>
    
    <div class="match-teams">
        <div class="team team-winner">
            <img src="team1-logo.png" alt="Team Alpha" class="team-logo">
            <span class="team-name">Team Alpha</span>
            <span class="team-score">13</span>
        </div>
        
        <div class="match-divider">
            <span class="match-vs">VS</span>
        </div>
        
        <div class="team">
            <img src="team2-logo.png" alt="Team Beta" class="team-logo">
            <span class="team-name">Team Beta</span>
            <span class="team-score">8</span>
        </div>
    </div>
    
    <div class="match-footer">
        <button class="btn btn-ghost btn-sm">
            <svg class="icon-sm"><!-- Eye icon --></svg>
            Watch Stream
        </button>
        <button class="btn btn-ghost btn-sm">
            View Details
        </button>
    </div>
</article>
```

**Match Card Styles:**

```css
.card-match {
    background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-tertiary) 100%);
}

.match-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--space-4) var(--space-6);
    border-bottom: 1px solid var(--border-secondary);
}

.match-round {
    font-size: var(--text-xs);
    font-weight: var(--font-bold);
    color: var(--text-tertiary);
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.match-status {
    padding: var(--space-1) var(--space-3);
    border-radius: var(--radius-full);
    font-size: var(--text-xs);
    font-weight: var(--font-bold);
}

.match-status-live {
    background: rgba(6, 182, 212, 0.2);
    color: var(--neon-cyan);
    border: 1px solid var(--neon-cyan);
    animation: pulse 2s infinite;
}

.match-teams {
    padding: var(--space-6);
}

.team {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-4);
    border-radius: var(--radius-base);
    transition: var(--transition-base);
}

.team:hover {
    background: var(--bg-hover);
}

.team-winner {
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid rgba(59, 130, 246, 0.3);
}

.team-logo {
    width: 40px;
    height: 40px;
    border-radius: var(--radius-base);
    object-fit: cover;
}

.team-name {
    flex: 1;
    font-weight: var(--font-medium);
    color: var(--text-primary);
}

.team-score {
    font-size: var(--text-2xl);
    font-weight: var(--font-bold);
    color: var(--brand-primary);
}

.match-divider {
    display: flex;
    justify-content: center;
    margin: var(--space-2) 0;
}

.match-vs {
    font-size: var(--text-sm);
    font-weight: var(--font-bold);
    color: var(--text-tertiary);
}

.match-footer {
    display: flex;
    gap: var(--space-3);
    padding: var(--space-4) var(--space-6);
    border-top: 1px solid var(--border-secondary);
}
```

---

### 4.3 Form Elements

**Input Fields:**

```html
<!-- Text Input -->
<div class="form-group">
    <label class="form-label" for="tournament-name">
        Tournament Name
        <span class="form-required">*</span>
    </label>
    <input 
        type="text" 
        id="tournament-name" 
        class="form-input" 
        placeholder="Enter tournament name"
        required
    >
    <span class="form-hint">This will be displayed publicly</span>
</div>

<!-- Input with Icon -->
<div class="form-group">
    <label class="form-label" for="search">Search</label>
    <div class="input-group">
        <span class="input-icon input-icon-left">
            <svg class="icon-sm"><!-- Search icon --></svg>
        </span>
        <input 
            type="search" 
            id="search" 
            class="form-input input-with-icon-left" 
            placeholder="Search tournaments..."
        >
    </div>
</div>

<!-- Input with Error -->
<div class="form-group form-group-error">
    <label class="form-label" for="email">Email</label>
    <input 
        type="email" 
        id="email" 
        class="form-input form-input-error" 
        value="invalidemail"
        aria-invalid="true"
        aria-describedby="email-error"
    >
    <span class="form-error" id="email-error">
        <svg class="icon-sm"><!-- Alert icon --></svg>
        Please enter a valid email address
    </span>
</div>

<!-- Input with Success -->
<div class="form-group form-group-success">
    <label class="form-label" for="username">Username</label>
    <input 
        type="text" 
        id="username" 
        class="form-input form-input-success" 
        value="player123"
    >
    <span class="form-success">
        <svg class="icon-sm"><!-- Check icon --></svg>
        Username is available
    </span>
</div>
```

**Form Styles:**

```css
.form-group {
    margin-bottom: var(--space-6);
}

.form-label {
    display: block;
    margin-bottom: var(--space-2);
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-primary);
}

.form-required {
    color: var(--error);
    margin-left: var(--space-1);
}

.form-input {
    width: 100%;
    padding: var(--space-3) var(--space-4);
    font-size: var(--text-base);
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 2px solid var(--border-primary);
    border-radius: var(--radius-base);
    transition: var(--transition-base);
}

.form-input:hover {
    border-color: var(--border-accent);
}

.form-input:focus {
    outline: none;
    border-color: var(--brand-primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-input::placeholder {
    color: var(--text-tertiary);
}

.form-input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: var(--bg-secondary);
}

/* Input with icon */
.input-group {
    position: relative;
}

.input-icon {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-tertiary);
}

.input-icon-left {
    left: var(--space-4);
}

.input-icon-right {
    right: var(--space-4);
}

.input-with-icon-left {
    padding-left: calc(var(--space-4) + var(--icon-sm) + var(--space-2));
}

.input-with-icon-right {
    padding-right: calc(var(--space-4) + var(--icon-sm) + var(--space-2));
}

/* Error state */
.form-input-error {
    border-color: var(--error);
}

.form-input-error:focus {
    box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
}

.form-error {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-top: var(--space-2);
    font-size: var(--text-sm);
    color: var(--error);
}

/* Success state */
.form-input-success {
    border-color: var(--success);
}

.form-input-success:focus {
    box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
}

.form-success {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    margin-top: var(--space-2);
    font-size: var(--text-sm);
    color: var(--success);
}

/* Hint text */
.form-hint {
    display: block;
    margin-top: var(--space-2);
    font-size: var(--text-sm);
    color: var(--text-tertiary);
}
```

**Select Dropdown:**

```html
<div class="form-group">
    <label class="form-label" for="game">Game</label>
    <div class="select-wrapper">
        <select id="game" class="form-select">
            <option value="">Select a game</option>
            <option value="valorant">VALORANT</option>
            <option value="efootball">eFootball</option>
            <option value="pubgm">PUBG Mobile</option>
            <option value="freefire">Free Fire</option>
        </select>
        <span class="select-icon">
            <svg class="icon-sm"><!-- Chevron down --></svg>
        </span>
    </div>
</div>
```

```css
.select-wrapper {
    position: relative;
}

.form-select {
    width: 100%;
    padding: var(--space-3) calc(var(--space-10)) var(--space-3) var(--space-4);
    font-size: var(--text-base);
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 2px solid var(--border-primary);
    border-radius: var(--radius-base);
    appearance: none;
    cursor: pointer;
    transition: var(--transition-base);
}

.form-select:hover {
    border-color: var(--border-accent);
}

.form-select:focus {
    outline: none;
    border-color: var(--brand-primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.select-icon {
    position: absolute;
    right: var(--space-4);
    top: 50%;
    transform: translateY(-50%);
    pointer-events: none;
    color: var(--text-tertiary);
}
```

**Checkbox & Radio:**

```html
<!-- Checkbox -->
<div class="form-check">
    <input type="checkbox" id="agree" class="form-checkbox">
    <label for="agree" class="form-check-label">
        I agree to the tournament rules
    </label>
</div>

<!-- Radio Group -->
<div class="form-group">
    <label class="form-label">Tournament Format</label>
    <div class="form-radio-group">
        <div class="form-check">
            <input type="radio" id="single" name="format" class="form-radio" checked>
            <label for="single" class="form-check-label">Single Elimination</label>
        </div>
        <div class="form-check">
            <input type="radio" id="double" name="format" class="form-radio">
            <label for="double" class="form-check-label">Double Elimination</label>
        </div>
        <div class="form-check">
            <input type="radio" id="roundrobin" name="format" class="form-radio">
            <label for="roundrobin" class="form-check-label">Round Robin</label>
        </div>
    </div>
</div>
```

```css
.form-check {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    margin-bottom: var(--space-3);
}

.form-checkbox,
.form-radio {
    width: 20px;
    height: 20px;
    border: 2px solid var(--border-primary);
    background: var(--bg-tertiary);
    cursor: pointer;
    transition: var(--transition-base);
}

.form-checkbox {
    border-radius: var(--radius-sm);
}

.form-radio {
    border-radius: 50%;
}

.form-checkbox:checked,
.form-radio:checked {
    background: var(--brand-primary);
    border-color: var(--brand-primary);
}

.form-checkbox:focus,
.form-radio:focus {
    outline: none;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-check-label {
    font-size: var(--text-base);
    color: var(--text-primary);
    cursor: pointer;
}

.form-radio-group {
    display: flex;
    flex-direction: column;
    gap: var(--space-2);
}
```

**Textarea:**

```html
<div class="form-group">
    <label class="form-label" for="description">Tournament Description</label>
    <textarea 
        id="description" 
        class="form-textarea" 
        rows="5" 
        placeholder="Describe your tournament..."
    ></textarea>
    <div class="form-footer">
        <span class="form-hint">Markdown supported</span>
        <span class="form-counter">0 / 500</span>
    </div>
</div>
```

```css
.form-textarea {
    width: 100%;
    padding: var(--space-4);
    font-size: var(--text-base);
    font-family: var(--font-primary);
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border: 2px solid var(--border-primary);
    border-radius: var(--radius-base);
    resize: vertical;
    transition: var(--transition-base);
}

.form-textarea:hover {
    border-color: var(--border-accent);
}

.form-textarea:focus {
    outline: none;
    border-color: var(--brand-primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.form-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: var(--space-2);
}

.form-counter {
    font-size: var(--text-sm);
    color: var(--text-tertiary);
}
```

---

### 4.4 Badges & Tags

```html
<!-- Game Badge -->
<span class="badge badge-game">VALORANT</span>

<!-- Status Badges -->
<span class="badge badge-success">Completed</span>
<span class="badge badge-warning">Pending</span>
<span class="badge badge-error">Cancelled</span>
<span class="badge badge-info">Draft</span>

<!-- Live Badge -->
<span class="badge badge-live">
    <span class="badge-dot"></span>
    LIVE
</span>

<!-- Featured Badge -->
<span class="badge badge-featured">
    <svg class="icon-xs"><!-- Star icon --></svg>
    Featured
</span>

<!-- Counter Badge -->
<button class="btn btn-ghost">
    Notifications
    <span class="badge badge-counter">3</span>
</button>
```

```css
.badge {
    display: inline-flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-1) var(--space-3);
    font-size: var(--text-xs);
    font-weight: var(--font-bold);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-radius: var(--radius-full);
    white-space: nowrap;
}

.badge-game {
    background: rgba(139, 92, 246, 0.2);
    color: var(--brand-secondary);
    border: 1px solid rgba(139, 92, 246, 0.3);
}

.badge-success {
    background: rgba(16, 185, 129, 0.2);
    color: var(--success);
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-warning {
    background: rgba(245, 158, 11, 0.2);
    color: var(--warning);
    border: 1px solid rgba(245, 158, 11, 0.3);
}

.badge-error {
    background: rgba(239, 68, 68, 0.2);
    color: var(--error);
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.badge-info {
    background: rgba(59, 130, 246, 0.2);
    color: var(--info);
    border: 1px solid rgba(59, 130, 246, 0.3);
}

.badge-live {
    background: rgba(6, 182, 212, 0.2);
    color: var(--neon-cyan);
    border: 1px solid var(--neon-cyan);
    box-shadow: var(--glow-live);
    animation: pulse 2s infinite;
}

.badge-featured {
    background: linear-gradient(135deg, #F59E0B 0%, #EC4899 100%);
    color: white;
    border: none;
}

.badge-counter {
    min-width: 20px;
    height: 20px;
    padding: 0 var(--space-2);
    background: var(--error);
    color: white;
    font-size: 11px;
    line-height: 20px;
    text-align: center;
}
```

---

### 4.5 Modal / Dialog

**Accessibility Behavior:**

- **Focus Trap:** Focus must remain within modal while open
- **ESC Key:** Pressing ESC closes the modal
- **Focus Return:** After closing, focus returns to the triggering element
- **ARIA Attributes:** 
  - `role="dialog"`
  - `aria-labelledby` points to modal title
  - `aria-describedby` points to modal description (if present)
  - `aria-hidden="true"` when closed, removed when open
- **Backdrop Click:** Clicking overlay closes modal (configurable)
- **Keyboard Navigation:** Tab cycles through modal elements only

```html
<!-- Modal Overlay -->
<div class="modal-overlay" 
     id="modal-register" 
     aria-hidden="true"
     data-focus-trap="true">
    <div class="modal" 
         role="dialog" 
         aria-labelledby="modal-title"
         aria-describedby="modal-description">
        <!-- Modal Header -->
        <div class="modal-header">
            <h2 class="modal-title" id="modal-title">Register for Tournament</h2>
            <button class="modal-close" 
                    aria-label="Close modal"
                    data-analytics-id="modal_register_close">
                <svg class="icon-base"><!-- X icon --></svg>
            </button>
        </div>
        
        <!-- Modal Body -->
        <div class="modal-body">
            <p>You are about to register for DeltaCrown Valorant Cup 2025.</p>
            
            <div class="alert alert-warning">
                <svg class="icon-sm"><!-- Alert icon --></svg>
                <p>Entry fee of ৳500 will be required after registration.</p>
            </div>
            
            <form>
                <!-- Form fields here -->
            </form>
        </div>
        
        <!-- Modal Footer -->
        <div class="modal-footer">
            <button class="btn btn-ghost">Cancel</button>
            <button class="btn btn-primary">Confirm Registration</button>
        </div>
    </div>
</div>
```

```css
.modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--space-4);
    z-index: 1000;
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-base);
}

.modal-overlay:not([aria-hidden="true"]) {
    opacity: 1;
    pointer-events: auto;
}

.modal {
    width: 100%;
    max-width: 600px;
    max-height: 90vh;
    background: var(--bg-secondary);
    border-radius: var(--radius-xl);
    border: 1px solid var(--border-primary);
    box-shadow: var(--shadow-2xl);
    display: flex;
    flex-direction: column;
    transform: scale(0.95);
    transition: transform var(--duration-base);
}

.modal-overlay:not([aria-hidden="true"]) .modal {
    transform: scale(1);
}

.modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--space-6);
    border-bottom: 1px solid var(--border-secondary);
}

.modal-title {
    font-size: var(--text-2xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
}

.modal-close {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    background: transparent;
    border: none;
    border-radius: var(--radius-base);
    cursor: pointer;
    transition: var(--transition-base);
}

.modal-close:hover {
    background: var(--bg-hover);
    color: var(--text-primary);
}

.modal-body {
    padding: var(--space-6);
    overflow-y: auto;
}

.modal-footer {
    display: flex;
    gap: var(--space-3);
    justify-content: flex-end;
    padding: var(--space-6);
    border-top: 1px solid var(--border-secondary);
}
```

**Modal Accessibility JavaScript:**

```javascript
// Modal focus trap and keyboard management
class ModalManager {
    constructor(modalId) {
        this.modal = document.getElementById(modalId);
        this.overlay = this.modal;
        this.trigger = null; // Store element that opened modal
        this.focusableElements = null;
    }
    
    open(triggerElement) {
        this.trigger = triggerElement; // Remember who opened it
        this.overlay.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden'; // Prevent background scroll
        
        // Get all focusable elements
        this.focusableElements = this.modal.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        
        // Focus first element
        if (this.focusableElements.length > 0) {
            this.focusableElements[0].focus();
        }
        
        // Add event listeners
        this.overlay.addEventListener('keydown', this.handleKeydown.bind(this));
        this.overlay.addEventListener('click', this.handleBackdropClick.bind(this));
    }
    
    close() {
        this.overlay.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = ''; // Restore scroll
        
        // Return focus to trigger element
        if (this.trigger) {
            this.trigger.focus();
        }
        
        // Remove event listeners
        this.overlay.removeEventListener('keydown', this.handleKeydown.bind(this));
        this.overlay.removeEventListener('click', this.handleBackdropClick.bind(this));
    }
    
    handleKeydown(event) {
        // ESC key closes modal
        if (event.key === 'Escape') {
            this.close();
            return;
        }
        
        // TAB key trap focus
        if (event.key === 'Tab') {
            const firstElement = this.focusableElements[0];
            const lastElement = this.focusableElements[this.focusableElements.length - 1];
            
            if (event.shiftKey) {
                // Shift + Tab
                if (document.activeElement === firstElement) {
                    lastElement.focus();
                    event.preventDefault();
                }
            } else {
                // Tab
                if (document.activeElement === lastElement) {
                    firstElement.focus();
                    event.preventDefault();
                }
            }
        }
    }
    
    handleBackdropClick(event) {
        // Close if clicking overlay (not modal content)
        if (event.target === this.overlay) {
            this.close();
        }
    }
}

// Usage
const registerModal = new ModalManager('modal-register');

document.querySelector('[data-open-modal="modal-register"]').addEventListener('click', function(e) {
    registerModal.open(e.target); // Pass trigger element
});

document.querySelector('.modal-close').addEventListener('click', function() {
    registerModal.close();
});
```

---

### 4.6 Navigation Components

**Navbar:**

```html
<nav class="navbar">
    <div class="navbar-container">
        <!-- Logo -->
        <a href="/" class="navbar-logo">
            <img src="logo.svg" alt="DeltaCrown">
        </a>
        
        <!-- Desktop Nav Links -->
        <ul class="navbar-menu">
            <li><a href="/tournaments" class="navbar-link navbar-link-active">Tournaments</a></li>
            <li><a href="/teams" class="navbar-link">Teams</a></li>
            <li><a href="/rankings" class="navbar-link">Rankings</a></li>
            <li><a href="/about" class="navbar-link">About</a></li>
        </ul>
        
        <!-- Actions -->
        <div class="navbar-actions">
            <button class="btn btn-ghost btn-sm">
                <svg class="icon-sm"><!-- Bell icon --></svg>
                <span class="badge badge-counter">3</span>
            </button>
            
            <div class="navbar-profile">
                <img src="avatar.jpg" alt="Player" class="navbar-avatar">
                <span class="navbar-name">Player123</span>
            </div>
        </div>
        
        <!-- Mobile Menu Button -->
        <button class="navbar-toggle" aria-label="Toggle menu">
            <svg class="icon-base"><!-- Menu icon --></svg>
        </button>
    </div>
</nav>
```

```css
.navbar {
    position: sticky;
    top: 0;
    background: var(--bg-primary);
    border-bottom: 1px solid var(--border-primary);
    z-index: 100;
    backdrop-filter: blur(8px);
}

.navbar-container {
    max-width: 1280px;
    margin: 0 auto;
    padding: var(--space-4) var(--space-6);
    display: flex;
    align-items: center;
    gap: var(--space-8);
}

.navbar-logo img {
    height: 40px;
}

.navbar-menu {
    display: none;
    list-style: none;
    margin: 0;
    padding: 0;
    gap: var(--space-2);
}

@media (min-width: 1024px) {
    .navbar-menu {
        display: flex;
        flex: 1;
    }
}

.navbar-link {
    padding: var(--space-2) var(--space-4);
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    text-decoration: none;
    border-radius: var(--radius-base);
    transition: var(--transition-base);
}

.navbar-link:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
}

.navbar-link-active {
    color: var(--brand-primary);
    background: rgba(59, 130, 246, 0.1);
}

.navbar-actions {
    display: flex;
    align-items: center;
    gap: var(--space-4);
    margin-left: auto;
}

.navbar-profile {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-2);
    border-radius: var(--radius-base);
    cursor: pointer;
    transition: var(--transition-base);
}

.navbar-profile:hover {
    background: var(--bg-tertiary);
}

.navbar-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    object-fit: cover;
}

.navbar-name {
    font-weight: var(--font-medium);
    color: var(--text-primary);
}

.navbar-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    background: transparent;
    border: none;
    color: var(--text-primary);
    cursor: pointer;
}

@media (min-width: 1024px) {
    .navbar-toggle {
        display: none;
    }
}
```

**Breadcrumbs:**

```html
<nav class="breadcrumbs" aria-label="Breadcrumb">
    <ol class="breadcrumbs-list">
        <li class="breadcrumbs-item">
            <a href="/" class="breadcrumbs-link">Home</a>
        </li>
        <li class="breadcrumbs-separator">/</li>
        <li class="breadcrumbs-item">
            <a href="/tournaments" class="breadcrumbs-link">Tournaments</a>
        </li>
        <li class="breadcrumbs-separator">/</li>
        <li class="breadcrumbs-item">
            <span class="breadcrumbs-current">DeltaCrown Valorant Cup 2025</span>
        </li>
    </ol>
</nav>
```

```css
.breadcrumbs {
    padding: var(--space-4) 0;
}

.breadcrumbs-list {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    list-style: none;
    margin: 0;
    padding: 0;
}

.breadcrumbs-link {
    font-size: var(--text-sm);
    color: var(--text-secondary);
    text-decoration: none;
    transition: var(--transition-base);
}

.breadcrumbs-link:hover {
    color: var(--brand-primary);
}

.breadcrumbs-separator {
    color: var(--text-tertiary);
    font-size: var(--text-sm);
}

.breadcrumbs-current {
    font-size: var(--text-sm);
    color: var(--text-primary);
    font-weight: var(--font-medium);
}
```

**Tabs:**

```html
<div class="tabs">
    <div class="tabs-header" role="tablist">
        <button class="tab tab-active" role="tab" aria-selected="true" aria-controls="panel-details">
            Details
        </button>
        <button class="tab" role="tab" aria-selected="false" aria-controls="panel-participants">
            Participants
        </button>
        <button class="tab" role="tab" aria-selected="false" aria-controls="panel-bracket">
            Bracket
        </button>
        <button class="tab" role="tab" aria-selected="false" aria-controls="panel-rules">
            Rules
        </button>
    </div>
    
    <div class="tabs-content">
        <div class="tab-panel tab-panel-active" id="panel-details" role="tabpanel">
            <!-- Details content -->
        </div>
        <div class="tab-panel" id="panel-participants" role="tabpanel" hidden>
            <!-- Participants content -->
        </div>
        <div class="tab-panel" id="panel-bracket" role="tabpanel" hidden>
            <!-- Bracket content -->
        </div>
        <div class="tab-panel" id="panel-rules" role="tabpanel" hidden>
            <!-- Rules content -->
        </div>
    </div>
</div>
```

```css
.tabs-header {
    display: flex;
    border-bottom: 2px solid var(--border-secondary);
    overflow-x: auto;
}

.tab {
    padding: var(--space-4) var(--space-6);
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    cursor: pointer;
    white-space: nowrap;
    transition: var(--transition-base);
}

.tab:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
}

.tab-active {
    color: var(--brand-primary);
    border-bottom-color: var(--brand-primary);
}

.tabs-content {
    padding: var(--space-6);
}

.tab-panel {
    display: none;
}

.tab-panel-active {
    display: block;
}
```

---

### 4.7 Loading States

**Spinner:**

```html
<!-- Small Spinner -->
<div class="spinner spinner-sm"></div>

<!-- Base Spinner -->
<div class="spinner"></div>

<!-- Large Spinner -->
<div class="spinner spinner-lg"></div>

<!-- Spinner with Text -->
<div class="loading">
    <div class="spinner"></div>
    <p class="loading-text">Loading tournament data...</p>
</div>
```

```css
.spinner {
    width: 24px;
    height: 24px;
    border: 3px solid rgba(59, 130, 246, 0.2);
    border-top-color: var(--brand-primary);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
}

.spinner-sm {
    width: 16px;
    height: 16px;
    border-width: 2px;
}

.spinner-lg {
    width: 48px;
    height: 48px;
    border-width: 4px;
}

@keyframes spin {
    to { transform: rotate(360deg); }
}

.loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--space-4);
    padding: var(--space-12);
}

.loading-text {
    font-size: var(--text-base);
    color: var(--text-secondary);
}
```

**Skeleton Loader:**

```html
<div class="card">
    <div class="skeleton skeleton-image"></div>
    <div class="card-body">
        <div class="skeleton skeleton-text skeleton-text-lg"></div>
        <div class="skeleton skeleton-text"></div>
        <div class="skeleton skeleton-text skeleton-text-sm"></div>
    </div>
</div>
```

```css
.skeleton {
    background: linear-gradient(
        90deg,
        var(--bg-tertiary) 0%,
        var(--bg-hover) 50%,
        var(--bg-tertiary) 100%
    );
    background-size: 200% 100%;
    animation: skeleton-loading 1.5s ease-in-out infinite;
    border-radius: var(--radius-base);
}

.skeleton-image {
    aspect-ratio: 16/9;
    width: 100%;
}

.skeleton-text {
    height: 1em;
    margin-bottom: var(--space-3);
}

.skeleton-text-sm {
    width: 60%;
}

.skeleton-text-lg {
    height: 1.5em;
}

@keyframes skeleton-loading {
    0% {
        background-position: 200% 0;
    }
    100% {
        background-position: -200% 0;
    }
}
```

**Progress Bar:**

```html
<div class="progress">
    <div class="progress-bar" style="width: 65%;" role="progressbar" aria-valuenow="65" aria-valuemin="0" aria-valuemax="100">
        <span class="progress-label">65%</span>
    </div>
</div>

<!-- With label outside -->
<div class="progress-group">
    <div class="progress-header">
        <span class="progress-title">Registration Progress</span>
        <span class="progress-value">13 / 32 teams</span>
    </div>
    <div class="progress">
        <div class="progress-bar progress-bar-success" style="width: 40%;"></div>
    </div>
</div>
```

```css
.progress {
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-full);
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background: var(--brand-primary);
    border-radius: var(--radius-full);
    transition: width var(--duration-slow) ease-out;
    position: relative;
}

.progress-bar-success {
    background: var(--success);
}

.progress-bar-warning {
    background: var(--warning);
}

.progress-bar-error {
    background: var(--error);
}

.progress-label {
    position: absolute;
    right: var(--space-2);
    top: 50%;
    transform: translateY(-50%);
    font-size: var(--text-xs);
    font-weight: var(--font-bold);
    color: white;
}

.progress-group {
    width: 100%;
}

.progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--space-2);
}

.progress-title {
    font-size: var(--text-sm);
    font-weight: var(--font-medium);
    color: var(--text-primary);
}

.progress-value {
    font-size: var(--text-sm);
    color: var(--text-secondary);
}
```

---

### 4.8 Toast Notifications

```html
<!-- Toast Container -->
<div class="toast-container" aria-live="polite">
    <!-- Success Toast -->
    <div class="toast toast-success">
        <div class="toast-icon">
            <svg class="icon-sm"><!-- Check circle icon --></svg>
        </div>
        <div class="toast-content">
            <p class="toast-title">Registration Successful</p>
            <p class="toast-message">You have successfully registered for the tournament.</p>
        </div>
        <button class="toast-close" aria-label="Close">
            <svg class="icon-sm"><!-- X icon --></svg>
        </button>
    </div>
    
    <!-- Error Toast -->
    <div class="toast toast-error">
        <div class="toast-icon">
            <svg class="icon-sm"><!-- Alert circle icon --></svg>
        </div>
        <div class="toast-content">
            <p class="toast-title">Payment Failed</p>
            <p class="toast-message">Unable to process your payment. Please try again.</p>
        </div>
        <button class="toast-close" aria-label="Close">
            <svg class="icon-sm"><!-- X icon --></svg>
        </button>
    </div>
</div>
```

```css
.toast-container {
    position: fixed;
    top: var(--space-4);
    right: var(--space-4);
    z-index: 1100;
    display: flex;
    flex-direction: column;
    gap: var(--space-3);
    max-width: 400px;
}

.toast {
    display: flex;
    align-items: flex-start;
    gap: var(--space-4);
    padding: var(--space-4);
    background: var(--bg-secondary);
    border-radius: var(--radius-lg);
    border: 1px solid var(--border-primary);
    box-shadow: var(--shadow-xl);
    animation: toast-slide-in var(--duration-base) ease-out;
}

@keyframes toast-slide-in {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

.toast-success {
    border-left: 4px solid var(--success);
}

.toast-success .toast-icon {
    color: var(--success);
}

.toast-error {
    border-left: 4px solid var(--error);
}

.toast-error .toast-icon {
    color: var(--error);
}

.toast-warning {
    border-left: 4px solid var(--warning);
}

.toast-warning .toast-icon {
    color: var(--warning);
}

.toast-info {
    border-left: 4px solid var(--info);
}

.toast-info .toast-icon {
    color: var(--info);
}

.toast-content {
    flex: 1;
}

.toast-title {
    font-size: var(--text-base);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-1);
}

.toast-message {
    font-size: var(--text-sm);
    color: var(--text-secondary);
}

.toast-close {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: var(--text-tertiary);
    cursor: pointer;
    transition: var(--transition-base);
}

.toast-close:hover {
    color: var(--text-primary);
}
```

---

### 4.9 Alert / Banner

```html
<!-- Info Alert -->
<div class="alert alert-info">
    <svg class="alert-icon"><!-- Info icon --></svg>
    <div class="alert-content">
        <p class="alert-title">Tournament Format Updated</p>
        <p class="alert-message">The tournament format has been changed to double elimination.</p>
    </div>
    <button class="alert-close" aria-label="Close">
        <svg class="icon-sm"><!-- X icon --></svg>
    </button>
</div>

<!-- Success Alert -->
<div class="alert alert-success">
    <svg class="alert-icon"><!-- Check circle icon --></svg>
    <p>Your payment has been verified by the organizer.</p>
</div>

<!-- Warning Alert -->
<div class="alert alert-warning">
    <svg class="alert-icon"><!-- Alert triangle icon --></svg>
    <p>Check-in required within 30 minutes or your registration will be cancelled.</p>
</div>

<!-- Error Alert -->
<div class="alert alert-error">
    <svg class="alert-icon"><!-- X circle icon --></svg>
    <p>You have been disqualified for violating tournament rules.</p>
</div>
```

```css
.alert {
    display: flex;
    align-items: flex-start;
    gap: var(--space-4);
    padding: var(--space-4);
    border-radius: var(--radius-lg);
    border: 1px solid;
}

.alert-info {
    background: rgba(59, 130, 246, 0.1);
    border-color: rgba(59, 130, 246, 0.3);
    color: var(--info);
}

.alert-success {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.3);
    color: var(--success);
}

.alert-warning {
    background: rgba(245, 158, 11, 0.1);
    border-color: rgba(245, 158, 11, 0.3);
    color: var(--warning);
}

.alert-error {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.3);
    color: var(--error);
}

.alert-icon {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
}

.alert-content {
    flex: 1;
}

.alert-title {
    font-weight: var(--font-semibold);
    margin-bottom: var(--space-1);
    color: var(--text-primary);
}

.alert-message {
    font-size: var(--text-sm);
    color: var(--text-secondary);
}

.alert-close {
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: transparent;
    border: none;
    color: inherit;
    opacity: 0.7;
    cursor: pointer;
    transition: var(--transition-base);
}

.alert-close:hover {
    opacity: 1;
}
```

---

### 4.10 Dropdown Menu

```html
<div class="dropdown">
    <button class="dropdown-trigger btn btn-ghost">
        <span>Options</span>
        <svg class="icon-sm"><!-- Chevron down icon --></svg>
    </button>
    
    <div class="dropdown-menu" hidden>
        <a href="#" class="dropdown-item">
            <svg class="icon-sm"><!-- Edit icon --></svg>
            <span>Edit Tournament</span>
        </a>
        <a href="#" class="dropdown-item">
            <svg class="icon-sm"><!-- Copy icon --></svg>
            <span>Duplicate</span>
        </a>
        <div class="dropdown-divider"></div>
        <a href="#" class="dropdown-item dropdown-item-danger">
            <svg class="icon-sm"><!-- Trash icon --></svg>
            <span>Delete</span>
        </a>
    </div>
</div>
```

```css
.dropdown {
    position: relative;
    display: inline-block;
}

.dropdown-trigger {
    display: flex;
    align-items: center;
    gap: var(--space-2);
}

.dropdown-menu {
    position: absolute;
    top: calc(100% + var(--space-2));
    right: 0;
    min-width: 200px;
    background: var(--bg-tertiary);
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-xl);
    padding: var(--space-2);
    z-index: 100;
    animation: dropdown-appear var(--duration-fast) ease-out;
}

@keyframes dropdown-appear {
    from {
        opacity: 0;
        transform: translateY(-8px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.dropdown-item {
    display: flex;
    align-items: center;
    gap: var(--space-3);
    padding: var(--space-3) var(--space-4);
    font-size: var(--text-base);
    color: var(--text-primary);
    text-decoration: none;
    border-radius: var(--radius-base);
    transition: var(--transition-base);
    cursor: pointer;
}

.dropdown-item:hover {
    background: var(--bg-hover);
}

.dropdown-item-danger {
    color: var(--error);
}

.dropdown-item-danger:hover {
    background: rgba(239, 68, 68, 0.1);
}

.dropdown-divider {
    height: 1px;
    background: var(--border-secondary);
    margin: var(--space-2) 0;
}
```

---

### 4.11 Pagination

```html
<nav class="pagination" aria-label="Pagination">
    <button class="pagination-btn pagination-prev" disabled>
        <svg class="icon-sm"><!-- Chevron left icon --></svg>
        <span>Previous</span>
    </button>
    
    <ul class="pagination-list">
        <li>
            <a href="#" class="pagination-link pagination-link-active" aria-current="page">1</a>
        </li>
        <li>
            <a href="#" class="pagination-link">2</a>
        </li>
        <li>
            <a href="#" class="pagination-link">3</a>
        </li>
        <li>
            <span class="pagination-ellipsis">...</span>
        </li>
        <li>
            <a href="#" class="pagination-link">10</a>
        </li>
    </ul>
    
    <button class="pagination-btn pagination-next">
        <span>Next</span>
        <svg class="icon-sm"><!-- Chevron right icon --></svg>
    </button>
</nav>
```

```css
.pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-3);
    padding: var(--space-6) 0;
}

.pagination-list {
    display: flex;
    gap: var(--space-2);
    list-style: none;
    margin: 0;
    padding: 0;
}

.pagination-link,
.pagination-btn {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--space-2);
    min-width: 40px;
    height: 40px;
    padding: var(--space-2) var(--space-3);
    font-size: var(--text-base);
    font-weight: var(--font-medium);
    color: var(--text-secondary);
    background: transparent;
    border: 1px solid var(--border-primary);
    border-radius: var(--radius-base);
    text-decoration: none;
    cursor: pointer;
    transition: var(--transition-base);
}

.pagination-link:hover,
.pagination-btn:hover {
    color: var(--text-primary);
    background: var(--bg-tertiary);
    border-color: var(--border-accent);
}

.pagination-link-active {
    color: var(--text-primary);
    background: var(--brand-primary);
    border-color: var(--brand-primary);
}

.pagination-link-active:hover {
    background: #2563EB;
}

.pagination-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    pointer-events: none;
}

.pagination-ellipsis {
    display: flex;
    align-items: center;
    justify-content: center;
    min-width: 40px;
    height: 40px;
    color: var(--text-tertiary);
}
```

---

### 4.12 Tooltip / Popover

```html
<!-- Tooltip -->
<button class="btn btn-ghost" data-tooltip="Delete tournament">
    <svg class="icon-base"><!-- Trash icon --></svg>
</button>

<!-- Tooltip implementation -->
<div class="tooltip" role="tooltip" hidden>
    Delete tournament
</div>
```

```css
[data-tooltip] {
    position: relative;
}

[data-tooltip]::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: calc(100% + var(--space-2));
    left: 50%;
    transform: translateX(-50%);
    padding: var(--space-2) var(--space-3);
    background: var(--bg-primary);
    color: var(--text-primary);
    font-size: var(--text-sm);
    white-space: nowrap;
    border-radius: var(--radius-base);
    border: 1px solid var(--border-primary);
    box-shadow: var(--shadow-lg);
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-fast);
    z-index: 1000;
}

[data-tooltip]::before {
    content: '';
    position: absolute;
    bottom: calc(100% + var(--space-2) - 6px);
    left: 50%;
    transform: translateX(-50%);
    border: 6px solid transparent;
    border-top-color: var(--border-primary);
    opacity: 0;
    pointer-events: none;
    transition: opacity var(--duration-fast);
    z-index: 1001;
}

[data-tooltip]:hover::after,
[data-tooltip]:hover::before {
    opacity: 1;
}
```

---

### 4.13 Empty States

```html
<div class="empty-state">
    <div class="empty-state-icon">
        <svg class="icon-xl"><!-- Trophy icon --></svg>
    </div>
    <h3 class="empty-state-title">No tournaments found</h3>
    <p class="empty-state-message">
        There are no active tournaments matching your filters. Try adjusting your search criteria.
    </p>
    <button class="btn btn-primary">
        Create Tournament
    </button>
</div>
```

```css
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-16);
    text-align: center;
}

.empty-state-icon {
    width: 80px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: 50%;
    color: var(--text-tertiary);
    margin-bottom: var(--space-6);
}

.empty-state-title {
    font-size: var(--text-2xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-3);
}

.empty-state-message {
    font-size: var(--text-base);
    color: var(--text-secondary);
    max-width: 400px;
    margin-bottom: var(--space-6);
}
```

---

### 4.14 Error & Edge States (Comprehensive Templates)

**Purpose:** Explicit designs for failure scenarios, preventing user confusion.

**1. No Internet Connection / Offline**

```html
<div class="error-state error-state-offline">
    <div class="error-icon">
        <svg class="icon-xl"><!-- WiFi off icon --></svg>
    </div>
    <h3 class="error-title">No Internet Connection</h3>
    <p class="error-message">
        You're currently offline. Some features may not be available.
    </p>
    <div class="error-actions">
        <button class="btn btn-primary" onclick="location.reload()">
            Retry Connection
        </button>
    </div>
    <div class="error-info">
        <p class="text-sm text-secondary">
            Your actions will be saved and synced when connection is restored.
        </p>
    </div>
</div>
```

**HTMX Offline Handling:**
```javascript
// Queue actions when offline
document.body.addEventListener('htmx:sendError', (event) => {
    if (!navigator.onLine) {
        // Queue request for retry
        queueOfflineAction(event.detail);
        showToast('Action queued. Will sync when online.', 'info');
    }
});
```

**2. Server Error (500, Bracket Load Failure)**

```html
<div class="error-state error-state-server">
    <div class="error-icon error-icon-danger">
        <svg class="icon-xl"><!-- Alert triangle icon --></svg>
    </div>
    <h3 class="error-title">Unable to Load Bracket</h3>
    <p class="error-message">
        We're experiencing technical difficulties. Please try again in a moment.
    </p>
    <div class="error-actions">
        <button class="btn btn-primary" onclick="location.reload()">
            <svg class="icon-sm"><!-- Refresh icon --></svg>
            Retry
        </button>
        <button class="btn btn-secondary" onclick="contactSupport()">
            Contact Support
        </button>
    </div>
    <details class="error-details">
        <summary>Technical Details</summary>
        <code>Error ID: ERR-500-ABC123<br>Timestamp: 2025-11-03 10:30:45 BST</code>
    </details>
</div>
```

**3. Payment File Validation Errors**

```html
<!-- File Too Large -->
<div class="alert alert-error">
    <svg class="alert-icon"><!-- X circle icon --></svg>
    <div class="alert-content">
        <p class="alert-title">File Too Large</p>
        <p class="alert-message">
            Your file (7.2 MB) exceeds the maximum size of 5 MB.
            <a href="/help/compress-images" class="alert-link">Learn how to compress images</a>
        </p>
    </div>
    <button class="btn btn-sm btn-ghost">
        Choose Different File
    </button>
</div>

<!-- Invalid File Format -->
<div class="alert alert-error">
    <svg class="alert-icon"><!-- X circle icon --></svg>
    <div class="alert-content">
        <p class="alert-title">Invalid File Format</p>
        <p class="alert-message">
            File type ".txt" is not supported. Please upload JPG, PNG, or PDF.
            <a href="/examples/payment-screenshot" class="alert-link">View example screenshot</a>
        </p>
    </div>
</div>

<!-- Corrupted File -->
<div class="alert alert-error">
    <svg class="alert-icon"><!-- X circle icon --></svg>
    <div class="alert-content">
        <p class="alert-title">Unable to Read File</p>
        <p class="alert-message">
            The file appears to be corrupted or damaged. Please try uploading a different file.
        </p>
    </div>
    <button class="btn btn-sm btn-ghost">
        Try Again
    </button>
</div>
```

**Sample Screenshot Preview Link:**
- Opens modal with annotated example
- Shows required elements: Transaction ID, Amount, Date/Time
- Highlights acceptable and unacceptable screenshots

**4. Zero States (No Data Yet)**

```html
<!-- No Tournaments Created Yet (Organizer Dashboard) -->
<div class="empty-state">
    <div class="empty-state-icon">
        <svg class="icon-xl"><!-- Sparkles icon --></svg>
    </div>
    <h3 class="empty-state-title">Create Your First Tournament</h3>
    <p class="empty-state-message">
        You haven't created any tournaments yet. Get started by creating your first tournament and inviting players!
    </p>
    <button class="btn btn-primary btn-lg">
        <svg class="icon-sm"><!-- Plus icon --></svg>
        Create Tournament
    </button>
</div>

<!-- No Matches Yet (Live Matches Section) -->
<div class="empty-state">
    <div class="empty-state-icon">
        <svg class="icon-xl"><!-- Clock icon --></svg>
    </div>
    <h3 class="empty-state-title">No Live Matches</h3>
    <p class="empty-state-message">
        There are no matches in progress right now. Check back when the tournament starts!
    </p>
</div>

<!-- No Certificates Yet (Player Dashboard) -->
<div class="empty-state">
    <div class="empty-state-icon">
        <svg class="icon-xl"><!-- Award icon --></svg>
    </div>
    <h3 class="empty-state-title">No Certificates Yet</h3>
    <p class="empty-state-message">
        Earn certificates by participating in tournaments and achieving top placements!
    </p>
    <button class="btn btn-secondary">
        Browse Tournaments
    </button>
</div>
```

**5. Permission Denied (Access Control)**

```html
<div class="error-state error-state-forbidden">
    <div class="error-icon error-icon-warning">
        <svg class="icon-xl"><!-- Lock icon --></svg>
    </div>
    <h3 class="error-title">Access Restricted</h3>
    <p class="error-message">
        You don't have permission to view this page. This tournament may be private or you may need to log in.
    </p>
    <div class="error-actions">
        <button class="btn btn-primary" onclick="window.location='/login'">
            Sign In
        </button>
        <button class="btn btn-ghost" onclick="history.back()">
            Go Back
        </button>
    </div>
</div>
```

**Error State Styles:**

```css
.error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--space-16);
    text-align: center;
    min-height: 400px;
}

.error-icon {
    width: 80px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-tertiary);
    border-radius: 50%;
    color: var(--text-tertiary);
    margin-bottom: var(--space-6);
}

.error-icon-danger {
    background: rgba(239, 68, 68, 0.1);
    color: var(--error);
}

.error-icon-warning {
    background: rgba(245, 158, 11, 0.1);
    color: var(--warning);
}

.error-title {
    font-size: var(--text-2xl);
    font-weight: var(--font-semibold);
    color: var(--text-primary);
    margin-bottom: var(--space-3);
}

.error-message {
    font-size: var(--text-base);
    color: var(--text-secondary);
    max-width: 400px;
    margin-bottom: var(--space-6);
}

.error-actions {
    display: flex;
    gap: var(--space-3);
    margin-bottom: var(--space-6);
}

.error-info {
    padding: var(--space-4);
    background: var(--bg-tertiary);
    border-radius: var(--radius-lg);
    max-width: 400px;
}

.error-details {
    margin-top: var(--space-4);
    padding: var(--space-4);
    background: var(--bg-tertiary);
    border-radius: var(--radius-base);
    text-align: left;
}

.error-details summary {
    cursor: pointer;
    font-size: var(--text-sm);
    color: var(--text-secondary);
    margin-bottom: var(--space-2);
}

.error-details code {
    font-family: var(--font-mono);
    font-size: var(--text-xs);
    color: var(--text-tertiary);
}
```

---

## Component Library Summary

✅ **20+ Components Documented:**

1. **Buttons** - Primary, secondary, ghost, danger, loading, sizes
2. **Cards** - Tournament card, match card with live states
3. **Form Elements** - Input, select, checkbox, radio, textarea with validation states
4. **Badges & Tags** - Game badges, status badges, live indicators, counters
5. **Modal / Dialog** - Overlay, header, body, footer with animations
6. **Navigation** - Navbar, breadcrumbs
7. **Tabs** - Tab navigation with ARIA support
8. **Loading States** - Spinner, skeleton loader, progress bar
9. **Toast Notifications** - Success, error, warning, info with animations
10. **Alert / Banner** - Inline alerts with variants
11. **Dropdown Menu** - Context menus with dividers
12. **Pagination** - Page navigation with ellipsis
13. **Tooltip / Popover** - Hover hints with positioning
14. **Empty States** - No data placeholders

**Each component includes:**
- HTML structure with semantic markup
- Complete CSS with custom properties
- Accessibility features (ARIA labels, keyboard support)
- Responsive behavior
- Hover/focus states
- Animation specifications

---

## 5. Tournament Management Screens

### 5.1 Tournament Listing Page

**Purpose:** Browse and discover active, upcoming, and past tournaments with filtering and search capabilities.

**URL:** `/tournaments`

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Hero Section                                            │
│  - Heading: "Discover Tournaments"                      │
│  - Search bar (prominent)                               │
│  - Quick filter chips (Live, Upcoming, Popular)         │
├────────────────────────────────────────────────────────┤
│ Filters (Sidebar)      │ Tournament Grid                │
│  - Game                │  ┌─────┐ ┌─────┐ ┌─────┐      │
│  - Date Range          │  │ Card│ │ Card│ │ Card│      │
│  - Prize Pool          │  └─────┘ └─────┘ └─────┘      │
│  - Status              │  ┌─────┐ ┌─────┐ ┌─────┐      │
│  - Entry Fee           │  │ Card│ │ Card│ │ Card│      │
│  - Format              │  └─────┘ └─────┘ └─────┘      │
│                        │  [Load More]                   │
└────────────────────────────────────────────────────────┘
```

**Key Features:**

1. **Hero Search Section**
   - Large search input with autocomplete
   - Voice search icon (future enhancement)
   - Quick filter chips: "Live Now" (with pulsing red dot), "Starting Soon", "High Prize Pool"
   - Trending games carousel

2. **Sidebar Filters**
   - **Game Selection:** Checkboxes with game icons (VALORANT, eFootball, PUBG Mobile, etc.)
   - **Date Range:** Calendar picker with presets (Today, This Week, This Month)
   - **Prize Pool:** Range slider (৳0 - ৳100,000+)
   - **Status:** Radio buttons (All, Registration Open, Ongoing, Completed)
   - **Entry Fee:** Checkboxes (Free, ৳0-500, ৳500-1000, ৳1000+)
   - **Format:** Checkboxes (Single Elimination, Double Elimination, Round Robin)
   - **Reset Filters** button at bottom

3. **Tournament Grid**
   - 3-column grid on desktop (1 column mobile, 2 columns tablet)
   - Tournament cards with:
     - Banner image with live badge overlay
     - Game badge and date
     - Tournament title
     - Stats (teams, prize pool, registered count)
     - Progress bar showing registration status
     - Primary CTA: "Register Now" or "View Details"
   - Sort dropdown (top-right): "Relevance", "Start Date", "Prize Pool", "Participants"

4. **Empty State**
   - Trophy icon
   - "No tournaments found"
   - "Try adjusting your filters or create your own tournament"
   - "Create Tournament" button

**Responsive Behavior:**

- **Desktop (1024px+):** Sidebar + 3-column grid
- **Tablet (768px-1023px):** Collapsible sidebar + 2-column grid
- **Mobile (<768px):** Bottom sheet filters + 1-column grid

**Interactions:**

- Hover on card: Lift effect (4px translateY) + border glow
- Click "Register Now": Opens registration modal (if logged in) or redirects to login
- Click card anywhere else: Navigate to tournament detail page
- Scroll infinite: Auto-load more tournaments (with skeleton loaders)

**HTMX Integration:**

```html
<!-- Infinite scroll -->
<div 
    hx-get="/tournaments?page=2" 
    hx-trigger="revealed" 
    hx-swap="afterend"
    class="loading-trigger"
>
    <div class="spinner"></div>
</div>

<!-- Filter update -->
<form 
    hx-get="/tournaments/filter" 
    hx-trigger="change" 
    hx-target="#tournament-grid"
    hx-swap="innerHTML"
>
    <!-- Filter inputs -->
</form>
```

---

### 5.2 Tournament Detail Page

**Purpose:** Comprehensive view of a single tournament with all information, registration, and live updates.

**URL:** `/tournaments/<tournament-slug>`

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Hero Section (Full-width banner)                        │
│  - Background: Tournament banner image                  │
│  - Overlay gradient                                     │
│  - Game badge, Live badge (if applicable)               │
│  - Tournament title (H1)                                │
│  - Organizer info (avatar, name, verified badge)        │
│  - Primary CTA: "Register Now" (prominent)              │
├────────────────────────────────────────────────────────┤
│ Breadcrumbs: Home / Tournaments / [Tournament Name]     │
├────────────────────────────────────────────────────────┤
│ Stats Cards (4 columns, responsive)                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 32 Teams │ │ ৳50,000  │ │ Dec 15   │ │ 16/32    │  │
│  │ Capacity │ │ Prize    │ │ Start    │ │ Registered│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├────────────────────────────────────────────────────────┤
│ Tabs Navigation                                         │
│  [Details] [Participants] [Bracket] [Rules] [Sponsors] │
├────────────────────────────────────────────────────────┤
│ Tab Content Area                                        │
│  (Details, Participants, Bracket, Rules, or Sponsors)   │
├────────────────────────────────────────────────────────┤
│ Sidebar (Desktop only)                                  │
│  - Quick Actions card                                   │
│  - Timeline card                                        │
│  - Sponsors card                                        │
│  - Share buttons                                        │
└────────────────────────────────────────────────────────┘
```

**Tab 1: Details**

Content:
- **Description** (rich text with markdown support)
- **Format Information:** Single Elimination, Best of 3
- **Entry Fee:** ৳500 (or "Free Entry" or "500 DC" if DeltaCoin enabled)
- **Prize Distribution:**
  ```
  🥇 1st Place: ৳25,000
  🥈 2nd Place: ৳15,000
  🥉 3rd Place: ৳10,000
  ```
- **Check-in Window:** 30 minutes before start
- **Custom Fields:** (if defined by organizer)
  - In-Game Username
  - Team Discord Server
  - etc.
- **Contact Organizer:** Button (prominent, always visible, opens message modal)

**Tab 2: Participants**

Content:
- Search/filter participants
- Grid of participant cards:
  - Team logo
  - Team name
  - **"✓ Verified Winner"** chip (if certificate issued for past tournaments)
  - Rank/seed (if applicable)
  - Registration date
  - Payment status (for organizer only)
  - Past placement badges (🥇, 🥈, 🥉 with count)
- Total count: "16 / 32 teams registered"
- Export list button (organizer only)

**Tab 3: Bracket**

Content:
- Interactive bracket visualization (SVG-based)
- Zoom/pan controls
- Match cards within bracket nodes
- Highlight user's team path
- Real-time updates (WebSocket)
- Download bracket image button

**Tab 4: Rules**

Content:
- Formatted rules text (markdown) — stored in `Tournament.rules_text` field
- Sections:
  - Eligibility
  - Match Rules
  - Conduct & Fair Play
  - Disputes
  - Anti-Cheat Requirements
- Accept rules checkbox (for registration)

**Field Name Convention:** UI displays "Rules" but API/database field is `rules_text` (consistent with Part 2 & 3)

**Tab 5: Sponsors**

Content:
- Sponsor logos with links
- Sponsor tier badges (Platinum, Gold, Silver, Bronze)
- Click to view sponsor profile

**Sidebar Cards:**

1. **Quick Actions**
   - Register button (primary)
   - Save tournament (bookmark icon)
   - Share (dropdown: Facebook, Twitter, Discord, Copy Link)
   - Report tournament (flag icon)
   - **Contact Organizer** (message icon, opens dialog)

2. **Timeline**
   - Registration Opens: Dec 1, 2025
   - Registration Closes: Dec 14, 2025
   - Check-in: Dec 15, 2025 (9:30 AM)
   - Tournament Start: Dec 15, 2025 (10:00 AM)
   - Visual progress indicator

3. **Organizer Card**
   - Avatar, name, verified badge
   - Rating: ⭐ 4.8 (120 reviews)
   - "View Profile" link
   - **"Contact Organizer"** button (primary action, opens message modal)

**Contact Organizer Modal:**
- Pre-filled subject: "Question about [Tournament Name]"
- Message textarea
- Send button (creates notification for organizer + optional email)
- Response time estimate: "Usually responds within 24 hours"

---

#### Contact Organizer Placement Hierarchy

**Purpose:** Ensure "Contact Organizer" button is accessible at every critical touchpoint where users may need support or clarification.

**Primary Placements (Always Visible):**

```
┌────────────────────────────────────────────────────────┐
│ 1. Tournament Detail Page - Organizer Card             │
│    Location: Right sidebar (desktop) / Bottom (mobile) │
│    Visual: Primary button with message icon            │
│    Priority: HIGH - Primary support channel             │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 2. Tournament Header Bar                                │
│    Location: Top-right corner, next to Register button │
│    Visual: Ghost button with envelope icon 💬          │
│    Priority: MEDIUM - Quick access without scrolling    │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 3. Registration Form Footer                             │
│    Location: Below form fields, before Submit button    │
│    Visual: Ghost button, left-aligned                   │
│    Text: "Need help? Contact Organizer"                │
│    Priority: HIGH - Registration assistance             │
└────────────────────────────────────────────────────────┘
```

**Contextual Placements (Conditional):**

```
┌────────────────────────────────────────────────────────┐
│ 4. Payment Rejection Notice                            │
│    Trigger: Payment status = "Rejected"                │
│    Visual: Primary button in error alert                │
│    Text: "Contact Organizer" (discuss rejection)       │
│    Pre-fill: Subject "Payment Rejection Inquiry"       │
│    Priority: CRITICAL - Dispute resolution              │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 5. Payment Expiration Alert                            │
│    Trigger: Payment deadline passed, status "Expired"  │
│    Visual: Secondary button in warning alert            │
│    Text: "Request Extension"                           │
│    Pre-fill: Subject "Payment Extension Request"       │
│    Priority: HIGH - Time-sensitive resolution           │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 6. Check-In Missed Alert                               │
│    Trigger: User missed check-in deadline              │
│    Visual: Secondary button in error state              │
│    Text: "Contact Organizer" (appeal disqualification) │
│    Pre-fill: Subject "Check-in Missed Appeal"          │
│    Priority: HIGH - Last chance to resolve              │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ 7. Match Dispute Panel                                 │
│    Trigger: User clicks "Dispute Result"               │
│    Visual: Ghost button below evidence upload          │
│    Text: "Escalate to Organizer"                       │
│    Pre-fill: Subject "Match Result Dispute - [Match]"  │
│    Priority: MEDIUM - Formal dispute process            │
└────────────────────────────────────────────────────────┘
```

**Visual Hierarchy Reference:**

```
Tournament Detail Page (Desktop):
┌────────────────────────────────────────────────────────┐
│ Header Bar: [💬 Contact Organizer]         [Register] │ ← Ghost button
├────────────────────────────────────────────────────────┤
│ Main Content        │ Sidebar                          │
│                     │ ┌─────────────────────────────┐  │
│                     │ │ Organizer Card              │  │
│                     │ │ 👤 JohnDoe                  │  │
│                     │ │ ⭐ 4.8 (120 reviews)        │  │
│                     │ │ [Contact Organizer] ←───────┼──┼ Primary button
│                     │ │ [View Profile]              │  │
│                     │ └─────────────────────────────┘  │
└────────────────────────────────────────────────────────┘

Registration Form:
┌────────────────────────────────────────────────────────┐
│ [Team Name Input]                                      │
│ [Player Fields...]                                     │
│ [Custom Fields...]                                     │
├────────────────────────────────────────────────────────┤
│ Footer Actions:                                        │
│ [Need help? Contact Organizer] ←────── [Submit Entry] │ ← Left-aligned ghost
└────────────────────────────────────────────────────────┘

Payment Rejected State:
┌────────────────────────────────────────────────────────┐
│ ❌ Payment Rejected                                    │
│ Reason: Invalid transaction ID format                  │
│ Please review and resubmit your payment proof.         │
│ [Resubmit Payment] [Contact Organizer] ←───────────────┼ Primary action
└────────────────────────────────────────────────────────┘
```

**Button Styling by Context:**

| Location | Style | Icon | Color | Size |
|----------|-------|------|-------|------|
| Organizer Card | `btn-primary` | 💬 | Blue | Large (full-width) |
| Header Bar | `btn-ghost` | 💬 | Gray | Medium |
| Form Footer | `btn-ghost` | None | Gray | Small |
| Error Alerts | `btn-primary` | None | Blue | Medium |
| Warning Alerts | `btn-secondary` | ⚠️ | Amber | Medium |

**Mobile Optimization:**

- **Tournament Page:** Fixed bottom bar (sticky)
  ```
  ┌────────────────────────────────────────┐
  │ [Contact Organizer] [Register Now]     │ ← 50/50 split
  └────────────────────────────────────────┘
  ```
- **Registration Form:** Inline with submit button (stacked on small screens)
- **Alerts:** Full-width buttons (stacked vertically)

**Analytics Tracking:**

```html
<!-- All Contact Organizer buttons use consistent ID pattern -->
<button data-analytics-id="dc-contact-organizer-{context}" 
        data-tournament-id="{{ tournament.id }}"
        data-context="header|sidebar|registration|payment_rejected|check_in_missed|dispute">
    Contact Organizer
</button>
```

**Context Values:**
- `header` - Header bar placement
- `sidebar` - Organizer card placement
- `registration` - Registration form footer
- `payment_rejected` - Payment rejection alert
- `payment_expired` - Payment expiration alert
- `check_in_missed` - Check-in failure alert
- `dispute` - Match dispute panel

**Live Updates (WebSocket):**

When tournament status changes:
- Registration count updates in real-time
- Live badge appears when tournament starts
- Match results update bracket immediately
- Toast notifications for important events

**Responsive Behavior:**

- **Desktop:** Sidebar visible, 8-column main + 4-column sidebar
- **Tablet/Mobile:** Sidebar content moved to bottom sections

**CTA States:**

- **Before Registration Opens:** "Notify Me" button
- **Registration Open:** "Register Now" (blue, glowing)
- **Registration Full:** "Waitlist" button
- **Registration Closed:** "Registration Closed" (gray, disabled)
- **User Registered:** "Registered ✓" (green) + "Manage Registration" button

---

### 5.3 Tournament Creation Wizard

**Purpose:** Multi-step form for organizers to create and publish tournaments.

**URL:** `/tournaments/create`

**Access:** Requires authentication + organizer permissions

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Progress Header                                         │
│  [1. Basic Info] → [2. Format] → [3. Rules] → [4. Preview]│
│  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  25%          │
├────────────────────────────────────────────────────────┤
│ Form Area (centered, max-width 800px)                   │
│  ┌────────────────────────────────────────────────┐    │
│  │ Step Content                                    │    │
│  │ (Form fields for current step)                  │    │
│  │                                                 │    │
│  │                                                 │    │
│  │                                                 │    │
│  └────────────────────────────────────────────────┘    │
├────────────────────────────────────────────────────────┤
│ Footer Actions                                          │
│  [← Back]                    [Save Draft] [Next →]     │
└────────────────────────────────────────────────────────┘
```

**Step 1: Basic Information**

Fields:
- **Tournament Name*** (text input, 60 char max)
  - Real-time availability check
  - Slug preview: `/tournaments/deltacrown-valorant-cup-2025`
- **Game*** (dropdown with search)
  - VALORANT, eFootball, PUBG Mobile, Free Fire, MLBB, CS2, Dota 2, EA Sports FC
- **Banner Image*** (file upload)
  - Recommended: 1920x1080px
  - Drag-and-drop area
  - Image preview with crop tool
- **Description*** (rich text editor)
  - Markdown toolbar
  - Character count: 0/2000
  - Preview button
- **Start Date & Time*** (datetime picker)
  - Timezone: Bangladesh Standard Time (BST)
  - Minimum: 24 hours from now
- **Organizer Name** (auto-filled from profile, editable)
- **Contact Email*** (auto-filled, editable)
- **Discord Server** (optional URL)

Validation:
- All required fields marked with *
- Real-time validation with inline errors
- "Next" button disabled until valid

**Step 2: Format & Settings**

Fields:
- **Tournament Format*** (radio select with visual icons)
  - Single Elimination (bracket diagram)
  - Double Elimination (bracket diagram)
  - Round Robin (table diagram)
- **Team Capacity*** (select or number input)
  - 4, 8, 16, 32, 64, 128, Custom
  - Warning if >64: "Large tournaments require approval"
- **Match Format*** (select)
  - Best of 1 (BO1)
  - Best of 3 (BO3)
  - Best of 5 (BO5)
- **Check-in Required** (toggle)
  - If enabled: Check-in window duration (15/30/60 minutes)
- **Entry Fee** (toggle + amount)
  - Free Entry (toggle)
  - If paid: Amount in BDT (৳0-10,000)
  - **Accept DeltaCoin** (toggle) — allows players to pay with earned DC
  - Payment methods accepted: bKash, Nagad, Rocket, Bank Transfer (+ DeltaCoin if enabled)
- **Prize Pool*** (number input + distribution)
  - Total Prize Pool: ৳______
  - Auto-calculate distribution:
    - 1st: 50% (৳_____)
    - 2nd: 30% (৳_____)
    - 3rd: 20% (৳_____)
  - Or custom distribution (advanced)
- **Registration Window***
  - Opens: (datetime picker)
  - Closes: (datetime picker)
  - Validation: Closes before tournament start

---

**Advanced Options** (collapsible section, collapsed by default)

**Visual Hierarchy Mockup:**

```
┌────────────────────────────────────────────────────────┐
│ ⚙️ Advanced Options                        [Show ▼]    │  ← Collapsed state
│                                                         │
│ Fine-tune tournament behavior and features              │
└────────────────────────────────────────────────────────┘

When expanded → [Hide ▲]:

┌────────────────────────────────────────────────────────┐
│ ⚙️ Advanced Options                        [Hide ▲]    │
├────────────────────────────────────────────────────────┤
│ Fine-tune tournament behavior and features              │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🎯 Dynamic Seeding                        [⚪ OFF] │ │
│ │ Automatically balance bracket based on              │ │
│ │ participant rankings and history                    │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 💰 Entry Fee Waivers                     [⚪ OFF] │ │
│ │ Waive fees for top-ranked teams to attract talent  │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🏆 Custom Challenges                     [⚪ OFF] │ │
│ │ Bonus challenges with DeltaCoin/prize rewards      │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 📡 Live Match Updates                     [🔵 ON] │ │
│ │ Real-time scoreboard and WebSocket updates         │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🔔 Check-in Reminders                    [🔵 ON] │ │
│ │ Send reminders 1 hour & 15 min before check-in    │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 👥 Public Registration List              [🔵 ON] │ │
│ │ Show registered teams publicly on tournament page  │ │
│ │                                     [Learn More →] │ │
│ └────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────┘
```

**Component Specification:**

- **Section Header:** `h3` with gear icon ⚙️, subtitle text-secondary
- **Collapsible Trigger:** Button with `[Show ▼]` / `[Hide ▲]` (150ms transition)
- **Option Cards:** Each option in bordered card with:
  - **Icon:** Emoji or SVG (24x24px) representing feature
  - **Title:** Semibold, 16px, with toggle aligned right
  - **Description:** One-line explanation, text-secondary, 14px
  - **Learn More Link:** Small ghost button, opens help drawer (HTMX)
- **Toggle States:**
  - OFF: `⚪` gray circle, card background: `--bg-secondary`
  - ON: `🔵` blue circle, card background: `--bg-secondary` with `--brand-primary` left border (4px)
- **Spacing:** 16px between cards, 20px section padding
- **Animation:** 
  - Expand: 300ms ease-out with max-height transition
  - Toggle switch: 150ms ease-in-out
  - Card hover: 200ms transform translateY(-2px)

**Accessibility:**
- `aria-expanded="false"` on collapsed state
- `role="region"` for expanded content
- `aria-labelledby` linking header to content
- Keyboard navigation: Space/Enter to toggle

Click "Show Advanced Options ▼" to reveal:

1. **Dynamic Seeding** (toggle, default: off)
   - Description: "Automatically balance bracket based on participant rankings and history"
   - When enabled: Show seeding algorithm dropdown (Skill-based, Random with seed restrictions, Manual)
   - [Learn More →] (opens help article)
   - **Tooltip** (on hover): "Seed teams based on DeltaCrown ranking or match history to create balanced brackets"

2. **Entry Fee Waivers for Top Teams** (toggle, default: off)
   - Description: "Automatically waive entry fees for top-ranked teams to attract talent"
   - **Tooltip:** "Invite high-skill teams without entry fees based on their DeltaCrown ranking"
   - When enabled:
     - Select number of teams: 2, 4, 8
     - Minimum rank required: Input field (e.g., "Top 10")
     - Auto-notify waived teams (toggle)
   - [Learn More →]

3. **Custom Tournament Challenges** (toggle, default: off)
   - Description: "Create bonus challenges with extra prizes or DeltaCoin rewards"
   - **Tooltip:** "Add side objectives like 'Most Kills' or 'Fastest Win' with bonus rewards"
   - When enabled: Opens challenge builder:
     - Add Challenge button (repeatable)
     - For each challenge:
       - Challenge Name* (e.g., "Most Kills", "Fastest Win")
       - Description
       - Reward Type: DeltaCoin / Cash Prize / Badge
       - Reward Amount
       - Challenge Type: Individual / Team
     - Challenges display on match pages and player dashboards
   - [Learn More →]

4. **Live Match Updates** (toggle, default: on)
   - Description: "Enable real-time scoreboard integration and WebSocket updates"
   - **Tooltip:** "Live scores and bracket updates powered by WebSocket (recommended for competitive events)"
   - When disabled: Shows "Manual Updates" mode globally
     - Organizer must manually enter all scores
     - No live badges or real-time bracket updates
     - Reduces server load for casual tournaments
   - [Learn More →]

5. **Automated Check-in Reminders** (toggle, default: on)
   - Description: "Send email/Discord reminders 1 hour and 15 minutes before check-in"
   - **Tooltip:** "Reduce no-shows with automatic reminders sent before check-in window"
   - When enabled: Configure reminder channels (Email, Discord, Both)

6. **Public Registration List** (toggle, default: on)
   - Description: "Show registered teams/players publicly on tournament page"
   - **Tooltip:** "Make registrations public or keep them private until tournament starts"
   - When disabled: Only organizer can see registrations (for surprise reveals)

Each toggle includes:
- One-line description
- Small "Learn More →" link (opens help drawer)
- Visual indicator when enabled (blue accent)

**Step 3: Rules & Custom Fields**

Sections:

1. **Tournament Rules** (rich text editor)
   - Template option: "Use Standard Rules for [Game]"
   - Sections: Eligibility, Match Rules, Conduct, Disputes
   - Character count: 0/5000
   - Field name in database: `rules_text`

2. **Custom Registration Fields** (repeatable component with power-ups)
   
   **Field List View with Drag-Drop:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ Custom Fields                          [+ Add Field]   │
   ├────────────────────────────────────────────────────────┤
   │ Drag to reorder · 3 fields configured                  │
   │                                                         │
   │ ┌────────────────────────────────────────────────────┐ │
   │ │ ⋮⋮ 📝 Team Discord Server              [Edit] [×] │ │  ← Drag handle
   │ │    Text · Required                                 │ │
   │ └────────────────────────────────────────────────────┘ │
   │                                                         │
   │ ┌────────────────────────────────────────────────────┐ │
   │ │ ⋮⋮ 🎮 In-Game ID                       [Edit] [×] │ │
   │ │    Text · Required · Validation: Riot ID           │ │
   │ └────────────────────────────────────────────────────┘ │
   │                                                         │
   │ ┌────────────────────────────────────────────────────┐ │
   │ │ ⋮⋮ 📎 Team Logo                        [Edit] [×] │ │
   │ │    File Upload · Optional · Max 5MB                │ │
   │ └────────────────────────────────────────────────────┘ │
   └────────────────────────────────────────────────────────┘
   ```
   
   **Drag-Drop Behavior:**
   - Drag handle (⋮⋮) on left side of each field card
   - On drag: Card elevates with shadow, cursor changes to `grab`
   - Drop zones highlight with blue dashed border
   - On drop: Smooth animation (200ms) to new position
   - Order saves automatically
   - **Alpine.js Implementation:** `x-sort` directive or Sortable.js integration
   
   **Add Field** button → Opens field builder modal:
   
   **Field Builder Modal Layout:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ Add Custom Field                             [×Close]  │
   ├────────────────────────────────────────────────────────┤
   │ ┌──────────────────────┬─────────────────────────────┐ │
   │ │ Configuration        │ Live Preview                │ │  ← Split view
   │ │                      │                             │ │
   │ │ (Form on left)       │ (Field renders on right)    │ │
   │ └──────────────────────┴─────────────────────────────┘ │
   ├────────────────────────────────────────────────────────┤
   │                                [Cancel] [Save Field]   │
   └────────────────────────────────────────────────────────┘
   ```
   
   **For each field:**
   
   a) **Basic Settings**
   - Field Label* (text, 60 char max)
   - Field Type* (dropdown with ICONS):
     - 📝 Text (single line)
     - 🔢 Number
     - 🔗 URL
     - 📋 Select (dropdown)
     - ☑️ Multi-Select (checkboxes, multiple choices)
     - ✅ Checkbox Group (multiple yes/no options)
     - 📎 File Upload (for documents, images)
     - 📅 Date (date picker)
     - 📧 Email (validated email input)
     - 🎮 Game-specific (pre-configured Riot ID, Steam ID, etc.)
   - Required? (toggle)
   - Help Text (optional, shown below field, live preview updates)
   
   **Icon Display in Dropdown:**
   Each option shows icon + label with brief description on hover.
   Example: `📝 Text` → Hover shows "Single-line text input for short answers"
   
   b) **Validation** (if applicable)
   - Validation Preset (dropdown):
     - None
     - **Riot ID** (PlayerName#TAG format)
     - **Discord Tag** (username#1234 format)
     - **Bangladesh Phone** (+880 1XXX-XXXXXX format)
     - **URL** (valid http/https)
     - **Email**
     - Custom Regex (advanced)
   - Min/Max length or value constraints
   - Error message (custom validation failure text)
   
   c) **Conditional Visibility** (advanced)
   - Show this field only when: (dropdown)
     - Always (default)
     - Game = [Select Game] (e.g., only show "Riot ID" for VALORANT)
     - Another field has value = [condition]
   - Example use case: "Show 'Rank Limit' only when Game=VALORANT"
   
   d) **Display & Placement**
   - Display on Tournament Page (toggle)
     - If enabled: Shows field value as read-only badge on participant list
     - Example: Show "Team Discord Server" publicly
   - Collect at Registration (toggle, default: on)
     - If disabled: Admin-only field (organizer fills later)
   - Placement order: Drag to reorder fields in registration form
   
   e) **Field Options** (for Select/Multi-Select/Checkbox Group)
   - Add Option button (repeatable)
   - Option Label, Option Value
   - Default selection (for Select fields)
   
   **Live Preview Panel** (right side of modal, updates in real-time):
   
   ```
   ┌────────────────────────────────────────┐
   │ Preview: How players see this field    │
   ├────────────────────────────────────────┤
   │                                         │
   │ Team Discord Server *                  │  ← Field label (updates as you type)
   │ ┌───────────────────────────────────┐  │
   │ │ https://discord.gg/...            │  │  ← Field input (type-appropriate)
   │ └───────────────────────────────────┘  │
   │ Enter your team's Discord invite link  │  ← Help text (if provided)
   │                                         │
   │ [Preview on Dark Mode] [Preview Mobile]│  ← Toggle options
   └────────────────────────────────────────┘
   ```
   
   **Preview Features:**
   - **Real-time Updates:** Every change in configuration instantly updates preview
   - **Dark Mode Toggle:** See field in light/dark theme
   - **Mobile Preview:** Show how field renders on mobile (320px width)
   - **Validation Preview:** If validation selected, show example valid/invalid states
   - **Conditional Visibility Demo:** If conditions set, show "This field will appear when..."
   
   **Example Preview States:**
   
   1. **Text Field with Riot ID Validation:**
      ```
      In-Game Riot ID *
      ┌─────────────────────────┐
      │ PlayerName#TAG          │  ← Placeholder shows format
      └─────────────────────────┘
      Format: YourName#1234
      
      ✓ Valid: "Faker#KR1" (green check)
      ✗ Invalid: "BadFormat" (red error: "Must match PlayerName#TAG")
      ```
   
   2. **File Upload Field with Thumbnail & Progress:**
      
      **Before Upload:**
      ```
      Team Logo
      ┌─────────────────────────┐
      │  📎 Choose File         │  ← File button
      └─────────────────────────┘
      Accepted: PNG, JPG, WebP · Max: 5MB
      ```
      
      **During Upload (Progress Bar):**
      ```
      Team Logo
      ┌─────────────────────────┐
      │ 📷 team-logo.png (2.3MB)│
      │ ████████░░░░░░░░░ 45%   │  ← Progress bar
      └─────────────────────────┘
      Uploading...
      ```
      
      **After Upload (Thumbnail Preview):**
      ```
      Team Logo
      ┌──────────┐
      │ [Image]  │  ← Thumbnail (80x80px)
      │  Logo    │
      └──────────┘
      ✓ team-logo.png (2.3MB)
      [Change File] [Remove]
      ```
      
      **Error States:**
      
      a) **File Too Large:**
      ```
      ❌ File too large (8.5MB). Maximum size is 5MB.
      [Choose Another File]
      ```
      
      b) **Invalid Type:**
      ```
      ❌ Invalid file type (.pdf). Accepted formats: PNG, JPG, WebP
      [Choose Another File]
      ```
      
      c) **Upload Failed:**
      ```
      ❌ Upload failed. Please check your connection and try again.
      [Retry Upload]
      ```
   
   3. **Multi-Select with Options:**
      ```
      Preferred Match Times
      ☐ Morning (9 AM - 12 PM)
      ☐ Afternoon (12 PM - 5 PM)
      ☑ Evening (5 PM - 10 PM)    ← Pre-checked if default
      ☐ Night (10 PM - 2 AM)
      ```
   
   **Actions:**
   - **Cancel** (closes modal, discards changes)
   - **Save Field** (primary button, adds field to list, closes modal)
   - Duplicate Field (copy all settings)
   - Delete Field (with confirmation)
   - Drag handle (reorder fields)

3. **Seeding Method** (radio select)
   - Random Seeding
   - First-Come-First-Served
   - Use Team Rankings (if DeltaCrown rankings available)
   - Manual Seeding (organizer assigns after registration closes)
   - **Dynamic Seeding** (if enabled in Advanced Options)

4. **Sponsors** (optional, repeatable)
   - Add Sponsor button
   - For each sponsor:
     - Sponsor Name
     - Logo Upload (WebP/PNG/JPG, max 1MB)
     - Website URL (validation: valid URL)
     - Tier (Platinum/Gold/Silver/Bronze)
     - Sponsor Description (optional, 200 chars)

**Step 4: Preview & Publish**

Content:
- Full preview of tournament page (read-only)
- Tabs: Details, Rules, Sponsors
- Edit buttons next to each section (jump back to that step)
- Agreement checkbox:
  - "I agree to DeltaCrown Terms of Service"
  - "I confirm all information is accurate"
- Action buttons:
  - **Save as Draft** (gray) - Tournament not visible to public
  - **Publish Tournament** (blue, glowing) - Goes live immediately

**Validation Summary:**
- List of all validation errors (if any)
- Click error to jump to that step/field

**Success State:**
- After publishing: Redirect to tournament detail page
- Toast notification: "Tournament published successfully!"
- Confetti animation (brief celebration)

**Auto-save:**
- Draft auto-saved every 30 seconds
- "Last saved: 2 minutes ago" indicator (top-right)
- Resume draft from dashboard

**Responsive Behavior:**
- **Mobile:** Single-column form, larger touch targets
- **Desktop:** Form centered with max-width, sticky progress header

---

### 5.4 Organizer Dashboard

**Purpose:** Centralized management interface for tournament organizers.

**URL:** `/organizer/dashboard`

**Access:** Requires organizer role

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Dashboard Header                                        │
│  - Greeting: "Welcome back, OrganizersName!"            │
│  - Quick action: [+ Create Tournament]                  │
├────────────────────────────────────────────────────────┤
│ Overview Stats (4 cards)                                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ 3 Active │ │ 47 Pending│ │ ৳12,500  │ │ 4.8 ⭐   │  │
│  │ Tournaments│ │ Payments │ │ To Payout│ │ Rating   │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
├────────────────────────────────────────────────────────┤
│ Tabs Navigation                                         │
│  [Active] [Upcoming] [Completed] [Drafts]              │
├────────────────────────────────────────────────────────┤
│ Tournament Table                                        │
│  ┌───────┬──────────┬────────┬──────────┬─────────┐   │
│  │ Title │ Date     │ Status │ Participants │ Actions│   │
│  ├───────┼──────────┼────────┼──────────┼─────────┤   │
│  │ Row 1 │ ...      │ ...    │ ...      │ [...]   │   │
│  │ Row 2 │ ...      │ ...    │ ...      │ [...]   │   │
│  └───────┴──────────┴────────┴──────────┴─────────┘   │
│  [Pagination]                                           │
└────────────────────────────────────────────────────────┘
```

**Overview Stats Cards:**

1. **Active Tournaments**
   - Count of live tournaments
   - Click to filter active

2. **Pending Payments**
   - Count of unverified payment submissions
   - Red badge if >10
   - Click to navigate to payment verification tab

3. **Pending Payouts**
   - Total prize money to be paid out
   - Click to view payout schedule

4. **Average Rating**
   - Organizer rating (1-5 stars)
   - Based on participant feedback
   - Click to view reviews

**Tournament Table Columns:**

- **Thumbnail** (small banner preview)
- **Title** (clickable to tournament page)
- **Game** (badge)
- **Start Date**
- **Status** (badge with color coding):
  - Draft (gray)
  - Registration Open (blue)
  - Registration Full (purple)
  - Ongoing (green, live badge)
  - Completed (neutral)
  - Cancelled (red)
- **Participants** (progress: "16 / 32")
- **Payments** (progress: "12 verified, 4 pending")
- **Actions** (dropdown menu):
  - View Tournament
  - Edit Details
  - Manage Participants
  - Verify Payments
  - Manage Bracket
  - View Analytics
  - Duplicate
  - Cancel Tournament
  - Archive

**Active Tab Content:**

Features:
- Quick filters: "Live Now", "Needs Attention" (pending actions)
- Search by tournament name
- Sort by: Start date, participants, status
- Bulk actions: (checkbox column)
  - Send Announcement (to all participants)
  - Export Participants
  - Archive Selected

**Payment Verification Section** (when clicked):

Modal or slide-over panel showing:
- List of pending payment submissions
- For each submission:
  - Participant name and team
  - Payment method (bKash/Nagad/etc.)
  - Transaction ID
  - Amount
  - Proof image (zoomable)
  - Submitted date
  - Actions:
    - **Verify** (green button) - Marks payment as confirmed
    - **Reject** (red button) - Opens rejection reason modal
    - **Contact** (opens message dialog)

Real-time updates:
- New payment submissions appear with badge notification
- Toast notification: "New payment submission from Team Alpha"

**Bracket Management** (when clicked):

Interface for:
- Viewing current bracket
- Entering match results (if not submitted by participants)
- Resolving disputes
- Advancing winners
- Marking no-shows (disqualification)
- Exporting bracket as image/PDF

**Analytics Section:**

Charts and metrics (using **Chart.js** for template-first implementation):
- Registration timeline graph (line chart)
- Participant demographics (bar chart: regions, ranks)
- Traffic sources (pie chart: how users found tournament)
- Engagement metrics (views, registrations, completion rate)

**Tech Stack:** Chart.js 4.x for all data visualizations (aligned with Part 2, template-compatible, no React)

**Responsive Behavior:**

- **Desktop:** Table view with all columns
- **Tablet:** Hide less critical columns, horizontal scroll
- **Mobile:** Card view instead of table

---

### 5.5 Staff & Roles Management (Organizer Dashboard)

**Purpose:** Delegate tournament management tasks to staff members (referees, bracket managers, payment verifiers).

**URL:** `/organizer/dashboard/tournaments/<tournament-id>/staff`

**Access:** Tournament organizer (creator) only

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ Staff Management - DeltaCrown Valorant Cup 2025        │
├────────────────────────────────────────────────────────┤
│ Current Staff Members                                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │ [Avatar] PlayerName  |  Referee     | [Remove]  │  │
│  │ [Avatar] OtherUser   |  Bracket Mgr | [Remove]  │  │
│  └──────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────┤
│ Add Staff Member                                        │
│  [Search users...] [Role Dropdown] [Add]               │
└────────────────────────────────────────────────────────┘
```

**Staff Roles & Permissions:**

| Role | Permissions |
|------|-------------|
| **Referee** | View all matches, enter/override scores, resolve disputes, disqualify teams |
| **Bracket Manager** | Edit bracket structure, advance winners, manage seeding, handle no-shows |
| **Payment Verifier** | View payment submissions, approve/reject payments, contact participants |
| **Moderator** | Manage community discussions, remove inappropriate content, ban users |
| **Co-Organizer** | All permissions except delete tournament or remove organizer |

**Add Staff Flow:**

1. Search for user by username/email
2. Select role from dropdown
3. Click "Add" — sends invitation notification
4. User must accept invitation (notification + email)
5. Once accepted, staff member appears in list

**Staff Member Actions:**

- **Edit Role:** Change permissions (dropdown)
- **Remove:** Revoke access (confirmation dialog)
- **View Activity Log:** See actions performed by staff member

**Audit Ribbon on Sensitive Screens:**

For actions performed by staff (or organizer), show audit notice:

```html
<div class="audit-ribbon">
    <svg class="icon-sm"><!-- Shield icon --></svg>
    <span>This action is logged for tournament integrity</span>
</div>
```

```css
.audit-ribbon {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    padding: var(--space-2) var(--space-4);
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.3);
    border-radius: var(--radius-base);
    font-size: var(--text-xs);
    color: var(--warning);
    margin-bottom: var(--space-4);
}
```

**Examples of audited actions:**
- Score override by referee
- Payment approval/rejection
- Disqualification
- Bracket manual edit
- Prize payout confirmation

**Audit Log View (Organizer Only):**

- URL: `/organizer/dashboard/tournaments/<tournament-id>/audit-log`
- Table with columns: Timestamp, Staff Member, Action, Details
- Filter by: Date range, Staff member, Action type
- Export as CSV for records

---

## Tournament Management Summary

✅ **4 Screens Documented:**

1. **Tournament Listing Page** - Browse, filter, search with infinite scroll
2. **Tournament Detail Page** - Comprehensive view with tabs, live updates, sidebar actions
3. **Tournament Creation Wizard** - 4-step form with validation, preview, auto-save
4. **Organizer Dashboard** - Centralized management with stats, tables, payment verification

**Key UI Patterns:**
- Responsive grid layouts (1/2/3 columns)
- Tabbed navigation for content organization
- Progress indicators for multi-step flows
- Real-time updates via HTMX + WebSocket
- Contextual CTAs based on state
- Comprehensive filtering and search
- Empty states with helpful CTAs

---

## 6. Registration & Payment Flow

### 6.1 Registration Form

**Purpose:** Allow participants to register for a tournament with team/player information and custom fields.

**URL:** `/tournaments/<slug>/register` (modal or dedicated page)

**Entry Points:**
- "Register Now" button on tournament detail page
- "Register" CTA on tournament cards
- Direct link from tournament listing

**Prerequisites:**
- User must be logged in
- Tournament registration must be open
- User must not already be registered
- Capacity not yet reached

**Layout Structure (Modal Version):**

```
┌────────────────────────────────────────────────────────┐
│ Modal Overlay (backdrop blur)                           │
│  ┌────────────────────────────────────────────────┐    │
│  │ Header                                          │    │
│  │  "Register for DeltaCrown Valorant Cup 2025"   │    │
│  │  [X] Close                                      │    │
│  ├────────────────────────────────────────────────┤    │
│  │ Progress Steps                                  │    │
│  │  [1. Team Info] → [2. Custom Fields] → [3. Review]│    │
│  │  ████████████████░░░░░░░░░░░░░░░░░░░░  60%    │    │
│  ├────────────────────────────────────────────────┤    │
│  │ Form Content (scrollable)                       │    │
│  │  ┌────────────────────────────────────────┐    │    │
│  │  │ [Current step form fields]             │    │    │
│  │  │                                         │    │    │
│  │  └────────────────────────────────────────┘    │    │
│  ├────────────────────────────────────────────────┤    │
│  │ Footer Actions                                  │    │
│  │  [← Back]                      [Next →]        │    │
│  └────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

**Step 1: Team/Player Information**

**For Team-based Tournaments:**

Fields:
- **Select Team*** (dropdown)
  - List of user's existing teams
  - "+ Create New Team" option (opens inline form)
  - Team preview card (logo, name, members)
  
- **Team Members Verification** (read-only display)
  - List of team members with avatars
  - Check if meets min/max requirements
  - Warning if member already registered in another team

- **Captain Confirmation** (checkbox)
  - "I confirm I am authorized to register this team"
  - "All team members are aware and available"

**For Solo Tournaments:**

Fields:
- **Player Name*** (auto-filled from profile)
- **In-Game Username*** (auto-filled if available, editable)
- **Region*** (dropdown: Dhaka, Chittagong, Sylhet, etc.)

**Auto-fill Smart Features:**
- Pre-populate fields from user profile
- Remember last used team for similar tournaments
- Suggest teams based on game and team size

**Step 2: Custom Fields**

Dynamic fields based on organizer configuration:

Examples:
- **Discord Username** (text input)
  - Placeholder: "username#1234"
  - Validation: Discord username format
  
- **Riot ID** (text input, for VALORANT)
  - Placeholder: "PlayerName#TAG"
  - Real-time validation badge
  
- **Preferred Communication** (select)
  - Discord, WhatsApp, Telegram
  
- **Team Logo URL** (URL input)
  - Optional thumbnail preview
  
- **Emergency Contact** (phone number)
  - Bangladesh phone format validation

**Help Text:**
- Each field has contextual help icon
- Tooltip on hover with instructions
- Example values shown in placeholder

**Step 3: Review & Confirm**

Content:
- **Tournament Summary Card**
  - Tournament name, game, date
  - Entry fee: ৳500 (highlighted if paid)
  - Payment required badge (if applicable)

- **Registration Summary**
  - Team/Player info review
  - All custom field values
  - Edit buttons (jump back to specific step)

- **Rules Acceptance**
  - Expandable rules section (collapsible)
  - Checkbox: "I have read and accept the tournament rules"
  - Link to full rules in new tab

- **Entry Fee Notice** (if applicable)
  - Alert box (warning style):
    ```
    ⚠️ Entry Fee Required
    After registration, you must submit payment of ৳500
    Registration will be pending until payment is verified
    ```

- **Consent Checkboxes**
  - "I agree to DeltaCrown Terms of Service"
  - "I consent to share my in-game stats for tournament use"

**Action Buttons:**
- **Back** (go to previous step)
- **Register** (primary, blue, disabled until all checkboxes checked)
- **Contact Organizer** (ghost button, bottom-left, opens message dialog)

**Loading State:**
- Button shows spinner: "Processing..."
- Disable form interactions

**Success State:**
- Checkmark animation
- "Registration Successful!" message
- If entry fee required: Redirect to payment submission
- If free: Show confirmation screen

**Error Handling:**
- Inline validation on each field (real-time)
- Summary of errors at top of form
- Scroll to first error field
- Toast notification for server errors
- **"Contact Organizer"** option if persistent errors

---

### 6.2 Payment Submission

**Purpose:** Allow registered participants to submit payment proof for entry fee verification.

**URL:** `/tournaments/<slug>/payment` or `/registrations/<id>/payment`

**Access:** 
- Shown immediately after registration (if entry fee required)
- Accessible from user dashboard ("Pending Payment" badge)
- Email reminder with direct link

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Breadcrumbs: Dashboard / My Tournaments / Payment       │
├────────────────────────────────────────────────────────┤
│ Page Header                                             │
│  H1: "Submit Payment Proof"                             │
│  Subtitle: "For DeltaCrown Valorant Cup 2025"           │
├────────────────────────────────────────────────────────┤
│ Layout (2-column on desktop)                            │
│ ┌─────────────────────────┬─────────────────────────┐  │
│ │ Payment Instructions    │ Payment Form            │  │
│ │ (Left, sticky)          │ (Right)                 │  │
│ │                         │                         │  │
│ │ - Amount: ৳500          │ - Payment Method*       │  │
│ │ - Methods accepted      │ - Transaction ID*       │  │
│ │ - Account numbers       │ - Screenshot Upload*    │  │
│ │ - Deadline countdown    │ - Amount Paid*          │  │
│ │                         │ - Notes (optional)      │  │
│ │                         │ [Submit]                │  │
│ └─────────────────────────┴─────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

**Payment Instructions Panel (Left):**

Content:
- **Amount to Pay:** ৳500 (large, bold, highlighted)
  
- **Accepted Payment Methods** (visual cards):
  ```
  ┌─────────┬─────────┬─────────┬─────────┬──────────┐
  │ bKash   │ Nagad   │ Rocket  │ Bank    │DeltaCoin │
  │ [Logo]  │ [Logo]  │ [Logo]  │Transfer │ [Icon]   │
  └─────────┴─────────┴─────────┴─────────┴──────────┘
  ```

- **DeltaCoin Option** (if enabled by organizer):
  - Display: "💰 **Pay with DeltaCoin:** 500 DC"
  - Help text: "DeltaCoin earned from achievements and past tournament winnings"
  - Balance display: "Your balance: 1,250 DC"
  - If insufficient: "Insufficient balance. Earn more DC or use cash payment."
  - **Auto-deduct on submission** (no screenshot required)

- **Organizer Cash Payment Details** (for bKash/Nagad/Rocket/Bank):
  - **bKash Personal:** 01712345678 [Copy 📋]
    - Send Money → Enter this number → Amount: ৳500
  
  - **Nagad:** 01812345678 [Copy 📋]
  - **Rocket:** 01912345678 [Copy 📋]
  - **Bank Transfer:**
    - Bank: Dutch-Bangla Bank
    - Account: 1234567890123 [Copy 📋]
    - Name: Tournament Organizer Name

- **Deadline Countdown** (prominent):
  ```
  ⏰ Submit payment within:
  [23 : 45 : 32]
   HH   MM   SS
  ```
  - After 48 hours: Registration may be cancelled

- **Help Section:**
  - "Need Help?" expandable
  - FAQ: How long for verification? What if rejected?
  - Contact organizer button

**Payment Form (Right):**

Fields:

1. **Payment Method*** (radio button cards)
   ```
   ○ DeltaCoin  ○ bKash  ○ Nagad  ○ Rocket  ○ Bank Transfer
   ```
   - Large, clickable cards with logos
   - Selected state: Blue border + check icon
   - **DeltaCoin card:** Shows DC balance, auto-hides fields 2-4 when selected

2. **Transaction ID / Reference Number*** (text input — hidden if DeltaCoin)
   - Placeholder: "Enter transaction/reference ID from receipt"
   - Help text: "Found on your mobile banking app receipt"
   - Character count if needed

3. **Amount Paid*** (number input — hidden if DeltaCoin)
   - Pre-filled: ৳500
   - Validation: Must match entry fee exactly
   - **Error states:**
     - Underpaid: "❌ Amount is ৳450. Entry fee is ৳500. Please pay the full amount."
     - Overpaid: "⚠️ Amount is ৳550. Entry fee is ৳500. Excess will not be refunded."
   - Real-time validation feedback

4. **Payment Screenshot*** (file upload — hidden if DeltaCoin)
   - Drag-and-drop area
   - Supported formats: JPG, PNG, PDF (max 5MB)
   - Image preview after upload (zoomable)
   - Requirements:
     - Must show transaction ID
     - Must show amount
     - Must show date/time
   - Example screenshot button (shows sample)
   - **File validation errors:**
     - Too large: "File size is 7.2MB. Maximum is 5MB. Try compressing the image."
     - Invalid format: "File type .txt not supported. Please upload JPG, PNG, or PDF."
     - Corrupted: "Unable to read file. Please try again or use a different file."

5. **Additional Notes** (textarea, optional)
   - Placeholder: "Any additional information..."
   - Character limit: 500

**Validation:**
- All required fields must be filled (except DeltaCoin auto-payment)
- Transaction ID format check (alphanumeric, min 6 characters)
- Amount must match exactly (warn on overpay, error on underpay)
- File must be valid image/PDF under 5MB

**Submit Button:**
- **DeltaCoin:** "Confirm Payment (500 DC)"
- **Cash methods:** "Submit Payment Proof"
- Loading state: Spinner + "Processing..." or "Uploading..."
- Disabled until form valid

**Success State:**
- Redirect to confirmation screen
- Toast: "Payment proof submitted successfully!"

**Payment Status Visual States:**

1. **Pending Verification** (Yellow badge - `--warning`):
   - Show submitted details (read-only)
   - Badge: `🕐 Pending Verification`
   - Estimated verification time: "Usually within 24 hours"
   - "Edit Submission" button (if organizer allows)
   - "Cancel Registration" button (with confirmation)
   - **"Contact Organizer"** button (prominent, opens message dialog)
   - **Analytics:** `data-analytics-id="payment_pending_view"`

2. **Verification In Progress** (Blue badge - `--info`):
   - Badge: `🔍 Verification In Progress`
   - Message: "Organizer is currently reviewing your payment proof"
   - Progress indicator: "Started 2 hours ago"
   - No edit allowed during verification
   - **"Contact Organizer"** button available

3. **Approved** (Green badge - `--success`):
   - Badge: `✓ Payment Verified`
   - Confetti animation on first view
   - Message: "Your payment has been approved. You're all set!"
   - Display: Approved by [Organizer Name], Verified on [Date]
   - Next steps card: "Check-in opens 30 minutes before start"
   - **Analytics:** `data-analytics-id="payment_approved_view"`

4. **Rejected** (Red badge - `--error`):
   - Badge: `✗ Payment Rejected`
   - Red alert box with rejection reason from organizer
   - Reason display: "Screenshot unclear - amount not visible"
   - "Resubmit Payment" button (clears form, pre-fills details)
   - **"Contact Organizer"** button (discuss rejection)
   - **Analytics:** `data-analytics-id="payment_rejected_resubmit"`

5. **Refunded** (Purple badge - `--brand-secondary`):
   - Badge: `↩️ Refunded`
   - Message: "Your payment has been refunded to [Method]"
   - Reason: "Tournament cancelled" or "Organizer-initiated"
   - Refund amount: ৳500
   - Refund date: [Date]
   - No action buttons (final state)

6. **Fee Waived** (Gold badge - `--brand-accent`):
   - Badge: `🎉 Fee Waived`
   - Message: "Entry fee waived by organizer - You're a featured participant!"
   - Reason: "Top-ranked team" or "Sponsor invitation" or "Promotional waiver"
   - Display: Waived by [Organizer Name]
   - No payment required

7. **Expired** (Gray badge - faded `--error`):
   - Badge: `⏰ Payment Expired`
   - Warning alert: "Payment deadline passed. Your registration has been cancelled."
   - Explanation: "The tournament may allow late registration if spots are available."
   - **"Contact Organizer"** button (request extension)
   - "Re-register" button (if tournament still open)
   - **Analytics:** `data-analytics-id="payment_expired_contact"`

**Edge State Banners (contextual alerts):**

**Color Token Reference for All Alerts:**
- **Error/Critical** → `--error` (#EF4444) - payment rejected, check-in missed, duplicate entries
- **Warning/Caution** → `--warning` (#F59E0B) - underpaid, team conflict, deadline approaching
- **Info/Notice** → `--info` (#3B82F6) - overpaid, helpful tips
- **Success** → `--success` (#10B981) - payment approved, registration confirmed

1. **Underpaid Amount:** (Warning - `--warning`)
   ```
   ⚠️ Your submitted amount (৳450) is less than the entry fee (৳500).
   Please resubmit with the correct amount or contact the organizer.
   ```
   - **CSS Class:** `alert alert-warning`
   - **Icon:** `⚠️` warning triangle
   - **Action:** "Resubmit Payment" button

2. **Overpaid Amount:** (Info - `--info`)
   ```
   ℹ️ Your submitted amount (৳550) exceeds the entry fee (৳500).
   The excess ৳50 will not be refunded. Proceed only if intended.
   ```
   - **CSS Class:** `alert alert-info`
   - **Icon:** `ℹ️` info circle
   - **Action:** "Confirm Anyway" button

3. **Check-in Missed:** (Error - `--error`)
   ```
   ❌ Check-in deadline passed. You have been disqualified from the tournament.
   Contact the organizer if you believe this is an error.
   ```
   - **CSS Class:** `alert alert-error`
   - **Icon:** `❌` cross mark
   - **"Contact Organizer"** button (secondary, opens message dialog with pre-filled subject: "Check-in Missed Appeal")

4. **Team Member Already Registered:** (Warning - `--warning`)
   ```
   ⚠️ Player "PlayerName" is already registered in another team for this tournament.
   Please select a different team member or withdraw their other registration.
   ```
   - **CSS Class:** `alert alert-warning`
   - **Icon:** `⚠️` warning triangle
   - **Action:** "Change Team Member" button

5. **Duplicate Registration Attempt:** (Error - `--error`)
   ```
   ❌ Your team is already registered for this tournament.
   You cannot register the same team twice.
   ```
   - **CSS Class:** `alert alert-error`
   - **Icon:** `❌` cross mark
   - **Action:** "View Existing Registration" button

6. **Payment Expired:** (Error - `--error`)
   ```
   ⏰ Payment deadline expired. Your registration has been cancelled.
   Contact the organizer to request an extension if spots are still available.
   ```
   - **CSS Class:** `alert alert-error`
   - **Icon:** `⏰` clock
   - **Action:** "Contact Organizer" button (primary)

---

### 6.3 Confirmation Screen

**Purpose:** Confirm successful registration and guide user to next steps.

**URL:** `/tournaments/<slug>/registered` or `/registrations/<id>/confirmation`

**Layout Structure:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Success Hero (centered, full-width)                     │
│  ✓ Success Icon (large, animated checkmark)            │
│  H1: "Registration Successful!"                         │
│  Subtitle: "You're all set for DeltaCrown Valorant Cup"│
├────────────────────────────────────────────────────────┤
│ Status Card (centered, max-width 800px)                 │
│  ┌────────────────────────────────────────────────┐    │
│  │ Registration Status                             │    │
│  │  - Team: Team Alpha                             │    │
│  │  - Tournament: DeltaCrown Valorant Cup 2025     │    │
│  │  - Status: [Pending Payment] or [Confirmed]     │    │
│  │  - Registration Date: Nov 3, 2025               │    │
│  └────────────────────────────────────────────────┘    │
├────────────────────────────────────────────────────────┤
│ Next Steps (3-column cards)                             │
│  ┌──────────┬──────────┬──────────┐                    │
│  │ 1. Pay   │ 2. Check │ 3. Play  │                    │
│  │ Entry Fee│ -In      │ Tournament│                    │
│  └──────────┴──────────┴──────────┘                    │
├────────────────────────────────────────────────────────┤
│ Quick Actions (button group)                            │
│  [View Tournament] [Add to Calendar] [Share]            │
├────────────────────────────────────────────────────────┤
│ Important Information (card)                            │
│  - Check-in time, Discord server, Rules reminder        │
└────────────────────────────────────────────────────────┘
```

**Success Hero Section:**

Visual:
- Large checkmark icon (80px) with green glow
- Confetti animation (brief, 2 seconds)
- Success message tailored to status:
  - If payment required: "Registration Received!"
  - If free entry: "You're Registered!"
  - If waitlist: "You're on the Waitlist!"

**Status Card:**

Information displayed:
- **Registration ID:** REG-12345 (copyable)
- **Tournament:** [Tournament Name] (link)
- **Team/Player:** [Team Name]
- **Status:** Badge with color coding
  - 🟡 Pending Payment (yellow)
  - 🟢 Confirmed (green)
  - 🔵 Waitlisted (blue)
- **Registration Date:** Nov 3, 2025 10:30 AM
- **Entry Fee:** ৳500 (if applicable)
  - Link to payment submission if not paid

**Next Steps Cards:**

**Card 1: Complete Payment** (if applicable)
- Icon: 💳
- Title: "Submit Payment Proof"
- Description: "Upload your payment screenshot to confirm your spot"
- Deadline: "Within 48 hours"
- Button: "Submit Payment" (primary)

**Card 2: Check-In**
- Icon: ✅
- Title: "Check-In Required"
- Description: "Check in 30 minutes before tournament start"
- Time: "Dec 15, 2025 - 9:30 AM BST"
- Button: "Set Reminder"

**Card 3: Prepare**
- Icon: 🎮
- Title: "Get Ready to Play"
- Description: "Join tournament Discord and review rules"
- Button: "Join Discord"

**Quick Actions:**

Buttons:
1. **View Tournament Details** (secondary button)
   - Navigates back to tournament page

2. **Add to Calendar** (ghost button)
   - Dropdown: Google Calendar, Outlook, iCal
   - Pre-filled event with tournament details

3. **Share with Team** (ghost button)
   - Dropdown: Copy link, WhatsApp, Discord
   - Shareable link: "I just registered for [Tournament]!"

**Important Information Card:**

Alert-style box (info):

Content:
- **Check-in Window:** Dec 15, 2025 - 9:30 AM to 10:00 AM BST
  - "Failure to check in will result in disqualification"
  
- **Tournament Discord:** [Join Server] button
  - "Mandatory for communication and match coordination"
  
- **Tournament Rules:** [Read Full Rules] link
  - "Make sure all team members are aware"
  
- **Contact Organizer:** [Message] button
  - "For any questions or issues"

**Email Confirmation:**

User receives email with:
- Registration confirmation
- All important dates and times
- Payment instructions (if applicable)
- Calendar attachment (.ics file)
- Tournament rules PDF

**Status-Specific Variations:**

**Free Entry (No Payment Required):**
- Skip Card 1 (payment)
- Status: "Confirmed ✓" (green)
- Emphasize preparation steps

**Waitlisted:**
- Hero: "You're on the Waitlist"
- Explanation: "You'll be automatically enrolled if a spot opens"
- Status: "Waitlisted (Position #5)"
- Email notification when spot opens

**Responsive Behavior:**
- **Desktop:** 3-column next steps cards
- **Mobile:** Stacked cards, full-width buttons

---

## Registration & Payment Flow Summary

✅ **3 Screens Documented:**

1. **Registration Form** - Multi-step modal/page with team selection, custom fields, review
2. **Payment Submission** - Split layout with instructions + upload form, deadline countdown
3. **Confirmation Screen** - Success state with status, next steps, quick actions

**Key UX Features:**
- **Progressive Disclosure:** Multi-step forms reduce cognitive load
- **Smart Auto-fill:** Pre-populate from user profile and team data
- **Real-time Validation:** Instant feedback on field errors
- **Clear Instructions:** Payment details prominently displayed with copy buttons
- **Deadline Awareness:** Countdown timer for payment submission
- **Status Transparency:** Clear badges and explanations for each state
- **Action-Oriented:** Next steps guide users through post-registration tasks
- **Calendar Integration:** Easy addition to user's calendar
- **Mobile Optimization:** Touch-friendly, single-column layouts

**Error Prevention:**
- Required field indicators (*)
- Inline validation messages
- Confirmation dialogs for destructive actions
- Image preview before submission
- Amount matching validation

**Accessibility:**
- Form labels with explicit associations
- Error announcements via aria-live regions
- Keyboard navigable multi-step forms
- High contrast status badges

---

## 7. Bracket & Match Screens

### 7.1 Bracket Visualization

**Purpose:** Interactive tournament bracket for viewing matchups, results, and progression.

**URL:** `/tournaments/<slug>/bracket`

**Key Features:**
- **SVG-based bracket tree** with zoom/pan controls
- **Responsive layouts:** Single/double elimination, round robin table
- **Real-time updates** via WebSocket
- **User highlight:** User's team path emphasized
- **Match navigation:** Click node to view match details

**Bracket Controls:**
- Zoom in/out buttons (+/-)
- Fit to screen button
- Download as image (PNG/PDF)
- Fullscreen mode
- Minimap for large brackets (>32 teams)

**Bracket Node Structure:**
```
┌───────────────────────┐
│ SEMIFINALS - Match 1  │
├───────────────────────┤
│ Team Alpha        [2] │ ← Winner (bold)
│ Team Beta         [0] │
└───────────────────────┘
```

**States:**
- **Upcoming:** Gray border, TBD teams
- **In Progress:** Blue border, live badge, pulsing
- **Completed:** Green border, winner highlighted
- **User's Team:** Neon cyan border with glow

### 7.2 Match Card (Compact)

**Purpose:** Display match information in bracket or list views.

**Visual (from Component Library 4.2):**
- Team logos, names, scores
- Match status badge (Scheduled/Live/Completed)
- Round indicator (Quarterfinals, Semifinals, etc.)
- Stream link icon (if available)
- Click to expand to full match page

### 7.3 Live Match Page

**Purpose:** Real-time match tracking with scores, chat, and stream integration.

**URL:** `/tournaments/<slug>/matches/<match-id>`

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Match Header                                            │
│  [LIVE] SEMIFINALS - Match 1                            │
│  DeltaCrown Valorant Cup 2025                           │
│  👁️ 1,234 viewers online                               │  ← Viewers counter
├────────────────────────────────────────────────────────┤
│ Scoreboard (prominent)                                  │
│  ┌─────────────────────────────────────────────┐       │
│  │ Team Alpha  [13]  VS  [8]  Team Beta        │       │
│  │ [Logo]                          [Logo]      │       │
│  └─────────────────────────────────────────────┘       │
├────────────────────────────────────────────────────────┤
│ Content Tabs                                            │
│  [Stream] [Map Stats] [Chat] [Info]                    │
├────────────────────────────────────────────────────────┤
│ Tab Content Area                                        │
│  (Stream embed, stats, chat, or match info)            │
└────────────────────────────────────────────────────────┘
```

**Viewers Online Counter:**

**Position:** Below match title, right-aligned or center

**Visual Design:**
```
👁️ 1,234 viewers online
```
- **Icon:** Eye emoji (👁️) or SVG eye icon
- **Count:** Formatted with commas (1,234 / 12,345 / 123K for > 100k)
- **Label:** "viewers online" in text-secondary color
- **Styling:** 
  - Small badge style with subtle background (`--bg-tertiary`)
  - Pulsing green dot (•) next to icon when count is updating
  - Font size: 14px, medium weight

**Update Behavior:**
- **Real-time Updates:** WebSocket connection tracks page views
- **Update Frequency:** Every 5 seconds (batched to reduce load)
- **Animation:** Smooth number transition (150ms ease-out) when count changes
- **Peak Indicator:** Show "🔥 Peak: 2,456" on hover (tooltip)
- **Historical Data:** Organizers can view viewer graph in dashboard

**Technical Implementation:**
```javascript
// WebSocket message for viewer count update
{
    "type": "viewer_count",
    "match_id": 123,
    "count": 1234,
    "peak": 2456
}

// Update counter with animation
function updateViewerCount(newCount) {
    const counter = document.querySelector('.viewer-count');
    const oldCount = parseInt(counter.textContent);
    
    // Animate number transition
    animateCounter(oldCount, newCount, 150);
    
    // Add pulse effect
    counter.classList.add('count-updated');
    setTimeout(() => counter.classList.remove('count-updated'), 150);
}
```

**Viewer Tracking:**
- **Active Viewer:** User has page tab active (Page Visibility API)
- **Idle Detection:** User idle > 5 minutes = not counted
- **Session Timeout:** Disconnect after 10 minutes of inactivity
- **Unique Count:** One count per user session (not page refreshes)
- **Bot Prevention:** Rate limiting and CAPTCHA challenges if suspicious

**Display Rules:**
- **Live matches:** Show real-time count
- **Upcoming matches:** Show "Match starts in X minutes"
- **Completed matches:** Show "Watched by 2,456 viewers" (peak count)
- **No viewers:** Show "Be the first to watch" (encourages engagement)

**Privacy:**
- **Anonymous Counting:** No individual user tracking displayed publicly
- **Organizer View:** Detailed analytics in dashboard (viewer timeline graph)

**Scoreboard Features:**
- **Live score updates** (WebSocket)
- **Map progress:** "Map 1 of 3" (for BO3/BO5)
- **Round-by-round timeline** (expandable)
- **Team rosters:** Hover team logo to see players

**Stream Tab:**
- YouTube/Twitch embed (responsive iframe)
- If no stream: "No stream available" empty state
- Viewer count display
- Chat integration alongside stream

**Map Stats Tab** (for applicable games):
- Kill/death leaderboard
- Objective completions
- Economy graphs (CS2, VALORANT)
- MVP highlight

**Chat Tab:**
- Live chat room (WebSocket)
- Moderation controls (for organizers)
- Emoji reactions
- Rate limiting to prevent spam

**Info Tab:**
- Match schedule
- Tournament rules excerpt
- Referee information
- **Contact Organizer** button (prominent, opens message dialog)
- Report issue button

### 7.4 Result Submission

**Purpose:** Allow participants to submit match results and evidence.

**URL:** `/tournaments/<slug>/matches/<match-id>/submit`

**Access:** Only participants of the match

**Form Fields:**

1. **Match Outcome*** (radio select)
   - ○ We Won
   - ○ We Lost
   - ○ Draw (if applicable)

2. **Score*** (number inputs)
   - Our Score: ___
   - Opponent Score: ___
   - Validation: Must be valid for match format

3. **Evidence Upload*** (multiple files)
   - Screenshot(s) of final scoreboard
   - Supported: PNG, JPG (max 10MB per file, up to 5 files)
   - Drag-and-drop area with preview grid
   - Help text: "Include full scoreboard with both team names visible"

4. **Additional Notes** (textarea, optional)
   - Any relevant match details
   - Issues encountered
   - Character limit: 500

**Submit Button:**
- "Submit Result"
- Confirmation dialog: "This will notify the opponent and referee"

**States:**
- **Both teams submitted same result:** Auto-approved, winner advances
- **Conflicting results:** Creates dispute, referee notified
- **One team submitted:** Shows "Waiting for opponent confirmation"

---

## 8. Player Experience Screens

### 8.1 Player Dashboard

**Purpose:** Personalized hub for players to manage tournaments, matches, and achievements.

**URL:** `/dashboard` or `/my/tournaments`

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ Navbar                                                  │
├────────────────────────────────────────────────────────┤
│ Welcome Header & Profile Badge Progress                │
│  Avatar + "Welcome back, PlayerName!"                   │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 🏅 Badge Level: Competitive Player (Lvl 15)      │  │
│  │ ████████████░░░░░░░░ 2,450 / 3,000 XP (82%)     │  │  ← Progress bar
│  │ 550 XP to next level: "Elite Competitor"         │  │
│  └──────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────┤
│ Quick Stats (4 cards)                                   │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                  │
│  │ 5    │ │ 2    │ │ 12   │ │ 3    │                  │
│  │Active│ │Live  │ │Total │ │Wins  │                  │
│  └──────┘ └──────┘ └──────┘ └──────┘                  │
├────────────────────────────────────────────────────────┤
```

**Profile Badge Level Progress Bar:**

**Visual Design:**
```
┌────────────────────────────────────────────────────────┐
│ 🏅 Badge Level: Competitive Player (Lvl 15)            │
│ ████████████████░░░░ 2,450 / 3,000 XP (82%)           │  ← Gradient fill
│ 🎯 550 XP to Elite Competitor                          │
└────────────────────────────────────────────────────────┘
```

**Badge Level Tiers:**
1. **Rookie** (Lvl 1-4): Gray badge, 0-1,000 XP
2. **Amateur** (Lvl 5-9): Green badge, 1,000-2,500 XP
3. **Competitive** (Lvl 10-14): Blue badge, 2,500-5,000 XP
4. **Elite** (Lvl 15-19): Purple badge, 5,000-10,000 XP
5. **Pro** (Lvl 20-24): Gold badge, 10,000-20,000 XP
6. **Legend** (Lvl 25+): Rainbow gradient, 20,000+ XP

**XP Earning:**
- Tournament participation: 100 XP
- Tournament win: 500 XP
- Match win: 50 XP
- Perfect game: 100 XP bonus
- Prediction correct: 10 XP
- MVP vote: 25 XP

**Progress Bar Styling:**
- **Gradient Fill:** Tier-specific colors (blue for Competitive tier)
- **Smooth Animation:** 400ms ease-out on XP gain
- **Percentage Display:** Shows % completion
- **Next Level Preview:** "550 XP to Elite Competitor"

**Level Up Animation:**

When player earns enough XP to level up:

1. **Progress Bar Fills:** Smooth animation (1s) from current to 100%
2. **Flash Effect:** Gold flash across bar
3. **Confetti Burst:** Canvas-confetti celebration (1.5s)
4. **Level Up Modal:**
   ```
   ┌────────────────────────────────────┐
   │ 🎉 LEVEL UP! 🎉                   │
   │                                    │
   │ You are now Level 16!              │
   │ 🏅 Elite Competitor                │
   │                                    │
   │ New Perks Unlocked:                │
   │ ✓ Priority tournament registration │
   │ ✓ Special badge on profile         │
   │ ✓ 100 DC bonus reward 🪙           │
   │                                    │
   │ [Share Achievement] [Continue]     │
   └────────────────────────────────────┘
   ```
5. **Sound Effect:** Optional "level up" sound (can disable in settings)
6. **Profile Badge Updates:** New tier badge appears immediately
7. **Analytics:** `data-analytics-id="gamification_level_up"`

**Progress Bar CSS:**
```css
.progress-bar-gamification {
    height: 24px;
    background: var(--bg-tertiary);
    border-radius: var(--radius-full);
    position: relative;
    overflow: hidden;
}

.progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #3B82F6, #8B5CF6); /* Tier gradient */
    border-radius: var(--radius-full);
    transition: width 400ms ease-out;
    position: relative;
}

.progress-bar-fill.leveling-up {
    animation: level-up-flash 1s ease-out;
}

@keyframes level-up-flash {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; box-shadow: 0 0 30px var(--brand-accent); }
}
```

**Hover Tooltip:**
- Hovering over progress bar shows detailed XP breakdown:
  ```
  Recent XP Gains:
  • Tournament Win: +500 XP
  • 3 Match Wins: +150 XP
  • 5 Correct Predictions: +50 XP
  Total this week: +700 XP
  ```

├────────────────────────────────────────────────────────┤
│ Sections (tabs or cards)                                │
│  - Upcoming Tournaments                                 │
│  - Active Matches (live badge if any)                   │
│  - Recent Achievements                                  │
│  - Pending Actions (payment, check-in, result submit)   │
└────────────────────────────────────────────────────────┘
```

**Upcoming Tournaments Section:**
- Card list with tournament info
- Countdown to start
- Check-in button (if within window)
- View bracket link
- Withdraw button (with confirmation)

**Active Matches:**
- Match cards with live updates
- "Submit Result" button (if match completed)
- Join stream button
- Real-time score updates

**Pending Actions (Priority):**
- Red badge count
- Action items:
  - "Submit payment for [Tournament]" (urgent, deadline shown)
  - "Check in for [Tournament]" (urgent, time remaining)
  - "Submit match result" (reminder)
  - "Resolve dispute" (if applicable)

### 8.2 Tournament History

**Purpose:** Archive of past tournament participations and results.

**URL:** `/profile/tournaments` or `/my/history`

**Features:**
- **Timeline view** (default) or **grid view** toggle
- **Filters:** Date range, game, status (Completed/Cancelled)
- **Search:** Tournament name
- **Sort:** Most recent, best placement, highest prize

**Tournament History Card:**
- Tournament name, game badge
- Date participated
- Placement badge: 🥇 1st, 🥈 2nd, 🥉 3rd, or "Top 8"
- Prize earned: ৳5,000 (if won)
- Certificate link (if issued)
- "View Details" button

**Statistics Summary:**
- Total tournaments: 24
- Win rate: 35%
- Total prizes earned: ৳15,000
- Best placement: 🥇 Champion (3x)
- Favorite game: VALORANT (15 tournaments)

### 8.3 Certificate View

**Purpose:** Display and share tournament certificates.

**URL:** `/certificates/<certificate-id>`

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ 🎊 Confetti Animation (1.5s on page load) 🎊           │  ← Celebration!
├────────────────────────────────────────────────────────┤
│ Certificate Preview (full-width, elegant design)        │
│  ┌────────────────────────────────────────────────┐    │
│  │ ╔════════════════════════════════════════════╗ │    │
│  │ ║  DeltaCrown Tournament Engine              ║ │    │
│  │ ║  Certificate of Achievement                ║ │    │
│  │ ║                                            ║ │    │
│  │ ║  This certifies that                       ║ │    │
│  │ ║  [Team Alpha]                              ║ │    │
│  │ ║  has achieved                              ║ │    │
│  │ ║  🥇 1st Place                              ║ │    │
│  │ ║  in                                        ║ │    │
│  │ ║  DeltaCrown Valorant Cup 2025              ║ │    │
│  │ ║                                            ║ │    │
│  │ ║  Prize: ৳25,000                            ║ │    │
│  │ ║  Date: December 15, 2025                   ║ │    │
│  │ ║                                            ║ │    │
│  │ ║  [QR Code]  [Organizer Signature]         ║ │    │
│  │ ║  Verify: CERT-ABC123                       ║ │    │
│  │ ╚════════════════════════════════════════════╝ │    │
│  └────────────────────────────────────────────────┘    │
├────────────────────────────────────────────────────────┤
│ Actions                                                 │
│  [📥 Download PDF] [📤 Share] [✓ Verify Certificate]   │
├────────────────────────────────────────────────────────┤
│ Share on Social (expanded when clicking Share)          │
│  ┌────────────────────────────────────────────────┐    │
│  │ [📘 Facebook] [🐦 Twitter] [💼 LinkedIn]       │    │
│  │ [📸 Instagram Story] [📋 Copy Link]            │    │
│  └────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

**Page Load Animation:**
- **Confetti burst** on first certificate view (1.5s duration)
- Uses canvas-confetti.js with gold colors (#FFD700, #FFA500, #DAA520)
- Triggered once per session (localStorage flag prevents repeat)
- Respects `prefers-reduced-motion`
- **Analytics:** `data-analytics-id="certificate_confetti_triggered"`

**Certificate Features:**
- **Dynamic design** based on placement (gold, silver, bronze themes)
- **QR code** for verification (links to public verification page)
- **Unique ID:** CERT-ABC123 (verifiable)
- **Organizer signature** (digital or uploaded image)
- **Featured winner badge** (if organizer marked as featured)

**Actions:**

1. **Download PDF** 
   - High-res PDF for printing (A4 landscape, 1920x1080, 300 DPI)
   - Filename: `DeltaCrown_Certificate_TeamAlpha_2025.pdf`
   - **Analytics:** `data-analytics-id="certificate_download_pdf"`

2. **Share on Social** (expandable dropdown)
   
   **Facebook:**
   - Pre-filled post: "🏆 We won 1st Place at DeltaCrown Valorant Cup 2025! ৳25,000 prize 🎉 #DeltaCrown #VALORANT #Esports"
   - Auto-generates OG image (certificate thumbnail)
   - Link: Certificate verification URL
   - **Analytics:** `data-analytics-id="certificate_share_facebook"`
   
   **Twitter:**
   - Pre-filled tweet: "🥇 Champions! Just won @DeltaCrown Valorant Cup 2025! ৳25,000 prize pool 🔥 [Certificate Link] #DeltaCrown #VALORANTEsports"
   - Twitter Card with certificate preview
   - Character count: 280 limit respected
   - **Analytics:** `data-analytics-id="certificate_share_twitter"`
   
   **LinkedIn:**
   - Professional post: "Proud to announce our team secured 1st place at DeltaCrown Valorant Cup 2025, competing against 32 teams. This achievement reflects our dedication to competitive gaming excellence."
   - Certificate image attachment
   - **Analytics:** `data-analytics-id="certificate_share_linkedin"`
   
   **Instagram Story:**
   - Opens Instagram app (mobile) or web (desktop)
   - Pre-formatted story template with certificate
   - Stickers: "🏆 Winner", "@deltacrown", "#VALORANT"
   - **Analytics:** `data-analytics-id="certificate_share_instagram"`
   
   **Copy Link:**
   - Copies certificate URL to clipboard
   - Toast notification: "Link copied! Share it anywhere"
   - URL format: `deltacrown.gg/certificates/ABC123`
   - **Analytics:** `data-analytics-id="certificate_copy_link"`

3. **Verify Certificate**
   - Opens public verification page (`/verify/<hash>`)
   - Shows authenticity indicators
   - QR code visible for physical certificate verification
   - **Analytics:** `data-analytics-id="certificate_verify_click"`

**Public Verification Page:**

**URL:** `/verify/<hash>` (e.g., `/verify/e7a4b9c2d1f5`)

**Layout:**

```
┌────────────────────────────────────────────────────────┐
│ Certificate Verification                                │
├────────────────────────────────────────────────────────┤
│ ┌────────────────────────────────────────────────────┐ │
│ │  ✓ VERIFIED DELTACROWN CERTIFICATE                 │ │  ← Green banner
│ │  This certificate is authentic and issued by       │ │
│ │  DeltaCrown Tournament Engine                      │ │
│ └────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────┤
│ Certificate Details                                     │
│  ┌──────────────────────────┬──────────────────────┐   │
│  │ Certificate ID:          │ CERT-ABC123          │   │
│  │ Issued To:               │ Team Alpha           │   │
│  │ Achievement:             │ 🥇 1st Place         │   │
│  │ Tournament:              │ DeltaCrown Valorant  │   │
│  │                          │ Cup 2025             │   │
│  │ Organizer:               │ DeltaCrown eSports   │   │
│  │ Prize:                   │ ৳25,000              │   │
│  │ Date:                    │ December 15, 2025    │   │
│  │ Issued On:               │ Dec 16, 2025 2:30 PM │   │
│  │ Verification Hash:       │ e7a4b9c2d1f5a3b8     │   │
│  └──────────────────────────┴──────────────────────┘   │
├────────────────────────────────────────────────────────┤
│ Security Indicators                                     │
│  ✓ Certificate matches DeltaCrown records              │
│  ✓ Tournament organizer verified                       │
│  ✓ Issued within 48 hours of tournament completion     │
│  ✓ QR code matches hash                                │
├────────────────────────────────────────────────────────┤
│ [View Full Certificate] [Download PDF] [Report Issue]  │
└────────────────────────────────────────────────────────┘
```

**Verification Features:**
- **QR Code Integration:** Scan QR on physical certificate → auto-redirects to `/verify/<hash>`
- **Security Indicators:**
  - ✓ Certificate matches DeltaCrown records
  - ✓ Tournament organizer verified account
  - ✓ Issued within reasonable timeframe
  - ✓ Hash integrity check passed
- **Verification Hash:** Unique, tamper-proof identifier (SHA-256 of certificate data)
- **Blockchain Future-Proofing:** Hash stored for future blockchain verification
- **Invalid Certificate Handling:**
  ```
  ✗ INVALID CERTIFICATE
  This certificate ID does not exist in our records or has been revoked.
  [Report Fake Certificate] [Contact Support]
  ```
- **Revoked Certificate:**
  ```
  ⚠️ CERTIFICATE REVOKED
  This certificate was revoked by the tournament organizer.
  Reason: [Organizer's reason]
  Revoked On: [Date]
  ```
- **Expired Link (if > 5 years old):**
  ```
  ℹ️ ARCHIVED CERTIFICATE
  This certificate is from [Date]. Records are archived but authenticity is confirmed.
  [View Archived Details]
  ```

**Reporting Mechanism:**
- **"Report Fake Certificate"** button (if user suspects forgery)
- Opens form:
  - Reason for report (dropdown: Forged, Altered, Duplicate, Other)
  - Additional details (textarea)
  - Upload suspicious certificate image (optional)
  - Reporter email (for follow-up)
- Submission creates moderation ticket for DeltaCrown staff review

---

### Organizer Certificate Issuance (Organizer Dashboard)

**After Tournament Completion:**

New action in organizer dashboard: **"Issue Certificates"** button

**Certificate Issuance Workflow:**

1. **Eligible Recipients** (auto-populated)
   - List of placements (1st, 2nd, 3rd, Top 8, etc.)
   - Select which placements receive certificates
   - Checkbox: Include all participants (participation certificate)

2. **Certificate Template Selection & Preview**
   
   **Preview Screen Layout:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ Preview Certificate                         [× Close]   │
   ├────────────────────────────────────────────────────────┤
   │ ┌──────────────────────┬─────────────────────────────┐ │
   │ │ Configuration        │ Live Certificate Preview    │ │
   │ │                      │                             │ │
   │ │ Template:            │ ╔═══════════════════════╗   │ │
   │ │ ○ Gold (1st Place)   │ ║  DeltaCrown          ║   │ │
   │ │ ● Silver (2nd Place) │ ║  Certificate         ║   │ │
   │ │ ○ Bronze (3rd)       │ ║                      ║   │ │
   │ │ ○ Standard           │ ║  [Team Name]         ║   │ │
   │ │                      │ ║  2nd Place           ║   │ │
   │ │ Logo Placement:      │ ║  Tournament Name     ║   │ │
   │ │ [Upload Logo]        │ ║  ৳10,000 Prize       ║   │ │
   │ │ Preview: [logo.png]  │ ║                      ║   │ │
   │ │ Position: Top-Center │ ║  [Organizer Logo]    ║   │ │
   │ │                      │ ║  [Signature]         ║   │ │
   │ │ Signature:           │ ║  [QR Code] CERT-123  ║   │ │
   │ │ [Upload Signature]   │ ╚═══════════════════════╝   │ │
   │ │ Preview: [sign.png]  │                             │ │
   │ │ Position: Bottom-Right│ [Download Sample PDF]      │ │
   │ │                      │                             │ │
   │ │ Achievement Text:    │                             │ │
   │ │ ┌──────────────────┐ │                             │ │
   │ │ │ has achieved     │ │                             │ │
   │ │ │ 2nd Place in...  │ │                             │ │
   │ │ └──────────────────┘ │                             │ │
   │ │                      │                             │ │
   │ │ Additional Notes:    │                             │ │
   │ │ ┌──────────────────┐ │                             │ │
   │ │ │ Outstanding...   │ │                             │ │
   │ │ └──────────────────┘ │                             │ │
   │ └──────────────────────┴─────────────────────────────┘ │
   ├────────────────────────────────────────────────────────┤
   │                   [Cancel] [Apply to All Certificates] │
   └────────────────────────────────────────────────────────┘
   ```
   
   **Preview Features:**
   - **Real-time Updates:** Certificate preview refreshes as you type/upload
   - **Template Themes:**
     - Gold: Gold border, trophy icon, #FFD700 accents
     - Silver: Silver border, medal icon, #C0C0C0 accents
     - Bronze: Bronze border, ribbon icon, #CD7F32 accents
     - Standard: Blue brand color, participation trophy
   - **Logo Placement Options:**
     - Top-Center (above title)
     - Top-Left (corner)
     - Watermark (centered, semi-transparent background)
     - None (DeltaCrown branding only)
   - **Signature Options:**
     - Upload image (PNG with transparency, max 500KB)
     - Use text signature (typed name in script font)
     - None (DeltaCrown official only)
     - Position: Bottom-Right, Bottom-Center, Bottom-Left
   - **Download Sample PDF:** Generate one certificate PDF to review before bulk issuance
   - **Zoom Controls:** 50%, 75%, 100%, 150% (to inspect details)
   
   **Customization Options:**
   - Achievement description (text, 200 char max)
   - Organizer signature (upload image or use typed name)
   - Organizer logo (upload, positioned as selected)
   - Additional notes (appears at bottom, 100 char max)
   - Certificate dimensions: A4 landscape (297x210mm, 1920x1080px at 150 DPI)

3. **Featured Winners** (toggle for each placement)
   - Mark winners as "Featured" (displays on public tournament page)
   - Featured certificates appear in platform-wide "Hall of Fame"

4. **Bulk Actions:**
   - **"Preview All"** — Generate PDF previews for review
   - **"Issue Certificates"** — Sends certificates to all recipients
   - Auto-notification to recipients (email + platform notification)
   - Certificates appear in player "Tournament History"

5. **Post-Issuance:**
   - View issued certificates list
   - Revoke certificate (rare, requires reason, notifies recipient)
   - Re-issue (if corrections needed)

### 8.4 Profile Integration

**Purpose:** Display tournament stats and achievements on user profile.

**Location:** `/profile/<username>` (existing DeltaCrown profile page)

**New Sections Added:**

**Tournament Stats Card:**
- Tournaments participated: 24
- Wins / Losses: 8 / 16
- Best placement: 🥇 Champion
- Total prizes: ৳15,000
- Favorite game: VALORANT

**Achievements & Badges:**
- Grid of unlocked badges
- Examples:
  - "First Tournament" 🎮
  - "Champion" 🏆 (with count if multiple)
  - "Perfect Attendance" ✅
  - "Community Champion" 💬 (for active participants)
- Hover for description and unlock date

**Recent Tournaments:**
- List of 5 most recent tournaments
- Quick stats (placement, date)
- "View All" link to tournament history

**Certificates Showcase:**
- Carousel of earned certificates
- Only featured certificates shown publicly
- Click to view full certificate

---

## 9. Spectator & Community Screens

### 9.1 Spectator View

**Purpose:** Engaging view for non-participants to follow tournament action.

**URL:** `/tournaments/<slug>/spectate` or `/tournaments/<slug>/live`

**Features:**

**Live Tournament Hub:**
- **Hero Section:** Featured stream embed (largest ongoing match)
- **Live Matches Grid:** All currently live matches with thumbnails
- **Upcoming Matches:** Schedule with countdown timers
- **Bracket Overview:** Mini bracket with live match highlights
- **Leaderboard:** Current standings (for round robin or group stages)

**Match Cards (Spectator View):**
- Current score (real-time)
- Team names and logos
- "Watch" button (opens match page)
- Viewer count
- Game time elapsed

**Engagement Features:**

1. **Match Predictions with Lock Timers** (Fan Vote Widget)
   
   **Widget Layout:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ 🔮 Predict the Winner                                  │
   ├────────────────────────────────────────────────────────┤
   │ ⏱️ Predictions lock in: 05:32                          │  ← Countdown timer
   │                                                         │
   │ ┌────────────────────┐  ┌────────────────────┐        │
   │ │  Team Alpha        │  │  Team Beta          │        │
   │ │  [Logo]            │  │  [Logo]             │        │
   │ │  65% (1,234 votes) │  │  35% (654 votes)    │        │
   │ │  [Vote ▶]          │  │  [Vote ▶]           │        │
   │ └────────────────────┘  └────────────────────┘        │
   │                                                         │
   │ Your Prediction: None yet · Earn 5 DC if correct! 🪙   │
   └────────────────────────────────────────────────────────┘
   ```
   
   **After Voting:**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ 🔮 Your Prediction                                      │
   ├────────────────────────────────────────────────────────┤
   │ ⏱️ Predictions locked · Match starting soon            │
   │                                                         │
   │ ┌────────────────────┐  ┌────────────────────┐        │
   │ │  Team Alpha ✓      │  │  Team Beta          │        │  ← Checkmark on voted team
   │ │  [Logo]            │  │  [Logo]             │        │
   │ │  68% (1,456 votes) │  │  32% (680 votes)    │        │
   │ │  YOUR VOTE         │  │                     │        │
   │ └────────────────────┘  └────────────────────┘        │
   │                                                         │
   │ ✓ Locked in! Results revealed after match              │
   └────────────────────────────────────────────────────────┘
   ```
   
   **Countdown Timer Features:**
   - **Live countdown:** Updates every second using JavaScript
   - **Lock time:** 5 minutes before match start (configurable by organizer)
   - **Color coding:**
     - Green (> 10 min): Plenty of time
     - Yellow (5-10 min): Hurry up!
     - Red (< 5 min): Closing soon!
     - Locked: Gray with lock icon 🔒
   - **Animation:** Timer pulses when < 1 minute remaining
   - **Auto-lock:** Predictions auto-close at 00:00, voting buttons disabled
   - **WebSocket sync:** Countdown synced across all spectators
   
   **Post-Match Results:**
   - Reveal correct prediction with green highlight
   - Wrong prediction: Red highlight (friendly)
   - Display: "You earned 5 DC! 🎉" or "Better luck next time!"
   - Update leaderboard: "Top Predictors" with accuracy %
   - Streak tracking: "🔥 5-match prediction streak!"

2. **MVP Voting Widget**
   
   **Widget Layout (During/After Match):**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ 🏆 Vote for MVP                                        │
   ├────────────────────────────────────────────────────────┤
   │ ⏱️ Voting closes in: 02:15 after match ends            │  ← Countdown (15 min window)
   │                                                         │
   │ ┌──────────────────────────────────────────────────┐   │
   │ │ [Avatar] PlayerOne        Team Alpha    [Vote]   │   │
   │ │          453 votes (32%) ████░░░░                 │   │  ← Progress bar
   │ └──────────────────────────────────────────────────┘   │
   │                                                         │
   │ ┌──────────────────────────────────────────────────┐   │
   │ │ [Avatar] PlayerTwo        Team Alpha    [Vote] ✓ │   │  ← Voted
   │ │          689 votes (49%) ████████░                │   │
   │ └──────────────────────────────────────────────────┘   │
   │                                                         │
   │ ┌──────────────────────────────────────────────────┐   │
   │ │ [Avatar] PlayerThree      Team Beta     [Vote]   │   │
   │ │          268 votes (19%) ███░░░░░                 │   │
   │ └──────────────────────────────────────────────────┘   │
   │                                                         │
   │ Your Vote: PlayerTwo · Total Votes: 1,410              │
   └────────────────────────────────────────────────────────┘
   ```
   
   **MVP Announcement (Post-Voting):**
   
   ```
   ┌────────────────────────────────────────────────────────┐
   │ 🏆 MATCH MVP                                            │
   ├────────────────────────────────────────────────────────┤
   │         ╔════════════════════════╗                      │
   │         ║   [Avatar - Large]     ║                      │
   │         ║                        ║                      │
   │         ║   PlayerTwo            ║                      │
   │         ║   Team Alpha           ║                      │
   │         ║                        ║                      │
   │         ║   689 votes (49%)      ║                      │
   │         ║   +50 DC Bonus 🪙       ║                      │
   │         ╚════════════════════════╝                      │
   │                                                         │
   │ 🎊 Confetti animation plays 🎊                          │  ← Confetti trigger
   └────────────────────────────────────────────────────────┘
   ```
   
   **Features:**
   - **Vote Weight System:**
     - Verified match participants: 3x weight
     - Logged-in spectators: 1x weight
     - Anonymous viewers: Cannot vote (must log in)
   - **Live Updates:** Vote counts update in real-time (WebSocket)
   - **One Vote Per User:** Cannot change vote after submission
   - **Voting Window:** Opens when match ends, closes 15 minutes later
   - **Countdown Timer:** Shows time remaining to vote (same styling as predictions)
   - **MVP Bonus:** Winner earns 50 DC automatically credited
   - **MVP Badge:** "🏆 MVP" badge appears on player profile for this tournament

3. **Live Reactions**
   - Emoji reactions: 🔥 Fire, 👏 Applause, 😱 Shocked, ⚡ Clutch
   - Reactions float up on screen (like live stream reactions)
   - Aggregated count: "🔥 245 reactions"
   - Rate limit: 1 reaction per 5 seconds

4. **Highlight Reels** (post-match)
   - Curated clips section on tournament page
   - Organizer or community uploads highlights
   - Timestamp links to VOD (if stream archived)
   - Upvote best highlights
   - Filter: Best Plays, Funny Moments, Clutches, Upsets

5. **Confetti Animation** (Result Publish Celebration)
   
   **Triggers:**
   - Match result published (winner announced)
   - MVP voting result revealed
   - Tournament champion crowned (finals)
   - Perfect game achieved (13-0, 3-0 sweep)
   
   **Animation Specification:**
   - **Library:** canvas-confetti.js (lightweight, 6KB gzipped)
   - **Duration:** 1.5 seconds
   - **Particle Count:** 150 pieces
   - **Colors:** Brand colors (#3B82F6, #8B5CF6, #F59E0B, #10B981)
   - **Origin:** Center-top of widget/screen
   - **Spread:** 70° cone angle
   - **Gravity:** 1 (realistic fall)
   - **Shapes:** Squares, circles (no custom shapes to keep performance)
   - **Performance:** Uses requestAnimationFrame, GPU-accelerated
   
   **Code Example:**
   ```javascript
   // Trigger confetti on MVP announcement
   function celebrateMVP() {
       confetti({
           particleCount: 150,
           spread: 70,
           origin: { y: 0.3 },
           colors: ['#3B82F6', '#8B5CF6', '#F59E0B', '#10B981']
       });
       
       // Second burst after 300ms for extra flair
       setTimeout(() => {
           confetti({
               particleCount: 100,
               angle: 60,
               spread: 55,
               origin: { x: 0 }
           });
           confetti({
               particleCount: 100,
               angle: 120,
               spread: 55,
               origin: { x: 1 }
           });
       }, 300);
   }
   ```
   
   **User Control:**
   - **Reduced Motion:** Respects `prefers-reduced-motion: reduce` (no animation)
   - **Disable Option:** User settings > "Disable celebration animations"
   - **Mobile:** Reduced particle count (75 pieces) for performance

6. **Shareable Result Cards** (auto-generated OG images)
   - After each match: Generate shareable card
   - Design: Team logos, final score, tournament branding
   - Templates for:
     - Match Results (standard)
     - **Upsets** (lower seed beats higher seed) → **Confetti animation on page load**
     - **Finals Results** (champion announcement) → **Double confetti burst**
     - **Perfect Game** (13-0, 3-0, etc.) → **Gold confetti**
   - One-click share to Twitter/Facebook/Instagram Stories
   - Cards include: "View Tournament on DeltaCrown [link]"

6. **Share Tournament**
   - Social media buttons with pre-filled text
   - Copy tournament link with tracking (referral stats)
   - Embed code for tournament widget (iframe)

### 9.2 Community Discussions

**Purpose:** Forum-style discussions for each tournament with rich interaction features.

**URL:** `/tournaments/<slug>/discussions`

**Features:**
- **Discussion threads** for tournament
- Categories: General, Match Predictions, Highlights, Disputes
- Create new thread (requires login)
- Reply to threads (nested comments, up to 5 levels deep)
- Upvote/downvote system
- Organizer/Admin badges on posts
- Report inappropriate content

**Rich Text Features (HTMX-powered):**

1. **@Mentions**
   - Type `@username` to mention users
   - Autocomplete dropdown appears after typing `@`
   - Shows avatars + usernames of participants/organizers
   - Mentioned users receive notification
   - Mention styling: Blue highlight, clickable to user profile
   - **Implementation:** HTMX autocomplete endpoint `/api/mentions?q=username`
   
   **Example:**
   ```
   Hey @PlayerOne, did you see that clutch play? 🔥
   ```

2. **Rich Media Embeds** (Link Previews)
   - Paste URL → Auto-generates preview card
   - **Supported:**
     - YouTube/Twitch videos: Embed player
     - Twitter posts: Embedded tweet
     - Images (direct links): Inline image
     - DeltaCrown tournament links: Rich tournament card
   - **Implementation:** HTMX triggers `/api/link-preview?url=...` on paste
   - Preview loads asynchronously (doesn't block post submission)
   - **Lazy Loading:** Preview renders only when comment is visible
   
   **Example Preview Card:**
   ```
   ┌────────────────────────────────────────┐
   │ 🎥 YouTube Video Preview               │
   │ ┌──────────────────────────────────┐   │
   │ │  [Thumbnail]                     │   │
   │ │  ▶️ Best VALORANT Plays          │   │
   │ └──────────────────────────────────┘   │
   │ 5:32 · 12K views                       │
   └────────────────────────────────────────┘
   ```

3. **GIF Support**
   - GIF picker button in comment editor
   - **Integration:** Tenor API or GIPHY
   - Search GIFs by keyword
   - Inline GIF display in comments
   - Max size: 5MB, auto-resize if larger
   - **Lazy Loading:** GIFs load on scroll
   - **Accessibility:** Alt text required for GIFs

4. **Emoji Reactions** (Quick Responses)
   - React to comments without replying
   - Common reactions: 👍 👎 😂 ❤️ 🔥 💀
   - Hover shows who reacted
   - One reaction per user per comment
   - Aggregated count: "👍 23"

**Comment Editor UI:**

```
┌────────────────────────────────────────────────────────┐
│ Write a Comment...                                      │
│ ┌────────────────────────────────────────────────────┐ │
│ │ Hey @PlayerOne, great match! Check this out:       │ │  ← @mention autocomplete
│ │ https://youtube.com/...                            │ │
│ │                                                     │ │
│ │ [YouTube Preview Card Renders Here]                │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ [😊 Emoji] [🎬 GIF] [📎 Attach] [**B** *I*]          │  ← Formatting toolbar
│                                      [Cancel] [Post]   │
└────────────────────────────────────────────────────────┘
```

**Formatting Toolbar:**
- **Bold:** `**text**` → **text**
- **Italic:** `*text*` → *text*
- **Link:** Auto-detects URLs, renders as hyperlinks
- **Code:** `` `code` `` → `code` (inline)
- **Quote:** `> text` → Blockquote style

**Moderation & Content Filtering:**

1. **Auto-Moderation Rules:**
   - **Profanity Filter:** Blocks/flags common slurs and offensive words
   - **Spam Detection:** 
     - Same message posted > 3 times = auto-hide
     - External links from new accounts = require approval
     - Rate limit: Max 10 comments per 5 minutes per user
   - **Link Whitelist:** 
     - Allow: YouTube, Twitch, Twitter, DeltaCrown, imgur
     - Block: Suspicious domains, phishing links
     - Unknown domains: Require organizer approval

2. **Manual Moderation Actions** (Organizer/Admin):**
   - **Edit Comment:** Organizer can edit inappropriate content (logged)
   - **Hide Comment:** Visible only to author and mods
   - **Delete Comment:** Permanent removal (requires reason)
   - **Ban User:** From tournament discussions (temporary or permanent)
   - **Lock Thread:** Prevent new comments (for resolved disputes)
   - **Pin Comment:** Sticky comment at top (for announcements)

3. **Moderation Queue:**
   - Flagged comments appear in organizer dashboard
   - Actions: Approve, Hide, Delete, Ban User
   - Bulk moderation: Select multiple comments
   - Mod log: All actions timestamped with moderator name

4. **User Reporting:**
   - **Report Comment** button on each comment
   - Report reasons:
     - Spam or misleading
     - Harassment or hate speech
     - Inappropriate content
     - Violates tournament rules
   - Report goes to moderation queue
   - Reporters remain anonymous

**Thread Card (Enhanced):**
- Thread title (clickable)
- Author avatar, name, organizer/admin badge
- Posted time (relative: "2 hours ago")
- Reply count, upvote count
- **Emoji Reactions Bar:** 👍23 🔥15 💬8 (quick response without replying)
- Latest reply preview (first 100 chars)
- Tags (if applicable): #highlights #dispute
- **Rich Media Indicator:** 🎥 (if video), 🖼️ (if image), 🎬 (if GIF)
- **Pinned Indicator:** 📌 (if moderator pinned)

**Reactions Feature (Quick Responses):**

```
┌────────────────────────────────────────────────────────┐
│ Comment by PlayerOne · 2 hours ago                      │
├────────────────────────────────────────────────────────┤
│ That clutch play was insane! Best moment of the match. │
├────────────────────────────────────────────────────────┤
│ Reactions:  👍 23  🔥 15  😂 5  ❤️ 8  💀 3             │  ← Reaction bar
│                                                         │
│ [Add Reaction ➕]  [Reply]  [Report]                   │
└────────────────────────────────────────────────────────┘
```

**Reaction Options:**
- 👍 Thumbs Up (like, agree)
- 👎 Thumbs Down (disagree)
- 😂 Laugh (funny)
- ❤️ Heart (love it)
- 🔥 Fire (amazing, lit)
- 💀 Skull (dead from laughing, brutal)

**Reaction Behavior:**
- **One Reaction Per User:** Can react once per comment, can change reaction
- **Hover Shows Users:** Hover over reaction count shows list of users who reacted
- **Real-time Updates:** New reactions appear immediately (WebSocket)
- **Sorting:** Comments can be sorted by "Most Reacted"
- **Analytics:** `data-analytics-id="comment_reaction_[emoji]"`

**Pinned Comments (Moderator Feature):**

**Pin Action** (Organizer/Admin only):
- Right-click comment → "Pin Comment" option
- Or three-dot menu → "📌 Pin to Top"
- Confirmation: "This comment will appear at the top of the discussion."

**Pinned Comment Display:**
```
┌────────────────────────────────────────────────────────┐
│ 📌 PINNED BY ORGANIZER                                 │  ← Yellow banner
├────────────────────────────────────────────────────────┤
│ Comment by TournamentOrganizer · Pinned 1 day ago      │
│                                                         │
│ Important Update: Match schedule changed to 6 PM BST   │
│ due to technical issues. All teams notified via email. │
│                                                         │
│ Reactions:  👍 45  ❤️ 12                               │
│ [Reply]                                                 │
└────────────────────────────────────────────────────────┘
```

**Pinned Comment Features:**
- **Yellow/Gold Background:** Stands out visually (bg: `#FFFBEB`)
- **Pin Icon:** 📌 prefix on title
- **Always at Top:** Appears above all other comments (even when sorted)
- **Multiple Pins:** Support up to 3 pinned comments per thread
- **Unpin Action:** Moderator can unpin (removes from top, returns to timeline)
- **Notification:** Thread participants get notification when comment is pinned
- **Analytics:** `data-analytics-id="comment_pin_action"`

### 9.3 Social Features

**Purpose:** Enhance community engagement and shareability.

**Features Throughout Platform:**

**Social Sharing:**
- Tournament cards: Share button
- Match results: Share scoreboard image
- Certificates: Auto-generate social media posts
- Achievements: Share badge unlocks

**Social Media Integration:**
- **Facebook:** Auto-post tournament announcements
- **Twitter:** Share match updates
- **Instagram:** Stories integration for highlights
- **Discord:** Rich embeds for tournament links

**Team Finder:**
- "/tournaments/<slug>/team-finder"
- Players looking for teams
- Post availability (game, role, rank)
- Message interested players
- Public teammate search

**Invitations:**
- Send tournament invites to friends
- Generate referral links (track registrations)
- Group registration discounts (if configured)

---

## 10. Mobile Design Patterns

### Internationalization & Bengali Support

**Language Switcher:**
- Location: Top-right corner of navbar (next to profile)
- Icon: Globe 🌐 with current language code (EN/বাং)
- Dropdown: English, বাংলা (Bengali)
- Persists selection in localStorage + user profile
- Reload page or use i18n library (Django i18n) for dynamic switching

**Bengali Font Verification:**
- Primary Bengali font: **Noto Sans Bengali** (Google Fonts)
- Verify font includes **Bengali numerals** (০১২৩৪৫৬৭৮৯)
- Test counters, progress bars, scores with Bengali numerals
- Fallback: Use Western numerals if Bengali numerals cause layout issues

**Localization Scope (Strings to Translate):**

Priority 1 (Must translate):
- Navigation menu items
- Button labels (Register, Submit, Cancel, etc.)
- Form field labels and placeholders
- Error messages and validation text
- Status badges (Live, Pending, Completed, etc.)
- Tournament state labels

Priority 2 (Should translate):
- Tournament descriptions (user-generated, optional)
- Help text and tooltips
- Empty state messages
- Success/confirmation messages
- Email notifications

Priority 3 (Nice to have):
- Admin panel strings
- Advanced settings descriptions
- Legal text (Terms, Privacy)

**Date & Time Localization:**
- Format: DD MMM, YYYY (e.g., "15 Dec, 2025" / "১৫ ডিসে, ২০২৫")
- Time: 12-hour with AM/PM (e.g., "10:00 AM" / "সকাল ১০:০০")
- Timezone: Always show "BST" (Bangladesh Standard Time)

**Currency Display:**
- Always prefix with ৳ symbol (Taka)
- Number format: Bangladeshi style with commas (৳50,000 or ৳৫০,০০০)
- DeltaCoin: "DC" suffix (500 DC / ৫০০ DC)

**Game Name Translation:**
- Keep English game names by default (VALORANT, CS2, etc.)
- Bengali descriptions optional (user-preference)

### Mobile-First Approach

**Principle:** Design for mobile, enhance for desktop.

**Key Patterns:**

**1. Bottom Sheet Navigation**
- Filters, actions slide up from bottom
- Easier thumb reach
- Example: Tournament filters (replaces sidebar)

**2. Sticky CTAs**
- Registration button always visible at bottom
- Fixed position, above navbar
- Example: "Register Now" floats on tournament detail page

**3. Collapsible Sections**
- Accordion pattern for long content
- Tournament details, rules, participants
- Default: First section expanded

**4. Swipe Gestures**
- Swipe between tabs (tournament detail tabs)
- Swipe to dismiss modals
- Pull-to-refresh for live updates

**5. Touch-Optimized Controls**
- Minimum tap target: 44x44px
- Spacing between tappable elements: 8px
- Large, thumb-friendly buttons

**6. Mobile Navigation**
- Hamburger menu for main nav
- Bottom navigation bar for primary actions:
  - Home | Tournaments | Matches | Profile
- Max 5 items in bottom nav

**7. Card-Based Layouts**
- Stack cards vertically on mobile
- Full-bleed images
- Swipeable carousels for multiple items

**8. Optimized Forms**
- One field per row
- Large input fields
- Native keyboards (number, email, phone)
- Auto-advance on completion (OTP inputs)

**9. Condensed Information**
- Hide less critical data on mobile
- "Show More" expand buttons
- Prioritize essential info above fold

**10. Offline Capabilities**
- Cache tournament details
- Queue actions (result submissions) when offline
- Sync when connection restored

**11. iOS Safe Areas (Notch Compatibility)**
- Sticky bottom CTAs respect safe area insets
- Use `env(safe-area-inset-bottom)` for padding
- Test on iPhone 14 Pro (Dynamic Island), iPhone SE (no notch)
- Example:
  ```css
  .sticky-cta {
      padding-bottom: calc(16px + env(safe-area-inset-bottom));
  }
  ```

**12. Payment Number Copy Buttons (Thumb-Optimized)**
- Large copy buttons (min 48x48px) next to payment numbers
- Success feedback: Button text changes to "Copied! ✓" for 2 seconds
- Haptic feedback (if supported)
- Numeric keyboard automatically opens when tapping payment field
- Example layout:
  ```
  bKash: 01712345678  [Copy 📋]
          └─ 44px tall button, right-aligned
  ```

**13. Keyboard Overlap Prevention**
- Auto-scroll active input field above keyboard
- Ensure "Next" button visible when keyboard open
- Use `scrollIntoView()` with `behavior: 'smooth'`
- "Next" button advances to next field automatically
- "Done" on last field submits form or closes keyboard
- Test on iOS Safari (keyboard toolbar) and Android Chrome

---

## 10. Staff & Moderator Tools

### 10.1 Admin Activity Log Panel

**Purpose:** Provide staff and moderators with comprehensive audit trail of all administrative actions for transparency, compliance, and troubleshooting.

**Access:** Staff members with "can_view_activity_log" permission

**Location:** 
- URL: `/admin/activity-log`
- Navigation: Admin panel sidebar → "Activity Log"
- Also: Dashboard widget showing recent 10 activities

**Panel Layout:**

```
┌────────────────────────────────────────────────────────┐
│ 🔒 AUDIT MODE ACTIVE - All actions are logged          │
└────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────┐
│ Activity Log                                    [Export CSV] │
├────────────────────────────────────────────────────────┤
│ Filters:                                                │
│ [User ▼] [Action Type ▼] [Date Range ▼] [Search...]   │
├────────────────────────────────────────────────────────┤
│ Table (Paginated - 50 per page)                        │
│ ┌──────────┬────────────┬────────┬──────────────────┐ │
│ │ Date/Time│ User       │ Action │ Details          │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 2m ago   │ Admin_John │ ✓ PAY  │ Approved payment │ │
│ │          │            │        │ for Team Alpha   │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 15m ago  │ Mod_Sara   │ ✗ PAY  │ Rejected payment │ │
│ │          │            │        │ (Invalid proof)  │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 1h ago   │ Admin_John │ 🏆 CERT│ Issued certif.   │ │
│ │          │            │        │ to 16 players    │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 2h ago   │ Mod_Ali    │ 🔨 BAN │ Banned user      │ │
│ │          │            │        │ PlayerX (reason) │ │
│ ├──────────┼────────────┼────────┼──────────────────┤ │
│ │ 3h ago   │ Admin_John │ ⚙️ SET │ Changed max      │ │
│ │          │            │        │ teams: 32→64     │ │
│ └──────────┴────────────┴────────┴──────────────────┘ │
├────────────────────────────────────────────────────────┤
│ Pagination: [< Prev] Page 1 of 45 [Next >]            │
└────────────────────────────────────────────────────────┘
```

**Audit Mode Banner:**

When staff performs sensitive actions (payment verification, user ban, etc.), banner appears:

```
┌────────────────────────────────────────────────────────┐
│ 🔒 AUDIT MODE ACTIVE - All actions are logged          │
│ Your activity is being recorded for compliance.        │
└────────────────────────────────────────────────────────┘
```

**Banner Styling:**
- Background: `#374151` (gray-700)
- Text color: White with 90% opacity
- Icon: 🔒 lock
- Position: Sticky at top of admin panel
- Height: 48px
- Animation: Slide down on first sensitive action (300ms ease-out)
- Dismiss: "Got it" button (hides banner for session)

**Logged Action Types:**

1. **Payment Verification** (`PAY`)
   - Action: Approved, Rejected, Refunded, Fee Waived
   - Details: Team name, tournament, amount, reason (if rejected)
   - Logged Fields: Previous state → New state

2. **Match Result Modification** (`MATCH`)
   - Action: Result edited, Result disputed, Score corrected
   - Details: Match ID, teams, old score → new score
   - Logged Fields: Who submitted original, edit reason

3. **User Moderation** (`USER`)
   - Action: User banned, User unbanned, Warning issued
   - Details: Username, reason, duration (if temporary ban)
   - Logged Fields: Moderator notes

4. **Certificate Management** (`CERT`)
   - Action: Certificate issued, Certificate revoked
   - Details: Tournament, recipient count, batch ID
   - Logged Fields: Template used

5. **Tournament Settings** (`SET`)
   - Action: Setting changed (max teams, check-in time, fee, etc.)
   - Details: Setting name, old value → new value
   - Logged Fields: Tournament slug

6. **Registration Override** (`REG`)
   - Action: Manual registration, Waitlist override, Slot reserved
   - Details: Team/player, tournament, reason
   - Logged Fields: Override type

**Activity Log Table Columns:**

1. **Date/Time:**
   - Format: "2m ago", "15m ago", "1h ago", "Nov 3, 10:30 AM" (for older)
   - Tooltip on hover shows exact timestamp
   - Sortable (default: newest first)

2. **User:**
   - Staff member who performed action
   - Link to user profile
   - Avatar thumbnail (24x24px)
   - Badge: "Admin", "Moderator", "Organizer"

3. **Action:**
   - Icon + category badge
   - Color-coded: Green (✓), Red (✗), Blue (ℹ️), Gold (🏆)
   - Tooltip shows full action name

4. **Details:**
   - Summary of action (1-2 lines)
   - "View Details" link opens modal with full context
   - Related object link (tournament, user, match)

5. **IP Address** (optional column, admin-only):
   - Shows IP address of staff member
   - Privacy: Only visible to super admins

**Filters:**

1. **User Filter:**
   - Dropdown: All staff members
   - Autocomplete search
   - Option: "My Actions Only"

2. **Action Type Filter:**
   - Multi-select dropdown
   - Options: Payment, Match, User, Certificate, Settings, Registration
   - Badge count: Shows # of actions per type

3. **Date Range Filter:**
   - Presets: Today, Last 7 days, Last 30 days, Custom range
   - Date picker for custom range

4. **Search Box:**
   - Search by: Team name, user, tournament, keyword
   - Real-time search (debounced)

**Export CSV:**
- Button: "Export CSV" (top-right)
- Exports filtered results (respects current filters)
- CSV Columns: Date, Time, User, Action, Details, IP (if admin)
- Filename: `activity-log-YYYY-MM-DD.csv`
- Analytics: `data-analytics-id="admin_activity_log_export"`

**Details Modal:**

Clicking "View Details" opens modal:

```
┌────────────────────────────────────────────────────────┐
│ Activity Details                              [X Close] │
├────────────────────────────────────────────────────────┤
│ Action: Payment Approved                                │
│ Performed by: Admin_John (admin@deltacrown.com)        │
│ Date: Nov 3, 2025 - 10:30:45 AM BST                    │
│ IP Address: 103.15.xxx.xxx (Dhaka, Bangladesh)         │
├────────────────────────────────────────────────────────┤
│ Action Details:                                         │
│  - Payment ID: PAY-12345                                │
│  - Team: Team Alpha                                     │
│  - Tournament: DeltaCrown Valorant Cup 2025            │
│  - Amount: ৳500                                         │
│  - Previous Status: Pending Verification                │
│  - New Status: Approved                                 │
│  - Verification Note: "Valid bKash transaction"         │
├────────────────────────────────────────────────────────┤
│ Related Links:                                          │
│  [View Payment] [View Tournament] [Contact Admin]      │
└────────────────────────────────────────────────────────┘
```

**Real-Time Updates:**

- **WebSocket Integration:** New activities appear without refresh
- **Live Indicator:** Green dot on Activity Log menu item when new activity
- **Toast Notification:** "New activity logged" (dismissible)
- **Auto-Refresh:** Table updates every 30 seconds (if WebSocket unavailable)

**Retention Policy:**

- **Activity logs retained for:** 2 years
- **After 2 years:** Archived (not deleted)
- **Super admin access:** Can view archived logs
- **Compliance:** GDPR-compliant (user can request their logged actions)

**Permissions:**

- **View Activity Log:** Staff, Moderators, Admins
- **Export CSV:** Admins only
- **View IP Addresses:** Super Admins only
- **Delete Logs:** No one (immutable audit trail)

**Dashboard Widget:**

Compact version shown on admin dashboard:

```
┌────────────────────────────────────────────────────────┐
│ Recent Activity (Last 24h)                    [View All]│
├────────────────────────────────────────────────────────┤
│ • 2m ago - Admin_John approved payment (Team Alpha)    │
│ • 15m ago - Mod_Sara rejected payment (Invalid proof)  │
│ • 1h ago - Admin_John issued 16 certificates           │
│ • 2h ago - Mod_Ali banned user PlayerX                 │
│ • 3h ago - Admin_John changed tournament settings      │
├────────────────────────────────────────────────────────┤
│ [View Full Activity Log →]                             │
└────────────────────────────────────────────────────────┘
```

**Analytics:**
- `data-analytics-id="admin_activity_log_view"`
- `data-analytics-id="admin_activity_log_filter"`
- `data-analytics-id="admin_activity_log_export"`
- `data-analytics-id="admin_activity_log_detail_view"`

---

## 11. Accessibility Guidelines

### WCAG 2.1 Level AA Compliance

**Color Contrast:**
- Text on background: Minimum 4.5:1 ratio
- Large text (18pt+): Minimum 3:1 ratio
- Interactive elements: 3:1 contrast with adjacent colors
- Test all color combinations with contrast checker

**Keyboard Navigation:**
- All interactive elements accessible via Tab
- Tab order follows logical reading order
- Focus indicators clearly visible (2px outline, brand color)
- Escape key closes modals/dropdowns
- Arrow keys navigate lists/menus
- Enter/Space activates buttons

**Screen Reader Support:**
- Semantic HTML (nav, main, article, aside)
- ARIA labels for icons and buttons
  ```html
  <button aria-label="Close modal">
    <svg><!-- X icon --></svg>
  </button>
  ```
- ARIA live regions for dynamic updates
  ```html
  <div aria-live="polite" aria-atomic="true">
    Match score updated: Team Alpha 13 - Team Beta 8
  </div>
  ```
- ARIA roles for custom widgets (tabs, modals)
- Alt text for all images (descriptive, not redundant)

**Focus Management:**

**Critical Rule: Focus Return Pattern**

When a modal, drawer, dropdown, or any overlay closes, keyboard focus **MUST** return to the element that triggered it. This ensures:
- Keyboard users don't lose their place
- Screen reader users maintain context
- Meets WCAG 2.1 Success Criterion 2.4.3 (Focus Order)

**Implementation:**

```javascript
// Store triggering element reference
let triggerElement = null;

// On modal open
function openModal(event) {
    triggerElement = event.target; // Store the button that opened modal
    modal.showModal();
    trapFocus(modal); // Focus first interactive element in modal
}

// On modal close
function closeModal() {
    modal.close();
    if (triggerElement) {
        triggerElement.focus(); // Return focus to trigger
        triggerElement = null;
    }
}

// Example with ESC key
modal.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        closeModal(); // Handles focus return automatically
    }
});
```

**HTML Pattern:**

```html
<!-- Trigger button -->
<button id="register-btn" 
        onclick="openModal(event)" 
        data-analytics-id="dc-btn-register">
    Register Now
</button>

<!-- Modal -->
<dialog id="registration-modal" 
        aria-labelledby="modal-title" 
        aria-describedby="modal-description">
    <!-- Modal content -->
    <button onclick="closeModal()" 
            data-analytics-id="dc-modal-close">
        Close
    </button>
</dialog>
```

**Focus Return Checklist:**

| Component | Trigger Example | Focus Return Target |
|-----------|----------------|---------------------|
| Modal | "Register Now" button | Same button |
| Dropdown | "Game Filter ▼" | Dropdown toggle button |
| Drawer | "☰ Menu" (mobile) | Menu icon button |
| Tooltip | Icon button (hover/focus) | Same icon button |
| Dialog | "Delete Tournament" | Delete button (or cancel if deleted) |

**Additional Focus Rules:**
- **Focus Trap:** Within modals, Tab cycles only through focusable modal elements (no escape to background)
- **First Focus:** When modal opens, focus moves to first interactive element (Close button or primary input)
- **Skip Links:** Provide "Skip to main content" link (visible on focus) for keyboard users
- **Logical Order:** Tab order follows visual reading order (left-to-right, top-to-bottom)

**Heading Hierarchy:**
- Single H1 per page
- Logical H2-H6 nesting (no skipping levels)
- Use headings for structure, not styling

**Form Accessibility:**
- Labels explicitly associated with inputs
  ```html
  <label for="tournament-name">Tournament Name</label>
  <input id="tournament-name" type="text" required aria-required="true">
  ```
- Error messages linked via aria-describedby
- Required fields indicated (*, aria-required)
- Fieldsets for grouped inputs (radio buttons)

**Mobile Form Optimization:**

Use the `inputmode` attribute to trigger the optimal mobile keyboard layout for each input type. This improves user experience on touch devices without changing the input's semantic type.

**`inputmode` Reference Table:**

| Field Type | `inputmode` Value | Keyboard Layout | Example |
|------------|-------------------|-----------------|---------|
| Phone Number | `numeric` | Numeric keypad (0-9, +, -, *, #) | `<input type="tel" inputmode="numeric">` |
| Email Address | `email` | Email keyboard (@, .com shortcuts) | `<input type="email" inputmode="email">` |
| URL/Website | `url` | URL keyboard (.com, /, :) | `<input type="url" inputmode="url">` |
| Search Field | `search` | Search keyboard (Go/Search button) | `<input type="search" inputmode="search">` |
| Decimal Number | `decimal` | Numeric with decimal point | `<input type="text" inputmode="decimal">` |
| Integer | `numeric` | Numeric only (no decimal) | `<input type="text" inputmode="numeric">` |
| Text (default) | `text` | Full QWERTY keyboard | `<input type="text" inputmode="text">` |

**Implementation Examples:**

```html
<!-- Tournament Registration Form -->

<!-- Player Phone (Bangladesh format: +880XXXXXXXXXX) -->
<label for="player-phone">Phone Number</label>
<input type="tel" 
       id="player-phone" 
       inputmode="numeric" 
       placeholder="+880XXXXXXXXXX"
       pattern="[+]?[0-9]{11,14}"
       data-analytics-id="dc-input-phone">

<!-- Player Email -->
<label for="player-email">Email Address</label>
<input type="email" 
       id="player-email" 
       inputmode="email" 
       placeholder="player@example.com"
       required
       data-analytics-id="dc-input-email">

<!-- In-Game ID (alphanumeric) -->
<label for="game-id">VALORANT In-Game ID</label>
<input type="text" 
       id="game-id" 
       inputmode="text" 
       placeholder="PlayerName#TAG"
       pattern="[A-Za-z0-9]+#[A-Za-z0-9]+"
       data-analytics-id="dc-input-game-id">

<!-- Team Fee (entry fee amount) -->
<label for="entry-fee">Entry Fee (৳)</label>
<input type="text" 
       id="entry-fee" 
       inputmode="numeric" 
       placeholder="500"
       pattern="[0-9]+"
       data-analytics-id="dc-input-fee">

<!-- Discord Server URL -->
<label for="discord-url">Discord Server</label>
<input type="url" 
       id="discord-url" 
       inputmode="url" 
       placeholder="https://discord.gg/xxxxx"
       data-analytics-id="dc-input-discord">

<!-- Tournament Search -->
<label for="tournament-search">Search Tournaments</label>
<input type="search" 
       id="tournament-search" 
       inputmode="search" 
       placeholder="VALORANT, CS2, PUBG..."
       data-analytics-id="dc-search-tournament">
```

**Mobile Keyboard Best Practices:**

1. **Always use `inputmode` for numeric inputs** (phone, age, rank, score, fee)
2. **Pair with `pattern` attribute** for client-side validation
3. **Use `type="tel"` with `inputmode="numeric"`** for phone numbers (enables numeric keyboard on all devices)
4. **Avoid `type="number"`** for non-arithmetic values (ID, phone) — it adds spinner buttons and breaks formatting
5. **Test on iOS Safari and Android Chrome** — keyboard layouts vary slightly

**Mobile Form UX Enhancements:**

```html
<!-- Auto-scroll active input above keyboard -->
<script>
document.querySelectorAll('input, textarea, select').forEach(input => {
    input.addEventListener('focus', () => {
        setTimeout(() => {
            input.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
        }, 300); // Wait for keyboard animation
    });
});
</script>

<!-- Disable zoom on input focus (iOS Safari fix) -->
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<!-- Note: Only use if inputs have font-size >= 16px to prevent auto-zoom -->
```

**Form Field Sizing for Mobile:**

- **Input Height:** Minimum 44px (iOS touch target guideline)
- **Font Size:** Minimum 16px (prevents auto-zoom on iOS)
- **Padding:** 12px vertical, 16px horizontal
- **Tap Target Spacing:** 8px between clickable elements

**Motion & Animation:**
- Respect prefers-reduced-motion
  ```css
  @media (prefers-reduced-motion: reduce) {
    * {
      animation-duration: 0.01ms !important;
      transition-duration: 0.01ms !important;
    }
  }
  ```
- Pause/stop controls for auto-playing content
- No flashing content >3 times per second

**Content Accessibility:**
- Plain language, avoid jargon
- Instructions don't rely solely on color ("Click the blue button" → "Click the Register button")
- Sufficient line height (1.5 for body text)
- Text resizable up to 200% without loss of functionality

**Testing Checklist:**
- ✅ Test with screen reader (NVDA, JAWS, VoiceOver)
- ✅ Test keyboard-only navigation
- ✅ Test with browser zoom at 200%
- ✅ Test with color blindness simulators
- ✅ Automated testing (axe, Lighthouse)

---

## 12. Animation & Interaction Patterns

### Animation Principles

**Purpose of Animation:**
1. **Feedback:** Confirm user actions (button click, form submit)
2. **Attention:** Draw eye to important elements (live badge, new message)
3. **Relationship:** Show how elements connect (modal from button)
4. **Continuity:** Smooth transitions between states

**Duration Guidelines:**

```css
/* Instant feedback (hover, focus) */
--duration-instant: 100ms;

/* Quick interactions (dropdowns, tooltips) */
--duration-fast: 150ms;

/* Standard transitions (page elements) */
--duration-base: 250ms;

/* Complex animations (modals, slides) */
--duration-slow: 350ms;

/* Page transitions */
--duration-slower: 500ms;
```

**Easing Functions:**

```css
/* Natural deceleration (exiting) */
--ease-out: cubic-bezier(0, 0, 0.2, 1);

/* Natural acceleration (entering) */
--ease-in: cubic-bezier(0.4, 0, 1, 1);

/* Standard (most interactions) */
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);

/* Bouncy (playful interactions) */
--ease-bounce: cubic-bezier(0.68, -0.55, 0.265, 1.55);
```

### Specific Animations

**1. Button Click**
```css
.btn:active {
    transform: scale(0.98);
    transition: transform 100ms ease-out;
}
```

**2. Card Hover**
```css
.card {
    transition: all 250ms ease-out;
}
.card:hover {
    transform: translateY(-4px);
    box-shadow: var(--shadow-lg);
}
```

**3. Modal Appear**
```css
.modal {
    animation: modal-appear 300ms ease-out;
}

@keyframes modal-appear {
    from {
        opacity: 0;
        transform: scale(0.95) translateY(-20px);
    }
    to {
        opacity: 1;
        transform: scale(1) translateY(0);
    }
}
```

**4. Toast Notification**
```css
.toast {
    animation: toast-slide-in 250ms ease-out;
}

@keyframes toast-slide-in {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}
```

**5. Live Badge Pulse**
```css
.badge-live {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
    0%, 100% {
        opacity: 1;
    }
    50% {
        opacity: 0.5;
    }
}
```

**6. Skeleton Loading**
```css
.skeleton {
    animation: skeleton-loading 1.5s ease-in-out infinite;
}

@keyframes skeleton-loading {
    0% {
        background-position: 200% 0;
    }
    100% {
        background-position: -200% 0;
    }
}
```

**7. Page Transition (HTMX)**
```css
.htmx-swapping {
    opacity: 0;
    transition: opacity 200ms ease-out;
}

.htmx-settling {
    opacity: 1;
    transition: opacity 200ms ease-in;
}
```

**8. Success Checkmark**
```css
.checkmark {
    animation: checkmark-pop 400ms cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

@keyframes checkmark-pop {
    0% {
        transform: scale(0);
        opacity: 0;
    }
    50% {
        transform: scale(1.1);
    }
    100% {
        transform: scale(1);
        opacity: 1;
    }
}
```

---

### Real-Time Flow Animations

**Purpose:** Smooth, non-disruptive transitions for live data updates (scores, brackets, notifications).

**9. Score Update (Live Match)**
```css
/* Score changes with highlight flash - 200ms fade as specified */
.score-update {
    animation: score-flash 200ms ease-out;
}

@keyframes score-flash {
    0% {
        background-color: var(--brand-primary);
        transform: scale(1.05);
    }
    100% {
        background-color: transparent;
        transform: scale(1);
    }
}

/* Score transition timing */
.score-value {
    transition: all 200ms ease-out;
}
```

**10. Bracket Update (Match Result)**
```css
/* Bracket node update - 300ms smooth transition */
.bracket-match {
    transition: all 300ms ease-in-out;
}

.bracket-match.updated {
    animation: bracket-highlight 300ms ease-out;
}

@keyframes bracket-highlight {
    0% {
        background-color: var(--success);
        box-shadow: 0 0 20px var(--success);
    }
    100% {
        background-color: var(--bg-secondary);
        box-shadow: var(--shadow-base);
    }
}

/* Winner line animation - 400ms draw */
.bracket-line {
    stroke-dasharray: 100;
    stroke-dashoffset: 100;
    animation: draw-line 400ms ease-out forwards;
}

@keyframes draw-line {
    to {
        stroke-dashoffset: 0;
    }
}
```

**11. Live Badge Pulsing**
```css
/* Live indicator pulse - 2s infinite as defined above */
.badge-live {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.badge-live-dot {
    animation: pulse-dot 1.5s ease-in-out infinite;
}

@keyframes pulse-dot {
    0%, 100% {
        transform: scale(1);
        opacity: 1;
    }
    50% {
        transform: scale(1.2);
        opacity: 0.8;
    }
}
```

**12. Notification Toast (Real-time)**
```css
/* Toast slide-in from right - 250ms */
.toast-realtime {
    animation: toast-slide-in 250ms ease-out;
}

@keyframes toast-slide-in {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* Auto-dismiss after 5s */
.toast-realtime.dismissing {
    animation: toast-fade-out 300ms ease-in forwards;
}

@keyframes toast-fade-out {
    to {
        opacity: 0;
        transform: translateX(50px);
    }
}
```

**13. Participant Count Update**
```css
/* Registration counter increment - 150ms */
.participant-count {
    transition: transform 150ms ease-out;
}

.participant-count.updated {
    animation: count-bump 150ms ease-out;
}

@keyframes count-bump {
    0%, 100% {
        transform: scale(1);
    }
    50% {
        transform: scale(1.15);
    }
}
```

**14. New Message Indicator**
```css
/* New message badge bounce - 400ms */
.message-badge-new {
    animation: badge-bounce 400ms cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

@keyframes badge-bounce {
    0% {
        transform: scale(0);
    }
    50% {
        transform: scale(1.2);
    }
    100% {
        transform: scale(1);
    }
}
```

**15. Confetti Animation (Result Publish)**
```css
/* Confetti burst on tournament completion - 1.5s */
.confetti-piece {
    animation: confetti-fall 1.5s ease-out forwards;
}

@keyframes confetti-fall {
    0% {
        transform: translateY(-100vh) rotate(0deg);
        opacity: 1;
    }
    100% {
        transform: translateY(100vh) rotate(720deg);
        opacity: 0;
    }
}

/* Stagger confetti pieces with delay */
.confetti-piece:nth-child(2n) {
    animation-delay: 100ms;
}
.confetti-piece:nth-child(3n) {
    animation-delay: 200ms;
}
```

**Animation Timing Summary Table:**

| Element | Duration | Easing | Use Case |
|---------|----------|--------|----------|
| Score Update | 200ms | ease-out | Live match score changes |
| Bracket Update | 300ms | ease-in-out | Match result propagation |
| Winner Line Draw | 400ms | ease-out | Bracket advancement animation |
| Live Badge Pulse | 2s (infinite) | cubic-bezier | Continuous live indicator |
| Toast Notification | 250ms | ease-out | Real-time alerts |
| Participant Count | 150ms | ease-out | Registration counter |
| Message Badge | 400ms | bounce | New message indicator |
| Confetti | 1.5s | ease-out | Celebration animation |

**Reduced Motion Support:**
```css
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
    }
    
    /* Keep essential live indicators but remove decorative animations */
    .badge-live {
        animation: none;
        opacity: 1;
    }
}
```

---

### WebSocket Real-Time Update Strategy

**HTMX WebSocket Integration:**

```html
<!-- Live score updates -->
<div hx-ext="ws" ws-connect="/ws/match/123">
    <div class="score-display" ws-receive="updateScore">
        <span class="score-value">0</span>
    </div>
</div>

<script>
// JavaScript handler for smooth transitions
document.body.addEventListener('ws-receive', function(event) {
    if (event.detail.type === 'score_update') {
        const scoreElement = event.target.querySelector('.score-value');
        scoreElement.classList.add('score-update'); // Triggers 200ms animation
        
        setTimeout(() => {
            scoreElement.classList.remove('score-update');
        }, 200);
    }
});
</script

@keyframes checkmark-pop {
    0% {
        transform: scale(0);
        opacity: 0;
    }
    50% {
        transform: scale(1.1);
    }
    100% {
        transform: scale(1);
        opacity: 1;
    }
}
```

**9. Score Update (Live Match)**
```css
.score-update {
    animation: score-flash 500ms ease-out;
}

@keyframes score-flash {
    0%, 100% {
        background: transparent;
    }
    50% {
        background: rgba(59, 130, 246, 0.3);
        transform: scale(1.05);
    }
}
```

**10. Countdown Timer**
```css
.countdown.urgent {
    animation: countdown-pulse 1s ease-in-out infinite;
}

@keyframes countdown-pulse {
    0%, 100% {
        color: var(--error);
        transform: scale(1);
    }
    50% {
        color: var(--warning);
        transform: scale(1.05);
    }
}
```

### Microinteractions

**Form Validation:**
- ❌ Error shake: 3 quick left-right movements
- ✅ Success bounce: Checkmark pops in with slight overshoot
- ⚠️ Warning glow: Subtle pulsing border

**Loading States:**
- Button: Spinner replaces text, button expands slightly
- Page: Skeleton loaders mimic final content structure
- Infinite scroll: Spinner appears at bottom, smooth fade-in of new content

**Real-time Updates:**
- New notification: Badge number increments with pop animation
- Score update: Flash background, number counts up smoothly
- Match start: "LIVE" badge fades in with glow effect

**Navigation:**
- Tab switch: Content slides left/right
- Page change: Fade out old, fade in new (200ms overlap)
- Dropdown: Slide down with slight fade-in

---

---

## 13. Performance & Asset Strategy

### 13.1 Image Guidelines

**Image Format Priorities:**

1. **WebP (Preferred)**
   - Use for all modern browsers (95%+ support)
   - Fallback to JPG/PNG for legacy browsers
   - Example:
     ```html
     <picture>
         <source srcset="banner.webp" type="image/webp">
         <img src="banner.jpg" alt="Tournament banner">
     </picture>
     ```

2. **Responsive Images (srcset)**
   - Serve different sizes based on viewport
   - Reduce bandwidth on mobile
   - Example:
     ```html
     <img 
         srcset="banner-320w.webp 320w,
                 banner-640w.webp 640w,
                 banner-1280w.webp 1280w,
                 banner-1920w.webp 1920w"
         sizes="(max-width: 768px) 100vw,
                (max-width: 1024px) 50vw,
                33vw"
         src="banner-1280w.webp"
         alt="Tournament banner"
     >
     ```

**Image Size Guidelines:**

| Asset Type | Dimensions | Max Size | Format | Lazy Load? |
|------------|------------|----------|--------|------------|
| Tournament Banner | 1920x1080 | 200 KB | WebP | No (hero) |
| Tournament Card Thumbnail | 640x360 | 50 KB | WebP | Yes |
| Team Logo | 200x200 | 20 KB | WebP/PNG | Yes |
| Player Avatar | 128x128 | 10 KB | WebP | Yes |
| Certificate Background | 1920x1080 (300 DPI for print) | 500 KB | WebP (screen), PDF (print) | N/A |
| Sponsor Logo | 400x200 | 30 KB | WebP/PNG | Yes |
| Payment Screenshot | Original (max 5MB) | 5 MB | JPG/PNG | No |

**Lazy Loading Strategy:**

```html
<!-- Above fold (eager) -->
<img src="hero-banner.webp" alt="Hero" loading="eager">

<!-- Below fold (lazy) -->
<img src="tournament-card.webp" alt="Tournament" loading="lazy">
```

**Image Optimization Tools:**
- Build-time: `imagemin` (Webpack/Vite plugin)
- Runtime: `django-imagekit` for on-the-fly resizing
- CDN: Cloudflare Image Resizing or Cloudinary

### 13.2 CSS Splitting & Critical CSS

**Critical CSS Strategy:**

1. **Inline Critical CSS** (first paint)
   - Above-the-fold styles only
   - Navbar, hero section, primary CTA
   - Max 14 KB inline
   - Example:
     ```html
     <head>
         <style>/* Critical CSS inline */</style>
         <link rel="preload" href="main.css" as="style" onload="this.onload=null;this.rel='stylesheet'">
         <noscript><link rel="stylesheet" href="main.css"></noscript>
     </head>
     ```

2. **Split CSS by Route**
   - `base.css` — Global styles, design tokens (always loaded)
   - `tournaments.css` — Tournament-specific styles
   - `dashboard.css` — Dashboard-specific styles
   - `bracket.css` — Bracket visualization (large, isolated)
   - Use Django's `{% static %}` with cache busting

3. **Purge Unused CSS**
   - PurgeCSS or Tailwind's built-in purging
   - Remove unused Tailwind classes in production
   - Scan templates: `templates/**/*.html`
   - Reduce Tailwind from ~3MB to ~50KB

**Loading Priorities:**

```html
<!-- High priority (critical resources) -->
<link rel="preload" href="fonts/inter.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="hero-banner.webp" as="image">

<!-- Medium priority (async scripts) -->
<script src="htmx.min.js" defer></script>
<script src="alpine.min.js" defer></script>

<!-- Low priority (analytics) -->
<script src="analytics.js" async></script>
```

### 13.3 JavaScript Bundle Strategy

**Bundle Splitting:**

1. **Vendor Bundle** (`vendor.js`)
   - HTMX, Alpine.js, Chart.js
   - Cached long-term (versioned filename)
   - ~50 KB gzipped

2. **App Bundle** (`app.js`)
   - Custom JavaScript (form validation, WebSocket handlers)
   - ~20 KB gzipped

3. **Route-Specific Bundles**
   - `bracket.js` — Bracket visualization logic (loaded only on bracket pages)
   - `payment.js` — Payment form handlers

**Tree Shaking:**
- Remove unused exports
- Use ES modules (not CommonJS)
- Webpack/Vite automatically tree-shakes

**Code Splitting Example:**

```javascript
// Dynamic import for bracket
document.querySelector('[data-bracket]').addEventListener('click', async () => {
    const { initBracket } = await import('./bracket.js');
    initBracket();
});
```

### 13.4 Performance Budgets

**Target Metrics (Lighthouse):**

| Metric | Target | Acceptable | Tools |
|--------|--------|------------|-------|
| First Contentful Paint (FCP) | < 1.5s | < 2.5s | Lighthouse, WebPageTest |
| Largest Contentful Paint (LCP) | < 2.5s | < 4.0s | Core Web Vitals |
| Time to Interactive (TTI) | < 3.5s | < 5.0s | Lighthouse |
| Cumulative Layout Shift (CLS) | < 0.1 | < 0.25 | Core Web Vitals |
| Total Bundle Size | < 200 KB | < 400 KB | Webpack Bundle Analyzer |

**Performance Checklist:**

- ✅ Enable Gzip/Brotli compression (server-side)
- ✅ Set cache headers (static assets: 1 year, HTML: no-cache)
- ✅ Use HTTP/2 or HTTP/3
- ✅ Minify HTML, CSS, JS in production
- ✅ Defer non-critical JavaScript
- ✅ Preconnect to third-party domains (Google Fonts, CDN)
- ✅ Use `font-display: swap` to prevent invisible text
- ✅ Avoid layout shifts (set width/height on images)
- ✅ Use `will-change` sparingly (only for animated elements)

**Django Template Optimization:**

```django
{# Load static with cache busting #}
{% load static %}
<link rel="stylesheet" href="{% static 'css/main.css' %}?v={{ version }}">

{# Conditional loading #}
{% if user.is_organizer %}
    <script src="{% static 'js/organizer.js' %}" defer></script>
{% endif %}
```

---

## 14. Analytics & Tracking Strategy

### 14.1 Analytics Attribute Naming Convention

**Purpose:** Consistent `data-analytics-id` naming enables comprehensive tracking of user behavior, conversion funnels, and feature adoption without coupling to CSS classes or changing HTML structure.

**Naming Pattern:**

```
data-analytics-id="dc-{component-type}-{action|element}-{context}"
```

**Component Types:**

| Prefix | Component | Example |
|--------|-----------|---------|
| `dc-btn-` | Buttons | `dc-btn-register`, `dc-btn-submit-payment` |
| `dc-link-` | Links | `dc-link-tournament-detail`, `dc-link-view-bracket` |
| `dc-modal-` | Modals | `dc-modal-payment-submission`, `dc-modal-contact-organizer` |
| `dc-form-` | Forms | `dc-form-registration`, `dc-form-create-tournament` |
| `dc-input-` | Form Inputs | `dc-input-team-name`, `dc-input-phone` |
| `dc-card-` | Cards | `dc-card-tournament`, `dc-card-match-result` |
| `dc-nav-` | Navigation | `dc-nav-tournaments`, `dc-nav-profile` |
| `dc-filter-` | Filters | `dc-filter-game`, `dc-filter-date-range` |
| `dc-tab-` | Tabs | `dc-tab-upcoming`, `dc-tab-completed` |
| `dc-badge-` | Badges | `dc-badge-live`, `dc-badge-featured` |
| `dc-dropdown-` | Dropdowns | `dc-dropdown-sort`, `dc-dropdown-language` |
| `dc-search-` | Search | `dc-search-tournament`, `dc-search-player` |
| `dc-toggle-` | Toggles | `dc-toggle-dark-mode`, `dc-toggle-notifications` |
| `dc-icon-` | Icon Buttons | `dc-icon-share`, `dc-icon-favorite` |
| `dc-alert-` | Alerts | `dc-alert-payment-rejected`, `dc-alert-check-in-reminder` |

**Context-Specific Naming:**

```html
<!-- Tournament Registration Flow -->
<button data-analytics-id="dc-btn-register-tournament-detail">
    Register Now
</button>

<button data-analytics-id="dc-btn-register-tournament-card">
    Register
</button>

<!-- Payment Actions -->
<button data-analytics-id="dc-btn-submit-payment-initial">
    Submit Payment
</button>

<button data-analytics-id="dc-btn-resubmit-payment-rejected">
    Resubmit Payment
</button>

<!-- Contact Organizer (context-aware) -->
<button data-analytics-id="dc-btn-contact-organizer-header">
    Contact Organizer
</button>

<button data-analytics-id="dc-btn-contact-organizer-payment-rejected">
    Contact Organizer
</button>

<!-- Social Sharing -->
<button data-analytics-id="dc-btn-share-certificate-facebook">
    Share on Facebook
</button>

<button data-analytics-id="dc-btn-share-certificate-twitter">
    Share on Twitter
</button>
```

**Comprehensive Examples by Component:**

**1. Tournament Listing Page:**

```html
<!-- Search -->
<input data-analytics-id="dc-search-tournament-listing" 
       type="search" 
       placeholder="Search tournaments...">

<!-- Filters -->
<select data-analytics-id="dc-filter-game-selection">
    <option>VALORANT</option>
    <option>CS2</option>
</select>

<input data-analytics-id="dc-filter-date-range-start" 
       type="date">

<!-- Tournament Card -->
<div data-analytics-id="dc-card-tournament-${tournament.id}" 
     data-tournament-id="${tournament.id}"
     data-tournament-status="${tournament.status}">
    
    <a data-analytics-id="dc-link-tournament-detail-${tournament.id}" 
       href="/tournaments/${tournament.slug}">
        View Tournament
    </a>
    
    <button data-analytics-id="dc-btn-register-card-${tournament.id}">
        Register Now
    </button>
</div>

<!-- Sort Dropdown -->
<select data-analytics-id="dc-dropdown-sort-tournaments">
    <option value="date">Start Date</option>
    <option value="prize">Prize Pool</option>
</select>
```

**2. Registration Form:**

```html
<form data-analytics-id="dc-form-registration-${tournament.id}"
      data-tournament-id="${tournament.id}">
    
    <!-- Team Name Input -->
    <input data-analytics-id="dc-input-team-name" 
           id="team-name" 
           name="team_name">
    
    <!-- Player Fields -->
    <input data-analytics-id="dc-input-player-ign-1" 
           name="player1_ign"
           inputmode="text">
    
    <input data-analytics-id="dc-input-player-phone-1" 
           name="player1_phone"
           inputmode="numeric">
    
    <!-- Submit Button -->
    <button data-analytics-id="dc-btn-submit-registration" 
            type="submit">
        Submit Entry
    </button>
    
    <!-- Help Link -->
    <button data-analytics-id="dc-btn-contact-organizer-registration">
        Need help?
    </button>
</form>
```

**3. Payment Submission:**

```html
<!-- Payment Method Selection -->
<div data-analytics-id="dc-form-payment-submission">
    <button data-analytics-id="dc-btn-payment-method-bkash">
        bKash
    </button>
    
    <button data-analytics-id="dc-btn-payment-method-nagad">
        Nagad
    </button>
    
    <!-- File Upload -->
    <input data-analytics-id="dc-input-payment-proof-upload" 
           type="file" 
           accept="image/*">
    
    <!-- Transaction ID -->
    <input data-analytics-id="dc-input-transaction-id" 
           name="transaction_id">
    
    <!-- Submit -->
    <button data-analytics-id="dc-btn-submit-payment">
        Submit Payment
    </button>
</div>
```

**4. Match Result Submission:**

```html
<form data-analytics-id="dc-form-match-result-${match.id}"
      data-match-id="${match.id}">
    
    <!-- Score Inputs -->
    <input data-analytics-id="dc-input-score-team-a" 
           name="score_team_a"
           inputmode="numeric">
    
    <input data-analytics-id="dc-input-score-team-b" 
           name="score_team_b"
           inputmode="numeric">
    
    <!-- Proof Upload -->
    <input data-analytics-id="dc-input-match-proof-upload" 
           type="file">
    
    <!-- Submit -->
    <button data-analytics-id="dc-btn-submit-match-result">
        Submit Result
    </button>
    
    <!-- Dispute -->
    <button data-analytics-id="dc-btn-dispute-match-result">
        Dispute Result
    </button>
</form>
```

**5. Certificate Actions:**

```html
<!-- Certificate View -->
<div data-analytics-id="dc-page-certificate-${certificate.id}"
     data-certificate-id="${certificate.id}">
    
    <!-- Download -->
    <button data-analytics-id="dc-btn-download-certificate">
        Download Certificate
    </button>
    
    <!-- Share Options -->
    <button data-analytics-id="dc-btn-share-certificate-facebook">
        Share on Facebook
    </button>
    
    <button data-analytics-id="dc-btn-share-certificate-twitter">
        Share on Twitter
    </button>
    
    <button data-analytics-id="dc-btn-share-certificate-linkedin">
        Share on LinkedIn
    </button>
    
    <button data-analytics-id="dc-btn-copy-certificate-link">
        Copy Link
    </button>
</div>
```

**6. Spectator View:**

```html
<!-- Predictions -->
<button data-analytics-id="dc-btn-predict-team-a-${match.id}"
        data-match-id="${match.id}"
        data-team-id="${team_a.id}">
    Predict Team A Wins
</button>

<!-- MVP Voting -->
<button data-analytics-id="dc-btn-vote-mvp-${player.id}"
        data-match-id="${match.id}"
        data-player-id="${player.id}">
    Vote MVP
</button>

<!-- Live Chat -->
<form data-analytics-id="dc-form-live-chat-message">
    <input data-analytics-id="dc-input-live-chat">
    <button data-analytics-id="dc-btn-send-live-chat">Send</button>
</form>
```

**7. Community Discussions:**

```html
<!-- Create Thread -->
<button data-analytics-id="dc-btn-create-discussion-thread">
    Start Discussion
</button>

<!-- Thread Interactions -->
<button data-analytics-id="dc-btn-reply-thread-${thread.id}">
    Reply
</button>

<!-- Reactions -->
<button data-analytics-id="dc-btn-react-comment-thumbsup-${comment.id}"
        data-reaction="thumbsup">
    👍
</button>

<!-- Pin Comment (Moderator) -->
<button data-analytics-id="dc-btn-pin-comment-${comment.id}">
    Pin Comment
</button>
```

**8. Admin Actions:**

```html
<!-- Payment Verification -->
<button data-analytics-id="dc-admin-btn-approve-payment-${payment.id}">
    Approve Payment
</button>

<button data-analytics-id="dc-admin-btn-reject-payment-${payment.id}">
    Reject Payment
</button>

<!-- Activity Log -->
<button data-analytics-id="dc-admin-btn-export-activity-log">
    Export CSV
</button>

<!-- Certificate Issuance -->
<button data-analytics-id="dc-admin-btn-issue-certificates-${tournament.id}">
    Issue Certificates
</button>
```

**Additional Tracking Attributes:**

```html
<!-- Add contextual metadata -->
<button data-analytics-id="dc-btn-register"
        data-tournament-id="123"
        data-tournament-status="REGISTRATION_OPEN"
        data-entry-fee="500"
        data-game="valorant"
        data-user-role="player">
    Register Now
</button>
```

**Event Tracking Schema:**

| Event Category | Action | Label | Value |
|----------------|--------|-------|-------|
| Tournament | Click Register | Tournament ID | Entry Fee |
| Payment | Submit Payment | Payment Method | Amount |
| Match | Submit Result | Match ID | Winner Team ID |
| Certificate | Download | Certificate ID | Tournament ID |
| Social | Share Certificate | Platform | Certificate ID |
| Admin | Approve Payment | Payment ID | Amount |
| Community | Create Thread | Tournament ID | - |
| Spectator | Predict Winner | Match ID | Team ID |

**Google Analytics 4 Implementation Example:**

```javascript
// Send event on button click
document.querySelectorAll('[data-analytics-id]').forEach(element => {
    element.addEventListener('click', (e) => {
        const analyticsId = e.currentTarget.dataset.analyticsId;
        const [prefix, component, action, context] = analyticsId.split('-');
        
        // Send to GA4
        gtag('event', action, {
            'event_category': component,
            'event_label': context || 'default',
            'element_id': analyticsId,
            'tournament_id': e.currentTarget.dataset.tournamentId,
            'user_role': e.currentTarget.dataset.userRole
        });
    });
});
```

**Analytics Dashboard Metrics to Track:**

- **Conversion Funnels:**
  - Tournament view → Registration start → Registration complete → Payment submit → Payment approved
- **Feature Adoption:**
  - Certificate downloads, social shares, predictions, MVP votes
- **User Engagement:**
  - Spectator view time, live chat messages, discussion threads
- **Admin Efficiency:**
  - Payment verification time, certificate issuance rate
- **Drop-off Points:**
  - Where users abandon registration, payment submission failures

---

## Conclusion

This UI/UX Design Specification provides a comprehensive blueprint for implementing the DeltaCrown Tournament Engine interface. Key deliverables include:

**✅ Design System Foundation**
- Complete color palette (40+ tokens)
- Typography system with 10 size scales
- Spacing, border radius, shadows, and grid system
- 50+ CSS custom properties for consistency

**✅ Component Library**
- 20+ reusable components with variants
- Comprehensive HTML/CSS patterns
- Accessibility baked into every component
- Responsive behaviors documented

**✅ Screen Designs (20+ Screens)**
- **Tournament Management:** Listing, detail, creation wizard, organizer dashboard
- **Registration & Payment:** Multi-step forms, payment submission, confirmation
- **Bracket & Matches:** Interactive bracket, live match page, result submission
- **Player Experience:** Dashboard, history, certificates, profile integration
- **Spectator & Community:** Live spectator view, discussions, social features

**✅ Mobile Design Patterns**
- Bottom sheets, sticky CTAs, swipe gestures
- Touch-optimized controls (44px minimum)
- Offline capabilities and mobile navigation

**✅ Accessibility Guidelines**
- WCAG 2.1 Level AA compliance
- Keyboard navigation and screen reader support
- Focus management and color contrast
- Testing checklist included

**✅ Animation & Interactions**
- 10 specific animations with code
- Duration and easing guidelines
- Microinteraction patterns
- Motion accessibility (prefers-reduced-motion)

**Implementation Notes:**
- All designs use Tailwind CSS + custom properties
- HTMX patterns included for dynamic updates
- Alpine.js for client-side interactivity
- Django Templates structure maintained
- WebSocket integration points identified

**Total Documented:**
- 40+ custom CSS properties
- 20+ reusable components
- 20+ screens with full specifications
- 10+ animation patterns
- 100+ interaction states

This specification ensures visual consistency, accessibility, and exceptional user experience across all touchpoints of the DeltaCrown Tournament Engine.

---

---

## 14. Handoff Materials

### 14.1 Design Token Map (JSON)

**Purpose:** Machine-readable token definitions for automatic Tailwind config generation.

**File:** `design-tokens.json`

```json
{
  "colors": {
    "bg": {
      "primary": "#0A0E1A",
      "secondary": "#151928",
      "tertiary": "#1F2937",
      "hover": "#2D3748"
    },
    "brand": {
      "primary": "#3B82F6",
      "secondary": "#8B5CF6",
      "accent": "#F59E0B"
    },
    "semantic": {
      "success": "#10B981",
      "warning": "#F59E0B",
      "error": "#EF4444",
      "info": "#3B82F6"
    },
    "neon": {
      "cyan": "#06B6D4",
      "magenta": "#EC4899",
      "lime": "#84CC16"
    },
    "text": {
      "primary": "#F9FAFB",
      "secondary": "#9CA3AF",
      "tertiary": "#6B7280",
      "disabled": "#4B5563"
    },
    "border": {
      "primary": "#374151",
      "secondary": "#1F2937",
      "accent": "#3B82F6"
    }
  },
  "typography": {
    "fontFamily": {
      "primary": "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      "heading": "'Outfit', 'Inter', sans-serif",
      "mono": "'Fira Code', 'Courier New', monospace",
      "bengali": "'Noto Sans Bengali', sans-serif"
    },
    "fontSize": {
      "xs": "0.75rem",
      "sm": "0.875rem",
      "base": "1rem",
      "lg": "1.125rem",
      "xl": "1.25rem",
      "2xl": "1.5rem",
      "3xl": "1.875rem",
      "4xl": "2.25rem",
      "5xl": "3rem"
    },
    "fontWeight": {
      "normal": 400,
      "medium": 500,
      "semibold": 600,
      "bold": 700,
      "black": 900
    },
    "lineHeight": {
      "tight": 1.25,
      "normal": 1.5,
      "relaxed": 1.75
    }
  },
  "spacing": {
    "0": "0",
    "1": "0.25rem",
    "2": "0.5rem",
    "3": "0.75rem",
    "4": "1rem",
    "5": "1.25rem",
    "6": "1.5rem",
    "8": "2rem",
    "10": "2.5rem",
    "12": "3rem",
    "16": "4rem",
    "20": "5rem",
    "24": "6rem"
  },
  "borderRadius": {
    "none": "0",
    "sm": "0.25rem",
    "base": "0.5rem",
    "lg": "0.75rem",
    "xl": "1rem",
    "2xl": "1.5rem",
    "full": "9999px"
  },
  "boxShadow": {
    "sm": "0 1px 2px 0 rgba(0, 0, 0, 0.3)",
    "base": "0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px 0 rgba(0, 0, 0, 0.3)",
    "md": "0 4px 6px -1px rgba(0, 0, 0, 0.4), 0 2px 4px -1px rgba(0, 0, 0, 0.3)",
    "lg": "0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.3)",
    "xl": "0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 10px 10px -5px rgba(0, 0, 0, 0.3)",
    "2xl": "0 25px 50px -12px rgba(0, 0, 0, 0.6)",
    "glow": {
      "primary": "0 0 20px rgba(59, 130, 246, 0.5)",
      "success": "0 0 20px rgba(16, 185, 129, 0.5)",
      "warning": "0 0 20px rgba(245, 158, 11, 0.5)",
      "live": "0 0 30px rgba(6, 182, 212, 0.7)"
    }
  },
  "animation": {
    "duration": {
      "instant": "100ms",
      "fast": "150ms",
      "base": "250ms",
      "slow": "350ms",
      "slower": "500ms"
    },
    "easing": {
      "in": "cubic-bezier(0.4, 0, 1, 1)",
      "out": "cubic-bezier(0, 0, 0.2, 1)",
      "inOut": "cubic-bezier(0.4, 0, 0.2, 1)",
      "bounce": "cubic-bezier(0.68, -0.55, 0.265, 1.55)"
    }
  },
  "breakpoints": {
    "sm": "640px",
    "md": "768px",
    "lg": "1024px",
    "xl": "1280px",
    "2xl": "1536px"
  }
}
```

**Tailwind Config Generation:**

```javascript
// tailwind.config.js (generated from tokens)
const designTokens = require('./design-tokens.json');

module.exports = {
  content: ['./templates/**/*.html', './static/**/*.js'],
  theme: {
    extend: {
      colors: designTokens.colors,
      fontFamily: designTokens.typography.fontFamily,
      fontSize: designTokens.typography.fontSize,
      // ... other tokens
    },
  },
  plugins: [],
};
```

---

### 14.2 Component Status Table

**Purpose:** Track implementation progress and blockers.

| Component | Status | Priority | Blocked By | Notes |
|-----------|--------|----------|------------|-------|
| **Design System** | | | | |
| Color Tokens | ✅ Ready | High | — | Design tokens.json |
| Typography Scale | ✅ Ready | High | — | |
| Spacing System | ✅ Ready | High | — | |
| **Buttons** | ✅ Ready | High | — | All variants documented |
| **Cards** | ✅ Ready | High | — | Tournament, Match cards |
| **Forms** | 🔄 Planned | High | — | Input, Select, Checkbox, Textarea |
| **Modals** | ✅ Ready | High | Alpine.js | Requires x-data binding |
| **Navigation** | ✅ Ready | High | — | Navbar, Breadcrumbs, Tabs |
| **Loading States** | ✅ Ready | Medium | — | Spinner, Skeleton, Progress |
| **Toasts** | 🔄 Planned | Medium | HTMX events | Trigger from HTMX responses |
| **Alerts** | ✅ Ready | Medium | — | Info, Success, Warning, Error |
| **Dropdowns** | 🔄 Planned | Medium | Alpine.js | Requires x-show directive |
| **Pagination** | ✅ Ready | Low | — | |
| **Tooltips** | ✅ Ready | Low | — | CSS-only, no JS |
| **Empty States** | ✅ Ready | Medium | — | All templates defined |
| **Error States** | ✅ Ready | High | — | Offline, Server, Validation |
| **Screens** | | | | |
| Tournament Listing | 🔄 Planned | High | — | HTMX infinite scroll |
| Tournament Detail | 🔄 Planned | High | WebSocket | Live count updates |
| Creation Wizard | 🔄 Planned | High | — | Multi-step form with Alpine |
| Organizer Dashboard | 🔄 Planned | High | — | Table + filters |
| Registration Form | 🔄 Planned | High | — | Multi-step modal |
| Payment Submission | 🔄 Planned | High | File upload | DeltaCoin integration |
| Confirmation Screen | ✅ Ready | High | — | |
| Bracket Visualization | ⏸️ Blocked | High | SVG lib | Need bracket library decision |
| Live Match Page | 🔄 Planned | High | WebSocket | Real-time score updates |
| Result Submission | ✅ Ready | Medium | — | |
| Player Dashboard | 🔄 Planned | Medium | — | |
| Certificate View | ✅ Ready | Medium | PDF lib | Verify PDF generation |
| Spectator View | 🔄 Planned | Low | — | |
| Community Discussions | ⏸️ Blocked | Low | Comment system | Need moderation tools |

**Legend:**
- ✅ **Ready:** Fully documented, ready for implementation
- 🔄 **Planned:** Documented, implementation pending
- ⏸️ **Blocked:** Waiting on dependency or decision
- ❌ **Deprecated:** No longer needed

---

### 14.3 Component → Django Template Convention

**Purpose:** Standardize file structure and naming for component templates.

**Directory Structure:**

```
templates/
├── components/               # Reusable components
│   ├── buttons/
│   │   ├── btn_primary.html
│   │   ├── btn_secondary.html
│   │   └── btn_loading.html
│   ├── cards/
│   │   ├── tournament_card.html
│   │   ├── match_card.html
│   │   └── empty_state.html
│   ├── forms/
│   │   ├── input.html
│   │   ├── select.html
│   │   └── textarea.html
│   ├── modals/
│   │   └── base_modal.html
│   └── nav/
│       ├── navbar.html
│       ├── breadcrumbs.html
│       └── tabs.html
├── tournament/               # App-specific pages
│   ├── list.html
│   ├── detail.html
│   ├── create.html
│   └── partials/            # HTMX partials
│       ├── tournament_card.html
│       └── filter_results.html
└── base.html                # Base layout
```

**Component Template Pattern:**

```django
{# templates/components/cards/tournament_card.html #}
{% load static %}

<article class="card card-tournament" data-tournament-id="{{ tournament.id }}">
    {# Card Image #}
    <div class="card-image">
        <img src="{{ tournament.banner.url }}" alt="{{ tournament.name }}" loading="lazy">
        {% if tournament.is_live %}
            <div class="card-badge card-badge-live">
                <span class="badge-dot"></span>
                LIVE
            </div>
        {% endif %}
    </div>
    
    {# Card Body #}
    <div class="card-body">
        <div class="card-meta">
            <span class="badge badge-game">{{ tournament.game.name }}</span>
            <span class="card-date">
                <svg class="icon-sm"><!-- Calendar icon --></svg>
                {{ tournament.start_date|date:"M d, Y" }}
            </span>
        </div>
        
        <h3 class="card-title">{{ tournament.name }}</h3>
        
        {# Stats #}
        <div class="card-stats">
            <div class="stat">
                <span class="stat-value">{{ tournament.max_teams }}</span>
                <span class="stat-label">Teams</span>
            </div>
            <div class="stat">
                <span class="stat-value">৳{{ tournament.prize_pool|floatformat:0 }}</span>
                <span class="stat-label">Prize Pool</span>
            </div>
            <div class="stat">
                <span class="stat-value">{{ tournament.registration_count }}/{{ tournament.max_teams }}</span>
                <span class="stat-label">Registered</span>
            </div>
        </div>
        
        {# Actions #}
        <div class="card-footer">
            <a href="{% url 'tournament:register' tournament.slug %}" class="btn btn-primary btn-sm">
                Register Now
            </a>
            <a href="{% url 'tournament:detail' tournament.slug %}" class="btn btn-ghost btn-sm">
                View Details
            </a>
        </div>
    </div>
</article>
```

**Include Component:**

```django
{# templates/tournament/list.html #}
{% extends "base.html" %}
{% load static %}

{% block content %}
<div class="container">
    <div class="tournament-grid">
        {% for tournament in tournaments %}
            {% include "components/cards/tournament_card.html" with tournament=tournament %}
        {% empty %}
            {% include "components/cards/empty_state.html" with title="No tournaments found" %}
        {% endfor %}
    </div>
</div>
{% endblock %}
```

**Slot Pattern (Advanced):**

```django
{# templates/components/modals/base_modal.html #}
<div class="modal-overlay" id="{{ modal_id }}" aria-hidden="true">
    <div class="modal" role="dialog">
        <div class="modal-header">
            <h2 class="modal-title">{{ modal_title }}</h2>
            <button class="modal-close" aria-label="Close modal">
                <svg class="icon-base"><!-- X icon --></svg>
            </button>
        </div>
        
        <div class="modal-body">
            {{ modal_body|safe }}  {# Slot for body content #}
        </div>
        
        <div class="modal-footer">
            {{ modal_footer|safe }}  {# Slot for footer actions #}
        </div>
    </div>
</div>
```

**Usage:**

```django
{% include "components/modals/base_modal.html" with modal_id="register-modal" modal_title="Register for Tournament" modal_body=registration_form modal_footer=action_buttons %}
```

**HTMX Partial Pattern:**

```django
{# templates/tournament/partials/filter_results.html #}
{# This partial is swapped via HTMX #}

{% for tournament in tournaments %}
    {% include "components/cards/tournament_card.html" with tournament=tournament %}
{% empty %}
    <div class="empty-state">
        <p>No tournaments match your filters.</p>
    </div>
{% endfor %}

{# Infinite scroll trigger #}
{% if has_next %}
<div hx-get="{% url 'tournament:list' %}?page={{ next_page }}" 
     hx-trigger="revealed" 
     hx-swap="afterend">
    <div class="loading">
        <div class="spinner"></div>
    </div>
</div>
{% endif %}
```

**Naming Conventions:**

- **Snake_case** for file names: `tournament_card.html`, `btn_primary.html`
- **kebab-case** for CSS classes: `card-tournament`, `btn-primary`
- **dc- prefix** for component classes: `dc-button-primary`, `dc-modal-payment`, `dc-card-tournament`
- **PascalCase** for Alpine.js components: `x-data="TournamentForm()"`
- **camelCase** for JavaScript variables: `const tournamentId = ...`
- **data-analytics-id** for tracking: `data-analytics-id="tournament_register_click"`

---

### 14.4 Storybook Checklist (Optional)

If using Storybook for component development:

**Storybook Stories to Create:**

- [ ] All button variants (primary, secondary, ghost, danger, loading, sizes)
- [ ] Card variants (tournament, match, empty, loading)
- [ ] Form elements (input, select, checkbox, radio, textarea) with all states
- [ ] Modal with different content lengths
- [ ] Toast notifications (success, error, warning, info)
- [ ] Loading states (spinner, skeleton, progress)
- [ ] Empty states (various contexts)
- [ ] Error states (offline, server, validation)
- [ ] Navigation components (navbar, breadcrumbs, tabs)

**Storybook Addons:**
- `@storybook/addon-a11y` — Accessibility testing
- `@storybook/addon-viewport` — Responsive testing
- `@storybook/addon-docs` — Auto-generate docs from stories

---

### 14.5 Analytics & Event Tracking

**Purpose:** Instrument all user interactions for product analytics and conversion optimization.

**Analytics Tool:** Google Analytics 4 (GA4) or Mixpanel

**Data Attribute Convention:**

```html
<!-- Standard format -->
<button data-analytics-id="tournament_register_click" 
        data-analytics-category="tournament"
        data-analytics-label="valorant-cup-2025">
    Register Now
</button>
```

**Naming Convention:**
- **Format:** `{page}_{component}_{action}`
- **Case:** snake_case (lowercase with underscores)
- **Examples:**
  - `tournament_register_click`
  - `payment_submit_click`
  - `bracket_zoom_in`
  - `profile_edit_save`

**Event Categories:**

| Category | Description | Examples |
|----------|-------------|----------|
| `tournament` | Tournament discovery & registration | `tournament_view`, `tournament_register_click`, `tournament_share` |
| `payment` | Payment submission & verification | `payment_method_select`, `payment_submit_click`, `payment_screenshot_upload` |
| `bracket` | Bracket interactions | `bracket_zoom_in`, `bracket_match_click`, `bracket_export_pdf` |
| `match` | Match management & viewing | `match_result_submit`, `match_live_view`, `match_prediction_vote` |
| `profile` | User profile actions | `profile_edit_click`, `profile_avatar_upload`, `profile_settings_save` |
| `social` | Social interactions | `share_tournament_click`, `copy_link_click`, `discord_join` |
| `certificate` | Certificate actions | `certificate_download`, `certificate_share`, `certificate_verify` |
| `navigation` | Site navigation | `navbar_tournaments_click`, `footer_about_click`, `breadcrumb_click` |

**Priority Events to Track:**

**1. Tournament Funnel:**
```html
<!-- View Tournament -->
<a href="/tournaments/valorant-cup" 
   data-analytics-id="tournament_card_click"
   data-analytics-category="tournament"
   data-analytics-label="valorant-cup-2025">

<!-- Register Button -->
<button data-analytics-id="tournament_register_click"
        data-analytics-category="tournament"
        data-analytics-label="valorant-cup-2025">
    Register Now
</button>

<!-- Registration Step 1 Complete -->
<button data-analytics-id="registration_step1_complete"
        data-analytics-category="tournament"
        data-analytics-label="valorant-cup-2025">
    Continue
</button>

<!-- Payment Method Selected -->
<input type="radio" 
       data-analytics-id="payment_method_select"
       data-analytics-category="payment"
       data-analytics-label="bkash"
       value="bkash">

<!-- Payment Submitted -->
<button data-analytics-id="payment_submit_click"
        data-analytics-category="payment"
        data-analytics-label="valorant-cup-2025">
    Submit Payment
</button>
```

**2. Social & Engagement:**
```html
<!-- Share Tournament -->
<button data-analytics-id="share_tournament_facebook"
        data-analytics-category="social"
        data-analytics-label="valorant-cup-2025">
    Share on Facebook
</button>

<!-- Match Prediction Vote -->
<button data-analytics-id="match_prediction_vote"
        data-analytics-category="match"
        data-analytics-label="team-alpha"
        data-analytics-value="match-123">
    Vote for Team Alpha
</button>

<!-- MVP Vote -->
<button data-analytics-id="mvp_vote_click"
        data-analytics-category="match"
        data-analytics-label="player-name"
        data-analytics-value="match-123">
    Vote MVP
</button>
```

**3. Conversion Actions:**
```html
<!-- Create Tournament (Organizer) -->
<button data-analytics-id="tournament_create_start"
        data-analytics-category="tournament"
        data-analytics-label="create-wizard-step1">
    Create Tournament
</button>

<!-- Purchase DeltaCoin -->
<button data-analytics-id="deltacoin_purchase_click"
        data-analytics-category="economy"
        data-analytics-label="package-500-dc"
        data-analytics-value="500">
    Buy 500 DC - ৳50
</button>

<!-- Download Certificate -->
<a href="/certificates/123/download"
   data-analytics-id="certificate_download"
   data-analytics-category="certificate"
   data-analytics-label="cert-abc123">
    Download PDF
</a>
```

**4. Navigation Tracking:**
```html
<!-- Main Nav Links -->
<a href="/tournaments" 
   data-analytics-id="navbar_tournaments_click"
   data-analytics-category="navigation">
    Tournaments
</a>

<!-- Footer Links -->
<a href="/about" 
   data-analytics-id="footer_about_click"
   data-analytics-category="navigation">
    About Us
</a>

<!-- Breadcrumbs -->
<a href="/tournaments" 
   data-analytics-id="breadcrumb_tournaments_click"
   data-analytics-category="navigation">
    Tournaments
</a>
```

**JavaScript Event Listener Example:**

```javascript
// Auto-track all data-analytics-id clicks
document.addEventListener('click', function(event) {
    const target = event.target.closest('[data-analytics-id]');
    if (!target) return;
    
    const eventId = target.dataset.analyticsId;
    const category = target.dataset.analyticsCategory || 'general';
    const label = target.dataset.analyticsLabel || '';
    const value = target.dataset.analyticsValue || '';
    
    // Send to GA4
    gtag('event', eventId, {
        'event_category': category,
        'event_label': label,
        'value': value
    });
    
    // Or Mixpanel
    mixpanel.track(eventId, {
        category: category,
        label: label,
        value: value
    });
});
```

**Custom Events (Non-Click):**

```javascript
// Track WebSocket events
socket.on('score_update', function(data) {
    gtag('event', 'match_score_update_received', {
        'event_category': 'match',
        'event_label': data.match_id,
        'non_interaction': true  // Doesn't affect bounce rate
    });
});

// Track video play
document.querySelector('video').addEventListener('play', function() {
    gtag('event', 'stream_video_play', {
        'event_category': 'engagement',
        'event_label': tournamentSlug
    });
});

// Track scroll depth
let scrollDepth = 0;
window.addEventListener('scroll', function() {
    const depth = Math.round((window.scrollY / document.body.scrollHeight) * 100);
    if (depth > scrollDepth && depth % 25 === 0) {
        scrollDepth = depth;
        gtag('event', 'scroll_depth', {
            'event_category': 'engagement',
            'value': depth
        });
    }
});
```

**Conversion Goals to Track:**

| Goal | Event ID | Success Metric |
|------|----------|----------------|
| Tournament Registration | `registration_complete` | Conversion rate > 15% |
| Payment Submission | `payment_submit_click` | Payment completion > 80% |
| Tournament Creation | `tournament_create_publish` | 10+ tournaments/month |
| Certificate Download | `certificate_download` | 90% download rate |
| Social Share | `share_*_click` | 5% share rate |
| Bracket View | `bracket_view` | Avg time > 2 minutes |
| Match Prediction | `match_prediction_vote` | 30% participation |

**Privacy & Compliance:**

- **GDPR Consent:** Show cookie consent banner, respect user opt-out
- **No PII in Events:** Never send emails, IDs, or personal data in labels
- **Anonymize IPs:** Enable IP anonymization in GA4
- **Data Retention:** 14 months (configurable)
- **User-ID Tracking:** Optional, requires explicit consent

---

### 14.6 QA Testing Checklist

**Visual Testing:**
- [ ] All screens tested at 320px, 768px, 1024px, 1920px
- [ ] Dark theme colors consistent across all components
- [ ] Hover states working on all interactive elements
- [ ] Focus indicators visible (keyboard navigation)
- [ ] Loading states display correctly
- [ ] Empty states appear when no data

**Functional Testing:**
- [ ] Tournament registration flow (end-to-end)
- [ ] Payment submission with all methods (bKash, Nagad, Rocket, Bank, DeltaCoin)
- [ ] Bracket visualization (zoom, pan, click)
- [ ] Live match updates (WebSocket)
- [ ] Certificate download (PDF generation)
- [ ] Search and filters (tournament listing)

**Accessibility Testing:**
- [ ] Screen reader testing (NVDA, JAWS, VoiceOver)
- [ ] Keyboard-only navigation (Tab, Enter, Escape)
- [ ] Color contrast (WCAG AA)
- [ ] Form validation announcements (aria-live)
- [ ] All images have alt text

**Performance Testing:**
- [ ] Lighthouse score > 90 on all pages
- [ ] LCP < 2.5s
- [ ] CLS < 0.1
- [ ] Bundle size < 200 KB

**Browser Testing:**
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest, iOS/macOS)
- [ ] Edge (latest)

**Device Testing:**
- [ ] iPhone 14 Pro (Safari)
- [ ] Samsung Galaxy S23 (Chrome)
- [ ] iPad Pro (Safari)
- [ ] Desktop (1920x1080)

---

**Document Metadata:**
- **Word Count:** ~20,000 words (expanded with enhancements)
- **Completion Date:** November 3, 2025
- **Version:** 1.1 (Enhanced based on review feedback)
- **Changes:** Added DeltaCoin payments, advanced options, custom field power-ups, certification workflow, spectator engagement, mobile QoL, i18n, error states, staff management, performance strategy, handoff materials
- **Next Steps:** Proceed to Part 5 (Implementation Roadmap)

---

[End of Part 4: UI/UX Design Specifications — Enhanced Edition]
