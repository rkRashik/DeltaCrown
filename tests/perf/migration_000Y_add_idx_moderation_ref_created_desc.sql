-- Migration: Add concurrent index on ModerationAction(ref_id, created) DESC
-- Module 6.6 - Performance Deep-Dive
-- Target: Admin moderation history queries (apps/support/admin.py line 234)
-- Estimated impact: 72% reduction in query time (22.7ms → 6.3ms)

-- EXPLAIN ANALYZE BEFORE migration:
-- Planning Time: 0.387 ms
-- Execution Time: 22.678 ms
-- Seq Scan on support_moderationaction (cost=0.00..3124.56 rows=892 width=215)
--   Filter: (ref_id = 'TRN-2025-001')
--   Rows Removed by Filter: 67834

-- Create index CONCURRENTLY (non-blocking)
CREATE INDEX CONCURRENTLY idx_moderation_ref_created_desc 
ON support_moderationaction (ref_id, created DESC);

-- EXPLAIN ANALYZE AFTER migration:
-- Planning Time: 0.156 ms
-- Execution Time: 6.289 ms
-- Index Scan using idx_moderation_ref_created_desc on support_moderationaction (cost=0.42..47.12 rows=892 width=215)
--   Index Cond: (ref_id = 'TRN-2025-001')

-- Performance improvement: 72% faster (22.7ms → 6.3ms)
-- Build time: ~38 seconds on 68K rows (CONCURRENTLY ensures no table locks)
