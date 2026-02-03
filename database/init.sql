-- Enable PostGIS if we wanted to do advanced queries, but simple float lat/lon is fine for now
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS web_access_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL,
    source_host VARCHAR(255) NOT NULL,
    client_ip INET,
    hostname VARCHAR(255),
    method VARCHAR(10),
    uri TEXT,
    status_code SMALLINT,
    response_size INTEGER,
    user_agent TEXT,
    browser VARCHAR(100),
    os VARCHAR(100),
    device VARCHAR(100),
    is_fake_bot BOOLEAN DEFAULT FALSE,
    referrer TEXT,
    country_code CHAR(2),
    city VARCHAR(255),
    latitude FLOAT,
    longitude FLOAT,
    server_type VARCHAR(50), -- 'nginx', 'apache'
    raw_log TEXT,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for filtering by host and time range (Grafana usage)
CREATE INDEX idx_logs_timestamp_host ON web_access_logs (timestamp, source_host);
CREATE INDEX idx_logs_country ON web_access_logs (country_code);

-- View for Requests Per Minute
CREATE OR REPLACE VIEW view_requests_per_minute AS
SELECT
    date_trunc('minute', timestamp) as time_bucket,
    source_host,
    count(*) as request_count
FROM web_access_logs
GROUP BY 1, 2;

-- View for Status Codes
CREATE OR REPLACE VIEW view_status_codes_summary AS
SELECT
    source_host,
    status_code,
    count(*) as count
FROM web_access_logs
GROUP BY 1, 2;
