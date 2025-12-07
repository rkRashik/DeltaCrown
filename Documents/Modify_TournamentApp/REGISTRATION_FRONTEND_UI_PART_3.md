# Part 3/6: Frontend Registration UI & Stack Analysis

**Document Purpose**: Comprehensive audit of the frontend side of tournament registration, covering the templating system, styling approach, JavaScript interactions, form fields, auto-fill mechanisms, and submission workflows.

**Audit Date**: December 8, 2025  
**Scope**: Frontend templates, CSS/styling, JavaScript, form handling, auto-fill UX

---

## 1. Frontend Technology Stack

### 1.1 Template Engine
- **System**: Django Template Language (DTL)
- **Base Template**: `templates/base.html`
- **Template Inheritance**: Used extensively via `{% extends "..." %}`
- **Template Organization**: 
  - Registration wizard: `templates/tournaments/team_registration/`
  - Components: `templates/tournaments/components/`
  - Registration status: `templates/tournaments/registration/`

### 1.2 CSS Framework & Styling

**Primary Framework**: **Tailwind CSS (CDN)**
```html
<!-- From base.html line 32 -->
<script src="https://cdn.tailwindcss.com"></script>
<script src="{% static 'siteui/js/tailwind-config.js' %}"></script>
```

**Custom CSS Architecture**:
- **Token-based design system**: `static/siteui/css/tokens.css` (CSS variables)
- **Base styles**: `static/siteui/css/base.css` (custom utility classes)
- **Component styles**: `static/siteui/css/components.css`
- **Effects/animations**: `static/siteui/css/effects.css`
- **Tournament-specific**: `static/siteui/css/tournament-detail-*.css`

**Styling Approach**:
- **Hybrid model**: Tailwind utility classes + custom CSS
- **No @apply directives**: Pure utility-first approach
- **Inline styles in templates**: Extensive use of scoped `<style>` blocks in step templates
- **Theme system**: CSS custom properties for dark mode support

**Example from `solo_step1_enhanced.html`**:
```html
<input type="text" id="player_name" name="player_name" required
    value="{{ player_data.player_name|default:'' }}"
    placeholder="Amanul Hakim"
    class="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg text-white 
           placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent 
           transition-all">
```

### 1.3 JavaScript Stack

**No Frontend Framework**: Pure vanilla JavaScript (no React, Vue, Angular)

**JavaScript Files**:
- **Global site JS**: `static/siteui/js/` (loaded in base.html)
  - `theme.js` - Dark mode toggle
  - `components.js` - Reusable UI components
  - `notifications.js` - Toast messages
  - `reg_wizard.js` - **Registration wizard step navigation**
  - `tournaments.js` - Tournament list interactions
  - `auth.js` - Authentication flows
  - `follow.js` - Social features

- **Tournament-specific**: `static/tournaments/js/`
  - `tournament-detail.js` - Detail page interactions, countdowns, registration modals
  - `tournaments-hub-v2.js` - Hub page filtering

**Key Pattern**: Modular, file-scoped IIFEs (Immediately Invoked Function Expressions)

---

## 2. Registration Wizard Structure

### 2.1 Template Organization

**Location**: `templates/tournaments/team_registration/`

**Template Naming Pattern**:
```
solo_step1_enhanced.html  (current version)
solo_step1_new.html       (iteration)
solo_step1.html           (legacy)

team_step1_enhanced.html
team_step1_new.html
team_step1.html
```

**Template Variants**:
- **Enhanced**: Full auto-fill UI with progress indicators
- **New**: Simplified versions
- **Legacy**: Original implementations
- **Simple**: Minimal styling (e.g., `solo_step3_simple.html`)

**Total Templates**: 24 files in `team_registration/` folder
- 11 solo registration templates
- 11 team registration templates
- 2 error/status templates

### 2.2 Base Template Structure

**File**: `templates/tournaments/team_registration/base.html`

**Extends**: Main site base template
**Purpose**: Provides consistent wizard layout (header, step indicators, footer)

