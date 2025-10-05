# Team Pages - Quick Visual Reference

## 🏠 Team Hub Page (`/teams/`)

### Hero Section - BEFORE vs AFTER

**BEFORE** ❌
```
┌─────────────────────────────────────────┐
│  Elite Esports Team Rankings           │
│  [Stats] [Stats] [Stats]               │
│  [Buttons]                              │
│                                         │
│  🎮 🎮 🎮  ← Floating game icons       │
│    🎮 🎮   ← (CLUTTERED & REMOVED)     │
│                                         │
└─────────────────────────────────────────┘
```

**AFTER** ✅
```
┌─────────────────────────────────────────┐
│  Elite Esports Team Rankings           │
│  Discover top competitive teams         │
│  [Stats] [Stats] [Stats]               │
│  [Create Team] [Invitations] [My Teams]│
│                                         │
│  • • •  ← Only projectiles (subtle)    │
│  CLEAN & PROFESSIONAL                   │
└─────────────────────────────────────────┘
```

---

### List View - BEFORE vs AFTER

**BEFORE** ❌
```
┌────────────────────────────────────────────┐
│ #1 [Logo] TeamName [Game]                 │  ← Misaligned
│           Stats cramped here ────────────→ │
└────────────────────────────────────────────┘
```

**AFTER** ✅
```
┌────────────────────────────────────────────────────┐
│ #1 [Logo] TeamName [Game]  │  50 │ 1500 │ 12 │ BD │  ← Properly aligned
│                             │ Mem │ Pts  │ Win│ Reg│
└────────────────────────────────────────────────────┘
```

---

### Filter Dropdown - BEFORE vs AFTER

**BEFORE** ❌
```
📁 Filter by Game ▼
   ├─ All Games
   ├─ Valorant
   ├─ CS2
   ├─ eFootball
   ├─ MLBB
   ├─ Free Fire
   ├─ PUBG
   ├─ FC26
   ├─ Call of Duty Mobile  ← Remove
   ├─ League of Legends    ← Remove
   └─ Dota 2               ← Remove

[Content Below]  ← OVERLAPPING!
```

**AFTER** ✅
```
📁 Filter by Game ▼  (z-index: 10)
   ├─ All Games
   ├─ Valorant
   ├─ CS2
   ├─ eFootball
   ├─ MLBB
   ├─ Free Fire
   ├─ PUBG
   └─ FC26
   
   
[Content Below]  ← NO OVERLAP!
```

---

## 👥 Team Detail Page (`/teams/<slug>/`)

### Desktop View (≥1024px)

```
┌────────────────────────────────────────────────────────────┐
│                   [Banner Image with Overlay]               │
│  ┌────┐                                                     │
│  │Logo│  TeamName                    [⭐ 1500] [🏆 12]     │
│  │120 │  🎮 Valorant | 🔍 Recruiting [👥 50]               │
│  └────┘  "Professional esports team..."                    │
│                                                             │
│  [Manage Team] [Invite Members] [Settings] [Share]         │
└────────────────────────────────────────────────────────────┘
```

### Tablet View (768-1023px)

```
┌──────────────────────────────────────────────┐
│         [Banner Image with Overlay]          │
│  ┌───┐                                       │
│  │Logo│ TeamName              [⭐ 1500]      │
│  │90 │ 🎮 Valorant           [🏆 12]        │
│  └───┘ "Professional team..." [👥 50]       │
│                                              │
│  [Manage] [Invite] [Settings] [Share]       │
└──────────────────────────────────────────────┘
```

### Mobile View (≤640px)

```
┌─────────────────────────┐
│ [Banner with Overlay]   │
│                         │
│      ┌─────┐            │
│      │Logo │            │
│      │100px│            │
│      └─────┘            │
│                         │
│      TeamName           │
│   🎮 Valorant           │
│   🔍 Recruiting         │
│                         │
│ "Professional team..."  │
│                         │
│ [⭐ 1500] [🏆 12] [👥 50] │
│                         │
│ ┌─────────────────────┐ │
│ │   Manage Team       │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │  Invite Members     │ │
│ └─────────────────────┘ │
│ ┌─────────────────────┐ │
│ │    Settings         │ │
│ └─────────────────────┘ │
└─────────────────────────┘
```

---

## 🎨 Design System

### Color Palette

**Primary Actions**:
```css
background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
/* Indigo gradient for primary buttons */
```

