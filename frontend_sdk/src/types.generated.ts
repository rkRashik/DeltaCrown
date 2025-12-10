/**
 * Auto-Generated TypeScript Types for DeltaCrown API
 *
 * Generated: 2025-12-10T17:48:36.539975
 * Source: schema.yml (OpenAPI 3.0)
 * Generator: tools/generate_frontend_types.py
 *
 * DO NOT EDIT MANUALLY - Regenerate with: pnpm run generate
 *
 * Epic: Phase 9, Epic 9.2 - JSON Schemas & TypeScript Types
 */

/* eslint-disable */
/* tslint:disable */

/**
 * * `single-elimination` - Single Elimination
* `double-elimination` - Double Elimination
* `round-robin` - Round Robin
 */
export type BracketFormatEnum = "single-elimination" | "double-elimination" | "round-robin";

/**
 * * `1` - 1v1
* `2` - 2v2
* `3` - 3v3
* `4` - 4v4
* `5` - 5v5
* `0` - Variable
 */
export type DefaultTeamSizeEnum = "1" | "2" | "3" | "4" | "5" | "0";

/**
 * * `single_elimination` - Single Elimination
* `double_elimination` - Double Elimination
* `round_robin` - Round Robin
* `swiss` - Swiss
* `group_playoff` - Group Stage + Playoff
 */
export type FormatEnum = "single_elimination" | "double_elimination" | "round_robin" | "swiss" | "group_playoff";

/**
 * * `bkash` - bKash
* `nagad` - Nagad
* `rocket` - Rocket
* `bank` - Bank Transfer
* `other` - Other
 */
export type MethodEnum = "bkash" | "nagad" | "rocket" | "bank" | "other";

/**
 * * `team` - Team
* `solo` - Solo/Individual
 */
export type ParticipationTypeEnum = "team" | "solo";

/**
 * * `deltacoin` - DeltaCoin
* `bkash` - bKash
* `nagad` - Nagad
* `rocket` - Rocket
* `bank_transfer` - Bank Transfer
 */
export type PaymentMethodsEnum = "deltacoin" | "bkash" | "nagad" | "rocket" | "bank_transfer";

/**
 * * `pending` - Pending
* `verified` - Verified
* `rejected` - Rejected
* `refunded` - Refunded
 */
export type PaymentVerificationStatusEnum = "pending" | "verified" | "rejected" | "refunded";

/**
 * * `OWNER` - Team Owner
* `GENERAL_MANAGER` - General Manager
* `TEAM_MANAGER` - Team Manager
* `HEAD_COACH` - Head Coach
* `ASSISTANT_COACH` - Assistant Coach
* `PERFORMANCE_COACH` - Performance Coach
* `ANALYST` - Analyst
* `STRATEGIST` - Strategist
* `DATA_ANALYST` - Data Analyst
* `PLAYER` - Player
* `SUBSTITUTE` - Substitute
* `CONTENT_CREATOR` - Content Creator
* `SOCIAL_MEDIA_MANAGER` - Social Media Manager
* `COMMUNITY_MANAGER` - Community Manager
* `MANAGER` - Manager (Legacy)
* `COACH` - Coach (Legacy)
* `CAPTAIN` - Captain (Legacy)
* `SUB` - Substitute (Legacy)
 */
export type RoleEnum = "OWNER" | "GENERAL_MANAGER" | "TEAM_MANAGER" | "HEAD_COACH" | "ASSISTANT_COACH" | "PERFORMANCE_COACH" | "ANALYST" | "STRATEGIST" | "DATA_ANALYST" | "PLAYER" | "SUBSTITUTE" | "CONTENT_CREATOR" | "SOCIAL_MEDIA_MANAGER" | "COMMUNITY_MANAGER" | "MANAGER" | "COACH" | "CAPTAIN" | "SUB";

/**
 * * `slot-order` - Slot Order (Registration order)
* `random` - Random
* `manual` - Manual (requires seed values)
* `ranked` - Ranked (from team rankings)
 */
export type SeedingMethodEnum = "slot-order" | "random" | "manual" | "ranked";

/**
 * * `scheduled` - Scheduled
* `check_in` - Check-in Open
* `ready` - Ready to Start
* `live` - Live/In Progress
* `pending_result` - Pending Result
* `completed` - Completed
* `disputed` - Disputed
* `forfeit` - Forfeit
* `cancelled` - Cancelled
 */
export type StateEnum = "scheduled" | "check_in" | "ready" | "live" | "pending_result" | "completed" | "disputed" | "forfeit" | "cancelled";

/**
 * * `draft` - Draft
* `submitted` - Submitted
* `pending` - Pending
* `auto_approved` - Auto Approved
* `needs_review` - Needs Review
* `payment_submitted` - Payment Submitted
* `confirmed` - Confirmed
* `rejected` - Rejected
* `cancelled` - Cancelled
* `waitlisted` - Waitlisted
* `no_show` - No Show
 */
export type Status1f9Enum = "draft" | "submitted" | "pending" | "auto_approved" | "needs_review" | "payment_submitted" | "confirmed" | "rejected" | "cancelled" | "waitlisted" | "no_show";

/**
 * * `draft` - Draft
* `pending_approval` - Pending Approval
* `published` - Published
* `registration_open` - Registration Open
* `registration_closed` - Registration Closed
* `live` - Live
* `completed` - Completed
* `cancelled` - Cancelled
* `archived` - Archived
 */
export type StatusC51Enum = "draft" | "pending_approval" | "published" | "registration_open" | "registration_closed" | "live" | "completed" | "cancelled" | "archived";

/**
 * * `PENDING` - Pending
* `ACCEPTED` - Accepted
* `DECLINED` - Declined
* `EXPIRED` - Expired
* `CANCELLED` - Cancelled
 */
export type TeamInviteStatusEnum = "PENDING" | "ACCEPTED" | "DECLINED" | "EXPIRED" | "CANCELLED";

