/**
 * Domain-Level TypeScript Types for DeltaCrown SDK
 *
 * Hand-curated, frontend-friendly types that build on types.generated.ts.
 * Organized by feature area for developer ergonomics.
 *
 * Epic: Phase 9, Epic 9.2 - JSON Schemas & TypeScript Types
 */

// Import base generated types (these will be available after generation)
// Uncomment when types.generated.ts exists:
// import * as Generated from './types.generated';

/**
 * ============================================================================
 * REGISTRATION DOMAIN
 * ============================================================================
 */

export interface RegistrationForm {
  tournament_id: number;
  participant_type: 'user' | 'team';
  participant_id: number;
  game_identity_fields?: Record<string, any>;
  custom_fields?: Record<string, any>;
  documents?: File[];
  agreed_to_rules: boolean;
}

export type RegistrationStatus =
  | 'pending'
  | 'approved'
  | 'rejected'
  | 'waitlisted'
  | 'cancelled';

export type PaymentStatus =
  | 'pending'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'refunded';

export interface RegistrationSummary {
  registration_id: number;
  tournament_id: number;
  tournament_name: string;
  participant_type: 'user' | 'team';
  participant_id: number;
  participant_name: string;
  status: RegistrationStatus;
  payment_status: PaymentStatus;
  registered_at: string;
  entry_fee?: number;
  can_cancel: boolean;
}

/**
 * ============================================================================
 * TOURNAMENT DOMAIN
 * ============================================================================
 */

export type TournamentFormat =
  | 'single_elimination'
  | 'double_elimination'
  | 'round_robin'
  | 'swiss'
  | 'group_stage';

export type TournamentStatus =
  | 'draft'
  | 'published'
  | 'registration_open'
  | 'registration_closed'
  | 'in_progress'
  | 'completed'
  | 'cancelled';

export interface TournamentSummary {
  tournament_id: number;
  name: string;
  game_slug: string;
  game_display_name: string;
  format: TournamentFormat;
  status: TournamentStatus;
  max_participants: number;
  current_participants: number;
  entry_fee?: number;
  prize_pool?: number;
  start_date: string;
  registration_deadline: string;
  created_at: string;
  can_register: boolean;
  is_registered?: boolean;
}

export interface TournamentDetail extends TournamentSummary {
  description: string;
  rules: string;
  organizer_id: number;
  organizer_name: string;
  bracket_config?: Record<string, any>;
  registration_schema?: Record<string, any>;
  stages: TournamentStage[];
}

export interface TournamentStage {
  stage_id: number;
  name: string;
  format: TournamentFormat;
  order: number;
  status: string;
  start_date?: string;
  end_date?: string;
}

/**
 * ============================================================================
 * MATCH DOMAIN
 * ============================================================================
 */

export type MatchStatus =
  | 'scheduled'
  | 'ready'
  | 'in_progress'
  | 'pending_results'
  | 'disputed'
  | 'completed'
  | 'cancelled'
  | 'forfeit';

export interface MatchSummary {
  match_id: number;
  tournament_id: number;
  round_number: number;
  match_number: number;
  participant_1_type: 'user' | 'team';
  participant_1_id: number;
  participant_1_name: string;
  participant_2_type: 'user' | 'team';
  participant_2_id: number;
  participant_2_name: string;
  status: MatchStatus;
  scheduled_at?: string;
  completed_at?: string;
  winner_type?: 'user' | 'team';
  winner_id?: number;
  score?: string;
}

export interface MatchWithResult extends MatchSummary {
  result_data?: Record<string, any>;
  submitted_by?: number;
  submitted_at?: string;
  confirmed_by?: number;
  confirmed_at?: string;
  dispute?: DisputeSummary;
}

/**
 * ============================================================================
 * RESULTS & DISPUTES DOMAIN
 * ============================================================================
 */

export interface ResultSubmission {
  match_id: number;
  winner_type: 'user' | 'team';
  winner_id: number;
  score: string;
  result_data?: Record<string, any>;
  proof_files?: File[];
}

export type DisputeStatus =
  | 'open'
  | 'under_review'
  | 'escalated'
  | 'resolved_accepted'
  | 'resolved_rejected'
  | 'resolved_modified'
  | 'dismissed';

export interface DisputeSummary {
  dispute_id: number;
  match_id: number;
  filed_by_type: 'user' | 'team';
  filed_by_id: number;
  filed_by_name: string;
  status: DisputeStatus;
  reason: string;
  filed_at: string;
  resolved_at?: string;
  resolution?: string;
}

/**
 * ============================================================================
 * ORGANIZER - RESULTS INBOX DOMAIN
 * ============================================================================
 */

export interface OrganizerReviewItem {
  submission_id: number;
  match_id: number;
  tournament_id: number;
  tournament_name: string;
  status: 'pending' | 'disputed' | 'confirmed' | 'finalized' | 'rejected';
  dispute_status?: DisputeStatus;
  created_at: string;
  auto_confirm_deadline?: string;
  is_overdue: boolean;
  priority: number;
  age_in_hours: number;
}

export interface BulkActionRequest {
  submission_ids: number[];
  action: 'finalize' | 'reject';
  reason?: string;
}

export interface BulkActionResponse {
  success_count: number;
  failed_count: number;
  results: Array<{
    submission_id: number;
    success: boolean;
    error?: string;
  }>;
}

