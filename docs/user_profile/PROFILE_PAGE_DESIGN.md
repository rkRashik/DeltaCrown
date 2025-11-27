# Glassmorphic Cyberpunk 2025 Profile Page

## 🎨 Design System Overview

This profile page implements a modern "Glassmorphic Cyberpunk 2025" design language specifically built for esports portfolios.

### Color Palette
- **Background:** Deep Slate (`bg-slate-950`)
- **Glass Panels:** `bg-slate-900/60 backdrop-blur-xl border border-white/10`
- **Primary Accent:** Indigo-500 (#6366f1)
- **Win/Success:** Emerald-500 (#10b981)
- **Loss/Danger:** Rose-600 (#e11d48)
- **Gold:** Amber-400 (for trophies/coins)

---

## 📁 File Structure

```
templates/user_profile/
├── profile.html          # Main profile template (6 modules)

static/css/
├── profile.css           # Design system & animations

static/js/
├── profile.js            # Interactivity & utilities
```

---

## 🔧 Module Breakdown

### Module 1: Global Design System & Animations
**File:** `static/css/profile.css`

**Custom Animations:**
- `animate-spin-slow` - 3s coin rotation for DeltaCoin wallet
- `pulse-glow` - Pulsing red ring for live streaming status
- `hover-lift` - Card lift effect on hover

**Utility Classes:**
- `.glass-card` - Glassmorphic panel base
- `.win-strip` / `.loss-strip` - Match history borders
- `.trophy-glow` - Golden trophy shadow effect
- `.social-{platform}` - Brand color hover effects

### Module 2: The Cinematic Hero Section
**Height:** 280px (desktop) / 220px (mobile)

**Features:**
- User banner image with cinematic gradient fade
- Large circular avatar with optional pulsing live ring
- Verification badge (blue checkmark)
- Dynamic action bar:
  - **Owner:** Edit Profile, Settings, Share Portfolio
  - **Visitor:** Follow, Challenge, Message

**Mobile:** Fixed bottom action bar for thumb access

### Module 3: Left Column - Identity & Trust
**Layout:** `col-span-3`, Sticky sidebar

**Cards:**
1. **Vital Statistics**
   - Location (flag + city)
   - Age (privacy-controlled)
   - Phone (privacy-controlled with lock icon)
   - Reputation Score (animated progress bar)

2. **Social Grid**
   - 2x2 grid of connected accounts
   - Brand color hover effects
   - Live badge for Twitch

### Module 4: Middle Column - The Game Feed
**Layout:** `col-span-6`, Main content area

**Components:**
1. **Trophy Shelf**
   - Horizontal scrollable gold/silver/bronze trophies
   - Glow effect on hover
   - Tooltips with achievement names

2. **Game Passport**
   - Tabbed interface (Valorant/CS2/eFootball)
   - Large rank badge with gradient
   - Copyable Riot ID/Steam ID (clipboard toast)
   - Role badges (Duelist, IGL, Sniper)

3. **Match History**
   - Win/Loss rows with colored left borders
   - Green (#10b981) for wins, Red (#e11d48) for losses
   - Clickable rows → Match details page
   - Empty state for new users

### Module 5: Right Column - Career & Economy
**Layout:** `col-span-3`, Sticky sidebar

**Cards:**
1. **Current Team**
   - Team logo + name
   - User role (Captain/IGL)
   - Facepile (3 overlapping avatars)
   - `hover-lift` effect, clickable to team page

2. **DeltaCoin Wallet** (Private)
   - Animated spinning coin icon
   - Balance with blur toggle (eye icon)
   - Sparkline earnings graph (SVG)
   - Blurred view for visitors

3. **Certificate Vault**
   - Downloadable PDF certificates
   - Hover reveals download button
   - Season awards, MVP certificates

### Module 6: Mobile Responsiveness
**Strategy:** Desktop grid hidden (`hidden md:grid`), mobile tabs shown (`md:hidden`)

**Sticky Tab Navigation:**
- **[INFO]** - Vitals + Trophy Shelf (swipeable) + Socials
- **[GAMES]** - Game Passport + Match History
- **[CAREER]** - Team + Wallet (owner only) + Certificates

**Mobile Action Bar:** Fixed at bottom with glass background

---

## 🎯 Key Features

### Interactions (JavaScript)
1. **Copy to Clipboard** - Riot ID/Steam ID with toast notification
2. **Share Profile** - Web Share API with fallback
3. **Follow/Unfollow** - AJAX with optimistic UI update
4. **Wallet Blur Toggle** - Privacy control for balance visibility
5. **Download Certificates** - Direct PDF download

### Animations
- Reputation bar fills on page load (500ms delay)
- Spinning DeltaCoin icon (3s rotation)
- Pulsing live badge (2s cycle)
- Match rows slide on hover
- Trophy shelf glow effect

### Privacy Controls
- Phone visibility (lock icon when hidden)
- Age visibility
- Social links visibility
- Wallet blur for non-owners

### Responsive Design
- **Desktop:** 3-column grid (3-6-3 ratio)
- **Mobile:** Tabbed interface with sticky nav
- **Breakpoint:** `md:` (768px)

---

## 🚀 Usage

### Accessing the Profile
- **Own Profile:** `/profile/me/` or `/user_profile/profile/`
- **Public Profile:** `/user_profile/u/<username>/`

### Required Context Variables
```python
{
    'profile': UserProfile,
    'profile_user': User,
    'is_own_profile': bool,
    'privacy_settings': PrivacySettings,
    'social': [SocialLink],
    'pinned_badges': [UserBadge],
    'game_profiles': [GameProfile],
    'match_history': [Match],
    'current_teams': [TeamMember],
    'wallet_balance': Decimal,
}
```

### Template Blocks
```django
{% block extra_css %}
    <link rel="stylesheet" href="{% static 'css/profile.css' %}">
{% endblock %}

{% block extra_js %}
    <script src="{% static 'js/profile.js' %}"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
{% endblock %}
```

---

## 🎨 Customization

### Adding New Social Platforms
1. Add emoji icon in template
2. Add hover color in `profile.css`:
```css
.social-newplatform:hover {
    background-color: #BRAND_COLOR !important;
}
```

### Custom Match Result Colors
Edit `.win-strip` and `.loss-strip` classes in `profile.css`

### Reputation Score Thresholds
Modify in template:
```django
{% if profile.reputation_score >= 80 %}High Trust
{% elif profile.reputation_score >= 50 %}Moderate Trust
{% else %}Low Trust{% endif %}
```

---

## 📊 Performance Notes

- Alpine.js loaded via CDN (deferred)
- CSS animations use GPU-accelerated properties (transform, opacity)
- Images use `object-cover` for optimal display
- Sparkline SVG is lightweight (<1KB)
- Toast notifications auto-remove after 3s

---

## 🐛 Debugging

### Common Issues
1. **CSS not loading:** Check `{% load static %}` in template
2. **JS not working:** Verify Alpine.js CDN is accessible
3. **Blurred wallet:** Privacy setting applied correctly
4. **Tabs not switching:** Check Alpine.js initialization

### Dev Tools
- Use browser DevTools to inspect glass effects
- Check console for JavaScript errors
- Verify CSRF token for AJAX requests

---

## 🔮 Future Enhancements

- [ ] Real-time match updates (WebSocket)
- [ ] Animated rank progression
- [ ] Trophy showcase carousel
- [ ] Team roster live status
- [ ] Earnings chart with Chart.js
- [ ] Certificate verification QR codes
- [ ] Social activity feed
- [ ] Match replay highlights

---

**Version:** 1.0.0  
**Last Updated:** November 26, 2025  
**Design System:** Glassmorphic Cyberpunk 2025
