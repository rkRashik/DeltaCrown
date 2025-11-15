# Frontend Inventory - DeltaCrown

**Date**: November 14, 2025  
**Purpose**: Complete inventory of existing frontend implementation  
**Status**: Documentation only - no code changes

---

## 📁 1. Frontend Folders & Files

### 1.1 Templates (`templates/`)

**Path**: `g:\My Projects\WORK\DeltaCrown\templates\`

**Description**: Django templates containing all HTML pages and UI components. Primary frontend rendering technology.

**Key Subdirectories**:

- **`templates/account/`** - Authentication pages (login, signup, password reset, email verification)
- **`templates/teams/`** - Team management pages (create, detail, dashboard, roster, settings)
- **`templates/tournaments/`** - Tournament pages (in `legacy_backup/` - archived old implementation)
- **`templates/spectator/`** - Public spectator views for tournaments and matches
- **`templates/dashboard/`** - User dashboard pages (my matches, tournament overview)
- **`templates/user_profile/`** - User profile pages (view, edit, my tournaments)
- **`templates/ecommerce/`** - Store pages (product list, detail, cart, checkout)
- **`templates/economy/`** - Wallet and economy pages
- **`templates/notifications/`** - Notification list and email templates
- **`templates/support/`** - FAQ, contact forms
- **`templates/search/`** - Search results page
- **`templates/players/`** - Player profile pages
- **`templates/partials/`** - Shared UI fragments (navigation, footer, toasts, SEO meta)
- **`templates/components/`** - Reusable UI components (buttons, cards, modals, forms)
- **`templates/sections/`** - Page sections (hero, stats, timeline, SVG graphics)
- **`templates/pages/`** - Static pages (about, community)
- **`templates/legal/`** - Terms and privacy pages

**Base Templates**:
- `base.html` - Main layout with Tailwind CDN, navigation, footer
- `base_no_footer.html` - Layout without footer

**Homepage Templates**:
- `home_modern.html` - Modern/current homepage design
- `home_cyberpunk.html` - Alternative cyberpunk-themed homepage
- `Arena.html` - Arena/tournament hub page

---

### 1.2 Static Assets (`static/`)

**Path**: `g:\My Projects\WORK\DeltaCrown\static\`

**Description**: All static files including JavaScript, CSS, images, and fonts.

**Key Subdirectories**:

#### **`static/siteui/`** - Main site UI assets

**CSS Files** (`static/siteui/css/`):
- `base.css` - Base styles and utilities aligned with Tailwind
- `tokens.css` - Design tokens (colors, spacing, typography, shadows)
- `components.css` - Reusable component styles
- `effects.css` - Visual effects (animations, transitions)
- `navigation-unified.css` - Unified navigation system styles
- `footer.css` - Footer styles
- `auth.css` - Authentication page styles
- `home.css`, `home-premium.css` - Homepage styles
- `community.css`, `community-social.css` - Community page styles
- `tournaments.css`, `tournaments-hub.css`, `tournaments-detail-v8.css` - Tournament styles
- `teams-*.css` - Team page styles (list, detail, dashboard, responsive)
- `user-profile.css` - Profile page styles
- `mobile-*.css` - Mobile-specific styles (nav, bottom nav, enhancements)
- `responsive.css` - General responsive utilities

**JavaScript Files** (`static/siteui/js/`):
- `base.js` - Base JavaScript (empty/minimal)
- `theme.js` - Theme switching (dark/light mode)
- `components.js` - Generic component behaviors (overlays, collapses)
- `auth.js` - Authentication UI logic (password toggle)
- `notifications.js` - Toast notification system
- `motion.js` - Animation utilities
- `micro.js` - Micro-interactions
- `nav.js`, `navigation-unified.js` - Navigation behaviors
- `mobile-nav.js`, `mobile-nav-v2.js`, `mobile-nav-v3.js` - Mobile navigation variants
- `teams.js`, `teams-*.js` - Team page behaviors
- `tournaments.js`, `tournaments-list.js`, `tournaments-detail-v8.js` - Tournament behaviors
- `home.js`, `home-premium.js` - Homepage interactions
- `community.js`, `community-social.js`, `community-mobile.js` - Community features
- `profile.js`, `user-profile.js` - Profile page interactions
- `forms.js`, `reg_wizard.js` - Form handling and registration wizard
- `filter-orb.js` - Filter UI component
- `tailwind-config.js` - Tailwind CSS configuration

#### **`static/teams/`** - Team-specific assets

**CSS Files** (`static/teams/css/`):
- `team-dashboard.css` - Team dashboard styles
- `team-list-modern-redesign.css` - Modern team list design
- `team-list-premium-complete.css` - Premium team list styles
- `team-create-fixed.css` - Team creation form styles

**JavaScript Files** (`static/teams/js/`):
- `team-list-vlr-style.js` - VLR-style team list
- `team-list-premium.js` - Premium team list behaviors
- `team-create-enhanced.js` - Enhanced team creation with validation

#### **`static/js/`** - General JavaScript

**Root JS Files**:
- `spectator_ws.js` - WebSocket client for real-time spectator updates
- `dynamic-registration.js` - Dynamic tournament registration flow
- `registration-v2.js` - Registration form v2
- `homepage-*.js` - Homepage variants (modern, cyberpunk, enhanced, animations)
- `tournament-*.js` - Tournament-related scripts
- `countdown-timer.js` - Countdown timer component
- `game-id-prompt.js` - Game ID collection prompt
- `sponsorship.js` - Sponsorship features

**Team Detail Scripts** (`static/js/team-detail/`):
- `api-client.js` - API communication layer
- `app-init.js` - App initialization
- `main.js` - Main team detail logic
- `chat-poller.js` - Team chat polling
- `player-profile-modal.js`, `player-stats-modal.js` - Player modals
- `dashboard-actions.js` - Dashboard action handlers
- `form-validator.js` - Form validation
- `skeleton-loader.js` - Loading skeletons
- `mobile-optimizer.js` - Mobile optimizations
- `accessibility.js` - A11y enhancements
- `keyboard-shortcuts.js` - Keyboard navigation
- `clipboard.js` - Copy-to-clipboard utilities
- `logger.js`, `telemetry.js` - Logging and analytics
- `toast.js` - Toast notifications
- `theme-manager.js` - Theme management
- `meta-tags.js` - Dynamic meta tag updates
- `image-optimizer.js` - Image optimization

**Team Dashboard Scripts** (`static/js/team-dashboard/`):
- `dashboard-manager.js` - Dashboard state management
- `ranking-history.js` - Ranking history visualization

**Team Settings Scripts** (`static/js/team-settings/`):
- `privacy-settings.js` - Privacy settings UI
- `member-management.js` - Member management

**Teams Scripts** (`static/js/teams/`):
- `hub-v2.js` - Team hub page

#### **`static/css/`** - General CSS

**Root CSS Files**:
- `homepage-*.css` - Homepage variants (modern, cyberpunk, premium, improvements)
- `dynamic-registration.css`, `registration-v2.css`, `modern-registration.css` - Registration styles
- `game-cards-*.css` - Game card styles (modern, v3, premium)
- `game-id-prompt.css` - Game ID prompt styles
- `footer-cyberpunk.css` - Cyberpunk footer

**Team Detail CSS** (`static/css/team-detail/`):
- `team-detail-new.css` - New team detail layout
- `hero-*.css` - Hero section templates and variants
- `tabs.css`, `tabs-enhanced.css` - Tab system styles
- `tab-content.css` - Tab content styles
- `components.css` - Team detail components
- `roster-*.css` - Roster display styles
- `sidebar.css` - Sidebar styles
- `animations.css` - Animation definitions
- `loading-states.css` - Loading state styles
- `skeleton.css` - Skeleton loader styles
- `toast.css` - Toast notification styles
- `player-modal-*.css`, `player-stats-modal.css` - Player modal styles
- `dashboard-modals.css` - Dashboard modal styles
- `game-themes.css` - Game-specific themes
- `overview-enhanced.css` - Enhanced overview section

**Team Dashboard CSS** (`static/css/team-dashboard/`):
- `modern-dashboard.css` - Modern dashboard layout

**Team Settings CSS** (`static/css/team-settings/`):
- `privacy-settings.css` - Privacy settings styles
- `member-management.css` - Member management styles

**Teams CSS** (`static/css/teams/`):
- `hub-v2.css` - Team hub styles

#### **`static/ecommerce/`** - E-commerce assets

**CSS Files**:
- `store.css` - Store homepage styles
- `store-bd.css` - Bangladesh-specific store styles
- `product-list.css` - Product list styles
- `ecommerce-modern.css` - Modern e-commerce design

**JavaScript Files**:
- `store.js` - Store page logic
- `product-list.js` - Product list behaviors

#### **`static/admin/`** - Django admin customizations

**CSS Files**:
- `ckeditor5_fix.css` - CKEditor fixes
- `team_points_widget.css` - Team points widget styles
- `prize_distribution_widget.css` - Prize distribution widget styles

**JavaScript Files**:
- `tournament_admin.js` - Tournament admin enhancements
- `team_points_widget.js` - Team points widget logic
- `prize_distribution_widget.js` - Prize distribution logic
- `points-calculator-test.js` - Points calculator testing

#### **`static/img/`** - Images and graphics

**Subdirectories**:
- `favicon/` - Favicon files (multiple sizes, webmanifest)
- `deltaCrown_logos/` - Brand logos (including `logo.svg`)
- `games/` - Game-related images
- `game_cards/` - Game card graphics
- `game_logos/` - Game logo assets
- `user_avatar/` - Default user avatars

**Root Files**:
- `deltacrown-logo.svg` - Main logo SVG

#### **`static/fonts/`** - Web fonts (if any)

#### **`static/logos/`** - Additional logos

---

### 1.3 Legacy Backup (`legacy_backup/`)

**Path**: `g:\My Projects\WORK\DeltaCrown\legacy_backup\`

**Description**: Archived old implementation of tournaments module with extensive templates.

**Key Contents**:
- `legacy_backup/templates/tournaments/tournaments/` - Old tournament templates (bracket, registration, standings, dashboard, war-room, etc.)
- Contains 27+ archived tournament HTML files
- **Status**: Not actively used, kept for reference

---

## 📄 2. Existing Screens/Pages

### 2.1 Authentication Pages

**Location**: `templates/account/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Login** | `account/login.html` | `/account/login/` | User login page with email/username and password fields |
| **Signup** | `account/signup.html` | `/account/signup/` | User registration with email verification |
| **Logout** | `account/logout.html` | `/account/logout/` | Logout confirmation page |
| **Password Reset** | `account/password_reset.html` | `/account/password/reset/` | Request password reset email |
| **Password Reset Form** | `account/password_reset_form.html` | `/account/password/reset/key/...` | Enter new password |
| **Password Reset Done** | `account/password_reset_done.html` | `/account/password/reset/done/` | Password reset confirmation |
| **Email Verification** | `account/verify_email.html` | `/account/verify-email/` | Email verification page |
| **Verification Sent** | `account/verification_sent.html` | `/account/email-verification-sent/` | Email sent confirmation |
| **Social Signup** | `socialaccount/signup.html` | `/accounts/social/signup/` | Social auth signup flow |

