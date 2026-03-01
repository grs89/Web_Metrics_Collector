import logging
import asyncio
from parser import LogParser
from verifier import BotVerifier
from metrics import (
    LOGS_PROCESSED_TOTAL, 
    LOG_BATCHES_SAVED_TOTAL, 
    DB_SAVE_ERRORS_TOTAL, 
    LOG_BUFFER_SIZE,
    INGESTION_LATENCY_SECONDS
)

class LogProcessor:
    def __init__(self, geoip, ua_enricher, dns_enricher, storage):
        self.geoip = geoip
        self.ua_enricher = ua_enricher
        self.dns_enricher = dns_enricher
        self.storage = storage
        self.bot_verifier = BotVerifier()
        self.log_buffer = asyncio.Queue(maxsize=10000) # Buffer up to 10k parsed logs
        self._worker_task = None
        self._running = True

    def start(self):
        """Starts the background worker for flushing logs."""
        if not self._worker_task:
            self._worker_task = asyncio.create_task(self._buffer_worker())
            logging.info("LogProcessor background worker started.")

    async def stop(self):
        """Stops the processor and worker."""
        self._running = False
        if self._worker_task:
            logging.info("Stopping LogProcessor worker...")
            self._worker_task.cancel()
            await self._worker_task
            self._worker_task = None

    async def _buffer_worker(self):
        """Background task that pulls logs from the queue and saves them to the DB."""
        while self._running:
            try:
                # Update buffer size gauge
                LOG_BUFFER_SIZE.set(self.log_buffer.qsize())
                
                # Wait for at least one log
                batch = []
                log = await self.log_buffer.get()
                batch.append(log)

                # Try to grab more logs if available (up to 500)
                while len(batch) < 500:
                    try:
                        log = self.log_buffer.get_nowait()
                        batch.append(log)
                    except asyncio.QueueEmpty:
                        break
                
                # Attempt to save the batch
                success = await self._save_batch_with_retry(batch)
                
                # Mark as processed in the queue
                for _ in range(len(batch)):
                    self.log_buffer.task_done()

                if success:
                    LOG_BATCHES_SAVED_TOTAL.inc()
                else:
                    DB_SAVE_ERRORS_TOTAL.inc()
                    logging.error(f"Failed to persist batch of {len(batch)} logs after internal retries.")

            except asyncio.CancelledError:
                logging.info("Worker task cancelled.")
                raise # Re-raise as requested by lint
            except Exception as e:
                logging.error(f"Error in LogProcessor worker: {e}")
                await asyncio.sleep(1)

    async def _save_batch_with_retry(self, batch, max_retries=5):
        """Tries to save logs to the database with exponential backoff."""
        for attempt in range(max_retries):
            try:
                await self.storage.save_logs(batch)
                return True
            except Exception as e:
                delay = 1 * (2 ** attempt)
                logging.warning(f"Database save attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {delay}s...")
                await asyncio.sleep(delay)
        return False

    async def process_host(self, host_cfg, reader):
        """
        Process all log files for a single host.
        """
        host_name = host_cfg['name']
        
        try:
            # Ensure worker is running
            self.start()

            # Iterate through files for this host
            for log_file in host_cfg.get('log_files', []):
                await self._process_file(reader, host_cfg, log_file)

        except Exception as e:
            logging.error(f"[{host_name}] Error in process_host: {e}")

    async def _process_file(self, reader, host_cfg, log_file):
        host_name = host_cfg['name']
        file_path = log_file['path']
        log_type = log_file['type']
        
        try:
            raw_data = await reader.read_updates(file_path)
            if raw_data:
                await self._handle_raw_data(raw_data, host_name, log_type)
        except Exception as e:
            logging.error(f"[{host_name}] Error processing {file_path}: {e}")

    async def _handle_raw_data(self, raw_data, host_name, log_type):
        lines = raw_data.split('\n')
        for line in lines:
            if not line.strip():
                continue
                
            parsed = await self._parse_and_enrich_line(line, log_type, host_name)
            if parsed:
                # Instead of saving directly, we put it in the queue
                try:
                    self.log_buffer.put_nowait(parsed)
                except asyncio.QueueFull:
                    logging.error("Log buffer is full! Dropping log entry.")

    async def _parse_and_enrich_line(self, line, log_type, host_name):
        parsed = LogParser.parse(line, log_type)
        if not parsed:
            return None

        await self._enrich_log(parsed)
        
        # Fake Googlebot Verification
        hostname = parsed.get('hostname')
        user_agent = parsed.get('user_agent', '')
        
        if self.bot_verifier.is_fake_googlebot(user_agent, hostname):
            logging.warning(f"FAKE BOT DETECTED: IP={parsed.get('client_ip')} Hostname={hostname}")
            await self.storage.block_ip(parsed.get('client_ip'), 'Fake Googlebot')
            parsed['is_fake_bot'] = True
        else:
            parsed['is_fake_bot'] = False

        # Ensure defaults and metadata
        for key in ['country_code', 'city', 'latitude', 'longitude', 'request_time_ms', 'bot_category']:
            parsed.setdefault(key, None)
        
        parsed['source_host'] = host_name
        parsed['log_category'] = LogParser.get_category(log_type)
        parsed['server_type'] = 'nginx' if 'nginx' in log_type else 'apache'
        
        return parsed

    async def _enrich_log(self, parsed):
        # Async Enrichers
        geo_data = await self.geoip.enrich(parsed.get('client_ip'))
        parsed.update(geo_data)

        ua_data = self.ua_enricher.enrich(parsed.get('user_agent'))
        parsed.update(ua_data)

        # Async DNS
        hostname = await self.dns_enricher.enrich(parsed.get('client_ip'))
        parsed['hostname'] = hostname
