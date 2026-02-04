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
            # Try parsing as JSON first if configured or if it looks like JSON
            if log_type == 'nginx-json' or line.startswith('{'):
                try:
                    return LogParser._parse_json(line)
                except json.JSONDecodeError:
                    # Fallback to CLF if JSON fails but type was specifically json
                    # This happens if user configured wrong type
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
    def _parse_json(line):
        data = json.loads(line)
        # Normalize to internal schema
        # Expecting keys compatible with common Nginx JSON config
        # Try to extract request_time (Nginx usually logs seconds float)
        req_time_ms = 0
        try:
            rt = data.get('request_time') or data.get('upstream_response_time')
            if rt:
                # Handle "0.001" string or float
                req_time_ms = int(float(str(rt).split()[0].replace(',', '.')) * 1000)
        except (ValueError, TypeError):
            req_time_ms = 0

        return {
            'client_ip': data.get('remote_addr') or data.get('client_ip'),
            'timestamp': data.get('time_iso8601') or data.get('time_local'), # Needs parsing
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
            'timestamp': data['time'], # Needs format conversion
            'method': data['method'],
            'uri': data['uri'],
            'status_code': int(data['status']),
            'response_size': int(size),
            'request_time_ms': 0, # CLF doesn't have time by default
            'user_agent': data.get('ua'),
            'referrer': data.get('referrer'),
            'raw_log': line
        }

    @staticmethod
    def _parse_iis(line):
        # Default IIS W3C Fields: date time s-ip cs-method cs-uri-stem cs-uri-query s-port cs-username c-ip cs(User-Agent) cs(Referer) sc-status sc-substatus sc-win32-status time-taken
        # Note: IIS replaces spaces with + in UA and Referrer
        
        # Skip comments
        if line.startswith('#'):
            return None

        try:
            parts = line.split()
            # Basic validation: standard IIS log has at least 14-15 columns. 
            # We map aggressively based on standard positions.
            if len(parts) < 10: 
                return None
            
            # Extract common fields based on standard W3C layout
            # 0:date 1:time 2:s-ip 3:method 4:uri-stem 5:query 6:port 7:user 8:c-ip 9:ua 10:ref 11:status
            
            # Combine Date+Time
            timestamp_str = f"{parts[0]} {parts[1]}"
            
            method = parts[3]
            uri_stem = parts[4]
            uri_query = parts[5]
            client_ip = parts[8]
            user_agent = urllib.parse.unquote_plus(parts[9])
            referrer = urllib.parse.unquote_plus(parts[10]) # might be -
            status = int(parts[11])
            
            # Reconstruct Full URI
            uri = uri_stem
            if uri_query != '-':
                uri = f"{uri_stem}?{uri_query}"
                
            if referrer == '-':
                referrer = None
                
            if user_agent == '-':
                user_agent = None

            # Try to get time-taken (last column usually)
            time_taken = 0
            if len(parts) >= 15:
                try:
                     time_taken = int(parts[-1]) # IIS logs milliseconds
                except ValueError:
                    time_taken = 0

            return {
                'client_ip': client_ip,
                'timestamp': timestamp_str, # ISO-like "YYYY-MM-DD HH:MM:SS" is usually fine to parse directly later
                'method': method,
                'uri': uri,
                'status_code': status,
                'response_size': 0, # IIS default log usually puts size at the end, but variable. defaulting to 0.
                'request_time_ms': time_taken,
                'user_agent': user_agent,
                'referrer': referrer,
                'raw_log': line
            }

        except (ValueError, IndexError):
            return None

