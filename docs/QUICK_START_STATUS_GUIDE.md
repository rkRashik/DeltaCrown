# 🎯 QUICK START GUIDE - Tournament Status System

## What is "Status"?

The **Status** field controls your tournament's **lifecycle** - like a workflow:

```
📝 DRAFT ──→ 🌐 PUBLISHED ──→ 🎮 RUNNING ──→ 🏆 COMPLETED
(hidden)      (accepting      (matches       (finished)
              registrations)   playing)
```

---

## Status Meanings

### 📝 DRAFT
- **Visible?** ❌ NO (hidden from public)
- **Can register?** ❌ NO
- **Use when**: Setting up tournament, not ready yet
- **Next step**: Change to PUBLISHED when ready

### 🌐 PUBLISHED  
- **Visible?** ✅ YES (shows on tournament hub)
- **Can register?** ✅ YES (if dates allow)
- **Use when**: Tournament ready, accepting registrations
- **Next step**: Change to RUNNING when tournament starts

### 🎮 RUNNING
- **Visible?** ✅ YES (shows results, brackets)
- **Can register?** ❌ NO (registration closed)
- **Use when**: Tournament in progress, matches being played
- **Next step**: Change to COMPLETED when tournament ends

### 🏆 COMPLETED
- **Visible?** ✅ YES (archived, shows results)
- **Can register?** ❌ NO
- **Use when**: All matches finished, results finalized
- **Next step**: None (final state)

---

## How to Change Status

### Method 1: Edit Tournament
1. Click tournament name in admin list
2. Find "Status" dropdown field
3. Select new status
4. Click "Save"

### Method 2: Bulk Actions (FASTER! ⚡)
1. Go to tournament list
2. **Check boxes** next to tournaments
3. Select action from dropdown:
   - **🔵 Publish selected tournaments** (DRAFT → PUBLISHED)
   - **🟢 Start selected tournaments** (PUBLISHED → RUNNING)
   - **🔴 Complete selected tournaments** (RUNNING → COMPLETED)
   - **⚙️ Reset to DRAFT status** (Any → DRAFT)
4. Click **"Go"**
5. Review confirmation messages

---

## Quick Examples

### Example 1: Launch New Tournament

```
1. Create tournament → Status = DRAFT (automatic)
2. Fill in all details (dates, fees, rules)
3. Add game config (Valorant or eFootball)
4. When ready → Select tournament → "🔵 Publish selected"
5. Tournament now visible! ✅
```

### Example 2: Tournament Day

```
1. Tournament day arrives
2. Select tournament → "🟢 Start selected tournaments"
3. Registration closes automatically
4. Matches begin
5. After tournament ends → "🔴 Complete selected"
6. Results finalized! ✅
```

### Example 3: Fix Mistake

```
1. Oops! Published wrong tournament
2. Select it → "⚙️ Reset to DRAFT status"
3. Tournament hidden from public
4. Fix details
5. Publish again when ready ✅
```

---

## Status Transitions (What's Allowed)

### ✅ Allowed Transitions

```
DRAFT → PUBLISHED     ✅ (publish when ready)
PUBLISHED → RUNNING   ✅ (start tournament)
RUNNING → COMPLETED   ✅ (finish tournament)
Any Status → DRAFT    ✅ (emergency reset)
```

### ❌ Blocked Transitions

```
DRAFT → RUNNING       ❌ (must publish first)
PUBLISHED → COMPLETED ❌ (must start first)
COMPLETED → RUNNING   ❌ (tournament already finished)
```

**System will warn you** if you try invalid transition!

---

## Color-Coded Status Badges

In admin list, you'll see colored badges:

