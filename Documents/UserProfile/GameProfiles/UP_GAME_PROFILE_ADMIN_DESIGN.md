# UP-GAME-PROFILE-ADMIN-DESIGN
## Admin UX for First-Class Game Profile Management

**Status:** Design Review  
**Date:** 2024-12-24  
**Author:** AI Agent (supervised by RK Rashik)  
**Phase:** Admin Interface Design (No Code)

---

## Executive Summary

Design a **Django admin interface** for game profile management that:
- Makes editing game profiles **1-click easy** for staff
- Shows **audit trail** per game profile change
- Validates **per-game rules** (Riot ID format, Steam ID length, etc.)
- Supports **bulk normalization** for data cleanup
- Provides **verification workflow** for admins

**Key UX Goal:** Replace JSON text editor with intuitive inline forms.

---

## 1. Current Admin UX (Problems)

### 1.1 What Exists Today

**UserProfileAdmin:**
```python
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm  # Uses GameProfilesField (JSON editor)
    inlines = [GameProfileInline]  # Hidden by default
    
    fields = [
        ...,
        'game_profiles',  # TextArea with JSON validation
        ...
    ]
```

**GameProfilesField:**
- Raw JSON text editor with placeholder
- Manual formatting required
- No per-game validation
- Error-prone (easy to introduce malformed JSON)

**GameProfileInline:**
- Exists but not prominent
- Shows in collapsed section
- Not primary editing method

### 1.2 Admin Pain Points

**Problem 1: JSON Editing is Error-Prone**
```json
// Easy to make mistakes:
[
  {"game": "VALORANT", "ign": "Player#TAG"}  // Uppercase (should be lowercase)
  {"game": "valorant", "ign": "InvalidRiotID"}  // Missing tagline
]
```

**Problem 2: No Visual Feedback**
- Admin saves → no idea if IGN format is valid
- No warning for duplicate game entries
- No confirmation if changes affect tournaments

**Problem 3: No Audit Context**
- Who changed which game profile?
- When was VALORANT profile verified?
- What was the old IGN before admin edited it?

---

## 2. Proposed Admin UX

### 2.1 Primary Interface: Inline Editor

**Layout: UserProfile Change Form**

```
┌─────────────────────────────────────────────────────────────┐
│ Change User Profile: @PlayerOne (DC-25-000042)             │
├─────────────────────────────────────────────────────────────┤
│ Display Name: [PlayerOne            ] Bio: [Pro gamer...] │
│ Country: [Bangladesh ▼]                                    │
├─────────────────────────────────────────────────────────────┤
│ GAME PROFILES ────────────────────────────────────────────  │
│                                                             │
│ ┌───────────────────────────────────────────────────────┐  │
│ │ Game           IGN                Rank      Verified  │  │
│ ├───────────────────────────────────────────────────────┤  │
│ │ VALORANT ▼    [Player#1234  ]   [Immortal ] ☑ ✅     │  │
│ │ CS2 ▼         [76561198...  ]   [Global   ] ☐ 🗑️     │  │
│ │ MLBB ▼        [123456789    ]   [Mythic   ] ☐ 🗑️     │  │
│ │ ─────────────────────────────────────────────────────  │  │
│ │ + Add another Game Profile                            │  │
│ └───────────────────────────────────────────────────────┘  │
│                                                             │
│ [Save and continue editing]  [Save]  [Delete]              │
└─────────────────────────────────────────────────────────────┘
```

**Features:**
- **Dropdown for game selection** (no typos)
- **Real-time validation** (IGN format errors shown immediately)
- **Verification checkbox** (admins can mark as verified)
- **Delete button per row** (soft delete with confirmation)

### 2.2 Inline Form Fields

**GameProfileInline Configuration:**

```python
class GameProfileInline(admin.TabularInline):
    model = GameProfile
    extra = 1
    fields = [
        'game',
        'in_game_name',
        'rank_name',
        'main_role',
        'is_verified',
        'verification_method',
        'updated_at',
        'actions'  # Custom column with verify/delete buttons
    ]
    readonly_fields = ['updated_at', 'actions']
    autocomplete_fields = []
    
    def get_queryset(self, request):
        """Order by most recently updated."""
        qs = super().get_queryset(request)
        return qs.order_by('-updated_at')
    
    def actions(self, obj):
        """Custom action buttons per row."""
        if not obj.id:
            return ''
        
        return format_html(
            '<a class="button" href="{}">Audit Trail</a>',
            reverse('admin:user_profile_gameprofile_audit', args=[obj.id])
        )
```

