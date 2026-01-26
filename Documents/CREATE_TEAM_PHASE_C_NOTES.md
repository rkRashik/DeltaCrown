# Create Team Phase C — Gap Closure + UX Hardening

**Status:** ✅ COMPLETE  
**Date:** January 26, 2026  
**Phase:** C (Gap Closure + UX)  
**Scope:** Persist tag/tagline, manager invites, error-to-step navigation, file preview

---

## 🎯 Phase C Objectives

**Primary Goal:** Fill critical gaps from Phase B (tag/tagline storage, manager invites, error UX) without visual changes.

**Key Deliverables:**
1. ✅ Tag + tagline persistence in DB
2. ✅ Manager invite pipeline (membership + invite model)
3. ✅ Error-to-step navigation in wizard
4. ✅ Logo/banner client-side preview with validation
5. ✅ Comprehensive regression tests

---

## 📦 What Changed

### 1. Database Schema (Tag + Tagline)

**File:** `apps/organizations/models/team.py`

**New Fields:**
```python
tag = models.CharField(
    max_length=5,
    blank=True,
    null=True,
    db_index=True,
    help_text="Team tag/abbreviation (e.g., 'PRTCL', 'SYN')"
)

tagline = models.CharField(
    max_length=100,
    blank=True,
    help_text="Short team motto/slogan"
)
```

**Constraints:**
- Tag uniqueness per game (case-insensitive enforced at app level)
- DB constraint: `unique_tag_per_game` (game_id + tag, NULL allowed)
- Index: `team_game_tag_idx` on (game_id, tag)

**Migration:** `0002_add_team_tag_and_tagline.py`

---

### 2. Manager Invite Pipeline

**New Model:** `apps/organizations/models/team_invite.py`

**Features:**
- Supports existing users (invited_user FK) or email invites (invited_email)
- 7-day expiration (auto-set on save)
- Status: PENDING, ACCEPTED, DECLINED, EXPIRED, CANCELLED
- Unique token (UUID) for invite acceptance

**Create Flow:**
1. If `manager_email` provided and user exists:
   - Create `TeamMembership` with role=MANAGER, status=INVITED
2. If `manager_email` provided and user doesn't exist:
   - Create `TeamInvite` record with invited_email
3. Response includes `invite_created: true/false`

**Files Modified:**
- `apps/organizations/api/serializers.py` - Added `manager_email` field
- `apps/organizations/api/views.py` - Invite logic in create_team endpoint
- `apps/organizations/models/__init__.py` - Export TeamInvite

**Migration:** `0003_add_team_invite_model.py`

---

### 3. Error-to-Step Navigation (Frontend)

**File:** `templates/organizations/team_create.html`

**Logic:**
- Maps `field_errors` to wizard steps:
  - Step 1: game, game_slug
  - Step 2: name, tag, tagline
  - Step 3: region, organization_id
  - Step 4: manager_email
  - Step 5: logo, banner, description
- Auto-navigates to earliest error step
- Scrolls to first error field
- Displays inline field errors

**UX Improvement:**
- Users no longer stuck on final step after submission error
- Clear visual feedback on which step needs fixing

---

### 4. File Preview + Validation (Frontend)

**Enhanced:** `previewImage()` function

**Validations:**
- File type: JPEG, PNG, WebP only
- File size: Max 5MB
- Error handling: Alert + clear input on failure

**Preview Behavior:**
- Instant FileReader preview
- Updates both preview panel and summary card
- Maintains existing design (zero visual changes)

---

### 5. API Updates

**Endpoint:** `POST /api/vnext/teams/create/`

**New Response Fields:**
```json
{
  "ok": true,
  "team_id": 123,
  "team_slug": "my-team",
  "team_url": "/organizations/teams/my-team/",
  "invite_created": true  // NEW
}
```

**Endpoint:** `GET /api/vnext/teams/validate-tag/`

**Behavior:**
- Now checks DB for uniqueness (case-insensitive)
- Query: `Team.objects.filter(tag__iexact=tag, game_id=game.id)`
- Removed org-scoping (tags are globally unique per game)

---

## 🧪 Testing

**File:** `apps/organizations/tests/test_phase_c_integration.py`

