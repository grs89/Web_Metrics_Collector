# --- Stage 1: Builder ---
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies into a user-specific folder
COPY log_processor/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Stage 2: Final Runtime ---
FROM python:3.12-slim

# Create a non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser

WORKDIR /app

# Install runtime dependencies ONLY (libpq5 is the runtime library for PostgreSQL)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
# Python --user installs to /root/.local, we copy it to our appuser's .local
COPY --from=builder /root/.local /home/appuser/.local
COPY log_processor/ .

# Ensure appuser owns their home and app directory
RUN chown -R appuser:appgroup /app /home/appuser

# Update PATH for the non-root user
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUSERBASE=/home/appuser/.local

# Switch to non-root user
USER appuser

# Expose metrics port
EXPOSE 8080

# Health check (verify event loop and metrics server)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python healthcheck.py

CMD ["python", "main.py"]