---

### 2.2 Homepage & Landing Pages

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Homepage (Modern)** | `home_modern.html` | `/` | Main landing page with hero section, featured tournaments, stats, game cards |
| **Homepage (Cyberpunk)** | `home_cyberpunk.html` | `/` (alternate) | Alternative cyberpunk-themed homepage design |
| **About** | `about.html` or `pages/about.html` | `/about/` | About DeltaCrown page |
| **Community** | `community.html` or `pages/community.html` | `/community/` | Community hub page |
| **Arena** | `Arena.html` | `/arena/` (if routed) | Tournament arena/hub page |
| **UI Showcase** | `ui_showcase.html` | `/ui-showcase/` (if routed) | Component showcase for testing |

---

### 2.3 User Profile Pages

**Location**: `templates/user_profile/` and `templates/users/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **My Profile** | `user_profile/profile.html` or `profile_modern.html` | `/profile/` | User's own profile view with stats and recent activity |
| **Edit Profile** | `users/profile_edit.html` or `profile_edit_modern.html` | `/profile/edit/` | Edit profile form (bio, avatar, social links) |
| **Public Profile** | `users/public_profile.html` or `public_profile_modern.html` | `/users/<username>/` | Public view of another user's profile |
| **My Tournaments** | `user_profile/my_tournaments.html` | `/profile/my-tournaments/` | List of tournaments user is registered in |
| **Profile Index** | `profile/index.html` | `/profile/` (alternate) | Alternative profile layout |

---

### 2.4 Team Pages

**Location**: `templates/teams/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Team List** | `teams/list.html` | `/teams/` | Browse all teams with filters (game, region, rank) |
| **Team Hub** | `teams/hub.html` | `/teams/hub/` | Team discovery hub with featured teams |
| **Team Create** | `teams/team_create.html` | `/teams/create/` | Create new team form with game selection and roster |
| **Team Detail** | `teams/detail.html` or `team_detail_new.html` | `/teams/<slug>/` | Team profile with overview, roster, matches, stats tabs |
| **Team Dashboard** | `teams/team_dashboard.html` or `dashboard_modern.html` | `/teams/<slug>/dashboard/` | Team management dashboard (captain view) |
| **Team Settings** | `teams/team_settings_modern.html` or `settings_*.html` | `/teams/<slug>/settings/` | Team settings (name, logo, privacy, members) |
| **Team Manage** | `teams/manage.html` or `team_manage.html` | `/teams/<slug>/manage/` | Manage team members and invites |
| **Invite Member** | `teams/invite_member.html` | `/teams/<slug>/invite/` | Send team invitation to user |
| **Accept Invite** | `teams/accept_invite.html` | `/teams/invite/<token>/` | Accept team invitation page |
| **My Invites** | `teams/my_invites.html` | `/teams/invites/` | View all pending invites |
| **Confirm Leave** | `teams/confirm_leave.html` | `/teams/<slug>/leave/` | Confirm leaving team |
| **Transfer Captain** | `teams/transfer_captain.html` | `/teams/<slug>/transfer-captain/` | Transfer team captain role |
| **Team Match Detail** | `teams/match_detail.html` | `/teams/<slug>/matches/<id>/` | Detailed match view for team |
| **Discussion Board** | `teams/discussion_board.html` | `/teams/<slug>/discussion/` | Team discussion board |
| **Discussion Post** | `teams/discussion_post_detail.html` | `/teams/<slug>/discussion/<id>/` | View discussion post |
| **Leaderboard** | `teams/leaderboard.html` or `ranking_leaderboard.html` | `/teams/leaderboard/` | Team rankings leaderboard |
| **Team Analytics** | `teams/analytics_dashboard.html` | `/teams/<slug>/analytics/` | Team performance analytics |
| **Player Analytics** | `teams/player_analytics.html` | `/teams/<slug>/players/<id>/analytics/` | Individual player stats |
| **Tournament History** | `teams/tournament_history.html` | `/teams/<slug>/tournaments/` | Team's tournament history |
| **Team Comparison** | `teams/team_comparison.html` | `/teams/compare/` | Compare two teams side-by-side |
| **Merchandise** | `teams/merchandise.html` | `/teams/<slug>/merch/` | Team merchandise store |
| **Sponsors** | `teams/sponsors.html` | `/teams/<slug>/sponsors/` | Team sponsor page |
| **Presets List** | `teams/presets_list.html` | `/teams/presets/` | Game-specific team presets (Valorant, eFootball) |
| **Collect Game ID** | `teams/collect_game_id.html` | `/teams/<slug>/collect-game-id/` | Collect player in-game IDs |

