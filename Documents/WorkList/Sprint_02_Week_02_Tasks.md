# Sprint 2 - Week 2: Authentication UI & Design System

**Sprint Goal:** Build authentication UI and establish design system foundation  
**Duration:** Week 2 (5 days)  
**Story Points:** 45  
**Team:** Frontend (3), Backend (2), QA (1), DevOps (1)  
**Linked Epic:** Epic 1 - Project Foundation (see `00_BACKLOG_OVERVIEW.md`)

---

## 📋 Task Cards - Frontend Track (25 points)

### **FE-001: Tailwind CSS Setup & Configuration**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 3  
**Assignee:** Frontend Dev 1  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Set up Tailwind CSS with custom configuration, PostCSS processing, and integration with Django templates. Configure build pipeline for CSS optimization.

**Acceptance Criteria:**
- [ ] Tailwind CSS 3.4+ installed via npm
- [ ] `tailwind.config.js` configured with custom theme
- [ ] PostCSS configured for Tailwind processing
- [ ] Django template integration via `{% load static %}`
- [ ] Purge configuration removes unused CSS in production
- [ ] Build script: `npm run build:css` generates `static/css/main.css`
- [ ] Watch script: `npm run watch:css` enables hot reload during development
- [ ] Custom `@layer` directives for base, components, utilities
- [ ] Dark mode support configured (class-based strategy)
- [ ] Font families configured (system fonts + Google Fonts fallback)

**Dependencies:**
- BE-003 (Django static files configuration)

**Technical Notes:**
- Use JIT (Just-In-Time) mode for faster builds
- Configure content paths to scan Django templates: `./templates/**/*.html`
- Dark mode toggle implemented with Alpine.js in later sprint
- Reference: PROPOSAL_PART_4.md Section 10.1 (Design System Foundation)

**Files to Create/Modify:**
- `package.json` (new)
- `tailwind.config.js` (new)
- `postcss.config.js` (new)
- `static/css/main.css` (new - Tailwind directives)
- `templates/base.html` (link compiled CSS)
- `.gitignore` (add `node_modules/`)

**tailwind.config.js Example:**
```javascript
module.exports = {
  content: ['./templates/**/*.html', './apps/**/templates/**/*.html'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#eff6ff',
          500: '#3b82f6',
          900: '#1e3a8a',
        },
        accent: {
          500: '#f59e0b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}
```

**Testing:**
- Run `npm run build:css` → verify `static/css/main.css` generated
- Add Tailwind class to template → verify styling applies
- Build production CSS → verify purged (small file size)
- Test responsive breakpoints: `sm:`, `md:`, `lg:`, `xl:`, `2xl:`

---

### **FE-002: Design Tokens (Colors, Typography, Spacing)**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 5  
**Assignee:** Frontend Dev 1  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Define comprehensive design token system for colors, typography, spacing, shadows, and borders. Create CSS custom properties and Tailwind theme configuration aligned with brand guidelines.

**Acceptance Criteria:**
- [ ] Color palette defined: Primary, Secondary, Accent, Neutral, Semantic (success, warning, error, info)
- [ ] Typography scale defined: 5 font sizes (xs, sm, base, lg, xl, 2xl, 3xl, 4xl)
- [ ] Font weights: 400 (normal), 500 (medium), 600 (semibold), 700 (bold)
- [ ] Spacing scale: 0.5rem increments (0, 0.5, 1, 1.5, 2, 3, 4, 6, 8, 12, 16, 24rem)
- [ ] Border radius: sm (0.25rem), md (0.5rem), lg (1rem), full (9999px)
- [ ] Box shadows: sm, md, lg, xl for elevation
- [ ] CSS custom properties defined in `:root` for runtime theming
- [ ] Design tokens documented in `docs/DESIGN_SYSTEM.md`
- [ ] Storybook setup to preview design tokens
- [ ] Dark mode color palette defined

**Dependencies:**
- FE-001 (Tailwind CSS)

**Technical Notes:**
- Use HSL color format for easy manipulation
- CSS custom properties enable dynamic theming
- Semantic colors (success, error) improve UX consistency
- Reference: PROPOSAL_PART_4.md Section 10.2 (Design Tokens)

