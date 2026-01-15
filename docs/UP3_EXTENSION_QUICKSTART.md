# UP.3 EXTENSION - Quick Start Guide for Next Agent

**Status**: ✅ Backend Complete | ⏸️ UI Pending  
**Migrations**: Applied (0067 + 0068)  
**System Check**: ✅ 0 issues

---

## 🚀 Quick Context

User requested 4 features after UP.3 completion:
1. **Pronouns** - Already existed, added to admin
2. **Profile Story** - New TextField for extended About bio
3. **Primary Team + Game** - New FKs with auto-sync (team.game → primary_game)
4. **Country Flags** - Upgraded to django-countries (ISO codes + flags)

**What's Done**: Models, migrations, admin registration  
**What's Left**: Settings forms, profile template wiring, JS sync

---

## 📋 Next Steps (In Order)

### Step 1: Update Settings Forms
**Files**: `apps/user_profile/forms.py`, `templates/user_profile/profile/settings_control_deck.html`

**Form Changes**:
```python
# apps/user_profile/forms.py

# Identity tab form - add pronouns
class IdentityForm(forms.ModelForm):
    class Meta:
        fields = [..., 'pronouns', 'country']  # country now uses CountryField widget automatically
        
# About tab form - add profile_story
class AboutForm(forms.ModelForm):
    class Meta:
        fields = [..., 'profile_story']
        widgets = {
            'profile_story': forms.Textarea(attrs={'rows': 8, 'maxlength': 2000})
        }

# Competitive tab form - add primary_team + primary_game
class CompetitiveForm(forms.ModelForm):
    class Meta:
        fields = [..., 'primary_team', 'primary_game']
    
    def clean(self):
        # Validate: if primary_team set, primary_game must match team.game
        team = self.cleaned_data.get('primary_team')
        game = self.cleaned_data.get('primary_game')
        if team and game and team.game != game:
            raise ValidationError("Primary game must match your primary team's game")
        return self.cleaned_data
```

**Template Changes** (settings_control_deck.html):
```django
{# Identity Tab #}
<div class="form-group">
    <label for="id_pronouns">Pronouns</label>
    {{ identity_form.pronouns }}
</div>

<div class="form-group">
    <label for="id_country">Country</label>
    {{ identity_form.country }}  {# django-countries widget with flags #}
</div>

{# About Tab #}
<div class="form-group">
    <label for="id_profile_story">Your Story (Optional)</label>
    <small class="form-text">Share your journey, achievements, or background</small>
    {{ about_form.profile_story }}
</div>

{# Competitive Tab #}
<div class="form-group">
    <label for="id_primary_team">Primary Team</label>
    {{ competitive_form.primary_team }}
</div>

<div class="form-group">
    <label for="id_primary_game">Primary Game</label>
    {{ competitive_form.primary_game }}
    <small class="form-text" id="game-auto-sync-hint" style="display:none;">
        🔄 Auto-filled from your primary team
    </small>
</div>

<script>
// Auto-sync logic
document.getElementById('id_primary_team').addEventListener('change', function() {
    const teamSelect = this;
    const gameSelect = document.getElementById('id_primary_game');
    const hint = document.getElementById('game-auto-sync-hint');
    
    if (teamSelect.value) {
        // Get team's game from data attribute
        const selectedOption = teamSelect.options[teamSelect.selectedIndex];
        const teamGameId = selectedOption.dataset.gameId;
        
        if (teamGameId) {
            gameSelect.value = teamGameId;
            gameSelect.disabled = true;
            hint.style.display = 'block';
        }
    } else {
        gameSelect.disabled = false;
        hint.style.display = 'none';
    }
});
</script>
```

**View Changes** (settings update views):
- Ensure team dropdown options include `data-game-id="{{ team.game.id }}"` attribute
- Validate form before saving
- Let save() override handle auto-sync (no need to manually set primary_game)

### Step 2: Wire Public Profile Template
**Files**: `apps/user_profile/views/public_profile_views.py`, `templates/user_profile/profile/public_profile.html`

**View Changes**:
```python
# public_profile_views.py

# Add to competitive_ctx
competitive_ctx = {
    ...
    'primary_team': user_profile.primary_team,  # May be None
    'primary_game': user_profile.primary_game,  # May be None
}
```

**Template Changes**:
```django
{# About Section - Profile Story #}
<div class="about-story">
    {% if profile.profile_story %}
        <h3>My Story</h3>
        <div class="prose">
            {{ profile.profile_story|linebreaks }}
        </div>
    {% endif %}
</div>

{# Competitive DNA Section - Primary Team + Game #}
{% if competitive_ctx.primary_team %}
<div class="stat-card">
    <span class="label">🏠 Home Team</span>
    <span class="value">
        <a href="{% url 'teams:team_detail' competitive_ctx.primary_team.slug %}">
            {{ competitive_ctx.primary_team.name }}
        </a>
    </span>
</div>
{% endif %}

{% if competitive_ctx.primary_game %}
<div class="stat-card">
    <span class="label">🎮 Signature Game</span>
    <span class="value">{{ competitive_ctx.primary_game.display_name }}</span>
</div>
{% endif %}

{# Hero Section - Country Flag #}
{% if profile.country %}
<div class="nationality-badge">
    {{ profile.country.flag }} {{ profile.country.name }}
</div>
{% endif %}

{# Identity Section - Country with Flag #}
{% if identity_ctx.nationality %}
<div class="identity-card">
    <span class="label">Country</span>
    <span class="value">
        {{ profile.country.flag }} {{ identity_ctx.nationality }}
    </span>
</div>
{% endif %}

{# Pronouns already wired in UP.3 phase - check identity_ctx.pronouns #}
```

