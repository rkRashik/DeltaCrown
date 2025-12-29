# UP-PHASE9D: SEO & Public Profile Discoverability

**Phase:** Post-Launch Readiness  
**Type:** SEO Strategy & Indexing Rules  
**Date:** 2025-12-29  
**Status:** Strategy Document

---

## Executive Summary

This document analyzes the user_profile system's SEO readiness, defines what should be indexable by search engines, proposes OpenGraph/Twitter Card metadata, and establishes privacy-safe indexing rules.

**Goal:** Make public profiles discoverable while protecting private data from search engines.

---

## 1. Current SEO State Analysis

### 1.1 Meta Tags Audit

**File:** `templates/user_profile/profile/public.html`

**Current State:**
```django-html
{% block title %}{{ profile.display_name }} (@{{ profile_user.username }}) - Profile{% endblock %}
```

**Issues Found:**
- ❌ No meta description
- ❌ No OpenGraph tags (og:title, og:image, og:description)
- ❌ No Twitter Card tags
- ❌ No canonical URL
- ❌ No robots meta tag for privacy control

**Status:** ⚠️ **Not SEO-ready**

---

### 1.2 URL Structure

**Current URLs:**
- Profile: `/@<username>/`
- Activity: `/@<username>/activity/`
- Settings: `/me/settings/`
- Privacy: `/me/privacy/`

#### ✅ Good Practices

**Clean URLs:**
- ✅ No query parameters for main pages
- ✅ Human-readable usernames
- ✅ Consistent @ prefix pattern

**Canonical Format:**
- ✅ Profile uses `@username` (Twitter-style)
- ✅ No trailing slashes inconsistency

---

### 1.3 Indexability Analysis

**Should Be Indexed:**
- ✅ Public profiles (`/@<username>/`)
- ✅ Public activity feeds (`/@<username>/activity/`)

**Should NOT Be Indexed:**
- ❌ Private profiles (need noindex tag)
- ❌ Settings pages (`/me/settings/`)
- ❌ Privacy pages (`/me/privacy/`)
- ❌ Admin pages (already handled by robots.txt)

**Current Protection:** None (no robots meta tags)

---

## 2. SEO Strategy

### 2.1 Target Keywords

**Per-Profile Keywords:**
- Primary: `[Display Name] DeltaCrown`
- Secondary: `[Username] esports profile`
- Long-tail: `[Display Name] [Game] player stats`

**Example:**
- "John Doe DeltaCrown"
- "johndoe123 esports profile"
- "John Doe VALORANT player stats"

---

### 2.2 Search Intent

**What Users Search For:**
1. **Player Lookup:** "johndoe123 esports" (find profile)
2. **Stats Research:** "johndoe123 VALORANT rank" (check skill)
3. **Team Research:** "johndoe123 team" (find affiliations)
4. **Social Discovery:** "johndoe123 Twitter" (find social links)

**How to Rank:**
- Optimize title tags with display name + username
- Include game passport data in meta description
- Show team affiliations in structured data

---

### 2.3 Competitive Analysis

**Competitor Profiles:**

| Platform | Profile URL | Indexability | Rich Snippets |
|----------|-------------|--------------|---------------|
| **Liquipedia** | `/wiki/Player:Name` | ✅ Indexed | ✅ (Infobox) |
| **Battlefy** | `/players/id` | ✅ Indexed | ❌ None |
| **Checkmate GG** | `/@username` | ✅ Indexed | ❌ None |

**DeltaCrown Opportunity:**
- ✅ Use structured data (Person schema)
- ✅ Include game identities in meta
- ✅ Show tournament history in rich snippets

---

## 3. Meta Tags Implementation Plan

### 3.1 Basic SEO Tags

**Profile Page (`public.html`):**

