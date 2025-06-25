#!/bin/sh
set -ex

# Debug: Print environment variables
echo "=== Environment Variables ==="
printenv | sort
echo "==========================="

# Default values if not set
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-postgres}
POSTGRES_HOST=${POSTGRES_HOST:-db}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_DB=${POSTGRES_DB:-healthcare_integration}

# Get database connection details from DATABASE_URL if set
if [ -n "$DATABASE_URL" ]; then
    echo "Using DATABASE_URL: $DATABASE_URL"
    # Extract from DATABASE_URL format: postgresql://user:password@host:port/dbname
    # Remove the protocol part
    PROTO="$(echo $DATABASE_URL | grep :// | sed -e's,^\(.*://\).*,\1,g')"
    # Remove the protocol
    URL=$(echo $DATABASE_URL | sed -e s,$PROTO,,g)
    # Extract the user (and password if any)
    USERPASS="$(echo $URL | grep @ | cut -d@ -f1)"
    PASS="$(echo $USERPASS | grep : | cut -d: -f2)"
    if [ -n "$PASS" ]; then
        export POSTGRES_USER=$(echo $USERPASS | grep : | cut -d: -f1)
        export POSTGRES_PASSWORD=$PASS
    else
        export POSTGRES_USER=$USERPASS
    fi
    # Extract the host and port
    HOSTPORT=$(echo $URL | sed -e s,$USERPASS@,,g | cut -d/ -f1)
    export POSTGRES_HOST=$(echo $HOSTPORT | cut -d: -f1)
    if [ $(echo $HOSTPORT | grep -o : | wc -l) -gt 0 ]; then
        export POSTGRES_PORT=$(echo $HOSTPORT | cut -d: -f2)
    fi
    # Extract the database name
    export POSTGRES_DB=$(echo $URL | grep / | cut -d/ -f2- | cut -d? -f1)
fi

# Export for Alembic
export POSTGRES_USER POSTGRES_PASSWORD POSTGRES_HOST POSTGRES_PORT POSTGRES_DB

# Debug: Print connection details
echo "=== Database Connection Details ==="
echo "Host: $POSTGRES_HOST"
echo "User: $POSTGRES_USER"
echo "Database: $POSTGRES_DB"
echo "=================================="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready on $POSTGRES_HOST:$POSTGRES_PORT..."
max_retries=60
retry_count=0

until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' >/dev/null 2>&1 || [ $retry_count -eq $max_retries ]
do
  retry_count=$((retry_count+1))
  echo "PostgreSQL is unavailable - sleeping ($retry_count/$max_retries)"
  sleep 1
done

if [ $retry_count -eq $max_retries ]; then
  echo "Failed to connect to PostgreSQL after $max_retries attempts"
  exit 1
fi

# Check if database exists, create if it doesn't
if ! PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; then
  echo "Database $POSTGRES_DB does not exist, creating..."
  PGPASSWORD=$POSTGRES_PASSWORD createdb -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" "$POSTGRES_DB"
fi

# Check if we have any tables
table_count=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d '[:space:]')

echo "Found $table_count tables in the database"

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Verify migrations
migration_count=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT count(*) FROM alembic_version;" 2>/dev/null | tr -d '[:space:]' || echo "0")

echo "=== Migration Status ==="
if [ "$migration_count" -gt 0 ]; then
  echo "Successfully applied $migration_count migrations"
  PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT version_num FROM alembic_version;"
else
  echo "No migrations applied or error checking migration status"
  exit 1
fi

echo "Migrations completed successfully"

# Keep container running if this is the entrypoint
if [ "$1" = "sleep" ]; then
    echo "Container started in sleep mode"
    tail -f /dev/null
fi
