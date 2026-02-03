#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
WGP - Web Geo Profiler - Log Processor
Parses Nginx and Apache JSON logs, enriches with GeoIP data, and stores in PostgreSQL
═══════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import signal
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from abc import ABC, abstractmethod

import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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
    log_file: str = os.getenv('LOG_FILE', '/var/log/webserver/access.log')
    geoip_db: str = os.getenv('GEOIP_DB', '/app/geoip/GeoLite2-City.mmdb')
    batch_size: int = int(os.getenv('BATCH_SIZE', '100'))
    flush_interval: float = float(os.getenv('FLUSH_INTERVAL', '5.0'))
    default_server_type: str = os.getenv('DEFAULT_SERVER_TYPE', 'nginx')  # 'nginx' or 'apache'


config = Config()


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
            logger.info("To enable GeoIP: Download GeoLite2-City.mmdb from MaxMind")
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
        except geoip2.errors.AddressNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"GeoIP lookup failed for {ip}: {e}")
        
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
    
    def __init__(self, config: Config):
        self.config = config
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
        
        raise Exception("Failed to connect to database after maximum retries")
    
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
        except:
            logger.warning("Database connection lost, reconnecting...")
            self._connect()
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# Log Parsers
# ═══════════════════════════════════════════════════════════════════════════

class BaseLogParser(ABC):
    """Abstract base class for log parsers."""
    
    @abstractmethod
    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single log line."""
        pass
    
    @abstractmethod
    def get_server_type(self) -> str:
        """Return the server type this parser handles."""
        pass


class NginxLogParser(BaseLogParser):
    """Parses Nginx JSON log entries."""
    
    def get_server_type(self) -> str:
        return 'nginx'
    
    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single JSON log line from Nginx."""
        if not line.strip():
            return None
        
        try:
            data = json.loads(line)
            
            # Clean and validate required fields
            parsed = {
                'server_type': 'nginx',
                'source_host': data.get('source_host') or data.get('host_name') or data.get('beat', {}).get('hostname') or data.get('agent', {}).get('hostname'),
                'timestamp': data.get('timestamp') or datetime.utcnow().isoformat(),
                'remote_addr': data.get('remote_addr', '0.0.0.0'),
                'remote_user': data.get('remote_user') if data.get('remote_user') != '-' else None,
                'request_method': data.get('request_method'),
                'request_uri': data.get('request_uri'),
                'request': data.get('request'),
                'status': int(data.get('status', 0)),
                'body_bytes_sent': int(data.get('body_bytes_sent', 0)),
                'request_time': float(data.get('request_time', 0)) if data.get('request_time') else None,
                'request_length': int(data.get('request_length', 0)) if data.get('request_length') else None,
                'http_referer': data.get('http_referer') if data.get('http_referer') != '-' else None,
                'http_user_agent': data.get('http_user_agent') if data.get('http_user_agent') != '-' else None,
                'http_x_forwarded_for': data.get('http_x_forwarded_for') if data.get('http_x_forwarded_for') != '-' else None,
                'host': data.get('host'),
                'server_name': data.get('server_name'),
                'upstream_addr': data.get('upstream_addr') if data.get('upstream_addr') != '-' else None,
                'upstream_response_time': data.get('upstream_response_time') if data.get('upstream_response_time') != '-' else None,
                'ssl_protocol': data.get('ssl_protocol') if data.get('ssl_protocol') != '-' else None,
                'ssl_cipher': data.get('ssl_cipher') if data.get('ssl_cipher') != '-' else None,
                'connection': int(data.get('connection', 0)) if data.get('connection') else None,
                'connection_requests': int(data.get('connection_requests', 0)) if data.get('connection_requests') else None,
                'gzip_ratio': data.get('gzip_ratio') if data.get('gzip_ratio') != '-' else None,
            }
            
            return parsed
        except json.JSONDecodeError:
            logger.debug(f"Invalid JSON log line: {line[:100]}...")
            return None
        except Exception as e:
            logger.debug(f"Failed to parse Nginx log line: {e}")
            return None


