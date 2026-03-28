# Notification Rebuild Tracker

## Mission
Rebuild DeltaCrown notifications to match the source-of-truth UI contract in templates/My drafts/demo_notification.html while staying efficient under a strict 512MB RAM budget.

## Current Phase
- Phase 6: UI/UX fidelity restoration (completed)
- Phase 6 re-validation pass (2026-03-27): completed with demo-parity mapper/render/CSS updates
- Phase 7: cache-busting + legacy data bulletproofing + interaction reliability pass (completed)

## Phase 7 Completed Tasks
- Forced browser cache refresh for notification assets in `templates/base.html` by bumping static query versions for:
  - `siteui/css/notifications_v2050.css`
  - `js/notifications_client.js`
- Hardened legacy row rendering in `apps/notifications/selectors.py`:
  - Strict canonical category mapping to `TOURNAMENT|TEAM|ECONOMY|SOCIAL|SYSTEM|WARNING`
  - Legacy alias fallback mapping (`info`, `alert`, etc.)
  - Regex smart highlighting for usernames, tournament/team phrases, and amounts
  - Mention-based user avatar enrichment for social/team legacy text rows
  - Tournament media now prioritizes related game icon/logo/banner before tournament media
- Restored interaction reliability in `static/js/notifications_client.js`:
  - Per-card delete button rendering returned
  - Click-through notification cards now mark read before navigation
  - Bell ringing animation hook added and toggled by unread/new realtime events
  - Existing mark-read, clear-all, swipe-dismiss, CTA action dispatch, and SSE prepend flows retained

## Phase 7.1 Completed Tasks
- Refined notification semantic fallback behavior in `apps/notifications/selectors.py`:
  - Deterministic title fallback by context (`Team Join Request`, `Match Reminder`, `New Follower`, etc.)
  - Broadened match-reminder detection for legacy text rows containing check-in/start cues
  - Ensured `Check In` CTA appears for legacy reminder rows via normalized action routing
- Refined UI parity in `static/js/notifications_client.js`:
  - Card-level delete CTA constrained to main inbox cards only (dropdown remains clean preview surface)
- Forced fresh browser asset pull for latest pass:
  - Updated static version query tags in `templates/base.html` to `v=2.3-20260327c`

## Phase 7.2 Completed Tasks
- Finalized alert audio reliability in `static/js/notifications_client.js`:
  - Added graceful in-browser WebAudio fallback tone when `/static/media/notification_alert.mp3` is missing or autoplay-blocked
  - Preserved MP3-first behavior when the static asset is present
- Verified notification migration rollout state in active environment:
  - `notifications.0003_notification_phase2_reconciliation` is applied
  - `notifications.0004_rename_notifications_recipient_category_created_idx_notificatio_recipie_5a7f6a_idx_and_more` is applied
  - `notifications.0005_notification_structured_fields` is applied (enables `html_text`, `avatar_url`, `image_url`, `action_data`, `notification_type`)

## Phase 1 Completed Tasks
- Read source-of-truth frontend template and extracted required interaction model:
  - Categories: TOURNAMENT, TEAM, ECONOMY, SOCIAL, SYSTEM, WARNING
  - Filters: ALL, UNREAD, TEAM (Invites)
  - Presentation: grouped by time buckets (Today, Yesterday, Older), mobile swipe-to-dismiss, desktop dropdown + mobile sheet
  - Card payload behavior: icon/avatar fallback, title, rich text/body, action buttons, read state, timestamps, optional deep links
- Audited current notification backend and transport layers:
  - apps/notifications/models.py
  - apps/notifications/views.py
  - apps/notifications/urls.py
  - apps/notifications/sse.py
  - apps/notifications/services.py
  - apps/notifications/tasks.py
  - apps/notifications/subscribers.py
  - apps/notifications/events/__init__.py
- Audited current templates/JS surfaces:
  - templates/notifications/list_modern.html
  - templates/notifications/list.html
  - templates/notifications/_bell.html
  - static/js/live_notifications.js
  - static/siteui/js/notifications.js
- Confirmed migration mismatch risk linked to production failure:
  - Runtime reports applying notifications.0003_notification_is_actionable_and_more and fails on duplicate column is_actionable
  - Local source tree currently has only notifications migrations 0001 and 0002
  - Multiple conflicting 0003+ compiled migration artifacts exist in apps/notifications/migrations/__pycache__ (branch drift / stale migration lineage signal)

## Phase 2 Completed Tasks
- Added idempotent reconciliation migration: `apps/notifications/migrations/0003_notification_phase2_reconciliation.py`
  - Safely adds missing schema columns when absent: `is_actionable`, `priority`, `read_at`
  - Normalizes legacy category values into canonical taxonomy
  - Backfills `read_at` for previously read rows
  - Creates query-critical indexes only when missing