```django-html
{% block head_extra %}
    <!-- Basic SEO -->
    <title>{{ profile.display_name }} (@{{ profile_user.username }}) - DeltaCrown Esports</title>
    
    <meta name="description" content="{{ profile.bio|default:'Professional esports player' }} | {{ profile.display_name }} plays {{ game_list }} on DeltaCrown. View stats, teams, and achievements.">
    
    <!-- Canonical URL (privacy-aware) -->
    {% if can_view_profile %}
        <link rel="canonical" href="https://deltacrown.com/@{{ profile_user.username }}/">
    {% else %}
        <meta name="robots" content="noindex, nofollow">
    {% endif %}
    
    <!-- Privacy Control -->
    {% if not can_view_profile or privacy_settings.profile_visibility == 'PRIVATE' %}
        <meta name="robots" content="noindex, nofollow">
    {% elif privacy_settings.profile_visibility == 'FOLLOWERS_ONLY' %}
        <meta name="robots" content="noindex, follow">
    {% else %}
        <meta name="robots" content="index, follow">
    {% endif %}
{% endblock %}
```

**Rationale:**
- Description includes bio, games, and CTA
- Canonical URL prevents duplicate content
- Robots tag respects privacy settings

---

### 3.2 OpenGraph Tags (Social Sharing)

**Purpose:** Rich previews on Facebook, LinkedIn, Discord

```django-html
<!-- OpenGraph Protocol -->
<meta property="og:type" content="profile">
<meta property="og:title" content="{{ profile.display_name }} (@{{ profile_user.username }})">
<meta property="og:description" content="{{ profile.bio|default:'Professional esports player on DeltaCrown' }}">
<meta property="og:url" content="https://deltacrown.com/@{{ profile_user.username }}/">

<!-- Profile-specific OG tags -->
<meta property="profile:username" content="{{ profile_user.username }}">
{% if profile.real_full_name and not privacy_settings.hide_real_name %}
    <meta property="profile:first_name" content="{{ profile.real_full_name|split:' '|first }}">
    <meta property="profile:last_name" content="{{ profile.real_full_name|split:' '|last }}">
{% endif %}

<!-- Image (use avatar or default) -->
{% if profile.avatar %}
    <meta property="og:image" content="{{ profile.avatar.url }}">
    <meta property="og:image:width" content="400">
    <meta property="og:image:height" content="400">
    <meta property="og:image:alt" content="{{ profile.display_name }} avatar">
{% else %}
    <meta property="og:image" content="https://deltacrown.com/static/images/default-avatar.png">
{% endif %}

<!-- Site branding -->
<meta property="og:site_name" content="DeltaCrown Esports">
<meta property="og:locale" content="en_US">
```

**Preview Example:**
```
[Avatar Image]
John Doe (@johndoe123)
Professional VALORANT player | Ranked Immortal 3 | Team Alpha
DeltaCrown Esports
```

---

### 3.3 Twitter Card Tags

**Purpose:** Rich previews on Twitter/X

```django-html
<!-- Twitter Card -->
<meta name="twitter:card" content="summary">
<meta name="twitter:site" content="@DeltaCrownGG">
<meta name="twitter:title" content="{{ profile.display_name }} (@{{ profile_user.username }})">
<meta name="twitter:description" content="{{ profile.bio|truncatechars:200 }}">

{% if profile.avatar %}
    <meta name="twitter:image" content="{{ profile.avatar.url }}">
    <meta name="twitter:image:alt" content="{{ profile.display_name }} avatar">
{% endif %}

<!-- Link to user's Twitter if public -->
{% if can_view_social_links and profile.twitter %}
    <meta name="twitter:creator" content="@{{ profile.twitter|extract_handle }}">
{% endif %}
```

**Card Type:** `summary` (square image, not large)

---

### 3.4 Structured Data (JSON-LD)

**Purpose:** Google rich snippets (Knowledge Graph)

```django-html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Person",
  "name": "{{ profile.display_name }}",
  "alternateName": "@{{ profile_user.username }}",
  {% if profile.avatar %}
  "image": "{{ profile.avatar.url }}",
  {% endif %}
  {% if profile.bio %}
  "description": "{{ profile.bio|escapejs }}",
  {% endif %}
  "url": "https://deltacrown.com/@{{ profile_user.username }}/",
  
  {% if can_view_social_links %}
  "sameAs": [
    {% if profile.twitter %}"https://twitter.com/{{ profile.twitter }}",{% endif %}
    {% if profile.twitch_link %}"{{ profile.twitch_link }}",{% endif %}
    {% if profile.youtube_link %}"{{ profile.youtube_link }}"{% endif %}
  ],
  {% endif %}
  
  {% if profile.country %}
  "homeLocation": {
    "@type": "Place",
    "address": {
      "@type": "PostalAddress",
      "addressCountry": "{{ profile.country }}"
    }
  },
  {% endif %}
  
  "worksFor": {
    "@type": "Organization",
    "name": "DeltaCrown Esports"
  }
}
</script>
```

