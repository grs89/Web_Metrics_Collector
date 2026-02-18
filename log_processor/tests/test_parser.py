import pytest
from parser import LogParser

class TestLogParser:
    def test_parse_nginx_json(self):
        log_line = '{"remote_addr": "127.0.0.1", "time_local": "2023-10-27T10:00:00+00:00", "request_method": "GET", "request_uri": "/index.html", "status": 200, "body_bytes_sent": 1024, "request_time": "0.100", "http_user_agent": "TestAgent"}'
        result = LogParser.parse(log_line, "nginx-json")
        
        assert result is not None
        assert result['client_ip'] == "127.0.0.1"
        assert result['method'] == "GET"
        assert result['status_code'] == 200
        assert result['request_time_ms'] == 100
        assert result['user_agent'] == "TestAgent"

    def test_parse_apache_combined(self):
        log_line = '127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326 "http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"'
        result = LogParser.parse(log_line, "apache-combined")
        
        assert result is not None
        assert result['client_ip'] == "127.0.0.1"
        assert result['method'] == "GET"
        assert result['uri'] == "/apache_pb.gif"
        assert result['status_code'] == 200
        assert result['response_size'] == 2326
        assert result['user_agent'] == "Mozilla/4.08 [en] (Win98; I ;Nav)"
        
    def test_parse_iis_w3c(self):
        # 2002-05-02 17:42:15 172.22.255.255 - 172.30.255.255 80 GET /images/picture.jpg - 200 Mozilla/4.0+(compatible;MSIE+5.5;+Windows+2000+Server)
        # Note: The parser relies on specific column positions. The key ones are:
        # 0:date 1:time 3:method 4:uri-stem 8:client-ip 9:ua 11:status
        log_line = "2023-10-27 10:00:00 192.168.1.1 GET /app/main.css query 80 user 10.0.0.1 Mozilla/5.0+TestAgent - 200 0 0 500"
        
        result = LogParser.parse(log_line, "iis")
        
        assert result is not None
        assert result['client_ip'] == "10.0.0.1" # Index 8
        assert result['method'] == "GET"
        assert result['uri'] == "/app/main.css?query"
        assert result['status_code'] == 200
        assert result['request_time_ms'] == 500 # Last column
        assert result['user_agent'] == "Mozilla/5.0 TestAgent" # Unquoted
    
    def test_invalid_log(self):
        assert LogParser.parse("invalid junk", "nginx-json") is None
