# Architecture Decision Records (ADRs)

**Purpose:** This directory contains Architecture Decision Records (ADRs) documenting key design decisions for the organizations app (Team & Organization vNext system).

**Status:** Active - All decisions in this directory are binding unless explicitly superseded.

---

## What is an ADR?

An Architecture Decision Record (ADR) captures an important architectural decision made along with its context and consequences. ADRs help maintain institutional knowledge and prevent revisiting settled debates.

**Standard ADR Format:**
1. **Title** - Short noun phrase (e.g., "Team Ownership Constraint")
2. **Status** - Accepted, Superseded, Deprecated, Proposed
3. **Context** - The issue motivating this decision
4. **Decision** - What we decided to do (use imperative mood: "We will...")
5. **Consequences** - What becomes easier or harder as a result
6. **Alternatives Considered** - Other options evaluated and why rejected
7. **References** - Links to planning docs, RFCs, discussions
8. **Notes** - Implementation details, migration notes, future considerations

---

## ADR Index

| ADR | Title | Status | Date | Related Docs |
|-----|-------|--------|------|--------------|
| [001](001-team-ownership-constraint.md) | Team Ownership Constraint (Organization XOR Owner) | ✅ Accepted | 2026-01-25 | ARCHITECTURE.md §2.1 |
| [002](002-game-passport-requirement.md) | Game Passport Requirement for Roles | ✅ Accepted | 2026-01-25 | ARCHITECTURE.md §6.2 |
| [003](003-empire-score-calculation.md) | Empire Score Calculation (Top 3 Teams) | ✅ Accepted | 2026-01-25 | ARCHITECTURE.md §7.3 |
| [004](004-integerfield-game-id-bridge.md) | IntegerField game_id Migration Bridge | ✅ Accepted | 2026-01-25 | ARCHITECTURE.md §2.2, COMPATIBILITY_CONTRACT.md §3.1 |

---

## ADR Naming Rules

**File Naming Convention:**
```
<number>-<short-title-kebab-case>.md

Examples:
001-team-ownership-constraint.md
002-game-passport-requirement.md
010-caching-strategy.md
```

**Numbering Rules:**
- Zero-padded to 3 digits (001, 002, ..., 999)
- Sequential numbering (no gaps)
- Never reuse numbers (even if ADR is superseded)

---

## How to Propose a New ADR

**Process:**

1. **Create Draft ADR**
   - Copy template from existing ADR
   - Assign next available number
   - Set status to "Proposed"
   - Fill all required sections

2. **Review Process**
   - Submit PR with ADR file
   - Tag @engineering-leads for review
   - Address feedback in PR comments
   - Update ADR based on discussion

3. **Acceptance Criteria**
   - All sections complete
   - Alternatives documented
   - Consequences understood
   - No blocking concerns from leads

4. **Merge & Activate**
   - Update status to "Accepted"
   - Merge PR
   - Update ADR index (this README)
   - Notify team in #engineering channel

---

## When ADR Updates Are Allowed

### ✅ Allowed Updates (No Review Required)

- Fix typos, grammar, formatting
- Add clarifying notes to "Notes" section
- Add references to related tickets/PRs
- Update implementation examples if API unchanged

### ⚠️ Requires Review (PR + Engineering Lead Approval)

- Change "Decision" section (use case: correcting misunderstanding)
- Add new alternatives with retroactive analysis
- Update "Consequences" based on production learnings
- Change "Status" to "Superseded" (must create new ADR)

### ❌ Never Allowed

- Delete ADR files (use "Deprecated" status instead)
- Change ADR number (breaks references)
- Rewrite history (add new ADR that supersedes instead)

---

## Superseding an ADR

When a decision is reversed or replaced:

1. Create new ADR with next available number
2. In new ADR, explain why superseding previous decision
3. Update old ADR:
   - Change status to "Superseded by ADR-XXX"
   - Add note at top: "⚠️ **SUPERSEDED:** See [ADR-XXX](XXX-new-title.md)"
4. Update this index with both ADRs

**Example:**
```markdown
# ADR-001: Team Ownership Constraint (Organization XOR Owner)

**Status:** Superseded by [ADR-015](015-team-ownership-v2.md)

⚠️ **SUPERSEDED (2026-03-15):** This decision was replaced due to [reason].  
See [ADR-015: Team Ownership Model v2](015-team-ownership-v2.md) for current approach.

---
[Original content preserved below]
```

---

## Authority & Enforcement

**Binding Authority:**
- Accepted ADRs are **MANDATORY** for all code in this app
- Code reviews MUST verify compliance with relevant ADRs
- Violations require either:
  - Fix the code to comply, OR
  - Propose ADR change via review process

**When ADRs Apply:**
- Models, services, views within `apps/organizations/`
- External integrations that depend on organizations app
- Database schema decisions (migrations)
- API contracts (when Phase 3 API built)

**When ADRs Don't Apply:**
- Internal implementation details not affecting contracts
- Performance optimizations not changing behavior
- Frontend styling/UI decisions (unless affecting architecture)

---

## References

**Planning Documents:**
- [TEAM_ORG_ARCHITECTURE.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ARCHITECTURE.md) - System architecture
- [TEAM_ORG_COMPATIBILITY_CONTRACT.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_COMPATIBILITY_CONTRACT.md) - Legacy compatibility rules
- [TEAM_ORG_ENGINEERING_STANDARDS.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_ENGINEERING_STANDARDS.md) - Code quality standards
- [TEAM_ORG_PERFORMANCE_CONTRACT.md](../../../../../Documents/Team%20&%20Organization/Planning%20Documents/TEAM_ORG_PERFORMANCE_CONTRACT.md) - Performance requirements
- [TEAM_ORG_VNEXT_TRACKER.md](../../../../../Documents/Team%20&%20Organization/Execution/TEAM_ORG_VNEXT_TRACKER.md) - Execution tracker

**ADR Resources:**
- [Michael Nygard's ADR Template](https://github.com/joelparkerhenderson/architecture-decision-record)
- [ThoughtWorks Technology Radar: ADRs](https://www.thoughtworks.com/radar/techniques/lightweight-architecture-decision-records)

---

**Last Updated:** 2026-01-25  
**Maintainer:** Engineering Team  
**Review Cycle:** Quarterly (or as needed for new ADRs)
