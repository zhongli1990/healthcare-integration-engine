FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    wget \
    gnupg2 \
    && rm -rf /var/lib/apt/lists/*

# Create directory for IRIS Python bindings
RUN mkdir -p /usr/irissys/mgr/python/

# Copy all files first
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -e .

EXPOSE 8080

ENTRYPOINT ["mcp-server-iris"]