# Management commands

Purpose: what each custom `manage.py` command is for, so you can find the right one without reading the code. Purposes come from each command's `help` text in `apps/<app>/management/commands/`. Run `python manage.py <command> --help` for options. Commands marked **dry run** change nothing unless `--apply` is passed. **Never run repair, reset or purge commands against production without explicit owner approval.**

## Setup and seed data

| Command | Purpose |
|---|---|
| `seed_games` | Seed the 11 supported games |
| `seed_game_passport_schemas` | Seed per-game in-game ID (passport) schemas |
| `seed_game_ranking_configs` | Seed ranking configuration for supported games |
| `seed_seasons` | Seed seasons S1-S3 and snapshot current rankings |
| `seed_form_templates` | System registration form templates |
| `init_default_games` | Initialise/update the canonical default games (legacy) |
| `create_achievement_types`, `create_starter_badges`, `create_privacy_settings` | Achievement definitions, starter badges, privacy settings for existing profiles |
| `populate_featured_faqs` | Sample FAQs for the homepage |
| `seed_full_tournament` | 100 users, 40 teams, 3 organizations, 15 tournaments (large sample set) |
| `seed_spring_showdown`, `seed_uradhura_ucl`, `seed_crown_arena` | Specific sample tournaments (16-team double elimination, 32-player group stage stress test, Crown Arena) |
| `import_rules_from_pdfs` | Import tournament rules text from PDFs |

## Scheduled and operational

| Command | Purpose |
|---|---|
| `process_account_deletions` | Process deletion requests whose scheduled date has passed |
| `send_checkin_reminders`, `send_digests`, `cleanup_notifications` | Check-in reminders, daily digests, delete old read notifications (default older than 90 days) |
| `expire_bounties` | Expire open bounties and refund creators |
| `refresh_analytics` | Refresh the tournament analytics materialized view |
| `run_vnext_rank_jobs`, `compute_initial_rankings`, `bootstrap_team_rankings`, `backfill_match_cp` | Rebuild or backfill team rankings |
| `recalc_all_wallets`, `reconcile_economy`, `verify_payment_consistency` | Wallet balance drift detection/fix; profile economy fields versus ledger; payment versus verification comparison |
| `recompute_user_stats` | Recompute tournament and team stats on profiles |
| `run_discord_bot` | Run the Discord bot (needs `ENABLE_DISCORD_BOT` and tokens) |
| `flush_cache`, `clear_template_cache` | Flush the default cache (Redis on production!) / clear the template cache |

## Backfills and migrations helpers

`backfill_game_profiles`, `backfill_public_ids`, `backfill_social_links`, `backfill_user_activities` (user_profile); `backfill_certificates_to_s3`, `backfill_knockout_bracket_fk` (tournaments); `reencrypt_oauth_tokens` and `resign_editor_image_urls` (count by status, `--apply` to rewrite); `export_media_references` (read-only export of confidential media references).

## Media

| Command | Purpose |
|---|---|
| `generate_image_derivatives` | Resized WebP derivatives for allowlisted public artwork (**dry run** unless `--apply`) |
| `publish_public_media` | Publish approved public artwork to the Cloudinary CDN (**dry run** unless `--apply`) |
| `audit_game_media`, `audit_cloudinary_orphans`, `clear_broken_game_images` | Audit game media files and Cloudinary orphans; clear broken image fields |
| `game_assets` | Manage game asset configuration and paths |

## Repair and diagnostics

| Command | Purpose |
|---|---|
| `repair_bracket_match_links`, `repair_bracket_names`, `repair_toc_capacity_overflow` | Link missing bracket/match foreign keys; fix names; revert suspicious reactivated registrations |
| `cleanup_ghost_teams` | Remove teams without proper memberships/events |
| `check_identity_configs`, `cleanup_passport_schema`, `mark_passport_supported`, `fix_efootball_schema` | Game passport and identity configuration |
| `update_catalog_metadata`, `update_football_metadata`, `update_fc27_artwork` | Catalog metadata and artwork (preview unless `--apply`) |
| `urls_audit` | Smoke-test that named URLs reverse and key templates render |
| `competition_check_schema` | Check that competition tables exist |
| `db_migration_reconcile` | Compare tables with migration history (**read-only** unless `--apply-fake`) |
| `verify_clean_migrate`, `diagnose_real_db`, `incident_assessment`, `debug_migrations`, `debug_hub_visibility`, `verify_org_templatetags`, `vnext_validation_report`, `riot_api_selftest` | Diagnostics and validation reports |
| `list_dead_letter_events`, `replay_event`, `replay_events` | Inspect/replay failed events from the event log |
| `audit_export`, `audit_verify_integrity` | Export audit events (JSONL); verify the audit log is append-only |
| `simulate_matches` | Generate simulated matches for the ranking pipeline |

## Dangerous (do not run casually)

`economy_genesis_reset` (**deletes all transaction history** and resets wallets), `purge_test_data` (deletes fake users/teams/tournaments), `ops_reset_neon_schema` (resets a database schema), `fake_organizations_migrations`, `reconcile_legacy_migrations`, `fix_migration_0010` (rewrite migration state). They exist for past incidents and local resets; treat them as tools for a disposable database only.
