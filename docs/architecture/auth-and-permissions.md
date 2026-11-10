# Authentication and permissions

Purpose: how users authenticate, how sessions and tokens are used, and where authorization is enforced. Security policy and incident notes: [security](../operations/security.md).

## Authentication flows

| Flow | Entry points (`apps/accounts/urls.py`, mounted at `account/`) | Behaviour |
|---|---|---|
| Signup + email OTP | `signup/`, `verify/otp/`, `verify/`, `verify/resend/` | The form creates a `PendingSignup` (password stored hashed) and emails a 6-digit `EmailOTP` (5 attempts, rate-limited resend, expiry). The `User` row is created only after a correct code; too many wrong codes remove the pending signup. Recovery mode: with no pending session the page asks for the email again |
| Login / logout | `login/`, `logout/` | `DCLoginView` (username **or** email via `EmailOrUsernameBackend`), 10 attempts per 60 s per IP, generic error text. `next` is validated by `LoginView.get_redirect_url` (same host only; external, `//host` and `javascript:` are ignored). `redirect_authenticated_user` is on |
| Password reset | `password_reset/`, `reset/<uid>/<token>/`, `reset/done/` | Always redirects to the "sent" page whether or not the account exists; 5 requests per 60 s per IP; email failures are logged, not shown; tokens are Django's single-use tokens |
| Password change | `password_change/` (login required) | Django `PasswordChangeView`; validators from `AUTH_PASSWORD_VALIDATORS` (similarity, minimum length 8, common, numeric) |
| Google | `google/login/`, `google/callback/` | Authorization-code flow, scopes `openid email profile`; state is verified; the redirect URI is `SITE_URL` + the callback path. Provider configuration in production is unverified in this repository |
| Discord | `discord/link`, `discord/callback/`, `discord/unlink/` | Account linking only |
| Account deletion | `me/settings/account-deletion/{schedule,cancel,status}/` | Scheduled deletion; `BlockScheduledDeletionMiddleware` blocks sign-in while pending; `process_account_deletions` command finalises |
| API / WebSocket | `api/token/`, `api/token/refresh/`, `api/token/verify/` | SimpleJWT. DRF default authentication: JWT, then session (and HTTP Basic only when `DEBUG`) |

`User.is_verified` records email verification; `createsuperuser` users are verified. Allauth is optional (`ENABLE_ALLAUTH`); legacy `accounts/login|signup|logout` URLs redirect to `account/...`.

## Sessions and CSRF

Database-backed Django sessions, `CsrfViewMiddleware` on all browser POSTs (APIs using session auth need the CSRF token; JWT clients do not). Secure cookies and HSTS in production. Sessions cannot be shared across different registrable domains (relevant to a domain move, see [deployment](../operations/deployment.md#domain-and-seo)).

## Authorization

Authentication proves who you are; each view or service decides what you may do. Hiding a link in a template is never authorization.

| Area | Where enforced | Rule |
|---|---|---|
| Staff / superuser | Django admin, TOC, economy console | `is_staff`/`is_superuser` |
| Tournament organizer console (TOC) | `TOCBaseView.check_toc_permission` in `apps/tournaments/api/toc/base.py` | superuser/staff, the tournament organizer, or an active `TournamentStaffAssignment`; fine-grained roles in `toc/rbac.py` and `rbac_service.py`; every TOC call is audited by `TOCAuditMiddleware` |
| Tournament REST API | `apps/tournaments/api/permissions.py` | `IsOrganizerOrReadOnly`, `IsOrganizerOrAdmin`, `IsOwnerOrOrganizer`, `IsPlayerOrSpectator`, `IsMatchParticipant`; default DRF permission is `IsAuthenticatedOrReadOnly` |
| Match results | `apps/tournaments/services/match_authority.py` | who may submit, confirm or override a score ([tournaments](tournaments.md)) |
| Teams and organizations | `TeamMembership.Role` (OWNER, MANAGER, COACH, PLAYER, SUBSTITUTE, ANALYST, SCOUT; legacy "captain" maps to OWNER) and helper methods such as `can_manage_roster`, `can_check_in_tournaments` in `apps/organizations/models/membership.py` | role checks in services and views; manager-only controls are not rendered to visitors |
| Profiles | `apps/user_profile` privacy settings | private accounts hide content from non-followers; follow requests for private accounts |
| Wallet | `apps/economy` views | login required; wallet PIN for withdrawals; staff approval for top-ups, withdrawals, prize claims |
| Moderation | `apps/moderation`, `MODERATION_ENFORCEMENT_*` flags | sanctions can block actions (purchases, WebSocket joins) when enforcement flags are on |

## Rate limits

* Views: cache-based `_is_rate_limited` in `apps/accounts/views.py` (login, password reset, OTP resend).
* DRF: `AnonRateThrottle` (`THROTTLE_ANON_RATE`, default 100/hour), `UserRateThrottle` (`THROTTLE_USER_RATE`, 1000/hour) and scoped throttles (`THROTTLE_DISCOVERY_READ_RATE`, `THROTTLE_REGISTRATION_WRITE_RATE`, `THROTTLE_LOGIN_RATE`, `THROTTLE_PASSWORD_RESET_RATE`, ...). All configurable by environment.
* WebSockets: see [realtime](realtime-and-notifications.md#websockets-channels) (limiter inactive unless configured).