**Test Classes:**
1. **TestTagTaglinePersistence** (4 tests)
   - Model has fields
   - Create with tag/tagline
   - API persists tag/tagline
   - Null tag allowed

2. **TestTagUniqueness** (4 tests)
   - Same tag, different games → allowed
   - Same tag, same game → rejected
   - Validate endpoint checks uniqueness
   - Case-insensitive validation

3. **TestManagerInvite** (5 tests)
   - Existing user → TeamMembership INVITED
   - Non-existent user → TeamInvite record
   - Works without manager_email
   - Invite has expiry date
   - Invite includes inviter

4. **TestErrorResponses** (2 tests)
   - Validation errors include field_errors
   - Invalid tag returns field error

5. **TestPhaseQueryPerformance** (1 test)
   - Create with invite ≤15 queries

6. **TestPhaseIntegration** (1 test)
   - End-to-end with all fields

**Total:** 17 tests

**Run Tests:**
```bash
pytest apps/organizations/tests/test_phase_c_integration.py -v
```

---

## 🔍 Verification Checklist

### Database
- [x] Migrations created (0002, 0003)
- [x] `python manage.py check` passes
- [x] Tag unique constraint active
- [x] TeamInvite model exports correctly

### Backend
- [x] Tag/tagline persist on create
- [x] Validate-tag checks DB
- [x] Manager invite for existing user works
- [x] Manager invite for new email works
- [x] Create succeeds without manager_email
- [x] Hub API pattern maintained (ok field)

### Frontend
- [x] Error-to-step navigation works
- [x] File preview validation works
- [x] Field errors displayed inline
- [x] No visual regressions (pixel-perfect)

### Tests
- [x] 17 Phase C tests pass
- [x] Query count ≤15 for create with invite

---

## 📊 Query Budget

**Target:** ≤15 queries for `POST /create/` with manager invite

**Breakdown:**
1. User authentication (session, user)
2. Game lookup (by slug)
3. Organization lookup (if org_id provided)
4. Permission check (org membership)
5. Team create
6. Owner membership create
7. Manager user lookup (by email)
8. Manager membership/invite create

**Status:** ✅ Within budget

---

## 🚀 Manual Testing Steps

### 1. Tag + Tagline Persistence
```bash
# Create team with tag/tagline
curl -X POST http://localhost:8000/api/vnext/teams/create/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "name=Cloud9" \
  -F "tag=C9" \
  -F "tagline=Victory or Nothing" \
  -F "game_slug=valorant" \
  -F "region=US"

# Verify in DB
python manage.py shell
>>> from apps.organizations.models import Team
>>> team = Team.objects.get(tag='C9')
>>> print(team.tag, team.tagline)
```

### 2. Tag Uniqueness
```bash
# Try to create duplicate tag
curl -X POST http://localhost:8000/api/vnext/teams/create/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "name=FakeCloud9" \
  -F "tag=C9" \
  -F "game_slug=valorant"

# Should fail with: "This tag is already taken in this game"
```

### 3. Manager Invite (Existing User)
```bash
# Create team with existing user's email
curl -X POST http://localhost:8000/api/vnext/teams/create/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "name=MyTeam" \
  -F "game_slug=valorant" \
  -F "manager_email=existinguser@test.com"

# Check membership
>>> from apps.organizations.models import TeamMembership
>>> TeamMembership.objects.filter(status='INVITED', role='MANAGER')
```

### 4. Manager Invite (New Email)
```bash
# Create team with non-existent email
curl -X POST http://localhost:8000/api/vnext/teams/create/ \
  -F "manager_email=newuser@test.com"

# Check invite
>>> from apps.organizations.models import TeamInvite
>>> TeamInvite.objects.filter(invited_email='newuser@test.com')
```

### 5. Error-to-Step Navigation
1. Navigate to `/teams/create/`
2. Fill steps 1-5, submit without accepting terms
3. Should jump back to relevant step with error
4. Fix error, resubmit → success

### 6. File Preview
1. Upload logo → preview appears instantly
2. Upload >5MB file → alert shown, input cleared
3. Upload .txt file → alert shown, input cleared

---

## 🐛 Known Limitations (Future Work)

### From Phase B (Still Remaining)
- ❌ No "go back to fix errors" after final submission
  - **Mitigation:** Error-to-step navigation implemented in Phase C
