/**
 * DeltaCrown API Client
 *
 * Typed HTTP client for DeltaCrown Tournament Platform API.
 * Wraps core endpoints with full TypeScript type safety.
 *
 * Epic: Phase 9, Epic 9.2 - JSON Schemas & TypeScript Types
 */

import * as Endpoints from './endpoints';
import type * as Domain from './types.domain';

/**
 * Client configuration options
 */
export interface DeltaCrownClientConfig {
  baseUrl?: string;
  accessToken?: string;
  onUnauthorized?: () => void;
  onError?: (error: ApiError) => void;
}

/**
 * HTTP request options
 */
interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  headers?: Record<string, string>;
  body?: any;
  params?: Record<string, any>;
}

/**
 * API error class
 */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public details?: Record<string, any>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/**
 * Main DeltaCrown API Client
 */
export class DeltaCrownClient {
  private baseUrl: string;
  private accessToken?: string;
  private onUnauthorized?: () => void;
  private onError?: (error: ApiError) => void;

  constructor(config: DeltaCrownClientConfig = {}) {
    this.baseUrl = config.baseUrl || Endpoints.DEFAULT_BASE_URL;
    this.accessToken = config.accessToken;
    this.onUnauthorized = config.onUnauthorized;
    this.onError = config.onError;
  }

  /**
   * Set authentication token
   */
  setAccessToken(token: string): void {
    this.accessToken = token;
  }

  /**
   * Clear authentication token
   */
  clearAccessToken(): void {
    this.accessToken = undefined;
  }

  /**
   * Make HTTP request
   */
  private async request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
    const { method = 'GET', headers = {}, body, params } = options;

    // Build URL with query params
    const url = Endpoints.buildUrl(this.baseUrl, endpoint, params);