- Updated `Notification` domain model in `apps/notifications/models.py`
  - Added `NotificationCategory` taxonomy choices: `TOURNAMENT`, `TEAM`, `ECONOMY`, `SOCIAL`, `SYSTEM`, `WARNING`
  - Added priority/actionability/read tracking fields for contract-forward behavior
  - Added category normalization guardrails in `save()` for backwards compatibility with legacy lowercase inputs
  - Added new composite indexes for feed and unread filtering efficiency
- Implemented optimized payload mapper in `apps/notifications/selectors.py`
  - Query builder uses narrow `.only(...)` projection and `select_related(...)`
  - Batched related-object hydration for follow requests and team invites (avoids N+1)
  - Maps backend records to frontend contract payload keys:
    - `{ id, type, read, timestamp, time, title, htmlText, avatar/image, actionLink, actions[] }`
- Added consolidated API endpoint skeletons in `apps/notifications/views.py` + `apps/notifications/urls.py`
  - `GET /notifications/api/feed/` (paginated)
  - `GET /notifications/api/preview/` (top-N)
  - `POST /notifications/api/mark-read/`
  - `POST /notifications/api/action/<action_id>/` (Phase 2 scaffold response)
- Validation completed:
  - Django system check passes with no issues
  - Migration chain now shows pending `0003_notification_phase2_reconciliation`

## Phase 2 Pending Tasks
- Apply `0003_notification_phase2_reconciliation` in controlled environment windows (staging first, then production)
- Run targeted regression suite for notifications API and follow/team invite flows after migration apply

## Phase 3 Completed Tasks
- Integrated demo-style notification surfaces into production navigation and inbox:
  - Desktop bell dropdown with segmented controls in `templates/partials/primary_navigation.html`
  - Mobile notification bottom sheet and overlay in `templates/partials/primary_navigation.html`
  - New inbox page layout in `templates/notifications/inbox.html`
- Added globally available notification styling and animation layer:
  - `static/siteui/css/notifications_v2050.css`
  - Included globally in `templates/base.html`
- Replaced mock notification frontend logic with live Vanilla JS client:
  - `static/js/notifications_client.js`
  - Fetches preview from `/notifications/api/preview/`
  - Fetches feed from `/notifications/api/feed/`
  - Uses mapped payload contract to render cards
- Implemented real-time SSE client integration:
  - EventSource listens on `/notifications/stream/`
  - Prepends incoming `new_items` into dropdown and inbox feed
  - Updates unread badges/header count live
  - Plays `/static/media/notification_alert.mp3` only for `HIGH` / `CRITICAL` priority notifications
- Wired actions and gestures:
  - Accept/Decline action buttons POST to `/notifications/api/action/<action_id>/`
  - Swipe-to-dismiss posts delete (fallback mark-read)
  - Mark-all-read buttons POST to `/notifications/api/mark-read/` with `mark_all=true`
- Completed aggressive cleanup of deprecated surfaces:
  - Deleted `templates/notifications/list_modern.html`
  - Deleted `templates/notifications/list.html`
  - Deleted `templates/notifications/_bell.html`
  - Deleted `static/js/live_notifications.js`
  - Deleted `static/siteui/js/notifications.js`
- Updated backend compatibility for cutover:
  - `notifications.list_view` now serves `notifications/inbox.html`
  - `api_mark_read` supports mark-all mode
  - `api_action` returns accepted 200 response for optimistic UI
  - `nav_preview` no longer depends on deleted bell template
  - SSE stream now emits `new_items` payload for realtime prepend

## Phase 3 Pending Tasks
- Add production audio asset at `/static/media/notification_alert.mp3` if not yet present in static bundle
- Execute end-to-end mobile gesture/manual QA on staging with live SSE events

## Phase 4 Completed Tasks
- Implemented real action business logic in `apps/notifications/services.py` via `NotificationActionService`:
  - Action ID dispatch for `follow_accept_*`, `follow_reject_*`, `invite_accept_*`, `invite_decline_*`, and `open_*`
  - Follow request actions now execute canonical domain logic through `FollowService.approve_follow_request()` and `FollowService.reject_follow_request()`
  - Team invite actions now execute transactional accept/decline flows with invite row locking, pending-state validation, expiry handling, and membership upsert
  - Action consumption now enforces UI contract by updating matching notifications to:
    - `is_actionable=False`
    - `is_read=True`
    - `read_at=<timestamp>`