**Benefits:**
- Google Knowledge Graph eligibility
- Rich snippets in search results
- Better social media previews

---

## 4. Privacy-Safe Indexing Rules

### 4.1 What Should Be Indexed

**✅ Always Index:**
- Public profiles (`profile_visibility='PUBLIC'`)
- Display name, username, avatar
- Public bio
- Public game passports (if `show_game_ids=True`)
- Public achievements (if `show_achievements=True`)

**✅ Conditionally Index:**
- Social links (if `show_social_links=True`)
- Teams (if `show_teams=True`)
- Country/region (if `show_country=True`)

---

### 4.2 What Should NEVER Be Indexed

**❌ Private Data:**
- Email addresses
- Phone numbers
- Real names (unless public profile)
- Date of birth
- Emergency contacts
- Wallet account numbers
- KYC documents

**❌ Private Profiles:**
- Profiles with `profile_visibility='PRIVATE'`
- Profiles with `profile_visibility='FOLLOWERS_ONLY'`

**❌ Owner-Only Pages:**
- Settings pages (`/me/settings/`)
- Privacy pages (`/me/privacy/`)
- Admin pages (`/admin/`)

---

### 4.3 Robots Meta Tag Logic

**Implementation:**

```python
# apps/user_profile/views/fe_v2.py (CONCEPTUAL)
def profile_public_v2(request, username):
    # ... existing code
    
    # Determine robots directive
    if not permissions['can_view_profile']:
        robots_directive = 'noindex, nofollow'
    elif privacy_settings.profile_visibility == 'PRIVATE':
        robots_directive = 'noindex, nofollow'
    elif privacy_settings.profile_visibility == 'FOLLOWERS_ONLY':
        robots_directive = 'noindex, follow'  # Allow crawling links, but don't index page
    else:  # PUBLIC
        robots_directive = 'index, follow'
    
    context['robots_directive'] = robots_directive
```

**Template:**
```django-html
<meta name="robots" content="{{ robots_directive }}">
```

---

### 4.4 Robots.txt

**File:** `static/robots.txt`

```
User-agent: *

# Allow public profiles
Allow: /@*/

# Disallow owner-only pages
Disallow: /me/
Disallow: /settings/
Disallow: /privacy/

# Disallow admin
Disallow: /admin/

# Disallow API endpoints
Disallow: /api/

# Disallow authentication pages
Disallow: /account/login/
Disallow: /account/signup/

# Sitemap
Sitemap: https://deltacrown.com/sitemap.xml
```

---

## 5. Sitemap Strategy

### 5.1 Dynamic Sitemap

**URL:** `/sitemap.xml` or `/sitemap-profiles.xml`

**Content:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <!-- Only include PUBLIC profiles -->
    {% for profile in public_profiles %}
    <url>
        <loc>https://deltacrown.com/@{{ profile.user.username }}/</loc>
        <lastmod>{{ profile.updated_at|date:"c" }}</lastmod>
        <changefreq>daily</changefreq>
        <priority>0.8</priority>
    </url>
    {% endfor %}
