# Project Cleanup Plan - Backend V1 Finalization

**Date**: November 14, 2025  
**Status**: PENDING APPROVAL  
**Purpose**: Clean, reorganize, and standardize project structure before frontend development

---

## Planning Documents Consulted

- ✅ Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md
- ✅ Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md
- ✅ Documents/Planning/PART_2.3_REALTIME_SECURITY.md
- ✅ Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md
- ✅ Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md
- ✅ Documents/Planning/PART_4.1-4.6_UI_UX_DESIGN.md (all sections)
- ✅ Documents/Planning/PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md
- ✅ Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md
- ✅ Documents/ExecutionPlan/Core/00_MASTER_EXECUTION_PLAN.md
- ✅ Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md
- ✅ Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md
- ✅ Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md
- ✅ Documents/ExecutionPlan/Core/MAP.md
- ✅ Documents/ExecutionPlan/Core/trace.yml
- ✅ All MODULE_*_COMPLETION_STATUS.md files (50+ files)

---

## 1. Files to DELETE PERMANENTLY

### Root-Level Temporary Files (Test Outputs & Debug Files)
**Rationale**: Testing artifacts that served their purpose during development

```
/debug_bracket.py                    # Temporary debugging script
/fix_backticks.py                    # One-time fix script
/fix_decimal.py                      # One-time fix script
/fix_decorators.py                   # One-time fix script
/fix_services_and_tests.py           # One-time fix script
/test_debug_auth.py                  # Temporary test file
/test_debug_auth2.py                 # Temporary test file
/failure_reject.txt                  # Old test output
/forfeit_trace.txt                   # Old test trace
/h2h_fail.txt                        # Old test output
/h2h_trace.txt                       # Old test trace
/score_diff_trace.txt                # Old test trace
/test_disputed.txt                   # Old test output
/test_failure_output.txt             # Old test output
/test_output.txt                     # Old test output
/test_results.txt                    # Old test results
/test_results_current.txt            # Old test results
/test_trace.txt                      # Old test trace
/trace_output.txt                    # Old trace output
/trace_verify_output.txt             # Old trace output
/verify_trace_output.txt             # Old trace output
```

### Root-Level Documentation (Superseded by ExecutionPlan)
**Rationale**: Content has been moved to proper locations or superseded

```
/MODULE_8.3_OBSERVABILITY_NOTES.md   # Superseded by MODULE_8.3_ENFORCEMENT_COMPLETION_STATUS.md
/PHASE_9_SMOKE_AND_ALERTING.md       # Content moved to docs/runbooks/
/PHASE_E_PR_DESCRIPTION.md           # Historical PR description, not needed
/RELEASE_CHECKLIST_V1.md             # Superseded by docs/runbooks/deployment.md
```

### Documents/ Root-Level Files (Should be in Subdirectories)
**Rationale**: Files in wrong location, should be in ExecutionPlan/ or Runbooks/

```
Documents/DB_RESET_NOTES.md                      # Move to Documents/Runbooks/
Documents/MONITORING.md                          # Move to Documents/Runbooks/
Documents/Phase3_Prep_Checklist.md              # Superseded by PHASE_3_COMPLETION_SUMMARY.md
Documents/PHASE3_PREP_STATUS.md                  # Superseded by PHASE_3_COMPLETION_SUMMARY.md
Documents/Phase5_6_Hardening_Spec.md             # Superseded by completion docs
Documents/Phase5_9Game_Blueprint_Verification.md # Superseded by completion docs
Documents/Phase5_Closeout_Package.md             # Superseded by PHASE_5_COMPLETION_SUMMARY.md
Documents/Phase5_Configuration_Rollback.md       # Content absorbed into runbooks
Documents/Phase5_PII_Discipline.md               # Content absorbed into security docs
Documents/Phase5_Staging_Enablement.md           # Superseded by runbooks
Documents/Phase5_Webhook_Evidence.md             # Move to Documents/Archive/Phase5/
Documents/PRODUCTION_CANARY_RUNBOOK.md           # Move to Documents/Runbooks/
Documents/CANARY_5_PERCENT_CONFIG.md             # Move to Documents/Archive/Phase5/
Documents/CANARY_ENABLEMENT_GO.md                # Move to Documents/Archive/Phase5/
Documents/FRONTEND_INTEGRATION.md                # Keep, but move to Documents/Planning/
Documents/staging_matches_output.json            # Old test output - DELETE
Documents/staging_payments_output.json           # Old test output - DELETE
```

### Documents/Development/ (Superseded Files)
**Rationale**: Content moved to ExecutionPlan MODULE docs