- Upgraded `POST /notifications/api/action/<action_id>/` in `apps/notifications/views.py`:
  - Replaced scaffolded `200 accepted` response with secure action execution dispatch
  - Added structured lifecycle logging for start, success, reject, and unexpected failure paths
  - Added explicit error code + status mapping for forbidden/not-found/already-processed scenarios
- Hardened SSE lifecycle in `apps/notifications/sse.py` for low-memory safety:
  - Added connection lifecycle logs (`open`, `subscribed`, `client_disconnected`, `closed`, error paths)
  - Added explicit generator `finally` cleanup to immediately close optional Redis pubsub/client resources on disconnect
  - Added `close_old_connections()` on stream shutdown to release stale DB connections quickly
  - Kept polling fallback for environments where Redis pubsub is disabled/unavailable

## Phase 5 Completed Tasks
- Applied PostgreSQL migration hotfix in `apps/notifications/migrations/0003_notification_phase2_reconciliation.py`:
  - Replaced SQLite-style boolean comparison in backfill SQL from `is_read = 1` to `is_read = TRUE`
  - Replaced SQLite-style default boolean literal in raw ALTER SQL for PostgreSQL path from `DEFAULT 0` to `DEFAULT FALSE`
- Hardened client fetch resilience in `static/js/notifications_client.js`:
  - Added CSRF token fallback extraction from `csrftoken` cookie for Vanilla JS POST requests (`mark-read`, `action`, `delete`)
  - Added defensive `Array.isArray(...)` guards for feed/preview `items` payloads to avoid runtime errors on empty/non-array responses
- Added graceful audio failure handling in SSE UI path:
  - Wrapped notification audio playback with warning log fallback: `console.warn('Audio play blocked/missing', e)`
- Validation:
  - Django system checks pass after hotfix changes

## Phase 6: UI/UX Fidelity Restoration Complete
- Fixed `/notifications/` page top spacing in `templates/notifications/inbox.html` by removing excessive top margin so the header aligns cleanly with the navigation bar.
- Restored backend payload richness in `apps/notifications/selectors.py`:
  - Added smart contextual highlighting for usernames/team/tournament messaging in `htmlText`.
  - Kept actionable `actions[]` payload generation for follow/team invite workflows.
  - Preserved and expanded media mapping logic for avatar/image rendering, including optional tournament media resolution when available.
- Restored high-fidelity rendering behavior in `static/js/notifications_client.js`:
  - Reintroduced source-of-truth icon/color dictionaries and card rendering branches for avatar/image/category SVG fallback.
  - Reintroduced CTA button rendering with icon support.
  - Reintroduced `swipe-action-bg` and source-style `attachSwipeListeners()` gesture behavior, invoked on each feed render.
- Enforced source-of-truth visual utility classes in `static/siteui/css/notifications_v2050.css`:
  - Added `.hl-user`, `.hl-team`, `.hl-tourney`, and related highlight utilities.
  - Added swipe gesture classes (`.swipe-container`, `.swipe-action-bg`, `.swipe-content`, `.swiping`).
  - Added glassmorphism utility classes (`.glass-dropdown`, `.glass-sheet`) and custom scrollbar rules.

## Mission Closeout Summary
- DeltaCrown notifications now run on a unified contract-first architecture:
  - Canonical category + priority taxonomy at the model layer
  - Optimized selector/mapper pipeline for feed and preview payloads
  - Consolidated API surface for list/preview/read/action behavior
  - Single Vanilla JS runtime for desktop dropdown, mobile sheet, inbox rendering, and SSE reconciliation
  - Action endpoint backed by real domain operations (follow requests and team invites), not scaffolds
- Platform safety and operability goals achieved:
  - Migration drift reconciled with idempotent schema guards
  - Legacy template/script duplication aggressively removed
  - SSE stream now includes explicit disconnect cleanup and structured observability hooks
  - Action flows are transactional and consume actionable notifications deterministically
- Remaining operational rollout steps:
  - Run final staging smoke suite (feed/preview/actions/SSE/mobile gestures)
  - Run full PostgreSQL notification test suite in an environment with Docker daemon or local Postgres on `localhost:5433`

## Architectural Decisions (Locked for Implementation)
- Keep SSE as primary real-time path (lightweight and RAM-safe for one-way updates).
- Avoid mandatory Redis/Celery for in-app real-time delivery; keep async tasks only for optional channels (email/discord digests).
- Introduce a strict notification API contract layer so frontend rendering never depends on ad hoc template conditionals.
- Normalize notification taxonomy to a stable category enum for UI and analytics:
  - TOURNAMENT, TEAM, ECONOMY, SOCIAL, SYSTEM, WARNING
