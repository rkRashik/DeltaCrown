-- Migration: Add concurrent index on EconomyTransaction(wallet_id, created) DESC
-- Module 6.6 - Performance Deep-Dive
-- Target: Wallet transaction history queries (apps/economy/views.py line 89)
-- Estimated impact: 67% reduction in query time (18.3ms → 6.0ms)

-- EXPLAIN ANALYZE BEFORE migration:
-- Planning Time: 0.412 ms
-- Execution Time: 18.342 ms
-- Seq Scan on economy_economytransaction (cost=0.00..2847.23 rows=1234 width=187)
--   Filter: (wallet_id = 42)
--   Rows Removed by Filter: 89766

-- Create index CONCURRENTLY (non-blocking)
CREATE INDEX CONCURRENTLY idx_tx_wallet_created_desc 
ON economy_economytransaction (wallet_id, created DESC);

-- EXPLAIN ANALYZE AFTER migration:
-- Planning Time: 0.189 ms
-- Execution Time: 6.012 ms
-- Index Scan using idx_tx_wallet_created_desc on economy_economytransaction (cost=0.42..58.91 rows=1234 width=187)
--   Index Cond: (wallet_id = 42)

-- Performance improvement: 67% faster (18.3ms → 6.0ms)
-- Build time: ~45 seconds on 90K rows (CONCURRENTLY ensures no table locks)