</urlset>
```

**Query:**
```python
# Generate sitemap for profiles with profile_visibility='PUBLIC'
public_profiles = UserProfile.objects.filter(
    privacy_settings__profile_visibility='PUBLIC'
).select_related('user').order_by('-updated_at')[:10000]  # Max 10k profiles per sitemap
```

---

### 5.2 Sitemap Update Frequency

**Strategy:**
- Regenerate sitemap daily (cron job)
- Cache sitemap for 24 hours
- Update immediately when profile becomes public/private

**Performance:**
- Limit to 10,000 profiles per sitemap
- Use sitemap index if >10k profiles
- Cache sitemap XML in Redis (1 day TTL)

---

## 6. Search Console Setup

### 6.1 Google Search Console

**Verification:** Add meta tag or DNS TXT record

**Configuration:**
- Submit sitemap.xml
- Monitor indexing status
- Track search queries
- Fix crawl errors

**Expected Queries:**
- "[Username] esports"
- "[Display Name] player"
- "[Username] VALORANT"

---

### 6.2 Search Console Monitoring

**Weekly Review:**
- Indexing coverage (how many profiles indexed?)
- Crawl errors (404s, 5xxs)
- Mobile usability issues
- Core Web Vitals

**Monthly Review:**
- Top search queries (what users search for)
- Click-through rate (CTR)
- Average position in search results

---

## 7. Link Building Strategy

### 7.1 Internal Linking

**From Profile Pages:**
- Link to game pages (`/games/valorant/`)
- Link to team pages (`/teams/<slug>/`)
- Link to tournament pages (`/tournaments/<slug>/`)

**To Profile Pages:**
- Link from tournament rosters
- Link from team member lists
- Link from match history

**Benefit:** Improves PageRank distribution

---

### 7.2 External Linking

**Outbound Links (DoFollow):**
- User's social media (Twitter, Twitch, YouTube)
- Team websites
- Tournament organizer sites

**Inbound Links (Goal):**
- Tournament organizers link to player profiles
- Teams link to rosters
- Social media shares

---

## 8. Page Speed & Core Web Vitals

### 8.1 Target Metrics

**Core Web Vitals:**
- **LCP (Largest Contentful Paint):** <2.5s
- **FID (First Input Delay):** <100ms
- **CLS (Cumulative Layout Shift):** <0.1

**Current State:** Unknown (needs measurement)

---

### 8.2 Optimization Opportunities

**Image Optimization:**
- Use WebP format for avatars/banners
- Lazy load images below fold
- Add `width` and `height` attributes (prevent CLS)

**CSS Optimization:**
- Inline critical CSS
- Defer non-critical CSS
- Minify Tailwind CSS

**JavaScript Optimization:**
- Defer Alpine.js until DOM ready
- Use `async` or `defer` on scripts
- Minimize third-party scripts

---

## 9. Mobile-First SEO

### 9.1 Mobile Usability

**Google's Mobile-First Indexing:** Desktop and mobile must have same content

**Current State:** ✅ Responsive design (Tailwind CSS)

**Verification Needed:**
- [ ] Mobile viewport meta tag correct
- [ ] Touch targets ≥48px
- [ ] Font sizes readable (≥16px)
- [ ] No horizontal scroll

---

### 9.2 Mobile Search Features

**Google Discover Eligibility:**
- High-quality images (avatars/banners)
- Engaging content (bio, achievements)
- Fresh content (recent activity)

**Voice Search Optimization:**
- Natural language in bio
- Question-based content (FAQs)
- Structured data (speakable content)

---

## 10. Analytics & Tracking

### 10.1 Google Analytics 4

**Events to Track:**
- Profile views (pageview)
- Follow button clicks (event)
- Social link clicks (event)
- Game Passport views (event)

**Custom Dimensions:**
- Profile visibility (PUBLIC/PRIVATE/FOLLOWERS_ONLY)
- Viewer role (owner/follower/visitor/anonymous)
- Has game passports (yes/no)

---

### 10.2 Search Performance

**Metrics to Track:**
- Organic search traffic (GA4)
- Search impressions (Search Console)
- Click-through rate (Search Console)
- Average search position (Search Console)

**Goal:** 10% of traffic from organic search within 6 months

---

## 11. Content Strategy

### 11.1 Encourage Rich Bios

**User Education:**
- Prompt users to write detailed bios
- Suggest including: games played, achievements, goals
- Show character count (encourage 100+ words)

**Example:**
```
Good Bio:
"Professional VALORANT player with 5+ years of competitive experience. 
Former Immortal 3 peak, now coaching aspiring players. Specializes in 
Controller agents (Viper, Omen). Looking for tournament opportunities 
in Southeast Asia."