**Files to Create/Modify:**
- `static/css/design-tokens.css` (new)
- `tailwind.config.js` (extend theme with tokens)
- `docs/DESIGN_SYSTEM.md` (new)
- `.storybook/main.js` (new - Storybook config)

**Design Tokens Example:**
```css
:root {
  /* Colors - Primary */
  --color-primary-50: 239 246 255;
  --color-primary-500: 59 130 246;
  --color-primary-900: 30 58 138;
  
  /* Typography */
  --font-size-xs: 0.75rem;
  --font-size-base: 1rem;
  --font-size-xl: 1.25rem;
  --font-weight-normal: 400;
  --font-weight-semibold: 600;
  
  /* Spacing */
  --spacing-1: 0.25rem;
  --spacing-4: 1rem;
  --spacing-8: 2rem;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}
```

**Testing:**
- Apply token classes: `bg-primary-500`, `text-xl`, `p-4` → verify styling
- Toggle dark mode → verify dark mode colors apply
- Open Storybook → verify all tokens visible
- Measure color contrast ratios → ensure WCAG AA compliance (4.5:1 minimum)

---

### **FE-003: Login Page**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 5  
**Assignee:** Frontend Dev 2  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Create login page with email/password form, validation, error handling, and JWT token management. Implement "Remember Me" and "Forgot Password" links.

**Acceptance Criteria:**
- [ ] Login page accessible at `/login/`
- [ ] Form fields: Email (email input), Password (password input with show/hide toggle)
- [ ] "Remember Me" checkbox extends token expiry to 30 days
- [ ] Client-side validation: Email format, password min length (8 chars)
- [ ] Server-side validation error display (invalid credentials, account locked)
- [ ] Loading state during authentication (button disabled, spinner shown)
- [ ] Success: Redirect to dashboard, store tokens in localStorage/cookie
- [ ] Error: Display error message below form (non-intrusive)
- [ ] "Forgot Password?" link to password reset page
- [ ] "Don't have an account? Sign up" link to registration page
- [ ] Fully responsive (mobile-first design)
- [ ] Accessibility: ARIA labels, keyboard navigation, focus management

**Dependencies:**
- FE-002 (Design tokens)
- BE-005 (Login API endpoint)

**Technical Notes:**
- Use HTMX for form submission (no page reload)
- Store access token in memory, refresh token in httpOnly cookie (security best practice)
- Implement CSRF protection with Django `{% csrf_token %}`
- Reference: PROPOSAL_PART_4.md Section 4.1 (Login Screen)

**Files to Create/Modify:**
- `templates/account/login.html` (new)
- `apps/accounts/views.py` (add `LoginView` class-based view)
- `apps/accounts/urls.py` (add `/login/` route)
- `static/js/auth.js` (new - token management)

**HTML Structure Example:**
```html
<div class="min-h-screen flex items-center justify-center bg-gray-50">
  <div class="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow-md">
    <h2 class="text-3xl font-bold text-center text-gray-900">Sign in to DeltaCrown</h2>
    
    <form hx-post="/api/auth/login/" hx-target="#error-message" hx-swap="innerHTML">
      <div id="error-message" class="text-red-600 text-sm mb-4"></div>
      
      <label for="email" class="block text-sm font-medium text-gray-700">Email</label>
      <input type="email" id="email" name="email" required 
             class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
      
      <label for="password" class="block text-sm font-medium text-gray-700 mt-4">Password</label>
      <input type="password" id="password" name="password" required 
             class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md">
      
      <button type="submit" class="w-full mt-6 bg-primary-500 text-white py-2 rounded-md hover:bg-primary-600">
        Sign In
      </button>
    </form>
  </div>
</div>
```

**Testing:**
- Submit empty form → validation errors shown
- Submit invalid email → "Invalid email format" error
- Submit wrong password → "Invalid credentials" error
- Submit valid credentials → redirect to `/dashboard/`, tokens stored
- Test "Remember Me" → verify extended token expiry
- Test keyboard navigation: Tab through form, Enter to submit
- Test screen reader: Verify ARIA labels announced correctly

