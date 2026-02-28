import asyncio
import time
import logging
import signal
import sys
import json
from config import load_config, get_db_params, get_ch_params
from geoip import GeoIPEnricher
from ua_enricher import UAEnricher
from dns_enricher import DNSEnricher
from processor import LogProcessor
from storage import PostgresStorage, ClickHouseStorage, MultiStorage
from ssh_client import SSHLogReader
from system_metrics import SystemMetricsCollector
from ssl_monitor import SSLMonitor
from state import StateManager
from anomaly_detector import AnomalyDetector
from prometheus_client import start_http_server

# Initialize Metrics Server early
# This allows healthchecks to pass as soon as the process starts
METRICS_PORT = 8080
start_http_server(METRICS_PORT)
logging.info(f"Prometheus metrics server started on port {METRICS_PORT}")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

# Setup Structured Logging
handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.handlers = [handler]

async def main():
    config = load_config()
    db_params = get_db_params()
    ch_params = get_ch_params()
    
    # Initialize shared components
    geoip = GeoIPEnricher()
    ua_enricher = UAEnricher()
    dns_enricher = DNSEnricher()
    
    # Initialize Storage Backends
    pg_storage = PostgresStorage(db_params)
    ch_storage = ClickHouseStorage(ch_params)
    storage = MultiStorage(pg_storage, ch_storage)
    
    # Initialize State Manager
    state_manager = StateManager(state_file="/app/data/state.json")
    saved_offsets = state_manager.load()
    
    # Initialize Anomaly Detector
    anomaly_detector = AnomalyDetector(storage)
    
    if not await storage.connect():
        logging.error("Critical: Could not connect to primary database. Exiting.")
        return

    # Initialize Processor
    processor = LogProcessor(geoip, ua_enricher, dns_enricher, storage)
    processor.start() # Start the background pusher worker
    
    hosts = config.get('hosts', [])
    # Initialize SSH Readers for each host with saved offsets
    readers = {h['name']: SSHLogReader(h, saved_offsets.get(h['name'])) for h in hosts}
    
    logging.info(f"Initialized monitoring for {len(hosts)} hosts using asyncio.")

    running = True
    def signal_handler(sig, frame):
        nonlocal running
        logging.info("Shutting down...")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start background tasks
    metrics_task = asyncio.create_task(run_system_metrics_task(hosts, readers))
    ssl_task = asyncio.create_task(run_ssl_monitor_task(hosts))
    state_task = asyncio.create_task(run_state_persistence_task(state_manager, readers))
    anomaly_task = asyncio.create_task(run_anomaly_detection_task(anomaly_detector, hosts))
    
    while running:
        tasks = []
        for host_cfg in hosts:
            if not running: break
            h_name = host_cfg['name']
            reader = readers[h_name]
            tasks.append(processor.process_host(host_cfg, reader))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        if running:
            await asyncio.sleep(10)
    
    # Cleanup tasks
    metrics_task.cancel()
    ssl_task.cancel()
    state_task.cancel()
    anomaly_task.cancel()
    await asyncio.gather(metrics_task, ssl_task, state_task, anomaly_task, return_exceptions=True)
    
    # Cleanup
    await processor.stop() # Stop the background pusher worker
    
    # Save final state before closing
    current_offsets = {name: r.log_offsets for name, r in readers.items()}
    await state_manager.save(current_offsets)
    
    for reader in readers.values():
        await reader.close()
    await storage.close()
    geoip.close()

async def run_ssl_monitor_task(hosts):
    """
    Periodically checks SSL certificates (every 12 hours).
    """
    logging.info("Starting SSL Monitor Task (Interval: 12h)")
    monitor = SSLMonitor(hosts)
    while True:
        try:
            await monitor.check_all()
            await asyncio.sleep(12 * 60 * 60)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"Error in SSL task: {e}")
            await asyncio.sleep(60 * 60)

async def run_system_metrics_task(hosts, readers):
    """
    Periodically collects system metrics from all hosts.
    """
    logging.info("Starting System Metrics Collector Task (Interval: 60s)")
    collectors = {h['name']: SystemMetricsCollector(h, readers[h['name']]) for h in hosts}
    
    while True:
        try:
            tasks = [c.collect() for c in collectors.values()]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"Error in metrics task: {e}")
            await asyncio.sleep(10)

async def run_cleanup_task(retention_days=365):
    """
    Runs periodically to clean up old logs.
    """
    logging.info(f"Starting Data Retention Scheduler (Retention: {retention_days} days).")
    db_params = get_db_params()
    ch_params = get_ch_params()
    pg_storage = PostgresStorage(db_params)
    ch_storage = ClickHouseStorage(ch_params)
    storage = MultiStorage(pg_storage, ch_storage)
    
    while True:
        try:
            if await storage.connect():
                await storage.cleanup_old_logs(retention_days)
            
            await asyncio.sleep(24 * 60 * 60)
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60 * 60)
        finally:
            await storage.close()

async def run_state_persistence_task(state_manager, readers, interval=30):
    """
    Periodically saves the log offsets to disk.
    """
    logging.info(f"Starting State Persistence Task (Interval: {interval}s)")
    while True:
        try:
            await asyncio.sleep(interval)
            current_offsets = {name: r.log_offsets for name, r in readers.items()}
            await state_manager.save(current_offsets)
        except asyncio.CancelledError:
            # Final save is handled in main()
            raise
        except Exception as e:
            logging.error(f"Error in state persistence task: {e}")

async def run_anomaly_detection_task(anomaly_detector, hosts, interval=300):
    """
    Periodically checks for traffic anomalies (every 5 minutes).
    """
    logging.info(f"Starting Anomaly Detection Task (Interval: {interval}s)")
    while True:
        try:
            await asyncio.sleep(interval)
            tasks = [anomaly_detector.check_anomalies(h['name']) for h in hosts]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logging.error(f"Error in anomaly detection task: {e}")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start cleanup task
    cleanup_task = loop.create_task(run_cleanup_task(365))
    
    # We need host config and readers for metrics task
    # but readers are created inside main(). 
    # Let's refactor slightly to pass them or create them here.
    # For now, I'll just let main() handle its loop and start a separate metrics task inside main.
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        # Cancel background tasks
        cleanup_task.cancel()
        
        # Give them a moment to finish/cancel
        pending = asyncio.all_tasks(loop)
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            
        loop.close()
