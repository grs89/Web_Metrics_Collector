FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (needed for some python packages if not binary)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY log_processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY log_processor/ .

CMD ["python", "main.py"]
