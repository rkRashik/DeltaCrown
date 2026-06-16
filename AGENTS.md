# DeltaCrown Agent Instructions

## Settings Redesign Guardrail

The DeltaCrown settings page at `/me/settings/` is functionally fragile. Before any future visual redesign or refactor of this page, read:

- `Documents/DELTACROWN/SETTINGS_REDESIGN_SPEC.md`

The current settings implementation is centered on:

- Template: `templates/user_profile/profile/settings_control_deck.html`
- Active partial: `templates/user_profile/profile/settings/partials/_game_passports.html`
- View: `apps/user_profile/views/public_profile_views.py`, `profile_settings_view`
- URL names: `user_profile:profile_settings`, `user_profile:settings`, `user_profile:profile_settings_v2`

Do not redesign, rename, extract, delete, or reorganize settings behavior unless the task explicitly asks for that phase.

## Required Visual Direction

Future settings work must move away from the current neon "Control Deck" treatment. The target is a premium, quiet, modern dark settings surface:

- Dark charcoal or near-black page background
- Slightly lighter surfaces for panels and rows
- Thin separators instead of heavy cards
- Low-contrast borders
- Calm spacing and readable forms
- Clean settings rows
- Desktop sidebar navigation
- Mobile-first responsive layout
- Subtle brand accents only
- Premium SaaS/product quality, not a generic AI dashboard

DeltaCrown brand accents:

- Azure: `#0A84FF`
- Royal Violet: `#6849E5`
- Gold: `#CFA75A`

Use accents sparingly for active navigation, primary buttons, focus rings, important status badges, and small section markers.

Avoid:

- Excessive glassmorphism
- Bright gradients
- Strong neon glow
- Over-colorful cards
- Decorative gaming clutter
- All-uppercase labels everywhere
- Confusing labels such as "Control Deck", "Identity Protocol", and "Privacy & Vis."
- Fake settings that are not supported by the backend
- Backend contract changes during visual redesign

## Settings Safety Rules

Preserve these contracts unless a later task explicitly authorizes a migration and updates the matching JavaScript and backend paths:

- Every existing `tab-*` id
- Every existing form id
- Every existing field `name`
- Every hidden `settings_tab` value
- CSRF handling
- All `{% url %}` template tags
- All AJAX endpoint behavior
- All Django context variables
- All auth and permission behavior
- Passport modal ids and scripts

Do not blindly extract inline JavaScript from the settings template. It is coupled to Django template tags, CSRF behavior, DOM ids, and runtime context.

Do not rewrite backend logic as part of a visual redesign. Files such as views, URLs, forms, APIs, model methods, and permission logic are out of scope unless the user explicitly requests a backend phase.

Do not run tests against a production database.

## Proposed Settings Information Architecture

Future redesign work should organize settings around these top-level sections:

1. Profile
2. Contact & Connections
3. Competitive Profile
4. Privacy & Safety
5. Notifications
6. Platform Preferences
7. Assets & Wallet
8. Danger Zone

Danger Zone must remain visually separated and should contain account deletion only.

## Known Issues To Account For

Future work must account for these existing structural risks:

- Header Save does not support many saveable tabs.
- `tab-matchmaking` is stale or unreachable and references missing form behavior.
- `tab-billing` exists but has no navigation item.
- Mobile navigation misses Notifications, Community, Danger Zone, Billing/Wallet, and Matchmaking.
- Privacy fields exist that may not be saved by the current payload or API allowlist.
- Multiple `DOMContentLoaded` blocks and duplicate handlers increase fragility.
- Several forms depend entirely on JavaScript.
- There may be an extra closing `</div>` around the matchmaking section.
- The current UI is over-decorated with heavy glass, neon effects, radial backgrounds, mixed labels, and too many accent colors.

## Safe Editing Scope

For a visual-only settings redesign phase, prefer scoped template and CSS changes while preserving behavior. Do not edit these unless explicitly authorized:

- `apps/user_profile/urls.py`
- `apps/user_profile/views/public_profile_views.py`
- Settings API view modules
- Forms and models
- `static/user_profile/js/oauth_linked_accounts.js`
- Existing AJAX contracts
- Database migrations

Any responsive QA must check desktop, tablet, and mobile widths for no horizontal overflow, complete navigation access, readable forms, working modals, and unchanged save behavior.
