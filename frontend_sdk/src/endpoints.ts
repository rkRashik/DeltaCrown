/**
 * API Endpoints Configuration for DeltaCrown SDK
 *
 * Centralizes all API endpoint paths and URL builders.
 * Organized by domain for easy discovery.
 *
 * Epic: Phase 9, Epic 9.2 - JSON Schemas & TypeScript Types
 */

/**
 * Base API URL - should be configured by client
 */
export const DEFAULT_BASE_URL = 'http://localhost:8000';

/**
 * ============================================================================
 * AUTHENTICATION ENDPOINTS
 * ============================================================================
 */
export const AUTH_ENDPOINTS = {
  obtainToken: '/api/token/',
  refreshToken: '/api/token/refresh/',
  verifyToken: '/api/token/verify/',
} as const;

/**
 * ============================================================================
 * REGISTRATION ENDPOINTS
 * ============================================================================
 */
export const REGISTRATION_ENDPOINTS = {
  register: (tournamentId: number) => `/api/tournaments/v1/${tournamentId}/register/`,
  list: (tournamentId: number) => `/api/tournaments/v1/${tournamentId}/registrations/`,
  detail: (registrationId: number) => `/api/tournaments/v1/registrations/${registrationId}/`,
  cancel: (registrationId: number) => `/api/tournaments/v1/registrations/${registrationId}/cancel/`,
  checkEligibility: (tournamentId: number) => `/api/tournaments/v1/${tournamentId}/eligibility/`,
} as const;

/**
 * ============================================================================
 * TOURNAMENT ENDPOINTS
 * ============================================================================
 */
export const TOURNAMENT_ENDPOINTS = {
  list: '/api/tournaments/v1/',
  detail: (tournamentId: number) => `/api/tournaments/v1/${tournamentId}/`,
  bracket: (tournamentId: number) => `/api/tournaments/v1/${tournamentId}/bracket/`,
  standings: (tournamentId: number) => `/api/tournaments/v1/${tournamentId}/standings/`,
  myTournaments: '/api/tournaments/v1/my-tournaments/',
} as const;

/**
 * ============================================================================
 * MATCH ENDPOINTS
 * ============================================================================
 */
export const MATCH_ENDPOINTS = {
  detail: (matchId: number) => `/api/matches/v1/${matchId}/`,
  myMatches: '/api/matches/v1/my-matches/',
  submitResult: (matchId: number) => `/api/matches/v1/${matchId}/submit-result/`,
  confirmResult: (matchId: number) => `/api/matches/v1/${matchId}/confirm-result/`,
  status: (matchId: number) => `/api/matches/v1/${matchId}/status/`,
} as const;

/**
 * ============================================================================
 * DISPUTE ENDPOINTS
 * ============================================================================
 */
export const DISPUTE_ENDPOINTS = {
  create: (matchId: number) => `/api/disputes/v1/matches/${matchId}/dispute/`,
  detail: (disputeId: number) => `/api/disputes/v1/${disputeId}/`,
  list: '/api/disputes/v1/',
  myDisputes: '/api/disputes/v1/my-disputes/',
} as const;

/**
 * ============================================================================
 * ORGANIZER - RESULTS INBOX ENDPOINTS
 * ============================================================================
 */
export const ORGANIZER_RESULTS_INBOX_ENDPOINTS = {
  list: '/api/v1/organizer/results-inbox/',
  bulkAction: '/api/v1/organizer/results-inbox/bulk-action/',
} as const;

/**
 * ============================================================================
 * ORGANIZER - SCHEDULING ENDPOINTS
 * ============================================================================
 */
export const ORGANIZER_SCHEDULING_ENDPOINTS = {
  list: '/api/v1/organizer/scheduling/',
  assign: '/api/v1/organizer/scheduling/assign/',
  bulkShift: '/api/v1/organizer/scheduling/bulk-shift/',
  availableSlots: (tournamentId: number) => `/api/v1/organizer/scheduling/${tournamentId}/slots/`,
} as const;

/**
 * ============================================================================
 * ORGANIZER - STAFFING ENDPOINTS
 * ============================================================================
 */
export const ORGANIZER_STAFFING_ENDPOINTS = {
  listStaff: (tournamentId: number) => `/api/v1/organizer/staffing/${tournamentId}/`,
  assignStaff: '/api/v1/organizer/staffing/assign/',
  removeStaff: (assignmentId: number) => `/api/v1/organizer/staffing/${assignmentId}/remove/`,
  assignReferee: '/api/v1/organizer/staffing/assign-referee/',
} as const;

/**
 * ============================================================================
 * ORGANIZER - MATCH OPS (MOCC) ENDPOINTS
 * ============================================================================
 */
