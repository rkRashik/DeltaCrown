# Team Management Console - Routing & Navigation Architecture

**Date**: January 31, 2026  
**Status**: OPTION C - Legacy Team Authoritative  
**Phase**: Stabilization + Console Integration

---

## 🔐 LOCKED ARCHITECTURAL DECISIONS

### Model Authority
- **Legacy Team** (`apps.teams.models.Team`) is the ONLY authoritative team model
- **vNext Team** (`apps.organizations.models.Team`) is DORMANT (no production data)
- No migrations, no dual-writes, no vNext Team activation

### Implications
- vNext pages are **UI skins over legacy data**
- Organization pages **DO NOT own teams yet** (no `organization.teams` relation)
- All team queries must use Legacy Team model

---

## 🧭 URL ROUTING MAP

### Current Production Routes

```
/teams/                          → Legacy team list (apps.teams.urls)
/teams/vnext/                    → vNext hub UI (lists Legacy Teams)
/teams/<slug>/                   → Team Detail Page (vNext template, Legacy data)
/teams/management/               → Team Management Console (NEW - staff-only HQ)
/teams/<slug>/manage/            → vNext team_manage view (DORMANT - queries empty vNext Team)

/orgs/                           → Organization directory (no team counts)
/orgs/<slug>/                    → Organization detail (teams list stubbed)

/admin/teams/                    → Legacy admin (verbose_name: "Teams (Legacy System)")
/admin/organizations/            → vNext admin (verbose_name: "Organizations (vNext)")
```

### Mental Model

```
PUBLIC FACING:
/teams/<slug>/                   
  ↓ 
  Public team profile
  vNext template styling
  Legacy Team data source
  Shows "MANAGE" button if permissions.can_edit_team == True

PRIVATE CONTROL PLANE:
/teams/management/
  ↓
  Team Management Console (HQ)
  Staff/owner/admin only
  3124-line unified interface
  Legacy Team data source
  Navigation: Linked from Team Detail "MANAGE" button
```

---

## 🔌 NAVIGATION FLOW

### User Journey (Owner/Admin)

1. **Start**: Visit `/teams/<slug>/` (Team Detail Page)
2. **Permission Check**: `permissions.can_edit_team == True`
3. **Action**: Click "MANAGE" button (top-right header)
4. **Destination**: `/teams/management/` (Management Console)

### Implementation

**Team Detail Template** (`templates/organizations/team/partials/_body.html` line 258):
```html
{% if permissions.can_edit_team %}
  <button onclick="window.location.href='{% url 'teams:management_console' %}'"
          class="h-11 px-6 bg-[var(--team-primary)] ...">
    <span>MANAGE</span>
  </button>
{% endif %}
```

**Management Console View** (`apps/teams/views/manage_console.py`):
```python
@login_required
@user_passes_test(is_staff_or_superuser, login_url='/')
def team_management_console(request):
    # Uses Legacy Team model
    # Staff-only access (for now)
    # Team-level permissions TBD in Phase 6
```

---

## 🚧 ROUTING COLLISION (KNOWN ISSUE)

### Problem
- vNext URLs are registered BEFORE legacy in `deltacrown/urls.py`:
  - Line 75: `path("", include("apps.organizations.urls"))`  
  - Line 83: `path("teams/", include("apps.teams.urls"))`

### Current Behavior
- vNext team detail (`/teams/<slug>/`) OVERRIDES legacy team detail
- This is **intentional short-term** - vNext template uses Legacy Team data
- No user-facing breakage

### Future Phase 6 Options

**Option A**: Hard URL Separation
```
/teams/<slug>/         → Legacy team detail
/vnext/teams/<slug>/   → vNext team detail
```

**Option B**: Migration-Map Router
```python
def team_detail_router(request, slug):
    if TeamMigrationMap.objects.filter(legacy_slug=slug).exists():
        return vnext_team_detail(request, slug)
    else:
        return legacy_team_detail(request, slug)
```

**Decision**: DEFERRED until Phase 6 (migration activation)

---

## 📦 MODULARIZATION STATUS

### Team Management Console Template

**Source**: `templates/My drafts/TMC/Team_management.html` (3124 lines)  
**Destination**: `templates/teams/management/team_management.html`

**Extraction Progress**:
- ✅ `_head_styles.html` (lines 18-228) - CDN links, CSS variables, modal framework
- ⏸️ Pending: Sidebar, Header, Footer, Modals, Scripts

**Strategy**: ONE section at a time, verify after each extraction

---

## ✅ VERIFICATION CHECKLIST

After ANY routing or template changes:

- [ ] `python manage.py check` → 0 errors
- [ ] `/teams/management/` loads (staff login required)
- [ ] `/teams/vnext/` still lists teams
- [ ] `/teams/<slug>/` still renders correctly
- [ ] "MANAGE" button visible when `can_edit_team == True`
- [ ] No FieldError / AttributeError
- [ ] No `organization.teams` queries introduced

---

## 🛑 STOP CONDITIONS

**DO NOT PROCEED** if any change would:
- Touch vNext Team schema
- Activate organization ownership
- Rewrite large template sections inline
- Introduce new permissions/roles
- Query vNext Team model for production data

---

**Last Updated**: January 31, 2026  
**Next Phase**: Modularization (extract sidebar next)
