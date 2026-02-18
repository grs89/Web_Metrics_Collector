import logging
from ssh_client import SSHLogReader
from parser import LogParser
from storage import LogStorage
from config import get_db_params
from verifier import BotVerifier

class LogProcessor:
    def __init__(self, geoip, ua_enricher, dns_enricher):
        self.geoip = geoip
        self.ua_enricher = ua_enricher
        self.dns_enricher = dns_enricher
        self.bot_verifier = BotVerifier()

    def process_host(self, host_cfg):
        """
        Process all log files for a single host.
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
                self._process_file(reader, host_cfg, log_file, storage)

        finally:
            # Always close the thread-local DB connection
            if storage.conn:
                storage.conn.close()

    def _process_file(self, reader, host_cfg, log_file, storage):
        host_name = host_cfg['name']
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
                        self._enrich_log(parsed)
                        
                        # Fake Googlebot Verification
                        hostname = parsed.get('hostname')
                        user_agent = parsed.get('user_agent', '')
                        
                        if self.bot_verifier.is_fake_googlebot(user_agent, hostname):
                            logging.warning(f"FAKE BOT DETECTED: IP={parsed.get('client_ip')} Hostname={hostname}")
                            # Trigger Block
                            storage.block_ip(parsed.get('client_ip'), 'Fake Googlebot')
                            parsed['is_fake_bot'] = True
                        else:
                            parsed['is_fake_bot'] = False

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

    def _enrich_log(self, parsed):
        # Enrich (GeoIP is usually thread-safe for reading)
        geo_data = self.geoip.enrich(parsed.get('client_ip'))
        parsed.update(geo_data)

        # Enrich User Agent
        ua_data = self.ua_enricher.enrich(parsed.get('user_agent'))
        parsed.update(ua_data)

        # Enrich DNS (Reverse Lookup)
        hostname = self.dns_enricher.enrich(parsed.get('client_ip'))
        parsed['hostname'] = hostname
