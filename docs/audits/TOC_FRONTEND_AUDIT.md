# TOC Frontend QA & Sync Audit

> **Sprint:** Frontend QA & Sync Sprint  
> **Date:** 2026-02-10  
> **Scope:** All 6 TOC tabs — end-to-end API ↔ JS ↔ Template alignment  
> **Staging DB:** Neon (32 players, 32 payments, 96 matches, 8 groups, 32 standings)

---

## Executive Summary

The TOC frontend had **7 bugs** preventing normal operation across the Participants, Payments, and Brackets tabs. All 7 have been resolved in this sprint. The root cause of most failures was a **`created_at` field that doesn't exist on the `Payment` model** — the model uses `submitted_at` instead.

---

## Tab-by-Tab Status

### 1. Overview Tab ✅ HEALTHY

| Item | Status |
|------|--------|
| Revenue summary cards | ✅ Working — calls `payments/summary/` |
| Tournament metadata | ✅ Working — rendered from Django context |
| Quick stats | ✅ Working |

No bugs found.

---

### 2. Participants Tab ✅ FIXED

| Bug | File | Line | Fix |
|-----|------|------|-----|
| `Payment.order_by('-created_at')` crash | `participants_service.py` | 263 | → `'-submitted_at'` |
| `{# Header #}` Django comments visible in drawer | `toc-participants.js` | 448+ | → `<!-- Header -->` HTML comments |
| Registration Form Answers shown as raw JSON blob | `toc-participants.js` | 490 | → Clean key-value pair rendering |
| Payment proof was a text link only | `toc-participants.js` | 425 | → Inline thumbnail with click-to-zoom |
| Drawer missing payer phone / reference number | `toc-participants.js` | 420 | → Added Sender Phone + Reference rows |
| `_get_payment_info()` returns `None` when no PaymentVerification | `participants_service.py` | 457 | → Falls back to `Payment` model |

**Current state:**
- Participant list: ✅ renders, filters, paginates
- Detail drawer: ✅ opens, shows status/meta, payment info (with proof thumbnail), registration form answers as formatted key-value pairs, roster, timestamps
- Action buttons (approve/reject/DQ): ✅ functional
- CSV export: ✅ functional

---

### 3. Payments Tab ✅ FIXED

| Bug | File | Line | Fix |
|-----|------|------|-----|
| View default ordering `"-created_at"` → 500 error | `payments.py` | 39 | → `"-submitted_at"` |
| `ParticipantPaymentSerializer.created_at` field mismatch | `serializers.py` | 138 | → `submitted_at` |
| `PaymentRowSerializer.created_at` field mismatch | `serializers.py` | 283 | → `submitted_at` |
| JS renders `p.payment_method` but API returns `p.method` | `toc-payments.js` | 139 | → `p.method` |
| JS renders `p.submitted_at \|\| p.created_at` | `toc-payments.js` | 151 | → `p.submitted_at` |
| Pagination uses `data.count` but API returns `data.total` | `toc-payments.js` | 177 | → `data.total` + `data.pages` |

**Smart Search enhancement:**
- Backend: added `payer_account_number` to search filter (`payments_service.py`)
- Frontend: search placeholder updated to "Search by txn ID, phone, name..."
- Searches: transaction ID, sender phone, username, registration number

**Current state:**
- Payment list: ✅ loads, no more infinite spinner
- Filters (status, method): ✅ functional
- Smart Search: ✅ searches by txn ID, phone number, name, reg number
- Bulk verify: ✅ functional
- Pagination: ✅ correct total/pages from API
- Revenue cards: ✅ render from `payments/summary/`

---

### 4. Brackets Tab ✅ ENHANCED

| Change | File | Description |
|--------|------|-------------|
| Added P, GD columns to group standings | `toc-brackets.js` | Shows Played, Goal Difference alongside W/D/L/Pts |
| Added "Recalculate" button | `toc-brackets.js` | Calls `groups/standings/` to recompute |
| Group header shows format + finalized state | `toc-brackets.js` | e.g. "8 Groups · round_robin" |

**Current state:**
- Bracket tree: ✅ renders when bracket exists (single elim, double elim)
- SVG connectors: ✅ drawn between rounds
- Group stage panel: ✅ renders 8 groups with full standings table
- Group standings: ✅ Rank, Team, P, W, D, L, GD, Pts + advancing/eliminated styling
- Configure/Draw groups: ✅ functional
- Seeding editor: ✅ shows when bracket is draft
- Pipeline panel: ✅ functional

---

### 5. Matches Tab ✅ HEALTHY

| Item | Status |
|------|--------|
| Match list with state filters | ✅ Working |
| Score entry drawer | ✅ Working |
| Match state transitions | ✅ Working |
| Dispute handling | ✅ Working |

No bugs found in this sprint. Tab was already functional.

---

### 6. Settings Tab ✅ HEALTHY

| Item | Status |
|------|--------|
| Tournament settings form | ✅ Working |
| Rule editor | ✅ Working |
| Danger zone (reset, delete) | ✅ Working |

No bugs found.

---

## Files Changed

| File | Changes |
|------|---------|
| `apps/tournaments/api/toc/participants_service.py` | `created_at` → `submitted_at` in ordering; `_get_payment_info` fallback to Payment model |
| `apps/tournaments/api/toc/payments.py` | Default ordering `"-created_at"` → `"-submitted_at"` |
| `apps/tournaments/api/toc/payments_service.py` | Added `payer_account_number` to search filter |
| `apps/tournaments/api/toc/serializers.py` | 2× `created_at` → `submitted_at` (ParticipantPayment + PaymentRow serializers) |
| `static/tournaments/toc/js/toc-participants.js` | Django comments → HTML comments; enhanced drawer (proof thumbnail, form answers, phone/ref fields) |
| `static/tournaments/toc/js/toc-payments.js` | `p.payment_method` → `p.method`; removed `created_at` fallback; `data.count` → `data.total` |
| `static/tournaments/toc/js/toc-brackets.js` | Enhanced group standings table (P, GD columns); added Recalculate button |
| `templates/tournaments/toc/base.html` | Updated search placeholder text |

---

## Remaining Known Issues (Non-blocking)

1. **Knockout bracket scaffold** — No knockout bracket is generated until the admin clicks "Generate" and groups are finalized. This is by design; the UI correctly shows "No bracket generated yet."
2. **Payment proof zoom** — Uses `TOC.payments.viewProof()` overlay if available, otherwise falls back to `window.open()`. A dedicated lightbox component would be nicer long-term.
3. **Django template comments in base.html** — The `{# ... #}` comments in `base.html` are processed correctly by Django's template engine. Only the JS string literals had this issue (now fixed).

---

## Verification Checklist

- [x] Payments tab loads without 500/infinite spinner
- [x] Payments search works by txn ID, phone, name
- [x] Participant drawer shows payment info (even without PaymentVerification)
- [x] Participant drawer shows clean form answers (not raw JSON)
- [x] Participant drawer shows inline proof thumbnail
- [x] No `{# ... #}` Django comments visible in drawer
- [x] Group standings show P, W, D, L, GD, Pts
- [x] Recalculate button triggers `calculate_group_standings`
- [x] All `created_at` references on Payment model eliminated
