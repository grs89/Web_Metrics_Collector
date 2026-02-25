CREATE TABLE IF NOT EXISTS web_access_logs (
    id UUID DEFAULT generateUUIDv4(),
    timestamp DateTime64(3),
    source_host LowCardinality(String),
    client_ip IPv4,
    hostname String,
    method LowCardinality(String),
    uri String,
    status_code UInt16,
    response_size UInt32,
    request_time_ms Float64,
    country_code LowCardinality(String),
    city String,
    latitude Float64,
    longitude Float64,
    user_agent String,
    browser LowCardinality(String),
    os LowCardinality(String),
    device LowCardinality(String),
    bot_category LowCardinality(String),
    is_fake_bot UInt8,
    referrer String,
    server_type LowCardinality(String),
    raw_log String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, source_host, status_code);
