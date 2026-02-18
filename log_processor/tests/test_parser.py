from datetime import datetime
from parser import LogParser

class TestLogParser:
    def test_parse_nginx_json(self):
        log_line = '{"remote_addr": "127.0.0.1", "time_local": "2023-10-27T10:00:00+00:00", "request_method": "GET", "request_uri": "/index.html", "status": 200, "body_bytes_sent": 1024, "request_time": "0.100", "http_user_agent": "TestAgent"}'
        result = LogParser.parse(log_line, "nginx-json")
        
        assert result is not None
        assert isinstance(result['timestamp'], datetime)
        assert result['client_ip'] == "127.0.0.1"
        assert result['method'] == "GET"
        assert result['status_code'] == 200
        assert result['request_time_ms'] == 100
        assert result['user_agent'] == "TestAgent"

    def test_parse_apache_combined(self):
        log_line = '127.0.0.1 - - [10/Oct/2000:13:55:36 -0700] "GET /apache_pb.gif HTTP/1.0" 200 2326 "http://www.example.com/start.html" "Mozilla/4.08 [en] (Win98; I ;Nav)"'
        result = LogParser.parse(log_line, "apache-combined")
        
        assert result is not None
        assert isinstance(result['timestamp'], datetime)
        assert result['client_ip'] == "127.0.0.1"
        assert result['method'] == "GET"
        assert result['uri'] == "/apache_pb.gif"
        assert result['status_code'] == 200
        assert result['response_size'] == 2326
        assert result['user_agent'] == "Mozilla/4.08 [en] (Win98; I ;Nav)"
        
    def test_parse_iis_w3c(self):
        log_line = "2023-10-27 10:00:00 192.168.1.1 GET /app/main.css query 80 user 10.0.0.1 Mozilla/5.0+TestAgent - 200 0 0 500"
        
        result = LogParser.parse(log_line, "iis")
        
        assert result is not None
        assert isinstance(result['timestamp'], datetime)
        assert result['client_ip'] == "10.0.0.1"
        assert result['method'] == "GET"
        assert result['uri'] == "/app/main.css?query"
        assert result['status_code'] == 200
        assert result['request_time_ms'] == 500
        assert result['user_agent'] == "Mozilla/5.0 TestAgent"

    def test_parse_traefik(self):
        log_line = '{"ClientAddr":"1.2.3.4:5678","Duration":2000000,"RequestMethod":"GET","RequestPath":"/","ResponseStatus":200,"DownstreamContentSize":500,"StartUTC":"2023-10-27T10:00:00Z","RequestUserAgent":"TraefikAgent"}'
        result = LogParser.parse(log_line, "traefik")
        
        assert result is not None
        assert isinstance(result['timestamp'], datetime)
        assert result['client_ip'] == "1.2.3.4"
        assert result['method'] == "GET"
        assert result['status_code'] == 200
        assert result['request_time_ms'] == pytest.approx(2.0)
        assert result['user_agent'] == "TraefikAgent"

    def test_parse_caddy(self):
        log_line = '{"ts":1698393600,"duration":0.005,"status":200,"size":1024,"request":{"remote_addr":"5.6.7.8:1234","method":"POST","uri":"/api/data","headers":{"User-Agent":["CaddyAgent"],"Referer":["https://google.com"]}}}'
        result = LogParser.parse(log_line, "caddy")
        
        assert result is not None
        assert isinstance(result['timestamp'], datetime)
        assert result['client_ip'] == "5.6.7.8"
        assert result['method'] == "POST"
        assert result['status_code'] == 200
        assert result['request_time_ms'] == pytest.approx(5.0)
        assert result['user_agent'] == "CaddyAgent"
        assert result['referrer'] == "https://google.com"

    def test_invalid_log(self):
        assert LogParser.parse("invalid junk", "nginx-json") is None
