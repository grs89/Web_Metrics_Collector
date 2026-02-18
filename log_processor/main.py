import asyncio
import time
import logging
import signal
import sys
import json
from config import load_config, get_db_params
from geoip import GeoIPEnricher
from ua_enricher import UAEnricher
from dns_enricher import DNSEnricher
from processor import LogProcessor
from storage import LogStorage
from ssh_client import SSHLogReader

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
    
    # Initialize shared components
    geoip = GeoIPEnricher()
    ua_enricher = UAEnricher()
    dns_enricher = DNSEnricher()
    storage = LogStorage(db_params)
    
    if not await storage.connect():
        logging.error("Critical: Could not connect to database. Exiting.")
        return

    # Initialize Processor
    processor = LogProcessor(geoip, ua_enricher, dns_enricher, storage)
    
    hosts = config.get('hosts', [])
    # Initialize SSH Readers for each host
    readers = {h['name']: SSHLogReader(h) for h in hosts}
    
    logging.info(f"Initialized monitoring for {len(hosts)} hosts using asyncio.")

    running = True
    def signal_handler(sig, frame):
        nonlocal running
        logging.info("Shutting down...")
        running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while running:
        tasks = []
        for host_cfg in hosts:
            if not running: break
            h_name = host_cfg['name']
            reader = readers[h_name]
            # Create a task for each host processing cycle
            tasks.append(processor.process_host(host_cfg, reader))
        
        if tasks:
            # Run all host processing cycles concurrently
            await asyncio.gather(*tasks, return_exceptions=True)

        if running:
            await asyncio.sleep(10) # Poll interval
    
    # Cleanup
    for reader in readers.values():
        await reader.close()
    await storage.close()
    geoip.close()

async def run_cleanup_task(retention_days=365):
    """
    Runs periodically to clean up old logs.
    """
    logging.info(f"Starting Data Retention Scheduler (Retention: {retention_days} days).")
    db_params = get_db_params()
    storage = LogStorage(db_params)
    
    while True:
        try:
            if await storage.connect():
                await storage.cleanup_old_logs(retention_days)
            
            # Sleep for 24 hours
            await asyncio.sleep(24 * 60 * 60)
            
        except Exception as e:
            logging.error(f"Error in cleanup task: {e}")
            await asyncio.sleep(60 * 60) # Retry in 1 hour if failed
        finally:
            await storage.close()

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Start cleanup task
    cleanup_task = loop.create_task(run_cleanup_task(365))
    
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
