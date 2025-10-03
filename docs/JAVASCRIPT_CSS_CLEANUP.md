# JavaScript & CSS Cleanup - Phase 3

## Analysis Results

### Tournament JavaScript Files

| File | Size | Status | Action |
|------|------|--------|--------|
| `js/tournament-state-poller.js` | 10KB | ✅ KEEP | Phase 1 - Real-time updates |
| `js/tournament-detail-modern.js` | 7KB | ✅ KEEP | Phase 1 - Dynamic buttons |
| `js/tournament-card-dynamic.js` | 5KB | ✅ KEEP | Card components |
| `siteui/js/tournament-detail-neo.js` | 6KB | ✅ KEEP | Detail page enhancements |
| `siteui/js/tournaments-detail.js` | 4KB | ✅ KEEP | Detail orchestrator |
| `siteui/js/tournaments-hub-modern.js` | 10KB | ✅ KEEP | Hub filtering/search |
| `siteui/js/tournaments-hub.js` | 1KB | ✅ KEEP | Basic hub utils |
| `siteui/js/tournaments.js` | 1KB | ✅ KEEP | Base utilities |
| `siteui/js/tournaments-list.js` | 10KB | 📦 REVIEW | May have duplication |
| `siteui/js/tournament-matches-neo.js` | 3KB | ✅ KEEP | Match display |
| `siteui/js/valorant-tournament.js` | 16KB | ❌ DEPRECATED | Game-specific (moved) |
| `siteui/js/tournament-register-neo.js` | 6KB | ❌ DEPRECATED | Old registration (moved) |

### Tournament CSS Files

| File | Size | Status | Action |
|------|------|--------|--------|
| `css/tournament-state-poller.css` | 4KB | ✅ KEEP | Phase 1 - Animations |
| `siteui/css/tournament-detail-neo.css` | 13KB | ✅ KEEP | Detail styling |
| `siteui/css/tournament-detail-pro.css` | 4KB | ✅ KEEP | Professional theme |
| `siteui/css/tournament-hub-modern.css` | 13KB | ✅ KEEP | Hub styling |
| `siteui/css/tournaments.css` | 14KB | ✅ KEEP | Base styles |
| `siteui/css/tournament-matches-neo.css` | 7KB | ✅ KEEP | Match styling |
| `siteui/css/tournament-register-neo.css` | 8KB | 📦 REVIEW | Check if used |
| `siteui/css/valorant-tournament.css` | 10KB | ❌ DEPRECATED | Game-specific |

## Consolidation Strategy

### Phase 3A: Immediate Cleanup ✅

**Files Moved to `_deprecated/`**:
1. ✅ `siteui/js/valorant-tournament.js` - Game-specific (not generic)
2. ✅ `siteui/js/tournament-register-neo.js` - Old registration system

**Reason**: These are only referenced in deprecated templates.

### Phase 3B: CSS Consolidation

**Files to Move**:
1. `siteui/css/valorant-tournament.css` - Game-specific styling
2. `siteui/css/tournament-register-neo.css` - Old registration styling (if unused)

### Phase 3C: Module Consolidation

**Potential Consolidation** (needs analysis):
- `tournaments.js` + `tournaments-hub.js` → Might be mergeable
- Check if `tournaments-list.js` has overlap with hub functionality

## Usage Map

### Detail Page (`templates/tournaments/detail.html`)
```html
<!-- Essential Scripts -->
<script src="tournament-detail-neo.js"></script>      <!-- UI interactions -->
<script src="tournaments-detail.js"></script>         <!-- Orchestrator -->
<script src="tournaments-hub-modern.js"></script>     <!-- Filters -->
<script src="tournament-card-dynamic.js"></script>    <!-- Card components -->
<script src="tournament-detail-modern.js"></script>   <!-- Registration buttons -->
<script src="tournament-state-poller.js"></script>    <!-- Live updates -->
```

**Analysis**: All 6 scripts have distinct purposes, no duplication.

### Hub Page (`templates/tournaments/hub.html`)
```html
<script src="tournaments-hub.js"></script>            <!-- Basic utils -->
<script src="tournaments-hub-modern.js"></script>     <!-- Filters/search -->
<script src="tournament-card-dynamic.js"></script>    <!-- Card rendering -->
```

**Analysis**: Clean separation of concerns.

### Base Template
```html
<script src="tournaments.js"></script>                <!-- Global utils -->
<script src="tournaments-list.js"></script>           <!-- List management -->
```

**Analysis**: Loaded globally, check for actual usage.

## Recommendations

### Keep Active (12 files)
These files are actively used and have distinct purposes:
1. `tournament-state-poller.js` - Real-time state polling
2. `tournament-detail-modern.js` - Registration button logic
3. `tournament-card-dynamic.js` - Card component rendering
4. `tournament-detail-neo.js` - Detail page UI enhancements
5. `tournaments-detail.js` - Detail page orchestrator
6. `tournaments-hub-modern.js` - Hub filtering/search
7. `tournaments-hub.js` - Basic hub utilities
8. `tournaments.js` - Base tournament utilities
9. `tournament-matches-neo.js` - Match display
10. `tournaments-list.js` - Tournament list management

### Deprecated (2 files) ✅ DONE
Moved to `_deprecated/`:
1. ✅ `valorant-tournament.js` - Game-specific, replaced by modern system
2. ✅ `tournament-register-neo.js` - Old registration, replaced by modern

### Review Needed (2 files)
1. `tournaments-list.js` - Check if still used in base template
2. `tournament-register-neo.css` - Check if any non-deprecated templates use it

## CSS Cleanup Plan

### Step 1: Move Game-Specific Styles
```powershell
Move valorant-tournament.css to _deprecated/
Move tournament-register-neo.css to _deprecated/ (if unused)
```

### Step 2: Consolidate Variables
Check for duplicate CSS variables across tournament stylesheets.

### Step 3: Optimize Loading
Review which CSS files are needed on each page.

## Impact

### Before Cleanup:
- Tournament JS: 12 files (~76KB)
- Tournament CSS: 8 files (~75KB)

### After Phase 3A:
- Tournament JS: 10 files (~54KB) - **29% reduction**
- Deprecated JS: 2 files (~22KB)

### After Full Phase 3 (projected):
- Tournament JS: 9-10 files (~50KB) - **34% reduction**
- Tournament CSS: 6-7 files (~60KB) - **20% reduction**

## Next Steps

1. ✅ Move deprecated JS files
2. ⏳ Move deprecated CSS files
3. ⏳ Analyze tournaments-list.js usage
4. ⏳ Check for CSS variable duplication
5. ⏳ Create unified JS/CSS loading strategy

## Code Quality Improvements

### Before:
- Mixed modern and legacy code
- Game-specific files polluting namespace
- Old registration JS still loaded

### After:
- Clean modern codebase
- Generic, reusable components
- Clear separation: active vs deprecated
- Better performance (less to load)

---

**Status**: Phase 3A Complete ✅  
**Next**: Phase 3B - CSS Consolidation
