/**
 * Type Safety Tests
 *
 * Validates TypeScript compilation and type inference for DeltaCrown SDK.
 * Run with: pnpm run type-check
 */

import {
  DeltaCrownClient,
  createClient,
  ApiError,
  type TournamentStatus,
  type RegistrationForm,
  type PaginatedResponse,
  type TournamentSummary,
} from '../src/index';

// ========================================================================
// CLIENT INSTANTIATION
// ========================================================================

// Should compile: basic client creation
const client1 = new DeltaCrownClient();

// Should compile: client with config
const client2 = new DeltaCrownClient({
  baseUrl: 'https://api.deltacrown.gg',
  accessToken: 'eyJ0eXAi...',
  onUnauthorized: () => console.log('Unauthorized'),
  onError: (error) => console.error(error.message),
});

// Should compile: factory function
const client3 = createClient({ baseUrl: 'http://localhost:8000' });

// ========================================================================
// AUTHENTICATION
// ========================================================================

async function testAuth() {
  const client = new DeltaCrownClient();
  
  // Should compile: obtain token
  const tokens = await client.obtainToken('username', 'password');
  const accessToken: string = tokens.access;
  const refreshToken: string = tokens.refresh;
  
  // Should compile: set token
  client.setAccessToken(accessToken);
  
  // Should compile: refresh token
  const newTokens = await client.refreshToken(refreshToken);
  const newAccess: string = newTokens.access;
}

// ========================================================================
// REGISTRATION
// ========================================================================

async function testRegistration() {
  const client = new DeltaCrownClient();
  
  // Should compile: registration form
  const form: RegistrationForm = {
    tournament_id: 1,
    participant_type: 'user',
    participant_id: 42,
    game_identity_fields: {
      summoner_name: 'TheLegend27',
      region: 'NA',
    },
    agreed_to_rules: true,
  };
  
  // Should compile: register
  const registration = await client.register(1, form);
  const regId: number = registration.id;
  const canCancel: boolean = registration.can_cancel;
  
  // Should compile: get registrations
  const registrations = await client.getRegistrations(1);
  const count: number = registrations.count;
  const results = registrations.results;
}

// ========================================================================
// TOURNAMENTS
// ========================================================================

async function testTournaments() {
  const client = new DeltaCrownClient();
  
  // Should compile: get tournaments with filters
  const tournaments = await client.getTournaments({
    game_slug: 'league-of-legends',
    status: 'registration_open',
    format: 'single_elimination',
    page: 1,
  });
  
  // Should compile: typed response
  const response: PaginatedResponse<TournamentSummary> = tournaments;
  const firstTournament = tournaments.results[0];
  if (firstTournament) {
    const name: string = firstTournament.name;
    const entryFee: number | null = firstTournament.entry_fee;
    const canRegister: boolean = firstTournament.can_register;
  }
  
  // Should compile: get single tournament
  const tournament = await client.getTournament(1);
  const stages = tournament.stages;
  const description: string | null = tournament.description;
}

// ========================================================================
// MATCHES & RESULTS
// ========================================================================

async function testMatches() {
  const client = new DeltaCrownClient();
  
  // Should compile: submit result
  await client.submitResult(123, {
    match_id: 123,
    winner_type: 'user',
    winner_id: 42,
    score: '2-1',
    result_data: {
      game_1_screenshot: 'https://...',
    },
  });
  
  // Should compile: confirm result
  await client.confirmResult(123);
  
  // Should compile: get match
  const match = await client.getMatch(123);
  const status = match.status;
  const winnerId = match.winner_id;
}

// ========================================================================
// ORGANIZER - RESULTS INBOX
// ========================================================================

async function testOrganizerInbox() {
  const client = new DeltaCrownClient();
  
  // Should compile: get inbox
  const inbox = await client.getOrganizerResultsInbox({
    tournament_id: 1,
    status: 'awaiting_review',
    page: 1,
  });
  
  const items = inbox.results;
  if (items[0]) {
    const priority = items[0].priority;
    const ageHours = items[0].age_in_hours;
  }
  
  // Should compile: bulk action
  const result = await client.bulkActionResultsInbox({
    submission_ids: [1, 2, 3],
    action: 'finalize',
  });
  
  const successCount: number = result.success_count;
  const failedCount: number = result.failed_count;
}

// ========================================================================
// STATS & LEADERBOARDS
// ========================================================================

async function testStatsAndLeaderboards() {
  const client = new DeltaCrownClient();
  
  // Should compile: user stats
  const userStats = await client.getUserStats(42, 'league-of-legends');
  const winRate: number = userStats.win_rate;
  const elo: number | null = userStats.elo;
  
  // Should compile: team stats
  const teamStats = await client.getTeamStats(10);
  const tier = teamStats.tier;
  const synergy: number = teamStats.synergy_score;
  
  // Should compile: leaderboard
  const leaderboard = await client.getLeaderboard('global_user', {
    game_slug: 'valorant',
    limit: 100,
  });
  
  const entries = leaderboard.entries;
  if (entries[0]) {
    const rank: number = entries[0].rank;
    const score: number = entries[0].score;
  }
}

// ========================================================================
// ERROR HANDLING
// ========================================================================

async function testErrorHandling() {
  const client = new DeltaCrownClient({
    onError: (error) => {
      const message: string = error.message;
      const statusCode: number = error.statusCode;
      const details = error.details;
    },
  });
  
  try {
    await client.getTournament(999999);
  } catch (error) {
    if (error instanceof ApiError) {
      console.error(`Error ${error.statusCode}: ${error.message}`);
    }
  }
}

// ========================================================================
// TYPE NARROWING
// ========================================================================

function testTypeNarrowing() {
  const status: TournamentStatus = 'registration_open';
  
  // Should compile: all valid statuses
  const validStatuses: TournamentStatus[] = [
    'draft',
    'published',
    'registration_open',
    'registration_closed',
    'check_in_open',
    'in_progress',
    'completed',
    'cancelled',
  ];
  
  // @ts-expect-error - invalid status should not compile
  const invalid: TournamentStatus = 'not_a_status';
}

console.log('✅ All type checks passed!');