### 2.3 Field-Level Validation

**Real-Time Validation (JavaScript):**

```javascript
// On IGN field blur
document.querySelectorAll('.field-in_game_name input').forEach(input => {
    input.addEventListener('blur', async (e) => {
        const gameField = e.target.closest('tr').querySelector('[name$="-game"]');
        const game = gameField.value;
        const ign = e.target.value;
        
        // Call validation endpoint
        const response = await fetch('/admin/validate-game-ign/', {
            method: 'POST',
            body: JSON.stringify({ game, ign }),
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (!result.valid) {
            e.target.classList.add('error');
            showErrorTooltip(e.target, result.error);
        } else {
            e.target.classList.remove('error');
        }
    });
});
```

**Server-Side Validation (Django):**

```python
# apps/user_profile/admin.py

@admin.register(GameProfile)
class GameProfileAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        """Validate IGN format before saving."""
        validator = GameValidators.get_validator(obj.game)
        
        if not validator.is_valid_ign(obj.in_game_name):
            messages.error(
                request,
                f"Invalid IGN format for {obj.game_display_name}. "
                f"Expected: {validator.format_example}"
            )
            return  # Abort save
        
        # Proceed with save
        super().save_model(request, obj, form, change)
        
        # Log audit event
        AuditService.record_event(
            subject_user_id=obj.user_id,
            actor_user_id=request.user.id,
            event_type='game_profile.admin_updated',
            object_type='GameProfile',
            object_id=obj.id,
            metadata={
                'game': obj.game,
                'changed_by': request.user.username,
                'ip_address': request.META.get('REMOTE_ADDR')
            }
        )
```

---

## 3. Bulk Actions

### 3.1 Normalize All Game Profiles

**Use Case:** Fix data inconsistencies (uppercase game slugs, malformed IGNs).

**Admin Action:**

```python
@admin.action(description="Normalize and validate game profiles")
def normalize_game_profiles(modeladmin, request, queryset):
    """Batch normalize game profiles."""
    
    success_count = 0
    error_count = 0
    errors = []
    
    for profile in queryset:
        try:
            # Get all game profiles
            game_profiles = profile.user.game_profiles.all()
            
            for gp in game_profiles:
                # Normalize game slug (lowercase)
                gp.game = gp.game.lower()
                
                # Validate IGN format
                validator = GameValidators.get_validator(gp.game)
                if not validator.is_valid_ign(gp.in_game_name):
                    errors.append(f"{profile.display_name} - {gp.game}: Invalid IGN")
                    error_count += 1
                    continue
                
                # Save
                gp.save()
                success_count += 1
        
        except Exception as e:
            errors.append(f"{profile.display_name}: {str(e)}")
            error_count += 1
    
    # Show results
    if success_count:
        modeladmin.message_user(
            request,
            f"✅ Normalized {success_count} game profiles",
            messages.SUCCESS
        )
    
    if error_count:
        modeladmin.message_user(
            request,
            f"❌ {error_count} errors. Details:\n" + "\n".join(errors[:5]),
            messages.WARNING
        )
```

### 3.2 Verify Game Profiles (Batch)

**Use Case:** Admin manually verifies screenshots submitted by users.

**Admin Action:**

```python
@admin.action(description="Mark selected profiles as verified")
def bulk_verify_profiles(modeladmin, request, queryset):
    """Bulk mark game profiles as verified."""
    
    # For each UserProfile
    for profile in queryset:
        # Get all unverified game profiles
        unverified = profile.user.game_profiles.filter(is_verified=False)
        
        for gp in unverified:
            gp.is_verified = True
            gp.verified_at = timezone.now()
            gp.verification_method = 'manual_admin'
            gp.save()
            
            # Audit log
            AuditService.record_event(
                subject_user_id=profile.user_id,
                actor_user_id=request.user.id,
                event_type='game_profile.verified',
                object_type='GameProfile',
                object_id=gp.id,
                metadata={
                    'game': gp.game,
                    'verified_by': request.user.username
                }
            )
    
    modeladmin.message_user(
        request,
        f"✅ Verified game profiles for {queryset.count()} users",
        messages.SUCCESS
    )
```