---

### 2.5 Tournament/Spectator Pages

**Location**: `templates/spectator/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Tournament List** | `spectator/tournament_list.html` | `/tournaments/` or `/spectator/tournaments/` | Browse all public tournaments |
| **Tournament Detail** | `spectator/tournament_detail.html` | `/spectator/tournaments/<id>/` | Public view of tournament with matches, leaderboard, bracket |
| **Match Detail** | `spectator/match_detail.html` | `/spectator/matches/<id>/` | Public match detail with scores and timeline |

**Partials** (HTMX fragments):
- `spectator/_leaderboard_table.html` - Auto-refreshing leaderboard
- `spectator/_match_list.html` - Auto-refreshing match list
- `spectator/_scoreboard.html` - Match scoreboard

---

### 2.6 Dashboard Pages

**Location**: `templates/dashboard/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Dashboard Index** | `dashboard/index.html` | `/dashboard/` | User dashboard overview with tournaments and notifications |
| **My Matches** | `dashboard/my_matches.html` or `matches.html` | `/dashboard/matches/` | User's upcoming and past matches |

---

### 2.7 E-commerce Pages

**Location**: `templates/ecommerce/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Store Home** | `ecommerce/store_home.html` | `/store/` | E-commerce store homepage |
| **Product List** | `ecommerce/product_list.html` | `/store/products/` | Browse products with filters |
| **Product Detail** | `ecommerce/product_detail.html` | `/store/products/<slug>/` | Product detail page with images and purchase option |
| **Category Detail** | `ecommerce/category_detail.html` | `/store/categories/<slug>/` | Products in specific category |
| **Cart** | `ecommerce/cart.html` | `/store/cart/` | Shopping cart page |
| **Checkout** | `ecommerce/checkout.html` | `/store/checkout/` | Checkout and payment page |

**Partials**:
- `ecommerce/partials/bd_payment_methods.html` - Bangladesh payment methods

---

### 2.8 Economy/Wallet Pages

**Location**: `templates/economy/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Wallet** | `economy/wallet.html` | `/wallet/` or `/economy/wallet/` | User wallet with balance, transactions, and coin management |