/**
 * * `bronze` - bronze
* `silver` - silver
* `gold` - gold
* `diamond` - diamond
* `crown` - crown
 */
export type TierEnum = "bronze" | "silver" | "gold" | "diamond" | "crown";

/**
 * Serializer for referee assignment request.

Reference: Phase 7, Epic 7.3 - Assign Referee Endpoint
 */
export interface AssignRefereeRequestRequest {
  staff_assignment_id: number;
  is_primary?: boolean | undefined;
  notes?: string | undefined;
  check_load?: boolean | undefined;
}

/**
 * Serializer for referee assignment response (includes warning).

Reference: Phase 7, Epic 7.3 - Assign Referee Response
 */
export interface AssignRefereeResponse {
  assignment?: any | undefined;
  warning?: string | null | undefined;
}

/**
 * Serializer for staff assignment request.

Reference: Phase 7, Epic 7.3 - Assign Staff Endpoint
 */
export interface AssignStaffRequestRequest {
  user_id: number;
  role_code: string;
  stage_id?: number | null | undefined;
  notes?: string | undefined;
}

/**
 * Serializer for Bracket model (list view).

Read-only basic bracket information without nodes.
 */
export interface Bracket {
  id: number;
  tournament_id: number;
  tournament_name: string;
  format: string;
  format_display: string;
  seeding_method: string;
  seeding_method_display: string;
  total_rounds: number;
  total_matches: number;
  is_finalized: boolean;
  generated_at: string;
  updated_at: string;
}

/**
 * Serializer for Bracket model (detail view with nodes).

Includes full bracket structure with all nodes.
 */
export interface BracketDetail {
  id: number;
  tournament_id: number;
  tournament_name: string;
  format: string;
  format_display: string;
  seeding_method: string;
  seeding_method_display: string;
  total_rounds: number;
  total_matches: number;
  is_finalized: boolean;
  generated_at: string;
  updated_at: string;
  bracket_structure: any;
  nodes?: string | undefined;
}

/**
 * Serializer for bracket generation request.

Validates bracket generation parameters for POST /api/brackets/tournaments/{id}/generate/

Module: 4.1 - Bracket Generation API
Source: PHASE_4_IMPLEMENTATION_PLAN.md Module 4.1 Technical Requirements
 */
export interface BracketGeneration {
  /** Bracket format (defaults to tournament.format)

* `single-elimination` - Single Elimination
* `double-elimination` - Double Elimination
* `round-robin` - Round Robin */
  bracket_format?: any | undefined;
  /** Seeding strategy for participant placement

* `slot-order` - Slot Order (Registration order)
* `random` - Random
* `manual` - Manual (requires seed values)
* `ranked` - Ranked (from team rankings) */
  seeding_method?: any | undefined;
  /** Optional: Manual participant selection (registration IDs) */
  participant_ids?: Array<number | undefined> | undefined;
}

/**
 * Serializer for bracket generation request.

Validates bracket generation parameters for POST /api/brackets/tournaments/{id}/generate/

Module: 4.1 - Bracket Generation API
Source: PHASE_4_IMPLEMENTATION_PLAN.md Module 4.1 Technical Requirements
 */
export interface BracketGenerationRequest {
  /** Bracket format (defaults to tournament.format)

* `single-elimination` - Single Elimination
* `double-elimination` - Double Elimination
* `round-robin` - Round Robin */
  bracket_format?: any | undefined;
  /** Seeding strategy for participant placement

* `slot-order` - Slot Order (Registration order)
* `random` - Random
* `manual` - Manual (requires seed values)
* `ranked` - Ranked (from team rankings) */
  seeding_method?: any | undefined;
  /** Optional: Manual participant selection (registration IDs) */
  participant_ids?: Array<number | undefined> | undefined;
}

/**
 * Serializer for Bracket model (list view).

Read-only basic bracket information without nodes.
 */
export interface BracketRequest {
  id: number;
  tournament_id: number;
  tournament_name: string;
  format: string;
  format_display: string;
  seeding_method: string;
  seeding_method_display: string;
  total_rounds: number;
  total_matches: number;
  is_finalized: boolean;
  generated_at: string;
  updated_at: string;
}

/**
 * Serializer for bulk check-in request
 */
export interface BulkCheckin {
  /** List of registration IDs to check in (max 200) */
  registration_ids: Array<number | undefined>;
}

/**
 * Serializer for bulk check-in request
 */
export interface BulkCheckinRequest {
  /** List of registration IDs to check in (max 200) */
  registration_ids: Array<number | undefined>;
}

/**
 * Serializer for user who performed check-in
 */
export interface CheckedInBy {
  id?: number | undefined;
  /** Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only. */
  username: string;
  email: string;
}

/**
 * Serializer for check-in status response
 */
export interface CheckinStatus {
  id?: number | undefined;
  tournament_id?: number | undefined;
  tournament_title?: string | undefined;
  registration_type?: string | undefined;
  /** Current registration status

* `draft` - Draft
* `submitted` - Submitted
* `pending` - Pending
* `auto_approved` - Auto Approved
* `needs_review` - Needs Review
* `payment_submitted` - Payment Submitted
* `confirmed` - Confirmed
* `rejected` - Rejected
* `cancelled` - Cancelled
* `waitlisted` - Waitlisted
* `no_show` - No Show */
  status?: any | undefined;
  /** Whether participant has checked in on tournament day */
  checked_in?: boolean | undefined;
  /** When participant checked in */
  checked_in_at?: string | null | undefined;
  /** User who performed the check-in (owner, captain, or organizer) */
  checked_in_by?: number | null | undefined;
  checked_in_by_details?: any | undefined;
  can_undo?: string | undefined;
}

/**
 * Minimal game serializer for tournament relations.
 */