**Wizard Flow**:
```
Solo Registration:          Team Registration:
├── Step 1: Player Info     ├── Step 1: Team Info
├── Step 2: Review/Terms    ├── Step 2: Review/Terms  
└── Step 3: Payment         └── Step 3: Payment
```

---

## 3. Step-by-Step Template Analysis

### 3.1 Step 1: Information Collection

#### Solo Step 1 Template: `solo_step1_enhanced.html`

**Fields Rendered** (from template lines 1-229):
1. **Personal Details Section**:
   - `player_name` (Full Name) - Text input, required
   - `email` - Email input, required
   - `age` - Number input, required, min=13, max=100
   - `phone` - Tel input, required
   - `discord` - Text input (Discord ID)
   - `country` - Dropdown/select

2. **Game-Specific Section** (dynamic based on tournament.game):
   - `riot_id` / `pubg_mobile_id` / `mlbb_id` / etc.
   - `platform_server` - Server/region selection
   - `rank` - In-game rank

3. **Contact Preferences**:
   - `preferred_contact` - Radio buttons (email/phone/discord)

**Auto-Fill Integration**:
```django
<div class="flex items-center justify-between mb-2">
    <label for="player_name" class="block text-sm font-medium text-gray-300">
        Full Name <span class="text-red-500">*</span>
    </label>
    {% if autofill_data.player_name %}
        {% include 'tournaments/components/autofill_badge.html' with field=autofill_data.player_name %}
    {% endif %}
</div>
```

**Field Locking**: None - All auto-filled fields remain **editable**

#### Team Step 1 Template: `team_step1_enhanced.html`

**Fields Rendered**:
1. **Team Details Section**:
   - `team_name` - Text input, required
   - `team_logo` - Display only (from team profile, not editable)
   - `team_region` - Dropdown select

2. **Captain Information Section**:
   - `captain_name` - Text input
   - `captain_email` - Email input
   - `captain_phone` - Tel input
   - `captain_discord` - Text input
   - `captain_game_id` - Game-specific ID

3. **Hidden Fields**:
   - `team_id` - Hidden input (from URL parameter or session)

### 3.2 Step 2: Review & Terms

**Template**: `solo_step2_new.html` / `team_step2_new.html`

**Purpose**: Display review cards + terms acceptance

**Review Card Structure** (from template lines 1-363):
```html
<div class="review-card">
    <div class="review-section-title">
        Personal Information
        <a href="?type=solo&step=1" class="edit-btn">
            <i class="fas fa-edit"></i> Edit
        </a>
    </div>
    <div class="review-field">
        <span class="review-label">Full Name:</span>
        <span class="review-value">{{ step_data.full_name }}</span>
    </div>
    <!-- More fields... -->
</div>
```

**Terms Acceptance**:
```html
<div class="terms-section">
    <div class="checkbox-group">
        <label class="checkbox-label">
            <input type="checkbox" name="accept_terms" required>
            <span>I accept the tournament rules and code of conduct</span>
        </label>
    </div>
</div>
```

**Edit Functionality**: Query parameter navigation (`?type=solo&step=1`) reloads step with preserved data

### 3.3 Step 3: Payment

**Template**: `solo_step3_simple.html` / `team_step3_new.html`

**Payment Method Selection** (from template lines 1-568):

```html
<div class="payment-methods">
    <!-- Bkash -->
    <div class="method-option">
        <input type="radio" name="payment_method" value="bkash" id="bkash">
        <label for="bkash" class="method-label">
            <i class="fas fa-mobile-alt" style="color: #E2136E;"></i>
            <span class="method-name">Bkash</span>
        </label>
    </div>
    
    <!-- Nagad -->
    <div class="method-option">
        <input type="radio" name="payment_method" value="nagad" id="nagad">
        <label for="nagad" class="method-label">
            <i class="fas fa-mobile-alt" style="color: #F26522;"></i>
            <span class="method-name">Nagad</span>
        </label>
    </div>
    
    <!-- DeltaCoin (if sufficient balance) -->
    {% if deltacoin_can_afford %}
    <div class="method-option">
        <input type="radio" name="payment_method" value="deltacoin" id="deltacoin">
        <label for="deltacoin" class="deltacoin-label method-label">
            <i class="fas fa-coins" style="color: #EAB308;"></i>
            <span class="method-name">DeltaCoin</span>
            <span class="deltacoin-balance">Balance: {{ deltacoin_balance }}</span>
        </label>
    </div>
    {% endif %}
</div>
```

