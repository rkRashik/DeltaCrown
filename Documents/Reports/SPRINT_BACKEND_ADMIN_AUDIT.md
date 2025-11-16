# PART 1/5 – Diagnosis Report (Backend + Django Admin Audit)

Scope: Comprehensive audit of backend models, services, and Django Admin, aligned strictly to Planning Documents.

Planning sources reviewed:
- Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md
- Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md
- Documents/Planning/PART_2.3_REALTIME_SECURITY.md
- Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md
- Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md
- Documents/Planning/PART_4.1_UI_UX_DESIGN_FOUNDATIONS.md
- Documents/Planning/PART_4.2_UI_COMPONENTS_NAVIGATION.md
- Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md
- Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md
- Documents/Planning/PART_4.5_SPECTATOR_MOBILE_ACCESSIBILITY.md
- Documents/Planning/PART_4.6_ANIMATION_PATTERNS_CONCLUSION.md
- Documents/Planning/PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md
- Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md
- Documents/Planning/PROPOSAL_PART_1_EXECUTIVE_SUMMARY.md

Key code reviewed:
- apps/tournaments/models/{tournament.py, registration.py, match.py, bracket.py}
- apps/tournaments/admin.py, admin_registration.py, admin_match.py, admin_bracket.py
- apps/tournaments/services/{registration_service.py, game_config_service.py}
- apps/tournaments/services/check_in_service.py (new), plus view integrations

---

## A) What is missing

- Game model is missing `game_config` JSONB field required by Game Admin and GameConfigService.
- Tournament model missing key JSONB `config` block described in ERD for advanced configuration.
- Tournament model lacks separate check-in closing field (`check_in_closes_minutes_before`); planning calls for open/close windows.
- Registration model lacks unique constraint on `(tournament, team_id)` for team tournaments.
- Organizer/staff role models or filtering hooks missing for admin forms (Tournament.organizer should be limited to staff/organizers).
- Rich text editor integration (WYSIWYG) for Tournament.description and rules_text in admin.
- Admin custom pages for advanced controls (payments, webhooks, audit, notifications) as per planning docs.
- Versioning/audit hooks are referenced but incomplete across models beyond TournamentVersion.
- Admin actions for “force check-in”, “regenerate bracket”, “approve/reject/refund” are incomplete or not wired in all relevant places.
- Data seed/fixtures for Games (planning expects ~9 supported games) not present.

## B) What is incorrect

- Admin/GameAdmin references `game_config` in fieldsets, but `Game` model does not have such field → raises error “Unknown field(s) (game_config) specified for Game.”
- Admin/MatchAdmin references `tournament.title` and `tournament__title` ordering; model uses `Tournament.name` field → admin list/search/links are broken.
- Bracket.__str__ uses `self.tournament.title`; `Tournament` has `name` → string representation broken.
- Check-in implementation assumes `check_in_closes_minutes_before` but field does not exist on Tournament → mismatched logic and fallbacks.
- Registration unique_together only (tournament, user) — misses team uniqueness constraint required by ERD for team tournaments.

## C) What is incomplete

- Payment proof validation checks file size and extension but does not validate MIME/content-type or anti-malware scanning hooks described in security planning.
- GameConfigService provides schema management but without a backing Game.game_config field and no admin widget to edit/validate JSON with schema hints.
- TournamentVersion exists but end-to-end versioning and rollback flows not wired for all critical changes.
- Bracket/Match admin actions exist but state transition enforcement and permissions need more constraints (per planning security rules).
- Staff/role-based filtering in admin queryset/forms is not applied (organizer choices unbounded).

## D) What violates the planning docs

