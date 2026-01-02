# Platform Wiring & Production-Grade Settings Sprint
## Implementation Plan & Progress Tracker

**Date Started:** January 2, 2026  
**Lead Engineer:** GitHub Copilot  
**Estimated Total Effort:** 13-20 hours

---

## Phase 0: Truth Reconciliation ✅ COMPLETE

**Deliverable:** [REALITY_MATRIX_SETTINGS_AUDIT.md](REALITY_MATRIX_SETTINGS_AUDIT.md)

**Key Findings:**
- Backend is 80% complete (Phase 5A platform prefs, Phase 6A/6B private accounts, Phase 2A/2B settings APIs all exist)
- Frontend shows placeholders for features that actually work
- 4 missing templates (wallet pages)
- Platform Preferences tab missing from UI despite complete backend

**Action Items Generated:** 14 prioritized tasks (P0-P3)

---

## Phase 1: Global Wiring (Platform Preferences) 🚧 IN PROGRESS

### 1.1 Add Platform Tab to Settings UI ✅ PARTIAL COMPLETE

**Files Modified:**
- `templates/user_profile/profile/settings_control_deck.html` - Added Platform nav button

**Still TODO:**
- [ ] Add Platform tab content section (after line 850, before Security tab)
- [ ] Wire to existing GET `/me/settings/platform-global/` API
- [ ] Wire to existing POST `/me/settings/platform-global/save/` API
- [ ] Add to mobile nav
- [ ] Add to tab-form mapping for auto-save

**Backend Already Exists:**
```python
# apps/user_profile/api/platform_prefs_api.py
GET  /me/settings/platform-global/  # Returns prefs + options
POST /me/settings/platform-global/save/  # Validates + saves
```

### 1.2 Platform Tab Content (TODO)

**UI Design:**
```django-html
<div id="tab-platform" class="tab-section space-y-6">
    <h2 class="text-3xl font-display font-bold text-white mb-2">Platform Preferences</h2>
    <p class="text-gray-400 mb-6">Global settings for timezone, language, time format, and currency display.</p>
    
    <form id="platform-form" onsubmit="savePlatformSettings(event)">
        {% csrf_token %}
        
        <!-- Language Selection -->
        <div class="glass-panel p-6 space-y-4">
            <label class="z-label">
                <i class="fa-solid fa-language"></i> Preferred Language
            </label>
            <select id="preferred_language" name="preferred_language" class="z-input">
                <!-- Loaded from backend: /me/settings/platform-global/ -->
            </select>
            <p class="text-xs text-gray-500">Bengali translation coming soon</p>
        </div>
        
        <!-- Timezone Selection -->
        <div class="glass-panel p-6 space-y-4">
            <label class="z-label">
                <i class="fa-solid fa-clock"></i> Timezone
            </label>
            <select id="timezone_pref" name="timezone_pref" class="z-input">
                <!-- Loaded from backend -->
            </select>
            <p class="text-xs text-gray-500">All timestamps will display in your selected timezone</p>
        </div>
        
        <!-- Time Format -->
        <div class="glass-panel p-6 space-y-4">
            <label class="z-label">
                <i class="fa-solid fa-clock"></i> Time Format
            </label>
            <select id="time_format" name="time_format" class="z-input">
                <option value="12h">12-hour (3:00 PM)</option>
                <option value="24h">24-hour (15:00)</option>
            </select>
        </div>
        
        <!-- Currency Display (Read-Only for now) -->
        <div class="glass-panel p-6 space-y-4">
            <label class="z-label">
                <i class="fa-solid fa-bangladeshi-taka-sign"></i> Currency
            </label>
            <select id="currency" name="currency" class="z-input" disabled>
                <option value="BDT" selected>BDT (৳)</option>
                <option value="USD">USD ($) - Coming Soon</option>
            </select>
            <p class="text-xs text-gray-500">Multi-currency support coming soon</p>
        </div>
        
        <!-- Theme Preference -->
        <div class="glass-panel p-6 space-y-4">
            <label class="z-label">
                <i class="fa-solid fa-palette"></i> Theme
            </label>
            <select id="theme_preference" name="theme_preference" class="z-input">
                <option value="dark" selected>Dark Mode</option>
                <option value="light">Light Mode (Coming Soon)</option>
                <option value="system">System Default</option>
            </select>
        </div>
        
        <div class="mt-6">
            <button type="submit" class="bg-z-cyan text-black px-6 py-2.5 rounded-xl text-xs font-black uppercase tracking-wider hover:bg-white transition flex items-center gap-2">
                <i class="fa-solid fa-floppy-disk"></i> Save Platform Settings
            </button>
        </div>
    </form>
</div>
```

