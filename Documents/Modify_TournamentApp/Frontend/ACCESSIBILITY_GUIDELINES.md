# DeltaCrown Accessibility Guidelines

**Epic:** Phase 9, Epic 9.3 - UI/UX Framework & Design Tokens  
**Date:** December 10, 2025  
**Standard:** WCAG 2.1 Level AA Compliance  
**Purpose:** Ensure DeltaCrown is accessible to all users, including those with disabilities

---

## 1. WCAG 2.1 Level AA Requirements

### 1.1 Perceivable

**Guideline 1.1: Text Alternatives**
- All images have `alt` text
- Decorative images have `alt=""` or `aria-hidden="true"`
- Icon buttons have `aria-label`
- Complex images (charts, brackets) have detailed descriptions

**Guideline 1.2: Time-based Media**
- Video content has captions (if applicable)
- Audio content has transcripts

**Guideline 1.3: Adaptable**
- Content can be presented in different ways without losing information
- Use semantic HTML (`<header>`, `<nav>`, `<main>`, `<article>`, `<aside>`, `<footer>`)
- Heading hierarchy is logical (H1 → H2 → H3)
- Form inputs have associated `<label>` elements
- Tables use `<th>` headers with `scope` attribute

**Guideline 1.4: Distinguishable**
- Color contrast ratio ≥ 4.5:1 for normal text
- Color contrast ratio ≥ 3:1 for large text (18pt+ or 14pt+ bold)
- Color is not the only way to convey information
- Text can be resized up to 200% without loss of content or functionality
- Focus indicators are visible (minimum 2px outline)

---

### 1.2 Operable

**Guideline 2.1: Keyboard Accessible**
- All functionality available via keyboard
- No keyboard traps (focus can move away from any element)
- Keyboard shortcuts don't override browser/assistive tech shortcuts

**Guideline 2.2: Enough Time**
- Auto-save drafts (no data loss from timeouts)
- Countdowns have warning before expiration
- Users can extend time limits

**Guideline 2.3: Seizures and Physical Reactions**
- No content flashes more than 3 times per second
- Animations can be disabled (respect `prefers-reduced-motion`)

**Guideline 2.4: Navigable**
- Skip links to main content
- Descriptive page titles (`<title>`)
- Focus order is logical (matches visual order)
- Link text is descriptive (avoid "click here")
- Multiple ways to navigate (menu, search, breadcrumbs)
- Clear headings and labels

