# PART 4.2: UI/UX Design Specifications - Form Components & Navigation

**Navigation:**  
← [Previous: PART_4.1_UI_UX_DESIGN_FOUNDATIONS.md](PART_4.1_UI_UX_DESIGN_FOUNDATIONS.md) | [Next: PART_4.3 (Tournament Management Screens - Coming Soon)](PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md) →

**Contents:** Additional Form Elements (Checkbox, Radio, Textarea, File Upload), Badges & Tags, Modal/Dialog, Navigation Components (Navbar, Breadcrumbs, Tabs), Loading States, Toast Notifications, Alerts, Dropdowns, Pagination

---

*This is Part 4.2 of the UI/UX Design Specifications (Lines 1401-2801 from PROPOSAL_PART_4_UI_UX_DESIGN_SPECIFICATIONS.md)*

---

### 4.3 Form Elements (Continued)

**Select Icon Continuation:**

```css
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
    color: var(--brand-primary);
    background: rgba(59, 130, 246, 0.1);
    border-color: var(--brand-primary);
    pointer-events: none;
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

**End of Part 4.2: UI Components & Navigation**

---

**Navigation:**  
← [Previous: PART_4.1_UI_UX_DESIGN_FOUNDATIONS.md](PART_4.1_UI_UX_DESIGN_FOUNDATIONS.md) | [Next: PART_4.3 (Tournament Management Screens - Coming Soon)](PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md) →
