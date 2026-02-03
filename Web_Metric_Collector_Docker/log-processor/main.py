#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
WGP - Web Geo Profiler - Log Processor with PULL-based Collection
Collects logs from remote servers via SSH, parses them, and stores in PostgreSQL
═══════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import signal
import logging
import re
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path
from abc import ABC, abstractmethod
import threading

import yaml
import paramiko
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

# Optional GeoIP support
try:
    import geoip2.database
    import geoip2.errors
    GEOIP_AVAILABLE = True
except ImportError:
    GEOIP_AVAILABLE = False

# ═══════════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Application configuration from environment variables."""
    postgres_host: str = os.getenv('POSTGRES_HOST', 'localhost')
    postgres_port: int = int(os.getenv('POSTGRES_PORT', '5432'))
    postgres_user: str = os.getenv('POSTGRES_USER', 'wgp_user')
    postgres_password: str = os.getenv('POSTGRES_PASSWORD', 'wgp_secure_password_2024')
    postgres_db: str = os.getenv('POSTGRES_DB', 'web_logs')
    geoip_db: str = os.getenv('GEOIP_DB', '/app/geoip/GeoLite2-City.mmdb')
    batch_size: int = int(os.getenv('BATCH_SIZE', '100'))
    flush_interval: float = float(os.getenv('FLUSH_INTERVAL', '5.0'))
    hosts_config: str = os.getenv('HOSTS_CONFIG', '/app/config/hosts.yml')
    position_file: str = os.getenv('POSITION_FILE', '/app/data/positions.json')


config = Config()


# ═══════════════════════════════════════════════════════════════════════════
# Host Configuration
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class HostConfig:
    """Configuration for a remote host."""
    name: str
    host: str
    port: int = 22
    ssh_user: str = 'wgp'
    ssh_key_path: str = '/app/ssh/id_rsa'
    server_type: str = 'nginx'
    log_paths: List[str] = field(default_factory=list)
    log_format: str = 'json'
    enabled: bool = True


def load_hosts_config(config_path: str) -> tuple[dict, List[HostConfig]]:
    """Load host configuration from YAML file."""
    if not Path(config_path).exists():
        logger.warning(f"Hosts config not found at {config_path}")
        return {}, []
    
    with open(config_path) as f:
        data = yaml.safe_load(f)
    
    global_config = data.get('global', {})
    hosts = []
    
    for host_data in data.get('hosts', []):
        if not host_data.get('enabled', True):
            continue
        
        host = HostConfig(
            name=host_data['name'],
            host=host_data['host'],
            port=host_data.get('port', 22),
            ssh_user=host_data.get('ssh_user', global_config.get('ssh_user', 'wgp')),
            ssh_key_path=host_data.get('ssh_key_path', global_config.get('ssh_key_path', '/app/ssh/id_rsa')),
            server_type=host_data.get('server_type', 'nginx'),
            log_paths=host_data.get('log_paths', []),
            log_format=host_data.get('log_format', 'json'),
            enabled=host_data.get('enabled', True)
        )
        hosts.append(host)
    
    return global_config, hosts


# ═══════════════════════════════════════════════════════════════════════════
# Position Tracking
# ═══════════════════════════════════════════════════════════════════════════

class PositionTracker:
    """Tracks read positions for each log file to avoid re-reading."""
    
    def __init__(self, position_file: str):
        self.position_file = position_file
        self.positions: Dict[str, int] = {}
        self._load()
    
    def _load(self):
        """Load positions from file."""
        if Path(self.position_file).exists():
            try:
                with open(self.position_file) as f:
                    self.positions = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load positions: {e}")
                self.positions = {}
    
    def _save(self):
        """Save positions to file."""
        try:
            Path(self.position_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.position_file, 'w') as f:
                json.dump(self.positions, f)
        except Exception as e:
            logger.warning(f"Failed to save positions: {e}")
    
    def get_position(self, host: str, log_path: str) -> int:
        """Get the last read position for a log file."""
        key = f"{host}:{log_path}"
        return self.positions.get(key, 0)
    
    def set_position(self, host: str, log_path: str, position: int):
        """Set the read position for a log file."""
        key = f"{host}:{log_path}"
        self.positions[key] = position
        self._save()


# ═══════════════════════════════════════════════════════════════════════════
# SSH Log Collector
# ═══════════════════════════════════════════════════════════════════════════