export interface Game {
  id?: number | undefined;
  name?: string | undefined;
  slug?: string | undefined;
  /** Game icon/logo image */
  icon?: string | undefined;
  /** Default team size for this game

* `1` - 1v1
* `2` - 2v2
* `3` - 3v3
* `4` - 4v4
* `5` - 5v5
* `0` - Variable */
  default_team_size?: any | undefined;
  /** Whether this game is actively supported */
  is_active?: boolean | undefined;
}

/**
 * Read-only serializer for game configuration.

Returns the full game_config JSONB or default schema.

Example response:
{
    "schema_version": "1.0",
    "allowed_formats": ["single_elimination", "double_elimination"],
    "team_size_range": [1, 5],
    "custom_field_schemas": [],
    "match_settings": {"default_best_of": 1, "available_maps": []}
}
 */
export interface GameConfig {
  schema_version?: string | undefined;
  allowed_formats?: Array<string | undefined> | undefined;
  team_size_range?: Array<number | undefined> | undefined;
  custom_field_schemas?: Array<Record<string, any> | undefined> | undefined;
  match_settings?: Record<string, any> | undefined;
}

/**
 * Serializer for leaderboard entries.
 */
export interface LeaderboardEntry {
  leaderboard_type: string;
  rank: number;
  reference_id: number;
  game_slug?: string | null | undefined;
  season_id?: string | null | undefined;
  score: number;
  wins: number;
  losses: number;
  win_rate: string;
  payload: any;
  computed_at?: string | null | undefined;
}

/**
 * Serializer for leaderboard refresh requests.
 */
export interface LeaderboardRefreshRequestRequest {
  /** Optional list of specific leaderboard types to refresh */
  leaderboard_types?: Array<string | undefined> | undefined;
  /** Force immediate refresh even if recently updated */
  force?: boolean | undefined;
}

/**
 * Read-only serializer for match responses (no PII).
 */
export interface Match {
  id?: number | undefined;
  tournament_id?: number | undefined;
  /** Round number in bracket (1 = first round) */
  round_number?: number | undefined;
  /** Current state in match lifecycle

* `scheduled` - Scheduled
* `check_in` - Check-in Open
* `ready` - Ready to Start
* `live` - Live/In Progress
* `pending_result` - Pending Result
* `completed` - Completed
* `disputed` - Disputed
* `forfeit` - Forfeit
* `cancelled` - Cancelled */
  state?: any | undefined;
  sides?: string | undefined;
  /** When match is scheduled to start */
  scheduled_time?: string | null | undefined;
  /** When match actually started (state → LIVE) */
  started_at?: string | null | undefined;
  /** When match was completed (state → COMPLETED) */
  completed_at?: string | null | undefined;
  /** Timestamp when this record was created */
  created_at?: string | undefined;
  /** Timestamp when this record was last updated */
  updated_at?: string | undefined;
}

/**
 * Serializer for match referee assignment information.

Reference: Phase 7, Epic 7.3 - Referee Assignment API
 */
export interface MatchRefereeAssignment {
  assignment_id?: number | undefined;
  match_id?: number | undefined;
  tournament_id?: number | undefined;
  stage_id?: number | undefined;
  round_number?: number | undefined;
  match_number?: number | undefined;
  staff_assignment?: any | undefined;
  is_primary?: boolean | undefined;
  assigned_by_user_id?: number | null | undefined;
  assigned_by_username?: string | null | undefined;
  assigned_at?: string | undefined;
  notes?: string | undefined;
}

/**
 * Read-only serializer for match result status.

Used for response payloads after submit/confirm/dispute operations.

Fields:
- id: Match ID
- tournament_id: Tournament ID
- tournament_name: Tournament name (read-only)
- bracket_id: Bracket ID
- round_number: Round number
- match_number: Match number
- state: Current match state
- participant1_id: Participant 1 ID
- participant1_name: Participant 1 name
- participant1_score: Participant 1 score
- participant2_id: Participant 2 ID
- participant2_name: Participant 2 name
- participant2_score: Participant 2 score
- winner_id: Winner ID (nullable)
- loser_id: Loser ID (nullable)
- started_at: Match start timestamp
- completed_at: Match completion timestamp
- has_result: Boolean computed property
 */
export interface MatchResult {
  id?: number | undefined;
  /** Tournament this match belongs to */
  tournament_id?: number | undefined;
  tournament_name?: string | undefined;
  /** Bracket this match belongs to (null for group stage) */
  bracket_id?: number | null | undefined;
  /** Round number in bracket (1 = first round) */
  round_number?: number | undefined;
  /** Match number within round */
  match_number?: number | undefined;
  /** Current state in match lifecycle

* `scheduled` - Scheduled
* `check_in` - Check-in Open
* `ready` - Ready to Start
* `live` - Live/In Progress
* `pending_result` - Pending Result
* `completed` - Completed
* `disputed` - Disputed
* `forfeit` - Forfeit
* `cancelled` - Cancelled */
  state?: any | undefined;
  /** Team ID or User ID for participant 1 */
  participant1_id?: number | null | undefined;
  /** Denormalized name for display */
  participant1_name?: string | undefined;
  /** Score for participant 1 */
  participant1_score?: number | undefined;
  /** Team ID or User ID for participant 2 */
  participant2_id?: number | null | undefined;
  /** Denormalized name for display */
  participant2_name?: string | undefined;
  /** Score for participant 2 */
  participant2_score?: number | undefined;
  /** Team ID or User ID of winner (set when match completed) */
  winner_id?: number | null | undefined;
  /** Team ID or User ID of loser (set when match completed) */
  loser_id?: number | null | undefined;
  /** When match actually started (state → LIVE) */
  started_at?: string | null | undefined;
  /** When match was completed (state → COMPLETED) */
  completed_at?: string | null | undefined;
  has_result?: string | undefined;
}

