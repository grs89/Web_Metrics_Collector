-- ═══════════════════════════════════════════════════════════════════════════
-- NGP - Additional PostgreSQL Extensions
-- ═══════════════════════════════════════════════════════════════════════════

-- Text search extension for URI pattern matching
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Enable better statistics
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