**Secondary Actions**:
```css
background: rgba(255, 255, 255, 0.15);
backdrop-filter: blur(10px);
/* Glass morphism effect */
```

**Danger Actions**:
```css
background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
/* Red gradient for destructive actions */
```

**Stats Cards**:
```css
background: rgba(255, 255, 255, 0.15);
backdrop-filter: blur(10px);
border: 1px solid rgba(255, 255, 255, 0.2);
/* Glass morphic cards with blur */
```

### Typography Scale

| Element | Desktop | Tablet | Mobile |
|---------|---------|--------|--------|
| **Hero Title** | 36px | 28px | 24px |
| **Tagline** | 16px | 14px | 13px |
| **Stat Value** | 24px | 20px | 18px |
| **Stat Label** | 12px | 12px | 10px |
| **Button** | 15px | 14px | 14px |

### Spacing System

| Screen | Container Padding | Hero Padding | Button Padding |
|--------|------------------|--------------|----------------|
| **Desktop** | 24px | 32-48px | 12px 24px |
| **Tablet** | 16px | 24px | 10px 20px |
| **Mobile** | 12px | 20px | 12px 20px |

---

## 🔧 Component Breakdown

### Team Hero Button States

```
┌─────────────────────┐
│ ⚡ Primary Button   │  ← Indigo gradient, shadow
└─────────────────────┘

┌─────────────────────┐
│ ⚪ Secondary Button │  ← Glass with border
└─────────────────────┘

┌─────────────────────┐
│ 👻 Ghost Button     │  ← Transparent with border
└─────────────────────┘

┌─────────────────────┐
│ 🔴 Danger Button    │  ← Red gradient, shadow
└─────────────────────┘

┌─────────────────────┐
│ 🚫 Disabled Button  │  ← Gray, no hover
└─────────────────────┘
```

### Stats Card Layout

```
┌──────────────┐
│      👥      │  ← Icon
│      50      │  ← Value (bold, large)
│   MEMBERS    │  ← Label (small, uppercase)
└──────────────┘
```

---

## 📐 Layout Grid

### Desktop (1024px+)
```
┌────────┬──────────────────────────┐
│        │  Hero Content            │
│  Logo  │  • Title + Badges        │
│  120px │  • Tagline               │
│        │  • Stats (3 columns)     │
└────────┴──────────────────────────┘
│  Actions (horizontal row)          │
└────────────────────────────────────┘
```

### Mobile (≤640px)
```
┌────────────┐
│    Logo    │
│   100px    │
├────────────┤
│   Title    │
├────────────┤
│   Badges   │
├────────────┤
│  Tagline   │
├────────────┤
│   Stats    │
│ (3 cols)   │
├────────────┤
│  Action 1  │
├────────────┤
│  Action 2  │
├────────────┤
│  Action 3  │
└────────────┘
```

---

## 🎯 Key Features

### Glass Morphism ✨
- Semi-transparent backgrounds
- Backdrop blur (10px)
- Subtle borders
- Premium modern feel

### Gradient Buttons 🌈
- Primary: Indigo (#6366f1 → #4f46e5)
- Danger: Red (#ef4444 → #dc2626)
- Hover: Darker shade + lift effect
- Shadow: Colored glow matching gradient

### Responsive Stats 📊
- Desktop: 3 columns, horizontal
- Tablet: 3 columns, compact
- Mobile: 3 columns, minimal spacing
- Always visible icons

### Mobile Optimization 📱
- Full-width buttons
- Centered content
- Touch-optimized sizing (min 44px)
- Stacked vertical layout
- No horizontal scroll

---

## 🚀 Performance

- **Pure CSS**: No JavaScript for layout
- **GPU Accelerated**: Uses transform, opacity
- **Lazy Loading**: Images load on demand
- **Minimal Reflows**: Fixed dimensions where possible
- **Small Bundle**: ~15KB additional CSS

---

## 🎨 Theme Support

Both light and dark themes fully supported via CSS variables:

```css
:root {
  --hero-bg: rgba(255, 255, 255, 0.95);
  --hero-text: #1e293b;
}

[data-theme="dark"] {
  --hero-bg: rgba(15, 23, 42, 0.95);
  --hero-text: #f8fafc;
}
```

---

**Quick Reference Created**: October 5, 2025  
**For**: Team Hub & Team Detail Pages  
**Status**: Production Ready ✅