export interface PaginatedBracketList {
  count: number;
  next?: string | null | undefined;
  previous?: string | null | undefined;
  results: Array<Bracket | undefined>;
}

export interface PaginatedMatchList {
  count: number;
  next?: string | null | undefined;
  previous?: string | null | undefined;
  results: Array<Match | undefined>;
}

export interface PaginatedTeamInviteList {
  count: number;
  next?: string | null | undefined;
  previous?: string | null | undefined;
  results: Array<TeamInvite | undefined>;
}

export interface PaginatedTeamListList {
  count: number;
  next?: string | null | undefined;
  previous?: string | null | undefined;
  results: Array<TeamList | undefined>;
}

export interface PaginatedTournamentListList {
  count: number;
  next?: string | null | undefined;
  previous?: string | null | undefined;
  results: Array<TournamentList | undefined>;
}

/**
 * Serializer for team updates (captain only).
 */
export interface PatchedTeamUpdateRequest {
  /** Brief team description */
  description?: string | undefined;
  /** Team logo image */
  logo?: string | null | undefined;
  banner_image?: string | null | undefined;
  roster_image?: string | null | undefined;
  region?: string | undefined;
  twitter?: string | undefined;
  instagram?: string | undefined;
  discord?: string | undefined;
  youtube?: string | undefined;
  twitch?: string | undefined;
  linktree?: string | undefined;
}

/**
 * Serializer for updating tournaments (DRAFT status only).

All fields are optional for partial updates.
Delegates to TournamentService.update_tournament().
 */
export interface PatchedTournamentUpdateRequest {
  name?: string | undefined;
  description?: string | undefined;
  format?: FormatEnum | undefined;
  participation_type?: ParticipationTypeEnum | undefined;
  max_participants?: number | undefined;
  min_participants?: number | undefined;
  registration_start?: string | undefined;
  registration_end?: string | undefined;
  tournament_start?: string | undefined;
  tournament_end?: string | null | undefined;
  prize_pool?: string | undefined;
  prize_currency?: string | undefined;
  prize_deltacoin?: number | undefined;
  prize_distribution?: any | undefined;
  has_entry_fee?: boolean | undefined;
  entry_fee_amount?: string | undefined;
  entry_fee_currency?: string | undefined;
  entry_fee_deltacoin?: number | undefined;
  payment_methods?: Array<PaymentMethodsEnum | undefined> | undefined;
  enable_fee_waiver?: boolean | undefined;
  fee_waiver_top_n_teams?: number | undefined;
  banner_image?: string | null | undefined;
  thumbnail_image?: string | null | undefined;
  rules_pdf?: string | null | undefined;
  promo_video_url?: string | undefined;
  stream_youtube_url?: string | undefined;
  stream_twitch_url?: string | undefined;
  enable_check_in?: boolean | undefined;
  check_in_minutes_before?: number | undefined;
  enable_dynamic_seeding?: boolean | undefined;
  enable_live_updates?: boolean | undefined;
  enable_certificates?: boolean | undefined;
  enable_challenges?: boolean | undefined;
  enable_fan_voting?: boolean | undefined;
  rules_text?: string | undefined;
  meta_description?: string | undefined;
  meta_keywords?: Array<string | undefined> | undefined;
  game_id?: number | undefined;
}

/**
 * Read-only serializer for payment verification responses (no PII).
 */
export interface PaymentVerification {
  id?: number | undefined;
  registration_id?: number | undefined;
  status?: any | undefined;
  method?: any | undefined;
  /** Transaction ID from bKash/Nagad/Rocket */
  transaction_id?: string | undefined;
  /** Your bKash/Nagad/Rocket account number (payer) */
  payer_account_number?: string | undefined;
  amount_bdt?: number | null | undefined;
  verified_at?: string | null | undefined;
  rejected_at?: string | null | undefined;
  refunded_at?: string | null | undefined;
  notes?: any | undefined;
  created_at?: string | undefined;
  updated_at?: string | undefined;
}

/**
 * Serializer for PaymentVerification nested in registration response.
 */
export interface PaymentVerificationRequest {
  method?: MethodEnum | undefined;
  /** Transaction ID from bKash/Nagad/Rocket */
  transaction_id?: string | undefined;
  /** Your bKash/Nagad/Rocket account number (payer) */
  payer_account_number?: string | undefined;
  amount_bdt?: number | null | undefined;
}

/**
 * Base registration serializer.
 */
export interface Registration {
  id?: number | undefined;
  /** Tournament being registered for */
  tournament: number;
  /** User who registered (for solo tournaments or team captain) */
  user?: number | null | undefined;
  /** Team ID reference (for team tournaments, IntegerField to avoid circular dependency) */
  team_id?: number | null | undefined;
  /** Current registration status

* `draft` - Draft
* `submitted` - Submitted
* `pending` - Pending
* `auto_approved` - Auto Approved
* `needs_review` - Needs Review
* `payment_submitted` - Payment Submitted
* `confirmed` - Confirmed
* `rejected` - Rejected
* `cancelled` - Cancelled
* `waitlisted` - Waitlisted
* `no_show` - No Show */
  status?: any | undefined;
  /** Timestamp when this record was created */
  created_at?: string | undefined;
  payment_verification?: any | undefined;
}

/**
 * Base registration serializer.
 */
export interface RegistrationRequest {
  /** Tournament being registered for */
  tournament: number;
  /** Team ID reference (for team tournaments, IntegerField to avoid circular dependency) */
  team_id?: number | null | undefined;
}

/**
 * Serializer for staff removal response.

Reference: Phase 7, Epic 7.3 - Remove Staff Endpoint
 */
export interface RemoveStaffResponse {
  assignment?: any | undefined;
  message?: string | undefined;
}

/**
 * Serializer for seasons.
 */
export interface Season {
  season_id: string;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
  decay_rules: any;
}

/**
 * Serializer for staff workload information.

Reference: Phase 7, Epic 7.3 - Staff Load API
 */
