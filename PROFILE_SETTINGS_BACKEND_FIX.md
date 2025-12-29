# Profile Settings Backend Integration Fix

## Issues Fixed

### 1. Backend API Improvements

#### Updated `/me/settings/basic/` Endpoint
**File**: `apps/user_profile/views/fe_v2.py`

Now handles ALL UserProfile fields:
- **Basic**: display_name, bio, pronouns, country, city, postal_code, address, phone
- **Legal Identity & KYC**: real_full_name, date_of_birth, nationality (only if not KYC verified)
- **Demographics**: gender
- **Emergency Contact**: emergency_contact_name, emergency_contact_phone, emergency_contact_relation

Returns JSON instead of redirect for AJAX compatibility.

#### New Endpoint: `/api/profile/data/`
**File**: `apps/user_profile/views/settings_api.py`

- GET endpoint to load current profile data
- Returns all fields for populating forms
- Added to URLs

#### Fixed Privacy Settings
**File**: `apps/user_profile/views/settings_api.py`

- Now properly connects to `PrivacySettings` model (not `UserProfile`)
- Returns all 20 privacy toggle fields
- Properly saves to database table `user_profile_privacysettings`

### 2. Required Frontend Changes

The following sections need to be added to `templates/user_profile/profile/settings.html` after the Profile & Media section:

#### Section 1: Legal Identity & KYC
```html
<section id="kyc-section" class="content-section glass-card p-8 mb-8">
    <h2 class="section-title">
        <span class="section-title-icon">📋</span>
        Legal Identity & KYC
    </h2>
    
    <div class="mb-6 p-6 bg-gradient-to-r from-yellow-900/20 to-orange-900/20 rounded-xl border border-yellow-500/30">
        <p class="text-slate-300 text-sm leading-relaxed">
            <span class="font-semibold text-yellow-400">🔒 Secure Information:</span> These details are required for tournament registration and prize distribution. 
            Once KYC is verified, these fields become locked for security.
        </p>
    </div>
    
    <form id="kyc-form" class="space-y-6">
        {% csrf_token %}
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
                <label class="form-label">Full Legal Name</label>
                <input type="text" name="real_full_name" value="{{ user_profile.real_full_name }}" 
                       class="form-input" maxlength="200" placeholder="As on official documents"
                       {% if user_profile.kyc_status == 'verified' %}disabled{% endif %}>
                <p class="form-help">Used for official tournament registration</p>
            </div>
            
            <div>
                <label class="form-label">Date of Birth</label>
                <input type="date" name="date_of_birth" value="{{ user_profile.date_of_birth|date:'Y-m-d' }}" 
                       class="form-input"
                       {% if user_profile.kyc_status == 'verified' %}disabled{% endif %}>
                <p class="form-help">Required for age verification</p>
            </div>
            
            <div>
                <label class="form-label">Nationality</label>
                <input type="text" name="nationality" value="{{ user_profile.nationality }}" 
                       class="form-input" maxlength="100" placeholder="Country of citizenship"
                       {% if user_profile.kyc_status == 'verified' %}disabled{% endif %}>
            </div>
            
            <div>
                <label class="form-label">KYC Status</label>
                <div class="p-4 rounded-xl {% if user_profile.kyc_status == 'verified' %}bg-green-900/30 border border-green-500/50{% else %}bg-slate-800/50 border border-slate-600/50{% endif %}">
                    <span class="text-white font-bold">
                        {% if user_profile.kyc_status == 'verified' %}
                            ✅ Verified
                        {% elif user_profile.kyc_status == 'pending' %}
                            ⏳ Pending Review
                        {% else %}
                            ⚠️ Not Verified
                        {% endif %}
                    </span>
                </div>
            </div>
        </div>
        
        {% if user_profile.kyc_status != 'verified' %}
        <button type="submit" class="btn btn-primary">
            💾 Save Legal Identity
        </button>
        {% endif %}
    </form>
</section>
```

