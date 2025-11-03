# DeltaCrown Tournament System Documentation

**Purpose:** Complete technical documentation of the **current** DeltaCrown tournament system (backend and frontend) for developer onboarding and future system redesign planning.

**Audience:** Development teams tasked with understanding, maintaining, or redesigning the tournament platform.

**Status:** Current system documentation (as of November 2, 2025)

---

## 📋 Navigation Map

This documentation pack contains **8 core files** that comprehensively cover the existing tournament system:

### Core Documentation

| # | File | Contents | Read Time |
|---|------|----------|-----------|
| 01 | [project-overview-and-scope](./01-project-overview-and-scope.md) | Product purpose, user flows, supported games, limitations | 15 min |
| 02 | [architecture-and-tech-stack](./02-architecture-and-tech-stack.md) | Backend/frontend architecture, frameworks, integration patterns | 20 min |
| 03 | [domain-model-erd-and-storage](./03-domain-model-erd-and-storage.md) | Core entities, relationships, database schema, lifecycle states | 25 min |
| 04 | [modules-services-and-apis](./04-modules-services-and-apis.md) | App structure, service layer, REST APIs, internal interfaces | 20 min |
| 05 | [user-flows-ui-and-frontend](./05-user-flows-ui-and-frontend.md) | UX journeys, screens, components, styling, templates | 20 min |
| 06 | [scheduling-brackets-payments-and-disputes](./06-scheduling-brackets-payments-and-disputes.md) | Tournament mechanics, bracket generation, payment flows, dispute resolution | 25 min |
| 07 | [permissions-notifications-and-realtime](./07-permissions-notifications-and-realtime.md) | RBAC, notification system, WebSocket implementation | 15 min |
| 08 | [operations-environments-and-observability](./08-operations-environments-and-observability.md) | Deployment, config, monitoring, runbooks, DR | 15 min |

**Total Reading Time:** ~2.5 hours for complete system understanding

---

## 🚀 Quick Start

### For New Developers
1. **Start here:** Read [01-project-overview-and-scope](./01-project-overview-and-scope.md) to understand the product
2. **Setup environment:** Follow [08-operations-environments-and-observability](./08-operations-environments-and-observability.md) → Local Setup section
3. **Understand architecture:** Read [02-architecture-and-tech-stack](./02-architecture-and-tech-stack.md) and [03-domain-model-erd-and-storage](./03-domain-model-erd-and-storage.md)
4. **Explore code:** Use [04-modules-services-and-apis](./04-modules-services-and-apis.md) as your map
5. **Learn workflows:** Review [05-user-flows-ui-and-frontend](./05-user-flows-ui-and-frontend.md) and [06-scheduling-brackets-payments-and-disputes](./06-scheduling-brackets-payments-and-disputes.md)

### For System Redesign Planning
1. Read files **01** through **03** to understand current capabilities and constraints
2. Study **04** and **06** to identify architectural bottlenecks
3. Review **07** and **08** to understand operational requirements
4. Cross-reference limitations documented in each file's "Known Issues" sections

### For Frontend Developers
- Primary: **05** (user-flows-ui-and-frontend)
- Supporting: **01** (user types), **02** (frontend stack), **07** (realtime updates)

### For Backend Developers  
- Primary: **03** (domain model), **04** (services/APIs), **06** (business logic)
- Supporting: **02** (backend stack), **07** (notifications), **08** (operations)

---

## 📐 Documentation Principles

### What This Pack Contains
✅ **Current system** architecture, code, and behavior (as-is documentation)  
✅ **Existing** user flows, screens, and APIs  
✅ **Actual** data models, relationships, and storage  
✅ **Real** technical limitations and known issues  
✅ **Working** deployment and operational procedures

### What This Pack Does NOT Contain
❌ **Proposals** for new system design  
❌ **Speculative** future architecture  
❌ **Hypothetical** feature implementations  
❌ **Marketing** or sales materials  
❌ **Outdated** or deprecated information

### Assumptions and Verification
Where behavior is uncertain or undocumented, sections include:
```markdown
**Assumptions / To-Verify:**
- [Assumption about behavior]
- [Question requiring stakeholder confirmation]
```

These should be resolved through code review, testing, or stakeholder interviews.

---

## 🔗 Cross-References

Documentation files frequently reference each other:

- **Entities** defined in `03` are referenced in `04`, `06`, `07`
- **APIs** listed in `04` implement flows described in `05` and `06`
- **Architecture** in `02` underpins all technical details
- **Operations** in `08` references config from `02` and `04`

Each file includes a "Where to Read Next" section for navigation.

---

## 📊 System Health Snapshot

**Current Status** (as of November 2, 2025):

| Aspect | Status | Notes |
|--------|--------|-------|
| Core functionality | ✅ Operational | MVP features working |
| Scalability | ⚠️ Limited | Max ~8 games, manual bracket creation |
| Coupling | ⚠️ Tight | Apps interdependent, hard to modify |
| Test coverage | ⚠️ Partial | 94+ test files but gaps exist |
| Documentation | ✅ Complete | This pack |
| Production readiness | ⚠️ Partial | Missing monitoring, auto-scaling |

---

## 🛠️ Maintenance

**Document Owner:** Development Team  
**Last Updated:** November 2, 2025  
**Review Cycle:** Quarterly or on major system changes  

**How to Update:**
1. Keep documentation synchronized with code changes
2. Update diagrams when architecture evolves
3. Add new "Assumptions / To-Verify" blocks for uncertain behavior
4. Archive outdated sections rather than deleting (preserve history)

---

## 📞 Support

**Questions about documentation:**
- Create issue with label `docs:tournament-system`
- Tag: `@dev-team`

**Questions about system behavior:**
- Refer to specific doc file and section
- Include code references from `04-modules-services-and-apis.md`

---

## 📜 Change Log

| Date | Changes | Author |
|------|---------|--------|
| 2025-11-02 | Initial comprehensive documentation pack created | Development Team |

---

**Ready to dive in?** Start with [01-project-overview-and-scope.md](./01-project-overview-and-scope.md) →
