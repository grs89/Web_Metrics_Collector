# ═══════════════════════════════════════════════════════════════════════════
# NGP - Log Processor Service
# ═══════════════════════════════════════════════════════════════════════════
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create geoip directory
RUN mkdir -p /app/geoip

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Run the log processor
CMD ["python", "-u", "main.py"]