export const ORGANIZER_MOCC_ENDPOINTS = {
  dashboard: '/api/v1/organizer/match-ops/dashboard/',
  executeAction: '/api/v1/organizer/match-ops/action/',
  matchTimeline: (matchId: number) => `/api/v1/organizer/match-ops/${matchId}/timeline/`,
} as const;

/**
 * ============================================================================
 * ORGANIZER - AUDIT LOG ENDPOINTS
 * ============================================================================
 */
export const ORGANIZER_AUDIT_LOG_ENDPOINTS = {
  list: '/api/audit-logs/',
  detail: (logId: number) => `/api/audit-logs/${logId}/`,
  export: '/api/audit-logs/export/',
  tournamentAudit: (tournamentId: number) => `/api/audit-logs/tournament/${tournamentId}/`,
  matchAudit: (matchId: number) => `/api/audit-logs/match/${matchId}/`,
  userAudit: (userId: number) => `/api/audit-logs/user/${userId}/`,
  recentActivity: '/api/audit-logs/activity/',
} as const;

/**
 * ============================================================================
 * STATS ENDPOINTS (V1 - Basic)
 * ============================================================================
 */
export const STATS_V1_ENDPOINTS = {
  userStats: (userId: number) => `/api/stats/v1/users/${userId}/`,
  userSummary: (userId: number) => `/api/stats/v1/users/${userId}/summary/`,
  userAllStats: (userId: number) => `/api/stats/v1/users/${userId}/all/`,
  currentUserStats: '/api/stats/v1/users/me/',
  
  teamStats: (teamId: number) => `/api/stats/v1/teams/${teamId}/`,
  teamSummary: (teamId: number) => `/api/stats/v1/teams/${teamId}/summary/`,
  teamAllStats: (teamId: number) => `/api/stats/v1/teams/${teamId}/all/`,
  teamRanking: (teamId: number) => `/api/stats/v1/teams/${teamId}/ranking/`,
  teamForGame: (teamId: number, gameSlug: string) => `/api/stats/v1/teams/${teamId}/games/${gameSlug}/`,
  
  gameUserLeaderboard: (gameSlug: string) => `/api/stats/v1/games/${gameSlug}/leaderboard/`,
  gameTeamLeaderboard: (gameSlug: string) => `/api/stats/v1/games/${gameSlug}/teams/leaderboard/`,
} as const;

/**
 * ============================================================================
 * MATCH HISTORY ENDPOINTS
 * ============================================================================
 */
export const MATCH_HISTORY_ENDPOINTS = {
  userHistory: (userId: number) => `/api/tournaments/v1/history/users/${userId}/`,
  teamHistory: (teamId: number) => `/api/tournaments/v1/history/teams/${teamId}/`,
  myHistory: '/api/tournaments/v1/history/me/',
} as const;

/**
 * ============================================================================
 * ANALYTICS ENDPOINTS (V2 - Advanced)
 * ============================================================================
 */
export const ANALYTICS_V2_ENDPOINTS = {
  userAnalytics: (userId: number) => `/api/stats/v2/users/${userId}/`,
  teamAnalytics: (teamId: number) => `/api/stats/v2/teams/${teamId}/`,
} as const;

/**
 * ============================================================================
 * LEADERBOARDS ENDPOINTS
 * ============================================================================
 */
export const LEADERBOARD_ENDPOINTS = {
  get: (leaderboardType: string) => `/api/leaderboards/v2/${leaderboardType}/`,
  refresh: '/api/leaderboards/v2/refresh/',
} as const;

/**
 * ============================================================================
 * SEASONS ENDPOINTS
 * ============================================================================
 */
export const SEASON_ENDPOINTS = {
  current: '/api/seasons/current/',
  list: '/api/seasons/',
  detail: (seasonId: string) => `/api/seasons/${seasonId}/`,
} as const;

/**
 * ============================================================================
 * PAYMENT ENDPOINTS
 * ============================================================================
 */
export const PAYMENT_ENDPOINTS = {
  process: '/api/payments/v1/process/',
  status: (paymentId: number) => `/api/payments/v1/${paymentId}/status/`,
  refund: (paymentId: number) => `/api/payments/v1/${paymentId}/refund/`,
} as const;

/**
 * ============================================================================
 * API DOCUMENTATION ENDPOINTS
 * ============================================================================
 */
export const API_DOCS_ENDPOINTS = {
  schema: '/api/schema/',
  swaggerUI: '/api/docs/',
  redocUI: '/api/redoc/',
} as const;

/**
 * Utility: Build full URL
 */
export function buildUrl(baseUrl: string, path: string, params?: Record<string, any>): string {
  let url = `${baseUrl}${path}`;
  
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }
  
  return url;
}