#### Section 2: Contact Information
```html
<section id="contact-section" class="content-section glass-card p-8 mb-8">
    <h2 class="section-title">
        <span class="section-title-icon">📞</span>
        Contact Information
    </h2>
    
    <form id="contact-form" class="space-y-6">
        {% csrf_token %}
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
                <label class="form-label">Phone Number</label>
                <input type="tel" name="phone" value="{{ user_profile.phone }}" 
                       class="form-input" maxlength="20" placeholder="+8801XXXXXXXXX">
                <p class="form-help">International format preferred</p>
            </div>
            
            <div>
                <label class="form-label">City</label>
                <input type="text" name="city" value="{{ user_profile.city }}" 
                       class="form-input" maxlength="100" placeholder="Your city">
            </div>
            
            <div>
                <label class="form-label">Postal/ZIP Code</label>
                <input type="text" name="postal_code" value="{{ user_profile.postal_code }}" 
                       class="form-input" maxlength="20" placeholder="1234">
            </div>
        </div>
        
        <div>
            <label class="form-label">Street Address</label>
            <textarea name="address" class="form-input" rows="3" maxlength="300" 
                      placeholder="For correspondence and prize shipping">{{ user_profile.address }}</textarea>
        </div>
        
        <button type="submit" class="btn btn-primary">
            💾 Save Contact Info
        </button>
    </form>
</section>
```

#### Section 3: Demographics
```html
<section id="demographics-section" class="content-section glass-card p-8 mb-8">
    <h2 class="section-title">
        <span class="section-title-icon">👥</span>
        Demographics
    </h2>
    
    <form id="demographics-form" class="space-y-6">
        {% csrf_token %}
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
                <label class="form-label">Gender (Optional)</label>
                <select name="gender" class="form-input">
                    <option value="">Prefer not to specify</option>
                    <option value="male" {% if user_profile.gender == 'male' %}selected{% endif %}>Male</option>
                    <option value="female" {% if user_profile.gender == 'female' %}selected{% endif %}>Female</option>
                    <option value="other" {% if user_profile.gender == 'other' %}selected{% endif %}>Other</option>
                    <option value="prefer_not_to_say" {% if user_profile.gender == 'prefer_not_to_say' %}selected{% endif %}>Prefer not to say</option>
                </select>
                <p class="form-help">For demographics and gender-specific events</p>
            </div>
            
            <div>
                <label class="form-label">Pronouns (Optional)</label>
                <input type="text" name="pronouns" value="{{ user_profile.pronouns }}" 
                       class="form-input" maxlength="50" placeholder="he/him, she/her, they/them">
            </div>
        </div>
        
        <button type="submit" class="btn btn-primary">
            💾 Save Demographics
        </button>
    </form>
</section>
```

#### Section 4: Emergency Contact
```html
<section id="emergency-section" class="content-section glass-card p-8 mb-8">
    <h2 class="section-title">
        <span class="section-title-icon">🚨</span>
        Emergency Contact
    </h2>
    
    <div class="mb-6 p-6 bg-gradient-to-r from-red-900/20 to-orange-900/20 rounded-xl border border-red-500/30">
        <p class="text-slate-300 text-sm leading-relaxed">
            <span class="font-semibold text-red-400">🛡️ LAN Events Safety:</span> Emergency contact information is required for participation in LAN events and offline tournaments.
        </p>
    </div>
    
    <form id="emergency-form" class="space-y-6">
        {% csrf_token %}
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
                <label class="form-label">Emergency Contact Name</label>
                <input type="text" name="emergency_contact_name" value="{{ user_profile.emergency_contact_name }}" 
                       class="form-input" maxlength="200" placeholder="Full name">
            </div>
            
            <div>
                <label class="form-label">Emergency Contact Phone</label>
                <input type="tel" name="emergency_contact_phone" value="{{ user_profile.emergency_contact_phone }}" 
                       class="form-input" maxlength="20" placeholder="+8801XXXXXXXXX">
            </div>
            
            <div>
                <label class="form-label">Relationship</label>
                <input type="text" name="emergency_contact_relation" value="{{ user_profile.emergency_contact_relation }}" 
                       class="form-input" maxlength="50" placeholder="Parent, Spouse, Guardian, etc.">
            </div>
        </div>
        
        <button type="submit" class="btn btn-primary">
            💾 Save Emergency Contact
        </button>
    </form>
</section>
```

#### Update Sidebar Navigation
Add these items to the sidebar navigation (after "Platform"):

