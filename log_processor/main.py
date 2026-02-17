import time
import logging
import signal
import sys
import os
from concurrent.futures import ThreadPoolExecutor
from config import load_config, get_db_params
from ssh_client import SSHLogReader
from parser import LogParser
from geoip import GeoIPEnricher
from storage import LogStorage
from ua_enricher import UAEnricher
from dns_enricher import DNSEnricher

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def process_host(host_cfg, geoip, ua_enricher, dns_enricher):
    """
    Process all log files for a single host.
    This runs in a separate thread.
    """
    host_name = host_cfg['name']
    
    # Create a dedicated DB connection for this thread
    db_params = get_db_params()
    storage = LogStorage(db_params)
    if not storage.connect():
        logging.error(f"[{host_name}] Could not connect to DB. Skipping this cycle.")
        return

    try:
        reader = SSHLogReader(host_cfg)
        
        # Iterate through files for this host
        for log_file in host_cfg.get('log_files', []):
            file_path = log_file['path']
            log_type = log_file['type']
            
            try:
                # Synchronous read within this thread
                raw_data = reader.read_updates(file_path)
                
                if raw_data:
                    lines = raw_data.split('\n')
                    parsed_logs = []
                    for line in lines:
                        if not line.strip():
                            continue
                            
                        parsed = LogParser.parse(line, log_type)
                        if parsed:
                            # Enrich (GeoIP is usually thread-safe for reading)
                            geo_data = geoip.enrich(parsed.get('client_ip'))
                            parsed.update(geo_data)

                            # Enrich User Agent
                            ua_data = ua_enricher.enrich(parsed.get('user_agent'))
                            parsed.update(ua_data)

                            # Enrich DNS (Reverse Lookup)
                            hostname = dns_enricher.enrich(parsed.get('client_ip'))
                            parsed['hostname'] = hostname
                            
                            # Fake Googlebot Verification
                            user_agent = parsed.get('user_agent', '').lower()
                            is_fake = False
                            if 'googlebot' in user_agent:
                                if not hostname or not (hostname.endswith('.googlebot.com') or hostname.endswith('.google.com')):
                                    is_fake = True
                                    logging.warning(f"FAKE BOT DETECTED: IP={parsed.get('client_ip')} Hostname={hostname}")
                                    # Trigger Block
                                    storage.block_ip(parsed.get('client_ip'), 'Fake Googlebot')
                            
                            parsed['is_fake_bot'] = is_fake

                            # Ensure defaults
                            for key in ['country_code', 'city', 'latitude', 'longitude', 'request_time_ms', 'bot_category']:
                                parsed.setdefault(key, None)
                            
                            # Add metadata
                            parsed['source_host'] = host_name
                            parsed['server_type'] = 'nginx' if 'nginx' in log_type else 'apache'
                            
                            parsed_logs.append(parsed)
                    
                    if parsed_logs:
                        storage.save_logs(parsed_logs)
                        
            except Exception as e:
                logging.error(f"[{host_name}] Error processing {file_path}: {e}")

    finally:
        # Always close the thread-local DB connection
        if storage.conn:
            storage.conn.close()

def main():
    config = load_config()
    
    # Initialize components
    # GeoIPEnricher loads a file, reading is generally thread-safe if it just does lookups
    geoip = GeoIPEnricher()
    ua_enricher = UAEnricher()
    dns_enricher = DNSEnricher()
    
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
            future = executor.submit(process_host, host_cfg, geoip, ua_enricher, dns_enricher)
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
