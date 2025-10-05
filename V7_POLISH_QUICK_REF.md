# 🎨 V7 POLISH - QUICK VISUAL REFERENCE

## Animation Classes Quick Guide

### 🔄 LOADING STATES
```html
<!-- Skeleton Loader -->
<div class="skeleton skeleton-card"></div>
<div class="skeleton skeleton-text"></div>
<div class="skeleton skeleton-title"></div>

<!-- Loading Spinner -->
<div class="loading-spinner"></div>

<!-- Loading Overlay (auto-created by JS) -->
<div class="loading-overlay active">
  <div class="loading-content">
    <div class="loading-spinner"></div>
    <div class="loading-text">Loading...</div>
  </div>
</div>
```

### 🎯 HOVER EFFECTS
```html
<!-- Magnetic Button (follows cursor) -->
<button class="btn-magnetic">Hover Me</button>

<!-- Glow Pulse -->
<button class="glow-on-hover">Glow Button</button>

<!-- Card Lift -->
<div class="card-lift">Card Content</div>

<!-- Shine Sweep Effect -->
<button class="shine-effect">Shine Button</button>

<!-- Icon Bounce -->
<a href="#" class="icon-bounce">
  <svg>...</svg>
  Link Text
</a>

<!-- Pulse on Hover -->
<div class="pulse-on-hover">Pulse Element</div>
```

### 🎬 ENTRANCE ANIMATIONS
```html
<!-- Fade In -->
<div class="fade-in">Content</div>

<!-- Slide Up -->
<div class="slide-up">Content</div>

<!-- Zoom In -->
<div class="zoom-in">Content</div>

<!-- Stagger Animation (for lists) -->
<div data-stagger>
  <div class="stagger-item">Item 1</div>
  <div class="stagger-item">Item 2</div>
  <div class="stagger-item">Item 3</div>
</div>
```

### 📜 SCROLL ANIMATIONS
```html
<!-- Scroll Reveal -->
<div class="scroll-reveal">Reveals on scroll</div>

<!-- Parallax Effect -->
<div class="parallax" data-parallax-speed="0.5">
  Background Element
</div>
```

### 🔘 BUTTON STATES
```html
<!-- Loading Button -->
<button class="btn-loading">Processing...</button>

<!-- Success Button -->
<button class="btn-success">Completed!</button>

<!-- Error Button -->
<button class="btn-error">Failed!</button>
```

### 💬 TOOLTIPS
```html
<!-- Enhanced Tooltip -->
<button class="tooltip-enhanced" data-tooltip="Helpful text">
  Hover for tooltip
</button>
```

### 📱 INTERACTIONS
```html
<!-- Ripple Effect on Click -->
<button class="ripple-effect">Click Me</button>

<!-- Counter Animation -->
<span data-counter="1234">0</span>

<!-- Number Change Highlight -->
<span class="number-changed">99</span>
```

### 🎉 SPECIAL EFFECTS
```html
<!-- Notification Dot -->
<div style="position: relative;">
  <button>Button</button>
  <span class="notification-dot"></span>
</div>

<!-- Animated Badge -->
<span class="badge-animate">New!</span>
```

---

## JavaScript API Quick Reference

### Initialize Polish System
```javascript
// Auto-initializes on page load
// Access via: window.tournamentPolish
```

### Show/Hide Loading
```javascript
tournamentPolish.showLoading('Loading tournament...');
tournamentPolish.hideLoading();
```

### Button States
```javascript
const btn = document.querySelector('.my-button');

// Loading
tournamentPolish.setButtonLoading(btn, true);

// Success
tournamentPolish.setButtonSuccess(btn);

// Error
tournamentPolish.setButtonError(btn);
```

### Notifications
```javascript
// Show toast
tournamentPolish.showToast('Registration successful!', 'success');
tournamentPolish.showToast('An error occurred', 'error');
tournamentPolish.showToast('Processing...', 'info');
```

### Number Animations
```javascript
const element = document.querySelector('.counter');
tournamentPolish.animateNumberChange(element, 150);
```