Bad Bio:
"gamer"
```

---

### 11.2 Auto-Generated Content

**Profile Summary (for SEO):**
```
{{ profile.display_name }} is a professional esports player on DeltaCrown.
{% if game_passports %}
Plays {{ game_list }}.
{% endif %}
{% if teams %}
Member of {{ team_list }}.
{% endif %}
{% if tournaments_played > 0 %}
Competed in {{ tournaments_played }} tournaments.
{% endif %}
```

**Use Case:** Display when bio is empty (for search engines only)

---

## 12. Competitive Advantage

### 12.1 What DeltaCrown Does Better

**vs Liquipedia:**
- ✅ Real-time profile updates (Liquipedia is wiki-based)
- ✅ Player-controlled content (not editors)

**vs Battlefy:**
- ✅ Persistent profiles (Battlefy is tournament-focused)
- ✅ Cross-game identity (not siloed)

**vs Checkmate GG:**
- ✅ Structured data (better rich snippets)
- ✅ Game Passport system (unique identity)

---

### 12.2 SEO Moat

**Unique Value:**
- First mover in South Asia esports profiles
- Schema.org structured data (rich snippets)
- Cross-game identity (search "[Name] esports" → DeltaCrown)

---

## 13. International SEO

### 13.1 Hreflang Tags

**Purpose:** Tell Google which language/region version to show

```django-html
<!-- If multilingual support added -->
<link rel="alternate" hreflang="en" href="https://deltacrown.com/@{{ username }}/">
<link rel="alternate" hreflang="bn" href="https://deltacrown.com/bn/@{{ username }}/">
<link rel="alternate" hreflang="x-default" href="https://deltacrown.com/@{{ username }}/">
```

**Current State:** Not needed (English-only)

---

### 13.2 Regional Targeting

**Google Search Console:**
- Set international targeting to "Bangladesh" (primary market)
- Add hreflang if expanding to India, Pakistan

---

## 14. Implementation Checklist

### 14.1 Pre-Launch (Blockers)

- [ ] Add meta description to profile pages
- [ ] Add OpenGraph tags (og:title, og:image, og:description)
- [ ] Add Twitter Card tags
- [ ] Add canonical URL
- [ ] Add robots meta tag (privacy-aware)
- [ ] Create robots.txt
- [ ] Add structured data (Person schema)

**Effort:** 4-6 hours

---

### 14.2 Launch Week

- [ ] Generate dynamic sitemap
- [ ] Submit sitemap to Google Search Console
- [ ] Verify Google Search Console ownership
- [ ] Set up Google Analytics 4
- [ ] Test social media previews (Facebook/Twitter debuggers)

**Effort:** 2-3 hours

---

### 14.3 Post-Launch (First Month)

- [ ] Monitor indexing status (Search Console)
- [ ] Optimize page speed (Core Web Vitals)
- [ ] Build internal links (tournaments → profiles)
- [ ] Encourage users to write rich bios

---

## 15. Success Metrics

**3-Month Goals:**
- 80% of public profiles indexed by Google
- 100+ organic search visits/week
- <3s page load time (LCP)

**6-Month Goals:**
- 1,000+ organic search visits/week
- Top 10 ranking for "[username] esports" queries
- 5% CTR on search results

**1-Year Goals:**
- 10,000+ organic search visits/week
- Featured in Google Knowledge Graph (top players)
- 10% of total traffic from organic search

---

## Final Recommendations

**Launch Blockers:** 7 SEO tasks (6 hours of work)

**Priority 1 (Critical):**
1. Add OpenGraph/Twitter Card tags
2. Add robots meta tag (privacy-aware)
3. Create robots.txt

**Priority 2 (Important):**
4. Add structured data (Person schema)
5. Generate dynamic sitemap
6. Submit to Google Search Console

**Priority 3 (Nice-to-Have):**
7. Optimize page speed
8. Build internal links

**SEO Readiness:** ⚠️ **Not ready to launch** (missing critical meta tags)

---

**Document Version:** 1.0  
**Last Updated:** 2025-12-29  
**Status:** Strategy Document - Implementation Required Before Launch  
**Owner:** Marketing + Engineering Teams
