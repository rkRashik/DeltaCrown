# DeltaCrown UI Patterns & Best Practices

**Epic:** Phase 9, Epic 9.3 - UI/UX Framework & Design Tokens  
**Date:** December 10, 2025  
**Purpose:** Standard UI patterns and usage guidelines for consistent user experience

---

## 1. Form Patterns

### 1.1 Standard Form Layout

**Pattern:**
```html
<form method="POST" class="space-y-6">
  <div class="form-field">
    <label for="username" class="block text-sm font-medium text-neutral-700">
      Username <span class="text-error-500">*</span>
    </label>
    <input 
      type="text" 
      id="username" 
      name="username"
      class="mt-1 block w-full rounded-md border-neutral-300 shadow-sm focus:border-brand-primary-500 focus:ring-brand-primary-500"
      required
      aria-describedby="username-help username-error"
    />
    <p id="username-help" class="mt-1 text-sm text-neutral-500">
      Choose a unique username (3-20 characters)
    </p>
    <p id="username-error" class="mt-1 text-sm text-error-600" role="alert">
      <!-- Error message appears here -->
    </p>
  </div>
  
  <div class="form-actions">
    <button type="button" class="btn-secondary">Cancel</button>
    <button type="submit" class="btn-primary">Submit</button>
  </div>
</form>
```

**Rules:**
- Required fields marked with red asterisk
- Help text below input (neutral color)
- Error messages below help text (error color, role="alert")
- Submit button on right, Cancel on left
- Vertical spacing: `space-y-6` between fields

---

### 1.2 Multi-Step Form (Wizard)

**Pattern:**
```html
<div class="wizard">
  <!-- Progress Indicator -->
  <div class="wizard-progress">
    <div class="step completed">
      <div class="step-number">1</div>
      <div class="step-label">Team</div>
    </div>
    <div class="step-connector completed"></div>
    <div class="step active">
      <div class="step-number">2</div>
      <div class="step-label">Identity</div>
    </div>
    <div class="step-connector"></div>
    <div class="step">
      <div class="step-number">3</div>
      <div class="step-label">Questions</div>
    </div>
  </div>
  
  <!-- Current Step Content -->
  <div class="wizard-step-content">
    <!-- Step 2 fields here -->
  </div>
  
  <!-- Navigation -->
  <div class="wizard-navigation">
    <button type="button" class="btn-secondary">Back</button>
    <button type="button" class="btn-ghost">Save as Draft</button>
    <button type="submit" class="btn-primary">Next</button>
  </div>
</div>
```

**Rules:**
- Show progress (current step of total)
- Validate before advancing
- Save draft functionality
- Disable "Back" on step 1
- Change "Next" to "Submit" on last step

---

### 1.3 Inline Validation

**Pattern:**
```javascript
// Real-time validation (debounced)
const input = document.getElementById('email');
let validationTimeout;

input.addEventListener('input', (e) => {
  clearTimeout(validationTimeout);
  validationTimeout = setTimeout(() => {
    validateField(e.target);
  }, 500); // Wait 500ms after typing stops
});

function validateField(field) {
  const value = field.value;
  const errorEl = document.getElementById(`${field.id}-error`);
  
  // Client-side validation
  if (!value.includes('@')) {
    field.setAttribute('aria-invalid', 'true');
    field.classList.add('border-error-500');
    errorEl.textContent = 'Invalid email format';
    return;
  }
  
  // AJAX validation (check availability)
  fetch(`/api/validate-field/`, {
    method: 'POST',
    body: JSON.stringify({ field: field.name, value: value }),
    headers: { 'Content-Type': 'application/json' }
  })
  .then(res => res.json())
  .then(data => {
    if (data.valid) {
      field.setAttribute('aria-invalid', 'false');
      field.classList.remove('border-error-500');
      field.classList.add('border-success-500');
      errorEl.textContent = '';
    } else {
      field.setAttribute('aria-invalid', 'true');
      field.classList.add('border-error-500');
      errorEl.textContent = data.error;
    }
  });
}
```

