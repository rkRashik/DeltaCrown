# Part 5: Implementation Roadmap & Technical Integration

**DeltaCrown Tournament Engine**  
**Version:** 1.0  
**Date:** November 3, 2025  
**Author:** Implementation Team

---

## Executive Summary

This document provides a comprehensive implementation roadmap for building the DeltaCrown Tournament Engine, integrating the technical architecture (Part 2), database design (Part 3), and UI/UX specifications (Part 4) into an actionable development plan.

**Project Scope:**
- 20+ tournament management screens
- 50+ reusable UI components
- Real-time features (live matches, WebSocket updates)
- Multi-role support (Players, Organizers, Spectators, Admins)
- Mobile-first responsive design
- Bengali + English localization
- Payment verification system
- Certificate generation system

**Timeline:** 16 weeks (4 phases × 4 sprints)  
**Team Size:** 5-7 developers (2 Frontend, 2 Backend, 1 Full-stack, 1 QA, 1 DevOps)  
**Target Launch:** Q2 2026

---

## Document Purpose

This implementation roadmap serves multiple audiences:

**For Development Team:**
- Sprint-by-sprint task breakdown
- Clear acceptance criteria
- Technical integration points
- Testing requirements

**For Project Managers:**
- Timeline and milestones
- Resource allocation
- Risk assessment
- Success metrics

**For Stakeholders:**
- Progress tracking
- Delivery schedule
- Budget alignment
- Launch readiness criteria

---

## Table of Contents

