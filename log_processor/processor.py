import logging
from parser import LogParser
from verifier import BotVerifier

class LogProcessor:
    def __init__(self, geoip, ua_enricher, dns_enricher, storage):
        self.geoip = geoip
        self.ua_enricher = ua_enricher
        self.dns_enricher = dns_enricher
        self.storage = storage # Storage is now shared/pool-based
        self.bot_verifier = BotVerifier()

    async def process_host(self, host_cfg, reader):
        """
        Process all log files for a single host.
        """
        host_name = host_cfg['name']
        
        try:
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
        parsed_logs = []
        for line in lines:
            if not line.strip():
                continue
                
            parsed = await self._parse_and_enrich_line(line, log_type, host_name)
            if parsed:
                parsed_logs.append(parsed)
        
        if parsed_logs:
            await self.storage.save_logs(parsed_logs)

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
        parsed['server_type'] = 'nginx' if 'nginx' in log_type else 'apache'
        
        return parsed

    async def _enrich_log(self, parsed):
        # Async Enrichers
        geo_data = await self.geoip.enrich(parsed.get('client_ip'))
        parsed.update(geo_data)

        # UA enricher is still CPU-bound sync (regex/logic) 
        # but fast enough to not block significantly, 
        # though we could wrap it in to_thread if needed.
        ua_data = self.ua_enricher.enrich(parsed.get('user_agent'))
        parsed.update(ua_data)

        # Async DNS
        hostname = await self.dns_enricher.enrich(parsed.get('client_ip'))
        parsed['hostname'] = hostname
