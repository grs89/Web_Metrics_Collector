import json
import re
import logging
import urllib.parse
from datetime import datetime

# Combined Log Format Regex
# 127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326 "http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"
CLF_REGEX = re.compile(
    r'(?P<ip>[\d\.]+) - - \[(?P<time>.*?)\] "(?P<method>\w+) (?P<uri>.*?) (?P<protocol>.*?)" (?P<status>\d+) (?P<size>\d+|-)( "(?P<referrer>.*?)" "(?P<ua>.*?)")?'
)

class LogParser:
    @staticmethod
    def parse(line, log_type):
        line = line.strip()
        if not line:
            return None
            
        try:
            # Route to specific parsers based on type
            if log_type == 'traefik':
                return LogParser._parse_traefik(line)
            
            elif log_type == 'caddy':
                return LogParser._parse_caddy(line)

            # Try parsing as JSON first if configured or if it looks like JSON
            elif log_type == 'nginx-json' or line.startswith('{'):
                try:
                    return LogParser._parse_json(line)
                except json.JSONDecodeError:
                    # Fallback to CLF if JSON fails but type was specifically json
                    logging.warning(f"Failed to parse as JSON, retrying as Combined Log Format: {line[:30]}...")
                    return LogParser._parse_clf(line)

            elif 'combined' in log_type:
               return LogParser._parse_clf(line)
            
            elif 'iis' in log_type: # IIS W3C Support
                return LogParser._parse_iis(line)
                
            else:
                # Default fallback
                return LogParser._parse_clf(line)
        except Exception as e:
            logging.error(f"Error parsing line: {line[:50]}... Error: {e}")
            return None

    @staticmethod
    def _parse_datetime(ts_val):
        if not ts_val or ts_val == '-':
            return datetime.now()
        
        # Handle numeric timestamps (Caddy uses float Unix seconds)
        if isinstance(ts_val, (int, float)):
            return datetime.fromtimestamp(float(ts_val))
        
        # Handle strings that look like numbers
        if isinstance(ts_val, str) and ts_val.replace('.', '', 1).isdigit():
            return datetime.fromtimestamp(float(ts_val))

        # Formats to try
        formats = [
            "%d/%b/%Y:%H:%M:%S %z", # CLF: 18/Feb/2026:00:04:27 -0500
            "%Y-%m-%d %H:%M:%S",    # IIS: 2026-02-18 13:50:19
            "%Y-%m-%dT%H:%M:%S%z",  # ISO8601
            "%Y-%m-%dT%H:%M:%SZ",   # ISO8601 UTC
        ]
        
        # Try ISO format first (fastest and handles many variants)
        try:
            return datetime.fromisoformat(ts_val.replace(' ', 'T'))
        except (ValueError, TypeError):
            pass

        for fmt in formats:
            try:
                return datetime.strptime(ts_val, fmt)
            except (ValueError, TypeError):
                continue
        
        logging.warning(f"Could not parse timestamp: {ts_val}. Using current time.")
        return datetime.now()

    @staticmethod
    def _parse_json(line):
        data = json.loads(line)
        # Normalize to internal schema
        req_time_ms = 0
        try:
            rt = data.get('request_time') or data.get('upstream_response_time')
            if rt:
                req_time_ms = int(float(str(rt).split()[0].replace(',', '.')) * 1000)
        except (ValueError, TypeError):
            req_time_ms = 0

        ts_val = data.get('time_iso8601') or data.get('time_local')
        return {
            'client_ip': data.get('remote_addr') or data.get('client_ip'),
            'timestamp': LogParser._parse_datetime(ts_val), 
            'method': data.get('request_method') or data.get('method'),
            'uri': data.get('request_uri') or data.get('uri'),
            'status_code': int(data.get('status') or 0),
            'response_size': int(data.get('body_bytes_sent') or 0),
            'request_time_ms': req_time_ms,
            'user_agent': data.get('http_user_agent'),
            'referrer': data.get('http_referer'),
            'raw_log': line
        }

    @staticmethod
    def _parse_traefik(line):
        data = json.loads(line)
        # Traefik uses StartUTC/StartLocal and Duration (nanoseconds)
        duration_ns = data.get('Duration', 0)
        req_time_ms = int(duration_ns) / 1_000_000 if duration_ns else 0
        
        # ClientAddr is usually IP:Port
        client_ip = data.get('ClientAddr', '').split(':')[0]
        
        return {
            'client_ip': client_ip or data.get('ClientHost'),
            'timestamp': LogParser._parse_datetime(data.get('StartUTC') or data.get('StartLocal')),
            'method': data.get('RequestMethod'),
            'uri': data.get('RequestPath'),
            'status_code': int(data.get('ResponseStatus') or 200),
            'response_size': int(data.get('DownstreamContentSize') or 0),
            'request_time_ms': req_time_ms,
            'user_agent': data.get('RequestUserAgent'),
            'referrer': data.get('RequestReferer'),
            'raw_log': line
        }

    @staticmethod
    def _parse_caddy(line):
        data = json.loads(line)
        # Caddy uses 'ts' (Unix float), 'duration' (seconds float)
        # and nested request object
        req = data.get('request', {})
        headers = req.get('headers', {})
        
        duration_s = data.get('duration') or data.get('latency', 0)
        req_time_ms = int(duration_s * 1000) if duration_s else 0
        
        client_ip = req.get('remote_addr', '').split(':')[0]
        
        return {
            'client_ip': client_ip,
            'timestamp': LogParser._parse_datetime(data.get('ts')),
            'method': req.get('method'),
            'uri': req.get('uri'),
            'status_code': int(data.get('status') or 200),
            'response_size': int(data.get('size') or 0),
            'request_time_ms': req_time_ms,
            'user_agent': headers.get('User-Agent', [None])[0] if isinstance(headers.get('User-Agent'), list) else headers.get('User-Agent'),
            'referrer': headers.get('Referer', [None])[0] if isinstance(headers.get('Referer'), list) else headers.get('Referer'),
            'raw_log': line
        }

    @staticmethod
    def _parse_clf(line):
        match = CLF_REGEX.match(line)
        if not match:
            return None
        
        data = match.groupdict()
        size = data['size']
        if size == '-':
            size = 0
            
        return {
            'client_ip': data['ip'],
            'timestamp': LogParser._parse_datetime(data['time']),
            'method': data['method'],
            'uri': data['uri'],
            'status_code': int(data['status']),
            'response_size': int(size),
            'request_time_ms': 0,
            'user_agent': data.get('ua'),
            'referrer': data.get('referrer'),
            'raw_log': line
        }

    @staticmethod
    def _parse_iis(line):
        if line.startswith('#'):
            return None

        try:
            parts = line.split()
            if len(parts) < 10: 
                return None
            
            # Combine Date+Time
            timestamp_str = f"{parts[0]} {parts[1]}"
            
            method = parts[3]
            uri_stem = parts[4]
            uri_query = parts[5]
            client_ip = parts[8]
            user_agent = urllib.parse.unquote_plus(parts[9])
            referrer = urllib.parse.unquote_plus(parts[10])
            status = int(parts[11])
            
            uri = uri_stem
            if uri_query != '-':
                uri = f"{uri_stem}?{uri_query}"
                
            if referrer == '-':
                referrer = None
                
            if user_agent == '-':
                user_agent = None

            time_taken = 0
            if len(parts) >= 15:
                try:
                     time_taken = int(parts[-1])
                except ValueError:
                    time_taken = 0

            return {
                'client_ip': client_ip,
                'timestamp': LogParser._parse_datetime(timestamp_str),
                'method': method,
                'uri': uri,
                'status_code': status,
                'response_size': 0,
                'request_time_ms': time_taken,
                'user_agent': user_agent,
                'referrer': referrer,
                'raw_log': line
            }

        except (ValueError, IndexError):
            return None