**Guideline 2.5: Input Modalities**
- Touch targets ≥ 44×44 pixels
- Pointer cancellation (don't trigger on mousedown)
- Label in name matches accessible name

---

### 1.3 Understandable

**Guideline 3.1: Readable**
- Language declared (`<html lang="en">`)
- Language changes marked (`<span lang="es">`)
- Unusual words/jargon explained

**Guideline 3.2: Predictable**
- Navigation is consistent across pages
- Components are consistent (same icons, same placement)
- No surprise context changes (e.g., auto-submit on select)

**Guideline 3.3: Input Assistance**
- Form errors identified and described
- Labels or instructions provided
- Error suggestions offered (e.g., "Email must contain @")
- Prevent errors (confirmation for destructive actions)

---

### 1.4 Robust

**Guideline 4.1: Compatible**
- Valid HTML (no major parsing errors)
- Proper ARIA usage
- Status messages announced (`role="status"`, `aria-live`)

---

## 2. Keyboard Navigation

### 2.1 Tab Order

**Standard Tab Order:**
1. Skip to main content link (hidden until focused)
2. Logo
3. Navigation links
4. Search (if present)
5. User menu (if authenticated)
6. Main content (forms, links, buttons)
7. Footer links

**Rules:**
- `tabindex="0"`: Naturally focusable elements (links, buttons, inputs)
- `tabindex="-1"`: Programmatically focusable (for JS focus management)
- Never use `tabindex > 0` (disrupts natural tab order)

**Example:**
```html
<!-- Skip link (visible on focus) -->
<a href="#main-content" class="sr-only focus:not-sr-only">
  Skip to main content
</a>

<!-- Navbar -->
<nav>
  <a href="/">Home</a>
  <a href="/tournaments">Tournaments</a>
</nav>

<!-- Main content -->
<main id="main-content" tabindex="-1">
  <!-- Content here -->
</main>
```

---

### 2.2 Keyboard Shortcuts

**Global Shortcuts:**
- `Tab`: Next focusable element
- `Shift + Tab`: Previous focusable element
- `Enter`: Activate link/button
- `Space`: Activate button, toggle checkbox
- `Escape`: Close modal/dropdown

**Component-Specific:**
- **Dropdown Menu**: `↓` open, `↑↓` navigate, `Enter` select, `Esc` close
- **Modal**: `Esc` close, `Tab` cycles within modal
- **Table**: `↑↓` navigate rows (if implemented)
- **Bracket**: `Tab` through matches, `Enter` view details

**Implementation:**
```javascript
// Dropdown menu keyboard navigation
dropdown.addEventListener('keydown', (e) => {
  const items = dropdown.querySelectorAll('[role="menuitem"]');
  const currentIndex = Array.from(items).indexOf(document.activeElement);
  
  switch (e.key) {
    case 'ArrowDown':
      e.preventDefault();
      items[(currentIndex + 1) % items.length].focus();
      break;
    case 'ArrowUp':
      e.preventDefault();
      items[(currentIndex - 1 + items.length) % items.length].focus();
      break;
    case 'Escape':
      closeDropdown();
      break;
  }
});
```

---

## 3. ARIA Attributes

### 3.1 Landmarks

**Use Semantic HTML First:**
```html
<header> → <div role="banner">
<nav> → <div role="navigation">
<main> → <div role="main">
<aside> → <div role="complementary">
<footer> → <div role="contentinfo">
```

**Additional Landmarks:**
```html
<div role="search"><!-- Search form --></div>
<form role="search"><!-- Same as above --></form>
```

**Landmark Labels:**
```html
<nav aria-label="Primary navigation">...</nav>
<nav aria-label="Footer navigation">...</nav>
<nav aria-label="Tournament navigation">...</nav>
```

---

### 3.2 Live Regions

**Announce Dynamic Content:**
```html
<!-- Polite (wait for user to finish) -->
<div aria-live="polite" aria-atomic="true">
  Match status updated: Now Live
</div>

<!-- Assertive (interrupt immediately) -->
<div role="alert" aria-live="assertive">
  Error: Registration deadline has passed
</div>

<!-- Status (for non-critical updates) -->
<div role="status" aria-live="polite">
  Saved 5 seconds ago
</div>
```

**Usage:**
- `aria-live="polite"`: Non-urgent updates (autosave, filtering results)
- `aria-live="assertive"`: Urgent updates (errors, warnings)
- `role="alert"`: Equivalent to `aria-live="assertive"`
- `role="status"`: Equivalent to `aria-live="polite"`

---

### 3.3 Form Controls

**Text Inputs:**
```html
<label for="username">Username <span aria-label="required">*</span></label>
<input 
  type="text" 
  id="username" 
  name="username"
  aria-required="true"
  aria-invalid="false"
  aria-describedby="username-help username-error"
/>
<p id="username-help">3-20 characters, letters and numbers only</p>
<p id="username-error" role="alert"></p>
```

**Select Dropdowns:**
```html
<label for="tournament">Select Tournament</label>
<select 
  id="tournament" 
  name="tournament"
  aria-required="true"
  aria-invalid="false"
>
  <option value="">-- Select --</option>
  <option value="1">Tournament A</option>
</select>
```

**Checkbox Groups:**
```html
<fieldset>
  <legend>Select Games</legend>
  <div>
    <input type="checkbox" id="lol" name="games" value="lol" />
    <label for="lol">League of Legends</label>
  </div>
  <div>
    <input type="checkbox" id="valorant" name="games" value="valorant" />
    <label for="valorant">Valorant</label>
  </div>
</fieldset>
```

---

### 3.4 Dialogs and Modals

**Modal Structure:**
```html
<div 
  id="confirm-modal" 
  role="dialog" 
  aria-modal="true"
  aria-labelledby="modal-title"
  aria-describedby="modal-description"
  hidden
>
  <h2 id="modal-title">Confirm Cancellation</h2>
  <p id="modal-description">
    Are you sure you want to cancel your registration?
  </p>
  <button>Cancel</button>
  <button>Confirm</button>
</div>
```

**Focus Management:**
```javascript
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  const previousFocus = document.activeElement;
  
  modal.removeAttribute('hidden');
  modal.querySelector('button').focus(); // Focus first button
  
  // Store previous focus for restoration
  modal.dataset.previousFocus = previousFocus.id;
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  const previousFocusId = modal.dataset.previousFocus;
  
  modal.setAttribute('hidden', '');
  
  // Restore focus
  if (previousFocusId) {
    document.getElementById(previousFocusId).focus();
  }
}
```

---

### 3.5 Buttons vs Links

**Buttons** (perform actions):
```html
<button type="button" onclick="submitForm()">Submit</button>
<button type="submit">Register</button>
```

**Links** (navigate):
```html
<a href="/tournaments">View Tournaments</a>
```

**Never:**
```html
<!-- BAD: Link that acts like button -->
<a href="#" onclick="submitForm()">Submit</a>

<!-- GOOD: Button styled as link (if needed) -->
<button type="button" class="btn-link" onclick="submitForm()">Submit</button>
```

---

### 3.6 Custom Components

**Toggle Button:**
```html
<button 
  type="button"
  role="switch"
  aria-checked="false"
  onclick="toggleDarkMode(this)"
>
  Dark Mode
</button>
```

**Tabs:**
```html
<div role="tablist" aria-label="Tournament Information">
  <button role="tab" aria-selected="true" aria-controls="overview-panel" id="overview-tab">
    Overview
  </button>
  <button role="tab" aria-selected="false" aria-controls="rules-panel" id="rules-tab">
    Rules
  </button>
</div>

<div role="tabpanel" id="overview-panel" aria-labelledby="overview-tab">
  <!-- Overview content -->
</div>
<div role="tabpanel" id="rules-panel" aria-labelledby="rules-tab" hidden>
  <!-- Rules content -->
</div>
```

---

## 4. Color Contrast

### 4.1 Contrast Ratios

**WCAG AA Requirements:**
- Normal text (< 18pt): **4.5:1** minimum
- Large text (≥ 18pt or ≥ 14pt bold): **3:1** minimum
- UI components & graphics: **3:1** minimum

**Design Token Verification:**
```
✅ PASS: White text on brand-primary-600 (7.2:1)
✅ PASS: neutral-700 text on white (12.6:1)
✅ PASS: success-800 on success-50 (7.5:1)
❌ FAIL: neutral-300 on white (2.1:1) - DO NOT USE FOR TEXT
```

**Tools:**
- WebAIM Contrast Checker: https://webaim.org/resources/contrastchecker/
- Browser DevTools: Inspect element → Accessibility panel
- Automated: axe DevTools extension

---

### 4.2 Color Independence

**Don't Rely on Color Alone:**

❌ **Bad:**
```html
<span style="color: red;">Required field</span>
```

✅ **Good:**
```html
<span class="text-error-600">
  <span aria-label="required">*</span> Required field
</span>
```

❌ **Bad:**
```html
<div class="bg-success-500">Success</div>
<div class="bg-error-500">Error</div>
```

✅ **Good:**
```html
<div class="bg-success-500">
  <span class="sr-only">Success:</span>
  ✓ Registration complete
</div>
<div class="bg-error-500">
  <span class="sr-only">Error:</span>
  ✗ Registration failed
</div>
```

---

## 5. Focus Management

### 5.1 Visible Focus Indicators

**Minimum Requirement:**
- Outline: 2px solid
- Contrast: 3:1 against background
- No removal of default focus styles without replacement

**Design Token:**
```css
:focus-visible {
  outline: 2px solid var(--brand-primary-500);
  outline-offset: 2px;
  border-radius: 4px;
}

/* Remove outline for mouse users (still shows for keyboard) */
:focus:not(:focus-visible) {
  outline: none;
}
```

**Tailwind Class:**
```html
<button class="btn-primary focus:ring-2 focus:ring-brand-primary-500 focus:ring-offset-2">
  Click Me
</button>
```

---

### 5.2 Focus Trapping

**Modal Focus Trap:**
```javascript
function trapFocus(element) {
  const focusable = element.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const firstFocusable = focusable[0];
  const lastFocusable = focusable[focusable.length - 1];
  
  element.addEventListener('keydown', (e) => {
    if (e.key !== 'Tab') return;
    
    if (e.shiftKey) {
      // Shift + Tab
      if (document.activeElement === firstFocusable) {
        e.preventDefault();
        lastFocusable.focus();
      }
    } else {
      // Tab
      if (document.activeElement === lastFocusable) {
        e.preventDefault();
        firstFocusable.focus();
      }
    }
  });
}
```

---

## 6. Screen Reader Support

### 6.1 Screen Reader Only Text

**Utility Class:**
```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

.sr-only-focusable:focus {
  position: static;
  width: auto;
  height: auto;
  padding: inherit;
  margin: inherit;
  overflow: visible;
  clip: auto;
  white-space: normal;
}
```

**Usage:**
```html
<!-- Icon button with screen reader text -->
<button type="button">
  <span class="sr-only">Close modal</span>
  <span aria-hidden="true">×</span>
</button>

<!-- Skip link (visible on focus) -->
<a href="#main-content" class="sr-only sr-only-focusable">
  Skip to main content
</a>

<!-- Decorative icon -->
<svg aria-hidden="true" focusable="false">...</svg>
```

---

### 6.2 Accessible Names

**Calculation Order (by browser):**
1. `aria-labelledby` (references another element's ID)
2. `aria-label` (directly provides label)
3. Label element (for form controls)
4. `alt` attribute (for images)
5. Text content (for links/buttons)

**Examples:**
```html
<!-- aria-labelledby -->
<h2 id="modal-title">Confirm Action</h2>
<div role="dialog" aria-labelledby="modal-title">...</div>

<!-- aria-label -->
<button aria-label="Close notification">×</button>

<!-- Label element -->
<label for="email">Email</label>
<input id="email" type="email" />

<!-- Alt attribute -->
<img src="logo.png" alt="DeltaCrown Logo" />

<!-- Text content -->
<button>Submit</button>
<a href="/tournaments">View Tournaments</a>
```

---

## 7. Testing Checklist

### 7.1 Automated Testing

**Tools:**
- axe DevTools (Chrome/Firefox extension)
- WAVE (WebAIM accessibility evaluation tool)
- Lighthouse (Chrome DevTools → Audits)

**Run on Every Page:**
- [ ] No critical/serious violations
- [ ] Color contrast passes
- [ ] All images have alt text
- [ ] Form inputs have labels
- [ ] Headings are hierarchical

---

### 7.2 Manual Keyboard Testing

**Test Scenarios:**
- [ ] Can navigate entire site with Tab key
- [ ] Focus indicators always visible
- [ ] No keyboard traps
- [ ] Dropdowns work with Arrow keys
- [ ] Modals close with Escape
- [ ] Forms submit with Enter

---

### 7.3 Screen Reader Testing

**Recommended Tools:**
- NVDA (Windows, free)
- JAWS (Windows, paid)
- VoiceOver (macOS/iOS, built-in)
- TalkBack (Android, built-in)

**Test Scenarios:**
- [ ] All content is announced
- [ ] Form errors are announced
- [ ] Dynamic content updates announced
- [ ] Landmark navigation works
- [ ] Headings navigation works
- [ ] Button/link purpose is clear

---

### 7.4 Zoom Testing

**Test at:**
- [ ] 100% (default)
- [ ] 150% (common)
- [ ] 200% (WCAG requirement)
- [ ] 400% (extreme, but should not break)

**Verify:**
- [ ] No horizontal scrolling (except data tables)
- [ ] Text remains readable
- [ ] No content overlap
- [ ] Interactive elements still clickable

---

## 8. Common Mistakes to Avoid

### 8.1 Don'ts

❌ **Removing focus outlines:**
```css
/* NEVER DO THIS */
* { outline: none; }
button:focus { outline: none; }
```

❌ **Empty links/buttons:**
```html
<a href="/profile"><img src="avatar.jpg" /></a>
<!-- Needs alt text on image -->

<button><i class="icon-close"></i></button>
<!-- Needs accessible label -->
```

❌ **Div/span buttons:**
```html
<div onclick="submit()">Submit</div>
<!-- Use <button> -->
```

❌ **Auto-playing media:**
```html
<video autoplay>...</video>
<!-- Violates WCAG 2.2 (unless user initiated) -->
```

❌ **Placeholder as label:**
```html
<input type="text" placeholder="Email" />
<!-- Needs <label> -->
```

---

### 8.2 Do's

✅ **Proper button markup:**
```html
<button type="button" aria-label="Close modal">
  <span aria-hidden="true">×</span>
</button>
```

✅ **Form labels:**
```html
<label for="email">Email <span aria-label="required">*</span></label>
<input type="email" id="email" name="email" required aria-required="true" />
```

✅ **Descriptive links:**
```html
<!-- Bad -->
<a href="/tournament/123">Click here</a>

<!-- Good -->
<a href="/tournament/123">Register for Summer Championship</a>
```

✅ **Semantic HTML:**
```html
<nav aria-label="Primary">
  <ul>
    <li><a href="/">Home</a></li>
    <li><a href="/tournaments">Tournaments</a></li>
  </ul>
</nav>
```

---

## 9. Resources

**Official Documentation:**
- WCAG 2.1 Guidelines: https://www.w3.org/WAI/WCAG21/quickref/
- ARIA Authoring Practices: https://www.w3.org/WAI/ARIA/apg/

**Testing Tools:**
- axe DevTools: https://www.deque.com/axe/devtools/
- WAVE: https://wave.webaim.org/
- Color Contrast Analyzer: https://www.tpgi.com/color-contrast-checker/

**Learning:**
- WebAIM: https://webaim.org/
- A11ycasts (videos): https://www.youtube.com/playlist?list=PLNYkxOF6rcICWx0C9LVWWVqvHlYJyqw7g

**End of Accessibility Guidelines**
