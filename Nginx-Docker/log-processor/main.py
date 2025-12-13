#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════
NGP - Nginx Log Processor
Parses Nginx JSON logs, enriches with GeoIP data, and stores in PostgreSQL
═══════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import signal
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

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
    postgres_user: str = os.getenv('POSTGRES_USER', 'ngp_user')
    postgres_password: str = os.getenv('POSTGRES_PASSWORD', 'ngp_secure_password_2024')
    postgres_db: str = os.getenv('POSTGRES_DB', 'nginx_logs')
    log_file: str = os.getenv('LOG_FILE', '/var/log/nginx/access.log')
    geoip_db: str = os.getenv('GEOIP_DB', '/app/geoip/GeoLite2-City.mmdb')
    batch_size: int = int(os.getenv('BATCH_SIZE', '100'))
    flush_interval: float = float(os.getenv('FLUSH_INTERVAL', '5.0'))


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
    
    def insert_logs(self, logs: list[Dict[str, Any]]) -> int:
        """Insert multiple log entries in batch."""
        if not logs:
            return 0
        
        columns = [
            'timestamp', 'remote_addr', 'remote_user', 'request_method', 'request_uri',
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
                    INSERT INTO nginx_access_logs ({})
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
# Log Parser
# ═══════════════════════════════════════════════════════════════════════════

class LogParser:
    """Parses Nginx JSON log entries."""
    
    @staticmethod
    def parse_line(line: str) -> Optional[Dict[str, Any]]:
        """Parse a single JSON log line."""
        if not line.strip():
            return None
        
        try:
            data = json.loads(line)
            
            # Clean and validate required fields
            parsed = {
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
            logger.debug(f"Failed to parse log line: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════
# Log File Watcher
# ═══════════════════════════════════════════════════════════════════════════

class LogProcessor:
    """Main log processor that watches and processes Nginx logs."""
    
    def __init__(self, config: Config):
        self.config = config
        self.geoip = GeoIPHandler(config.geoip_db)
        self.db = DatabaseHandler(config)
        self.parser = LogParser()
        self.buffer: list[Dict[str, Any]] = []
        self.last_flush = time.time()
        self.running = True
        self.file_position = 0
        
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
            return
        
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
            logger.info(f"Inserted {count} log entries")
        
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
        logger.info("Cleanup completed")


# ═══════════════════════════════════════════════════════════════════════════
# Main Entry Point
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("NGP - Nginx Geo Profiler - Log Processor")
    logger.info("=" * 70)
    logger.info(f"PostgreSQL: {config.postgres_host}:{config.postgres_port}/{config.postgres_db}")
    logger.info(f"Log file: {config.log_file}")
    logger.info(f"GeoIP DB: {config.geoip_db}")
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

