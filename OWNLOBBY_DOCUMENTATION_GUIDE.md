# OwnLobby documentation guide

Start with [README](README.md) for setup and the [Development workspace](Documents/Development/README.md) for current task management and dated status. The [release handoff](OWNLOBBY_RELEASE_HANDOFF.md) and other engineering reports preserve historical evidence; consult [STATUS](Documents/Development/STATUS.md) before treating their operational claims as current. This guide classifies documentation; it does not approve production operations. Earlier Phase 5 cleanup/media labels describe separate historical workstreams, not today's implementation state.

## Active entry points

| Question | Source |
|---|---|
| How do I run/build/test safely? | [README](README.md) |
| What should the next agent do, and what is actually verified? | [Development entry point](Documents/Development/README.md), [current status](Documents/Development/STATUS.md), [backlog](Documents/Development/BACKLOG.md) |
| What is the current release status and historical rollback context? | [Current status](Documents/Development/STATUS.md), [release handoff](OWNLOBBY_RELEASE_HANDOFF.md), [readiness history](OWNLOBBY_PRODUCTION_READINESS.md) |
| Why is Twisted vendored and how is it verified? | [Security closure](OWNLOBBY_SECURITY_CLOSURE.md), [package provenance](vendor/twisted/README.md) |
| Was Linux/native Cairo tested? | [Linux parity](OWNLOBBY_LINUX_PARITY.md) |
| Which OAuth contracts/tests are current? | [OAuth reliability](OWNLOBBY_OAUTH_RELIABILITY.md) |
| What media design and inventory history applies? | [Media architecture](OWNLOBBY_MEDIA_ARCHITECTURE.md), [field inventory](branding/media-storage-inventory.json); use Development status/backlog for current work |
| How are domains/SEO migrated later? | [Domain migration](OWNLOBBY_DOMAIN_MIGRATION.md), [technical SEO](OWNLOBBY_TECHNICAL_SEO.md) |
| What do dependency scans actually mean? | [Dependency security](OWNLOBBY_DEPENDENCY_SECURITY.md), [current dual scan](branding/security-runtime-dependency-audit.json) |
| What changed in cleanup? | [Repository audit](OWNLOBBY_REPOSITORY_AUDIT.md), [manifest](OWNLOBBY_CLEANUP_MANIFEST.md), [cleanup handoff](OWNLOBBY_CLEANUP_HANDOFF.md) |
| Which agent/settings contracts are protected? | [AGENTS.md](AGENTS.md) |

The small existing root report set remains at stable paths because tools, prior reports and operational guidance reference it. Existing phase evidence is not replaced by a duplicate new hierarchy. New topical documents should extend existing entry points or app-level references; add root entry points only after updating the reviewed placement policy.

Owner-approved addition, 2026-10-29: `Documents/Development/` provides ongoing product/task/status/decision/handoff management. It links historical technical reports rather than copying them. BACKLOG owns task state; STATUS is a dated summary. Only explicitly reviewed documents listed in repository policy and narrow Git ignore exceptions are public; this is not permission to publish other `Documents/` contents or private audit evidence.

## App and integration references

- [Core services/events](apps/core/README.md), [games](apps/games/README.md).
- [Organizations](apps/organizations/README.md), [organization ADR index](apps/organizations/docs/adr/README.md), [constants](apps/organizations/constants/README.md).
- [Tournaments](apps/tournaments/README.md), [API notes](apps/tournaments/api/README.md), [services](apps/tournaments/services/README.md), [bracket generators](apps/tournament_ops/services/bracket_generators/README.md), [game adapters](apps/tournament_ops/adapters/README.md).
- [SDK contract notes](frontend_sdk/README.md), [feature flags](config/flags.md), [font attribution](static/fonts/README.md).

These references can contain historical examples; source, current tests and current release reports resolve conflicts. Plain pytest and old operational scripts are not automatically isolated. [Historical test notes](tests/README.md) and [ops notes](ops/README.md) remain available, with current safe setup in the main README.