---

### 2.9 Notifications Pages

**Location**: `templates/notifications/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Notification List** | `notifications/list.html` | `/notifications/` | List of user notifications (unread/read) |

**Email Templates**:
- `notifications/email/single_notification.html` - Single notification email
- `notifications/email/daily_digest.html` - Daily digest email

---

### 2.10 Support Pages

**Location**: `templates/support/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Contact** | `support/contact.html` | `/support/contact/` | Contact form |
| **Contact Success** | `support/contact_success.html` | `/support/contact/success/` | Form submission success |
| **Contact Error** | `support/contact_error.html` | `/support/contact/error/` | Form submission error |
| **FAQ** | `support/faq.html` | `/support/faq/` | Frequently asked questions |

---

### 2.11 Search Pages

**Location**: `templates/search/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Search Results** | `search/index.html` | `/search/` | Global search results for teams, tournaments, users |

---

### 2.12 Player Pages

**Location**: `templates/players/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Player Detail** | `players/detail.html` | `/players/<id>/` | Public player profile page |

---

### 2.13 Error Pages

**Location**: `templates/` (root)

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **403 Forbidden** | `403.html` | (error) | Access denied page |
| **404 Not Found** | `404.html` | (error) | Page not found |
| **500 Server Error** | `500.html` | (error) | Server error page |

