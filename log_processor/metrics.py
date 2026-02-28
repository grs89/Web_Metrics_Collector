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

# Host System Metrics
HOST_CPU_USAGE = Gauge(
    "wmc_host_cpu_usage_percent",
    "CPU usage percentage on the monitored host",
    ["host"]
)

HOST_MEMORY_USAGE = Gauge(
    "wmc_host_memory_usage_percent",
    "Memory usage percentage on the monitored host",
    ["host"]
)

HOST_DISK_USAGE = Gauge(
    "wmc_host_disk_usage_percent",
    "Disk usage percentage on the monitored host",
    ["host", "mountpoint"]
)

HOST_LOAD_AVG = Gauge(
    "wmc_host_load_avg",
    "System load average (1 min) on the monitored host",
    ["host"]
)

# Anomaly Detection Metrics
TRAFFIC_ANOMALY_SCORE = Gauge(
    "wmc_traffic_anomaly_score",
    "Current anomaly Z-Score based on traffic volume compared to historical data",
    ["host"]
)

ANOMALIES_DETECTED_TOTAL = Counter(
    "wmc_anomalies_detected_total",
    "Total number of anomalies detected for a host",
    ["host"]
)