- Database naming and fields diverge from ERD: planning references `Tournament.title`, JSONB `config`, while code uses `name` and lacks `config`.
- Missing Game `game_config` contradicts “PostgreSQL-first” JSONB strategy and GameConfigService expectations.
- Check-in windows should have explicit open and close offsets (planning); only a single `check_in_minutes_before` exists.
- Admin UX lacks the specified sections (Scheduling, Rules, Prizes, Eligibility, Payments, Custom fields, Notifications, Webhooks, Audit, Versioning, Match config) with rich grouping and dynamic forms.
- Staff filtering and permissions (organizers vs general users) not enforced in admin selection widgets.

## E) What violates Django best practices

- Admin referencing non-existent model fields (`game_config`) — must be synchronized with models or decoupled via custom forms.
- Admin list/search fields pointing to non-existent attributes (`tournament.title`) — should match model field names.
- String representations relying on non-existent fields (Bracket.__str__).
- Over-reliance on extension-based file validation without MIME checks.

## F) What must be redesigned completely

- Tournament Admin form grouping and sections: needs a full rework to align to planning’s organizer workflow (with fieldsets, inlines, actions, widgets).
- Game configuration pipeline: introduce `Game.game_config` JSONB with admin editor + GameConfigService validation.
- Staff/permission model for organizer selection and admin visibility scoping.
- Bracket/Match Admin references and display fields (use `Tournament.name`, ensure robust links and filters).

## G) What backend functionality is half-implemented

- Check-in service and views exist but rely on missing configuration fields; admin-side force-check-in actions are not present.
- Payment verification pipeline (admin actions exist) but lacks tighter validations and configurable rules per planning.
- Versioning surfaced only for TournamentVersion; service-level version snapshots for other entities not consistently applied.

## H) All admin UX problems

- Game Admin breaks due to `game_config` field missing.
- Tournament Admin organizer field not filtered to staff/organizers.
- Tournament Admin lacks rich text/WYSIWYG for `description` and `rules_text`.
- Admin groupings do not match planning (disparate models listed; no “Organizer Hub”).
- Match Admin shows broken tournament display due to `.title` misuse; filters and ordering likely error out.
- No JSON schema-assisted editors for JSONB fields (prize_distribution, lobby_info, etc.).

## I) All related model errors

- Game: Missing `game_config` JSONField.
- Tournament: Missing JSONB `config`; check-in close offset field missing; name vs title inconsistency with ERD.
- Bracket: `__str__` uses `tournament.title` instead of `tournament.name`.
- Registration: Missing uniqueness on `(tournament, team_id)` for team tournaments.
- Match: Admin references `tournament__title`; model exposes `name` — search/order problems.

## J) All broken relationships

- Admin-side references to Tournament.title effectively break MatchAdmin list/search and Bracket string representations.
- Potential duplicate team registrations due to missing uniqueness constraint for team_id per tournament.

## K) All incomplete services

- GameConfigService: No persistence target (Game.game_config).
- RegistrationService: Strong, but lacks hooks to enforce new check-in close window; also no organizer-role enforcement in admin.
- Check-in Service: Uses fallback defaults due to missing fields; admin force-check-in flow not wired.

## L) Issues in registration/payment/check-in/eligibility flows

- Eligibility checks do not enforce staff-only organizer selection in admin.
- Payment content-type validation incomplete; no anti-malware scanning hook (as per security planning).
- Check-in window uses a single offset; planning specifies open/close windows; no-shows logic not surfaced in admin as action.
- No staff-only admin actions to “verify all pending payments for tournament X” or report views per planning.

## M) Issues in bracket/match management backend logic

- Admin relies on `Tournament.title`; model uses `name` → broken admin list and search.
- No admin actions to regenerate bracket, finalize/lock, or export bracket in current non-legacy codepath (legacy backup contains patterns but not wired in current app).
- MatchService referenced but alignment with admin actions and permissions needs hardening per planning (state transitions, audit).

---

## Immediate Root Causes (Top Priority)

