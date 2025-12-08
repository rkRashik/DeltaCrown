"""
TournamentOps domain exceptions.

This module defines exception classes for the TournamentOps orchestration layer,
covering adapter failures, registration errors, and service-level domain violations.

Reference: ROADMAP_AND_EPICS_PART_4.md - Phase 1 (Architecture Foundations)
"""


class TournamentOpsError(Exception):
    """
    Base exception for all TournamentOps domain errors.

    All domain-specific exceptions in the TournamentOps app should inherit from this.
    This allows callers to catch TournamentOpsError to handle any tournament orchestration
    error, or catch specific subclasses for targeted error handling.

    Reference: ARCH_PLAN_PART_1.md - Section 2.1 (Domain Boundaries)
    """

    pass


# ==============================================================================
# Adapter-related exceptions (Phase 1, Epic 1.1)
# ==============================================================================


class TeamNotFoundError(TournamentOpsError):
    """
    Raised when a team lookup fails in TeamAdapter.

    This indicates that a requested team_id does not exist in the teams domain.
    Services should handle this by returning appropriate user-facing error messages
    or validation failures.

    Reference: Phase 1, Epic 1.1 (Service Adapter Layer)
    """

    pass


class UserNotFoundError(TournamentOpsError):
    """
    Raised when a user lookup fails in UserAdapter.

    This indicates that a requested user_id does not exist in the user_profile domain.
    Services should handle this by returning appropriate validation errors.

    Reference: Phase 1, Epic 1.1 (Service Adapter Layer)
    """

    pass


class GameConfigNotFoundError(TournamentOpsError):
    """
    Raised when a game configuration lookup fails in GameAdapter.

    This indicates that a requested game_slug or game_id does not exist in the
    games configuration domain. This may happen if a tournament references a game
    that hasn't been configured yet.

    Reference: Phase 2, Epic 2.1 (Game Configuration Models)
    """

    pass


class PaymentFailedError(TournamentOpsError):
    """
    Raised when a payment operation fails in EconomyAdapter.

    This can occur due to insufficient balance, payment processor errors,
    or invalid transaction parameters. The exception message should contain
    details from the payment result.

    Reference: Phase 5, Epic 5.4 (Payment Integration)
    """

    pass


class EligibilityCheckFailedError(TournamentOpsError):
    """
    Raised when an eligibility check encounters an error.

    This is distinct from a user/team being ineligible (which returns a
    ValidationResult with is_valid=False). This exception indicates a system
    error during the eligibility check itself.

    Reference: Phase 5, Epic 5.1 (Smart Registration - Eligibility Rules)
    """

    pass


class AdapterHealthCheckError(TournamentOpsError):
    """
    Raised when an adapter health check fails.

    This indicates that a domain service (teams, users, games, economy) is
    unreachable or unhealthy. Services should handle this by degrading gracefully
    or returning maintenance mode messages.

    Reference: Phase 1, Epic 1.1 (Service Adapter Layer - Health Checks)
    """

    pass


# ==============================================================================
# Registration-related exceptions (Phase 4 & 5)
# ==============================================================================


class RegistrationAlreadyExistsError(TournamentOpsError):
    """
    Raised when attempting to create a duplicate registration.

    This occurs when a team tries to register for a tournament they're already
    registered for. Services should return a user-friendly message indicating
    the team is already registered.

    Reference: Phase 5, Epic 5.1 (Smart Registration)
    """

    pass


class InvalidRegistrationStateError(TournamentOpsError):
    """
    Raised when attempting an operation on a registration in an invalid state.

    For example:
    - Trying to complete a registration that's already completed
    - Trying to withdraw a registration that's already withdrawn
    - Trying to approve a registration that's already rejected

    The exception message should describe the current state and the invalid
    operation attempted.

    Reference: Phase 4, Epic 4.1 (TournamentOps Core Workflows)
    """

    pass


class RegistrationNotFoundError(TournamentOpsError):
    """
    Raised when a registration lookup fails.

    This indicates that a requested registration_id does not exist.
    Services should handle this by returning 404-style errors.

    Reference: Phase 5, Epic 5.1 (Smart Registration)
    """

    pass


# ==============================================================================
# Tournament lifecycle exceptions (Phase 4)
# ==============================================================================


class TournamentNotFoundError(TournamentOpsError):
    """
    Raised when a tournament lookup fails.

    This indicates that a requested tournament_id does not exist.

    Reference: Phase 4, Epic 4.1 (Tournament Lifecycle)
    """

    pass


class InvalidTournamentStateError(TournamentOpsError):
    """
    Raised when attempting an invalid tournament state transition.

    For example:
    - Trying to start a tournament that's already completed
    - Trying to open a tournament that's already in progress
    - Trying to complete a tournament with pending matches

    Reference: Phase 4, Epic 4.1 (Tournament Lifecycle)
    """

    pass


# ==============================================================================
# Match-related exceptions (Phase 6)
# ==============================================================================


class MatchNotFoundError(TournamentOpsError):
    """
    Raised when a match lookup fails.

    This indicates that a requested match_id does not exist.

    Reference: Phase 6, Epic 6.1 (Result Submission)
    """

    pass


class InvalidMatchStateError(TournamentOpsError):
    """
    Raised when attempting an operation on a match in an invalid state.

    For example:
    - Trying to report results for a completed match
    - Trying to void a pending match

    Reference: Phase 6, Epic 6.1 (Result Submission)
    """

    pass


class MatchResultDisputeError(TournamentOpsError):
    """
    Raised when match results from both teams don't match (dispute detected).

    This is not necessarily an error condition, but signals that the result
    needs manual review. Services should route disputed matches to the
    organizer console.

    Reference: Phase 6, Epic 6.2 (Dispute Resolution)
    """

    pass
