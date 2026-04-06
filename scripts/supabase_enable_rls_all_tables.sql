-- =============================================================================
-- SUPABASE SECURITY FIX: Enable Row Level Security on all public tables
-- =============================================================================
-- WHAT THIS FIXES:
--   - rls_disabled_in_public  (ERROR: table publicly accessible via PostgREST)
--   - sensitive_columns_exposed (ERROR: passwords/tokens readable via REST API)
--
-- WHY THIS IS SAFE FOR DJANGO:
--   Django connects via the Transaction Pooler (Port 6543) as the `postgres`
--   superuser. PostgreSQL superusers bypass RLS entirely unless they explicitly
--   SET ROLE to a restricted user. Django never does this. Your ORM queries,
--   migrations, and Celery tasks are completely unaffected.
--
--   RLS only restricts access via Supabase's PostgREST REST API (the `anon`
--   and `authenticated` roles). DeltaCrown doesn't use PostgREST — Django
--   handles all data access — so blocking it costs you nothing.
--
-- HOW TO RUN:
--   1. Go to Supabase Dashboard → SQL Editor
--   2. Paste this entire file and click "Run"
--   3. Check the output for "Enabled RLS on public.<table>" messages
--   4. Supabase Security Advisor warnings will clear within a few minutes
-- =============================================================================

DO $$
DECLARE
    tbl text;
    tbl_count integer := 0;
BEGIN
    FOR tbl IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename
    LOOP
        EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', tbl);
        RAISE NOTICE 'Enabled RLS on public.%', tbl;
        tbl_count := tbl_count + 1;
    END LOOP;

    RAISE NOTICE '========================================';
    RAISE NOTICE 'Done. Enabled RLS on % tables.', tbl_count;
    RAISE NOTICE 'Django (postgres superuser) is unaffected.';
    RAISE NOTICE 'Supabase PostgREST API access is now blocked.';
    RAISE NOTICE '========================================';
END;
$$;