**Conditional Fields** (shown only for cash payment methods):
```html
<div class="cash-fields" id="cash-fields" style="display: none;">
    <div class="form-group">
        <label class="form-label">
            Transaction ID <span class="required">*</span>
        </label>
        <input type="text" name="transaction_id" class="form-input"
               placeholder="e.g., 8D4KL9X2P1">
    </div>
    
    <div class="form-group">
        <label class="form-label">
            Sender Number <span class="required">*</span>
        </label>
        <input type="tel" name="sender_number" class="form-input"
               placeholder="01XXXXXXXXX">
    </div>
    
    <div class="form-group">
        <label class="form-label">
            Payment Screenshot
        </label>
        <input type="file" name="payment_proof" accept="image/*" class="form-input">
    </div>
</div>
```

**DeltaCoin Logic**:
- If `deltacoin_can_afford == True`: Show DeltaCoin option
- If selected: No additional fields required (instant verification)
- If insufficient balance: Show shortfall warning, hide option

---

## 4. Auto-Fill System (Frontend Components)

### 4.1 Auto-Fill Progress Component

**File**: `templates/tournaments/components/autofill_progress.html`

**Purpose**: Visual progress indicator showing completion percentage

**UI Elements** (from template lines 1-131):
1. **Progress Bar**:
   - Dynamic width: `style="width: {{ percentage }}%"`
   - Color-coded:
     - Green (≥80%): "All fields auto-filled!"
     - Yellow (≥50%): "Almost there!"
     - Blue (<50%): "Complete your profile..."

2. **Percentage Badge**:
   - Large percentage display (e.g., "85%")
   - Checkmark icon if 100% complete

3. **Status Message**:
   - Shows missing field count: "{{ missing_count }} field{{ missing_count|pluralize }} remaining"

**Visual Design**:
```html
<div class="bg-gradient-to-r from-gray-800 to-gray-900 rounded-xl p-6 border border-gray-700 shadow-lg">
    <!-- Header with lightning bolt icon -->
    <div class="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
        <svg class="w-5 h-5 text-blue-400">...</svg>
    </div>
    
    <!-- Animated progress bar with shimmer effect -->
    <div class="relative h-3 bg-gray-700 rounded-full overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-r from-green-500 to-green-400 
                    transition-all duration-500 ease-out" style="width: {{ percentage }}%">
            <div class="animate-shimmer"></div>
        </div>
    </div>
</div>
```

**Placement**: Rendered at top of Step 1 templates (solo/team)

### 4.2 Auto-Fill Badge Component

**File**: `templates/tournaments/components/autofill_badge.html`

**Purpose**: Inline badge next to each auto-filled field

**Badge Types** (from template lines 1-84):

1. **Auto-Filled Badge** (field has value):
```html
<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs 
            bg-green-500/10 text-green-400 border border-green-500/30">
    <svg class="w-3.5 h-3.5"><!-- Profile/Team/Game icon --></svg>
    <span>From Profile</span>
</div>
```

2. **Missing Badge** (field empty):
```html
<div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs 
            bg-red-500/10 text-red-400 border border-red-500/30">
    <svg class="w-3.5 h-3.5"><!-- Warning icon --></svg>
    <span>Missing</span>
    <a href="/profile/edit" class="underline">Update Profile</a>
</div>
```

**Confidence Levels**:
- **High**: Green badge (data from verified profile)
- **Medium**: Yellow badge (inferred or partial data)
- **Low**: Blue badge (fallback values)

**Data Sources** (icon differentiation):
- `source='profile'`: User icon
- `source='team'`: Team icon
- `source='game_account'`: Game controller icon

### 4.3 Auto-Fill Data Flow

**Backend → Frontend Pipeline**:

1. **Backend Service** (`apps/tournaments/services/registration_autofill.py`):
```python
autofill_data = RegistrationAutoFillService.get_autofill_data(
    user=request.user,
    tournament=tournament,
    team=team
)
completion_percentage = RegistrationAutoFillService.get_completion_percentage(autofill_data)
missing_fields = RegistrationAutoFillService.get_missing_fields(autofill_data)
```

2. **View Context** (`apps/tournaments/views/registration_wizard.py` line 172):
```python
context = {
    'tournament': tournament,
    'autofill_data': autofill_data,  # Dict of AutoFillField objects
    'completion_percentage': completion_percentage,  # 0-100 integer
    'missing_count': len(missing_fields),
}
```

3. **Template Rendering**:
```django
{% if autofill_data %}
    {% include 'tournaments/components/autofill_progress.html' 
              with percentage=completion_percentage missing_count=missing_count %}
{% endif %}

<!-- Field-level badges -->
{% if autofill_data.player_name %}
    {% include 'tournaments/components/autofill_badge.html' 
              with field=autofill_data.player_name %}
{% endif %}
```

4. **Input Pre-Population**:
```django
<input type="text" name="player_name"
    value="{{ player_data.player_name|default:'' }}"
    ...>
```

**Key Insight**: Auto-fill is **advisory, not enforced**. Users can override any pre-filled value.

---

## 5. JavaScript Interactions

### 5.1 Wizard Step Navigation

**File**: `static/siteui/js/reg_wizard.js`

**Functionality**: Client-side step switching (progressive disclosure)

**Code** (full file, 34 lines):
```javascript
(function () {
  const form = document.getElementById('reg-form');
  if (!form) return;

  const steps = Array.from(document.querySelectorAll('[data-step]'));
  const sec1 = document.getElementById('step-1');
  const sec2 = document.getElementById('step-2');
  const sec3 = document.getElementById('step-3');

  function go(n) {
    [sec1, sec2, sec3].forEach((el, i) => {
      if (!el) return;
      el.classList.toggle('hidden', i !== (n - 1));
    });
    steps.forEach((s, i) => {
      s.classList.toggle('bg-blue-600', i === (n - 1));
      s.classList.toggle('text-white', i === (n - 1));
      s.classList.toggle('bg-slate-200', i !== (n - 1));
    });
    localStorage.setItem('reg_step', String(n));
  }

  form.addEventListener('click', (e) => {
    const next = e.target.closest('[data-next]');
    const prev = e.target.closest('[data-prev]');
    if (next) { e.preventDefault(); go(Math.min(3, (Number(localStorage.getItem('reg_step')||'1') + 1))); }
    if (prev) { e.preventDefault(); go(Math.max(1, (Number(localStorage.getItem('reg_step')||'1') - 1))); }
  });

  go(Number(localStorage.getItem('reg_step') || '1'));
})();
```

**Behavior**:
- **localStorage persistence**: Remembers current step across page reloads
- **Event delegation**: Single listener on form, checks for `[data-next]` and `[data-prev]` buttons
- **DOM manipulation**: Shows/hides step sections via `.hidden` class
- **Step indicators**: Highlights active step with `bg-blue-600`

**Usage in Templates**:
```html
<button type="button" data-next class="btn-primary">Next Step</button>
<button type="button" data-prev class="btn-secondary">Previous</button>
```

**Limitation**: This is **client-side only**. Actual wizard state managed server-side via session data.

### 5.2 Tournament Detail Page Interactions

**File**: `static/tournaments/js/tournament-detail.js` (550 lines)

**Key Functions** (from lines 1-100):

1. **Registration Modal Trigger**:
   - Opens registration wizard in modal/redirect
   - Checks user authentication status
   - Validates tournament status (registration open/closed)

2. **Countdown Timers**:
   - Registration closing countdown
   - Check-in countdown
   - Tournament start countdown
   - Updates every second via `setInterval`

3. **Cancel Registration**:
   - AJAX call to cancel endpoint
   - Confirmation modal
   - Updates UI state after cancellation