- ❌ No email sending for invites
  - **Mitigation:** Invite records stored, email integration deferred to Phase D

### New in Phase C
- ❌ No invite acceptance UI yet
  - Invites are stored but users can't accept via UI
  - Requires Phase D: Invite management dashboard
- ❌ No invite notifications
  - No WebSocket/email notifications when invited
  - Requires Phase D: Notification system integration

---

## 📁 Files Modified (Summary)

**Models:**
1. `apps/organizations/models/team.py` - Added tag, tagline fields
2. `apps/organizations/models/team_invite.py` - NEW model
3. `apps/organizations/models/__init__.py` - Export TeamInvite

**API:**
1. `apps/organizations/api/serializers.py` - Added manager_email field
2. `apps/organizations/api/views.py` - Invite logic in create_team, tag validation fix

**Frontend:**
1. `templates/organizations/team_create.html` - Error-to-step, file validation

**Migrations:**
1. `apps/organizations/migrations/0002_add_team_tag_and_tagline.py`
2. `apps/organizations/migrations/0003_add_team_invite_model.py`

**Tests:**
1. `apps/organizations/tests/test_phase_c_integration.py` - NEW (17 tests)

**Total Changes:** 4 new files, 6 modified files, 2 migrations

---

## 🎓 Developer Notes

### Tag Normalization
- **Storage:** Case-preserved (e.g., "C9", "TL", "FNC")
- **Validation:** Case-insensitive (`tag__iexact`)
- **Why:** Users expect "TL" != "tl" visually, but DB constraint is case-sensitive on PostgreSQL
- **Implementation:** App-level case-insensitive uniqueness check

### Manager Invite Strategy
- **Why Two Models?**
  - `TeamMembership(status=INVITED)` - User already registered
  - `TeamInvite` - User not registered yet
- **Acceptance Flow (Future):**
  - Existing users: Accept → Update membership status to ACTIVE
  - New users: Sign up → Match email → Create membership → Mark invite ACCEPTED

### Error-to-Step Mapping
- **Why Not Use Scroll?**
  - Multi-step wizards hide previous steps
  - Scrolling to hidden field is bad UX
- **Solution:** Navigate to step containing error field

---

## 🔄 Migration Path

### Applying Migrations
```bash
# Staging/Production
python manage.py migrate organizations 0002
python manage.py migrate organizations 0003

# Verify
python manage.py showmigrations organizations
```

### Rollback (If Needed)
```bash
python manage.py migrate organizations 0001

# Data loss:
# - All tag/tagline values will be deleted
# - All TeamInvite records will be deleted
```

---

## 📈 Next Steps (Phase D Candidates)

1. **Invite Acceptance UI**
   - `/teams/invites/` dashboard
   - Accept/decline buttons
   - Email notifications

2. **Tag/Tagline Display**
   - Show on team detail pages
   - Include in search results
   - Add to team cards

3. **Advanced File Handling**
   - Image cropping/resizing
   - CDN upload
   - Format conversion

4. **Bulk Invite System**
   - CSV import for roster invites
   - Template-based invites

---

## ✅ Phase C Acceptance Criteria

| Criterion | Status | Notes |
|-----------|--------|-------|
| Pixel-perfect UI unchanged | ✅ | Zero visual changes |
| Tag + tagline persist | ✅ | DB fields + indexes |
| Manager invite produces artifact | ✅ | TeamMembership or TeamInvite |
| Wizard jumps to error step | ✅ | Field-to-step mapping |
| Logo/banner preview works | ✅ | FileReader + validation |
| Tests added | ✅ | 17 tests, all pass |
| Django check passes | ✅ | 0 issues |
| No production blockers | ✅ | All features stable |

**Overall Status:** ✅ **PRODUCTION READY**

---

## 🔗 Related Documentation

- [Phase B Hardening Report](./CREATE_TEAM_PHASE_B_HARDENING.md)
- [Team/Org Tracker](./TEAM_ORG_VNEXT_TRACKER.md)
- [Team Model Spec](../Documents/Team & Organization/Planning Documents/TEAM_ORG_ARCHITECTURE.md)

---

**End of Phase C Notes**
