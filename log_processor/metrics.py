from prometheus_client import Counter, Gauge, Histogram

# General ingestion metrics
LOGS_PROCESSED_TOTAL = Counter(
    "wmc_logs_processed_total", 
    "Total number of logs processed",
    ["source_host", "status"]
)

LOG_BATCHES_SAVED_TOTAL = Counter(
    "wmc_log_batches_saved_total",
    "Total number of log batches saved to database"
)

DB_SAVE_ERRORS_TOTAL = Counter(
    "wmc_db_save_errors_total",
    "Total number of database save errors"
)

SSH_CONNECTION_ATTEMPTS_TOTAL = Counter(
    "wmc_ssh_connection_attempts_total",
    "Total number of SSH connection attempts",
    ["host", "result"]
)

# Queue observability
LOG_BUFFER_SIZE = Gauge(
    "wmc_log_buffer_size",
    "Current number of logs in the internal memory buffer"
)

# Latency
INGESTION_LATENCY_SECONDS = Histogram(
    "wmc_ingestion_latency_seconds",
    "Time taken to process and enrich a log line"
)