---

### 2.14 Legal Pages

**Location**: `templates/legal/`

| Page | File Path | URL | Description |
|------|-----------|-----|-------------|
| **Terms of Service** | `legal/terms.html` | `/legal/terms/` | Terms and conditions |
| **Privacy Policy** | `legal/privacy.html` | `/legal/privacy/` | Privacy policy |

---

## 🧩 3. Existing Layout & Navigation

### 3.1 Base Layouts

**Primary Layout**: `templates/base.html`

**Structure**:
```django-html
<!doctype html>
<html lang="en" data-theme="system">
  <head>
    <!-- Tailwind CDN -->
    <!-- Design tokens, base CSS, components, effects, navigation -->
    <!-- Font Awesome icons, AOS animations -->
    {% block extra_css %}{% endblock %}
  </head>
  <body>
    <!-- Skip link for accessibility -->
    {% include "partials/navigation_unified.html" %}
    
    <main id="main">
      {% block content %}{% endblock %}
    </main>
    
    {% block footer %}
      {% if request.path == '/' %}
        {% include "partials/footer_industry.html" %}
      {% endif %}
    {% endblock %}
    
    {% include "partials/toasts.html" %}
    
    <!-- Global JS: theme, notifications, components, motion, etc. -->
    {% block extra_js %}{% endblock %}
  </body>
</html>
```

