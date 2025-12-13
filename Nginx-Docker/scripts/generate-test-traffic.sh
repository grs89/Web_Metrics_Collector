#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# NGP - Generate Test Traffic
# ═══════════════════════════════════════════════════════════════════════════
# 
# Generates sample traffic to test the NGP system
# ═══════════════════════════════════════════════════════════════════════════

set -e

HOST="${1:-http://localhost}"
COUNT="${2:-100}"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "                   NGP - Test Traffic Generator"
echo "═══════════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

echo -e "${GREEN}Generating $COUNT requests to $HOST...${NC}"
echo ""

# Array of paths to test
PATHS=(
    "/"
    "/health"
    "/index.html"
    "/about"
    "/contact"
    "/api/users"
    "/api/products"
    "/api/orders"
    "/static/css/style.css"
    "/static/js/app.js"
    "/images/logo.png"
    "/docs"
    "/login"
    "/register"
    "/dashboard"
)

# Array of user agents
USER_AGENTS=(
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0"
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    "curl/8.1.2"
    "PostmanRuntime/7.33.0"
)

# Generate requests
for i in $(seq 1 $COUNT); do
    # Random path
    PATH_IDX=$((RANDOM % ${#PATHS[@]}))
    URL="${HOST}${PATHS[$PATH_IDX]}"
    
    # Random user agent
    UA_IDX=$((RANDOM % ${#USER_AGENTS[@]}))
    UA="${USER_AGENTS[$UA_IDX]}"
    
    # Random X-Forwarded-For (simulating different IPs)
    OCTET1=$((RANDOM % 223 + 1))
    OCTET2=$((RANDOM % 256))
    OCTET3=$((RANDOM % 256))
    OCTET4=$((RANDOM % 256))
    XFF="${OCTET1}.${OCTET2}.${OCTET3}.${OCTET4}"
    
    # Make request
    curl -s -o /dev/null -w "" \
        -H "User-Agent: ${UA}" \
        -H "X-Forwarded-For: ${XFF}" \
        "${URL}" 2>/dev/null || true
    
    # Progress
    if [ $((i % 10)) -eq 0 ]; then
        echo -ne "\r  Progress: $i / $COUNT requests"
    fi
    
    # Small delay
    sleep 0.05
done

echo -e "\r  Progress: $COUNT / $COUNT requests"
echo ""
echo -e "${GREEN}✅ Generated $COUNT test requests!${NC}"
echo ""
echo "View the results in Grafana: http://localhost:3000"

