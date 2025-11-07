# Plan ↔ Implementation Map (Human-Readable)

This file maps each Phase/Module to the exact Planning doc sections used.

## Example Format
- Phase 4 → Module 4.2 Match Management & Scheduling
  - Implements:
    - PART_2.2_SERVICES_INTEGRATION.md#match-services
    - PART_3.1_DATABASE_DESIGN_ERD.md#match-model
    - PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md#match-admin
    - PART_2.3_REALTIME_SECURITY.md#websocket-channels
  - ADRs: ADR-001 Service Layer, ADR-007 Channels (Documents/ExecutionPlan/01_ARCHITECTURE_DECISIONS.md)

---

## Phase 0: Repository Guardrails & Scaffolding

### Module 0.1: Traceability & CI Setup
- Implements:
  - Documents/ExecutionPlan/00_MASTER_EXECUTION_PLAN.md#phase-0
  - Documents/ExecutionPlan/02_TECHNICAL_STANDARDS.md
- ADRs: None (foundational setup)
- Files Created:
  - Documents/ExecutionPlan/MAP.md (this file)
  - Documents/ExecutionPlan/trace.yml
  - .pre-commit-config.yaml
  - .github/workflows/ci.yml
  - scripts/verify_trace.py
  - .github/PULL_REQUEST_TEMPLATE.md
  - .github/ISSUE_TEMPLATE/module_task.md
  - .github/CODEOWNERS

---

## Phase 1: Core Models & Database

### Module 1.1: Base Models & Infrastructure
*[To be filled when implementation starts]*

### Module 1.2: Tournament & Game Models
*[To be filled when implementation starts]*

### Module 1.3: Registration & Payment Models
*[To be filled when implementation starts]*

### Module 1.4: Bracket & Match Models
*[To be filled when implementation starts]*

### Module 1.5: Supporting Models
*[To be filled when implementation starts]*

---

## Phase 2: Tournament Before (Creation & Discovery)

### Module 2.1: Tournament CRUD Services
*[To be filled when implementation starts]*

### Module 2.2: Game Configurations & Custom Fields
*[To be filled when implementation starts]*

### Module 2.3: Tournament Templates System
*[To be filled when implementation starts]*

### Module 2.4: Tournament Discovery & Filtering
*[To be filled when implementation starts]*

### Module 2.5: Organizer Dashboard
*[To be filled when implementation starts]*

---

## Phase 3: Tournament During (Registration & Participation)

### Module 3.1: Registration Flow & Validation
*[To be filled when implementation starts]*

### Module 3.2: Payment Processing & Verification
*[To be filled when implementation starts]*

### Module 3.3: Team Management
*[To be filled when implementation starts]*

### Module 3.4: Check-in System
*[To be filled when implementation starts]*

### Module 3.5: Participant Dashboard
*[To be filled when implementation starts]*

---

## Phase 4: Tournament During (Match & Competition)

### Module 4.1: Bracket Generation
*[To be filled when implementation starts]*

### Module 4.2: Match Management & Scheduling
*[To be filled when implementation starts]*

### Module 4.3: Score Submission & Validation
*[To be filled when implementation starts]*

### Module 4.4: Dispute Resolution
*[To be filled when implementation starts]*

### Module 4.5: Live Match Updates
*[To be filled when implementation starts]*

### Module 4.6: Match Admin Interface
*[To be filled when implementation starts]*

---

## Phase 5: Tournament After (Results & Rewards)

### Module 5.1: Winner Determination & Verification
*[To be filled when implementation starts]*

### Module 5.2: Prize Distribution
*[To be filled when implementation starts]*

### Module 5.3: Certificate Generation
*[To be filled when implementation starts]*

### Module 5.4: Tournament Analytics & Reports
*[To be filled when implementation starts]*

---

## Phase 6: Real-time Features

### Module 6.1: WebSocket Infrastructure
*[To be filled when implementation starts]*

### Module 6.2: Live Tournament Feed
*[To be filled when implementation starts]*

### Module 6.3: Chat System
*[To be filled when implementation starts]*

### Module 6.4: Notifications System
*[To be filled when implementation starts]*

### Module 6.5: Spectator Mode
*[To be filled when implementation starts]*

---

## Phase 7: Economy & Monetization

### Module 7.1: Coin System
*[To be filled when implementation starts]*

### Module 7.2: Shop & Purchases
*[To be filled when implementation starts]*

### Module 7.3: Transaction History
*[To be filled when implementation starts]*

### Module 7.4: Revenue Analytics
*[To be filled when implementation starts]*

### Module 7.5: Promotional System
*[To be filled when implementation starts]*

---

## Phase 8: Admin & Moderation

### Module 8.1: Tournament Moderation
*[To be filled when implementation starts]*

### Module 8.2: User Moderation
*[To be filled when implementation starts]*

### Module 8.3: Content Moderation
*[To be filled when implementation starts]*

### Module 8.4: Audit Logs
*[To be filled when implementation starts]*

### Module 8.5: Admin Analytics Dashboard
*[To be filled when implementation starts]*

---

## Phase 9: Polish & Optimization

### Module 9.1: Performance Optimization
*[To be filled when implementation starts]*

### Module 9.2: Mobile Optimization
*[To be filled when implementation starts]*

### Module 9.3: Accessibility (WCAG 2.1 AA)
*[To be filled when implementation starts]*

### Module 9.4: SEO & Social Sharing
*[To be filled when implementation starts]*

### Module 9.5: Error Handling & Monitoring
*[To be filled when implementation starts]*

### Module 9.6: Documentation & Onboarding
*[To be filled when implementation starts]*

---

**Note:** This file is updated as each module is implemented. Each entry should include:
- Exact Planning document anchors used
- Relevant ADRs from 01_ARCHITECTURE_DECISIONS.md
- Files created/modified
- Any deviations from plan (with justification)