export interface StaffLoad {
  staff_assignment?: any | undefined;
  total_matches_assigned?: number | undefined;
  upcoming_matches?: number | undefined;
  completed_matches?: number | undefined;
  concurrent_matches?: number | undefined;
  is_overloaded?: boolean | undefined;
  load_percentage?: number | undefined;
}

/**
 * Serializer for staff role information.

Reference: Phase 7, Epic 7.3 - Staff Roles API
 */
export interface StaffRole {
  role_id?: number | undefined;
  name?: string | undefined;
  code?: string | undefined;
  description?: string | undefined;
  capabilities?: Record<string, any> | undefined;
  is_referee_role?: boolean | undefined;
  created_at?: string | undefined;
  updated_at?: string | undefined;
}

/**
 * Serializer for team analytics snapshots.
 */
export interface TeamAnalytics {
  team_id: number;
  game_slug: string;
  elo_snapshot: number;
  elo_volatility: string;
  avg_member_skill: string;
  win_rate: string;
  win_rate_7d: string;
  win_rate_30d: string;
  synergy_score: string;
  activity_score: string;
  matches_last_7d: number;
  matches_last_30d: number;
  tier: TierEnum;
  percentile_rank: string;
  recalculated_at: string;
}

/**
 * Serializer for team creation.
 */
export interface TeamCreate {
  /** Team name must be unique */
  name: string;
  /** Team tag/abbreviation (2-10 characters) */
  tag: string;
  /** Which game this team competes in (blank for legacy teams). */
  game?: string | undefined;
  /** Brief team description */
  description?: string | undefined;
  /** Team logo image */
  logo?: string | null | undefined;
  region?: string | undefined;
}

/**
 * Serializer for team creation.
 */
export interface TeamCreateRequest {
  /** Team name must be unique */
  name: string;
  /** Team tag/abbreviation (2-10 characters) */
  tag: string;
  /** Which game this team competes in (blank for legacy teams). */
  game?: string | undefined;
  /** Brief team description */
  description?: string | undefined;
  /** Team logo image */
  logo?: string | null | undefined;
  region?: string | undefined;
}

/**
 * Serializer for team detail view (full fields).
 */
export interface TeamDetail {
  id?: number | undefined;
  /** Team name must be unique */
  name: string;
  /** Team tag/abbreviation (2-10 characters) */
  tag: string;
  /** Unique per game */
  slug?: string | undefined;
  /** Which game this team competes in (blank for legacy teams). */
  game?: string | undefined;
  /** Brief team description */
  description?: string | undefined;
  /** Team logo image */
  logo?: string | null | undefined;
  banner_image?: string | null | undefined;
  roster_image?: string | null | undefined;
  region?: string | undefined;
  captain?: any | undefined;
  members?: string | undefined;
  twitter?: string | undefined;
  instagram?: string | undefined;
  discord?: string | undefined;
  youtube?: string | undefined;
  twitch?: string | undefined;
  linktree?: string | undefined;
  /** Team is active and visible */
  is_active?: boolean | undefined;
  /** Verified team badge */
  is_verified?: boolean | undefined;
  /** Featured team status */
  is_featured?: boolean | undefined;
  /** Number of followers */
  followers_count?: number | undefined;
  /** Number of posts */
  posts_count?: number | undefined;
  created_at?: string | undefined;
  updated_at?: string | undefined;
}

/**
 * Serializer for team detail view (full fields).
 */
export interface TeamDetailRequest {
  /** Team name must be unique */
  name: string;
  /** Team tag/abbreviation (2-10 characters) */
  tag: string;
  /** Which game this team competes in (blank for legacy teams). */
  game?: string | undefined;
  /** Brief team description */
  description?: string | undefined;
  /** Team logo image */
  logo?: string | null | undefined;
  banner_image?: string | null | undefined;
  roster_image?: string | null | undefined;
  region?: string | undefined;
  twitter?: string | undefined;
  instagram?: string | undefined;
  discord?: string | undefined;
  youtube?: string | undefined;
  twitch?: string | undefined;
  linktree?: string | undefined;
  /** Team is active and visible */
  is_active?: boolean | undefined;
  /** Verified team badge */
  is_verified?: boolean | undefined;
  /** Featured team status */
  is_featured?: boolean | undefined;
  /** Number of followers */
  followers_count?: number | undefined;
  /** Number of posts */
  posts_count?: number | undefined;
}

/**
 * Serializer for team invitations.
 */
export interface TeamInvite {
  id?: number | undefined;
  team: number;
  team_name?: string | undefined;
  invited_user?: number | null | undefined;
  invited_username?: string | null | undefined;
  inviter?: number | null | undefined;
  inviter_username?: string | null | undefined;
  role?: RoleEnum | undefined;
  status?: any | undefined;
  created_at?: string | undefined;
  expires_at?: string | null | undefined;
}

/**
 * Serializer for team invitations.
 */
export interface TeamInviteRequest {
  team: number;
  invited_user?: number | null | undefined;
  inviter?: number | null | undefined;
  role?: RoleEnum | undefined;
}

/**
 * Serializer for team list view (minimal fields).
 */
export interface TeamList {
  id?: number | undefined;
  /** Team name must be unique */
  name?: string | undefined;
  /** Team tag/abbreviation (2-10 characters) */
  tag?: string | undefined;
  /** Unique per game */
  slug?: string | undefined;
  /** Which game this team competes in (blank for legacy teams). */
  game?: string | undefined;
  /** Team logo image */
  logo?: string | null | undefined;
  captain_username?: string | undefined;
  members_count?: string | undefined;
  /** Team is active and visible */
  is_active?: boolean | undefined;
  created_at?: string | undefined;
}

/**
 * Serializer for team updates (captain only).
 */
