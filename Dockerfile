FROM python:3.12-slim

# Create a non-root user with a fixed UID
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1000 appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY log_processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY log_processor/ .

# Change ownership of the application directory to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

CMD ["python", "main.py"]