**Key Features**:
- **Tailwind CDN**: Loaded via `<script src="https://cdn.tailwindcss.com">`
- **Custom Tailwind Config**: `static/siteui/js/tailwind-config.js`
- **Design Tokens**: `static/siteui/css/tokens.css` (colors, spacing, shadows)
- **Theme System**: `data-theme="system"` with dark/light mode support
- **Global JS**: Theme toggle, notifications, components, motion utilities
- **SEO Meta**: Included via `partials/seo_meta.html`
- **Toast Notifications**: Included via `partials/toasts.html`

**Alternative Layout**: `templates/base_no_footer.html`
- Same structure but without footer block

**Spectator Layout**: `templates/spectator/base.html`
- Specialized layout for spectator pages with inline Tailwind config

---

### 3.2 Navigation Components

#### **Unified Navigation**: `templates/partials/navigation_unified.html`

**Features**:
- Top navigation bar with logo, main menu, user profile dropdown
- Responsive design with mobile hamburger menu
- Authentication-aware (shows login/signup or profile menu)
- Notification bell with unread count
- Theme toggle button (dark/light mode)

**CSS**: `static/siteui/css/navigation-unified.css`  
**JS**: `static/siteui/js/navigation-unified.js`

**Main Navigation Items**:
- Home
- Tournaments
- Teams
- Store
- Community
- Support

#### **Mobile Navigation Variants**:

1. **Mobile Nav V1**: `partials/mobile_nav.html` + `static/siteui/css/mobile-nav.css` + `static/siteui/js/mobile-nav.js`
2. **Mobile Nav V2**: `partials/mobile_nav_v2.html` + `static/siteui/css/mobile-nav-v2.css` + `static/siteui/js/mobile-nav-v2.js`
3. **Mobile Nav V3**: `partials/mobile_nav_v3.html` + `static/siteui/css/mobile-nav-v3.css` + `static/siteui/js/mobile-nav-v3.js`
4. **Mobile Bottom Nav**: `partials/mobile_bottom_nav.html` + `static/siteui/css/mobile-bottom-nav.css` + `static/siteui/js/mobile-bottom-nav.js`

**Status**: Multiple navigation variants exist (legacy), currently consolidated into `navigation_unified.html`

#### **Main Nav**: `partials/main_nav.html`
- Alternative main navigation component
- **CSS**: `static/siteui/css/main-nav.css`
- **JS**: `static/siteui/js/main-nav.js`

#### **Legacy Nav**: `partials/nav.html`
- Older navigation component
- **CSS**: `static/siteui/css/nav.css`
- **JS**: `static/siteui/js/nav.js`

---

### 3.3 Footer

**Primary Footer**: `templates/partials/footer_industry.html`