export interface TeamUpdate {
  /** Brief team description */
  description?: string | undefined;
  /** Team logo image */
  logo?: string | null | undefined;
  banner_image?: string | null | undefined;
  roster_image?: string | null | undefined;
  region?: string | undefined;
  twitter?: string | undefined;
  instagram?: string | undefined;
  discord?: string | undefined;
  youtube?: string | undefined;
  twitch?: string | undefined;
  linktree?: string | undefined;
}

/**
 * Serializer for team updates (captain only).
 */
export interface TeamUpdateRequest {
  /** Brief team description */
  description?: string | undefined;
  /** Team logo image */
  logo?: string | null | undefined;
  banner_image?: string | null | undefined;
  roster_image?: string | null | undefined;
  region?: string | undefined;
  twitter?: string | undefined;
  instagram?: string | undefined;
  discord?: string | undefined;
  youtube?: string | undefined;
  twitch?: string | undefined;
  linktree?: string | undefined;
}

export interface TokenObtainPair {
  access?: string | undefined;
  refresh?: string | undefined;
}

export interface TokenObtainPairRequest {
  username: string;
  password: string;
}

export interface TokenRefresh {
  access?: string | undefined;
  refresh: string;
}

export interface TokenRefreshRequest {
  refresh: string;
}

export interface TokenVerifyRequest {
  token: string;
}

/**
 * Serializer for cancelling tournaments.

Accepts optional reason field for audit trail.
 */
export interface TournamentCancel {
  reason?: string | undefined;
}

/**
 * Serializer for cancelling tournaments.

Accepts optional reason field for audit trail.
 */
export interface TournamentCancelRequest {
  reason?: string | undefined;
}

/**
 * Serializer for creating tournaments (DRAFT status).

Delegates to TournamentService.create_tournament() for business logic.
Validates input but does not create model directly.
 */
export interface TournamentCreate {
  name: string;
  game_id: number;
  format: FormatEnum;
  max_participants: number;
  registration_start: string;
  registration_end: string;
  tournament_start: string;
  description?: string | undefined;
  participation_type?: any | undefined;
  min_participants?: number | undefined;
  tournament_end?: string | null | undefined;
  prize_pool?: string | undefined;
  prize_currency?: string | undefined;
  prize_deltacoin?: number | undefined;
  prize_distribution?: any | undefined;
  has_entry_fee?: boolean | undefined;
  entry_fee_amount?: string | undefined;
  entry_fee_currency?: string | undefined;
  entry_fee_deltacoin?: number | undefined;
  payment_methods?: Array<PaymentMethodsEnum | undefined> | undefined;
  enable_fee_waiver?: boolean | undefined;
  fee_waiver_top_n_teams?: number | undefined;
  banner_image?: string | null | undefined;
  thumbnail_image?: string | null | undefined;
  rules_pdf?: string | null | undefined;
  promo_video_url?: string | undefined;
  stream_youtube_url?: string | undefined;
  stream_twitch_url?: string | undefined;
  enable_check_in?: boolean | undefined;
  check_in_minutes_before?: number | undefined;
  enable_dynamic_seeding?: boolean | undefined;
  enable_live_updates?: boolean | undefined;
  enable_certificates?: boolean | undefined;
  enable_challenges?: boolean | undefined;
  enable_fan_voting?: boolean | undefined;
  rules_text?: string | undefined;
  meta_description?: string | undefined;
  meta_keywords?: Array<string | undefined> | undefined;
  is_official?: boolean | undefined;
}

/**
 * Serializer for creating tournaments (DRAFT status).

Delegates to TournamentService.create_tournament() for business logic.
Validates input but does not create model directly.
 */
export interface TournamentCreateRequest {
  name: string;
  game_id: number;
  format: FormatEnum;
  max_participants: number;
  registration_start: string;
  registration_end: string;
  tournament_start: string;
  description?: string | undefined;
  participation_type?: any | undefined;
  min_participants?: number | undefined;
  tournament_end?: string | null | undefined;
  prize_pool?: string | undefined;
  prize_currency?: string | undefined;
  prize_deltacoin?: number | undefined;
  prize_distribution?: any | undefined;
  has_entry_fee?: boolean | undefined;
  entry_fee_amount?: string | undefined;
  entry_fee_currency?: string | undefined;
  entry_fee_deltacoin?: number | undefined;
  payment_methods?: Array<PaymentMethodsEnum | undefined> | undefined;
  enable_fee_waiver?: boolean | undefined;
  fee_waiver_top_n_teams?: number | undefined;
  banner_image?: string | null | undefined;
  thumbnail_image?: string | null | undefined;
  rules_pdf?: string | null | undefined;
  promo_video_url?: string | undefined;
  stream_youtube_url?: string | undefined;
  stream_twitch_url?: string | undefined;
  enable_check_in?: boolean | undefined;
  check_in_minutes_before?: number | undefined;
  enable_dynamic_seeding?: boolean | undefined;
  enable_live_updates?: boolean | undefined;
  enable_certificates?: boolean | undefined;
  enable_challenges?: boolean | undefined;
  enable_fan_voting?: boolean | undefined;
  rules_text?: string | undefined;
  meta_description?: string | undefined;
  meta_keywords?: Array<string | undefined> | undefined;
  is_official?: boolean | undefined;
}

/**
 * Comprehensive serializer for tournament detail views.

Returns all fields needed for tournament detail page.
Includes game details, organizer info, media URLs.
 */
