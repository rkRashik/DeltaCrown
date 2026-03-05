# Sprint 29 — TOC Enhancements & Calendar Export

**Sprint Goal:** Surface quality-of-life features: schedule export, bracket sharing, overview countdowns, and check-in blast reminder.

**Status:** ✅ Complete

---

## Phase 1: Overview Countdown Timers (Sprint 29A)

### Problem
Overview API (`GET /api/toc/<slug>/`) already returned `data.countdowns` array but no JS renderer existed. Calling `renderCountdowns()` would throw a `ReferenceError` at runtime.

### Solution
- **`static/tournaments/toc/js/toc-overview.js`** — Implemented `renderCountdowns(countdowns)` function:
  - Live-ticking countdown cards using `setInterval` per countdown
  - Clears previous interval sets on each refresh (no memory leaks)
  - Hides `#overview-countdowns` container when array is empty
  - Color-coded by type: registration (info), start (success), match (theme), checkin (warning)
  - Icon mapping: registration→user-plus, start→play-circle, match→swords, checkin→user-check
  - Format: `Xd HH:MM:SS` for multi-day, `HH:MM:SS` for same-day, `Now!` when expired
- **`templates/tournaments/toc/base.html`** — Added `<div id="overview-countdowns">` to overview tab

### Files Modified
| File | Change |
|------|--------|
| `toc-overview.js` | `renderCountdowns()` function + call in `render()` |
| `base.html` | `#overview-countdowns` div in overview tab |

---

## Phase 2: Check-in Blast Reminder (Sprint 29B)

### Problem
Sprint 28D planned a "Blast Reminder" button in the Check-in Hub. Backend was never implemented, HTML button was missing, data-action attributes on Open/Close buttons were absent (JS pattern `[data-checkin-action="open"]` relied on them).

### Solution — Full Stack Implementation

#### Backend
- **`checkin_service.py`** — `blast_reminder()` static method:
  - Queries `Registration.objects.filter(checked_in=False, status__in=["confirmed","auto_approved","pending"])`
  - Returns early with friendly message if all checked in
  - Fires `TOCNotificationsService.fire_auto_event(tournament, "checkin_reminder")`
  - Fires `DiscordWebhookService.send_event(tournament, "checkin_reminder", {"pending_count": count})`
  - Returns `{"sent": count, "user_ids": [...], "message": "..."}`
- **`checkin.py`** — `CheckinBlastReminderView` class
- **`urls.py`** — `POST /api/toc/<slug>/checkin/blast-reminder/`
- **`discord_webhook.py`** — `checkin_reminder` event handler in `_EVENT_HANDLERS`

#### Frontend
- **`base.html`** — Check-in Hub action bar:
  - Added `data-checkin-action="open"` to Open Check-in button
  - Added `data-checkin-action="close"` to Close Check-in button
  - Added Blast Reminder button with megaphone icon
- **`toc-checkin.js`** — `blastReminder()` async function + export

### Files Modified
| File | Change |
|------|--------|
| `checkin_service.py` | `blast_reminder()` method added |
| `checkin.py` | `CheckinBlastReminderView` added |
| `urls.py` | blast-reminder URL added |
| `discord_webhook.py` | `checkin_reminder` event handler |
| `base.html` | data-checkin-action attrs + blast button |
| `toc-checkin.js` | `blastReminder()` + export |

---

## Phase 3: Schedule Export (.ics Calendar) (Sprint 29C)

### Problem
No way to export the tournament schedule to a calendar application.

### Solution
- **`brackets.py`** — `ScheduleExportICSView` class (new):
  - `GET /api/toc/<slug>/schedule/export.ics`
  - Builds iCalendar 2.0 format (RFC 5545 compliant)
  - Each scheduled match → VEVENT with: UID, DTSTART, DTEND (1h default), SUMMARY (teams), DESCRIPTION (tournament/round/stream), URL
  - Handles both timezone-aware and naive datetimes
  - Graceful fallback: adds placeholder event if no scheduled matches
  - `_ics_escape()` helper for RFC-safe text escaping
  - Returns `text/calendar; charset=utf-8` with download disposition
- **`urls.py`** — `/schedule/export.ics` path added
- **`base.html`** — "Export .ics" button added to Schedule Manager action bar
- **`toc-schedule.js`** — `exportICS()` function (anchor-click download pattern) + export

### Files Modified
| File | Change |
|------|--------|
| `brackets.py` | `ScheduleExportICSView` + `_ics_escape()` |
| `urls.py` | `schedule/export.ics` URL |
| `base.html` | Export .ics button in schedule header |
| `toc-schedule.js` | `exportICS()` function + export |
| `toc-core.js` | `api.url()` helper (raw URL without fetch) |

---

## Phase 4: Public Bracket Share & Embed (Sprint 29D)

### Problem
No quick way for organizers to share the public bracket view or embed it in external pages.

### Solution
- **`toc-brackets.js`** — `shareBracket()` function:
  - Opens overlay with two sections:
    1. **Public Link** — read-only input field + Copy + Open New Tab
    2. **Embed Code** — `<iframe>` snippet + Copy (targets existing `#bracket-share-embed` textarea ID)
  - Uses `window.TOC_CONFIG.tournamentSlug` to build the URL: `{origin}/tournaments/{slug}/bracket/`
  - Existing public bracket view (`/tournaments/<slug>/bracket/`) requires no login (already confirmed)
- **`base.html`** — "Share" button added to playoff bracket action bar

### Files Modified
| File | Change |
|------|--------|
| `toc-brackets.js` | `shareBracket()` + export |
| `base.html` | Share button in bracket action bar |

---

## API Endpoints Added

| Method | URL | Handler | Purpose |
|--------|-----|---------|---------|
| `GET` | `/api/toc/<slug>/schedule/export.ics` | `ScheduleExportICSView` | Download schedule as iCal |
| `POST` | `/api/toc/<slug>/checkin/blast-reminder/` | `CheckinBlastReminderView` | Send reminder to all un-checked-in |

---

## Success Criteria

- [x] Overview countdown timers tick in real time on the overview tab
- [x] Check-in Open/Close buttons have correct data-action attributes for JS state management
- [x] Blast Reminder sends notifications + Discord to all pending check-in participants
- [x] Schedule can be downloaded as .ics for any calendar app (Google, Outlook, Apple)
- [x] Bracket share panel shows public URL + iframe embed code with one-click copy
- [x] `manage.py check` → 0 issues (confirmed)

---

*Sprint 29 completed: March 5, 2026*