```
Documents/Development/MODULE_5.3_COMPLETION_STATUS.md  # Move to ExecutionPlan/
Documents/Development/MODULE_5.4_TEST_FIXES_NEEDED.md  # Historical, superseded
```

### Documents/WorkList/ (Old Sprint Files)
**Rationale**: Sprint planning superseded by BACKEND_ONLY_BACKLOG.md

```
Documents/WorkList/Phase4_Notification_Signals_COMPLETE.md  # Superseded
Documents/WorkList/Backup/*                                  # All old sprint files - ARCHIVE
```

### Documents/Reports/ (Superseded Reports)
**Rationale**: Historical reports no longer relevant

```
Documents/Reports/FINAL_DELIVERY_REPORT.md           # Superseded by newer completion docs
Documents/Reports/MODULE_6.6_PERF_REPORT.md          # Superseded by MODULE_6.6_COMPLETION_STATUS.md
Documents/Reports/My_Notes                           # Personal notes - DELETE or ARCHIVE
```

---

## 2. Files to ARCHIVE

**Target Directory**: `Documents/Archive/`

### Archive Structure
```
Documents/Archive/
├── Phase3/                          # Phase 3 historical docs
├── Phase4/                          # Phase 4 historical docs
├── Phase5/                          # Phase 5 historical docs
├── PhaseE/                          # Phase E historical docs
├── OldReports/                      # Superseded reports
├── OldPlanning/                     # Superseded planning versions
└── README.md                        # Archive index
```

### Files to Archive

**Phase 5 Historical Evidence**:
```
Documents/Phase5_Webhook_Evidence.md              → Archive/Phase5/
Documents/CANARY_5_PERCENT_CONFIG.md              → Archive/Phase5/
Documents/CANARY_ENABLEMENT_GO.md                 → Archive/Phase5/
```

**Old Reports**:
```
Documents/Reports/FINAL_BUNDLED_DELIVERY.md       → Archive/OldReports/
Documents/Reports/FINAL_CLOSURE_BUNDLED.md        → Archive/OldReports/
Documents/Reports/SECTION_A_STATUS_COMPREHENSIVE.md → Archive/OldReports/
```

**ExecutionPlan Historical Docs**:
```
Documents/ExecutionPlan/BACKEND_AUDIT_SUMMARY.md           → Archive/Phase3/
Documents/ExecutionPlan/MERGE_READY_SUMMARY.md             → Archive/Phase4/
Documents/ExecutionPlan/SECTION_A_B_PROGRESS_REPORT.md     → Archive/Phase3/
Documents/ExecutionPlan/WORKFLOW_AUDIT_REPORT.md           → Archive/Phase3/
Documents/ExecutionPlan/MILESTONE_E_PHASE3_COMPLETE.md     → Archive/PhaseE/
Documents/ExecutionPlan/MILESTONES_E_F_SESSION_SUMMARY.md  → Archive/PhaseE/
Documents/ExecutionPlan/PHASE_E_MAP_SECTION.md             → Archive/PhaseE/
Documents/ExecutionPlan/PHASE_E_PII_HARDENING_SUMMARY.md   → Archive/PhaseE/
Documents/ExecutionPlan/PHASE_E_TRACE_NODES.yml            → Archive/PhaseE/
Documents/ExecutionPlan/PR_BODY_MILESTONES_BCD.md          → Archive/Phase4/
Documents/ExecutionPlan/PR_MILESTONES_B_C_D.md             → Archive/Phase4/
Documents/ExecutionPlan/MILESTONE_BCD_BLUEPRINT_ALIGNMENT.md → Archive/Phase4/
Documents/ExecutionPlan/MILESTONE_BCD_COMPLETION_PROOF.md    → Archive/Phase4/
Documents/ExecutionPlan/MILESTONE_BCD_FINAL_ACCEPTANCE.md    → Archive/Phase4/
Documents/ExecutionPlan/MILESTONE_BCD_FINAL_DELIVERABLE.md   → Archive/Phase4/
Documents/ExecutionPlan/MILESTONE_D_MATCHES_API_STATUS.md    → Archive/Phase4/
Documents/ExecutionPlan/MILESTONES_E_F_PLAN.md               → Archive/PhaseE/
Documents/ExecutionPlan/MILESTONES_E_F_STATUS.md             → Archive/PhaseE/
Documents/ExecutionPlan/MILESTONES_E_TEST_RESULTS.md         → Archive/PhaseE/
```

**Old Sprint Files**:
```
Documents/WorkList/Backup/*                       → Archive/OldPlanning/Sprints/
Documents/WorkList/Phase4_Notification_Signals_COMPLETE.md → Archive/Phase4/
```

