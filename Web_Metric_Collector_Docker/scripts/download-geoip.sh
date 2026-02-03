#!/bin/bash
# ═══════════════════════════════════════════════════════════════════════════
# NGP - Download MaxMind GeoLite2 Database
# ═══════════════════════════════════════════════════════════════════════════
# 
# This script downloads the free GeoLite2-City database from MaxMind.
# You need a free MaxMind account and license key to download.
#
# Get your free license key at: https://www.maxmind.com/en/geolite2/signup
# ═══════════════════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
GEOIP_DIR="$PROJECT_DIR/log-processor/geoip"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "═══════════════════════════════════════════════════════════════════════════"
echo "              NGP - MaxMind GeoLite2 Database Downloader"
echo "═══════════════════════════════════════════════════════════════════════════"
echo -e "${NC}"

# Create directory
mkdir -p "$GEOIP_DIR"

# Check if license key is provided
if [ -z "$MAXMIND_LICENSE_KEY" ]; then
    echo -e "${YELLOW}⚠️  MAXMIND_LICENSE_KEY environment variable not set.${NC}"
    echo ""
    echo "To download the GeoLite2 database, you need a free MaxMind account."
    echo ""
    echo "1. Sign up at: https://www.maxmind.com/en/geolite2/signup"
    echo "2. Generate a license key in your account"
    echo "3. Run this script with:"
    echo ""
    echo -e "   ${CYAN}MAXMIND_LICENSE_KEY=your_key ./scripts/download-geoip.sh${NC}"
    echo ""
    echo -e "${YELLOW}Alternative: Manual Download${NC}"
    echo "1. Download from: https://dev.maxmind.com/geoip/geoip2/geolite2/"
    echo "2. Extract GeoLite2-City.mmdb to: log-processor/geoip/"
    echo ""
    
    # Check if file already exists
    if [ -f "$GEOIP_DIR/GeoLite2-City.mmdb" ]; then
        echo -e "${GREEN}✅ GeoLite2-City.mmdb already exists in $GEOIP_DIR${NC}"
        exit 0
    fi
    
    exit 1
fi

echo -e "${CYAN}📥 Downloading GeoLite2-City database...${NC}"

# Download URL
DOWNLOAD_URL="https://download.maxmind.com/app/geoip_download?edition_id=GeoLite2-City&license_key=${MAXMIND_LICENSE_KEY}&suffix=tar.gz"

# Temporary file
TEMP_FILE=$(mktemp)
TEMP_DIR=$(mktemp -d)

# Download
curl -s -o "$TEMP_FILE" "$DOWNLOAD_URL"

# Check if download was successful
if [ ! -s "$TEMP_FILE" ]; then
    echo -e "${RED}❌ Download failed. Please check your license key.${NC}"
    rm -f "$TEMP_FILE"
    rmdir "$TEMP_DIR"
    exit 1
fi

# Extract
echo -e "${CYAN}📦 Extracting database...${NC}"
tar -xzf "$TEMP_FILE" -C "$TEMP_DIR"

# Find and move the mmdb file
MMDB_FILE=$(find "$TEMP_DIR" -name "GeoLite2-City.mmdb" -type f)

if [ -z "$MMDB_FILE" ]; then
    echo -e "${RED}❌ Could not find GeoLite2-City.mmdb in the archive.${NC}"
    rm -f "$TEMP_FILE"
    rm -rf "$TEMP_DIR"
    exit 1
fi

# Move to destination
mv "$MMDB_FILE" "$GEOIP_DIR/GeoLite2-City.mmdb"

# Cleanup
rm -f "$TEMP_FILE"
rm -rf "$TEMP_DIR"

echo -e "${GREEN}✅ GeoLite2-City.mmdb downloaded successfully!${NC}"
echo -e "   Location: $GEOIP_DIR/GeoLite2-City.mmdb"
echo ""
echo -e "${CYAN}You can now start the NGP stack with: docker compose up -d${NC}"

