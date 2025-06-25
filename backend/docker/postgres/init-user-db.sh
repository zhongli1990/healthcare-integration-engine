#!/bin/bash
set -e

echo "Setting up PostgreSQL..."

# Create a temporary file with the new configuration
cat > /tmp/pg_hba_new.conf << EOF
# Custom configuration for healthcare integration
# TYPE  DATABASE        USER            ADDRESS                 METHOD
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
host    all             all             all                     md5
local   replication     all                                     trust
host    replication     all             127.0.0.1/32            trust
host    replication     all             ::1/128                 trust
EOF

# Append the original configuration (excluding the default entries)
grep -v -E '^local|^host' "$PGDATA/pg_hba.conf" >> /tmp/pg_hba_new.conf

# Replace the original file
mv /tmp/pg_hba_new.conf "$PGDATA/pg_hba.conf"

echo "PostgreSQL configuration updated successfully!"