4. **Game Theme Application**:
```javascript
function applyGameTheme() {
    const gameSlug = state.tournamentData.gameSlug.toLowerCase();
    document.body.setAttribute('data-game', gameSlug);
}
```
Applies game-specific CSS via `[data-game="valorant"]` selectors

**Global Debug Logging**:
```javascript
window.dcLog = function(){};  // No-op for regular users
// Set to console.log for superusers via base.html:
window.DELTACROWN_DEBUG = {% if request.user.is_superuser %}true{% else %}false{% endif %};
```

### 5.3 Payment Method Conditional Display

**Inline JavaScript** (in `solo_step3_simple.html`):

```html
<script>
document.querySelectorAll('input[name="payment_method"]').forEach(radio => {
    radio.addEventListener('change', function() {
        const cashFields = document.getElementById('cash-fields');
        if (this.value === 'deltacoin') {
            cashFields.style.display = 'none';
        } else {
            cashFields.style.display = 'block';
        }
    });
});
</script>
```

**Behavior**:
- DeltaCoin selected → Hide transaction ID, sender number, screenshot fields
- Cash method selected → Show additional verification fields

---

## 6. Form Submission Workflow

### 6.1 Submission Method

**Standard HTTP POST**: No AJAX, traditional form submission

**Form Structure**:
```html
<form method="POST" class="space-y-8">
    {% csrf_token %}
    <input type="hidden" name="step" value="1">
    <!-- Fields... -->
    <button type="submit" class="btn-primary">Continue</button>
</form>
```

**CSRF Protection**: Django CSRF token required (`{% csrf_token %}`)

### 6.2 Step Progression

**Step 1 → Step 2** (from `registration_wizard.py` line 250):
```python
def _handle_solo_registration_post(self, request, tournament):
    step = request.POST.get('step', '1')
    
    if step == '1':
        # Extract all form fields
        player_data = {
            'full_name': request.POST.get('full_name', ''),
            'display_name': request.POST.get('display_name', ''),
            'age': request.POST.get('age', ''),
            # ... 10+ fields
        }
        # Save to session
        self.save_wizard_data(request, tournament.id, 'solo', player_data)
        # Redirect to step 2
        return redirect(f'{request.path}?type=solo&step=2')
```

**Step 2 → Step 3** (line 253):
```python
elif step == '2':
    terms_accepted = request.POST.get('accept_terms') == 'on'
    if not terms_accepted:
        messages.error(request, 'You must accept terms...')
        return redirect(f'{request.path}?type=solo&step=2')
    
    wizard_data['terms_accepted'] = True
    wizard_data['terms_accepted_at'] = timezone.now().isoformat()
    self.save_wizard_data(request, tournament.id, 'solo', wizard_data)
    return redirect(f'{request.path}?type=solo&step=3')
```

**Step 3 → Completion**:
```python
elif step == '3':
    try:
        return self._process_solo_registration(request, tournament)
    except ValidationError as e:
        messages.error(request, str(e))
        return redirect(f'{request.path}?type=solo&step=3')
```

### 6.3 Session-Based Wizard Data

**Storage**: Django session (server-side)

**Key Pattern**:
```python
SESSION_KEY_PREFIX = 'tournament_registration_wizard_'

def get_wizard_data(self, request, tournament_id, reg_type):
    key = f'{self.SESSION_KEY_PREFIX}{tournament_id}_{reg_type}'
    return request.session.get(key, {})

def save_wizard_data(self, request, tournament_id, reg_type, data):
    key = f'{self.SESSION_KEY_PREFIX}{tournament_id}_{reg_type}'
    request.session[key] = data
```

**Lifecycle**:
1. Step 1 GET: Auto-fill data → session
2. Step 1 POST: User input → session
3. Step 2 GET: Load from session for review
4. Step 2 POST: Add terms acceptance → session
5. Step 3 GET: Load from session for payment
6. Step 3 POST: Create Registration record → clear session

---

## 7. Hardcoded Game Logic in Templates

### 7.1 Game-Specific Field Rendering

**Problem**: Templates don't dynamically adapt to tournament.game configuration