export interface TournamentDetail {
  id?: number | undefined;
  slug?: string | undefined;
  /** Tournament name */
  name: string;
  /** Tournament description and overview */
  description: string;
  /** Current tournament status

* `draft` - Draft
* `pending_approval` - Pending Approval
* `published` - Published
* `registration_open` - Registration Open
* `registration_closed` - Registration Closed
* `live` - Live
* `completed` - Completed
* `cancelled` - Cancelled
* `archived` - Archived */
  status?: any | undefined;
  /** Whether this is an official DeltaCrown tournament */
  is_official?: boolean | undefined;
  game?: any | undefined;
  organizer_id?: number | undefined;
  organizer_username?: string | undefined;
  /** Bracket format for the tournament

* `single_elimination` - Single Elimination
* `double_elimination` - Double Elimination
* `round_robin` - Round Robin
* `swiss` - Swiss
* `group_playoff` - Group Stage + Playoff */
  format?: any | undefined;
  /** Whether teams or individuals participate

* `team` - Team
* `solo` - Solo/Individual */
  participation_type?: any | undefined;
  /** Maximum number of participants/teams */
  max_participants: number;
  /** Minimum participants needed to start */
  min_participants?: number | undefined;
  participant_count?: string | undefined;
  /** When registration opens */
  registration_start: string;
  /** When registration closes */
  registration_end: string;
  /** When tournament begins */
  tournament_start: string;
  /** When tournament ends (set automatically) */
  tournament_end?: string | null | undefined;
  /** When tournament was published */
  published_at?: string | null | undefined;
  /** Timestamp when this record was created */
  created_at?: string | undefined;
  /** Timestamp when this record was last updated */
  updated_at?: string | undefined;
  /** Total prize pool amount */
  prize_pool?: string | undefined;
  /** Currency for prize pool (BDT, USD, etc.) */
  prize_currency?: string | undefined;
  /** Prize pool in DeltaCoins */
  prize_deltacoin?: number | undefined;
  /** Prize distribution by placement (JSONB): {"1": "50%", "2": "30%", "3": "20%"} */
  prize_distribution?: any | undefined;
  /** Whether tournament has an entry fee */
  has_entry_fee?: boolean | undefined;
  /** Entry fee amount */
  entry_fee_amount?: string | undefined;
  /** Currency for entry fee */
  entry_fee_currency?: string | undefined;
  /** Entry fee in DeltaCoins */
  entry_fee_deltacoin?: number | undefined;
  /** Accepted payment methods */
  payment_methods?: Array<PaymentMethodsEnum | undefined> | undefined;
  /** Enable automatic fee waiver for top teams */
  enable_fee_waiver?: boolean | undefined;
  /** Number of top teams eligible for fee waiver */
  fee_waiver_top_n_teams?: number | undefined;
  /** Tournament banner image */
  banner_image?: string | null | undefined;
  /** Tournament thumbnail for listings */
  thumbnail_image?: string | null | undefined;
  /** Tournament rules PDF file */
  rules_pdf?: string | null | undefined;
  /** YouTube/Vimeo promo video URL */
  promo_video_url?: string | undefined;
  /** Official YouTube stream URL */
  stream_youtube_url?: string | undefined;
  /** Official Twitch stream URL */
  stream_twitch_url?: string | undefined;
  /** Require participants to check in before matches */
  enable_check_in?: boolean | undefined;
  /** Check-in window duration in minutes */
  check_in_minutes_before?: number | undefined;
  /** Use team rankings for seeding instead of registration order */
  enable_dynamic_seeding?: boolean | undefined;
  /** Enable WebSocket live updates for spectators */
  enable_live_updates?: boolean | undefined;
  /** Generate certificates for winners */
  enable_certificates?: boolean | undefined;
  /** Enable bonus challenges during tournament */
  enable_challenges?: boolean | undefined;
  /** Enable spectator voting/predictions */
  enable_fan_voting?: boolean | undefined;
  /** Tournament rules in text format */
  rules_text?: string | undefined;
  /** Meta description for SEO */
  meta_description?: string | undefined;
  /** SEO keywords */
  meta_keywords?: Array<string | undefined> | undefined;
  can_register?: string | undefined;
}

/**
 * Lightweight serializer for tournament list views.

Returns minimal fields for list endpoints with pagination.
Frontend can fetch full details via detail endpoint.

Module 2.4: Enhanced with ID fields for IDs-only discipline.
 */
export interface TournamentList {
  id?: number | undefined;
  slug: string;
  /** Tournament name */
  name: string;
  game_id?: number | undefined;
  game_name?: string | undefined;
  organizer_id?: number | undefined;
  organizer_username?: string | undefined;
  /** Current tournament status

* `draft` - Draft
* `pending_approval` - Pending Approval
* `published` - Published
* `registration_open` - Registration Open
* `registration_closed` - Registration Closed
* `live` - Live
* `completed` - Completed
* `cancelled` - Cancelled
* `archived` - Archived */
  status?: any | undefined;
  /** Bracket format for the tournament

* `single_elimination` - Single Elimination
* `double_elimination` - Double Elimination
* `round_robin` - Round Robin
* `swiss` - Swiss
* `group_playoff` - Group Stage + Playoff */
  format?: any | undefined;
  /** Whether teams or individuals participate

* `team` - Team
* `solo` - Solo/Individual */
  participation_type?: any | undefined;
  /** Maximum number of participants/teams */
  max_participants: number;
  participant_count?: string | undefined;
  /** When registration opens */
  registration_start: string;
  /** When registration closes */
  registration_end: string;
  /** When tournament begins */
  tournament_start: string;
  /** Total prize pool amount */
  prize_pool?: string | undefined;
  /** Currency for prize pool (BDT, USD, etc.) */
  prize_currency?: string | undefined;
  /** Whether tournament has an entry fee */
  has_entry_fee?: boolean | undefined;
  /** Entry fee amount */
  entry_fee_amount?: string | undefined;
  /** Tournament thumbnail for listings */
  thumbnail_image?: string | null | undefined;
  /** Whether this is an official DeltaCrown tournament */
  is_official?: boolean | undefined;
  /** Timestamp when this record was created */
  created_at?: string | undefined;
}

/**
 * Serializer for tournament staff assignment information.

Reference: Phase 7, Epic 7.3 - Staff Assignment API
 */
