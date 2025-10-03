# Deprecated CSS Files

⚠️ **WARNING: These stylesheets are no longer used in active templates.**

## Moved Here: October 3, 2025

### Phase 3: JavaScript/CSS Cleanup

These CSS files were part of the old tournament system and have been replaced by modern, generic implementations.

## Files in This Directory

### 1. `valorant-tournament.css` (10KB)
- **Purpose**: Game-specific styling for Valorant tournaments
- **Used By**: `templates/tournaments/_deprecated/valorant_register.html`
- **Replaced By**: Modern registration uses generic tournament CSS
- **Why Deprecated**: 
  - Game-specific, not reusable
  - Valorant branding/colors hardcoded
  - Replaced by generic, themeable CSS

### 2. `tournament-register-neo.css` (8KB)
- **Purpose**: Styling for old registration form
- **Used By**: `templates/tournaments/_deprecated/register.html`
- **Replaced By**: Modern registration form CSS
- **Why Deprecated**:
  - Part of old registration UI
  - Not using CSS variables
  - Replaced by modern, accessible styles

## Modern Replacements

### Old System:
```css
/* Game-specific CSS (valorant-tournament.css) */
.valorant-theme { color: #ff4655; }
.valorant-bg { background: #0f1923; }
/* Hardcoded colors, no theming */
```

### New System:
```css
/* Generic, themeable CSS */
:root {
  --tournament-primary: var(--game-color, #8b5cf6);
  --tournament-bg: var(--game-bg, #1a1a2e);
}
/* Works for all games via CSS variables */
```

## Modern CSS Files (Active)

1. **`tournament-detail-neo.css`** - Detail page styling
2. **`tournament-detail-pro.css`** - Professional theme
3. **`tournament-hub-modern.css`** - Hub page styling
4. **`tournament-state-poller.css`** - State animations
5. **`tournaments.css`** - Base tournament styles

## Benefits of Modern System

✅ **Game-Agnostic**: Works for Valorant, eFootball, any game  
✅ **Themeable**: Uses CSS variables for colors  
✅ **Responsive**: Mobile-first design  
✅ **Accessible**: WCAG 2.1 compliant  
✅ **Performant**: Optimized, no duplication  

## CSS Reduction

| Metric | Before | After | Reduction |
|--------|--------|-------|-----------|
| Tournament CSS Files | 8 files | 6 files | 25% |
| Total CSS Size | ~75KB | ~60KB | 20% |
| Game-Specific Files | 2 files | 0 files | 100% |

## Safe to Delete?

**Not yet** - Kept for reference during transition period.

**Deletion Timeline**:
- **Oct 2025**: Moved to `_deprecated/`
- **Nov 2025**: Verify no references remain
- **Jan 2026**: Safe to delete permanently

## Rollback (Emergency Only)

If needed:
```bash
cd static/siteui/css
mv _deprecated/valorant-tournament.css ./
mv _deprecated/tournament-register-neo.css ./
```

**Not recommended** - Modern CSS is far superior.

---

**Last Updated**: October 3, 2025  
**Part of**: Tournament System Refactoring Phase 3