**Features**:
- Displayed only on homepage (`{% if request.path == '/' %}`)
- Company info, social links, newsletter signup
- Links to legal pages (Terms, Privacy)
- Game logos and partner badges

**CSS**: `static/siteui/css/footer.css`

**Alternative Footer**: `static/css/footer-cyberpunk.css` (for cyberpunk theme)

---

### 3.4 Shared UI Partials

**Location**: `templates/partials/`

| Component | File | Description |
|-----------|------|-------------|
| **Toasts** | `toasts.html` | Toast notification container |
| **SEO Meta** | `seo_meta.html` | SEO meta tags (Open Graph, Twitter Card) |
| **Breadcrumbs** | `_breadcrumbs.html` | Breadcrumb navigation |

**Backup/Unused**:
- `partials/backup_unused/` - Archived old partials (theme toggle, mobile nav, messages, JSON-LD)

---

### 3.5 Reusable Components

**Location**: `templates/components/`

| Component | File | Description |
|-----------|------|-------------|
| **Button** | `button.html` | Reusable button component with variants (primary, outline, ghost) |
| **Card** | `card.html` | Card container component |
| **Modal** | `modal.html` | Modal/dialog component |
| **Drawer** | `drawer.html` | Slide-out drawer component |
| **Tooltip** | `tooltip.html` | Tooltip component |
| **Form Field** | `form_field.html` | Form input wrapper with label and error display |
| **Checkbox** | `checkbox.html` | Styled checkbox component |
| **Radio** | `radio.html` | Styled radio button component |
| **Select** | `select.html` | Styled select dropdown component |
| **Sidebar** | `sidebar.html` | Sidebar component |
| **Game Badge** | `game_badge.html` | Game badge/pill component |
| **Empty State** | `empty.html` | Empty state placeholder |
| **Breadcrumbs** | `breadcrumbs.html` | Breadcrumb navigation |

**Underscore-prefixed variants** (alternative implementations):
- `_button.html`, `_modal.html`, `_tooltip.html`, `_toast.html`, `_share.html`, `_form_fields.html`, `_breadcrumbs.html`

---

### 3.6 Section Components

**Location**: `templates/sections/`

**Purpose**: Reusable page sections and SVG graphics

| Component | File | Description |
|-----------|------|-------------|
| **Hero** | `hero.html` | Hero section template |
| **Stats** | `stats.html` | Statistics display section |
| **Timeline** | `timeline.html` | Timeline/history section |
| **Spotlight** | `spotlight.html` | Featured content spotlight |
| **Pillars** | `pillars.html` | Feature pillars section |
| **Split CTA** | `split_cta.html` | Split call-to-action section |
| **SVG Graphics** | `svg_*.html` | SVG illustrations (rank, profile, wallet, shield, bracket, flag) |

---

### 3.7 Navigation Flow

**How Navigation Currently Works**:

1. **Top Navigation Bar**:
   - Always visible via `{% include "partials/navigation_unified.html" %}`
   - Fixed position at top of viewport
   - Collapses to hamburger menu on mobile

2. **Authentication State**:
   - **Not logged in**: Shows "Login" and "Sign Up" buttons
   - **Logged in**: Shows user avatar, notification bell, profile dropdown

3. **Profile Dropdown** (logged in users):
   - My Profile
   - My Teams
   - My Tournaments
   - Wallet
   - Settings
   - Logout

4. **Mobile Navigation**:
   - Hamburger icon opens slide-out drawer
   - Main menu items + authentication actions
   - Bottom navigation bar for quick access (optional variant)

5. **Breadcrumbs**:
   - Some pages include breadcrumb navigation
   - Not consistently implemented across all pages

6. **Team-Specific Navigation**:
   - Team pages have secondary tab navigation (Overview, Roster, Matches, Stats)
   - Implemented in `templates/teams/partials/team_nav.html`

7. **Footer Navigation**:
   - Only shown on homepage
   - Links to About, Community, Legal pages, Social media