export interface TournamentStaffAssignment {
  assignment_id?: number | undefined;
  tournament_id?: number | undefined;
  tournament_name?: string | undefined;
  user_id?: number | undefined;
  username?: string | undefined;
  user_email?: string | undefined;
  role?: any | undefined;
  is_active?: boolean | undefined;
  stage_id?: number | null | undefined;
  stage_name?: string | null | undefined;
  assigned_by_user_id?: number | null | undefined;
  assigned_by_username?: string | null | undefined;
  assigned_at?: string | undefined;
  notes?: string | undefined;
}

/**
 * Serializer for updating tournaments (DRAFT status only).

All fields are optional for partial updates.
Delegates to TournamentService.update_tournament().
 */
export interface TournamentUpdate {
  name?: string | undefined;
  description?: string | undefined;
  format?: FormatEnum | undefined;
  participation_type?: ParticipationTypeEnum | undefined;
  max_participants?: number | undefined;
  min_participants?: number | undefined;
  registration_start?: string | undefined;
  registration_end?: string | undefined;
  tournament_start?: string | undefined;
  tournament_end?: string | null | undefined;
  prize_pool?: string | undefined;
  prize_currency?: string | undefined;
  prize_deltacoin?: number | undefined;
  prize_distribution?: any | undefined;
  has_entry_fee?: boolean | undefined;
  entry_fee_amount?: string | undefined;
  entry_fee_currency?: string | undefined;
  entry_fee_deltacoin?: number | undefined;
  payment_methods?: Array<PaymentMethodsEnum | undefined> | undefined;
  enable_fee_waiver?: boolean | undefined;
  fee_waiver_top_n_teams?: number | undefined;
  banner_image?: string | null | undefined;
  thumbnail_image?: string | null | undefined;
  rules_pdf?: string | null | undefined;
  promo_video_url?: string | undefined;
  stream_youtube_url?: string | undefined;
  stream_twitch_url?: string | undefined;
  enable_check_in?: boolean | undefined;
  check_in_minutes_before?: number | undefined;
  enable_dynamic_seeding?: boolean | undefined;
  enable_live_updates?: boolean | undefined;
  enable_certificates?: boolean | undefined;
  enable_challenges?: boolean | undefined;
  enable_fan_voting?: boolean | undefined;
  rules_text?: string | undefined;
  meta_description?: string | undefined;
  meta_keywords?: Array<string | undefined> | undefined;
  game_id?: number | undefined;
}

/**
 * Serializer for updating tournaments (DRAFT status only).

All fields are optional for partial updates.
Delegates to TournamentService.update_tournament().
 */
export interface TournamentUpdateRequest {
  name?: string | undefined;
  description?: string | undefined;
  format?: FormatEnum | undefined;
  participation_type?: ParticipationTypeEnum | undefined;
  max_participants?: number | undefined;
  min_participants?: number | undefined;
  registration_start?: string | undefined;
  registration_end?: string | undefined;
  tournament_start?: string | undefined;
  tournament_end?: string | null | undefined;
  prize_pool?: string | undefined;
  prize_currency?: string | undefined;
  prize_deltacoin?: number | undefined;
  prize_distribution?: any | undefined;
  has_entry_fee?: boolean | undefined;
  entry_fee_amount?: string | undefined;
  entry_fee_currency?: string | undefined;
  entry_fee_deltacoin?: number | undefined;
  payment_methods?: Array<PaymentMethodsEnum | undefined> | undefined;
  enable_fee_waiver?: boolean | undefined;
  fee_waiver_top_n_teams?: number | undefined;
  banner_image?: string | null | undefined;
  thumbnail_image?: string | null | undefined;
  rules_pdf?: string | null | undefined;
  promo_video_url?: string | undefined;
  stream_youtube_url?: string | undefined;
  stream_twitch_url?: string | undefined;
  enable_check_in?: boolean | undefined;
  check_in_minutes_before?: number | undefined;
  enable_dynamic_seeding?: boolean | undefined;
  enable_live_updates?: boolean | undefined;
  enable_certificates?: boolean | undefined;
  enable_challenges?: boolean | undefined;
  enable_fan_voting?: boolean | undefined;
  rules_text?: string | undefined;
  meta_description?: string | undefined;
  meta_keywords?: Array<string | undefined> | undefined;
  game_id?: number | undefined;
}

/**
 * Serializer for POST /api/teams/{id}/transfer-captain/.
 */
export interface TransferCaptain {
  new_captain_membership_id: number;
}

/**
 * Serializer for POST /api/teams/{id}/transfer-captain/.
 */
export interface TransferCaptainRequest {
  new_captain_membership_id: number;
}

/**
 * Serializer for undo check-in request
 */
export interface UndoCheckinRequest {
  /** Optional reason for undoing check-in */
  reason?: string | undefined;
  /** Flag indicating organizer override (set automatically) */
  organizer_override?: boolean | undefined;
}

/**
 * Serializer for undo check-in request
 */
export interface UndoCheckinRequestRequest {
  /** Optional reason for undoing check-in */
  reason?: string | undefined;
  /** Flag indicating organizer override (set automatically) */
  organizer_override?: boolean | undefined;
}

/**
 * Serializer for user analytics snapshots.
 */
export interface UserAnalytics {
  user_id: number;
  game_slug: string;
  mmr_snapshot: number;
  elo_snapshot: number;
  win_rate: string;
  kda_ratio: string;
  matches_last_7d: number;
  matches_last_30d: number;
  win_rate_7d: string;
  win_rate_30d: string;
  current_streak: number;
  longest_win_streak: number;
  tier: TierEnum;
  percentile_rank: string;
  recalculated_at: string;
}

/**
 * Nested serializer for user profile info in team responses.
 */
export interface UserProfileNested {
  id?: number | undefined;
  username?: string | undefined;
  email?: string | undefined;
  avatar?: string | null | undefined;
}