**Old Module Kickoff/Progress Files**:
```
Documents/ExecutionPlan/Modules/MODULE_3.3_IMPLEMENTATION_PLAN.md  → Archive/Phase3/
Documents/ExecutionPlan/Modules/MODULE_4.3_APPEND.md               → Archive/Phase4/
Documents/ExecutionPlan/Modules/MODULE_4.3_COMPLETION_STATUS_APPEND.md → Archive/Phase4/
Documents/ExecutionPlan/Modules/MODULE_5.1_EXECUTION_CHECKLIST.md  → Archive/Phase5/
Documents/ExecutionPlan/Modules/MODULE_6.5_FINAL_DELIVERY.md       → Archive/Phase6/
Documents/ExecutionPlan/Modules/MODULE_6.5_FINAL_PACKAGE.md        → Archive/Phase6/
Documents/ExecutionPlan/Modules/MODULE_6.5_REMEDIATION_FINAL_REPORT.md → Archive/Phase6/
Documents/ExecutionPlan/Modules/MODULE_6.6_INTEGRATION_UNBLOCK.md  → Archive/Phase6/
Documents/ExecutionPlan/Modules/MODULE_6.7_KICKOFF.md              → Archive/Phase6/
Documents/ExecutionPlan/Modules/MODULE_6.8_KICKOFF.md              → Archive/Phase6/
Documents/ExecutionPlan/Modules/MODULE_6.8_PHASE1_STATUS.md        → Archive/Phase6/
Documents/ExecutionPlan/Modules/MODULE_7.1_KICKOFF.md              → Archive/Phase7/
Documents/ExecutionPlan/Modules/MODULE_7.2_KICKOFF.md              → Archive/Phase7/
Documents/ExecutionPlan/Modules/MODULE_7.2_PROGRESS_REPORT.md      → Archive/Phase7/
Documents/ExecutionPlan/Modules/MODULE_9.1_PERFORMANCE_AUDIT.md    → Archive/Phase9/
```

**Phase Implementation Plans (Superseded by Completion Summaries)**:
```
Documents/ExecutionPlan/PHASE_2_IMPLEMENTATION_PLAN.md     → Archive/Phase2/
Documents/ExecutionPlan/PHASE_4_IMPLEMENTATION_PLAN.md     → Archive/Phase4/
Documents/ExecutionPlan/PHASE_5_IMPLEMENTATION_PLAN.md     → Archive/Phase5/
Documents/ExecutionPlan/PHASE_5_PERF_REPORT.md             → Archive/Phase5/
Documents/ExecutionPlan/PHASE_5_STAGING_CHECKLIST.md       → Archive/Phase5/
Documents/ExecutionPlan/PHASE_6_IMPLEMENTATION_PLAN.md     → Archive/Phase6/
Documents/ExecutionPlan/PHASE_6_RESIDUALS_CLOSEOUT.md      → Archive/Phase6/
Documents/ExecutionPlan/PHASE_8_3_HARDENING_DELIVERY.md    → Archive/Phase8/
```

**Old Backlogs (Superseded by BACKEND_ONLY_BACKLOG.md)**:
```
Documents/ExecutionPlan/BACKLOG_MASTER_FINAL.md            → Archive/OldPlanning/
Documents/ExecutionPlan/BACKLOG_PHASE_4_DEFERRED.md        → Archive/Phase4/
Documents/ExecutionPlan/BACKLOG_PHASE_5_DEFERRED.md        → Archive/Phase5/
```

---

## 3. Files to KEEP (Core Source of Truth)

### Planning Documents (Keep All)
```
Documents/Planning/INDEX_MASTER_NAVIGATION.md
Documents/Planning/PART_2.1_ARCHITECTURE_FOUNDATIONS.md
Documents/Planning/PART_2.2_SERVICES_INTEGRATION.md
Documents/Planning/PART_2.3_REALTIME_SECURITY.md
Documents/Planning/PART_3.1_DATABASE_DESIGN_ERD.md
Documents/Planning/PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md
Documents/Planning/PART_4.1_UI_UX_DESIGN_FOUNDATIONS.md
Documents/Planning/PART_4.2_UI_COMPONENTS_NAVIGATION.md
Documents/Planning/PART_4.3_TOURNAMENT_MANAGEMENT_SCREENS.md
Documents/Planning/PART_4.4_REGISTRATION_PAYMENT_FLOW.md
Documents/Planning/PART_4.5_SPECTATOR_MOBILE_ACCESSIBILITY.md
Documents/Planning/PART_4.6_ANIMATION_PATTERNS_CONCLUSION.md
Documents/Planning/PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md
Documents/Planning/PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md
Documents/Planning/PROPOSAL_PART_*.md (all files)
Documents/Planning/README.md
Documents/Planning/SETUP_GUIDE.md
Documents/Planning/ORIGINALS_BACKUP/ (entire folder)
```