---

## 4. Audit Trail View

### 4.1 Per-Game Profile History

**URL:** `/admin/user_profile/gameprofile/{id}/audit/`

**View Layout:**

```
┌─────────────────────────────────────────────────────────────┐
│ Game Profile Audit Trail: PlayerOne - VALORANT             │
├─────────────────────────────────────────────────────────────┤
│ Current State:                                              │
│   IGN: Player#1234                                          │
│   Rank: Immortal 3                                          │
│   Verified: ✅ Yes (by admin_user on 2024-12-20)           │
├─────────────────────────────────────────────────────────────┤
│ CHANGE HISTORY                                              │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 2024-12-20 15:30 | admin_user (Admin Panel)          │   │
│ │ Action: Verified profile                              │   │
│ │ Changes:                                               │   │
│ │   • is_verified: false → true                         │   │
│ │   • verification_method: '' → 'manual_admin'          │   │
│ ├───────────────────────────────────────────────────────┤   │
│ │ 2024-12-15 10:45 | PlayerOne (Settings Page)         │   │
│ │ Action: Updated rank                                  │   │
│ │ Changes:                                               │   │
│ │   • rank_name: 'Diamond 3' → 'Immortal 3'            │   │
│ ├───────────────────────────────────────────────────────┤   │
│ │ 2024-12-01 09:00 | PlayerOne (Registration)          │   │
│ │ Action: Created profile                               │   │
│ │ Initial Values:                                        │   │
│ │   • ign: 'Player#1234'                                │   │
│ │   • rank_name: 'Diamond 3'                            │   │
│ └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Implementation:**

```python
# apps/user_profile/admin.py

class GameProfileAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:pk>/audit/',
                self.admin_site.admin_view(self.audit_trail_view),
                name='user_profile_gameprofile_audit'
            ),
        ]
        return custom_urls + urls
    
    def audit_trail_view(self, request, pk):
        """Show audit trail for single game profile."""
        game_profile = get_object_or_404(GameProfile, pk=pk)
        
        # Get audit events
        events = UserAuditEvent.objects.filter(
            object_type='GameProfile',
            object_id=game_profile.id
        ).order_by('-created_at')
        
        context = {
            'game_profile': game_profile,
            'events': events,
            'opts': self.model._meta,
        }
        
        return render(request, 'admin/game_profile_audit.html', context)
```

### 4.2 Bulk Audit Report

**Admin Action: Export Game Profile Changes**

```python
@admin.action(description="Export game profile changes (CSV)")
def export_game_profile_changes(modeladmin, request, queryset):
    """Export audit trail for selected users."""
    
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="game_profile_audit.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['User', 'Game', 'Event Type', 'Changed By', 'Changed At', 'Changes'])
    
    for profile in queryset:
        events = UserAuditEvent.objects.filter(
            subject_user_id=profile.user_id,
            object_type='GameProfile'
        ).order_by('-created_at')[:50]
        
        for event in events:
            writer.writerow([
                profile.display_name,
                event.metadata.get('game', 'N/A'),
                event.event_type,
                event.actor_user.username if event.actor_user else 'System',
                event.created_at.strftime('%Y-%m-%d %H:%M'),
                event.get_changes_summary()
            ])
    
    return response
```

---

## 5. Search & Filters

### 5.1 Admin List View Filters

**UserProfileAdmin List Filters:**

```python
class UserProfileAdmin(admin.ModelAdmin):
    list_filter = [
        'kyc_status',
        'level',
        ('user__game_profiles__game', admin.RelatedOnlyFieldListFilter),  # Filter by game
        ('user__game_profiles__is_verified', admin.BooleanFieldListFilter),
    ]
    
    search_fields = [
        'display_name',
        'user__username',
        'user__game_profiles__in_game_name',  # Search by IGN
        'public_id',
    ]
```

**Filter Example:**
```
Filters:
  Game: [All] [VALORANT] [CS2] [MLBB] ...
  Verified: [All] [Yes] [No]
  KYC Status: [All] [Verified] [Unverified] ...
