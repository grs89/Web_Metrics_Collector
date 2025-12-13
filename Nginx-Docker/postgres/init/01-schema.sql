-- ═══════════════════════════════════════════════════════════════════════════
-- NGP - Nginx Geo Profiler - Database Schema
-- ═══════════════════════════════════════════════════════════════════════════

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ═══════════════════════════════════════════════════════════════════════════
-- Main access logs table with partitioning support
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE nginx_access_logs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    -- Request info
    remote_addr     INET NOT NULL,
    remote_user     VARCHAR(255),
    request_method  VARCHAR(10),
    request_uri     TEXT,
    request         TEXT,
    status          SMALLINT NOT NULL,
    body_bytes_sent BIGINT DEFAULT 0,
    request_time    DECIMAL(10, 6),
    request_length  INTEGER,
    
    -- Headers
    http_referer    TEXT,
    http_user_agent TEXT,
    http_x_forwarded_for TEXT,
    
    -- Server info
    host            VARCHAR(255),
    server_name     VARCHAR(255),
    upstream_addr   VARCHAR(255),
    upstream_response_time VARCHAR(50),
    
    -- SSL info
    ssl_protocol    VARCHAR(20),
    ssl_cipher      VARCHAR(100),
    
    -- Connection info
    connection      BIGINT,
    connection_requests INTEGER,
    gzip_ratio      VARCHAR(20),
    
    -- GeoIP enrichment
    country_code    CHAR(2),
    country_name    VARCHAR(100),
    city            VARCHAR(255),
    region          VARCHAR(255),
    latitude        DECIMAL(9, 6),
    longitude       DECIMAL(9, 6),
    timezone        VARCHAR(50),
    isp             VARCHAR(255),
    asn             INTEGER,
    as_org          VARCHAR(255),
    
    -- Metadata
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════════════════
-- Indexes for common queries
-- ═══════════════════════════════════════════════════════════════════════════

-- Time-based queries (most common)
CREATE INDEX idx_logs_timestamp ON nginx_access_logs (timestamp DESC);
CREATE INDEX idx_logs_timestamp_date ON nginx_access_logs ((timestamp::DATE));

-- IP-based queries
CREATE INDEX idx_logs_remote_addr ON nginx_access_logs (remote_addr);

-- Status code queries
CREATE INDEX idx_logs_status ON nginx_access_logs (status);

-- Geographic queries
CREATE INDEX idx_logs_country ON nginx_access_logs (country_code);
CREATE INDEX idx_logs_geo ON nginx_access_logs (latitude, longitude) WHERE latitude IS NOT NULL;

-- URI queries
CREATE INDEX idx_logs_uri ON nginx_access_logs USING gin (request_uri gin_trgm_ops);

-- Composite indexes for dashboard queries
CREATE INDEX idx_logs_timestamp_status ON nginx_access_logs (timestamp DESC, status);
CREATE INDEX idx_logs_timestamp_country ON nginx_access_logs (timestamp DESC, country_code);

-- ═══════════════════════════════════════════════════════════════════════════
-- Aggregated metrics table (for faster dashboard queries)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE nginx_metrics_hourly (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hour            TIMESTAMPTZ NOT NULL,
    
    -- Request counts
    total_requests  BIGINT DEFAULT 0,
    requests_2xx    BIGINT DEFAULT 0,
    requests_3xx    BIGINT DEFAULT 0,
    requests_4xx    BIGINT DEFAULT 0,
    requests_5xx    BIGINT DEFAULT 0,
    
    -- Performance metrics
    avg_response_time DECIMAL(10, 6),
    max_response_time DECIMAL(10, 6),
    min_response_time DECIMAL(10, 6),
    p95_response_time DECIMAL(10, 6),
    p99_response_time DECIMAL(10, 6),
    
    -- Bandwidth
    total_bytes_sent BIGINT DEFAULT 0,
    
    -- Unique counts
    unique_ips      INTEGER DEFAULT 0,
    unique_countries INTEGER DEFAULT 0,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(hour)
);