### Copy to Clipboard
```javascript
const copyBtn = document.querySelector('.copy-btn');
await tournamentPolish.copyToClipboard('Tournament URL', copyBtn);
```

### Celebration
```javascript
// Trigger confetti
tournamentPolish.triggerConfetti();
```

---

## Hub-Specific Classes

### Game Cards
```html
<div class="dc-game-card" data-tooltip="Valorant - 12 tournaments">
  <!-- Card content -->
</div>
```

### Stat Cards
```html
<div class="dc-stat-card">
  <div class="dc-stat-number" data-counter="156">0</div>
  <div class="dc-stat-label">Active Tournaments</div>
</div>
```

### Tournament Cards
```html
<!-- Auto-stagger animation applied -->
<div class="dc-tournament-card">
  <!-- Card content -->
</div>
```

### Progress Bars
```html
<div class="dc-progress-bar">
  <div class="dc-progress-fill" style="width: 75%"></div>
</div>
```

### Live Indicators
```html
<div class="dc-live-indicator">
  <span>LIVE</span>
</div>
```

### Filter Pills
```html
<button class="dc-filter-pill active">
  All Games
</button>
```

---

## Animation Timing Reference

| Animation Type | Duration | Easing | Use Case |
|---------------|----------|---------|----------|
| Button Hover | 0.3s | cubic-bezier(0.4, 0, 0.2, 1) | Quick feedback |
| Card Entrance | 0.6s | cubic-bezier(0.34, 1.56, 0.64, 1) | Spring bounce |
| Scroll Reveal | 0.8s | cubic-bezier(0.34, 1.56, 0.64, 1) | Smooth reveal |
| Progress Fill | 1.5s | cubic-bezier(0.4, 0, 0.2, 1) | Steady progress |
| Pulse Loop | 2-3s | ease-in-out | Subtle attention |
| Shimmer | 2s | linear | Loading effect |

---

## Color Variables

```css
--primary: #00ff88;
--primary-hover: #00e67a;
--primary-glow: rgba(0, 255, 136, 0.4);

--accent: #ff4655;
--accent-hover: #ff2e40;

--gold: #FFD700;

--bg-page: #0a0a0f;
--bg-card: rgba(20, 25, 35, 0.6);
--bg-elevated: rgba(25, 30, 42, 0.8);

--glass: rgba(255, 255, 255, 0.04);
--glass-border: rgba(255, 255, 255, 0.1);
--glass-hover: rgba(255, 255, 255, 0.08);
```

---

## Performance Tips

### ✅ DO:
- Use `transform` and `opacity` for animations
- Apply `will-change` for frequently animated elements
- Use `contain: layout style paint` for isolated components
- Leverage IntersectionObserver for scroll animations
- Use requestAnimationFrame for scroll events

### ❌ DON'T:
- Animate `width`, `height`, `top`, `left`
- Use too many simultaneous animations
- Forget to clean up event listeners
- Ignore reduced motion preferences
- Overuse `will-change`

---

## Browser DevTools Tips

### Check Animation Performance:
1. Open Chrome DevTools (F12)
2. Go to **Performance** tab
3. Click **Record** (Ctrl+E)
4. Interact with page
5. Stop recording
6. Check for:
   - 60fps (green bars)
   - No layout thrashing (purple bars)
   - Minimal paint (green bars)

### Rendering Panel:
1. Open DevTools (F12)
2. Press `Esc` to show console drawer
3. Click `...` → **Rendering**
4. Enable:
   - **Frame Rendering Stats** (FPS meter)
   - **Paint flashing** (see repaints)
   - **Layout Shift Regions** (CLS issues)

### Accessibility Testing:
1. Open DevTools (F12)
2. Go to **Elements** tab
3. Click **Accessibility** pane
4. Test with:
   - **Emulate reduced motion**: DevTools → Settings → Rendering
   - **Keyboard only**: Tab through all elements

---

## Common Patterns

### 1. Animated Card Grid
```html
<div class="grid" data-stagger>
  <div class="stagger-item card-lift scroll-reveal">
    Card 1
  </div>
  <div class="stagger-item card-lift scroll-reveal">
    Card 2
  </div>
</div>
```

