#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# NGP - Filebeat Installation Script for Nginx Server
# ═══════════════════════════════════════════════════════════════════════════
#
# Run this script on your Nginx server to install and configure Filebeat
#
# Usage:
#   chmod +x install-filebeat.sh
#   sudo ./install-filebeat.sh YOUR_NGP_SERVER_IP
#
# ═══════════════════════════════════════════════════════════════════════════

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "              NGP - Filebeat Installation for Nginx Server"
echo "═══════════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ Please run as root (sudo)${NC}"
    exit 1
fi

# Get NGP server IP
NGP_SERVER_IP="${1}"
if [ -z "$NGP_SERVER_IP" ]; then
    echo -e "${YELLOW}Usage: $0 YOUR_NGP_SERVER_IP${NC}"
    echo -e "${YELLOW}Example: $0 192.168.1.100${NC}"
    exit 1
fi

echo -e "${CYAN}📦 Installing Filebeat...${NC}"

# Detect OS
if [ -f /etc/debian_version ]; then
    # Debian/Ubuntu
    echo "Detected Debian/Ubuntu system"
    
    # Add Elastic repository
    wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | gpg --dearmor -o /usr/share/keyrings/elastic-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/elastic-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | tee /etc/apt/sources.list.d/elastic-8.x.list
    
    apt-get update
    apt-get install -y filebeat
    
elif [ -f /etc/redhat-release ]; then
    # RHEL/CentOS/Fedora
    echo "Detected RHEL/CentOS/Fedora system"
    
    # Add Elastic repository
    rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch
    cat > /etc/yum.repos.d/elastic.repo << EOF
[elastic-8.x]
name=Elastic repository for 8.x packages
baseurl=https://artifacts.elastic.co/packages/8.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=1
autorefresh=1
type=rpm-md
EOF
    
    yum install -y filebeat
    
else
    echo -e "${RED}❌ Unsupported operating system${NC}"
    echo "Please install Filebeat manually: https://www.elastic.co/guide/en/beats/filebeat/current/filebeat-installation.html"
    exit 1
fi

echo -e "${CYAN}⚙️  Configuring Filebeat...${NC}"

# Backup original config
cp /etc/filebeat/filebeat.yml /etc/filebeat/filebeat.yml.backup

# Create NGP configuration
cat > /etc/filebeat/filebeat.yml << EOF
# ═══════════════════════════════════════════════════════════════════════════
# NGP - Filebeat Configuration (Auto-generated)
# ═══════════════════════════════════════════════════════════════════════════

filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/nginx/access.log
      - /var/log/nginx/*access*.log
    json.keys_under_root: true
    json.add_error_key: true
    fields:
      log_type: nginx_access
      server_name: "$(hostname)"
    fields_under_root: true

processors:
  - add_host_metadata:
      when.not.contains.tags: forwarded
  - drop_event:
      when:
        contains:
          request_uri: "/health"

output.logstash:
  hosts: ["${NGP_SERVER_IP}:5044"]
  loadbalance: true
  backoff.init: 1s
  backoff.max: 60s

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7

monitoring.enabled: false
EOF

echo -e "${CYAN}🔄 Starting Filebeat...${NC}"

# Enable and start Filebeat
systemctl daemon-reload
systemctl enable filebeat
systemctl start filebeat

# Check status
sleep 2
if systemctl is-active --quiet filebeat; then
    echo -e "${GREEN}✅ Filebeat installed and running!${NC}"
    echo ""
    echo -e "${CYAN}Configuration:${NC}"
    echo "  - Config file: /etc/filebeat/filebeat.yml"
    echo "  - Logs: /var/log/filebeat/filebeat"
    echo "  - Sending to: ${NGP_SERVER_IP}:5044"
    echo ""
    echo -e "${YELLOW}⚠️  Make sure your Nginx uses JSON log format!${NC}"
    echo "  See: nginx-server/nginx.conf.example"
    echo ""
    echo -e "${CYAN}Useful commands:${NC}"
    echo "  sudo systemctl status filebeat    # Check status"
    echo "  sudo systemctl restart filebeat   # Restart"
    echo "  sudo tail -f /var/log/filebeat/filebeat  # View logs"
else
    echo -e "${RED}❌ Filebeat failed to start${NC}"
    echo "Check logs: sudo journalctl -u filebeat"
    exit 1
fi