```

### 5.2 GameProfile Admin

**Standalone Admin Interface:**

```python
@admin.register(GameProfile)
class GameProfileAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'game_display_name',
        'in_game_name',
        'rank_name',
        'is_verified',
        'updated_at',
        'audit_link'
    ]
    
    list_filter = [
        'game',
        'is_verified',
        'verification_method',
        ('updated_at', admin.DateFieldListFilter),
    ]
    
    search_fields = [
        'user__username',
        'in_game_name',
        'user__profile__display_name',
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'game_display_name']
    
    actions = [
        'verify_profiles',
        'unverify_profiles',
        'export_as_csv',
    ]
    
    def audit_link(self, obj):
        """Link to audit trail."""
        url = reverse('admin:user_profile_gameprofile_audit', args=[obj.id])
        return format_html('<a href="{}">View Audit</a>', url)
    
    audit_link.short_description = 'Audit'
```

---

## 6. Verification Workflow

### 6.1 Manual Verification (Admin)

**Workflow:**

1. User submits game profile with screenshot
2. Staff opens UserProfile in admin
3. Staff clicks "Verify" button on game profile row
4. Confirmation dialog: "Verify VALORANT profile for @PlayerOne?"
5. On confirm:
   - `is_verified = True`
   - `verified_at = now()`
   - `verification_method = 'manual_admin'`
   - Audit event logged
   - User notified (optional)

**UI Implementation:**

```python
# Inline form with custom button
class GameProfileInline(admin.TabularInline):
    def get_readonly_fields(self, request, obj=None):
        """Make verify button available."""
        fields = list(super().get_readonly_fields(request, obj))
        if obj and not obj.is_verified:
            fields.append('verify_button')
        return fields
    
    def verify_button(self, obj):
        """Custom verify button."""
        if obj.is_verified:
            return '✅ Verified'
        
        return format_html(
            '<a class="button" onclick="return confirm(\'Verify this profile?\')" '
            'href="{}?verify=1">Verify</a>',
            reverse('admin:user_profile_gameprofile_change', args=[obj.id])
        )
    
    verify_button.short_description = 'Verification'
```

### 6.2 Automatic Verification (API)

**Future Enhancement (Not in Scope):**

- Integrate Riot API for VALORANT verification
- Integrate Steam API for CS2/Dota 2 verification
- Background task checks IGN existence
- Auto-verify if API confirms match

---

## 7. Data Safety Features

### 7.1 Pre-Save Warnings

**Warn admin if change affects active tournaments:**

```python
def save_model(self, request, obj, form, change):
    """Check if user has active tournament registrations."""
    
    if change:
        # Check for active tournaments using this game profile
        from apps.tournaments.models import Registration
        
        active_registrations = Registration.objects.filter(
            user=obj.user,
            tournament__game__slug=obj.game,
            tournament__status__in=['registration_open', 'live']
        ).count()
        
        if active_registrations > 0:
            messages.warning(
                request,
                f"⚠️ This user has {active_registrations} active tournament(s) for {obj.game_display_name}. "
                f"Changing IGN may cause registration issues."
            )
    
    super().save_model(request, obj, form, change)
```

### 7.2 Duplicate Detection

**Prevent duplicate game entries:**

```python
def save_model(self, request, obj, form, change):
    """Check for duplicate game profiles."""
    
    if not change:  # New profile
        existing = GameProfile.objects.filter(
            user=obj.user,
            game=obj.game
        ).exists()
        
        if existing:
            messages.error(
                request,
                f"❌ {obj.user.username} already has a {obj.game_display_name} profile. "
                f"Edit the existing profile instead."
            )
            return  # Abort save
    
    super().save_model(request, obj, form, change)
