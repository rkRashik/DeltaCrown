# Task template

Copy only when a substantive task needs its own plan. Add the new public Markdown path to the narrow tracking exceptions and active-document list after reviewing its contents. Never place private evidence here.

## Identity

- Task ID / title:
- BACKLOG anchor / parent ID:
- Owner / implementer / reviewer:
- Priority / status (BACKLOG is canonical):
- Created / last reviewed (Asia/Dhaka, explicit offset):
- Repository branch / baseline SHA:
- Issue / PR / approved private evidence reference (if supplied):

## Description and objective

State the observed problem, affected user journey, evidence and measurable intended outcome. Label assumptions and unverified claims.

## Scope and exclusions

- Included code/docs/services and deliverables:
- Explicit exclusions:
- Local/staging/production boundary and actual authorization:
- Dependencies and owner actions:
- Public information review: no secrets, exploit examples, private inventories or user/media data.

## Risks

Record privacy, auth, financial, migration, operational capacity, cost and compatibility risks that actually apply. Preserve existing contracts and owner-protected material.

## Implementation plan

1. Inspect source and prior evidence; record baseline results.
2. Prepare the smallest scoped change and reviewable diff.
3. Validate in an isolated environment and document failures/limits.
4. Obtain any required production approval only after the concrete plan, tests and rollback are ready.

## Tests

| Check / command | Environment and data isolation | Expected result | Actual result / evidence / date |
|---|---|---|---|
| To be defined | Never production test data | To be defined | NOT RUN |

Record baseline failures separately, meaningful negative cases, skips and remaining unknowns. A planned check is not a PASS.

## Acceptance criteria

- [ ] Explicit functional/security/performance outcome supported by evidence.
- [ ] Compatibility and required negative cases verified.
- [ ] Owner/provider dependencies resolved or explicitly left open.
- [ ] Required CI actually executed for the reviewed revision.
- [ ] Production-specific acceptance verified separately when required.

## Rollback

Define trigger, exact reversible scope, responsible owner, retained artifacts and verification. Do not reset real data, delete media or restore an unsafe public/private state. If no runtime change occurs, say so and describe the document/source revert only.

## Evidence and limitations

Record event date, code SHA, environment, exact command/check, result, safe evidence link and limitation. Keep sensitive evidence in an approved private location; if none is supplied, state that without inventing a URL. Never copy credentials or raw incident details into a public PR.

## Completion checklist

- [ ] Scope/exclusions respected; no unrelated files staged.
- [ ] Criteria met; remaining issues have stable backlog IDs.
- [ ] BACKLOG status and evidence updated; DONE only when complete.
- [ ] STATUS timestamp/summary and HANDOFF next action updated.
- [ ] CHANGELOG retains actual event dates; relevant DECISIONS updated.
- [ ] Links/anchors, hygiene baseline, tracking boundaries and diff checked.
- [ ] Reviewed commit/PR linked; merge/deploy status stated separately.
