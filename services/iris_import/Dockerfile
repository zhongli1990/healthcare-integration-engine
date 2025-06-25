FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    gcc \
    python3-dev \
    libldap2-dev \
    libsasl2-dev \
    ldap-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY services/iris_import/requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Create necessary directories
RUN mkdir -p /app/app /app/uploads /app/app/templates /app/app/static

# Copy the application code
COPY services/iris_import/app /app/app

# Copy test files and directories
COPY services/iris_import/tests /app/tests
COPY services/iris_import/scripts /app/scripts

# Copy the test relationships scripts
COPY services/iris_import/tests/test_relationships.py /app/
COPY services/iris_import/tests/test_relationship_import.py /app/

# Copy samples directory for testing
COPY samples /app/samples

# Install Jinja2 explicitly to ensure it's available
RUN pip install --no-cache-dir Jinja2==3.0.3

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV UPLOAD_DIR=/app/uploads

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