**Rules:**
- Debounce input (wait for user to stop typing)
- Show validation after first blur, then on every change
- Use AJAX sparingly (username availability, game ID verification)
- Never rely solely on client-side validation

---

### 1.4 Auto-Save Drafts

**Pattern:**
```javascript
let draftTimeout;
const DRAFT_SAVE_INTERVAL = 30000; // 30 seconds

function autosaveDraft() {
  const formData = new FormData(document.getElementById('registration-form'));
  const draftId = document.querySelector('[name="draft_id"]').value;
  
  fetch(`/api/v1/drafts/${draftId}/autosave/`, {
    method: 'POST',
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    updateSaveStatus('Saved ' + formatTimeAgo(new Date()));
  });
}

// Start autosave on form interaction
document.getElementById('registration-form').addEventListener('input', () => {
  clearTimeout(draftTimeout);
  draftTimeout = setTimeout(autosaveDraft, DRAFT_SAVE_INTERVAL);
  updateSaveStatus('Unsaved changes...');
});
```

**Rules:**
- Auto-save every 30 seconds after last change
- Show save status ("Saved 5 seconds ago")
- Manual "Save as Draft" button
- Recover draft on return (show banner)

---

## 2. Card Patterns

### 2.1 Tournament Card Grid

**Pattern:**
```html
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
  {% for tournament in tournaments %}
  <article class="card hoverable">
    <div class="card-header">
      <img src="{{ tournament.game_icon }}" alt="{{ tournament.game_name }}" class="w-12 h-12" />
      <h3 class="text-xl font-semibold">{{ tournament.name }}</h3>
    </div>
    <div class="card-body">
      <div class="flex justify-between mb-2">
        <span class="badge badge-tournament-{{ tournament.status }}">
          {{ tournament.status|title }}
        </span>
        <span class="badge badge-format">
          {{ tournament.format|title }}
        </span>
      </div>
      <div class="text-sm text-neutral-600 space-y-1">
        <div>📅 {{ tournament.start_date }} - {{ tournament.end_date }}</div>
        <div>👥 {{ tournament.current_participants }} / {{ tournament.max_participants }}</div>
        {% if tournament.entry_fee %}
        <div>💰 Entry: {{ tournament.entry_fee }} DC</div>
        {% endif %}
        {% if tournament.prize_pool %}
        <div>🏆 Prize: {{ tournament.prize_pool }} DC</div>
        {% endif %}
      </div>
    </div>
    <div class="card-footer">
      <a href="{% url 'tournament-detail' tournament.id %}" class="btn-primary w-full">
        {% if tournament.can_register %}
          Register Now
        {% elif tournament.status == 'in_progress' %}
          View Bracket
        {% else %}
          View Details
        {% endif %}
      </a>
    </div>
  </article>
  {% endfor %}
</div>
```

**Rules:**
- Responsive grid (1 col mobile, 2 tablet, 3 desktop)
- Consistent card height
- Hover effect (lift)
- Status badge prominent
- CTA button conditional on status

---

### 2.2 Match Card (Compact)

**Pattern:**
```html
<div class="match-card match-status-{{ match.status }}">
  <div class="match-header">
    <span class="text-sm text-neutral-500">{{ match.tournament_name }} - Round {{ match.round }}</span>
    <span class="badge badge-match-{{ match.status }}">{{ match.status|title }}</span>
  </div>
  <div class="match-participants">
    <div class="participant {{ match.winner_id == match.participant1_id ? 'winner' : '' }}">
      <img src="{{ match.participant1_avatar }}" alt="" class="w-8 h-8 rounded-full" />
      <span class="font-medium">{{ match.participant1_name }}</span>
      {% if match.score %}<span class="score">{{ match.score.split('-')[0] }}</span>{% endif %}
    </div>
    <div class="text-neutral-400">vs</div>
    <div class="participant {{ match.winner_id == match.participant2_id ? 'winner' : '' }}">
      <img src="{{ match.participant2_avatar }}" alt="" class="w-8 h-8 rounded-full" />
      <span class="font-medium">{{ match.participant2_name }}</span>
      {% if match.score %}<span class="score">{{ match.score.split('-')[1] }}</span>{% endif %}
    </div>
  </div>
  {% if match.scheduled_at %}
  <div class="match-time">
    🕐 {{ match.scheduled_at|date:"M d, Y g:i A" }}
  </div>
  {% endif %}
</div>
```