class SSHLogCollector:
    """Collects logs from remote servers via SSH."""
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self._connections: Dict[str, paramiko.SSHClient] = {}
    
    def _get_connection(self, host: HostConfig) -> Optional[paramiko.SSHClient]:
        """Get or create SSH connection to host."""
        key = f"{host.host}:{host.port}"
        
        if key in self._connections:
            # Test if connection is still alive
            try:
                transport = self._connections[key].get_transport()
                if transport and transport.is_active():
                    return self._connections[key]
            except Exception:
                pass
            # Connection dead, remove it
            del self._connections[key]
        
        # Create new connection
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Check if key file exists
            if not Path(host.ssh_key_path).exists():
                logger.error(f"SSH key not found: {host.ssh_key_path}")
                return None
            
            client.connect(
                hostname=host.host,
                port=host.port,
                username=host.ssh_user,
                key_filename=host.ssh_key_path,
                timeout=self.timeout
            )
            self._connections[key] = client
            logger.info(f"Connected to {host.name} ({host.host})")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to {host.name}: {e}")
            return None
    
    def get_file_size(self, host: HostConfig, log_path: str) -> Optional[int]:
        """Get the current size of a log file."""
        client = self._get_connection(host)
        if not client:
            return None
        
        try:
            stdin, stdout, stderr = client.exec_command(f"stat -c %s {log_path} 2>/dev/null || stat -f %z {log_path}")
            output = stdout.read().decode().strip()
            return int(output) if output else None
        except Exception as e:
            logger.debug(f"Failed to get file size for {log_path}: {e}")
            return None
    
    def read_from_position(self, host: HostConfig, log_path: str, position: int) -> tuple[str, int]:
        """Read log file from a specific position. Returns (content, new_position)."""
        client = self._get_connection(host)
        if not client:
            return "", position
        
        try:
            # Get current file size
            file_size = self.get_file_size(host, log_path)
            if file_size is None:
                return "", position
            
            # Handle log rotation (file is smaller than position)
            if file_size < position:
                logger.info(f"Log rotation detected for {log_path} on {host.name}")
                position = 0
            
            # No new data
            if file_size == position:
                return "", position
            
            # Read new data using tail
            bytes_to_read = file_size - position
            command = f"tail -c {bytes_to_read} {log_path}"
            
            stdin, stdout, stderr = client.exec_command(command)
            content = stdout.read().decode('utf-8', errors='replace')
            
            return content, file_size
        except Exception as e:
            logger.error(f"Failed to read {log_path} from {host.name}: {e}")
            return "", position
    
    def close_all(self):
        """Close all SSH connections."""
        for client in self._connections.values():
            try:
                client.close()
            except Exception:
                pass
        self._connections.clear()


# ═══════════════════════════════════════════════════════════════════════════
# GeoIP Handler
# ═══════════════════════════════════════════════════════════════════════════

class GeoIPHandler:
    """Handles GeoIP lookups using MaxMind database."""
    
    def __init__(self, db_path: str):
        self.reader = None
        self.db_path = db_path
        self._load_database()
    
    def _load_database(self):
        """Load the GeoIP database if available."""
        if not GEOIP_AVAILABLE:
            logger.warning("GeoIP2 library not available. GeoIP lookups disabled.")
            return
        
        if not Path(self.db_path).exists():
            logger.warning(f"GeoIP database not found at {self.db_path}. GeoIP lookups disabled.")
            return
        
        try:
            self.reader = geoip2.database.Reader(self.db_path)
            logger.info(f"GeoIP database loaded from {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to load GeoIP database: {e}")
    
    def lookup(self, ip: str) -> Dict[str, Any]:
        """Look up geographic information for an IP address."""
        result = {
            'country_code': None,
            'country_name': None,
            'city': None,
            'region': None,
            'latitude': None,
            'longitude': None,
            'timezone': None,
        }
        
        if not self.reader:
            return result
        
        # Skip private/local IPs
        if ip.startswith(('10.', '172.16.', '172.17.', '172.18.', '172.19.',
                         '172.20.', '172.21.', '172.22.', '172.23.', '172.24.',
                         '172.25.', '172.26.', '172.27.', '172.28.', '172.29.',
                         '172.30.', '172.31.', '192.168.', '127.', '::1', 'fe80:')):
            return result
        
        try:
            response = self.reader.city(ip)
            result['country_code'] = response.country.iso_code
            result['country_name'] = response.country.name
            result['city'] = response.city.name
            result['region'] = response.subdivisions.most_specific.name if response.subdivisions else None
            result['latitude'] = response.location.latitude
            result['longitude'] = response.location.longitude
            result['timezone'] = response.location.time_zone
        except Exception:
            pass
        
        return result
    
    def close(self):
        """Close the GeoIP database reader."""
        if self.reader:
            self.reader.close()