### ExecutionPlan Core Documents (Keep)
```
Documents/ExecutionPlan/Core/00_MASTER_EXECUTION_PLAN.md
Documents/ExecutionPlan/Core/01_ARCHITECTURE_DECISIONS.md
Documents/ExecutionPlan/Core/02_TECHNICAL_STANDARDS.md
Documents/ExecutionPlan/Core/BACKEND_ONLY_BACKLOG.md
Documents/ExecutionPlan/Core/MAP.md
Documents/ExecutionPlan/Core/trace.yml
Documents/ExecutionPlan/README_GUARDRAILS.md
Documents/ExecutionPlan/Phases/PHASE_0_COMPLETE.md
Documents/ExecutionPlan/Phases/PHASE_3_COMPLETION_SUMMARY.md
Documents/ExecutionPlan/Phases/PHASE_4_COMPLETION_SUMMARY.md
Documents/ExecutionPlan/Phases/PHASE_5_COMPLETION_SUMMARY.md
```

### All MODULE Completion Docs (Keep All 50+)
```
Documents/ExecutionPlan/Modules/MODULE_1.2_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_1.3_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_1.4_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_1.5_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_2.1_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_2.2_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_2.3_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_2.4_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_2.4_TOURNAMENT_DISCOVERY_COMPLETION.md
Documents/ExecutionPlan/Modules/MODULE_2.5_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_2.5_ORGANIZER_DASHBOARD.md
Documents/ExecutionPlan/Modules/MODULE_3.1_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_3.2_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_3.3_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_3.4_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_4.1_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_4.2_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_4.3_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_4.4_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_4.5_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_4.6_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_5.1_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_5.2_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_5.4_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_6.1_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_6.2_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_6.3_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_6.4_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_6.5_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_6.6_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_6.7_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_6.8_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_7.1_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_7.2_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_7.3_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_7.4_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_8.1_8.2_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_8.3_ENFORCEMENT_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_9.1_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_9.5_COMPLETION_STATUS.md
Documents/ExecutionPlan/Modules/MODULE_9.6_COMPLETION_STATUS.md
```

### Runbooks & Operational Docs (Keep)
```
Documents/ExecutionPlan/API_CONTRACT_STATUS.md
Documents/ExecutionPlan/DR_RUNBOOK.md
Documents/ExecutionPlan/FUZZ_TESTING_STATUS.md
Documents/ExecutionPlan/RUNBOOKS.md
Documents/ExecutionPlan/RUNBOOK_CERT_S3_CUTOVER.md
Documents/ExecutionPlan/S3_MIGRATION_DESIGN.md
Documents/ExecutionPlan/SECURITY_HARDENING_STATUS.md
Documents/ExecutionPlan/STATUS_TEST_INFRASTRUCTURE.md
```

### New Documentation (Module 9.6 - Keep All)
```
docs/development/setup_guide.md
docs/api/endpoint_catalog.md
docs/architecture/system_architecture.md
docs/runbooks/deployment.md
docs/runbooks/module_2_6_realtime_monitoring.md
docs/runbooks/phase_e_leaderboards.md
```

### Other docs/ Content (Keep All)
```
docs/admin/
docs/canary/
docs/ci/
docs/integration/
docs/leaderboards/
docs/observability/
docs/ops/
docs/spectator/
docs/specs/
All *.md files in docs/
```

### For_New_Tournament_design/ (Keep All - Important Reference)
```
Documents/For_New_Tournament_design/01-project-overview-and-scope.md
Documents/For_New_Tournament_design/02-architecture-and-tech-stack.md
Documents/For_New_Tournament_design/03-domain-model-erd-and-storage.md
Documents/For_New_Tournament_design/04-modules-services-and-apis.md
Documents/For_New_Tournament_design/05-user-flows-ui-and-frontend.md
Documents/For_New_Tournament_design/06-teams-economy-ecommerce-integration.md
Documents/For_New_Tournament_design/07-permissions-notifications-and-realtime.md
Documents/For_New_Tournament_design/08-operations-environments-and-observability.md
Documents/For_New_Tournament_design/CHANGELOG.md
Documents/For_New_Tournament_design/CORRECTIONS_AND_EVIDENCE.md
Documents/For_New_Tournament_design/EVIDENCE_MATRIX.md
Documents/For_New_Tournament_design/MESSAGE_TO_DEVELOPERS.md
Documents/For_New_Tournament_design/PROJECT_BRIEF_FOR_DEVELOPERS.md
Documents/For_New_Tournament_design/README.md
```