```

---

## 8. Mobile/Responsive Design

### 8.1 Admin Mobile UX

**Responsive Inline Forms:**

```css
/* Custom admin CSS */
@media (max-width: 768px) {
    .inline-related {
        display: block;
        width: 100%;
    }
    
    .inline-related td {
        display: block;
        width: 100%;
        border: none;
        padding: 5px 0;
    }
    
    .inline-related td:before {
        content: attr(data-label);
        font-weight: bold;
        display: block;
    }
}
```

**Mobile-Friendly Actions:**
- Large tap targets (44x44px minimum)
- Swipe to delete gesture
- Pull-to-refresh audit trail

---

## 9. Performance Optimizations

### 9.1 Query Optimization

**Prefetch Related Game Profiles:**

```python
class UserProfileAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        """Prefetch game profiles to avoid N+1 queries."""
        qs = super().get_queryset(request)
        return qs.prefetch_related('user__game_profiles')
```

### 9.2 Caching

**Cache game profile counts:**

```python
def game_profile_count(self, obj):
    """Show count of game profiles (cached)."""
    from django.core.cache import cache
    
    cache_key = f'gp_count_{obj.user_id}'
    count = cache.get(cache_key)
    
    if count is None:
        count = obj.user.game_profiles.count()
        cache.set(cache_key, count, 300)  # 5 min cache
    
    return count

game_profile_count.short_description = 'Game Profiles'
```

---

## 10. Accessibility (WCAG 2.1 AA)

### 10.1 Keyboard Navigation

- **Tab order:** Game → IGN → Rank → Verify checkbox
- **Enter key:** Submit form
- **Escape key:** Cancel editing
- **Arrow keys:** Navigate between rows

### 10.2 Screen Reader Support

```html
<div class="inline-group" role="group" aria-label="Game Profiles">
    <table>
        <thead>
            <tr>
                <th scope="col">Game</th>
                <th scope="col">In-Game Name</th>
                <th scope="col">Rank</th>
                <th scope="col">Verified</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>
                    <label for="id_game_profiles-0-game" class="sr-only">Game</label>
                    <select id="id_game_profiles-0-game" name="game_profiles-0-game">
                        <option value="valorant">VALORANT</option>
                    </select>
                </td>
                <!-- ... -->
            </tr>
        </tbody>
    </table>
