-- Drop incomplete form builder tables
DROP TABLE IF EXISTS tournaments_form_response CASCADE;
DROP TABLE IF EXISTS tournaments_registration_form CASCADE;
DROP TABLE IF EXISTS tournaments_registration_form_template CASCADE;

-- Delete migration record so it can be re-run
DELETE FROM django_migrations WHERE app = 'tournaments' AND name = '0010_create_form_builder_models';