### 1.3 JavaScript Functions (TODO)

**Add to settings_control_deck.html `<script>` section:**

```javascript
// Load platform settings on page load
async function loadPlatformSettings() {
    try {
        const response = await fetch('/me/settings/platform-global/', {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            }
        });
        
        if (!response.ok) throw new Error('Failed to load platform settings');
        
        const data = await response.json();
        
        if (data.success) {
            // Populate form fields
            const prefs = data.preferences;
            document.getElementById('preferred_language').value = prefs.preferred_language || 'en';
            document.getElementById('timezone_pref').value = prefs.timezone || 'Asia/Dhaka';
            document.getElementById('time_format').value = prefs.time_format || '12h';
            document.getElementById('theme_preference').value = prefs.theme_preference || 'dark';
            
            // Populate dropdowns from available options
            const options = data.available_options;
            populateSelect('preferred_language', options.languages);
            populateSelect('timezone_pref', options.timezones);
        }
    } catch (error) {
        console.error('Error loading platform settings:', error);
        showToast('Failed to load platform settings', 'error');
    }
}

function populateSelect(selectId, optionsArray) {
    const select = document.getElementById(selectId);
    const currentValue = select.value;
    
    // Clear existing options
    select.innerHTML = '';
    
    // Add new options
    optionsArray.forEach(option => {
        const optionElement = document.createElement('option');
        if (Array.isArray(option)) {
            // [value, label] format
            optionElement.value = option[0];
            optionElement.textContent = option[1];
        } else {
            // String format
            optionElement.value = option;
            optionElement.textContent = option;
        }
        select.appendChild(optionElement);
    });
    
    // Restore selected value
    select.value = currentValue;
}

async function savePlatformSettings(event) {
    event.preventDefault();
    
    const formData = {
        preferred_language: document.getElementById('preferred_language').value,
        timezone: document.getElementById('timezone_pref').value,
        time_format: document.getElementById('time_format').value,
        currency: 'BDT',  // Fixed for now
    };
    
    try {
        const response = await fetch('/me/settings/platform-global/save/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: JSON.stringify(formData),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showToast('✅ Platform preferences saved successfully!', 'success');
            // Reload page to apply timezone/language changes
            setTimeout(() => window.location.reload(), 1500);
        } else {
            showToast(`❌ ${data.error || 'Failed to save platform preferences'}`, 'error');
        }
    } catch (error) {
        console.error('Error saving platform settings:', error);
        showToast('❌ Network error. Please try again.', 'error');
    }
}

// Call on page load
document.addEventListener('DOMContentLoaded', function() {
    // ... existing DOMContentLoaded code ...
    
    // Load platform settings if platform tab exists
    if (document.getElementById('tab-platform')) {
        loadPlatformSettings();
    }
});
```

### 1.4 Mobile Nav Update (TODO)

**Add after line ~280:**
```django-html
<button onclick="switchTab('platform')" class="mobile-nav-btn" data-target="platform">Platform</button>
```

### 1.5 Tab-Form Mapping Update (TODO)