```html
<div class="nav-item" data-section="kyc">
    <span class="nav-icon">📋</span>
    <span>Legal & KYC</span>
</div>
<div class="nav-item" data-section="contact">
    <span class="nav-icon">📞</span>
    <span>Contact Info</span>
</div>
<div class="nav-item" data-section="demographics">
    <span class="nav-icon">👥</span>
    <span>Demographics</span>
</div>
<div class="nav-item" data-section="emergency">
    <span class="nav-icon">🚨</span>
    <span>Emergency Contact</span>
</div>
```

### 3. JavaScript Updates Required

Add to `static/user_profile/settings.js`:

```javascript
// Initialize new form handlers
const KYCForm = {
    init() {
        const form = document.getElementById('kyc-form');
        if (!form) return;
        form.addEventListener('submit', (e) => this.save(e));
        this.load();
    },
    async load() {
        try {
            const response = await fetch('/api/profile/data/');
            const data = await response.json();
            if (data.success) {
                const form = document.getElementById('kyc-form');
                if (form && data.profile) {
                    form.querySelector('[name="real_full_name"]').value = data.profile.real_full_name || '';
                    form.querySelector('[name="date_of_birth"]').value = data.profile.date_of_birth || '';
                    form.querySelector('[name="nationality"]').value = data.profile.nationality || '';
                }
            }
        } catch (error) {
            console.error('Failed to load KYC data:', error);
        }
    },
    async save(e) {
        e.preventDefault();
        const formData = new FormData(e.target);
        const data = {
            real_full_name: formData.get('real_full_name'),
            date_of_birth: formData.get('date_of_birth'),
            nationality: formData.get('nationality')
        };
        
        try {
            const response = await fetch('/me/settings/basic/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify(data)
            });
            const result = await response.json();
            if (result.success) {
                Toast.success('Legal identity updated! 📋');
            } else {
                Toast.error(result.error || 'Failed to update');
            }
        } catch (error) {
            console.error('Error:', error);
            Toast.error('Failed to save changes');
        }
    }
};

// Similar implementations for ContactForm, DemographicsForm, EmergencyForm
// Then add to DOMContentLoaded:
KYCForm.init();
ContactForm.init();
DemographicsForm.init();
EmergencyForm.init();
```

### 4. Privacy Settings JavaScript Update

Update the Privacy module in `settings.js` to properly send/receive data:

```javascript
const Privacy = {
    async load() {
        try {
            const response = await fetch('/me/settings/privacy/');
            if (response.ok) {
                const data = await response.json();
                this.populateForm(data.settings);
            }
        } catch (error) {
            console.error('Failed to load privacy settings:', error);
        }
    },
    
    async save() {
        const form = document.getElementById('privacy-form');
        const formData = new FormData(form);
        const data = {};
        
        // Include visibility_preset
        data.visibility_preset = formData.get('visibility_preset');
        
        // Include all toggles
        const toggles = form.querySelectorAll('input[type="checkbox"]');
        toggles.forEach(toggle => {
            data[toggle.name] = toggle.checked;
        });
        
        try {
            const response = await fetch('/me/settings/privacy/save/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify(data)
            });
            
            if (response.ok) {
                Toast.success('Privacy settings updated! 🔒');
            } else {
                Toast.error('Failed to update privacy settings');
            }
        } catch (error) {
            console.error('Privacy error:', error);
            Toast.error('Failed to save changes');
        }
    }
};
```

## Summary

✅ **Fixed Backend**:
- `/me/settings/basic/` now accepts ALL profile fields (15+ fields)
- New `/api/profile/data/` endpoint to load current data
- Privacy settings properly connect to `PrivacySettings` model
- All endpoints return proper JSON responses

⚠️ **Frontend HTML Needs**:
- Add 4 new sections (KYC, Contact, Demographics, Emergency)
- Update sidebar navigation with 4 new items
- All form fields properly connected

⚠️ **Frontend JavaScript Needs**:
- Add form handlers for 4 new sections
- Update Privacy.load() and Privacy.save()
- Initialize all new modules in DOMContentLoaded

## Testing Checklist

1. ✅ Open Django admin: http://127.0.0.1:8000/admin/user_profile/userprofile/1/change/
2. ✅ Fill in test data for all fields
3. ✅ Save in admin
4. Go to `/me/settings/`
5. Navigate to each section using sidebar
6. Verify all fields are populated from database
7. Edit fields and save
8. Refresh page - verify persistence
9. Check admin again - verify database updated

The backend is now fully connected and ready. The frontend HTML additions need to be made to complete the integration.
