FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libsasl2-dev \
    python3-dev \
    libldap2-dev \
    inotify-tools \
    curl \
    wget \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Create scripts directory
RUN mkdir -p /app/scripts

# Install Python dependencies first for better caching
COPY requirements.txt .
# Install all dependencies including test dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 8850

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8850/api/health || exit 1

# Commented out migration script for initial testing
# RUN chmod 777 /app/run_migrations.sh && \
#     sed -i 's/\r$//' /app/run_migrations.sh && \
#     ls -la /app/run_migrations.sh && \
#     cat /app/run_migrations.sh

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8850"]