**Update around line 1210:**
```javascript
const tabFormMap = {
    'tab-identity': 'identity-form',
    'tab-recruitment': 'career-form',
    'tab-matchmaking': 'matchmaking-form',
    'tab-notifications': 'notifications-form',
    'tab-platform': 'platform-form',  // ADD THIS
    'tab-loadout': 'loadout-form',
    'tab-stream': 'stream-form'
};
```

### 1.6 Verification Steps

After implementing:
1. Navigate to Settings → Platform tab
2. Verify dropdowns populate from backend API
3. Change timezone to UTC → Save → Reload page
4. Check that all timestamps now show in UTC
5. Change time format to 24h → Verify wallet/tournaments show 24h format
6. Check browser console for no errors

---

## Phase 2: Settings → Profile Synchronization ⏳ NOT STARTED

**Goal:** Every setting change reflects immediately on profile page

### 2.1 Display Name Sync Test

**Test:** Change display_name in Identity tab → Save → Visit public profile → Verify name updated

**Backend:** Already wired (uses POST `/me/settings/basic/`)

**Status:** ✅ Should work already, needs verification

### 2.2 Privacy Settings Sync Test

**Test:** Toggle "Show Game Passports" → Save → Visit profile → Verify passports hidden

**Backend:** Uses ProfilePermissionChecker which reads PrivacySettings model

**Status:** ✅ Should work already, needs verification

### 2.3 Private Account Sync Test

**Test:** Enable private account → Save → Log out → View profile → See private wall

**Backend:** Phase 6B complete

**Status:** ✅ Already working (Phase 6B tests passed)

### 2.4 Inventory Visibility Sync Test

**Test:** Set inventory to PRIVATE → Save → Visit inventory page → Verify blocked

**Backend:** Needs verification of enforcement

**Status:** ⚠️ Needs verification

---

## Phase 3: Admin Parity Audit ⏳ NOT STARTED

### 3.1 GameProfile Fields

**Admin Fields:**
- in_game_name ✅
- game_id ✅
- rank ✅
- rank_tier ✅
- region ✅
- lft_status ✅
- is_pinned ✅
- is_public ✅
- sort_order ✅

**Website UI:**
- in_game_name ⚠️ (shows display text, not editable)
- game_id ❌ (not shown)
- rank ❌ (not editable)
- region ❌ (not editable)
- lft_status ⚠️ (toggle exists but not per-game)
- is_pinned ❌ (placeholder)
- sort_order ❌ (no drag-drop reorder)

**Action:** Wire full CRUD for game passports

### 3.2 PrivacySettings Fields

**Admin Fields (14 toggles):**
- show_following_list ✅ (in UI)
- show_achievements ❌ (not in UI)
- show_game_passports ❌ (not in UI)
- show_social_links ❌ (not in UI)
- show_wallet ❌ (not in UI)
- show_match_history ❌ (not in UI)
- show_teams ❌ (not in UI)
- show_certificates ❌ (not in UI)
- show_badges ❌ (not in UI)
- show_tournaments ❌ (not in UI)
- show_endorsements ❌ (not in UI)
- show_real_name ❌ (not in UI)
- show_email ❌ (not in UI)
- inventory_visibility ✅ (in UI)
- is_private_account ✅ (Phase 6B)

**Action:** Expand Privacy tab to show all 14 toggles

---

## Phase 4: Feature-Specific Rebuilds ⏳ NOT STARTED

### 4A: Identity - Gender Field (P3)

**Check backend:** Does UserProfile have gender field?

```bash
grep -n "gender" apps/user_profile/models_main.py
```

**If YES:** Add gender dropdown (Male/Female/Non-binary/Prefer not to say)