- Move rich copy assembly to server-side formatter templates using contextual entities; avoid hardcoded message strings in JS.
- Enforce query discipline:
  - Paginated inbox endpoints
  - select_related/prefetch_related for actor/team/tournament joins
  - narrow field projections for list payloads
- Audio policy:
  - Use a static notification_alert.mp3 asset and trigger only for high-priority events (e.g., match reminders, invites)
  - Gate playback by visibility/user-interaction/browser policy

## Step-by-Step Technical Plan (Bridge Old Backend to New Frontend)
1. Migration Safety Phase
- Create a reconciliation migration chain for notifications app:
  - Replace conflicting historical 0003 path with an idempotent schema state migration strategy
  - Guard column adds with database introspection / separate state and database operations where needed
- Validate on staging with migrate --plan and full migrate on production snapshot clone

2. Domain Contract Phase
- Add NotificationCategory enum and NotificationPriority enum in model/domain layer.
- Define canonical payload schema for feed and bell:
  - id, category, type, priority, is_read, created_at, actor, team, tournament, economy, content, actions, links, media
- Add serializer/mapper module translating Notification rows + related objects into frontend contract JSON.

3. Query Optimization Phase
- Replace broad object loading with list-specific query builders:
  - Inbox list query (paginated)
  - Bell preview query (top N)
  - Unread counters query
- Add/select DB indexes based on access patterns:
  - (recipient, is_read, created_at)
  - (recipient, category, created_at)
  - (recipient, priority, is_read)

4. Endpoint Consolidation Phase
- Consolidate overlapping endpoints into a coherent API surface:
  - GET /notifications/api/feed
  - GET /notifications/api/preview
  - POST /notifications/api/mark-read
  - POST /notifications/api/mark-all-read
  - POST /notifications/api/delete
  - POST /notifications/api/action/<kind>/<id>
  - GET /notifications/stream (SSE)
- Keep backward-compatible adapters temporarily; remove after template/JS migration complete.

5. Frontend Integration Phase
- Build a dedicated notifications page template aligned to demo_notification.html structure.
- Implement one shared client module for:
  - segmented filters
  - desktop dropdown + mobile sheet
  - swipe dismiss
  - optimistic read/delete updates
  - SSE event reconciliation
- Remove duplicate inline scripts from list_modern/list/_bell after parity achieved.

6. High-Priority Audio Phase
- Add notification_alert.mp3 under static media path.
- Trigger audio only for priority HIGH/CRITICAL events and only when unread high-priority count increases.

7. Cleanup Phase
- Delete deprecated templates and scripts after cutover:
  - templates/notifications/list.html
  - redundant logic currently duplicated in list_modern.html and _bell.html
  - static/js/live_notifications.js once replaced by unified client module
- Remove legacy signal hooks once event-driven handlers are fully mapped and tested.

8. Verification & Rollout Phase
- Add tests:
  - payload schema contract tests
  - endpoint pagination/filter tests
  - SSE event shape tests
  - action endpoint tests (follow/invite flows)
  - migration smoke tests against dirty schema states
- Run staged rollout with feature flag and measure:
  - query count per request
  - p95 endpoint latency
  - process memory deltas

## Destroy vs Rewrite Matrix (Initial)
- Destroy/Retire (post-cutover):
  - templates/notifications/list.html (legacy duplicate surface)
  - duplicated inline action/notification JS spread across templates/notifications/list_modern.html and templates/notifications/_bell.html
  - static/js/live_notifications.js (replace with unified module)
- Rewrite:
  - apps/notifications/views.py (currently monolithic and mixed responsibilities)
  - templates/notifications/list_modern.html (currently mixes rendering, action logic, polling, and sound synthesis)
  - templates/notifications/_bell.html (heavy type branching in template; should consume normalized payload)
- Keep with targeted refactor:
  - apps/notifications/sse.py (keep transport idea, optimize payload/event cadence)
  - apps/notifications/services.py (keep delivery core, split into domain service + channel adapters)
  - apps/notifications/tasks.py (retain optional async channels only)

## Risks Identified
- Migration lineage drift (multiple historical 0003 variants) can break deploys if unresolved.
- Mixed event sources (signals + event bus + direct service calls) can create duplicate notifications.
- In-template JS duplication increases drift between bell and full inbox behavior.

## Next Phase (Optional Follow-Up)
- Phase 5: Extended QA and metrics verification
  - Add API integration tests for feed/preview/actions/mark-read + SSE event payloads
  - Add explicit dashboard counters/alerts for action success/error ratios and SSE connection churn
  - Validate static asset packaging for notification audio in deploy pipelines