**CSS:**
```css
.match-card {
  border-left: 4px solid var(--neutral-300);
  padding: 1rem;
  border-radius: 0.5rem;
  background: white;
}

.match-status-live {
  border-left-color: var(--error-500);
  animation: pulse 2s infinite;
}

.participant.winner {
  font-weight: 700;
  color: var(--success-600);
}
```

**Rules:**
- Color-coded border by status
- Winner highlighted (bold, green)
- Time shown if scheduled
- Pulsing animation for live matches

---

## 3. Modal Patterns

### 3.1 Confirmation Modal

**Pattern:**
```html
<div id="confirm-modal" class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-title" hidden>
  <div class="modal-backdrop" onclick="closeModal()"></div>
  <div class="modal-content modal-sm">
    <div class="modal-header">
      <h3 id="modal-title" class="text-lg font-semibold">Confirm Action</h3>
      <button onclick="closeModal()" class="modal-close" aria-label="Close">×</button>
    </div>
    <div class="modal-body">
      <p>Are you sure you want to cancel your registration? This action cannot be undone.</p>
    </div>
    <div class="modal-footer">
      <button onclick="closeModal()" class="btn-secondary">Cancel</button>
      <button onclick="confirmAction()" class="btn-danger">Confirm</button>
    </div>
  </div>
</div>
```

**JavaScript:**
```javascript
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  modal.removeAttribute('hidden');
  document.body.style.overflow = 'hidden'; // Prevent scroll
  
  // Focus trap
  const focusable = modal.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  const firstFocusable = focusable[0];
  const lastFocusable = focusable[focusable.length - 1];
  
  firstFocusable.focus();
  
  modal.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal(modalId);
    if (e.key === 'Tab') {
      if (e.shiftKey && document.activeElement === firstFocusable) {
        e.preventDefault();
        lastFocusable.focus();
      } else if (!e.shiftKey && document.activeElement === lastFocusable) {
        e.preventDefault();
        firstFocusable.focus();
      }
    }
  });
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId || 'confirm-modal');
  modal.setAttribute('hidden', '');
  document.body.style.overflow = ''; // Restore scroll
}
```

**Rules:**
- Destructive actions (Delete, Cancel registration): Use danger button
- Focus trap (Tab cycles within modal)
- Escape key closes modal
- Backdrop click closes modal (optional)
- Restore focus to trigger element on close

---

### 3.2 Form Modal

**Pattern:**
```html
<div id="result-submit-modal" class="modal" hidden>
  <div class="modal-backdrop"></div>
  <div class="modal-content modal-lg">
    <form method="POST" id="result-form">
      <div class="modal-header">
        <h3>Submit Match Result</h3>
        <button type="button" onclick="closeModal('result-submit-modal')" class="modal-close">×</button>
      </div>
      <div class="modal-body">
        <!-- Form fields -->
        <div class="form-field">
          <label for="winner">Winner</label>
          <select id="winner" name="winner" required>
            <option value="">Select Winner</option>
            <option value="participant1">{{ match.participant1_name }}</option>
            <option value="participant2">{{ match.participant2_name }}</option>
          </select>
        </div>
        <div class="form-field">
          <label for="score">Score</label>
          <input type="text" id="score" name="score" placeholder="2-1" required />
        </div>
        <div class="form-field">
          <label for="proof">Proof Screenshot</label>
          <input type="file" id="proof" name="proof" accept="image/*" required />
        </div>
      </div>
      <div class="modal-footer">
        <button type="button" onclick="closeModal('result-submit-modal')" class="btn-secondary">Cancel</button>
        <button type="submit" class="btn-primary">Submit Result</button>
      </div>
    </form>
  </div>
</div>
```

**Rules:**
- Form inside modal
- Validation before submit
- Loading state on submit (disable buttons, show spinner)
- Close on successful submit
- Keep open on validation error

---

## 4. Table Patterns

### 4.1 Responsive Data Table