1) Game Admin crash: Admin expects `Game.game_config` but model lacks it. Also GameConfigService expects it. Root fix: add JSONField and migrations.
2) Tournament/Match/Bracket admin field mismatches: `title` vs `name`. Root fix: standardize on `name` (or migrate to `title`) and update all Admin usage.
3) Check-in configuration mismatch: add `check_in_closes_minutes_before` and admin UI for it; reflect in services.
4) Registration uniqueness for teams: add partial UniqueConstraint on `(tournament, team_id)` when team_id is not null.
5) Organizer filtering: restrict Tournament.organizer choices to staff or organizer role.

---

## Environment/Operational Gaps

- Missing data seeds/fixtures for `Game` leading to empty selectors in admin.
- Missing JSON editors and validation widgets for JSONB fields.
- Incomplete admin grouping and navigation for Organizer workflows.

---

## Conclusion

The backend and Django Admin require coordinated model corrections (JSONB fields, constraints, check-in windows), admin refactors (fieldsets, staff filtering, rich text, corrected references), and service alignment (GameConfigService, Check-in windows). The items above will be addressed in the Fix Plan (Part 2/5) and Admin Redesign Plan (Part 3/5), followed by implementation and hardening.


# PART 4/5 – Implementation Updates (Delta)

Scope: Apply targeted schema/admin fixes, remove legacy field usages causing runtime errors, and validate with smoke tests.

What changed (code-level):
- Tournament homepage context: Replaced legacy `settings__*` filters with `tournament_start`/`tournament_end` in `apps/common/context_homepage.py`. Fixed `game` access, counts by `game__slug`, and live/upcoming queries. Eliminates frequent FieldErrors in logs.
- Site UI integrations: Updated `apps/siteui/nav_context.py` and `apps/siteui/services.py` to prefer `tournament_start`/`tournament_end` and `registration_start`/`registration_end`; removed dependency on non-existent `settings` relation. Preserves defensive fallbacks.
- Admin consistency: Replaced `tournament.title` and `tournament__title` with `name`/`tournament__name` in:
	- `apps/tournaments/admin_result.py`
	- `apps/tournaments/admin_prize.py`
	- `apps/tournaments/admin_certificate.py`
	- `apps/tournaments/models/result.py` (`__str__`) now uses `tournament.name`.
- Tournament admin UX: Exposed `check_in_closes_minutes_before` in Features fieldset and surfaced the `config` JSONB in a new collapsed fieldset in `apps/tournaments/admin.py`.

Previously completed in this phase:
- Added `Game.game_config` (JSONField), `Tournament.config` (JSONField), and `Tournament.check_in_closes_minutes_before` (int). Fixed `Bracket.__str__` to use `tournament.name`.
- Restricted organizer queryset to staff in TournamentAdmin.
- Added partial unique constraint ensuring one team per tournament (excluding soft-deleted) in Registration.
- Generated migrations and pruned duplicate index/constraint ops to match live DB; applied successfully.
- Fixed CTA query error in `TournamentDetailView` by removing invalid `select_related('team')`.

Validation and results:
- Sprint 1 Smoke Tests: PASS
	- Command: `python manage.py test apps.tournaments.tests.test_sprint1_smoke -v 2`
- Top-level repository tests: Numerous pre-existing failures outside scope (profile/team UI expectations and URL names). Not regressions from the changes above. Proposed to handle under separate UI/teams test stabilization task.
- Observability: The repeated FieldError "Cannot resolve keyword 'settings' into field" no longer appears during smoke tests.

Risks and mitigations:
- Updated context/service logic assumes presence of `tournament_start`/`tournament_end`. These fields exist and are indexed; fallbacks remain in `siteui/services.py` for broader compatibility.
- Admin JSON field exposure (`config`) is intentionally minimal; richer JSON editor widgets can be added in Part 3/5 polish.

Next (towards Part 5/5 – Hardening Report):
- Broader admin UX polish (JSON editor widgets, WYSIWYG for description/rules), and organizer workflows per the redesign plan.
- Prepare final hardening summary with diffs, migration status, and operator notes.