/**
 * ============================================================================
 * ORGANIZER - SCHEDULING DOMAIN
 * ============================================================================
 */

export interface MatchSchedulingItem {
  match_id: number;
  tournament_id: number;
  round_number: number;
  match_number: number;
  participant_1_name: string;
  participant_2_name: string;
  scheduled_at?: string;
  has_conflicts: boolean;
  conflicts?: string[];
}

export interface ManualSchedulingRequest {
  match_id: number;
  scheduled_at: string;
  slot_id?: string;
  override_conflicts?: boolean;
}

export interface SchedulingSlot {
  slot_id: string;
  start_time: string;
  end_time: string;
  available: boolean;
  capacity: number;
  matches_scheduled: number;
}

/**
 * ============================================================================
 * ORGANIZER - STAFFING DOMAIN
 * ============================================================================
 */

export type StaffRole = 'referee' | 'moderator' | 'observer' | 'admin';

export interface StaffMember {
  user_id: number;
  username: string;
  email: string;
  role: StaffRole;
  assigned_at: string;
  assigned_by: number;
}

export interface RefereeAssignment {
  assignment_id: number;
  match_id: number;
  referee_id: number;
  referee_name: string;
  assigned_at: string;
  status: 'assigned' | 'acknowledged' | 'completed';
}

/**
 * ============================================================================
 * ORGANIZER - MATCH OPS (MOCC) DOMAIN
 * ============================================================================
 */

export type MoccActionType =
  | 'pause_match'
  | 'resume_match'
  | 'mark_live'
  | 'force_complete'
  | 'override_result'
  | 'add_note';

export interface MoccAction {
  match_id: number;
  action: MoccActionType;
  reason?: string;
  data?: Record<string, any>;
}

export interface MatchTimeline {
  match_id: number;
  events: Array<{
    event_id: number;
    event_type: string;
    timestamp: string;
    actor_id?: number;
    actor_name?: string;
    description: string;
    metadata?: Record<string, any>;
  }>;
}

/**
 * ============================================================================
 * ORGANIZER - AUDIT LOG DOMAIN
 * ============================================================================
 */

export type AuditAction =
  | 'tournament_created'
  | 'tournament_updated'
  | 'registration_approved'
  | 'registration_rejected'
  | 'match_scheduled'
  | 'result_finalized'
  | 'result_rejected'
  | 'dispute_created'
  | 'dispute_resolved'
  | 'staff_assigned'
  | 'staff_removed';

export interface AuditLogEntry {
  log_id: number;
  action: AuditAction;
  actor_type: 'user' | 'system';
  actor_id?: number;
  actor_name?: string;
  target_type: string;
  target_id: number;
  tournament_id?: number;
  timestamp: string;
  details?: Record<string, any>;
  ip_address?: string;
}

/**
 * ============================================================================
 * STATS & ANALYTICS DOMAIN
 * ============================================================================
 */

export interface UserStatsSummary {
  user_id: number;
  game_slug: string;
  total_matches: number;
  matches_won: number;
  matches_lost: number;
  win_rate: string;
  current_streak: number;
  longest_win_streak: number;
  longest_lose_streak: number;
  kills_total?: number;
  deaths_total?: number;
  assists_total?: number;
  kd_ratio?: string;
  elo_rating: number;
  mmr_rating: number;
}

export interface TeamStatsSummary {
  team_id: number;
  game_slug: string;
  total_matches: number;
  matches_won: number;
  matches_lost: number;
  win_rate: string;
  elo_rating: number;
  tier: 'bronze' | 'silver' | 'gold' | 'diamond' | 'crown';
  synergy_score: string;
  activity_score: string;
  last_match_at?: string;
}

export interface MatchHistoryEntry {
  match_id: number;
  tournament_id: number;
  tournament_name: string;
  game_slug: string;
  opponent_type: 'user' | 'team';
  opponent_id: number;
  opponent_name: string;
  result: 'won' | 'lost' | 'draw';
  score: string;
  played_at: string;
  elo_change?: number;
}

/**
 * ============================================================================
 * LEADERBOARDS DOMAIN
 * ============================================================================
 */

export type LeaderboardType =
  | 'global_user'
  | 'game_user'
  | 'team'
  | 'seasonal'
  | 'mmr'
  | 'elo'
  | 'tier';

export interface LeaderboardRow {
  rank: number;
  reference_id: number;
  reference_type: 'user' | 'team';
  name: string;
  game_slug?: string;
  season_id?: string;
  score: number;
  wins: number;
  losses: number;
  win_rate: string;
  tier?: string;
  elo_rating?: number;
  mmr_rating?: number;
  computed_at: string;
}

export interface LeaderboardResponse {
  leaderboard_type: LeaderboardType;
  game_slug?: string;
  season_id?: string;
  total_entries: number;
  entries: LeaderboardRow[];
}

/**
 * ============================================================================
 * SEASONS DOMAIN
 * ============================================================================
 */

export interface Season {
  season_id: string;
  name: string;
  game_slug: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  decay_rules?: {
    grace_period_days: number;
    decay_percentage: number;
    decay_interval_days: number;
  };
}

/**
 * ============================================================================
 * PAGINATION & COMMON TYPES
 * ============================================================================
 */

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiError {
  error: string;
  details?: Record<string, any>;
  status_code: number;
}

export interface SuccessResponse {
  message: string;
  data?: Record<string, any>;
}