class ApacheLogParser(BaseLogParser):
    """Parses Apache log entries (JSON and Combined Log Format)."""
    
    # Apache Combined Log Format regex
    # Format: %h %l %u %t "%r" %>s %b "%{Referer}i" "%{User-Agent}i"
    COMBINED_LOG_PATTERN = re.compile(
        r'^(?P<remote_addr>\S+)\s+'                    # IP address
        r'(?P<ident>\S+)\s+'                           # Ident (usually -)
        r'(?P<remote_user>\S+)\s+'                     # Remote user
        r'\[(?P<timestamp>[^\]]+)\]\s+'                # Timestamp [day/month/year:hour:min:sec zone]
        r'"(?P<request>[^"]*)"\s+'                     # Request line
        r'(?P<status>\d+)\s+'                          # Status code
        r'(?P<body_bytes_sent>\S+)\s*'                 # Bytes sent (- if 0)
        r'(?:"(?P<http_referer>[^"]*)"\s*)?'           # Referer (optional)
        r'(?:"(?P<http_user_agent>[^"]*)")?'           # User agent (optional)
    )
    
    # Apache timestamp format: 02/Feb/2024:10:30:00 +0000
    APACHE_TIME_FORMAT = "%d/%b/%Y:%H:%M:%S %z"
    
    def get_server_type(self) -> str:
        return 'apache'
    
    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single log line from Apache (JSON or Combined format)."""
        if not line.strip():
            return None
        
        # Try JSON format first
        if line.strip().startswith('{'):
            return self._parse_json(line)
        
        # Try Combined Log Format
        return self._parse_combined(line)
    
    def _parse_json(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse Apache JSON log format."""
        try:
            data = json.loads(line)
            
            # Handle Apache-specific field names
            parsed = {
                'server_type': 'apache',
                'source_host': data.get('source_host') or data.get('host_name') or data.get('beat', {}).get('hostname') or data.get('agent', {}).get('hostname'),
                'timestamp': data.get('timestamp') or data.get('time') or datetime.utcnow().isoformat(),
                'remote_addr': data.get('remote_addr') or data.get('clientip') or data.get('a') or '0.0.0.0',
                'remote_user': self._clean_field(data.get('remote_user') or data.get('u')),
                'request_method': data.get('request_method') or data.get('m'),
                'request_uri': data.get('request_uri') or data.get('U') or data.get('Uq'),
                'request': data.get('request') or data.get('r'),
                'status': int(data.get('status') or data.get('s') or 0),
                'body_bytes_sent': self._parse_bytes(data.get('body_bytes_sent') or data.get('B') or data.get('b')),
                'request_time': self._parse_request_time(data.get('request_time') or data.get('D') or data.get('T')),
                'request_length': self._parse_int(data.get('request_length') or data.get('I')),
                'http_referer': self._clean_field(data.get('http_referer') or data.get('Referer')),
                'http_user_agent': self._clean_field(data.get('http_user_agent') or data.get('User-Agent')),
                'http_x_forwarded_for': self._clean_field(data.get('http_x_forwarded_for') or data.get('X-Forwarded-For')),
                'host': data.get('host') or data.get('v') or data.get('V'),
                'server_name': data.get('server_name') or data.get('v'),
                'ssl_protocol': self._clean_field(data.get('ssl_protocol')),
                'ssl_cipher': self._clean_field(data.get('ssl_cipher')),
            }
            
            return parsed
        except json.JSONDecodeError:
            return None
        except Exception as e:
            logger.debug(f"Failed to parse Apache JSON log line: {e}")
            return None
    
    def _parse_combined(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse Apache Combined Log Format."""
        try:
            match = self.COMBINED_LOG_PATTERN.match(line)
            if not match:
                logger.debug(f"Line does not match Combined Log Format: {line[:100]}...")
                return None
            
            groups = match.groupdict()
            
            # Parse the request line to extract method and URI
            request = groups.get('request', '')
            method, uri = self._parse_request_line(request)
            
            # Parse timestamp
            timestamp = self._parse_apache_timestamp(groups.get('timestamp', ''))
            
            parsed = {
                'server_type': 'apache',
                'timestamp': timestamp or datetime.utcnow().isoformat(),
                'remote_addr': groups.get('remote_addr', '0.0.0.0'),
                'remote_user': self._clean_field(groups.get('remote_user')),
                'request_method': method,
                'request_uri': uri,
                'request': request,
                'status': int(groups.get('status', 0)),
                'body_bytes_sent': self._parse_bytes(groups.get('body_bytes_sent')),
                'request_time': None,  # Not available in Combined format
                'request_length': None,
                'http_referer': self._clean_field(groups.get('http_referer')),
                'http_user_agent': self._clean_field(groups.get('http_user_agent')),
                'http_x_forwarded_for': None,
                'host': None,
                'server_name': None,
            }
            
            return parsed
        except Exception as e:
            logger.debug(f"Failed to parse Apache Combined log line: {e}")
            return None
    
    def _parse_request_line(self, request: str) -> tuple:
        """Parse request line to extract method and URI."""
        parts = request.split(' ', 2)
        if len(parts) >= 2:
            return parts[0], parts[1]
        return None, None
    
    def _parse_apache_timestamp(self, ts: str) -> Optional[str]:
        """Convert Apache timestamp to ISO format."""
        try:
            dt = datetime.strptime(ts, self.APACHE_TIME_FORMAT)
            return dt.isoformat()
        except ValueError:
            return None
    
    def _clean_field(self, value: Any) -> Optional[str]:
        """Clean a field value, returning None for empty/dash values."""
        if value is None or value == '-' or value == '':
            return None
        return str(value)
    
    def _parse_bytes(self, value: Any) -> int:
        """Parse bytes sent, handling '-' for 0."""
        if value is None or value == '-' or value == '':
            return 0
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0
    
    def _parse_int(self, value: Any) -> Optional[int]:
        """Parse an integer value."""
        if value is None or value == '-' or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_request_time(self, value: Any) -> Optional[float]:
        """Parse request time. Apache's %D is in microseconds, %T is in seconds."""
        if value is None or value == '-' or value == '':
            return None
        try:
            val = float(value)
            # If value is large, assume it's microseconds (Apache %D format)
            if val > 1000:
                return val / 1000000.0
            return val
        except (ValueError, TypeError):
            return None


class LogParserFactory:
    """Factory for creating appropriate log parsers."""
    
    @staticmethod
    def detect_format(line: str) -> str:
        """Detect the log format from a sample line."""
        if not line.strip():
            return 'unknown'
        
        # Check for JSON format
        if line.strip().startswith('{'):
            try:
                data = json.loads(line)
                # Check for Nginx-specific fields
                if 'nginx' in str(data.get('log_type', '')).lower():
                    return 'nginx'
                if 'apache' in str(data.get('log_type', '')).lower():
                    return 'apache'
                # Check for Nginx-specific fields
                if 'upstream_addr' in data or 'gzip_ratio' in data:
                    return 'nginx'
                # Default to nginx for JSON (more common)
                return 'nginx'
            except json.JSONDecodeError:
                pass
        
        # Check for Apache Combined Log Format
        if ApacheLogParser.COMBINED_LOG_PATTERN.match(line):
            return 'apache'
        
        return 'unknown'
    
    @staticmethod
    def get_parser(server_type: str) -> BaseLogParser:
        """Get the appropriate parser for a server type."""
        if server_type == 'apache':
            return ApacheLogParser()
        return NginxLogParser()


class AutoDetectLogParser(BaseLogParser):
    """Parser that auto-detects log format and delegates to appropriate parser."""
    
    def __init__(self, default_type: str = 'nginx'):
        self.nginx_parser = NginxLogParser()
        self.apache_parser = ApacheLogParser()
        self.default_type = default_type
        self._detected_type = None
    
    def get_server_type(self) -> str:
        return self._detected_type or self.default_type
    
    def parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a log line, auto-detecting the format."""
        if not line.strip():
            return None
        
        # Check for explicit log_type in JSON
        if line.strip().startswith('{'):
            try:
                data = json.loads(line)
                log_type = str(data.get('log_type', '')).lower()
                
                if 'apache' in log_type:
                    self._detected_type = 'apache'
                    return self.apache_parser.parse_line(line)
                elif 'nginx' in log_type:
                    self._detected_type = 'nginx'
                    return self.nginx_parser.parse_line(line)
            except json.JSONDecodeError:
                pass
        
        # Try Nginx parser first (JSON format)
        result = self.nginx_parser.parse_line(line)
        if result:
            self._detected_type = 'nginx'
            return result
        
        # Try Apache parser (JSON or Combined format)
        result = self.apache_parser.parse_line(line)
        if result:
            self._detected_type = 'apache'
            return result
        
        logger.debug(f"Could not parse line with any parser: {line[:100]}...")
        return None


# ═══════════════════════════════════════════════════════════════════════════
# Log File Watcher
# ═══════════════════════════════════════════════════════════════════════════

class LogProcessor:
    """Main log processor that watches and processes web server logs."""
    
    def __init__(self, config: Config):
        self.config = config
        self.geoip = GeoIPHandler(config.geoip_db)
        self.db = DatabaseHandler(config)
        self.parser = AutoDetectLogParser(config.default_server_type)
        self.buffer: List[Dict[str, Any]] = []
        self.last_flush = time.time()
        self.running = True
        self.file_position = 0
        
        # Statistics
        self.stats = {
            'nginx': 0,
            'apache': 0,
            'unknown': 0
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def process_line(self, line: str):
        """Process a single log line."""
        parsed = self.parser.parse_line(line)
        if not parsed:
            self.stats['unknown'] += 1
            return
        
        # Track stats by server type
        server_type = parsed.get('server_type', 'unknown')
        self.stats[server_type] = self.stats.get(server_type, 0) + 1
        
        # Enrich with GeoIP data
        ip = parsed.get('remote_addr', '')
        geo_data = self.geoip.lookup(ip)
        parsed.update(geo_data)
        
        self.buffer.append(parsed)
        
        # Flush if buffer is full or timeout reached
        if len(self.buffer) >= self.config.batch_size or \
           (time.time() - self.last_flush) >= self.config.flush_interval:
            self.flush()
    
    def flush(self):
        """Flush buffer to database."""
        if not self.buffer:
            return
        
        count = self.db.insert_logs(self.buffer)
        if count > 0:
            # Log with server type breakdown
            nginx_count = sum(1 for log in self.buffer if log.get('server_type') == 'nginx')
            apache_count = sum(1 for log in self.buffer if log.get('server_type') == 'apache')
            logger.info(f"Inserted {count} log entries (Nginx: {nginx_count}, Apache: {apache_count})")
        
        self.buffer = []
        self.last_flush = time.time()
    
    def tail_file(self):
        """Tail the log file and process new lines."""
        log_path = Path(self.config.log_file)
        
        logger.info(f"Watching log file: {log_path}")
        
        # Wait for log file to exist
        while not log_path.exists() and self.running:
            logger.info(f"Waiting for log file {log_path} to appear...")
            time.sleep(5)
        
        if not self.running:
            return
        
        # Track processed lines to avoid duplicates after restart
        last_lines_hash = set()
        
        # Main processing loop
        while self.running:
            try:
                # Read all lines and process new ones
                try:
                    with open(log_path, 'r') as f:
                        lines = f.readlines()
                except IOError as e:
                    logger.warning(f"Could not read log file: {e}")
                    time.sleep(2)
                    continue
                
                # Process only lines we haven't seen
                new_lines = []
                current_hashes = set()
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Create hash of line for deduplication
                    line_hash = hash(line)
                    current_hashes.add(line_hash)
                    
                    # Only process if we haven't seen this line
                    if line_hash not in last_lines_hash:
                        new_lines.append(line)
                
                # Update our tracking set (keep only current file's lines)
                last_lines_hash = current_hashes
                
                # Process new lines
                for line in new_lines:
                    self.process_line(line)
                
                if new_lines:
                    logger.debug(f"Processed {len(new_lines)} new log lines")
                
                # Flush periodically
                if (time.time() - self.last_flush) >= self.config.flush_interval:
                    self.flush()
                
                time.sleep(0.5)
                
            except FileNotFoundError:
                logger.warning(f"Log file {log_path} not found, waiting...")
                last_lines_hash = set()
                time.sleep(5)
            except Exception as e:
                logger.error(f"Error processing log file: {e}")
                time.sleep(1)
        
        # Final flush on shutdown
        self.flush()
    
    def cleanup(self):
        """Cleanup resources."""
        self.flush()
        self.geoip.close()
        self.db.close()
        logger.info(f"Cleanup completed. Stats: Nginx={self.stats.get('nginx', 0)}, "
                   f"Apache={self.stats.get('apache', 0)}, Unknown={self.stats.get('unknown', 0)}")


# ═══════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("WGP - Web Geo Profiler - Log Processor")
    logger.info("Supports: Nginx, Apache")
    logger.info("=" * 70)
    logger.info(f"PostgreSQL: {config.postgres_host}:{config.postgres_port}/{config.postgres_db}")
    logger.info(f"Log file: {config.log_file}")
    logger.info(f"GeoIP DB: {config.geoip_db}")
    logger.info(f"Default server type: {config.default_server_type}")
    logger.info(f"Batch size: {config.batch_size}, Flush interval: {config.flush_interval}s")
    logger.info("=" * 70)
    
    processor = LogProcessor(config)
    
    try:
        processor.tail_file()
    finally:
        processor.cleanup()
    
    logger.info("Log processor stopped")


if __name__ == '__main__':
    main()