</div>
```

---

## 11. Success Metrics

### 11.1 Admin Efficiency

**Before (JSON Editor):**
- Average time to edit game profile: 2-3 minutes
- Error rate: 15% (malformed JSON, wrong formats)
- Support tickets: ~10/month for "help me edit JSON"

**After (Inline Forms):**
- Target time to edit: < 30 seconds
- Target error rate: < 2% (with validation)
- Target support tickets: < 2/month

### 11.2 Data Quality

**Metrics to Track:**
- % of game profiles with verified=True
- % of IGNs matching format validation
- Duplicate game entries per user (target: 0)
- Audit events per month (track admin activity)

---

## 12. Implementation Checklist

**Phase 1: Basic Inline Editor**
- [ ] Make `GameProfileInline` primary editing method
- [ ] Hide `game_profiles` JSONField (mark read-only)
- [ ] Add game dropdown (choices from SUPPORTED_GAMES)
- [ ] Add delete button per row

**Phase 2: Validation**
- [ ] Server-side IGN format validation
- [ ] JavaScript real-time validation (optional)
- [ ] Duplicate detection on save
- [ ] Tournament warning on IGN change

**Phase 3: Audit Trail**
- [ ] Create audit trail view (`/admin/.../audit/`)
- [ ] Add "View Audit" button per row
- [ ] Implement CSV export action

**Phase 4: Bulk Actions**
- [ ] Normalize game profiles action
- [ ] Bulk verify action
- [ ] Export changes action

**Phase 5: Polish**
- [ ] Mobile-responsive CSS
- [ ] Accessibility improvements (ARIA labels)
- [ ] Performance optimization (prefetch, caching)

---

## 13. Wireframes (Text-Based)

### 13.1 Inline Form (Edit Mode)

```
┌──────────────────────────────────────────────────────────────┐
│ GAME PROFILES                                                │
├──────────────────────────────────────────────────────────────┤
│ ┌────────┬─────────────┬──────────┬──────────┬─────────────┐│
│ │ Game   │ IGN         │ Rank     │ Verified │ Actions     ││
│ ├────────┼─────────────┼──────────┼──────────┼─────────────┤│
│ │[VAL ▼] │[Player#1234]│[Immortal]│[✓]       │[Audit][🗑️] ││
│ │[CS2 ▼] │[76561198...] [Global ]│[ ]       │[Audit][🗑️] ││
│ │[Add ▼] │[           ]│[        ]│[ ]       │            ││
│ └────────┴─────────────┴──────────┴──────────┴─────────────┘│
│                                                              │
│ [+ Add another Game Profile]                                │
└──────────────────────────────────────────────────────────────┘
```

### 13.2 Audit Trail Page

```
┌──────────────────────────────────────────────────────────────┐
│ ← Back to User Profile                                       │
├──────────────────────────────────────────────────────────────┤
│ Game Profile Audit Trail                                     │
│ User: @PlayerOne  |  Game: VALORANT                         │
├──────────────────────────────────────────────────────────────┤
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃ 2024-12-20 15:30 UTC                                    ┃ │
│ ┃ Changed by: admin_user (via Django Admin)               ┃ │
│ ┃ Event: Profile Verified                                 ┃ │
│ ┃                                                          ┃ │
│ ┃ Changes:                                                 ┃ │
│ ┃   is_verified:    false → true                          ┃ │
│ ┃   verified_at:    null → 2024-12-20 15:30:00            ┃ │
│ ┃   verified_method: '' → 'manual_admin'                  ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
│                                                              │
│ ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃ 2024-12-15 10:45 UTC                                    ┃ │
│ ┃ Changed by: PlayerOne (via Settings Page)               ┃ │
│ ┃ Event: Rank Updated                                     ┃ │
│ ┃                                                          ┃ │
│ ┃ Changes:                                                 ┃ │
│ ┃   rank_name: 'Diamond 3' → 'Immortal 3'                ┃ │
│ ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛ │
└──────────────────────────────────────────────────────────────┘
```

---

## 14. Testing Plan

### 14.1 Manual Testing

**Test Cases:**
1. Add new game profile via inline form
2. Edit existing game profile
3. Delete game profile (confirm deletion)
4. Validate IGN format (VALORANT: require #tagline)
5. Attempt duplicate game (should block)
6. Verify game profile (mark as verified)
7. View audit trail (check event history)
8. Export audit trail as CSV
9. Bulk normalize action (fix uppercase games)
10. Mobile responsiveness (test on phone)

### 14.2 Automated Testing

```python
# apps/user_profile/tests/test_admin_game_profiles.py

class TestGameProfileAdmin:
    def test_inline_form_shows_game_profiles(self, admin_client, user_with_game_profiles):
        """Admin inline shows user's game profiles."""
        response = admin_client.get(f'/admin/user_profile/userprofile/{user_with_game_profiles.profile.id}/change/')
        assert response.status_code == 200
        assert b'GameProfileInline' in response.content
    
    def test_save_validates_ign_format(self, admin_client, user):
        """Admin save validates IGN format per game."""
        data = {
            'game': 'valorant',
            'in_game_name': 'InvalidFormat',  # Missing #tagline
        }
        response = admin_client.post(f'/admin/user_profile/gameprofile/add/', data)
        assert 'Invalid IGN format' in str(response.content)
    
    def test_bulk_verify_action(self, admin_client, users_with_unverified_profiles):
        """Bulk verify action marks profiles as verified."""
        # Select users and run action
        ...
        
        # Check all game profiles now verified
        for user in users_with_unverified_profiles:
            assert all(gp.is_verified for gp in user.game_profiles.all())
```

---

## 15. Documentation for Staff

### 15.1 Admin Guide

**How to Edit Game Profiles:**

1. Navigate to User Profile in admin
2. Scroll to "Game Profiles" section
3. Click game dropdown to select game
4. Enter IGN (format validated automatically)
5. Enter rank (optional)
6. Check "Verified" if confirming user owns this account
7. Click "Save"

**How to Verify Game Profiles:**

1. User submits verification request with screenshot
2. Open User Profile in admin
3. Find game profile row
4. Check "Verified" checkbox
5. Save profile
6. Audit event logged automatically

**How to View Change History:**

1. Open User Profile in admin
2. Click "Audit" link next to game profile
3. View timeline of all changes
4. Export as CSV if needed

---

**Document Status:** ✅ READY FOR REVIEW  
**Next Document:** UP_GAME_PROFILE_FE_CONTRACT.md  
**Implementation:** Pending architecture + FE contract approval