**Evidence** (inferred from backend view logic):

From `registration_wizard.py` lines 479-491:
```python
# Map game-specific ID based on tournament game
game_slug = tournament.game.slug if tournament.game else ''

# Legacy hardcoded mapping
if game_slug == 'valorant':
    auto_filled['game_id'] = profile.riot_id or ''
elif game_slug == 'pubg-mobile':
    auto_filled['game_id'] = profile.pubg_mobile_id or ''
elif game_slug == 'mobile-legends':
    auto_filled['game_id'] = profile.mlbb_id or ''
elif game_slug == 'free-fire':
    auto_filled['game_id'] = profile.free_fire_id or ''
# ... 7 total games
```

**Template Impact**:
- Field labels are generic: "Game ID", "In-Game Name"
- No game-specific validation hints (e.g., "Riot ID format: Name#TAG")
- No dynamic field addition (e.g., "Steam Friend Code" for CS2)

**Current Workaround**: Backend auto-fill maps correct field, but templates don't show game branding

### 7.2 Missing Dynamic Configuration

**Desired Behavior** (from TOURNAMENT_OPS_DESIGN.md):
```python
# GamePlayerIdentityConfig should drive frontend
identity_configs = game_service.get_identity_validation_rules(tournament.game)
for config in identity_configs:
    # Render field with:
    # - config.display_label: "Riot ID"
    # - config.validation_pattern: r'^[\w]+#[\w]+$'
    # - config.help_text: "Format: Username#TAG"
```

**Current State**: Templates use static field names, rely on backend to map correctly

---

## 8. UI/UX Patterns

### 8.1 Design Language

**Visual Style**:
- **Dark theme**: Gray-800/900 backgrounds, white/gray text
- **Gradient accents**: Blue-to-purple gradients for CTAs
- **Glass morphism**: Subtle borders, backdrop blur effects
- **Neumorphism**: Soft shadows on cards