1. [Implementation Strategy Overview](#1-implementation-strategy-overview)
2. [Sprint Planning & Task Breakdown](#2-sprint-planning--task-breakdown)
3. [Frontend Implementation Guide](#3-frontend-implementation-guide)
4. [Backend Integration Points](#4-backend-integration-points)
5. [Testing & QA Strategy](#5-testing--qa-strategy)
6. [Deployment & DevOps](#6-deployment--devops)
7. [Team Structure & Responsibilities](#7-team-structure--responsibilities)
8. [Integration Checklist & Dependencies](#8-integration-checklist--dependencies)
9. [Post-Launch & Iteration Plan](#9-post-launch--iteration-plan)
10. [Appendix: Technical Reference](#10-appendix-technical-reference)

---

## 1. Implementation Strategy Overview

### 1.1 Development Approach

**Methodology:** Agile Scrum with 2-week sprints

**Core Principles:**
1. **Component-First Development:** Build reusable UI components before pages
2. **API-First Integration:** Backend APIs ready before frontend consumption
3. **Test-Driven Development:** Write tests alongside features
4. **Continuous Integration:** Automated testing on every commit
5. **Progressive Enhancement:** Core functionality works without JavaScript

**Development Phases:**

```
Phase 1: Foundation (Weeks 1-4)
├── Design System Setup
├── Core Components
├── Authentication & User Management
└── Basic Tournament CRUD

Phase 2: Core Features (Weeks 5-8)
├── Tournament Registration & Payments
├── Bracket Generation & Display
├── Match Management
└── Admin Dashboard

Phase 3: Advanced Features (Weeks 9-12)
├── Real-time Live Matches
├── Spectator Features
├── Community Discussions
└── Certificate System

Phase 4: Polish & Launch (Weeks 13-16)
├── Performance Optimization
├── Accessibility Audit
├── User Acceptance Testing
└── Production Deployment
```

### 1.2 Timeline Overview

**16-Week Delivery Schedule:**

| Phase | Duration | Sprints | Key Deliverables | Milestone |
|-------|----------|---------|------------------|-----------|
| **Phase 1: Foundation** | Weeks 1-4 | Sprint 1-2 | Design system, auth, basic CRUD | ✅ MVP Demo Ready |
| **Phase 2: Core Features** | Weeks 5-8 | Sprint 3-4 | Registration, payments, brackets | ✅ Alpha Release |
| **Phase 3: Advanced** | Weeks 9-12 | Sprint 5-6 | Live matches, spectator, community | ✅ Beta Release |
| **Phase 4: Polish** | Weeks 13-16 | Sprint 7-8 | Optimization, testing, deployment | ✅ Production Launch |

**Critical Milestones:**

- **Week 4:** MVP Demo (stakeholder review)
- **Week 8:** Alpha Release (internal testing)
- **Week 12:** Beta Release (limited user testing)
- **Week 16:** Production Launch (public availability)

### 1.3 Resource Requirements

**Development Team:**

| Role | Count | Responsibilities | Weekly Hours |
|------|-------|------------------|--------------|
| **Frontend Developer** | 2 | React/HTMX, Tailwind, component library | 40h × 2 = 80h |
| **Backend Developer** | 2 | Django, APIs, WebSocket, database | 40h × 2 = 80h |
| **Full-stack Developer** | 1 | Bridge frontend/backend, troubleshooting | 40h |
| **QA Engineer** | 1 | Test automation, manual testing, accessibility | 40h |
| **DevOps Engineer** | 0.5 | CI/CD, deployment, monitoring | 20h |
| **UI/UX Designer** | 0.5 | Figma mockups, design review, assets | 20h |
| **Project Manager** | 0.5 | Sprint planning, stakeholder communication | 20h |

**Total Weekly Effort:** 300 hours  
**Total Project Effort:** 4,800 hours (16 weeks)

**Infrastructure:**

- **Development:** Local Docker setup + staging server
- **Staging:** 2GB RAM VPS (DigitalOcean/AWS)
- **Production:** 4GB RAM VPS + CDN (Cloudflare)
- **Database:** PostgreSQL 15+ (managed service recommended)
- **Storage:** 50GB SSD for media uploads
- **Tools:** GitHub, Jira, Figma, Sentry, DataDog

**Budget Estimate:**

| Category | Monthly Cost | 4-Month Total |
|----------|--------------|---------------|
| Team Salaries | $15,000 | $60,000 |
| Infrastructure | $300 | $1,200 |
| Tools & Services | $200 | $800 |
| Contingency (10%) | $1,550 | $6,200 |
| **Total** | **$17,050** | **$68,200** |

### 1.4 Risk Assessment

**High-Priority Risks:**

| Risk | Impact | Probability | Mitigation Strategy |
|------|--------|-------------|---------------------|
| **Real-time feature complexity** | High | Medium | Start WebSocket integration early (Sprint 2), allocate extra time |
| **Payment gateway integration** | High | Low | Use sandbox testing, have backup manual verification flow |
| **Performance on mobile** | Medium | Medium | Performance testing in every sprint, optimize images/JS |
| **Team member unavailability** | Medium | Low | Cross-train developers, maintain documentation |
| **Scope creep** | High | High | Strict sprint planning, defer non-critical features to Phase 5 |
| **Third-party API changes** | Low | Low | Abstract API calls, version lock dependencies |

**Mitigation Actions:**
- Weekly risk review in sprint planning
- Contingency buffer (1 week) before launch
- Feature flagging for risky features
- Automated alerts for production issues

### 1.5 Success Criteria

**Technical Metrics:**

- ✅ Lighthouse Performance Score: >90
- ✅ Lighthouse Accessibility Score: 100 (WCAG 2.1 AA)
- ✅ Page Load Time (LCP): <2.5s on 3G
- ✅ Test Coverage: >80% (backend), >70% (frontend)
- ✅ Zero critical security vulnerabilities (OWASP)
- ✅ API Response Time: <200ms (p95)
- ✅ WebSocket Connection Stability: >99%

**Feature Completeness:**

- ✅ All 20 screens from Part 4 implemented
- ✅ 50+ components in Storybook
- ✅ Multi-role access control working
- ✅ Payment verification workflow complete
- ✅ Real-time match updates functional
- ✅ Certificate generation automated
- ✅ Bengali localization 100% translated

**User Acceptance:**

- ✅ 10 beta users complete full tournament flow
- ✅ Zero P0/P1 bugs in production
- ✅ <5 P2 bugs in first week
- ✅ Positive feedback from 8/10 beta testers
- ✅ Admin panel usable without training

---

## 2. Sprint Planning & Task Breakdown

### 2.1 Phase 1: Foundation (Weeks 1-4)

#### Sprint 1 (Week 1-2): Design System & Authentication

**Goals:**
- Establish design system foundation
- Implement authentication flows
- Set up development environment

**Frontend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| FE-001 | Install Tailwind CSS + configure design tokens | 3 | Frontend 1 | - |
| FE-002 | Create base layout components (Navbar, Footer, Container) | 5 | Frontend 1 | FE-001 |
| FE-003 | Build button component with all variants | 3 | Frontend 2 | FE-001 |
| FE-004 | Build form components (Input, Select, Textarea, Checkbox) | 8 | Frontend 2 | FE-001 |
| FE-005 | Create card component with variants | 3 | Frontend 1 | FE-001 |
| FE-006 | Build modal/dialog component with accessibility | 5 | Frontend 1 | FE-002 |
| FE-007 | Implement login page UI | 3 | Frontend 2 | FE-004 |
| FE-008 | Implement signup page UI | 3 | Frontend 2 | FE-004 |
| FE-009 | Set up HTMX for dynamic content loading | 5 | Frontend 1 | FE-002 |

**Total Frontend Story Points:** 38

**Backend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| BE-001 | Set up Django project structure + Docker | 3 | Backend 1 | - |
| BE-002 | Configure PostgreSQL database | 2 | Backend 1 | BE-001 |
| BE-003 | Install Django Allauth + configure providers | 5 | Backend 2 | BE-001 |
| BE-004 | Create User model extensions (profile fields) | 3 | Backend 2 | BE-002 |
| BE-005 | Build authentication API endpoints | 5 | Backend 2 | BE-003 |
| BE-006 | Implement JWT token authentication | 5 | Backend 1 | BE-005 |
| BE-007 | Create user profile CRUD endpoints | 3 | Backend 1 | BE-004 |
| BE-008 | Set up email verification flow | 5 | Backend 2 | BE-003 |
| BE-009 | Configure CORS + security middleware | 2 | Backend 1 | BE-001 |

**Total Backend Story Points:** 33

**DevOps Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| DO-001 | Set up GitHub repository + branching strategy | 2 | DevOps | - |
| DO-002 | Configure CI/CD pipeline (GitHub Actions) | 5 | DevOps | DO-001 |
| DO-003 | Set up staging environment (VPS + Docker) | 5 | DevOps | BE-001 |
| DO-004 | Configure automated testing runner | 3 | DevOps | DO-002 |

**Total DevOps Story Points:** 15

**Acceptance Criteria:**
- [ ] User can sign up with email/password
- [ ] User can log in and receive JWT token
- [ ] User can view/edit their profile
- [ ] All form components are keyboard accessible
- [ ] Design tokens match Part 4 specifications
- [ ] CI pipeline runs tests on every PR
- [ ] Staging environment accessible via HTTPS

---

#### Sprint 2 (Week 3-4): Tournament CRUD & Listing

**Goals:**
- Build tournament listing page
- Implement tournament creation wizard
- Set up tournament detail page structure

**Frontend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| FE-010 | Build tournament card component | 5 | Frontend 1 | FE-005 |
| FE-011 | Create tournament listing page layout | 5 | Frontend 1 | FE-010 |
| FE-012 | Implement filters sidebar (game, date, fee, status) | 8 | Frontend 2 | FE-004 |
| FE-013 | Add infinite scroll with HTMX | 5 | Frontend 2 | FE-009 |
| FE-014 | Build tournament creation wizard (4 steps) | 13 | Frontend 1 | FE-006 |
| FE-015 | Create tournament detail page layout | 8 | Frontend 1 | FE-002 |
| FE-016 | Build organizer card component | 3 | Frontend 2 | FE-005 |
| FE-017 | Implement contact organizer modal | 3 | Frontend 2 | FE-006 |

**Total Frontend Story Points:** 50

**Backend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| BE-010 | Create Tournament model + migrations | 5 | Backend 1 | BE-002 |
| BE-011 | Implement tournament CRUD API endpoints | 8 | Backend 1 | BE-010 |
| BE-012 | Create tournament listing API with filters | 8 | Backend 2 | BE-010 |
| BE-013 | Build tournament detail API | 5 | Backend 2 | BE-010 |
| BE-014 | Implement organizer permission checks | 3 | Backend 1 | BE-004 |
| BE-015 | Create game configuration models | 5 | Backend 1 | BE-010 |
| BE-016 | Build custom fields dynamic form system | 8 | Backend 2 | BE-015 |
| BE-017 | Implement tournament state machine logic | 5 | Backend 1 | BE-010 |

**Total Backend Story Points:** 47

**Acceptance Criteria:**
- [ ] Organizer can create tournament with all fields
- [ ] Public users can browse tournaments with filters
- [ ] Tournament cards show correct status badges
- [ ] Tournament detail page displays all information
- [ ] Organizer can edit their tournaments only
- [ ] Custom fields render dynamically
- [ ] State transitions (DRAFT → PUBLISHED) work
- [ ] Performance: Listing page loads in <2s

---

### 2.2 Phase 2: Core Features (Weeks 5-8)

#### Sprint 3 (Week 5-6): Registration & Payment

**Goals:**
- Build registration flow
- Implement payment submission
- Create admin payment verification

**Frontend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| FE-018 | Build team registration form | 8 | Frontend 1 | FE-004 |
| FE-019 | Implement player field dynamic rows | 5 | Frontend 1 | FE-018 |
| FE-020 | Create custom field renderer | 5 | Frontend 2 | FE-004 |
| FE-021 | Build payment submission page | 8 | Frontend 2 | FE-004 |
| FE-022 | Implement file upload with preview | 5 | Frontend 1 | FE-004 |
| FE-023 | Create confirmation screen | 3 | Frontend 1 | FE-015 |
| FE-024 | Build admin payment review panel | 8 | Frontend 2 | FE-011 |
| FE-025 | Implement payment status badges | 3 | Frontend 2 | FE-003 |

**Total Frontend Story Points:** 45

**Backend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| BE-018 | Create Registration model + migrations | 5 | Backend 1 | BE-010 |
| BE-019 | Build registration submission API | 8 | Backend 1 | BE-018 |
| BE-020 | Implement payment proof upload (S3/local) | 5 | Backend 2 | BE-018 |
| BE-021 | Create payment verification workflow | 8 | Backend 2 | BE-020 |
| BE-022 | Build admin payment review API | 5 | Backend 1 | BE-021 |
| BE-023 | Implement email notifications (payment approved/rejected) | 5 | Backend 2 | BE-021 |
| BE-024 | Create registration status logic | 3 | Backend 1 | BE-018 |
| BE-025 | Build waitlist management system | 5 | Backend 1 | BE-024 |

**Total Backend Story Points:** 44

**Acceptance Criteria:**
- [ ] User can register team with 5 players
- [ ] Custom fields render and validate correctly
- [ ] File upload shows progress and preview
- [ ] Payment proof uploads successfully
- [ ] Admin can approve/reject payments
- [ ] Email notifications sent on payment status change
- [ ] Waitlist auto-promotes when slot available
- [ ] Registration capacity limits enforced

---

#### Sprint 4 (Week 7-8): Bracket Generation & Match Management

**Goals:**
- Implement bracket display
- Build match result submission
- Create admin match management

**Frontend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| FE-026 | Build bracket display component (Chart.js/SVG) | 13 | Frontend 1 | FE-001 |
| FE-027 | Implement bracket navigation (zoom, scroll) | 5 | Frontend 1 | FE-026 |
| FE-028 | Create match card component | 5 | Frontend 2 | FE-005 |
| FE-029 | Build match result submission form | 8 | Frontend 2 | FE-004 |
| FE-030 | Implement match dispute modal | 5 | Frontend 1 | FE-006 |
| FE-031 | Create admin match management panel | 8 | Frontend 2 | FE-024 |
| FE-032 | Build match timeline/history view | 5 | Frontend 1 | FE-015 |

**Total Frontend Story Points:** 49

**Backend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| BE-026 | Create Match model + migrations | 5 | Backend 1 | BE-010 |
| BE-027 | Implement bracket generation algorithm | 13 | Backend 1 | BE-026 |
| BE-028 | Build match CRUD API endpoints | 5 | Backend 2 | BE-026 |
| BE-029 | Create match result submission API | 8 | Backend 2 | BE-028 |
| BE-030 | Implement dispute workflow | 8 | Backend 1 | BE-029 |
| BE-031 | Build bracket progression logic | 8 | Backend 1 | BE-027 |
| BE-032 | Create match state machine | 5 | Backend 2 | BE-026 |

**Total Backend Story Points:** 52

**Acceptance Criteria:**
- [ ] Bracket generates correctly for 8, 16, 32 teams
- [ ] Bracket displays on desktop and mobile
- [ ] Team can submit match result with proof
- [ ] Opponent can confirm or dispute result
- [ ] Admin can override match results
- [ ] Bracket auto-progresses winners
- [ ] Match history shows all updates
- [ ] Performance: Bracket renders in <1s

---

### 2.3 Phase 3: Advanced Features (Weeks 9-12)

#### Sprint 5 (Week 9-10): Real-time & Spectator Features

**Goals:**
- Implement WebSocket live updates
- Build spectator view with predictions
- Create live match HUD

**Frontend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| FE-033 | Set up WebSocket client connection | 5 | Frontend 1 | FE-009 |
| FE-034 | Build live match HUD overlay | 8 | Frontend 1 | FE-028 |
| FE-035 | Create spectator view page | 8 | Frontend 2 | FE-015 |
| FE-036 | Implement prediction system UI | 5 | Frontend 2 | FE-004 |
| FE-037 | Build MVP voting component | 3 | Frontend 1 | FE-003 |
| FE-038 | Create live chat component | 8 | Frontend 2 | FE-004 |
| FE-039 | Implement live score updates (WebSocket) | 5 | Frontend 1 | FE-033 |
| FE-040 | Build viewer counter display | 2 | Frontend 2 | FE-033 |

**Total Frontend Story Points:** 44

**Backend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| BE-033 | Set up Django Channels + Redis | 8 | Backend 1 | BE-001 |
| BE-034 | Create WebSocket consumers | 8 | Backend 1 | BE-033 |
| BE-035 | Implement live match update broadcasting | 5 | Backend 2 | BE-034 |
| BE-036 | Create prediction model + API | 5 | Backend 2 | BE-026 |
| BE-037 | Build MVP voting system | 5 | Backend 1 | BE-029 |
| BE-038 | Implement live chat storage + moderation | 8 | Backend 2 | BE-034 |
| BE-039 | Create viewer tracking system | 3 | Backend 1 | BE-034 |

**Total Backend Story Points:** 42

**Acceptance Criteria:**
- [ ] WebSocket connection stable and auto-reconnects
- [ ] Live scores update in real-time (<1s delay)
- [ ] Predictions lock 5 minutes before match
- [ ] MVP votes tally correctly
- [ ] Live chat messages appear instantly
- [ ] Chat moderation (ban/mute) works
- [ ] Viewer count updates every 10 seconds
- [ ] Performance: 100+ concurrent viewers supported

---

#### Sprint 6 (Week 11-12): Community & Certificates

**Goals:**
- Build community discussions
- Implement certificate generation
- Create player dashboard

**Frontend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| FE-041 | Build discussion thread component | 8 | Frontend 1 | FE-005 |
| FE-042 | Implement comment system with reactions | 5 | Frontend 1 | FE-003 |
| FE-043 | Create pinned comments feature | 3 | Frontend 2 | FE-041 |
| FE-044 | Build certificate view page | 5 | Frontend 2 | FE-015 |
| FE-045 | Implement social sharing buttons | 3 | Frontend 1 | FE-003 |
| FE-046 | Create player dashboard layout | 8 | Frontend 2 | FE-015 |
| FE-047 | Build tournament history component | 5 | Frontend 1 | FE-011 |
| FE-048 | Implement achievement badges display | 3 | Frontend 2 | FE-005 |

**Total Frontend Story Points:** 40

**Backend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| BE-040 | Create discussion thread models | 5 | Backend 1 | BE-010 |
| BE-041 | Build comment/reply API endpoints | 5 | Backend 1 | BE-040 |
| BE-042 | Implement reaction system | 3 | Backend 2 | BE-041 |
| BE-043 | Create moderator pin/unpin feature | 3 | Backend 2 | BE-041 |
| BE-044 | Build certificate generation (Pillow/Canvas) | 8 | Backend 1 | BE-029 |
| BE-045 | Implement certificate verification system | 5 | Backend 1 | BE-044 |
| BE-046 | Create player statistics aggregation | 5 | Backend 2 | BE-029 |
| BE-047 | Build achievement tracking system | 5 | Backend 2 | BE-046 |

**Total Backend Story Points:** 39

**Acceptance Criteria:**
- [ ] Users can create discussion threads
- [ ] Comments support emoji reactions
- [ ] Moderators can pin/unpin comments
- [ ] Certificates auto-generate for winners
- [ ] Certificate has unique verification code
- [ ] Social sharing includes OG image preview
- [ ] Player dashboard shows accurate stats
- [ ] Achievements unlock correctly

---

### 2.4 Phase 4: Polish & Launch (Weeks 13-16)

#### Sprint 7 (Week 13-14): Optimization & Accessibility

**Goals:**
- Performance optimization
- Accessibility audit and fixes
- UI polish and animations

**Frontend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| FE-049 | Implement lazy loading for images | 3 | Frontend 1 | - |
| FE-050 | Optimize bundle size (code splitting) | 5 | Frontend 1 | FE-009 |
| FE-051 | Add loading skeletons to all pages | 5 | Frontend 2 | FE-005 |
| FE-052 | Implement animation library (transitions) | 5 | Frontend 2 | FE-001 |
| FE-053 | Audit accessibility (WCAG 2.1 AA) | 8 | Frontend 1 | All FE |
| FE-054 | Fix accessibility issues | 8 | Frontend 1 | FE-053 |
| FE-055 | Add keyboard shortcuts (power users) | 3 | Frontend 2 | FE-002 |
| FE-056 | Implement dark mode toggle | 5 | Frontend 2 | FE-001 |

**Total Frontend Story Points:** 42

**Backend Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| BE-048 | Optimize database queries (select_related, prefetch) | 8 | Backend 1 | All BE |
| BE-049 | Implement database indexing strategy | 5 | Backend 1 | BE-048 |
| BE-050 | Add API response caching (Redis) | 5 | Backend 2 | BE-033 |
| BE-051 | Optimize image uploads (compression, WebP) | 5 | Backend 2 | BE-020 |
| BE-052 | Implement rate limiting | 3 | Backend 1 | BE-001 |
| BE-053 | Security audit (OWASP checklist) | 5 | Backend 1 | All BE |
| BE-054 | Fix security vulnerabilities | 5 | Backend 2 | BE-053 |

**Total Backend Story Points:** 36

**Acceptance Criteria:**
- [ ] Lighthouse Performance Score >90
- [ ] Lighthouse Accessibility Score 100
- [ ] Page load time <2.5s on 3G
- [ ] All images lazy loaded
- [ ] Zero WCAG violations
- [ ] API response time <200ms (p95)
- [ ] No SQL N+1 queries
- [ ] Zero critical security issues

---

#### Sprint 8 (Week 15-16): Testing & Deployment

**Goals:**
- User acceptance testing
- Production deployment
- Monitoring setup
- Documentation finalization

**QA Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| QA-001 | Create test plan document | 3 | QA | All sprints |
| QA-002 | Execute end-to-end test scenarios | 13 | QA | All features |
| QA-003 | Bug bash session (team-wide) | 5 | QA + Team | QA-002 |
| QA-004 | User acceptance testing (10 beta users) | 8 | QA | QA-002 |
| QA-005 | Performance testing (load testing) | 5 | QA | BE-048 |
| QA-006 | Security penetration testing | 5 | QA | BE-053 |
| QA-007 | Browser compatibility testing | 3 | QA | All FE |

**Total QA Story Points:** 42

**DevOps Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| DO-005 | Set up production environment (4GB VPS) | 5 | DevOps | DO-003 |
| DO-006 | Configure CDN (Cloudflare) | 3 | DevOps | DO-005 |
| DO-007 | Set up database backups (daily) | 3 | DevOps | DO-005 |
| DO-008 | Implement monitoring (Sentry, DataDog) | 5 | DevOps | DO-005 |
| DO-009 | Configure logging and alerts | 3 | DevOps | DO-008 |
| DO-010 | Deploy to production (blue-green deployment) | 5 | DevOps | All tasks |
| DO-011 | Set up SSL certificates (Let's Encrypt) | 2 | DevOps | DO-005 |
| DO-012 | Configure auto-scaling (if needed) | 5 | DevOps | DO-005 |

**Total DevOps Story Points:** 31

**Documentation Tasks:**

| Task ID | Description | Story Points | Assignee | Dependencies |
|---------|-------------|--------------|----------|--------------|
| DOC-001 | Write API documentation (Swagger/OpenAPI) | 5 | Backend 1 | All BE |
| DOC-002 | Create component documentation (Storybook) | 5 | Frontend 1 | All FE |
| DOC-003 | Write admin user guide | 3 | QA | FE-024 |
| DOC-004 | Create organizer onboarding guide | 3 | QA | FE-014 |
| DOC-005 | Write deployment runbook | 3 | DevOps | DO-010 |

**Total Documentation Story Points:** 19

**Acceptance Criteria:**
- [ ] All P0/P1 bugs fixed
- [ ] <5 P2 bugs remaining
- [ ] 10 beta users complete full flow
- [ ] Production environment stable for 48 hours
- [ ] Monitoring dashboards operational
- [ ] Documentation complete and reviewed
- [ ] Launch checklist 100% complete
- [ ] Rollback plan tested

---

## 3. Frontend Implementation Guide

### 3.1 Tech Stack Setup

**Core Technologies:**

```json
{
  "framework": "Django Templates + HTMX",
  "styling": "Tailwind CSS 3.4+",
  "interactivity": "Alpine.js 3.x",
  "realtime": "WebSocket (native) + Django Channels",
  "charts": "Chart.js 4.x",
  "icons": "Heroicons (SVG)",
  "build": "Webpack 5 / Vite",
  "package_manager": "npm / pnpm"
}
```

**Installation Steps:**

```bash
# 1. Install Node.js dependencies
npm install -D tailwindcss@latest postcss autoprefixer
npm install htmx.org alpinejs chart.js

# 2. Initialize Tailwind
npx tailwindcss init -p

# 3. Configure Tailwind (tailwind.config.js)
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/templates/**/*.html',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      colors: {
        'brand-primary': '#3B82F6',
        'brand-secondary': '#8B5CF6',
        'brand-accent': '#F59E0B',
        // ... (all design tokens from Part 4)
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
}

# 4. Create CSS entry point (static/css/main.css)
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer components {
  .btn-primary {
    @apply bg-brand-primary hover:bg-blue-600 text-white px-6 py-3 rounded-lg;
  }
}

# 5. Build process
npm run build:css  # Tailwind compilation
npm run watch:css  # Development mode
```

### 3.2 Component Library Structure

**Directory Structure:**

```
static/
├── css/
│   ├── main.css                 # Tailwind entry
│   ├── components/              # Component-specific styles
│   │   ├── button.css
│   │   ├── card.css
│   │   └── modal.css
│   └── dist/
│       └── main.min.css         # Compiled output
├── js/
│   ├── main.js                  # App entry point
│   ├── components/              # Component JavaScript
│   │   ├── modal-manager.js
│   │   ├── bracket-renderer.js
│   │   └── live-updates.js
│   └── utils/
│       ├── api.js               # Fetch wrapper
│       └── websocket.js         # WebSocket client
└── img/
    ├── logos/
    └── placeholders/

templates/
├── base.html                    # Base template
├── components/                  # Reusable components
│   ├── button.html
│   ├── card.html
│   ├── modal.html
│   ├── navbar.html
│   └── footer.html
├── tournaments/                 # Tournament templates
│   ├── list.html
│   ├── detail.html
│   └── create.html
└── partials/                    # HTMX partials
    ├── tournament_card.html
    ├── match_card.html
    └── payment_status.html
```

**Base Template (templates/base.html):**

```django
<!DOCTYPE html>
<html lang="{{ LANGUAGE_CODE }}" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}DeltaCrown{% endblock %}</title>
    
    <!-- Tailwind CSS -->
    <link rel="stylesheet" href="{% static 'css/dist/main.min.css' %}">
    
    <!-- Preconnect to CDNs -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    
    <!-- Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    
    {% block extra_head %}{% endblock %}
</head>
<body class="bg-bg-primary text-text-primary min-h-screen">
    <!-- Navbar -->
    {% include 'components/navbar.html' %}
    
    <!-- Main Content -->
    <main id="main-content" class="container mx-auto px-4 py-8">
        {% block content %}{% endblock %}
    </main>
    
    <!-- Footer -->
    {% include 'components/footer.html' %}
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    
    <!-- Alpine.js -->
    <script defer src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
    
    <!-- Custom JS -->
    <script src="{% static 'js/dist/main.min.js' %}"></script>
    
    {% block extra_scripts %}{% endblock %}
</body>
</html>
```

### 3.3 Design Token Implementation

**CSS Custom Properties (static/css/tokens.css):**

```css
:root {
  /* Color Tokens */
  --bg-primary: #0A0E1A;
  --bg-secondary: #151928;
  --bg-tertiary: #1F2937;
  --bg-hover: #2D3748;
  
  --brand-primary: #3B82F6;
  --brand-secondary: #8B5CF6;
  --brand-accent: #F59E0B;
  
  --success: #10B981;
  --warning: #F59E0B;
  --error: #EF4444;
  --info: #3B82F6;
  
  --text-primary: #F9FAFB;
  --text-secondary: #9CA3AF;
  --text-tertiary: #6B7280;
  
  /* Spacing */
  --space-xs: 0.25rem;    /* 4px */
  --space-sm: 0.5rem;     /* 8px */
  --space-md: 1rem;       /* 16px */
  --space-lg: 1.5rem;     /* 24px */
  --space-xl: 2rem;       /* 32px */
  --space-2xl: 3rem;      /* 48px */
  
  /* Border Radius */
  --radius-sm: 0.25rem;   /* 4px */
  --radius-md: 0.5rem;    /* 8px */
  --radius-lg: 0.75rem;   /* 12px */
  --radius-full: 9999px;
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  --shadow-xl: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  
  /* Animation Durations */
  --duration-instant: 100ms;
  --duration-fast: 150ms;
  --duration-base: 250ms;
  --duration-slow: 350ms;
  --duration-slower: 500ms;
  
  /* Easing */
  --ease-out: cubic-bezier(0, 0, 0.2, 1);
  --ease-in: cubic-bezier(0.4, 0, 1, 1);
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
}

/* Light theme overrides (optional) */
[data-theme="light"] {
  --bg-primary: #FFFFFF;
  --bg-secondary: #F3F4F6;
  --text-primary: #111827;
  --text-secondary: #4B5563;
}
```

**Tailwind Config Mapping:**

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        'bg': {
          primary: 'var(--bg-primary)',
          secondary: 'var(--bg-secondary)',
          tertiary: 'var(--bg-tertiary)',
          hover: 'var(--bg-hover)',
        },
        'brand': {
          primary: 'var(--brand-primary)',
          secondary: 'var(--brand-secondary)',
          accent: 'var(--brand-accent)',
        },
        'text': {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
        },
      },
      spacing: {
        'xs': 'var(--space-xs)',
        'sm': 'var(--space-sm)',
        'md': 'var(--space-md)',
        'lg': 'var(--space-lg)',
        'xl': 'var(--space-xl)',
        '2xl': 'var(--space-2xl)',
      },
      borderRadius: {
        'sm': 'var(--radius-sm)',
        'md': 'var(--radius-md)',
        'lg': 'var(--radius-lg)',
        'full': 'var(--radius-full)',
      },
      boxShadow: {
        'sm': 'var(--shadow-sm)',
        'md': 'var(--shadow-md)',
        'lg': 'var(--shadow-lg)',
        'xl': 'var(--shadow-xl)',
      },
      transitionDuration: {
        'instant': 'var(--duration-instant)',
        'fast': 'var(--duration-fast)',
        'base': 'var(--duration-base)',
        'slow': 'var(--duration-slow)',
        'slower': 'var(--duration-slower)',
      },
    },
  },
}
```

### 3.4 Core Component Examples

#### Button Component (templates/components/button.html)

```django
{% comment %}
Usage: {% include 'components/button.html' with variant='primary' size='md' text='Click Me' %}
Variants: primary, secondary, ghost, danger
Sizes: sm, md, lg
{% endcomment %}

<button 
    type="{{ type|default:'button' }}"
    class="
        btn
        {% if variant == 'primary' %}btn-primary{% endif %}
        {% if variant == 'secondary' %}btn-secondary{% endif %}
        {% if variant == 'ghost' %}btn-ghost{% endif %}
        {% if variant == 'danger' %}btn-danger{% endif %}
        {% if size == 'sm' %}btn-sm{% endif %}
        {% if size == 'lg' %}btn-lg{% endif %}
        {{ class }}
    "
    {% if disabled %}disabled{% endif %}
    {% if analytics_id %}data-analytics-id="{{ analytics_id }}"{% endif %}
    {% if hx_get %}hx-get="{{ hx_get }}"{% endif %}
    {% if hx_post %}hx-post="{{ hx_post }}"{% endif %}
    {% if hx_target %}hx-target="{{ hx_target }}"{% endif %}
    {{ attrs }}
>
    {% if icon %}
        <svg class="w-5 h-5 {% if text %}mr-2{% endif %}" fill="currentColor">
            <use href="#icon-{{ icon }}"></use>
        </svg>
    {% endif %}
    {{ text }}
    {% if slot %}{{ slot|safe }}{% endif %}
</button>
```

**Button CSS:**

```css
.btn {
  @apply inline-flex items-center justify-center font-medium rounded-lg transition-all duration-base;
  @apply focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-primary;
}

.btn-primary {
  @apply bg-brand-primary text-white hover:bg-blue-600 active:bg-blue-700;
}

.btn-secondary {
  @apply bg-brand-secondary text-white hover:bg-purple-600 active:bg-purple-700;
}

.btn-ghost {
  @apply bg-transparent text-text-secondary hover:bg-bg-hover hover:text-text-primary;
}

.btn-danger {
  @apply bg-error text-white hover:bg-red-600 active:bg-red-700;
}

.btn-sm {
  @apply px-3 py-1.5 text-sm;
}

.btn, .btn-md {
  @apply px-6 py-3 text-base;
}

.btn-lg {
  @apply px-8 py-4 text-lg;
}

.btn:disabled {
  @apply opacity-50 cursor-not-allowed;
}
```

#### Card Component (templates/components/card.html)

```django
<div class="card {{ class }}">
    {% if image %}
        <div class="card-image">
            <img src="{{ image }}" alt="{{ image_alt }}" loading="lazy">
            {% if badge %}
                <span class="card-badge {{ badge_class }}">{{ badge }}</span>
            {% endif %}
        </div>
    {% endif %}
    
    <div class="card-body">
        {% if title %}
            <h3 class="card-title">{{ title }}</h3>
        {% endif %}
        
        {% if description %}
            <p class="card-description">{{ description }}</p>
        {% endif %}
        
        {% if slot %}
            {{ slot|safe }}
        {% endif %}
    </div>
    
    {% if footer %}
        <div class="card-footer">
            {{ footer|safe }}
        </div>
    {% endif %}
</div>
```

**Card CSS:**

```css
.card {
  @apply bg-bg-secondary rounded-lg overflow-hidden shadow-md transition-all duration-base;
  @apply hover:shadow-lg hover:-translate-y-1;
}

.card-image {
  @apply relative w-full h-48 bg-bg-tertiary;
}

.card-image img {
  @apply w-full h-full object-cover;
}

.card-badge {
  @apply absolute top-2 right-2 px-2 py-1 rounded text-xs font-semibold;
}

.card-body {
  @apply p-4;
}

.card-title {
  @apply text-xl font-semibold text-text-primary mb-2;
}

.card-description {
  @apply text-text-secondary text-sm;
}

.card-footer {
  @apply px-4 pb-4 flex items-center justify-between;
}
```

### 3.5 HTMX Integration Patterns

**Example 1: Infinite Scroll (Tournament Listing)**

```django
<!-- templates/tournaments/list.html -->
<div id="tournament-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    {% for tournament in tournaments %}
        {% include 'partials/tournament_card.html' with tournament=tournament %}
    {% endfor %}
</div>

<!-- Load more trigger -->
{% if has_next_page %}
<div 
    hx-get="{% url 'tournaments:list' %}?page={{ next_page }}"
    hx-trigger="revealed"
    hx-swap="afterend"
    hx-target="#tournament-grid"
    class="text-center py-8"
>
    <div class="spinner"></div>
    <p class="text-text-secondary">Loading more tournaments...</p>
</div>
{% endif %}
```

**Example 2: Dynamic Filters**

```django
<!-- Filter form -->
<form 
    hx-get="{% url 'tournaments:list' %}"
    hx-trigger="change, submit"
    hx-target="#tournament-grid"
    hx-indicator="#loading-spinner"
    hx-push-url="true"
>
    <select name="game" class="form-select">
        <option value="">All Games</option>
        <option value="valorant">VALORANT</option>
        <option value="cs2">CS2</option>
    </select>
    
    <select name="status" class="form-select">
        <option value="">All Status</option>
        <option value="registration_open">Registration Open</option>
        <option value="ongoing">Ongoing</option>
    </select>
    
    <button type="submit" class="btn-primary">Apply Filters</button>
</form>

<div id="loading-spinner" class="htmx-indicator">
    <div class="spinner"></div>
</div>

<div id="tournament-grid">
    <!-- Results loaded here -->
</div>
```

**Example 3: Modal with HTMX**

```django
<!-- Trigger button -->
<button 
    hx-get="{% url 'tournaments:contact_organizer' tournament.id %}"
    hx-target="#modal-container"
    hx-swap="innerHTML"
    class="btn-primary"
    data-analytics-id="dc-btn-contact-organizer"
>
    Contact Organizer
</button>

<!-- Modal container (in base.html) -->
<div id="modal-container"></div>

<!-- Modal content (returned by HTMX) -->
<div class="modal" x-data="{ open: true }" x-show="open">
    <div class="modal-overlay" @click="open = false"></div>
    <div class="modal-content">
        <h2>Contact Organizer</h2>
        <form hx-post="{% url 'tournaments:send_message' %}" hx-target="this">
            <textarea name="message" required></textarea>
            <button type="submit" class="btn-primary">Send Message</button>
        </form>
        <button @click="open = false" class="btn-ghost">Cancel</button>
    </div>
</div>
```

### 3.6 WebSocket Client Implementation

**static/js/utils/websocket.js:**

```javascript
class LiveUpdateClient {
    constructor(tournamentId) {
        this.tournamentId = tournamentId;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 2000;
    }

    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/tournament/${this.tournamentId}/`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.sendPing();
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket closed');
            this.reconnect();
        };
    }

    handleMessage(data) {
        switch (data.type) {
            case 'match_update':
                this.updateMatchScore(data.match_id, data.score);
                break;
            case 'registration_update':
                this.updateRegistrationCount(data.count);
                break;
            case 'live_chat':
                this.appendChatMessage(data.message);
                break;
            case 'bracket_update':
                this.refreshBracket();
                break;
            default:
                console.warn('Unknown message type:', data.type);
        }
    }

    updateMatchScore(matchId, score) {
        const matchElement = document.querySelector(`[data-match-id="${matchId}"]`);
        if (matchElement) {
            matchElement.querySelector('.score-team-a').textContent = score.team_a;
            matchElement.querySelector('.score-team-b').textContent = score.team_b;
            
            // Animate score change
            matchElement.classList.add('score-updated');
            setTimeout(() => matchElement.classList.remove('score-updated'), 1000);
        }
    }

    updateRegistrationCount(count) {
        const countElement = document.getElementById('registration-count');
        if (countElement) {
            countElement.textContent = count;
        }
    }

    appendChatMessage(message) {
        const chatContainer = document.getElementById('live-chat');
        if (chatContainer) {
            const messageElement = document.createElement('div');
            messageElement.className = 'chat-message';
            messageElement.innerHTML = `
                <span class="chat-user">${message.username}:</span>
                <span class="chat-text">${message.text}</span>
            `;
            chatContainer.appendChild(messageElement);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    }

    refreshBracket() {
        // Use HTMX to refresh bracket
        htmx.ajax('GET', `/tournaments/${this.tournamentId}/bracket/`, {
            target: '#bracket-container',
            swap: 'innerHTML'
        });
    }

    sendPing() {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'ping' }));
            setTimeout(() => this.sendPing(), 30000); // Every 30 seconds
        }
    }

    reconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Reconnecting... Attempt ${this.reconnectAttempts}`);
            setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.error('Max reconnection attempts reached');
            // Show user notification
            alert('Connection lost. Please refresh the page.');
        }
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
        }
    }
}

// Usage
document.addEventListener('DOMContentLoaded', () => {
    const tournamentId = document.body.dataset.tournamentId;
    if (tournamentId) {
        const liveClient = new LiveUpdateClient(tournamentId);
        liveClient.connect();
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => liveClient.disconnect());
    }
});
```

### 3.7 Build Process & Optimization

**package.json scripts:**

```json
{
  "scripts": {
    "dev": "concurrently \"npm:watch:*\"",
    "watch:css": "tailwindcss -i ./static/css/main.css -o ./static/css/dist/main.css --watch",
    "watch:js": "webpack --mode development --watch",
    "build": "npm run build:css && npm run build:js",
    "build:css": "tailwindcss -i ./static/css/main.css -o ./static/css/dist/main.min.css --minify",
    "build:js": "webpack --mode production",
    "lint": "eslint static/js",
    "format": "prettier --write \"static/**/*.{js,css}\""
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "webpack": "^5.90.0",
    "webpack-cli": "^5.1.0",
    "terser-webpack-plugin": "^5.3.0",
    "concurrently": "^8.2.0",
    "eslint": "^8.56.0",
    "prettier": "^3.2.0"
  },
  "dependencies": {
    "htmx.org": "^1.9.10",
    "alpinejs": "^3.13.0",
    "chart.js": "^4.4.0"
  }
}
```

**Webpack Configuration (webpack.config.js):**

```javascript
const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');

module.exports = {
  entry: './static/js/main.js',
  output: {
    filename: 'main.min.js',
    path: path.resolve(__dirname, 'static/js/dist'),
  },
  optimization: {
    minimize: true,
    minimizer: [new TerserPlugin()],
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          priority: 10,
        },
      },
    },
  },
  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env'],
          },
        },
      },
    ],
  },
};
```

---

## 4. Backend Integration Points

### 4.1 Django Views Architecture

**View Types:**

| View Type | Use Case | Example | Response |
|-----------|----------|---------|----------|
| **Template View** | Full page render | Tournament listing | HTML template |
| **HTMX Partial** | Dynamic content | Filter results | HTML fragment |
| **API View** | Mobile app, SPA | Tournament detail | JSON |
| **WebSocket Consumer** | Real-time updates | Live match scores | WebSocket message |

**Example 1: Tournament Listing (Template + HTMX)**

```python
# apps/tournaments/views.py
from django.views.generic import ListView
from django.db.models import Q, Count
from .models import Tournament