### Runbooks/ (Keep)
```
Documents/Runbooks/S3_OPERATIONS_CHECKLIST.md
RUNBOOKS/ONCALL_HANDOFF.md
```

---

## 4. Files to MOVE/REORGANIZE

### Move to Documents/Runbooks/
```
Documents/DB_RESET_NOTES.md              → Documents/Runbooks/database_reset.md
Documents/MONITORING.md                  → Documents/Runbooks/monitoring_setup.md
Documents/PRODUCTION_CANARY_RUNBOOK.md   → Documents/Runbooks/canary_deployment.md
Documents/RECEIVER_INTEGRATION_GUIDE.md  → Documents/Runbooks/webhook_receiver_setup.md
```

### Move to Documents/Planning/
```
Documents/FRONTEND_INTEGRATION.md        → Documents/Planning/FRONTEND_INTEGRATION.md
```

### Move to Documents/ExecutionPlan/
```
Documents/Development/MODULE_5.3_COMPLETION_STATUS.md → Documents/ExecutionPlan/Modules/MODULE_5.3_COMPLETION_STATUS.md
```

### Root-Level Files to Move
```
/SECURITY.md                             → docs/security/SECURITY.md
```

---

## 5. Proposed Final Directory Structure

```
DeltaCrown/
├── apps/                                # Django apps (NO CHANGES)
│   ├── accounts/
│   ├── common/
│   ├── core/
│   ├── dashboard/
│   ├── ecommerce/
│   ├── economy/
│   ├── leaderboards/
│   ├── moderation/
│   ├── notifications/
│   ├── players/
│   ├── search/
│   ├── shop/
│   ├── siteui/
│   ├── spectator/
│   ├── support/
│   ├── teams/
│   ├── tournaments/
│   └── user_profile/
│
├── deltacrown/                          # Django project config (NO CHANGES)
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   ├── asgi.py
│   ├── celery.py
│   ├── exception_handlers.py
│   ├── health.py
│   ├── metrics.py
│   └── middleware/
│
├── Documents/                           # REORGANIZED
│   ├── Planning/                        # ✅ Core planning docs (KEEP ALL)
│   │   ├── INDEX_MASTER_NAVIGATION.md
│   │   ├── PART_2.1_ARCHITECTURE_FOUNDATIONS.md
│   │   ├── PART_2.2_SERVICES_INTEGRATION.md
│   │   ├── PART_2.3_REALTIME_SECURITY.md
│   │   ├── PART_3.1_DATABASE_DESIGN_ERD.md
│   │   ├── PART_3.2_DATABASE_CONSTRAINTS_MIGRATION.md
│   │   ├── PART_4.1-4.6_*.md
│   │   ├── PART_5.1_IMPLEMENTATION_ROADMAP_SPRINT_PLANNING.md
│   │   ├── PART_5.2_BACKEND_INTEGRATION_TESTING_DEPLOYMENT.md
│   │   ├── FRONTEND_INTEGRATION.md      # MOVED FROM ROOT
│   │   ├── PROPOSAL_PART_*.md
│   │   ├── README.md
│   │   ├── SETUP_GUIDE.md
│   │   └── ORIGINALS_BACKUP/
│   │
│   ├── ExecutionPlan/                   # ✅ Core execution tracking (CLEANED)
│   │   ├── 00_MASTER_EXECUTION_PLAN.md
│   │   ├── 01_ARCHITECTURE_DECISIONS.md
│   │   ├── 02_TECHNICAL_STANDARDS.md
│   │   ├── BACKEND_ONLY_BACKLOG.md
│   │   ├── MAP.md
│   │   ├── trace.yml
│   │   ├── README_GUARDRAILS.md
│   │   ├── PHASE_*_COMPLETION_SUMMARY.md (4 files)
│   │   ├── MODULE_*_COMPLETION_STATUS.md (50+ files - ALL KEPT)
│   │   ├── API_CONTRACT_STATUS.md
│   │   ├── DR_RUNBOOK.md
│   │   ├── FUZZ_TESTING_STATUS.md
│   │   ├── RUNBOOKS.md
│   │   ├── RUNBOOK_CERT_S3_CUTOVER.md
│   │   ├── S3_MIGRATION_DESIGN.md
│   │   ├── SECURITY_HARDENING_STATUS.md
│   │   ├── STATUS_TEST_INFRASTRUCTURE.md
│   │   └── PROJECT_CLEANUP_PLAN.md      # THIS FILE
│   │
│   ├── Runbooks/                        # ✅ Operational procedures (REORGANIZED)
│   │   ├── database_reset.md            # MOVED FROM Documents/
│   │   ├── monitoring_setup.md          # MOVED FROM Documents/
│   │   ├── canary_deployment.md         # MOVED FROM Documents/
│   │   ├── webhook_receiver_setup.md    # MOVED FROM Documents/
│   │   └── S3_OPERATIONS_CHECKLIST.md
│   │
│   ├── For_New_Tournament_design/       # ✅ Reference docs (KEEP ALL)
│   │   ├── 01-08-*.md (8 files)
│   │   ├── CHANGELOG.md
│   │   ├── CORRECTIONS_AND_EVIDENCE.md
│   │   ├── EVIDENCE_MATRIX.md
│   │   ├── MESSAGE_TO_DEVELOPERS.md
│   │   ├── PROJECT_BRIEF_FOR_DEVELOPERS.md
│   │   └── README.md
│   │
│   ├── Games/                           # ✅ Game specifications (KEEP)
│   │   └── Game_Spec.md
│   │
│   └── Archive/                         # ✅ NEW - Historical documents
│       ├── README.md                    # Index of archived content
│       ├── Phase2/
│       ├── Phase3/
│       ├── Phase4/
│       ├── Phase5/
│       ├── Phase6/
│       ├── Phase7/
│       ├── Phase8/
│       ├── Phase9/
│       ├── PhaseE/
│       ├── OldPlanning/
│       │   └── Sprints/
│       └── OldReports/
│
├── docs/                                # ✅ NEW - Technical documentation (Module 9.6)
│   ├── development/
│   │   └── setup_guide.md
│   ├── api/
│   │   └── endpoint_catalog.md
│   ├── architecture/
│   │   └── system_architecture.md
│   ├── runbooks/
│   │   ├── deployment.md
│   │   ├── module_2_6_realtime_monitoring.md
│   │   └── phase_e_leaderboards.md
│   ├── admin/
│   ├── canary/
│   ├── ci/
│   ├── integration/
│   ├── leaderboards/
│   ├── observability/
│   ├── ops/
│   ├── security/
│   │   └── SECURITY.md                  # MOVED FROM ROOT
│   ├── spectator/
│   └── specs/
│
├── tests/                               # Testing (NO CHANGES)
├── static/                              # Static files (NO CHANGES)
├── templates/                           # Django templates (NO CHANGES)
├── media/                               # User uploads (NO CHANGES)
├── logs/                                # Log files (NO CHANGES)
│
├── Artifacts/                           # Test artifacts (KEEP)
├── evidence/                            # Evidence files (KEEP)
├── reports/                             # Test reports (KEEP)
├── RUNBOOKS/                            # Root runbooks (KEEP)
│   └── ONCALL_HANDOFF.md
│
├── .github/                             # CI/CD (NO CHANGES)
├── ci/                                  # CI config (NO CHANGES)
├── config/                              # Config files (NO CHANGES)
├── grafana/                             # Grafana dashboards (NO CHANGES)
├── ops/                                 # Ops scripts (NO CHANGES)
├── scripts/                             # Utility scripts (NO CHANGES)
├── synthetics/                          # Synthetic monitoring (NO CHANGES)
│
├── manage.py
├── pytest.ini
├── pyproject.toml
├── requirements.txt
├── README.md
├── Makefile
└── docker-compose.yml
```