---

### **FE-004: Registration Page**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 5  
**Assignee:** Frontend Dev 2  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Create user registration page with multi-field form, real-time validation, password strength indicator, and email verification notice.

**Acceptance Criteria:**
- [ ] Registration page accessible at `/register/`
- [ ] Form fields: Email, Password, Confirm Password, First Name, Last Name, Country (dropdown)
- [ ] Real-time validation (as user types):
  - Email format validation
  - Password strength indicator (weak/medium/strong)
  - Password match validation (Confirm Password field)
  - First/Last name required
- [ ] Server-side validation error display
- [ ] Password requirements tooltip: "Min 8 chars, 1 letter, 1 number"
- [ ] Country dropdown with 200+ countries (use `django-countries`)
- [ ] Terms of Service and Privacy Policy checkboxes (required)
- [ ] Success: Show "Check your email to verify account" message
- [ ] Loading state during submission
- [ ] "Already have an account? Sign in" link
- [ ] Fully responsive and accessible

**Dependencies:**
- FE-003 (Login page for reference)
- BE-005 (Register API endpoint)

**Technical Notes:**
- Use `zxcvbn` library for password strength calculation
- Terms/Privacy links open in new tab (target="_blank")
- Email verification link sent via Celery background task
- Reference: PROPOSAL_PART_4.md Section 4.2 (Registration Flow)

**Files to Create/Modify:**
- `templates/account/register.html` (new)
- `apps/accounts/views.py` (add `RegisterView`)
- `apps/accounts/urls.py` (add `/register/` route)
- `static/js/password-strength.js` (new)
- `package.json` (add `zxcvbn` dependency)

**Password Strength Indicator:**
```javascript
import zxcvbn from 'zxcvbn';

function updatePasswordStrength(password) {
  const result = zxcvbn(password);
  const strength = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'][result.score];
  const color = ['red', 'orange', 'yellow', 'green', 'green'][result.score];
  
  document.getElementById('strength').textContent = strength;
  document.getElementById('strength-bar').style.width = `${(result.score + 1) * 20}%`;
  document.getElementById('strength-bar').className = `bg-${color}-500 h-2 transition-all`;
}
```

**Testing:**
- Type email → verify format validation
- Type password → verify strength indicator updates (weak → strong)
- Mismatch passwords → verify error shown
- Submit without accepting terms → validation error
- Submit valid form → "Check your email" message shown
- Verify email sent to inbox with activation link

---

### **FE-005: Password Reset Flow**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 4  
**Assignee:** Frontend Dev 3  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Implement complete password reset flow: Request reset page → Email with token → Reset password page. Handle token expiry and invalid token scenarios.