**If NO:** Skip (don't invent migrations)

### 4B: Security & KYC (P1)

**Subtasks:**
1. Replace password change placeholder with link to `/accounts/password/change/`
2. Wire KYC upload flow (backend exists: POST `/me/kyc/upload/`)
3. Wire KYC status check (GET `/me/kyc/status/`)
4. Show verification status badge (Unverified/Pending/Verified)
5. Gate withdrawals + tournaments by KYC status

**Estimated:** 2-3 hours

### 4C: Privacy & Visibility Expansion (P0)

**Subtask:** Expand Privacy tab to show all 14 privacy toggles

**Current UI Shows:**
- show_following_list
- inventory_visibility
- is_private_account

**Missing (Add to UI):**
- show_achievements
- show_game_passports
- show_social_links
- show_wallet
- show_match_history
- show_teams
- show_certificates
- show_badges
- show_tournaments
- show_endorsements
- show_real_name
- show_email

**Backend:** Already exists in PrivacySettings model

**Estimated:** 1 hour

### 4D: Notifications Cleanup (P2)

**Subtasks:**
1. Remove "Quiet Hours" section (not desired)
2. Wire category toggles:
   - Tournament updates
   - Team invites
   - Bounties/Economy
   - Messages
   - System announcements
3. Wire channel toggles (Email/Push) if backend supports

**Backend:** Uses system_settings JSON

**Estimated:** 1-2 hours

### 4E: Career & LFT Redesign (P1)

**Current:** Single LFT toggle (not game-aware)

**New Design:** Per-game status display

```django-html
<div class="glass-panel p-6">
    <h3 class="font-bold text-white mb-4">Career Status by Game</h3>
    
    <!-- Load games from /api/games/ -->
    <div id="game-career-list" class="space-y-4">
        <!-- For each game: -->
        <div class="flex items-center justify-between p-4 rounded-lg border border-white/10">
            <div class="flex items-center gap-4">
                <img src="{{ game.icon_url }}" class="w-10 h-10 rounded" alt="{{ game.name }}">
                <div>
                    <h4 class="font-bold text-white">{{ game.name }}</h4>
                    <p class="text-xs text-gray-400">
                        {% if user_has_team_for_game %}
                            Team: {{ team_name }}
                        {% else %}
                            No team
                        {% endif %}
                    </p>
                </div>
            </div>
            <div class="flex items-center gap-4">
                <label class="z-toggle-wrapper">
                    <input type="checkbox" class="z-toggle-input" data-game-id="{{ game.id }}" onchange="toggleLFTForGame({{ game.id }}, this.checked)">
                    <span class="z-toggle-slider"></span>
                </label>
                <span class="text-xs font-bold text-gray-400">LFT</span>
            </div>
        </div>
    </div>
</div>
```

**Backend:**
- Load games from GET `/api/games/`
- Get user's teams via `Team.objects.filter(members=user)`
- Toggle LFT via POST `/api/passports/toggle-lft/` (already exists)

**Estimated:** 2-3 hours

### 4F: Game Passports CRUD (P0) 🔥 CRITICAL

**Current:** Placeholder "coming soon" toasts

**Wire to existing APIs:**
```javascript
// DELETE passport
async function deleteGamePassport(passportId) {
    if (!confirm('Delete this game passport? This cannot be undone.')) return;
    
    try {
        const response = await fetch(`/api/game-passports/delete/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken'),
            },
            body: JSON.stringify({ passport_id: passportId }),
        });
        
        const data = await response.json();
        if (data.success) {
            showToast('✅ Game passport deleted', 'success');
            reloadPassportsList();
        } else {
            showToast(`❌ ${data.error}`, 'error');
        }
    } catch (error) {
        showToast('❌ Network error', 'error');
    }
}

// CREATE passport modal
function showAddPassportModal() {
    // Load games from /api/games/
    // Show modal with game selector + fields
    // POST to /api/game-passports/create/
}