---

## 6. Frontend Folder Preparation (Proposal Only)

**DO NOT CREATE YET - Planning Only**

### Proposed Frontend Structure
```
frontend/                                # Next.js 14+ App Router
├── app/                                 # App Router pages
│   ├── layout.tsx                       # Root layout
│   ├── page.tsx                         # Home page
│   ├── tournaments/
│   │   ├── page.tsx                     # Tournament list
│   │   ├── [id]/
│   │   │   ├── page.tsx                 # Tournament details
│   │   │   ├── register/page.tsx        # Registration
│   │   │   ├── bracket/page.tsx         # Bracket view
│   │   │   └── matches/[matchId]/page.tsx
│   │   └── create/page.tsx              # Create tournament
│   ├── teams/
│   │   ├── page.tsx                     # Team list
│   │   ├── [id]/page.tsx                # Team details
│   │   └── create/page.tsx              # Create team
│   ├── profile/
│   │   └── page.tsx                     # User profile
│   ├── leaderboards/
│   │   └── page.tsx                     # Leaderboards
│   ├── auth/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   └── dashboard/
│       ├── organizer/                   # Organizer dashboard
│       └── admin/                       # Admin dashboard
│
├── components/                          # React components
│   ├── ui/                              # Base UI components (shadcn/ui)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   ├── tournaments/                     # Tournament-specific components
│   │   ├── TournamentCard.tsx
│   │   ├── TournamentList.tsx
│   │   ├── BracketView.tsx
│   │   ├── MatchCard.tsx
│   │   └── RegistrationForm.tsx
│   ├── teams/                           # Team components
│   │   ├── TeamCard.tsx
│   │   ├── TeamList.tsx
│   │   └── MemberList.tsx
│   ├── leaderboards/                    # Leaderboard components
│   │   ├── LeaderboardTable.tsx
│   │   └── PlayerRankCard.tsx
│   ├── layout/                          # Layout components
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   ├── Sidebar.tsx
│   │   └── Navigation.tsx
│   └── forms/                           # Form components
│       ├── FormField.tsx
│       ├── FormSelect.tsx
│       └── FormError.tsx
│
├── lib/                                 # Utilities & API client
│   ├── api/                             # API client layer
│   │   ├── client.ts                    # Base API client (fetch wrapper)
│   │   ├── tournaments.ts               # Tournament API methods
│   │   ├── teams.ts                     # Team API methods
│   │   ├── auth.ts                      # Auth API methods
│   │   ├── matches.ts                   # Match API methods
│   │   ├── leaderboards.ts              # Leaderboard API methods
│   │   └── websocket.ts                 # WebSocket client
│   ├── types/                           # TypeScript types (IDs-only)
│   │   ├── tournament.ts
│   │   ├── team.ts
│   │   ├── match.ts
│   │   ├── user.ts
│   │   └── api.ts                       # Generic API types
│   ├── utils/                           # Utility functions
│   │   ├── formatters.ts                # Date, currency formatters
│   │   ├── validators.ts                # Form validation
│   │   └── helpers.ts                   # General helpers
│   └── constants.ts                     # Constants
│
├── hooks/                               # Custom React hooks
│   ├── useAuth.ts                       # Authentication hook
│   ├── useTournaments.ts                # Tournament data hook
│   ├── useWebSocket.ts                  # WebSocket hook
│   ├── useLeaderboards.ts               # Leaderboard hook
│   └── useTeams.ts                      # Teams hook
│
├── styles/                              # Global styles
│   ├── globals.css                      # Global CSS + Tailwind
│   └── themes/                          # Theme variables
│
├── public/                              # Static assets
│   ├── images/
│   ├── icons/
│   └── fonts/
│
├── middleware.ts                        # Next.js middleware (auth)
├── next.config.js                       # Next.js configuration
├── tailwind.config.ts                   # Tailwind configuration
├── tsconfig.json                        # TypeScript configuration
├── package.json                         # Dependencies
└── .env.local.example                   # Environment variables template
```