### Step 3: Test Everything
```bash
# 1. System check
python manage.py check  # Should be 0 issues

# 2. Test endpoints
# Settings page
curl -I http://localhost:8000/me/settings/
# Expect: 200 OK

# Public profile
curl -I http://localhost:8000/@rkrashik/
# Expect: 200 OK

# Admin
curl -I http://localhost:8000/admin/user_profile/userprofile/
# Expect: 200 OK (if logged in as admin)

# 3. Manual testing
# - Go to /me/settings/
# - Fill in pronouns, profile_story, select primary_team
# - Verify primary_game auto-fills
# - Save and check /@username/ shows new data
# - Verify country dropdown has flags
# - Test privacy toggle for pronouns
```

---

## 🔍 Troubleshooting

### Migration Issues
```bash
# Check migration status
python manage.py showmigrations user_profile

# Should show:
# [X] 0066_remove_legacy_social_fields
# [X] 0067_convert_country_to_iso
# [X] 0068_up3_extension_fields

# If not applied:
python manage.py migrate user_profile
```

### Country Field Issues
```python
# Verify country data format
from apps.user_profile.models import UserProfile
countries = UserProfile.objects.exclude(country='').values_list('country', flat=True).distinct()
print(countries)  # Should print ISO codes like ['BD', 'US', 'IN']

# Test Country object
profile = UserProfile.objects.first()
print(profile.country.code)  # "BD"
print(profile.country.name)  # "Bangladesh"
print(profile.country.flag)  # "🇧🇩"
```

### Auto-Sync Not Working
```python
# Test save() override
from apps.user_profile.models import UserProfile
from apps.teams.models import Team

profile = UserProfile.objects.first()
team = Team.objects.first()  # Get any team
profile.primary_team = team
profile.save()

# Check if primary_game was auto-set
print(profile.primary_game)  # Should match team.game
print(profile.primary_game == team.game)  # Should be True
```

### Form Validation Errors
- If "Primary game must match your primary team's game" error appears, check:
  1. Is team.game properly loaded in form context?
  2. Is data-game-id attribute set on team dropdown options?
  3. Is JS sync script running before form submit?

---

## 📁 Key Files Reference

**Models**:
- `apps/user_profile/models_main.py` (lines 96-100, 233-255, 422-433)

**Migrations**:
- `apps/user_profile/migrations/0067_convert_country_to_iso.py` (data migration)
- `apps/user_profile/migrations/0068_up3_extension_fields.py` (schema migration)

**Admin**:
- `apps/user_profile/admin/users.py` (UserProfileAdmin + PrivacySettingsAdmin)

**Forms** (TO UPDATE):
- `apps/user_profile/forms.py`

**Templates** (TO UPDATE):
- `templates/user_profile/profile/settings_control_deck.html` (Settings page)
- `templates/user_profile/profile/public_profile.html` (Public profile)

**Views** (TO UPDATE):
- `apps/user_profile/views/public_profile_views.py` (add primary_team/game to context)

---

## 🎯 Acceptance Criteria

**When Done**:
- [ ] User can set pronouns in Settings
- [ ] User can write profile_story in Settings
- [ ] User can select primary_team in Settings
- [ ] Primary_game auto-fills when team is selected (JS)
- [ ] User can pick country with flag dropdown
- [ ] Profile shows pronouns (if visible)
- [ ] Profile shows profile_story in About section
- [ ] Profile shows primary_team in Competitive DNA
- [ ] Profile shows primary_game in Competitive DNA
- [ ] Profile shows country flag in Hero + Identity
- [ ] Server-side validation prevents mismatched team/game
- [ ] Privacy toggle works for pronouns

**Testing Checklist**:
```bash
# Backend
✅ python manage.py check → 0 issues
✅ Migrations applied (0067 + 0068)
✅ Admin forms load
✅ save() override works

# Frontend (TO TEST)
[ ] /me/settings/ → 200
[ ] Form shows all new fields
[ ] JS auto-sync works
[ ] Save succeeds
[ ] /@username/ → 200
[ ] Profile shows new data
[ ] Privacy toggle works
```

---

## 💡 Tips

1. **django-countries** automatically renders dropdown with flags - no custom widget needed
2. **save() override** handles auto-sync - don't set primary_game manually in view
3. **JS sync** is UX enhancement - backend validation is the safety net
4. **profile_story** vs **bio**: bio is hero text (short), profile_story is About section (long)
5. **Country object** has properties: `.code`, `.name`, `.flag`, `.flag_css`

---

## 📚 Reference Links

- **django-countries docs**: https://github.com/SmileyChris/django-countries
- **Full delivery report**: `docs/UP3_EXTENSION_DELIVERY_REPORT.md`
- **Original UP.3 phase**: Check `docs/` for UP.3 related documentation
- **Model auto-sync logic**: `apps/user_profile/models_main.py` lines 422-433

---

**Quick Start Command**:
```bash
# Verify backend ready
python manage.py check && echo "✅ Backend ready for UI implementation"
```

**Estimated Time**: 2-3 hours for forms + templates + testing

Good luck! 🚀