// UPDATE passport
function showEditPassportModal(passportId) {
    // Load current passport data
    // Show modal with prefilled fields
    // POST to /api/game-passports/update/
}
```

**Backend APIs (Already Exist):**
- GET `/api/game-passports/` - List all passports
- POST `/api/game-passports/create/` - Create new
- POST `/api/game-passports/update/` - Update existing
- POST `/api/game-passports/delete/` - Delete by ID

**Estimated:** 3-4 hours

### 4G: Pro Loadout Redesign (P1)

**Current:** Simple form

**New:** Category-based hardware editor

```django-html
<div class="glass-panel p-6">
    <h3 class="font-bold text-white mb-4">Hardware Setup</h3>
    
    <div class="space-y-6">
        <!-- Mouse -->
        <div class="p-4 rounded-lg border border-white/10">
            <h4 class="font-bold text-white mb-2">
                <i class="fa-solid fa-computer-mouse"></i> Mouse
            </h4>
            <div class="grid grid-cols-2 gap-4">
                <input type="text" class="z-input" placeholder="Brand" id="mouse_brand">
                <input type="text" class="z-input" placeholder="Model" id="mouse_model">
            </div>
            <textarea class="z-input mt-2" placeholder="Specs (DPI, polling rate, etc)" id="mouse_specs"></textarea>
        </div>
        
        <!-- Keyboard -->
        <div class="p-4 rounded-lg border border-white/10">
            <h4 class="font-bold text-white mb-2">
                <i class="fa-solid fa-keyboard"></i> Keyboard
            </h4>
            <!-- Similar structure -->
        </div>
        
        <!-- Monitor -->
        <!-- Headset -->
        <!-- Mousepad -->
        <!-- Chair -->
    </div>
</div>
```

**Backend:** HardwareGear model with category field

**Estimated:** 2-3 hours

### 4H: Live Feed/Stream URL Validation (P2)

**Add client-side validation:**
```javascript
function validateStreamURL(url) {
    const validPlatforms = [
        /^https:\/\/(www\.)?twitch\.tv\/.+/,
        /^https:\/\/(www\.)?youtube\.com\/.+/,
        /^https:\/\/(www\.)?facebook\.com\/gaming\/.+/,
    ];
    
    return validPlatforms.some(regex => regex.test(url));
}
```

**Add backend validation in view:**
```python
# apps/user_profile/views/...
from urllib.parse import urlparse

def validate_stream_url(url):
    allowed_domains = ['twitch.tv', 'youtube.com', 'facebook.com']
    parsed = urlparse(url)
    return any(domain in parsed.netloc for domain in allowed_domains)
```

**Estimated:** 1 hour

### 4I: Wallet Templates (P0) 🔥 CRITICAL

**Missing Templates:**
1. `templates/economy/wallet_dashboard.html`
2. `templates/economy/withdrawal_request.html`
3. `templates/economy/transaction_history.html`

**Create Wallet Dashboard:**
```django-html
{% extends "base.html" %}
{% load platform_filters %}