### Backend ↔ Frontend Integration

**API Client Layer** (`lib/api/client.ts`):
```typescript
// Base client with authentication and error handling
class APIClient {
  baseURL: string;
  token: string | null;
  
  async request(endpoint, options) {
    // Add JWT token to headers
    // Handle Module 9.5 error format
    // Map error codes to user-friendly messages
    // Handle 401 (redirect to login)
    // Handle 403 (show permission error)
    // Return IDs-only response
  }
}
```

**Error Format Mapping** (Module 9.5):
```typescript
// Map backend error codes to frontend messages
const ERROR_MESSAGES = {
  UNAUTHENTICATED: "Please log in to continue",
  PERMISSION_DENIED: "You don't have permission",
  VALIDATION_ERROR: "Please check your input",
  RATE_LIMITED: "Too many requests, try again later",
  // ... all error codes from Module 9.5
};
```

**Auth Handling**:
```typescript
// JWT token management
// Token refresh logic
// Protected route middleware
// Login/logout flows
```

**Types/Interfaces** (IDs-Only Discipline):
```typescript
// All types match backend serializers (IDs only, no nested objects)
interface Tournament {
  id: number;
  name: string;
  game_id: number;           // ID, not nested Game object
  organizer_id: number;      // ID, not nested User object
  status: string;
  start_date: string;
  // ... all fields as per endpoint_catalog.md
}

// Client-side resolves IDs by fetching related data separately
```

**WebSocket Integration**:
```typescript
// Connect to WebSocket endpoints from endpoint_catalog.md
// Handle message types from Module 2.6 (tournament updates, match updates, bracket updates)
// Reconnection logic
// Authentication with JWT
```