| Badge | Status | Meaning |
|-------|--------|---------|
| ![Gray](https://via.placeholder.com/60x20/6c757d/ffffff?text=DRAFT) | DRAFT | Hidden, setup mode |
| ![Blue](https://via.placeholder.com/60x20/0d6efd/ffffff?text=PUBLISHED) | PUBLISHED | Visible, open for registration |
| ![Green](https://via.placeholder.com/60x20/198754/ffffff?text=RUNNING) | RUNNING | Tournament in progress |
| ![Red](https://via.placeholder.com/60x20/dc3545/ffffff?text=COMPLETED) | COMPLETED | Tournament finished |

---

## Common Questions

### Q: Can I change status back?
**A**: Yes! Use "⚙️ Reset to DRAFT" to unpublish. But be careful - hides tournament from public.

### Q: What happens when I publish?
**A**: Tournament appears on public hub, users can see it and register (if dates allow).

### Q: What happens when I start?
**A**: Registration closes, tournament marked as "ongoing", matches can be played.

### Q: What happens when I complete?
**A**: Results are finalized, tournament moves to "past tournaments" section, coins/prizes can be awarded.

### Q: Can I publish multiple at once?
**A**: YES! That's the point of bulk actions. Select 10 tournaments, click "🔵 Publish selected", done! ⚡

### Q: What if I set wrong status?
**A**: Just change it back. Use "⚙️ Reset to DRAFT" if needed, fix, then republish.

---

## Pro Tips 💡

### Tip 1: Use Bulk Actions
Don't edit one by one! Select multiple, use bulk actions. Saves tons of time.

### Tip 2: Check Before Publishing
Before publishing, verify:
- ✅ Dates set correctly
- ✅ Entry fee correct
- ✅ Slot size set (if limit needed)
- ✅ Game config added
- ✅ Banner uploaded

### Tip 3: Watch Registration Count
When starting tournament:
- Check how many registered
- Admin shows: "Started: Tournament Name (45 registrations)"
- If 0 registrations, you'll get a warning

### Tip 4: Status Filters
Use admin filters to see:
- Only PUBLISHED tournaments (active)
- Only RUNNING tournaments (ongoing)
- Only COMPLETED tournaments (past)

### Tip 5: Bulk Operations
Select all PUBLISHED tournaments that should start today:
1. Filter by status = PUBLISHED
2. Check all
3. "🟢 Start selected tournaments"
4. All start at once! ⚡

---

## Cheat Sheet

### Daily Admin Workflow

**Morning**:
```
1. Check tournaments starting today
2. Select them
3. "🟢 Start selected tournaments"
4. Done!
```

**Evening**:
```
1. Check tournaments that ended
2. Select them  
3. "🔴 Complete selected tournaments"
4. Review results, award prizes
5. Done!
```

**Weekly**:
```
1. Create new tournaments (DRAFT)
2. Fill in details
3. When ready, select all
4. "🔵 Publish selected tournaments"
5. Done!
```

---

## Need Help?

### System Validation
The system **prevents mistakes**:
- ❌ Can't publish tournament with invalid dates
- ❌ Can't add wrong game config
- ❌ Can't start tournament that's not published
- ❌ Clear error messages tell you what's wrong

### Error Messages
If you see errors:
1. Read the message (it tells you what's wrong)
2. Fix the issue
3. Try again

Example:
```
❌ Error: "Registration close time must be after open time"
→ Fix: Check dates, make sure close_at > open_at
→ Save again
```

### Documentation
- **Full Guide**: `docs/TOURNAMENT_COMPLETE_FIX_REPORT.md`
- **Technical Details**: `docs/TOURNAMENT_SYSTEM_AUDIT_AND_FIXES.md`
- **Summary**: `docs/TOURNAMENT_SYSTEM_FIX_SUMMARY.md`

---

## 🎉 That's It!

The status system is simple:

1. **Create** → DRAFT (hidden)
2. **Publish** → PUBLISHED (visible, open)
3. **Start** → RUNNING (active, closed)
4. **Complete** → COMPLETED (finished)

Use **bulk actions** to manage multiple tournaments at once!

---

**Questions?** Check the detailed documentation in `docs/` folder.

**Status: ✅ System Ready to Use!**