class TournamentListView(ListView):
    model = Tournament
    template_name = 'tournaments/list.html'
    context_object_name = 'tournaments'
    paginate_by = 12
    
    def get_queryset(self):
        qs = Tournament.objects.filter(
            status__in=['PUBLISHED', 'REGISTRATION_OPEN', 'ONGOING']
        ).select_related(
            'organizer', 'game'
        ).prefetch_related(
            'registrations'
        ).annotate(
            registration_count=Count('registrations')
        )
        
        # Apply filters
        game = self.request.GET.get('game')
        if game:
            qs = qs.filter(game__slug=game)
        
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)
        
        search = self.request.GET.get('q')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return qs.order_by('-start_date')
    
    def get_template_names(self):
        # HTMX request returns partial
        if self.request.htmx:
            return ['partials/tournament_grid.html']
        return ['tournaments/list.html']
```

**Example 2: Tournament Detail (Full Page + API)**

```python
from django.views.generic import DetailView
from rest_framework.generics import RetrieveAPIView
from .serializers import TournamentDetailSerializer

class TournamentDetailView(DetailView):
    model = Tournament
    template_name = 'tournaments/detail.html'
    context_object_name = 'tournament'
    
    def get_queryset(self):
        return Tournament.objects.select_related(
            'organizer__user',
            'game',
        ).prefetch_related(
            'registrations__team',
            'custom_fields',
            'sponsors'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tournament = self.object
        
        # Check if user already registered
        if self.request.user.is_authenticated:
            context['user_registration'] = tournament.registrations.filter(
                team__members__user=self.request.user
            ).first()
        
        # Calculate spots remaining
        context['spots_remaining'] = (
            tournament.max_teams - tournament.registrations.count()
        )
        
        # Get upcoming matches
        context['upcoming_matches'] = tournament.matches.filter(
            status='SCHEDULED'
        ).select_related('team_a', 'team_b')[:5]
        
        return context

# API version for mobile/SPA
class TournamentDetailAPIView(RetrieveAPIView):
    queryset = Tournament.objects.all()
    serializer_class = TournamentDetailSerializer
    lookup_field = 'slug'
```

### 4.2 API Endpoint Mapping

**REST API Structure:**

```
/api/v1/
├── tournaments/
│   ├── GET    /                      # List tournaments (filtered)
│   ├── POST   /                      # Create tournament (organizer only)
│   ├── GET    /{slug}/               # Tournament detail
│   ├── PATCH  /{slug}/               # Update tournament (organizer only)
│   ├── DELETE /{slug}/               # Delete tournament (organizer only)
│   ├── POST   /{slug}/register/      # Submit registration
│   ├── GET    /{slug}/bracket/       # Get bracket data
│   └── GET    /{slug}/matches/       # List matches
├── registrations/
│   ├── GET    /                      # User's registrations
│   ├── GET    /{id}/                 # Registration detail
│   ├── POST   /{id}/payment/         # Submit payment proof
│   └── DELETE /{id}/                 # Withdraw registration
├── matches/
│   ├── GET    /{id}/                 # Match detail
│   ├── POST   /{id}/submit_result/   # Submit result
│   ├── POST   /{id}/dispute/         # Dispute result
│   └── POST   /{id}/predict/         # Submit prediction (spectator)
├── payments/
│   ├── GET    /                      # Admin: Pending payments
│   ├── POST   /{id}/approve/         # Admin: Approve payment
│   └── POST   /{id}/reject/          # Admin: Reject payment
├── certificates/
│   ├── GET    /{id}/                 # View certificate
│   ├── GET    /{id}/download/        # Download PDF
│   └── GET    /{id}/verify/          # Verify certificate
└── users/
    ├── GET    /profile/              # User profile
    ├── PATCH  /profile/              # Update profile
    └── GET    /stats/                # User statistics
```

**API Authentication:**

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    }
}
```

**Example API View with Permissions:**

```python
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Tournament, Registration
from .serializers import RegistrationSerializer
from .permissions import IsOrganizerOrReadOnly

class RegistrationViewSet(viewsets.ModelViewSet):
    serializer_class = RegistrationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Users see only their registrations
        if self.request.user.is_staff:
            return Registration.objects.all()
        return Registration.objects.filter(
            team__members__user=self.request.user
        )
    
    def create(self, request, *args, **kwargs):
        """Submit tournament registration"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Validate tournament capacity
        tournament = serializer.validated_data['tournament']
        if tournament.registrations.count() >= tournament.max_teams:
            return Response(
                {'error': 'Tournament is full'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate registration window
        if tournament.status != 'REGISTRATION_OPEN':
            return Response(
                {'error': 'Registration is not open'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def submit_payment(self, request, pk=None):
        """Upload payment proof"""
        registration = self.get_object()
        
        # Validate user owns this registration
        if not registration.team.members.filter(user=request.user).exists():
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        payment_proof = request.FILES.get('payment_proof')
        if not payment_proof:
            return Response(
                {'error': 'Payment proof required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        registration.payment_proof = payment_proof
        registration.payment_status = 'PENDING_VERIFICATION'
        registration.save()
        
        # Send notification to admins
        from .tasks import notify_payment_submitted
        notify_payment_submitted.delay(registration.id)
        
        return Response({'message': 'Payment submitted successfully'})
```

### 4.3 WebSocket Channel Configuration

**Django Channels Setup:**

```python
# settings.py
INSTALLED_APPS = [
    'daphne',  # Must be before django.contrib.staticfiles
    'django.contrib.staticfiles',
    'channels',
    # ...
]

ASGI_APPLICATION = 'deltacrown.asgi.application'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [('redis', 6379)],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}

# asgi.py
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from apps.tournaments import routing as tournament_routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(
            tournament_routing.websocket_urlpatterns
        )
    ),
})
```

**WebSocket Consumer Example:**

```python
# apps/tournaments/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Tournament, Match

class TournamentLiveConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.tournament_id = self.scope['url_route']['kwargs']['tournament_id']
        self.room_group_name = f'tournament_{self.tournament_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()
        
        # Send initial data
        tournament_data = await self.get_tournament_data()
        await self.send(text_data=json.dumps({
            'type': 'initial_data',
            'tournament': tournament_data
        }))
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        data = json.dumps(text_data)
        message_type = data.get('type')
        
        if message_type == 'ping':
            await self.send(text_data=json.dumps({'type': 'pong'}))
        
        elif message_type == 'chat_message':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': data['message'],
                    'username': self.scope['user'].username
                }
            )
    
    # Handler for match_update messages
    async def match_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'match_update',
            'match_id': event['match_id'],
            'score': event['score']
        }))
    
    # Handler for chat messages
    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'live_chat',
            'message': {
                'username': event['username'],
                'text': event['message']
            }
        }))
    
    @database_sync_to_async
    def get_tournament_data(self):
        tournament = Tournament.objects.get(id=self.tournament_id)
        return {
            'id': tournament.id,
            'title': tournament.title,
            'status': tournament.status,
            'registration_count': tournament.registrations.count()
        }

# Broadcasting match updates from views
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def broadcast_match_update(match):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'tournament_{match.tournament_id}',
        {
            'type': 'match_update',
            'match_id': match.id,
            'score': {
                'team_a': match.score_team_a,
                'team_b': match.score_team_b
            }
        }
    )
```

**URL Routing:**

```python
# apps/tournaments/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(
        r'ws/tournament/(?P<tournament_id>\d+)/$',
        consumers.TournamentLiveConsumer.as_asgi()
    ),
]
```

### 4.4 Database Query Optimization

**Common Optimization Patterns:**

```python
# ❌ Bad: N+1 query problem
tournaments = Tournament.objects.all()
for tournament in tournaments:
    print(tournament.organizer.username)  # Extra query per tournament
    print(tournament.registrations.count())  # Extra query per tournament

# ✅ Good: Use select_related and prefetch_related
tournaments = Tournament.objects.select_related(
    'organizer',  # ForeignKey
    'game'
).prefetch_related(
    'registrations',  # ManyToMany or reverse ForeignKey
    'sponsors'
).annotate(
    registration_count=Count('registrations')
)

# ✅ Good: Prefetch with custom queryset
from django.db.models import Prefetch

tournaments = Tournament.objects.prefetch_related(
    Prefetch(
        'registrations',
        queryset=Registration.objects.filter(
            payment_status='APPROVED'
        ).select_related('team')
    )
)

# ✅ Good: Use only() and defer() for large models
tournaments = Tournament.objects.only(
    'id', 'title', 'start_date', 'status'
)  # Only fetch these fields

# ✅ Good: Database indexes (in models)
class Tournament(models.Model):
    title = models.CharField(max_length=200, db_index=True)
    status = models.CharField(max_length=20, db_index=True)
    start_date = models.DateTimeField(db_index=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['status', 'start_date']),  # Composite index
            models.Index(fields=['-created_at']),  # Descending order
        ]
```

**Caching Strategy:**

```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page

# Cache entire view response (5 minutes)
@cache_page(60 * 5)
def tournament_list(request):
    # ...
    pass

# Cache specific queryset
def get_featured_tournaments():
    cache_key = 'featured_tournaments'
    tournaments = cache.get(cache_key)
    
    if tournaments is None:
        tournaments = Tournament.objects.filter(
            is_featured=True,
            status='REGISTRATION_OPEN'
        ).select_related('organizer', 'game')[:6]
        
        cache.set(cache_key, tournaments, 60 * 10)  # 10 minutes
    
    return tournaments

# Invalidate cache on update
from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=Tournament)
def invalidate_tournament_cache(sender, instance, **kwargs):
    cache.delete('featured_tournaments')
    cache.delete(f'tournament_{instance.id}')
```

### 4.5 Background Tasks with Celery

**Celery Setup:**

```python
# deltacrown/celery.py
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'deltacrown.settings')

app = Celery('deltacrown')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# settings.py
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Dhaka'
```

**Example Background Tasks:**

```python
# apps/tournaments/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from .models import Tournament, Registration, Certificate
from .utils import generate_certificate_pdf

@shared_task
def send_payment_approval_email(registration_id):
    """Send email when payment approved"""
    registration = Registration.objects.select_related(
        'team', 'tournament'
    ).get(id=registration_id)
    
    send_mail(
        subject=f'Payment Approved - {registration.tournament.title}',
        message=f'Your payment has been approved. You are now registered!',
        from_email='noreply@deltacrown.com',
        recipient_list=[registration.team.captain.email],
        fail_silently=False,
    )

@shared_task
def generate_certificates_for_tournament(tournament_id):
    """Generate certificates for all winners (runs after tournament ends)"""
    tournament = Tournament.objects.get(id=tournament_id)
    
    # Get top 3 teams
    winners = tournament.get_winners()  # Custom method
    
    for rank, team in enumerate(winners, start=1):
        for player in team.members.all():
            certificate = Certificate.objects.create(
                tournament=tournament,
                player=player.user,
                rank=rank,
                verification_code=Certificate.generate_code()
            )
            
            # Generate PDF
            pdf_data = generate_certificate_pdf(certificate)
            certificate.pdf_file.save(
                f'cert_{certificate.id}.pdf',
                pdf_data
            )
    
    return f'Generated {len(winners)} certificates'

@shared_task
def check_tournament_start_times():
    """Cron job: Check for tournaments that should start (runs every minute)"""
    from django.utils import timezone
    now = timezone.now()
    
    tournaments = Tournament.objects.filter(
        status='REGISTRATION_OPEN',
        start_time__lte=now
    )
    
    for tournament in tournaments:
        tournament.status = 'ONGOING'
        tournament.save()
        
        # Generate brackets
        from .bracket_generator import generate_bracket
        generate_bracket(tournament)
        
        # Notify participants
        notify_tournament_started.delay(tournament.id)
    
    return f'Started {tournaments.count()} tournaments'

# Celery Beat schedule (periodic tasks)
from celery.schedules import crontab

app.conf.beat_schedule = {
    'check-tournament-starts': {
        'task': 'apps.tournaments.tasks.check_tournament_start_times',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
    'send-check-in-reminders': {
        'task': 'apps.tournaments.tasks.send_check_in_reminders',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
}
```

### 4.6 Model-View-Template Flow Examples

**Example: Registration Submission Flow**

```
1. User clicks "Register Now" button
   └─> Frontend: HTMX POST request
       └─> Backend: RegistrationViewSet.create()
           ├─> Validate tournament capacity
           ├─> Validate registration window
           ├─> Create Registration instance
           ├─> Trigger Celery task: send_confirmation_email.delay()
           └─> Return: JSON response or HTML partial
               └─> Frontend: Display confirmation modal + analytics tracking

2. User uploads payment proof
   └─> Frontend: File upload with progress bar
       └─> Backend: RegistrationViewSet.submit_payment()
           ├─> Upload file to S3 / local storage
           ├─> Update payment_status = 'PENDING_VERIFICATION'
           ├─> Trigger Celery task: notify_admin_payment.delay()
           └─> Return: Success message
               └─> Frontend: Show "Payment submitted" confirmation

3. Admin reviews payment
   └─> Frontend: Admin panel click "Approve"
       └─> Backend: PaymentViewSet.approve()
           ├─> Update payment_status = 'APPROVED'
           ├─> Increment registration count
           ├─> Trigger Celery task: send_approval_email.delay()
           ├─> Broadcast WebSocket: registration_update
           └─> Return: Updated payment status
               └─> Frontend: Badge changes to green "Approved"
```

**Database Transaction Example:**

```python
from django.db import transaction

@transaction.atomic
def submit_match_result(match_id, score_team_a, score_team_b, submitted_by):
    """Atomic transaction for match result submission"""
    match = Match.objects.select_for_update().get(id=match_id)
    
    # Validate match state
    if match.status != 'IN_PROGRESS':
        raise ValueError('Match is not in progress')
    
    # Update match
    match.score_team_a = score_team_a
    match.score_team_b = score_team_b
    match.result_submitted_by = submitted_by
    match.status = 'AWAITING_CONFIRMATION'
    match.save()
    
    # Determine winner
    if score_team_a > score_team_b:
        winner = match.team_a
    elif score_team_b > score_team_a:
        winner = match.team_b
    else:
        raise ValueError('Scores cannot be equal')
    
    # Create match history entry
    MatchHistory.objects.create(
        match=match,
        action='RESULT_SUBMITTED',
        data={'score_a': score_team_a, 'score_b': score_team_b},
        user=submitted_by
    )
    
    # Update bracket (if opponent confirms)
    if match.result_confirmed:
        next_match = match.bracket.get_next_match(match)
        if next_match:
            next_match.assign_team(winner)
            next_match.save()
    
    return match
```

---

## 5. Testing & QA Strategy

### 5.1 Testing Pyramid

```
           /\
          /E2E\         10% - End-to-End (Cypress)
         /______\
        /  API   \       20% - Integration (pytest-django)
       /__________\
      /   Unit     \     70% - Unit Tests (pytest, Jest)
     /______________\
```

**Test Coverage Targets:**
- Backend: >80% coverage
- Frontend: >70% coverage
- Critical paths: 100% coverage (payment, registration, bracket)

### 5.2 Backend Testing

**Unit Tests (pytest + pytest-django):**

```python
# tests/test_tournament_registration.py
import pytest
from apps.tournaments.models import Tournament, Registration
from apps.teams.models import Team

@pytest.mark.django_db
class TestTournamentRegistration:
    
    def test_registration_success(self, tournament, team):
        """Test successful tournament registration"""
        registration = Registration.objects.create(
            tournament=tournament,
            team=team,
            payment_status='PENDING'
        )
        assert registration.id is not None
        assert registration.tournament == tournament
        assert registration.payment_status == 'PENDING'
    
    def test_registration_capacity_limit(self, tournament_full, team):
        """Test registration rejected when tournament full"""
        with pytest.raises(ValidationError):
            tournament_full.register_team(team)
    
    def test_payment_approval_flow(self, registration):
        """Test payment approval updates status"""
        registration.approve_payment()
        registration.refresh_from_db()
        
        assert registration.payment_status == 'APPROVED'
        assert registration.approved_at is not None

# conftest.py (fixtures)
import pytest
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def user():
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def tournament():
    from apps.tournaments.models import Tournament
    return Tournament.objects.create(
        title='Test Tournament',
        max_teams=16,
        status='REGISTRATION_OPEN'
    )

@pytest.fixture
def team(user):
    from apps.teams.models import Team
    return Team.objects.create(
        name='Test Team',
        captain=user
    )
```

**API Tests:**

```python
# tests/test_api_tournaments.py
import pytest
from rest_framework.test import APIClient
from rest_framework import status

@pytest.mark.django_db
class TestTournamentAPI:
    
    def setup_method(self):
        self.client = APIClient()
    
    def test_list_tournaments(self, tournament):
        """Test GET /api/v1/tournaments/"""
        response = self.client.get('/api/v1/tournaments/')
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
    
    def test_create_tournament_requires_auth(self):
        """Test POST /api/v1/tournaments/ requires authentication"""
        response = self.client.post('/api/v1/tournaments/', {})
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_register_team(self, user, tournament, team):
        """Test POST /api/v1/tournaments/{id}/register/"""
        self.client.force_authenticate(user=user)
        
        response = self.client.post(
            f'/api/v1/tournaments/{tournament.id}/register/',
            {'team_id': team.id}
        )
        
        assert response.status_code == status.HTTP_201_CREATED
        assert tournament.registrations.count() == 1
```

### 5.3 Frontend Testing

**Component Tests (Jest + Testing Library):**

```javascript
// __tests__/components/Button.test.js
import { render, screen, fireEvent } from '@testing-library/dom';
import { Button } from '@/components/Button';

describe('Button Component', () => {
    test('renders with text', () => {
        render(Button({ text: 'Click Me' }));
        expect(screen.getByText('Click Me')).toBeInTheDocument();
    });
    
    test('calls onClick handler', () => {
        const handleClick = jest.fn();
        render(Button({ text: 'Click Me', onClick: handleClick }));
        
        fireEvent.click(screen.getByText('Click Me'));
        expect(handleClick).toHaveBeenCalledTimes(1);
    });
    
    test('applies variant classes', () => {
        const { container } = render(Button({ variant: 'primary' }));
        expect(container.firstChild).toHaveClass('btn-primary');
    });
});
```

### 5.4 End-to-End Tests (Cypress)

```javascript
// cypress/e2e/tournament_registration.cy.js
describe('Tournament Registration Flow', () => {
    beforeEach(() => {
        cy.login('testuser@example.com', 'password123');
    });
    
    it('completes full registration flow', () => {
        // Navigate to tournament
        cy.visit('/tournaments');
        cy.contains('Test Tournament').click();
        
        // Click register button
        cy.get('[data-analytics-id="dc-btn-register"]').click();
        
        // Fill registration form
        cy.get('#team-name').type('Team Alpha');
        cy.get('#player1-ign').type('Player1');
        cy.get('#player1-phone').type('01700000000');
        
        // Submit registration
        cy.get('[data-analytics-id="dc-btn-submit-registration"]').click();
        
        // Verify confirmation
        cy.contains('Registration Successful').should('be.visible');
        
        // Upload payment proof
        cy.get('[data-analytics-id="dc-input-payment-proof"]')
            .attachFile('payment_proof.png');
        
        cy.get('[data-analytics-id="dc-btn-submit-payment"]').click();
        
        // Verify success message
        cy.contains('Payment submitted').should('be.visible');
    });
});
```

### 5.5 Accessibility Testing

**axe-core Integration:**

```javascript
// cypress/e2e/accessibility.cy.js
describe('Accessibility Tests', () => {
    it('tournament listing page has no violations', () => {
        cy.visit('/tournaments');
        cy.injectAxe();
        cy.checkA11y();
    });
    
    it('registration form has no violations', () => {
        cy.visit('/tournaments/test-tournament');
        cy.get('[data-analytics-id="dc-btn-register"]').click();
        cy.injectAxe();
        cy.checkA11y();
    });
});
```

### 5.6 Performance Testing

**Lighthouse CI Configuration:**

```javascript
// lighthouserc.js
module.exports = {
    ci: {
        collect: {
            url: [
                'http://localhost:8000/',
                'http://localhost:8000/tournaments/',
                'http://localhost:8000/tournaments/test-tournament/'
            ],
            numberOfRuns: 3,
        },
        assert: {
            assertions: {
                'categories:performance': ['error', { minScore: 0.9 }],
                'categories:accessibility': ['error', { minScore: 1.0 }],
                'first-contentful-paint': ['error', { maxNumericValue: 2000 }],
                'largest-contentful-paint': ['error', { maxNumericValue: 2500 }],
                'cumulative-layout-shift': ['error', { maxNumericValue: 0.1 }],
            },
        },
    },
};
```

### 5.7 Test Coverage Requirements

| Component | Unit | Integration | E2E | Accessibility |
|-----------|------|-------------|-----|---------------|
| **Auth System** | ✅ 90% | ✅ Yes | ✅ Login flow | ✅ Forms |
| **Tournament CRUD** | ✅ 85% | ✅ Yes | ✅ Full flow | ✅ All pages |
| **Registration** | ✅ 100% | ✅ Yes | ✅ Full flow | ✅ Forms |
| **Payment** | ✅ 100% | ✅ Yes | ✅ Upload flow | ✅ Admin panel |
| **Bracket** | ✅ 90% | ✅ Yes | ✅ Display | ✅ Navigation |
| **Match Results** | ✅ 85% | ✅ Yes | ✅ Submission | ✅ Forms |
| **WebSocket** | ✅ 70% | ✅ Yes | ✅ Live updates | N/A |
| **Certificates** | ✅ 80% | ✅ Yes | ✅ Download | ✅ View page |

---

## 6. Deployment & DevOps

### 6.1 CI/CD Pipeline (GitHub Actions)

**.github/workflows/ci.yml:**

```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-django pytest-cov
      
      - name: Run tests
        env:
          DATABASE_URL: postgresql://postgres:postgres@localhost/test_db
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest --cov=apps --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  frontend-build:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run linter
        run: npm run lint
      
      - name: Build assets
        run: npm run build
      
      - name: Run Lighthouse CI
        run: |
          npm install -g @lhci/cli
          lhci autorun
  
  deploy-staging:
    needs: [test, frontend-build]
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    
    steps:
      - name: Deploy to staging
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.STAGING_HOST }}
          username: ${{ secrets.STAGING_USER }}
          key: ${{ secrets.STAGING_SSH_KEY }}
          script: |
            cd /var/www/deltacrown-staging
            git pull origin develop
            docker-compose up -d --build
            docker-compose exec web python manage.py migrate
            docker-compose exec web python manage.py collectstatic --noinput
  
  deploy-production:
    needs: [test, frontend-build]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    
    steps:
      - name: Deploy to production (blue-green)
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.PROD_HOST }}
          username: ${{ secrets.PROD_USER }}
          key: ${{ secrets.PROD_SSH_KEY }}
          script: |
            cd /var/www/deltacrown
            ./deploy.sh
```

### 6.2 Docker Configuration

**docker-compose.yml:**

```yaml
version: '3.9'

services:
  web:
    build: .
    command: gunicorn deltacrown.wsgi:application --bind 0.0.0.0:8000 --workers 4
    volumes:
      - .:/app
      - static_volume:/app/static
      - media_volume:/app/media
    env_file:
      - .env
    depends_on:
      - db
      - redis
    networks:
      - app-network
  
  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    env_file:
      - .env
    networks:
      - app-network
  
  redis:
    image: redis:7
    networks:
      - app-network
  
  celery:
    build: .
    command: celery -A deltacrown worker -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - db
      - redis
    networks:
      - app-network
  
  celery-beat:
    build: .
    command: celery -A deltacrown beat -l info
    volumes:
      - .:/app
    env_file:
      - .env
    depends_on:
      - redis
    networks:
      - app-network
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/static
      - media_volume:/app/media
      - ./certbot/conf:/etc/letsencrypt
      - ./certbot/www:/var/www/certbot
    depends_on:
      - web
    networks:
      - app-network

volumes:
  postgres_data:
  static_volume:
  media_volume:

networks:
  app-network:
    driver: bridge
```

### 6.3 Deployment Script (Blue-Green)

**deploy.sh:**

```bash
#!/bin/bash
set -e

# Configuration
APP_DIR="/var/www/deltacrown"
BLUE_PORT=8000
GREEN_PORT=8001
NGINX_CONF="/etc/nginx/sites-enabled/deltacrown"

# Determine current active environment
CURRENT=$(grep -oP 'proxy_pass.*:\K\d+' $NGINX_CONF)

if [ "$CURRENT" == "$BLUE_PORT" ]; then
    NEW_PORT=$GREEN_PORT
    NEW_ENV="green"
    OLD_ENV="blue"
else
    NEW_PORT=$BLUE_PORT
    NEW_ENV="blue"
    OLD_ENV="red"
fi

echo "Current: $OLD_ENV ($CURRENT) -> Deploying: $NEW_ENV ($NEW_PORT)"

# Pull latest code
cd $APP_DIR
git pull origin main

# Build new environment
docker-compose -f docker-compose.$NEW_ENV.yml up -d --build

# Wait for health check
echo "Waiting for $NEW_ENV environment to be healthy..."
for i in {1..30}; do
    if curl -f http://localhost:$NEW_PORT/healthz/; then
        echo "$NEW_ENV is healthy!"
        break
    fi
    if [ $i == 30 ]; then
        echo "$NEW_ENV failed to start!"
        exit 1
    fi
    sleep 2
done

# Switch nginx to new environment
sed -i "s/:$CURRENT/:$NEW_PORT/" $NGINX_CONF
sudo nginx -t && sudo nginx -s reload

echo "Traffic switched to $NEW_ENV"

# Wait 30 seconds for connections to drain
sleep 30

# Stop old environment
docker-compose -f docker-compose.$OLD_ENV.yml down

echo "Deployment complete! $NEW_ENV is now serving traffic."
```

### 6.4 Monitoring & Logging

**Sentry Configuration:**

```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn=os.environ.get('SENTRY_DSN'),
    integrations=[DjangoIntegration()],
    traces_sample_rate=0.1,
    send_default_pii=True,
    environment=os.environ.get('ENVIRONMENT', 'development'),
)
```

**Prometheus Metrics:**

```python
# apps/core/middleware.py
from prometheus_client import Counter, Histogram
import time

request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

class MetricsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time
        
        request_count.labels(request.method, request.path).inc()
        request_duration.observe(duration)
        
        return response
```

---

## 7. Team Structure & Responsibilities

### 7.1 Development Roles

| Role | Team Member | Responsibilities | Key Deliverables |
|------|-------------|------------------|------------------|
| **Frontend Lead** | Dev 1 | Component library, HTMX integration | Tailwind setup, core components |
| **Frontend Dev** | Dev 2 | Page implementations, animations | Tournament screens, player dashboard |
| **Backend Lead** | Dev 3 | Django apps, API design | Models, serializers, viewsets |
| **Backend Dev** | Dev 4 | Business logic, Celery tasks | Bracket generation, payment flow |
| **Full-stack** | Dev 5 | Bridge frontend/backend, WebSocket | Real-time features, troubleshooting |
| **QA Engineer** | QA 1 | Test automation, manual testing | Test suite, bug reports |
| **DevOps** | DevOps 1 (0.5 FTE) | CI/CD, infrastructure | Deployment pipeline, monitoring |
| **Designer** | Designer 1 (0.5 FTE) | Figma mockups, asset export | High-fidelity designs, icons |
| **PM** | PM 1 (0.5 FTE) | Sprint planning, stakeholder comms | Sprint reports, roadmap |

### 7.2 Communication Channels

**Daily Standup (15 min):**
- Time: 10:00 AM (Bangladesh time)
- Format: What I did yesterday, what I'll do today, blockers
- Platform: Slack huddle or Zoom

**Sprint Planning (2 hours):**
- Frequency: Every 2 weeks (Monday)
- Agenda: Review previous sprint, plan next sprint, assign tasks
- Artifacts: Sprint backlog, story point estimates

**Sprint Review (1 hour):**
- Frequency: End of sprint (Friday)
- Agenda: Demo completed features, gather feedback
- Attendees: Team + stakeholders

**Retrospective (1 hour):**
- Frequency: After sprint review
- Format: What went well, what didn't, action items
- Tools: Miro board

**Tech Sync (1 hour):**
- Frequency: Weekly (Wednesday)
- Topics: Architecture decisions, code reviews, technical blockers
- Attendees: Developers only

### 7.3 Development Workflow

```
1. Task Assignment (Jira)
   ├─> Create branch: feature/FE-001-button-component
   ├─> Implement feature
   ├─> Write tests (80% coverage)
   └─> Local testing

2. Code Review (GitHub PR)
   ├─> Create pull request
   ├─> CI/CD runs (tests, lint, build)
   ├─> Code review (2 approvals required)
   └─> Address feedback

3. Merge & Deploy
   ├─> Merge to develop branch
   ├─> Auto-deploy to staging
   ├─> QA testing on staging
   └─> Merge to main (production)
```

---

## 8. Integration Checklist & Dependencies

### 8.1 Part 2 (Architecture) Integration

| Architecture Component | Implementation Status | Location | Notes |
|------------------------|----------------------|----------|-------|
| **Django Apps** | ✅ Structure defined | `apps/` folder | See Sprint 1 tasks |
| **REST API** | ✅ Endpoints mapped | Section 4.2 | DRF viewsets |
| **WebSocket** | ✅ Channels configured | Section 4.3 | Django Channels + Redis |
| **Celery Tasks** | ✅ Task list defined | Section 4.5 | Email, certificates, cron jobs |
| **Database Schema** | ✅ Models created | Part 3 reference | Migrations in Sprint 1-2 |
| **Authentication** | ✅ JWT + Session | Section 4.2 | Allauth integration |
| **File Storage** | 🔄 S3 or local | Sprint 3 | Payment proofs, certificates |
| **Email Service** | 🔄 SMTP or SendGrid | Sprint 3 | Notifications |

### 8.2 Part 3 (Database) Integration

| Database Model | Sprint | Dependencies | Status |
|----------------|--------|--------------|--------|
| **User & Profile** | Sprint 1 | Auth system | ✅ Core |
| **Tournament** | Sprint 2 | User | ✅ Core |
| **Game Config** | Sprint 2 | - | ✅ Core |
| **Registration** | Sprint 3 | Tournament, Team | ✅ Phase 2 |
| **Payment** | Sprint 3 | Registration | ✅ Phase 2 |
| **Bracket** | Sprint 4 | Tournament | ✅ Phase 2 |
| **Match** | Sprint 4 | Bracket, Team | ✅ Phase 2 |
| **Certificate** | Sprint 6 | Tournament, User | ✅ Phase 3 |
| **Discussion** | Sprint 6 | Tournament, User | ✅ Phase 3 |
| **Notification** | Sprint 5 | User | ✅ Phase 3 |

### 8.3 Part 4 (UI/UX) Integration

| UI Component | Frontend Task | Backend API | Status |
|--------------|---------------|-------------|--------|
| **Navbar** | FE-002 | `/api/v1/users/profile/` | ✅ Sprint 1 |
| **Tournament Card** | FE-010 | `/api/v1/tournaments/` | ✅ Sprint 2 |
| **Registration Form** | FE-018 | `/api/v1/registrations/` | ✅ Sprint 3 |
| **Payment Panel** | FE-021 | `/api/v1/payments/` | ✅ Sprint 3 |
| **Bracket Display** | FE-026 | `/api/v1/tournaments/{id}/bracket/` | ✅ Sprint 4 |
| **Match Card** | FE-028 | `/api/v1/matches/{id}/` | ✅ Sprint 4 |
| **Live HUD** | FE-034 | WebSocket consumer | ✅ Sprint 5 |
| **Certificate View** | FE-044 | `/api/v1/certificates/{id}/` | ✅ Sprint 6 |

---

## 9. Post-Launch & Iteration Plan

### 9.1 Monitoring Metrics

**Application Metrics (DataDog/Prometheus):**

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| **Request Rate** | 100 req/s | >500 req/s |
| **Error Rate** | <1% | >5% (5 min) |
| **Response Time (p95)** | <200ms | >500ms |
| **WebSocket Connections** | 100+ concurrent | Connection drops >10/min |
| **Celery Queue Length** | <50 | >500 tasks pending |
| **Database Connections** | <80% pool | >90% pool usage |

**Business Metrics (Google Analytics 4):**

| Metric | Week 1 Target | Month 1 Target |
|--------|---------------|----------------|
| **Tournaments Created** | 10 | 100 |
| **Teams Registered** | 50 | 500 |
| **Payment Submissions** | 40 | 400 |
| **Certificates Issued** | 20 | 200 |
| **Active Users (DAU)** | 100 | 1,000 |
| **Spectator Views** | 200 | 2,000 |

### 9.2 User Feedback Collection

**In-App Feedback Widget:**
- Location: Bottom-right corner (all pages)
- Types: Bug report, feature request, general feedback
- Integration: Typeform or Google Forms

**Post-Tournament Survey:**
- Trigger: 24 hours after tournament completion
- Questions: Satisfaction (1-5), improvements, issues
- Incentive: Entry into raffle for ৳500 DeltaCoin

**Beta User Interviews:**
- Frequency: Weekly (first month)
- Participants: 5-10 organizers and players
- Format: 30-minute video call, structured questions

### 9.3 Feature Iteration Roadmap

**Phase 5 (Weeks 17-20): Post-Launch Improvements**

Based on user feedback:

| Feature | Priority | Effort | Impact |
|---------|----------|--------|--------|
| **Mobile App (PWA)** | High | 8 weeks | High |
| **Advanced Analytics Dashboard** | Medium | 4 weeks | Medium |
| **Sponsor Management Module** | Medium | 3 weeks | High (revenue) |
| **Team Rankings System** | High | 2 weeks | Medium |
| **Discord Bot Integration** | Low | 2 weeks | Medium |
| **Payment Gateway (bKash API)** | High | 6 weeks | High (automation) |
| **Automated Bracket Broadcasting** | Medium | 4 weeks | Medium |

### 9.4 Maintenance Schedule

**Daily:**
- Monitor error logs (Sentry)
- Check server health (uptime, CPU, memory)
- Review user feedback submissions

**Weekly:**
- Database backup verification
- Dependency security updates
- Performance report review

**Monthly:**
- Full security audit
- Database optimization (vacuum, reindex)
- User analytics report
- Stakeholder update meeting

### 9.5 Scaling Plan

**When to Scale (Triggers):**
- >500 concurrent users (current: 100)
- >1,000 tournaments/month (current: 100)
- Response time >500ms (current: <200ms)

**Scaling Actions:**
- **Horizontal scaling:** Add 2 more web servers (load balanced)
- **Database:** Upgrade to 8GB RAM, read replicas
- **CDN:** Enable full CDN for static/media (Cloudflare)
- **Cache layer:** Expand Redis cache (8GB)

---

## 10. Appendix: Technical Reference

### 10.1 Key Dependencies

**Python (requirements.txt):**
```
Django==4.2.7
djangorestframework==3.14.0
django-allauth==0.57.0
django-cors-headers==4.3.0
djangorestframework-simplejwt==5.3.0
channels==4.0.0
channels-redis==4.1.0
celery==5.3.4
redis==5.0.1
psycopg2-binary==2.9.9
Pillow==10.1.0
gunicorn==21.2.0
sentry-sdk==1.38.0
pytest==7.4.3
pytest-django==4.7.0
pytest-cov==4.1.0
```

**JavaScript (package.json):**
```json
{
  "dependencies": {
    "htmx.org": "^1.9.10",
    "alpinejs": "^3.13.3",
    "chart.js": "^4.4.0"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.32",
    "autoprefixer": "^10.4.16",
    "webpack": "^5.89.0",
    "@tailwindcss/forms": "^0.5.7",
    "@tailwindcss/typography": "^0.5.10"
  }
}
```

### 10.2 Environment Variables

**.env.example:**
```bash
# Django
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=deltacrown.com,www.deltacrown.com

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/deltacrown

# Redis
REDIS_URL=redis://localhost:6379/0

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@deltacrown.com
EMAIL_HOST_PASSWORD=your-password

# AWS S3 (optional)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_STORAGE_BUCKET_NAME=deltacrown-media

# Sentry
SENTRY_DSN=https://your-sentry-dsn

# Environment
ENVIRONMENT=production
```

### 10.3 Useful Commands

```bash
# Development
python manage.py runserver
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py shell_plus

# Testing
pytest
pytest --cov=apps
pytest -v -s tests/test_tournaments.py

# Frontend
npm run dev
npm run build
npm run lint

# Celery
celery -A deltacrown worker -l info
celery -A deltacrown beat -l info

# Docker
docker-compose up -d
docker-compose logs -f web
docker-compose exec web python manage.py migrate
docker-compose down

# Deployment
./deploy.sh
python manage.py collectstatic --noinput
python manage.py compress
```

---

## Conclusion

This Implementation Roadmap provides a comprehensive, actionable plan for building the DeltaCrown Tournament Engine over 16 weeks. Key achievements:

✅ **4 phases, 8 sprints** with detailed task breakdown (200+ tasks)  
✅ **Clear dependencies** mapped across Parts 2-4  
✅ **Testing strategy** with 80%+ coverage targets  
✅ **CI/CD pipeline** with blue-green deployment  
✅ **Team structure** with defined roles and workflows  
✅ **Post-launch plan** with monitoring, feedback, and iteration  

**Next Steps:**
1. ✅ **Sprint 0 (Prep Week):** Set up repositories, tools, environments
2. ✅ **Sprint 1 (Week 1-2):** Begin Phase 1 - Foundation
3. 📈 **Track Progress:** Daily standups, weekly demos, sprint reviews
4. 🚀 **Launch (Week 16):** Production deployment + marketing campaign

**Success Metrics:**
- Timeline: On schedule (±1 week acceptable)
- Quality: <5 P2 bugs in first week of production
- Performance: Lighthouse scores >90
- User satisfaction: >80% positive feedback from beta users

---

**Document Status:** ✅ **COMPLETE** - Ready for Team Review  
**Total Pages:** 100+ (comprehensive implementation guide)  
**Word Count:** ~15,000 words  
**Prepared by:** Implementation Team  
**Review Date:** November 3, 2025  
**Approved for Execution:** Pending stakeholder sign-off