# ═══════════════════════════════════════════════════════════════════════════
# Database Handler
# ═══════════════════════════════════════════════════════════════════════════

class DatabaseHandler:
    """Handles PostgreSQL database operations."""
    
    def __init__(self, cfg: Config):
        self.config = cfg
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Establish database connection with retries."""
        max_retries = 30
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.conn = psycopg2.connect(
                    host=self.config.postgres_host,
                    port=self.config.postgres_port,
                    user=self.config.postgres_user,
                    password=self.config.postgres_password,
                    database=self.config.postgres_db
                )
                self.conn.autocommit = False
                logger.info("Connected to PostgreSQL database")
                return
            except psycopg2.OperationalError as e:
                logger.warning(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
                time.sleep(retry_delay)
        
        raise ConnectionError("Failed to connect to database after maximum retries")
    
    def insert_logs(self, logs: List[Dict[str, Any]]) -> int:
        """Insert multiple log entries in batch."""
        if not logs:
            return 0
        
        columns = [
            'timestamp', 'server_type', 'source_host', 'remote_addr', 'remote_user', 'request_method', 'request_uri',
            'request', 'status', 'body_bytes_sent', 'request_time', 'request_length',
            'http_referer', 'http_user_agent', 'http_x_forwarded_for',
            'host', 'server_name', 'upstream_addr', 'upstream_response_time',
            'ssl_protocol', 'ssl_cipher', 'connection', 'connection_requests', 'gzip_ratio',
            'country_code', 'country_name', 'city', 'region', 'latitude', 'longitude', 'timezone'
        ]
        
        values = []
        for log in logs:
            values.append((
                log.get('timestamp'),
                log.get('server_type', 'nginx'),
                log.get('source_host'),
                log.get('remote_addr'),
                log.get('remote_user'),
                log.get('request_method'),
                log.get('request_uri'),
                log.get('request'),
                log.get('status'),
                log.get('body_bytes_sent'),
                log.get('request_time'),
                log.get('request_length'),
                log.get('http_referer'),
                log.get('http_user_agent'),
                log.get('http_x_forwarded_for'),
                log.get('host'),
                log.get('server_name'),
                log.get('upstream_addr'),
                log.get('upstream_response_time'),
                log.get('ssl_protocol'),
                log.get('ssl_cipher'),
                log.get('connection'),
                log.get('connection_requests'),
                log.get('gzip_ratio'),
                log.get('country_code'),
                log.get('country_name'),
                log.get('city'),
                log.get('region'),
                log.get('latitude'),
                log.get('longitude'),
                log.get('timezone'),
            ))
        
        try:
            with self.conn.cursor() as cursor:
                insert_query = sql.SQL("""
                    INSERT INTO web_access_logs ({})
                    VALUES %s
                """).format(sql.SQL(', ').join(map(sql.Identifier, columns)))
                
                execute_values(cursor, insert_query.as_string(self.conn), values)
                self.conn.commit()
                return len(values)
        except Exception as e:
            logger.error(f"Failed to insert logs: {e}")
            self.conn.rollback()
            self._reconnect_if_needed()
            return 0
    
    def _reconnect_if_needed(self):
        """Reconnect to database if connection is lost."""
        try:
            self.conn.cursor().execute("SELECT 1")
        except Exception:
            logger.warning("Database connection lost, reconnecting...")
            self._connect()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# Log Parsers
# ═══════════════════════════════════════════════════════════════════════════

class LogParser:
    """Parses log lines from different server types."""
    
    # Apache Combined Log Format regex
    COMBINED_LOG_PATTERN = re.compile(
        r'^(?P<remote_addr>\S+)\s+'
        r'(?P<ident>\S+)\s+'
        r'(?P<remote_user>\S+)\s+'
        r'\[(?P<timestamp>[^\]]+)\]\s+'
        r'"(?P<request>[^"]*)"\s+'
        r'(?P<status>\d+)\s+'
        r'(?P<body_bytes_sent>\S+)\s*'
        r'(?:"(?P<http_referer>[^"]*)"\s*)?'
        r'(?:"(?P<http_user_agent>[^"]*)")?'
    )
    
    def parse_line(self, line: str, server_type: str, source_host: str) -> Optional[Dict[str, Any]]:
        """Parse a single log line."""
        line = line.strip()
        if not line:
            return None
        
        # Try JSON first
        if line.startswith('{'):
            return self._parse_json(line, server_type, source_host)
        
        # Try Combined Log Format
        return self._parse_combined(line, server_type, source_host)
    
    def _parse_json(self, line: str, server_type: str, source_host: str) -> Optional[Dict[str, Any]]:
        """Parse JSON log format."""
        try:
            data = json.loads(line)
            
            parsed = {
                'server_type': server_type,
                'source_host': source_host,
                'timestamp': data.get('timestamp') or data.get('time') or datetime.now(timezone.utc).isoformat(),
                'remote_addr': data.get('remote_addr') or data.get('clientip') or '0.0.0.0',
                'remote_user': self._clean(data.get('remote_user')),
                'request_method': data.get('request_method'),
                'request_uri': data.get('request_uri'),
                'request': data.get('request'),
                'status': self._to_int(data.get('status')),
                'body_bytes_sent': self._to_int(data.get('body_bytes_sent')),
                'request_time': self._to_float(data.get('request_time')),
                'request_length': self._to_int(data.get('request_length')),
                'http_referer': self._clean(data.get('http_referer')),
                'http_user_agent': self._clean(data.get('http_user_agent')),
                'http_x_forwarded_for': self._clean(data.get('http_x_forwarded_for')),
                'host': data.get('host'),
                'server_name': data.get('server_name'),
                'upstream_addr': self._clean(data.get('upstream_addr')),
                'upstream_response_time': self._clean(data.get('upstream_response_time')),
                'ssl_protocol': self._clean(data.get('ssl_protocol')),
                'ssl_cipher': self._clean(data.get('ssl_cipher')),
                'connection': self._to_int(data.get('connection')),
                'connection_requests': self._to_int(data.get('connection_requests')),
                'gzip_ratio': self._clean(data.get('gzip_ratio')),
            }
            return parsed
        except json.JSONDecodeError:
            return None
    
    def _parse_combined(self, line: str, server_type: str, source_host: str) -> Optional[Dict[str, Any]]:
        """Parse Combined Log Format."""
        match = self.COMBINED_LOG_PATTERN.match(line)
        if not match:
            return None
        
        groups = match.groupdict()
        
        # Parse request line
        request = groups.get('request', '')
        method, uri = None, None
        parts = request.split(' ', 2)
        if len(parts) >= 2:
            method, uri = parts[0], parts[1]
        
        # Parse timestamp
        timestamp = self._parse_apache_timestamp(groups.get('timestamp', ''))
        
        return {
            'server_type': server_type,
            'source_host': source_host,
            'timestamp': timestamp or datetime.now(timezone.utc).isoformat(),
            'remote_addr': groups.get('remote_addr', '0.0.0.0'),
            'remote_user': self._clean(groups.get('remote_user')),
            'request_method': method,
            'request_uri': uri,
            'request': request,
            'status': self._to_int(groups.get('status')),
            'body_bytes_sent': self._to_int(groups.get('body_bytes_sent')),
            'request_time': None,
            'request_length': None,
            'http_referer': self._clean(groups.get('http_referer')),
            'http_user_agent': self._clean(groups.get('http_user_agent')),
            'http_x_forwarded_for': None,
            'host': None,
            'server_name': None,
        }
    
    def _parse_apache_timestamp(self, ts: str) -> Optional[str]:
        """Convert Apache timestamp to ISO format."""
        try:
            dt = datetime.strptime(ts, "%d/%b/%Y:%H:%M:%S %z")
            return dt.isoformat()
        except ValueError:
            return None
    
    def _clean(self, value: Any) -> Optional[str]:
        """Clean field value."""
        if value is None or value == '-' or value == '':
            return None
        return str(value)
    
    def _to_int(self, value: Any) -> Optional[int]:
        """Convert to int."""
        if value is None or value == '-' or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _to_float(self, value: Any) -> Optional[float]:
        """Convert to float."""
        if value is None or value == '-' or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None


# ═══════════════════════════════════════════════════════════════════════════
# Main Log Processor
# ═══════════════════════════════════════════════════════════════════════════

class LogProcessor:
    """Main log processor that collects and processes logs via SSH."""
    
    def __init__(self):
        self.config = config
        self.geoip = GeoIPHandler(config.geoip_db)
        self.db = DatabaseHandler(config)
        self.parser = LogParser()
        self.collector = SSHLogCollector()
        self.positions = PositionTracker(config.position_file)
        
        self.buffer: List[Dict[str, Any]] = []
        self.last_flush = time.time()
        self.running = True
        
        # Stats
        self.stats = {'total': 0, 'errors': 0}
        
        # Load hosts config
        self.global_config, self.hosts = load_hosts_config(config.hosts_config)
        self.pull_interval = self.global_config.get('pull_interval', 30)
        
        # Signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def process_logs(self, content: str, host: HostConfig):
        """Process log content from a host."""
        lines = content.strip().split('\n')
        
        for line in lines:
            parsed = self.parser.parse_line(line, host.server_type, host.name)
            if not parsed:
                continue
            
            # Enrich with GeoIP
            ip = parsed.get('remote_addr', '')
            geo_data = self.geoip.lookup(ip)
            parsed.update(geo_data)
            
            self.buffer.append(parsed)
            self.stats['total'] += 1
        
        # Flush if buffer is full
        if len(self.buffer) >= self.config.batch_size:
            self.flush()
    
    def flush(self):
        """Flush buffer to database."""
        if not self.buffer:
            return
        
        count = self.db.insert_logs(self.buffer)
        if count > 0:
            logger.info(f"Inserted {count} log entries")
        
        self.buffer = []
        self.last_flush = time.time()
    
    def collect_from_host(self, host: HostConfig):
        """Collect logs from a single host."""
        for log_path in host.log_paths:
            position = self.positions.get_position(host.host, log_path)
            content, new_position = self.collector.read_from_position(host, log_path, position)
            
            if content:
                logger.debug(f"Read {len(content)} bytes from {host.name}:{log_path}")
                self.process_logs(content, host)
                self.positions.set_position(host.host, log_path, new_position)
    
    def run(self):
        """Main loop - collect logs from all hosts periodically."""
        logger.info("=" * 70)
        logger.info("WGP - Web Geo Profiler - PULL-based Log Processor")
        logger.info("=" * 70)
        logger.info(f"PostgreSQL: {config.postgres_host}:{config.postgres_port}/{config.postgres_db}")
        logger.info(f"Hosts config: {config.hosts_config}")
        logger.info(f"Pull interval: {self.pull_interval}s")
        logger.info(f"Configured hosts: {len(self.hosts)}")
        for host in self.hosts:
            logger.info(f"  - {host.name} ({host.host}): {host.server_type}")
        logger.info("=" * 70)
        
        if not self.hosts:
            logger.warning("No hosts configured! Add hosts to config/hosts.yml")
            logger.info("Waiting for hosts configuration...")
        
        while self.running:
            try:
                # Reload config to pick up changes
                self.global_config, self.hosts = load_hosts_config(config.hosts_config)
                self.pull_interval = self.global_config.get('pull_interval', 30)
                
                # Collect from all hosts
                for host in self.hosts:
                    if not self.running:
                        break
                    try:
                        self.collect_from_host(host)
                    except Exception as e:
                        logger.error(f"Error collecting from {host.name}: {e}")
                        self.stats['errors'] += 1
                
                # Flush any remaining logs
                if (time.time() - self.last_flush) >= self.config.flush_interval:
                    self.flush()
                
                # Wait for next pull
                time.sleep(self.pull_interval)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)
        
        # Cleanup on shutdown
        self.flush()
        self.collector.close_all()
        self.geoip.close()
        self.db.close()
        logger.info(f"Shutdown complete. Total logs: {self.stats['total']}, Errors: {self.stats['errors']}")


# ═══════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    processor = LogProcessor()
    processor.run()


if __name__ == '__main__':
    main()