**Pattern:**
```html
<!-- Desktop: Full table -->
<div class="hidden md:block overflow-x-auto">
  <table class="data-table">
    <thead>
      <tr>
        <th scope="col">Rank</th>
        <th scope="col">Player</th>
        <th scope="col" class="sortable" onclick="sort('wins')">
          Wins <span class="sort-icon">↕</span>
        </th>
        <th scope="col">Losses</th>
        <th scope="col">Win Rate</th>
        <th scope="col">Points</th>
      </tr>
    </thead>
    <tbody>
      {% for player in standings %}
      <tr class="{% if player.rank <= 4 %}bg-success-50{% endif %}">
        <td>{{ player.rank }}</td>
        <td>
          <div class="flex items-center gap-2">
            <img src="{{ player.avatar }}" alt="" class="w-8 h-8 rounded-full" />
            <span class="font-medium">{{ player.name }}</span>
          </div>
        </td>
        <td>{{ player.wins }}</td>
        <td>{{ player.losses }}</td>
        <td>{{ player.win_rate }}%</td>
        <td>{{ player.points }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- Mobile: Card layout -->
<div class="md:hidden space-y-4">
  {% for player in standings %}
  <div class="card">
    <div class="flex justify-between items-start">
      <div class="flex items-center gap-2">
        <span class="text-2xl font-bold text-neutral-400">#{{ player.rank }}</span>
        <img src="{{ player.avatar }}" alt="" class="w-12 h-12 rounded-full" />
        <div>
          <div class="font-medium">{{ player.name }}</div>
          <div class="text-sm text-neutral-500">{{ player.wins }}W - {{ player.losses }}L</div>
        </div>
      </div>
      <div class="text-right">
        <div class="text-lg font-bold">{{ player.points }}</div>
        <div class="text-sm text-neutral-500">{{ player.win_rate }}%</div>
      </div>
    </div>
  </div>
  {% endfor %}
</div>
```

**Rules:**
- Desktop: Full table with all columns
- Mobile: Card layout with essential info
- Highlight top ranks (green background)
- Sortable columns (click header)
- Sticky header on scroll

---

### 4.2 Pagination

**Pattern:**
```html
<nav class="pagination" aria-label="Pagination">
  <div class="pagination-info">
    Showing {{ start }}-{{ end }} of {{ total }} results
  </div>
  <div class="pagination-controls">
    <a href="?page=1" class="pagination-btn" {% if page == 1 %}aria-disabled="true"{% endif %}>
      First
    </a>
    <a href="?page={{ page - 1 }}" class="pagination-btn" {% if page == 1 %}aria-disabled="true"{% endif %}>
      Previous
    </a>
    
    {% for page_num in page_range %}
      {% if page_num == '...' %}
        <span class="pagination-ellipsis">...</span>
      {% else %}
        <a href="?page={{ page_num }}" class="pagination-num {% if page_num == page %}active{% endif %}" {% if page_num == page %}aria-current="page"{% endif %}>
          {{ page_num }}
        </a>
      {% endif %}
    {% endfor %}
    
    <a href="?page={{ page + 1 }}" class="pagination-btn" {% if page == total_pages %}aria-disabled="true"{% endif %}>
      Next
    </a>
    <a href="?page={{ total_pages }}" class="pagination-btn" {% if page == total_pages %}aria-disabled="true"{% endif %}>
      Last
    </a>
  </div>
</nav>
```

**Rules:**
- Show total count
- Truncate middle pages (1 2 ... 5 6 7 ... 10)
- Disable First/Previous on page 1
- Disable Last/Next on last page
- Highlight current page

---

## 5. Notification Patterns

### 5.1 Toast Notifications

**Pattern:**
```javascript
function showToast(message, variant = 'info', duration = 5000) {
  const toast = document.createElement('div');
  toast.className = `toast toast-${variant}`;
  toast.innerHTML = `
    <div class="toast-icon">${getIcon(variant)}</div>
    <div class="toast-message">${message}</div>
    <button onclick="this.parentElement.remove()" class="toast-close" aria-label="Close">×</button>
  `;
  
  document.getElementById('toast-container').appendChild(toast);
  
  // Auto-dismiss
  setTimeout(() => {
    toast.classList.add('toast-exit');
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

// Usage
showToast('Registration successful!', 'success');
showToast('Failed to save changes', 'error');
```