---

## 7. Cleanup Execution Phases (After Approval)

### Phase 1: Delete Temporary Files (5 minutes)
```bash
# Delete root-level test outputs and debug files
rm -f debug_bracket.py fix_*.py test_debug_auth*.py
rm -f *_trace.txt *_output.txt test_*.txt failure_reject.txt h2h_fail.txt
rm -f MODULE_8.3_OBSERVABILITY_NOTES.md PHASE_9_SMOKE_AND_ALERTING.md
rm -f PHASE_E_PR_DESCRIPTION.md RELEASE_CHECKLIST_V1.md

# Delete Documents/ temporary files
rm -f Documents/staging_*.json
rm -f Documents/Phase3_Prep_Checklist.md Documents/PHASE3_PREP_STATUS.md
rm -f Documents/Phase5_*.md (except Phase5_Webhook_Evidence.md - archive first)
rm -f Documents/Development/MODULE_5.4_TEST_FIXES_NEEDED.md
```

### Phase 2: Create Archive Structure (2 minutes)
```bash
mkdir -p Documents/Archive/{Phase2,Phase3,Phase4,Phase5,Phase6,Phase7,Phase8,Phase9,PhaseE,OldPlanning/Sprints,OldReports}
# Create Archive README with index
```

### Phase 3: Archive Historical Docs (10 minutes)
```bash
# Move files according to "Files to ARCHIVE" section
# Preserve git history with `git mv`
```

### Phase 4: Reorganize Active Docs (5 minutes)
```bash
# Move to Documents/Runbooks/
git mv Documents/DB_RESET_NOTES.md Documents/Runbooks/database_reset.md
git mv Documents/MONITORING.md Documents/Runbooks/monitoring_setup.md
git mv Documents/PRODUCTION_CANARY_RUNBOOK.md Documents/Runbooks/canary_deployment.md
git mv Documents/RECEIVER_INTEGRATION_GUIDE.md Documents/Runbooks/webhook_receiver_setup.md

# Move to Documents/Planning/
git mv Documents/FRONTEND_INTEGRATION.md Documents/Planning/

# Move to Documents/ExecutionPlan/
git mv Documents/Development/MODULE_5.3_COMPLETION_STATUS.md Documents/ExecutionPlan/

# Move to docs/security/
mkdir -p docs/security
git mv SECURITY.md docs/security/
```

### Phase 5: Update References (15 minutes)
```bash
# Update MAP.md with new file locations
# Update trace.yml with new file locations
# Update README.md with new structure
# Update any cross-references in planning docs
```

### Phase 6: Commit & Verify (5 minutes)
```bash
git add -A
git commit -m "[Cleanup] Project reorganization for frontend phase

- Deleted 25+ temporary test output files
- Archived 60+ historical documents to Documents/Archive/
- Reorganized 8 active docs to proper locations
- Updated MAP.md and trace.yml references
- Standardized Documents/ folder structure
- NO SOURCE CODE CHANGES"

# Verify all tests still pass
pytest

# Verify trace.yml still validates
python scripts/verify_trace.py
```

---

## 8. Summary

### Scope
- **Delete**: 29 files (test outputs, superseded docs)
- **Archive**: ~65 files (historical docs, old reports, superseded planning)
- **Move**: 8 files (reorganize to proper locations)
- **Keep**: 200+ files (all source code, core planning, MODULE completion docs, new documentation)
- **Create**: Documents/Archive/ structure with README

### Risk Mitigation
- ✅ NO source code deletions
- ✅ NO migration deletions
- ✅ NO test file deletions
- ✅ All MODULE_*_COMPLETION_STATUS.md files preserved
- ✅ All planning documents preserved
- ✅ Git history preserved (using `git mv`)
- ✅ Archive structure for historical reference

### Expected Outcomes
1. Clean root directory (no test outputs)
2. Organized Documents/ folder (Planning, ExecutionPlan, Runbooks, Archive)
3. Clear separation of active vs. historical docs
4. Standardized structure for frontend integration
5. Easier navigation for new developers
6. Reduced clutter without losing history

---

## 9. Approval Required

**STOP - DO NOT PROCEED WITHOUT EXPLICIT APPROVAL**

This plan requires user confirmation before:
1. Deleting any files
2. Archiving any documents
3. Moving any files
4. Creating new directories

Please review this plan and approve or request modifications before cleanup execution begins.

---

**Next Steps After Approval**:
1. Execute cleanup phases 1-6
2. Update MAP.md and trace.yml
3. Verify all tests pass
4. Commit cleanup changes
5. Prepare for frontend development kickoff
