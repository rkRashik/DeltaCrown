# Competitive Ecosystem Audit Report
Date: 2026-05-06

## Scope
- Modules: Challenges, Scrims, Bounties, 1v1 Duels (including wager matches).
- Sources: README.md, Documents/DELTACROWN/EXECUTIVE_SUMMARY.md, Documents/DELTACROWN/Guide/DELTACROWN_PLATFORM_GUIDE (2).md.
- Note: DELTACROWN_MASTER_PLATFORM_GUIDE.md was not found in the workspace; the platform guide above was used.

## Current State Analysis

### Challenges (competition app)
- Model: apps/competition/models/challenge.py
  - Status and type enums include WAGER and SCRIM; wager_amount_dc and escrow_locked exist.
- Service: apps/competition/services/challenge_service.py
  - Create, accept, schedule, submit result, dispute, settle.
  - Creates MatchReport on result submission.
- API: apps/api/views/challenge_views.py, apps/api/serializers/challenge_serializers.py, apps/api/urls/challenge_urls.py.
- UI: apps/competition/views.py (challenge_hub, challenge_detail_page) and templates/competition/challenge_hub.html.
- Legacy: apps/challenges/models.py (deprecated) includes duel/scrim/wager types but no current logic.

### Bounties (competition app)
- Model: apps/competition/models/bounty.py and BountyClaim.
- Service: BountyService (in apps/competition/services/challenge_service.py).
- API: apps/api/views/challenge_views.py and serializers.
- UI: apps/competition/views.py (bounty_board).
- Facade: apps/competition/services/bounty_facade.py merges competition and user_profile bounties for dashboards.

### Bounties (user_profile app)
- Model: apps/user_profile/models/bounties.py with acceptance, proof, dispute models.
- Service: apps/user_profile/services/bounty_service.py implements full lifecycle, escrow, and disputes.
- API: apps/user_profile/views/bounty_api.py.
- Tests: tests/test_bounty_lifecycle.py, tests/test_team_bounty.py.

### Scrims
- active_scrims endpoint: apps/organizations/api/hub_endpoints.py expects ScrimRequest model (not present).
- MatchReport supports match_type=SCRIM, but no scrim-specific model or lifecycle exists.

### 1v1 Duels
- Legacy challenges include a duel type.
- user_profile bounties support SOLO (1v1) but are not represented as a dedicated duel module in competition.

### Wager/Economy
- Escrow engine exists in apps/economy/escrow_service.py (lock_funds, refund_funds, payout_winner).
- Competition Challenge/Bounty models include wager_amount_dc/reward_amount_dc and escrow_locked fields, but no service uses them.
- user_profile bounties use economy_services debit/credit plus wallet.pending_balance; only the creator stakes.

## Pipeline and Functional Audit

### State transitions
- Competition Challenge:
  - Implemented: OPEN -> ACCEPTED -> SCHEDULED -> COMPLETED, plus SETTLED and DISPUTED.
  - Missing: explicit IN_PROGRESS transition, ADMIN_RESOLVED flow, and escrow-linked cancel/expire handling.
- Competition Bounty:
  - Implemented: ACTIVE -> CLAIMED/VERIFIED (claim path).
  - Missing: PAID status, escrow lock/unlock, payout distribution, and dispute handling.
- user_profile Bounty:
  - Implemented: OPEN -> ACCEPTED -> IN_PROGRESS -> PENDING_RESULT -> COMPLETED/DISPUTED/EXPIRED/CANCELLED.
  - Includes escrow lock and refund with dispute workflow.
- Scrims:
  - No lifecycle; endpoint returns empty when ScrimRequest is missing.

### Verification and validation
- MatchReport + MatchVerification exist, but ChallengeService.submit_result creates MatchReport without MatchVerification; no opponent confirmation or automated verification for challenges.
- Competition bounty claims can be verified, but there is no payout or escrow validation.

### Wager/Bounty lock and unlock
- Escrow service is implemented and idempotent, but there are no call sites for competition challenges/bounties.
- user_profile bounty uses pending_balance and economy_services (soft escrow), with no acceptor stake for true wagers.

## Gap and Failure Analysis
- Scrim pipeline is missing: ScrimRequest model is not implemented; active_scrims returns empty.
- Wager pipeline is missing: WAGER challenge type exists, but wager_amount_dc is not exposed or enforced; no lock/refund/payout flows.
- Challenge verification is missing: challenge results bypass MatchVerification and dispute resolution is only a status toggle.
- Competition bounties are stubbed: reward_amount_dc/escrow_locked unused; PAID status never reached; no payout path.
- 1v1 duels are not first-class: only represented via user_profile bounties and deprecated challenge types.
- Fragmentation: two bounty systems with divergent schemas, states, and APIs; facade is display-only and hides inconsistencies.

## Actionable Recommendations (Roadmap)
1. Canonicalize the competitive ecosystem domain
   - Decide whether competition or user_profile is the canonical system.
   - Migrate or wrap legacy challenges; align APIs and UI to a single source of truth.
2. Implement escrow integration for wagers and competition bounties
   - Wire apps/economy/escrow_service.py into challenge and bounty services.
   - Expose and validate wager_amount_dc and reward_amount_dc in serializers.
   - Set escrow_locked and refund on cancel/expire; settle on verified completion.
3. Connect challenge results to verification and disputes
   - Create MatchVerification records for challenge-generated MatchReports.
   - Require opponent confirmation or time-based auto-confirm for SETTLED.
   - Implement ADMIN_RESOLVED flow with audit logs.
4. Build scrim request model and lifecycle
   - Implement ScrimRequest and use active_scrims as the public feed.
   - Define states (OPEN -> ACCEPTED -> COMPLETED) and integrate with challenges or match reports.
5. Promote 1v1 duels to first-class
   - Add duel support in competition challenges or surface user_profile bounties as Duels.
   - Provide explicit duel endpoints and UI that align with wager rules and verification.
6. Add tests and observability
   - Add tests for wager locking/refunds, challenge verification, and competition bounty payouts.
   - Log and alert on escrow failures, disputes, and incomplete state transitions.