**HTML:**
```html
<div id="toast-container" class="fixed top-4 right-4 z-tooltip space-y-2"></div>
```

**CSS:**
```css
.toast {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 0.5rem;
  box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
  animation: slideIn 0.3s ease-out;
}

.toast-success { background: var(--success-50); color: var(--success-800); }
.toast-error { background: var(--error-50); color: var(--error-800); }
.toast-warning { background: var(--warning-50); color: var(--warning-800); }
.toast-info { background: var(--info-50); color: var(--info-800); }

@keyframes slideIn {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
```

**Rules:**
- Position: Top-right corner
- Stack vertically (newest on top)
- Auto-dismiss after 5 seconds
- Manual close button
- Slide-in animation

---

### 5.2 Banner Alerts

**Pattern:**
```html
<div class="alert alert-warning" role="alert">
  <div class="alert-icon">⚠️</div>
  <div class="alert-content">
    <strong>Draft Recovered</strong>
    <p>We found an unsaved registration draft from December 9. Would you like to continue?</p>
  </div>
  <div class="alert-actions">
    <button onclick="recoverDraft()" class="btn-sm btn-primary">Continue</button>
    <button onclick="dismissAlert(this)" class="btn-sm btn-secondary">Dismiss</button>
  </div>
</div>
```

**Rules:**
- Full-width banner at top of page
- Variant colors (success, warning, error, info)
- Dismissible (X button or close action)
- Persistent (doesn't auto-dismiss)

---

## 6. Loading States

### 6.1 Loading Spinner

**Pattern:**
```html
<div class="flex items-center justify-center h-64">
  <div class="spinner" role="status" aria-label="Loading">
    <span class="sr-only">Loading...</span>
  </div>
</div>
```

**CSS:**
```css
.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid var(--neutral-200);
  border-top-color: var(--brand-primary-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

---

### 6.2 Skeleton Loaders

**Pattern:**
```html
<div class="skeleton-card">
  <div class="skeleton-header"></div>
  <div class="skeleton-body">
    <div class="skeleton-line"></div>
    <div class="skeleton-line"></div>
    <div class="skeleton-line w-3/4"></div>
  </div>
</div>
```

**CSS:**
```css
.skeleton-header, .skeleton-line {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
```

**Rules:**
- Match layout of actual content
- Pulse/shimmer animation
- Show during initial load
- Replace with real content smoothly

---

## 7. Empty States

### 7.1 No Results Pattern

**Pattern:**
```html
<div class="empty-state">
  <div class="empty-icon">
    <svg><!-- Trophy icon --></svg>
  </div>
  <h3 class="empty-title">No Tournaments Found</h3>
  <p class="empty-description">
    Try adjusting your filters or browse all tournaments.
  </p>
  <a href="{% url 'tournaments' %}" class="btn-primary">Browse All Tournaments</a>
</div>
```

**CSS:**
```css
.empty-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 1.5rem;
  color: var(--neutral-300);
}

.empty-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: var(--neutral-700);
  margin-bottom: 0.5rem;
}

.empty-description {
  color: var(--neutral-500);
  margin-bottom: 1.5rem;
}
```

---

## 8. Best Practices Summary

### Performance
- Lazy load images (`loading="lazy"`)
- Minimize JavaScript (use vanilla where possible)
- Debounce expensive operations (search, validation)
- Use CSS transitions (faster than JS animations)

### Accessibility
- Semantic HTML always
- Proper heading hierarchy (H1 → H2 → H3)
- ARIA when needed (not on everything)
- Keyboard navigation tested
- Color contrast verified

### Responsive Design
- Mobile-first approach
- Test on real devices
- Touch targets ≥ 44px
- Avoid horizontal scroll

### Consistency
- Use design tokens (don't hardcode colors)
- Follow component library
- Consistent spacing (use design system)
- Consistent terminology

**End of UI Patterns Guide**