## History and classification policy

| Classification | Meaning and action |
|---|---|
| KEEP | Active documentation or required app/ADR/configuration/runtime material; maintain links. |
| CONSOLIDATE | Bring overlapping entry-point guidance together while preserving unique content and provenance. README/index consolidation was performed; it does not discard prior reports. |
| ARCHIVE CANDIDATE | Valuable, superseded context; retain until a reviewed move is justified. A label is not approval to delete or move. |
| DELETE CANDIDATE | Only verified disposable/identical material with demonstrated references and recovery. Current single performed deletion is documented in the cleanup manifest. |
| PROTECTED | Owner-owned planning, operational evidence, approved assets, data or essential instructions; no automatic reorganization. |
| NEEDS OWNER REVIEW | Unclear purpose, ownership or future value; preserve and explain the decision needed. |

[Pre-cleanup product README](reference/README_PRODUCT_HISTORY.md) is a verbatim snapshot with [provenance](reference/README.md); the engineering README replaces its setup role. [Technical overview](README_TECHNICAL.md), [competitive audit](AuditReport.md), [route inventory](DELTACROWN_ROUTE_AND_PAGE_INVENTORY.md) and [capture plan](DELTACROWN_SCREENSHOT_CAPTURE_PLAN.md) remain in place. Their DeltaCrown names/dates are historical context, not rename targets or current completion guarantees.

[Rebrand report](OWNLOBBY_REBRAND.md), [original validation](OWNLOBBY_VALIDATION.md) and [Phase 3 dependency validation](OWNLOBBY_DEPENDENCY_VALIDATION.md) preserve audit/rollback evidence. Current reports explicitly supersede older unresolved items; never copy old Go/No-Go claims forward without verification. The [machine inventory](reference/repository-inventory.json) classifies existing tracked document-like files, including email templates/requirements that must not be archived as prose.

## Protected owner workspace

`Documents/DELTACROWN/` and all 26 existing files remain unchanged, verified by local pre/post fingerprints. Do not delete, move, archive or rename this directory without explicit owner approval. Other `Documents/`, ignored `docs/`, drafts, research, reports and design masters also remain at their original locations. They may be unique even if old or duplicated. No public manifest lists private media filenames or protected document contents.

Ignored does not mean unnecessary: `.env`, local uploads/evidence, QA databases, screenshots, synthetic sessions, temporary test TLS keys and test environments stay local. Local Docs links can exist only in the owner's workspace; a Git clone cannot recreate them. Obtain owner-approved references when needed rather than unignoring/publishing the entire collection. The settings redesign specification remains in its protected owner path and is required before any future settings redesign.

The local root `.env.example` has a populated provider-key-shaped value. It is ignored and remains untouched; use [blank setup example](config/development.env.example). Treat the older file as sensitive pending private owner review; no live credential test or rotation was performed. Do not quote its value in issues or reports.

## Link and placement checks

```powershell
python scripts/ops/check_repo_hygiene.py
python scripts/check_documentation.py --all --output Artifacts/repository-cleanup/documentation-links.json
```

[Repository policy](config/repository-policy.json) lists active documents, intentionally retained root files and owner-protected directories. The hygiene command checks tracked and non-ignored candidates; it never deletes or recommends blind disk cleanup. It still flags a force-tracked environment/database file. Its pass is a placement result, not release/security certification.

The offline link checker validates active local targets and Markdown headings, skips external URLs/application routes and code-fence examples, and reports historical missing/workspace-only links separately. Historical findings require review; do not invent missing specifications or publish ignored owner material to make the counter green. It is not a complete CommonMark parser or external-link availability audit.

When a tracked file genuinely moves, use a reviewed Git move, update inbound/outbound references and runtime discovery, then validate. Do not rename Python packages, app labels, migrations, tables, API keys/routes, currency identifiers, infrastructure names or asset paths for appearance. A source search alone cannot prove a persisted path is unused.
