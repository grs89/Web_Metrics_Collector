import time
import logging
import signal
import sys
import json
from concurrent.futures import ThreadPoolExecutor
from config import load_config, get_db_params
from geoip import GeoIPEnricher
from ua_enricher import UAEnricher
from dns_enricher import DNSEnricher
from processor import LogProcessor
from storage import LogStorage

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
# Remove default handlers to avoid duplicate logs if basicConfig was called internally
logger.handlers = [handler]

def main():
    config = load_config()
    
    # Initialize components
    # GeoIPEnricher loads a file, reading is generally thread-safe if it just does lookups
    geoip = GeoIPEnricher()
    ua_enricher = UAEnricher()
    dns_enricher = DNSEnricher()
    
    # Initialize Processor
    processor = LogProcessor(geoip, ua_enricher, dns_enricher)
    
    hosts = config.get('hosts', [])
    logging.info(f"Initialized monitoring for {len(hosts)} hosts with Multi-threading support.")

    running = True
    def signal_handler(sig, frame):
        nonlocal running
        logging.info("Shutting down...")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    executor = ThreadPoolExecutor(max_workers=len(hosts) + 2)

    while running:
        futures = []
        for host_cfg in hosts:
            if not running: break
            # Submit each host as a task
            future = executor.submit(processor.process_host, host_cfg)
            futures.append(future)
        
        # Wait for all hosts to finish this cycle
        for future in futures:
            try:
                future.result() # This re-raises exceptions from threads if any
            except Exception as e:
                logging.error(f"Thread exception: {e}")

        if running:
            time.sleep(10) # Poll interval
    
    executor.shutdown(wait=True)
    geoip.close()

def run_cleanup_task(retention_days=365):
    """
    Runs periodically to clean up old logs.
    """
    logging.info(f"Starting Data Retention Scheduler (Retention: {retention_days} days).")
    
    while True:
        try:
            db_params = get_db_params()
            storage = LogStorage(db_params)
            if storage.connect():
                storage.cleanup_old_logs(retention_days)
                storage.conn.close()
            
            # Sleep for 24 hours
            time.sleep(24 * 60 * 60)
            
        except Exception as e:
            logging.error(f"Error in cleanup task: {e}")
            time.sleep(60 * 60) # Retry in 1 hour if failed

if __name__ == "__main__":
    import threading
    
    # Start cleanup in a background daemon thread
    cleanup_thread = threading.Thread(target=run_cleanup_task, args=(365,), daemon=True)
    cleanup_thread.start()
    
    main()
