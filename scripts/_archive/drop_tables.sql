-- Drop all tournament tables
DROP TABLE IF EXISTS tournaments_game CASCADE;
DROP TABLE IF EXISTS tournaments_tournament CASCADE;
DROP TABLE IF EXISTS tournaments_customfield CASCADE;
DROP TABLE IF EXISTS tournaments_tournamentversion CASCADE;
DROP TABLE IF EXISTS tournaments_registration CASCADE;
DROP TABLE IF EXISTS tournaments_payment CASCADE;
DROP TABLE IF EXISTS tournament_engine_bracket_bracket CASCADE;
DROP TABLE IF EXISTS tournament_engine_bracket_bracketnode CASCADE;
DROP TABLE IF EXISTS tournament_engine_match_match CASCADE;
DROP TABLE IF EXISTS tournament_engine_match_dispute CASCADE;
DROP TABLE IF EXISTS tournament_engine_game_game CASCADE;
DROP TABLE IF EXISTS tournament_engine_tournament_tournament CASCADE;
DROP TABLE IF EXISTS tournament_engine_tournament_customfield CASCADE;
DROP TABLE IF EXISTS tournament_engine_tournament_tournamentversion CASCADE;
DROP TABLE IF EXISTS tournament_engine_registration_registration CASCADE;
DROP TABLE IF EXISTS tournament_engine_registration_payment CASCADE;

-- Drop all tournament indexes
DROP INDEX IF EXISTS idx_match_tournament;
DROP INDEX IF EXISTS idx_match_bracket;
DROP INDEX IF EXISTS idx_match_round;
DROP INDEX IF EXISTS idx_match_state;
DROP INDEX IF EXISTS idx_match_scheduled;
DROP INDEX IF EXISTS idx_match_participants;
DROP INDEX IF EXISTS idx_match_winner;
DROP INDEX IF EXISTS idx_match_check_in;
DROP INDEX IF EXISTS idx_match_live;
DROP INDEX IF EXISTS idx_match_lobby_gin;
DROP INDEX IF EXISTS idx_bracket_tournament;
DROP INDEX IF EXISTS idx_bracket_format;
DROP INDEX IF EXISTS idx_bracket_structure_gin;
DROP INDEX IF EXISTS idx_bracketnode_bracket;
DROP INDEX IF EXISTS idx_bracketnode_round;
DROP INDEX IF EXISTS idx_bracketnode_position;
DROP INDEX IF EXISTS idx_bracketnode_match;
DROP INDEX IF EXISTS idx_bracketnode_parent;
DROP INDEX IF EXISTS idx_bracketnode_children;
DROP INDEX IF EXISTS idx_bracketnode_participants;

