/**
 * DeltaCrown SDK - Main Entry Point
 *
 * TypeScript SDK for DeltaCrown Tournament Platform API.
 * Provides full type safety for frontend developers.
 *
 * Epic: Phase 9, Epic 9.2 - JSON Schemas & TypeScript Types
 *
 * @example
 * ```typescript
 * import { DeltaCrownClient, TournamentStatus } from '@deltacrown/sdk';
 *
 * const client = new DeltaCrownClient({ baseUrl: 'https://api.deltacrown.gg' });
 * const tournaments = await client.getTournaments({ status: TournamentStatus.REGISTRATION_OPEN });
 * ```
 */

// ========================================================================
// CLIENT
// ========================================================================
export { DeltaCrownClient, createClient, ApiError } from './client';
export type { DeltaCrownClientConfig } from './client';

// ========================================================================
// DOMAIN TYPES
// ========================================================================
export type {
  // Registration
  RegistrationForm,
  RegistrationStatus,
  PaymentStatus,
  RegistrationSummary,
  
  // Tournament
  TournamentFormat,
  TournamentStatus,
  TournamentSummary,
  TournamentDetail,
  TournamentStage,
  
  // Match
  MatchStatus,
  MatchSummary,
  MatchWithResult,
  
  // Results & Disputes
  ResultSubmission,
  DisputeStatus,
  DisputeSummary,
  
  // Organizer - Results Inbox
  OrganizerReviewItem,
  BulkActionRequest,
  BulkActionResponse,
  
  // Organizer - Scheduling
  MatchSchedulingItem,
  ManualSchedulingRequest,
  SchedulingSlot,
  
  // Organizer - Staffing
  StaffRole,
  StaffMember,
  RefereeAssignment,
  
  // Organizer - MOCC
  MoccActionType,
  MoccAction,
  MatchTimeline,
  
  // Organizer - Audit
  AuditAction,
  AuditLogEntry,
  
  // Stats & Analytics
  UserStatsSummary,
  TeamStatsSummary,
  MatchHistoryEntry,
  
  // Leaderboards
  LeaderboardType,
  LeaderboardRow,
  LeaderboardResponse,
  
  // Seasons
  Season,
  
  // Common
  PaginatedResponse,
  ApiError as ApiErrorResponse,
  SuccessResponse,
} from './types.domain';

// ========================================================================
// ENDPOINTS
// ========================================================================
export {
  DEFAULT_BASE_URL,
  AUTH_ENDPOINTS,
  REGISTRATION_ENDPOINTS,
  TOURNAMENT_ENDPOINTS,
  MATCH_ENDPOINTS,
  DISPUTE_ENDPOINTS,
  ORGANIZER_RESULTS_INBOX_ENDPOINTS,
  ORGANIZER_SCHEDULING_ENDPOINTS,
  ORGANIZER_STAFFING_ENDPOINTS,
  ORGANIZER_MOCC_ENDPOINTS,
  ORGANIZER_AUDIT_LOG_ENDPOINTS,
  STATS_V1_ENDPOINTS,
  MATCH_HISTORY_ENDPOINTS,
  ANALYTICS_V2_ENDPOINTS,
  LEADERBOARD_ENDPOINTS,
  SEASON_ENDPOINTS,
  PAYMENT_ENDPOINTS,
  API_DOCS_ENDPOINTS,
  buildUrl,
} from './endpoints';

// ========================================================================
// DEFAULT EXPORT
// ========================================================================
export { DeltaCrownClient as default } from './client';