---

## 📊 4. Technology Stack Summary

| Technology | Usage | Implementation |
|------------|-------|----------------|
| **Django Templates** | Primary | All HTML rendering via Django template engine |
| **Tailwind CSS** | Styling | Loaded via CDN + custom config (`tailwind-config.js`) |
| **Custom CSS** | Design System | `tokens.css`, `base.css`, `components.css`, `effects.css` |
| **Vanilla JavaScript** | Interactivity | No framework - plain JS with ES6+ features |
| **HTMX** | Partial Updates | Used in spectator pages for auto-refresh (`hx-get`, `hx-trigger`) |
| **WebSocket** | Real-time | `spectator_ws.js` for live tournament updates |
| **Fetch API** | HTTP Requests | API communication (no axios, no jQuery) |
| **Font Awesome** | Icons | Loaded via CDN (v6.4.0) |
| **AOS (Animate On Scroll)** | Animations | Loaded via CDN (v2.3.1) |
| **Google Fonts** | Typography | Inter + Space Grotesk fonts |

**No React, Vue, or Angular** - Pure Django templates with progressive enhancement via JavaScript.

---

## 🚨 5. Key Observations

### 5.1 Strengths

✅ **Comprehensive page coverage** - Most user flows have templates  
✅ **Component-based structure** - Reusable components in `templates/components/`  
✅ **Design token system** - Centralized in `tokens.css`  
✅ **Mobile-responsive** - Multiple mobile navigation variants  
✅ **Theme support** - Dark/light mode with `data-theme` attribute  
✅ **Real-time features** - WebSocket + HTMX for live updates  
✅ **Tailwind integration** - CDN with custom config  
✅ **Accessibility features** - Skip links, ARIA attributes, screen reader support  

### 5.2 Issues/Gaps

⚠️ **Multiple navigation variants** - `nav.html`, `main_nav.html`, `mobile_nav_v1/v2/v3` - consolidation needed  
⚠️ **Duplicate components** - Underscore-prefixed vs non-prefixed versions (`button.html` vs `_button.html`)  
⚠️ **Legacy code** - `legacy_backup/` folder with old tournament templates  
⚠️ **Inconsistent patterns** - Some pages use modern JS modules, others use inline scripts  
⚠️ **No bundler** - JavaScript files loaded individually (no Webpack/Vite)  
⚠️ **Tailwind CDN** - Using CDN instead of build process (larger bundle, no purging)  
⚠️ **Scattered CSS** - Many CSS files (`tournaments-detail-v8.css`, `teams-list-modern.css`) - versioning suggests iteration  
⚠️ **Mixed API patterns** - Some pages use `fetch()`, some use forms, some use HTMX  
⚠️ **No centralized state** - Each page manages its own state independently  

### 5.3 Missing Frontend Infrastructure

❌ **No package.json** - No npm/yarn dependency management  
❌ **No build process** - No transpilation, minification, or bundling  
❌ **No TypeScript** - All JavaScript is vanilla ES6+  
❌ **No testing framework** - No Jest, Cypress, or Playwright tests for frontend  
❌ **No component documentation** - No Storybook or similar tool  
❌ **No linting** - No ESLint or Prettier configuration  
❌ **No CSS preprocessor** - Plain CSS (no SCSS/SASS build step)  

---

## 📝 6. Summary

**Current Frontend Architecture**: **Django Templates + Tailwind CDN + Vanilla JS**

**Total Estimated Files**:
- **Templates**: ~200+ HTML files
- **CSS Files**: ~100+ files
- **JavaScript Files**: ~80+ files
- **Images**: Favicon set + logos + game assets

**Frontend is**: Production-ready Django templates with progressive enhancement, but lacks modern build tooling and standardized patterns.

**Next Steps**: See `EXISTING_FRONTEND_FULL_REPORT.md` for detailed analysis and recommendations.

---

**End of Inventory**
