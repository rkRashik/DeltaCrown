# DeltaCrown Design System

**Version:** 2.0  
**Last Updated:** November 5, 2025  
**Status:** Active

This document defines the complete design token system for the DeltaCrown platform, ensuring consistency across all UI components and pages.

---

## 📋 Table of Contents

1. [Color Palette](#color-palette)
2. [Typography](#typography)
3. [Spacing Scale](#spacing-scale)
4. [Border Radius](#border-radius)
5. [Box Shadows](#box-shadows)
6. [Animation & Transitions](#animation--transitions)
7. [Component Classes](#component-classes)
8. [Dark Mode](#dark-mode)
9. [Usage Examples](#usage-examples)

---

## 🎨 Color Palette

### Primary Colors (Brand Blue)
Used for primary actions, links, and brand elements.

| Shade | Hex | RGB | Usage |
|-------|-----|-----|-------|
| 50 | `#eff6ff` | `rgb(239, 246, 255)` | Lightest background |
| 100 | `#dbeafe` | `rgb(219, 234, 254)` | Light background |
| 200 | `#bfdbfe` | `rgb(191, 219, 254)` | Hover states |
| 300 | `#93c5fd` | `rgb(147, 197, 253)` | Borders |
| 400 | `#60a5fa` | `rgb(96, 165, 250)` | Secondary actions |
| **500** | `#3b82f6` | `rgb(59, 130, 246)` | **Primary (default)** |
| 600 | `#2563eb` | `rgb(37, 99, 235)` | Primary hover |
| 700 | `#1d4ed8` | `rgb(29, 78, 216)` | Primary active |
| 800 | `#1e40af` | `rgb(30, 64, 175)` | Dark text |
| 900 | `#1e3a8a` | `rgb(30, 58, 138)` | Darkest |

**CSS Usage:**
```css
.bg-primary-500 { background-color: #3b82f6; }
.text-primary-600 { color: #2563eb; }
.border-primary-300 { border-color: #93c5fd; }
```

---

### Secondary Colors (Purple)
Used for secondary actions, badges, and accents.

| Shade | Hex | Usage |
|-------|-----|-------|
| 50 | `#faf5ff` | Light background |
| 500 | `#a855f7` | Secondary default |
| 600 | `#9333ea` | Secondary hover |
| 700 | `#7e22ce` | Secondary active |
| 900 | `#581c87` | Dark text |

---

### Accent Colors (Amber - Gaming Aesthetic)
Used for highlights, featured content, and call-to-actions.

| Shade | Hex | Usage |
|-------|-----|-------|
| 50 | `#fffbeb` | Light background |
| 400 | `#fbbf24` | Accent light |
| **500** | `#f59e0b` | **Accent default** |
| 600 | `#d97706` | Accent hover |
| 700 | `#b45309` | Accent dark |

---

### Semantic Colors

#### Success (Green)
| Shade | Hex | Usage |
|-------|-----|-------|
| 50 | `#f0fdf4` | Success background |
| 100 | `#dcfce7` | Success light |
| 500 | `#10b981` | Success default |
| 600 | `#059669` | Success hover |
| 800 | `#065f46` | Success text |

#### Warning (Amber)
| Shade | Hex | Usage |
|-------|-----|-------|
| 50 | `#fffbeb` | Warning background |
| 100 | `#fef3c7` | Warning light |
| 500 | `#f59e0b` | Warning default |
| 600 | `#d97706` | Warning hover |

#### Error (Red)
| Shade | Hex | Usage |
|-------|-----|-------|
| 50 | `#fef2f2` | Error background |
| 100 | `#fee2e2` | Error light |
| 500 | `#ef4444` | Error default |
| 600 | `#dc2626` | Error hover |
| 700 | `#b91c1c` | Error dark |

#### Info (Blue)
| Shade | Hex | Usage |
|-------|-----|-------|
| 50 | `#eff6ff` | Info background |
| 500 | `#3b82f6` | Info default |
| 600 | `#2563eb` | Info hover |

---

### Theme-Aware Colors
Colors that adapt based on light/dark mode.

| Variable | Light Mode | Dark Mode | Usage |
|----------|------------|-----------|-------|
| `--color-body` | `#ffffff` | `#111827` | Page background |
| `--color-body-secondary` | `#f9fafb` | `#1f2937` | Secondary background |
| `--color-text-body` | `#111827` | `#f3f4f6` | Primary text |
| `--color-text-muted` | `#6b7280` | `#9ca3af` | Secondary text |
| `--color-border` | `#e5e7eb` | `#374151` | Borders |
| `--color-card-bg` | `#ffffff` | `#1f2937` | Card background |

**CSS Usage:**
```css
body {
  background-color: rgb(var(--color-body));
  color: rgb(var(--color-text-body));
}
```

---

## ✍️ Typography

### Font Families

| Family | Usage | Stack |
|--------|-------|-------|
| **Sans** | Body text, UI elements | Inter, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif |
| **Mono** | Code blocks, technical text | JetBrains Mono, Fira Code, Courier New, monospace |
| **Display** | Headings, hero text | Rajdhani, Inter, sans-serif |

**CSS Classes:**
```html
<p class="font-sans">Default body text</p>
<code class="font-mono">Code snippet</code>
<h1 class="font-display">Hero Heading</h1>
```

---

### Font Sizes

| Size | Value | Line Height | Usage | CSS Class |
|------|-------|-------------|-------|-----------|
| xs | 0.75rem (12px) | 1rem | Labels, badges | `text-xs` |
| sm | 0.875rem (14px) | 1.25rem | Small text | `text-sm` |
| **base** | 1rem (16px) | 1.5rem | **Body text (default)** | `text-base` |
| lg | 1.125rem (18px) | 1.75rem | Large body | `text-lg` |
| xl | 1.25rem (20px) | 1.75rem | H4 | `text-xl` |
| 2xl | 1.5rem (24px) | 2rem | H3 | `text-2xl` |
| 3xl | 1.875rem (30px) | 2.25rem | H2 | `text-3xl` |
| 4xl | 2.25rem (36px) | 2.5rem | H1 | `text-4xl` |
| 5xl | 3rem (48px) | 1 | Hero | `text-5xl` |
| 6xl | 3.75rem (60px) | 1 | Large hero | `text-6xl` |

---

### Font Weights

| Weight | Value | Usage | CSS Class |
|--------|-------|-------|-----------|
| Normal | 400 | Body text | `font-normal` |
| Medium | 500 | Emphasized text | `font-medium` |
| Semibold | 600 | Subheadings | `font-semibold` |
| Bold | 700 | Headings, strong emphasis | `font-bold` |

---

### Heading Styles

```html
<h1 class="text-4xl lg:text-5xl font-semibold">Main Heading</h1>
<h2 class="text-3xl lg:text-4xl font-semibold">Section Heading</h2>
<h3 class="text-2xl lg:text-3xl font-semibold">Subsection</h3>
<h4 class="text-xl lg:text-2xl font-semibold">Component Title</h4>
```

---

## 📏 Spacing Scale

Consistent spacing using 0.25rem (4px) base unit.

| Name | Value | Pixels | Usage |
|------|-------|--------|-------|
| 0.5 | 0.125rem | 2px | Micro spacing |
| 1 | 0.25rem | 4px | Tiny spacing |
| 1.5 | 0.375rem | 6px | Extra small |
| 2 | 0.5rem | 8px | Small spacing |
| 3 | 0.75rem | 12px | Medium small |
| **4** | **1rem** | **16px** | **Default spacing** |
| 5 | 1.25rem | 20px | Medium |
| 6 | 1.5rem | 24px | Medium large |
| 8 | 2rem | 32px | Large |
| 10 | 2.5rem | 40px | Extra large |
| 12 | 3rem | 48px | XXL |
| 16 | 4rem | 64px | Section spacing |
| 20 | 5rem | 80px | Large section |
| 24 | 6rem | 96px | Page spacing |

**Usage Examples:**
```html
<div class="p-4">Padding 16px all sides</div>
<div class="px-6 py-4">Padding 24px horizontal, 16px vertical</div>
<div class="mb-8">Margin bottom 32px</div>
<div class="space-y-4">Gap 16px between children</div>
```

---

## 🔲 Border Radius

| Size | Value | Usage | CSS Class |
|------|-------|-------|-----------|
| sm | 0.25rem (4px) | Badges, small elements | `rounded-sm` |
| **md** | **0.5rem (8px)** | **Buttons, inputs (default)** | `rounded-md` |
| lg | 1rem (16px) | Cards, containers | `rounded-lg` |
| xl | 1.5rem (24px) | Large cards | `rounded-xl` |
| 2xl | 2rem (32px) | Hero sections | `rounded-2xl` |
| full | 9999px | Pills, avatars | `rounded-full` |

---

## 🌑 Box Shadows

### Standard Shadows

| Size | Value | Usage | CSS Class |
|------|-------|-------|-----------|
| sm | `0 1px 2px 0 rgb(0 0 0 / 0.05)` | Subtle elevation | `shadow-sm` |
| **md** | **0 4px 6px rgb(0 0 0 / 0.1)** | **Default cards** | `shadow-md` |
| lg | `0 10px 15px rgb(0 0 0 / 0.1)` | Elevated cards | `shadow-lg` |
| xl | `0 20px 25px rgb(0 0 0 / 0.1)` | Modals, popovers | `shadow-xl` |
| 2xl | `0 25px 50px rgb(0 0 0 / 0.25)` | Overlays | `shadow-2xl` |
| inner | `inset 0 2px 4px rgb(0 0 0 / 0.05)` | Pressed states | `shadow-inner` |

### Gaming Glow Shadows

| Size | Value | Usage | CSS Class |
|------|-------|-------|-----------|
| glow-sm | `0 0 10px rgba(59, 130, 246, 0.3)` | Subtle glow | `shadow-glow-sm` |
| glow-md | `0 0 20px rgba(59, 130, 246, 0.4)` | Medium glow | `shadow-glow-md` |
| glow-lg | `0 0 30px rgba(59, 130, 246, 0.5)` | Strong glow | `shadow-glow-lg` |
| glow-accent | `0 0 20px rgba(245, 158, 11, 0.5)` | Accent glow | `shadow-glow-accent` |

**Usage:**
```html
<div class="shadow-glow-md">Glowing card</div>
<button class="hover:shadow-glow-accent">Hover glow effect</button>
```

---

## ⚡ Animation & Transitions

### Transition Durations

| Duration | Value | Usage | CSS Class |
|----------|-------|-------|-----------|
| 75 | 75ms | Instant feedback | `duration-75` |
| **200** | **200ms** | **Standard (default)** | `duration-200` |
| 300 | 300ms | Smooth transitions | `duration-300` |
| 500 | 500ms | Slower animations | `duration-500` |

### Animations

| Name | Keyframes | Usage | CSS Class |
|------|-----------|-------|-----------|
| fade-in | opacity 0 → 1 | Appear effect | `animate-fade-in` |
| slide-up | translateY(10px) → 0 | Slide from bottom | `animate-slide-up` |
| slide-down | translateY(-10px) → 0 | Slide from top | `animate-slide-down` |
| float | translateY(0) ↔ -10px | Floating effect | `animate-float` |
| pulse | scale 100% ↔ 105% | Pulsing | `animate-pulse` |
| spin | rotate 360° | Loading spinners | `animate-spin` |

**Usage:**
```html
<div class="animate-fade-in">Fades in on load</div>
<button class="hover:animate-pulse">Pulses on hover</button>
<div class="animate-spin">Loading...</div>
```

---

## 🧩 Component Classes

### Buttons

```html
<!-- Primary button -->
<button class="btn btn-primary">Save Changes</button>

<!-- Secondary button -->
<button class="btn btn-secondary">Cancel</button>

<!-- Ghost button -->
<button class="btn btn-ghost">Learn More</button>

<!-- Danger button -->
<button class="btn btn-danger">Delete</button>

<!-- Sizes -->
<button class="btn btn-primary btn-sm">Small</button>
<button class="btn btn-primary btn-lg">Large</button>

<!-- Loading state -->
<button class="btn btn-primary btn-loading">Processing...</button>
```

### Cards

```html
<!-- Basic card -->
<div class="card">
  <div class="card-header">
    <h3>Card Title</h3>
  </div>
  <div class="card-body">
    <p>Card content goes here.</p>
  </div>
  <div class="card-footer">
    <button class="btn btn-primary">Action</button>
  </div>
</div>

<!-- Elevated card -->
<div class="card card-elevated">Content</div>

<!-- Interactive card (hover effect) -->
<div class="card card-interactive">Clickable content</div>
```

### Form Elements

```html
<!-- Form group with label and input -->
<div class="form-group">
  <label class="form-label form-label-required" for="email">
    Email Address
  </label>
  <input type="email" id="email" class="form-input" placeholder="you@example.com">
  <p class="form-helper">We'll never share your email.</p>
</div>

<!-- Input with error -->
<div class="form-group">
  <label class="form-label" for="password">Password</label>
  <input type="password" id="password" class="form-input form-input-error">
  <p class="form-error">Password must be at least 8 characters.</p>
</div>
```

### Alerts

```html
<div class="alert alert-info">This is an info message.</div>
<div class="alert alert-success">Operation successful!</div>
<div class="alert alert-warning">Warning: Please review.</div>
<div class="alert alert-error">Error: Something went wrong.</div>
```

### Badges

```html
<span class="badge badge-primary">New</span>
<span class="badge badge-success">Active</span>
<span class="badge badge-warning">Pending</span>
<span class="badge badge-error">Closed</span>
```

---

## 🌓 Dark Mode

### Implementation
Dark mode uses a `data-theme="dark"` attribute on the `<html>` tag.

```javascript
// Toggle dark mode
document.documentElement.setAttribute('data-theme', 'dark');

// Toggle light mode
document.documentElement.setAttribute('data-theme', 'light');

// Use system preference
document.documentElement.removeAttribute('data-theme');
```

### CSS Custom Properties
All theme-aware colors automatically update:

```css
/* Light mode (default) */
:root {
  --color-body: 255 255 255;
  --color-text-body: 17 24 39;
}

/* Dark mode */
[data-theme="dark"] {
  --color-body: 17 24 39;
  --color-text-body: 243 244 246;
}
```

### Usage in Components
```html
<!-- Uses theme-aware color -->
<div class="bg-body text-text-body">
  Content adapts to theme
</div>

<!-- Force dark background -->
<div class="bg-gray-900 text-white">
  Always dark
</div>
```

---

## 📖 Usage Examples

### Complete Button Component
```html
<button class="
  px-4 py-2 
  bg-primary-600 hover:bg-primary-700 active:bg-primary-800
  text-white font-medium
  rounded-md shadow-sm
  transition-all duration-200
  focus:ring-2 focus:ring-primary-500 focus:ring-offset-2
  disabled:opacity-50 disabled:cursor-not-allowed
">
  Click Me
</button>
```

### Responsive Card Layout
```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  <div class="card card-elevated">
    <div class="card-body">
      <h3 class="text-xl font-semibold mb-2">Tournament 1</h3>
      <p class="text-text-muted">Details here...</p>
    </div>
  </div>
  <!-- More cards -->
</div>
```

### Hero Section
```html
<section class="py-20 bg-gradient-to-r from-primary-600 to-secondary-600">
  <div class="container mx-auto px-4 text-center text-white">
    <h1 class="text-5xl lg:text-6xl font-display font-bold mb-4">
      Welcome to DeltaCrown
    </h1>
    <p class="text-xl mb-8 max-w-2xl mx-auto">
      Bangladesh's Premier Esports Platform
    </p>
    <button class="btn btn-lg bg-white text-primary-600 hover:bg-gray-100">
      Get Started
    </button>
  </div>
</section>
```

---

## 🎓 Best Practices

1. **Consistent Spacing**: Use the spacing scale (4, 8, 16, 24, 32px)
2. **Semantic Colors**: Use semantic colors (success, error, warning) for states
3. **Accessible Contrast**: Ensure text meets WCAG AA (4.5:1 contrast minimum)
4. **Focus States**: Always include focus ring for keyboard navigation
5. **Responsive Design**: Use mobile-first breakpoints (sm, md, lg, xl)
6. **Theme Awareness**: Use theme-aware colors for adaptable UI
7. **Animation Timing**: Use 200-300ms for most transitions
8. **Shadow Elevation**: Use consistent shadow scale for visual hierarchy

---

## 📚 Reference

- **Tailwind CSS Docs**: https://tailwindcss.com
- **Color Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **WCAG Guidelines**: https://www.w3.org/WAI/WCAG21/quickref/

---

**Document Maintained By:** Frontend Team  
**Last Review:** November 5, 2025  
**Next Review:** December 2025
