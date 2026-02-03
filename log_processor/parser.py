import json
import re
import logging
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
        return {
            'client_ip': data.get('remote_addr') or data.get('client_ip'),
            'timestamp': data.get('time_iso8601') or data.get('time_local'), # Needs parsing
            'method': data.get('request_method') or data.get('method'),
            'uri': data.get('request_uri') or data.get('uri'),
            'status_code': int(data.get('status') or 0),
            'response_size': int(data.get('body_bytes_sent') or 0),
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
            'user_agent': data.get('ua'),
            'referrer': data.get('referrer'),
            'raw_log': line
        }