CREATE INDEX idx_metrics_hour ON nginx_metrics_hourly (hour DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- Country statistics table
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE nginx_country_stats (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date            DATE NOT NULL,
    country_code    CHAR(2) NOT NULL,
    country_name    VARCHAR(100),
    
    request_count   BIGINT DEFAULT 0,
    unique_ips      INTEGER DEFAULT 0,
    total_bytes     BIGINT DEFAULT 0,
    avg_response_time DECIMAL(10, 6),
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(date, country_code)
);

CREATE INDEX idx_country_stats_date ON nginx_country_stats (date DESC);
CREATE INDEX idx_country_stats_country ON nginx_country_stats (country_code);

-- ═══════════════════════════════════════════════════════════════════════════
-- Top URIs table (for endpoint analysis)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE TABLE nginx_uri_stats (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    date            DATE NOT NULL,
    request_uri     TEXT NOT NULL,
    
    request_count   BIGINT DEFAULT 0,
    total_bytes     BIGINT DEFAULT 0,
    avg_response_time DECIMAL(10, 6),
    error_count     BIGINT DEFAULT 0,
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(date, request_uri)
);

CREATE INDEX idx_uri_stats_date ON nginx_uri_stats (date DESC);

-- ═══════════════════════════════════════════════════════════════════════════
-- Views for Grafana
-- ═══════════════════════════════════════════════════════════════════════════

-- Real-time requests per second (last 5 minutes)
CREATE VIEW v_requests_per_second AS
SELECT 
    date_trunc('second', timestamp) AS time,
    COUNT(*) AS requests
FROM nginx_access_logs
WHERE timestamp > NOW() - INTERVAL '5 minutes'
GROUP BY date_trunc('second', timestamp)
ORDER BY time DESC;

-- Status code distribution
CREATE VIEW v_status_distribution AS
SELECT 
    CASE 
        WHEN status BETWEEN 200 AND 299 THEN '2xx Success'
        WHEN status BETWEEN 300 AND 399 THEN '3xx Redirect'
        WHEN status BETWEEN 400 AND 499 THEN '4xx Client Error'
        WHEN status BETWEEN 500 AND 599 THEN '5xx Server Error'
        ELSE 'Other'
    END AS status_group,
    status,
    COUNT(*) AS count
FROM nginx_access_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY status
ORDER BY count DESC;

-- Geographic distribution for world map
CREATE VIEW v_geo_distribution AS
SELECT 
    country_code,
    country_name,
    latitude,
    longitude,
    COUNT(*) AS request_count,
    COUNT(DISTINCT remote_addr) AS unique_visitors
FROM nginx_access_logs
WHERE 
    timestamp > NOW() - INTERVAL '24 hours'
    AND latitude IS NOT NULL
GROUP BY country_code, country_name, latitude, longitude
ORDER BY request_count DESC;

-- Top IPs
CREATE VIEW v_top_ips AS
SELECT 
    remote_addr,
    country_code,
    country_name,
    city,
    COUNT(*) AS request_count,
    SUM(body_bytes_sent) AS total_bytes,
    AVG(request_time) AS avg_response_time
FROM nginx_access_logs
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY remote_addr, country_code, country_name, city
ORDER BY request_count DESC
LIMIT 100;

-- ═══════════════════════════════════════════════════════════════════════════
-- Function to cleanup old data (retention policy)
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION cleanup_old_logs(retention_days INTEGER DEFAULT 365)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM nginx_access_logs 
    WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    DELETE FROM nginx_metrics_hourly 
    WHERE hour < NOW() - (retention_days || ' days')::INTERVAL;
    
    DELETE FROM nginx_country_stats 
    WHERE date < NOW() - (retention_days || ' days')::INTERVAL;
    
    DELETE FROM nginx_uri_stats 
    WHERE date < NOW() - (retention_days || ' days')::INTERVAL;
    
    -- Vacuum analyze to reclaim space
    -- Note: This is commented out because it requires elevated privileges
    -- VACUUM ANALYZE nginx_access_logs;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ═══════════════════════════════════════════════════════════════════════════
-- Function to aggregate hourly metrics
-- ═══════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION aggregate_hourly_metrics(target_hour TIMESTAMPTZ)
RETURNS VOID AS $$
BEGIN
    INSERT INTO nginx_metrics_hourly (
        hour, total_requests, requests_2xx, requests_3xx, requests_4xx, requests_5xx,
        avg_response_time, max_response_time, min_response_time,
        total_bytes_sent, unique_ips, unique_countries
    )
    SELECT 
        date_trunc('hour', target_hour) AS hour,
        COUNT(*) AS total_requests,
        COUNT(*) FILTER (WHERE status BETWEEN 200 AND 299) AS requests_2xx,
        COUNT(*) FILTER (WHERE status BETWEEN 300 AND 399) AS requests_3xx,
        COUNT(*) FILTER (WHERE status BETWEEN 400 AND 499) AS requests_4xx,
        COUNT(*) FILTER (WHERE status BETWEEN 500 AND 599) AS requests_5xx,
        AVG(request_time) AS avg_response_time,
        MAX(request_time) AS max_response_time,
        MIN(request_time) AS min_response_time,
        SUM(body_bytes_sent) AS total_bytes_sent,
        COUNT(DISTINCT remote_addr) AS unique_ips,
        COUNT(DISTINCT country_code) AS unique_countries
    FROM nginx_access_logs
    WHERE timestamp >= date_trunc('hour', target_hour)
      AND timestamp < date_trunc('hour', target_hour) + INTERVAL '1 hour'
    ON CONFLICT (hour) DO UPDATE SET
        total_requests = EXCLUDED.total_requests,
        requests_2xx = EXCLUDED.requests_2xx,
        requests_3xx = EXCLUDED.requests_3xx,
        requests_4xx = EXCLUDED.requests_4xx,
        requests_5xx = EXCLUDED.requests_5xx,
        avg_response_time = EXCLUDED.avg_response_time,
        max_response_time = EXCLUDED.max_response_time,
        min_response_time = EXCLUDED.min_response_time,
        total_bytes_sent = EXCLUDED.total_bytes_sent,
        unique_ips = EXCLUDED.unique_ips,
        unique_countries = EXCLUDED.unique_countries;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO PUBLIC;
GRANT USAGE ON SCHEMA public TO PUBLIC;