**Acceptance Criteria:**
- [ ] **Page 1:** Password reset request at `/password-reset/`
  - Single email input field
  - "Send reset link" button
  - Success message: "Check your email for reset link"
  - Works even if email not found (security: don't reveal user existence)
- [ ] **Page 2:** Reset password at `/password-reset/confirm/<token>/`
  - New password and confirm password fields
  - Password strength indicator
  - Token validation (expired, invalid, already used)
  - Success: Redirect to login with "Password reset successful" message
- [ ] Email template with reset link (valid for 1 hour)
- [ ] Rate limiting: Max 3 reset requests per email per hour
- [ ] Loading states and error handling
- [ ] Fully responsive and accessible

**Dependencies:**
- FE-004 (Registration page for password UI reference)
- BE-005 (Password reset API endpoints)

**Technical Notes:**
- Use Django's built-in password reset token generator
- Token should be single-use (invalidated after reset)
- Email should be HTML formatted with branded design
- Reference: PROPOSAL_PART_4.md Section 4.3 (Password Reset Flow)

**Files to Create/Modify:**
- `templates/account/password_reset.html` (new)
- `templates/account/password_reset_confirm.html` (new)
- `templates/emails/password_reset_email.html` (new)
- `apps/accounts/views.py` (add `PasswordResetView`, `PasswordResetConfirmView`)
- `apps/accounts/urls.py` (add reset routes)

**Email Template Example:**
```html
<div style="max-width: 600px; margin: 0 auto; font-family: sans-serif;">
  <h2>Reset Your Password</h2>
  <p>Hi {{ user.first_name }},</p>
  <p>You requested to reset your password for your DeltaCrown account.</p>
  <p>Click the button below to reset your password:</p>
  <a href="{{ reset_url }}" style="background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;">
    Reset Password
  </a>
  <p style="color: #666; font-size: 14px;">This link expires in 1 hour.</p>
  <p style="color: #666; font-size: 14px;">If you didn't request this, please ignore this email.</p>
</div>
```

**Testing:**
- Submit email for reset → verify email received
- Click reset link → verify token valid, form shown
- Submit new password → verify password changed, can login
- Try reset link again → verify token invalidated ("Link already used")
- Wait 1 hour, try link → verify expired ("Link expired")
- Submit 4 reset requests in 1 hour → verify rate limit ("Too many requests")

---

### **FE-006: Profile Settings Page**

**Type:** Story  
**Priority:** Medium (P2)  
**Story Points:** 3  
**Assignee:** Frontend Dev 3  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Create user profile settings page for editing account information, uploading avatar, changing password, and account preferences.

**Acceptance Criteria:**
- [ ] Profile page accessible at `/profile/` (requires authentication)
- [ ] **Section 1: Account Information**
  - Edit: First Name, Last Name, Email, Phone, Date of Birth, Country, Bio
  - Avatar upload with preview (max 2MB, JPG/PNG only)
  - "Save Changes" button
- [ ] **Section 2: Change Password**
  - Current Password, New Password, Confirm New Password
  - Password strength indicator
  - "Update Password" button (separate from Section 1)
- [ ] **Section 3: Preferences**
  - Email notifications toggle (tournament updates, match reminders)
  - Language selection (English, Spanish, French)
  - Timezone selection (auto-detected, manual override)
- [ ] **Section 4: Account Actions**
  - "Deactivate Account" button (confirmation modal)
  - "Delete Account" button (requires password re-entry)
- [ ] Form validation and error handling
- [ ] Success messages on save
- [ ] Fully responsive (stacked sections on mobile)

**Dependencies:**
- FE-003 (Login for authentication state)
- BE-005 (Profile update API endpoint)

**Technical Notes:**
- Use Dropzone.js or similar for drag-drop avatar upload
- Store avatar in AWS S3 or local media directory
- Deactivate vs Delete: Deactivate hides account, Delete permanently removes
- Reference: PROPOSAL_PART_4.md Section 4.4 (Profile Settings)

**Files to Create/Modify:**
- `templates/account/profile.html` (new)
- `apps/accounts/views.py` (add `ProfileView`)
- `apps/accounts/urls.py` (add `/profile/` route)
- `static/js/avatar-upload.js` (new)

**Testing:**
- Access `/profile/` without login → redirect to login page
- Upload avatar > 2MB → validation error shown
- Update email to existing email → "Email already in use" error
- Change password with wrong current password → error shown
- Toggle email notifications → verify saved
- Click "Delete Account" → confirmation modal shown, requires password

---

## 📋 Task Cards - Frontend Track - Components (15 points)

### **FE-007: Button Component**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 3  
**Assignee:** Frontend Dev 1  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Create reusable button component with multiple variants (primary, secondary, ghost, danger), sizes (sm, md, lg), and states (default, hover, active, disabled, loading).

**Acceptance Criteria:**
- [ ] Button component defined in `templates/components/button.html`
- [ ] **Variants:**
  - Primary: Blue background, white text
  - Secondary: White background, blue border, blue text
  - Ghost: Transparent background, blue text, no border
  - Danger: Red background, white text
- [ ] **Sizes:**
  - Small: px-3 py-1.5 text-sm
  - Medium: px-4 py-2 text-base (default)
  - Large: px-6 py-3 text-lg
- [ ] **States:**
  - Hover: Darker shade
  - Active: Even darker shade
  - Disabled: Gray, cursor-not-allowed
  - Loading: Spinner icon, disabled
- [ ] Icon support (before/after text)
- [ ] Full-width option
- [ ] Usage documented in Storybook
- [ ] Accessibility: Focus ring, keyboard support

**Dependencies:**
- FE-002 (Design tokens)

**Technical Notes:**
- Use Tailwind utility classes (no custom CSS)
- Loading spinner uses SVG animation
- Component should be includable: `{% include 'components/button.html' with text='Click Me' variant='primary' %}`
- Reference: PROPOSAL_PART_4.md Section 10.3 (Button Component)

**Files to Create/Modify:**
- `templates/components/button.html` (new)
- `static/css/components/button.css` (optional custom styles)
- `.storybook/stories/Button.stories.js` (new)

**Component Usage Example:**
```django
{% include 'components/button.html' with 
   text='Save Changes'
   variant='primary'
   size='md'
   icon='save'
   loading=False
   disabled=False
%}
```

**Tailwind Classes Example:**
```html
<!-- Primary Medium Button -->
<button class="px-4 py-2 bg-primary-500 text-white rounded-md hover:bg-primary-600 active:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 transition-colors">
  Save Changes
</button>
```

**Testing:**
- Render button with each variant → verify colors
- Render button with each size → verify dimensions
- Hover button → verify darker shade
- Click disabled button → verify no action
- Click loading button → verify spinner shown
- Tab to button, press Enter → verify activation
- Test with screen reader → verify button announced

---

### **FE-008: Input/Form Components**

**Type:** Story  
**Priority:** Critical (P0)  
**Story Points:** 5  
**Assignee:** Frontend Dev 2  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Create reusable form input components: Text input, Email input, Password input, Textarea, Select dropdown, Checkbox, Radio button. Include label, error state, helper text, and validation.

**Acceptance Criteria:**
- [ ] **Text Input Component:**
  - Label, placeholder, helper text
  - Error state (red border, error message)
  - Required indicator (red asterisk)
  - Disabled state
  - Icon support (prefix/suffix)
- [ ] **Email Input:** Email validation
- [ ] **Password Input:** Show/hide password toggle
- [ ] **Textarea:** Auto-resize option, character count
- [ ] **Select Dropdown:** Custom styling, searchable option
- [ ] **Checkbox:** Label, checked/unchecked states
- [ ] **Radio Button:** Group support
- [ ] All components accessible (ARIA labels, focus management)
- [ ] Documented in Storybook

**Dependencies:**
- FE-002 (Design tokens)
- FE-007 (Button for show/hide toggle)

**Technical Notes:**
- Use `@tailwindcss/forms` plugin for base styling
- Custom select dropdown uses Alpine.js for behavior
- Validation errors use red-600 color
- Reference: PROPOSAL_PART_4.md Section 10.4 (Form Components)

**Files to Create/Modify:**
- `templates/components/input.html` (new)
- `templates/components/textarea.html` (new)
- `templates/components/select.html` (new)
- `templates/components/checkbox.html` (new)
- `templates/components/radio.html` (new)
- `.storybook/stories/FormComponents.stories.js` (new)

**Text Input Example:**
```django
{% include 'components/input.html' with 
   label='Email Address'
   type='email'
   name='email'
   placeholder='you@example.com'
   required=True
   error='Invalid email format'
   helper='We will never share your email'
%}
```

**Password Input with Toggle:**
```html
<div class="relative">
  <input type="password" id="password" class="pr-10 ...">
  <button type="button" class="absolute right-2 top-2" onclick="togglePassword()">
    <svg id="eye-icon">...</svg>
  </button>
</div>
```

**Testing:**
- Render each input type → verify styling
- Set error prop → verify red border and error message
- Test required fields → verify asterisk shown
- Test password toggle → verify type changes password ↔ text
- Test textarea auto-resize → verify height adjusts
- Test select dropdown → verify searchable
- Test with keyboard → verify Tab, Enter, Space work

---

### **FE-009: Card Component**

**Type:** Story  
**Priority:** Medium (P2)  
**Story Points:** 3  
**Assignee:** Frontend Dev 3  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Create reusable card component for displaying content blocks. Support header, body, footer sections, and various styling options (shadow, border, hover effect).

**Acceptance Criteria:**
- [ ] Card component with optional sections:
  - Header: Title, subtitle, actions (buttons, menu)
  - Body: Main content area (accepts any HTML)
  - Footer: Actions or metadata
- [ ] **Variants:**
  - Default: White background, subtle shadow
  - Bordered: Border instead of shadow
  - Elevated: Larger shadow (md)
  - Interactive: Hover lift effect, cursor pointer
- [ ] Padding options: sm, md, lg
- [ ] Full-width or fixed-width
- [ ] Loading state (skeleton loader)
- [ ] Empty state support
- [ ] Documented in Storybook

**Dependencies:**
- FE-002 (Design tokens)

**Technical Notes:**
- Interactive cards use `hover:shadow-lg hover:-translate-y-1 transition-all`
- Skeleton loader uses animated gradient
- Component should be flexible for various use cases (tournament card, user card, stat card)
- Reference: PROPOSAL_PART_4.md Section 10.5 (Card Component)

**Files to Create/Modify:**
- `templates/components/card.html` (new)
- `.storybook/stories/Card.stories.js` (new)

**Component Usage Example:**
```django
{% include 'components/card.html' with 
   variant='elevated'
   interactive=True
   padding='md'
%}
  <div slot="header">
    <h3 class="text-lg font-semibold">Tournament Card</h3>
  </div>
  <div slot="body">
    <p>Tournament details here...</p>
  </div>
  <div slot="footer">
    <button>Register</button>
  </div>
{% endinclude %}
```

**HTML Structure:**
```html
<div class="bg-white rounded-lg shadow-md p-6 hover:shadow-lg hover:-translate-y-1 transition-all cursor-pointer">
  <div class="flex items-center justify-between mb-4">
    <h3 class="text-lg font-semibold text-gray-900">Card Title</h3>
    <span class="text-sm text-gray-500">Badge</span>
  </div>
  <div class="text-gray-600">
    Card body content
  </div>
  <div class="mt-4 pt-4 border-t border-gray-200 flex justify-between">
    <button class="text-primary-500">Action</button>
  </div>
</div>
```

**Testing:**
- Render card with all sections → verify layout
- Hover interactive card → verify lift effect
- Render loading state → verify skeleton animation
- Test on mobile → verify responsive stacking
- Nest cards → verify styling preserved

---

### **FE-010: Modal Component**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 4  
**Assignee:** Frontend Dev 1  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Create reusable modal/dialog component with backdrop, close button, header/body/footer sections, and various sizes. Handle focus trapping and Escape key to close.

**Acceptance Criteria:**
- [ ] Modal component with overlay backdrop (semi-transparent dark)
- [ ] **Sections:**
  - Header: Title, close button (X icon)
  - Body: Scrollable content area
  - Footer: Action buttons (aligned right)
- [ ] **Sizes:** sm (400px), md (600px), lg (800px), full
- [ ] **Behaviors:**
  - Click backdrop → close modal (optional, configurable)
  - Click X button → close modal
  - Press Escape key → close modal
  - Focus trapped within modal (can't Tab outside)
  - Focus returns to trigger element on close
- [ ] Smooth open/close animation (fade + slide)
- [ ] Prevent body scroll when modal open
- [ ] Confirmation modal variant (for delete actions)
- [ ] Documented in Storybook

**Dependencies:**
- FE-007 (Button for modal actions)
- FE-002 (Design tokens)

**Technical Notes:**
- Use Alpine.js for modal state management
- Focus trap using `focusTrap` directive
- Backdrop uses `fixed inset-0 bg-black bg-opacity-50`
- Reference: PROPOSAL_PART_4.md Section 10.6 (Modal Component)

**Files to Create/Modify:**
- `templates/components/modal.html` (new)
- `static/js/modal.js` (new - Alpine.js component)
- `.storybook/stories/Modal.stories.js` (new)

**Alpine.js Modal Example:**
```javascript
Alpine.data('modal', () => ({
  open: false,
  
  show() {
    this.open = true;
    document.body.style.overflow = 'hidden';
    this.$nextTick(() => {
      this.$refs.closeButton.focus();
    });
  },
  
  hide() {
    this.open = false;
    document.body.style.overflow = '';
    this.$refs.trigger.focus();
  },
  
  onEscape(e) {
    if (e.key === 'Escape') this.hide();
  }
}));
```

**HTML Structure:**
```html
<div x-data="modal()" @keydown.escape.window="hide()">
  <!-- Trigger -->
  <button @click="show()" x-ref="trigger">Open Modal</button>
  
  <!-- Modal -->
  <div x-show="open" class="fixed inset-0 z-50 overflow-y-auto">
    <!-- Backdrop -->
    <div class="fixed inset-0 bg-black bg-opacity-50" @click="hide()"></div>
    
    <!-- Modal Content -->
    <div class="relative min-h-screen flex items-center justify-center p-4">
      <div class="relative bg-white rounded-lg max-w-md w-full p-6">
        <button @click="hide()" x-ref="closeButton" class="absolute top-4 right-4">
          <svg><!-- X icon --></svg>
        </button>
        <h2 class="text-xl font-bold mb-4">Modal Title</h2>
        <div class="mb-6">Modal body content</div>
        <div class="flex justify-end gap-2">
          <button @click="hide()">Cancel</button>
          <button>Confirm</button>
        </div>
      </div>
    </div>
  </div>
</div>
```

**Testing:**
- Click trigger → modal opens
- Click backdrop → modal closes
- Press Escape → modal closes
- Tab through elements → focus stays in modal
- Close modal → focus returns to trigger button
- Test nested modals → verify z-index stacking
- Test on mobile → verify responsive sizing
- Test with screen reader → verify ARIA attributes

---

## 📋 Task Cards - Quality Track (5 points)

### **QA-003: Frontend Test Setup (Jest + Testing Library)**

**Type:** Story  
**Priority:** High (P1)  
**Story Points:** 2  
**Assignee:** QA Engineer  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Set up Jest test framework with Testing Library for frontend component testing. Configure test environment, mock modules, and coverage reporting.

**Acceptance Criteria:**
- [ ] Jest 29+ installed and configured
- [ ] Testing Library (DOM) installed
- [ ] `jest.config.js` configured with test patterns
- [ ] Test environment: jsdom (simulates browser)
- [ ] Mock modules configured (fetch, localStorage, Alpine.js)
- [ ] Coverage reporting configured (target >70% for frontend)
- [ ] Test command: `npm test` runs all tests
- [ ] Coverage command: `npm run test:coverage` generates report
- [ ] Example test created: `static/js/__tests__/auth.test.js`
- [ ] CI integration: tests run on every PR

**Dependencies:**
- FE-001 (package.json for npm scripts)
- DO-002 (CI pipeline)

**Technical Notes:**
- Use Testing Library for user-centric testing (avoid implementation details)
- Mock Alpine.js for component tests
- Test user interactions: click, type, submit
- Reference: PROPOSAL_PART_5.md Section 5.2 (Frontend Testing)

**Files to Create/Modify:**
- `jest.config.js` (new)
- `static/js/__tests__/auth.test.js` (new)
- `static/js/__tests__/setup.js` (new - test setup)
- `package.json` (add Jest scripts)
- `.github/workflows/ci.yml` (add frontend test job)

**jest.config.js Example:**
```javascript
module.exports = {
  testEnvironment: 'jsdom',
  roots: ['<rootDir>/static/js'],
  testMatch: ['**/__tests__/**/*.test.js'],
  collectCoverageFrom: [
    'static/js/**/*.js',
    '!static/js/__tests__/**',
    '!static/js/vendor/**',
  ],
  coverageThreshold: {
    global: {
      statements: 70,
      branches: 70,
      functions: 70,
      lines: 70,
    },
  },
  setupFilesAfterEnv: ['<rootDir>/static/js/__tests__/setup.js'],
};
```

**Testing:**
- Run `npm test` → all tests pass
- Run `npm run test:coverage` → coverage report >70%
- Create failing test → Jest exits with error code 1
- Verify CI runs tests on PR

---

### **QA-004: Component Tests**

**Type:** Story  
**Priority:** Medium (P2)  
**Story Points:** 3  
**Assignee:** QA Engineer  
**Sprint:** Sprint 2  
**Epic:** Epic 1 - Project Foundation

**Description:**
Write comprehensive tests for all frontend components created in Sprint 2: Button, Input, Card, Modal. Test rendering, interactions, accessibility.

**Acceptance Criteria:**
- [ ] **Button Component Tests:**
  - Renders with all variants (primary, secondary, ghost, danger)
  - Renders with all sizes (sm, md, lg)
  - Disabled state prevents click
  - Loading state shows spinner
  - Click event fires
  - Accessible (role, ARIA attributes)
- [ ] **Input Component Tests:**
  - Renders with label and placeholder
  - Error state shows error message
  - Required indicator shown
  - Password toggle works
  - Validation fires on blur
  - Accessible (labels, ARIA)
- [ ] **Card Component Tests:**
  - Renders header, body, footer
  - Interactive hover effect
  - Loading skeleton shown
- [ ] **Modal Component Tests:**
  - Opens/closes on trigger
  - Closes on backdrop click
  - Closes on Escape key
  - Focus trapped
  - Focus returns after close
- [ ] All tests use Testing Library queries (not implementation details)
- [ ] Coverage >80% for component files

**Dependencies:**
- QA-003 (Jest setup)
- FE-007, FE-008, FE-009, FE-010 (Components)

**Technical Notes:**
- Use `screen.getByRole()` over `querySelector()` (accessibility-first)
- Use `fireEvent` or `userEvent` for interactions
- Test keyboard navigation
- Reference: PROPOSAL_PART_5.md Section 5.2 (Frontend Testing)

**Files to Create/Modify:**
- `static/js/__tests__/button.test.js` (new)
- `static/js/__tests__/input.test.js` (new)
- `static/js/__tests__/card.test.js` (new)
- `static/js/__tests__/modal.test.js` (new)

**Button Test Example:**
```javascript
import { screen, fireEvent } from '@testing-library/dom';

describe('Button Component', () => {
  test('renders primary button', () => {
    document.body.innerHTML = `
      <button class="bg-primary-500 text-white">Click Me</button>
    `;
    
    const button = screen.getByRole('button', { name: /click me/i });
    expect(button).toBeInTheDocument();
    expect(button).toHaveClass('bg-primary-500');
  });
  
  test('disabled button does not fire click event', () => {
    document.body.innerHTML = `
      <button disabled onclick="handleClick()">Click Me</button>
    `;
    
    const button = screen.getByRole('button');
    fireEvent.click(button);
    // Verify handleClick not called
  });
  
  test('button is accessible', () => {
    document.body.innerHTML = `
      <button aria-label="Save changes">Save</button>
    `;
    
    const button = screen.getByLabelText(/save changes/i);
    expect(button).toBeInTheDocument();
  });
});
```

**Testing:**
- Run `npm test button.test.js` → all button tests pass
- Run `npm run test:coverage` → button.js coverage >80%
- Verify tests fail if component breaks (e.g., remove class)

---

## 📊 Sprint 2 Summary

**Total Story Points:** 45  
**Total Tasks:** 13  
**Completion Criteria:** All tasks pass QA, UI matches design specs, accessibility validated

**Team Allocation:**
- Frontend Dev 1: FE-001, FE-002, FE-007, FE-010 (15 points)
- Frontend Dev 2: FE-003, FE-004, FE-008 (15 points)
- Frontend Dev 3: FE-005, FE-006, FE-009 (12 points)
- QA Engineer: QA-003, QA-004 (5 points)

**Definition of Done:**
All committed stories are code-complete, reviewed, tested, and deployed on staging with no high-priority bugs.

**Integration Review:**
- **API Contract Alignment:** Wednesday 2 PM - Backend & Frontend leads align on auth endpoint responses
- **Frontend Demo:** Friday 3 PM - Demo login/registration flow to PM & QA

---

**Document Location:** `Documents/WorkList/Sprint_02_Week_02_Tasks.md`  
**Last Updated:** November 3, 2025  
**Version:** v1.0