{% block content %}
<div class="container mx-auto p-8">
    <h1 class="text-3xl font-bold text-white mb-8">Wallet Dashboard</h1>
    
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <!-- Balance Card -->
        <div class="glass-panel p-6">
            <h3 class="text-gray-400 text-sm mb-2">Available Balance</h3>
            <p class="text-4xl font-bold text-z-cyan">
                {% format_money_context wallet.balance %}
            </p>
        </div>
        
        <!-- Pending Card -->
        <div class="glass-panel p-6">
            <h3 class="text-gray-400 text-sm mb-2">Pending</h3>
            <p class="text-4xl font-bold text-yellow-400">
                {% format_money_context wallet.pending_balance %}
            </p>
        </div>
        
        <!-- Lifetime Earnings Card -->
        <div class="glass-panel p-6">
            <h3 class="text-gray-400 text-sm mb-2">Lifetime Earnings</h3>
            <p class="text-4xl font-bold text-green-400">
                {% format_money_context wallet.lifetime_earnings %}
            </p>
        </div>
    </div>
    
    <!-- Actions -->
    <div class="flex gap-4 mb-8">
        <a href="{% url 'withdrawal_request' %}" class="bg-z-cyan text-black px-6 py-3 rounded-xl font-bold">
            <i class="fa-solid fa-money-bill-transfer"></i> Withdraw
        </a>
        <a href="{% url 'transaction_history' %}" class="bg-white/10 text-white px-6 py-3 rounded-xl font-bold">
            <i class="fa-solid fa-clock-rotate-left"></i> History
        </a>
    </div>
    
    <!-- Recent Transactions -->
    <div class="glass-panel p-6">
        <h3 class="font-bold text-white mb-4">Recent Transactions</h3>
        <div class="space-y-4">
            {% for transaction in recent_transactions %}
            <div class="flex justify-between items-center p-4 rounded-lg bg-white/5">
                <div>
                    <p class="font-bold text-white">{{ transaction.description }}</p>
                    <p class="text-xs text-gray-400">{% format_dt_context transaction.created_at %}</p>
                </div>
                <p class="font-bold {% if transaction.amount >= 0 %}text-green-400{% else %}text-red-400{% endif %}">
                    {% if transaction.amount >= 0 %}+{% endif %}{% format_money_context transaction.amount %}
                </p>
            </div>
            {% endfor %}
        </div>
    </div>
</div>
{% endblock %}
```

**Estimated:** 2-3 hours

### 4J: Danger Zone Production-Grade (P2)

**Requirements:**
1. Password confirmation required
2. Confirmation phrase: "DELETE MY ACCOUNT"
3. 7-day cooling-off period
4. Schedule deletion (don't delete immediately)
5. Allow cancellation during cooling-off
6. Show countdown timer
7. Clear all sessions on deletion request

**Estimated:** 2-3 hours

---

## Phase 5: Testing & QA ⏳ NOT STARTED

### 5.1 Endpoint Tests

**Create:** `tests/test_settings_integration.py`

```python
@pytest.mark.django_db
class TestPlatformPrefsIntegration:
    def test_change_timezone_reflects_everywhere(self, client, profile):
        """Change timezone in settings → verify all timestamps show in new timezone"""
        # Test implementation
        pass
    
    def test_change_time_format_reflects_everywhere(self, client, profile):
        """Change to 24h → verify wallet/tournaments show 24h format"""
        pass

@pytest.mark.django_db
class TestPrivacySettingsReflection:
    def test_hide_passports_blocks_display(self, client, profile):
        """Toggle show_game_passports=False → profile page hides them"""
        pass
    
    def test_private_account_blocks_non_followers(self, client, profile):
        """Enable private account → non-followers see private wall"""
        pass

@pytest.mark.django_db
class TestGamePassportsCRUD:
    def test_create_passport_via_api(self, client, profile):
        """POST /api/game-passports/create/ → passport appears on profile"""
        pass
    
    def test_delete_passport_via_api(self, client, profile):
        """POST /api/game-passports/delete/ → passport removed from profile"""
        pass
```

**Estimated:** 2-3 hours

### 5.2 Manual QA Checklist

**Create:** `docs/SETTINGS_MANUAL_QA_CHECKLIST.md`

```markdown
# Settings Manual QA Checklist

## Platform Preferences
- [ ] Navigate to Settings → Platform
- [ ] Change language to Bengali → Verify Bengali selected (UI remains English for now)
- [ ] Change timezone to UTC → Save → Reload
- [ ] Check wallet timestamps show UTC
- [ ] Check tournament times show UTC
- [ ] Change time format to 24h → Verify wallet shows "15:00" not "3:00 PM"
- [ ] Change back to Asia/Dhaka → Verify reverted

## Privacy Settings
- [ ] Toggle show_game_passports=OFF → Visit profile → Passports hidden
- [ ] Toggle show_wallet=OFF → Visit profile → Wallet section hidden
- [ ] Enable private account → Log out → View profile → See private wall
- [ ] As different user → Send follow request → See "Request Pending"
- [ ] Approve request → Requester can view profile