**Color Palette** (from `tokens.css` variables):
- `--bg`: Dark background (#0b1220)
- `--text`: Light text (#e2e8f0)
- `--brand-delta`: Blue (#3b82f6)
- `--brand-crown`: Purple (#8b5cf6)
- `--border`: Gray-700 (#374151)

**Typography**:
- **Font stack**: System fonts (no custom web fonts loaded for registration)
- **Heading sizes**: `text-3xl` (Step titles), `text-xl` (Section headers)
- **Body text**: `text-sm` to `text-base`

### 8.2 Responsive Design

**Tailwind Breakpoints**:
```html
<!-- Example from solo_step1_enhanced.html -->
<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
    <!-- Age field -->
    <!-- Phone field -->
</div>
```

**Mobile Adaptations**:
- Single-column layouts on mobile (`grid-cols-1`)
- Two-column on medium+ screens (`md:grid-cols-2`)
- Full-width buttons on mobile
- Responsive font sizes via `clamp()` in base.css

**CSS Files for Mobile**:
- `static/siteui/css/mobile-enhancements.css`
- `static/siteui/css/responsive.css`
- `static/siteui/css/mobile-bottom-nav.css`

### 8.3 Accessibility Considerations

**Positive**:
- Semantic HTML: `<label for="...">`, `<input id="...">`
- Required field indicators: `<span class="text-red-500">*</span>`
- Focus states: `focus:ring-2 focus:ring-blue-500`
- Skip link in base.html: `<a href="#main" class="skip-link">Skip to main content</a>`

**Gaps**:
- No ARIA labels on auto-fill badges
- No `aria-describedby` linking help text to inputs
- Payment method radio labels could use `aria-checked`
- No keyboard navigation hints for step wizard

### 8.4 Error Handling & Validation

**Client-Side Validation**:
- HTML5 attributes: `required`, `type="email"`, `min="13"`, `pattern="..."`
- Browser-native validation bubbles

**Server-Side Validation**:
- Django form validation (not shown in templates)
- Error messages via Django messages framework:

```python
if not terms_accepted:
    messages.error(request, 'You must accept the terms and conditions to proceed.')
    return redirect(f'{request.path}?type=solo&step=2')
```

**Error Display** (from `base.html` messages block):
```html
{% if messages %}
<script id="dj-messages" type="application/json">[
  {% for message in messages %}
    {"level":"{{ message.tags|default:'info' }}","text":"{{ message|escapejs }}"}
  {% endfor %}
]</script>
{% endif %}
```

Rendered as toast notifications via `static/siteui/js/notifications.js`

---

## 9. Frontend-Backend Integration Points

### 9.1 URL Routing

**Registration Entry Point**: `/tournaments/{slug}/register/`

**View**: `apps.tournaments.views.registration_wizard.TournamentRegistrationWizardView`

**URL Parameters**:
- `?type=solo` or `?type=team` - Registration mode
- `?step=1|2|3` - Current wizard step
- `?team_id=123` - Team selection (for team registrations)

**Example URL**: `/tournaments/valorant-championship-2025/register/?type=solo&step=2`

### 9.2 Template Context Variables

**Common Variables** (passed from view to template):

```python
context = {
    'tournament': tournament,              # Tournament model instance
    'current_step': int(step),             # 1, 2, or 3
    'total_steps': 3,
    'registration_type': 'solo',           # 'solo' or 'team'
    'autofill_data': autofill_data,        # Dict of AutoFillField objects
    'completion_percentage': 85,           # 0-100 integer
    'missing_count': 2,                    # Number of empty fields
    'player_data': wizard_data,            # Session data for current registration
    'entry_fee': Decimal('100.00'),
    'deltacoin_balance': 250,
    'deltacoin_can_afford': True,
}
```

### 9.3 Static Asset Loading

**Base Template** (`base.html` lines 91-100):
```django
<script src="{% static 'siteui/js/theme.js' %}"></script>
<script src="{% static 'siteui/js/components.js' %}"></script>
<script src="{% static 'siteui/js/reg_wizard.js' %}"></script>
<!-- ... 10+ global JS files -->
```

**Page-Specific Assets** (via template blocks):
```django
{% block extra_css %}
<link rel="stylesheet" href="{% static 'tournaments/css/registration-wizard.css' %}">
{% endblock %}

{% block extra_js %}
<script src="{% static 'tournaments/js/payment-validation.js' %}"></script>
{% endblock %}
```

**CDN Dependencies**:
- Tailwind CSS: `https://cdn.tailwindcss.com`
- Font Awesome: `https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css`
- AOS (Animate On Scroll): `https://unpkg.com/aos@2.3.1/dist/aos.css`

---

## 10. Performance Considerations

### 10.1 Asset Optimization

**Current State**:
- ❌ **Tailwind CDN**: 3MB+ full framework loaded (not production-ready)
- ❌ **No minification**: CSS/JS served uncompressed
- ✅ **Preload critical CSS**: `<link rel="preload" href="{% static 'siteui/css/tokens.css' %}" as="style">`
- ✅ **Font preconnect**: `<link rel="preconnect" href="https://fonts.gstatic.com">`

**Recommendations**:
- Build Tailwind with PurgeCSS for production (~10KB instead of 3MB)
- Bundle and minify JS files
- Lazy-load non-critical assets

### 10.2 Template Rendering

**Efficiency**:
- ✅ **Template inheritance**: Minimizes duplication
- ✅ **Component includes**: Reusable auto-fill components
- ❌ **Inline styles**: Repeated `<style>` blocks in step templates (50-150 lines each)

**Suggestion**: Extract inline styles to dedicated CSS files

### 10.3 JavaScript Execution

**Loading Strategy**:
- Scripts loaded at **end of `<body>`** (non-blocking)
- No `async` or `defer` attributes
- All scripts execute sequentially

**Optimization Opportunity**:
```html
<script src="{% static 'siteui/js/reg_wizard.js' %}" defer></script>
```

---

## 11. Key Frontend Findings Summary

### 11.1 Strengths

1. ✅ **Auto-Fill UX**: Excellent visual feedback (progress bars, badges, color coding)
2. ✅ **Step Wizard**: Clear 3-step progression with localStorage persistence
3. ✅ **Responsive Design**: Mobile-first Tailwind approach
4. ✅ **Component Reusability**: `autofill_progress.html`, `autofill_badge.html`
5. ✅ **Payment Flexibility**: DeltaCoin + manual payment options with conditional fields
6. ✅ **Session Persistence**: Wizard data survives page reloads
7. ✅ **Error Handling**: Toast notifications for user feedback

### 11.2 Weaknesses

1. ❌ **Hardcoded Game Logic**: No dynamic field rendering based on Game configuration
2. ❌ **Template Proliferation**: 24 templates with overlapping functionality (enhanced/new/legacy versions)
3. ❌ **Tailwind CDN**: Unoptimized 3MB payload in production
4. ❌ **Inline Styles**: 100+ lines of CSS duplicated across step templates
5. ❌ **No Real-Time Validation**: Only browser-native HTML5 validation
6. ❌ **Accessibility Gaps**: Missing ARIA labels, keyboard navigation hints
7. ❌ **No Progressive Enhancement**: JavaScript required for step navigation

### 11.3 Technical Debt

1. **Template Variants**: Need consolidation strategy (keep enhanced, archive legacy)
2. **CSS Architecture**: Extract inline styles to dedicated files
3. **JavaScript Modularity**: Bundle wizard logic into single module
4. **Asset Optimization**: Build process for Tailwind, minification
5. **Game Abstraction**: Replace hardcoded game checks with dynamic config rendering

---

## 12. Modernization Recommendations

### 12.1 Immediate Improvements (Low Effort)

1. **Consolidate Templates**: Remove `_legacy.html` and `_old.html` variants
2. **Extract Inline CSS**: Move step template `<style>` blocks to `registration-wizard.css`
3. **Add ARIA Labels**: Enhance accessibility for screen readers
4. **Defer Scripts**: Add `defer` attribute to non-critical JavaScript

### 12.2 Medium-Term Enhancements

1. **Dynamic Field Rendering**: Template tag to iterate over `identity_configs`:
```django
{% for config in game_identity_configs %}
    <div class="form-group">
        <label>{{ config.display_label }}</label>
        <input name="{{ config.field_name }}" 
               pattern="{{ config.validation_pattern }}"
               placeholder="{{ config.help_text }}">
    </div>
{% endfor %}
```

2. **Client-Side Validation**: Add `Parsley.js` or native Constraint Validation API with custom messages

3. **Build Process**: Replace Tailwind CDN with PostCSS build:
```bash
npx tailwindcss -i ./src/input.css -o ./static/css/output.css --minify
```

### 12.3 Long-Term Vision (Align with TournamentOps)

1. **API-Driven Registration**: Decouple frontend from Django templates
```javascript
// Step 1 submission becomes:
fetch('/api/tournaments/123/registration/', {
    method: 'POST',
    body: JSON.stringify(playerData),
    headers: {'Content-Type': 'application/json'}
})
```

2. **Component Library**: Standardize UI components (buttons, inputs, cards) across all tournament flows

3. **Progressive Web App**: Add service worker for offline form drafting

---

## 13. Related Files Reference

**Templates**:
- `templates/base.html` - Site base template
- `templates/tournaments/team_registration/*.html` - 24 registration templates
- `templates/tournaments/components/*.html` - Reusable components

**CSS**:
- `static/siteui/css/base.css` - Custom utility classes
- `static/siteui/css/tokens.css` - Design system variables
- `static/siteui/css/components.css` - Component styles

**JavaScript**:
- `static/siteui/js/reg_wizard.js` - Step navigation (34 lines)
- `static/tournaments/js/tournament-detail.js` - Detail page interactions (550 lines)
- `static/siteui/js/notifications.js` - Toast messages

**Backend Views**:
- `apps/tournaments/views/registration_wizard.py` - Wizard controller (817 lines)
- `apps/tournaments/services/registration_autofill.py` - Auto-fill service

---

**End of Part 3: Frontend Registration UI & Stack Analysis**

**Next**: Part 4 - Payment Verification Workflow