    // Build headers
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers,
    };

    // Add auth header if token available
    if (this.accessToken) {
      requestHeaders['Authorization'] = `Bearer ${this.accessToken}`;
    }

    // Make request
    try {
      const response = await fetch(url, {
        method,
        headers: requestHeaders,
        body: body ? JSON.stringify(body) : undefined,
      });

      // Handle errors
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const error = new ApiError(
          errorData.error || errorData.detail || `HTTP ${response.status}`,
          response.status,
          errorData
        );

        // Call error handlers
        if (response.status === 401 && this.onUnauthorized) {
          this.onUnauthorized();
        }
        if (this.onError) {
          this.onError(error);
        }

        throw error;
      }

      // Parse response
      if (response.status === 204) {
        return {} as T;
      }
      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) {
        throw error;
      }
      throw new ApiError('Network request failed', 0, { originalError: error });
    }
  }

  /**
   * ========================================================================
   * AUTHENTICATION
   * ========================================================================
   */

  async obtainToken(username: string, password: string): Promise<{ access: string; refresh: string }> {
    return this.request(Endpoints.AUTH_ENDPOINTS.obtainToken, {
      method: 'POST',
      body: { username, password },
    });
  }

  async refreshToken(refreshToken: string): Promise<{ access: string }> {
    return this.request(Endpoints.AUTH_ENDPOINTS.refreshToken, {
      method: 'POST',
      body: { refresh: refreshToken },
    });
  }

  /**
   * ========================================================================
   * REGISTRATION
   * ========================================================================
   */

  async register(tournamentId: number, data: Domain.RegistrationForm): Promise<Domain.RegistrationSummary> {
    return this.request(Endpoints.REGISTRATION_ENDPOINTS.register(tournamentId), {
      method: 'POST',
      body: data,
    });
  }

  async getRegistrations(tournamentId: number): Promise<Domain.PaginatedResponse<Domain.RegistrationSummary>> {
    return this.request(Endpoints.REGISTRATION_ENDPOINTS.list(tournamentId));
  }

  async getRegistration(registrationId: number): Promise<Domain.RegistrationSummary> {
    return this.request(Endpoints.REGISTRATION_ENDPOINTS.detail(registrationId));
  }

  async cancelRegistration(registrationId: number): Promise<Domain.SuccessResponse> {
    return this.request(Endpoints.REGISTRATION_ENDPOINTS.cancel(registrationId), {
      method: 'POST',
    });
  }

  async checkEligibility(tournamentId: number, participantType: 'user' | 'team', participantId: number): Promise<{
    eligible: boolean;
    reasons?: string[];
  }> {
    return this.request(Endpoints.REGISTRATION_ENDPOINTS.checkEligibility(tournamentId), {
      method: 'POST',
      body: { participant_type: participantType, participant_id: participantId },
    });
  }

  /**
   * ========================================================================
   * TOURNAMENTS
   * ========================================================================
   */

  async getTournaments(params?: {
    game_slug?: string;
    status?: Domain.TournamentStatus;
    format?: Domain.TournamentFormat;
    page?: number;
  }): Promise<Domain.PaginatedResponse<Domain.TournamentSummary>> {
    return this.request(Endpoints.TOURNAMENT_ENDPOINTS.list, { params });
  }

  async getTournament(tournamentId: number): Promise<Domain.TournamentDetail> {
    return this.request(Endpoints.TOURNAMENT_ENDPOINTS.detail(tournamentId));
  }

  async getMyTournaments(): Promise<Domain.PaginatedResponse<Domain.TournamentSummary>> {
    return this.request(Endpoints.TOURNAMENT_ENDPOINTS.myTournaments);
  }

  /**
   * ========================================================================
   * MATCHES
   * ========================================================================
   */

  async getMatch(matchId: number): Promise<Domain.MatchWithResult> {
    return this.request(Endpoints.MATCH_ENDPOINTS.detail(matchId));
  }

  async submitResult(matchId: number, data: Domain.ResultSubmission): Promise<Domain.SuccessResponse> {
    return this.request(Endpoints.MATCH_ENDPOINTS.submitResult(matchId), {
      method: 'POST',
      body: data,
    });
  }

  async confirmResult(matchId: number): Promise<Domain.SuccessResponse> {
    return this.request(Endpoints.MATCH_ENDPOINTS.confirmResult(matchId), {
      method: 'POST',
    });
  }

  /**
   * ========================================================================
   * DISPUTES
   * ========================================================================
   */

  async createDispute(matchId: number, reason: string, evidence?: string): Promise<Domain.DisputeSummary> {
    return this.request(Endpoints.DISPUTE_ENDPOINTS.create(matchId), {
      method: 'POST',
      body: { reason, evidence },
    });
  }

  async getDispute(disputeId: number): Promise<Domain.DisputeSummary> {
    return this.request(Endpoints.DISPUTE_ENDPOINTS.detail(disputeId));
  }

  /**
   * ========================================================================
   * ORGANIZER - RESULTS INBOX
   * ========================================================================
   */

  async getOrganizerResultsInbox(params?: {
    tournament_id?: number;
    status?: string;
    dispute_status?: string;
    ordering?: string;
    page?: number;
    page_size?: number;
  }): Promise<Domain.PaginatedResponse<Domain.OrganizerReviewItem>> {
    return this.request(Endpoints.ORGANIZER_RESULTS_INBOX_ENDPOINTS.list, { params });
  }

  async bulkActionResultsInbox(data: Domain.BulkActionRequest): Promise<Domain.BulkActionResponse> {
    return this.request(Endpoints.ORGANIZER_RESULTS_INBOX_ENDPOINTS.bulkAction, {
      method: 'POST',
      body: data,
    });
  }

  /**
   * ========================================================================
   * ORGANIZER - SCHEDULING
   * ========================================================================
   */

  async getSchedulingItems(params?: {
    tournament_id?: number;
    stage_id?: number;
    unscheduled_only?: boolean;
    with_conflicts?: boolean;
  }): Promise<Domain.MatchSchedulingItem[]> {
    return this.request(Endpoints.ORGANIZER_SCHEDULING_ENDPOINTS.list, { params });
  }

  async assignMatchSchedule(data: Domain.ManualSchedulingRequest): Promise<Domain.SuccessResponse> {
    return this.request(Endpoints.ORGANIZER_SCHEDULING_ENDPOINTS.assign, {
      method: 'POST',
      body: data,
    });
  }

  async getAvailableSlots(tournamentId: number): Promise<Domain.SchedulingSlot[]> {
    return this.request(Endpoints.ORGANIZER_SCHEDULING_ENDPOINTS.availableSlots(tournamentId));
  }

  /**
   * ========================================================================
   * ORGANIZER - STAFFING
   * ========================================================================
   */

  async getStaffMembers(tournamentId: number): Promise<Domain.StaffMember[]> {
    return this.request(Endpoints.ORGANIZER_STAFFING_ENDPOINTS.listStaff(tournamentId));
  }

  async assignStaff(tournamentId: number, userId: number, role: Domain.StaffRole): Promise<Domain.SuccessResponse> {
    return this.request(Endpoints.ORGANIZER_STAFFING_ENDPOINTS.assignStaff, {
      method: 'POST',
      body: { tournament_id: tournamentId, user_id: userId, role },
    });
  }

  async assignReferee(matchId: number, refereeId: number): Promise<Domain.RefereeAssignment> {
    return this.request(Endpoints.ORGANIZER_STAFFING_ENDPOINTS.assignReferee, {
      method: 'POST',
      body: { match_id: matchId, referee_id: refereeId },
    });
  }

  /**
   * ========================================================================
   * ORGANIZER - MATCH OPS (MOCC)
   * ========================================================================
   */

  async executeMoccAction(data: Domain.MoccAction): Promise<Domain.SuccessResponse> {
    return this.request(Endpoints.ORGANIZER_MOCC_ENDPOINTS.executeAction, {
      method: 'POST',
      body: data,
    });
  }

  async getMatchTimeline(matchId: number): Promise<Domain.MatchTimeline> {
    return this.request(Endpoints.ORGANIZER_MOCC_ENDPOINTS.matchTimeline(matchId));
  }

  /**
   * ========================================================================
   * ORGANIZER - AUDIT LOGS
   * ========================================================================
   */

  async getAuditLogs(params?: {
    action?: Domain.AuditAction;
    tournament_id?: number;
    actor_id?: number;
    date_from?: string;
    date_to?: string;
    page?: number;
  }): Promise<Domain.PaginatedResponse<Domain.AuditLogEntry>> {
    return this.request(Endpoints.ORGANIZER_AUDIT_LOG_ENDPOINTS.list, { params });
  }

  async getTournamentAuditTrail(tournamentId: number): Promise<Domain.AuditLogEntry[]> {
    return this.request(Endpoints.ORGANIZER_AUDIT_LOG_ENDPOINTS.tournamentAudit(tournamentId));
  }

  /**
   * ========================================================================
   * STATS & HISTORY
   * ========================================================================
   */

  async getUserStats(userId: number, gameSlug?: string): Promise<Domain.UserStatsSummary> {
    return this.request(Endpoints.STATS_V1_ENDPOINTS.userStats(userId), {
      params: gameSlug ? { game_slug: gameSlug } : undefined,
    });
  }

  async getTeamStats(teamId: number, gameSlug?: string): Promise<Domain.TeamStatsSummary> {
    return this.request(Endpoints.STATS_V1_ENDPOINTS.teamStats(teamId), {
      params: gameSlug ? { game_slug: gameSlug } : undefined,
    });
  }

  async getUserMatchHistory(userId: number, params?: {
    game_slug?: string;
    limit?: number;
    offset?: number;
  }): Promise<Domain.PaginatedResponse<Domain.MatchHistoryEntry>> {
    return this.request(Endpoints.MATCH_HISTORY_ENDPOINTS.userHistory(userId), { params });
  }

  async getTeamMatchHistory(teamId: number, params?: {
    game_slug?: string;
    limit?: number;
    offset?: number;
  }): Promise<Domain.PaginatedResponse<Domain.MatchHistoryEntry>> {
    return this.request(Endpoints.MATCH_HISTORY_ENDPOINTS.teamHistory(teamId), { params });
  }

  /**
   * ========================================================================
   * LEADERBOARDS
   * ========================================================================
   */

  async getLeaderboard(
    leaderboardType: Domain.LeaderboardType,
    params?: {
      game_slug?: string;
      season_id?: string;
      limit?: number;
    }
  ): Promise<Domain.LeaderboardResponse> {
    return this.request(Endpoints.LEADERBOARD_ENDPOINTS.get(leaderboardType), { params });
  }

  /**
   * ========================================================================
   * SEASONS
   * ========================================================================
   */

  async getCurrentSeason(gameSlug?: string): Promise<Domain.Season> {
    return this.request(Endpoints.SEASON_ENDPOINTS.current, {
      params: gameSlug ? { game_slug: gameSlug } : undefined,
    });
  }

  async getSeasons(params?: {
    game_slug?: string;
    include_inactive?: boolean;
  }): Promise<Domain.Season[]> {
    return this.request(Endpoints.SEASON_ENDPOINTS.list, { params });
  }
}

/**
 * Create a new DeltaCrown API client instance
 */
export function createClient(config?: DeltaCrownClientConfig): DeltaCrownClient {
  return new DeltaCrownClient(config);
}

/**
 * Default export
 */
export default DeltaCrownClient;