### 2. CTA Button with All Effects
```html
<button class="btn-primary-cta btn-magnetic shine-effect ripple-effect glow-on-hover">
  <svg>...</svg>
  Register Now
</button>
```

### 3. Loading State Pattern
```html
<button class="btn-action" onclick="handleClick(this)">
  Submit
</button>

<script>
async function handleClick(btn) {
  tournamentPolish.setButtonLoading(btn, true);
  
  try {
    await submitForm();
    tournamentPolish.setButtonSuccess(btn);
    tournamentPolish.showToast('Success!', 'success');
    tournamentPolish.triggerConfetti();
  } catch (error) {
    tournamentPolish.setButtonError(btn);
    tournamentPolish.showToast('Error: ' + error, 'error');
  }
}
</script>
```

### 4. Scroll-Triggered Content
```html
<section class="content-section">
  <div class="scroll-reveal card-lift">
    <h2 class="slide-up">Heading</h2>
    <p class="fade-in">Description text...</p>
  </div>
</section>
```

---

## Troubleshooting

### Animation Not Working?
1. Check if CSS file is loaded: `tournaments-detail-v7-polish.css`
2. Check if JS file is loaded: `tournaments-v7-polish.js`
3. Check browser console for errors
4. Verify class name spelling
5. Check if element is visible (display: none blocks animations)

### Performance Issues?
1. Reduce number of simultaneous animations
2. Remove `will-change` from non-animated elements
3. Use `contain: layout style paint` on containers
4. Optimize animation complexity
5. Test on lower-end devices

### Accessibility Concerns?
1. Test with keyboard only (Tab key)
2. Enable reduced motion in OS settings
3. Use screen reader (NVDA, JAWS, VoiceOver)
4. Check color contrast (4.5:1 minimum)
5. Ensure focus states are visible

---

## Examples in Action

### Detail Page Hero
```html
<div class="detail-hero">
  <div class="hero-content zoom-in">
    <h1 class="slide-up">Valorant Crown Battle</h1>
    <a href="#" class="btn-primary-cta btn-magnetic shine-effect ripple-effect glow-on-hover">
      Register Now
    </a>
  </div>
</div>
```

### Hub Page Stats
```html
<div class="dc-stats-grid">
  <div class="dc-stat-card card-lift">
    <div class="dc-stat-number" data-counter="156">0</div>
    <div class="dc-stat-label">Active</div>
  </div>
  <div class="dc-stat-card card-lift">
    <div class="dc-stat-number" data-counter="2450">0</div>
    <div class="dc-stat-label">Players</div>
  </div>
</div>
```

### Loading Overlay Usage
```javascript
// Show loading
tournamentPolish.showLoading('Fetching tournament data...');

// Fetch data
const response = await fetch('/api/tournaments/');
const data = await response.json();

// Hide loading
tournamentPolish.hideLoading();
```

---

## Quick Copy-Paste Snippets

### Success Flow
```javascript
const btn = document.querySelector('#register-btn');
tournamentPolish.setButtonLoading(btn, true);

setTimeout(() => {
  tournamentPolish.setButtonSuccess(btn);
  tournamentPolish.showToast('Registration successful!', 'success');
  tournamentPolish.triggerConfetti();
}, 2000);
```

### Error Flow
```javascript
const btn = document.querySelector('#submit-btn');
tournamentPolish.setButtonLoading(btn, true);

setTimeout(() => {
  tournamentPolish.setButtonError(btn);
  tournamentPolish.showToast('Submission failed!', 'error');
}, 2000);
```

### Counter Update
```javascript
const counter = document.querySelector('.participants-count');
// Animate from current to new value
tournamentPolish.animateNumberChange(counter, 45);
```

---

**Pro Tip:** Combine multiple classes for rich effects!
```html
<button class="btn-magnetic shine-effect ripple-effect glow-on-hover tooltip-enhanced"
        data-tooltip="Click to register">
  Register Now
</button>
```

**Remember:** Always test with reduced motion preference enabled! ♿

---

**End of Quick Reference** 🎨