## Game Passports
- [ ] Click "Add Game Passport" → Modal opens with game list
- [ ] Select Valorant → Fill IGN/rank → Save
- [ ] Passport appears on profile instantly
- [ ] Click Edit → Change rank → Save → Updated on profile
- [ ] Click Delete → Confirm → Passport removed from profile
- [ ] Drag-drop reorder passports → Order saved
- [ ] Pin passport → Appears first on profile

... (50+ more test cases)
```

**Estimated:** 1 hour to write, 2-3 hours to execute

---

## Phase 6: Documentation ⏳ NOT STARTED

### 6.1 DELIVERABLES.md

**Summary of all files modified/created with reasons**

### 6.2 VERIFICATION.md

**Commands to run, URLs to test, expected behaviors**

### 6.3 DONE_VS_NEXT.md

**What is complete, what remains for future sprints**

---

## Total Estimated Hours

| Phase | Estimated Hours | Status |
|-------|----------------|---------|
| 0. Truth Reconciliation | 2h | ✅ COMPLETE |
| 1. Platform Wiring | 3h | 🚧 25% COMPLETE (nav added, content TODO) |
| 2. Settings Sync Verification | 2h | ⏳ NOT STARTED |
| 3. Admin Parity | 1h | ⏳ NOT STARTED |
| 4A. Identity Gender | 0.5h | ⏳ NOT STARTED (P3) |
| 4B. Security & KYC | 2.5h | ⏳ NOT STARTED (P1) |
| 4C. Privacy Expansion | 1h | ⏳ NOT STARTED (P0) |
| 4D. Notifications Cleanup | 1.5h | ⏳ NOT STARTED (P2) |
| 4E. Career & LFT Redesign | 2.5h | ⏳ NOT STARTED (P1) |
| 4F. Game Passports CRUD | 3.5h | ⏳ NOT STARTED (P0 🔥) |
| 4G. Pro Loadout Redesign | 2.5h | ⏳ NOT STARTED (P1) |
| 4H. Stream URL Validation | 1h | ⏳ NOT STARTED (P2) |
| 4I. Wallet Templates | 2.5h | ⏳ NOT STARTED (P0 🔥) |
| 4J. Danger Zone | 2.5h | ⏳ NOT STARTED (P2) |
| 5. Testing | 5h | ⏳ NOT STARTED |
| 6. Documentation | 2h | ⏳ NOT STARTED |
| **TOTAL** | **35-40 hours** | **~5% Complete** |

---

## Critical Path (For MVP)

To achieve "production-grade settings with no hardcoding":

### Must Complete (P0):
1. ✅ Platform Preferences tab (3h) - **25% done**
2. Game Passports CRUD (3.5h) - Wire to existing APIs
3. Wallet Templates (2.5h) - Fix broken pages
4. Privacy Expansion (1h) - Show all 14 toggles

**MVP Total:** 10 hours

### Should Complete (P1):
5. Security & KYC (2.5h) - Wire upload flow
6. Career & LFT Redesign (2.5h) - Make game-aware
7. Pro Loadout Redesign (2.5h) - Category-based

**P1 Total:** 7.5 hours

### Total for Production-Ready:** 17.5 hours

---

## Next Action

**DECISION REQUIRED:** Given the 35-40 hour scope, should we:

**Option A:** Complete MVP (10 hours) only
- Platform tab
- Game Passports CRUD
- Wallet templates
- Privacy expansion

**Option B:** Full production sprint (35-40 hours)
- All features
- Full testing
- Complete documentation

**Option C:** Phased approach
- Sprint 1 (today): MVP (10h)
- Sprint 2 (tomorrow): P1 features (7.5h)
- Sprint 3 (next): P2 polish + tests (15h)

**Your call, Lead Engineer.** Which path should we take?
